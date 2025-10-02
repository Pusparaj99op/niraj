"""
Strategy Service for NIRAJ Trading System

Provides comprehensive strategy management including CRUD operations,
validation, backtesting, and performance tracking.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Dict, Any, List, Optional, Tuple

from sqlalchemy import select, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from ..core.database import DatabaseManager
from ..core.cache import CacheManager
from ..models.strategy import (
    Strategy,
    StrategyORM,
    StrategyCreateRequest,
    StrategyUpdateRequest,
    StrategyResponse,
    StrategyCategory,
    StrategyNotFoundError,
    validate_strategy_name_availability,
)
from ..models.backtest import (
    BacktestRequest,
    BacktestResult,
    BacktestConfiguration,
    BacktestEngine,
    validate_backtest_request,
    BacktestExecutionError,
)
from ..ai.gemma3_integration import Gemma3Client

logger = structlog.get_logger(__name__)


class StrategyServiceError(Exception):
    """Base exception for strategy service errors"""

    def __init__(self, message: str, strategy_id: str = None, error_code: str = None):
        self.message = message
        self.strategy_id = strategy_id
        self.error_code = error_code
        super().__init__(self.message)


class StrategyService:
    """
    Comprehensive strategy management service

    Handles all strategy-related operations including:
    - CRUD operations
    - Validation and business rules
    - Backtesting integration
    - Performance tracking
    - Caching and optimization
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        cache_manager: CacheManager,
        ai_integration: Optional[Gemma3Client] = None,
    ):
        self.db_manager = db_manager
        self.cache_manager = cache_manager
        self.ai_integration = ai_integration

        # Cache keys
        self._strategy_cache_prefix = "strategy:"
        self._strategies_list_cache = "strategies:list"

    async def create_strategy(
        self, create_request: StrategyCreateRequest
    ) -> StrategyResponse:
        """
        Create a new trading strategy

        Args:
            create_request: Validated strategy creation data

        Returns:
            Created strategy response

        Raises:
            StrategyServiceError: If creation fails
        """
        try:
            async with self.db_manager.get_session() as session:
                # Check name availability
                existing_names = await self._get_existing_strategy_names(session)
                if not validate_strategy_name_availability(
                    create_request.name, existing_names
                ):
                    raise StrategyServiceError(
                        f"Strategy name '{create_request.name}' already exists",
                        error_code="DUPLICATE_NAME",
                    )

                # Create strategy instance
                strategy = Strategy(
                    name=create_request.name,
                    category=create_request.category,
                    description=create_request.description,
                    parameters=create_request.parameters,
                    target_symbols=create_request.target_symbols,
                    min_confidence=create_request.min_confidence,
                    max_position_size=create_request.max_position_size,
                    stop_loss_pct=create_request.stop_loss_pct,
                    take_profit_pct=create_request.take_profit_pct,
                    max_daily_trades=create_request.max_daily_trades,
                    is_paper_only=create_request.is_paper_only,
                )

                # Convert to ORM and save
                orm_strategy = StrategyORM(
                    strategy_id=strategy.strategy_id,
                    name=strategy.name,
                    category=strategy.category.value,
                    description=strategy.description,
                    parameters=strategy.parameters,
                    target_symbols=strategy.target_symbols,
                    min_confidence=strategy.min_confidence,
                    max_position_size=strategy.max_position_size,
                    stop_loss_pct=strategy.stop_loss_pct,
                    take_profit_pct=strategy.take_profit_pct,
                    max_daily_trades=strategy.max_daily_trades,
                    is_active=strategy.is_active,
                    is_paper_only=strategy.is_paper_only,
                    total_trades=strategy.total_trades,
                    win_rate=strategy.win_rate,
                    total_pnl=strategy.total_pnl,
                    sharpe_ratio=strategy.sharpe_ratio,
                    max_drawdown=strategy.max_drawdown,
                    created_at=strategy.created_at,
                    updated_at=strategy.updated_at,
                )

                session.add(orm_strategy)
                await session.commit()
                await session.refresh(orm_strategy)

                # Convert back to response model
                response = await self._orm_to_response(orm_strategy)

                # Invalidate cache
                await self._invalidate_strategy_cache()

                logger.info(
                    "Strategy created successfully", strategy_id=strategy.strategy_id
                )
                return response

        except Exception as e:
            logger.error("Strategy creation failed", error=str(e))
            raise StrategyServiceError(f"Failed to create strategy: {str(e)}")

    async def get_strategy(self, strategy_id: str) -> StrategyResponse:
        """
        Retrieve a strategy by ID

        Args:
            strategy_id: Strategy UUID

        Returns:
            Strategy response

        Raises:
            StrategyNotFoundError: If strategy doesn't exist
        """
        try:
            # Check cache first
            cache_key = f"{self._strategy_cache_prefix}{strategy_id}"
            cached = await self.cache_manager.get(cache_key)
            if cached:
                return StrategyResponse(**cached)

            async with self.db_manager.get_session() as session:
                stmt = select(StrategyORM).where(StrategyORM.strategy_id == strategy_id)
                result = await session.execute(stmt)
                orm_strategy = result.scalar_one_or_none()

                if not orm_strategy:
                    raise StrategyNotFoundError(strategy_id)

                response = await self._orm_to_response(orm_strategy)

                # Cache result
                await self.cache_manager.set(
                    cache_key, response.dict(), ttl=300
                )  # 5 minutes

                return response

        except StrategyNotFoundError:
            raise
        except Exception as e:
            logger.error(
                "Strategy retrieval failed", strategy_id=strategy_id, error=str(e)
            )
            raise StrategyServiceError(f"Failed to retrieve strategy: {str(e)}")

    async def list_strategies(
        self,
        category: Optional[str] = None,
        is_active: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[List[StrategyResponse], int]:
        """
        List strategies with optional filtering

        Args:
            category: Filter by strategy category
            is_active: Filter by active status
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            Tuple of (strategies list, total count)
        """
        try:
            # Check cache for unfiltered results
            cache_key = (
                f"{self._strategies_list_cache}:{category}:{is_active}:{limit}:{offset}"
            )
            if not any([category, is_active]):
                cached = await self.cache_manager.get(cache_key)
                if cached:
                    strategies = [StrategyResponse(**s) for s in cached["strategies"]]
                    return strategies, cached["total"]

            async with self.db_manager.get_session() as session:
                # Build query
                query = select(StrategyORM)
                count_query = select(func.count(StrategyORM.strategy_id))

                # Apply filters
                filters = []
                if category:
                    filters.append(StrategyORM.category == category)
                if is_active is not None:
                    filters.append(StrategyORM.is_active == is_active)

                if filters:
                    query = query.where(and_(*filters))
                    count_query = count_query.where(and_(*filters))

                # Get total count
                count_result = await session.execute(count_query)
                total = count_result.scalar()

                # Apply pagination and ordering
                query = (
                    query.order_by(StrategyORM.created_at.desc())
                    .limit(limit)
                    .offset(offset)
                )

                # Execute query
                result = await session.execute(query)
                orm_strategies = result.scalars().all()

                # Convert to response models
                strategies = []
                for orm_strategy in orm_strategies:
                    strategies.append(await self._orm_to_response(orm_strategy))

                # Cache unfiltered results
                if not any([category, is_active]):
                    cache_data = {
                        "strategies": [s.dict() for s in strategies],
                        "total": total,
                    }
                    await self.cache_manager.set(cache_key, cache_data, ttl=300)

                return strategies, total

        except Exception as e:
            logger.error("Strategy listing failed", error=str(e))
            raise StrategyServiceError(f"Failed to list strategies: {str(e)}")

    async def update_strategy(
        self, strategy_id: str, update_request: StrategyUpdateRequest
    ) -> StrategyResponse:
        """
        Update an existing strategy

        Args:
            strategy_id: Strategy UUID
            update_request: Update data

        Returns:
            Updated strategy response

        Raises:
            StrategyNotFoundError: If strategy doesn't exist
        """
        try:
            async with self.db_manager.get_session() as session:
                # Get existing strategy
                stmt = select(StrategyORM).where(StrategyORM.strategy_id == strategy_id)
                result = await session.execute(stmt)
                orm_strategy = result.scalar_one_or_none()

                if not orm_strategy:
                    raise StrategyNotFoundError(strategy_id)

                # Check name uniqueness if name is being updated
                if update_request.name and update_request.name != orm_strategy.name:
                    existing_names = await self._get_existing_strategy_names(
                        session, exclude_id=strategy_id
                    )
                    if not validate_strategy_name_availability(
                        update_request.name, existing_names
                    ):
                        raise StrategyServiceError(
                            f"Strategy name '{update_request.name}' already exists",
                            strategy_id=strategy_id,
                            error_code="DUPLICATE_NAME",
                        )

                # Apply updates
                update_data = update_request.dict(exclude_unset=True)
                for field, value in update_data.items():
                    if hasattr(orm_strategy, field):
                        setattr(orm_strategy, field, value)

                # Update timestamp
                orm_strategy.updated_at = datetime.utcnow()

                # Validate the updated strategy
                strategy = await self._orm_to_strategy(orm_strategy)
                strategy.validate()

                await session.commit()
                await session.refresh(orm_strategy)

                response = await self._orm_to_response(orm_strategy)

                # Invalidate caches
                await self._invalidate_strategy_cache(strategy_id)

                logger.info("Strategy updated successfully", strategy_id=strategy_id)
                return response

        except StrategyNotFoundError:
            raise
        except Exception as e:
            logger.error(
                "Strategy update failed", strategy_id=strategy_id, error=str(e)
            )
            raise StrategyServiceError(f"Failed to update strategy: {str(e)}")

    async def delete_strategy(self, strategy_id: str) -> bool:
        """
        Delete a strategy

        Args:
            strategy_id: Strategy UUID

        Returns:
            True if deleted, False if not found

        Raises:
            StrategyServiceError: If deletion fails
        """
        try:
            async with self.db_manager.get_session() as session:
                stmt = delete(StrategyORM).where(StrategyORM.strategy_id == strategy_id)
                result = await session.execute(stmt)
                await session.commit()

                deleted = result.rowcount > 0

                if deleted:
                    # Invalidate caches
                    await self._invalidate_strategy_cache(strategy_id)
                    logger.info(
                        "Strategy deleted successfully", strategy_id=strategy_id
                    )

                return deleted

        except Exception as e:
            logger.error(
                "Strategy deletion failed", strategy_id=strategy_id, error=str(e)
            )
            raise StrategyServiceError(f"Failed to delete strategy: {str(e)}")

    async def run_backtest(
        self, strategy_id: str, backtest_request: BacktestRequest
    ) -> BacktestResult:
        """
        Run a backtest for a strategy

        Args:
            strategy_id: Strategy UUID
            backtest_request: Backtest parameters

        Returns:
            Backtest results

        Raises:
            StrategyNotFoundError: If strategy doesn't exist
            BacktestExecutionError: If backtest fails
        """
        try:
            # Validate request
            validate_backtest_request(backtest_request)

            # Get strategy
            strategy = await self.get_strategy(strategy_id)

            # Use provided symbols or strategy's target symbols
            symbols = backtest_request.symbols or strategy.target_symbols

            # Create backtest configuration
            config = BacktestConfiguration(
                strategy_id=strategy_id,
                start_date=backtest_request.start_date,
                end_date=backtest_request.end_date,
                initial_capital=Decimal(str(backtest_request.initial_capital)),
                symbols=symbols,
            )

            # Get historical market data (placeholder - would integrate with data manager)
            market_data = await self._get_historical_data(
                symbols=symbols,
                start_date=backtest_request.start_date,
                end_date=backtest_request.end_date,
            )

            if not market_data:
                raise BacktestExecutionError(
                    "No market data available for the specified period",
                    config.backtest_id,
                )

            # Create backtest engine
            engine = BacktestEngine(config)

            # Define strategy logic (placeholder - would load actual strategy implementation)
            strategy_logic = self._create_strategy_logic_function(strategy)

            # Run backtest
            result = engine.execute_backtest(strategy_logic, market_data)

            logger.info(
                "Backtest completed successfully",
                strategy_id=strategy_id,
                backtest_id=result.backtest_id,
                total_return=result.performance_metrics.total_return,
            )

            return result

        except (StrategyNotFoundError, BacktestExecutionError):
            raise
        except Exception as e:
            logger.error(
                "Backtest execution failed", strategy_id=strategy_id, error=str(e)
            )
            raise BacktestExecutionError(f"Backtest failed: {str(e)}")

    async def _get_existing_strategy_names(
        self, session: AsyncSession, exclude_id: Optional[str] = None
    ) -> List[str]:
        """Get list of existing strategy names"""
        query = select(StrategyORM.name)
        if exclude_id:
            query = query.where(StrategyORM.strategy_id != exclude_id)

        result = await session.execute(query)
        return [row[0] for row in result.all()]

    async def _orm_to_response(self, orm_strategy: StrategyORM) -> StrategyResponse:
        """Convert ORM model to response model"""
        return StrategyResponse(
            strategy_id=orm_strategy.strategy_id,
            name=orm_strategy.name,
            category=StrategyCategory(orm_strategy.category),
            description=orm_strategy.description,
            parameters=orm_strategy.parameters,
            target_symbols=orm_strategy.target_symbols,
            min_confidence=orm_strategy.min_confidence,
            max_position_size=Decimal(str(orm_strategy.max_position_size)),
            stop_loss_pct=Decimal(str(orm_strategy.stop_loss_pct)),
            take_profit_pct=Decimal(str(orm_strategy.take_profit_pct)),
            max_daily_trades=orm_strategy.max_daily_trades,
            is_active=orm_strategy.is_active,
            is_paper_only=orm_strategy.is_paper_only,
            total_trades=orm_strategy.total_trades,
            win_rate=orm_strategy.win_rate,
            total_pnl=Decimal(str(orm_strategy.total_pnl)),
            sharpe_ratio=orm_strategy.sharpe_ratio,
            max_drawdown=Decimal(str(orm_strategy.max_drawdown)),
            created_at=orm_strategy.created_at,
            updated_at=orm_strategy.updated_at,
        )

    async def _orm_to_strategy(self, orm_strategy: StrategyORM) -> Strategy:
        """Convert ORM model to business logic model"""
        return Strategy(
            strategy_id=orm_strategy.strategy_id,
            name=orm_strategy.name,
            category=StrategyCategory(orm_strategy.category),
            description=orm_strategy.description,
            parameters=orm_strategy.parameters,
            target_symbols=orm_strategy.target_symbols,
            min_confidence=orm_strategy.min_confidence,
            max_position_size=Decimal(str(orm_strategy.max_position_size)),
            stop_loss_pct=Decimal(str(orm_strategy.stop_loss_pct)),
            take_profit_pct=Decimal(str(orm_strategy.take_profit_pct)),
            max_daily_trades=orm_strategy.max_daily_trades,
            is_active=orm_strategy.is_active,
            is_paper_only=orm_strategy.is_paper_only,
            total_trades=orm_strategy.total_trades,
            win_rate=orm_strategy.win_rate,
            total_pnl=Decimal(str(orm_strategy.total_pnl)),
            sharpe_ratio=orm_strategy.sharpe_ratio,
            max_drawdown=Decimal(str(orm_strategy.max_drawdown)),
            created_at=orm_strategy.created_at,
            updated_at=orm_strategy.updated_at,
        )

    async def _invalidate_strategy_cache(
        self, strategy_id: Optional[str] = None
    ) -> None:
        """Invalidate strategy-related cache entries"""
        keys_to_delete = [self._strategies_list_cache]

        if strategy_id:
            keys_to_delete.append(f"{self._strategy_cache_prefix}{strategy_id}")

        for key in keys_to_delete:
            await self.cache_manager.delete(key)

    async def _get_historical_data(
        self, symbols: List[str], start_date: date, end_date: date
    ) -> List[Dict[str, Any]]:
        """
        Get historical market data for backtesting

        Placeholder implementation - would integrate with data manager
        """
        # This is a placeholder that returns mock data
        # In real implementation, this would query the data manager
        import random
        from datetime import timedelta

        data = []
        current_date = start_date

        while current_date <= end_date:
            if current_date.weekday() < 5:  # Monday to Friday
                for symbol in symbols:
                    # Generate mock OHLC data
                    base_price = 1000 + random.uniform(-200, 200)
                    open_price = base_price + random.uniform(-10, 10)
                    high_price = open_price + abs(random.uniform(0, 20))
                    low_price = open_price - abs(random.uniform(0, 20))
                    close_price = low_price + random.uniform(0, high_price - low_price)
                    volume = random.randint(10000, 1000000)

                    data.append(
                        {
                            "symbol": symbol,
                            "timestamp": datetime.combine(
                                current_date, datetime.min.time()
                            ),
                            "open": open_price,
                            "high": high_price,
                            "low": low_price,
                            "close": close_price,
                            "volume": volume,
                        }
                    )

            current_date += timedelta(days=1)

        return data

    def _create_strategy_logic_function(self, strategy: StrategyResponse):
        """
        Create a strategy logic function for backtesting

        Placeholder implementation - would load actual strategy implementation
        """

        def strategy_logic(market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            """
            Mock strategy logic - buy on dip, sell on rally

            In real implementation, this would execute the actual strategy logic
            """
            import random

            # Simple mock strategy: random signals for testing
            if random.random() > 0.7:  # 30% chance of signal
                action = "buy" if random.random() > 0.5 else "sell"
                quantity = random.uniform(10, 100)

                return {
                    "symbol": market_data["symbol"],
                    "side": action,
                    "quantity": quantity,
                    "confidence": random.uniform(0.5, 0.9),
                }

            return None

        return strategy_logic


# Service initialization
async def create_strategy_service(
    db_manager: DatabaseManager,
    cache_manager: CacheManager,
    ai_integration: Optional[Gemma3Client] = None,
) -> StrategyService:
    """Create and initialize strategy service"""
    return StrategyService(
        db_manager=db_manager,
        cache_manager=cache_manager,
        ai_integration=ai_integration,
    )


# Export classes and functions
__all__ = ["StrategyService", "StrategyServiceError", "create_strategy_service"]
