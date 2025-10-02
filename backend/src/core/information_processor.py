"""
NIRAJ Real-time Information Processor
Advanced real-time data processing system for market data, news, weather, and sentiment analysis
with sub-second latency requirements and comprehensive error handling.

This processor handles:
- Real-time market data from multiple broker APIs - News sentiment processing and relevance scoring - Weather data correlation for sector analysis - Social media sentiment analysis - Multi-stream data synchronization and aggregation - WebSocket stream management - Advanced error handling and circuit breakers -
Performance monitoring and alerting
"""

import asyncio
import json
import time
# Removed statistics import (unused)
import hashlib
import random
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Set, Awaitable, cast
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from collections import defaultdict, deque
import threading
import websockets
import re

from .data_manager import HistoricalDataManager
from .cache import RedisCache
from ..api.angel_one_client import AngelOneClient
from ..api.dhan_client import DhanClient
from ..api.news_client import NewsClient
from ..api.weather_client import WeatherClient
from ..utils.logger import get_logger

# Simplified protocol typing for compatibility across websockets versions
WebSocketServerProtocol = Any  # type: ignore


class StreamType(str, Enum):
    """Types of data streams"""

    MARKET_DATA = "market_data"
    NEWS = "news"
    WEATHER = "weather"
    SOCIAL_SENTIMENT = "social_sentiment"
    TRADE_SIGNALS = "trade_signals"
    PORTFOLIO_UPDATES = "portfolio_updates"
    AI_INSIGHTS = "ai_insights"
    SYSTEM_ALERTS = "system_alerts"


class ProcessingStatus(str, Enum):
    """Processing status states"""

    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"
    STOPPED = "stopped"


class AlertSeverity(str, Enum):
    """Alert severity levels"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class StreamData:
    """Base class for all stream data"""

    stream_type: StreamType
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    symbol: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    source: str = "unknown"
    latency_ms: float = 0.0
    confidence: float = 1.0

    def __post_init__(self):
        if self.timestamp.tzinfo is None:
            self.timestamp = self.timestamp.replace(tzinfo=timezone.utc)

    def to_websocket_message(self) -> Dict[str, Any]:
        """Convert to WebSocket message format"""
        return {
            "type": self.stream_type.value,
            "timestamp": self.timestamp.isoformat(),
            "data": {
                "symbol": self.symbol,
                "source": self.source,
                "latency_ms": self.latency_ms,
                "confidence": self.confidence,
                **self.data,
            },
        }


@dataclass
class MarketDataStream(StreamData):
    """Real-time market data stream"""

    stream_type: StreamType = StreamType.MARKET_DATA
    ohlcv: Optional[Dict[str, Any]] = None
    indicators: Optional[Dict[str, float]] = None
    quote: Optional[Dict[str, float]] = None

    def __post_init__(self):
        super().__post_init__()
        self.data.update(
            {"ohlcv": self.ohlcv, "indicators": self.indicators, "quote": self.quote}
        )


@dataclass
class NewsStream(StreamData):
    """Real-time news stream"""

    stream_type: StreamType = StreamType.NEWS
    title: str = ""
    content: str = ""
    relevance_score: float = 0.0
    sentiment_score: float = 0.0
    extracted_symbols: List[str] = field(default_factory=list)

    def __post_init__(self):
        super().__post_init__()
        self.data.update(
            {
                "title": self.title,
                "content": self.content[:500],  # Truncate for WebSocket
                "relevance_score": self.relevance_score,
                "sentiment_score": self.sentiment_score,
                "extracted_symbols": self.extracted_symbols,
            }
        )


@dataclass
class WeatherStream(StreamData):
    """Weather data stream"""

    stream_type: StreamType = StreamType.WEATHER
    location: str = ""
    temperature: float = 0.0
    humidity: float = 0.0
    conditions: str = ""
    sector_impact: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        super().__post_init__()
        self.data.update(
            {
                "location": self.location,
                "temperature": self.temperature,
                "humidity": self.humidity,
                "conditions": self.conditions,
                "sector_impact": self.sector_impact,
            }
        )


@dataclass
class SystemAlert(StreamData):
    """System alert stream"""

    stream_type: StreamType = StreamType.SYSTEM_ALERTS
    severity: AlertSeverity = AlertSeverity.INFO
    message: str = ""
    component: str = ""
    resolution: Optional[str] = None

    def __post_init__(self):
        super().__post_init__()
        self.data.update(
            {
                "severity": self.severity.value,
                "message": self.message,
                "component": self.component,
                "resolution": self.resolution,
            }
        )


class StreamMetrics:
    """Performance metrics for stream processing"""

    def __init__(self, stream_type: StreamType):
        self.stream_type = stream_type
        self.messages_received = 0
        self.messages_processed = 0
        self.messages_failed = 0
        self.total_latency = 0.0
        self.max_latency = 0.0
        self.min_latency = float("inf")
        self.latency_history = deque(maxlen=100)
        self.throughput_history = deque(maxlen=60)  # Last 60 seconds
        self.last_message_time = None
        self.start_time = time.time()
        self.error_rate = 0.0
        self._lock = threading.Lock()

    def record_message(self, latency_ms: float, success: bool = True):
        """Record a processed message"""
        with self._lock:
            self.messages_received += 1

            if success:
                self.messages_processed += 1
                self.total_latency += latency_ms
                self.max_latency = max(self.max_latency, latency_ms)
                self.min_latency = min(self.min_latency, latency_ms)
                self.latency_history.append(latency_ms)
            else:
                self.messages_failed += 1

            self.last_message_time = time.time()
            self.throughput_history.append(time.time())
            self._update_error_rate()

    def _update_error_rate(self):
        """Update error rate"""
        if self.messages_received > 0:
            self.error_rate = self.messages_failed / self.messages_received

    def get_average_latency(self) -> float:
        """Get average latency"""
        if self.messages_processed > 0:
            return self.total_latency / self.messages_processed
        return 0.0

    def get_p95_latency(self) -> float:
        """Get 95th percentile latency"""
        if self.latency_history:
            sorted_latencies = sorted(self.latency_history)
            index = int(len(sorted_latencies) * 0.95)
            return sorted_latencies[min(index, len(sorted_latencies) - 1)]
        return 0.0

    def get_throughput(self) -> float:
        """Get messages per second"""
        current_time = time.time()
        # Count messages in last second
        recent_messages = sum(
            1 for ts in self.throughput_history if current_time - ts <= 1.0
        )
        return recent_messages

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics"""
        uptime = time.time() - self.start_time
        return {
            "stream_type": self.stream_type.value,
            "messages_received": self.messages_received,
            "messages_processed": self.messages_processed,
            "messages_failed": self.messages_failed,
            "error_rate": self.error_rate,
            "average_latency_ms": self.get_average_latency(),
            "p95_latency_ms": self.get_p95_latency(),
            "max_latency_ms": self.max_latency,
            "min_latency_ms": (
                self.min_latency if self.min_latency != float("inf") else 0
            ),
            "throughput_per_second": self.get_throughput(),
            "uptime_seconds": uptime,
            "last_message_ago_seconds": (
                time.time() - self.last_message_time if self.last_message_time else None
            ),
        }


