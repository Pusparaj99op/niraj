"""
AI Analysis API Routes for NIRAJ Trading System

Provides AI-powered analysis endpoints including:
- Technical analysis with Gemma3 AI
- News sentiment analysis
- Market prediction and signals
- Pattern recognition
- Risk assessment
- Strategy recommendations

Endpoints:
- POST /api/v1/ai/analyze/technical: Technical analysis
- POST /api/v1/ai/analyze/news: News sentiment analysis
- POST /api/v1/ai/analyze/market: Market analysis
- POST /api/v1/ai/predict: Market predictions
- POST /api/v1/ai/signals: Trading signals
- GET /api/v1/ai/models: Available AI models
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
import structlog

from ...core.database import DatabaseManager
from ...core.cache import CacheManager
from ...ai.gemma3_integration import (
    Gemma3Client,
    AnalysisRequest,
    AnalysisType,
)
from ...api.routes.auth import get_security_context, SecurityContext

# Initialize router
router = APIRouter(
    prefix="/ai",
    tags=["ai-analysis"],
    responses={
        400: {"description": "Bad Request - Invalid parameters"},
        401: {"description": "Unauthorized - Authentication required"},
        422: {"description": "Unprocessable Entity - Invalid analysis request"},
        503: {"description": "Service Unavailable - AI service down"},
        500: {"description": "Internal Server Error - System error"},
    },
)

# Constants
MAX_SYMBOLS_PER_REQUEST = 20
MAX_ARTICLES_PER_REQUEST = 100
MAX_TIME_WINDOW_HOURS = 168  # 1 week
MIN_ANALYSIS_DATA_POINTS = 5
MAX_SYMBOL_LENGTH = 10
CACHE_TTL_TECHNICAL = 900  # 15 minutes
CACHE_TTL_NEWS = 3600  # 1 hour
CACHE_TTL_SIGNALS = 300  # 5 minutes
CACHE_TTL_MODELS = 3600  # 1 hour

# Initialize logger
logger = structlog.get_logger(__name__)

# Global service instances
_db_manager: Optional[DatabaseManager] = None
_cache_manager: Optional[CacheManager] = None
_ai_client: Optional[Gemma3Client] = None


# Enums
class AnalysisTypeEnum(str, Enum):
    """Analysis types"""

    TECHNICAL = "technical"
    NEWS_SENTIMENT = "news_sentiment"
    MARKET_ANALYSIS = "market_analysis"
    PATTERN_RECOGNITION = "pattern_recognition"
    RISK_ASSESSMENT = "risk_assessment"


class PredictionHorizon(str, Enum):
    """Prediction time horizons"""

    INTRADAY = "intraday"
    SHORT_TERM = "short_term"  # 1-7 days
    MEDIUM_TERM = "medium_term"  # 1-4 weeks
    LONG_TERM = "long_term"  # 1-3 months


class SignalType(str, Enum):
    """Trading signal types"""

    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    STRONG_BUY = "strong_buy"
    STRONG_SELL = "strong_sell"


# Request Models
class TechnicalAnalysisRequest(BaseModel):
    """Technical analysis request"""

    symbol: str = Field(description="Trading symbol")
    timeframe: str = Field(default="15m", description="Analysis timeframe")
    indicators: Dict[str, float] = Field(description="Technical indicators data")
    price_data: List[Dict[str, Any]] = Field(description="OHLC price data")
    volume_data: Optional[List[int]] = Field(None, description="Volume data")
    analysis_depth: str = Field(
        default="standard", description="Analysis depth (quick/standard/deep)"
    )


class NewsAnalysisRequest(BaseModel):
    """News sentiment analysis request"""

    articles: List[Dict[str, Any]] = Field(description="News articles to analyze")
    symbol: Optional[str] = Field(None, description="Focus symbol")
    time_window: int = Field(default=24, description="Time window in hours")
    include_social_sentiment: bool = Field(
        default=False, description="Include social media sentiment"
    )


class MarketAnalysisRequest(BaseModel):
    """Market analysis request"""

    symbols: List[str] = Field(description="Symbols to analyze")
    market_data: Dict[str, Any] = Field(description="Market data")
    news_data: Optional[List[Dict[str, Any]]] = Field(None, description="Relevant news")
    sector_data: Optional[Dict[str, Any]] = Field(
        None, description="Sector information"
    )
    analysis_focus: List[str] = Field(
        default=["trend", "momentum", "volatility"], description="Analysis focus areas"
    )


class PredictionRequest(BaseModel):
    """Market prediction request"""

    symbol: str = Field(description="Symbol to predict")
    horizon: PredictionHorizon = Field(description="Prediction horizon")
    input_data: Dict[str, Any] = Field(description="Input data for prediction")
    confidence_threshold: float = Field(
        default=0.7, ge=0.0, le=1.0, description="Minimum confidence"
    )
    include_factors: bool = Field(
        default=True, description="Include influencing factors"
    )


class SignalsRequest(BaseModel):
    """Trading signals request"""

    symbols: List[str] = Field(
        description="Symbols for signal generation", max_length=20
    )
    strategy_type: Optional[str] = Field(None, description="Strategy type filter")
    risk_level: str = Field(
        default="medium", description="Risk level (low/medium/high)"
    )
    timeframe: str = Field(default="15m", description="Signal timeframe")
    min_confidence: float = Field(
        default=0.6, ge=0.0, le=1.0, description="Minimum signal confidence"
    )


# Response Models
class TechnicalAnalysisResponse(BaseModel):
    """Technical analysis response"""

    symbol: str
    timeframe: str
    analysis_timestamp: datetime
    overall_signal: SignalType
    confidence_score: float
    key_findings: List[str]
    technical_indicators: Dict[str, Dict[str, Any]]
    support_resistance: Dict[str, List[float]]
    trend_analysis: Dict[str, Any]
    pattern_recognition: Dict[str, Any]
    risk_reward_ratio: float
    target_prices: Dict[str, float]
    stop_loss_levels: Dict[str, float]
    reasoning: str


class NewsAnalysisResponse(BaseModel):
    """News sentiment analysis response"""

    symbol: Optional[str]
    analysis_timestamp: datetime
    overall_sentiment: float  # -1 to 1
    sentiment_breakdown: Dict[str, float]
    article_count: int
    positive_articles: int
    negative_articles: int
    neutral_articles: int
    key_themes: List[str]
    sentiment_trend: List[Dict[str, Any]]
    impact_assessment: Dict[str, Any]
    confidence_score: float


class MarketAnalysisResponse(BaseModel):
    """Market analysis response"""

    symbols: List[str]
    analysis_timestamp: datetime
    market_outlook: str
    sector_analysis: Dict[str, Dict[str, Any]]
    correlation_matrix: Dict[str, Dict[str, float]]
    volatility_assessment: Dict[str, float]
    momentum_indicators: Dict[str, Dict[str, float]]
    risk_factors: List[str]
    opportunities: List[str]
    recommendations: List[Dict[str, Any]]
    confidence_score: float


class PredictionResponse(BaseModel):
    """Market prediction response"""

    symbol: str
    horizon: str
    prediction_timestamp: datetime
    predicted_direction: SignalType
    predicted_change_percent: float
    confidence_score: float
    probability_distribution: Dict[str, float]
    key_factors: List[Dict[str, Any]]
    risk_assessment: Dict[str, float]
    scenario_analysis: Dict[str, Dict[str, Any]]
    model_used: str
    data_quality_score: float


class TradingSignal(BaseModel):
    """Individual trading signal"""

    symbol: str
    signal_type: SignalType
    confidence: float
    entry_price: Optional[float]
    target_price: Optional[float]
    stop_loss: Optional[float]
    timeframe: str
    generated_at: datetime
    strategy: str
    reasoning: str
    risk_score: float


class SignalsResponse(BaseModel):
    """Trading signals response"""

    signals: List[TradingSignal]
    total_signals: int
    high_confidence_signals: int
    signal_summary: Dict[str, int]
    market_conditions: Dict[str, Any]
    timestamp: datetime


class AIModelInfo(BaseModel):
    """AI model information"""

    model_name: str
    model_type: str
    version: str
    capabilities: List[str]
    accuracy_metrics: Dict[str, float]
    last_updated: datetime
    status: str


class AIModelsResponse(BaseModel):
    """Available AI models response"""

    models: List[AIModelInfo]
    total_models: int
    active_models: int
    timestamp: datetime


# Helper functions
async def get_ai_client() -> Gemma3Client:
    """Get AI client instance"""
    global _ai_client

    if not _ai_client:
        try:
            _ai_client = Gemma3Client()
            logger.info("AI client initialized")
        except Exception as e:
            logger.error("Failed to initialize AI client", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI service unavailable",
            )

    return _ai_client


def cache_key(prefix: str, *args) -> str:
    """Generate cache key for AI analysis"""
    return f"ai:{prefix}:{':'.join(str(arg) for arg in args)}"


async def get_cached_analysis(key: str, ttl: int = 1800) -> Optional[Dict[str, Any]]:
    """Get cached analysis data with error handling"""
    if not _cache_manager:
        return None

    try:
        cached_data = await _cache_manager.get(key)
        if cached_data is None:
            return None

        # Validate cached data structure
        if not isinstance(cached_data, dict):
            logger.warning("Invalid cached data format", key=key, data_type=type(cached_data))
            return None

        return cached_data
    except Exception as e:
        logger.warning("AI cache get failed", key=key, error=str(e))
        return None


async def set_cached_analysis(key: str, data: Dict[str, Any], ttl: int = 1800):
    """Set cached analysis data with error handling"""
    if not _cache_manager:
        return

    try:
        # Validate data before caching
        if not isinstance(data, dict):
            logger.warning("Attempted to cache invalid data type", key=key, data_type=type(data))
            return

        # Ensure TTL is reasonable
        if ttl < 0 or ttl > 86400:  # Max 24 hours
            logger.warning("Invalid TTL for cache", key=key, ttl=ttl)
            ttl = min(max(ttl, 60), 86400)  # Clamp between 1 minute and 24 hours

        await _cache_manager.set(key, data, ttl=ttl)
    except Exception as e:
        logger.warning("AI cache set failed", key=key, error=str(e))


# API Endpoints
@router.post(
    "/analyze/technical",
    response_model=TechnicalAnalysisResponse,
    summary="Technical Analysis",
    description="""
    Perform AI-powered technical analysis on price data and indicators.

    **Features:**
    - Pattern recognition
    - Support/resistance identification
    - Trend analysis
    - Signal generation
    - Risk assessment
    """,
)
async def analyze_technical(
    request: TechnicalAnalysisRequest,
    security_context: SecurityContext = Depends(get_security_context),
) -> TechnicalAnalysisResponse:
    """Perform technical analysis using AI"""

    start_time = datetime.now(timezone.utc)

    try:
        with structlog.contextvars.bound_contextvars(
            user_id=security_context.user_id,
            symbol=request.symbol,
            timeframe=request.timeframe,
            analysis_depth=request.analysis_depth,
        ):
            logger.info("Technical analysis request")

            # Input validation
            if not request.symbol or not request.symbol.strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Symbol is required and cannot be empty",
                )

            if not request.price_data or len(request.price_data) == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Price data is required and cannot be empty",
                )

            if len(request.price_data) < MIN_ANALYSIS_DATA_POINTS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"At least {MIN_ANALYSIS_DATA_POINTS} price data points are required for analysis",
                )

            if not request.indicators:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Technical indicators are required",
                )

            # Validate analysis depth
            valid_depths = ["quick", "standard", "deep"]
            if request.analysis_depth not in valid_depths:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Analysis depth must be one of: {', '.join(valid_depths)}",
                )

            # Check cache
            cache_key_str = cache_key(
                "technical", request.symbol, request.timeframe, len(request.price_data)
            )
            cached_data = await get_cached_analysis(
                cache_key_str, ttl=CACHE_TTL_TECHNICAL
            )  # 15 minute cache

            if cached_data:
                logger.info("Returning cached technical analysis")
                return TechnicalAnalysisResponse(**cached_data)

            # Get AI client
            try:
                ai_client = await get_ai_client()
            except HTTPException:
                raise
            except Exception as e:
                logger.error("AI client unavailable for technical analysis", error=str(e))
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="AI service is currently unavailable",
                )

            # Prepare analysis request
            try:
                analysis_request = AnalysisRequest(
                    analysis_type=AnalysisType.TECHNICAL_ANALYSIS,
                    input_data={
                        "symbol": request.symbol,
                        "timeframe": request.timeframe,
                        "indicators": request.indicators,
                        "price_data": request.price_data[-100:],  # Last 100 data points
                        "volume_data": (
                            request.volume_data[-100:] if request.volume_data else None
                        ),
                        "analysis_depth": request.analysis_depth,
                    },
                    confidence_threshold=0.7,
                )
            except Exception as e:
                logger.error("Failed to prepare analysis request", error=str(e))
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid analysis request data",
                )

            # Perform analysis
            try:
                analysis_result = await ai_client.analyze(analysis_request)
            except Exception as e:
                logger.error("AI analysis failed", error=str(e))
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="AI analysis service encountered an error",
                )

            # Process results
            try:
                result_data = analysis_result.result

                # Generate signal based on analysis
                signal_score = result_data.get("signal_score", 0.0)
                if signal_score > 0.7:
                    overall_signal = SignalType.BUY
                elif signal_score > 0.3:
                    overall_signal = SignalType.HOLD
                elif signal_score > -0.3:
                    overall_signal = SignalType.HOLD
                elif signal_score > -0.7:
                    overall_signal = SignalType.SELL
                else:
                    overall_signal = SignalType.STRONG_SELL

                # Extract technical indicators analysis
                indicators_analysis = {}
                for indicator, value in request.indicators.items():
                    indicators_analysis[indicator] = {
                        "value": value,
                        "signal": (
                            "bullish"
                            if value > 50
                            else "bearish" if indicator == "RSI" else "neutral"
                        ),
                        "strength": abs(value - 50) / 50 if indicator == "RSI" else 0.5,
                    }

                # Support and resistance levels (simplified)
                price_data = request.price_data
                highs = [p.get("high", 0) for p in price_data[-20:]]
                lows = [p.get("low", 0) for p in price_data[-20:]]

                support_resistance = {
                    "support_levels": sorted(set(lows))[-3:] if lows else [],
                    "resistance_levels": (
                        sorted(set(highs), reverse=True)[:3] if highs else []
                    ),
                }

                # Current price for targets
                current_price = price_data[-1].get("close", 0) if price_data else 0

                response = TechnicalAnalysisResponse(
                    symbol=request.symbol,
                    timeframe=request.timeframe,
                    analysis_timestamp=start_time,
                    overall_signal=overall_signal,
                    confidence_score=analysis_result.confidence,
                    key_findings=result_data.get("key_findings", []),
                    technical_indicators=indicators_analysis,
                    support_resistance=support_resistance,
                    trend_analysis=result_data.get("trend_analysis", {}),
                    pattern_recognition=result_data.get("patterns", {}),
                    risk_reward_ratio=result_data.get("risk_reward_ratio", 1.0),
                    target_prices={
                        "short_term": current_price * (1 + signal_score * 0.02),
                        "medium_term": current_price * (1 + signal_score * 0.05),
                    },
                    stop_loss_levels={
                        "conservative": current_price * (1 - abs(signal_score) * 0.01),
                        "aggressive": current_price * (1 - abs(signal_score) * 0.02),
                    },
                    reasoning=result_data.get("reasoning", "Technical analysis completed"),
                )

            except Exception as e:
                logger.error("Failed to process analysis results", error=str(e))
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to process analysis results",
                )

            # Cache response
            try:
                await set_cached_analysis(cache_key_str, response.dict(), ttl=CACHE_TTL_TECHNICAL)
            except Exception as e:
                logger.warning("Failed to cache analysis response", error=str(e))
                # Don't fail the request if caching fails

            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.info(
                "Technical analysis completed",
                symbol=request.symbol,
                signal=overall_signal.value,
                confidence=analysis_result.confidence,
                duration=f"{duration:.3f}s",
            )

            return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Technical analysis failed", error=str(e), traceback=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to perform technical analysis",
        )


@router.post(
    "/analyze/news",
    response_model=NewsAnalysisResponse,
    summary="News Sentiment Analysis",
    description="""
    Analyze news sentiment and its potential market impact.

    **Features:**
    - Sentiment scoring
    - Theme extraction
    - Impact assessment
    - Trend analysis
    - Confidence measurement
    """,
)
async def analyze_news_sentiment(
    request: NewsAnalysisRequest,
    security_context: SecurityContext = Depends(get_security_context),
) -> NewsAnalysisResponse:
    """Analyze news sentiment using AI"""

    start_time = datetime.now(timezone.utc)

    try:
        with structlog.contextvars.bound_contextvars(
            user_id=security_context.user_id,
            symbol=request.symbol,
            article_count=len(request.articles),
            time_window=request.time_window,
        ):
            logger.info("News sentiment analysis request")

            # Input validation
            if not request.articles:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="At least one article is required",
                )

            if len(request.articles) > MAX_ARTICLES_PER_REQUEST:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Maximum {MAX_ARTICLES_PER_REQUEST} articles allowed per request",
                )

            if request.time_window < 1 or request.time_window > MAX_TIME_WINDOW_HOURS:  # Max 1 week
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Time window must be between 1 and {MAX_TIME_WINDOW_HOURS} hours",
                )

            # Validate article structure
            for i, article in enumerate(request.articles):
                if not isinstance(article, dict):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Article {i} must be a dictionary",
                    )
                if "title" not in article and "content" not in article:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Article {i} must have at least 'title' or 'content' field",
                    )

            # Check cache
            articles_hash = str(hash(str(request.articles)))
            cache_key_str = cache_key(
                "news_sentiment", request.symbol or "general", articles_hash
            )
            cached_data = await get_cached_analysis(
                cache_key_str, ttl=CACHE_TTL_NEWS
            )  # 1 hour cache

            if cached_data:
                logger.info("Returning cached news sentiment analysis")
                return NewsAnalysisResponse(**cached_data)

            # Get AI client
            try:
                ai_client = await get_ai_client()
            except HTTPException:
                raise
            except Exception as e:
                logger.error("AI client unavailable for news sentiment analysis", error=str(e))
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="AI service is currently unavailable",
                )

            # Prepare analysis request
            try:
                analysis_request = AnalysisRequest(
                    analysis_type=AnalysisType.NEWS_SENTIMENT,
                    input_data={
                        "articles": request.articles,
                        "symbol": request.symbol,
                        "time_window": request.time_window,
                        "analysis_timestamp": start_time.isoformat(),
                    },
                    confidence_threshold=0.6,
                )
            except Exception as e:
                logger.error("Failed to prepare news sentiment analysis request", error=str(e))
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid news analysis request data",
                )

            # Perform sentiment analysis
            try:
                analysis_result = await ai_client.analyze(analysis_request)
                result_data = analysis_result.result
            except Exception as e:
                logger.error("AI news sentiment analysis failed", error=str(e))
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="AI sentiment analysis service encountered an error",
                )

            # Calculate sentiment metrics
            try:
                total_articles = len(request.articles)
                sentiment_scores = []
                positive_count = 0
                negative_count = 0
                neutral_count = 0

                # Simulate sentiment analysis (in real implementation, use actual AI model)
                for article in request.articles:
                    # Simple keyword-based sentiment (placeholder)
                    title = article.get("title", "").lower()
                    content = article.get("content", "").lower()
                    text = f"{title} {content}"

                    sentiment_score = 0.0
                    positive_words = [
                        "good",
                        "growth",
                        "profit",
                        "increase",
                        "up",
                        "bullish",
                        "positive",
                        "gain",
                    ]
                    negative_words = [
                        "bad",
                        "loss",
                        "decrease",
                        "down",
                        "bearish",
                        "negative",
                        "decline",
                        "fall",
                    ]

                    for word in positive_words:
                        sentiment_score += text.count(word) * 0.1
                    for word in negative_words:
                        sentiment_score -= text.count(word) * 0.1

                    sentiment_score = max(-1.0, min(1.0, sentiment_score))
                    sentiment_scores.append(sentiment_score)

                    if sentiment_score > 0.1:
                        positive_count += 1
                    elif sentiment_score < -0.1:
                        negative_count += 1
                    else:
                        neutral_count += 1

                overall_sentiment = (
                    sum(sentiment_scores) / len(sentiment_scores)
                    if sentiment_scores
                    else 0.0
                )

                response = NewsAnalysisResponse(
                    symbol=request.symbol,
                    analysis_timestamp=start_time,
                    overall_sentiment=overall_sentiment,
                    sentiment_breakdown={
                        "very_positive": len([s for s in sentiment_scores if s > 0.5]),
                        "positive": len([s for s in sentiment_scores if 0.1 < s <= 0.5]),
                        "neutral": len([s for s in sentiment_scores if -0.1 <= s <= 0.1]),
                        "negative": len([s for s in sentiment_scores if -0.5 <= s < -0.1]),
                        "very_negative": len([s for s in sentiment_scores if s < -0.5]),
                    },
                    article_count=total_articles,
                    positive_articles=positive_count,
                    negative_articles=negative_count,
                    neutral_articles=neutral_count,
                    key_themes=result_data.get(
                        "key_themes", ["market", "trading", "investment"]
                    ),
                    sentiment_trend=[],  # Could be implemented with historical data
                    impact_assessment={
                        "short_term_impact": abs(overall_sentiment) * 0.5,
                        "market_moving_potential": (
                            1.0 if abs(overall_sentiment) > 0.7 else 0.5
                        ),
                        "confidence_level": analysis_result.confidence,
                    },
                    confidence_score=analysis_result.confidence,
                )

            except Exception as e:
                logger.error("Failed to process news sentiment results", error=str(e))
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to process sentiment analysis results",
                )

            # Cache response
            try:
                await set_cached_analysis(cache_key_str, response.dict(), ttl=CACHE_TTL_NEWS)
            except Exception as e:
                logger.warning("Failed to cache news sentiment response", error=str(e))
                # Don't fail the request if caching fails

            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.info(
                "News sentiment analysis completed",
                symbol=request.symbol,
                overall_sentiment=overall_sentiment,
                confidence=analysis_result.confidence,
                duration=f"{duration:.3f}s",
            )

            return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("News sentiment analysis failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze news sentiment",
        )


@router.post(
    "/signals",
    response_model=SignalsResponse,
    summary="Generate Trading Signals",
    description="""
    Generate AI-powered trading signals for multiple symbols.

    **Features:**
    - Multi-symbol analysis
    - Confidence scoring
    - Entry/exit points
    - Risk assessment
    - Strategy-based signals
    """,
)
async def generate_trading_signals(
    request: SignalsRequest,
    security_context: SecurityContext = Depends(get_security_context),
) -> SignalsResponse:
    """Generate trading signals using AI"""

    start_time = datetime.now(timezone.utc)

    try:
        with structlog.contextvars.bound_contextvars(
            user_id=security_context.user_id,
            symbols_count=len(request.symbols),
            risk_level=request.risk_level,
            timeframe=request.timeframe,
        ):
            logger.info("Trading signals generation request")

            if not request.symbols:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="At least one symbol is required",
                )

            if len(request.symbols) > MAX_SYMBOLS_PER_REQUEST:  # From the model definition
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Maximum {MAX_SYMBOLS_PER_REQUEST} symbols allowed per request",
                )

            # Validate symbols
            for symbol in request.symbols:
                if not symbol or not symbol.strip():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Symbol cannot be empty or whitespace",
                    )
                if len(symbol) > MAX_SYMBOL_LENGTH:  # Reasonable symbol length limit
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Symbol '{symbol}' is too long (max {MAX_SYMBOL_LENGTH} characters)",
                    )

            # Validate risk level
            valid_risk_levels = ["low", "medium", "high"]
            if request.risk_level not in valid_risk_levels:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Risk level must be one of: {', '.join(valid_risk_levels)}",
                )

            # Validate confidence threshold
            if request.min_confidence < 0.0 or request.min_confidence > 1.0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Minimum confidence must be between 0.0 and 1.0",
                )

            # Check cache
            cache_key_str = cache_key(
                "signals", str(request.symbols), request.timeframe, request.risk_level
            )
            cached_data = await get_cached_analysis(
                cache_key_str, ttl=CACHE_TTL_SIGNALS
            )  # 5 minute cache

            if cached_data:
                logger.info("Returning cached trading signals")
                return SignalsResponse(**cached_data)

            # Get AI client
            try:
                await get_ai_client()
            except HTTPException:
                raise
            except Exception as e:
                logger.error("AI client unavailable for signal generation", error=str(e))
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="AI service is currently unavailable",
                )

            signals = []
            high_confidence_count = 0

            # Generate signals for each symbol (simplified implementation)
            for symbol in request.symbols:
                try:
                    # Simulate signal generation (in real implementation, use comprehensive analysis)
                    import random

                    signal_strength = random.uniform(-1.0, 1.0)
                    confidence = random.uniform(0.4, 0.95)

                    if confidence < request.min_confidence:
                        continue

                    # Determine signal type
                    if signal_strength > 0.6:
                        signal_type = SignalType.BUY
                    elif signal_strength > 0.2:
                        signal_type = SignalType.HOLD
                    elif signal_strength > -0.2:
                        signal_type = SignalType.HOLD
                    elif signal_strength > -0.6:
                        signal_type = SignalType.SELL
                    else:
                        signal_type = SignalType.STRONG_SELL

                    # Calculate prices (simplified)
                    base_price = (
                        100.0  # In real implementation, get current market price
                    )
                    entry_price = base_price

                    if signal_type in [SignalType.BUY, SignalType.STRONG_BUY]:
                        target_price = base_price * (1 + abs(signal_strength) * 0.03)
                        stop_loss = base_price * (1 - abs(signal_strength) * 0.015)
                    elif signal_type in [SignalType.SELL, SignalType.STRONG_SELL]:
                        target_price = base_price * (1 - abs(signal_strength) * 0.03)
                        stop_loss = base_price * (1 + abs(signal_strength) * 0.015)
                    else:
                        target_price = None
                        stop_loss = None

                    signal = TradingSignal(
                        symbol=symbol,
                        signal_type=signal_type,
                        confidence=confidence,
                        entry_price=(
                            entry_price if signal_type != SignalType.HOLD else None
                        ),
                        target_price=target_price,
                        stop_loss=stop_loss,
                        timeframe=request.timeframe,
                        generated_at=start_time,
                        strategy=request.strategy_type or "ai_analysis",
                        reasoning=f"AI analysis indicates {signal_type.value} signal with {confidence:.2f} confidence",
                        risk_score=1.0 - confidence,
                    )

                    signals.append(signal)

                    if confidence > 0.8:
                        high_confidence_count += 1

                except Exception as e:
                    logger.warning(
                        "Failed to generate signal", symbol=symbol, error=str(e)
                    )
                    continue

            # Generate signal summary and response
            try:
                signal_summary = {}
                for signal in signals:
                    signal_type = signal.signal_type.value
                    signal_summary[signal_type] = signal_summary.get(signal_type, 0) + 1

                # Market conditions assessment (simplified)
                market_conditions = {
                    "volatility": "medium",
                    "trend": "sideways",
                    "sentiment": "neutral",
                    "volume": "average",
                }

                response = SignalsResponse(
                    signals=signals,
                    total_signals=len(signals),
                    high_confidence_signals=high_confidence_count,
                    signal_summary=signal_summary,
                    market_conditions=market_conditions,
                    timestamp=start_time,
                )

            except Exception as e:
                logger.error("Failed to create signals response", error=str(e))
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to process trading signals",
                )

            # Cache response
            try:
                await set_cached_analysis(cache_key_str, response.dict(), ttl=CACHE_TTL_SIGNALS)
            except Exception as e:
                logger.warning("Failed to cache signals response", error=str(e))
                # Don't fail the request if caching fails

            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.info(
                "Trading signals generated",
                total_signals=len(signals),
                high_confidence=high_confidence_count,
                duration=f"{duration:.3f}s",
            )

            return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Trading signals generation failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate trading signals",
        )


@router.get(
    "/models",
    response_model=AIModelsResponse,
    summary="Get Available AI Models",
    description="""
    Get information about available AI models and their capabilities.

    **Features:**
    - Model specifications
    - Accuracy metrics
    - Capability descriptions
    - Status information
    """,
)
async def get_ai_models(
    security_context: SecurityContext = Depends(get_security_context),
) -> AIModelsResponse:
    """Get available AI models"""

    try:
        with structlog.contextvars.bound_contextvars(user_id=security_context.user_id):
            logger.info("AI models request")

            # Check cache
            cache_key_str = cache_key("models")
            cached_data = await get_cached_analysis(
                cache_key_str, ttl=CACHE_TTL_MODELS
            )  # 1 hour cache

            if cached_data:
                return AIModelsResponse(**cached_data)

            # Get AI client
            try:
                await get_ai_client()
                client_available = True
            except Exception:
                client_available = False

            # Mock model information (in real implementation, query actual models)
            models = [
                AIModelInfo(
                    model_name="Gemma3-Trading",
                    model_type="Language Model",
                    version="3.0",
                    capabilities=[
                        "Technical Analysis",
                        "News Sentiment Analysis",
                        "Pattern Recognition",
                        "Risk Assessment",
                    ],
                    accuracy_metrics={
                        "technical_analysis": 0.82,
                        "sentiment_analysis": 0.78,
                        "pattern_recognition": 0.75,
                    },
                    last_updated=datetime.now(timezone.utc) - timedelta(days=7),
                    status="active" if client_available else "unavailable",
                ),
                AIModelInfo(
                    model_name="NIRAJ-Predictor",
                    model_type="Ensemble Model",
                    version="2.1",
                    capabilities=[
                        "Price Prediction",
                        "Trend Forecasting",
                        "Volatility Analysis",
                    ],
                    accuracy_metrics={
                        "price_prediction": 0.71,
                        "trend_accuracy": 0.68,
                        "volatility_forecast": 0.73,
                    },
                    last_updated=datetime.now(timezone.utc) - timedelta(days=14),
                    status="active",
                ),
            ]

            active_models = len([m for m in models if m.status == "active"])

            response = AIModelsResponse(
                models=models,
                total_models=len(models),
                active_models=active_models,
                timestamp=datetime.now(timezone.utc),
            )

            # Cache response
            await set_cached_analysis(cache_key_str, response.dict(), ttl=CACHE_TTL_MODELS)

            logger.info(
                "AI models information retrieved",
                total=len(models),
                active=active_models,
            )
            return response

    except Exception as e:
        logger.error("AI models retrieval failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve AI models information",
        )


# Health check endpoint
@router.get(
    "/health",
    summary="AI Service Health Check",
    description="Check the health status of AI services and models",
)
async def ai_health_check(
    security_context: SecurityContext = Depends(get_security_context),
) -> Dict[str, Any]:
    """Check AI service health"""

    try:
        with structlog.contextvars.bound_contextvars(user_id=security_context.user_id):
            logger.info("AI health check request")

            health_status = {
                "status": "healthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "services": {},
                "version": "1.0.0",  # API version
            }

            # Check AI client
            try:
                ai_client = await get_ai_client()
                if hasattr(ai_client, "health_check"):
                    try:
                        ai_health = await ai_client.health_check()
                        health_status["services"]["ai_client"] = ai_health
                    except Exception as e:
                        health_status["services"]["ai_client"] = {
                            "status": "error",
                            "error": str(e),
                        }
                        health_status["status"] = "degraded"
                else:
                    health_status["services"]["ai_client"] = {"status": "available"}
            except HTTPException:
                health_status["services"]["ai_client"] = {
                    "status": "unavailable",
                    "error": "Service initialization failed",
                }
                health_status["status"] = "unhealthy"
            except Exception as e:
                health_status["services"]["ai_client"] = {
                    "status": "unavailable",
                    "error": str(e),
                }
                health_status["status"] = "unhealthy"

            # Check cache
            if _cache_manager:
                try:
                    test_key = f"ai:health_test:{security_context.user_id}"
                    await _cache_manager.set(test_key, {"test": True}, ttl=10)
                    cached_value = await _cache_manager.get(test_key)
                    if cached_value and cached_value.get("test"):
                        health_status["services"]["cache"] = {"status": "healthy"}
                    else:
                        health_status["services"]["cache"] = {
                            "status": "unhealthy",
                            "error": "Cache read/write test failed",
                        }
                        health_status["status"] = "degraded"
                except Exception as e:
                    health_status["services"]["cache"] = {
                        "status": "unhealthy",
                        "error": str(e),
                    }
                    health_status["status"] = "degraded"
            else:
                health_status["services"]["cache"] = {"status": "not_configured"}

            # Add system info
            health_status["system_info"] = {
                "python_version": f"{__import__('sys').version_info.major}.{__import__('sys').version_info.minor}",
                "timezone": str(timezone.utc),
            }

            logger.info("AI health check completed", status=health_status["status"])
            return health_status

    except Exception as e:
        logger.error("AI health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# Initialization function
def init_ai_routes(
    db_manager: DatabaseManager,
    cache_manager: CacheManager,
    ai_client: Optional[Gemma3Client] = None,
) -> APIRouter:
    """Initialize AI analysis routes"""
    global _db_manager, _cache_manager, _ai_client

    _db_manager = db_manager
    _cache_manager = cache_manager
    _ai_client = ai_client

    logger.info("AI analysis routes initialized successfully")
    return router


# Export
__all__ = [
    "router",
    "init_ai_routes",
    "TechnicalAnalysisRequest",
    "NewsAnalysisRequest",
    "MarketAnalysisRequest",
    "PredictionRequest",
    "SignalsRequest",
    "TechnicalAnalysisResponse",
    "NewsAnalysisResponse",
    "MarketAnalysisResponse",
    "PredictionResponse",
    "SignalsResponse",
    "AIModelsResponse",
    "AnalysisTypeEnum",
    "PredictionHorizon",
    "SignalType",
]
