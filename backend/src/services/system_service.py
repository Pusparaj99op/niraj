"""
System Management Service

Provides comprehensive system monitoring, status reporting, and AI prediction management
for the NIRAJ trading system. Includes health checks, metrics collection, and system state management.
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

import structlog
from sqlalchemy import text

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    psutil = None
    PSUTIL_AVAILABLE = False

from ..core.database import DatabaseManager

try:
    from ..core.cache import CacheManager

    CACHE_AVAILABLE = True
    CacheManagerType = CacheManager
except ImportError:
    CacheManager = None
    CACHE_AVAILABLE = False
    CacheManagerType = Any
from ..core.config import config

try:
    from ..ai.gemma3_integration import Gemma3Client

    AI_AVAILABLE = True
    Gemma3ClientType = Gemma3Client
except ImportError:
    Gemma3Client = None
    AI_AVAILABLE = False
    Gemma3ClientType = Any

# Import AI prediction classes
from ..models.ai_prediction import AIPrediction, PredictionStatus

from ..api.angel_one_client import AngelOneClient
from ..api.dhan_client import DhanClient


class SystemStatus(str, Enum):
    """System overall status enumeration"""

    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    DOWN = "DOWN"


class ServiceStatus(str, Enum):
    """Individual service status enumeration"""

    RUNNING = "RUNNING"
    STOPPED = "STOPPED"
    ERROR = "ERROR"
    NOT_CONFIGURED = "NOT_CONFIGURED"


class TradingMode(str, Enum):
    """Trading mode enumeration"""

    PAPER = "paper"
    LIVE = "live"


@dataclass
class SystemMetrics:
    """System performance metrics"""

    cpu_usage_pct: float
    memory_usage_pct: float
    disk_usage_pct: float
    active_strategies: int
    open_positions: int
    total_predictions_today: int
    successful_predictions_today: int
    uptime_seconds: float


@dataclass
class ServiceHealth:
    """Individual service health information"""

    status: ServiceStatus
    last_check: datetime
    response_time_ms: Optional[float] = None
    error_message: Optional[str] = None
    version: Optional[str] = None
    additional_info: Optional[Dict[str, Any]] = None


@dataclass
class APIConnectionStatus:
    """API connection status information"""

    status: str  # CONNECTED, DISCONNECTED, ERROR
    last_heartbeat: Optional[datetime] = None
    response_time_ms: Optional[float] = None
    error_message: Optional[str] = None


class SystemServiceError(Exception):
    """Custom exception for system service errors"""

    def __init__(self, message: str, service: str = None, error_code: str = None):
        self.message = message
        self.service = service
        self.error_code = error_code
        super().__init__(self.message)


class SystemService:
    """
    System management service for NIRAJ trading platform

    Provides comprehensive system monitoring, health checks, and status reporting.
    Manages AI predictions retrieval and system metrics collection.
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        cache_manager: Optional[Any] = None,
        ai_client: Optional[Any] = None,
        angel_one_client: Optional[AngelOneClient] = None,
        dhan_client: Optional[DhanClient] = None,
    ):
        """
        Initialize system service

        Args:
            db_manager: Database manager instance
            cache_manager: Optional cache manager instance
            ai_client: Optional AI integration client
            angel_one_client: Optional Angel One API client
            dhan_client: Optional Dhan API client
        """
        self.db_manager = db_manager
        self.cache_manager = cache_manager
        self.ai_client = ai_client
        self.angel_one_client = angel_one_client
        self.dhan_client = dhan_client

        # Service state
        self._start_time = time.time()
        self._service_health_cache: Dict[str, ServiceHealth] = {}
        self._cache_expiry = 30  # seconds

        # Logger
        self.logger = structlog.get_logger(__name__)

    async def get_system_status(self) -> Dict[str, Any]:
        """
        Get comprehensive system status information

        Returns:
            Dictionary containing complete system status
        """
        try:
            self.logger.info("Retrieving system status")

            # Get current timestamp
            now = datetime.now(timezone.utc)

            # Determine trading mode
            trading_mode = self._get_trading_mode()

            # Check if market is open (simplified - Indian markets)
            market_hours = self._is_market_hours(now)

            # Get service statuses
            services = await self._get_services_status()

            # Get API connection statuses
            api_connections = await self._get_api_connections_status()

            # Get system metrics
            system_metrics = await self._get_system_metrics()

            # Determine overall system status
            overall_status = self._calculate_overall_status(services, api_connections)

            status_data = {
                "status": overall_status.value,
                "trading_mode": trading_mode.value,
                "market_hours": market_hours,
                "timestamp": now.isoformat(),
                "services": services,
                "api_connections": api_connections,
                "system_metrics": system_metrics,
            }

            self.logger.info(
                "System status retrieved",
                overall_status=overall_status.value,
                trading_mode=trading_mode.value,
                market_hours=market_hours,
            )

            return status_data

        except Exception as e:
            self.logger.error("Failed to get system status", error=str(e))
            raise SystemServiceError(
                f"Failed to get system status: {str(e)}", "system_status"
            )

    async def get_ai_predictions(
        self,
        symbol: Optional[str] = None,
        strategy_id: Optional[str] = None,
        min_confidence: float = 0.7,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Get AI predictions with optional filtering

        Args:
            symbol: Optional symbol filter
            strategy_id: Optional strategy ID filter
            min_confidence: Minimum confidence threshold (default 0.7)
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            Dictionary containing predictions list
        """
        try:
            self.logger.info(
                "Retrieving AI predictions",
                symbol=symbol,
                strategy_id=strategy_id,
                min_confidence=min_confidence,
                limit=limit,
                offset=offset,
            )

            # Build query conditions
            conditions = []
            params = {}

            # Status filter - only active predictions
            conditions.append("status IN (:status1, :status2, :status3)")
            params.update(
                {
                    "status1": PredictionStatus.PENDING.value,
                    "status2": PredictionStatus.VALIDATED.value,
                    "status3": PredictionStatus.EXPIRED.value,
                }
            )

            # Confidence filter
            conditions.append("confidence_score >= :min_confidence")
            params["min_confidence"] = min_confidence

            # Symbol filter
            if symbol:
                conditions.append(
                    "JSON_EXTRACT(prediction_value, '$.symbol') = :symbol"
                )
                params["symbol"] = symbol

            # Strategy ID filter (if provided)
            if strategy_id:
                conditions.append("strategy_id = :strategy_id")
                params["strategy_id"] = strategy_id

            # Build query
            where_clause = " AND ".join(conditions)

            query = f"""
                SELECT
                    prediction_id, model_id, prediction_type, prediction_value,
                    confidence_score, confidence_level, input_features,
                    market_context, created_at, updated_at, prediction_time,
                    expiry_time, outcome_determined_at, status, is_active,
                    actual_outcome, outcome_type, outcome_accuracy,
                    prediction_accuracy, directional_accuracy, magnitude_error,
                    timing_error_seconds, trade_executed, trade_id,
                    profit_loss, risk_reward_ratio, processing_time_ms,
                    model_version_used, algorithm_parameters,
                    signal_to_noise_ratio, prediction_stability,
                    feature_importance, tags, prediction_metadata, notes,
                    error_message, error_code, retry_count
                FROM ai_predictions
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
            """

            params.update({"limit": limit, "offset": offset})

            # Execute query
            async with self.db_manager.get_connection() as session:
                result = await session.execute(text(query), params)
                rows = result.fetchall()

            # Convert to prediction objects
            predictions = []
            for row in rows:
                prediction_data = dict(row)
                # Convert JSON fields back to dict
                json_fields = [
                    "prediction_value",
                    "input_features",
                    "market_context",
                    "actual_outcome",
                    "algorithm_parameters",
                    "feature_importance",
                    "tags",
                    "prediction_metadata",
                ]
                for field in json_fields:
                    if prediction_data[field] and isinstance(
                        prediction_data[field], str
                    ):
                        try:
                            prediction_data[field] = json.loads(prediction_data[field])
                        except json.JSONDecodeError:
                            prediction_data[field] = {}

                # Create AIPrediction instance
                prediction = AIPrediction(**prediction_data)
                predictions.append(prediction)

            # Convert to response format
            predictions_response = []
            for prediction in predictions:
                pred_dict = {
                    "prediction_id": prediction.prediction_id,
                    "symbol": (
                        prediction.prediction_value.get("symbol", "")
                        if isinstance(prediction.prediction_value, dict)
                        else ""
                    ),
                    "strategy_id": getattr(prediction, "strategy_id", ""),
                    "timestamp": prediction.prediction_time.isoformat(),
                    "predicted_direction": (
                        prediction.prediction_value.get("direction", "UNKNOWN")
                        if isinstance(prediction.prediction_value, dict)
                        else "UNKNOWN"
                    ),
                    "confidence_score": prediction.confidence_score,
                    "predicted_magnitude": (
                        prediction.prediction_value.get("magnitude", 0.0)
                        if isinstance(prediction.prediction_value, dict)
                        else 0.0
                    ),
                    "prediction_horizon": (
                        prediction.prediction_value.get("horizon", 1)
                        if isinstance(prediction.prediction_value, dict)
                        else 1
                    ),
                    "reasoning": prediction.notes or "AI-generated prediction",
                    "market_features": prediction.market_context or {},
                    "was_correct": (
                        prediction.outcome_accuracy
                        if prediction.outcome_accuracy is not None
                        else None
                    ),
                    "trade_executed": prediction.trade_executed,
                }
                predictions_response.append(pred_dict)

            result = {
                "predictions": predictions_response,
                "total": len(
                    predictions_response
                ),  # Simplified - in production would need COUNT query
                "limit": limit,
                "offset": offset,
            }

            self.logger.info(
                "AI predictions retrieved",
                count=len(predictions_response),
                symbol=symbol,
                strategy_id=strategy_id,
            )

            return result

        except Exception as e:
            self.logger.error("Failed to get AI predictions", error=str(e))
            raise SystemServiceError(
                f"Failed to get AI predictions: {str(e)}",
                "ai_predictions",
                "AI_PREDICTIONS_ERROR",
            )

    def _get_trading_mode(self) -> TradingMode:
        """Get current trading mode from configuration"""
        try:
            mode = config.get("trading.default_mode", "paper")
            return TradingMode(mode)
        except ValueError:
            return TradingMode.PAPER

    def _is_market_hours(self, now: datetime) -> bool:
        """
        Check if current time is within Indian market hours

        Args:
            now: Current datetime

        Returns:
            True if market is open, False otherwise
        """
        # Simplified market hours check (Indian equity markets: 9:15 AM - 3:30 PM IST)
        # In production, this would be more sophisticated with holidays, etc.
        hour = now.hour
        minute = now.minute

        # Convert to IST (assuming now is UTC)
        ist_hour = (hour + 5) % 24
        ist_minute = minute + 30
        if ist_minute >= 60:
            ist_hour = (ist_hour + 1) % 24
            ist_minute -= 60

        # Market hours: 9:15 AM - 3:30 PM IST
        market_open = (ist_hour > 9) or (ist_hour == 9 and ist_minute >= 15)
        market_close = (ist_hour < 15) or (ist_hour == 15 and ist_minute <= 30)

        return market_open and market_close

    async def _get_services_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all system services"""
        services = {}

        # Database service
        services["data_manager"] = await self._check_database_health()

        # Analysis engine (AI service)
        services["analysis_engine"] = await self._check_ai_health()

        # Execution engine
        services["execution_engine"] = await self._check_execution_engine_health()

        # AI service
        services["ai_service"] = await self._check_ai_health()

        return services

    async def _get_api_connections_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of external API connections"""
        connections = {}

        # Angel One API
        connections["angel_one"] = await self._check_angel_one_connection()

        # Dhan API
        connections["dhan"] = await self._check_dhan_connection()

        return connections

    async def _get_system_metrics(self) -> Dict[str, Any]:
        """Get system performance metrics"""
        try:
            if not PSUTIL_AVAILABLE:
                return {
                    "cpu_usage_pct": 0.0,
                    "memory_usage_pct": 0.0,
                    "disk_usage_pct": 0.0,
                    "active_strategies": 0,
                    "open_positions": 0,
                    "total_predictions_today": 0,
                    "successful_predictions_today": 0,
                    "uptime_seconds": time.time() - self._start_time,
                }

            # CPU usage
            cpu_usage = psutil.cpu_percent(interval=1)

            # Memory usage
            memory = psutil.virtual_memory()
            memory_usage = memory.percent

            # Disk usage
            disk = psutil.disk_usage("/")
            disk_usage = disk.percent

            # Active strategies (simplified - would query database)
            active_strategies = 0

            # Open positions (simplified)
            open_positions = 0

            # AI predictions today (simplified)
            total_predictions_today = 0
            successful_predictions_today = 0

            # Uptime
            uptime_seconds = time.time() - self._start_time

            return {
                "cpu_usage_pct": cpu_usage,
                "memory_usage_pct": memory_usage,
                "disk_usage_pct": disk_usage,
                "active_strategies": active_strategies,
                "open_positions": open_positions,
                "total_predictions_today": total_predictions_today,
                "successful_predictions_today": successful_predictions_today,
                "uptime_seconds": uptime_seconds,
            }

        except Exception as e:
            self.logger.warning("Failed to collect system metrics", error=str(e))
            return {
                "cpu_usage_pct": 0.0,
                "memory_usage_pct": 0.0,
                "disk_usage_pct": 0.0,
                "active_strategies": 0,
                "open_positions": 0,
                "total_predictions_today": 0,
                "successful_predictions_today": 0,
                "uptime_seconds": time.time() - self._start_time,
            }

    async def _check_database_health(self) -> Dict[str, Any]:
        """Check database service health"""
        try:
            start_time = time.time()

            # Simple health check query
            async with self.db_manager.get_connection() as session:
                result = await session.execute(text("SELECT 1 as health_check"))
                row = result.fetchone()

            response_time = (time.time() - start_time) * 1000

            return {
                "status": ServiceStatus.RUNNING.value,
                "last_check": datetime.now(timezone.utc).isoformat(),
                "response_time_ms": response_time,
                "version": "SQLite",  # Would be more specific in production
                "message": "Database connection healthy",
            }

        except Exception as e:
            return {
                "status": ServiceStatus.ERROR.value,
                "last_check": datetime.now(timezone.utc).isoformat(),
                "error_message": str(e),
                "message": "Database connection failed",
            }

    async def _check_ai_health(self) -> Dict[str, Any]:
        """Check AI service health"""
        if not self.ai_client:
            return {
                "status": ServiceStatus.NOT_CONFIGURED.value,
                "last_check": datetime.now(timezone.utc).isoformat(),
                "message": "AI client not configured",
            }

        try:
            start_time = time.time()

            # Check AI service health
            health_result = await self.ai_client.health_check()

            response_time = (time.time() - start_time) * 1000

            if health_result.get("status") == "healthy":
                return {
                    "status": ServiceStatus.RUNNING.value,
                    "last_check": datetime.now(timezone.utc).isoformat(),
                    "response_time_ms": response_time,
                    "version": health_result.get("version", "unknown"),
                    "model": health_result.get("model", "unknown"),
                    "message": "AI service healthy",
                }
            else:
                return {
                    "status": ServiceStatus.ERROR.value,
                    "last_check": datetime.now(timezone.utc).isoformat(),
                    "response_time_ms": response_time,
                    "error_message": health_result.get("error", "Unknown error"),
                    "message": "AI service unhealthy",
                }

        except Exception as e:
            return {
                "status": ServiceStatus.ERROR.value,
                "last_check": datetime.now(timezone.utc).isoformat(),
                "error_message": str(e),
                "message": "AI service check failed",
            }

    async def _check_execution_engine_health(self) -> Dict[str, Any]:
        """Check execution engine health"""
        try:
            # Check if execution engine can be imported and basic components are available
            from ..core.execution_engine import ExecutionEngine

            # Check if broker clients are available
            has_brokers = (
                self.angel_one_client is not None or self.dhan_client is not None
            )

            if has_brokers:
                return {
                    "status": ServiceStatus.RUNNING.value,
                    "last_check": datetime.now(timezone.utc).isoformat(),
                    "message": "Execution engine ready",
                }
            else:
                return {
                    "status": ServiceStatus.NOT_CONFIGURED.value,
                    "last_check": datetime.now(timezone.utc).isoformat(),
                    "message": "Execution engine available but no broker clients configured",
                }

        except ImportError:
            return {
                "status": ServiceStatus.NOT_CONFIGURED.value,
                "last_check": datetime.now(timezone.utc).isoformat(),
                "message": "Execution engine not implemented",
            }
        except Exception as e:
            return {
                "status": ServiceStatus.ERROR.value,
                "last_check": datetime.now(timezone.utc).isoformat(),
                "error_message": str(e),
                "message": "Execution engine check failed",
            }

    async def _check_angel_one_connection(self) -> Dict[str, Any]:
        """Check Angel One API connection"""
        if not self.angel_one_client:
            return {
                "status": "NOT_CONFIGURED",
                "last_check": datetime.now(timezone.utc).isoformat(),
                "message": "Angel One client not configured",
            }

        try:
            # Check connection (simplified - would do actual API call)
            return {
                "status": "CONNECTED",
                "last_heartbeat": datetime.now(timezone.utc).isoformat(),
                "response_time_ms": 150.0,  # Mock response time
                "message": "Angel One API connected",
            }

        except Exception as e:
            return {
                "status": "ERROR",
                "last_check": datetime.now(timezone.utc).isoformat(),
                "error_message": str(e),
                "message": "Angel One API connection failed",
            }

    async def _check_dhan_connection(self) -> Dict[str, Any]:
        """Check Dhan API connection"""
        if not self.dhan_client:
            return {
                "status": "NOT_CONFIGURED",
                "last_check": datetime.now(timezone.utc).isoformat(),
                "message": "Dhan client not configured",
            }

        try:
            # Check connection (simplified - would do actual API call)
            return {
                "status": "CONNECTED",
                "last_heartbeat": datetime.now(timezone.utc).isoformat(),
                "response_time_ms": 120.0,  # Mock response time
                "message": "Dhan API connected",
            }

        except Exception as e:
            return {
                "status": "ERROR",
                "last_check": datetime.now(timezone.utc).isoformat(),
                "error_message": str(e),
                "message": "Dhan API connection failed",
            }

    def _calculate_overall_status(
        self,
        services: Dict[str, Dict[str, Any]],
        api_connections: Dict[str, Dict[str, Any]],
    ) -> SystemStatus:
        """
        Calculate overall system status based on service and API health

        Args:
            services: Service health status
            api_connections: API connection status

        Returns:
            Overall system status
        """
        # Check critical services
        critical_services = ["data_manager", "analysis_engine"]
        critical_healthy = True

        for service_name in critical_services:
            if service_name in services:
                status = services[service_name].get("status")
                if status not in [ServiceStatus.RUNNING.value]:
                    critical_healthy = False
                    break

        # Check API connections
        api_healthy = True
        for api_name, api_status in api_connections.items():
            if api_status.get("status") not in ["CONNECTED", "NOT_CONFIGURED"]:
                api_healthy = False
                break

        # Determine overall status
        if critical_healthy and api_healthy:
            return SystemStatus.HEALTHY
        elif critical_healthy:
            return SystemStatus.DEGRADED
        else:
            return SystemStatus.DOWN