class StreamProcessor(ABC):
    """Abstract base class for stream processors"""

    def __init__(self, stream_type: StreamType):
        self.stream_type = stream_type
        self.logger: Any = get_logger(
            f"niraj.information_processor.{stream_type.value}"
        )
        self.metrics = StreamMetrics(stream_type)
        self.is_running = False
        # Subscribers may be synchronous or async callbacks
        self.subscribers: List[
            Callable[[StreamData], Any] | Callable[[StreamData], Awaitable[None]]
        ] = []
        self.error_handlers: List[Callable[[Exception], None]] = []

    @abstractmethod
    async def start(self):
        """Start the stream processor"""
        pass

    @abstractmethod
    async def stop(self):
        """Stop the stream processor"""
        pass

    @abstractmethod
    async def process_data(self, raw_data: Any) -> Optional[StreamData]:
        """Process raw data into structured stream data"""
        pass

    def subscribe(self, callback: Callable[[StreamData], Any] | Callable[[StreamData], Awaitable[None]]):
        """Subscribe to stream data (supports sync or async callbacks)"""
        self.subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[StreamData], None]):
        """Unsubscribe from stream data"""
        if callback in self.subscribers:
            self.subscribers.remove(callback)

    def add_error_handler(self, handler: Callable[[Exception], None]):
        """Add error handler"""
        self.error_handlers.append(handler)

    async def emit(self, stream_data: StreamData):
        """Emit data to subscribers"""
        for subscriber in list(self.subscribers):  # copy to avoid modification during iteration
            try:
                result = subscriber(stream_data)
                if asyncio.iscoroutine(result):  # Handles both coroutine functions and returned coroutines
                    await result
            except Exception as e:  # pragma: no cover - defensive logging
                self.logger.error(f"Error in subscriber: {e}")

    def handle_error(self, error: Exception):
        """Handle errors"""
        for handler in self.error_handlers:
            try:
                handler(error)
            except Exception as e:
                self.logger.error(f"Error in error handler: {e}")


