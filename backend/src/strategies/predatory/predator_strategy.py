"""
Predator Strategy Implementation for NIRAJ Trading System

High-risk, high-reward strategy that analyzes order book depth and front-runs
institutional orders. This strategy aims to profit from large institutional
trades by anticipating and trading ahead of them.

Key Features:
- Order book analysis and depth of market monitoring
- Institutional order pattern recognition
- Front-running signal generation with microsecond precision
- Advanced risk management for high-volatility trades
- AI-powered confidence scoring and pattern recognition
- Real-time market microstructure analysis
"""

import time
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import structlog
import uuid

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
            'strategy.predator.min_order_book_depth': 10,
            'strategy.predator.institutional_size_threshold': 1000,
            'strategy.predator.front_running_window': 5,
            'strategy.predator.max_slippage': 0.1,
            'strategy.predator.min_confidence': 0.8,
            'strategy.predator.max_history_size': 100,
            'strategy.predator.pattern_recognition_window': 30,
            'strategy.predator.max_active_opportunities': 5,
            'strategy.predator.max_concurrent_positions': 1,
            'strategy.predator.emergency_stop_multiplier': 2.0,
            'strategy.predator.profit_taking_levels': [0.5, 1.0, 2.0, 5.0, 10.0],
            'strategy.predator.max_consecutive_failures': 5
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
        strategy_type: StrategyType = StrategyType.PREDATORY
        max_position_size: float = 0.1
        max_drawdown_limit: float = 0.15
        stop_loss_percentage: float = 0.05
        take_profit_percentage: float = 0.10
        min_signal_strength: float = 0.8
        max_trades_per_day: int = 50
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


# Custom Exception Types for Predator Strategy
class PredatorStrategyError(Exception):
    """Base exception for Predator strategy errors"""
    pass


class ConfigurationError(PredatorStrategyError):
    """Configuration validation errors"""
    pass


class ValidationError(PredatorStrategyError):
    """Input validation errors"""
    pass


class OrderBookError(PredatorStrategyError):
    """Order book related errors"""
    pass


class InstitutionalDetectionError(PredatorStrategyError):
    """Institutional order detection errors"""
    pass


class CircuitBreakerError(PredatorStrategyError):
    """Circuit breaker activation errors"""
    pass


class ResourceError(PredatorStrategyError):
    """Resource management errors"""
    pass


# Validation utilities
class PredatorValidator:
    """Comprehensive validation utilities for Predator strategy"""

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

    @staticmethod
    def validate_config(config) -> None:
        """Validate strategy configuration"""
        if not config:
            raise ConfigurationError("Strategy configuration cannot be None")

        if config.strategy_type != StrategyType.PREDATORY:
            raise ConfigurationError(f"Invalid strategy type: {config.strategy_type}. Expected PREDATORY")

        if not isinstance(config.max_position_size, (int, float)) or not (0 < config.max_position_size <= 1):
            raise ConfigurationError("max_position_size must be between 0 and 1")

        if not isinstance(config.max_drawdown_limit, (int, float)) or not (0 < config.max_drawdown_limit <= 1):
            raise ConfigurationError("max_drawdown_limit must be between 0 and 1")

        if hasattr(config, 'custom_params') and config.custom_params:
            custom_params = config.custom_params
            if 'institutional_threshold' in custom_params:
                threshold = custom_params['institutional_threshold']
                if not isinstance(threshold, (int, float)) or threshold <= 0:
                    raise ConfigurationError("institutional_threshold must be positive number")

            if 'front_running_window' in custom_params:
                window = custom_params['front_running_window']
                if not isinstance(window, (int, float)) or window <= 0:
                    raise ConfigurationError("front_running_window must be positive number")

    @staticmethod
    def validate_order_book_snapshot(snapshot) -> None:
        """Validate order book snapshot"""
        if not snapshot:
            raise OrderBookError("Order book snapshot cannot be None")

        if not isinstance(snapshot.symbol, str) or not snapshot.symbol.strip():
            raise OrderBookError("Invalid symbol in order book snapshot")

        if not isinstance(snapshot.bids, list) or not isinstance(snapshot.asks, list):
            raise OrderBookError("Order book bids and asks must be lists")

        # Validate bid levels (should be sorted descending)
        for i, level in enumerate(snapshot.bids):
            if not isinstance(level.price, (int, float)) or level.price <= 0:
                raise OrderBookError(f"Invalid bid price at index {i}")
            if not isinstance(level.quantity, (int, float)) or level.quantity <= 0:
                raise OrderBookError(f"Invalid bid quantity at index {i}")
            if i > 0 and level.price >= snapshot.bids[i - 1].price:
                raise OrderBookError("Bid prices must be sorted in descending order")

        # Validate ask levels (should be sorted ascending)
        for i, level in enumerate(snapshot.asks):
            if not isinstance(level.price, (int, float)) or level.price <= 0:
                raise OrderBookError(f"Invalid ask price at index {i}")
            if not isinstance(level.quantity, (int, float)) or level.quantity <= 0:
                raise OrderBookError(f"Invalid ask quantity at index {i}")
            if i > 0 and level.price <= snapshot.asks[i - 1].price:
                raise OrderBookError("Ask prices must be sorted in ascending order")

    @staticmethod
    def validate_institutional_detection(detection) -> None:
        """Validate institutional order detection"""
        if not detection:
            raise InstitutionalDetectionError("Detection cannot be None")

        if not isinstance(detection.confidence_score, (int, float)) or not (0 <= detection.confidence_score <= 1):
            raise InstitutionalDetectionError("Confidence score must be between 0 and 1")

        if detection.direction not in ["buy", "sell"]:
            raise InstitutionalDetectionError("Direction must be 'buy' or 'sell'")

        if not isinstance(detection.estimated_size, (int, float)) or detection.estimated_size <= 0:
            raise InstitutionalDetectionError("Estimated size must be positive")

    @staticmethod
    def validate_signal_parameters(**kwargs) -> None:
        """Validate signal generation parameters"""
        confidence_threshold = kwargs.get('confidence_threshold', 0.5)
        if not isinstance(confidence_threshold, (int, float)) or not (0 <= confidence_threshold <= 1):
            raise SignalGenerationError("Confidence threshold must be between 0 and 1")

        max_opportunities = kwargs.get('max_opportunities', 10)
        if not isinstance(max_opportunities, int) or max_opportunities <= 0:
            raise SignalGenerationError("Max opportunities must be positive integer")


class OrderBookSide(str, Enum):
    """Order book sides"""
    BID = "bid"  # Buy orders
    ASK = "ask"  # Sell orders


class InstitutionalOrderPattern(str, Enum):
    """Types of institutional order patterns"""
    LARGE_BLOCK = "large_block"              # Single large order
    ICEBERG = "iceberg"                      # Hidden large order in small chunks
    LAYERING = "layering"                    # Multiple orders at different levels
    SPOOFING = "spoofing"                    # Fake orders to manipulate
    MOMENTUM = "momentum"                    # Institutional momentum trading
    ACCUMULATION = "accumulation"            # Slow accumulation over time


