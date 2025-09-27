"""
Vulture Approach Strategy Implementation for NIRAJ Trading System

Contrarian strategy that exploits market fear and panic selling by identifying
distressed situations and capitulation events. This strategy waits for extreme
negative sentiment and oversold conditions to buy at bargain prices.

Key Features:
- Oversold condition detection using RSI, Bollinger Bands, and volume analysis - Sentiment analysis for fear/panic detection and capitulation events - Mean reversion signals after extreme market moves - Contrarian position sizing with high conviction trades - Advanced risk management for distressed market conditions - AI-powered fear detection and market psychology analysis -
Real-time capitulation monitoring and signal generation
"""

import time
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import structlog
import uuid
import statistics

try:
    from ...core.config import get_config
    from ...models.strategy import StrategyConfig, StrategyType
    from ...models.strategy_signal import SignalType
    from ...models.market_data import MarketData
    from ...models.technical_indicator import IndicatorType
    from ...utils.technical_indicators import TechnicalIndicatorsCalculator
    from ...ai.gemma3_integration import Gemma3Client, AnalysisType, AnalysisRequest
    from ...ai.confidence_tracker import AdvancedConfidenceTracker
    from ..base_strategy import (
        BaseStrategy,
        MarketAnalysis,
        TradingSignal,
        StrategyPhase,
        SignalGenerationError,
        RiskManagementError,
    )
except ImportError as e:
    # Handle imports for isolated testing - define minimal interfaces
    print(f"Some imports failed, using minimal interfaces: {str(e)}")

    # Mock get_config function
    def get_config(key: str, default=None):
        """Mock configuration getter for testing"""
        config_defaults = {
            "strategy.vulture.min_oversold_rsi": 25,
            "strategy.vulture.max_overbought_rsi": 75,
            "strategy.vulture.capitulation_volume_multiplier": 2.5,
            "strategy.vulture.sentiment_fear_threshold": -0.7,
            "strategy.vulture.mean_reversion_lookback": 20,
            "strategy.vulture.min_confidence": 0.75,
            "strategy.vulture.max_history_size": 200,
            "strategy.vulture.pattern_recognition_window": 50,
            "strategy.vulture.max_active_opportunities": 3,
            "strategy.vulture.max_concurrent_positions": 2,
            "strategy.vulture.emergency_stop_multiplier": 1.5,
            "strategy.vulture.conservative_profit_targets": [1.5, 3.0, 5.0, 8.0, 12.0],
            "strategy.vulture.max_consecutive_failures": 3,
        }
        return config_defaults.get(key, default)

    # Define minimal required classes
    class StrategyType(str, Enum):
        PREDATORY = "predatory"
        PSYCHOLOGICAL = "psychological"
        QUANTITATIVE = "quantitative"

    @dataclass
    class StrategyConfig:
        name: str = ""
        description: str = ""
        strategy_type: StrategyType = StrategyType.PSYCHOLOGICAL
        max_position_size: float = 0.05  # More conservative
        max_drawdown_limit: float = 0.08  # Tighter drawdown limit
        stop_loss_percentage: float = 0.03  # Tighter stops
        take_profit_percentage: float = 0.08  # Higher targets for mean reversion
        min_signal_strength: float = 0.75  # Higher conviction required
        max_trades_per_day: int = 5  # Lower frequency
        supported_symbols: List[str] = None

        def __post_init__(self):
            if self.supported_symbols is None:
                self.supported_symbols = []

    @dataclass
    class MarketData:
        symbol: str
        timestamp: datetime
        open: float = 0.0
        high: float = 0.0
        low: float = 0.0
        close: float = 0.0
        volume: int = 0

    # Mock classes for dependencies
    class TechnicalIndicatorsCalculator:
        def calculate_indicator(self, indicator_type, data_points, **kwargs):
            class MockResult:
                value = 0.5
                values = [0.5]

            return MockResult()

    class Gemma3Client:
        def __init__(self):
            pass

        async def connect(self):
            pass

        async def analyze(self, request):
            class MockResponse:
                result = {
                    "confidence": 0.5,
                    "key_points": [],
                    "risk_level": "medium",
                    "rationale": "Mock response",
                }
                confidence_score = 0.5
                processing_time_ms = 100

            return MockResponse()

        @property
        def is_connected(self):
            return True

    class AdvancedConfidenceTracker:
        pass

    # Mock enums
    class IndicatorType(str, Enum):
        PREDATOR_SIGNAL = "predator_signal"
        VOLUME_WEIGHTED_AVERAGE_PRICE = "vwap"
        BOLLINGER_BANDS = "bollinger_bands"
        RSI = "rsi"
        MACD = "macd"
        ATR = "atr"
        CHAIKIN_MF = "chaikin_mf"

    class AnalysisType(str, Enum):
        PATTERN_RECOGNITION = "pattern_recognition"

    @dataclass
    class AnalysisRequest:
        analysis_type: AnalysisType
        input_data: Dict[str, Any]
        confidence_threshold: float = 0.5

    # Define minimal BaseStrategy interface for testing
    class BaseStrategy:
        def __init__(self, config, learning_engine=None):
            self.config = config
            self.learning_engine = learning_engine
            self.strategy_id = str(uuid.uuid4())
            self.status = type("Status", (), {"ACTIVE": "active", "PAUSED": "paused"})()
            self.current_phase = StrategyPhase.INITIALIZING
            self.active_positions = {}
            self.performance = type(
                "Performance",
                (),
                {"total_return": 0.0, "total_trades": 0, "win_rate": 0.0},
            )()
            self.last_analysis = {}

        async def initialize(self):
            return True

        async def manage_risk(self, portfolio):
            return []

        async def update_performance(self, trade_result):
            pass

        async def health_check(self):
            return {"status": "unknown"}

        async def cleanup(self):
            pass

        def log_strategy_event(self, event_type, data):
            pass

    # Define other minimal classes
    @dataclass
    class MarketAnalysis:
        symbol: str
        analysis_type: str = ""
        indicators: Dict[str, Any] = None
        ai_insights: Dict[str, Any] = None
        sentiment_score: float = 0.0
        volatility: float = 0.0
        liquidity_score: float = 1.0
        confidence_score: float = 0.5
        processing_time_ms: float = 0.0

        def __post_init__(self):
            if self.indicators is None:
                self.indicators = {}
            if self.ai_insights is None:
                self.ai_insights = {}

    @dataclass
    class TradingSignal:
        strategy_id: str
        symbol: str
        signal_type: Any
        strength: float
        entry_price: float
        stop_loss_price: float
        take_profit_price: float
        position_size_percentage: float
        quantity: int
        reasoning: str
        supporting_data: Dict[str, Any] = None
        expiry_minutes: int = 60
        signal_id: str = ""

        def __post_init__(self):
            if self.supporting_data is None:
                self.supporting_data = {}
            if not self.signal_id:
                self.signal_id = str(uuid.uuid4())

    # Define minimal enums and exceptions
    class StrategyPhase(str, Enum):
        INITIALIZING = "initializing"
        ANALYZING = "analyzing"
        SIGNAL_GENERATION = "signal_generation"

    class SignalGenerationError(Exception):
        pass

    class RiskManagementError(Exception):
        pass


# Configure structured logging
logger = structlog.get_logger(__name__)


# Custom Exception Types for Vulture Strategy
class VultureStrategyError(Exception):
    """Base exception for Vulture strategy errors"""

    pass


class ConfigurationError(VultureStrategyError):
    """Configuration validation errors"""

    pass


class ValidationError(VultureStrategyError):
    """Input validation errors"""

    pass


class SentimentAnalysisError(VultureStrategyError):
    """Sentiment analysis related errors"""

    pass


class CapitulationDetectionError(VultureStrategyError):
    """Capitulation detection errors"""

    pass


class MeanReversionError(VultureStrategyError):
    """Mean reversion calculation errors"""

    pass


class ResourceError(VultureStrategyError):
    """Resource management errors"""

    pass


