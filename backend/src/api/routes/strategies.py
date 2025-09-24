"""
Strategy Management API Routes for NIRAJ Trading System

Provides comprehensive REST API endpoints for strategy management including:
- CRUD operations for trading strategies
- Backtesting capabilities
- Strategy performance tracking
- Advanced filtering and pagination
- Comprehensive error handling and validation

Endpoints:
- GET /api/v1/strategies: List strategies with filtering
- POST /api/v1/strategies: Create new strategy
- GET /api/v1/strategies/{strategy_id}: Get strategy details
- PUT /api/v1/strategies/{strategy_id}: Update strategy
- DELETE /api/v1/strategies/{strategy_id}: Delete strategy
- POST /api/v1/strategies/{strategy_id}/backtest: Run backtest
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import structlog

from ...core.database import DatabaseManager
from ...core.cache import CacheManager
from ...services.strategy_service import StrategyService, StrategyServiceError
from ...models.strategy import (
    StrategyCreateRequest, StrategyUpdateRequest, StrategyResponse,
    StrategyCategory, StrategyNotFoundError
)
from ...models.backtest import BacktestRequest, BacktestResult
from ...ai.gemma3_integration import Gemma3Client

# Initialize router with comprehensive configuration
router = APIRouter(
    prefix="/strategies",
    tags=["strategies"],
    responses={
        400: {"description": "Bad Request - Invalid input data"},
        401: {"description": "Unauthorized - Authentication required"},
        403: {"description": "Forbidden - Insufficient permissions"},
        404: {"description": "Not Found - Strategy not found"},
        409: {"description": "Conflict - Strategy name already exists"},
        422: {"description": "Unprocessable Entity - Validation error"},
        500: {"description": "Internal Server Error - System error"}
    }
)

# Initialize structured logger
logger = structlog.get_logger(__name__)

# Global service instances (initialized on startup)
_strategy_service: Optional[StrategyService] = None


# Pydantic models for API requests and responses
class StrategyListResponse(BaseModel):
    """Response model for strategy listing"""
    strategies: List[StrategyResponse]
    total: int
    limit: int
    offset: int


class BacktestResponse(BaseModel):
    """Response model for backtest results"""
    backtest_result: BacktestResult


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
async def get_strategy_service() -> StrategyService:
    """Get strategy service instance"""
    global _strategy_service
    if _strategy_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Strategy service not initialized"
        )
    return _strategy_service


# Error handling utilities
def create_error_response(
    error: str,
    error_code: str,
    message: str,
    status_code: int,
    details: Optional[Dict[str, Any]] = None,
    path: Optional[str] = None
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
            path=path
        ).dict()
    )


def handle_strategy_error(e: Exception, request_path: str) -> JSONResponse:
    """Handle strategy-related errors with appropriate HTTP status codes"""
    logger.warning(
        "Strategy operation error",
        error_type=type(e).__name__,
        error_code=getattr(e, 'error_code', 'UNKNOWN'),
        path=request_path,
        strategy_id=getattr(e, 'strategy_id', None)
    )

    # Map error types to HTTP status codes
    if isinstance(e, StrategyNotFoundError):
        status_code = status.HTTP_404_NOT_FOUND
        error_code = "STRATEGY_NOT_FOUND"
    elif isinstance(e, StrategyServiceError):
        if "DUPLICATE_NAME" in str(e):
            status_code = status.HTTP_409_CONFLICT
            error_code = "DUPLICATE_STRATEGY_NAME"
        else:
            status_code = status.HTTP_400_BAD_REQUEST
            error_code = getattr(e, 'error_code', 'STRATEGY_ERROR')
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        error_code = "INTERNAL_ERROR"

    return create_error_response(
        error=type(e).__name__,
        error_code=error_code,
        message=str(e),
        status_code=status_code,
        details={
            'strategy_id': getattr(e, 'strategy_id', None)
        },
        path=request_path
    )


# Route handlers
@router.get(
    "",
    response_model=StrategyListResponse,
    summary="List Strategies",
    description="""
    Retrieve a list of trading strategies with optional filtering and pagination.

    **Filtering Options:**
    - `category`: Filter by strategy category (predatory, quantitative, psychological, mathematical, extreme)
    - `is_active`: Filter by active status (true/false)

    **Pagination:**
    - `limit`: Maximum number of results (default: 100, max: 1000)
    - `offset`: Pagination offset (default: 0)

    **Returns:**
    - List of strategy objects
    - Total count for pagination
    - Applied limit and offset
    """,
    responses={
        200: {"description": "Strategies retrieved successfully"},
        400: {"description": "Invalid filter parameters"},
        500: {"description": "Internal server error"}
    }
)
async def list_strategies(
    category: Optional[str] = Query(None, description="Filter by strategy category"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    strategy_service: StrategyService = Depends(get_strategy_service)
) -> StrategyListResponse:
    """
    List strategies with filtering and pagination

    Supports advanced filtering by category and active status with
    comprehensive pagination support.
    """
    start_time = datetime.now(timezone.utc)

    try:
        with structlog.contextvars.bound_contextvars(
            category=category,
            is_active=is_active,
            limit=limit,
            offset=offset
        ):
            logger.info("Listing strategies")

            # Validate category filter
            if category and category not in [c.value for c in StrategyCategory]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid category: {category}. Must be one of: {[c.value for c in StrategyCategory]}"
                )

            # Get strategies from service
            strategies, total = await strategy_service.list_strategies(
                category=category,
                is_active=is_active,
                limit=limit,
                offset=offset
            )

            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.info(
                "Strategies listed successfully",
                count=len(strategies),
                total=total,
                duration=f"{duration:.3f}s"
            )

            return StrategyListResponse(
                strategies=strategies,
                total=total,
                limit=limit,
                offset=offset
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("List strategies error", error=str(e))
        return handle_strategy_error(e, "/strategies")


@router.post(
    "",
    response_model=StrategyResponse,
    summary="Create Strategy",
    description="""
    Create a new trading strategy with comprehensive validation.

    **Required Fields:**
    - `name`: Unique strategy name
    - `category`: Strategy category
    - `target_symbols`: List of trading symbols

    **Optional Fields:**
    - `description`: Strategy description
    - `parameters`: Strategy-specific parameters
    - `min_confidence`: Minimum AI confidence threshold
    - `max_position_size`: Maximum position size
    - `stop_loss_pct`: Stop loss percentage
    - `take_profit_pct`: Take profit percentage
    - `max_daily_trades`: Maximum trades per day
    - `is_paper_only`: Restrict to paper trading

    **Validation:**
    - Name uniqueness across all strategies
    - Category must be valid enum value
    - Target symbols must be non-empty
    - Numeric fields must be within valid ranges

    **Returns:**
    - Complete strategy object with generated ID and timestamps
    """,
    responses={
        201: {"description": "Strategy created successfully"},
        400: {"description": "Invalid request data"},
        409: {"description": "Strategy name already exists"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"}
    },
    status_code=status.HTTP_201_CREATED
)
async def create_strategy(
    strategy_data: StrategyCreateRequest,
    strategy_service: StrategyService = Depends(get_strategy_service)
) -> StrategyResponse:
    """
    Create a new trading strategy

    Performs comprehensive validation including name uniqueness,
    category validation, and parameter validation.
    """
    start_time = datetime.now(timezone.utc)

    try:
        with structlog.contextvars.bound_contextvars(
            strategy_name=strategy_data.name,
            category=strategy_data.category.value
        ):
            logger.info("Creating strategy")

            # Create strategy through service
            strategy = await strategy_service.create_strategy(strategy_data)

            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.info(
                "Strategy created successfully",
                strategy_id=strategy.strategy_id,
                duration=f"{duration:.3f}s"
            )

            return strategy

    except Exception as e:
        logger.error("Create strategy error", error=str(e))
        return handle_strategy_error(e, "/strategies")


@router.get(
    "/{strategy_id}",
    response_model=StrategyResponse,
    summary="Get Strategy",
    description="""
    Retrieve detailed information about a specific trading strategy.

    **Path Parameters:**
    - `strategy_id`: UUID of the strategy

    **Returns:**
    - Complete strategy object with all fields
    - Performance metrics and statistics
    - Configuration and parameters

    **Caching:**
    - Results are cached for 5 minutes for performance
    """,
    responses={
        200: {"description": "Strategy retrieved successfully"},
        404: {"description": "Strategy not found"},
        422: {"description": "Invalid strategy ID format"},
        500: {"description": "Internal server error"}
    }
)
async def get_strategy(
    strategy_id: str,
    strategy_service: StrategyService = Depends(get_strategy_service)
) -> StrategyResponse:
    """
    Get a specific strategy by ID

    Validates UUID format and retrieves strategy with caching.
    """
    start_time = datetime.now(timezone.utc)

    try:
        # Validate UUID format
        try:
            UUID(strategy_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid strategy ID format. Must be a valid UUID."
            )

        with structlog.contextvars.bound_contextvars(
            strategy_id=strategy_id
        ):
            logger.info("Retrieving strategy")

            # Get strategy from service
            strategy = await strategy_service.get_strategy(strategy_id)

            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.info(
                "Strategy retrieved successfully",
                strategy_id=strategy_id,
                duration=f"{duration:.3f}s"
            )

            return strategy

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Get strategy error", strategy_id=strategy_id, error=str(e))
        return handle_strategy_error(e, f"/strategies/{strategy_id}")


@router.put(
    "/{strategy_id}",
    response_model=StrategyResponse,
    summary="Update Strategy",
    description="""
    Update an existing trading strategy with partial or full updates.

    **Path Parameters:**
    - `strategy_id`: UUID of the strategy to update

    **Update Fields:** (all optional)
    - `name`: Update strategy name (must be unique)
    - `description`: Update description
    - `parameters`: Update strategy parameters
    - `target_symbols`: Update target symbols
    - `min_confidence`: Update confidence threshold
    - `max_position_size`: Update position size limit
    - `stop_loss_pct`: Update stop loss percentage
    - `take_profit_pct`: Update take profit percentage
    - `max_daily_trades`: Update daily trade limit
    - `is_active`: Update active status
    - `is_paper_only`: Update paper trading restriction

    **Validation:**
    - Strategy must exist
    - Name uniqueness if name is updated
    - All updated fields are validated
    - Timestamps are automatically updated

    **Returns:**
    - Updated complete strategy object
    """,
    responses={
        200: {"description": "Strategy updated successfully"},
        404: {"description": "Strategy not found"},
        409: {"description": "Strategy name already exists"},
        422: {"description": "Invalid strategy ID or update data"},
        500: {"description": "Internal server error"}
    }
)
async def update_strategy(
    strategy_id: str,
    update_data: StrategyUpdateRequest,
    strategy_service: StrategyService = Depends(get_strategy_service)
) -> StrategyResponse:
    """
    Update an existing strategy

    Supports partial updates with comprehensive validation.
    """
    start_time = datetime.now(timezone.utc)

    try:
        # Validate UUID format
        try:
            UUID(strategy_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid strategy ID format. Must be a valid UUID."
            )

        with structlog.contextvars.bound_contextvars(
            strategy_id=strategy_id,
            update_fields=list(update_data.dict(exclude_unset=True).keys())
        ):
            logger.info("Updating strategy")

            # Update strategy through service
            strategy = await strategy_service.update_strategy(strategy_id, update_data)

            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.info(
                "Strategy updated successfully",
                strategy_id=strategy_id,
                duration=f"{duration:.3f}s"
            )

            return strategy

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Update strategy error", strategy_id=strategy_id, error=str(e))
        return handle_strategy_error(e, f"/strategies/{strategy_id}")


@router.delete(
    "/{strategy_id}",
    summary="Delete Strategy",
    description="""
    Permanently delete a trading strategy.

    **Path Parameters:**
    - `strategy_id`: UUID of the strategy to delete

    **Security:**
    - Strategy must exist to be deleted
    - Operation is irreversible
    - Cache is invalidated after deletion

    **Returns:**
    - 204 No Content on successful deletion
    - 404 if strategy doesn't exist
    """,
    responses={
        204: {"description": "Strategy deleted successfully"},
        404: {"description": "Strategy not found"},
        422: {"description": "Invalid strategy ID format"},
        500: {"description": "Internal server error"}
    },
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_strategy(
    strategy_id: str,
    strategy_service: StrategyService = Depends(get_strategy_service)
) -> None:
    """
    Delete a strategy by ID

    Permanently removes strategy with proper cleanup.
    """
    start_time = datetime.now(timezone.utc)

    try:
        # Validate UUID format
        try:
            UUID(strategy_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid strategy ID format. Must be a valid UUID."
            )

        with structlog.contextvars.bound_contextvars(
            strategy_id=strategy_id
        ):
            logger.info("Deleting strategy")

            # Delete strategy through service
            deleted = await strategy_service.delete_strategy(strategy_id)

            if not deleted:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Strategy not found"
                )

            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.info(
                "Strategy deleted successfully",
                strategy_id=strategy_id,
                duration=f"{duration:.3f}s"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Delete strategy error", strategy_id=strategy_id, error=str(e))
        return handle_strategy_error(e, f"/strategies/{strategy_id}")


@router.post(
    "/{strategy_id}/backtest",
    response_model=BacktestResponse,
    summary="Run Strategy Backtest",
    description="""
    Execute a comprehensive backtest for a trading strategy.

    **Path Parameters:**
    - `strategy_id`: UUID of the strategy to backtest

    **Request Body:**
    - `start_date`: Backtest start date (YYYY-MM-DD)
    - `end_date`: Backtest end date (YYYY-MM-DD)
    - `initial_capital`: Starting capital amount
    - `symbols`: Optional list of symbols (defaults to strategy symbols)

    **Backtest Features:**
    - Historical market data simulation
    - Realistic commission and slippage modeling
    - Comprehensive performance metrics
    - Risk analysis and drawdown calculation
    - Trade-by-trade execution details
    - Equity curve generation

    **Performance Metrics:**
    - Total return and annualized return
    - Volatility and Sharpe ratio
    - Maximum drawdown and Calmar ratio
    - Win rate and profit factor
    - Risk-adjusted returns

    **Returns:**
    - Complete backtest results with metrics
    - Individual trade details
    - Daily equity curve
    - Performance statistics
    """,
    responses={
        200: {"description": "Backtest completed successfully"},
        400: {"description": "Invalid backtest parameters"},
        404: {"description": "Strategy not found"},
        422: {"description": "Invalid strategy ID or request data"},
        500: {"description": "Internal server error"}
    }
)
async def run_backtest(
    strategy_id: str,
    backtest_request: BacktestRequest,
    strategy_service: StrategyService = Depends(get_strategy_service)
) -> BacktestResponse:
    """
    Run a backtest for a strategy

    Executes comprehensive backtesting with realistic market simulation.
    """
    start_time = datetime.now(timezone.utc)

    try:
        # Validate UUID format
        try:
            UUID(strategy_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid strategy ID format. Must be a valid UUID."
            )

        with structlog.contextvars.bound_contextvars(
            strategy_id=strategy_id,
            start_date=backtest_request.start_date.isoformat(),
            end_date=backtest_request.end_date.isoformat(),
            initial_capital=backtest_request.initial_capital
        ):
            logger.info("Running strategy backtest")

            # Run backtest through service
            backtest_result = await strategy_service.run_backtest(strategy_id, backtest_request)

            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.info(
                "Backtest completed successfully",
                strategy_id=strategy_id,
                backtest_id=backtest_result.backtest_id,
                total_return=backtest_result.performance_metrics.total_return,
                duration=f"{duration:.3f}s"
            )

            return BacktestResponse(backtest_result=backtest_result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Backtest error", strategy_id=strategy_id, error=str(e))
        return handle_strategy_error(e, f"/strategies/{strategy_id}/backtest")


# Service initialization functions
def init_strategy_routes(
    db_manager: DatabaseManager,
    cache_manager: CacheManager,
    ai_integration: Optional[Gemma3Client] = None
) -> APIRouter:
    """
    Initialize strategy routes with required services

    Args:
        db_manager: Database manager instance
        cache_manager: Cache manager instance
        ai_integration: Optional AI integration instance

    Returns:
        Configured FastAPI router
    """
    global _strategy_service

    try:
        # Initialize strategy service
        _strategy_service = StrategyService(
            db_manager=db_manager,
            cache_manager=cache_manager,
            ai_integration=ai_integration
        )

        logger.info("Strategy routes initialized successfully")
        return router

    except Exception as e:
        logger.error("Failed to initialize strategy routes", error=str(e))
        raise


# Export router and initialization function
__all__ = [
    "router",
    "init_strategy_routes",
    "StrategyListResponse",
    "BacktestResponse",
    "ErrorResponse"
]