class FrontRunningSignal(str, Enum):
    """Front-running signal types"""
    INSTITUTIONAL_BUY = "institutional_buy"      # Front-run institutional buy
    INSTITUTIONAL_SELL = "institutional_sell"    # Front-run institutional sell
    MOMENTUM_BREAKOUT = "momentum_breakout"     # Front-run momentum moves
    LIQUIDITY_VOID = "liquidity_void"           # Exploit liquidity gaps
    ORDER_BOOK_IMBALANCE = "order_book_imbalance"  # Exploit order book imbalances


@dataclass
class OrderBookLevel:
    """Individual order book level"""
    price: float
    quantity: int
    order_count: int
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class OrderBookSnapshot:
    """Complete order book snapshot"""
    symbol: str
    timestamp: datetime
    bids: List[OrderBookLevel] = field(default_factory=list)  # Buy orders (sorted descending)
    asks: List[OrderBookLevel] = field(default_factory=list)  # Sell orders (sorted ascending)
    spread: float = 0.0
    total_bid_volume: int = 0
    total_ask_volume: int = 0
    imbalance_ratio: float = 0.0  # (bids - asks) / (bids + asks)


@dataclass
class InstitutionalOrderDetection:
    """Result of institutional order detection"""
    pattern_type: InstitutionalOrderPattern
    confidence_score: float
    estimated_size: float
    direction: str  # "buy" or "sell"
    detection_timestamp: datetime
    supporting_evidence: Dict[str, Any] = field(default_factory=dict)
    risk_assessment: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FrontRunningOpportunity:
    """Front-running trading opportunity"""
    signal_type: FrontRunningSignal
    entry_price: float
    stop_loss_price: float
    take_profit_price: float
    position_size_percentage: float
    confidence_score: float
    risk_reward_ratio: float
    estimated_profit_potential: float
    execution_urgency: str  # "immediate", "high", "medium", "low"
    expiry_seconds: int
    reasoning: str
    market_conditions: Dict[str, Any] = field(default_factory=dict)