class MarketDataProcessor(StreamProcessor):
    """Real-time market data stream processor"""

    def __init__(
        self,
        angel_one_client: Optional[AngelOneClient] = None,
        dhan_client: Optional[DhanClient] = None,
    ):
        super().__init__(StreamType.MARKET_DATA)
        self.angel_one_client = angel_one_client
        self.dhan_client = dhan_client
        self.websocket_connections: Dict[str, WebSocketServerProtocol] = {}
        self.subscribed_symbols: Set[str] = set()
        self.last_prices: Dict[str, Decimal] = {}

    async def start(self):
        """Start market data processing"""
        self.is_running = True
        self.logger.info("Starting market data processor")

        # Start WebSocket connections for real-time data
        tasks = []

        if self.angel_one_client:
            tasks.append(self._start_angel_one_stream())

        if self.dhan_client:
            tasks.append(self._start_dhan_stream())

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def stop(self):
        """Stop market data processing"""
        self.is_running = False

        # Close WebSocket connections
        for connection in self.websocket_connections.values():
            try:
                await connection.close()
            except Exception as e:
                self.logger.warning(f"Error closing WebSocket connection: {e}")

        self.websocket_connections.clear()
        self.logger.info("Market data processor stopped")

    async def _start_angel_one_stream(self):
        """Start Angel One WebSocket stream"""
        try:
            while self.is_running:
                try:
                    # This would connect to Angel One's WebSocket API
                    # Implementation would depend on their specific protocol
                    await self._process_angel_one_messages()
                except Exception as e:
                    self.logger.error(f"Angel One stream error: {e}")
                    await asyncio.sleep(5)  # Reconnection delay
        except Exception as e:
            self.logger.error(f"Fatal error in Angel One stream: {e}")

    async def _start_dhan_stream(self):
        """Start Dhan WebSocket stream"""
        try:
            while self.is_running:
                try:
                    # This would connect to Dhan's WebSocket API
                    # Implementation would depend on their specific protocol
                    await self._process_dhan_messages()
                except Exception as e:
                    self.logger.error(f"Dhan stream error: {e}")
                    await asyncio.sleep(5)  # Reconnection delay
        except Exception as e:
            self.logger.error(f"Fatal error in Dhan stream: {e}")

    async def _process_angel_one_messages(self):
        """Process Angel One WebSocket messages"""
        # Mock implementation - would connect to real WebSocket
        await asyncio.sleep(1)

        # Simulate market data
        for symbol in self.subscribed_symbols:
            if not self.is_running:
                break

            # Generate mock tick data
            last_price = self.last_prices.get(symbol, Decimal("45000"))
            # Use random.uniform; statistics.uniform does not exist (type-safe correction)
            price_change = Decimal(str(random.uniform(-50, 50)))
            new_price = last_price + price_change

            tick_data = {
                "symbol": symbol,
                "ltp": float(new_price),
                "timestamp": time.time() * 1000,
                "volume": int(random.uniform(1000, 10000)),
                "bid": float(new_price - Decimal("0.25")),
                "ask": float(new_price + Decimal("0.25")),
            }

            self.last_prices[symbol] = new_price

            # Process the tick data
            stream_data = await self.process_data(tick_data)
            if stream_data:
                await self.emit(stream_data)

    async def _process_dhan_messages(self):
        """Process Dhan WebSocket messages"""
        # Similar to Angel One implementation
        await asyncio.sleep(1)

    async def process_data(self, raw_data: Any) -> Optional[MarketDataStream]:
        """Process raw market data"""
        try:
            start_time = time.time()

            # Extract basic info
            symbol = raw_data.get("symbol")
            if not symbol:
                return None

            # Create OHLCV data (for tick data, O=H=L=C=LTP)
            ltp = raw_data.get("ltp", 0)
            ohlcv = {
                "timestamp": datetime.fromtimestamp(
                    raw_data.get("timestamp", time.time() * 1000) / 1000,
                    tz=timezone.utc,
                ).isoformat(),
                "open": ltp,
                "high": ltp,
                "low": ltp,
                "close": ltp,
                "volume": raw_data.get("volume", 0),
                "change_percent": 0.0,  # Would calculate from previous close
            }

            # Create quote data
            quote = {
                "bid": raw_data.get("bid", ltp),
                "ask": raw_data.get("ask", ltp),
                "last_price": ltp,
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }

            # Calculate basic indicators (simplified)
            indicators = {
                "rsi_14": 50.0,  # Would calculate actual RSI
                "sma_20": ltp,
                "bb_upper": ltp * 1.02,
                "bb_lower": ltp * 0.98,
            }

            latency = (time.time() - start_time) * 1000

            stream_data = MarketDataStream(
                timestamp=datetime.now(timezone.utc),
                symbol=symbol,
                source="angel_one",  # or determine from context
                latency_ms=latency,
                ohlcv=ohlcv,
                indicators=indicators,
                quote=quote,
            )

            self.metrics.record_message(latency, success=True)
            return stream_data

        except Exception as e:
            self.logger.error(f"Error processing market data: {e}")
            self.metrics.record_message(0, success=False)
            return None

    def subscribe_to_symbol(self, symbol: str):
        """Subscribe to real-time data for a symbol"""
        self.subscribed_symbols.add(symbol)
        self.logger.info(f"Subscribed to market data for {symbol}")

    def unsubscribe_from_symbol(self, symbol: str):
        """Unsubscribe from a symbol"""
        self.subscribed_symbols.discard(symbol)
        self.logger.info(f"Unsubscribed from market data for {symbol}")


