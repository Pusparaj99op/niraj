"""
Confidence Tracking System for NIRAJ Trading AI

Advanced confidence tracking and calibration system that learns from prediction outcomes
to improve future confidence estimates. Provides sophisticated metrics, calibration,
and adaptive confidence scoring with comprehensive error handling.

Features:
- Dynamic confidence calibration based on historical performance - Multi-dimensional confidence scoring (accuracy, timing, stability) - Learning mechanisms for confidence improvement - Comprehensive error handling and recovery - Integration with AI models and predictions - Real-time confidence adjustment -
Statistical validation and reporting
"""

import json
import time
import asyncio
import numpy as np
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple, TypedDict, Deque, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
from statistics import mean, median, stdev
import structlog

from ..core.config import get_config
from ..models.ai_model import ModelType
from ..models.ai_prediction import AIPrediction, PredictionType

# Configure structured logging
logger = structlog.get_logger(__name__)


class ConfidenceMetricType(str, Enum):
    """Types of confidence metrics"""

    ACCURACY_CONFIDENCE = "accuracy_confidence"  # Prediction accuracy confidence
    TIMING_CONFIDENCE = "timing_confidence"  # Timing prediction confidence
    MAGNITUDE_CONFIDENCE = "magnitude_confidence"  # Price magnitude confidence
    DIRECTIONAL_CONFIDENCE = "directional_confidence"  # Direction prediction confidence
    STABILITY_CONFIDENCE = "stability_confidence"  # Prediction stability confidence
    MARKET_CONFIDENCE = "market_confidence"  # Market condition confidence
    MODEL_CONFIDENCE = "model_confidence"  # Model-specific confidence
    COMPOSITE_CONFIDENCE = "composite_confidence"  # Overall composite confidence


class CalibrationMethod(str, Enum):
    """Confidence calibration methods"""

    PLATT_SCALING = "platt_scaling"  # Logistic regression calibration
    ISOTONIC_REGRESSION = "isotonic_regression"  # Monotonic calibration
    BAYESIAN_CALIBRATION = "bayesian_calibration"  # Bayesian approach
    TEMPERATURE_SCALING = "temperature_scaling"  # Neural network calibration
    HISTOGRAM_BINNING = "histogram_binning"  # Binning approach
    ADAPTIVE_BINNING = "adaptive_binning"  # Adaptive bin sizing


class ConfidenceLevel(str, Enum):
    """Enhanced confidence levels"""

    CRITICAL_LOW = "critical_low"  # 0.0 - 0.1 (Critical, avoid trading)
    VERY_LOW = "very_low"  # 0.1 - 0.3 (Very cautious)
    LOW = "low"  # 0.3 - 0.5 (Cautious)
    MEDIUM = "medium"  # 0.5 - 0.7 (Moderate)
    HIGH = "high"  # 0.7 - 0.85 (Confident)
    VERY_HIGH = "very_high"  # 0.85 - 0.95 (Very confident)
    CRITICAL_HIGH = "critical_high"  # 0.95 - 1.0 (Extremely confident)