class PredatorStrategy(BaseStrategy):
    """
    Predator Strategy: Order Book Analysis and Institutional Front-Running

    This strategy implements advanced order book analysis to detect institutional
    trading patterns and front-run them for high-profit potential trades.

    Key Components:
    - Real-time order book monitoring and analysis
    - Institutional order pattern recognition
    - Front-running signal generation
    - Ultra-fast execution with risk management
    - AI-powered confidence scoring
    """

    def __init__(self, config: StrategyConfig, learning_engine=None):
        """Initialize the Predator strategy with comprehensive validation"""
        try:
            # Validate configuration first
            PredatorValidator.validate_config(config)

            # Initialize parent class
            super().__init__(config, learning_engine)

            # Strategy-specific configuration with validation
            self.min_order_book_depth = get_config('strategy.predator.min_order_book_depth', 10)
            if not isinstance(self.min_order_book_depth, int) or self.min_order_book_depth < 1:
                raise ConfigurationError("min_order_book_depth must be positive integer")

            self.institutional_size_threshold = get_config('strategy.predator.institutional_size_threshold', 1000)
            if not isinstance(self.institutional_size_threshold, (int, float)) or self.institutional_size_threshold <= 0:
                raise ConfigurationError("institutional_size_threshold must be positive number")

            self.front_running_window_seconds = get_config('strategy.predator.front_running_window', 5)
            if not isinstance(self.front_running_window_seconds, (int, float)) or self.front_running_window_seconds <= 0:
                raise ConfigurationError("front_running_window must be positive number")

            self.max_slippage_percentage = get_config('strategy.predator.max_slippage', 0.1)
            if not isinstance(self.max_slippage_percentage, (int, float)) or not (0 <= self.max_slippage_percentage <= 1):
                raise ConfigurationError("max_slippage must be between 0 and 1")

            self.min_confidence_threshold = get_config('strategy.predator.min_confidence', 0.8)
            if not isinstance(self.min_confidence_threshold, (int, float)) or not (0 <= self.min_confidence_threshold <= 1):
                raise ConfigurationError("min_confidence must be between 0 and 1")

            # Order book tracking with validation
            self.current_order_book: Optional[OrderBookSnapshot] = None
            self.order_book_history: List[OrderBookSnapshot] = []
            self.max_history_size = get_config('strategy.predator.max_history_size', 100)
            if not isinstance(self.max_history_size, int) or self.max_history_size < 1:
                raise ConfigurationError("max_history_size must be positive integer")

            # Institutional order detection with validation
            self.detection_history: List[InstitutionalOrderDetection] = []
            self.pattern_recognition_window = get_config('strategy.predator.pattern_recognition_window', 30)
            if not isinstance(self.pattern_recognition_window, (int, float)) or self.pattern_recognition_window <= 0:
                raise ConfigurationError("pattern_recognition_window must be positive number")

            # Front-running state with validation
            self.active_opportunities: Dict[str, FrontRunningOpportunity] = {}
            self.executed_front_runs: List[Dict[str, Any]] = []
            self.max_active_opportunities = get_config('strategy.predator.max_active_opportunities', 5)
            if not isinstance(self.max_active_opportunities, int) or self.max_active_opportunities < 1:
                raise ConfigurationError("max_active_opportunities must be positive integer")

            # AI and technical analysis components
            self.indicators_calculator = TechnicalIndicatorsCalculator()
            self.ai_client = Gemma3Client()
            self.confidence_tracker = AdvancedConfidenceTracker()

            # Performance tracking with validation
            self.front_running_stats = {
                'total_opportunities': 0,
                'successful_front_runs': 0,
                'failed_front_runs': 0,
                'average_profit_per_trade': 0.0,
                'win_rate': 0.0,
                'average_holding_time': 0.0,
                'max_drawdown': 0.0,
                'total_trading_volume': 0.0,
                'best_trade': 0.0,
                'worst_trade': 0.0
            }

            # Risk management parameters with validation
            self.max_concurrent_positions = get_config('strategy.predator.max_concurrent_positions', 1)
            if not isinstance(self.max_concurrent_positions, int) or self.max_concurrent_positions < 1:
                raise ConfigurationError("max_concurrent_positions must be positive integer")

            self.emergency_stop_loss_multiplier = get_config('strategy.predator.emergency_stop_multiplier', 2.0)
            if not isinstance(self.emergency_stop_loss_multiplier, (int, float)) or self.emergency_stop_loss_multiplier <= 1:
                raise ConfigurationError("emergency_stop_multiplier must be greater than 1")

            self.profit_taking_levels = get_config('strategy.predator.profit_taking_levels', [0.5, 1.0, 2.0, 5.0, 10.0])
            if not isinstance(self.profit_taking_levels, list) or not all(isinstance(x, (int, float)) and x > 0 for x in self.profit_taking_levels):
                raise ConfigurationError("profit_taking_levels must be list of positive numbers")

            # Circuit breaker state
            self.circuit_breaker_active = False
            self.circuit_breaker_reason = ""
            self.circuit_breaker_timestamp = None
            self.consecutive_failures = 0
            self.max_consecutive_failures = get_config('strategy.predator.max_consecutive_failures', 5)

            logger.info(
                "Predator strategy initialized with validation",
                strategy_id=self.strategy_id,
                min_confidence=self.min_confidence_threshold,
                institutional_threshold=self.institutional_size_threshold,
                max_concurrent_positions=self.max_concurrent_positions
            )

        except (ConfigurationError, ValidationError) as e:
            logger.error("Predator strategy initialization validation failed", error=str(e))
            raise
        except Exception as e:
            logger.error("Unexpected error during Predator strategy initialization", error=str(e))
            raise ConfigurationError(f"Failed to initialize Predator strategy: {str(e)}")

    async def initialize(self) -> bool:
        """
        Initialize the Predator strategy with required resources

        Returns:
            True if initialization successful
        """
        try:
            self.current_phase = StrategyPhase.INITIALIZING

            # Initialize AI client
            await self.ai_client.connect()

            # Validate configuration
            if self.config.strategy_type != StrategyType.PREDATORY:
                raise ValueError(f"Invalid strategy type: {self.config.strategy_type}")

            # Set up high-frequency monitoring
            self.config.max_trades_per_day = 50  # Higher frequency for predator
            self.config.min_signal_strength = self.min_confidence_threshold

            # Initialize technical indicators
            await self._initialize_technical_indicators()

            logger.info("Predator strategy initialization completed")
            return True

        except Exception as e:
            logger.error("Predator strategy initialization failed", error=str(e))
            return False

    async def _initialize_technical_indicators(self):
        """Initialize technical indicators required for predator analysis"""
        # Predator strategy uses specific indicators for order book analysis
        self.required_indicators = [
            IndicatorType.PREDATOR_SIGNAL,
            IndicatorType.VOLUME_WEIGHTED_AVERAGE_PRICE,
            IndicatorType.BOLLINGER_BANDS,
            IndicatorType.RSI,
            IndicatorType.MACD,
            IndicatorType.ATR,
            IndicatorType.CHAIKIN_MF
        ]

    async def analyze_market(self, market_data: MarketData) -> MarketAnalysis:
        """
        Analyze market data with comprehensive validation and error handling

        Args:
            market_data: Current market data

        Returns:
            MarketAnalysis with predator-specific insights

        Raises:
            ValidationError: If market data is invalid
            CircuitBreakerError: If circuit breaker is active
            OrderBookError: If order book operations fail
        """
        try:
            # Check circuit breaker
            if self.circuit_breaker_active:
                raise CircuitBreakerError(f"Circuit breaker active: {self.circuit_breaker_reason}")

            # Validate input
            PredatorValidator.validate_market_data(market_data)

            self.current_phase = StrategyPhase.ANALYZING
            start_time = time.time()

            # Update order book with error handling
            await self._update_order_book(market_data)

            # Calculate technical indicators with fallback
            indicators = await self._calculate_technical_indicators(market_data)

            # Analyze order book patterns with validation
            await self._analyze_order_book_patterns()

            # Detect institutional orders with error recovery
            await self._detect_institutional_orders()

            # AI-powered market sentiment analysis with fallback
            ai_insights = await self._get_ai_market_insights(market_data, indicators)

            # Calculate market microstructure metrics
            microstructure = await self._calculate_market_microstructure()

            analysis = MarketAnalysis(
                symbol=market_data.symbol,
                analysis_type="predator_analysis",
                indicators=indicators,
                ai_insights=ai_insights,
                sentiment_score=microstructure.get('market_sentiment', 0.0),
                volatility=microstructure.get('volatility', 0.0),
                liquidity_score=microstructure.get('liquidity_score', 1.0),
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
                confidence=analysis.confidence_score,
                processing_time_ms=analysis.processing_time_ms,
                order_book_available=bool(self.current_order_book)
            )

            return analysis

        except (ValidationError, CircuitBreakerError) as e:
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
                analysis_type="degraded_predator_analysis",
                indicators={},
                ai_insights={
                    'institutional_probability': 0.5,
                    'detected_patterns': [],
                    'market_sentiment': 'neutral',
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
            raise CircuitBreakerError(f"Circuit breaker activation failed: {str(e)}")

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

            # Auto-recovery after 5 minutes
            if self.circuit_breaker_timestamp:
                time_since_activation = (datetime.utcnow() - self.circuit_breaker_timestamp).seconds
                if time_since_activation > 300:  # 5 minutes
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

    async def _update_order_book(self, market_data: MarketData):
        """Update order book snapshot from market data"""
        # In a real implementation, this would connect to broker APIs for live order book
        # For now, simulate order book based on market data

        try:
            # Simulate realistic order book based on current market data
            current_price = float(market_data.close)

            # Generate bid side (buy orders) - descending prices
            bids = []
            total_bid_volume = 0
            for i in range(10):  # Top 10 bid levels
                price = current_price - (i * 0.1)  # 0.1 price decrements
                quantity = int(market_data.volume * (0.1 - i * 0.008))  # Decreasing volume
                if quantity > 0:
                    bids.append(OrderBookLevel(
                        price=round(price, 2),
                        quantity=quantity,
                        order_count=max(1, quantity // 100)
                    ))
                    total_bid_volume += quantity

            # Generate ask side (sell orders) - ascending prices
            asks = []
            total_ask_volume = 0
            for i in range(10):  # Top 10 ask levels
                price = current_price + ((i + 1) * 0.1)  # 0.1 price increments
                quantity = int(market_data.volume * (0.1 - i * 0.008))  # Decreasing volume
                if quantity > 0:
                    asks.append(OrderBookLevel(
                        price=round(price, 2),
                        quantity=quantity,
                        order_count=max(1, quantity // 100)
                    ))
                    total_ask_volume += quantity

            # Calculate spread and imbalance
            spread = asks[0].price - bids[0].price if asks and bids else 0.0
            imbalance_ratio = (total_bid_volume - total_ask_volume) / (total_bid_volume + total_ask_volume) if (total_bid_volume + total_ask_volume) > 0 else 0.0

            # Create order book snapshot
            snapshot = OrderBookSnapshot(
                symbol=market_data.symbol,
                timestamp=market_data.timestamp,
                bids=bids,
                asks=asks,
                spread=spread,
                total_bid_volume=total_bid_volume,
                total_ask_volume=total_ask_volume,
                imbalance_ratio=imbalance_ratio
            )

            # Update current order book and history
            self.current_order_book = snapshot
            self.order_book_history.append(snapshot)

            # Maintain history size
            if len(self.order_book_history) > self.max_history_size:
                self.order_book_history.pop(0)

        except Exception:
            logger.warning("Failed to update order book")

    async def _calculate_technical_indicators(self, market_data: MarketData) -> Dict[str, Any]:
        """Calculate technical indicators for predator analysis"""
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
                    logger.warning(f"Failed to calculate {indicator_type.value}", error=str(e))
                    indicators[indicator_type.value] = None

            return indicators

        except Exception as e:
            logger.error("Technical indicators calculation failed", error=str(e))
            return {}

    async def _analyze_order_book_patterns(self) -> Dict[str, Any]:
        """Analyze order book patterns for institutional activity"""
        try:
            if not self.current_order_book:
                return {}

            ob = self.current_order_book

            # Analyze bid-ask imbalance
            imbalance_analysis = {
                'ratio': ob.imbalance_ratio,
                'strength': 'strong' if abs(ob.imbalance_ratio) > 0.3 else 'moderate' if abs(ob.imbalance_ratio) > 0.1 else 'weak',
                'direction': 'bullish' if ob.imbalance_ratio > 0 else 'bearish'
            }

            # Analyze order book depth
            depth_analysis = {
                'bid_depth': len(ob.bids),
                'ask_depth': len(ob.asks),
                'total_bid_volume': ob.total_bid_volume,
                'total_ask_volume': ob.total_ask_volume,
                'spread_bps': (ob.spread / ((ob.bids[0].price + ob.asks[0].price) / 2)) * 10000 if ob.bids and ob.asks else 0
            }

            # Detect large orders (potential institutional)
            large_orders = {
                'large_bids': [level for level in ob.bids if level.quantity >= self.institutional_size_threshold],
                'large_asks': [level for level in ob.asks if level.quantity >= self.institutional_size_threshold],
                'institutional_presence': any(level.quantity >= self.institutional_size_threshold for level in ob.bids + ob.asks)
            }

            # Analyze order clustering
            clustering = await self._analyze_order_clustering(ob)

            return {
                'imbalance': imbalance_analysis,
                'depth': depth_analysis,
                'large_orders': large_orders,
                'clustering': clustering,
                'timestamp': ob.timestamp.isoformat()
            }

        except Exception as e:
            logger.error("Order book pattern analysis failed", error=str(e))
            return {}

    async def _analyze_order_clustering(self, order_book: OrderBookSnapshot) -> Dict[str, Any]:
        """Analyze order clustering patterns"""
        try:
            # Calculate price levels and their concentrations
            # bid_prices = [level.price for level in order_book.bids]
            # ask_prices = [level.price for level in order_book.asks]

            # Detect iceberg orders (orders placed at same price level)
            bid_clustering = {}
            for level in order_book.bids:
                if level.price not in bid_clustering:
                    bid_clustering[level.price] = 0
                bid_clustering[level.price] += level.quantity

            ask_clustering = {}
            for level in order_book.asks:
                if level.price not in ask_clustering:
                    ask_clustering[level.price] = 0
                ask_clustering[level.price] += level.quantity

            # Find potential iceberg orders (unusually large at single level)
            avg_bid_per_level = order_book.total_bid_volume / len(order_book.bids) if order_book.bids else 0
            avg_ask_per_level = order_book.total_ask_volume / len(order_book.asks) if order_book.asks else 0

            iceberg_bids = [price for price, volume in bid_clustering.items() if volume > avg_bid_per_level * 3]
            iceberg_asks = [price for price, volume in ask_clustering.items() if volume > avg_ask_per_level * 3]

            return {
                'bid_clustering': bid_clustering,
                'ask_clustering': ask_clustering,
                'iceberg_bids': iceberg_bids,
                'iceberg_asks': iceberg_asks,
                'clustering_intensity': len(iceberg_bids) + len(iceberg_asks)
            }

        except Exception as e:
            logger.error("Order clustering analysis failed", error=str(e))
            return {}

    async def _detect_institutional_orders(self) -> List[InstitutionalOrderDetection]:
        """Detect institutional order patterns"""
        try:
            detections = []

            if not self.current_order_book or len(self.order_book_history) < 2:
                return detections

            current_ob = self.current_order_book
            previous_ob = self.order_book_history[-2] if len(self.order_book_history) >= 2 else None

            # 1. Large Block Detection
            for level in current_ob.bids + current_ob.asks:
                if level.quantity >= self.institutional_size_threshold:
                    direction = "buy" if level in current_ob.bids else "sell"
                    detection = InstitutionalOrderDetection(
                        pattern_type=InstitutionalOrderPattern.LARGE_BLOCK,
                        confidence_score=min(0.95, level.quantity / (self.institutional_size_threshold * 2)),
                        estimated_size=level.quantity * level.price,
                        direction=direction,
                        detection_timestamp=current_ob.timestamp,
                        supporting_evidence={
                            'price_level': level.price,
                            'quantity': level.quantity,
                            'order_count': level.order_count
                        }
                    )
                    detections.append(detection)

            # 2. Iceberg Order Detection
            clustering = await self._analyze_order_clustering(current_ob)
            for price in clustering['iceberg_bids'] + clustering['iceberg_asks']:
                direction = "buy" if price in clustering['iceberg_bids'] else "sell"
                detection = InstitutionalOrderDetection(
                    pattern_type=InstitutionalOrderPattern.ICEBERG,
                    confidence_score=0.8,
                    estimated_size=clustering['bid_clustering'].get(price, clustering['ask_clustering'].get(price, 0)) * price,
                    direction=direction,
                    detection_timestamp=current_ob.timestamp,
                    supporting_evidence={'clustered_price': price}
                )
                detections.append(detection)

            # 3. Momentum Detection (rapid order book changes)
            if previous_ob:
                momentum_score = await self._calculate_order_book_momentum(current_ob, previous_ob)
                if momentum_score > 0.7:
                    direction = "buy" if current_ob.imbalance_ratio > previous_ob.imbalance_ratio else "sell"
                    detection = InstitutionalOrderDetection(
                        pattern_type=InstitutionalOrderPattern.MOMENTUM,
                        confidence_score=momentum_score,
                        estimated_size=abs(current_ob.total_bid_volume - previous_ob.total_bid_volume) * current_ob.bids[0].price if current_ob.bids else 0,
                        direction=direction,
                        detection_timestamp=current_ob.timestamp,
                        supporting_evidence={'momentum_score': momentum_score}
                    )
                    detections.append(detection)

            # Store detections for pattern analysis
            self.detection_history.extend(detections)
            if len(self.detection_history) > 50:  # Keep last 50 detections
                self.detection_history = self.detection_history[-50:]

            return detections

        except Exception as e:
            logger.error("Institutional order detection failed", error=str(e))
            return []

    async def _calculate_order_book_momentum(self, current: OrderBookSnapshot, previous: OrderBookSnapshot) -> float:
        """Calculate momentum in order book changes"""
        try:
            # Compare imbalance changes
            imbalance_change = abs(current.imbalance_ratio - previous.imbalance_ratio)

            # Compare volume changes
            bid_volume_change = abs(current.total_bid_volume - previous.total_bid_volume)
            ask_volume_change = abs(current.total_ask_volume - previous.total_ask_volume)
            volume_change_ratio = (bid_volume_change + ask_volume_change) / (previous.total_bid_volume + previous.total_ask_volume) if (previous.total_bid_volume + previous.total_ask_volume) > 0 else 0

            # Combine metrics
            momentum_score = (imbalance_change * 0.6) + (volume_change_ratio * 0.4)
            return min(1.0, momentum_score)

        except Exception:
            return 0.0

    async def _get_ai_market_insights(self, market_data: MarketData, indicators: Dict[str, Any]) -> Dict[str, Any]:
        """Get AI-powered market insights for predator analysis"""
        try:
            # Prepare market context for AI analysis
            market_context = {
                'symbol': market_data.symbol,
                'current_price': float(market_data.close),
                'price_change_pct': ((market_data.close - market_data.open) / market_data.open) * 100 if market_data.open != 0 else 0,
                'volume': market_data.volume,
                'indicators': indicators,
                'order_book': {
                    'spread': self.current_order_book.spread if self.current_order_book else 0,
                    'imbalance': self.current_order_book.imbalance_ratio if self.current_order_book else 0,
                    'depth': len(self.current_order_book.bids) + len(self.current_order_book.asks) if self.current_order_book else 0
                } if self.current_order_book else {}
            }

            # AI analysis for institutional activity detection
            analysis_request = AnalysisRequest(
                analysis_type=AnalysisType.PATTERN_RECOGNITION,
                input_data={
                    'market_data': market_context,
                    'analysis_focus': 'institutional_order_detection',
                    'strategy_context': 'predator_front_running'
                },
                confidence_threshold=0.7
            )

            ai_response = await self.ai_client.analyze(analysis_request)

            return {
                'institutional_probability': ai_response.result.get('confidence', 0.5),
                'detected_patterns': ai_response.result.get('key_points', []),
                'market_sentiment': ai_response.result.get('risk_level', 'medium'),
                'overall_confidence': ai_response.confidence_score,
                'ai_reasoning': ai_response.result.get('rationale', ''),
                'processing_time_ms': ai_response.processing_time_ms
            }

        except Exception as e:
            logger.warning("AI market insights failed", error=str(e))
            return {
                'institutional_probability': 0.5,
                'detected_patterns': [],
                'market_sentiment': 'neutral',
                'overall_confidence': 0.5,
                'ai_reasoning': 'Analysis failed',
                'processing_time_ms': 0
            }

    async def _calculate_market_microstructure(self) -> Dict[str, Any]:
        """Calculate market microstructure metrics"""
        try:
            if not self.current_order_book:
                return {}

            ob = self.current_order_book

            # Calculate liquidity score
            # total_volume = ob.total_bid_volume + ob.total_ask_volume
            spread_bps = (ob.spread / ((ob.bids[0].price + ob.asks[0].price) / 2)) * 10000 if ob.bids and ob.asks else 0
            liquidity_score = max(0, 1 - (spread_bps / 100))  # Lower spread = higher liquidity

            # Calculate volatility from order book
            price_range = (ob.asks[-1].price - ob.bids[-1].price) if ob.asks and ob.bids else 0
            avg_price = (ob.bids[0].price + ob.asks[0].price) / 2 if ob.bids and ob.asks else 0
            volatility = (price_range / avg_price) if avg_price > 0 else 0

            # Calculate market pressure
            market_pressure = ob.imbalance_ratio

            return {
                'liquidity_score': liquidity_score,
                'volatility': volatility,
                'market_pressure': market_pressure,
                'spread_bps': spread_bps,
                'order_book_depth': len(ob.bids) + len(ob.asks),
                'volume_imbalance': ob.imbalance_ratio
            }

        except Exception as e:
            logger.error("Market microstructure calculation failed", error=str(e))
            return {}

    async def generate_signals(self, analysis: MarketAnalysis) -> List[TradingSignal]:
        """
        Generate front-running signals with comprehensive error handling

        Args:
            analysis: Market analysis results

        Returns:
            List of trading signals

        Raises:
            SignalGenerationError: If signal generation fails
            CircuitBreakerError: If circuit breaker is active
        """
        try:
            # Check circuit breaker
            if self.circuit_breaker_active:
                raise CircuitBreakerError(f"Circuit breaker active: {self.circuit_breaker_reason}")

            # Validate analysis input
            if not analysis or not hasattr(analysis, 'symbol'):
                raise ValidationError("Invalid analysis input")

            self.current_phase = StrategyPhase.SIGNAL_GENERATION
            signals = []

            # Check if we have minimum required data
            if not self.current_order_book:
                logger.warning("No order book available for signal generation")
                return signals

            # Detect institutional orders with error recovery
            try:
                institutional_detections = await self._detect_institutional_orders()
            except Exception as e:
                logger.warning("Institutional detection failed, using empty list", error=str(e))
                institutional_detections = []

            # Generate front-running opportunities
            for detection in institutional_detections:
                try:
                    if detection.confidence_score >= self.min_confidence_threshold:
                        opportunity = await self._create_front_running_opportunity(detection, analysis)

                        if opportunity and opportunity.confidence_score >= self.min_confidence_threshold:
                            # Convert opportunity to trading signal
                            signal = await self._convert_opportunity_to_signal(opportunity, analysis)

                            if signal:
                                signals.append(signal)
                                # Track opportunity
                                self.active_opportunities[signal.signal_id] = opportunity

                except Exception as e:
                    logger.warning("Failed to process detection", detection_id=id(detection), error=str(e))
                    continue

            # Limit to high-confidence signals only
            signals = [s for s in signals if s.strength >= self.min_confidence_threshold]

            # Limit active opportunities
            if len(self.active_opportunities) > self.max_active_opportunities:
                # Remove lowest confidence opportunities
                sorted_opportunities = sorted(
                    self.active_opportunities.items(),
                    key=lambda x: x[1].confidence_score
                )
                opportunities_to_remove = sorted_opportunities[:len(sorted_opportunities) - self.max_active_opportunities]
                for opp_id, _ in opportunities_to_remove:
                    del self.active_opportunities[opp_id]

            logger.info(
                "Signals generated successfully",
                signal_count=len(signals),
                institutional_detections=len(institutional_detections),
                active_opportunities=len(self.active_opportunities)
            )

            return signals

        except (ValidationError, CircuitBreakerError) as e:
            logger.warning("Signal generation validation/circuit breaker error", error=str(e))
            raise
        except Exception as e:
            logger.error("Signal generation failed", error=str(e))
            raise SignalGenerationError(f"Failed to generate signals: {str(e)}")

    async def _create_front_running_opportunity(
        self,
        detection: InstitutionalOrderDetection,
        analysis: MarketAnalysis
    ) -> Optional[FrontRunningOpportunity]:
        """Create a front-running opportunity from institutional detection"""
        try:
            if not self.current_order_book:
                return None

            ob = self.current_order_book
            current_price = ob.bids[0].price if ob.bids else 0

            # Determine front-running direction (opposite to institutional order)
            if detection.direction == "buy":
                # Institutional buying - front-run by selling first
                signal_type = FrontRunningSignal.INSTITUTIONAL_BUY
                entry_price = ob.asks[0].price if ob.asks else current_price * 1.001
                # expected_move = "up"  # Expect price to go up after institutional buy
            else:
                # Institutional selling - front-run by buying first
                signal_type = FrontRunningSignal.INSTITUTIONAL_SELL
                entry_price = ob.bids[0].price if ob.bids else current_price * 0.999
                # expected_move = "down"  # Expect price to go down after institutional sell

            # Calculate position sizing based on detection confidence and size
            base_position_size = 0.05  # 5% of portfolio
            confidence_multiplier = detection.confidence_score
            size_multiplier = min(2.0, detection.estimated_size / (self.institutional_size_threshold * 1000))
            position_size_percentage = base_position_size * confidence_multiplier * size_multiplier

            # Risk management
            stop_loss_distance = ob.spread * 3  # 3x spread as stop loss
            if detection.direction == "buy":
                stop_loss_price = entry_price + stop_loss_distance
                take_profit_price = entry_price - (stop_loss_distance * 2)  # 2:1 reward ratio
            else:
                stop_loss_price = entry_price - stop_loss_distance
                take_profit_price = entry_price + (stop_loss_distance * 2)

            # Calculate risk-reward ratio
            risk = abs(entry_price - stop_loss_price)
            reward = abs(take_profit_price - entry_price)
            risk_reward_ratio = reward / risk if risk > 0 else 0

            # Estimate profit potential
            estimated_profit_potential = reward / entry_price * 100  # Percentage

            # Determine execution urgency
            if detection.confidence_score > 0.9 and detection.pattern_type == InstitutionalOrderPattern.LARGE_BLOCK:
                execution_urgency = "immediate"
            elif detection.confidence_score > 0.8:
                execution_urgency = "high"
            elif detection.confidence_score > 0.7:
                execution_urgency = "medium"
            else:
                execution_urgency = "low"

            # Create opportunity
            opportunity = FrontRunningOpportunity(
                signal_type=signal_type,
                entry_price=entry_price,
                stop_loss_price=stop_loss_price,
                take_profit_price=take_profit_price,
                position_size_percentage=position_size_percentage,
                confidence_score=detection.confidence_score,
                risk_reward_ratio=risk_reward_ratio,
                estimated_profit_potential=estimated_profit_potential,
                execution_urgency=execution_urgency,
                expiry_seconds=self.front_running_window_seconds,
                reasoning=f"Institutional {detection.direction} order detected with {detection.confidence_score:.2f} confidence. Front-running opportunity.",
                market_conditions={
                    'order_book_imbalance': ob.imbalance_ratio,
                    'spread': ob.spread,
                    'liquidity_score': analysis.liquidity_score,
                    'volatility': analysis.volatility
                }
            )

            return opportunity

        except Exception as e:
            logger.error("Failed to create front-running opportunity", error=str(e))
            return None

    async def _convert_opportunity_to_signal(
        self,
        opportunity: FrontRunningOpportunity,
        analysis: MarketAnalysis
    ) -> Optional[TradingSignal]:
        """Convert front-running opportunity to trading signal"""
        try:
            # Determine signal type
            if opportunity.signal_type in [FrontRunningSignal.INSTITUTIONAL_BUY, FrontRunningSignal.MOMENTUM_BREAKOUT]:
                signal_type = SignalType.SELL  # Front-run institutional buy with sell
            else:
                signal_type = SignalType.BUY   # Front-run institutional sell with buy

            # Calculate quantity (placeholder - would be calculated based on position size)
            quantity = int((opportunity.position_size_percentage * 100000) / opportunity.entry_price)  # Assume ₹1L portfolio

            signal = TradingSignal(
                strategy_id=self.strategy_id,
                symbol=analysis.symbol,
                signal_type=signal_type,
                strength=opportunity.confidence_score,
                entry_price=opportunity.entry_price,
                stop_loss_price=opportunity.stop_loss_price,
                take_profit_price=opportunity.take_profit_price,
                position_size_percentage=opportunity.position_size_percentage,
                quantity=quantity,
                reasoning=opportunity.reasoning,
                supporting_data={
                    'opportunity_type': opportunity.signal_type.value,
                    'risk_reward_ratio': opportunity.risk_reward_ratio,
                    'estimated_profit_pct': opportunity.estimated_profit_potential,
                    'execution_urgency': opportunity.execution_urgency,
                    'market_conditions': opportunity.market_conditions,
                    'ai_confidence': analysis.ai_insights.get('overall_confidence', 0.5)
                },
                expiry_minutes=opportunity.expiry_seconds // 60
            )

            return signal

        except Exception as e:
            logger.error("Failed to convert opportunity to signal", error=str(e))
            return None

    async def calculate_position_size(self, signal: TradingSignal, portfolio) -> float:
        """
        Calculate position size with predator-specific risk management

        Args:
            signal: Trading signal
            portfolio: Current portfolio state

        Returns:
            Position size as percentage of portfolio
        """
        try:
            # Base position size from signal
            base_size = signal.position_size_percentage

            # Adjust for predator strategy risk
            risk_multiplier = 0.5  # Conservative sizing for high-risk strategy

            # Adjust based on signal confidence
            confidence_multiplier = signal.strength

            # Adjust based on market volatility
            volatility = self.last_analysis.get(signal.symbol, MarketAnalysis(symbol=signal.symbol)).volatility
            volatility_multiplier = max(0.3, 1.0 - volatility)  # Reduce size in high volatility

            # Adjust based on portfolio risk
            portfolio_risk_multiplier = 1.0
            if hasattr(portfolio, 'current_drawdown') and portfolio.current_drawdown > 0.05:
                portfolio_risk_multiplier = 0.5  # Reduce size if portfolio is down

            # Calculate final position size
            position_size = base_size * risk_multiplier * confidence_multiplier * volatility_multiplier * portfolio_risk_multiplier

            # Ensure within strategy limits
            position_size = min(position_size, self.config.max_position_size)
            position_size = max(position_size, 0.01)  # Minimum 1% position

            logger.debug(
                "Position size calculated",
                signal_id=signal.signal_id,
                base_size=base_size,
                final_size=position_size,
                adjustments={
                    'risk': risk_multiplier,
                    'confidence': confidence_multiplier,
                    'volatility': volatility_multiplier,
                    'portfolio': portfolio_risk_multiplier
                }
            )

            return position_size

        except Exception as e:
            logger.error("Position size calculation failed", error=str(e))
            return signal.position_size_percentage * 0.5  # Conservative fallback

    async def manage_risk(self, portfolio) -> List[str]:
        """
        Enhanced risk management for predator strategy

        Args:
            portfolio: Current portfolio state

        Returns:
            List of risk management actions taken
        """
        try:
            actions_taken = await super().manage_risk(portfolio)

            # Predator-specific risk checks
            current_positions = len(self.active_positions)

            # Emergency stop if too many concurrent positions
            if current_positions > self.max_concurrent_positions:
                actions_taken.append("predator_concurrent_position_limit")
                await self._emergency_stop("Too many concurrent predator positions")

            # Check for rapid losses (predator strategy specific)
            recent_trades = [trade for trade in self.executed_front_runs[-10:]]  # Last 10 trades
            if len(recent_trades) >= 5:
                loss_count = sum(1 for trade in recent_trades if trade.get('pnl', 0) < 0)
                loss_rate = loss_count / len(recent_trades)

                if loss_rate > 0.7:  # 70% loss rate
                    actions_taken.append("predator_high_loss_rate")
                    await self._emergency_stop("High loss rate in predator strategy")

            # Check signal quality degradation
            if len(self.active_opportunities) > 10:
                avg_confidence = sum(opp.confidence_score for opp in self.active_opportunities.values()) / len(self.active_opportunities)
                if avg_confidence < 0.6:
                    actions_taken.append("predator_low_signal_quality")
                    # Reduce position sizes for remaining opportunities
                    for opp in self.active_opportunities.values():
                        opp.position_size_percentage *= 0.7

            return actions_taken

        except Exception as e:
            logger.error("Predator risk management failed", error=str(e))
            raise RiskManagementError(f"Predator risk management failed: {str(e)}")

    async def _emergency_stop(self, reason: str):
        """Emergency stop for predator strategy"""
        try:
            logger.warning("Predator emergency stop triggered", reason=reason)

            # Close all active positions immediately
            for position_id in list(self.active_positions.keys()):
                await self._close_position(position_id, f"emergency_stop: {reason}")

            # Clear all active opportunities
            self.active_opportunities.clear()

            # Update status
            self.status = self.status.PAUSED

            # Log emergency action
            self.log_strategy_event("emergency_stop", {"reason": reason, "timestamp": datetime.utcnow().isoformat()})

        except Exception as e:
            logger.error("Emergency stop failed", error=str(e))

    async def update_performance(self, trade_result: Dict[str, Any]):
        """Update predator-specific performance metrics"""
        try:
            await super().update_performance(trade_result)

            # Update predator-specific stats
            self.front_running_stats['total_opportunities'] += 1

            pnl = trade_result.get('pnl', 0.0)
            if pnl > 0:
                self.front_running_stats['successful_front_runs'] += 1
            else:
                self.front_running_stats['failed_front_runs'] += 1

            # Update win rate
            total_trades = self.front_running_stats['successful_front_runs'] + self.front_running_stats['failed_front_runs']
            if total_trades > 0:
                self.front_running_stats['win_rate'] = self.front_running_stats['successful_front_runs'] / total_trades

            # Update average profit
            if total_trades > 0:
                # This is a simplified calculation - in reality would track all P&L
                self.front_running_stats['average_profit_per_trade'] = (
                    self.performance.total_return / total_trades
                )

            # Update max drawdown (simplified)
            if pnl < 0:
                self.front_running_stats['max_drawdown'] = max(
                    self.front_running_stats['max_drawdown'],
                    abs(pnl)
                )

            logger.debug("Predator performance updated", stats=self.front_running_stats)

        except Exception as e:
            logger.error("Predator performance update failed", error=str(e))

    async def health_check(self) -> Dict[str, Any]:
        """Enhanced health check with comprehensive monitoring"""
        try:
            base_health = await super().health_check()

            # Get circuit breaker status
            circuit_breaker_status = await self._check_circuit_breaker_status()

            # Get resource usage
            resource_usage = await self.get_resource_usage()

            # Add predator-specific health metrics
            predator_health = {
                'order_book_status': 'available' if self.current_order_book else 'unavailable',
                'order_book_age_seconds': (
                    (datetime.utcnow() - self.current_order_book.timestamp).seconds
                    if self.current_order_book else None
                ),
                'active_opportunities': len(self.active_opportunities),
                'detection_history_size': len(self.detection_history),
                'ai_client_connected': self.ai_client.is_connected if self.ai_client else False,
                'front_running_stats': self.front_running_stats,
                'signal_quality': {
                    'avg_confidence': (
                        sum(opp.confidence_score for opp in self.active_opportunities.values()) / len(self.active_opportunities)
                        if self.active_opportunities else 0
                    ),
                    'opportunities_count': len(self.active_opportunities),
                    'max_opportunities_limit': self.max_active_opportunities
                },
                'performance_metrics': {
                    'win_rate': self.front_running_stats.get('win_rate', 0),
                    'total_opportunities': self.front_running_stats.get('total_opportunities', 0),
                    'avg_profit_per_trade': self.front_running_stats.get('average_profit_per_trade', 0),
                    'max_drawdown': self.front_running_stats.get('max_drawdown', 0)
                }
            }

            # Add circuit breaker information
            predator_health.update({
                'circuit_breaker': circuit_breaker_status,
                'consecutive_failures': self.consecutive_failures,
                'max_consecutive_failures': self.max_consecutive_failures
            })

            # Add resource monitoring
            predator_health['resources'] = resource_usage

            # Determine overall health with more sophisticated logic
            health_score = 0

            # Order book availability (20 points)
            if self.current_order_book:
                health_score += 20
                # Recent order book (additional 10 points)
                if predator_health['order_book_age_seconds'] and predator_health['order_book_age_seconds'] < 300:  # 5 minutes
                    health_score += 10

            # AI client connection (15 points)
            if predator_health['ai_client_connected']:
                health_score += 15

            # Circuit breaker status (20 points)
            if not circuit_breaker_status.get('active', False):
                health_score += 20

            # Active opportunities within limits (10 points)
            if len(self.active_opportunities) <= self.max_active_opportunities:
                health_score += 10

            # Performance metrics (15 points)
            win_rate = self.front_running_stats.get('win_rate', 0)
            if win_rate >= 0.5:  # At least 50% win rate
                health_score += 15
            elif win_rate >= 0.3:  # At least 30% win rate
                health_score += 10

            # Resource usage (10 points)
            memory_mb = resource_usage.get('memory_usage_estimate', 0) / (1024 * 1024)
            if memory_mb < 100:  # Less than 100MB
                health_score += 10

            # Determine health status based on score
            if health_score >= 80:
                predator_health_status = 'healthy'
            elif health_score >= 60:
                predator_health_status = 'degraded'
            elif health_score >= 40:
                predator_health_status = 'unhealthy'
            else:
                predator_health_status = 'critical'

            base_health.update({
                'predator_health': predator_health,
                'predator_status': predator_health_status,
                'health_score': health_score,
                'last_order_book_update': (
                    self.current_order_book.timestamp.isoformat()
                    if self.current_order_book else None
                ),
                'last_health_check': datetime.utcnow().isoformat()
            })

            # Log health issues
            if predator_health_status in ['unhealthy', 'critical']:
                logger.warning(
                    "Predator strategy health issues detected",
                    status=predator_health_status,
                    score=health_score,
                    circuit_breaker=circuit_breaker_status.get('active', False)
                )

            return base_health

        except Exception as e:
            logger.error("Predator health check failed", error=str(e))
            return {
                'status': 'critical',
                'error': str(e),
                'strategy_id': self.strategy_id,
                'timestamp': datetime.utcnow().isoformat()
            }

    # Additional predator-specific methods

    async def get_institutional_detection_summary(self) -> Dict[str, Any]:
        """Get summary of institutional order detections"""
        try:
            if not self.detection_history:
                return {'total_detections': 0, 'patterns': {}}

            # Analyze detection patterns
            pattern_counts = {}
            confidence_scores = []

            for detection in self.detection_history[-100:]:  # Last 100 detections
                pattern = detection.pattern_type.value
                pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
                confidence_scores.append(detection.confidence_score)

            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0

            return {
                'total_detections': len(self.detection_history),
                'recent_detections': len([d for d in self.detection_history if (datetime.utcnow() - d.detection_timestamp).seconds < 3600]),  # Last hour
                'pattern_distribution': pattern_counts,
                'average_confidence': avg_confidence,
                'high_confidence_detections': len([d for d in confidence_scores if d >= 0.8])
            }

        except Exception as e:
            logger.error("Failed to get detection summary", error=str(e))
            return {'error': str(e)}

    async def get_front_running_performance(self) -> Dict[str, Any]:
        """Get detailed front-running performance metrics"""
        try:
            return {
                'performance_stats': self.front_running_stats,
                'active_opportunities': len(self.active_opportunities),
                'success_rate_trend': self._calculate_success_rate_trend(),
                'profit_distribution': self._calculate_profit_distribution(),
                'risk_metrics': {
                    'max_drawdown': self.front_running_stats['max_drawdown'],
                    'avg_holding_time': self.front_running_stats['average_holding_time'],
                    'risk_adjusted_return': self._calculate_risk_adjusted_return()
                }
            }

        except Exception as e:
            logger.error("Failed to get front-running performance", error=str(e))
            return {'error': str(e)}

    def _calculate_success_rate_trend(self) -> float:
        """Calculate trend in success rate"""
        # Simplified trend calculation
        if len(self.executed_front_runs) < 10:
            return 0.0

        recent_trades = self.executed_front_runs[-10:]
        recent_success_rate = sum(1 for trade in recent_trades if trade.get('pnl', 0) > 0) / len(recent_trades)

        older_trades = self.executed_front_runs[-20:-10] if len(self.executed_front_runs) >= 20 else []
        if older_trades:
            older_success_rate = sum(1 for trade in older_trades if trade.get('pnl', 0) > 0) / len(older_trades)
            return recent_success_rate - older_success_rate

        return 0.0

    def _calculate_profit_distribution(self) -> Dict[str, Any]:
        """Calculate profit distribution statistics"""
        if not self.executed_front_runs:
            return {'total_trades': 0}

        pnls = [trade.get('pnl', 0) for trade in self.executed_front_runs]
        positive_pnls = [p for p in pnls if p > 0]
        negative_pnls = [p for p in pnls if p < 0]

        return {
            'total_trades': len(pnls),
            'profitable_trades': len(positive_pnls),
            'losing_trades': len(negative_pnls),
            'avg_profit': sum(positive_pnls) / len(positive_pnls) if positive_pnls else 0,
            'avg_loss': sum(negative_pnls) / len(negative_pnls) if negative_pnls else 0,
            'largest_profit': max(pnls) if pnls else 0,
            'largest_loss': min(pnls) if pnls else 0
        }

    def _calculate_risk_adjusted_return(self) -> float:
        """Calculate risk-adjusted return metric"""
        if not self.executed_front_runs or self.front_running_stats['max_drawdown'] == 0:
            return 0.0

        total_return = sum(trade.get('pnl', 0) for trade in self.executed_front_runs)
        return total_return / self.front_running_stats['max_drawdown']

    # Resource Management and Cleanup Methods

    async def cleanup(self):
        """
        Comprehensive cleanup of resources

        Ensures all connections are properly closed and resources are freed
        """
        try:
            logger.info("Starting Predator strategy cleanup")

            # Close AI client connection
            if self.ai_client:
                try:
                    await self.ai_client.disconnect()
                    logger.debug("AI client disconnected")
                except Exception as e:
                    logger.warning("Failed to disconnect AI client", error=str(e))

            # Clear active opportunities
            self.active_opportunities.clear()

            # Clear order book history to free memory
            self.order_book_history.clear()
            self.current_order_book = None

            # Clear detection history
            self.detection_history.clear()

            # Reset circuit breaker
            await self._deactivate_circuit_breaker()

            # Call parent cleanup
            await super().cleanup()

            logger.info("Predator strategy cleanup completed")

        except Exception as e:
            logger.error("Predator strategy cleanup failed", error=str(e))
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
                'order_book_history_size': len(self.order_book_history),
                'detection_history_size': len(self.detection_history),
                'active_opportunities_count': len(self.active_opportunities),
                'executed_front_runs_count': len(self.executed_front_runs),
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
            order_book_usage = len(self.order_book_history) * 1024  # ~1KB per snapshot
            detection_usage = len(self.detection_history) * 512  # ~512B per detection
            opportunities_usage = len(self.active_opportunities) * 2048  # ~2KB per opportunity

            return base_usage + order_book_usage + detection_usage + opportunities_usage
        except Exception:
            return 0

    async def optimize_resources(self):
        """Optimize resource usage by cleaning up old data"""
        try:
            current_time = datetime.utcnow()

            # Clean up old order book history (keep last 24 hours)
            cutoff_time = current_time.replace(hour=current_time.hour - 24)
            self.order_book_history = [
                ob for ob in self.order_book_history
                if ob.timestamp > cutoff_time
            ]

            # Clean up old detection history (keep last 1000)
            if len(self.detection_history) > 1000:
                self.detection_history = self.detection_history[-1000:]

            # Clean up old executed trades (keep last 1000)
            if len(self.executed_front_runs) > 1000:
                self.executed_front_runs = self.executed_front_runs[-1000:]

            # Clean up expired opportunities
            expired_opportunities = []
            for opp_id, opportunity in self.active_opportunities.items():
                if (current_time - opportunity.expiry_seconds).seconds > opportunity.expiry_seconds:
                    expired_opportunities.append(opp_id)

            for opp_id in expired_opportunities:
                del self.active_opportunities[opp_id]

            logger.debug("Resource optimization completed", cleaned_opportunities=len(expired_opportunities))

        except Exception as e:
            logger.error("Resource optimization failed", error=str(e))


# Factory function for creating predator strategy instances
def create_predator_strategy(config: StrategyConfig, learning_engine=None) -> PredatorStrategy:
    """
    Create a Predator strategy instance

    Args:
        config: Strategy configuration
        learning_engine: Optional learning engine

    Returns:
        PredatorStrategy: Configured predator strategy instance
    """
    return PredatorStrategy(config, learning_engine)


# Example usage and testing functions
async def example_predator_usage():
    """Example usage of the Predator strategy"""

    # Create strategy configuration
    config = StrategyConfig(
        name="NIRAJ Predator Strategy",
        description="High-risk institutional front-running strategy",
        strategy_type=StrategyType.PREDATORY,
        max_position_size=0.1,
        max_drawdown_limit=0.15,  # Higher drawdown limit for high-risk strategy
        stop_loss_percentage=0.05,
        take_profit_percentage=0.10,
        min_signal_strength=0.8,
        max_trades_per_day=50,
        supported_symbols=["BANKNIFTY", "NIFTY"],
        custom_params={
            'front_running_window': 5,
            'institutional_threshold': 1000,
            'min_confidence': 0.8
        }
    )

    # Create strategy instance
    predator = create_predator_strategy(config)

    try:
        # Initialize strategy
        initialized = await predator.initialize()
        if not initialized:
            print("Failed to initialize predator strategy")
            return

        print("Predator strategy initialized successfully")

        # Example market data
        # from ..models.market_data import MarketData
        # from datetime import datetime

        # For example purposes, create a mock market data object
        class MockMarketData:
            def __init__(self):
                self.symbol = "BANKNIFTY"
                self.timestamp = datetime.utcnow()
                self.open = 45000.0
                self.high = 45200.0
                self.low = 44900.0
                self.close = 45150.0
                self.volume = 150000

        market_data = MockMarketData()

        # Analyze market
        analysis = await predator.analyze_market(market_data)
        print(f"Market analysis completed with confidence: {analysis.confidence_score:.3f}")

        # Generate signals
        signals = await predator.generate_signals(analysis)
        print(f"Generated {len(signals)} trading signals")

        for signal in signals:
            print(f"Signal: {signal.signal_type.value} {signal.symbol} at {signal.entry_price} (strength: {signal.strength:.3f})")

        # Health check
        health = await predator.health_check()
        print(f"Strategy health: {health['status']}")

        # Cleanup
        await predator.cleanup()

    except Exception as e:
        print(f"Error in predator strategy example: {str(e)}")


if __name__ == "__main__":
    # Run example usage
    asyncio.run(example_predator_usage())