class NewsProcessor(StreamProcessor):
    """Real-time news stream processor"""

    def __init__(self, news_client: Any):  # NewsClient treated as Any to allow dynamic methods
        super().__init__(StreamType.NEWS)
        self.news_client = news_client
        self.processed_articles: Set[str] = set()
        self.polling_interval = 60  # seconds
        self.sentiment_keywords = {
            "bullish": [
                "surge",
                "rally",
                "bull",
                "optimistic",
                "positive",
                "growth",
                "rise",
            ],
            "bearish": ["crash", "fall", "bear", "negative", "decline", "drop", "loss"],
        }

    async def start(self):
        """Start news processing"""
        self.is_running = True
        self.logger.info("Starting news processor")

        while self.is_running:
            try:
                await self._fetch_and_process_news()
                await asyncio.sleep(self.polling_interval)
            except Exception as e:
                self.logger.error(f"Error in news processing loop: {e}")
                await asyncio.sleep(30)  # Error recovery delay

    async def stop(self):
        """Stop news processing"""
        self.is_running = False
        self.logger.info("News processor stopped")

    async def _fetch_and_process_news(self):
        """Fetch and process latest news"""
        try:
            # Get business/finance news
            articles = await self.news_client.get_business_headlines(
                country="in", page_size=50
            )

            for article in articles:
                # Skip if already processed
                article_id = hashlib.md5(
                    f"{article['title']}{article.get('publishedAt', '')}".encode()
                ).hexdigest()

                if article_id in self.processed_articles:
                    continue

                self.processed_articles.add(article_id)

                # Limit cache size
                if len(self.processed_articles) > 1000:
                    # Remove oldest entries (simplified)
                    self.processed_articles = set(list(self.processed_articles)[-500:])

                # Process the article
                stream_data = await self.process_data(article)
                if stream_data:
                    await self.emit(stream_data)

        except Exception as e:
            self.logger.error(f"Error fetching news: {e}")

    def _calculate_sentiment_score(self, text: str) -> float:
        """Calculate sentiment score from text"""
        text_lower = text.lower()
        bullish_count = sum(
            1 for word in self.sentiment_keywords["bullish"] if word in text_lower
        )
        bearish_count = sum(
            1 for word in self.sentiment_keywords["bearish"] if word in text_lower
        )

        total_sentiment_words = bullish_count + bearish_count
        if total_sentiment_words == 0:
            return 0.0  # Neutral

        # Normalize to -1 to +1 scale
        return (bullish_count - bearish_count) / total_sentiment_words

    def _extract_symbols(self, text: str) -> List[str]:
        """Extract stock symbols from text"""
        # Indian market symbol patterns
        patterns = [
            r"\b[A-Z]{2,10}\.NS\b",  # NSE symbols
            r"\b[A-Z]{2,10}\.BO\b",  # BSE symbols
            r"\b(?:NIFTY|SENSEX|BANKNIFTY)\b",  # Index names
            r"\b[A-Z]{2,10}\s+(?:BANK|LTD|LIMITED)\b",  # Bank names
        ]

        symbols = set()
        for pattern in patterns:
            matches = re.findall(pattern, text.upper())
            symbols.update(matches)

        return list(symbols)

    async def process_data(self, raw_data: Any) -> Optional[NewsStream]:
        """Process raw news data"""
        try:
            start_time = time.time()

            title = raw_data.get("title", "")
            content = raw_data.get("description", "") or raw_data.get("content", "")

            if not title:
                return None

            # Calculate relevance and sentiment
            full_text = f"{title} {content}"
            relevance_score = await self.news_client.calculate_relevance_score(raw_data)
            sentiment_score = self._calculate_sentiment_score(full_text)

            # Extract symbols
            extracted_symbols = self._extract_symbols(full_text)

            # Only process if relevant to trading
            if relevance_score < 0.3 and not extracted_symbols:
                return None

            latency = (time.time() - start_time) * 1000

            stream_data = NewsStream(
                timestamp=datetime.now(timezone.utc),
                source=raw_data.get("source", {}).get("name", "unknown"),
                latency_ms=latency,
                title=title,
                content=content,
                relevance_score=relevance_score,
                sentiment_score=sentiment_score,
                extracted_symbols=extracted_symbols,
                confidence=min(relevance_score * 2, 1.0),  # Convert to confidence
            )

            self.metrics.record_message(latency, success=True)
            return stream_data

        except Exception as e:
            self.logger.error(f"Error processing news data: {e}")
            self.metrics.record_message(0, success=False)
            return None