# Validation utilities
class VultureValidator:
    """Comprehensive validation utilities for Vulture strategy"""

    @staticmethod
    def validate_market_data(market_data) -> None:
        """Validate market data input"""
        if not market_data:
            raise ValidationError("Market data cannot be None")

        required_attrs = ["symbol", "timestamp", "close", "volume"]
        for attr in required_attrs:
            if not hasattr(market_data, attr):
                raise ValidationError(f"Market data missing required attribute: {attr}")

        if not isinstance(market_data.symbol, str) or not market_data.symbol.strip():
            raise ValidationError("Invalid symbol in market data")

        if not isinstance(market_data.close, (int, float)) or market_data.close <= 0:
            raise ValidationError("Invalid close price in market data")

        if not isinstance(market_data.volume, (int, float)) or market_data.volume < 0:
            raise ValidationError("Invalid volume in market data")

    @staticmethod
    def validate_config(config) -> None:
        """Validate strategy configuration"""
        if not config:
            raise ConfigurationError("Strategy configuration cannot be None")

        if config.strategy_type not in [
            StrategyType.PSYCHOLOGICAL,
            StrategyType.QUANTITATIVE,
        ]:
            raise ConfigurationError(
                f"Invalid strategy type: {config.strategy_type}. Expected PSYCHOLOGICAL or QUANTITATIVE"
            )

        if not isinstance(config.max_position_size, (int, float)) or not (
            0 < config.max_position_size <= 0.1
        ):
            raise ConfigurationError(
                "max_position_size must be between 0 and 0.1 for conservative vulture strategy"
            )

        if not isinstance(config.max_drawdown_limit, (int, float)) or not (
            0 < config.max_drawdown_limit <= 0.15
        ):
            raise ConfigurationError("max_drawdown_limit must be between 0 and 0.15")

        if hasattr(config, "custom_params") and config.custom_params:
            custom_params = config.custom_params
            if "min_oversold_rsi" in custom_params:
                rsi = custom_params["min_oversold_rsi"]
                if not isinstance(rsi, (int, float)) or not (0 <= rsi <= 50):
                    raise ConfigurationError(
                        "min_oversold_rsi must be between 0 and 50"
                    )

            if "sentiment_fear_threshold" in custom_params:
                threshold = custom_params["sentiment_fear_threshold"]
                if not isinstance(threshold, (int, float)) or not (
                    -1 <= threshold <= 0
                ):
                    raise ConfigurationError(
                        "sentiment_fear_threshold must be between -1 and 0"
                    )

    @staticmethod
    def validate_sentiment_data(sentiment_data) -> None:
        """Validate sentiment analysis data"""
        if not sentiment_data:
            raise SentimentAnalysisError("Sentiment data cannot be None")

        if not isinstance(sentiment_data, dict):
            raise SentimentAnalysisError("Sentiment data must be a dictionary")

        if "fear_greed_index" in sentiment_data:
            fgi = sentiment_data["fear_greed_index"]
            if not isinstance(fgi, (int, float)) or not (0 <= fgi <= 100):
                raise SentimentAnalysisError(
                    "Fear greed index must be between 0 and 100"
                )

        if "sentiment_score" in sentiment_data:
            score = sentiment_data["sentiment_score"]
            if not isinstance(score, (int, float)) or not (-1 <= score <= 1):
                raise SentimentAnalysisError("Sentiment score must be between -1 and 1")

    @staticmethod
    def validate_capitulation_signal(signal) -> None:
        """Validate capitulation signal"""
        if not signal:
            raise CapitulationDetectionError("Capitulation signal cannot be None")

        if not isinstance(signal.confidence_score, (int, float)) or not (
            0 <= signal.confidence_score <= 1
        ):
            raise CapitulationDetectionError("Confidence score must be between 0 and 1")

        if signal.signal_type not in ["buy", "sell"]:
            raise CapitulationDetectionError("Signal type must be 'buy' or 'sell'")

        if (
            not isinstance(signal.price_target, (int, float))
            or signal.price_target <= 0
        ):
            raise CapitulationDetectionError("Price target must be positive")

    @staticmethod
    def validate_signal_parameters(**kwargs) -> None:
        """Validate signal generation parameters"""
        confidence_threshold = kwargs.get("confidence_threshold", 0.5)
        if not isinstance(confidence_threshold, (int, float)) or not (
            0 <= confidence_threshold <= 1
        ):
            raise SignalGenerationError("Confidence threshold must be between 0 and 1")

        max_opportunities = kwargs.get("max_opportunities", 5)
        if not isinstance(max_opportunities, int) or max_opportunities <= 0:
            raise SignalGenerationError("Max opportunities must be positive integer")


class OversoldCondition(str, Enum):
    """Types of oversold market conditions"""

    EXTREME_OVERSOLD = "extreme_oversold"  # RSI < 20, price below lower BB
    MODERATE_OVERSOLD = "moderate_oversold"  # RSI < 30, price near lower BB
    WEAK_OVERSOLD = "weak_oversold"  # RSI < 40, testing lower BB


class CapitulationEvent(str, Enum):
    """Types of capitulation events"""

    PANIC_SELLING = "panic_selling"  # High volume, extreme negative sentiment
    INSTITUTIONAL_CAPITULATION = "institutional_capitulation"  # Large blocks at lows
    RETAIL_CAPITULATION = "retail_capitulation"  # Social media fear spike
    TECHNICAL_BREAKDOWN = "technical_breakdown"  # Multiple technical levels broken


class MeanReversionSignal(str, Enum):
    """Mean reversion signal types"""

    BOUNCE_FROM_LOW = "bounce_from_low"  # Price rejection from extreme low
    RSI_DIVERGENCE = "rsi_divergence"  # Positive divergence in oversold territory
    VOLUME_EXHAUSTION = "volume_exhaustion"  # High volume followed by low volume
    SENTIMENT_EXTREME = "sentiment_extreme"  # Extreme fear followed by stabilization


@dataclass
class SentimentSnapshot:
    """Snapshot of market sentiment data"""

    timestamp: datetime
    fear_greed_index: float  # 0-100 scale
    sentiment_score: float  # -1 to 1 scale
    news_sentiment: float  # -1 to 1 scale
    social_sentiment: float  # -1 to 1 scale
    put_call_ratio: float  # Options sentiment
    vix_level: float  # Fear index
    volatility_index: float  # Market volatility


@dataclass
class CapitulationSignal:
    """Detected capitulation event"""

    event_type: CapitulationEvent
    confidence_score: float
    signal_type: str  # "buy" or "sell"
    price_target: float
    volume_multiplier: float
    sentiment_trigger: float
    detection_timestamp: datetime
    supporting_evidence: Dict[str, Any] = field(default_factory=dict)
    risk_assessment: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VultureOpportunity:
    """Vulture strategy trading opportunity"""

    signal_type: MeanReversionSignal
    entry_price: float
    stop_loss_price: float
    take_profit_price: float
    position_size_percentage: float
    confidence_score: float
    risk_reward_ratio: float
    estimated_profit_potential: float
    holding_period_days: int
    expiry_seconds: int
    reasoning: str
    market_conditions: Dict[str, Any] = field(default_factory=dict)


