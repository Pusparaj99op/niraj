"""
Technical Indicators Calculator

Advanced technical analysis calculator for NIRAJ trading system.
Supports comprehensive indicator calculations with error handling, validation,
and performance optimization for real-time trading applications.

Features:
- All major technical indicators (trend, momentum, volatility, volume) - Custom NIRAJ-specific indicators - Advanced error handling and data validation - Performance optimization with caching - Real-time calculation capabilities -
Confidence scoring and data quality assessment
"""

import time
import math
import statistics
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass, field
import logging

from models.technical_indicator import IndicatorType, get_default_parameters

# Configure logging
logger = logging.getLogger(__name__)


class CalculationError(Exception):
    """Custom exception for calculation errors"""

    def __init__(self, message: str, indicator_type: str = None, symbol: str = None):
        self.message = message
        self.indicator_type = indicator_type
        self.symbol = symbol
        super().__init__(self.message)


class InsufficientDataError(CalculationError):
    """Exception for insufficient data errors"""

    pass


class InvalidDataError(CalculationError):
    """Exception for invalid data errors"""

    pass


@dataclass
class MarketData:
    """Market data structure for calculations"""

    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    symbol: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MarketData":
        """Create MarketData from dictionary"""
        return cls(
            timestamp=(
                data["timestamp"]
                if isinstance(data["timestamp"], datetime)
                else datetime.fromisoformat(data["timestamp"])
            ),
            open=Decimal(str(data["open"])),
            high=Decimal(str(data["high"])),
            low=Decimal(str(data["low"])),
            close=Decimal(str(data["close"])),
            volume=int(data["volume"]),
            symbol=data.get("symbol", ""),
        )