class WeatherProcessor(StreamProcessor):
    """Weather data processor with sector impact analysis"""

    def __init__(self, weather_client: Any):  # WeatherClient treated as Any for flexible query input
        super().__init__(StreamType.WEATHER)
        self.weather_client = weather_client
        self.major_cities = ["Mumbai", "Delhi", "Bangalore", "Chennai", "Kolkata"]
        self.polling_interval = 1800  # 30 minutes
        self.sector_impact_map = {
            "agricultural_banks": ["temperature", "humidity", "precipitation"],
            "power_sector": ["temperature", "wind_speed"],
            "insurance": ["extreme_weather", "natural_disasters"],
            "commodities": ["temperature", "precipitation"],
        }

    async def start(self):
        """Start weather processing"""
        self.is_running = True
        self.logger.info("Starting weather processor")

        while self.is_running:
            try:
                await self._fetch_and_process_weather()
                await asyncio.sleep(self.polling_interval)
            except Exception as e:
                self.logger.error(f"Error in weather processing loop: {e}")
                await asyncio.sleep(300)  # Error recovery delay

    async def stop(self):
        """Stop weather processing"""
        self.is_running = False
        self.logger.info("Weather processor stopped")

    async def _fetch_and_process_weather(self):
        """Fetch and process weather data for major cities"""
        for city in self.major_cities:
            try:
                weather_data = await self.weather_client.get_current_weather(city)

                if weather_data:
                    stream_data = await self.process_data(weather_data)
                    if stream_data:
                        await self.emit(stream_data)

            except Exception as e:
                self.logger.error(f"Error processing weather for {city}: {e}")

    def _calculate_sector_impact(
        self, weather_data: Dict[str, Any]
    ) -> Dict[str, float]:
        """Calculate impact on different sectors"""
        impacts = {}

        temp = weather_data.get("temperature", 25)
        humidity = weather_data.get("humidity", 50)
        conditions = weather_data.get("conditions", "").lower()

        # Agricultural banks impact
        if temp > 40 or temp < 5:  # Extreme temperatures
            impacts["agricultural_banks"] = -0.3
        elif "rain" in conditions or humidity > 80:
            impacts["agricultural_banks"] = 0.2
        else:
            impacts["agricultural_banks"] = 0.0

        # Power sector impact
        if temp > 35:  # High power demand for cooling
            impacts["power_sector"] = 0.4
        elif temp < 10:  # High power demand for heating
            impacts["power_sector"] = 0.3
        else:
            impacts["power_sector"] = 0.0

        # Insurance sector impact
        if any(
            extreme in conditions
            for extreme in ["storm", "cyclone", "flood", "drought"]
        ):
            impacts["insurance"] = -0.5
        else:
            impacts["insurance"] = 0.0

        return impacts

    async def process_data(self, raw_data: Any) -> Optional[WeatherStream]:
        """Process raw weather data"""
        try:
            start_time = time.time()

            location = raw_data.get("name", "Unknown")
            temperature = raw_data.get("main", {}).get("temp", 0) - 273.15  # K to C
            humidity = raw_data.get("main", {}).get("humidity", 0)
            conditions = raw_data.get("weather", [{}])[0].get("description", "")

            # Calculate sector impacts
            sector_impact = self._calculate_sector_impact(
                {
                    "temperature": temperature,
                    "humidity": humidity,
                    "conditions": conditions,
                }
            )

            latency = (time.time() - start_time) * 1000

            stream_data = WeatherStream(
                timestamp=datetime.now(timezone.utc),
                source="openweathermap",
                latency_ms=latency,
                location=location,
                temperature=temperature,
                humidity=humidity,
                conditions=conditions,
                sector_impact=sector_impact,
                confidence=0.9,  # Weather data is generally reliable
            )

            self.metrics.record_message(latency, success=True)
            return stream_data

        except Exception as e:
            self.logger.error(f"Error processing weather data: {e}")
            self.metrics.record_message(0, success=False)
            return None


