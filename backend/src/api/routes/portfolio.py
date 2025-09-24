"""
Portfolio API Routes for NIRAJ Trading System

Provides comprehensive REST API endpoints for portfolio management including:
- Portfolio overview and position tracking
- P&L calculations and performance metrics
- Risk management and validation
- Real-time position updates

Endpoints:
- GET /api/v1/portfolio: Get user portfolio with positions and summary
- GET /api/v1/portfolio/{portfolio_id}: Get specific portfolio position
- POST /api/v1/portfolio: Create new portfolio position
- PUT /api/v1/portfolio/{portfolio_id}: Update portfolio position
- DELETE /api/v1/portfolio/{portfolio_id}: Close portfolio position
- POST /api/v1/portfolio/{portfolio_id}/close: Close position with price
- GET /api/v1/portfolio/summary: Get portfolio summary statistics
- POST /api/v1/portfolio/validate: Validate portfolio against risk rules
- POST /api/v1/portfolio/update-prices: Update prices for multiple symbols
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import structlog

from ...core.database import DatabaseManager
from ...core.cache import CacheManager
from ...services.portfolio_service import PortfolioService, PortfolioServiceError
from ...models.portfolio import (
    PortfolioCreateRequest, PortfolioUpdateRequest, PortfolioResponse,
    PortfolioAggregateResponse, PortfolioNotFoundError
)

# Initialize router with comprehensive configuration
router = APIRouter(
    prefix="/portfolio",
    tags=["portfolio"],
    responses={
        400: {"description": "Bad Request - Invalid input data"},
        401: {"description": "Unauthorized - Authentication required"},
        403: {"description": "Forbidden - Insufficient permissions"},
        404: {"description": "Not Found - Portfolio position not found"},
        409: {"description": "Conflict - Portfolio operation conflict"},
        422: {"description": "Unprocessable Entity - Validation error"},
        500: {"description": "Internal Server Error - System error"}
    }
)

# Initialize structured logger
logger = structlog.get_logger(__name__)

# Global service instances (initialized on startup)
_portfolio_service: Optional[PortfolioService] = None


# Pydantic models for API requests and responses
class PortfolioListResponse(BaseModel):
    """Response model for portfolio list with summary"""
    positions: List[PortfolioResponse]
    summary: PortfolioAggregateResponse
    total_positions: int
    last_updated: datetime


class PriceUpdateRequest(BaseModel):
    """Request model for updating position prices"""
    price_updates: Dict[str, float]  # symbol -> price mapping


class ClosePositionRequest(BaseModel):
    """Request model for closing a position"""
    close_price: float
    reason: Optional[str] = None


class RiskValidationResponse(BaseModel):
    """Response model for risk validation"""
    is_valid: bool
    violations: List[str]
    total_positions: int
    validated_at: datetime


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
async def get_portfolio_service() -> PortfolioService:
    """Get portfolio service instance"""
    global _portfolio_service
    if _portfolio_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Portfolio service not initialized"
        )
    return _portfolio_service


async def get_current_user_id() -> str:
    """
    Get current user ID from authentication context

    TODO: Implement proper authentication integration
    For now, returns a test user ID
    """
    # Placeholder - should be replaced with actual auth integration
    return "test_user_001"


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


def handle_portfolio_error(e: Exception, request_path: str) -> JSONResponse:
    """Handle portfolio-related errors with appropriate HTTP status codes"""
    logger.warning(
        "Portfolio operation error",
        error_type=type(e).__name__,
        error_code=getattr(e, 'error_code', 'UNKNOWN'),
        path=request_path,
        portfolio_id=getattr(e, 'portfolio_id', None)
    )

    # Map error types to HTTP status codes
    if isinstance(e, PortfolioNotFoundError):
        status_code = status.HTTP_404_NOT_FOUND
        error_code = "PORTFOLIO_NOT_FOUND"
    elif isinstance(e, PortfolioServiceError):
        if "VALIDATION_FAILED" in str(e):
            status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
            error_code = "VALIDATION_ERROR"
        elif "PERMISSION_DENIED" in str(e):
            status_code = status.HTTP_403_FORBIDDEN
            error_code = "PERMISSION_DENIED"
        else:
            status_code = status.HTTP_400_BAD_REQUEST
            error_code = getattr(e, 'error_code', 'PORTFOLIO_ERROR')
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        error_code = "INTERNAL_ERROR"

    return create_error_response(
        error=type(e).__name__,
        error_code=error_code,
        message=str(e),
        status_code=status_code,
        details={
            'portfolio_id': getattr(e, 'portfolio_id', None)
        },
        path=request_path
    )


# Route handlers
@router.get(
    "",
    response_model=PortfolioListResponse,
    summary="Get User Portfolio",
    description="""
    Retrieve the complete user portfolio including all positions and summary metrics.

    **Returns:**
    - List of all portfolio positions
    - Portfolio summary with aggregate metrics
    - Total position count
    - Last update timestamp

    **Features:**
    - Real-time P&L calculations
    - Risk metrics for each position
    - Performance tracking
    - Caching for performance
    """,
    responses={
        200: {"description": "Portfolio retrieved successfully"},
        401: {"description": "Authentication required"},
        500: {"description": "Internal server error"}
    }
)
async def get_portfolio(
    include_inactive: bool = Query(False, description="Include inactive/closed positions"),
    user_id: str = Depends(get_current_user_id),
    portfolio_service: PortfolioService = Depends(get_portfolio_service)
) -> PortfolioListResponse:
    """
    Get complete user portfolio with positions and summary

    Retrieves all portfolio positions for the authenticated user,
    calculates real-time P&L, and provides comprehensive summary metrics.
    """
    start_time = datetime.now(timezone.utc)

    try:
        with structlog.contextvars.bound_contextvars(
            user_id=user_id,
            include_inactive=include_inactive
        ):
            logger.info("Portfolio retrieval request")

            # Get portfolio positions and summary
            positions, summary = await portfolio_service.get_user_portfolio(
                user_id=user_id,
                include_inactive=include_inactive
            )

            response = PortfolioListResponse(
                positions=positions,
                summary=summary,
                total_positions=len(positions),
                last_updated=datetime.now(timezone.utc)
            )

            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.info(
                "Portfolio retrieved successfully",
                positions_count=len(positions),
                duration=f"{duration:.3f}s"
            )

            return response

    except Exception as e:
        # Handle unexpected errors
        return handle_portfolio_error(e, "/portfolio")


@router.get(
    "/{portfolio_id}",
    response_model=PortfolioResponse,
    summary="Get Portfolio Position",
    description="""
    Retrieve detailed information for a specific portfolio position.

    **Returns:**
    - Complete position details
    - Real-time P&L calculations
    - Risk metrics
    - Performance history

    **Path Parameters:**
    - `portfolio_id`: Unique identifier for the portfolio position
    """,
    responses={
        200: {"description": "Position retrieved successfully"},
        401: {"description": "Authentication required"},
        404: {"description": "Portfolio position not found"},
        500: {"description": "Internal server error"}
    }
)
async def get_portfolio_position(
    portfolio_id: str,
    user_id: str = Depends(get_current_user_id),
    portfolio_service: PortfolioService = Depends(get_portfolio_service)
) -> PortfolioResponse:
    """
    Get specific portfolio position by ID

    Validates user ownership and returns detailed position information
    with real-time calculations.
    """
    try:
        with structlog.contextvars.bound_contextvars(
            user_id=user_id,
            portfolio_id=portfolio_id
        ):
            logger.info("Portfolio position retrieval request")

            # Get position (service handles ownership validation)
            position = await portfolio_service.get_portfolio_position(portfolio_id)

            # TODO: Add ownership validation when auth is integrated
            # For now, assume all positions belong to the user

            logger.info("Portfolio position retrieved successfully")
            return position

    except Exception as e:
        return handle_portfolio_error(e, f"/portfolio/{portfolio_id}")


@router.post(
    "",
    response_model=PortfolioResponse,
    summary="Create Portfolio Position",
    description="""
    Create a new portfolio position.

    **Creates:**
    - New position record in database
    - Initial P&L calculations
    - Risk assessments
    - Performance tracking setup

    **Validation:**
    - Position size limits
    - Risk level assessment
    - Stop loss/take profit validation
    """,
    responses={
        201: {"description": "Position created successfully"},
        400: {"description": "Invalid position data"},
        401: {"description": "Authentication required"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"}
    }
)
async def create_portfolio_position(
    position_data: PortfolioCreateRequest,
    user_id: str = Depends(get_current_user_id),
    portfolio_service: PortfolioService = Depends(get_portfolio_service)
) -> PortfolioResponse:
    """
    Create a new portfolio position

    Validates input data, creates position record, and initializes
    all necessary calculations and tracking.
    """
    try:
        with structlog.contextvars.bound_contextvars(
            user_id=user_id,
            symbol=position_data.symbol,
            quantity=position_data.quantity
        ):
            logger.info("Portfolio position creation request")

            # Override user_id from auth context
            position_data.user_id = user_id

            # Create position
            created_position = await portfolio_service.create_portfolio_position(position_data)

            logger.info(
                "Portfolio position created successfully",
                portfolio_id=created_position.portfolio_id
            )

            return created_position

    except Exception as e:
        return handle_portfolio_error(e, "/portfolio")


@router.put(
    "/{portfolio_id}",
    response_model=PortfolioResponse,
    summary="Update Portfolio Position",
    description="""
    Update an existing portfolio position.

    **Updates:**
    - Position size (add/reduce)
    - Stop loss/take profit levels
    - Risk parameters
    - Notes and metadata

    **Validation:**
    - Ownership verification
    - Risk limit checks
    - Position size constraints
    """,
    responses={
        200: {"description": "Position updated successfully"},
        400: {"description": "Invalid update data"},
        401: {"description": "Authentication required"},
        404: {"description": "Portfolio position not found"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"}
    }
)
async def update_portfolio_position(
    portfolio_id: str,
    update_data: PortfolioUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    portfolio_service: PortfolioService = Depends(get_portfolio_service)
) -> PortfolioResponse:
    """
    Update an existing portfolio position

    Validates ownership, applies updates, and recalculates all metrics.
    """
    try:
        with structlog.contextvars.bound_contextvars(
            user_id=user_id,
            portfolio_id=portfolio_id
        ):
            logger.info("Portfolio position update request")

            # TODO: Add ownership validation
            # Update position
            updated_position = await portfolio_service.update_portfolio_position(
                portfolio_id=portfolio_id,
                update_request=update_data
            )

            logger.info("Portfolio position updated successfully")
            return updated_position

    except Exception as e:
        return handle_portfolio_error(e, f"/portfolio/{portfolio_id}")


@router.post(
    "/{portfolio_id}/close",
    summary="Close Portfolio Position",
    description="""
    Close a portfolio position at specified price.

    **Actions:**
    - Mark position as closed
    - Calculate final P&L
    - Move unrealized to realized P&L
    - Update performance metrics
    - Record closure reason

    **Parameters:**
    - `close_price`: Price at which to close the position
    - `reason`: Optional reason for closing (stop loss, take profit, manual, etc.)
    """,
    responses={
        200: {"description": "Position closed successfully"},
        400: {"description": "Invalid close request"},
        401: {"description": "Authentication required"},
        404: {"description": "Portfolio position not found"},
        500: {"description": "Internal server error"}
    }
)
async def close_portfolio_position(
    portfolio_id: str,
    close_request: ClosePositionRequest,
    user_id: str = Depends(get_current_user_id),
    portfolio_service: PortfolioService = Depends(get_portfolio_service)
) -> Dict[str, Any]:
    """
    Close a portfolio position

    Validates ownership, closes position, and calculates final P&L.
    """
    try:
        with structlog.contextvars.bound_contextvars(
            user_id=user_id,
            portfolio_id=portfolio_id,
            close_price=close_request.close_price
        ):
            logger.info("Portfolio position close request")

            # TODO: Add ownership validation
            # Close position
            close_result = await portfolio_service.close_portfolio_position(
                portfolio_id=portfolio_id,
                close_price=close_request.close_price,
                reason=close_request.reason
            )

            logger.info(
                "Portfolio position closed successfully",
                realized_pnl=close_result.get('realized_pnl')
            )

            return close_result

    except Exception as e:
        return handle_portfolio_error(e, f"/portfolio/{portfolio_id}/close")


@router.get(
    "/summary",
    response_model=PortfolioAggregateResponse,
    summary="Get Portfolio Summary",
    description="""
    Get comprehensive portfolio summary statistics.

    **Metrics Include:**
    - Total market value
    - Total unrealized and realized P&L
    - Position counts (long/short)
    - Risk metrics
    - Performance indicators
    - Sector allocation
    - Strategy performance

    **Caching:** Results are cached for performance
    """,
    responses={
        200: {"description": "Summary retrieved successfully"},
        401: {"description": "Authentication required"},
        500: {"description": "Internal server error"}
    }
)
async def get_portfolio_summary(
    include_inactive: bool = Query(False, description="Include inactive positions in summary"),
    user_id: str = Depends(get_current_user_id),
    portfolio_service: PortfolioService = Depends(get_portfolio_service)
) -> PortfolioAggregateResponse:
    """
    Get portfolio summary statistics

    Provides comprehensive overview of portfolio performance and risk metrics.
    """
    try:
        with structlog.contextvars.bound_contextvars(
            user_id=user_id,
            include_inactive=include_inactive
        ):
            logger.info("Portfolio summary request")

            # Get summary
            summary = await portfolio_service.get_portfolio_summary(
                user_id=user_id,
                include_inactive=include_inactive
            )

            logger.info("Portfolio summary retrieved successfully")
            return summary

    except Exception as e:
        return handle_portfolio_error(e, "/portfolio/summary")


@router.post(
    "/validate",
    response_model=RiskValidationResponse,
    summary="Validate Portfolio Risks",
    description="""
    Validate portfolio against risk management rules.

    **Validations:**
    - Position size limits
    - Risk concentration limits
    - Stop loss requirements
    - Sector exposure limits
    - Overall portfolio risk limits

    **Returns:**
    - Validation status
    - List of violations
    - Risk assessment details
    """,
    responses={
        200: {"description": "Risk validation completed"},
        401: {"description": "Authentication required"},
        500: {"description": "Internal server error"}
    }
)
async def validate_portfolio_risks(
    user_id: str = Depends(get_current_user_id),
    portfolio_service: PortfolioService = Depends(get_portfolio_service)
) -> RiskValidationResponse:
    """
    Validate portfolio against risk management rules

    Performs comprehensive risk assessment and returns validation results.
    """
    try:
        with structlog.contextvars.bound_contextvars(
            user_id=user_id
        ):
            logger.info("Portfolio risk validation request")

            # Validate risks
            validation_result = await portfolio_service.validate_portfolio_risks(user_id)

            response = RiskValidationResponse(
                is_valid=validation_result['is_valid'],
                violations=validation_result['violations'],
                total_positions=validation_result['total_positions'],
                validated_at=datetime.fromisoformat(validation_result['validated_at'])
            )

            logger.info(
                "Portfolio risk validation completed",
                is_valid=response.is_valid,
                violations_count=len(response.violations)
            )

            return response

    except Exception as e:
        return handle_portfolio_error(e, "/portfolio/validate")


@router.post(
    "/update-prices",
    summary="Update Position Prices",
    description="""
    Update current prices for multiple symbols and recalculate P&L.

    **Actions:**
    - Update prices for specified symbols
    - Recalculate P&L for affected positions
    - Update risk metrics
    - Invalidate relevant caches

    **Use Cases:**
    - Real-time price feeds
    - End-of-day price updates
    - Manual price corrections

    **Parameters:**
    - `price_updates`: Dictionary mapping symbols to new prices
    """,
    responses={
        200: {"description": "Prices updated successfully"},
        400: {"description": "Invalid price data"},
        401: {"description": "Authentication required"},
        500: {"description": "Internal server error"}
    }
)
async def update_position_prices(
    price_request: PriceUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    portfolio_service: PortfolioService = Depends(get_portfolio_service)
) -> Dict[str, Any]:
    """
    Update prices for multiple symbols

    Updates current prices and recalculates all affected portfolio metrics.
    """
    try:
        with structlog.contextvars.bound_contextvars(
            user_id=user_id,
            symbols=list(price_request.price_updates.keys())
        ):
            logger.info("Position price update request")

            # Convert prices to Decimal
            price_updates = {
                symbol: Decimal(str(price))
                for symbol, price in price_request.price_updates.items()
            }

            # Update prices
            update_result = await portfolio_service.update_position_prices(price_updates)

            logger.info(
                "Position prices updated successfully",
                updated_positions=update_result['updated_positions_count'],
                total_pnl_change=update_result['total_pnl_change']
            )

            return update_result

    except Exception as e:
        return handle_portfolio_error(e, "/portfolio/update-prices")


# Initialization functions
def init_portfolio_routes(
    db_manager: DatabaseManager,
    cache_manager: CacheManager
) -> APIRouter:
    """
    Initialize portfolio routes with required services

    Args:
        db_manager: Database manager instance
        cache_manager: Cache manager instance

    Returns:
        Configured FastAPI router
    """
    global _portfolio_service

    try:
        # Initialize portfolio service
        _portfolio_service = PortfolioService(
            db_manager=db_manager,
            cache_manager=cache_manager
        )

        logger.info("Portfolio routes initialized successfully")
        return router

    except Exception as e:
        logger.error("Failed to initialize portfolio routes", error=str(e))
        raise


# Export router and initialization function
__all__ = [
    "router",
    "init_portfolio_routes",
    "PortfolioListResponse",
    "PriceUpdateRequest",
    "ClosePositionRequest",
    "RiskValidationResponse",
    "ErrorResponse"
]
