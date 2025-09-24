"""
Time Arbitrage Strategy Implementation for NIRAJ Trading System

Quantitative strategy that exploits time-based market inefficiencies by identifying
discrepancies between different time frames and temporal patterns. This strategy
capitalizes on predictable price movements that occur at specific times or intervals.

Key Features:
- Multi-timeframe analysis and statistical arbitrage
- Intraday momentum vs daily trend discrepancies
- Opening range breakout detection and exploitation
- Time-based mean reversion patterns
- Calendar effect and seasonal pattern recognition
- Statistical arbitrage between time frames
- Advanced temporal risk management
- AI-powered time pattern recognition
"""

import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import structlog
import uuid
import statistics
import math

try:
    from ..core.config import get_config
    from ..models.strategy import StrategyConfig, StrategyType
    from ..models.strategy_signal import SignalType
    from ..models.market_data import MarketData
    from ..models.technical_indicator import IndicatorType
    from ..utils.technical_indicators import TechnicalIndicatorsCalculator
    from ..ai.gemma3_integration import Gemma3Client, AnalysisType, AnalysisRequest
    from ..ai.confidence_tracker import AdvancedConfidenceTracker
    from .base_strategy import (
        BaseStrategy,
        MarketAnalysis,
        TradingSignal,
        StrategyPhase,
        SignalGenerationError,
        RiskManagementError
    )
except ImportError as e:
    # Handle imports for isolated testing - define minimal interfaces
    print(f"Some imports failed, using minimal interfaces: {str(e)}")

    # Mock get_config function
    def get_config(key: str, default=None):
        """Mock configuration getter for testing"""
        config_defaults = {
            'strategy.time.min_timeframe_divergence': 0.5,
            'strategy.time.max_timeframe_correlation': 0.8,
            'strategy.time.opening_range_percentage': 0.02,
            'strategy.time.momentum_threshold': 1.5,
            'strategy.time.mean_reversion_lookback': 10,
            'strategy.time.min_confidence': 0.75,
            'strategy.time.max_history_size': 500,
            'strategy.time.pattern_recognition_window': 100,
            'strategy.time.max_active_opportunities': 5,
            'strategy.time.max_concurrent_positions': 3,
            'strategy.time.emergency_stop_multiplier': 1.8,
            'strategy.time.profit_targets': [2.0, 4.0, 6.0, 8.0, 10.0],
            'strategy.time.max_consecutive_failures': 4
        }
        return config_defaults.get(key, default)

    # Define minimal required classes
    class StrategyType(str, Enum):
        QUANTITATIVE = "quantitative"

    @dataclass
    class StrategyConfig:
        name: str = ""
        description: str = ""
        strategy_type: StrategyType = StrategyType.QUANTITATIVE
        max_position_size: float = 0.04
        max_drawdown_limit: float = 0.06
        stop_loss_percentage: float = 0.025
        take_profit_percentage: float = 0.06
        min_signal_strength: float = 0.75
        max_trades_per_day: int = 8
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
                result = {'confidence': 0.5, 'key_points': [], 'risk_level': 'medium', 'rationale': 'Mock response'}
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
        MOMENTUM = "momentum"
        RSI = "rsi"
        MACD = "macd"
        BOLLINGER_BANDS = "bollinger_bands"
        MOVING_AVERAGE = "moving_average"

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
            self.status = type('Status', (), {'ACTIVE': 'active', 'PAUSED': 'paused'})()
            self.current_phase = StrategyPhase.INITIALIZING
            self.active_positions = {}
            self.performance = type('Performance', (), {
                'total_return': 0.0,
                'total_trades': 0,
                'win_rate': 0.0
            })()
            self.last_analysis = {}

        async def initialize(self):
            return True

        async def manage_risk(self, portfolio):
            return []

        async def update_performance(self, trade_result):
            pass

        async def health_check(self):
            return {'status': 'unknown'}

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


# Custom Exception Types for Time Arbitrage Strategy
class TimeArbitrageError(Exception):
    """Base exception for Time arbitrage strategy errors"""
    pass


class ConfigurationError(TimeArbitrageError):
    """Configuration validation errors"""
    pass


class ValidationError(TimeArbitrageError):
    """Input validation errors"""
    pass


class TimeframeAnalysisError(TimeArbitrageError):
    """Timeframe analysis related errors"""
    pass


class StatisticalArbitrageError(TimeArbitrageError):
    """Statistical arbitrage calculation errors"""
    pass


class PatternRecognitionError(TimeArbitrageError):
    """Pattern recognition errors"""
    pass


class ResourceError(TimeArbitrageError):
    """Resource management errors"""
    pass


# Validation utilities
class TimeArbitrageValidator:
    """Comprehensive validation utilities for Time arbitrage strategy"""

    @staticmethod
    def validate_market_data(market_data) -> None:
        """Validate market data input"""
        if not market_data:
            raise ValidationError("Market data cannot be None")

        required_attrs = ['symbol', 'timestamp', 'close', 'volume']
        for attr in required_attrs:
            if not hasattr(market_data, attr):
                raise ValidationError(f"Market data missing required attribute: {attr}")

        if not isinstance(market_data.symbol, str) or not market_data.symbol.strip():
            raise ValidationError("Invalid symbol in market data")

        if not isinstance(market_data.close, (int, float)) or market_data.close <= 0:
            raise ValidationError("Invalid close price in market data")

        if not isinstance(market_data.volume, (int, float)) or market_data.volume < 0:
            raise ValidationError("Invalid volume in market data")

        # Validate timestamp is not in future (with 1 minute tolerance)
        if market_data.timestamp > datetime.utcnow() + timedelta(minutes=1):
            raise ValidationError("Market data timestamp cannot be in the future")

    @staticmethod
    def validate_config(config) -> None:
        """Validate strategy configuration"""
        if not config:
            raise ConfigurationError("Strategy configuration cannot be None")

        if config.strategy_type not in [StrategyType.QUANTITATIVE]:
            raise ConfigurationError(f"Invalid strategy type: {config.strategy_type}. Expected QUANTITATIVE")

        if not isinstance(config.max_position_size, (int, float)) or not (0 < config.max_position_size <= 0.1):
            raise ConfigurationError("max_position_size must be between 0 and 0.1")

        if not isinstance(config.max_drawdown_limit, (int, float)) or not (0 < config.max_drawdown_limit <= 0.1):
            raise ConfigurationError("max_drawdown_limit must be between 0 and 0.1")

        if hasattr(config, 'custom_params') and config.custom_params:
            custom_params = config.custom_params
            if 'min_timeframe_divergence' in custom_params:
                divergence = custom_params['min_timeframe_divergence']
                if not isinstance(divergence, (int, float)) or not (0 <= divergence <= 5):
                    raise ConfigurationError("min_timeframe_divergence must be between 0 and 5")

            if 'opening_range_percentage' in custom_params:
                orp = custom_params['opening_range_percentage']
                if not isinstance(orp, (int, float)) or not (0 < orp <= 0.1):
                    raise ConfigurationError("opening_range_percentage must be between 0 and 0.1")

    @staticmethod
    def validate_timeframe_data(timeframe_data: Dict[str, Any]) -> None:
        """Validate timeframe analysis data"""
        if not timeframe_data:
            raise TimeframeAnalysisError("Timeframe data cannot be None")

        if not isinstance(timeframe_data, dict):
            raise TimeframeAnalysisError("Timeframe data must be a dictionary")

        required_keys = ['short_term', 'medium_term', 'long_term']
        for key in required_keys:
            if key not in timeframe_data:
                raise TimeframeAnalysisError(f"Missing required timeframe: {key}")

            timeframe = timeframe_data[key]
            if not isinstance(timeframe, dict) or 'price' not in timeframe:
                raise TimeframeAnalysisError(f"Invalid timeframe data structure for {key}")

    @staticmethod
    def validate_arbitrage_signal(signal) -> None:
        """Validate arbitrage signal"""
        if not signal:
            raise StatisticalArbitrageError("Arbitrage signal cannot be None")

        if not isinstance(signal.confidence_score, (int, float)) or not (0 <= signal.confidence_score <= 1):
            raise StatisticalArbitrageError("Confidence score must be between 0 and 1")

        if signal.signal_type not in ["buy", "sell"]:
            raise StatisticalArbitrageError("Signal type must be 'buy' or 'sell'")

        if not isinstance(signal.expected_return, (int, float)) or signal.expected_return <= 0:
            raise StatisticalArbitrageError("Expected return must be positive")

    @staticmethod
    def validate_signal_parameters(**kwargs) -> None:
        """Validate signal generation parameters"""
        confidence_threshold = kwargs.get('confidence_threshold', 0.5)
        if not isinstance(confidence_threshold, (int, float)) or not (0 <= confidence_threshold <= 1):
            raise SignalGenerationError("Confidence threshold must be between 0 and 1")

        max_opportunities = kwargs.get('max_opportunities', 5)
        if not isinstance(max_opportunities, int) or max_opportunities <= 0:
            raise SignalGenerationError("Max opportunities must be positive integer")


class TimeframeType(str, Enum):
    """Types of timeframes for analysis"""
    TICK = "tick"              # Individual trades
    MINUTE_1 = "1m"           # 1-minute bars
    MINUTE_5 = "5m"           # 5-minute bars
    MINUTE_15 = "15m"         # 15-minute bars
    HOUR_1 = "1h"             # 1-hour bars
    HOUR_4 = "4h"             # 4-hour bars
    DAY_1 = "1d"              # Daily bars
    WEEK_1 = "1w"             # Weekly bars


