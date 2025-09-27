"""
Trading API Routes for NIRAJ Trading System

Provides comprehensive REST API endpoints for trade management including:
- CRUD operations for trades
- Advanced filtering and pagination
- Trade updates (stop loss, take profit)
- Comprehensive error handling and validation
- Real-time trade status tracking

Endpoints:
- GET /api/v1/trades: List trades with filtering and pagination
- POST /api/v1/trades: Create new trade
- GET /api/v1/trades/{trade_id}: Get trade details
- PATCH /api/v1/trades/{trade_id}: Update trade (stop loss/take profit)
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import structlog

from ...core.database import DatabaseManager
from ...core.cache import CacheManager
from ...models.trade import (
    Trade,
    TradeCreateRequest,
    TradeResponse,
    TradeType,
    BrokerType,
    TradeValidationError,
    TradeNotFoundError,
    TradeExecutionError,
)

# Initialize router with comprehensive configuration
router = APIRouter(
    prefix="/trades",
    tags=["trades"],
    responses={
        400: {"description": "Bad Request - Invalid input data"},
        401: {"description": "Unauthorized - Authentication required"},
        403: {"description": "Forbidden - Insufficient permissions"},
        404: {"description": "Not Found - Trade not found"},
        422: {"description": "Unprocessable Entity - Validation error"},
        500: {"description": "Internal Server Error - System error"},
    },
)

# Initialize structured logger
logger = structlog.get_logger(__name__)

# Global service instances (initialized on startup)
_db_manager: Optional[DatabaseManager] = None
_cache_manager: Optional[CacheManager] = None


# Pydantic models for API requests and responses
class TradeListResponse(BaseModel):
    """Response model for trade listing"""

    trades: List[TradeResponse]
    total: int
    has_more: bool


class TradeCreateRequestModel(BaseModel):
    """Request model for creating a new trade"""

    symbol: str = Field(..., min_length=1, max_length=50, description="Trading symbol")
    trade_type: str = Field(..., description="Trade type (BUY/SELL)")
    quantity: int = Field(..., gt=0, description="Number of shares/contracts")
    price: Optional[float] = Field(
        None, gt=0, description="Entry price (market order if not specified)"
    )
    stop_loss: Optional[float] = Field(None, gt=0, description="Stop loss price")
    take_profit: Optional[float] = Field(None, gt=0, description="Take profit price")
    strategy_id: Optional[str] = Field(
        None, description="Strategy ID if trade is from a strategy"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "symbol": "BANKNIFTY",
                "trade_type": "BUY",
                "quantity": 25,
                "price": 45000.50,
                "stop_loss": 44000.00,
                "take_profit": 46000.00,
                "strategy_id": "550e8400-e29b-41d4-a716-446655440000",
            }
        }
    }


class TradeUpdateRequestModel(BaseModel):
    """Request model for updating an existing trade"""

    stop_loss: Optional[float] = Field(
        None, gt=0, description="Updated stop loss price"
    )
    take_profit: Optional[float] = Field(
        None, gt=0, description="Updated take profit price"
    )

    model_config = {
        "json_schema_extra": {
            "example": {"stop_loss": 44500.00, "take_profit": 46500.00}
        }
    }


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
async def get_db_manager() -> DatabaseManager:
    """Get database manager instance"""
    global _db_manager
    if _db_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service not initialized",
        )
    return _db_manager


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


def handle_trade_error(e: Exception, request_path: str) -> JSONResponse:
    """Handle trade-related errors with appropriate HTTP status codes"""
    logger.warning(
        "Trade operation error",
        error_type=type(e).__name__,
        error_code=getattr(e, "error_code", "UNKNOWN"),
        path=request_path,
        trade_id=getattr(e, "trade_id", None),
    )

    # Map error types to HTTP status codes
    if isinstance(e, TradeNotFoundError):
        status_code = status.HTTP_404_NOT_FOUND
        error_code = "TRADE_NOT_FOUND"
    elif isinstance(e, TradeValidationError):
        status_code = status.HTTP_400_BAD_REQUEST
        error_code = "VALIDATION_ERROR"
    elif isinstance(e, TradeExecutionError):
        status_code = status.HTTP_400_BAD_REQUEST
        error_code = "EXECUTION_ERROR"
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        error_code = "INTERNAL_ERROR"

    return create_error_response(
        error=type(e).__name__,
        error_code=error_code,
        message=str(e),
        status_code=status_code,
        details={"trade_id": getattr(e, "trade_id", None)},
        path=request_path,
    )


# Route handlers
@router.get(
    "",
    response_model=TradeListResponse,
    summary="List Trades",
    description="""
    Retrieve a list of trades with optional filtering and pagination.

    **Filtering Options:**
    - `symbol`: Filter by trading symbol
    - `strategy_id`: Filter by strategy ID
    - `status`: Filter by trade status (OPEN, CLOSED, CANCELLED)
    - `start_date`: Filter trades from this date (YYYY-MM-DD)
    - `end_date`: Filter trades until this date (YYYY-MM-DD)
    - `limit`: Maximum number of results (default: 100, max: 1000)

    **Returns:**
    - List of trade objects
    - Total count for pagination
    - Has more flag for pagination
    """,
    responses={
        200: {"description": "Trades retrieved successfully"},
        400: {"description": "Invalid filter parameters"},
        500: {"description": "Internal server error"},
    },
)
async def list_trades(
    symbol: Optional[str] = Query(None, description="Filter by trading symbol"),
    strategy_id: Optional[str] = Query(None, description="Filter by strategy ID"),
    status: Optional[str] = Query(None, description="Filter by trade status"),
    start_date: Optional[str] = Query(
        None, description="Start date filter (YYYY-MM-DD)"
    ),
    end_date: Optional[str] = Query(None, description="End date filter (YYYY-MM-DD)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    db_manager: DatabaseManager = Depends(get_db_manager),
) -> TradeListResponse:
    """
    List trades with filtering and pagination

    Supports advanced filtering by symbol, strategy, status, and date range
    with comprehensive pagination support.
    """
    start_time = datetime.now(timezone.utc)

    try:
        with structlog.contextvars.bound_contextvars(
            symbol=symbol,
            strategy_id=strategy_id,
            status=status,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        ):
            logger.info("Listing trades with filters")

            # Validate filters
            if status and status not in ["OPEN", "CLOSED", "CANCELLED"]:
                return create_error_response(
                    error="ValidationError",
                    error_code="INVALID_STATUS",
                    message="Status must be one of: OPEN, CLOSED, CANCELLED",
                    status_code=status.HTTP_400_BAD_REQUEST,
                    path="/api/v1/trades",
                )

            # Validate date formats
            if start_date:
                try:
                    datetime.strptime(start_date, "%Y-%m-%d")
                except ValueError:
                    return create_error_response(
                        error="ValidationError",
                        error_code="INVALID_DATE_FORMAT",
                        message="start_date must be in YYYY-MM-DD format",
                        status_code=status.HTTP_400_BAD_REQUEST,
                        path="/api/v1/trades",
                    )

            if end_date:
                try:
                    datetime.strptime(end_date, "%Y-%m-%d")
                except ValueError:
                    return create_error_response(
                        error="ValidationError",
                        error_code="INVALID_DATE_FORMAT",
                        message="end_date must be in YYYY-MM-DD format",
                        status_code=status.HTTP_400_BAD_REQUEST,
                        path="/api/v1/trades",
                    )

            # Validate date range
            if start_date and end_date:
                start = datetime.strptime(start_date, "%Y-%m-%d")
                end = datetime.strptime(end_date, "%Y-%m-%d")
                if end < start:
                    return create_error_response(
                        error="ValidationError",
                        error_code="INVALID_DATE_RANGE",
                        message="end_date must be after start_date",
                        status_code=status.HTTP_400_BAD_REQUEST,
                        path="/api/v1/trades",
                    )

            # Build query filters
            filters = {}
            if symbol:
                filters["symbol"] = symbol
            if strategy_id:
                try:
                    UUID(strategy_id)  # Validate UUID format
                    filters["strategy_id"] = strategy_id
                except ValueError:
                    return create_error_response(
                        error="ValidationError",
                        error_code="INVALID_STRATEGY_ID",
                        message="strategy_id must be a valid UUID",
                        status_code=status.HTTP_400_BAD_REQUEST,
                        path="/api/v1/trades",
                    )
            if status:
                filters["status"] = status

            # Date range filtering
            date_filters = {}
            if start_date:
                date_filters["start_date"] = start_date
            if end_date:
                date_filters["end_date"] = end_date

            # Query trades from database
            async with db_manager.get_async_session() as session:
                # Build query
                from sqlalchemy import select, and_, func
                from ...models.trade import TradeORM

                query = select(TradeORM)

                # Apply filters
                conditions = []
                if filters.get("symbol"):
                    conditions.append(TradeORM.symbol == filters["symbol"])
                if filters.get("strategy_id"):
                    conditions.append(TradeORM.strategy_id == filters["strategy_id"])
                if filters.get("status"):
                    conditions.append(TradeORM.status == filters["status"])

                # Date range filters
                if date_filters.get("start_date"):
                    start_datetime = datetime.strptime(
                        date_filters["start_date"], "%Y-%m-%d"
                    )
                    conditions.append(TradeORM.entry_timestamp >= start_datetime)
                if date_filters.get("end_date"):
                    end_datetime = datetime.strptime(
                        date_filters["end_date"], "%Y-%m-%d"
                    )
                    end_datetime = end_datetime.replace(hour=23, minute=59, second=59)
                    conditions.append(TradeORM.entry_timestamp <= end_datetime)

                if conditions:
                    query = query.where(and_(*conditions))

                # Apply ordering (newest first)
                query = query.order_by(TradeORM.created_at.desc())

                # Apply limit + 1 to check if there are more results
                query = query.limit(limit + 1)

                result = await session.execute(query)
                trade_orms = result.scalars().all()

                # Check if there are more results
                has_more = len(trade_orms) > limit
                if has_more:
                    trade_orms = trade_orms[:limit]

                # Convert to response models
                trades = []
                for trade_orm in trade_orms:
                    trade_response = TradeResponse.from_orm(trade_orm)
                    trades.append(trade_response)

                # Get total count for pagination info
                count_query = select(func.count(TradeORM.trade_id))
                if conditions:
                    count_query = count_query.where(and_(*conditions))
                count_result = await session.execute(count_query)
                total = count_result.scalar()

                response = TradeListResponse(
                    trades=trades, total=total, has_more=has_more
                )

                duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                logger.info(
                    "Trades listed successfully",
                    count=len(trades),
                    total=total,
                    has_more=has_more,
                    duration=f"{duration:.3f}s",
                )

                return response

    except Exception as e:
        logger.error("List trades error", error=str(e), exc_info=True)
        return handle_trade_error(e, "/api/v1/trades")


@router.post(
    "",
    response_model=TradeResponse,
    summary="Create Trade",
    description="""
    Create a new trade with comprehensive validation and risk management.

    **Required Fields:**
    - `symbol`: Trading symbol
    - `trade_type`: BUY or SELL
    - `quantity`: Number of shares/contracts

    **Optional Fields:**
    - `price`: Entry price (market order if not specified)
    - `stop_loss`: Stop loss price
    - `take_profit`: Take profit price
    - `strategy_id`: Associated strategy ID

    **Validation:**
    - Price relationships validation
    - Risk management checks
    - Symbol validation
    - Quantity limits

    **Returns:**
    - Complete trade object with generated ID and timestamps
    """,
    responses={
        201: {"description": "Trade created successfully"},
        400: {"description": "Invalid trade data"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"},
    },
)
async def create_trade(
    trade_data: TradeCreateRequestModel,
    db_manager: DatabaseManager = Depends(get_db_manager),
) -> TradeResponse:
    """
    Create a new trade with comprehensive validation

    Performs extensive validation including price relationships,
    risk management checks, and market data validation.
    """
    start_time = datetime.now(timezone.utc)

    try:
        with structlog.contextvars.bound_contextvars(
            symbol=trade_data.symbol,
            trade_type=trade_data.trade_type,
            quantity=trade_data.quantity,
            strategy_id=trade_data.strategy_id,
        ):
            logger.info("Creating new trade")

            # Validate trade_type
            if trade_data.trade_type not in ["BUY", "SELL"]:
                return create_error_response(
                    error="ValidationError",
                    error_code="INVALID_TRADE_TYPE",
                    message="trade_type must be BUY or SELL",
                    status_code=status.HTTP_400_BAD_REQUEST,
                    path="/api/v1/trades",
                )

            # Validate strategy_id if provided
            if trade_data.strategy_id:
                try:
                    UUID(trade_data.strategy_id)
                except ValueError:
                    return create_error_response(
                        error="ValidationError",
                        error_code="INVALID_STRATEGY_ID",
                        message="strategy_id must be a valid UUID",
                        status_code=status.HTTP_400_BAD_REQUEST,
                        path="/api/v1/trades",
                    )

            # For market orders, we need to get current market price
            # This is a placeholder - in real implementation, integrate with broker APIs
            entry_price = trade_data.price
            if entry_price is None:
                # Market order - get current price from market data
                # Placeholder implementation
                entry_price = 45000.50  # This should come from real market data

            # Set default stop loss and take profit if not provided
            stop_loss = trade_data.stop_loss
            take_profit = trade_data.take_profit

            if stop_loss is None:
                # Default stop loss: 2% below entry for BUY, 2% above for SELL
                if trade_data.trade_type == "BUY":
                    stop_loss = entry_price * 0.98
                else:  # SELL
                    stop_loss = entry_price * 1.02

            if take_profit is None:
                # Default take profit: 2% above entry for BUY, 2% below for SELL
                if trade_data.trade_type == "BUY":
                    take_profit = entry_price * 1.02
                else:  # SELL
                    take_profit = entry_price * 0.98

            # Create trade request object
            trade_request = TradeCreateRequest(
                user_id="system",  # This should come from authentication context
                strategy_id=trade_data.strategy_id or "manual",
                symbol=trade_data.symbol,
                trade_type=TradeType(trade_data.trade_type),
                quantity=trade_data.quantity,
                entry_price=entry_price,
                initial_stop_loss=stop_loss,
                take_profit_target=take_profit,
                is_paper_trade=True,  # Default to paper trading
                broker=BrokerType.PAPER,
            )

            # Create trade object
            trade = Trade(
                user_id=trade_request.user_id,
                strategy_id=trade_request.strategy_id,
                symbol=trade_request.symbol,
                trade_type=trade_request.trade_type,
                quantity=trade_request.quantity,
                entry_price=trade_request.entry_price,
                initial_stop_loss=trade_request.initial_stop_loss,
                take_profit_target=trade_request.take_profit_target,
                is_paper_trade=trade_request.is_paper_trade,
                broker=trade_request.broker,
                transaction_cost=trade_request.transaction_cost,
            )

            # Validate trade
            trade.validate()

            # Save to database
            async with db_manager.get_async_session() as session:
                from ...models.trade import TradeORM

                # Convert to ORM object
                trade_orm = TradeORM(
                    user_id=trade.user_id,
                    strategy_id=trade.strategy_id,
                    symbol=trade.symbol,
                    trade_type=trade.trade_type.value,
                    quantity=trade.quantity,
                    entry_price=trade.entry_price,
                    entry_timestamp=trade.entry_timestamp,
                    initial_stop_loss=trade.initial_stop_loss,
                    current_stop_loss=trade.current_stop_loss,
                    take_profit_target=trade.take_profit_target,
                    transaction_cost=trade.transaction_cost,
                    is_paper_trade=trade.is_paper_trade,
                    broker=trade.broker.value,
                    status=trade.status.value,
                    notes=trade.notes,
                    created_at=trade.created_at,
                    updated_at=trade.updated_at,
                )

                # Save to database
                session.add(trade_orm)
                await session.commit()
                await session.refresh(trade_orm)

                # Convert back to response model
                trade_response = TradeResponse.from_orm(trade_orm)

                duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                logger.info(
                    "Trade created successfully",
                    trade_id=trade_response.trade_id,
                    symbol=trade_response.symbol,
                    duration=f"{duration:.3f}s",
                )

                return trade_response

    except TradeValidationError as e:
        logger.warning("Trade validation error", error=str(e))
        return create_error_response(
            error="ValidationError",
            error_code="TRADE_VALIDATION_FAILED",
            message=str(e),
            status_code=status.HTTP_400_BAD_REQUEST,
            path="/api/v1/trades",
        )
    except Exception as e:
        logger.error("Create trade error", error=str(e), exc_info=True)
        return handle_trade_error(e, "/api/v1/trades")


@router.get(
    "/{trade_id}",
    response_model=TradeResponse,
    summary="Get Trade",
    description="""
    Retrieve detailed information about a specific trade.

    **Path Parameters:**
    - `trade_id`: UUID of the trade to retrieve

    **Returns:**
    - Complete trade object with all details
    - P&L calculations if trade is closed
    - Risk metrics and performance data
    """,
    responses={
        200: {"description": "Trade retrieved successfully"},
        404: {"description": "Trade not found"},
        422: {"description": "Invalid trade ID format"},
        500: {"description": "Internal server error"},
    },
)
async def get_trade(
    trade_id: str, db_manager: DatabaseManager = Depends(get_db_manager)
) -> TradeResponse:
    """
    Get detailed information about a specific trade

    Retrieves complete trade information including P&L calculations
    and risk metrics.
    """
    start_time = datetime.now(timezone.utc)

    try:
        with structlog.contextvars.bound_contextvars(trade_id=trade_id):
            logger.info("Retrieving trade details")

            # Validate UUID format
            try:
                UUID(trade_id)
            except ValueError:
                return create_error_response(
                    error="ValidationError",
                    error_code="INVALID_TRADE_ID",
                    message="trade_id must be a valid UUID",
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    path=f"/api/v1/trades/{trade_id}",
                )

            # Query trade from database
            async with db_manager.get_async_session() as session:
                from sqlalchemy import select
                from ...models.trade import TradeORM

                query = select(TradeORM).where(TradeORM.trade_id == trade_id)
                result = await session.execute(query)
                trade_orm = result.scalar_one_or_none()

                if not trade_orm:
                    raise TradeNotFoundError(trade_id)

                # Convert to response model
                trade_response = TradeResponse.from_orm(trade_orm)

                duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                logger.info(
                    "Trade retrieved successfully",
                    trade_id=trade_id,
                    symbol=trade_response.symbol,
                    status=trade_response.status,
                    duration=f"{duration:.3f}s",
                )

                return trade_response

    except TradeNotFoundError:
        return create_error_response(
            error="NotFoundError",
            error_code="TRADE_NOT_FOUND",
            message=f"Trade with ID {trade_id} not found",
            status_code=status.HTTP_404_NOT_FOUND,
            path=f"/api/v1/trades/{trade_id}",
        )
    except Exception as e:
        logger.error("Get trade error", error=str(e), exc_info=True)
        return handle_trade_error(e, f"/api/v1/trades/{trade_id}")


@router.patch(
    "/{trade_id}",
    response_model=TradeResponse,
    summary="Update Trade",
    description="""
    Update trade parameters (stop loss and take profit levels).

    **Path Parameters:**
    - `trade_id`: UUID of the trade to update

    **Updateable Fields:**
    - `stop_loss`: Update stop loss price
    - `take_profit`: Update take profit price

    **Validation:**
    - Only OPEN trades can be updated
    - Price relationship validation
    - Risk management checks

    **Returns:**
    - Updated trade object
    """,
    responses={
        200: {"description": "Trade updated successfully"},
        400: {"description": "Invalid update data"},
        404: {"description": "Trade not found"},
        409: {"description": "Trade cannot be updated (closed/cancelled)"},
        422: {"description": "Invalid trade ID format"},
        500: {"description": "Internal server error"},
    },
)
async def update_trade(
    trade_id: str,
    update_data: TradeUpdateRequestModel,
    db_manager: DatabaseManager = Depends(get_db_manager),
) -> TradeResponse:
    """
    Update trade parameters (stop loss and take profit)

    Allows updating risk management parameters for open trades
    with comprehensive validation.
    """
    start_time = datetime.now(timezone.utc)

    try:
        with structlog.contextvars.bound_contextvars(
            trade_id=trade_id,
            stop_loss=update_data.stop_loss,
            take_profit=update_data.take_profit,
        ):
            logger.info("Updating trade parameters")

            # Validate UUID format
            try:
                UUID(trade_id)
            except ValueError:
                return create_error_response(
                    error="ValidationError",
                    error_code="INVALID_TRADE_ID",
                    message="trade_id must be a valid UUID",
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    path=f"/api/v1/trades/{trade_id}",
                )

            # Validate update data
            if not update_data.stop_loss and not update_data.take_profit:
                return create_error_response(
                    error="ValidationError",
                    error_code="NO_UPDATE_DATA",
                    message="At least one field (stop_loss or take_profit) must be provided",
                    status_code=status.HTTP_400_BAD_REQUEST,
                    path=f"/api/v1/trades/{trade_id}",
                )

            # Query and update trade
            async with db_manager.get_async_session() as session:
                from sqlalchemy import select
                from ...models.trade import TradeORM

                query = select(TradeORM).where(TradeORM.trade_id == trade_id)
                result = await session.execute(query)
                trade_orm = result.scalar_one_or_none()

                if not trade_orm:
                    raise TradeNotFoundError(trade_id)

                # Check if trade can be updated
                if trade_orm.status != "OPEN":
                    return create_error_response(
                        error="ValidationError",
                        error_code="TRADE_NOT_UPDATEABLE",
                        message=f"Cannot update trade with status {trade_orm.status}",
                        status_code=status.HTTP_409_CONFLICT,
                        path=f"/api/v1/trades/{trade_id}",
                    )

                # Validate price relationships
                entry_price = float(trade_orm.entry_price)
                trade_type = trade_orm.trade_type

                if update_data.stop_loss is not None:
                    if trade_type == "BUY" and update_data.stop_loss >= entry_price:
                        return create_error_response(
                            error="ValidationError",
                            error_code="INVALID_STOP_LOSS",
                            message="Stop loss must be below entry price for BUY trades",
                            status_code=status.HTTP_400_BAD_REQUEST,
                            path=f"/api/v1/trades/{trade_id}",
                        )
                    elif trade_type == "SELL" and update_data.stop_loss <= entry_price:
                        return create_error_response(
                            error="ValidationError",
                            error_code="INVALID_STOP_LOSS",
                            message="Stop loss must be above entry price for SELL trades",
                            status_code=status.HTTP_400_BAD_REQUEST,
                            path=f"/api/v1/trades/{trade_id}",
                        )

                if update_data.take_profit is not None:
                    if trade_type == "BUY" and update_data.take_profit <= entry_price:
                        return create_error_response(
                            error="ValidationError",
                            error_code="INVALID_TAKE_PROFIT",
                            message="Take profit must be above entry price for BUY trades",
                            status_code=status.HTTP_400_BAD_REQUEST,
                            path=f"/api/v1/trades/{trade_id}",
                        )
                    elif (
                        trade_type == "SELL" and update_data.take_profit >= entry_price
                    ):
                        return create_error_response(
                            error="ValidationError",
                            error_code="INVALID_TAKE_PROFIT",
                            message="Take profit must be below entry price for SELL trades",
                            status_code=status.HTTP_400_BAD_REQUEST,
                            path=f"/api/v1/trades/{trade_id}",
                        )

                # Update trade
                update_dict = {}
                if update_data.stop_loss is not None:
                    update_dict["current_stop_loss"] = update_data.stop_loss
                if update_data.take_profit is not None:
                    update_dict["take_profit_target"] = update_data.take_profit

                update_dict["updated_at"] = datetime.now(timezone.utc)

                # Apply updates
                for key, value in update_dict.items():
                    setattr(trade_orm, key, value)

                # Commit changes
                await session.commit()
                await session.refresh(trade_orm)

                # Convert to response model
                trade_response = TradeResponse.from_orm(trade_orm)

                duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                logger.info(
                    "Trade updated successfully",
                    trade_id=trade_id,
                    symbol=trade_response.symbol,
                    duration=f"{duration:.3f}s",
                )

                return trade_response

    except TradeNotFoundError:
        return create_error_response(
            error="NotFoundError",
            error_code="TRADE_NOT_FOUND",
            message=f"Trade with ID {trade_id} not found",
            status_code=status.HTTP_404_NOT_FOUND,
            path=f"/api/v1/trades/{trade_id}",
        )
    except Exception as e:
        logger.error("Update trade error", error=str(e), exc_info=True)
        return handle_trade_error(e, f"/api/v1/trades/{trade_id}")


# Initialization functions
def init_trade_routes(
    db_manager: DatabaseManager, cache_manager: Optional[CacheManager] = None
) -> APIRouter:
    """
    Initialize trade routes with required services

    Args:
        db_manager: Database manager instance
        cache_manager: Optional cache manager instance

    Returns:
        Configured FastAPI router
    """
    global _db_manager, _cache_manager

    try:
        # Store service instances
        _db_manager = db_manager
        _cache_manager = cache_manager

        logger.info("Trade routes initialized successfully")
        return router

    except Exception as e:
        logger.error("Failed to initialize trade routes", error=str(e))
        raise


# Export router and initialization function
__all__ = [
    "router",
    "init_trade_routes",
    "TradeListResponse",
    "TradeCreateRequestModel",
    "TradeUpdateRequestModel",
    "ErrorResponse",
]
