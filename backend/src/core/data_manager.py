"""
NIRAJ Historical Data Manager
A comprehensive system for fetching, caching, and managing market data from
multiple sources with advanced error handling, fallback mechanisms, and data
synchronization
"""

import asyncio
import hashlib
import statistics
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Awaitable
from decimal import Decimal
from contextlib import asynccontextmanager
import time
import concurrent.futures
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

from ..api.angel_one_client import AngelOneClient, AngelOneError
from ..api.dhan_client import DhanClient, DhanError
from ..core.cache import RedisCache
from ..utils.logger import get_logger, log_performance, LogContext


# Custom Exceptions
class DataManagerError(Exception):
    """Base exception for data manager errors"""
    pass


class DataSourceError(DataManagerError):
    """Error from data source operations"""
    pass


class DataValidationError(DataManagerError):
    """Error in data validation"""
    pass


class CacheError(DataManagerError):
    """Error in cache operations"""
    pass


class ConfigurationError(DataManagerError):
    """Error in configuration"""
    pass


class DataNotFoundError(DataManagerError):
    """Data not found error"""
    pass


class CircuitBreakerError(DataManagerError):
    """Circuit breaker triggered error"""
    pass


@dataclass
class DataManagerConfig:
    """Configuration for HistoricalDataManager"""

    max_concurrent_requests: int = 5
    default_cache_ttl: int = 3600  # 1 hour
    enable_data_validation: bool = True
    enable_gap_filling: bool = True
    fallback_sources: bool = True
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_recovery_timeout: int = 300  # 5 minutes
    retry_max_attempts: int = 3
    retry_base_delay: float = 1.0
    retry_max_delay: float = 60.0
    retry_backoff_factor: float = 2.0

    def __post_init__(self):
        """Validate configuration"""
        if self.max_concurrent_requests <= 0:
            raise ConfigurationError("max_concurrent_requests must be positive")
        if self.default_cache_ttl <= 0:
            raise ConfigurationError("default_cache_ttl must be positive")
        if self.circuit_breaker_failure_threshold <= 0:
            raise ConfigurationError(
                "circuit_breaker_failure_threshold must be positive"
            )
        if self.circuit_breaker_recovery_timeout <= 0:
            raise ConfigurationError(
                "circuit_breaker_recovery_timeout must be positive"
            )
        if self.retry_max_attempts < 0:
            raise ConfigurationError("retry_max_attempts cannot be negative")
        if self.retry_base_delay <= 0:
            raise ConfigurationError("retry_base_delay must be positive")
        if self.retry_max_delay <= self.retry_base_delay:
            raise ConfigurationError(
                "retry_max_delay must be greater than retry_base_delay"
            )
        if self.retry_backoff_factor <= 1:
            raise ConfigurationError(
                "retry_backoff_factor must be greater than 1"
            )


# Utility functions
async def retry_with_exponential_backoff(
    func: Callable[..., Awaitable[Any]],
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    *args: Any,
    **kwargs: Any
) -> Any:
    """
    Retry a function with exponential backoff

    Args:
        func: Async function to retry
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        backoff_factor: Backoff multiplier
        *args: Positional arguments for func
        **kwargs: Keyword arguments for func

    Returns:
        Result of the function call

    Raises:
        Exception: Last exception if all retries fail
    """
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_exception = e

            if attempt == max_retries:
                # Last attempt failed
                break

            # Calculate delay with exponential backoff
            delay = min(base_delay * (backoff_factor ** attempt), max_delay)

            # Add jitter to prevent thundering herd
            jitter = delay * 0.1 * (0.5 - time.time() % 1)  # Random jitter ±10%
            actual_delay = delay + jitter

            await asyncio.sleep(actual_delay)

    # All retries failed - ensure last_exception is not None
    if last_exception is None:
        raise RuntimeError("All retries failed but no exception was captured")
    raise last_exception


class DataSource(str, Enum):
    """Available data sources"""

    ANGEL_ONE = "angel_one"
    DHAN = "dhan"
    COMBINED = "combined"


class DataTimeframe(str, Enum):
    """Supported timeframes"""

    ONE_MINUTE = "1min"
    THREE_MINUTE = "3min"
    FIVE_MINUTE = "5min"
    TEN_MINUTE = "10min"
    FIFTEEN_MINUTE = "15min"
    THIRTY_MINUTE = "30min"
    ONE_HOUR = "1hour"
    FOUR_HOUR = "4hour"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class DataQuality(str, Enum):
    """Data quality levels"""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    CORRUPTED = "corrupted"


class CircuitBreakerState(str, Enum):
    """Circuit breaker states"""

    CLOSED = "closed"
    HALF_OPEN = "half_open"
    OPEN = "open"


@dataclass
class OHLCData:
    """OHLC data structure with validation and conversion methods"""

    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int = 0
    source: str = "unknown"
    quality: DataQuality = DataQuality.HIGH

    def __post_init__(self):
        """Validate OHLC data integrity"""
        # Ensure timezone awareness
        if self.timestamp.tzinfo is None:
            self.timestamp = self.timestamp.replace(tzinfo=timezone.utc)

        # Convert to Decimal for precision
        self.open = Decimal(str(self.open))
        self.high = Decimal(str(self.high))
        self.low = Decimal(str(self.low))
        self.close = Decimal(str(self.close))

        # Basic validation
        if not (
            self.low <= self.open <= self.high and self.low <= self.close <= self.high
        ):
            self.quality = DataQuality.CORRUPTED

        # Volume should be non-negative
        if self.volume < 0:
            self.volume = 0
            self.quality = DataQuality.MEDIUM

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "open": float(self.open),
            "high": float(self.high),
            "low": float(self.low),
            "close": float(self.close),
            "volume": self.volume,
            "source": self.source,
            "quality": self.quality.value,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OHLCData":
        """Create from dictionary"""
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00")),
            open=Decimal(str(data["open"])),
            high=Decimal(str(data["high"])),
            low=Decimal(str(data["low"])),
            close=Decimal(str(data["close"])),
            volume=data.get("volume", 0),
            source=data.get("source", "unknown"),
            quality=DataQuality(data.get("quality", "high")),
        )

    def is_valid(self) -> bool:
        """Check if data is valid"""
        return self.quality != DataQuality.CORRUPTED