class ArbitrageType(str, Enum):
    """Types of time arbitrage opportunities"""
    TIMEFRAME_DIVERGENCE = "timeframe_divergence"    # Price divergence between timeframes
    MOMENTUM_BREAKOUT = "momentum_breakout"          # Momentum breaking through time levels
    OPENING_RANGE_BREAK = "opening_range_break"      # Breaking out of opening price range
    INTRADAY_REVERSAL = "intraday_reversal"          # Intraday price reversals
    STATISTICAL_ARBITRAGE = "statistical_arbitrage"  # Statistical relationship breakdown
    CALENDAR_EFFECT = "calendar_effect"              # Calendar-based patterns
    SEASONAL_PATTERN = "seasonal_pattern"            # Seasonal trading patterns


class TimeArbitrageSignal(str, Enum):
    """Time arbitrage signal types"""
    SHORT_TERM_BREAKOUT = "short_term_breakout"      # Short-term momentum breakout
    MEDIUM_TERM_DIVERGENCE = "medium_term_divergence"  # Medium-term divergence signal
    LONG_TERM_TREND_FOLLOW = "long_term_trend_follow"  # Long-term trend following
    OPENING_RANGE_FADE = "opening_range_fade"        # Fade opening range moves
    TIME_BASED_REVERSAL = "time_based_reversal"      # Time-based reversal signal


@dataclass
class TimeframeData:
    """Data for a specific timeframe"""
    timeframe: TimeframeType
    timestamp: datetime
    price: float
    volume: int
    momentum: float = 0.0
    volatility: float = 0.0
    trend_strength: float = 0.0
    support_resistance: Dict[str, float] = field(default_factory=dict)


@dataclass
class ArbitrageOpportunity:
    """Time arbitrage trading opportunity"""
    arbitrage_type: ArbitrageType
    signal_type: TimeArbitrageSignal
    entry_price: float
    stop_loss_price: float
    take_profit_price: float
    position_size_percentage: float
    confidence_score: float
    expected_return: float
    risk_reward_ratio: float
    holding_period_minutes: int
    expiry_seconds: int
    reasoning: str
    timeframe_analysis: Dict[str, Any] = field(default_factory=dict)
    statistical_metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TimeArbitrageSignalData:
    """Detected time arbitrage signal"""
    signal_type: ArbitrageType
    confidence_score: float
    direction: str  # "long" or "short"
    expected_return: float
    entry_price: float
    timeframe_divergence: float
    statistical_significance: float
    detection_timestamp: datetime
    supporting_evidence: Dict[str, Any] = field(default_factory=dict)
    risk_assessment: Dict[str, Any] = field(default_factory=dict)


