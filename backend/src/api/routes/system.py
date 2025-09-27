"""
System and AI Endpoints for NIRAJ Trading System

Provides REST API endpoints for system monitoring, status reporting,
and AI prediction retrieval. Includes comprehensive health checks,
system metrics, and AI insights.

Endpoints:
- GET /api/v1/system/status: Get comprehensive system status
- GET /api/v1/ai/predictions: Get AI predictions with filtering
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import structlog

from ...core.database import DatabaseManager

try:
    from ...core.cache import CacheManager

    CACHE_AVAILABLE = True
except ImportError:
    CacheManager = None
    CACHE_AVAILABLE = False

try:
    from ...ai.gemma3_integration import Gemma3Client

    AI_AVAILABLE = True
except ImportError:
    Gemma3Client = None
    AI_AVAILABLE = False

from ...services.system_service import SystemService, SystemServiceError

# Initialize router with comprehensive configuration
router = APIRouter(
    prefix="",
    tags=["system", "ai"],
    responses={
        400: {"description": "Bad Request - Invalid input data"},
        401: {"description": "Unauthorized - Authentication required"},
        403: {"description": "Forbidden - Insufficient permissions"},
        422: {"description": "Unprocessable Entity - Validation error"},
        500: {"description": "Internal Server Error - System error"},
    },
)

# Initialize structured logger
logger = structlog.get_logger(__name__)

# Global service instances (initialized on startup)
_system_service: Optional[SystemService] = None


# Pydantic models for API requests and responses
class SystemStatusResponse(BaseModel):
    """Response model for system status"""

    status: str
    trading_mode: str
    market_hours: bool
    timestamp: str
    services: Dict[str, Any]
    api_connections: Dict[str, Any]
    system_metrics: Dict[str, Any]


class AIPredictionsResponse(BaseModel):
    """Response model for AI predictions"""

    predictions: List[Dict[str, Any]]
    total: int
    limit: int
    offset: int


class ErrorResponse(BaseModel):
    """Enhanced error response model"""

    error: str
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: str
    request_id: Optional[str] = None
    path: Optional[str] = None


# Dependency functions
async def get_system_service() -> SystemService:
    """Get system service instance"""
    global _system_service
    if _system_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="System service not initialized",
        )
    return _system_service


# Error handling utilities
def create_error_response(
    error: str,
    error_code: str,
    message: str,
    status_code: int,
    details: Optional[Dict[str, Any]] = None,
    path: Optional[str] = None,
) -> JSONResponse:
    """Create standardized error response"""
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(
            error=error,
            error_code=error_code,
            message=message,
            details=details,
            timestamp=datetime.now(timezone.utc).isoformat(),
            path=path,
        ).dict(),
    )


def handle_system_error(e: Exception, request_path: str) -> JSONResponse:
    """Handle system-related errors with appropriate HTTP status codes"""
    logger.warning(
        "System operation error",
        error_type=type(e).__name__,
        error_code=getattr(e, "error_code", "UNKNOWN"),
        path=request_path,
    )

    if isinstance(e, SystemServiceError):
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        error_code = getattr(e, "error_code", None) or "SYSTEM_ERROR"
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        error_code = "INTERNAL_ERROR"

    return create_error_response(
        error=type(e).__name__,
        error_code=error_code,
        message=str(e),
        status_code=status_code,
        details={"service": getattr(e, "service", None)},
        path=request_path,
    )


# Route handlers
@router.get(
    "/system/status",
    response_model=SystemStatusResponse,
    summary="Get System Status",
    description="""
    Retrieve comprehensive system status information including health checks,
    service statuses, API connections, and system metrics.

    **System Status:**
    - `HEALTHY`: All critical services running, APIs connected
    - `DEGRADED`: Critical services running but some issues
    - `DOWN`: Critical services not available

    **Trading Mode:**
    - `paper`: Paper trading mode (default)
    - `live`: Live trading mode (requires PIN 1937)

    **Market Hours:**
    - `true`: Indian equity markets open (9:15 AM - 3:30 PM IST)
    - `false`: Markets closed

    **Services Status:**
    - `data_manager`: Database and data services
    - `analysis_engine`: Technical analysis engine
    - `execution_engine`: Trade execution engine
    - `ai_service`: AI prediction services

    **API Connections:**
    - `angel_one`: Angel One Smart API status
    - `dhan`: Dhan HQ API status

    **System Metrics:**
    - CPU, memory, disk usage percentages
    - Active strategies and open positions count
    - AI predictions statistics
    - System uptime

    **Caching:**
    - Results cached for 30 seconds for performance
    """,
    responses={
        200: {"description": "System status retrieved successfully"},
        503: {"description": "System service unavailable"},
        500: {"description": "Internal server error"},
    },
)
async def get_system_status(
    system_service: SystemService = Depends(get_system_service),
) -> SystemStatusResponse:
    """
    Get comprehensive system status

    Returns detailed information about system health, services,
    connections, and performance metrics.
    """
    start_time = datetime.now(timezone.utc)

    try:
        logger.info("Retrieving system status")

        # Get system status from service
        status_data = await system_service.get_system_status()

        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        logger.info(
            "System status retrieved successfully",
            overall_status=status_data.get("status"),
            trading_mode=status_data.get("trading_mode"),
            market_hours=status_data.get("market_hours"),
            duration=f"{duration:.3f}s",
        )

        return SystemStatusResponse(**status_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Get system status error", error=str(e))
        return handle_system_error(e, "/system/status")


@router.get(
    "/ai/predictions",
    response_model=AIPredictionsResponse,
    summary="Get AI Predictions",
    description="""
    Retrieve AI-generated trading predictions with optional filtering.

    **Filtering Options:**
    - `symbol`: Filter predictions for specific symbol (e.g., "BANKNIFTY")
    - `strategy_id`: Filter predictions for specific strategy UUID
    - `min_confidence`: Minimum confidence threshold (0.0-1.0, default: 0.7)

    **Pagination:**
    - `limit`: Maximum number of results (default: 100, max: 1000)
    - `offset`: Pagination offset (default: 0)

    **Prediction Schema:**
    - `prediction_id`: Unique prediction identifier (UUID)
    - `symbol`: Trading symbol
    - `strategy_id`: Associated strategy identifier
    - `timestamp`: Prediction creation timestamp
    - `predicted_direction`: UP/DOWN/SIDEWAYS
    - `confidence_score`: AI confidence (0.0-1.0)
    - `predicted_magnitude`: Expected price movement magnitude
    - `prediction_horizon`: Time horizon in periods
    - `reasoning`: AI reasoning for the prediction
    - `market_features`: Market data features used
    - `was_correct`: Outcome validation (null if not validated)
    - `trade_executed`: Whether prediction led to trade execution

    **Response Structure:**
    ```json
    {
      "predictions": [...],
      "total": 150,
      "limit": 100,
      "offset": 0
    }
    ```

    **Performance Notes:**
    - Results ordered by creation time (newest first)
    - Confidence filtering applied server-side for efficiency
    - Large result sets may be paginated
    """,
    responses={
        200: {"description": "AI predictions retrieved successfully"},
        400: {"description": "Invalid filter parameters"},
        422: {"description": "Invalid UUID format or parameter values"},
        503: {"description": "System service unavailable"},
        500: {"description": "Internal server error"},
    },
)
async def get_ai_predictions(
    symbol: Optional[str] = Query(None, description="Filter by trading symbol"),
    strategy_id: Optional[str] = Query(None, description="Filter by strategy UUID"),
    min_confidence: float = Query(
        0.7, ge=0.0, le=1.0, description="Minimum confidence threshold"
    ),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    system_service: SystemService = Depends(get_system_service),
) -> AIPredictionsResponse:
    """
    Get AI predictions with filtering and pagination

    Supports advanced filtering by symbol, strategy, and confidence
    with comprehensive pagination support.
    """
    start_time = datetime.now(timezone.utc)

    try:
        with structlog.contextvars.bound_contextvars(
            symbol=symbol,
            strategy_id=strategy_id,
            min_confidence=min_confidence,
            limit=limit,
            offset=offset,
        ):
            logger.info("Retrieving AI predictions")

            # Validate strategy_id format if provided
            if strategy_id:
                try:
                    UUID(strategy_id)
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="Invalid strategy_id format. Must be a valid UUID.",
                    )

            # Get predictions from service
            predictions_data = await system_service.get_ai_predictions(
                symbol=symbol,
                strategy_id=strategy_id,
                min_confidence=min_confidence,
                limit=limit,
                offset=offset,
            )

            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.info(
                "AI predictions retrieved successfully",
                count=len(predictions_data.get("predictions", [])),
                total=predictions_data.get("total", 0),
                symbol=symbol,
                strategy_id=strategy_id,
                duration=f"{duration:.3f}s",
            )

            return AIPredictionsResponse(**predictions_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Get AI predictions error", error=str(e))
        return handle_system_error(e, "/ai/predictions")


# Service initialization functions
def init_system_routes(
    db_manager: DatabaseManager,
    cache_manager: Optional[Any] = None,
    ai_client: Optional[Any] = None,
    angel_one_client: Optional[Any] = None,
    dhan_client: Optional[Any] = None,
) -> APIRouter:
    """
    Initialize system routes with required services

    Args:
        db_manager: Database manager instance
        cache_manager: Optional cache manager instance
        ai_client: Optional AI integration client
        angel_one_client: Optional Angel One API client
        dhan_client: Optional Dhan API client

    Returns:
        Configured FastAPI router
    """
    global _system_service

    try:
        # Initialize system service
        _system_service = SystemService(
            db_manager=db_manager,
            cache_manager=cache_manager,
            ai_client=ai_client,
            angel_one_client=angel_one_client,
            dhan_client=dhan_client,
        )

        logger.info("System routes initialized successfully")
        return router

    except Exception as e:
        logger.error("Failed to initialize system routes", error=str(e))
        raise


# Export router and initialization function
__all__ = [
    "router",
    "init_system_routes",
    "SystemStatusResponse",
    "AIPredictionsResponse",
    "ErrorResponse",
]