class VultureStrategy(BaseStrategy):
    """
    Vulture Strategy: Contrarian Exploitation of Market Fear

    This strategy identifies oversold conditions, capitulation events, and extreme
    negative sentiment to buy at bargain prices. It waits patiently for distressed
    situations and uses mean reversion principles in fearful markets.

    Key Components:
    - Real-time sentiment analysis and fear detection - Oversold condition monitoring using RSI and Bollinger Bands - Capitulation event detection with volume and sentiment analysis - Mean reversion signal generation with high conviction - Conservative position sizing for contrarian trades -
    Advanced risk management for distressed market conditions
    """

    def __init__(self, config: StrategyConfig, learning_engine=None):
        """Initialize the Vulture strategy with comprehensive validation"""
        try:
            # Validate configuration first
            VultureValidator.validate_config(config)

            # Initialize parent class
            super().__init__(config, learning_engine)

            # Strategy-specific configuration with validation
            self.min_oversold_rsi = get_config("strategy.vulture.min_oversold_rsi", 25)
            if not isinstance(self.min_oversold_rsi, (int, float)) or not (
                0 <= self.min_oversold_rsi <= 50
            ):
                raise ConfigurationError("min_oversold_rsi must be between 0 and 50")

            self.max_overbought_rsi = get_config(
                "strategy.vulture.max_overbought_rsi", 75
            )
            if not isinstance(self.max_overbought_rsi, (int, float)) or not (
                50 <= self.max_overbought_rsi <= 100
            ):
                raise ConfigurationError(
                    "max_overbought_rsi must be between 50 and 100"
                )

            self.capitulation_volume_multiplier = get_config(
                "strategy.vulture.capitulation_volume_multiplier", 2.5
            )
            if (
                not isinstance(self.capitulation_volume_multiplier, (int, float))
                or self.capitulation_volume_multiplier <= 1
            ):
                raise ConfigurationError(
                    "capitulation_volume_multiplier must be greater than 1"
                )

            self.sentiment_fear_threshold = get_config(
                "strategy.vulture.sentiment_fear_threshold", -0.7
            )
            if not isinstance(self.sentiment_fear_threshold, (int, float)) or not (
                -1 <= self.sentiment_fear_threshold <= 0
            ):
                raise ConfigurationError(
                    "sentiment_fear_threshold must be between -1 and 0"
                )

            self.mean_reversion_lookback = get_config(
                "strategy.vulture.mean_reversion_lookback", 20
            )
            if (
                not isinstance(self.mean_reversion_lookback, (int, float))
                or self.mean_reversion_lookback <= 0
            ):
                raise ConfigurationError("mean_reversion_lookback must be positive")

            self.min_confidence_threshold = get_config(
                "strategy.vulture.min_confidence", 0.75
            )
            if not isinstance(self.min_confidence_threshold, (int, float)) or not (
                0 <= self.min_confidence_threshold <= 1
            ):
                raise ConfigurationError("min_confidence must be between 0 and 1")

            # Sentiment tracking with validation
            self.sentiment_history: List[SentimentSnapshot] = []
            self.max_history_size = get_config("strategy.vulture.max_history_size", 200)
            if not isinstance(self.max_history_size, int) or self.max_history_size < 1:
                raise ConfigurationError("max_history_size must be positive integer")

            # Capitulation detection with validation
            self.capitulation_history: List[CapitulationSignal] = []
            self.pattern_recognition_window = get_config(
                "strategy.vulture.pattern_recognition_window", 50
            )
            if (
                not isinstance(self.pattern_recognition_window, (int, float))
                or self.pattern_recognition_window <= 0
            ):
                raise ConfigurationError(
                    "pattern_recognition_window must be positive number"
                )

            # Mean reversion state with validation
            self.active_opportunities: Dict[str, VultureOpportunity] = {}
            self.mean_reversion_signals: List[Dict[str, Any]] = []
            self.max_active_opportunities = get_config(
                "strategy.vulture.max_active_opportunities", 3
            )
            if (
                not isinstance(self.max_active_opportunities, int)
                or self.max_active_opportunities < 1
            ):
                raise ConfigurationError(
                    "max_active_opportunities must be positive integer"
                )

            # AI and technical analysis components
            self.indicators_calculator = TechnicalIndicatorsCalculator()
            self.ai_client = Gemma3Client()
            self.confidence_tracker = AdvancedConfidenceTracker()

            # Performance tracking with validation
            self.vulture_stats = {
                "total_opportunities": 0,
                "successful_trades": 0,
                "failed_trades": 0,
                "average_profit_per_trade": 0.0,
                "win_rate": 0.0,
                "average_holding_period": 0.0,
                "max_drawdown": 0.0,
                "total_trading_volume": 0.0,
                "best_trade": 0.0,
                "worst_trade": 0.0,
                "capitulation_accuracy": 0.0,
                "sentiment_prediction_accuracy": 0.0,
            }

            # Risk management parameters with validation
            self.max_concurrent_positions = get_config(
                "strategy.vulture.max_concurrent_positions", 2
            )
            if (
                not isinstance(self.max_concurrent_positions, int)
                or self.max_concurrent_positions < 1
            ):
                raise ConfigurationError(
                    "max_concurrent_positions must be positive integer"
                )

            self.emergency_stop_loss_multiplier = get_config(
                "strategy.vulture.emergency_stop_multiplier", 1.5
            )
            if (
                not isinstance(self.emergency_stop_loss_multiplier, (int, float))
                or self.emergency_stop_loss_multiplier <= 1
            ):
                raise ConfigurationError(
                    "emergency_stop_multiplier must be greater than 1"
                )

            self.conservative_profit_targets = get_config(
                "strategy.vulture.conservative_profit_targets",
                [1.5, 3.0, 5.0, 8.0, 12.0],
            )
            if not isinstance(self.conservative_profit_targets, list) or not all(
                isinstance(x, (int, float)) and x > 0
                for x in self.conservative_profit_targets
            ):
                raise ConfigurationError(
                    "conservative_profit_targets must be list of positive numbers"
                )

            # Circuit breaker state
            self.circuit_breaker_active = False
            self.circuit_breaker_reason = ""
            self.circuit_breaker_timestamp = None
            self.consecutive_failures = 0
            self.max_consecutive_failures = get_config(
                "strategy.vulture.max_consecutive_failures", 3
            )

            logger.info(
                "Vulture strategy initialized with validation",
                strategy_id=self.strategy_id,
                min_rsi=self.min_oversold_rsi,
                fear_threshold=self.sentiment_fear_threshold,
                max_concurrent_positions=self.max_concurrent_positions,
            )

        except (ConfigurationError, ValidationError) as e:
            logger.error(
                "Vulture strategy initialization validation failed", error=str(e)
            )
            raise
        except Exception as e:
            logger.error(
                "Unexpected error during Vulture strategy initialization", error=str(e)
            )
            raise ConfigurationError(f"Failed to initialize Vulture strategy: {str(e)}")

    async def initialize(self) -> bool:
        """
        Initialize the Vulture strategy with required resources

        Returns:
            True if initialization successful
        """
        try:
            self.current_phase = StrategyPhase.INITIALIZING

            # Initialize AI client
            await self.ai_client.connect()

            # Validate configuration
            if self.config.strategy_type not in [
                StrategyType.PSYCHOLOGICAL,
                StrategyType.QUANTITATIVE,
            ]:
                raise ValueError(f"Invalid strategy type: {self.config.strategy_type}")

            # Set up conservative trading parameters
            self.config.max_trades_per_day = 5  # Low frequency, high conviction
            self.config.min_signal_strength = self.min_confidence_threshold

            # Initialize technical indicators
            await self._initialize_technical_indicators()

            logger.info("Vulture strategy initialization completed")
            return True

        except Exception as e:
            logger.error("Vulture strategy initialization failed", error=str(e))
            return False

    async def _initialize_technical_indicators(self):
        """Initialize technical indicators required for vulture analysis"""
        # Vulture strategy uses specific indicators for contrarian analysis
        self.required_indicators = [
            IndicatorType.RSI,
            IndicatorType.BOLLINGER_BANDS,
            IndicatorType.MACD,
            IndicatorType.ATR,
            IndicatorType.CHAIKIN_MF,
            IndicatorType.VOLUME_WEIGHTED_AVERAGE_PRICE,
        ]

    async def analyze_market(self, market_data: MarketData) -> MarketAnalysis:
        """
        Analyze market data with comprehensive validation and error handling

        Args:
            market_data: Current market data

        Returns:
            MarketAnalysis with vulture-specific insights

        Raises:
            ValidationError: If market data is invalid
            SentimentAnalysisError: If sentiment analysis fails
            CapitulationDetectionError: If capitulation detection fails
        """
        try:
            # Check circuit breaker
            if self.circuit_breaker_active:
                raise VultureStrategyError(
                    f"Circuit breaker active: {self.circuit_breaker_reason}"
                )

            # Validate input
            VultureValidator.validate_market_data(market_data)

            self.current_phase = StrategyPhase.ANALYZING
            start_time = time.time()

            # Update sentiment data with error handling
            await self._update_sentiment_data(market_data)

            # Calculate technical indicators with fallback
            indicators = await self._calculate_technical_indicators(market_data)

            # Analyze oversold conditions with validation
            await self._analyze_oversold_conditions(market_data, indicators)

            # Detect capitulation events with error recovery
            await self._detect_capitulation_events(market_data, indicators)

            # AI-powered sentiment analysis with fallback
            ai_insights = await self._get_ai_sentiment_insights(market_data, indicators)

            # Calculate market fear metrics
            fear_metrics = await self._calculate_market_fear_metrics(
                market_data, indicators
            )

            analysis = MarketAnalysis(
                symbol=market_data.symbol,
                analysis_type="vulture_analysis",
                indicators=indicators,
                ai_insights=ai_insights,
                sentiment_score=fear_metrics.get("composite_fear_score", 0.0),
                volatility=fear_metrics.get("volatility", 0.0),
                liquidity_score=fear_metrics.get("liquidity_score", 1.0),
                confidence_score=ai_insights.get("overall_confidence", 0.5),
                processing_time_ms=(time.time() - start_time) * 1000,
            )

            # Store analysis for signal generation
            self.last_analysis[market_data.symbol] = analysis

            # Reset consecutive failures on successful analysis
            self.consecutive_failures = 0

            logger.info(
                "Market analysis completed successfully",
                symbol=market_data.symbol,
                fear_score=analysis.sentiment_score,
                confidence=analysis.confidence_score,
                processing_time_ms=analysis.processing_time_ms,
                capitulation_events=len(self.capitulation_history),
            )

            return analysis

        except (ValidationError, VultureStrategyError) as e:
            # Don't count validation/circuit breaker errors as failures
            logger.warning(
                "Market analysis validation/circuit breaker error", error=str(e)
            )
            raise
        except Exception as e:
            self.consecutive_failures += 1
            logger.error(
                "Market analysis failed",
                error=str(e),
                consecutive_failures=self.consecutive_failures,
            )

            # Activate circuit breaker if too many consecutive failures
            if self.consecutive_failures >= self.max_consecutive_failures:
                await self._activate_circuit_breaker(
                    f"Too many consecutive analysis failures: {self.consecutive_failures}"
                )

            # Return degraded analysis for graceful degradation
            return self._create_degraded_analysis(market_data)

    def _create_degraded_analysis(self, market_data: MarketData) -> MarketAnalysis:
        """Create a degraded analysis when full analysis fails"""
        try:
            return MarketAnalysis(
                symbol=market_data.symbol,
                analysis_type="degraded_vulture_analysis",
                indicators={},
                ai_insights={
                    "fear_level": "unknown",
                    "capitulation_probability": 0.5,
                    "detected_patterns": [],
                    "market_sentiment": "neutral",
                    "overall_confidence": 0.1,  # Very low confidence
                    "ai_reasoning": "Analysis failed - using degraded mode",
                    "processing_time_ms": 0,
                },
                sentiment_score=0.0,
                volatility=0.5,  # Assume moderate volatility
                liquidity_score=0.5,  # Assume moderate liquidity
                confidence_score=0.1,  # Very low confidence
                processing_time_ms=0,
            )
        except Exception as e:
            logger.error("Failed to create degraded analysis", error=str(e))
            raise ResourceError("Cannot create even degraded analysis")

    async def _activate_circuit_breaker(self, reason: str):
        """Activate circuit breaker to prevent further trading"""
        try:
            self.circuit_breaker_active = True
            self.circuit_breaker_reason = reason
            self.circuit_breaker_timestamp = datetime.utcnow()

            # Emergency stop all positions
            await self._emergency_stop(reason)

            logger.warning(
                "Circuit breaker activated",
                reason=reason,
                timestamp=self.circuit_breaker_timestamp,
            )

        except Exception as e:
            logger.error("Failed to activate circuit breaker", error=str(e))
            raise VultureStrategyError(f"Circuit breaker activation failed: {str(e)}")

    async def _deactivate_circuit_breaker(self):
        """Deactivate circuit breaker after manual intervention"""
        try:
            self.circuit_breaker_active = False
            self.circuit_breaker_reason = ""
            self.circuit_breaker_timestamp = None
            self.consecutive_failures = 0

            logger.info("Circuit breaker deactivated")

        except Exception as e:
            logger.error("Failed to deactivate circuit breaker", error=str(e))

    async def _check_circuit_breaker_status(self) -> Dict[str, Any]:
        """Check circuit breaker status and auto-recovery conditions"""
        try:
            if not self.circuit_breaker_active:
                return {"active": False}

            # Auto-recovery after 10 minutes (longer than predator for more caution)
            if self.circuit_breaker_timestamp:
                time_since_activation = (
                    datetime.utcnow() - self.circuit_breaker_timestamp
                ).seconds
                if time_since_activation > 600:  # 10 minutes
                    await self._deactivate_circuit_breaker()
                    return {"active": False, "auto_recovered": True}

            return {
                "active": True,
                "reason": self.circuit_breaker_reason,
                "timestamp": (
                    self.circuit_breaker_timestamp.isoformat()
                    if self.circuit_breaker_timestamp
                    else None
                ),
                "consecutive_failures": self.consecutive_failures,
            }

        except Exception as e:
            logger.error("Failed to check circuit breaker status", error=str(e))
            return {"active": True, "error": str(e)}

    async def _update_sentiment_data(self, market_data: MarketData):
        """Update sentiment data from market data and external sources"""
        try:
            # In a real implementation, this would fetch from sentiment APIs
            # For now, simulate sentiment based on market data patterns

            # Calculate basic sentiment indicators from price action
            price_change_pct = (
                ((market_data.close - market_data.open) / market_data.open) * 100
                if market_data.open != 0
                else 0
            )

            # Volume-based sentiment (high volume down moves = fear)
            volume_intensity = market_data.volume / 100000  # Normalize volume

            # Calculate fear/greed index (simplified)
            if price_change_pct < -2 and volume_intensity > 1.5:
                fear_greed = 20  # Extreme fear
                sentiment_score = -0.8
            elif price_change_pct < -1 and volume_intensity > 1.2:
                fear_greed = 35  # Fear
                sentiment_score = -0.6
            elif price_change_pct > 2 and volume_intensity > 1.5:
                fear_greed = 80  # Greed
                sentiment_score = 0.6
            elif price_change_pct > 1 and volume_intensity > 1.2:
                fear_greed = 65  # Extreme greed
                sentiment_score = 0.8
            else:
                fear_greed = 50  # Neutral
                sentiment_score = 0.0

            # Create sentiment snapshot
            snapshot = SentimentSnapshot(
                timestamp=market_data.timestamp,
                fear_greed_index=fear_greed,
                sentiment_score=sentiment_score,
                news_sentiment=sentiment_score
                * 0.8,  # Correlated but slightly different
                social_sentiment=sentiment_score * 0.9,  # Highly correlated
                put_call_ratio=(
                    1.2
                    if sentiment_score < -0.5
                    else 0.8 if sentiment_score > 0.5 else 1.0
                ),
                vix_level=25 + (abs(sentiment_score) * 15),  # VIX rises with fear
                volatility_index=abs(price_change_pct) * 2,
            )

            # Update sentiment history
            self.sentiment_history.append(snapshot)

            # Maintain history size
            if len(self.sentiment_history) > self.max_history_size:
                self.sentiment_history.pop(0)

        except Exception as e:
            logger.warning("Failed to update sentiment data", error=str(e))

    async def _calculate_technical_indicators(
        self, market_data: MarketData
    ) -> Dict[str, Any]:
        """Calculate technical indicators for vulture analysis"""
        try:
            # Convert market data to list for indicator calculation
            data_points = [market_data]  # In real implementation, use historical data

            indicators = {}
            for indicator_type in self.required_indicators:
                try:
                    result = self.indicators_calculator.calculate_indicator(
                        indicator_type, data_points, symbol=market_data.symbol
                    )
                    indicators[indicator_type.value] = result.value or result.values
                except Exception as e:
                    logger.warning(
                        f"Failed to calculate {indicator_type.value}", error=str(e)
                    )
                    indicators[indicator_type.value] = None

            return indicators

        except Exception as e:
            logger.error("Technical indicators calculation failed", error=str(e))
            return {}

    async def _analyze_oversold_conditions(
        self, market_data: MarketData, indicators: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze oversold conditions for potential mean reversion"""
        try:
            rsi_value = indicators.get("rsi", 50)
            bb_values = indicators.get("bollinger_bands", {})

            oversold_conditions = {
                "rsi_oversold": rsi_value < self.min_oversold_rsi,
                "rsi_extreme_oversold": rsi_value < 20,
                "price_below_lower_bb": False,
                "price_near_lower_bb": False,
                "bb_squeeze": False,
            }

            # Check Bollinger Band position
            if bb_values and isinstance(bb_values, dict):
                lower_bb = bb_values.get("lower", market_data.close * 0.95)  # Fallback
                upper_bb = bb_values.get("upper", market_data.close * 1.05)  # Fallback
                middle_bb = bb_values.get("middle", market_data.close)  # Fallback

                bb_range = upper_bb - lower_bb
                price_position = (
                    (market_data.close - lower_bb) / bb_range if bb_range > 0 else 0.5
                )

                oversold_conditions["price_below_lower_bb"] = (
                    market_data.close < lower_bb
                )
                oversold_conditions["price_near_lower_bb"] = (
                    price_position < 0.1
                )  # Within 10% of lower BB
                oversold_conditions["bb_squeeze"] = bb_range < (
                    middle_bb * 0.05
                )  # Tight bands

            # Calculate oversold score (0-1, higher = more oversold)
            oversold_score = 0.0
            if oversold_conditions["rsi_extreme_oversold"]:
                oversold_score += 0.4
            elif oversold_conditions["rsi_oversold"]:
                oversold_score += 0.2

            if oversold_conditions["price_below_lower_bb"]:
                oversold_score += 0.4
            elif oversold_conditions["price_near_lower_bb"]:
                oversold_score += 0.2

            if oversold_conditions["bb_squeeze"]:
                oversold_score += 0.2

            oversold_conditions["oversold_score"] = min(1.0, oversold_score)
            oversold_conditions["condition_type"] = (
                OversoldCondition.EXTREME_OVERSOLD
                if oversold_score >= 0.8
                else (
                    OversoldCondition.MODERATE_OVERSOLD
                    if oversold_score >= 0.5
                    else (
                        OversoldCondition.WEAK_OVERSOLD
                        if oversold_score >= 0.2
                        else None
                    )
                )
            )

            return oversold_conditions

        except Exception as e:
            logger.error("Oversold conditions analysis failed", error=str(e))
            return {}

    async def _detect_capitulation_events(
        self, market_data: MarketData, indicators: Dict[str, Any]
    ) -> List[CapitulationSignal]:
        """Detect capitulation events in the market"""
        try:
            signals = []

            if len(self.sentiment_history) < 5:
                return signals

            # Get recent sentiment and volume data
            recent_sentiment = self.sentiment_history[-5:]
            avg_volume = (
                statistics.mean([s.volatility_index for s in recent_sentiment])
                if recent_sentiment
                else 1.0
            )

            # Check for panic selling (high volume + extreme fear)
            current_sentiment = recent_sentiment[-1]
            if (
                current_sentiment.sentiment_score < self.sentiment_fear_threshold
                and current_sentiment.volatility_index
                > avg_volume * self.capitulation_volume_multiplier
            ):
                signal = CapitulationSignal(
                    event_type=CapitulationEvent.PANIC_SELLING,
                    confidence_score=min(0.9, abs(current_sentiment.sentiment_score)),
                    signal_type="buy",  # Capitulation = buying opportunity
                    price_target=market_data.close * 1.05,  # Expect 5% bounce
                    volume_multiplier=current_sentiment.volatility_index / avg_volume,
                    sentiment_trigger=current_sentiment.sentiment_score,
                    detection_timestamp=market_data.timestamp,
                    supporting_evidence={
                        "fear_greed_index": current_sentiment.fear_greed_index,
                        "volume_spike": current_sentiment.volatility_index,
                        "sentiment_score": current_sentiment.sentiment_score,
                    },
                )
                signals.append(signal)

            # Check for institutional capitulation (large volume at lows)
            price_change_pct = (
                ((market_data.close - market_data.open) / market_data.open) * 100
                if market_data.open != 0
                else 0
            )
            if (
                price_change_pct < -3
                and market_data.volume > avg_volume * 2  # Sharp decline and
                and current_sentiment.sentiment_score < -0.5  # High volume
            ):  # Negative sentiment
                signal = CapitulationSignal(
                    event_type=CapitulationEvent.INSTITUTIONAL_CAPITULATION,
                    confidence_score=0.8,
                    signal_type="buy",
                    price_target=market_data.close * 1.08,  # Expect larger bounce
                    volume_multiplier=market_data.volume / avg_volume,
                    sentiment_trigger=current_sentiment.sentiment_score,
                    detection_timestamp=market_data.timestamp,
                    supporting_evidence={
                        "price_drop_pct": price_change_pct,
                        "volume_ratio": market_data.volume / avg_volume,
                        "rsi": indicators.get("rsi", 50),
                    },
                )
                signals.append(signal)

            # Store signals for pattern analysis
            self.capitulation_history.extend(signals)
            if len(self.capitulation_history) > 50:  # Keep last 50 signals
                self.capitulation_history = self.capitulation_history[-50:]

            return signals

        except Exception as e:
            logger.error("Capitulation detection failed", error=str(e))
            return []

    async def _get_ai_sentiment_insights(
        self, market_data: MarketData, indicators: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get AI-powered sentiment insights for vulture analysis"""
        try:
            # Prepare market context for AI analysis
            market_context = {
                "symbol": market_data.symbol,
                "current_price": float(market_data.close),
                "price_change_pct": (
                    ((market_data.close - market_data.open) / market_data.open) * 100
                    if market_data.open != 0
                    else 0
                ),
                "volume": market_data.volume,
                "indicators": indicators,
                "sentiment_history": (
                    [
                        {
                            "fear_greed": s.fear_greed_index,
                            "sentiment": s.sentiment_score,
                            "vix": s.vix_level,
                        }
                        for s in self.sentiment_history[
                            -10:
                        ]  # Last 10 sentiment readings
                    ]
                    if self.sentiment_history
                    else []
                ),
            }

            # AI analysis for fear detection and capitulation analysis
            analysis_request = AnalysisRequest(
                analysis_type=AnalysisType.PATTERN_RECOGNITION,
                input_data={
                    "market_data": market_context,
                    "analysis_focus": "fear_detection_and_capitulation",
                    "strategy_context": "vulture_contrarian",
                },
                confidence_threshold=0.7,
            )

            ai_response = await self.ai_client.analyze(analysis_request)

            return {
                "fear_level": ai_response.result.get("fear_level", "moderate"),
                "capitulation_probability": ai_response.result.get(
                    "capitulation_probability", 0.5
                ),
                "detected_patterns": ai_response.result.get("key_points", []),
                "market_sentiment": ai_response.result.get("sentiment", "neutral"),
                "overall_confidence": ai_response.confidence_score,
                "ai_reasoning": ai_response.result.get("rationale", ""),
                "processing_time_ms": ai_response.processing_time_ms,
            }

        except Exception as e:
            logger.warning("AI sentiment insights failed", error=str(e))
            return {
                "fear_level": "unknown",
                "capitulation_probability": 0.5,
                "detected_patterns": [],
                "market_sentiment": "neutral",
                "overall_confidence": 0.5,
                "ai_reasoning": "Analysis failed",
                "processing_time_ms": 0,
            }

    async def _calculate_market_fear_metrics(
        self, market_data: MarketData, indicators: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate comprehensive market fear metrics"""
        try:
            if not self.sentiment_history:
                return {}

            # Get recent sentiment data
            recent_sentiment = self.sentiment_history[-10:]

            # Calculate composite fear score
            fear_scores = [s.sentiment_score for s in recent_sentiment]
            fear_greed_scores = [s.fear_greed_index for s in recent_sentiment]

            avg_fear = statistics.mean(fear_scores) if fear_scores else 0
            avg_fear_greed = (
                statistics.mean(fear_greed_scores) if fear_greed_scores else 50
            )

            # Normalize fear score (-1 to 1) to fear level (0 to 1)
            composite_fear_score = (avg_fear + 1) / 2  # Convert -1,1 to 0,1

            # Calculate volatility from price action
            if len(recent_sentiment) >= 2:
                volatility_changes = []
                for i in range(1, len(recent_sentiment)):
                    change = abs(
                        recent_sentiment[i].volatility_index
                        - recent_sentiment[i - 1].volatility_index
                    )
                    volatility_changes.append(change)

                volatility = (
                    statistics.mean(volatility_changes) if volatility_changes else 0
                )
            else:
                volatility = 0

            # Calculate liquidity score (inverse of volatility)
            liquidity_score = max(0, 1 - (volatility / 50))  # Normalize

            return {
                "composite_fear_score": composite_fear_score,
                "average_fear_greed": avg_fear_greed,
                "volatility": volatility,
                "liquidity_score": liquidity_score,
                "fear_trend": (
                    "increasing" if fear_scores[-1] < fear_scores[0] else "decreasing"
                ),
                "capitulation_risk": (
                    "high"
                    if composite_fear_score > 0.7
                    else "medium" if composite_fear_score > 0.5 else "low"
                ),
            }

        except Exception as e:
            logger.error("Market fear metrics calculation failed", error=str(e))
            return {}

    async def generate_signals(self, analysis: MarketAnalysis) -> List[TradingSignal]:
        """
        Generate contrarian signals with comprehensive error handling

        Args:
            analysis: Market analysis results

        Returns:
            List of trading signals

        Raises:
            SignalGenerationError: If signal generation fails
            VultureStrategyError: If circuit breaker is active
        """
        try:
            # Check circuit breaker
            if self.circuit_breaker_active:
                raise VultureStrategyError(
                    f"Circuit breaker active: {self.circuit_breaker_reason}"
                )

            # Validate analysis input
            if not analysis or not hasattr(analysis, "symbol"):
                raise ValidationError("Invalid analysis input")

            self.current_phase = StrategyPhase.SIGNAL_GENERATION
            signals = []

            # Check if we have minimum required data
            if not self.sentiment_history:
                logger.warning("No sentiment data available for signal generation")
                return signals

            # Detect capitulation events with error recovery
            try:
                capitulation_signals = await self._detect_capitulation_events(
                    type(
                        "MarketData",
                        (),
                        {
                            "symbol": analysis.symbol,
                            "timestamp": datetime.utcnow(),
                            "close": 100.0,  # Placeholder
                            "open": 100.0,
                            "volume": 1000,
                        },
                    )(),
                    analysis.indicators,
                )
            except Exception as e:
                logger.warning(
                    "Capitulation detection failed, using empty list", error=str(e)
                )
                capitulation_signals = []

            # Generate vulture opportunities from capitulation signals
            for cap_signal in capitulation_signals:
                try:
                    if cap_signal.confidence_score >= self.min_confidence_threshold:
                        opportunity = await self._create_vulture_opportunity(
                            cap_signal, analysis
                        )

                        if (
                            opportunity
                            and opportunity.confidence_score
                            >= self.min_confidence_threshold
                        ):
                            # Convert opportunity to trading signal
                            signal = await self._convert_opportunity_to_signal(
                                opportunity, analysis
                            )

                            if signal:
                                signals.append(signal)
                                # Track opportunity
                                self.active_opportunities[signal.signal_id] = (
                                    opportunity
                                )

                except Exception as e:
                    logger.warning(
                        "Failed to process capitulation signal",
                        signal_id=id(cap_signal),
                        error=str(e),
                    )
                    continue

            # Generate mean reversion signals from oversold conditions
            try:
                mean_reversion_signals = await self._generate_mean_reversion_signals(
                    analysis
                )
                signals.extend(mean_reversion_signals)
            except Exception as e:
                logger.warning("Mean reversion signal generation failed", error=str(e))

            # Filter signals by confidence and limit active opportunities
            signals = [
                s for s in signals if s.strength >= self.min_confidence_threshold
            ]

            # Limit to high-confidence signals only
            signals = sorted(signals, key=lambda s: s.strength, reverse=True)[
                : self.max_active_opportunities
            ]

            # Update active opportunities
            for signal in signals:
                if signal.signal_id not in self.active_opportunities:
                    # Create opportunity from signal
                    opportunity = await self._create_opportunity_from_signal(
                        signal, analysis
                    )
                    if opportunity:
                        self.active_opportunities[signal.signal_id] = opportunity

            logger.info(
                "Signals generated successfully",
                signal_count=len(signals),
                capitulation_signals=len(capitulation_signals),
                active_opportunities=len(self.active_opportunities),
            )

            return signals

        except (ValidationError, VultureStrategyError) as e:
            logger.warning(
                "Signal generation validation/circuit breaker error", error=str(e)
            )
            raise
        except Exception as e:
            logger.error("Signal generation failed", error=str(e))
            raise SignalGenerationError(f"Failed to generate signals: {str(e)}")

    async def _create_vulture_opportunity(
        self, capitulation_signal: CapitulationSignal, analysis: MarketAnalysis
    ) -> Optional[VultureOpportunity]:
        """Create a vulture opportunity from capitulation signal"""
        try:
            # Use current market price as entry (would be from market data in real implementation)
            current_price = 100.0  # Placeholder - should come from market data

            # Determine signal type (always BUY for vulture - we buy fear)
            signal_type = MeanReversionSignal.BOUNCE_FROM_LOW

            # Calculate position sizing based on fear level and confidence
            base_position_size = 0.03  # Conservative sizing
            fear_multiplier = min(
                2.0, (abs(capitulation_signal.sentiment_trigger) - 0.5) * 4
            )  # More fear = larger position
            confidence_multiplier = capitulation_signal.confidence_score
            position_size_percentage = (
                base_position_size * fear_multiplier * confidence_multiplier
            )

            # Risk management - wider stops for contrarian trades
            stop_loss_distance = current_price * 0.05  # 5% stop loss
            stop_loss_price = current_price - stop_loss_distance

            # Profit targets - multiple levels for mean reversion
            profit_targets = [
                current_price * (1 + target / 100)
                for target in self.conservative_profit_targets
            ]
            take_profit_price = profit_targets[0]  # First profit target

            # Calculate risk-reward ratio
            risk = current_price - stop_loss_price
            reward = take_profit_price - current_price
            risk_reward_ratio = reward / risk if risk > 0 else 0

            # Estimate holding period based on signal type
            holding_period_days = (
                5
                if capitulation_signal.event_type == CapitulationEvent.PANIC_SELLING
                else 10
            )

            # Create opportunity
            opportunity = VultureOpportunity(
                signal_type=signal_type,
                entry_price=current_price,
                stop_loss_price=stop_loss_price,
                take_profit_price=take_profit_price,
                position_size_percentage=position_size_percentage,
                confidence_score=capitulation_signal.confidence_score,
                risk_reward_ratio=risk_reward_ratio,
                estimated_profit_potential=(reward / current_price) * 100,  # Percentage
                holding_period_days=holding_period_days,
                expiry_seconds=holding_period_days * 24 * 60 * 60,  # Convert to seconds
                reasoning=f"Capitulation detected: {capitulation_signal.event_type.value}. Buying extreme fear with {capitulation_signal.confidence_score:.2f} confidence.",
                market_conditions={
                    "fear_level": analysis.sentiment_score,
                    "volatility": analysis.volatility,
                    "liquidity": analysis.liquidity_score,
                    "capitulation_type": capitulation_signal.event_type.value,
                },
            )

            return opportunity

        except Exception as e:
            logger.error("Failed to create vulture opportunity", error=str(e))
            return None

    async def _generate_mean_reversion_signals(
        self, analysis: MarketAnalysis
    ) -> List[TradingSignal]:
        """Generate mean reversion signals from oversold conditions"""
        try:
            signals = []

            # Check oversold conditions from analysis
            indicators = analysis.indicators or {}
            rsi_value = indicators.get("rsi", 50)

            if rsi_value < self.min_oversold_rsi:
                # Create mean reversion signal
                current_price = 100.0  # Placeholder

                signal = TradingSignal(
                    strategy_id=self.strategy_id,
                    symbol=analysis.symbol,
                    signal_type=SignalType.BUY,
                    strength=min(
                        0.9, (self.min_oversold_rsi - rsi_value) / 30
                    ),  # Strength based on how oversold
                    entry_price=current_price,
                    stop_loss_price=current_price * 0.95,  # 5% stop loss
                    take_profit_price=current_price * 1.10,  # 10% profit target
                    position_size_percentage=0.025,  # Conservative size
                    quantity=100,  # Placeholder
                    reasoning=f"RSI oversold at {rsi_value:.1f}. Mean reversion expected.",
                    supporting_data={
                        "signal_type": "rsi_mean_reversion",
                        "rsi_value": rsi_value,
                        "oversold_threshold": self.min_oversold_rsi,
                        "ai_confidence": analysis.ai_insights.get(
                            "overall_confidence", 0.5
                        ),
                    },
                    expiry_minutes=24 * 60,  # 24 hours
                )

                signals.append(signal)

            return signals

        except Exception as e:
            logger.error("Mean reversion signal generation failed", error=str(e))
            return []

    async def _convert_opportunity_to_signal(
        self, opportunity: VultureOpportunity, analysis: MarketAnalysis
    ) -> Optional[TradingSignal]:
        """Convert vulture opportunity to trading signal"""
        try:
            # Calculate quantity (placeholder - would be calculated based on position size)
            quantity = int(
                (opportunity.position_size_percentage * 100000)
                / opportunity.entry_price
            )  # Assume ₹1L portfolio

            signal = TradingSignal(
                strategy_id=self.strategy_id,
                symbol=analysis.symbol,
                signal_type=SignalType.BUY,  # Vulture always buys
                strength=opportunity.confidence_score,
                entry_price=opportunity.entry_price,
                stop_loss_price=opportunity.stop_loss_price,
                take_profit_price=opportunity.take_profit_price,
                position_size_percentage=opportunity.position_size_percentage,
                quantity=quantity,
                reasoning=opportunity.reasoning,
                supporting_data={
                    "opportunity_type": opportunity.signal_type.value,
                    "risk_reward_ratio": opportunity.risk_reward_ratio,
                    "estimated_profit_pct": opportunity.estimated_profit_potential,
                    "holding_period_days": opportunity.holding_period_days,
                    "market_conditions": opportunity.market_conditions,
                    "ai_confidence": analysis.ai_insights.get(
                        "overall_confidence", 0.5
                    ),
                },
                expiry_minutes=opportunity.expiry_seconds // 60,
            )

            return signal

        except Exception as e:
            logger.error("Failed to convert opportunity to signal", error=str(e))
            return None

    async def _create_opportunity_from_signal(
        self, signal: TradingSignal, analysis: MarketAnalysis
    ) -> Optional[VultureOpportunity]:
        """Create opportunity from trading signal"""
        try:
            # Extract holding period from signal data
            holding_period_days = signal.supporting_data.get("holding_period_days", 5)

            opportunity = VultureOpportunity(
                signal_type=MeanReversionSignal.BOUNCE_FROM_LOW,
                entry_price=signal.entry_price,
                stop_loss_price=signal.stop_loss_price,
                take_profit_price=signal.take_profit_price,
                position_size_percentage=signal.position_size_percentage,
                confidence_score=signal.strength,
                risk_reward_ratio=signal.supporting_data.get("risk_reward_ratio", 2.0),
                estimated_profit_potential=signal.supporting_data.get(
                    "estimated_profit_pct", 5.0
                ),
                holding_period_days=holding_period_days,
                expiry_seconds=holding_period_days * 24 * 60 * 60,
                reasoning=signal.reasoning,
                market_conditions=signal.supporting_data.get("market_conditions", {}),
            )

            return opportunity

        except Exception as e:
            logger.error("Failed to create opportunity from signal", error=str(e))
            return None

    async def calculate_position_size(self, signal: TradingSignal, portfolio) -> float:
        """
        Calculate position size with vulture-specific conservative risk management

        Args:
            signal: Trading signal
            portfolio: Current portfolio state

        Returns:
            Position size as percentage of portfolio
        """
        try:
            # Base position size from signal
            base_size = signal.position_size_percentage

            # Vulture strategy adjustments - more conservative
            fear_multiplier = 0.7  # Reduce size in fearful markets
            confidence_multiplier = signal.strength

            # Adjust based on market volatility
            volatility = self.last_analysis.get(
                signal.symbol, MarketAnalysis(symbol=signal.symbol)
            ).volatility
            volatility_multiplier = max(
                0.5, 1.0 - volatility
            )  # More conservative in high volatility

            # Adjust based on portfolio risk
            portfolio_risk_multiplier = 1.0
            if (
                hasattr(portfolio, "current_drawdown")
                and portfolio.current_drawdown > 0.05
            ):
                portfolio_risk_multiplier = 0.8  # Slightly reduce in portfolio drawdown

            # Calculate final position size
            position_size = (
                base_size
                * fear_multiplier
                * confidence_multiplier
                * volatility_multiplier
                * portfolio_risk_multiplier
            )

            # Ensure within strategy limits (even more conservative than base)
            position_size = min(position_size, self.config.max_position_size * 0.8)
            position_size = max(position_size, 0.005)  # Minimum 0.5% position

            logger.debug(
                "Position size calculated",
                signal_id=signal.signal_id,
                base_size=base_size,
                final_size=position_size,
                adjustments={
                    "fear": fear_multiplier,
                    "confidence": confidence_multiplier,
                    "volatility": volatility_multiplier,
                    "portfolio": portfolio_risk_multiplier,
                },
            )

            return position_size

        except Exception as e:
            logger.error("Position size calculation failed", error=str(e))
            return signal.position_size_percentage * 0.5  # Conservative fallback

    async def manage_risk(self, portfolio) -> List[str]:
        """
        Enhanced risk management for vulture strategy

        Args:
            portfolio: Current portfolio state

        Returns:
            List of risk management actions taken
        """
        try:
            actions_taken = await super().manage_risk(portfolio)

            # Vulture-specific risk checks
            current_positions = len(self.active_positions)

            # Emergency stop if too many concurrent positions
            if current_positions > self.max_concurrent_positions:
                actions_taken.append("vulture_concurrent_position_limit")
                await self._emergency_stop("Too many concurrent vulture positions")

            # Check for sentiment improvement (contrarian exit signal)
            if self.sentiment_history:
                recent_sentiment = self.sentiment_history[-1]
                if recent_sentiment.sentiment_score > -0.2:  # Sentiment improving
                    # Consider reducing positions as fear subsides
                    actions_taken.append("sentiment_improvement")
                    # Reduce position sizes for remaining opportunities
                    for opp in self.active_opportunities.values():
                        opp.position_size_percentage *= 0.9

            # Check signal quality degradation
            if len(self.active_opportunities) > 5:
                avg_confidence = sum(
                    opp.confidence_score for opp in self.active_opportunities.values()
                ) / len(self.active_opportunities)
                if avg_confidence < 0.7:
                    actions_taken.append("vulture_low_signal_quality")
                    # Reduce position sizes for remaining opportunities
                    for opp in self.active_opportunities.values():
                        opp.position_size_percentage *= 0.8

            return actions_taken

        except Exception as e:
            logger.error("Vulture risk management failed", error=str(e))
            raise RiskManagementError(f"Vulture risk management failed: {str(e)}")

    async def _emergency_stop(self, reason: str):
        """Emergency stop for vulture strategy"""
        try:
            logger.warning("Vulture emergency stop triggered", reason=reason)

            # Close all active positions immediately
            for position_id in list(self.active_positions.keys()):
                await self._close_position(position_id, f"emergency_stop: {reason}")

            # Clear all active opportunities
            self.active_opportunities.clear()

            # Update status
            self.status = self.status.PAUSED

            # Log emergency action
            self.log_strategy_event(
                "emergency_stop",
                {"reason": reason, "timestamp": datetime.utcnow().isoformat()},
            )

        except Exception as e:
            logger.error("Emergency stop failed", error=str(e))

    async def update_performance(self, trade_result: Dict[str, Any]):
        """Update vulture-specific performance metrics"""
        try:
            await super().update_performance(trade_result)

            # Update vulture-specific stats
            self.vulture_stats["total_opportunities"] += 1

            pnl = trade_result.get("pnl", 0.0)
            if pnl > 0:
                self.vulture_stats["successful_trades"] += 1
            else:
                self.vulture_stats["failed_trades"] += 1

            # Update win rate
            total_trades = (
                self.vulture_stats["successful_trades"]
                + self.vulture_stats["failed_trades"]
            )
            if total_trades > 0:
                self.vulture_stats["win_rate"] = (
                    self.vulture_stats["successful_trades"] / total_trades
                )

            # Update average profit
            if total_trades > 0:
                # This is a simplified calculation - in reality would track all P&L
                self.vulture_stats["average_profit_per_trade"] = (
                    self.performance.total_return / total_trades
                )

            # Update max drawdown (simplified)
            if pnl < 0:
                self.vulture_stats["max_drawdown"] = max(
                    self.vulture_stats["max_drawdown"], abs(pnl)
                )

            logger.debug("Vulture performance updated", stats=self.vulture_stats)

        except Exception as e:
            logger.error("Vulture performance update failed", error=str(e))

    async def health_check(self) -> Dict[str, Any]:
        """Enhanced health check with comprehensive monitoring"""
        try:
            base_health = await super().health_check()

            # Get circuit breaker status
            circuit_breaker_status = await self._check_circuit_breaker_status()

            # Get resource usage
            resource_usage = await self.get_resource_usage()

            # Add vulture-specific health metrics
            vulture_health = {
                "sentiment_data_available": bool(self.sentiment_history),
                "sentiment_history_size": len(self.sentiment_history),
                "capitulation_history_size": len(self.capitulation_history),
                "ai_client_connected": (
                    self.ai_client.is_connected if self.ai_client else False
                ),
                "vulture_stats": self.vulture_stats,
                "signal_quality": {
                    "avg_confidence": (
                        sum(
                            opp.confidence_score
                            for opp in self.active_opportunities.values()
                        )
                        / len(self.active_opportunities)
                        if self.active_opportunities
                        else 0
                    ),
                    "opportunities_count": len(self.active_opportunities),
                    "max_opportunities_limit": self.max_active_opportunities,
                },
                "performance_metrics": {
                    "win_rate": self.vulture_stats.get("win_rate", 0),
                    "total_opportunities": self.vulture_stats.get(
                        "total_opportunities", 0
                    ),
                    "avg_profit_per_trade": self.vulture_stats.get(
                        "average_profit_per_trade", 0
                    ),
                    "max_drawdown": self.vulture_stats.get("max_drawdown", 0),
                    "capitulation_accuracy": self.vulture_stats.get(
                        "capitulation_accuracy", 0
                    ),
                },
                "market_fear_indicators": {
                    "current_fear_level": (
                        self.sentiment_history[-1].sentiment_score
                        if self.sentiment_history
                        else 0
                    ),
                    "fear_trend": (
                        "increasing"
                        if len(self.sentiment_history) >= 2
                        and self.sentiment_history[-1].sentiment_score
                        < self.sentiment_history[-2].sentiment_score
                        else "stable"
                    ),
                },
            }

            # Add circuit breaker information
            vulture_health.update(
                {
                    "circuit_breaker": circuit_breaker_status,
                    "consecutive_failures": self.consecutive_failures,
                    "max_consecutive_failures": self.max_consecutive_failures,
                }
            )

            # Add resource monitoring
            vulture_health["resources"] = resource_usage

            # Determine overall health with more sophisticated logic
            health_score = 0

            # Sentiment data availability (20 points)
            if self.sentiment_history:
                health_score += 20
                # Recent sentiment data (additional 10 points)
                if len(self.sentiment_history) >= 10:
                    health_score += 10

            # AI client connection (15 points)
            if vulture_health["ai_client_connected"]:
                health_score += 15

            # Circuit breaker status (20 points)
            if not circuit_breaker_status.get("active", False):
                health_score += 20

            # Active opportunities within limits (10 points)
            if len(self.active_opportunities) <= self.max_active_opportunities:
                health_score += 10

            # Performance metrics (15 points)
            win_rate = self.vulture_stats.get("win_rate", 0)
            if win_rate >= 0.6:  # At least 60% win rate for contrarian strategy
                health_score += 15
            elif win_rate >= 0.4:  # At least 40% win rate
                health_score += 10

            # Resource usage (10 points)
            memory_mb = resource_usage.get("memory_usage_estimate", 0) / (1024 * 1024)
            if memory_mb < 50:  # Less than 50MB for vulture
                health_score += 10

            # Determine health status based on score
            if health_score >= 80:
                vulture_health_status = "healthy"
            elif health_score >= 60:
                vulture_health_status = "degraded"
            elif health_score >= 40:
                vulture_health_status = "unhealthy"
            else:
                vulture_health_status = "critical"

            base_health.update(
                {
                    "vulture_health": vulture_health,
                    "vulture_status": vulture_health_status,
                    "health_score": health_score,
                    "last_sentiment_update": (
                        self.sentiment_history[-1].timestamp.isoformat()
                        if self.sentiment_history
                        else None
                    ),
                    "last_health_check": datetime.utcnow().isoformat(),
                }
            )

            # Log health issues
            if vulture_health_status in ["unhealthy", "critical"]:
                logger.warning(
                    "Vulture strategy health issues detected",
                    status=vulture_health_status,
                    score=health_score,
                    circuit_breaker=circuit_breaker_status.get("active", False),
                )

            return base_health

        except Exception as e:
            logger.error("Vulture health check failed", error=str(e))
            return {
                "status": "critical",
                "error": str(e),
                "strategy_id": self.strategy_id,
                "timestamp": datetime.utcnow().isoformat(),
            }

    # Additional vulture-specific methods

    async def get_sentiment_analysis_summary(self) -> Dict[str, Any]:
        """Get summary of sentiment analysis"""
        try:
            if not self.sentiment_history:
                return {"total_readings": 0, "current_fear_level": "unknown"}

            # Analyze sentiment patterns
            fear_scores = [s.sentiment_score for s in self.sentiment_history]
            fear_greed_scores = [s.fear_greed_index for s in self.sentiment_history]

            avg_fear = statistics.mean(fear_scores) if fear_scores else 0
            avg_fear_greed = (
                statistics.mean(fear_greed_scores) if fear_greed_scores else 50
            )

            # Determine current fear level
            current_fear = self.sentiment_history[-1].sentiment_score
            if current_fear < -0.7:
                fear_level = "extreme_fear"
            elif current_fear < -0.5:
                fear_level = "high_fear"
            elif current_fear < -0.3:
                fear_level = "moderate_fear"
            elif current_fear > 0.5:
                fear_level = "greed"
            else:
                fear_level = "neutral"

            return {
                "total_readings": len(self.sentiment_history),
                "current_fear_level": fear_level,
                "average_fear_score": avg_fear,
                "average_fear_greed_index": avg_fear_greed,
                "fear_trend": (
                    "increasing" if fear_scores[-1] < fear_scores[0] else "decreasing"
                ),
                "capitulation_opportunities": len(
                    [
                        s
                        for s in self.sentiment_history
                        if s.sentiment_score < self.sentiment_fear_threshold
                    ]
                ),
            }

        except Exception as e:
            logger.error("Failed to get sentiment summary", error=str(e))
            return {"error": str(e)}

    async def get_capitulation_performance(self) -> Dict[str, Any]:
        """Get detailed capitulation detection performance"""
        try:
            return {
                "performance_stats": self.vulture_stats,
                "active_opportunities": len(self.active_opportunities),
                "capitulation_success_rate": self._calculate_capitulation_success_rate(),
                "fear_accuracy": self._calculate_fear_prediction_accuracy(),
                "risk_metrics": {
                    "max_drawdown": self.vulture_stats["max_drawdown"],
                    "avg_holding_period": self.vulture_stats["average_holding_period"],
                    "risk_adjusted_return": self._calculate_risk_adjusted_return(),
                },
            }

        except Exception as e:
            logger.error("Failed to get capitulation performance", error=str(e))
            return {"error": str(e)}

    def _calculate_capitulation_success_rate(self) -> float:
        """Calculate success rate of capitulation signals"""
        if not self.capitulation_history:
            return 0.0

        # Simplified - in reality would track which capitulation signals led to successful trades
        successful_capitulations = len(
            [c for c in self.capitulation_history if c.confidence_score > 0.8]
        )
        return successful_capitulations / len(self.capitulation_history)

    def _calculate_fear_prediction_accuracy(self) -> float:
        """Calculate accuracy of fear level predictions"""
        # Simplified calculation
        if len(self.sentiment_history) < 5:
            return 0.5

        # Check if fear predictions were accurate (simplified)
        accurate_predictions = 0
        total_predictions = 0

        for i in range(4, len(self.sentiment_history)):
            # Check if sentiment trend was predicted correctly
            predicted_trend = (
                self.sentiment_history[i - 4].sentiment_score
                < self.sentiment_history[i - 2].sentiment_score
            )
            actual_trend = (
                self.sentiment_history[i - 2].sentiment_score
                < self.sentiment_history[i].sentiment_score
            )

            if predicted_trend == actual_trend:
                accurate_predictions += 1
            total_predictions += 1

        return (
            accurate_predictions / total_predictions if total_predictions > 0 else 0.5
        )

    def _calculate_risk_adjusted_return(self) -> float:
        """Calculate risk-adjusted return metric"""
        if (
            not self.vulture_stats["total_opportunities"]
            or self.vulture_stats["max_drawdown"] == 0
        ):
            return 0.0

        total_return = self.performance.total_return
        return total_return / self.vulture_stats["max_drawdown"]

    # Resource Management and Cleanup Methods

    async def cleanup(self):
        """
        Comprehensive cleanup of resources

        Ensures all connections are properly closed and resources are freed
        """
        try:
            logger.info("Starting Vulture strategy cleanup")

            # Close AI client connection
            if self.ai_client:
                try:
                    await self.ai_client.disconnect()
                    logger.debug("AI client disconnected")
                except Exception as e:
                    logger.warning("Failed to disconnect AI client", error=str(e))

            # Clear active opportunities
            self.active_opportunities.clear()

            # Clear sentiment and capitulation history to free memory
            self.sentiment_history.clear()
            self.capitulation_history.clear()

            # Reset circuit breaker
            await self._deactivate_circuit_breaker()

            # Call parent cleanup
            await super().cleanup()

            logger.info("Vulture strategy cleanup completed")

        except Exception as e:
            logger.error("Vulture strategy cleanup failed", error=str(e))
            raise ResourceError(f"Cleanup failed: {str(e)}")

    async def __aenter__(self):
        """Async context manager entry"""
        try:
            initialized = await self.initialize()
            if not initialized:
                raise ResourceError("Failed to initialize strategy in context manager")
            return self
        except Exception as e:
            logger.error("Failed to enter strategy context", error=str(e))
            raise

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        try:
            await self.cleanup()
        except Exception as e:
            logger.error("Failed to exit strategy context cleanly", error=str(e))
            # Don't raise cleanup errors in context manager exit

    def __del__(self):
        """Destructor for emergency cleanup"""
        try:
            # Schedule cleanup if event loop is running
            if hasattr(asyncio, "_get_running_loop"):
                try:
                    loop = asyncio._get_running_loop()
                    if loop and not loop.is_closed():
                        loop.create_task(self.cleanup())
                except RuntimeError:
                    pass  # No running loop
        except Exception as e:
            # Last resort logging
            print(f"Emergency cleanup failed: {str(e)}")

    async def get_resource_usage(self) -> Dict[str, Any]:
        """Get current resource usage statistics"""
        try:
            return {
                "sentiment_history_size": len(self.sentiment_history),
                "capitulation_history_size": len(self.capitulation_history),
                "active_opportunities_count": len(self.active_opportunities),
                "circuit_breaker_active": self.circuit_breaker_active,
                "consecutive_failures": self.consecutive_failures,
                "memory_usage_estimate": self._estimate_memory_usage(),
            }
        except Exception as e:
            logger.error("Failed to get resource usage", error=str(e))
            return {"error": str(e)}

    def _estimate_memory_usage(self) -> int:
        """Estimate memory usage in bytes"""
        try:
            # Rough estimation
            base_usage = 1024 * 1024  # 1MB base
            sentiment_usage = (
                len(self.sentiment_history) * 256
            )  # ~256B per sentiment snapshot
            capitulation_usage = (
                len(self.capitulation_history) * 512
            )  # ~512B per capitulation signal
            opportunities_usage = (
                len(self.active_opportunities) * 1024
            )  # ~1KB per opportunity

            return (
                base_usage + sentiment_usage + capitulation_usage + opportunities_usage
            )
        except Exception:
            return 0

    async def optimize_resources(self):
        """Optimize resource usage by cleaning up old data"""
        try:
            current_time = datetime.utcnow()

            # Clean up old sentiment history (keep last 24 hours)
            cutoff_time = current_time.replace(hour=current_time.hour - 24)
            self.sentiment_history = [
                s for s in self.sentiment_history if s.timestamp > cutoff_time
            ]

            # Clean up old capitulation history (keep last 100)
            if len(self.capitulation_history) > 100:
                self.capitulation_history = self.capitulation_history[-100:]

            # Clean up expired opportunities
            expired_opportunities = []
            for opp_id, opportunity in self.active_opportunities.items():
                if (
                    current_time - opportunity.expiry_seconds
                ).seconds > opportunity.expiry_seconds:
                    expired_opportunities.append(opp_id)

            for opp_id in expired_opportunities:
                del self.active_opportunities[opp_id]

            logger.debug(
                "Resource optimization completed",
                cleaned_opportunities=len(expired_opportunities),
            )

        except Exception as e:
            logger.error("Resource optimization failed", error=str(e))


# Factory function for creating vulture strategy instances
def create_vulture_strategy(
    config: StrategyConfig, learning_engine=None
) -> VultureStrategy:
    """
    Create a Vulture strategy instance

    Args:
        config: Strategy configuration
        learning_engine: Optional learning engine

    Returns:
        VultureStrategy: Configured vulture strategy instance
    """
    return VultureStrategy(config, learning_engine)


# Example usage and testing functions
async def example_vulture_usage():
    """Example usage of the Vulture strategy"""

    # Create strategy configuration
    config = StrategyConfig(
        name="NIRAJ Vulture Strategy",
        description="Contrarian fear exploitation strategy",
        strategy_type=StrategyType.PSYCHOLOGICAL,
        max_position_size=0.05,  # Conservative sizing
        max_drawdown_limit=0.08,  # Tighter drawdown limit
        stop_loss_percentage=0.03,  # Tighter stops
        take_profit_percentage=0.08,  # Higher targets for mean reversion
        min_signal_strength=0.75,  # High conviction required
        max_trades_per_day=5,  # Low frequency
        supported_symbols=["NIFTY", "BANKNIFTY"],
        custom_params={
            "min_oversold_rsi": 25,
            "sentiment_fear_threshold": -0.7,
            "capitulation_volume_multiplier": 2.5,
            "min_confidence": 0.75,
        },
    )

    # Create strategy instance
    vulture = create_vulture_strategy(config)

    try:
        # Initialize strategy
        initialized = await vulture.initialize()
        if not initialized:
            print("Failed to initialize vulture strategy")
            return

        print("Vulture strategy initialized successfully")

        # Example market data
        class MockMarketData:
            def __init__(self):
                self.symbol = "NIFTY"
                self.timestamp = datetime.utcnow()
                self.open = 18000.0
                self.high = 18100.0
                self.low = 17900.0
                self.close = 17950.0  # Down day
                self.volume = 250000

        market_data = MockMarketData()

        # Analyze market
        analysis = await vulture.analyze_market(market_data)
        print(
            f"Market analysis completed with fear score: {analysis.sentiment_score:.3f}"
        )

        # Generate signals
        signals = await vulture.generate_signals(analysis)
        print(f"Generated {len(signals)} contrarian signals")

        for signal in signals:
            print(
                f"Signal: {signal.signal_type.value} {signal.symbol} at {signal.entry_price} (strength: {signal.strength:.3f})"
            )

        # Health check
        health = await vulture.health_check()
        print(f"Strategy health: {health['status']}")

        # Cleanup
        await vulture.cleanup()

    except Exception as e:
        print(f"Error in vulture strategy example: {str(e)}")


if __name__ == "__main__":
    # Run example usage
    asyncio.run(example_vulture_usage())