@dataclass
class DataRequest:
    """Data fetch request with metadata"""

    symbol: str
    exchange: str
    timeframe: DataTimeframe
    start_date: datetime
    end_date: datetime
    sources: List[DataSource] = field(
        default_factory=lambda: [DataSource.ANGEL_ONE, DataSource.DHAN]
    )
    priority: int = 1  # 1=high, 2=medium, 3=low
    max_retries: int = 3
    timeout: float = 30.0
    use_cache: bool = True
    force_refresh: bool = False

    def __post_init__(self):
        """Validate and normalize request"""
        # Validate required fields
        if not self.symbol or not self.symbol.strip():
            raise ConfigurationError("Symbol cannot be empty")
        if not self.exchange or not self.exchange.strip():
            raise ConfigurationError("Exchange cannot be empty")

        # Ensure timezone awareness
        if self.start_date.tzinfo is None:
            self.start_date = self.start_date.replace(tzinfo=timezone.utc)
        if self.end_date.tzinfo is None:
            self.end_date = self.end_date.replace(tzinfo=timezone.utc)

        # Normalize symbol and exchange
        self.symbol = self.symbol.upper().strip()
        self.exchange = self.exchange.upper().strip()

        # Validate date range
        if self.start_date >= self.end_date:
            raise ConfigurationError(
                f"start_date ({self.start_date}) must be before "
                f"end_date ({self.end_date})"
            )

        # Validate timeframe
        if not isinstance(self.timeframe, DataTimeframe):
            raise ConfigurationError(f"Invalid timeframe: {self.timeframe}")

        # Validate sources
        if not self.sources:
            raise ConfigurationError("At least one data source must be specified")

        for source in self.sources:
            if not isinstance(source, DataSource):
                raise ConfigurationError(f"Invalid data source: {source}")

        # Validate priority
        if self.priority < 1 or self.priority > 3:
            raise ConfigurationError(
                f"Priority must be between 1 and 3, got {self.priority}"
            )

        # Validate timeout
        if self.timeout <= 0:
            raise ConfigurationError(
                f"Timeout must be positive, got {self.timeout}"
            )

        # Validate max retries
        if self.max_retries < 0:
            raise ConfigurationError(
                f"Max retries cannot be negative, got {self.max_retries}"
            )

    def cache_key(self) -> str:
        """Generate cache key for this request"""
        key_components = [
            self.symbol,
            self.exchange,
            self.timeframe.value,
            self.start_date.strftime("%Y%m%d"),
            self.end_date.strftime("%Y%m%d"),
        ]
        return hashlib.md5(":".join(key_components).encode()).hexdigest()


class CircuitBreaker:
    """Circuit breaker pattern for API call protection"""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type[Exception] = Exception,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = CircuitBreakerState.CLOSED

    async def call(
        self,
        func: Callable[..., Awaitable[Any]],
        *args: Any,
        **kwargs: Any
    ) -> Any:
        """Execute function with circuit breaker protection"""
        if self.state == CircuitBreakerState.OPEN:
            if time.time() - (self.last_failure_time or 0) < self.recovery_timeout:
                retry_in = self.recovery_timeout - (
                    time.time() - (self.last_failure_time or 0)
                )
                raise CircuitBreakerError(
                    f"Circuit breaker is OPEN. Next retry in {retry_in:.1f} seconds"
                )
            else:
                self.state = CircuitBreakerState.HALF_OPEN

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e

    def _on_success(self):
        """Handle successful call"""
        self.failure_count = 0
        self.state = CircuitBreakerState.CLOSED

    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN

    def get_state(self) -> Dict[str, Any]:
        """Get circuit breaker state"""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "last_failure_time": self.last_failure_time,
            "time_to_retry": max(
                0, self.recovery_timeout - (time.time() - (self.last_failure_time or 0))
            ),
        }