@dataclass
class CalculationResult:
    """Result of indicator calculation"""

    value: Optional[Decimal] = None
    values: Optional[Dict[str, Any]] = None
    confidence_score: Optional[Decimal] = None
    data_points_used: int = 0
    calculation_time_ms: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class TechnicalIndicatorsCalculator:
    """
    Advanced Technical Indicators Calculator

    Provides comprehensive technical analysis calculations with:
    - Error handling and validation - Performance optimization - Confidence scoring -
    Real-time capabilities
    """

    def __init__(self, cache_enabled: bool = True, max_cache_size: int = 1000):
        """
        Initialize calculator

        Args:
            cache_enabled: Whether to enable caching
            max_cache_size: Maximum cache size
        """
        self.cache_enabled = cache_enabled
        self.max_cache_size = max_cache_size
        self._cache: Dict[str, Tuple[CalculationResult, datetime]] = {}
        self._cache_hits = 0
        self._cache_misses = 0

    def calculate_indicator(
        self,
        indicator_type: IndicatorType,
        data: List[MarketData],
        parameters: Optional[Dict[str, Any]] = None,
        symbol: str = "",
        use_cache: bool = True,
    ) -> CalculationResult:
        """
        Calculate technical indicator

        Args:
            indicator_type: Type of indicator to calculate
            data: Market data for calculation
            parameters: Calculation parameters
            symbol: Symbol for caching
            use_cache: Whether to use cache

        Returns:
            CalculationResult: Calculation result

        Raises:
            CalculationError: If calculation fails
        """
        start_time = time.time()

        try:
            # Validate input data
            self._validate_data(data, indicator_type)

            # Set default parameters
            if parameters is None:
                parameters = get_default_parameters(indicator_type)

            # Check cache
            cache_key = self._get_cache_key(indicator_type, data, parameters, symbol)
            if use_cache and self.cache_enabled and cache_key in self._cache:
                cached_result, cache_time = self._cache[cache_key]
                # Check if cache is still valid (within 1 minute for real-time data)
                if (datetime.utcnow() - cache_time).total_seconds() < 60:
                    self._cache_hits += 1
                    return cached_result

            # Perform calculation
            result = self._calculate_indicator_impl(indicator_type, data, parameters)

            # Calculate confidence score
            result.confidence_score = self._calculate_confidence_score(
                data, indicator_type, result
            )

            # Add calculation time
            result.calculation_time_ms = int((time.time() - start_time) * 1000)

            # Cache result
            if self.cache_enabled and cache_key:
                self._cache[cache_key] = (result, datetime.utcnow())
                self._cleanup_cache()

            self._cache_misses += 1
            return result

        except Exception as e:
            logger.error(
                f"Indicator calculation failed: {indicator_type.value} - {str(e)}"
            )
            raise CalculationError(
                f"Failed to calculate {indicator_type.value}: {str(e)}",
                indicator_type.value,
                symbol,
            )

    def _calculate_indicator_impl(
        self,
        indicator_type: IndicatorType,
        data: List[MarketData],
        parameters: Dict[str, Any],
    ) -> CalculationResult:
        """Internal indicator calculation implementation"""
        if indicator_type in [IndicatorType.SMA, IndicatorType.EMA]:
            return self._calculate_moving_average(indicator_type, data, parameters)
        elif indicator_type == IndicatorType.RSI:
            return self._calculate_rsi(data, parameters)
        elif indicator_type == IndicatorType.MACD:
            return self._calculate_macd(data, parameters)
        elif indicator_type == IndicatorType.BOLLINGER_BANDS:
            return self._calculate_bollinger_bands(data, parameters)
        elif indicator_type == IndicatorType.STOCHASTIC:
            return self._calculate_stochastic(data, parameters)
        elif indicator_type == IndicatorType.WILLIAMS_R:
            return self._calculate_williams_r(data, parameters)
        elif indicator_type == IndicatorType.ROC:
            return self._calculate_roc(data, parameters)
        elif indicator_type == IndicatorType.MFI:
            return self._calculate_mfi(data, parameters)
        elif indicator_type == IndicatorType.ATR:
            return self._calculate_atr(data, parameters)
        elif indicator_type == IndicatorType.KELTNER_CHANNEL:
            return self._calculate_keltner_channel(data, parameters)
        elif indicator_type == IndicatorType.OBV:
            return self._calculate_obv(data, parameters)
        elif indicator_type == IndicatorType.VWAP:
            return self._calculate_vwap(data, parameters)
        elif indicator_type == IndicatorType.AD_LINE:
            return self._calculate_ad_line(data, parameters)
        elif indicator_type == IndicatorType.CHAIKIN_MF:
            return self._calculate_chaikin_mf(data, parameters)
        elif indicator_type == IndicatorType.ADX:
            return self._calculate_adx(data, parameters)
        elif indicator_type == IndicatorType.PARABOLIC_SAR:
            return self._calculate_parabolic_sar(data, parameters)
        elif indicator_type == IndicatorType.OBV:
            return self._calculate_obv(data, parameters)
        elif indicator_type == IndicatorType.VWAP:
            return self._calculate_vwap(data, parameters)
        elif indicator_type == IndicatorType.PIVOT_POINTS:
            return self._calculate_pivot_points(data, parameters)
        elif indicator_type == IndicatorType.FIBONACCI_RETRACEMENT:
            return self._calculate_fibonacci_retracement(data, parameters)
        elif indicator_type == IndicatorType.PREDATOR_SIGNAL:
            return self._calculate_predator_signal(data, parameters)
        elif indicator_type == IndicatorType.BANK_NIFTY_DIVERGENCE:
            return self._calculate_bank_nifty_divergence(data, parameters)
        elif indicator_type == IndicatorType.FEAR_GREED_INDEX:
            return self._calculate_fear_greed_index(data, parameters)
        elif indicator_type == IndicatorType.MARKET_SENTIMENT:
            return self._calculate_market_sentiment(data, parameters)
        else:
            raise CalculationError(
                f"Unsupported indicator type: {indicator_type.value}"
            )

    def _validate_data(
        self, data: List[MarketData], indicator_type: IndicatorType
    ) -> None:
        """Validate input data"""
        if not data:
            raise InsufficientDataError("No data provided for calculation")

        if len(data) < 2:
            raise InsufficientDataError("At least 2 data points required")

        # Check for required minimum data based on indicator
        min_data_points = self._get_minimum_data_points(indicator_type)
        if len(data) < min_data_points:
            raise InsufficientDataError(
                f"Insufficient data: {indicator_type.value} requires at least {min_data_points} points, got {len(data)}"
            )

        # Validate data integrity
        for i, point in enumerate(data):
            if point.high < point.low:
                raise InvalidDataError(f"Invalid OHLC data at index {i}: high < low")
            if point.close < 0 or point.open < 0 or point.high < 0 or point.low < 0:
                raise InvalidDataError(f"Negative price values at index {i}")
            if point.volume < 0:
                raise InvalidDataError(f"Negative volume at index {i}")

    def _get_minimum_data_points(self, indicator_type: IndicatorType) -> int:
        """Get minimum data points required for indicator"""
        minimums = {
            IndicatorType.SMA: 2,
            IndicatorType.EMA: 2,
            IndicatorType.RSI: 14,
            IndicatorType.MACD: 26,
            IndicatorType.BOLLINGER_BANDS: 20,
            IndicatorType.STOCHASTIC: 14,
            IndicatorType.WILLIAMS_R: 14,
            IndicatorType.ROC: 13,
            IndicatorType.MFI: 15,
            IndicatorType.ATR: 14,
            IndicatorType.KELTNER_CHANNEL: 21,
            IndicatorType.DONCHIAN_CHANNEL: 20,
            IndicatorType.ADX: 14,
            IndicatorType.OBV: 2,
            IndicatorType.VWAP: 2,
            IndicatorType.AD_LINE: 2,
            IndicatorType.CHAIKIN_MF: 21,
            IndicatorType.PIVOT_POINTS: 1,
            IndicatorType.FIBONACCI_RETRACEMENT: 2,
            IndicatorType.PREDATOR_SIGNAL: 20,
            IndicatorType.BANK_NIFTY_DIVERGENCE: 10,
            IndicatorType.FEAR_GREED_INDEX: 5,
            IndicatorType.MARKET_SENTIMENT: 5,
        }
        return minimums.get(indicator_type, 2)

    def _calculate_moving_average(
        self,
        indicator_type: IndicatorType,
        data: List[MarketData],
        parameters: Dict[str, Any],
    ) -> CalculationResult:
        """Calculate Simple or Exponential Moving Average"""
        period = parameters.get("period", 20)
        prices = [point.close for point in data[-period:]]

        if indicator_type == IndicatorType.SMA:
            # Simple Moving Average
            value = sum(prices) / len(prices)
        else:  # EMA
            # Exponential Moving Average
            multiplier = 2 / (len(prices) + 1)
            ema = prices[0]

            for price in prices[1:]:
                ema = (price * multiplier) + (ema * (1 - multiplier))

            value = ema

        return CalculationResult(
            value=Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            data_points_used=len(prices),
        )

    def _calculate_rsi(
        self, data: List[MarketData], parameters: Dict[str, Any]
    ) -> CalculationResult:
        """Calculate Relative Strength Index"""
        period = parameters.get("period", 14)
        prices = [point.close for point in data]

        if len(prices) < period + 1:
            raise InsufficientDataError(
                f"RSI requires at least {period + 1} data points"
            )

        # Calculate price changes
        changes = []
        for i in range(1, len(prices)):
            changes.append(float(prices[i] - prices[i - 1]))

        # Calculate gains and losses
        gains = [change if change > 0 else 0 for change in changes[-period:]]
        losses = [abs(change) if change < 0 else 0 for change in changes[-period:]]

        avg_gain = statistics.mean(gains) if gains else 0
        avg_loss = statistics.mean(losses) if losses else 0

        if avg_loss == 0:
            rsi = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

        return CalculationResult(
            value=Decimal(str(rsi)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            data_points_used=len(changes),
        )

    def _calculate_macd(
        self, data: List[MarketData], parameters: Dict[str, Any]
    ) -> CalculationResult:
        """Calculate MACD (Moving Average Convergence Divergence)"""
        fast_period = parameters.get("fast_period", 12)
        slow_period = parameters.get("slow_period", 26)
        signal_period = parameters.get("signal_period", 9)

        prices = [point.close for point in data]

        if len(prices) < slow_period:
            raise InsufficientDataError(
                f"MACD requires at least {slow_period} data points"
            )

        # Calculate EMAs
        fast_ema = self._calculate_ema_values(prices, fast_period)
        slow_ema = self._calculate_ema_values(prices, slow_period)

        # Calculate MACD line
        macd_line = [fast - slow for fast, slow in zip(fast_ema, slow_ema)]

        # Calculate signal line (EMA of MACD)
        signal_line = self._calculate_ema_values(macd_line, signal_period)

        # Calculate histogram
        histogram = [macd - signal for macd, signal in zip(macd_line, signal_line)]

        # Get latest values
        latest_macd = macd_line[-1] if macd_line else 0
        latest_signal = signal_line[-1] if signal_line else 0
        latest_histogram = histogram[-1] if histogram else 0

        return CalculationResult(
            values={
                "macd": float(latest_macd),
                "signal": float(latest_signal),
                "histogram": float(latest_histogram),
                "macd_line": [float(x) for x in macd_line],
                "signal_line": [float(x) for x in signal_line],
                "histogram_series": [float(x) for x in histogram],
            },
            data_points_used=len(prices),
        )

    def _calculate_bollinger_bands(
        self, data: List[MarketData], parameters: Dict[str, Any]
    ) -> CalculationResult:
        """Calculate Bollinger Bands"""
        period = parameters.get("period", 20)
        std_dev_multiplier = parameters.get("std_dev", 2.0)

        prices = [point.close for point in data[-period:]]

        if len(prices) < period:
            raise InsufficientDataError(
                f"Bollinger Bands require at least {period} data points"
            )

        # Calculate SMA (middle band)
        middle_band = sum(prices) / len(prices)

        # Calculate standard deviation
        variance = sum((price - middle_band) ** 2 for price in prices) / len(prices)
        std_dev = math.sqrt(variance)

        # Calculate bands
        upper_band = middle_band + (std_dev * std_dev_multiplier)
        lower_band = middle_band - (std_dev * std_dev_multiplier)

        # Calculate %B (position within bands)
        current_price = float(data[-1].close)
        if upper_band != lower_band:
            percent_b = (current_price - lower_band) / (upper_band - lower_band)
        else:
            percent_b = 0.5

        return CalculationResult(
            values={
                "upper": float(upper_band),
                "middle": float(middle_band),
                "lower": float(lower_band),
                "percent_b": percent_b,
                "bandwidth": (
                    (upper_band - lower_band) / middle_band if middle_band != 0 else 0
                ),
                "std_dev": std_dev,
            },
            data_points_used=len(prices),
        )

    def _calculate_stochastic(
        self, data: List[MarketData], parameters: Dict[str, Any]
    ) -> CalculationResult:
        """Calculate Stochastic Oscillator"""
        k_period = parameters.get("k_period", 14)
        d_period = parameters.get("d_period", 3)

        if len(data) < k_period:
            raise InsufficientDataError(
                f"Stochastic requires at least {k_period} data points"
            )

        # Calculate %K
        k_values = []
        for i in range(k_period - 1, len(data)):
            period_data = data[i - k_period + 1 : i + 1]
            highest_high = max(point.high for point in period_data)
            lowest_low = min(point.low for point in period_data)
            current_close = float(data[i].close)

            if highest_high != lowest_low:
                k_value = (
                    (current_close - lowest_low) / (highest_high - lowest_low)
                ) * 100
            else:
                k_value = 50  # Neutral value when range is zero

            k_values.append(k_value)

        # Calculate %D (SMA of %K)
        d_values = []
        for i in range(d_period - 1, len(k_values)):
            d_value = sum(k_values[i - d_period + 1 : i + 1]) / d_period
            d_values.append(d_value)

        return CalculationResult(
            values={
                "k_percent": k_values[-1] if k_values else 50,
                "d_percent": d_values[-1] if d_values else 50,
                "k_values": k_values,
                "d_values": d_values,
            },
            data_points_used=len(data),
        )

    def _calculate_atr(
        self, data: List[MarketData], parameters: Dict[str, Any]
    ) -> CalculationResult:
        """Calculate Average True Range"""
        period = parameters.get("period", 14)

        if len(data) < period + 1:
            raise InsufficientDataError(
                f"ATR requires at least {period + 1} data points"
            )

        # Calculate True Range for each period
        true_ranges = []
        for i in range(1, len(data)):
            current = data[i]
            previous = data[i - 1]

            tr1 = float(current.high - current.low)
            tr2 = abs(float(current.high - previous.close))
            tr3 = abs(float(current.low - previous.close))

            true_range = max(tr1, tr2, tr3)
            true_ranges.append(true_range)

        # Calculate ATR (SMA of True Ranges)
        atr = sum(true_ranges[-period:]) / period

        return CalculationResult(
            value=Decimal(str(atr)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            data_points_used=len(true_ranges),
        )

    def _calculate_adx(
        self, data: List[MarketData], parameters: Dict[str, Any]
    ) -> CalculationResult:
        """Calculate Average Directional Index"""
        period = parameters.get("period", 14)

        if len(data) < period + 1:
            raise InsufficientDataError(
                f"ADX requires at least {period + 1} data points"
            )

        # Calculate Directional Movement
        dm_plus = []
        dm_minus = []
        tr_values = []

        for i in range(1, len(data)):
            current = data[i]
            previous = data[i - 1]

            # True Range
            tr1 = float(current.high - current.low)
            tr2 = abs(float(current.high - previous.close))
            tr3 = abs(float(current.low - previous.close))
            tr = max(tr1, tr2, tr3)
            tr_values.append(tr)

            # Directional Movement
            move_up = float(current.high - previous.high)
            move_down = float(previous.low - current.low)

            dm_plus_val = move_up if move_up > move_down and move_up > 0 else 0
            dm_minus_val = move_down if move_down > move_up and move_down > 0 else 0

            dm_plus.append(dm_plus_val)
            dm_minus.append(dm_minus_val)

        # Calculate smoothed averages
        avg_dm_plus = sum(dm_plus[-period:]) / period
        avg_dm_minus = sum(dm_minus[-period:]) / period
        avg_tr = sum(tr_values[-period:]) / period

        # Calculate Directional Indicators
        di_plus = (avg_dm_plus / avg_tr) * 100 if avg_tr != 0 else 0
        di_minus = (avg_dm_minus / avg_tr) * 100 if avg_tr != 0 else 0

        # Calculate DX
        dx = (
            (abs(di_plus - di_minus) / (di_plus + di_minus)) * 100
            if (di_plus + di_minus) != 0
            else 0
        )

        # ADX is smoothed DX (typically using Wilder's smoothing)
        adx = dx  # Simplified version

        return CalculationResult(
            value=Decimal(str(adx)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            values={"di_plus": di_plus, "di_minus": di_minus, "dx": dx},
            data_points_used=len(data),
        )

    def _calculate_obv(
        self, data: List[MarketData], parameters: Dict[str, Any]
    ) -> CalculationResult:
        """Calculate On-Balance Volume"""
        if len(data) < 2:
            raise InsufficientDataError("OBV requires at least 2 data points")

        obv_values = [0]  # Start with 0

        for i in range(1, len(data)):
            current = data[i]
            previous = data[i - 1]

            if current.close > previous.close:
                # Price up, add volume
                obv_values.append(obv_values[-1] + current.volume)
            elif current.close < previous.close:
                # Price down, subtract volume
                obv_values.append(obv_values[-1] - current.volume)
            else:
                # Price unchanged, OBV unchanged
                obv_values.append(obv_values[-1])

        return CalculationResult(
            value=Decimal(str(obv_values[-1])),
            values={"obv": obv_values[-1], "obv_values": obv_values},
            data_points_used=len(data),
        )

    def _calculate_vwap(
        self, data: List[MarketData], parameters: Dict[str, Any]
    ) -> CalculationResult:
        """Calculate Volume Weighted Average Price"""
        if len(data) < 1:
            raise InsufficientDataError("VWAP requires at least 1 data point")

        # Calculate typical price * volume for each period
        price_volume_sum = 0
        volume_sum = 0

        for point in data:
            typical_price = (
                float(point.high) + float(point.low) + float(point.close)
            ) / 3
            price_volume_sum += typical_price * point.volume
            volume_sum += point.volume

        if volume_sum == 0:
            vwap = float(data[-1].close)  # Fallback to last close
        else:
            vwap = price_volume_sum / volume_sum

        return CalculationResult(
            value=Decimal(str(vwap)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            values={
                "vwap": vwap,
                "price_volume_sum": price_volume_sum,
                "volume_sum": volume_sum,
            },
            data_points_used=len(data),
        )

    def _calculate_ad_line(
        self, data: List[MarketData], parameters: Dict[str, Any]
    ) -> CalculationResult:
        """Calculate Accumulation/Distribution Line (A/D Line)"""
        if len(data) < 2:
            raise InsufficientDataError("A/D Line requires at least 2 data points")

        ad_values = [0]  # Start with 0

        for i in range(1, len(data)):
            current = data[i]

            # Calculate Money Flow Multiplier
            if current.high == current.low:
                mfm = 0  # Avoid division by zero
            else:
                mfm = (
                    (current.close - current.low) - (current.high - current.close)
                ) / (current.high - current.low)

            # Calculate Money Flow Volume
            mfv = mfm * current.volume

            # Add to A/D Line
            ad_values.append(ad_values[-1] + mfv)

        return CalculationResult(
            value=Decimal(str(ad_values[-1])),
            values={"ad_line": ad_values[-1], "ad_values": ad_values},
            data_points_used=len(data),
        )

    def _calculate_chaikin_mf(
        self, data: List[MarketData], parameters: Dict[str, Any]
    ) -> CalculationResult:
        """Calculate Chaikin Money Flow (CMF)"""
        period = parameters.get("period", 21)

        if len(data) < period:
            raise InsufficientDataError(
                f"Chaikin MF requires at least {period} data points"
            )

        # Get the relevant period data
        period_data = data[-period:]

        # Calculate Money Flow Multiplier and Volume for each period
        mf_volumes = []

        for point in period_data:
            # Money Flow Multiplier
            if point.high == point.low:
                mfm = 0
            else:
                mfm = ((point.close - point.low) - (point.high - point.close)) / (
                    point.high - point.low
                )

            # Money Flow Volume
            mfv = mfm * point.volume
            mf_volumes.append(mfv)

        # Calculate Chaikin Money Flow
        total_mfv = sum(mf_volumes)
        total_volume = sum(point.volume for point in period_data)

        if total_volume == 0:
            chaikin_mf = 0
        else:
            chaikin_mf = total_mfv / total_volume

        return CalculationResult(
            value=Decimal(str(chaikin_mf)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            ),
            values={
                "chaikin_mf": chaikin_mf,
                "total_mfv": total_mfv,
                "total_volume": total_volume,
            },
            data_points_used=len(period_data),
        )

    def _calculate_pivot_points(
        self, data: List[MarketData], parameters: Dict[str, Any]
    ) -> CalculationResult:
        """Calculate Pivot Points"""
        if not data:
            raise InsufficientDataError("No data for pivot points calculation")

        # Use the most recent complete period (typically daily)
        reference_point = data[-1]

        high = float(reference_point.high)
        low = float(reference_point.low)
        close = float(reference_point.close)

        # Calculate pivot point
        pivot = (high + low + close) / 3

        # Calculate support and resistance levels
        r1 = (2 * pivot) - low
        s1 = (2 * pivot) - high
        r2 = pivot + (high - low)
        s2 = pivot - (high - low)
        r3 = high + 2 * (pivot - low)
        s3 = low - 2 * (high - pivot)

        return CalculationResult(
            values={
                "pivot": pivot,
                "r1": r1,
                "r2": r2,
                "r3": r3,
                "s1": s1,
                "s2": s2,
                "s3": s3,
            },
            data_points_used=1,
        )

    def _calculate_fibonacci_retracement(
        self, data: List[MarketData], parameters: Dict[str, Any]
    ) -> CalculationResult:
        """Calculate Fibonacci Retracement levels"""
        if len(data) < 2:
            raise InsufficientDataError(
                "Fibonacci Retracement requires at least 2 data points"
            )

        # Find the swing high and low (simplified - uses recent high/low)
        period = parameters.get("period", 20)
        period_data = data[-min(period, len(data)) :]

        swing_high = max(point.high for point in period_data)
        swing_low = min(point.low for point in period_data)

        # Calculate price range
        price_range = float(swing_high - swing_low)

        if price_range == 0:
            # No range, return neutral levels
            current_price = float(data[-1].close)
            return CalculationResult(
                values={
                    "swing_high": float(swing_high),
                    "swing_low": float(swing_low),
                    "fib_0.0": current_price,
                    "fib_0.236": current_price,
                    "fib_0.382": current_price,
                    "fib_0.5": current_price,
                    "fib_0.618": current_price,
                    "fib_0.786": current_price,
                    "fib_1.0": current_price,
                },
                data_points_used=len(period_data),
            )

        # Calculate Fibonacci retracement levels
        # Standard Fibonacci ratios: 0.236, 0.382, 0.5, 0.618, 0.786
        fib_levels = {
            "fib_0.0": float(swing_low),  # 0% retracement
            "fib_0.236": float(swing_low + (price_range * 0.236)),  # 23.6%
            "fib_0.382": float(swing_low + (price_range * 0.382)),  # 38.2%
            "fib_0.5": float(swing_low + (price_range * 0.5)),  # 50%
            "fib_0.618": float(swing_low + (price_range * 0.618)),  # 61.8%
            "fib_0.786": float(swing_low + (price_range * 0.786)),  # 78.6%
            "fib_1.0": float(swing_high),  # 100% retracement (swing high)
        }

        return CalculationResult(
            values={
                "swing_high": float(swing_high),
                "swing_low": float(swing_low),
                "price_range": price_range,
                **fib_levels,
            },
            data_points_used=len(period_data),
        )

    def _calculate_predator_signal(
        self, data: List[MarketData], parameters: Dict[str, Any]
    ) -> CalculationResult:
        """Calculate NIRAJ Predator Signal"""
        lookback_period = parameters.get("lookback_period", 20)

        if len(data) < lookback_period:
            raise InsufficientDataError(
                f"Predator signal requires at least {lookback_period} data points"
            )

        recent_data = data[-lookback_period:]

        # Calculate price momentum
        prices = [float(point.close) for point in recent_data]
        price_momentum = self._calculate_price_momentum(prices)

        # Calculate volume strength
        volumes = [point.volume for point in recent_data]
        volume_strength = self._calculate_volume_strength(volumes)

        # Calculate volatility factor
        volatility_factor = self._calculate_volatility_factor(prices)

        # Calculate market microstructure factors
        spread_factor = self._calculate_spread_factor(recent_data)
        order_flow = self._calculate_order_flow(recent_data)

        # Combine factors into predator score
        predator_score = (
            (price_momentum * 0.25)
            + (volume_strength * 0.25)
            + (volatility_factor * 0.20)
            + (spread_factor * 0.15)
            + (order_flow * 0.15)
        )

        # Normalize to 0-100 scale
        predator_score = max(0, min(100, predator_score))

        # Determine signal strength
        if predator_score >= 80:
            signal_strength = "STRONG_BUY"
        elif predator_score >= 65:
            signal_strength = "BUY"
        elif predator_score >= 35:
            signal_strength = "NEUTRAL"
        elif predator_score >= 20:
            signal_strength = "SELL"
        else:
            signal_strength = "STRONG_SELL"

        return CalculationResult(
            value=Decimal(str(predator_score)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            ),
            values={
                "predator_score": predator_score,
                "signal_strength": signal_strength,
                "price_momentum": price_momentum,
                "volume_strength": volume_strength,
                "volatility_factor": volatility_factor,
                "spread_factor": spread_factor,
                "order_flow": order_flow,
            },
            data_points_used=len(recent_data),
        )

    def _calculate_bank_nifty_divergence(
        self, data: List[MarketData], parameters: Dict[str, Any]
    ) -> CalculationResult:
        """Calculate Bank Nifty Divergence"""
        # This would require Bank Nifty data comparison
        # Simplified implementation for now
        divergence_score = 50  # Neutral

        return CalculationResult(
            value=Decimal(str(divergence_score)),
            values={"divergence_score": divergence_score, "divergence_type": "neutral"},
            data_points_used=len(data),
        )

    def _calculate_fear_greed_index(
        self, data: List[MarketData], parameters: Dict[str, Any]
    ) -> CalculationResult:
        """Calculate Fear & Greed Index"""
        sentiment_weight = parameters.get("sentiment_weight", 0.4)
        volume_weight = parameters.get("volume_weight", 0.6)

        if len(data) < 5:
            raise InsufficientDataError(
                "Fear & Greed Index requires at least 5 data points"
            )

        # Calculate volatility component (simplified)
        prices = [float(point.close) for point in data[-5:]]
        volatility = statistics.stdev(prices) / statistics.mean(prices) if prices else 0
        volatility_score = min(100, volatility * 1000)  # Scale appropriately

        # Calculate volume component
        volume_score = 50  # Neutral for now (would need market comparison)

        # Combine components
        fear_greed_score = ((100 - volatility_score) * sentiment_weight) + (
            volume_score * volume_weight
        )

        return CalculationResult(
            value=Decimal(str(fear_greed_score)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            ),
            values={
                "fear_greed_score": fear_greed_score,
                "volatility_component": volatility_score,
                "volume_component": volume_score,
            },
            data_points_used=len(data),
        )

    def _calculate_market_sentiment(
        self, data: List[MarketData], parameters: Dict[str, Any]
    ) -> CalculationResult:
        """Calculate Market Sentiment"""
        if len(data) < 5:
            raise InsufficientDataError(
                "Market sentiment requires at least 5 data points"
            )

        # Calculate recent price trend
        recent_prices = [float(point.close) for point in data[-5:]]
        price_trend = (recent_prices[-1] - recent_prices[0]) / recent_prices[0] * 100

        # Calculate volume trend
        recent_volumes = [point.volume for point in data[-5:]]
        volume_trend = (
            (statistics.mean(recent_volumes[-3:]) - statistics.mean(recent_volumes[:2]))
            / statistics.mean(recent_volumes[:2])
            * 100
        )

        # Combine factors for sentiment score (0-100)
        sentiment_score = 50 + (price_trend * 0.4) + (volume_trend * 0.6)
        sentiment_score = max(0, min(100, sentiment_score))

        # Determine sentiment trend
        if sentiment_score >= 70:
            trend = "bullish"
        elif sentiment_score <= 30:
            trend = "bearish"
        else:
            trend = "neutral"

        return CalculationResult(
            value=Decimal(str(sentiment_score)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            ),
            values={
                "sentiment_score": sentiment_score,
                "sentiment_trend": trend,
                "price_trend": price_trend,
                "volume_trend": volume_trend,
            },
            data_points_used=len(data),
        )

    def _calculate_williams_r(
        self, data: List[MarketData], parameters: Dict[str, Any]
    ) -> CalculationResult:
        """Calculate Williams %R"""
        period = parameters.get("period", 14)

        if len(data) < period:
            raise InsufficientDataError(
                f"Williams %R requires at least {period} data points"
            )

        # Get the relevant period data
        period_data = data[-period:]

        # Find highest high and lowest low in the period
        highest_high = max(point.high for point in period_data)
        lowest_low = min(point.low for point in period_data)
        current_close = float(data[-1].close)

        # Calculate Williams %R
        if highest_high == lowest_low:
            williams_r = -50  # Neutral value when range is zero
        else:
            williams_r = (
                (highest_high - current_close) / (highest_high - lowest_low)
            ) * -100

        return CalculationResult(
            value=Decimal(str(williams_r)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            ),
            data_points_used=len(period_data),
        )

    def _calculate_roc(
        self, data: List[MarketData], parameters: Dict[str, Any]
    ) -> CalculationResult:
        """Calculate Rate of Change (ROC)"""
        period = parameters.get("period", 12)

        if len(data) < period + 1:
            raise InsufficientDataError(
                f"ROC requires at least {period + 1} data points"
            )

        # Calculate ROC: ((current - previous) / previous) * 100
        current_price = float(data[-1].close)
        previous_price = float(data[-(period + 1)].close)

        if previous_price == 0:
            roc = 0.0
        else:
            roc = ((current_price - previous_price) / previous_price) * 100

        return CalculationResult(
            value=Decimal(str(roc)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            data_points_used=period + 1,
        )

    def _calculate_mfi(
        self, data: List[MarketData], parameters: Dict[str, Any]
    ) -> CalculationResult:
        """Calculate Money Flow Index (MFI)"""
        period = parameters.get("period", 14)

        if len(data) < period + 1:
            raise InsufficientDataError(
                f"MFI requires at least {period + 1} data points"
            )

        # Calculate typical prices and raw money flow
        typical_prices = []
        money_flows = []

        for point in data[-(period + 1) :]:  # Include one extra for comparison
            typical_price = (
                float(point.high) + float(point.low) + float(point.close)
            ) / 3
            typical_prices.append(typical_price)
            money_flows.append(typical_price * point.volume)

        # Calculate positive and negative money flow
        positive_flow = 0
        negative_flow = 0

        for i in range(1, len(typical_prices)):
            if typical_prices[i] > typical_prices[i - 1]:
                positive_flow += money_flows[i]
            elif typical_prices[i] < typical_prices[i - 1]:
                negative_flow += money_flows[i]
            # If equal, no change

        # Calculate money flow ratio
        if negative_flow == 0:
            mfi = 100.0
        else:
            money_flow_ratio = positive_flow / negative_flow
            mfi = 100 - (100 / (1 + money_flow_ratio))

        return CalculationResult(
            value=Decimal(str(mfi)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            data_points_used=len(typical_prices),
        )

    def _calculate_keltner_channel(
        self, data: List[MarketData], parameters: Dict[str, Any]
    ) -> CalculationResult:
        """Calculate Keltner Channel"""
        period = parameters.get("period", 20)
        atr_period = parameters.get("atr_period", 10)
        multiplier = parameters.get("multiplier", 2.0)

        if len(data) < max(period, atr_period) + 1:
            raise InsufficientDataError(
                f"Keltner Channel requires at least {max(period, atr_period) + 1} data points"
            )

        # Calculate EMA of typical price (middle line)
        typical_prices = [
            (float(point.high) + float(point.low) + float(point.close)) / 3
            for point in data
        ]
        middle_line = self._calculate_ema_values(typical_prices, period)

        if not middle_line:
            raise InsufficientDataError("Could not calculate EMA for Keltner Channel")

        # Calculate ATR
        atr_values = []
        for i in range(1, len(data)):
            current = data[i]
            previous = data[i - 1]

            tr1 = float(current.high - current.low)
            tr2 = abs(float(current.high - previous.close))
            tr3 = abs(float(current.low - previous.close))

            true_range = max(tr1, tr2, tr3)
            atr_values.append(true_range)

        # Calculate ATR using EMA
        atr_ema = self._calculate_ema_values(atr_values, atr_period)

        if not atr_ema:
            raise InsufficientDataError("Could not calculate ATR for Keltner Channel")

        # Get latest values
        latest_middle = middle_line[-1]
        latest_atr = atr_ema[-1]

        upper_band = latest_middle + (latest_atr * multiplier)
        lower_band = latest_middle - (latest_atr * multiplier)

        return CalculationResult(
            values={
                "upper": float(upper_band),
                "middle": float(latest_middle),
                "lower": float(lower_band),
                "atr": float(latest_atr),
            },
            data_points_used=len(data),
        )

    def _calculate_donchian_channel(
        self, data: List[MarketData], parameters: Dict[str, Any]
    ) -> CalculationResult:
        """Calculate Donchian Channel"""
        period = parameters.get("period", 20)

        if len(data) < period:
            raise InsufficientDataError(
                f"Donchian Channel requires at least {period} data points"
            )

        # Get the relevant period data
        period_data = data[-period:]

        # Calculate highest high and lowest low
        highest_high = max(point.high for point in period_data)
        lowest_low = min(point.low for point in period_data)

        # Calculate middle line (average of high and low)
        middle_line = (float(highest_high) + float(lowest_low)) / 2

        return CalculationResult(
            values={
                "upper": float(highest_high),
                "middle": float(middle_line),
                "lower": float(lowest_low),
            },
            data_points_used=len(period_data),
        )

    # Helper methods
    def _calculate_ema_values(self, values: List[float], period: int) -> List[float]:
        """Calculate EMA values for a list"""
        if len(values) < period:
            return []

        multiplier = 2 / (period + 1)
        ema_values = [values[0]]  # First EMA is the first value

        for value in values[1:]:
            ema = (value * multiplier) + (ema_values[-1] * (1 - multiplier))
            ema_values.append(ema)

        return ema_values

    def _calculate_price_momentum(self, prices: List[float]) -> float:
        """Calculate price momentum factor"""
        if len(prices) < 5:
            return 0.0

        # Calculate short-term and long-term momentum
        short_term = (
            (prices[-1] - prices[-2]) / prices[-2] * 100 if len(prices) >= 2 else 0
        )
        long_term = (prices[-1] - prices[0]) / prices[0] * 100 if prices[0] != 0 else 0

        momentum = (short_term * 0.7) + (long_term * 0.3)
        return max(-100, min(100, momentum))

    def _calculate_volume_strength(self, volumes: List[int]) -> float:
        """Calculate volume strength factor"""
        if len(volumes) < 5:
            return 0.0

        recent_avg = statistics.mean(volumes[-3:]) if len(volumes) >= 3 else volumes[-1]
        overall_avg = statistics.mean(volumes)

        if overall_avg == 0:
            return 0.0

        strength = ((recent_avg - overall_avg) / overall_avg) * 100
        return max(-100, min(100, strength))

    def _calculate_volatility_factor(self, prices: List[float]) -> float:
        """Calculate volatility factor"""
        if len(prices) < 5:
            return 0.0

        try:
            returns = [
                ((prices[i] - prices[i - 1]) / prices[i - 1]) * 100
                for i in range(1, len(prices))
            ]
            volatility = statistics.stdev(returns)
            return min(100, volatility * 10)  # Scale appropriately
        except statistics.StatisticsError:
            return 0.0

    def _calculate_spread_factor(self, data: List[MarketData]) -> float:
        """Calculate spread factor (bid-ask spread proxy)"""
        if len(data) < 5:
            return 0.0

        # Use high-low range as spread proxy
        spreads = [
            (float(point.high - point.low) / float(point.close)) * 100
            for point in data[-5:]
        ]
        avg_spread = statistics.mean(spreads) if spreads else 0

        # Lower spread = higher factor (more liquid)
        spread_factor = max(0, 100 - avg_spread * 100)
        return spread_factor

    def _calculate_order_flow(self, data: List[MarketData]) -> float:
        """Calculate order flow factor"""
        if len(data) < 5:
            return 0.0

        # Simplified order flow based on price and volume changes
        bullish_signals = 0
        bearish_signals = 0

        for i in range(1, len(data)):
            current = data[i]
            previous = data[i - 1]

            if current.close > previous.close and current.volume > previous.volume:
                bullish_signals += 1
            elif current.close < previous.close and current.volume > previous.volume:
                bearish_signals += 1

        total_signals = bullish_signals + bearish_signals
        if total_signals == 0:
            return 50.0

        order_flow = ((bullish_signals - bearish_signals) / total_signals) * 50 + 50
        return max(0, min(100, order_flow))

    def _calculate_confidence_score(
        self,
        data: List[MarketData],
        indicator_type: IndicatorType,
        result: CalculationResult,
    ) -> Decimal:
        """Calculate confidence score for the result"""
        base_score = Decimal("80")

        # Adjust based on data quantity
        if result.data_points_used < 10:
            base_score -= Decimal("20")
        elif result.data_points_used < 20:
            base_score -= Decimal("10")

        # Adjust based on data quality (price consistency)
        prices = [float(point.close) for point in data[-min(20, len(data)) :]]
        if len(prices) >= 5:
            try:
                cv = statistics.stdev(prices) / statistics.mean(
                    prices
                )  # Coefficient of variation
                if cv > 0.1:  # High volatility reduces confidence
                    base_score -= Decimal("10")
            except (statistics.StatisticsError, ZeroDivisionError):
                base_score -= Decimal("15")

        # Adjust based on calculation time (faster = more confidence)
        if result.calculation_time_ms > 100:
            base_score -= Decimal("5")

        return max(Decimal("0"), min(Decimal("100"), base_score))

    def _get_cache_key(
        self,
        indicator_type: IndicatorType,
        data: List[MarketData],
        parameters: Dict[str, Any],
        symbol: str,
    ) -> str:
        """Generate cache key"""
        # Create a hash of the key components
        data_hash = hash(
            tuple(
                (point.timestamp.isoformat(), float(point.close), point.volume)
                for point in data[-20:]
            )
        )
        param_hash = hash(frozenset(parameters.items()) if parameters else frozenset())
        return f"{symbol}:{indicator_type.value}:{data_hash}:{param_hash}"

    def _cleanup_cache(self) -> None:
        """Clean up old cache entries"""
        if len(self._cache) > self.max_cache_size:
            # Remove oldest entries
            sorted_entries = sorted(self._cache.items(), key=lambda x: x[1][1])
            entries_to_remove = len(self._cache) - self.max_cache_size

            for key, _ in sorted_entries[:entries_to_remove]:
                del self._cache[key]

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = (
            (self._cache_hits / total_requests * 100) if total_requests > 0 else 0
        )

        return {
            "cache_size": len(self._cache),
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_rate_percent": hit_rate,
            "max_cache_size": self.max_cache_size,
        }

    def clear_cache(self) -> None:
        """Clear the calculation cache"""
        self._cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0


# Factory function for creating calculator instances
def create_calculator(
    cache_enabled: bool = True, max_cache_size: int = 1000
) -> TechnicalIndicatorsCalculator:
    """
    Create a technical indicators calculator instance

    Args:
        cache_enabled: Whether to enable caching
        max_cache_size: Maximum cache size

    Returns:
        TechnicalIndicatorsCalculator: Calculator instance
    """
    return TechnicalIndicatorsCalculator(
        cache_enabled=cache_enabled, max_cache_size=max_cache_size
    )


# Utility functions for batch calculations
def calculate_multiple_indicators(
    calculator: TechnicalIndicatorsCalculator,
    indicators: List[Tuple[IndicatorType, Dict[str, Any]]],
    data: List[MarketData],
    symbol: str = "",
) -> Dict[IndicatorType, CalculationResult]:
    """
    Calculate multiple indicators efficiently

    Args:
        calculator: Calculator instance
        indicators: List of (indicator_type, parameters) tuples
        data: Market data
        symbol: Symbol for caching

    Returns:
        Dict[IndicatorType, CalculationResult]: Results for each indicator
    """
    results = {}

    for indicator_type, parameters in indicators:
        try:
            result = calculator.calculate_indicator(
                indicator_type, data, parameters, symbol
            )
            results[indicator_type] = result
        except CalculationError as e:
            logger.warning(f"Failed to calculate {indicator_type.value}: {e.message}")
            # Create error result
            results[indicator_type] = CalculationResult(
                confidence_score=Decimal("0"), metadata={"error": e.message}
            )

    return results


def validate_indicator_parameters(
    indicator_type: IndicatorType, parameters: Dict[str, Any]
) -> List[str]:
    """
    Validate parameters for an indicator type

    Args:
        indicator_type: Type of indicator
        parameters: Parameters to validate

    Returns:
        List[str]: List of validation errors
    """
    errors = []

    try:
        if indicator_type in [IndicatorType.SMA, IndicatorType.EMA]:
            period = parameters.get("period")
            if not period or not isinstance(period, int) or period < 1 or period > 200:
                errors.append("Period must be integer between 1-200")

        elif indicator_type == IndicatorType.RSI:
            period = parameters.get("period", 14)
            if not isinstance(period, int) or period < 2 or period > 50:
                errors.append("RSI period must be integer between 2-50")

        elif indicator_type == IndicatorType.BOLLINGER_BANDS:
            period = parameters.get("period", 20)
            std_dev = parameters.get("std_dev", 2)
            if not isinstance(period, int) or period < 5 or period > 100:
                errors.append("Bollinger period must be integer between 5-100")
            if not isinstance(std_dev, (int, float)) or std_dev < 0.5 or std_dev > 5:
                errors.append("Bollinger std_dev must be between 0.5-5")

        elif indicator_type == IndicatorType.MACD:
            fast = parameters.get("fast_period", 12)
            slow = parameters.get("slow_period", 26)
            signal = parameters.get("signal_period", 9)
            if not all(isinstance(p, int) for p in [fast, slow, signal]):
                errors.append("MACD periods must be integers")
            elif fast >= slow:
                errors.append("MACD fast period must be less than slow period")
            elif signal < 1:
                errors.append("MACD signal period must be positive")

        elif indicator_type == IndicatorType.STOCHASTIC:
            k_period = parameters.get("k_period", 14)
            d_period = parameters.get("d_period", 3)
            if not isinstance(k_period, int) or k_period < 5 or k_period > 50:
                errors.append("Stochastic K period must be integer between 5-50")
            if not isinstance(d_period, int) or d_period < 2 or d_period > 10:
                errors.append("Stochastic D period must be integer between 2-10")

        elif indicator_type == IndicatorType.ATR:
            period = parameters.get("period", 14)
            if not isinstance(period, int) or period < 2 or period > 50:
                errors.append("ATR period must be integer between 2-50")

        elif indicator_type == IndicatorType.ADX:
            period = parameters.get("period", 14)
            if not isinstance(period, int) or period < 2 or period > 50:
                errors.append("ADX period must be integer between 2-50")

    except Exception as e:
        errors.append(f"Parameter validation error: {str(e)}")

    return errors