class ConfidenceTrackingError(Exception):
    """Base exception for confidence tracking errors.

    Optional fields are explicitly annotated to satisfy strict type checking.
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.message: str = message
        self.error_code: Optional[str] = error_code
        self.context: Dict[str, Any] = context or {}
        super().__init__(self.message)


class CalibrationError(ConfidenceTrackingError):
    """Exception for confidence calibration errors"""

    pass


class MetricsCalculationError(ConfidenceTrackingError):
    """Exception for metrics calculation errors"""

    pass


class LearningError(ConfidenceTrackingError):
    """Exception for learning mechanism errors"""

    pass


@dataclass
class ConfidenceMetrics:
    """Comprehensive confidence metrics"""

    metric_type: ConfidenceMetricType
    raw_confidence: float
    calibrated_confidence: float
    reliability_score: float
    prediction_count: int
    accuracy_rate: float

    # Calibration metrics
    calibration_error: float = 0.0
    brier_score: float = 0.0
    reliability: float = 0.0
    resolution: float = 0.0

    # Time-based metrics
    temporal_consistency: float = 0.0
    trend_confidence: float = 0.0
    volatility_adjustment: float = 0.0

    # Statistical metrics
    confidence_interval_lower: float = 0.0
    confidence_interval_upper: float = 1.0
    statistical_significance: float = 0.0

    # Meta information
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    sample_size: int = 0
    calibration_method: Optional[CalibrationMethod] = None


@dataclass
class ModelConfidenceProfile:
    """Confidence profile for a specific model"""

    model_id: str
    model_type: ModelType

    # Overall performance
    overall_accuracy: float = 0.0
    overall_confidence: float = 0.0
    prediction_count: int = 0

    # Confidence by prediction type
    type_confidence: "Dict[PredictionType, ConfidenceMetrics]" = field(
        default_factory=lambda: {}
    )

    # Calibration curves
    calibration_curve: "Dict[str, List[float]]" = field(default_factory=lambda: {})
    reliability_diagram: "Dict[str, List[float]]" = field(default_factory=lambda: {})

    # Learning parameters
    learning_rate: float = 0.01
    decay_factor: float = 0.95
    confidence_threshold: float = 0.6

    # Performance tracking
    recent_performance: Deque[float] = field(default_factory=lambda: deque(maxlen=100))
    performance_trend: float = 0.0

    # Error tracking
    error_count: int = 0
    last_error: Optional[str] = None
    recovery_attempts: int = 0


@dataclass
class ConfidenceAdjustment:
    """Confidence adjustment record"""

    adjustment_id: str = field(default_factory=lambda: str(time.time_ns()))
    original_confidence: float = 0.0
    adjusted_confidence: float = 0.0
    adjustment_reason: str = ""
    adjustment_factors: "Dict[str, float]" = field(default_factory=lambda: {})
    market_conditions: "Dict[str, Any]" = field(default_factory=lambda: {})
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class PredictionRecord(TypedDict):
    prediction_id: str
    model_id: str
    prediction_type: str
    confidence_score: float
    calibrated_confidence: float
    reliability_score: float
    timestamp: datetime
    expiry_time: Optional[datetime]
    prediction_value: Any
    input_features: Dict[str, Any]
    market_context: Dict[str, Any]
    outcome_accuracy: Optional[float]
    outcome_determined: bool
    actual_outcome: Optional[Dict[str, Any]]
    outcome_timestamp: Optional[datetime]


class AdvancedConfidenceTracker:
    """
    Advanced confidence tracking and calibration system for NIRAJ AI predictions

    This system provides sophisticated confidence tracking, calibration, and learning
    capabilities to improve the reliability of AI predictions over time.
    """

    def __init__(self) -> None:
        """Initialize the advanced confidence tracker"""

        # Configuration
        self.max_history_size = get_config("ai.confidence.max_history_size", 10000)
        self.calibration_window = get_config("ai.confidence.calibration_window", 1000)
        self.learning_rate = get_config("ai.confidence.learning_rate", 0.01)
        self.confidence_bins = get_config("ai.confidence.bins", 20)
        self.min_samples_for_calibration = get_config("ai.confidence.min_samples", 50)

        # Storage for tracking data
        self.model_profiles: Dict[str, ModelConfidenceProfile] = {}
        self.prediction_history: Deque[PredictionRecord] = deque(
            maxlen=self.max_history_size
        )
        self.confidence_adjustments: Deque[ConfidenceAdjustment] = deque(maxlen=1000)

        # Calibration data
        self.calibration_data: Dict[str, Dict[str, List[Any]]] = defaultdict(
            lambda: defaultdict(list)
        )
        self.calibration_models: Dict[str, Dict[str, Any]] = {}

        # Performance metrics
        self.global_metrics: Dict[str, Any] = {
            "total_predictions": 0,
            "total_correct": 0,
            "calibration_error": 0.0,
            "reliability_score": 0.0,
            "learning_iterations": 0,
            "last_calibration": None,
        }

        # Error tracking and recovery
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.recovery_strategies: Dict[str, Callable[..., Any]] = {}
        self.health_status = "healthy"

        logger.info(
            "Advanced confidence tracker initialized",
            max_history=self.max_history_size,
            calibration_window=self.calibration_window,
            learning_rate=self.learning_rate,
        )

    async def track_prediction_confidence(
        self,
        prediction: AIPrediction,
        market_context: Optional[Dict[str, Any]] = None,
        additional_features: Optional[Dict[str, Any]] = None,
    ) -> ConfidenceMetrics:
        """
        Track confidence for a new prediction

        Args:
            prediction: The AI prediction to track
            market_context: Current market conditions
            additional_features: Additional features for confidence calculation

        Returns:
            ConfidenceMetrics object with calculated confidence scores

        Raises:
            ConfidenceTrackingError: If tracking fails
        """
        try:
            start_time = time.time()

            # Validate input
            if not prediction or not prediction.model_id:
                raise ConfidenceTrackingError("Invalid prediction provided")

            # Get or create model profile
            profile = await self._get_or_create_model_profile(prediction.model_id)

            # Calculate raw confidence metrics
            raw_metrics = await self._calculate_raw_confidence_metrics(
                prediction, market_context, additional_features
            )

            # Apply calibration
            calibrated_metrics = await self._apply_confidence_calibration(
                raw_metrics, profile, prediction.prediction_type
            )

            # Apply dynamic adjustments
            adjusted_metrics = await self._apply_dynamic_adjustments(
                calibrated_metrics, market_context, profile
            )

            # Record for learning
            await self._record_prediction_for_learning(prediction, adjusted_metrics)

            # Update model profile with the prediction type key
            await self._update_model_profile(
                profile, adjusted_metrics, prediction.prediction_type
            )

            processing_time = (time.time() - start_time) * 1000

            logger.info(
                "Confidence tracking completed",
                model_id=prediction.model_id,
                prediction_type=prediction.prediction_type.value,
                raw_confidence=raw_metrics.raw_confidence,
                calibrated_confidence=adjusted_metrics.calibrated_confidence,
                processing_time_ms=processing_time,
            )

            return adjusted_metrics

        except Exception as e:
            await self._handle_tracking_error(
                e, prediction.model_id if prediction else "unknown"
            )
            raise ConfidenceTrackingError(
                f"Failed to track prediction confidence: {str(e)}"
            ) from e

    async def _calculate_raw_confidence_metrics(
        self,
        prediction: AIPrediction,
        market_context: Optional[Dict[str, Any]] = None,
        additional_features: Optional[Dict[str, Any]] = None,
    ) -> ConfidenceMetrics:
        """Calculate raw confidence metrics before calibration"""
        try:
            # Start with model's base confidence
            base_confidence = prediction.confidence_score

            # Calculate component confidences
            accuracy_confidence = await self._calculate_accuracy_confidence(prediction)
            timing_confidence = await self._calculate_timing_confidence(
                prediction, market_context
            )
            stability_confidence = await self._calculate_stability_confidence(
                prediction
            )
            market_confidence = await self._calculate_market_confidence(market_context)

            # Composite confidence calculation
            confidence_components = {
                "base": base_confidence,
                "accuracy": accuracy_confidence,
                "timing": timing_confidence,
                "stability": stability_confidence,
                "market": market_confidence,
            }

            # Weighted average with adaptive weights
            weights = await self._calculate_adaptive_weights(prediction.prediction_type)
            raw_confidence = sum(
                confidence_components[component] * weight
                for component, weight in weights.items()
                if component in confidence_components
            )

            # Ensure confidence is in valid range
            raw_confidence = max(0.0, min(1.0, raw_confidence))

            # Calculate reliability score
            reliability_score = await self._calculate_reliability_score(
                prediction, confidence_components
            )

            return ConfidenceMetrics(
                metric_type=ConfidenceMetricType.COMPOSITE_CONFIDENCE,
                raw_confidence=raw_confidence,
                calibrated_confidence=raw_confidence,  # Will be updated during calibration
                reliability_score=reliability_score,
                prediction_count=1,
                accuracy_rate=0.0,  # Unknown until outcome
                sample_size=1,
            )

        except Exception as e:
            raise MetricsCalculationError(
                f"Failed to calculate raw confidence metrics: {str(e)}"
            ) from e

    async def _calculate_accuracy_confidence(self, prediction: AIPrediction) -> float:
        """Calculate confidence based on model's historical accuracy"""
        try:
            model_profile = self.model_profiles.get(prediction.model_id)
            if not model_profile or model_profile.prediction_count < 10:
                return 0.5  # Neutral confidence for new models

            # Base accuracy confidence
            accuracy_confidence = model_profile.overall_accuracy

            # Adjust based on prediction type specific performance
            if prediction.prediction_type in model_profile.type_confidence:
                type_metrics = model_profile.type_confidence[prediction.prediction_type]
                accuracy_confidence = (
                    accuracy_confidence + type_metrics.accuracy_rate
                ) / 2

            # Recent performance adjustment
            if len(model_profile.recent_performance) > 5:
                recent_accuracy = mean(model_profile.recent_performance)
                trend_factor = min(
                    1.5, max(0.5, recent_accuracy / model_profile.overall_accuracy)
                )
                accuracy_confidence *= trend_factor

            return max(0.0, min(1.0, accuracy_confidence))

        except Exception as e:
            logger.warning("Failed to calculate accuracy confidence", error=str(e))
            return 0.5

    async def _calculate_timing_confidence(
        self, prediction: AIPrediction, market_context: Optional[Dict[str, Any]] = None
    ) -> float:
        """Calculate confidence based on timing factors"""
        try:
            timing_confidence = 0.7  # Base timing confidence

            # Adjust based on market hours
            if market_context:
                market_hours = market_context.get("market_hours", "unknown")
                if market_hours == "pre_market":
                    timing_confidence *= 0.8  # Less confident during pre-market
                elif market_hours == "after_hours":
                    timing_confidence *= 0.7  # Even less confident after hours
                elif market_hours == "market_open":
                    timing_confidence *= 1.1  # More confident during market hours

                # Volatility adjustment
                volatility = market_context.get("volatility", 0.5)
                if volatility > 0.8:
                    timing_confidence *= 0.9  # Less confident in high volatility
                elif volatility < 0.3:
                    timing_confidence *= 1.05  # More confident in low volatility

            # Expiry time adjustment
            if prediction.expiry_time:
                time_to_expiry = (
                    prediction.expiry_time - datetime.now(timezone.utc)
                ).total_seconds()
                if time_to_expiry < 300:  # Less than 5 minutes
                    timing_confidence *= 0.8
                elif time_to_expiry > 86400:  # More than 1 day
                    timing_confidence *= 0.9

            return max(0.0, min(1.0, timing_confidence))

        except Exception as e:
            logger.warning("Failed to calculate timing confidence", error=str(e))
            return 0.7

    async def _calculate_stability_confidence(self, prediction: AIPrediction) -> float:
        """Calculate confidence based on prediction stability"""
        try:
            # Base stability confidence
            stability_confidence = 0.8

            # Check for similar recent predictions
            similar_predictions = [
                p
                for p in list(self.prediction_history)[-50:]  # Last 50 predictions
                if p["model_id"] == prediction.model_id
                and p["prediction_type"] == prediction.prediction_type.value
            ]

            if len(similar_predictions) >= 3:
                # Calculate consistency of recent predictions
                recent_confidences = [
                    p["confidence_score"] for p in similar_predictions[-5:]
                ]
                if len(recent_confidences) > 1:
                    confidence_std = stdev(recent_confidences)
                    # Lower standard deviation means more stability
                    stability_factor = max(0.5, 1.0 - (confidence_std * 2))
                    stability_confidence *= stability_factor

            # Adjust based on input feature stability
            if hasattr(prediction, "input_features") and prediction.input_features:
                # Check for extreme values that might indicate instability
                numeric_features = {
                    k: v
                    for k, v in prediction.input_features.items()
                    if isinstance(v, (int, float))
                }

                if numeric_features:
                    feature_values = list(numeric_features.values())
                    if len(feature_values) > 1:
                        feature_std = stdev(feature_values)
                        feature_mean = mean(feature_values)
                        if feature_mean != 0:
                            cv = feature_std / abs(
                                feature_mean
                            )  # Coefficient of variation
                            if cv > 2.0:  # High variability
                                stability_confidence *= 0.9

            return max(0.0, min(1.0, stability_confidence))

        except Exception as e:
            logger.warning("Failed to calculate stability confidence", error=str(e))
            return 0.8

    async def _calculate_market_confidence(
        self, market_context: Optional[Dict[str, Any]] = None
    ) -> float:
        """Calculate confidence based on market conditions"""
        try:
            market_confidence = 0.6  # Base market confidence

            if not market_context:
                return market_confidence

            # Market trend confidence
            trend = market_context.get("trend", "neutral")
            if trend in ["strong_up", "strong_down"]:
                market_confidence *= 1.1  # More confident in strong trends
            elif trend == "neutral":
                market_confidence *= 0.9  # Less confident in neutral markets

            # Volume confidence
            volume_ratio = market_context.get("volume_ratio", 1.0)
            if volume_ratio > 1.5:
                market_confidence *= 1.05  # High volume increases confidence
            elif volume_ratio < 0.5:
                market_confidence *= 0.9  # Low volume decreases confidence

            # News sentiment confidence
            news_sentiment = market_context.get("news_sentiment", 0.0)
            sentiment_strength = abs(news_sentiment)
            if sentiment_strength > 0.7:
                market_confidence *= 1.1  # Strong sentiment increases confidence
            elif sentiment_strength < 0.2:
                market_confidence *= (
                    0.95  # Weak sentiment slightly decreases confidence
                )

            # Economic indicators
            economic_indicators = market_context.get("economic_indicators", {})
            if economic_indicators:
                indicator_count = len(economic_indicators)
                positive_indicators = sum(
                    1 for v in economic_indicators.values() if v > 0
                )
                indicator_ratio = (
                    positive_indicators / indicator_count
                    if indicator_count > 0
                    else 0.5
                )

                if indicator_ratio > 0.7:
                    market_confidence *= 1.05
                elif indicator_ratio < 0.3:
                    market_confidence *= 0.95

            return max(0.0, min(1.0, market_confidence))

        except Exception as e:
            logger.warning("Failed to calculate market confidence", error=str(e))
            return 0.6

    async def _calculate_adaptive_weights(
        self, prediction_type: PredictionType
    ) -> Dict[str, float]:
        """Calculate adaptive weights for confidence components"""
        try:
            # Default weights
            base_weights = {
                "base": 0.3,
                "accuracy": 0.25,
                "timing": 0.2,
                "stability": 0.15,
                "market": 0.1,
            }

            # Adjust weights based on prediction type
            if prediction_type in [
                PredictionType.PRICE_DIRECTION,
                PredictionType.PRICE_TARGET,
            ]:
                base_weights["accuracy"] += 0.1
                base_weights["market"] += 0.05
                base_weights["base"] -= 0.15

            elif prediction_type in [
                PredictionType.BUY_SIGNAL,
                PredictionType.SELL_SIGNAL,
            ]:
                base_weights["timing"] += 0.1
                base_weights["stability"] += 0.05
                base_weights["base"] -= 0.15

            elif prediction_type == PredictionType.VOLATILITY:
                base_weights["market"] += 0.15
                base_weights["stability"] += 0.1
                base_weights["base"] -= 0.25

            # Normalize weights to sum to 1.0
            total_weight = sum(base_weights.values())
            return {k: v / total_weight for k, v in base_weights.items()}

        except Exception as e:
            logger.warning("Failed to calculate adaptive weights", error=str(e))
            # Return default equal weights
            return {
                k: 0.2 for k in ["base", "accuracy", "timing", "stability", "market"]
            }

    async def _calculate_reliability_score(
        self, prediction: AIPrediction, confidence_components: Dict[str, float]
    ) -> float:
        """Calculate reliability score for the prediction"""
        try:
            # Base reliability from confidence consistency
            confidence_values = list(confidence_components.values())
            if len(confidence_values) <= 1:
                return 0.5

            confidence_std = stdev(confidence_values)
            confidence_mean = mean(confidence_values)

            # Lower standard deviation relative to mean indicates higher reliability
            cv = confidence_std / confidence_mean if confidence_mean > 0 else 1.0
            reliability_from_consistency = max(0.0, 1.0 - cv)

            # Adjust based on model history
            model_profile = self.model_profiles.get(prediction.model_id)
            if model_profile and model_profile.prediction_count > 10:
                historical_reliability = model_profile.overall_accuracy
                reliability_from_consistency = (
                    reliability_from_consistency + historical_reliability
                ) / 2

            # Adjust based on prediction confidence level
            if prediction.confidence_score > 0.8:
                reliability_from_consistency *= (
                    1.1  # High confidence predictions should be more reliable
                )
            elif prediction.confidence_score < 0.4:
                reliability_from_consistency *= (
                    0.9  # Low confidence predictions are less reliable
                )

            return max(0.0, min(1.0, reliability_from_consistency))

        except Exception as e:
            logger.warning("Failed to calculate reliability score", error=str(e))
            return 0.5

    async def _apply_confidence_calibration(
        self,
        metrics: ConfidenceMetrics,
        profile: ModelConfidenceProfile,
        prediction_type: PredictionType,
    ) -> ConfidenceMetrics:
        """Apply confidence calibration based on historical performance"""
        try:
            # Check if we have enough data for calibration
            if profile.prediction_count < self.min_samples_for_calibration:
                # Return metrics with minimal calibration for new models
                metrics.calibrated_confidence = (
                    metrics.raw_confidence * 0.9
                )  # Slight conservatism
                metrics.calibration_method = CalibrationMethod.HISTOGRAM_BINNING
                return metrics

            # Get calibration data for this model and prediction type
            calibration_key = f"{profile.model_id}_{prediction_type.value}"

            if calibration_key not in self.calibration_models:
                await self._build_calibration_model(profile, prediction_type)

            # Apply calibration
            calibrated_confidence = await self._apply_calibration_model(
                metrics.raw_confidence, calibration_key
            )

            # Calculate calibration error
            calibration_error = await self._calculate_calibration_error(
                profile, prediction_type
            )

            # Update metrics
            metrics.calibrated_confidence = calibrated_confidence
            metrics.calibration_error = calibration_error
            metrics.calibration_method = CalibrationMethod.ADAPTIVE_BINNING

            return metrics

        except Exception as e:
            logger.warning("Calibration failed, using raw confidence", error=str(e))
            metrics.calibrated_confidence = metrics.raw_confidence
            return metrics

    async def _build_calibration_model(
        self, profile: ModelConfidenceProfile, prediction_type: PredictionType
    ) -> None:
        """Build calibration model for a specific model and prediction type"""
        try:
            calibration_key = f"{profile.model_id}_{prediction_type.value}"

            # Gather historical data
            historical_data: List[Tuple[float, float]] = []
            for record in self.prediction_history:
                if (
                    record["model_id"] == profile.model_id
                    and record["prediction_type"] == prediction_type.value
                    and record["outcome_accuracy"] is not None
                ):
                    confidence = record["confidence_score"]
                    accuracy = record["outcome_accuracy"]
                    historical_data.append((confidence, accuracy))

            if len(historical_data) < self.min_samples_for_calibration:
                logger.warning(
                    "Insufficient data for calibration model",
                    calibration_key=calibration_key,
                    data_points=len(historical_data),
                )
                return

            # Sort by confidence
            historical_data.sort(key=lambda x: x[0])

            # Create calibration bins
            calibration_bins = await self._create_adaptive_bins(historical_data)

            # Store calibration model
            self.calibration_models[calibration_key] = {
                "method": CalibrationMethod.ADAPTIVE_BINNING,
                "bins": calibration_bins,
                "data_points": len(historical_data),
                "created_at": datetime.now(timezone.utc),
                "model_id": profile.model_id,
                "prediction_type": prediction_type.value,
            }

            logger.info(
                "Calibration model built",
                calibration_key=calibration_key,
                bins=len(calibration_bins),
                data_points=len(historical_data),
            )

        except Exception as e:
            raise CalibrationError(f"Failed to build calibration model: {str(e)}") from e

    async def _create_adaptive_bins(
        self, historical_data: List[Tuple[float, float]]
    ) -> List[Dict[str, float]]:
        """Create adaptive bins for calibration"""
        try:
            if len(historical_data) < 10:
                # Use simple binning for small datasets
                return await self._create_simple_bins(historical_data)

            # Adaptive binning based on data density
            confidences = [x[0] for x in historical_data]

            # Calculate optimal number of bins using Freedman-Diaconis rule
            q75, q25 = np.percentile(confidences, [75, 25])
            iqr = q75 - q25
            bin_width = 2 * iqr / (len(confidences) ** (1 / 3))
            num_bins = min(
                20, max(5, int((max(confidences) - min(confidences)) / bin_width))
            )

            bins: List[Dict[str, float]] = []
            bin_size = len(historical_data) // num_bins

            for i in range(num_bins):
                start_idx = i * bin_size
                end_idx = (
                    start_idx + bin_size if i < num_bins - 1 else len(historical_data)
                )

                bin_data = historical_data[start_idx:end_idx]
                if not bin_data:
                    continue

                bin_confidences = [x[0] for x in bin_data]
                bin_accuracies = [x[1] for x in bin_data]
                bins.append(
                    {
                        "confidence_min": min(bin_confidences),
                        "confidence_max": max(bin_confidences),
                        "confidence_mean": mean(bin_confidences)
                        if bin_confidences
                        else (min(bin_confidences) + max(bin_confidences)) / 2,
                        "accuracy_mean": mean(bin_accuracies),
                        "accuracy_std": (
                            stdev(bin_accuracies) if len(bin_accuracies) > 1 else 0.0
                        ),
                        "sample_count": len(bin_data),
                    }
                )

            return bins

        except Exception as e:
            logger.warning(
                "Failed to create adaptive bins, using simple binning", error=str(e)
            )
            return await self._create_simple_bins(historical_data)

    async def _create_simple_bins(
        self, historical_data: List[Tuple[float, float]]
    ) -> List[Dict[str, float]]:
        """Create simple equal-width bins for calibration"""
        try:
            bins: List[Dict[str, float]] = []
            bin_width = 1.0 / self.confidence_bins

            for i in range(self.confidence_bins):
                bin_min = i * bin_width
                bin_max = (i + 1) * bin_width

                # Find data points in this bin
                bin_data = [
                    (conf, acc)
                    for conf, acc in historical_data
                    if bin_min <= conf < bin_max
                    or (i == self.confidence_bins - 1 and conf <= bin_max)
                ]

                if bin_data:
                    bin_accuracies = [x[1] for x in bin_data]
                    bins.append(
                        {
                            "confidence_min": bin_min,
                            "confidence_max": bin_max,
                            "confidence_mean": mean(bin_accuracies)
                            if bin_accuracies
                            else (bin_min + bin_max) / 2,
                            "accuracy_mean": mean(bin_accuracies),
                            "accuracy_std": (
                                stdev(bin_accuracies)
                                if len(bin_accuracies) > 1
                                else 0.0
                            ),
                            "sample_count": len(bin_data),
                        }
                    )

            return bins

        except Exception as e:
            logger.error("Failed to create simple bins", error=str(e))
            return []

    async def _apply_calibration_model(
        self, raw_confidence: float, calibration_key: str
    ) -> float:
        """Apply calibration model to raw confidence"""
        try:
            if calibration_key not in self.calibration_models:
                return raw_confidence

            calibration_model = self.calibration_models[calibration_key]
            bins = calibration_model["bins"]

            if not bins:
                return raw_confidence

            # Find the appropriate bin
            target_bin: Optional[Dict[str, float]] = None
            for bin_data in bins:
                if (
                    bin_data["confidence_min"]
                    <= raw_confidence
                    <= bin_data["confidence_max"]
                ):
                    target_bin = bin_data
                    break

            if target_bin is None:
                # Use closest bin
                distances = [
                    abs(raw_confidence - bin_data["confidence_mean"])
                    for bin_data in bins
                ]
                closest_idx = distances.index(min(distances))
                target_bin = bins[closest_idx]

            # Interpolate within the bin if possible
            if target_bin is None:
                logger.warning(
                    "Could not find a suitable calibration bin.",
                    calibration_key=calibration_key,
                    raw_confidence=raw_confidence,
                )
                return raw_confidence

            calibrated_confidence = target_bin["accuracy_mean"]

            # Apply smoothing based on sample count
            if target_bin["sample_count"] < 10:
                # Blend with raw confidence for low sample counts
                smoothing_factor = target_bin["sample_count"] / 10.0
                calibrated_confidence = (
                    smoothing_factor * calibrated_confidence
                    + (1 - smoothing_factor) * raw_confidence
                )

            return max(0.0, min(1.0, calibrated_confidence))

        except Exception as e:
            logger.warning("Failed to apply calibration model", error=str(e))
            return raw_confidence

    async def _calculate_calibration_error(
        self, profile: ModelConfidenceProfile, prediction_type: PredictionType
    ) -> float:
        """Calculate calibration error (reliability - resolution)"""
        try:
            calibration_key = f"{profile.model_id}_{prediction_type.value}"

            if calibration_key not in self.calibration_models:
                return 0.0

            bins = self.calibration_models[calibration_key]["bins"]
            if not bins:
                return 0.0

            # Calculate Expected Calibration Error (ECE)
            ece = 0.0
            total_samples = sum(bin_data["sample_count"] for bin_data in bins)

            for bin_data in bins:
                if bin_data["sample_count"] > 0:
                    bin_weight = bin_data["sample_count"] / total_samples
                    confidence_accuracy_diff = abs(
                        bin_data["confidence_mean"] - bin_data["accuracy_mean"]
                    )
                    ece += bin_weight * confidence_accuracy_diff

            return ece

        except Exception as e:
            logger.warning("Failed to calculate calibration error", error=str(e))
            return 0.0

    async def _apply_dynamic_adjustments(
        self,
        metrics: ConfidenceMetrics,
        market_context: Optional[Dict[str, Any]],
        profile: ModelConfidenceProfile,
    ) -> ConfidenceMetrics:
        """Apply dynamic adjustments to calibrated confidence"""
        try:
            adjusted_confidence = metrics.calibrated_confidence
            adjustment_factors: Dict[str, float] = {}

            # Performance trend adjustment
            if len(profile.recent_performance) >= 5:
                recent_trend = profile.performance_trend
                if recent_trend > 0.1:  # Improving performance
                    trend_adjustment = min(0.1, recent_trend / 2)
                    adjusted_confidence += trend_adjustment
                    adjustment_factors["trend_boost"] = trend_adjustment
                elif recent_trend < -0.1:  # Declining performance
                    trend_adjustment = max(-0.15, recent_trend / 2)
                    adjusted_confidence += trend_adjustment
                    adjustment_factors["trend_penalty"] = trend_adjustment

            # Market volatility adjustment
            if market_context:
                volatility = market_context.get("volatility", 0.5)
                if volatility > 0.8:  # High volatility
                    volatility_adjustment = -0.05
                    adjusted_confidence += volatility_adjustment
                    adjustment_factors["high_volatility_penalty"] = (
                        volatility_adjustment
                    )
                elif volatility < 0.2:  # Low volatility
                    volatility_adjustment = 0.03
                    adjusted_confidence += volatility_adjustment
                    adjustment_factors["low_volatility_boost"] = volatility_adjustment

            # Model confidence threshold adjustment
            if adjusted_confidence < profile.confidence_threshold:
                threshold_adjustment = -0.05
                adjusted_confidence += threshold_adjustment
                adjustment_factors["below_threshold_penalty"] = threshold_adjustment

            # Ensure confidence remains in valid range
            adjusted_confidence = max(0.0, min(1.0, adjusted_confidence))

            # Record adjustment
            if adjustment_factors:
                adjustment = ConfidenceAdjustment(
                    original_confidence=metrics.calibrated_confidence,
                    adjusted_confidence=adjusted_confidence,
                    adjustment_reason="Dynamic market and performance adjustments",
                    adjustment_factors=adjustment_factors,
                    market_conditions=market_context or {},
                    timestamp=datetime.now(timezone.utc),
                )
                self.confidence_adjustments.append(adjustment)

            # Update metrics
            metrics.calibrated_confidence = adjusted_confidence

            return metrics

        except Exception as e:
            logger.warning("Failed to apply dynamic adjustments", error=str(e))
            return metrics

    async def _get_or_create_model_profile(
        self, model_id: str
    ) -> ModelConfidenceProfile:
        """Get existing model profile or create a new one"""
        try:
            if model_id not in self.model_profiles:
                # Create new profile
                profile = ModelConfidenceProfile(
                    model_id=model_id,
                    model_type=ModelType.TRANSFORMER,  # Default, should be updated
                )
                self.model_profiles[model_id] = profile

                logger.info("Created new model profile", model_id=model_id)

            return self.model_profiles[model_id]

        except Exception as e:
            raise ConfidenceTrackingError(
                f"Failed to get/create model profile: {str(e)}"
            ) from e

    async def _record_prediction_for_learning(
        self, prediction: AIPrediction, metrics: ConfidenceMetrics
    ) -> None:
        """Record prediction data for future learning"""
        try:
            prediction_record: PredictionRecord = {
                "prediction_id": prediction.prediction_id,
                "model_id": prediction.model_id,
                "prediction_type": prediction.prediction_type.value,
                "confidence_score": prediction.confidence_score,
                "calibrated_confidence": metrics.calibrated_confidence,
                "reliability_score": metrics.reliability_score,
                "timestamp": datetime.now(timezone.utc),
                "expiry_time": prediction.expiry_time,
                "prediction_value": prediction.prediction_value,
                "input_features": prediction.input_features or {},
                "market_context": prediction.market_context or {},
                "outcome_accuracy": None,  # Will be updated when outcome is known
                "outcome_determined": False,
                "actual_outcome": None,
                "outcome_timestamp": None,
            }

            self.prediction_history.append(prediction_record)

            # Update global metrics
            self.global_metrics["total_predictions"] += 1

        except Exception as e:
            logger.error("Failed to record prediction for learning", error=str(e))

    async def _update_model_profile(
        self,
        profile: ModelConfidenceProfile,
        metrics: ConfidenceMetrics,
        prediction_type: PredictionType,
    ) -> None:
        """Update model profile with new prediction metrics"""
        try:
            # Update prediction count
            profile.prediction_count += 1

            # Update overall confidence (running average)
            if profile.prediction_count == 1:
                profile.overall_confidence = metrics.calibrated_confidence
            else:
                alpha = profile.learning_rate
                profile.overall_confidence = (
                    (1 - alpha) * profile.overall_confidence
                    + alpha * metrics.calibrated_confidence
                )

            # Update type-specific confidence keyed by PredictionType
            if prediction_type not in profile.type_confidence:
                profile.type_confidence[prediction_type] = ConfidenceMetrics(
                    metric_type=metrics.metric_type,
                    raw_confidence=metrics.raw_confidence,
                    calibrated_confidence=metrics.calibrated_confidence,
                    reliability_score=metrics.reliability_score,
                    prediction_count=1,
                    accuracy_rate=0.0,
                )
            else:
                type_metrics = profile.type_confidence[prediction_type]
                type_metrics.prediction_count += 1

                # Update running averages
                alpha = profile.learning_rate
                type_metrics.calibrated_confidence = (
                    (1 - alpha) * type_metrics.calibrated_confidence
                    + alpha * metrics.calibrated_confidence
                )
                type_metrics.reliability_score = (
                    (1 - alpha) * type_metrics.reliability_score
                    + alpha * metrics.reliability_score
                )

        except Exception as e:
            logger.error("Failed to update model profile", error=str(e))

    async def update_prediction_outcome(
        self,
        prediction_id: str,
        actual_outcome: Dict[str, Any],
        outcome_accuracy: float,
    ) -> None:
        """
        Update prediction outcome for learning and calibration

        Args:
            prediction_id: ID of the prediction
            actual_outcome: The actual outcome that occurred
            outcome_accuracy: Accuracy score (0.0 to 1.0)

        Raises:
            ConfidenceTrackingError: If update fails
        """
        try:
            # Validate input
            if not (0.0 <= outcome_accuracy <= 1.0):
                raise ConfidenceTrackingError(
                    "Outcome accuracy must be between 0.0 and 1.0"
                )

            # Find prediction record
            prediction_record = None
            for record in self.prediction_history:
                if record.get("prediction_id") == prediction_id:
                    prediction_record = record
                    break

            if not prediction_record:
                logger.warning(
                    "Prediction record not found for outcome update",
                    prediction_id=prediction_id,
                )
                return

            # Update outcome data
            prediction_record["actual_outcome"] = actual_outcome
            prediction_record["outcome_accuracy"] = outcome_accuracy
            prediction_record["outcome_determined"] = True
            prediction_record["outcome_timestamp"] = datetime.now(timezone.utc)

            # Update model profile
            model_id = prediction_record["model_id"]
            if model_id in self.model_profiles:
                profile = self.model_profiles[model_id]

                # Update overall accuracy (running average)
                if profile.prediction_count == 1:
                    profile.overall_accuracy = outcome_accuracy
                else:
                    alpha = profile.learning_rate
                    profile.overall_accuracy = (
                        1 - alpha
                    ) * profile.overall_accuracy + alpha * outcome_accuracy

                # Add to recent performance tracking
                profile.recent_performance.append(outcome_accuracy)

                # Update performance trend
                if len(profile.recent_performance) >= 10:
                    recent_performance = list(profile.recent_performance)
                    half = len(recent_performance) // 2
                    first_half_avg = mean(recent_performance[:half])
                    second_half_avg = mean(recent_performance[half:])
                    profile.performance_trend = second_half_avg - first_half_avg

                # Update type-specific accuracy
                pred_type_str = prediction_record["prediction_type"]
                for pred_type, type_metrics in profile.type_confidence.items():
                    if pred_type.value == pred_type_str:
                        if type_metrics.prediction_count == 1:
                            type_metrics.accuracy_rate = outcome_accuracy
                        else:
                            alpha = profile.learning_rate
                            type_metrics.accuracy_rate = (
                                (1 - alpha) * type_metrics.accuracy_rate
                                + alpha * outcome_accuracy
                            )
                        break

            # Update global metrics
            self.global_metrics["total_correct"] += 1 if outcome_accuracy > 0.5 else 0

            # Trigger calibration update if needed
            await self._check_calibration_update_needed(model_id)

            logger.info(
                "Prediction outcome updated",
                prediction_id=prediction_id,
                outcome_accuracy=outcome_accuracy,
                model_id=model_id,
            )

        except Exception as e:
            await self._handle_tracking_error(e, prediction_id)
            raise ConfidenceTrackingError(
                f"Failed to update prediction outcome: {str(e)}"
            ) from e

    async def _check_calibration_update_needed(self, model_id: str) -> None:
        """Check if calibration model needs updating"""
        try:
            if model_id not in self.model_profiles:
                return

            profile = self.model_profiles[model_id]

            # Check if enough new data since last calibration
            predictions_since_calibration = 0
            for record in reversed(list(self.prediction_history)):
                if record["model_id"] == model_id:
                    predictions_since_calibration += 1
                    if predictions_since_calibration >= self.calibration_window // 4:
                        break

            if predictions_since_calibration >= self.calibration_window // 4:
                # Update calibration models
                for pred_type in profile.type_confidence.keys():
                    try:
                        await self._build_calibration_model(profile, pred_type)
                    except Exception as e:
                        logger.warning(
                            "Failed to update calibration model",
                            model_id=model_id,
                            prediction_type=pred_type.value,
                            error=str(e),
                        )

                self.global_metrics["last_calibration"] = datetime.now(timezone.utc)
                self.global_metrics["learning_iterations"] += 1

                logger.info(
                    "Calibration models updated",
                    model_id=model_id,
                    new_predictions=predictions_since_calibration,
                )

        except Exception as e:
            logger.error("Failed to check calibration update", error=str(e))

    async def get_model_confidence_summary(self, model_id: str) -> Dict[str, Any]:
        """
        Get comprehensive confidence summary for a model

        Args:
            model_id: ID of the model

        Returns:
            Dictionary containing confidence summary

        Raises:
            ConfidenceTrackingError: If summary generation fails
        """
        try:
            if model_id not in self.model_profiles:
                raise ConfidenceTrackingError(f"Model profile not found: {model_id}")

            profile = self.model_profiles[model_id]

            # Basic profile information
            summary: Dict[str, Any] = {
                "model_id": model_id,
                "model_type": profile.model_type.value,
                "prediction_count": profile.prediction_count,
                "overall_accuracy": profile.overall_accuracy,
                "overall_confidence": profile.overall_confidence,
                "performance_trend": profile.performance_trend,
            }

            # Type-specific confidence
            type_confidence_summary = {}
            for pred_type, metrics in profile.type_confidence.items():
                type_confidence_summary[pred_type.value] = {
                    "prediction_count": metrics.prediction_count,
                    "accuracy_rate": metrics.accuracy_rate,
                    "calibrated_confidence": metrics.calibrated_confidence,
                    "reliability_score": metrics.reliability_score,
                    "calibration_error": metrics.calibration_error,
                }

            summary["type_confidence"] = type_confidence_summary

            # Recent performance
            if profile.recent_performance:
                recent_perf = list(profile.recent_performance)
                summary["recent_performance"] = {
                    "count": len(recent_perf),
                    "average": mean(recent_perf),
                    "median": median(recent_perf),
                    "std_dev": stdev(recent_perf) if len(recent_perf) > 1 else 0.0,
                    "trend": profile.performance_trend,
                }

            # Calibration information
            calibration_info = {}
            for pred_type in profile.type_confidence.keys():
                calibration_key = f"{model_id}_{pred_type.value}"
                if calibration_key in self.calibration_models:
                    cal_model = self.calibration_models[calibration_key]
                    calibration_info[pred_type.value] = {
                        "method": cal_model["method"].value,
                        "bins": len(cal_model["bins"]),
                        "data_points": cal_model["data_points"],
                        "created_at": cal_model["created_at"].isoformat(),
                    }

            summary["calibration_models"] = calibration_info

            # Error tracking
            summary["error_tracking"] = {
                "error_count": profile.error_count,
                "last_error": profile.last_error,
                "recovery_attempts": profile.recovery_attempts,
            }

            return summary

        except Exception as e:
            raise ConfidenceTrackingError(
                f"Failed to generate model confidence summary: {str(e)}"
            )

    async def get_global_confidence_metrics(self) -> Dict[str, Any]:
        """
        Get global confidence tracking metrics

        Returns:
            Dictionary containing global metrics
        """
        try:
            # Calculate current global accuracy
            recent_predictions = [
                record
                for record in list(self.prediction_history)[-1000:]
                if record["outcome_determined"]
            ]

            global_accuracy = 0.0
            if recent_predictions:
                total_accuracy = sum(
                    record["outcome_accuracy"] or 0.0 for record in recent_predictions
                )
                global_accuracy = total_accuracy / len(recent_predictions)

            # Calculate calibration quality
            calibration_quality = await self._calculate_global_calibration_quality()

            # Model performance distribution
            model_performance = {}
            for model_id, profile in self.model_profiles.items():
                model_performance[model_id] = {
                    "accuracy": profile.overall_accuracy,
                    "confidence": profile.overall_confidence,
                    "prediction_count": profile.prediction_count,
                    "trend": profile.performance_trend,
                }

            return {
                "global_metrics": self.global_metrics,
                "current_global_accuracy": global_accuracy,
                "calibration_quality": calibration_quality,
                "active_models": len(self.model_profiles),
                "total_predictions_tracked": len(self.prediction_history),
                "calibration_models_count": len(self.calibration_models),
                "model_performance": model_performance,
                "health_status": self.health_status,
                "error_counts": dict(self.error_counts),
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error("Failed to get global confidence metrics", error=str(e))
            return {"error": str(e), "timestamp": datetime.now(timezone.utc).isoformat()}

    async def _calculate_global_calibration_quality(self) -> float:
        """Calculate overall calibration quality across all models"""
        try:
            if not self.calibration_models:
                return 0.0

            total_quality = 0.0
            model_count = 0

            for _, cal_model in self.calibration_models.items():
                bins = cal_model.get("bins", [])
                if not bins:
                    continue

                # Calculate Expected Calibration Error for this model
                ece = 0.0
                total_samples = sum(
                    bin_data.get("sample_count", 0) for bin_data in bins
                )

                if total_samples > 0:
                    for bin_data in bins:
                        sample_count = bin_data.get("sample_count", 0)
                        if sample_count > 0:
                            bin_weight = sample_count / total_samples
                            confidence_accuracy_diff = abs(
                                bin_data.get("confidence_mean", 0.5)
                                - bin_data.get("accuracy_mean", 0.5)
                            )
                            ece += bin_weight * confidence_accuracy_diff

                    # Convert ECE to quality score (lower ECE = higher quality)
                    quality = max(0.0, 1.0 - ece)
                    total_quality += quality
                    model_count += 1

            return total_quality / model_count if model_count > 0 else 0.0

        except Exception as e:
            logger.warning(
                "Failed to calculate global calibration quality", error=str(e)
            )
            return 0.0

    async def _handle_tracking_error(
        self, error: Exception, context: str = ""
    ) -> None:
        """Handle tracking errors with recovery strategies"""
        try:
            error_type = type(error).__name__
            self.error_counts[error_type] += 1

            logger.error(
                "Confidence tracking error",
                error_type=error_type,
                error_message=str(error),
                context=context,
                error_count=self.error_counts[error_type],
            )

            # Update health status based on error frequency
            total_errors = sum(self.error_counts.values())
            if total_errors > 100:
                self.health_status = "degraded"
            elif total_errors > 500:
                self.health_status = "unhealthy"

            # Apply recovery strategies
            if isinstance(error, CalibrationError):
                await self._recover_from_calibration_error(context)
            elif isinstance(error, MetricsCalculationError):
                await self._recover_from_metrics_error(context)

        except Exception as recovery_error:
            logger.error(
                "Failed to handle tracking error", recovery_error=str(recovery_error)
            )

    async def _recover_from_calibration_error(self, context: str) -> None:
        """Recover from calibration errors"""
        try:
            # Clear problematic calibration models
            problematic_keys = [
                key for key in self.calibration_models.keys() if context in key
            ]

            for key in problematic_keys:
                del self.calibration_models[key]
                logger.info(
                    "Cleared problematic calibration model", calibration_key=key
                )

        except Exception as e:
            logger.error("Failed to recover from calibration error", error=str(e))

    async def _recover_from_metrics_error(self, context: str) -> None:
        """Recover from metrics calculation errors"""
        try:
            # Reset metrics for problematic model
            if context in self.model_profiles:
                profile = self.model_profiles[context]
                profile.error_count += 1
                profile.recovery_attempts += 1

                if profile.recovery_attempts > 5:
                    # Reset profile if too many recovery attempts
                    self.model_profiles[context] = ModelConfidenceProfile(
                        model_id=context, model_type=profile.model_type
                    )
                    logger.info(
                        "Reset model profile after multiple recovery attempts",
                        model_id=context,
                    )

        except Exception as e:
            logger.error("Failed to recover from metrics error", error=str(e))

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the confidence tracking system

        Returns:
            Dictionary containing health status and metrics
        """
        try:
            # Check system components
            health_status = "healthy"
            issues: List[str] = []

            # Check prediction history size
            if len(self.prediction_history) == 0:
                issues.append("No prediction history available")
                health_status = "degraded"

            # Check model profiles
            if len(self.model_profiles) == 0:
                issues.append("No model profiles created")
                health_status = "degraded"

            # Check calibration models
            if len(self.calibration_models) == 0 and len(self.model_profiles) > 0:
                issues.append(
                    "No calibration models built despite having model profiles"
                )
                health_status = "degraded"

            # Check error rates
            total_errors = sum(self.error_counts.values())
            if total_errors > 100:
                issues.append(f"High error count: {total_errors}")
                health_status = "degraded"

            if total_errors > 500:
                health_status = "unhealthy"

            # Performance metrics
            performance_metrics: Dict[str, Any] = {
                "prediction_history_size": len(self.prediction_history),
                "active_model_profiles": len(self.model_profiles),
                "calibration_models": len(self.calibration_models),
                "total_errors": total_errors,
                "error_breakdown": dict(self.error_counts),
                "global_metrics": self.global_metrics,
            }

            return {
                "status": health_status,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "issues": issues,
                "performance_metrics": performance_metrics,
                "system_health": self.health_status,
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
            }


# Global instance
confidence_tracker = AdvancedConfidenceTracker()


# Convenience functions for easy integration
async def track_prediction_confidence(
    prediction: AIPrediction,
    market_context: Optional[Dict[str, Any]] = None,
    additional_features: Optional[Dict[str, Any]] = None,
) -> ConfidenceMetrics:
    """Track confidence for a prediction"""
    return await confidence_tracker.track_prediction_confidence(
        prediction, market_context, additional_features
    )


async def update_prediction_outcome(
    prediction_id: str, actual_outcome: Dict[str, Any], outcome_accuracy: float
) -> None:
    """Update prediction outcome for learning"""
    await confidence_tracker.update_prediction_outcome(
        prediction_id, actual_outcome, outcome_accuracy
    )


async def get_model_confidence_summary(model_id: str) -> Dict[str, Any]:
    """Get confidence summary for a model"""
    return await confidence_tracker.get_model_confidence_summary(model_id)


async def get_global_confidence_metrics() -> Dict[str, Any]:
    """Get global confidence metrics"""
    return await confidence_tracker.get_global_confidence_metrics()


async def check_confidence_tracker_health() -> Dict[str, Any]:
    """Check confidence tracker health"""
    return await confidence_tracker.health_check()


# Example usage and testing functions
async def example_usage():
    """Example usage of the confidence tracker"""

    # Example prediction (this would come from actual AI model)
    from ..models.ai_prediction import AIPrediction, PredictionType

    example_prediction = AIPrediction(
        model_id="test-model-123",
        prediction_type=PredictionType.PRICE_DIRECTION,
        prediction_value={"direction": "up", "confidence": 0.75},
        confidence_score=0.75,
        input_features={"rsi": 65, "macd": 0.1, "volume_ratio": 1.2},
        market_context={"trend": "bullish", "volatility": 0.4},
        expiry_time=datetime.now(timezone.utc),
    )

    # Track confidence
    try:
        confidence_metrics = await track_prediction_confidence(
            example_prediction,
            market_context={
                "trend": "bullish",
                "volatility": 0.4,
                "market_hours": "market_open",
                "volume_ratio": 1.2,
            },
        )

        print("Confidence Metrics:")
        print(f"  Raw Confidence: {confidence_metrics.raw_confidence:.3f}")
        print(
            f"  Calibrated Confidence: {confidence_metrics.calibrated_confidence:.3f}"
        )
        print(f"  Reliability Score: {confidence_metrics.reliability_score:.3f}")

        # Simulate outcome update later
        await asyncio.sleep(0.1)
        await update_prediction_outcome(
            example_prediction.prediction_id,
            {"direction": "up", "actual_price_change": 0.05},
            outcome_accuracy=0.9,  # High accuracy
        )

        print("Outcome updated successfully")

        # Get model summary
        summary = await get_model_confidence_summary(example_prediction.model_id)
        print(f"Model Summary: {json.dumps(summary, indent=2, default=str)}")

        # Health check
        health = await check_confidence_tracker_health()
        print(f"Health Status: {health['status']}")

    except Exception as e:
        print(f"Error in example usage: {str(e)}")
        logger.exception("Error during example usage")


if __name__ == "__main__":
    # Run example usage
    asyncio.run(example_usage())