class TimeArbitrageStrategy(BaseStrategy):
    """
    Time Arbitrage Strategy: Temporal Market Inefficiency Exploitation

    This strategy identifies and exploits time-based market inefficiencies by analyzing
    price movements across different timeframes and detecting statistical discrepancies
    that can be arbitraged for profit.

    Key Components:
    - Multi-timeframe correlation and divergence analysis
    - Statistical arbitrage between timeframes
    - Opening range breakout detection
    - Intraday momentum vs daily trend analysis
    - Calendar effect and seasonal pattern recognition
    - Time-based mean reversion signals
    - Advanced temporal risk management
    """

    def __init__(self, config: StrategyConfig, learning_engine=None):
        """Initialize the Time arbitrage strategy with comprehensive validation"""
        try:
            # Validate configuration first
            TimeArbitrageValidator.validate_config(config)

            # Initialize parent class
            super().__init__(config, learning_engine)

            # Strategy-specific configuration with validation
            self.min_timeframe_divergence = get_config('strategy.time.min_timeframe_divergence', 0.5)
            if not isinstance(self.min_timeframe_divergence, (int, float)) or not (0 <= self.min_timeframe_divergence <= 5):
                raise ConfigurationError("min_timeframe_divergence must be between 0 and 5")

            self.max_timeframe_correlation = get_config('strategy.time.max_timeframe_correlation', 0.8)
            if not isinstance(self.max_timeframe_correlation, (int, float)) or not (0 <= self.max_timeframe_correlation <= 1):
                raise ConfigurationError("max_timeframe_correlation must be between 0 and 1")

            self.opening_range_percentage = get_config('strategy.time.opening_range_percentage', 0.02)
            if not isinstance(self.opening_range_percentage, (int, float)) or not (0 < self.opening_range_percentage <= 0.1):
                raise ConfigurationError("opening_range_percentage must be between 0 and 0.1")

            self.momentum_threshold = get_config('strategy.time.momentum_threshold', 1.5)
            if not isinstance(self.momentum_threshold, (int, float)) or self.momentum_threshold <= 0:
                raise ConfigurationError("momentum_threshold must be positive")

            self.mean_reversion_lookback = get_config('strategy.time.mean_reversion_lookback', 10)
            if not isinstance(self.mean_reversion_lookback, (int, float)) or self.mean_reversion_lookback <= 0:
                raise ConfigurationError("mean_reversion_lookback must be positive")

            self.min_confidence_threshold = get_config('strategy.time.min_confidence', 0.75)
            if not isinstance(self.min_confidence_threshold, (int, float)) or not (0 <= self.min_confidence_threshold <= 1):
                raise ConfigurationError("min_confidence must be between 0 and 1")

            # Timeframe tracking with validation
            self.timeframe_history: Dict[str, List[TimeframeData]] = {}
            self.max_history_size = get_config('strategy.time.max_history_size', 500)
            if not isinstance(self.max_history_size, int) or self.max_history_size < 1:
                raise ConfigurationError("max_history_size must be positive integer")

            # Arbitrage detection with validation
            self.arbitrage_signals: List[TimeArbitrageSignalData] = []
            self.pattern_recognition_window = get_config('strategy.time.pattern_recognition_window', 100)
            if not isinstance(self.pattern_recognition_window, (int, float)) or self.pattern_recognition_window <= 0:
                raise ConfigurationError("pattern_recognition_window must be positive number")

            # Statistical arbitrage state with validation
            self.active_opportunities: Dict[str, ArbitrageOpportunity] = {}
            self.statistical_models: Dict[str, Any] = {}
            self.correlation_matrices: Dict[str, List[float]] = {}
            self.max_active_opportunities = get_config('strategy.time.max_active_opportunities', 5)
            if not isinstance(self.max_active_opportunities, int) or self.max_active_opportunities < 1:
                raise ConfigurationError("max_active_opportunities must be positive integer")

            # AI and technical analysis components
            self.indicators_calculator = TechnicalIndicatorsCalculator()
            self.ai_client = Gemma3Client()
            self.confidence_tracker = AdvancedConfidenceTracker()

            # Performance tracking with validation
            self.time_arbitrage_stats = {
                'total_opportunities': 0,
                'successful_trades': 0,
                'failed_trades': 0,
                'average_return_per_trade': 0.0,
                'win_rate': 0.0,
                'average_holding_period': 0.0,
                'max_drawdown': 0.0,
                'total_trading_volume': 0.0,
                'best_trade': 0.0,
                'worst_trade': 0.0,
                'arbitrage_accuracy': 0.0,
                'timeframe_prediction_accuracy': 0.0,
                'statistical_significance_rate': 0.0
            }

            # Risk management parameters with validation
            self.max_concurrent_positions = get_config('strategy.time.max_concurrent_positions', 3)
            if not isinstance(self.max_concurrent_positions, int) or self.max_concurrent_positions < 1:
                raise ConfigurationError("max_concurrent_positions must be positive integer")

            self.emergency_stop_loss_multiplier = get_config('strategy.time.emergency_stop_multiplier', 1.8)
            if not isinstance(self.emergency_stop_loss_multiplier, (int, float)) or self.emergency_stop_loss_multiplier <= 1:
                raise ConfigurationError("emergency_stop_multiplier must be greater than 1")

            self.profit_targets = get_config('strategy.time.profit_targets', [2.0, 4.0, 6.0, 8.0, 10.0])
            if not isinstance(self.profit_targets, list) or not all(isinstance(x, (int, float)) and x > 0 for x in self.profit_targets):
                raise ConfigurationError("profit_targets must be list of positive numbers")

            # Circuit breaker state
            self.circuit_breaker_active = False
            self.circuit_breaker_reason = ""
            self.circuit_breaker_timestamp = None
            self.consecutive_failures = 0
            self.max_consecutive_failures = get_config('strategy.time.max_consecutive_failures', 4)

            # Market session tracking
            self.market_open_time = None
            self.opening_range_high = None
            self.opening_range_low = None
            self.opening_range_established = False

            logger.info(
                "Time arbitrage strategy initialized with validation",
                strategy_id=self.strategy_id,
                min_divergence=self.min_timeframe_divergence,
                opening_range_pct=self.opening_range_percentage,
                max_concurrent_positions=self.max_concurrent_positions
            )

        except (ConfigurationError, ValidationError) as e:
            logger.error("Time arbitrage strategy initialization validation failed", error=str(e))
            raise
        except Exception as e:
            logger.error("Unexpected error during Time arbitrage strategy initialization", error=str(e))
            raise ConfigurationError(f"Failed to initialize Time arbitrage strategy: {str(e)}")

    async def initialize(self) -> bool:
        """
        Initialize the Time arbitrage strategy with required resources

        Returns:
            True if initialization successful
        """
        try:
            self.current_phase = StrategyPhase.INITIALIZING

            # Initialize AI client
            await self.ai_client.connect()

            # Validate configuration
            if self.config.strategy_type not in [StrategyType.QUANTITATIVE]:
                raise ValueError(f"Invalid strategy type: {self.config.strategy_type}")

            # Set up quantitative trading parameters
            self.config.max_trades_per_day = 8  # Higher frequency for time arbitrage
            self.config.min_signal_strength = self.min_confidence_threshold

            # Initialize technical indicators
            await self._initialize_technical_indicators()

            # Initialize statistical models
            await self._initialize_statistical_models()

            logger.info("Time arbitrage strategy initialization completed")
            return True

        except Exception as e:
            logger.error("Time arbitrage strategy initialization failed", error=str(e))
            return False

    async def _initialize_technical_indicators(self):
        """Initialize technical indicators required for time arbitrage analysis"""
        # Time arbitrage strategy uses specific indicators for temporal analysis
        self.required_indicators = [
            IndicatorType.MOMENTUM,
            IndicatorType.RSI,
            IndicatorType.MACD,
            IndicatorType.BOLLINGER_BANDS,
            IndicatorType.MOVING_AVERAGE
        ]

    async def _initialize_statistical_models(self):
        """Initialize statistical models for arbitrage detection"""
        try:
            # Initialize correlation tracking for different symbols
            for symbol in self.config.supported_symbols:
                self.correlation_matrices[symbol] = []
                self.timeframe_history[symbol] = []

            # Initialize basic statistical models
            self.statistical_models = {
                'correlation_model': {},
                'mean_reversion_model': {},
                'momentum_model': {},
                'breakout_model': {}
            }

        except Exception as e:
            logger.warning("Failed to initialize statistical models", error=str(e))

    async def analyze_market(self, market_data: MarketData) -> MarketAnalysis:
        """
        Analyze market data with comprehensive validation and error handling

        Args:
            market_data: Current market data

        Returns:
            MarketAnalysis with time arbitrage-specific insights

        Raises:
            ValidationError: If market data is invalid
            TimeframeAnalysisError: If timeframe analysis fails
            StatisticalArbitrageError: If statistical analysis fails
        """
        try:
            # Check circuit breaker
            if self.circuit_breaker_active:
                raise TimeArbitrageError(f"Circuit breaker active: {self.circuit_breaker_reason}")

            # Validate input
            TimeArbitrageValidator.validate_market_data(market_data)

            self.current_phase = StrategyPhase.ANALYZING
            start_time = time.time()

            # Update timeframe data with error handling
            await self._update_timeframe_data(market_data)

            # Establish opening range if needed
            await self._establish_opening_range(market_data)

            # Calculate multi-timeframe indicators with fallback
            timeframe_indicators = await self._calculate_timeframe_indicators(market_data)

            # Analyze timeframe correlations and divergences
            correlation_analysis = await self._analyze_timeframe_correlations(market_data, timeframe_indicators)

            # Detect arbitrage opportunities with error recovery
            await self._detect_arbitrage_opportunities(market_data, timeframe_indicators, correlation_analysis)

            # AI-powered temporal pattern analysis with fallback
            ai_insights = await self._get_ai_temporal_insights(market_data, timeframe_indicators, correlation_analysis)

            # Calculate temporal market metrics
            temporal_metrics = await self._calculate_temporal_market_metrics(market_data, timeframe_indicators)

            analysis = MarketAnalysis(
                symbol=market_data.symbol,
                analysis_type="time_arbitrage_analysis",
                indicators=timeframe_indicators,
                ai_insights=ai_insights,
                sentiment_score=temporal_metrics.get('temporal_sentiment', 0.0),
                volatility=temporal_metrics.get('temporal_volatility', 0.0),
                liquidity_score=temporal_metrics.get('temporal_liquidity', 1.0),
                confidence_score=ai_insights.get('overall_confidence', 0.5),
                processing_time_ms=(time.time() - start_time) * 1000
            )

            # Store analysis for signal generation
            self.last_analysis[market_data.symbol] = analysis

            # Reset consecutive failures on successful analysis
            self.consecutive_failures = 0

            logger.info(
                "Market analysis completed successfully",
                symbol=market_data.symbol,
                temporal_sentiment=analysis.sentiment_score,
                confidence=analysis.confidence_score,
                arbitrage_opportunities=len(self.arbitrage_signals),
                processing_time_ms=analysis.processing_time_ms
            )

            return analysis

        except (ValidationError, TimeArbitrageError) as e:
            # Don't count validation/circuit breaker errors as failures
            logger.warning("Market analysis validation/circuit breaker error", error=str(e))
            raise
        except Exception as e:
            self.consecutive_failures += 1
            logger.error("Market analysis failed", error=str(e), consecutive_failures=self.consecutive_failures)

            # Activate circuit breaker if too many consecutive failures
            if self.consecutive_failures >= self.max_consecutive_failures:
                await self._activate_circuit_breaker(f"Too many consecutive analysis failures: {self.consecutive_failures}")

            # Return degraded analysis for graceful degradation
            return self._create_degraded_analysis(market_data)

    def _create_degraded_analysis(self, market_data: MarketData) -> MarketAnalysis:
        """Create a degraded analysis when full analysis fails"""
        try:
            return MarketAnalysis(
                symbol=market_data.symbol,
                analysis_type="degraded_time_arbitrage_analysis",
                indicators={},
                ai_insights={
                    'temporal_patterns': [],
                    'arbitrage_opportunities': [],
                    'market_regime': 'unknown',
                    'overall_confidence': 0.1,  # Very low confidence
                    'ai_reasoning': 'Analysis failed - using degraded mode',
                    'processing_time_ms': 0
                },
                sentiment_score=0.0,
                volatility=0.5,  # Assume moderate volatility
                liquidity_score=0.5,  # Assume moderate liquidity
                confidence_score=0.1,  # Very low confidence
                processing_time_ms=0
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

            logger.warning("Circuit breaker activated", reason=reason, timestamp=self.circuit_breaker_timestamp)

        except Exception as e:
            logger.error("Failed to activate circuit breaker", error=str(e))
            raise TimeArbitrageError(f"Circuit breaker activation failed: {str(e)}")

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
                return {'active': False}

            # Auto-recovery after 15 minutes (longer than other strategies for more caution)
            if self.circuit_breaker_timestamp:
                time_since_activation = (datetime.utcnow() - self.circuit_breaker_timestamp).seconds
                if time_since_activation > 900:  # 15 minutes
                    await self._deactivate_circuit_breaker()
                    return {'active': False, 'auto_recovered': True}

            return {
                'active': True,
                'reason': self.circuit_breaker_reason,
                'timestamp': self.circuit_breaker_timestamp.isoformat() if self.circuit_breaker_timestamp else None,
                'consecutive_failures': self.consecutive_failures
            }

        except Exception as e:
            logger.error("Failed to check circuit breaker status", error=str(e))
            return {'active': True, 'error': str(e)}

    async def _update_timeframe_data(self, market_data: MarketData):
        """Update timeframe data for multi-timeframe analysis"""
        try:
            symbol = market_data.symbol

            # Initialize timeframe history if needed
            if symbol not in self.timeframe_history:
                self.timeframe_history[symbol] = []

            # Create timeframe data point
            timeframe_data = TimeframeData(
                timeframe=TimeframeType.MINUTE_1,  # Assume 1-minute data
                timestamp=market_data.timestamp,
                price=market_data.close,
                volume=market_data.volume,
                momentum=0.0,  # Will be calculated
                volatility=0.0,  # Will be calculated
                trend_strength=0.0  # Will be calculated
            )

            # Calculate momentum (simplified)
            if len(self.timeframe_history[symbol]) >= 5:
                recent_prices = [tf.price for tf in self.timeframe_history[symbol][-5:]]
                recent_prices.append(market_data.close)
                if len(recent_prices) >= 2:
                    timeframe_data.momentum = (recent_prices[-1] - recent_prices[0]) / recent_prices[0] * 100

            # Calculate volatility (simplified)
            if len(self.timeframe_history[symbol]) >= 10:
                prices = [tf.price for tf in self.timeframe_history[symbol][-10:]]
                prices.append(market_data.close)
                if len(prices) > 1:
                    returns = [(prices[i] - prices[i - 1]) / prices[i - 1] for i in range(1, len(prices))]
                    timeframe_data.volatility = statistics.stdev(returns) * math.sqrt(252)  # Annualized

            # Add to history
            self.timeframe_history[symbol].append(timeframe_data)

            # Maintain history size
            if len(self.timeframe_history[symbol]) > self.max_history_size:
                self.timeframe_history[symbol].pop(0)

        except Exception as e:
            logger.warning("Failed to update timeframe data", error=str(e))

    async def _establish_opening_range(self, market_data: MarketData):
        """Establish opening price range for breakout detection"""
        try:
            # Check if it's market open time (9:15 AM IST for Indian markets)
            current_time = market_data.timestamp.time()
            market_open = current_time.hour == 9 and current_time.minute >= 15

            if market_open and not self.opening_range_established:
                # First 15 minutes establish opening range
                if self.market_open_time is None:
                    self.market_open_time = market_data.timestamp

                # Update opening range
                if self.opening_range_high is None or market_data.high > self.opening_range_high:
                    self.opening_range_high = market_data.high
                if self.opening_range_low is None or market_data.low < self.opening_range_low:
                    self.opening_range_low = market_data.low

                # Check if opening range is established (after 15 minutes)
                if self.market_open_time and (market_data.timestamp - self.market_open_time).seconds >= 900:  # 15 minutes
                    self.opening_range_established = True
                    logger.info(
                        "Opening range established",
                        symbol=market_data.symbol,
                        high=self.opening_range_high,
                        low=self.opening_range_low,
                        range_pct=((self.opening_range_high - self.opening_range_low) / self.opening_range_low) * 100
                    )

        except Exception as e:
            logger.warning("Failed to establish opening range", error=str(e))

    async def _calculate_timeframe_indicators(self, market_data: MarketData) -> Dict[str, Any]:
        """Calculate indicators across multiple timeframes"""
        try:
            symbol = market_data.symbol
            indicators = {}

            # Get historical data for calculations
            history = self.timeframe_history.get(symbol, [])
            if len(history) < 10:
                return indicators

            # Convert to data points for indicator calculation
            data_points = [{'close': tf.price, 'volume': tf.volume} for tf in history[-50:]]  # Last 50 points

            for indicator_type in self.required_indicators:
                try:
                    result = self.indicators_calculator.calculate_indicator(
                        indicator_type, data_points, symbol=symbol
                    )
                    indicators[indicator_type.value] = result.value or result.values
                except Exception as e:
                    logger.warning(f"Failed to calculate {indicator_type.value}", error=str(e))
                    indicators[indicator_type.value] = None

            # Calculate multi-timeframe metrics
            indicators['multi_timeframe'] = await self._calculate_multi_timeframe_metrics(symbol)

            return indicators

        except Exception as e:
            logger.error("Timeframe indicators calculation failed", error=str(e))
            return {}

    async def _calculate_multi_timeframe_metrics(self, symbol: str) -> Dict[str, Any]:
        """Calculate metrics across different timeframes"""
        try:
            metrics = {}

            # Simulate different timeframe data (in real implementation, would fetch from data source)
            current_price = 100.0  # Placeholder

            # Short-term (5-minute)
            short_term_ma = current_price * 0.995  # Slight downtrend
            short_term_momentum = -0.5

            # Medium-term (1-hour)
            medium_term_ma = current_price * 1.01  # Uptrend
            medium_term_momentum = 1.2

            # Long-term (daily)
            long_term_ma = current_price * 0.98  # Downtrend
            long_term_momentum = -1.8

            metrics['short_term'] = {
                'price': current_price,
                'ma': short_term_ma,
                'momentum': short_term_momentum,
                'trend': 'down' if short_term_momentum < 0 else 'up'
            }

            metrics['medium_term'] = {
                'price': current_price,
                'ma': medium_term_ma,
                'momentum': medium_term_momentum,
                'trend': 'down' if medium_term_momentum < 0 else 'up'
            }

            metrics['long_term'] = {
                'price': current_price,
                'ma': long_term_ma,
                'momentum': long_term_momentum,
                'trend': 'down' if long_term_momentum < 0 else 'up'
            }

            return metrics

        except Exception as e:
            logger.error("Multi-timeframe metrics calculation failed", error=str(e))
            return {}

    async def _analyze_timeframe_correlations(self, market_data: MarketData, indicators: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze correlations between different timeframes"""
        try:
            multi_timeframe = indicators.get('multi_timeframe', {})

            correlations = {}

            # Calculate correlation between short and medium term
            if 'short_term' in multi_timeframe and 'medium_term' in multi_timeframe:
                short_momentum = multi_timeframe['short_term']['momentum']
                medium_momentum = multi_timeframe['medium_term']['momentum']

                # Simple correlation calculation
                correlation = (short_momentum * medium_momentum) / (abs(short_momentum) * abs(medium_momentum)) if short_momentum != 0 and medium_momentum != 0 else 0
                correlations['short_medium'] = correlation

            # Calculate correlation between medium and long term
            if 'medium_term' in multi_timeframe and 'long_term' in multi_timeframe:
                medium_momentum = multi_timeframe['medium_term']['momentum']
                long_momentum = multi_timeframe['long_term']['momentum']

                correlation = (medium_momentum * long_momentum) / (abs(medium_momentum) * abs(long_momentum)) if medium_momentum != 0 and long_momentum != 0 else 0
                correlations['medium_long'] = correlation

            # Detect divergences
            divergences = {}

            # Short vs medium term divergence
            short_trend = multi_timeframe.get('short_term', {}).get('trend')
            medium_trend = multi_timeframe.get('medium_term', {}).get('trend')
            if short_trend and medium_trend and short_trend != medium_trend:
                divergences['short_medium'] = {
                    'type': 'divergence',
                    'short_trend': short_trend,
                    'medium_trend': medium_trend,
                    'magnitude': abs(multi_timeframe['short_term']['momentum'] - multi_timeframe['medium_term']['momentum'])
                }

            # Medium vs long term divergence
            long_trend = multi_timeframe.get('long_term', {}).get('trend')
            if medium_trend and long_trend and medium_trend != long_trend:
                divergences['medium_long'] = {
                    'type': 'divergence',
                    'medium_trend': medium_trend,
                    'long_trend': long_trend,
                    'magnitude': abs(multi_timeframe['medium_term']['momentum'] - multi_timeframe['long_term']['momentum'])
                }

            return {
                'correlations': correlations,
                'divergences': divergences,
                'average_correlation': sum(correlations.values()) / len(correlations) if correlations else 0
            }

        except Exception as e:
            logger.error("Timeframe correlation analysis failed", error=str(e))
            return {}

    async def _detect_arbitrage_opportunities(self, market_data: MarketData, indicators: Dict[str, Any], correlation_analysis: Dict[str, Any]) -> List[TimeArbitrageSignalData]:
        """Detect time arbitrage opportunities"""
        try:
            opportunities = []

            # 1. Timeframe Divergence Arbitrage
            divergences = correlation_analysis.get('divergences', {})
            for divergence_key, divergence_data in divergences.items():
                if divergence_data.get('magnitude', 0) >= self.min_timeframe_divergence:
                    signal = TimeArbitrageSignalData(
                        signal_type=ArbitrageType.TIMEFRAME_DIVERGENCE,
                        confidence_score=min(0.9, divergence_data['magnitude'] / 5.0),
                        direction="long" if divergence_data['short_trend'] == 'up' else "short",
                        expected_return=divergence_data['magnitude'] * 0.5,  # Expected 50% of divergence magnitude
                        entry_price=market_data.close,
                        timeframe_divergence=divergence_data['magnitude'],
                        statistical_significance=divergence_data['magnitude'] / 2.0,  # Simplified
                        detection_timestamp=market_data.timestamp,
                        supporting_evidence={
                            'divergence_type': divergence_key,
                            'short_trend': divergence_data.get('short_trend'),
                            'medium_trend': divergence_data.get('medium_trend'),
                            'long_trend': divergence_data.get('long_trend')
                        }
                    )
                    opportunities.append(signal)

            # 2. Opening Range Break Arbitrage
            if self.opening_range_established and self.opening_range_high and self.opening_range_low:
                current_price = market_data.close
                opening_range_size = self.opening_range_high - self.opening_range_low

                # Break above opening range
                if current_price > self.opening_range_high + (opening_range_size * 0.1):
                    signal = TimeArbitrageSignalData(
                        signal_type=ArbitrageType.OPENING_RANGE_BREAK,
                        confidence_score=0.8,
                        direction="long",
                        expected_return=opening_range_size * 0.5,
                        entry_price=current_price,
                        timeframe_divergence=(current_price - self.opening_range_high) / self.opening_range_high,
                        statistical_significance=0.7,
                        detection_timestamp=market_data.timestamp,
                        supporting_evidence={
                            'break_type': 'above',
                            'opening_range_high': self.opening_range_high,
                            'opening_range_low': self.opening_range_low,
                            'break_distance': current_price - self.opening_range_high
                        }
                    )
                    opportunities.append(signal)

                # Break below opening range
                elif current_price < self.opening_range_low - (opening_range_size * 0.1):
                    signal = TimeArbitrageSignalData(
                        signal_type=ArbitrageType.OPENING_RANGE_BREAK,
                        confidence_score=0.8,
                        direction="short",
                        expected_return=opening_range_size * 0.5,
                        entry_price=current_price,
                        timeframe_divergence=(self.opening_range_low - current_price) / self.opening_range_low,
                        statistical_significance=0.7,
                        detection_timestamp=market_data.timestamp,
                        supporting_evidence={
                            'break_type': 'below',
                            'opening_range_high': self.opening_range_high,
                            'opening_range_low': self.opening_range_low,
                            'break_distance': self.opening_range_low - current_price
                        }
                    )
                    opportunities.append(signal)

            # 3. Momentum Breakout Arbitrage
            momentum = indicators.get('momentum')
            if momentum and abs(momentum) >= self.momentum_threshold:
                signal = TimeArbitrageSignalData(
                    signal_type=ArbitrageType.MOMENTUM_BREAKOUT,
                    confidence_score=min(0.85, abs(momentum) / 5.0),
                    direction="long" if momentum > 0 else "short",
                    expected_return=abs(momentum) * 0.3,
                    entry_price=market_data.close,
                    timeframe_divergence=abs(momentum),
                    statistical_significance=abs(momentum) / 2.0,
                    detection_timestamp=market_data.timestamp,
                    supporting_evidence={
                        'momentum_value': momentum,
                        'momentum_threshold': self.momentum_threshold,
                        'breakout_strength': abs(momentum) / self.momentum_threshold
                    }
                )
                opportunities.append(signal)

            # Store opportunities for pattern analysis
            self.arbitrage_signals.extend(opportunities)
            if len(self.arbitrage_signals) > 50:  # Keep last 50 signals
                self.arbitrage_signals = self.arbitrage_signals[-50:]

            return opportunities

        except Exception as e:
            logger.error("Arbitrage opportunity detection failed", error=str(e))
            return []

    async def _get_ai_temporal_insights(self, market_data: MarketData, indicators: Dict[str, Any], correlation_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Get AI-powered temporal pattern insights"""
        try:
            # Prepare temporal context for AI analysis
            temporal_context = {
                'symbol': market_data.symbol,
                'current_price': float(market_data.close),
                'timeframe_indicators': indicators,
                'correlation_analysis': correlation_analysis,
                'arbitrage_signals': len(self.arbitrage_signals),
                'opening_range_established': self.opening_range_established,
                'market_session_time': market_data.timestamp.strftime('%H:%M:%S'),
                'timeframe_history_length': len(self.timeframe_history.get(market_data.symbol, []))
            }

            # AI analysis for temporal pattern recognition
            analysis_request = AnalysisRequest(
                analysis_type=AnalysisType.PATTERN_RECOGNITION,
                input_data={
                    'market_data': temporal_context,
                    'analysis_focus': 'temporal_arbitrage_patterns',
                    'strategy_context': 'time_arbitrage_quantitative'
                },
                confidence_threshold=0.7
            )

            ai_response = await self.ai_client.analyze(analysis_request)

            return {
                'temporal_patterns': ai_response.result.get('key_points', []),
                'arbitrage_opportunities': ai_response.result.get('arbitrage_signals', []),
                'market_regime': ai_response.result.get('market_regime', 'neutral'),
                'timeframe_alignment': ai_response.result.get('timeframe_alignment', 'mixed'),
                'overall_confidence': ai_response.confidence_score,
                'ai_reasoning': ai_response.result.get('rationale', ''),
                'processing_time_ms': ai_response.processing_time_ms
            }

        except Exception as e:
            logger.warning("AI temporal insights failed", error=str(e))
            return {
                'temporal_patterns': [],
                'arbitrage_opportunities': [],
                'market_regime': 'unknown',
                'timeframe_alignment': 'unknown',
                'overall_confidence': 0.5,
                'ai_reasoning': 'Analysis failed',
                'processing_time_ms': 0
            }

    async def _calculate_temporal_market_metrics(self, market_data: MarketData, indicators: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate comprehensive temporal market metrics"""
        try:
            if not self.timeframe_history.get(market_data.symbol):
                return {}

            # Get recent timeframe data
            recent_data = self.timeframe_history[market_data.symbol][-20:]  # Last 20 points

            # Calculate temporal sentiment (trend alignment)
            trends = []
            for tf_data in recent_data:
                if tf_data.momentum != 0:
                    trends.append(1 if tf_data.momentum > 0 else -1)

            temporal_sentiment = sum(trends) / len(trends) if trends else 0

            # Calculate temporal volatility (variation across timeframes)
            volatilities = [tf.volatility for tf in recent_data if tf.volatility > 0]
            temporal_volatility = statistics.mean(volatilities) if volatilities else 0

            # Calculate temporal liquidity (consistency of volume)
            volumes = [tf.volume for tf in recent_data]
            volume_consistency = statistics.stdev(volumes) / statistics.mean(volumes) if volumes and statistics.mean(volumes) > 0 else 1
            temporal_liquidity = max(0, 1 - volume_consistency)  # Lower consistency = higher liquidity

            # Calculate timeframe momentum divergence
            momentum_values = [tf.momentum for tf in recent_data if tf.momentum != 0]
            momentum_divergence = statistics.stdev(momentum_values) if len(momentum_values) > 1 else 0

            return {
                'temporal_sentiment': temporal_sentiment,
                'temporal_volatility': temporal_volatility,
                'temporal_liquidity': temporal_liquidity,
                'momentum_divergence': momentum_divergence,
                'timeframe_alignment_score': abs(temporal_sentiment),  # How aligned timeframes are
                'arbitrage_risk_level': 'high' if momentum_divergence > 2.0 else 'medium' if momentum_divergence > 1.0 else 'low'
            }

        except Exception as e:
            logger.error("Temporal market metrics calculation failed", error=str(e))
            return {}

    async def generate_signals(self, analysis: MarketAnalysis) -> List[TradingSignal]:
        """
        Generate time arbitrage signals with comprehensive error handling

        Args:
            analysis: Market analysis results

        Returns:
            List of trading signals

        Raises:
            SignalGenerationError: If signal generation fails
            TimeArbitrageError: If circuit breaker is active
        """
        try:
            # Check circuit breaker
            if self.circuit_breaker_active:
                raise TimeArbitrageError(f"Circuit breaker active: {self.circuit_breaker_reason}")

            # Validate analysis input
            if not analysis or not hasattr(analysis, 'symbol'):
                raise ValidationError("Invalid analysis input")

            self.current_phase = StrategyPhase.SIGNAL_GENERATION
            signals = []

            # Check if we have minimum required data
            if not self.arbitrage_signals:
                logger.warning("No arbitrage signals available for signal generation")
                return signals

            # Generate opportunities from arbitrage signals
            for arb_signal in self.arbitrage_signals[-10:]:  # Last 10 signals
                try:
                    if arb_signal.confidence_score >= self.min_confidence_threshold:
                        opportunity = await self._create_arbitrage_opportunity(arb_signal, analysis)

                        if opportunity and opportunity.confidence_score >= self.min_confidence_threshold:
                            # Convert opportunity to trading signal
                            signal = await self._convert_opportunity_to_signal(opportunity, analysis)

                            if signal:
                                signals.append(signal)
                                # Track opportunity
                                self.active_opportunities[signal.signal_id] = opportunity

                except Exception as e:
                    logger.warning("Failed to process arbitrage signal", signal_id=id(arb_signal), error=str(e))
                    continue

            # Generate statistical arbitrage signals
            try:
                statistical_signals = await self._generate_statistical_arbitrage_signals(analysis)
                signals.extend(statistical_signals)
            except Exception as e:
                logger.warning("Statistical arbitrage signal generation failed", error=str(e))

            # Filter signals by confidence and limit active opportunities
            signals = [s for s in signals if s.strength >= self.min_confidence_threshold]

            # Sort by expected return and confidence
            signals = sorted(signals, key=lambda s: (s.supporting_data.get('expected_return', 0), s.strength), reverse=True)

            # Limit to high-confidence signals only
            signals = signals[:self.max_active_opportunities]

            # Update active opportunities
            for signal in signals:
                if signal.signal_id not in self.active_opportunities:
                    # Create opportunity from signal
                    opportunity = await self._create_opportunity_from_signal(signal, analysis)
                    if opportunity:
                        self.active_opportunities[signal.signal_id] = opportunity

            logger.info(
                "Signals generated successfully",
                signal_count=len(signals),
                arbitrage_signals=len(self.arbitrage_signals),
                active_opportunities=len(self.active_opportunities)
            )

            return signals

        except (ValidationError, TimeArbitrageError) as e:
            logger.warning("Signal generation validation/circuit breaker error", error=str(e))
            raise
        except Exception as e:
            logger.error("Signal generation failed", error=str(e))
            raise SignalGenerationError(f"Failed to generate signals: {str(e)}")

    async def _create_arbitrage_opportunity(
        self,
        arbitrage_signal: TimeArbitrageSignalData,
        analysis: MarketAnalysis
    ) -> Optional[ArbitrageOpportunity]:
        """Create an arbitrage opportunity from arbitrage signal"""
        try:
            # Determine signal type based on arbitrage type
            if arbitrage_signal.signal_type == ArbitrageType.TIMEFRAME_DIVERGENCE:
                signal_type = TimeArbitrageSignal.MEDIUM_TERM_DIVERGENCE
            elif arbitrage_signal.signal_type == ArbitrageType.OPENING_RANGE_BREAK:
                signal_type = TimeArbitrageSignal.SHORT_TERM_BREAKOUT
            elif arbitrage_signal.signal_type == ArbitrageType.MOMENTUM_BREAKOUT:
                signal_type = TimeArbitrageSignal.SHORT_TERM_BREAKOUT
            else:
                signal_type = TimeArbitrageSignal.TIME_BASED_REVERSAL

            # Position sizing based on confidence and expected return
            base_position_size = 0.04  # Conservative for quantitative strategy
            confidence_multiplier = arbitrage_signal.confidence_score
            return_multiplier = min(2.0, arbitrage_signal.expected_return / 2.0)  # Scale with expected return
            position_size_percentage = base_position_size * confidence_multiplier * return_multiplier

            # Risk management - tighter stops for time arbitrage
            stop_loss_distance = arbitrage_signal.entry_price * 0.02  # 2% stop loss
            stop_loss_price = (
                arbitrage_signal.entry_price - stop_loss_distance
                if arbitrage_signal.direction == "long"
                else arbitrage_signal.entry_price + stop_loss_distance
            )

            # Profit targets - multiple levels for arbitrage
            profit_distances = [arbitrage_signal.expected_return * target / 100 for target in self.profit_targets]
            take_profit_price = (
                arbitrage_signal.entry_price + profit_distances[0]
                if arbitrage_signal.direction == "long"
                else arbitrage_signal.entry_price - profit_distances[0]
            )

            # Calculate risk-reward ratio
            risk = abs(arbitrage_signal.entry_price - stop_loss_price)
            reward = abs(take_profit_price - arbitrage_signal.entry_price)
            risk_reward_ratio = reward / risk if risk > 0 else 0

            # Estimate holding period based on signal type
            if arbitrage_signal.signal_type == ArbitrageType.TIMEFRAME_DIVERGENCE:
                holding_period_minutes = 30  # Longer for divergence plays
            elif arbitrage_signal.signal_type == ArbitrageType.OPENING_RANGE_BREAK:
                holding_period_minutes = 15  # Shorter for breakout plays
            else:
                holding_period_minutes = 20  # Default

            # Create opportunity
            opportunity = ArbitrageOpportunity(
                arbitrage_type=arbitrage_signal.signal_type,
                signal_type=signal_type,
                entry_price=arbitrage_signal.entry_price,
                stop_loss_price=stop_loss_price,
                take_profit_price=take_profit_price,
                position_size_percentage=position_size_percentage,
                confidence_score=arbitrage_signal.confidence_score,
                expected_return=arbitrage_signal.expected_return,
                risk_reward_ratio=risk_reward_ratio,
                holding_period_minutes=holding_period_minutes,
                expiry_seconds=holding_period_minutes * 60,  # Convert to seconds
                reasoning=f"Time arbitrage detected: {arbitrage_signal.signal_type.value}. Expected return: {arbitrage_signal.expected_return:.2f}% with {arbitrage_signal.confidence_score:.2f} confidence.",
                timeframe_analysis={
                    'divergence': arbitrage_signal.timeframe_divergence,
                    'statistical_significance': arbitrage_signal.statistical_significance,
                    'direction': arbitrage_signal.direction
                },
                statistical_metrics={
                    'expected_return': arbitrage_signal.expected_return,
                    'confidence_score': arbitrage_signal.confidence_score,
                    'supporting_evidence': arbitrage_signal.supporting_evidence
                }
            )

            return opportunity

        except Exception as e:
            logger.error("Failed to create arbitrage opportunity", error=str(e))
            return None

    async def _generate_statistical_arbitrage_signals(self, analysis: MarketAnalysis) -> List[TradingSignal]:
        """Generate statistical arbitrage signals"""
        try:
            signals = []

            # Check for mean reversion opportunities
            indicators = analysis.indicators or {}
            rsi_value = indicators.get('rsi', 50)

            # RSI-based mean reversion
            if rsi_value < 30 or rsi_value > 70:  # Oversold or overbought
                direction = "long" if rsi_value < 30 else "short"
                confidence = min(0.8, abs(50 - rsi_value) / 30)  # Higher confidence for extreme RSI

                current_price = 100.0  # Placeholder

                signal = TradingSignal(
                    strategy_id=self.strategy_id,
                    symbol=analysis.symbol,
                    signal_type=SignalType.BUY if direction == "long" else SignalType.SELL,
                    strength=confidence,
                    entry_price=current_price,
                    stop_loss_price=current_price * (0.98 if direction == "long" else 1.02),
                    take_profit_price=current_price * (1.03 if direction == "long" else 0.97),
                    position_size_percentage=0.03,
                    quantity=100,  # Placeholder
                    reasoning=f"Statistical arbitrage: RSI {rsi_value:.1f} indicates {'oversold' if rsi_value < 30 else 'overbought'} condition.",
                    supporting_data={
                        'signal_type': 'statistical_arbitrage_rsi',
                        'rsi_value': rsi_value,
                        'direction': direction,
                        'expected_return': 2.0,
                        'ai_confidence': analysis.ai_insights.get('overall_confidence', 0.5)
                    },
                    expiry_minutes=30
                )

                signals.append(signal)

            return signals

        except Exception as e:
            logger.error("Statistical arbitrage signal generation failed", error=str(e))
            return []

    async def _convert_opportunity_to_signal(
        self,
        opportunity: ArbitrageOpportunity,
        analysis: MarketAnalysis
    ) -> Optional[TradingSignal]:
        """Convert arbitrage opportunity to trading signal"""
        try:
            # Calculate quantity (placeholder - would be calculated based on position size)
            quantity = int((opportunity.position_size_percentage * 100000) / opportunity.entry_price)  # Assume ₹1L portfolio

            signal = TradingSignal(
                strategy_id=self.strategy_id,
                symbol=analysis.symbol,
                signal_type=SignalType.BUY if opportunity.arbitrage_type != ArbitrageType.TIMEFRAME_DIVERGENCE or "long" in opportunity.reasoning.lower() else SignalType.SELL,
                strength=opportunity.confidence_score,
                entry_price=opportunity.entry_price,
                stop_loss_price=opportunity.stop_loss_price,
                take_profit_price=opportunity.take_profit_price,
                position_size_percentage=opportunity.position_size_percentage,
                quantity=quantity,
                reasoning=opportunity.reasoning,
                supporting_data={
                    'arbitrage_type': opportunity.arbitrage_type.value,
                    'signal_type': opportunity.signal_type.value,
                    'expected_return': opportunity.expected_return,
                    'risk_reward_ratio': opportunity.risk_reward_ratio,
                    'holding_period_minutes': opportunity.holding_period_minutes,
                    'timeframe_analysis': opportunity.timeframe_analysis,
                    'statistical_metrics': opportunity.statistical_metrics,
                    'ai_confidence': analysis.ai_insights.get('overall_confidence', 0.5)
                },
                expiry_minutes=opportunity.holding_period_minutes
            )

            return signal

        except Exception as e:
            logger.error("Failed to convert opportunity to signal", error=str(e))
            return None

    async def _create_opportunity_from_signal(
        self,
        signal: TradingSignal,
        analysis: MarketAnalysis
    ) -> Optional[ArbitrageOpportunity]:
        """Create opportunity from trading signal"""
        try:
            # Extract holding period from signal data
            holding_period_minutes = signal.supporting_data.get('holding_period_minutes', 20)

            # Determine arbitrage type from signal data
            arbitrage_type_str = signal.supporting_data.get('arbitrage_type', 'statistical_arbitrage')
            try:
                arbitrage_type = ArbitrageType(arbitrage_type_str)
            except ValueError:
                arbitrage_type = ArbitrageType.STATISTICAL_ARBITRAGE

            opportunity = ArbitrageOpportunity(
                arbitrage_type=arbitrage_type,
                signal_type=TimeArbitrageSignal.TIME_BASED_REVERSAL,
                entry_price=signal.entry_price,
                stop_loss_price=signal.stop_loss_price,
                take_profit_price=signal.take_profit_price,
                position_size_percentage=signal.position_size_percentage,
                confidence_score=signal.strength,
                expected_return=signal.supporting_data.get('expected_return', 2.0),
                risk_reward_ratio=signal.supporting_data.get('risk_reward_ratio', 2.0),
                holding_period_minutes=holding_period_minutes,
                expiry_seconds=holding_period_minutes * 60,
                reasoning=signal.reasoning,
                timeframe_analysis=signal.supporting_data.get('timeframe_analysis', {}),
                statistical_metrics=signal.supporting_data.get('statistical_metrics', {})
            )

            return opportunity

        except Exception as e:
            logger.error("Failed to create opportunity from signal", error=str(e))
            return None

    async def calculate_position_size(self, signal: TradingSignal, portfolio) -> float:
        """
        Calculate position size with time arbitrage-specific quantitative risk management

        Args:
            signal: Trading signal
            portfolio: Current portfolio state

        Returns:
            Position size as percentage of portfolio
        """
        try:
            # Base position size from signal
            base_size = signal.position_size_percentage

            # Time arbitrage adjustments - more quantitative approach
            confidence_multiplier = signal.strength
            expected_return = signal.supporting_data.get('expected_return', 2.0)
            return_multiplier = min(1.5, expected_return / 2.0)  # Scale with expected return

            # Adjust based on arbitrage type
            arbitrage_type = signal.supporting_data.get('arbitrage_type', '')
            if 'divergence' in arbitrage_type:
                type_multiplier = 1.2  # Slightly higher for divergence plays
            elif 'breakout' in arbitrage_type:
                type_multiplier = 1.1  # Moderate for breakout plays
            else:
                type_multiplier = 1.0  # Standard for statistical arbitrage

            # Adjust based on market volatility
            volatility = self.last_analysis.get(signal.symbol, MarketAnalysis(symbol=signal.symbol)).volatility
            volatility_multiplier = max(0.7, 1.0 - volatility)  # More conservative in high volatility

            # Adjust based on portfolio risk
            portfolio_risk_multiplier = 1.0
            if hasattr(portfolio, 'current_drawdown') and portfolio.current_drawdown > 0.03:
                portfolio_risk_multiplier = 0.9  # Slightly reduce in portfolio drawdown

            # Calculate final position size
            position_size = (
                base_size * confidence_multiplier * return_multiplier *
                type_multiplier * volatility_multiplier * portfolio_risk_multiplier
            )

            # Ensure within strategy limits
            position_size = min(position_size, self.config.max_position_size * 0.9)
            position_size = max(position_size, 0.01)  # Minimum 1% position

            logger.debug(
                "Position size calculated",
                signal_id=signal.signal_id,
                base_size=base_size,
                final_size=position_size,
                adjustments={
                    'confidence': confidence_multiplier,
                    'return': return_multiplier,
                    'type': type_multiplier,
                    'volatility': volatility_multiplier,
                    'portfolio': portfolio_risk_multiplier
                }
            )

            return position_size

        except Exception as e:
            logger.error("Position size calculation failed", error=str(e))
            return signal.position_size_percentage * 0.8  # Conservative fallback

    async def manage_risk(self, portfolio) -> List[str]:
        """
        Enhanced risk management for time arbitrage strategy

        Args:
            portfolio: Current portfolio state

        Returns:
            List of risk management actions taken
        """
        try:
            actions_taken = await super().manage_risk(portfolio)

            # Time arbitrage-specific risk checks
            current_positions = len(self.active_positions)

            # Emergency stop if too many concurrent positions
            if current_positions > self.max_concurrent_positions:
                actions_taken.append("time_arbitrage_concurrent_position_limit")
                await self._emergency_stop("Too many concurrent time arbitrage positions")

            # Check for timeframe correlation breakdown
            if self.correlation_matrices:
                avg_correlation = sum(sum(matrix) / len(matrix) if matrix else 0 for matrix in self.correlation_matrices.values()) / len(self.correlation_matrices)
                if avg_correlation > self.max_timeframe_correlation:
                    actions_taken.append("time_arbitrage_correlation_breakdown")
                    # Reduce position sizes for remaining opportunities
                    for opp in self.active_opportunities.values():
                        opp.position_size_percentage *= 0.9

            # Check signal quality degradation
            if len(self.active_opportunities) > 3:
                avg_confidence = sum(opp.confidence_score for opp in self.active_opportunities.values()) / len(self.active_opportunities)
                if avg_confidence < 0.7:
                    actions_taken.append("time_arbitrage_low_signal_quality")
                    # Reduce position sizes for remaining opportunities
                    for opp in self.active_opportunities.values():
                        opp.position_size_percentage *= 0.85

            return actions_taken

        except Exception as e:
            logger.error("Time arbitrage risk management failed", error=str(e))
            raise RiskManagementError(f"Time arbitrage risk management failed: {str(e)}")

    async def _emergency_stop(self, reason: str):
        """Emergency stop for time arbitrage strategy"""
        try:
            logger.warning("Time arbitrage emergency stop triggered", reason=reason)

            # Close all active positions immediately
            for position_id in list(self.active_positions.keys()):
                await self._close_position(position_id, f"emergency_stop: {reason}")

            # Clear all active opportunities
            self.active_opportunities.clear()

            # Reset arbitrage signals
            self.arbitrage_signals.clear()

            # Update status
            self.status = self.status.PAUSED

            # Log emergency action
            self.log_strategy_event("emergency_stop", {"reason": reason, "timestamp": datetime.utcnow().isoformat()})

        except Exception as e:
            logger.error("Emergency stop failed", error=str(e))

    async def update_performance(self, trade_result: Dict[str, Any]):
        """Update time arbitrage-specific performance metrics"""
        try:
            await super().update_performance(trade_result)

            # Update time arbitrage-specific stats
            self.time_arbitrage_stats['total_opportunities'] += 1

            pnl = trade_result.get('pnl', 0.0)
            if pnl > 0:
                self.time_arbitrage_stats['successful_trades'] += 1
            else:
                self.time_arbitrage_stats['failed_trades'] += 1

            # Update win rate
            total_trades = self.time_arbitrage_stats['successful_trades'] + self.time_arbitrage_stats['failed_trades']
            if total_trades > 0:
                self.time_arbitrage_stats['win_rate'] = self.time_arbitrage_stats['successful_trades'] / total_trades

            # Update average return
            if total_trades > 0:
                # This is a simplified calculation - in reality would track all P&L
                self.time_arbitrage_stats['average_return_per_trade'] = (
                    self.performance.total_return / total_trades
                )

            # Update max drawdown (simplified)
            if pnl < 0:
                self.time_arbitrage_stats['max_drawdown'] = max(
                    self.time_arbitrage_stats['max_drawdown'],
                    abs(pnl)
                )

            logger.debug("Time arbitrage performance updated", stats=self.time_arbitrage_stats)

        except Exception as e:
            logger.error("Time arbitrage performance update failed", error=str(e))

    async def health_check(self) -> Dict[str, Any]:
        """Enhanced health check with comprehensive monitoring"""
        try:
            base_health = await super().health_check()

            # Get circuit breaker status
            circuit_breaker_status = await self._check_circuit_breaker_status()

            # Get resource usage
            resource_usage = await self.get_resource_usage()

            # Add time arbitrage-specific health metrics
            time_arbitrage_health = {
                'timeframe_data_available': bool(self.timeframe_history),
                'timeframe_history_size': sum(len(history) for history in self.timeframe_history.values()),
                'arbitrage_signals_count': len(self.arbitrage_signals),
                'correlation_matrices_count': len(self.correlation_matrices),
                'ai_client_connected': self.ai_client.is_connected if self.ai_client else False,
                'opening_range_established': self.opening_range_established,
                'time_arbitrage_stats': self.time_arbitrage_stats,
                'signal_quality': {
                    'avg_confidence': (
                        sum(opp.confidence_score for opp in self.active_opportunities.values()) / len(self.active_opportunities)
                        if self.active_opportunities else 0
                    ),
                    'opportunities_count': len(self.active_opportunities),
                    'max_opportunities_limit': self.max_active_opportunities
                },
                'performance_metrics': {
                    'win_rate': self.time_arbitrage_stats.get('win_rate', 0),
                    'total_opportunities': self.time_arbitrage_stats.get('total_opportunities', 0),
                    'avg_return_per_trade': self.time_arbitrage_stats.get('average_return_per_trade', 0),
                    'max_drawdown': self.time_arbitrage_stats.get('max_drawdown', 0),
                    'arbitrage_accuracy': self.time_arbitrage_stats.get('arbitrage_accuracy', 0)
                },
                'market_session_info': {
                    'opening_range_high': self.opening_range_high,
                    'opening_range_low': self.opening_range_low,
                    'market_open_time': self.market_open_time.isoformat() if self.market_open_time else None
                }
            }

            # Add circuit breaker information
            time_arbitrage_health.update({
                'circuit_breaker': circuit_breaker_status,
                'consecutive_failures': self.consecutive_failures,
                'max_consecutive_failures': self.max_consecutive_failures
            })

            # Add resource monitoring
            time_arbitrage_health['resources'] = resource_usage

            # Determine overall health with more sophisticated logic
            health_score = 0

            # Timeframe data availability (20 points)
            if self.timeframe_history:
                health_score += 20
                # Sufficient history (additional 10 points)
                total_history = sum(len(history) for history in self.timeframe_history.values())
                if total_history >= 100:
                    health_score += 10

            # Arbitrage signals available (15 points)
            if self.arbitrage_signals:
                health_score += 15

            # AI client connection (15 points)
            if time_arbitrage_health['ai_client_connected']:
                health_score += 15

            # Circuit breaker status (20 points)
            if not circuit_breaker_status.get('active', False):
                health_score += 20

            # Opening range established (5 points)
            if self.opening_range_established:
                health_score += 5

            # Active opportunities within limits (10 points)
            if len(self.active_opportunities) <= self.max_active_opportunities:
                health_score += 10

            # Performance metrics (15 points)
            win_rate = self.time_arbitrage_stats.get('win_rate', 0)
            if win_rate >= 0.65:  # At least 65% win rate for quantitative strategy
                health_score += 15
            elif win_rate >= 0.5:  # At least 50% win rate
                health_score += 10

            # Resource usage (10 points)
            memory_mb = resource_usage.get('memory_usage_estimate', 0) / (1024 * 1024)
            if memory_mb < 100:  # Less than 100MB for time arbitrage
                health_score += 10

            # Determine health status based on score
            if health_score >= 80:
                time_arbitrage_health_status = 'healthy'
            elif health_score >= 60:
                time_arbitrage_health_status = 'degraded'
            elif health_score >= 40:
                time_arbitrage_health_status = 'unhealthy'
            else:
                time_arbitrage_health_status = 'critical'

            base_health.update({
                'time_arbitrage_health': time_arbitrage_health,
                'time_arbitrage_status': time_arbitrage_health_status,
                'health_score': health_score,
                'last_arbitrage_signal': (
                    self.arbitrage_signals[-1].detection_timestamp.isoformat()
                    if self.arbitrage_signals else None
                ),
                'last_health_check': datetime.utcnow().isoformat()
            })

            # Log health issues
            if time_arbitrage_health_status in ['unhealthy', 'critical']:
                logger.warning(
                    "Time arbitrage strategy health issues detected",
                    status=time_arbitrage_health_status,
                    score=health_score,
                    circuit_breaker=circuit_breaker_status.get('active', False)
                )

            return base_health

        except Exception as e:
            logger.error("Time arbitrage health check failed", error=str(e))
            return {
                'status': 'critical',
                'error': str(e),
                'strategy_id': self.strategy_id,
                'timestamp': datetime.utcnow().isoformat()
            }

    # Additional time arbitrage-specific methods

    async def get_arbitrage_performance_summary(self) -> Dict[str, Any]:
        """Get detailed arbitrage performance summary"""
        try:
            return {
                'performance_stats': self.time_arbitrage_stats,
                'active_opportunities': len(self.active_opportunities),
                'arbitrage_success_rate': self._calculate_arbitrage_success_rate(),
                'timeframe_accuracy': self._calculate_timeframe_accuracy(),
                'risk_metrics': {
                    'max_drawdown': self.time_arbitrage_stats['max_drawdown'],
                    'avg_holding_period': self.time_arbitrage_stats['average_holding_period'],
                    'sharpe_ratio': self._calculate_sharpe_ratio()
                },
                'arbitrage_types_performance': self._calculate_arbitrage_types_performance()
            }

        except Exception as e:
            logger.error("Failed to get arbitrage performance summary", error=str(e))
            return {'error': str(e)}

    def _calculate_arbitrage_success_rate(self) -> float:
        """Calculate success rate of arbitrage signals"""
        if not self.arbitrage_signals:
            return 0.0

        # Simplified - in reality would track which signals led to successful trades
        successful_signals = len([s for s in self.arbitrage_signals if s.confidence_score > 0.8])
        return successful_signals / len(self.arbitrage_signals)

    def _calculate_timeframe_accuracy(self) -> float:
        """Calculate accuracy of timeframe predictions"""
        # Simplified calculation
        if len(self.timeframe_history) < 2:
            return 0.5

        # Check if timeframe predictions were accurate (simplified)
        accurate_predictions = 0
        total_predictions = 0

        for symbol, history in self.timeframe_history.items():
            if len(history) >= 5:
                # Check momentum direction accuracy
                for i in range(4, len(history)):
                    predicted_direction = 1 if history[i - 4].momentum > 0 else -1
                    actual_direction = 1 if history[i].momentum > 0 else -1

                    if predicted_direction == actual_direction:
                        accurate_predictions += 1
                    total_predictions += 1

        return accurate_predictions / total_predictions if total_predictions > 0 else 0.5

    def _calculate_sharpe_ratio(self) -> float:
        """Calculate Sharpe ratio for risk-adjusted returns"""
        if not self.time_arbitrage_stats['total_opportunities'] or self.time_arbitrage_stats['max_drawdown'] == 0:
            return 0.0

        avg_return = self.time_arbitrage_stats.get('average_return_per_trade', 0)
        volatility = self.time_arbitrage_stats['max_drawdown']  # Simplified volatility measure

        return avg_return / volatility if volatility > 0 else 0.0

    def _calculate_arbitrage_types_performance(self) -> Dict[str, Any]:
        """Calculate performance by arbitrage type"""
        try:
            type_performance = {}

            for signal in self.arbitrage_signals:
                arb_type = signal.signal_type.value
                if arb_type not in type_performance:
                    type_performance[arb_type] = {
                        'count': 0,
                        'avg_confidence': 0,
                        'avg_expected_return': 0
                    }

                type_performance[arb_type]['count'] += 1
                type_performance[arb_type]['avg_confidence'] += signal.confidence_score
                type_performance[arb_type]['avg_expected_return'] += signal.expected_return

            # Calculate averages
            for arb_type, stats in type_performance.items():
                if stats['count'] > 0:
                    stats['avg_confidence'] /= stats['count']
                    stats['avg_expected_return'] /= stats['count']

            return type_performance

        except Exception as e:
            logger.error("Failed to calculate arbitrage types performance", error=str(e))
            return {}

    # Resource Management and Cleanup Methods

    async def cleanup(self):
        """
        Comprehensive cleanup of resources

        Ensures all connections are properly closed and resources are freed
        """
        try:
            logger.info("Starting Time arbitrage strategy cleanup")

            # Close AI client connection
            if self.ai_client:
                try:
                    await self.ai_client.disconnect()
                    logger.debug("AI client disconnected")
                except Exception as e:
                    logger.warning("Failed to disconnect AI client", error=str(e))

            # Clear active opportunities and signals
            self.active_opportunities.clear()
            self.arbitrage_signals.clear()

            # Clear timeframe history to free memory
            self.timeframe_history.clear()
            self.correlation_matrices.clear()

            # Reset statistical models
            self.statistical_models.clear()

            # Reset market session data
            self.market_open_time = None
            self.opening_range_high = None
            self.opening_range_low = None
            self.opening_range_established = False

            # Reset circuit breaker
            await self._deactivate_circuit_breaker()

            # Call parent cleanup
            await super().cleanup()

            logger.info("Time arbitrage strategy cleanup completed")

        except Exception as e:
            logger.error("Time arbitrage strategy cleanup failed", error=str(e))
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
            if hasattr(asyncio, '_get_running_loop'):
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
                'timeframe_history_size': sum(len(history) for history in self.timeframe_history.values()),
                'arbitrage_signals_count': len(self.arbitrage_signals),
                'correlation_matrices_size': len(self.correlation_matrices),
                'statistical_models_count': len(self.statistical_models),
                'active_opportunities_count': len(self.active_opportunities),
                'circuit_breaker_active': self.circuit_breaker_active,
                'consecutive_failures': self.consecutive_failures,
                'memory_usage_estimate': self._estimate_memory_usage()
            }
        except Exception as e:
            logger.error("Failed to get resource usage", error=str(e))
            return {'error': str(e)}

    def _estimate_memory_usage(self) -> int:
        """Estimate memory usage in bytes"""
        try:
            # Rough estimation
            base_usage = 1024 * 1024  # 1MB base
            timeframe_usage = sum(len(history) * 256 for history in self.timeframe_history.values())  # ~256B per timeframe data point
            arbitrage_usage = len(self.arbitrage_signals) * 1024  # ~1KB per arbitrage signal
            opportunities_usage = len(self.active_opportunities) * 2048  # ~2KB per opportunity

            return base_usage + timeframe_usage + arbitrage_usage + opportunities_usage
        except Exception:
            return 0

    async def optimize_resources(self):
        """Optimize resource usage by cleaning up old data"""
        try:
            current_time = datetime.utcnow()

            # Clean up old timeframe history (keep last 24 hours)
            cutoff_time = current_time.replace(hour=current_time.hour - 24)
            for symbol in list(self.timeframe_history.keys()):
                self.timeframe_history[symbol] = [
                    tf for tf in self.timeframe_history[symbol]
                    if tf.timestamp > cutoff_time
                ]
                # Remove empty histories
                if not self.timeframe_history[symbol]:
                    del self.timeframe_history[symbol]

            # Clean up old arbitrage signals (keep last 100)
            if len(self.arbitrage_signals) > 100:
                self.arbitrage_signals = self.arbitrage_signals[-100:]

            # Clean up expired opportunities
            expired_opportunities = []
            for opp_id, opportunity in self.active_opportunities.items():
                if (current_time - datetime.fromtimestamp(current_time.timestamp() - opportunity.expiry_seconds)).seconds > opportunity.expiry_seconds:
                    expired_opportunities.append(opp_id)

            for opp_id in expired_opportunities:
                del self.active_opportunities[opp_id]

            logger.debug("Resource optimization completed", cleaned_opportunities=len(expired_opportunities))

        except Exception as e:
            logger.error("Resource optimization failed", error=str(e))


# Factory function for creating time arbitrage strategy instances
def create_time_arbitrage_strategy(config: StrategyConfig, learning_engine=None) -> TimeArbitrageStrategy:
    """
    Create a Time arbitrage strategy instance

    Args:
        config: Strategy configuration
        learning_engine: Optional learning engine

    Returns:
        TimeArbitrageStrategy: Configured time arbitrage strategy instance
    """
    return TimeArbitrageStrategy(config, learning_engine)


# Example usage and testing functions
async def example_time_arbitrage_usage():
    """Example usage of the Time arbitrage strategy"""

    # Create strategy configuration
    config = StrategyConfig(
        name="NIRAJ Time Arbitrage Strategy",
        description="Quantitative time-based market inefficiency exploitation",
        strategy_type=StrategyType.QUANTITATIVE,
        max_position_size=0.04,  # Conservative quantitative sizing
        max_drawdown_limit=0.06,  # Tighter drawdown limit
        stop_loss_percentage=0.025,  # Tighter stops
        take_profit_percentage=0.06,  # Higher targets for arbitrage
        min_signal_strength=0.75,  # High conviction required
        max_trades_per_day=8,  # Higher frequency for time arbitrage
        supported_symbols=["NIFTY", "BANKNIFTY"],
        custom_params={
            'min_timeframe_divergence': 0.5,
            'opening_range_percentage': 0.02,
            'momentum_threshold': 1.5,
            'min_confidence': 0.75
        }
    )

    # Create strategy instance
    time_arbitrage = create_time_arbitrage_strategy(config)

    try:
        # Initialize strategy
        initialized = await time_arbitrage.initialize()
        if not initialized:
            print("Failed to initialize time arbitrage strategy")
            return

        print("Time arbitrage strategy initialized successfully")

        # Example market data
        class MockMarketData:
            def __init__(self):
                self.symbol = "NIFTY"
                self.timestamp = datetime.utcnow()
                self.open = 18000.0
                self.high = 18100.0
                self.low = 17900.0
                self.close = 18050.0  # Intraday move
                self.volume = 300000

        market_data = MockMarketData()

        # Analyze market
        analysis = await time_arbitrage.analyze_market(market_data)
        print(f"Market analysis completed with temporal sentiment: {analysis.sentiment_score:.3f}")

        # Generate signals
        signals = await time_arbitrage.generate_signals(analysis)
        print(f"Generated {len(signals)} time arbitrage signals")

        for signal in signals:
            print(f"Signal: {signal.signal_type.value} {signal.symbol} at {signal.entry_price} (strength: {signal.strength:.3f})")

        # Health check
        health = await time_arbitrage.health_check()
        print(f"Strategy health: {health['status']}")

        # Cleanup
        await time_arbitrage.cleanup()

    except Exception as e:
        print(f"Error in time arbitrage strategy example: {str(e)}")


if __name__ == "__main__":
    # Run example usage
    asyncio.run(example_time_arbitrage_usage())