class InformationProcessor:
    """
    Advanced real-time information processing system for NIRAJ trading system

    Features:
    - Multi-stream real-time data processing (market, news, weather) - Sub-second latency processing with performance monitoring - Advanced error handling and circuit breakers - WebSocket stream management and broadcasting - Comprehensive metrics and alerting - Data correlation and enrichment -
    Configurable processing pipelines
    """

    def __init__(
        self,
        data_manager: Optional[HistoricalDataManager] = None,
        angel_one_client: Optional[AngelOneClient] = None,
        dhan_client: Optional[DhanClient] = None,
        news_client: Optional[NewsClient] = None,
        weather_client: Optional[WeatherClient] = None,
        cache: Optional[RedisCache] = None,
    ):
        """
        Initialize information processor

        Args:
            data_manager: Historical data manager instance
            angel_one_client: Angel One API client
            dhan_client: Dhan API client
            news_client: News API client
            weather_client: Weather API client
            cache: Redis cache instance
        """
        self.logger: Any = get_logger("niraj.information_processor")

        # Core components
        self.data_manager = data_manager
        self.cache = cache or RedisCache()

        # Stream processors
        self.processors: Dict[StreamType, StreamProcessor] = {}

        if angel_one_client or dhan_client:
            self.processors[StreamType.MARKET_DATA] = MarketDataProcessor(
                angel_one_client, dhan_client
            )

        if news_client:
            self.processors[StreamType.NEWS] = NewsProcessor(news_client)

        if weather_client:
            self.processors[StreamType.WEATHER] = WeatherProcessor(weather_client)

        # WebSocket management
        self.websocket_clients: Set[WebSocketServerProtocol] = set()
        self.client_subscriptions: Dict[str, Dict[str, Any]] = defaultdict(dict)

        # Processing state
        self.status = ProcessingStatus.STOPPED
        self.start_time: Optional[datetime] = None
        self.processing_tasks: List[asyncio.Task] = []

        # Configuration
        self.max_latency_ms = 50  # Sub-second requirement
        self.alert_threshold_error_rate = 0.1  # 10%
        self.performance_check_interval = 30  # seconds

        # Metrics aggregation
        self.global_metrics = {
            "total_messages_processed": 0,
            "total_errors": 0,
            "average_processing_latency": 0.0,
            "peak_throughput": 0.0,
            "uptime_seconds": 0.0,
        }

        # Setup stream subscriptions
        self._setup_stream_subscriptions()

        self.logger.info(
            "Information Processor initialized; processors=%s max_latency_ms=%s",
            list(self.processors.keys()),
            self.max_latency_ms,
        )

    def _setup_stream_subscriptions(self):
        """Setup subscriptions between processors"""
        for processor in self.processors.values():
            processor.subscribe(self._handle_stream_data)  # Async handler accepted via updated subscriber typing
            processor.add_error_handler(self._handle_processor_error)

    async def _handle_stream_data(self, stream_data: StreamData):
        """Handle incoming stream data"""
        try:
            # Update global metrics
            self.global_metrics["total_messages_processed"] += 1

            # Check latency requirements
            if stream_data.latency_ms > self.max_latency_ms:
                await self._emit_alert(
                    AlertSeverity.WARNING,
                    f"High latency detected: {stream_data.latency_ms:.2f}ms > {self.max_latency_ms}ms",
                    f"{stream_data.stream_type.value}_processor",
                )

            # Store in cache for recent access
            cache_key = f"stream:{stream_data.stream_type.value}:{stream_data.symbol or 'global'}:latest"
            await self.cache.set(
                cache_key,
                stream_data.to_websocket_message(),
                prefix="real_time",
                ttl=300,  # 5 minutes
            )

            # Broadcast to WebSocket clients
            await self._broadcast_to_websockets(stream_data)

        except Exception as e:
            self.logger.error(f"Error handling stream data: {e}")
            self.global_metrics["total_errors"] += 1

    def _handle_processor_error(self, error: Exception):
        """Handle processor errors"""
        self.global_metrics["total_errors"] += 1
        self.logger.error(f"Processor error: {error}")

    async def _emit_alert(self, severity: AlertSeverity, message: str, component: str):
        """Emit system alert"""
        alert = SystemAlert(
            timestamp=datetime.now(timezone.utc),
            severity=severity,
            message=message,
            component=component,
            source="information_processor",
        )

        # Broadcast alert
        await self._broadcast_to_websockets(alert)

        # Log based on severity
        log_msg = f"[{component}] {message}"
        if severity == AlertSeverity.CRITICAL:
            self.logger.critical(log_msg)
        elif severity == AlertSeverity.ERROR:
            self.logger.error(log_msg)
        elif severity == AlertSeverity.WARNING:
            self.logger.warning(log_msg)
        else:
            self.logger.info(log_msg)

    async def _broadcast_to_websockets(self, stream_data: StreamData):
        """Broadcast data to WebSocket clients"""
        if not self.websocket_clients:
            return

        message = json.dumps(stream_data.to_websocket_message())
        disconnected_clients = set()

        for client in list(self.websocket_clients):  # copy to avoid mutation issues
            try:
                # Check if client is subscribed to this stream type
                client_id = id(client)
                subscriptions = self.client_subscriptions.get(str(client_id), {})

                stream_type = stream_data.stream_type.value
                if stream_type not in subscriptions:
                    continue

                # Check symbol-specific subscriptions
                if (
                    stream_data.symbol
                    and subscriptions[stream_type].get("symbols")
                    and stream_data.symbol not in subscriptions[stream_type]["symbols"]
                ):
                    continue

                await client.send(message)

            except websockets.exceptions.ConnectionClosed:
                disconnected_clients.add(client)
            except Exception as e:
                self.logger.warning(f"Error broadcasting to WebSocket client: {e}")
                disconnected_clients.add(client)

        # Remove disconnected clients
        self.websocket_clients -= disconnected_clients
        for client in disconnected_clients:
            client_id = str(id(client))
            if client_id in self.client_subscriptions:
                del self.client_subscriptions[client_id]

    async def start(self):
        """Start all stream processors"""
        if self.status == ProcessingStatus.ACTIVE:
            self.logger.warning("Information processor already running")
            return

        self.status = ProcessingStatus.ACTIVE
        self.start_time = datetime.now(timezone.utc)

        self.logger.info("Starting information processor")

        try:
            # Start all processors
            for stream_type, processor in self.processors.items():
                try:
                    task = asyncio.create_task(processor.start())
                    self.processing_tasks.append(task)
                    self.logger.info(f"Started {stream_type.value} processor")
                except Exception as e:
                    self.logger.error(
                        f"Failed to start {stream_type.value} processor: {e}"
                    )

            # Start performance monitoring
            monitor_task = asyncio.create_task(self._performance_monitor())
            self.processing_tasks.append(monitor_task)

            await self._emit_alert(
                AlertSeverity.INFO,
                "Information processor started successfully",
                "system",
            )

        except Exception as e:
            self.status = ProcessingStatus.ERROR
            self.logger.error(f"Failed to start information processor: {e}")
            raise

    async def stop(self):
        """Stop all stream processors"""
        if self.status == ProcessingStatus.STOPPED:
            return

        self.status = ProcessingStatus.STOPPED
        self.logger.info("Stopping information processor")

        # Stop all processors
        for processor in self.processors.values():
            try:
                await processor.stop()
            except Exception as e:
                self.logger.error(f"Error stopping processor: {e}")

        # Cancel all tasks
        for task in self.processing_tasks:
            if not task.done():
                task.cancel()

        # Wait for tasks to complete
        if self.processing_tasks:
            await asyncio.gather(*self.processing_tasks, return_exceptions=True)

        self.processing_tasks.clear()

        # Close WebSocket connections
        for client in list(self.websocket_clients):
            try:
                await client.close()
            except Exception as e:
                self.logger.warning(f"Error closing WebSocket client: {e}")

        self.websocket_clients.clear()
        self.client_subscriptions.clear()

        await self._emit_alert(
            AlertSeverity.INFO, "Information processor stopped", "system"
        )

    async def _performance_monitor(self):
        """Monitor performance and emit alerts"""
        while self.status == ProcessingStatus.ACTIVE:
            try:
                await asyncio.sleep(self.performance_check_interval)

                # Calculate global metrics
                total_throughput = 0
                max_latency = 0
                total_error_rate = 0

                for processor in self.processors.values():
                    stats = processor.metrics.get_stats()
                    total_throughput += stats["throughput_per_second"]
                    max_latency = max(max_latency, stats["max_latency_ms"])
                    total_error_rate += stats["error_rate"]

                avg_error_rate = (
                    total_error_rate / len(self.processors) if self.processors else 0
                )

                # Update global metrics
                self.global_metrics["peak_throughput"] = max(
                    self.global_metrics["peak_throughput"], total_throughput
                )

                if self.start_time:
                    self.global_metrics["uptime_seconds"] = (
                        datetime.now(timezone.utc) - self.start_time
                    ).total_seconds()

                # Check for performance issues
                if avg_error_rate > self.alert_threshold_error_rate:
                    await self._emit_alert(
                        AlertSeverity.ERROR,
                        f"High error rate detected: {avg_error_rate:.2%}",
                        "performance_monitor",
                    )

                if max_latency > self.max_latency_ms * 2:  # Double the threshold
                    await self._emit_alert(
                        AlertSeverity.WARNING,
                        f"Very high latency detected: {max_latency:.2f}ms",
                        "performance_monitor",
                    )

            except Exception as e:
                self.logger.error(f"Error in performance monitor: {e}")

    async def add_websocket_client(
        self,
        websocket: WebSocketServerProtocol,
        subscriptions: Dict[str, Any],
    ):
        """Add WebSocket client with subscriptions"""
        self.websocket_clients.add(websocket)
        client_id = str(id(websocket))
        self.client_subscriptions[client_id] = subscriptions

        self.logger.info(
            f"Added WebSocket client with subscriptions: {list(subscriptions.keys())}"
        )

        # Send current status
        status_message = {
            "type": "connection_status",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {
                "status": "connected",
                "subscriptions": subscriptions,
                "available_streams": list(self.processors.keys()),
            },
        }

        await websocket.send(json.dumps(status_message))

    def remove_websocket_client(self, websocket: WebSocketServerProtocol):
        """Remove WebSocket client"""
        self.websocket_clients.discard(websocket)
        client_id = str(id(websocket))
        if client_id in self.client_subscriptions:
            del self.client_subscriptions[client_id]

        self.logger.info("Removed WebSocket client")

    async def subscribe_to_market_data(self, symbols: List[str]):
        """Subscribe to real-time market data for symbols"""
        if StreamType.MARKET_DATA in self.processors:
            processor = self.processors[StreamType.MARKET_DATA]
            if isinstance(processor, MarketDataProcessor):  # type guard
                for symbol in symbols:
                    processor.subscribe_to_symbol(symbol)

    async def unsubscribe_from_market_data(self, symbols: List[str]):
        """Unsubscribe from market data for symbols"""
        if StreamType.MARKET_DATA in self.processors:
            processor = self.processors[StreamType.MARKET_DATA]
            if isinstance(processor, MarketDataProcessor):  # type guard
                for symbol in symbols:
                    processor.unsubscribe_from_symbol(symbol)

    async def get_latest_data(
        self, stream_type: StreamType, symbol: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get latest data for a stream type"""
        try:
            cache_key = f"stream:{stream_type.value}:{symbol or 'global'}:latest"
            data = await self.cache.get(cache_key, prefix="real_time")
            return data
        except Exception as e:
            self.logger.error(f"Error getting latest data: {e}")
            return None

    def get_comprehensive_metrics(self) -> Dict[str, Any]:
        """Get comprehensive metrics for all processors"""
        processor_metrics = {}

        for stream_type, processor in self.processors.items():
            processor_metrics[stream_type.value] = processor.metrics.get_stats()

        return {
            "global_metrics": self.global_metrics,
            "processor_metrics": processor_metrics,
            "websocket_clients": len(self.websocket_clients),
            "status": self.status.value,
            "uptime": self.global_metrics["uptime_seconds"],
            "subscriptions": {
                client_id: subs for client_id, subs in self.client_subscriptions.items()
            },
        }

    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check"""
        health = {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "information_processor": {
                "status": self.status.value,
                "processors_running": len(
                    [p for p in self.processors.values() if p.is_running]
                ),
                "total_processors": len(self.processors),
                "websocket_clients": len(self.websocket_clients),
            },
            "processors": {},
        }

        # Check individual processors
        all_healthy = True
        for stream_type, processor in self.processors.items():
            processor_health = {
                "running": processor.is_running,
                "error_rate": processor.metrics.error_rate,
                "average_latency": processor.metrics.get_average_latency(),
                "throughput": processor.metrics.get_throughput(),
            }

            if not processor.is_running or processor.metrics.error_rate > 0.2:
                all_healthy = False

            health["processors"][stream_type.value] = processor_health

        # Overall status
        if not all_healthy:
            health["status"] = "degraded"

        if self.status == ProcessingStatus.ERROR:
            health["status"] = "unhealthy"

        return health

    async def __aenter__(self):
        """Async context manager entry"""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.stop()


# Convenience factory function
async def create_information_processor(
    data_manager_config: Optional[Dict[str, Any]] = None,
    angel_one_config: Optional[Dict[str, str]] = None,
    dhan_config: Optional[Dict[str, str]] = None,
    news_config: Optional[Dict[str, str]] = None,
    weather_config: Optional[Dict[str, str]] = None,
    cache_config: Optional[Dict[str, Any]] = None,
) -> InformationProcessor:
    """
    Create and configure an information processor instance

    Args:
        data_manager_config: Data manager configuration
        angel_one_config: Angel One client configuration
        dhan_config: Dhan client configuration
        news_config: News client configuration
        weather_config: Weather client configuration
        cache_config: Cache configuration

    Returns:
        Configured InformationProcessor instance
    """
    # Create clients
    angel_one_client = None
    dhan_client = None
    news_client = None
    weather_client = None
    data_manager = None

    if angel_one_config:
        # Pass configuration via named parameter to match expected signature; cast for typing flexibility
        angel_one_client = AngelOneClient(config=cast(Any, angel_one_config))  # type: ignore[arg-type]

    if dhan_config:
        dhan_client = DhanClient(config=cast(Any, dhan_config))  # type: ignore[arg-type]

    if news_config:
        news_client = NewsClient(config=cast(Any, news_config))  # type: ignore[arg-type]

    if weather_config:
        weather_client = WeatherClient(config=cast(Any, weather_config))  # type: ignore[arg-type]

    if data_manager_config:
        from .data_manager import create_data_manager

        data_manager = await create_data_manager(**data_manager_config)

    # Create cache
    cache = None
    if cache_config:
        cache = RedisCache(**cache_config)
        await cache.connect()

    # Create information processor
    processor = InformationProcessor(
        data_manager=data_manager,
        angel_one_client=angel_one_client,
        dhan_client=dhan_client,
        news_client=news_client,
        weather_client=weather_client,
        cache=cache,
    )

    return processor