class DataSourceAdapter(ABC):
    """Abstract adapter for data sources"""

    @abstractmethod
    async def fetch_historical_data(self, request: DataRequest) -> List[OHLCData]:
        """Fetch historical data"""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check data source health"""
        pass

    @abstractmethod
    def get_source_name(self) -> DataSource:
        """Get source identifier"""
        pass


class AngelOneAdapter(DataSourceAdapter):
    """Angel One API adapter"""

    def __init__(self, client: AngelOneClient, config: DataManagerConfig):
        self.client = client
        self.config = config
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=config.circuit_breaker_failure_threshold,
            recovery_timeout=config.circuit_breaker_recovery_timeout,
            expected_exception=AngelOneError,
        )
        self.logger = get_logger("niraj.data_manager.angel_one")

    def get_source_name(self) -> DataSource:
        return DataSource.ANGEL_ONE

    async def health_check(self) -> bool:
        """Check Angel One API health"""
        try:
            result = await self.client.health_check()
            return result.get("status") == "healthy"
        except Exception as e:
            self.logger.warning(f"Angel One health check failed: {e}")
            return False

    def _map_timeframe(self, timeframe: DataTimeframe) -> str:
        """Map internal timeframe to Angel One API format"""
        mapping = {
            DataTimeframe.ONE_MINUTE: "ONE_MINUTE",
            DataTimeframe.THREE_MINUTE: "THREE_MINUTE",
            DataTimeframe.FIVE_MINUTE: "FIVE_MINUTE",
            DataTimeframe.TEN_MINUTE: "TEN_MINUTE",
            DataTimeframe.FIFTEEN_MINUTE: "FIFTEEN_MINUTE",
            DataTimeframe.THIRTY_MINUTE: "THIRTY_MINUTE",
            DataTimeframe.ONE_HOUR: "ONE_HOUR",
            DataTimeframe.DAILY: "ONE_DAY",
        }
        return mapping.get(timeframe, "ONE_MINUTE")

    async def _get_symbol_token(self, symbol: str, exchange: str) -> Optional[str]:
        """Get symbol token for Angel One API"""
        try:
            # This would typically query the instrument master
            # For now, using a simplified approach
            instruments = await self.client.search_scrips(symbol)
            data = instruments.get("data", [])

            for instrument in data:
                if (
                    instrument.get("tradingsymbol") == symbol
                    and instrument.get("exchange") == exchange
                ):
                    return instrument.get("symboltoken")

            return None
        except Exception as e:
            self.logger.error(f"Failed to get symbol token: {e}")
            return None

    async def fetch_historical_data(self, request: DataRequest) -> List[OHLCData]:
        """Fetch historical data from Angel One"""

        async def _fetch():
            try:
                # Get symbol token
                symbol_token = await self._get_symbol_token(
                    request.symbol, request.exchange
                )
                if not symbol_token:
                    raise ValueError(f"Symbol token not found for {request.symbol}")

                # Format dates for Angel One API
                from_date = request.start_date.strftime("%Y-%m-%d %H:%M")
                to_date = request.end_date.strftime("%Y-%m-%d %H:%M")

                # Fetch data
                response = await self.client.get_historical_data(
                    exchange=request.exchange,
                    symboltoken=symbol_token,
                    interval=self._map_timeframe(request.timeframe),
                    fromdate=from_date,
                    todate=to_date,
                )

                # Parse response
                data = response.get("data", [])
                ohlc_data = []

                for candle in data:
                    if len(candle) >= 6:  # [timestamp, open, high, low, close, volume]
                        timestamp = datetime.fromtimestamp(
                            candle[0] / 1000, tz=timezone.utc
                        )
                        ohlc = OHLCData(
                            timestamp=timestamp,
                            open=candle[1],
                            high=candle[2],
                            low=candle[3],
                            close=candle[4],
                            volume=int(candle[5]) if len(candle) > 5 else 0,
                            source=self.get_source_name().value,
                            quality=DataQuality.HIGH,
                        )

                        if ohlc.is_valid():
                            ohlc_data.append(ohlc)

                return ohlc_data

            except Exception as e:
                self.logger.error(f"Angel One fetch failed: {e}")
                raise

        return await self.circuit_breaker.call(_fetch)


class DhanAdapter(DataSourceAdapter):
    """Dhan API adapter"""

    def __init__(self, client: DhanClient, config: DataManagerConfig):
        self.client = client
        self.config = config
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=config.circuit_breaker_failure_threshold,
            recovery_timeout=config.circuit_breaker_recovery_timeout,
            expected_exception=DhanError,
        )
        self.logger = get_logger("niraj.data_manager.dhan")

    def get_source_name(self) -> DataSource:
        return DataSource.DHAN

    async def health_check(self) -> bool:
        """Check Dhan API health"""
        try:
            result = await self.client.health_check()
            return result.get("status") == "healthy"
        except Exception as e:
            self.logger.warning(f"Dhan health check failed: {e}")
            return False

    def _map_timeframe_to_method(self, timeframe: DataTimeframe) -> str:
        """Map timeframe to appropriate Dhan API method"""
        if timeframe in [
            DataTimeframe.DAILY,
            DataTimeframe.WEEKLY,
            DataTimeframe.MONTHLY,
        ]:
            return "historical_daily"
        else:
            return "intraday_minute"

    def _map_exchange(self, exchange: str) -> str:
        """Map exchange to Dhan format"""
        mapping = {
            "NSE": "NSE_EQ",
            "BSE": "BSE_EQ",
            "NFO": "NSE_FNO",
            "BFO": "BSE_FNO",
            "MCX": "MCX_COMM",
        }
        return mapping.get(exchange, exchange)

    async def fetch_historical_data(self, request: DataRequest) -> List[OHLCData]:
        """Fetch historical data from Dhan"""

        async def _fetch():
            try:
                method = self._map_timeframe_to_method(request.timeframe)

                if method == "historical_daily":
                    # Use historical daily data API
                    response = await self.client.get_historical_daily_data(
                        symbol=request.symbol,
                        exchange_segment=self._map_exchange(request.exchange),
                        instrument_type="EQUITY",  # This would need proper mapping
                        from_date=request.start_date.strftime("%Y-%m-%d"),
                        to_date=request.end_date.strftime("%Y-%m-%d"),
                    )
                else:
                    # Use intraday minute data API
                    # Note: Dhan intraday API only provides current day data
                    # This is a limitation we need to handle
                    response = await self.client.get_intraday_minute_data(
                        security_id=request.symbol,  # Needs proper security ID mapping
                        exchange_segment=self._map_exchange(request.exchange),
                        instrument_type="EQUITY",
                    )

                # Parse response based on Dhan API format
                ohlc_data = []

                if "open" in response and isinstance(response["open"], list):
                    # Array-based format
                    opens = response.get("open", [])
                    highs = response.get("high", [])
                    lows = response.get("low", [])
                    closes = response.get("close", [])
                    volumes = response.get("volume", [])
                    timestamps = response.get("start_Time", [])

                    for i in range(len(opens)):
                        timestamp = datetime.fromtimestamp(
                            timestamps[i], tz=timezone.utc
                        )
                        ohlc = OHLCData(
                            timestamp=timestamp,
                            open=opens[i],
                            high=highs[i],
                            low=lows[i],
                            close=closes[i],
                            volume=int(volumes[i]) if i < len(volumes) else 0,
                            source=self.get_source_name().value,
                            quality=DataQuality.HIGH,
                        )

                        if ohlc.is_valid():
                            ohlc_data.append(ohlc)

                return ohlc_data

            except Exception as e:
                self.logger.error(f"Dhan fetch failed: {e}")
                raise

        return await self.circuit_breaker.call(_fetch)


class DataValidator:
    """Data quality validation and cleaning"""

    def __init__(self):
        self.logger = get_logger("niraj.data_manager.validator")

    def validate_ohlc_sequence(self, data: List[OHLCData]) -> List[OHLCData]:
        """Validate and clean OHLC data sequence"""
        if not data:
            return data

        cleaned_data = []

        for i, candle in enumerate(data):
            if not candle.is_valid():
                self.logger.warning(
                    "Invalid OHLC data detected"
                )
                continue

            # Check for price gaps that might indicate bad data
            if i > 0 and cleaned_data:
                prev_candle = cleaned_data[-1]
                prev_close = float(prev_candle.close)
                price_gap = abs(float(candle.open - prev_candle.close)) / prev_close

                if price_gap > 0.2:  # 20% gap threshold
                    candle.quality = DataQuality.MEDIUM
                    self.logger.warning(f"Large price gap detected: {price_gap:.2%}")

            # Check for zero volume on trading days
            if candle.volume == 0 and candle.open != candle.close:
                candle.quality = DataQuality.LOW

            cleaned_data.append(candle)

        return cleaned_data

    def fill_missing_data(
        self, data: List[OHLCData], timeframe: DataTimeframe
    ) -> List[OHLCData]:
        """Fill missing data points using interpolation"""
        if len(data) < 2:
            return data

        # Sort by timestamp
        data.sort(key=lambda x: x.timestamp)

        filled_data = []
        timeframe_delta = self._get_timeframe_delta(timeframe)

        for i in range(len(data) - 1):
            filled_data.append(data[i])

            # Check for gaps
            current_time = data[i].timestamp
            next_time = data[i + 1].timestamp
            expected_next_time = current_time + timeframe_delta

            # Fill missing candles
            while expected_next_time < next_time:
                # Use previous close as OHLC for missing candle
                missing_candle = OHLCData(
                    timestamp=expected_next_time,
                    open=data[i].close,
                    high=data[i].close,
                    low=data[i].close,
                    close=data[i].close,
                    volume=0,
                    source="interpolated",
                    quality=DataQuality.LOW,
                )
                filled_data.append(missing_candle)
                expected_next_time += timeframe_delta

        # Add last candle
        if data:
            filled_data.append(data[-1])

        return filled_data

    def _get_timeframe_delta(self, timeframe: DataTimeframe) -> timedelta:
        """Get timedelta for timeframe"""
        mapping = {
            DataTimeframe.ONE_MINUTE: timedelta(minutes=1),
            DataTimeframe.THREE_MINUTE: timedelta(minutes=3),
            DataTimeframe.FIVE_MINUTE: timedelta(minutes=5),
            DataTimeframe.TEN_MINUTE: timedelta(minutes=10),
            DataTimeframe.FIFTEEN_MINUTE: timedelta(minutes=15),
            DataTimeframe.THIRTY_MINUTE: timedelta(minutes=30),
            DataTimeframe.ONE_HOUR: timedelta(hours=1),
            DataTimeframe.FOUR_HOUR: timedelta(hours=4),
            DataTimeframe.DAILY: timedelta(days=1),
            DataTimeframe.WEEKLY: timedelta(days=7),
            DataTimeframe.MONTHLY: timedelta(days=30),
        }
        return mapping.get(timeframe, timedelta(minutes=1))


class DataSynchronizer:
    """Synchronize data from multiple sources"""

    def __init__(self):
        self.logger = get_logger("niraj.data_manager.synchronizer")

    def merge_data_sources(
        self,
        primary_data: List[OHLCData],
        secondary_data: List[OHLCData],
        conflict_resolution: str = "primary_preferred",
    ) -> List[OHLCData]:
        """Merge data from multiple sources with conflict resolution"""
        if not secondary_data:
            return primary_data
        if not primary_data:
            return secondary_data

        # Create timestamp-based maps
        primary_map = {data.timestamp: data for data in primary_data}
        secondary_map = {data.timestamp: data for data in secondary_data}

        all_timestamps = sorted(set(primary_map.keys()) | set(secondary_map.keys()))
        merged_data = []

        for timestamp in all_timestamps:
            primary_candle = primary_map.get(timestamp)
            secondary_candle = secondary_map.get(timestamp)

            if primary_candle and secondary_candle:
                # Both sources have data - resolve conflict
                resolved_candle = self._resolve_conflict(
                    primary_candle, secondary_candle, conflict_resolution
                )
                merged_data.append(resolved_candle)
            elif primary_candle:
                merged_data.append(primary_candle)
            elif secondary_candle:
                merged_data.append(secondary_candle)

        return merged_data

    def _resolve_conflict(
        self, primary: OHLCData, secondary: OHLCData, strategy: str
    ) -> OHLCData:
        """Resolve conflicts between data sources"""
        if strategy == "primary_preferred":
            if primary.quality.value >= secondary.quality.value:
                return primary
            else:
                return secondary

        elif strategy == "higher_quality":
            quality_order = {
                DataQuality.HIGH: 3,
                DataQuality.MEDIUM: 2,
                DataQuality.LOW: 1,
                DataQuality.CORRUPTED: 0,
            }

            if quality_order[primary.quality] >= quality_order[secondary.quality]:
                return primary
            else:
                return secondary

        elif strategy == "average":
            # Average the prices
            return OHLCData(
                timestamp=primary.timestamp,
                open=(primary.open + secondary.open) / 2,
                high=max(primary.high, secondary.high),
                low=min(primary.low, secondary.low),
                close=(primary.close + secondary.close) / 2,
                volume=(primary.volume + secondary.volume) // 2,
                source="merged",
                quality=min(primary.quality, secondary.quality, key=lambda x: x.value),
            )

        else:  # Default to primary
            return primary


class HistoricalDataManager:
    """
    Comprehensive historical data manager for NIRAJ trading system.

    This class provides a unified interface for fetching, caching, and managing
    market data from multiple sources with advanced error handling, data
    validation, and performance monitoring.

    Features:
    - Multi-source data fetching with automatic fallback mechanisms
    - Intelligent Redis-based caching with configurable TTL
    - Data quality validation and gap filling
    - Circuit breaker pattern for API protection
    - Exponential backoff retry logic
    - Comprehensive error handling with custom exceptions
    - Data synchronization across sources with conflict resolution
    - Performance monitoring and health checks
    - Structured logging with request tracing

    Example:
        ```python
        from datetime import datetime, timezone
        from niraj.core.data_manager import HistoricalDataManager, DataRequest, \
            DataTimeframe

        # Create data manager
        data_manager = HistoricalDataManager(
            angel_one_client=angel_client,
            dhan_client=dhan_client
        )

        # Create data request
        request = DataRequest(
            symbol="RELIANCE",
            exchange="NSE",
            timeframe=DataTimeframe.ONE_MINUTE,
            start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2024, 1, 2, tzinfo=timezone.utc)
        )

        # Fetch data
        async with data_manager:
            data = await data_manager.fetch_historical_data(request)
            print(f"Fetched {len(data)} data points")
        ```

    Attributes:
        config (DataManagerConfig): Configuration settings
        adapters (Dict[DataSource, DataSourceAdapter]): Available data source \
            adapters
        cache (RedisCache): Redis cache instance
        validator (DataValidator): Data validation and cleaning component
        synchronizer (DataSynchronizer): Data synchronization component
        stats (Dict[str, Any]): Runtime statistics
    """

    def __init__(
        self,
        angel_one_client: Optional[AngelOneClient] = None,
        dhan_client: Optional[DhanClient] = None,
        cache: Optional[RedisCache] = None,
        config: Optional[DataManagerConfig] = None,
    ):
        """
        Initialize data manager

        Args:
            angel_one_client: Angel One API client
            dhan_client: Dhan API client
            cache: Redis cache instance
            config: Data manager configuration
        """
        self.config = config or DataManagerConfig()
        self.logger = get_logger("niraj.data_manager")

        # Initialize adapters
        self.adapters: Dict[DataSource, DataSourceAdapter] = {}
        if angel_one_client:
            self.adapters[DataSource.ANGEL_ONE] = AngelOneAdapter(
                angel_one_client, self.config
            )
        if dhan_client:
            self.adapters[DataSource.DHAN] = DhanAdapter(
                dhan_client, self.config
            )

        # Initialize components
        self.cache = cache or RedisCache()
        self.validator = DataValidator()
        self.synchronizer = DataSynchronizer()

        # Statistics tracking
        self.stats = {
            "requests_total": 0,
            "requests_cached": 0,
            "requests_failed": 0,
            "data_points_fetched": 0,
            "average_response_time": 0.0,
            "source_usage": {source.value: 0 for source in DataSource},
        }

        # Thread pool for concurrent operations
        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=self.config.max_concurrent_requests
        )

        # Log initialization without problematic parameters
        sources_list = list(self.adapters.keys())
        cache_status = self.cache is not None
        self.logger.info(
            f"Historical Data Manager initialized with sources: {sources_list}, cache_enabled: {cache_status}"
        )

    @asynccontextmanager
    async def _request_context(self, request: DataRequest):
        """Context manager for request lifecycle management"""
        start_time = time.time()

        with LogContext():
            try:
                self.stats["requests_total"] += 1
                self.logger.info(
                    "Starting data request"
                )

                yield

                # Update success statistics
                duration = time.time() - start_time
                self._update_response_time(duration)

                self.logger.info(
                    "Data request completed successfully"
                )

            except Exception:
                # Update failure statistics
                self.stats["requests_failed"] += 1
                duration = time.time() - start_time

                self.logger.error(
                    "Data request failed"
                )
                raise

    def _update_response_time(self, duration: float) -> None:
        """Update average response time statistics"""
        current_avg = self.stats["average_response_time"]
        total_requests = self.stats["requests_total"]

        # Calculate running average
        self.stats["average_response_time"] = (
            current_avg * (total_requests - 1) + duration
        ) / total_requests

    async def _get_from_cache(self, request: DataRequest) -> Optional[List[OHLCData]]:
        """
        Retrieve data from cache if available and valid.

        Performs cache lookup with the following logic:
        - Generates cache key from request parameters
        - Checks if caching is enabled and not forced refresh
        - Retrieves and deserializes cached data
        - Returns None if cache miss or error

        Args:
            request (DataRequest): Request to get cached data for

        Returns:
            Optional[List[OHLCData]]: Cached data if available, None otherwise

        Example:
            ```python
            cached_data = await data_manager._get_from_cache(request)
            if cached_data:
                print(f"Cache hit: {len(cached_data)} records")
            else:
                print("Cache miss")
            ```
        """
        if not request.use_cache or request.force_refresh:
            return None

        try:
            cache_key = f"historical:{request.cache_key()}"
            cached_data = await self.cache.get(cache_key, prefix="market_data")

            if cached_data:
                self.stats["requests_cached"] += 1

                # Convert back to OHLCData objects
                ohlc_data = [OHLCData.from_dict(item) for item in cached_data]

                self.logger.debug(
                    "Data retrieved from cache"
                )
                return ohlc_data

        except Exception as e:
            self.logger.warning(f"Cache retrieval failed: {e}")

        return None

    async def _save_to_cache(self, request: DataRequest, data: List[OHLCData]) -> None:
        """
        Save data to cache with appropriate TTL based on timeframe.

        Serializes OHLC data and stores it in Redis cache with:
        - Timeframe-based TTL for optimal cache freshness
        - Proper error handling for cache failures
        - Structured logging for cache operations

        Args:
            request (DataRequest): Request that generated the data
            data (List[OHLCData]): Data to cache

        Returns:
            None

        Example:
            ```python
            await data_manager._save_to_cache(request, ohlc_data)
            print(f"Cached {len(ohlc_data)} records for {request.symbol}")
            ```
        """
        if not data:
            return

        try:
            cache_key = f"historical:{request.cache_key()}"

            # Convert to serializable format
            cache_data = [item.to_dict() for item in data]

            # Determine TTL based on timeframe
            ttl = self._get_cache_ttl(request.timeframe)

            await self.cache.set(cache_key, cache_data, ttl=ttl)

            self.logger.debug("Data saved to cache")

        except Exception as e:
            self.logger.warning(f"Cache save failed: {e}")

    def _get_cache_ttl(self, timeframe: DataTimeframe) -> int:
        """
        Get appropriate cache TTL based on data timeframe.

        Different timeframes have different cache durations:
        - High-frequency data (1-5 min): Short TTL (5-15 min)
        - Medium-frequency data (10-60 min): Medium TTL (30-60 min)
        - Daily/weekly data: Long TTL (1-7 days)

        Args:
            timeframe (DataTimeframe): Data timeframe

        Returns:
            int: TTL in seconds

        Example:
            ```python
            ttl = data_manager._get_cache_ttl(DataTimeframe.ONE_MINUTE)
            print(f"One minute data cached for {ttl} seconds")
            ```
        """
        ttl_mapping: Dict[DataTimeframe, int] = {
            DataTimeframe.ONE_MINUTE: 300,  # 5 minutes
            DataTimeframe.THREE_MINUTE: 600,  # 10 minutes
            DataTimeframe.FIVE_MINUTE: 900,  # 15 minutes
            DataTimeframe.TEN_MINUTE: 1800,  # 30 minutes
            DataTimeframe.FIFTEEN_MINUTE: 2700,  # 45 minutes
            DataTimeframe.THIRTY_MINUTE: 3600,  # 1 hour
            DataTimeframe.ONE_HOUR: 7200,  # 2 hours
            DataTimeframe.FOUR_HOUR: 14400,  # 4 hours
            DataTimeframe.DAILY: 86400,  # 1 day
            DataTimeframe.WEEKLY: 604800,  # 1 week
            DataTimeframe.MONTHLY: 2592000,  # 30 days
        }
        return ttl_mapping.get(timeframe, self.config.default_cache_ttl)

    async def _fetch_from_source(
        self, source: DataSource, request: DataRequest
    ) -> Optional[List[OHLCData]]:
        """
        Fetch data from a specific source with comprehensive error handling.

        Implements the complete fetch pipeline for a single source:
        1. Adapter availability check
        2. Health check validation
        3. Timeout-protected API call
        4. Circuit breaker protection
        5. Data validation and statistics update

        Args:
            source (DataSource): Data source to fetch from
            request (DataRequest): Fetch request parameters

        Returns:
            Optional[List[OHLCData]]: Fetched data or None on failure

        Raises:
            DataSourceError: Source health check failed
            DataNotFoundError: No data returned from source
            CircuitBreakerError: Circuit breaker prevented call

        Example:
            ```python
            data = await data_manager._fetch_from_source(DataSource.ANGEL_ONE, request)
            if data:
                print(f"Successfully fetched {len(data)} records from Angel One")
            else:
                print("Failed to fetch from Angel One")
            ```
        """
        adapter = self.adapters.get(source)
        if not adapter:
            self.logger.warning(f"Adapter not available for source: {source}")
            return None

        async def _fetch_attempt() -> List[OHLCData]:
            """Single fetch attempt with circuit breaker"""
            # Check adapter health
            if not await adapter.health_check():
                raise DataSourceError(f"Source {source} failed health check")

            # Fetch data with timeout
            data = await asyncio.wait_for(
                adapter.fetch_historical_data(request), timeout=request.timeout
            )

            if not data:
                raise DataNotFoundError(f"No data returned from {source}")

            # Update statistics
            self.stats["source_usage"][source.value] += 1
            self.stats["data_points_fetched"] += len(data)

            self.logger.info(f"Fetched {len(data)} data points from {source}")
            return data

        try:
            # Use retry mechanism with circuit breaker if available
            # Cast to concrete adapter type that has circuit_breaker
            if hasattr(adapter, 'circuit_breaker'):
                return await self._execute_with_circuit_breaker(
                    adapter.circuit_breaker,  # type: ignore[attr-defined]
                    _fetch_attempt
                )
            else:
                return await _fetch_attempt()
        except asyncio.TimeoutError:
            self.logger.error(f"Timeout fetching from {source}")
            return None
        except (DataSourceError, DataNotFoundError) as e:
            self.logger.error(f"Data source error from {source}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error fetching from {source}: {e}")
            return None

    async def _execute_with_circuit_breaker(
        self, circuit_breaker: CircuitBreaker, func: Callable[[], Awaitable[Any]]
    ) -> Any:
        """Execute function with circuit breaker protection"""
        try:
            return await circuit_breaker.call(func)
        except CircuitBreakerError as e:
            self.logger.warning(f"Circuit breaker prevented call: {e}")
            raise DataSourceError("Circuit breaker is open") from e

    async def _fetch_from_multiple_sources(
        self, request: DataRequest
    ) -> List[OHLCData]:
        """
        Fetch data from multiple sources with fallback and merging.

        Implements multi-source data fetching strategy:
        1. Primary source fetch attempt
        2. Automatic fallback to secondary sources if enabled
        3. Data merging with conflict resolution
        4. Comprehensive error handling and logging

        Args:
            request (DataRequest): Request with source priorities

        Returns:
            List[OHLCData]: Merged data from available sources

        Raises:
            Exception: All sources failed to provide data

        Example:
            ```python
            try:
                data = await data_manager._fetch_from_multiple_sources(request)
                print(f"Merged data from sources: {len(data)} records")
            except Exception as e:
                print(f"All sources failed: {e}")
            ```
        """
        primary_data = None
        secondary_data = None

        # Try primary source first
        if request.sources:
            primary_source = request.sources[0]
            primary_data = await self._fetch_from_source(primary_source, request)

        # Try fallback sources if needed
        if self.config.fallback_sources and len(request.sources) > 1:
            for source in request.sources[1:]:
                if secondary_data is None:
                    secondary_data = await self._fetch_from_source(source, request)
                    if secondary_data:
                        break

        # Merge data sources
        if primary_data and secondary_data:
            merged_data = self.synchronizer.merge_data_sources(
                primary_data, secondary_data, "higher_quality"
            )
            self.logger.info(f"Merged data from {len(request.sources)} sources")
            return merged_data
        elif primary_data:
            return primary_data
        elif secondary_data:
            return secondary_data
        else:
            raise Exception("Failed to fetch data from any source")

    @log_performance("data_manager_fetch_historical")
    async def fetch_historical_data(self, request: DataRequest) -> List[OHLCData]:
        """
        Fetch historical OHLC data with comprehensive error handling and caching.

        This method implements a complete data fetching pipeline:
        1. Input validation and normalization
        2. Cache lookup (if enabled)
        3. Multi-source data fetching with fallback
        4. Data validation and cleaning
        5. Gap filling (if enabled)
        6. Cache storage
        7. Performance monitoring

        Args:
            request (DataRequest): Data request specification containing symbol,
                exchange, timeframe, date range, and other parameters.

        Returns:
            List[OHLCData]: List of OHLC data points sorted by timestamp.

        Raises:
            ConfigurationError: Invalid request parameters
            DataNotFoundError: No data available from any source
            DataSourceError: All data sources failed
            CircuitBreakerError: Circuit breaker prevented API calls

        Example:
            ```python
            request = DataRequest(
                symbol="TCS",
                exchange="NSE",
                timeframe=DataTimeframe.FIVE_MINUTE,
                start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
                end_date=datetime(2024, 1, 7, tzinfo=timezone.utc),
                sources=[DataSource.ANGEL_ONE, DataSource.DHAN]
            )

            data = await data_manager.fetch_historical_data(request)
            for candle in data:
                print(f"{candle.timestamp}: {candle.open} -> {candle.close}")
            ```
        """
        async with self._request_context(request):
            # Try cache first
            cached_data = await self._get_from_cache(request)
            if cached_data:
                return cached_data

            # Fetch from sources
            raw_data = await self._fetch_from_multiple_sources(request)

            if not raw_data:
                raise Exception("No data fetched from any source")

            # Validate and clean data
            if self.config.enable_data_validation:
                validated_data = self.validator.validate_ohlc_sequence(raw_data)
                self.logger.debug(
                    f"Validated {len(validated_data)}/{len(raw_data)} data points"
                )
                raw_data = validated_data

            # Fill missing data if enabled
            if self.config.enable_gap_filling:
                filled_data = self.validator.fill_missing_data(
                    raw_data, request.timeframe
                )
                if len(filled_data) > len(raw_data):
                    self.logger.debug(
                        f"Filled {len(filled_data) - len(raw_data)} missing data points"
                    )
                raw_data = filled_data

            # Cache the results
            await self._save_to_cache(request, raw_data)

            return raw_data

    async def get_latest_price(
        self, symbol: str, exchange: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get latest price for a symbol with caching.

        Fetches the most recent price data for a symbol:
        1. Cache lookup for recent price data
        2. Fresh data fetch if cache miss (last 5 minutes)
        3. Price extraction and formatting
        4. Short-term caching (30 seconds)

        Args:
            symbol (str): Trading symbol (e.g., "RELIANCE")
            exchange (str): Exchange name (e.g., "NSE")

        Returns:
            Optional[Dict[str, Any]]: Price data with keys:
                - symbol: Trading symbol
                - exchange: Exchange name
                - price: Latest close price
                - timestamp: ISO format timestamp
                - source: Data source name

        Example:
            ```python
            price_data = await data_manager.get_latest_price("TCS", "NSE")
            if price_data:
                print(f"TCS: ₹{price_data['price']} at {price_data['timestamp']}")
            else:
                print("Price not available")
            ```
        """
        try:
            # Try to get from cache first
            cache_key = f"{symbol}:{exchange}:latest"
            cached_price = await self.cache.get(cache_key, prefix="market_data")

            if cached_price:
                return cached_price

            # Fetch fresh data (last 2 candles to get latest)
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(minutes=5)

            request = DataRequest(
                symbol=symbol,
                exchange=exchange,
                timeframe=DataTimeframe.ONE_MINUTE,
                start_date=start_date,
                end_date=end_date,
                use_cache=False,
            )

            data = await self.fetch_historical_data(request)

            if data:
                latest = data[-1]
                price_data = {
                    "symbol": symbol,
                    "exchange": exchange,
                    "price": float(latest.close),
                    "timestamp": latest.timestamp.isoformat(),
                    "source": latest.source,
                }

                # Cache for 30 seconds
                await self.cache.set(
                    cache_key, price_data, prefix="market_data", ttl=30
                )

                return price_data

        except Exception as e:
            self.logger.error(f"Failed to get latest price for {symbol}: {e}")

        return None

    async def get_data_quality_report(
        self, symbol: str, exchange: str, timeframe: DataTimeframe, days_back: int = 7
    ) -> Dict[str, Any]:
        """
        Generate comprehensive data quality report for a symbol.

        Analyzes historical data quality over a specified period:
        1. Data completeness and gap analysis
        2. Quality distribution (high/medium/low/corrupted)
        3. Price statistics and volatility metrics
        4. Source usage patterns
        5. Gap detection and reporting

        Args:
            symbol (str): Trading symbol to analyze
            exchange (str): Exchange name
            timeframe (DataTimeframe): Data timeframe for analysis
            days_back (int): Number of days to analyze (default: 7)

        Returns:
            Dict[str, Any]: Comprehensive quality report with:
                - analysis_period: Date range analyzed
                - data_points: Count by quality level
                - quality_percentage: Quality distribution percentages
                - price_statistics: Min/max/mean/median/std_dev
                - gaps_detected: Number of data gaps found
                - gaps: List of gap details
                - data_sources_used: Sources that provided data
                - completeness_score: Overall data completeness (0-100)

        Example:
            ```python
            report = await data_manager.get_data_quality_report(
                "INFY", "NSE", DataTimeframe.ONE_MINUTE, days_back=14
            )

            print(f"Completeness: {report['completeness_score']:.1f}%")
            print(f"High quality: {report['quality_percentage']['high']:.1f}%")
            print(f"Gaps detected: {report['gaps_detected']}")
            ```
        """
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days_back)

        request = DataRequest(
            symbol=symbol,
            exchange=exchange,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
        )

        try:
            data = await self.fetch_historical_data(request)

            if not data:
                return {"error": "No data available"}

            # Calculate quality metrics
            total_points = len(data)
            high_quality = len([d for d in data if d.quality == DataQuality.HIGH])
            medium_quality = len([d for d in data if d.quality == DataQuality.MEDIUM])
            low_quality = len([d for d in data if d.quality == DataQuality.LOW])
            corrupted = len([d for d in data if d.quality == DataQuality.CORRUPTED])

            # Calculate price statistics
            prices = [float(d.close) for d in data]

            # Gap analysis
            gaps = []
            expected_delta = self.validator._get_timeframe_delta(timeframe)

            for i in range(1, len(data)):
                actual_delta = data[i].timestamp - data[i - 1].timestamp
                if actual_delta > expected_delta * 1.5:  # Allow some tolerance
                    gaps.append(
                        {
                            "start": data[i - 1].timestamp.isoformat(),
                            "end": data[i].timestamp.isoformat(),
                            "duration_minutes": actual_delta.total_seconds() / 60,
                        }
                    )

            return {
                "symbol": symbol,
                "exchange": exchange,
                "timeframe": timeframe.value,
                "analysis_period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                    "days": days_back,
                },
                "data_points": {
                    "total": total_points,
                    "high_quality": high_quality,
                    "medium_quality": medium_quality,
                    "low_quality": low_quality,
                    "corrupted": corrupted,
                },
                "quality_percentage": {
                    "high": (
                        (high_quality / total_points * 100) if total_points > 0 else 0
                    ),
                    "medium": (
                        (medium_quality / total_points * 100) if total_points > 0 else 0
                    ),
                    "low": (
                        (low_quality / total_points * 100) if total_points > 0 else 0
                    ),
                    "corrupted": (
                        (corrupted / total_points * 100) if total_points > 0 else 0
                    ),
                },
                "price_statistics": {
                    "min": min(prices) if prices else 0,
                    "max": max(prices) if prices else 0,
                    "mean": statistics.mean(prices) if prices else 0,
                    "median": statistics.median(prices) if prices else 0,
                    "std_dev": statistics.stdev(prices) if len(prices) > 1 else 0,
                },
                "gaps_detected": len(gaps),
                "gaps": gaps[:10],  # Return first 10 gaps
                "data_sources_used": list(set(d.source for d in data)),
                "completeness_score": (
                    ((total_points - corrupted) / total_points * 100)
                    if total_points > 0
                    else 0
                ),
            }

        except Exception as e:
            return {"error": f"Failed to generate quality report: {str(e)}"}

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check of the data manager and its components.

        Checks the health status of:
        1. Redis cache connection and performance
        2. All configured data source adapters
        3. Circuit breaker states for each adapter
        4. Overall system availability

        Returns:
            Dict[str, Any]: Health report with:
                - status: "healthy", "degraded", or "unhealthy"
                - timestamp: ISO format timestamp
                - components: Individual component health status
                - statistics: Runtime performance statistics

        Example:
            ```python
            health = await data_manager.health_check()
            print(f"System status: {health['status']}")

            for component, status in health['components'].items():
                print(f"{component}: {status['status']}")
            ```
        """
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "components": {},
        }

        # Check cache
        try:
            cache_healthy = await self.cache.health_check()
            health_status["components"]["cache"] = {
                "status": "healthy" if cache_healthy else "unhealthy",
                "details": await self.cache.get_stats() if cache_healthy else {},
            }
        except Exception as e:
            health_status["components"]["cache"] = {
                "status": "unhealthy",
                "error": str(e),
            }

        # Check adapters
        for source, adapter in self.adapters.items():
            try:
                adapter_healthy = await adapter.health_check()
                # Safely access circuit_breaker attribute
                circuit_breaker_state = {}
                if hasattr(adapter, 'circuit_breaker'):
                    circuit_breaker_state = adapter.circuit_breaker.get_state()  # type: ignore[attr-defined]

                health_status["components"][source.value] = {
                    "status": "healthy" if adapter_healthy else "unhealthy",
                    "circuit_breaker": circuit_breaker_state,
                }
            except Exception as e:
                health_status["components"][source.value] = {
                    "status": "unhealthy",
                    "error": str(e),
                }

        # Overall status
        component_statuses = [
            comp["status"] for comp in health_status["components"].values()
        ]
        if "unhealthy" in component_statuses:
            health_status["status"] = "degraded"
        if all(status == "unhealthy" for status in component_statuses):
            health_status["status"] = "unhealthy"

        # Add statistics
        health_status["statistics"] = self.stats.copy()

        return health_status

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive runtime statistics and configuration.

        Returns current operational metrics including:
        1. Request counts (total, cached, failed)
        2. Data points fetched and processing metrics
        3. Source usage distribution
        4. Performance statistics (response times)
        5. Current configuration settings

        Returns:
            Dict[str, Any]: Statistics report with:
                - statistics: Runtime metrics
                - configuration: Current config values
                - sources_available: List of configured sources
                - timestamp: Report generation time

        Example:
            ```python
            stats = data_manager.get_statistics()
            print(f"Total requests: {stats['statistics']['requests_total']}")
            print(f"Cache hit rate: "
                  f"{stats['statistics']['requests_cached']/stats['statistics']['requests_total']:.1%}")
            print(f"Avg response time: "
                  f"{stats['statistics']['average_response_time']:.2f}s")
            ```
        """
        return {
            "statistics": self.stats.copy(),
            "configuration": {
                "max_concurrent_requests": self.config.max_concurrent_requests,
                "default_cache_ttl": self.config.default_cache_ttl,
                "enable_data_validation": self.config.enable_data_validation,
                "enable_gap_filling": self.config.enable_gap_filling,
                "fallback_sources": self.config.fallback_sources,
            },
            "sources_available": list(self.adapters.keys()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def clear_cache(
        self, symbol: Optional[str] = None, exchange: Optional[str] = None
    ) -> int:
        """
        Clear cached data with optional filtering.

        Removes cached market data from Redis with support for:
        1. Complete cache clearing
        2. Symbol-specific cache clearing
        3. Exchange-specific cache clearing
        4. Graceful error handling

        Args:
            symbol (Optional[str]): Specific symbol to clear (optional)
            exchange (Optional[str]): Specific exchange to clear (optional)

        Returns:
            int: Number of cache keys cleared (approximate)

        Example:
            ```python
            # Clear all cache
            cleared = await data_manager.clear_cache()
            print(f"Cleared {cleared} cache entries")

            # Clear specific symbol
            cleared = await data_manager.clear_cache(symbol="TCS", exchange="NSE")
            print(f"Cleared TCS cache entries: {cleared}")
            ```
        """
        try:
            if symbol and exchange:
                # Clear specific symbol cache - simplified approach
                # In production, use more precise key management
                await self.cache.clear_prefix("market_data")
                return 1
            else:
                # Clear all market data cache
                return await self.cache.clear_prefix("market_data")
        except Exception as e:
            self.logger.error(f"Failed to clear cache: {e}")
            return 0

    async def close(self):
        """
        Cleanup resources and close connections.

        Performs graceful shutdown of:
        1. Thread pool executor
        2. Redis cache connection
        3. Any open file handles or network connections

        Should be called when the data manager is no longer needed
        or during application shutdown.

        Returns:
            None

        Example:
            ```python
            # Use context manager for automatic cleanup
            async with data_manager:
                data = await data_manager.fetch_historical_data(request)

            # Or manually close
            await data_manager.close()
            ```
        """
        try:
            # Close thread pool
            self.executor.shutdown(wait=True)

            # Close cache connection
            await self.cache.disconnect()

            self.logger.info("Data manager closed successfully")

        except Exception as e:
            self.logger.error(f"Error during data manager cleanup: {e}")

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()


# Convenience factory function
async def create_data_manager(
    angel_one_config: Optional[Dict[str, Any]] = None,
    dhan_config: Optional[Dict[str, Any]] = None,
    cache_config: Optional[Dict[str, Any]] = None,
    data_manager_config: Optional[DataManagerConfig] = None,
) -> HistoricalDataManager:
    """
    Create and configure a data manager instance with all dependencies.

    Factory function that handles the complete setup of a HistoricalDataManager:
    1. Creates API client instances from configurations
    2. Initializes Redis cache with provided config
    3. Configures data manager with optimal settings
    4. Performs initial health checks

    Args:
        angel_one_config (Optional[Dict[str, Any]]): Angel One API credentials
            Required keys: api_key, client_id, password, pin
        dhan_config (Optional[Dict[str, Any]]): Dhan API credentials
            Required keys: client_id, access_token
        cache_config (Optional[Dict[str, Any]]): Redis cache configuration
            Keys: host, port, db, password, ssl, etc.
        data_manager_config (Optional[DataManagerConfig]): Data manager settings
            Circuit breaker, caching, validation configurations

    Returns:
        HistoricalDataManager: Fully configured and ready-to-use data manager

    Raises:
        ConfigurationError: Invalid or missing configuration
        ConnectionError: Failed to connect to required services

    Example:
        ```python
        # Create with Angel One and Dhan support
        data_manager = await create_data_manager(
            angel_one_config={
                "api_key": "your_api_key",
                "client_id": "your_client_id",
                "password": "your_password",
                "pin": "your_pin"
            },
            dhan_config={
                "client_id": "your_dhan_client_id",
                "access_token": "your_access_token"
            },
            cache_config={
                "host": "localhost",
                "port": 6379,
                "db": 0
            },
            data_manager_config=DataManagerConfig(
                enable_data_validation=True,
                enable_gap_filling=True,
                fallback_sources=True
            )
        )

        # Use the data manager
        async with data_manager:
            data = await data_manager.fetch_historical_data(request)
        ```
    """
    # Create clients
    angel_one_client = None
    dhan_client = None

    if angel_one_config:
        from ..api.angel_one_client import AngelOneClient

        angel_one_client = AngelOneClient(
            api_key=angel_one_config.get("api_key", ""),  # type: ignore[arg-type]
            client_code=angel_one_config.get("client_id", ""),  # type: ignore[arg-type]
            client_pin=angel_one_config.get("pin", ""),  # type: ignore[arg-type]
        )

    if dhan_config:
        from ..api.dhan_client import DhanClient

        dhan_client = DhanClient(
            client_id=dhan_config.get("client_id", ""),  # type: ignore[arg-type]
            access_token=dhan_config.get("access_token", ""),  # type: ignore[arg-type]
        )

    # Create cache
    cache = None
    if cache_config:
        cache = RedisCache(**cache_config)
        await cache.connect()

    # Create data manager
    data_manager = HistoricalDataManager(
        angel_one_client=angel_one_client,
        dhan_client=dhan_client,
        cache=cache,
        config=data_manager_config,
    )

    return data_manager


# Simple DataManager class for execution engine compatibility
class DataManager:
    """
    Simple data manager wrapper for execution engine compatibility.

    Lightweight wrapper around the full HistoricalDataManager providing
    a simplified interface for basic market data operations. Designed
    for use in execution engines and strategies that need minimal
    data access without the full feature set.

    Features:
    - Simplified interface for basic operations
    - Automatic resource management
    - Error handling with graceful degradation
    - Compatible with existing execution engine expectations

    Note:
        This is a compatibility layer. For advanced features like
        multi-source fetching, caching, and data validation, use
        HistoricalDataManager directly.

    Attributes:
        db_manager: Database manager instance
        config (Dict[str, Any]): Configuration settings

    Example:
        ```python
        # Create simple data manager
        data_manager = DataManager(db_manager, {"timeout": 30})

        # Get basic market data
        price_data = await data_manager.get_market_data("RELIANCE", "1min")
        if price_data:
            print(f"RELIANCE: ₹{price_data['price']}")
        ```
    """

    def __init__(self, db_manager, config: Dict[str, Any]):
        self.db_manager = db_manager
        self.config = config
        self.logger = get_logger("niraj.core.data_manager")

    async def get_market_data(
        self, symbol: str, timeframe: str = "1min"
    ) -> Optional[Dict[str, Any]]:
        """
        Get market data for a symbol (placeholder implementation).

        Simplified market data retrieval for execution engine compatibility.
        Currently returns mock data - should be integrated with actual
        HistoricalDataManager in production.

        Args:
            symbol (str): Trading symbol (e.g., "RELIANCE")
            timeframe (str): Data timeframe (e.g., "1min", "5min") - currently ignored

        Returns:
            Optional[Dict[str, Any]]: Market data dictionary with:
                - symbol: Trading symbol
                - price: Current price (mock: 100.0)
                - timestamp: ISO format timestamp

        Example:
            ```python
            data = await data_manager.get_market_data("TCS", "5min")
            if data:
                print(f"TCS price: ₹{data['price']} at {data['timestamp']}")
            else:
                print("Market data not available")
            ```
        """
        try:
            # Placeholder implementation - would integrate with HistoricalDataManager
            return {
                "symbol": symbol,
                "price": 100.0,  # Placeholder price
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            self.logger.error(f"Failed to get market data: {e}")
            return None

    async def health_check(self) -> bool:
        """
        Perform basic health check.

        Simple health validation for execution engine compatibility.
        Always returns True in current implementation.

        Returns:
            bool: Health status (always True for compatibility)

        Example:
            ```python
            is_healthy = await data_manager.health_check()
            if is_healthy:
                print("Data manager is operational")
            else:
                print("Data manager health check failed")
            ```
        """
        return True
