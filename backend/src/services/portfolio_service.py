"""
Portfolio Service for NIRAJ Trading System

Provides comprehensive portfolio management including position tracking,
P&L calculations, risk management, and performance analytics.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple, TypedDict, cast

from sqlalchemy import select, and_, desc
import structlog  # type: ignore[import-untyped]

from ..core.database import DatabaseManager
from ..core.cache import CacheManager
from ..models.portfolio import (
    Portfolio,
    PortfolioORM,
    PortfolioCreateRequest,
    PortfolioUpdateRequest,
    PortfolioResponse,
    PortfolioAggregateResponse,
    PortfolioNotFoundError,
    PositionType,
    PositionStatus,
    RiskLevel,
    calculate_portfolio_summary,
)

logger = structlog.get_logger(__name__)


class PortfolioServiceError(Exception):
    """Base exception for portfolio service errors

    Args:
        message: Human readable error message
        portfolio_id: Optional related portfolio identifier
        error_code: Optional machine readable error code
    """

    def __init__(
        self,
        message: str,
        portfolio_id: Optional[str] = None,
        error_code: Optional[str] = None,
    ) -> None:
        self.message: str = message
        self.portfolio_id: Optional[str] = portfolio_id
        self.error_code: Optional[str] = error_code
        super().__init__(self.message)


# ----- Typed result contracts (improve Pylance precision & edge clarity) ----- #
class UpdatedPosition(TypedDict):
    portfolio_id: str
    symbol: str
    old_price: float
    new_price: float
    pnl_change: float


class PriceUpdateSummary(TypedDict):
    updated_positions_count: int
    total_pnl_change: float
    updated_positions: List[UpdatedPosition]
    affected_users: List[str]


class ClosePositionResult(TypedDict):
    portfolio_id: str
    symbol: str
    close_price: float
    realized_pnl: float
    total_pnl: float
    reason: Optional[str]
    closed_at: str


class RiskValidationResult(TypedDict):
    is_valid: bool
    violations: List[Any]
    total_positions: int
    validated_at: str


# Generic type variables/helpers
TPortfolioCache = Tuple[List[PortfolioResponse], PortfolioAggregateResponse]
_PortfolioTuple = Tuple[List[PortfolioResponse], PortfolioAggregateResponse]


class PortfolioService:
    """
    Comprehensive portfolio management service

    Handles all portfolio-related operations including:
    - Position management and tracking
    - P&L calculations and updates
    - Risk management and validation
    - Performance analytics
    - Real-time price updates
    - Portfolio aggregation and reporting
    """

    def __init__(self, db_manager: DatabaseManager, cache_manager: CacheManager):
        self.db_manager = db_manager
        self.cache_manager = cache_manager

        # Cache keys
        self._portfolio_cache_prefix = "portfolio:"
        self._user_portfolio_cache_prefix = "user_portfolio:"
        self._portfolio_summary_cache_prefix = "portfolio_summary:"

    async def get_user_portfolio(
        self, user_id: str, include_inactive: bool = False
    ) -> _PortfolioTuple:
        """
        Get complete user portfolio with positions and summary

        Args:
            user_id: User ID to get portfolio for
            include_inactive: Whether to include inactive positions

        Returns:
            Tuple of (positions list, portfolio summary)

        Raises:
            PortfolioServiceError: If retrieval fails
        """
        try:
            # Check cache first
            cache_key = f"{self._user_portfolio_cache_prefix}{user_id}:{include_inactive}"
            cached_any = await self.cache_manager.get(cache_key)
            if isinstance(cached_any, tuple) and len(cached_any) == 2:
                poss, summ = cached_any
                if isinstance(poss, list):
                    logger.debug("Portfolio retrieved from cache", user_id=user_id)
                    return cast(_PortfolioTuple, cached_any)

            # Use async session for proper non-blocking IO
            async with self.db_manager.get_async_session() as session:  # type: ignore[attr-defined]
                # Build query
                query = select(PortfolioORM).where(PortfolioORM.user_id == user_id)

                if not include_inactive:
                    query = query.where(
                        PortfolioORM.position_status == PositionStatus.ACTIVE.value
                    )

                query = query.order_by(desc(PortfolioORM.last_updated))

                exec_result = await session.execute(query)
                portfolio_orms = exec_result.scalars().all()

                # Convert to business objects
                portfolios = []
                for orm in portfolio_orms:
                    try:
                        portfolio = self._orm_to_portfolio(orm)
                        portfolios.append(portfolio)
                    except Exception as e:
                        logger.warning(
                            "Failed to convert portfolio ORM",
                            portfolio_id=orm.portfolio_id,
                            error=str(e),
                        )
                        continue

                # Convert to response models
                portfolio_responses = [
                    PortfolioResponse.from_orm(portfolio) for portfolio in portfolios
                ]

                # Calculate summary
                summary_data = calculate_portfolio_summary(portfolios)
                summary_response = PortfolioAggregateResponse(**summary_data)

                # Cache result
                result_data = (portfolio_responses, summary_response)
                await self.cache_manager.set(
                    cache_key, result_data, ttl=300  # 5 minutes
                )

                logger.info(
                    "Portfolio retrieved successfully",
                    user_id=user_id,
                    positions_count=len(portfolio_responses),
                )

                return result_data

        except Exception as e:
            logger.error("Failed to get user portfolio", user_id=user_id, error=str(e))
            raise PortfolioServiceError(
                f"Failed to retrieve portfolio: {str(e)}", error_code="RETRIEVAL_FAILED"
            )

    async def get_portfolio_position(self, portfolio_id: str) -> PortfolioResponse:
        """
        Get specific portfolio position by ID

        Args:
            portfolio_id: Portfolio position ID

        Returns:
            Portfolio position details

        Raises:
            PortfolioNotFoundError: If position not found
            PortfolioServiceError: If retrieval fails
        """
        try:
            # Check cache first
            cache_key = f"{self._portfolio_cache_prefix}{portfolio_id}"
            cached_result = await self.cache_manager.get(cache_key)
            if cached_result:
                logger.debug(
                    "Portfolio position retrieved from cache", portfolio_id=portfolio_id
                )
                return cached_result

            async with self.db_manager.get_async_session() as session:  # type: ignore[attr-defined]
                query = select(PortfolioORM).where(
                    PortfolioORM.portfolio_id == portfolio_id
                )
                sql_result = await session.execute(query)
                portfolio_orm = sql_result.scalar_one_or_none()

                if not portfolio_orm:
                    raise PortfolioNotFoundError(portfolio_id)

                # Convert to business object and response
                portfolio = self._orm_to_portfolio(portfolio_orm)
                portfolio_response = PortfolioResponse.from_orm(portfolio)

                # Cache result
                await self.cache_manager.set(
                    cache_key, portfolio_response, ttl=300  # 5 minutes
                )

                logger.info("Portfolio position retrieved", portfolio_id=portfolio_id)
                return portfolio_response

        except PortfolioNotFoundError:
            raise
        except Exception as e:
            logger.error(
                "Failed to get portfolio position",
                portfolio_id=portfolio_id,
                error=str(e),
            )
            raise PortfolioServiceError(
                f"Failed to retrieve portfolio position: {str(e)}",
                portfolio_id=portfolio_id,
                error_code="POSITION_RETRIEVAL_FAILED",
            )

    async def create_portfolio_position(
        self, create_request: PortfolioCreateRequest
    ) -> PortfolioResponse:
        """
        Create a new portfolio position

        Args:
            create_request: Validated portfolio creation data

        Returns:
            Created portfolio position

        Raises:
            PortfolioServiceError: If creation fails
        """
        try:
            async with self.db_manager.get_async_session() as session:  # type: ignore[attr-defined]
                # Create portfolio business object
                portfolio = Portfolio(
                    user_id=create_request.user_id,
                    symbol=create_request.symbol,
                    quantity=create_request.quantity,
                    average_price=create_request.average_price,
                    current_price=create_request.current_price,
                    margin_used=create_request.margin_used,
                    associated_strategies=create_request.associated_strategies,
                    is_paper_position=create_request.is_paper_position,
                    stop_loss_level=create_request.stop_loss_level,
                    take_profit_level=create_request.take_profit_level,
                    risk_level=create_request.risk_level,
                    notes=create_request.notes,
                )

                # Convert to ORM and save
                portfolio_orm = self._portfolio_to_orm(portfolio)
                session.add(portfolio_orm)
                await session.commit()
                await session.refresh(portfolio_orm)

                # Convert back to response
                created_portfolio = self._orm_to_portfolio(portfolio_orm)
                portfolio_response = PortfolioResponse.from_orm(created_portfolio)

                # Invalidate cache
                await self._invalidate_user_portfolio_cache(create_request.user_id)

                logger.info(
                    "Portfolio position created",
                    portfolio_id=portfolio.portfolio_id,
                    user_id=create_request.user_id,
                    symbol=create_request.symbol,
                )

                return portfolio_response

        except Exception as e:
            logger.error(
                "Failed to create portfolio position",
                user_id=create_request.user_id,
                symbol=create_request.symbol,
                error=str(e),
            )
            raise PortfolioServiceError(
                f"Failed to create portfolio position: {str(e)}",
                error_code="CREATION_FAILED",
            )

    async def update_portfolio_position(
        self, portfolio_id: str, update_request: PortfolioUpdateRequest
    ) -> PortfolioResponse:
        """
        Update an existing portfolio position

        Args:
            portfolio_id: Portfolio position ID
            update_request: Validated update data

        Returns:
            Updated portfolio position

        Raises:
            PortfolioNotFoundError: If position not found
            PortfolioServiceError: If update fails
        """
        try:
            async with self.db_manager.get_async_session() as session:  # type: ignore[attr-defined]
                # Get existing position
                query = select(PortfolioORM).where(
                    PortfolioORM.portfolio_id == portfolio_id
                )
                sql_result = await session.execute(query)
                portfolio_orm = sql_result.scalar_one_or_none()

                if not portfolio_orm:
                    raise PortfolioNotFoundError(portfolio_id)

                # Convert to business object
                portfolio = self._orm_to_portfolio(portfolio_orm)

                # Apply updates
                update_data = update_request.dict(exclude_unset=True)
                for field, value in update_data.items():
                    if hasattr(portfolio, field):
                        setattr(portfolio, field, value)

                # Validate and recalculate
                portfolio.validate()
                portfolio.update_calculated_fields()

                # Update ORM
                updated_orm = self._portfolio_to_orm(portfolio)
                await session.merge(updated_orm)
                await session.commit()

                # Convert to response
                portfolio_response = PortfolioResponse.from_orm(portfolio)

                # Invalidate caches
                await self._invalidate_portfolio_cache(portfolio_id)
                await self._invalidate_user_portfolio_cache(portfolio.user_id)

                logger.info(
                    "Portfolio position updated",
                    portfolio_id=portfolio_id,
                    symbol=portfolio.symbol,
                )

                return portfolio_response

        except PortfolioNotFoundError:
            raise
        except Exception as e:
            logger.error(
                "Failed to update portfolio position",
                portfolio_id=portfolio_id,
                error=str(e),
            )
            raise PortfolioServiceError(
                f"Failed to update portfolio position: {str(e)}",
                portfolio_id=portfolio_id,
                error_code="UPDATE_FAILED",
            )

    async def update_position_prices(
        self, price_updates: Dict[str, Decimal]
    ) -> PriceUpdateSummary:
        """
        Update current prices for multiple symbols and recalculate P&L

        Args:
            price_updates: Dict mapping symbols to new prices

        Returns:
            Update summary with affected positions

        Raises:
            PortfolioServiceError: If update fails
        """
        try:
            updated_positions = []
            total_pnl_change = Decimal("0")

            async with self.db_manager.get_async_session() as session:  # type: ignore[attr-defined]
                for symbol, new_price in price_updates.items():
                    # Get all active positions for this symbol
                    query = select(PortfolioORM).where(
                        and_(
                            PortfolioORM.symbol == symbol,
                            PortfolioORM.position_status == PositionStatus.ACTIVE.value,
                        )
                    )
                    sql_result = await session.execute(query)
                    position_orms = sql_result.scalars().all()

                    for orm in position_orms:
                        portfolio = self._orm_to_portfolio(orm)

                        # Update price and recalculate
                        update_result = portfolio.update_price(new_price)
                        total_pnl_change += Decimal(str(update_result["pnl_change"]))

                        # Update ORM
                        updated_orm = self._portfolio_to_orm(portfolio)
                        await session.merge(updated_orm)

                        updated_positions.append(
                            UpdatedPosition(
                                portfolio_id=portfolio.portfolio_id,
                                symbol=symbol,
                                old_price=float(update_result["old_price"]),
                                new_price=float(update_result["new_price"]),
                                pnl_change=float(update_result["pnl_change"]),
                            )
                        )

                await session.commit()

                # Invalidate affected user caches
                affected_users = set()
                for position in updated_positions:
                    # Get user_id for cache invalidation
                    portfolio_response = await self.get_portfolio_position(
                        position["portfolio_id"]
                    )
                    affected_users.add(portfolio_response.user_id)

                for user_id in affected_users:
                    await self._invalidate_user_portfolio_cache(user_id)

                result: PriceUpdateSummary = {
                    "updated_positions_count": len(updated_positions),
                    "total_pnl_change": float(total_pnl_change),
                    "updated_positions": updated_positions,  # type: ignore[arg-type]
                    "affected_users": list(affected_users),
                }

                logger.info(
                    "Position prices updated",
                    symbols=list(price_updates.keys()),
                    updated_positions=len(updated_positions),
                    total_pnl_change=float(total_pnl_change),
                )

                return result

        except Exception as e:
            logger.error(
                "Failed to update position prices",
                symbols=list(price_updates.keys()),
                error=str(e),
            )
            raise PortfolioServiceError(
                f"Failed to update position prices: {str(e)}",
                error_code="PRICE_UPDATE_FAILED",
            )

    async def close_portfolio_position(
        self, portfolio_id: str, close_price: Decimal, reason: Optional[str] = None
    ) -> ClosePositionResult:
        """
        Close a portfolio position

        Args:
            portfolio_id: Portfolio position ID
            close_price: Closing price
            reason: Optional reason for closing

        Returns:
            Close operation result

        Raises:
            PortfolioNotFoundError: If position not found
            PortfolioServiceError: If close fails
        """
        try:
            async with self.db_manager.get_async_session() as session:  # type: ignore[attr-defined]
                # Get position
                query = select(PortfolioORM).where(
                    PortfolioORM.portfolio_id == portfolio_id
                )
                sql_result = await session.execute(query)
                portfolio_orm = sql_result.scalar_one_or_none()

                if not portfolio_orm:
                    raise PortfolioNotFoundError(portfolio_id)

                # Convert to business object
                portfolio = self._orm_to_portfolio(portfolio_orm)

                # Close position
                realized_pnl = portfolio.close_position(close_price, reason or "")

                # Update ORM
                updated_orm = self._portfolio_to_orm(portfolio)
                await session.merge(updated_orm)
                await session.commit()

                # Invalidate caches
                await self._invalidate_portfolio_cache(portfolio_id)
                await self._invalidate_user_portfolio_cache(portfolio.user_id)

                result: ClosePositionResult = {
                    "portfolio_id": portfolio_id,
                    "symbol": portfolio.symbol,
                    "close_price": float(close_price),
                    "realized_pnl": float(realized_pnl),
                    "total_pnl": float(portfolio.total_pnl),
                    "reason": reason,
                    "closed_at": portfolio.last_updated.isoformat(),
                }

                logger.info(
                    "Portfolio position closed",
                    portfolio_id=portfolio_id,
                    symbol=portfolio.symbol,
                    realized_pnl=float(realized_pnl),
                )

                return result

        except PortfolioNotFoundError:
            raise
        except Exception as e:
            logger.error(
                "Failed to close portfolio position",
                portfolio_id=portfolio_id,
                error=str(e),
            )
            raise PortfolioServiceError(
                f"Failed to close portfolio position: {str(e)}",
                portfolio_id=portfolio_id,
                error_code="CLOSE_FAILED",
            )

    async def get_portfolio_summary(
        self, user_id: str, include_inactive: bool = False
    ) -> PortfolioAggregateResponse:
        """
        Get portfolio summary statistics

        Args:
            user_id: User ID
            include_inactive: Whether to include inactive positions

        Returns:
            Portfolio summary statistics

        Raises:
            PortfolioServiceError: If summary calculation fails
        """
        try:
            # Check cache first
            cache_key = (
                f"{self._portfolio_summary_cache_prefix}{user_id}:{include_inactive}"
            )
            cached_result = await self.cache_manager.get(cache_key)
            if cached_result:
                logger.debug("Portfolio summary retrieved from cache", user_id=user_id)
                return cached_result

            # Get full portfolio
            positions, summary = await self.get_user_portfolio(
                user_id, include_inactive
            )

            # Cache summary
            await self.cache_manager.set(cache_key, summary, ttl=300)  # 5 minutes

            return summary

        except Exception as e:
            logger.error(
                "Failed to get portfolio summary", user_id=user_id, error=str(e)
            )
            raise PortfolioServiceError(
                f"Failed to get portfolio summary: {str(e)}",
                error_code="SUMMARY_FAILED",
            )

    async def validate_portfolio_risks(self, user_id: str) -> RiskValidationResult:
        """
        Validate portfolio against risk management rules

        Args:
            user_id: User ID

        Returns:
            Risk validation results

        Raises:
            PortfolioServiceError: If validation fails
        """
        try:
            # Get portfolio positions
            positions, _ = await self.get_user_portfolio(user_id)

            # Convert to business objects for validation
            portfolio_objects = []
            for pos in positions:
                portfolio_objects.append(
                    Portfolio(
                        portfolio_id=pos.portfolio_id,
                        user_id=pos.user_id,
                        symbol=pos.symbol,
                        quantity=pos.quantity,
                        average_price=pos.average_price,
                        current_price=pos.current_price,
                        margin_used=pos.margin_used,
                        associated_strategies=pos.associated_strategies,
                        is_paper_position=pos.is_paper_position,
                        stop_loss_level=pos.stop_loss_level,
                        take_profit_level=pos.take_profit_level,
                        risk_level=pos.risk_level,
                        notes=pos.notes,
                        first_entry=pos.first_entry,
                        last_updated=pos.last_updated,
                        position_type=pos.position_type,
                        position_status=pos.position_status,
                        daily_pnl=pos.daily_pnl,
                        max_profit=pos.max_profit,
                        max_loss=pos.max_loss,
                        days_held=pos.days_held,
                        created_at=pos.created_at,
                    )
                )

            # Import risk validation function
            from ..models.portfolio import validate_portfolio_risk_limits

            # Define risk limits (these could be configurable)
            max_total_risk = Decimal("50000")  # $50,000 max total risk
            max_position_concentration = 0.2  # 20% max per position
            max_sector_concentration = 0.5  # 50% max per sector

            violations = validate_portfolio_risk_limits(
                portfolio_objects,
                max_total_risk,
                max_position_concentration,
                max_sector_concentration,
            )

            result: RiskValidationResult = {
                "is_valid": len(violations) == 0,
                "violations": cast(List[Any], violations),
                "total_positions": len(portfolio_objects),
                "validated_at": datetime.now(timezone.utc).isoformat(),
            }

            logger.info(
                "Portfolio risk validation completed",
                user_id=user_id,
                violations_count=len(violations),
                is_valid=result["is_valid"],
            )

            return result

        except Exception as e:
            logger.error(
                "Failed to validate portfolio risks", user_id=user_id, error=str(e)
            )
            raise PortfolioServiceError(
                f"Failed to validate portfolio risks: {str(e)}",
                error_code="RISK_VALIDATION_FAILED",
            )

    def _orm_to_portfolio(self, orm: PortfolioORM) -> Portfolio:
        """Convert ORM object to business Portfolio object"""
        # Cast SQLAlchemy instrumented attributes for type checkers. At runtime these are plain values.
        # Helper casts for SQLAlchemy attributes (instrumented) to satisfy type checker
        stop_loss_val = getattr(orm, "stop_loss_level")
        take_profit_val = getattr(orm, "take_profit_level")
        portfolio = Portfolio(
            portfolio_id=str(getattr(orm, "portfolio_id")),
            user_id=str(getattr(orm, "user_id")),
            symbol=str(getattr(orm, "symbol")),
            quantity=int(getattr(orm, "quantity")),
            average_price=Decimal(str(orm.average_price)),
            current_price=Decimal(str(orm.current_price)),
            market_value=Decimal(str(orm.market_value)),
            unrealized_pnl=Decimal(str(orm.unrealized_pnl)),
            realized_pnl=Decimal(str(orm.realized_pnl)),
            total_pnl=Decimal(str(orm.total_pnl)),
            position_risk=Decimal(str(orm.position_risk)),
            margin_used=Decimal(str(orm.margin_used)),
            first_entry=getattr(orm, "first_entry"),  # datetime
            last_updated=getattr(orm, "last_updated"),  # datetime
            associated_strategies=list(getattr(orm, "associated_strategies") or []),
            is_paper_position=bool(getattr(orm, "is_paper_position")),
            position_type=PositionType(orm.position_type),
            position_status=PositionStatus(orm.position_status),
            stop_loss_level=Decimal(str(stop_loss_val)) if stop_loss_val is not None else None,
            take_profit_level=Decimal(str(take_profit_val)) if take_profit_val is not None else None,
            risk_level=RiskLevel(orm.risk_level),
            daily_pnl=Decimal(str(orm.daily_pnl)),
            max_profit=Decimal(str(orm.max_profit)),
            max_loss=Decimal(str(orm.max_loss)),
            days_held=int(getattr(orm, "days_held")),
            notes=getattr(orm, "notes"),
            created_at=getattr(orm, "created_at"),
        )
        return portfolio

    def _portfolio_to_orm(self, portfolio: Portfolio) -> PortfolioORM:
        """Convert Portfolio object to ORM object"""
        return PortfolioORM(
            portfolio_id=portfolio.portfolio_id,
            user_id=portfolio.user_id,
            symbol=portfolio.symbol,
            quantity=portfolio.quantity,
            average_price=float(portfolio.average_price),
            current_price=float(portfolio.current_price),
            market_value=float(portfolio.market_value),
            unrealized_pnl=float(portfolio.unrealized_pnl),
            realized_pnl=float(portfolio.realized_pnl),
            total_pnl=float(portfolio.total_pnl),
            position_risk=float(portfolio.position_risk),
            margin_used=float(portfolio.margin_used),
            first_entry=portfolio.first_entry,
            last_updated=portfolio.last_updated,
            associated_strategies=portfolio.associated_strategies,
            is_paper_position=portfolio.is_paper_position,
            position_type=portfolio.position_type.value,
            position_status=portfolio.position_status.value,
            stop_loss_level=(
                float(portfolio.stop_loss_level) if portfolio.stop_loss_level else None
            ),
            take_profit_level=(
                float(portfolio.take_profit_level)
                if portfolio.take_profit_level
                else None
            ),
            risk_level=portfolio.risk_level.value,
            daily_pnl=float(portfolio.daily_pnl),
            max_profit=float(portfolio.max_profit),
            max_loss=float(portfolio.max_loss),
            days_held=portfolio.days_held,
            notes=portfolio.notes,
            created_at=portfolio.created_at,
        )

    async def _invalidate_portfolio_cache(self, portfolio_id: str) -> None:
        """Invalidate portfolio-specific cache"""
        cache_key = f"{self._portfolio_cache_prefix}{portfolio_id}"
        await self.cache_manager.delete(cache_key)

    async def _invalidate_user_portfolio_cache(self, user_id: str) -> None:
        """Invalidate user portfolio cache for all variants"""
        cache_keys = [
            f"{self._user_portfolio_cache_prefix}{user_id}:True",
            f"{self._user_portfolio_cache_prefix}{user_id}:False",
            f"{self._portfolio_summary_cache_prefix}{user_id}:True",
            f"{self._portfolio_summary_cache_prefix}{user_id}:False",
        ]
        for key in cache_keys:
            await self.cache_manager.delete(key)


# Export all classes and functions
__all__ = ["PortfolioService", "PortfolioServiceError"]
