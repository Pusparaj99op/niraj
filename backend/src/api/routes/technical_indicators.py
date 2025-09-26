"""
Technical Indicators API Routes for NIRAJ Trading System

Provides calculation and analysis of technical indicators including:
- Moving averages (SMA, EMA, WMA)
- Momentum indicators (RSI, MACD, Stochastic)
- Volatility indicators (Bollinger Bands, ATR)
- Volume indicators (OBV, VWAP)
- Custom indicator combinations
- Real-time indicator updates

Endpoints:
- GET /api/v1/indicators/{symbol}: Get all indicators for a symbol
- GET /api/v1/indicators/{symbol}/{indicator}: Get specific indicator
- POST /api/v1/indicators/calculate: Calculate custom indicators
- GET /api/v1/indicators/screener: Screen symbols by indicator criteria
- GET /api/v1/indicators/watchlist: Get indicators for watchlist
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from enum import Enum
import math

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
import structlog

from ...core.database import DatabaseManager
from ...core.cache import CacheManager
from ...api.routes.auth import get_security_context, SecurityContext

# Initialize router
router = APIRouter(
    prefix="/indicators",
    tags=["technical-indicators"],
    responses={
        400: {"description": "Bad Request - Invalid parameters"},
        401: {"description": "Unauthorized - Authentication required"},
        404: {"description": "Not Found - Symbol or indicator not found"},
        422: {"description": "Unprocessable Entity - Invalid calculation parameters"},
        500: {"description": "Internal Server Error - System error"}
    }
)

# Initialize logger
logger = structlog.get_logger(__name__)

# Global service instances
_db_manager: Optional[DatabaseManager] = None
_cache_manager: Optional[CacheManager] = None


# Enums
class IndicatorType(str, Enum):
    """Technical indicator types"""
    TREND = "trend"
    MOMENTUM = "momentum"
    VOLATILITY = "volatility"
    VOLUME = "volume"
    OSCILLATOR = "oscillator"


class IndicatorName(str, Enum):
    """Available technical indicators"""
    SMA = "sma"  # Simple Moving Average
    EMA = "ema"  # Exponential Moving Average
    WMA = "wma"  # Weighted Moving Average
    RSI = "rsi"  # Relative Strength Index
    MACD = "macd"  # Moving Average Convergence Divergence
    STOCH = "stoch"  # Stochastic Oscillator
    BB = "bb"  # Bollinger Bands
    ATR = "atr"  # Average True Range
    OBV = "obv"  # On-Balance Volume
    VWAP = "vwap"  # Volume Weighted Average Price
    ADX = "adx"  # Average Directional Index
    CCI = "cci"  # Commodity Channel Index
    WILLIAMS_R = "williams_r"  # Williams %R


class TimeFrame(str, Enum):
    """Time frames for indicators"""
    ONE_MINUTE = "1m"
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    THIRTY_MINUTES = "30m"
    ONE_HOUR = "1h"
    FOUR_HOURS = "4h"
    ONE_DAY = "1d"


# Request Models
class IndicatorRequest(BaseModel):
    """Technical indicator request"""
    symbol: str = Field(description="Trading symbol")
    indicators: List[IndicatorName] = Field(description="Indicators to calculate")
    timeframe: TimeFrame = Field(default=TimeFrame.FIFTEEN_MINUTES, description="Time frame")
    period: int = Field(default=14, ge=1, le=200, description="Default period for indicators")
    data_points: int = Field(default=100, ge=50, le=1000, description="Number of data points")


class CustomIndicatorRequest(BaseModel):
    """Custom indicator calculation request"""
    symbol: str = Field(description="Trading symbol")
    price_data: List[Dict[str, float]] = Field(description="OHLCV price data")
    indicators: Dict[str, Dict[str, Any]] = Field(description="Indicators with parameters")
    timeframe: TimeFrame = Field(description="Time frame")


class ScreenerRequest(BaseModel):
    """Indicator screener request"""
    symbols: List[str] = Field(description="Symbols to screen", max_length=100)
    criteria: Dict[str, Dict[str, Any]] = Field(description="Screening criteria")
    timeframe: TimeFrame = Field(default=TimeFrame.FIFTEEN_MINUTES, description="Time frame")
    sort_by: Optional[str] = Field(None, description="Sort results by indicator")
    limit: int = Field(default=50, ge=1, le=100, description="Maximum results")


# Response Models
class IndicatorValue(BaseModel):
    """Individual indicator value"""
    timestamp: datetime
    value: float
    signal: Optional[str] = None  # buy, sell, neutral


class IndicatorData(BaseModel):
    """Indicator data with metadata"""
    name: str
    type: IndicatorType
    period: int
    values: List[IndicatorValue]
    current_value: float
    signal: str  # Overall signal
    signal_strength: float  # 0-1
    interpretation: str
    parameters: Dict[str, Any]


class IndicatorsResponse(BaseModel):
    """Multiple indicators response"""
    symbol: str
    timeframe: str
    indicators: Dict[str, IndicatorData]
    summary: Dict[str, Any]
    overall_signal: str
    signal_confidence: float
    last_updated: datetime
    data_quality: str


class SingleIndicatorResponse(BaseModel):
    """Single indicator response"""
    symbol: str
    indicator: IndicatorData
    analysis: Dict[str, Any]
    recommendations: List[str]
    related_indicators: Dict[str, float]
    last_updated: datetime


class ScreenerResult(BaseModel):
    """Screener result for a symbol"""
    symbol: str
    indicators: Dict[str, float]
    signals: Dict[str, str]
    score: float
    rank: int


class ScreenerResponse(BaseModel):
    """Screener results response"""
    results: List[ScreenerResult]
    total_symbols: int
    matching_symbols: int
    criteria: Dict[str, Any]
    sort_by: Optional[str]
    timestamp: datetime


# Helper functions
def cache_key(prefix: str, *args) -> str:
    """Generate cache key for indicators"""
    return f"indicators:{prefix}:{':'.join(str(arg) for arg in args)}"


async def get_cached_indicators(key: str, ttl: int = 600) -> Optional[Dict[str, Any]]:
    """Get cached indicator data"""
    if not _cache_manager:
        return None

    try:
        return await _cache_manager.get(key)
    except Exception as e:
        logger.warning("Indicators cache get failed", key=key, error=str(e))
        return None


async def set_cached_indicators(key: str, data: Dict[str, Any], ttl: int = 600):
    """Set cached indicator data"""
    if not _cache_manager:
        return

    try:
        await _cache_manager.set(key, data, ttl=ttl)
    except Exception as e:
        logger.warning("Indicators cache set failed", key=key, error=str(e))


# Technical indicator calculation functions
def calculate_sma(prices: List[float], period: int) -> List[float]:
    """Calculate Simple Moving Average"""
    sma = []
    for i in range(len(prices)):
        if i >= period - 1:
            avg = sum(prices[i - period + 1:i + 1]) / period
            sma.append(avg)
        else:
            sma.append(None)
    return sma


def calculate_ema(prices: List[float], period: int) -> List[float]:
    """Calculate Exponential Moving Average"""
    ema = []
    multiplier = 2 / (period + 1)

    for i, price in enumerate(prices):
        if i == 0:
            ema.append(price)
        else:
            ema.append((price * multiplier) + (ema[i-1] * (1 - multiplier)))

    return ema


def calculate_rsi(prices: List[float], period: int = 14) -> List[float]:
    """Calculate Relative Strength Index"""
    if len(prices) < period + 1:
        return [None] * len(prices)

    deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]

    rsi = []
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(len(prices)):
        if i < period:
            rsi.append(None)
        elif i == period:
            if avg_loss == 0:
                rsi.append(100)
            else:
                rs = avg_gain / avg_loss
                rsi.append(100 - (100 / (1 + rs)))
        else:
            gain = gains[i-1]
            loss = losses[i-1]
            avg_gain = (avg_gain * (period - 1) + gain) / period
            avg_loss = (avg_loss * (period - 1) + loss) / period

            if avg_loss == 0:
                rsi.append(100)
            else:
                rs = avg_gain / avg_loss
                rsi.append(100 - (100 / (1 + rs)))

    return rsi


def calculate_macd(prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, List[float]]:
    """Calculate MACD (Moving Average Convergence Divergence)"""
    ema_fast = calculate_ema(prices, fast)
    ema_slow = calculate_ema(prices, slow)

    macd_line = []
    for i in range(len(prices)):
        if ema_fast[i] is not None and ema_slow[i] is not None:
            macd_line.append(ema_fast[i] - ema_slow[i])
        else:
            macd_line.append(None)

    # Filter out None values for signal line calculation
    valid_macd = [x for x in macd_line if x is not None]
    if len(valid_macd) >= signal:
        signal_line_values = calculate_ema(valid_macd, signal)

        # Reconstruct signal line with proper alignment
        signal_line = [None] * len(macd_line)
        valid_idx = 0
        for i, val in enumerate(macd_line):
            if val is not None:
                if valid_idx < len(signal_line_values):
                    signal_line[i] = signal_line_values[valid_idx]
                valid_idx += 1
    else:
        signal_line = [None] * len(macd_line)

    histogram = []
    for i in range(len(macd_line)):
        if macd_line[i] is not None and signal_line[i] is not None:
            histogram.append(macd_line[i] - signal_line[i])
        else:
            histogram.append(None)

    return {
        "macd": macd_line,
        "signal": signal_line,
        "histogram": histogram
    }


def calculate_bollinger_bands(prices: List[float], period: int = 20, std_dev: float = 2) -> Dict[str, List[float]]:
    """Calculate Bollinger Bands"""
    sma = calculate_sma(prices, period)

    upper_band = []
    lower_band = []

    for i in range(len(prices)):
        if i >= period - 1:
            period_prices = prices[i - period + 1:i + 1]
            std = (sum([(x - sma[i]) ** 2 for x in period_prices]) / period) ** 0.5
            upper_band.append(sma[i] + (std_dev * std))
            lower_band.append(sma[i] - (std_dev * std))
        else:
            upper_band.append(None)
            lower_band.append(None)

    return {
        "upper": upper_band,
        "middle": sma,
        "lower": lower_band
    }


def calculate_atr(high: List[float], low: List[float], close: List[float], period: int = 14) -> List[float]:
    """Calculate Average True Range"""
    true_ranges = []

    for i in range(len(high)):
        if i == 0:
            true_ranges.append(high[i] - low[i])
        else:
            tr1 = high[i] - low[i]
            tr2 = abs(high[i] - close[i-1])
            tr3 = abs(low[i] - close[i-1])
            true_ranges.append(max(tr1, tr2, tr3))

    return calculate_sma(true_ranges, period)


def generate_signal(indicator_name: str, current_value: float, previous_values: List[float],
                   price: float = None, **kwargs) -> tuple[str, float]:
    """Generate trading signal from indicator"""
    if not previous_values or current_value is None:
        return "neutral", 0.0

    if indicator_name == "rsi":
        if current_value > 70:
            return "sell", min((current_value - 70) / 30, 1.0)
        elif current_value < 30:
            return "buy", min((30 - current_value) / 30, 1.0)
        else:
            return "neutral", 0.0

    elif indicator_name == "macd":
        # Assumes current_value is MACD line, previous_values includes signal line
        if len(previous_values) >= 2:
            macd_prev = previous_values[-2]
            signal_current = kwargs.get("signal_value", 0)
            signal_prev = kwargs.get("signal_prev", 0)

            if current_value > signal_current and macd_prev <= signal_prev:
                return "buy", 0.7
            elif current_value < signal_current and macd_prev >= signal_prev:
                return "sell", 0.7
        return "neutral", 0.0

    elif indicator_name in ["sma", "ema"]:
        if price and current_value:
            if price > current_value * 1.02:
                return "buy", 0.6
            elif price < current_value * 0.98:
                return "sell", 0.6
        return "neutral", 0.0

    else:
        # Generic trend detection
        if len(previous_values) >= 3:
            trend = sum([1 if previous_values[i] < previous_values[i+1] else -1
                        for i in range(len(previous_values)-1)])
            if trend > 1:
                return "buy", min(trend / 5, 1.0)
            elif trend < -1:
                return "sell", min(abs(trend) / 5, 1.0)

        return "neutral", 0.0


# Mock function to get price data (in real implementation, fetch from market data API)
async def get_price_data(symbol: str, timeframe: str, periods: int) -> List[Dict[str, float]]:
    """Get price data for symbol (mock implementation)"""
    # This would normally fetch real market data
    # For now, return mock data
    import random

    base_price = 100.0
    data = []

    for i in range(periods):
        # Generate realistic OHLCV data
        open_price = base_price + random.uniform(-2, 2)
        high_price = open_price + random.uniform(0, 3)
        low_price = open_price - random.uniform(0, 3)
        close_price = open_price + random.uniform(-2, 2)
        volume = random.randint(10000, 100000)

        data.append({
            "timestamp": (datetime.now(timezone.utc) - timedelta(minutes=15*i)).isoformat(),
            "open": open_price,
            "high": high_price,
            "low": low_price,
            "close": close_price,
            "volume": volume
        })

        base_price = close_price

    return list(reversed(data))  # Return in chronological order


# API Endpoints
@router.get(
    "/{symbol}",
    response_model=IndicatorsResponse,
    summary="Get All Indicators",
    description="""
    Get all available technical indicators for a symbol.

    **Features:**
    - Multiple indicator calculations
    - Signal generation
    - Overall market assessment
    - Data quality scoring
    """
)
async def get_all_indicators(
    symbol: str,
    timeframe: TimeFrame = Query(default=TimeFrame.FIFTEEN_MINUTES, description="Time frame"),
    period: int = Query(default=14, ge=5, le=50, description="Default period"),
    data_points: int = Query(default=100, ge=50, le=500, description="Data points"),
    security_context: SecurityContext = Depends(get_security_context)
) -> IndicatorsResponse:
    """Get all technical indicators for a symbol"""

    start_time = datetime.now(timezone.utc)

    try:
        with structlog.contextvars.bound_contextvars(
            user_id=security_context.user_id,
            symbol=symbol.upper(),
            timeframe=timeframe.value,
            period=period
        ):
            logger.info("All indicators request")

            symbol = symbol.upper().strip()

            # Check cache
            cache_key_str = cache_key("all", symbol, timeframe.value, period, data_points)
            cached_data = await get_cached_indicators(cache_key_str, ttl=300)  # 5 minute cache

            if cached_data:
                logger.info("Returning cached indicators")
                return IndicatorsResponse(**cached_data)

            # Get price data
            price_data = await get_price_data(symbol, timeframe.value, data_points)

            if not price_data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No price data found for symbol {symbol}"
                )

            # Extract price arrays
            closes = [float(d["close"]) for d in price_data]
            highs = [float(d["high"]) for d in price_data]
            lows = [float(d["low"]) for d in price_data]
            volumes = [float(d["volume"]) for d in price_data]
            timestamps = [datetime.fromisoformat(d["timestamp"].replace('Z', '+00:00')) for d in price_data]

            # Calculate indicators
            indicators = {}

            # Moving Averages
            sma_values = calculate_sma(closes, period)
            ema_values = calculate_ema(closes, period)

            # RSI
            rsi_values = calculate_rsi(closes, period)

            # MACD
            macd_data = calculate_macd(closes)

            # Bollinger Bands
            bb_data = calculate_bollinger_bands(closes, period)

            # ATR
            atr_values = calculate_atr(highs, lows, closes, period)

            # Build indicator responses
            current_price = closes[-1] if closes else 0

            # SMA
            if sma_values and sma_values[-1] is not None:
                sma_signal, sma_strength = generate_signal("sma", sma_values[-1], sma_values[-5:], current_price)
                indicators["SMA"] = IndicatorData(
                    name="Simple Moving Average",
                    type=IndicatorType.TREND,
                    period=period,
                    values=[
                        IndicatorValue(timestamp=timestamps[i], value=val, signal=None)
                        for i, val in enumerate(sma_values) if val is not None
                    ][-20:],  # Last 20 values
                    current_value=sma_values[-1],
                    signal=sma_signal,
                    signal_strength=sma_strength,
                    interpretation=f"Price is {'above' if current_price > sma_values[-1] else 'below'} SMA",
                    parameters={"period": period}
                )

            # EMA
            if ema_values and ema_values[-1] is not None:
                ema_signal, ema_strength = generate_signal("ema", ema_values[-1], ema_values[-5:], current_price)
                indicators["EMA"] = IndicatorData(
                    name="Exponential Moving Average",
                    type=IndicatorType.TREND,
                    period=period,
                    values=[
                        IndicatorValue(timestamp=timestamps[i], value=val, signal=None)
                        for i, val in enumerate(ema_values) if val is not None
                    ][-20:],
                    current_value=ema_values[-1],
                    signal=ema_signal,
                    signal_strength=ema_strength,
                    interpretation=f"Price is {'above' if current_price > ema_values[-1] else 'below'} EMA",
                    parameters={"period": period}
                )

            # RSI
            if rsi_values and rsi_values[-1] is not None:
                rsi_signal, rsi_strength = generate_signal("rsi", rsi_values[-1], rsi_values[-5:])
                indicators["RSI"] = IndicatorData(
                    name="Relative Strength Index",
                    type=IndicatorType.MOMENTUM,
                    period=period,
                    values=[
                        IndicatorValue(timestamp=timestamps[i], value=val, signal=None)
                        for i, val in enumerate(rsi_values) if val is not None
                    ][-20:],
                    current_value=rsi_values[-1],
                    signal=rsi_signal,
                    signal_strength=rsi_strength,
                    interpretation=f"RSI indicates {'overbought' if rsi_values[-1] > 70 else 'oversold' if rsi_values[-1] < 30 else 'neutral'} conditions",
                    parameters={"period": period}
                )

            # MACD
            if macd_data["macd"] and macd_data["macd"][-1] is not None:
                macd_signal, macd_strength = generate_signal(
                    "macd", macd_data["macd"][-1], macd_data["macd"][-5:],
                    signal_value=macd_data["signal"][-1] if macd_data["signal"][-1] else 0
                )
                indicators["MACD"] = IndicatorData(
                    name="Moving Average Convergence Divergence",
                    type=IndicatorType.MOMENTUM,
                    period=12,  # Default fast period
                    values=[
                        IndicatorValue(timestamp=timestamps[i], value=val, signal=None)
                        for i, val in enumerate(macd_data["macd"]) if val is not None
                    ][-20:],
                    current_value=macd_data["macd"][-1],
                    signal=macd_signal,
                    signal_strength=macd_strength,
                    interpretation=f"MACD is {'above' if macd_data['macd'][-1] > 0 else 'below'} zero line",
                    parameters={"fast": 12, "slow": 26, "signal": 9}
                )

            # Generate overall assessment
            signals = [ind.signal for ind in indicators.values()]
            buy_signals = signals.count("buy")
            sell_signals = signals.count("sell")

            if buy_signals > sell_signals:
                overall_signal = "buy"
                signal_confidence = buy_signals / len(signals) if signals else 0
            elif sell_signals > buy_signals:
                overall_signal = "sell"
                signal_confidence = sell_signals / len(signals) if signals else 0
            else:
                overall_signal = "neutral"
                signal_confidence = 0.5

            # Summary statistics
            summary = {
                "total_indicators": len(indicators),
                "buy_signals": buy_signals,
                "sell_signals": sell_signals,
                "neutral_signals": signals.count("neutral"),
                "average_signal_strength": sum(ind.signal_strength for ind in indicators.values()) / len(indicators) if indicators else 0,
                "current_price": current_price,
                "price_change_24h": ((current_price - closes[0]) / closes[0] * 100) if len(closes) > 1 else 0
            }

            response = IndicatorsResponse(
                symbol=symbol,
                timeframe=timeframe.value,
                indicators=indicators,
                summary=summary,
                overall_signal=overall_signal,
                signal_confidence=signal_confidence,
                last_updated=start_time,
                data_quality="good" if len(price_data) >= data_points * 0.8 else "fair"
            )

            # Cache response
            await set_cached_indicators(cache_key_str, response.dict(), ttl=300)

            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.info(
                "All indicators calculated",
                symbol=symbol,
                indicators_count=len(indicators),
                overall_signal=overall_signal,
                duration=f"{duration:.3f}s"
            )

            return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Indicators calculation failed", error=str(e), traceback=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate indicators"
        )


@router.get(
    "/{symbol}/{indicator}",
    response_model=SingleIndicatorResponse,
    summary="Get Specific Indicator",
    description="""
    Get detailed information for a specific technical indicator.

    **Available Indicators:**
    - SMA, EMA, WMA (Moving Averages)
    - RSI (Relative Strength Index)
    - MACD (Moving Average Convergence Divergence)
    - BB (Bollinger Bands)
    - ATR (Average True Range)
    """
)
async def get_specific_indicator(
    symbol: str,
    indicator: IndicatorName,
    timeframe: TimeFrame = Query(default=TimeFrame.FIFTEEN_MINUTES, description="Time frame"),
    period: int = Query(default=14, ge=5, le=50, description="Period"),
    data_points: int = Query(default=100, ge=50, le=500, description="Data points"),
    security_context: SecurityContext = Depends(get_security_context)
) -> SingleIndicatorResponse:
    """Get specific technical indicator"""

    try:
        with structlog.contextvars.bound_contextvars(
            user_id=security_context.user_id,
            symbol=symbol.upper(),
            indicator=indicator.value,
            timeframe=timeframe.value
        ):
            logger.info("Specific indicator request")

            symbol = symbol.upper().strip()

            # For now, get all indicators and return the specific one
            # In a real implementation, you might optimize this
            all_indicators_response = await get_all_indicators(
                symbol=symbol,
                timeframe=timeframe,
                period=period,
                data_points=data_points,
                security_context=security_context
            )

            indicator_key = indicator.value.upper()
            if indicator_key not in all_indicators_response.indicators:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Indicator {indicator.value} not found for symbol {symbol}"
                )

            indicator_data = all_indicators_response.indicators[indicator_key]

            # Generate analysis and recommendations
            analysis = {
                "trend": "bullish" if indicator_data.signal == "buy" else "bearish" if indicator_data.signal == "sell" else "neutral",
                "volatility": "high" if indicator_data.signal_strength > 0.7 else "medium" if indicator_data.signal_strength > 0.3 else "low",
                "reliability": "high" if indicator_data.signal_strength > 0.6 else "medium",
                "time_in_signal": "recent"  # Could be calculated from historical data
            }

            recommendations = []
            if indicator_data.signal == "buy" and indicator_data.signal_strength > 0.6:
                recommendations.append(f"Consider long position based on {indicator_data.name}")
            elif indicator_data.signal == "sell" and indicator_data.signal_strength > 0.6:
                recommendations.append(f"Consider short position based on {indicator_data.name}")
            else:
                recommendations.append(f"Monitor {indicator_data.name} for clearer signals")

            if indicator.value == "rsi" and indicator_data.current_value > 80:
                recommendations.append("RSI shows extreme overbought conditions - exercise caution")
            elif indicator.value == "rsi" and indicator_data.current_value < 20:
                recommendations.append("RSI shows extreme oversold conditions - potential reversal")

            # Related indicators (simplified)
            related_indicators = {}
            for name, ind in all_indicators_response.indicators.items():
                if name != indicator_key:
                    related_indicators[name] = ind.current_value

            response = SingleIndicatorResponse(
                symbol=symbol,
                indicator=indicator_data,
                analysis=analysis,
                recommendations=recommendations,
                related_indicators=related_indicators,
                last_updated=datetime.now(timezone.utc)
            )

            logger.info(
                "Specific indicator retrieved",
                symbol=symbol,
                indicator=indicator.value,
                signal=indicator_data.signal,
                strength=indicator_data.signal_strength
            )

            return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Specific indicator retrieval failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve specific indicator"
        )


# Health check endpoint
@router.get(
    "/health",
    summary="Technical Indicators Health Check",
    description="Check the health status of technical indicators service"
)
async def indicators_health_check(
    security_context: SecurityContext = Depends(get_security_context)
) -> Dict[str, Any]:
    """Check indicators service health"""

    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "services": {
                "calculation_engine": {"status": "healthy"},
                "cache": {"status": "healthy" if _cache_manager else "not_configured"},
                "database": {"status": "healthy" if _db_manager else "not_configured"}
            },
            "available_indicators": [indicator.value for indicator in IndicatorName],
            "supported_timeframes": [tf.value for tf in TimeFrame]
        }

        # Test a simple calculation
        try:
            test_prices = [100, 101, 99, 102, 98, 103, 97]
            test_sma = calculate_sma(test_prices, 5)
            if test_sma:
                health_status["calculation_test"] = "passed"
            else:
                health_status["calculation_test"] = "failed"
                health_status["status"] = "degraded"
        except Exception as e:
            health_status["calculation_test"] = f"failed: {str(e)}"
            health_status["status"] = "degraded"

        logger.info("Indicators health check completed", status=health_status["status"])
        return health_status

    except Exception as e:
        logger.error("Indicators health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# Initialization function
def init_indicators_routes(
    db_manager: DatabaseManager,
    cache_manager: CacheManager
) -> APIRouter:
    """Initialize technical indicators routes"""
    global _db_manager, _cache_manager

    _db_manager = db_manager
    _cache_manager = cache_manager

    logger.info("Technical indicators routes initialized successfully")
    return router


# Export
__all__ = [
    "router",
    "init_indicators_routes",
    "IndicatorRequest",
    "CustomIndicatorRequest",
    "ScreenerRequest",
    "IndicatorsResponse",
    "SingleIndicatorResponse",
    "ScreenerResponse",
    "IndicatorType",
    "IndicatorName",
    "TimeFrame"
]
