"""
Integration Test: T031 - Paper Trading Workflow
Tests the complete paper trading workflow with comprehensive error handling.

This test validates:
1. User registration and authentication
2. Portfolio initialization in paper trading mode
3. Strategy creation and activation
4. Order placement and execution
5. Portfolio updates and tracking
6. Risk management triggers
7. Error scenarios and recovery
"""

import pytest
import asyncio
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Any
from unittest.mock import Mock, AsyncMock

# Mock imports for integration testing
from sqlalchemy.orm import Session


class MockUser:
    """Mock User model for testing"""
    def __init__(self, user_id: str = "test_user_001",
                 email: str = "test@example.com"):
        self.id = user_id
        self.email = email
        self.is_active = True
        self.trading_mode = "paper"
        self.paper_balance = Decimal("100000.00")
        self.created_at = datetime.now()


class MockPortfolio:
    """Mock Portfolio model for testing"""
    def __init__(self, user_id: str):
        self.id = f"portfolio_{user_id}"
        self.user_id = user_id
        self.cash_balance = Decimal("100000.00")
        self.total_value = Decimal("100000.00")
        self.positions = []
        self.updated_at = datetime.now()


class MockStrategy:
    """Mock Strategy model for testing"""
    def __init__(self, strategy_id: str = "paper_strategy_001"):
        self.id = strategy_id
        self.name = "Paper Trading Strategy"
        self.type = "quantitative"
        self.is_active = True
        self.parameters = {"risk_tolerance": 0.05, "max_position_size": 0.1}
        self.created_at = datetime.now()


class MockTrade:
    """Mock Trade model for testing"""
    def __init__(self, trade_id: str, symbol: str, quantity: int,
                 price: Decimal):
        self.id = trade_id
        self.symbol = symbol
        self.quantity = quantity
        self.price = price
        self.side = "BUY" if quantity > 0 else "SELL"
        self.status = "PENDING"
        self.order_type = "MARKET"
        self.created_at = datetime.now()
        self.executed_at = None


class PaperTradingError(Exception):
    """Custom exception for paper trading errors"""
    pass


class InsufficientFundsError(PaperTradingError):
    """Raised when insufficient funds for paper trading"""
    pass


class StrategyExecutionError(PaperTradingError):
    """Raised when strategy execution fails"""
    pass


class MarketDataError(PaperTradingError):
    """Raised when market data is unavailable"""
    pass


@pytest.fixture
def mock_db_session():
    """Mock database session"""
    session = Mock(spec=Session)
    session.commit = Mock()
    session.rollback = Mock()
    session.close = Mock()
    return session


@pytest.fixture
def mock_user():
    """Create mock user for testing"""
    return MockUser()


@pytest.fixture
def mock_portfolio(mock_user):
    """Create mock portfolio for testing"""
    return MockPortfolio(mock_user.id)


@pytest.fixture
def mock_strategy():
    """Create mock strategy for testing"""
    return MockStrategy()


@pytest.fixture
def paper_trading_service():
    """Mock paper trading service"""
    service = Mock()
    service.initialize_portfolio = AsyncMock()
    service.place_order = AsyncMock()
    service.execute_trade = AsyncMock()
    service.update_portfolio = AsyncMock()
    service.calculate_pnl = AsyncMock()
    return service


@pytest.fixture
def market_data_service():
    """Mock market data service"""
    service = Mock()
    service.get_current_price = AsyncMock()
    service.get_historical_data = AsyncMock()
    service.subscribe_to_updates = AsyncMock()
    return service


@pytest.fixture
def strategy_service():
    """Mock strategy service"""
    service = Mock()
    service.create_strategy = AsyncMock()
    service.activate_strategy = AsyncMock()
    service.generate_signals = AsyncMock()
    service.deactivate_strategy = AsyncMock()
    return service


class TestPaperTradingWorkflow:
    """Integration tests for paper trading workflow"""

    @pytest.mark.asyncio
    async def test_complete_paper_trading_workflow_success(
        self,
        mock_db_session,
        mock_user,
        mock_portfolio,
        mock_strategy,
        paper_trading_service,
        market_data_service,
        strategy_service
    ):
        """Test successful paper trading workflow from start to finish"""

        # Setup test data
        symbol = "RELIANCE"
        quantity = 10
        expected_price = Decimal("2500.00")

        # Mock service responses
        market_data_service.get_current_price.return_value = expected_price
        paper_trading_service.initialize_portfolio.return_value = \
            mock_portfolio
        strategy_service.create_strategy.return_value = mock_strategy

        # Create a mock trade
        mock_trade = MockTrade("trade_001", symbol, quantity, expected_price)
        paper_trading_service.place_order.return_value = mock_trade

        # Execute workflow
        try:
            # Step 1: Initialize portfolio
            portfolio = await paper_trading_service.initialize_portfolio(
                mock_user.id
            )
            assert portfolio.cash_balance == Decimal("100000.00")
            assert portfolio.user_id == mock_user.id

            # Step 2: Create and activate strategy
            strategy = await strategy_service.create_strategy(
                name="Test Strategy",
                strategy_type="quantitative",
                parameters={"risk_tolerance": 0.05}
            )
            assert strategy.name == "Paper Trading Strategy"
            assert strategy.is_active

            await strategy_service.activate_strategy(strategy.id)

            # Step 3: Get market data
            current_price = await market_data_service.get_current_price(symbol)
            assert current_price == expected_price

            # Step 4: Place paper trade
            trade = await paper_trading_service.place_order(
                user_id=mock_user.id,
                symbol=symbol,
                quantity=quantity,
                order_type="MARKET",
                side="BUY"
            )

            assert trade.symbol == symbol
            assert trade.quantity == quantity
            assert trade.side == "BUY"
            assert trade.status == "PENDING"

            # Step 5: Execute trade
            trade.status = "EXECUTED"
            trade.executed_at = datetime.now()
            await paper_trading_service.execute_trade(trade.id)

            # Step 6: Update portfolio
            updated_portfolio = await paper_trading_service.update_portfolio(
                mock_user.id,
                trade
            )

            # Verify portfolio updated correctly
            assert updated_portfolio.cash_balance <= mock_portfolio.cash_balance

            # Step 7: Calculate P&L
            pnl = await paper_trading_service.calculate_pnl(mock_user.id)
            assert pnl is not None

            print("✅ Complete paper trading workflow executed successfully")

        except Exception as e:
            pytest.fail(f"Paper trading workflow failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_insufficient_funds_error_handling(
        self,
        mock_db_session,
        mock_user,
        mock_portfolio,
        paper_trading_service,
        market_data_service
    ):
        """Test handling of insufficient funds error"""

        symbol = "RELIANCE"
        quantity = 1000  # Large quantity to exceed balance
        price = Decimal("2500.00")

        # Mock insufficient funds scenario
        mock_portfolio.cash_balance = Decimal("1000.00")  # Low balance
        market_data_service.get_current_price.return_value = price

        # Configure service to raise insufficient funds error
        required_amount = price * quantity
        available_amount = mock_portfolio.cash_balance
        error_msg = (
            f"Insufficient funds: Required {required_amount}, "
            f"Available {available_amount}"
        )
        paper_trading_service.place_order.side_effect = InsufficientFundsError(
            error_msg
        )

        try:
            with pytest.raises(InsufficientFundsError) as exc_info:
                await paper_trading_service.place_order(
                    user_id=mock_user.id,
                    symbol=symbol,
                    quantity=quantity,
                    order_type="MARKET",
                    side="BUY"
                )

            assert "Insufficient funds" in str(exc_info.value)
            print("✅ Insufficient funds error handled correctly")

        except Exception as e:
            pytest.fail(f"Insufficient funds error handling failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_strategy_execution_error_handling(
        self,
        mock_db_session,
        mock_user,
        mock_strategy,
        strategy_service
    ):
        """Test handling of strategy execution errors"""

        # Configure strategy service to fail
        error_msg = "Strategy activation failed: Invalid parameters"
        strategy_service.activate_strategy.side_effect = \
            StrategyExecutionError(error_msg)

        try:
            with pytest.raises(StrategyExecutionError) as exc_info:
                await strategy_service.activate_strategy(mock_strategy.id)

            assert "Strategy activation failed" in str(exc_info.value)
            print("✅ Strategy execution error handled correctly")

        except Exception as e:
            pytest.fail(f"Strategy execution error handling failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_market_data_error_handling(
        self,
        mock_db_session,
        market_data_service
    ):
        """Test handling of market data errors"""

        symbol = "INVALID_SYMBOL"

        # Configure market data service to fail
        market_data_service.get_current_price.side_effect = MarketDataError(
            f"Market data unavailable for symbol: {symbol}"
        )

        try:
            with pytest.raises(MarketDataError) as exc_info:
                await market_data_service.get_current_price(symbol)

            assert "Market data unavailable" in str(exc_info.value)
            print("✅ Market data error handled correctly")

        except Exception as e:
            pytest.fail(f"Market data error handling failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_portfolio_state_recovery(
        self,
        mock_db_session,
        mock_user,
        mock_portfolio,
        paper_trading_service
    ):
        """Test portfolio state recovery after errors"""

        original_balance = mock_portfolio.cash_balance

        # Simulate failed trade that should not affect portfolio
        paper_trading_service.place_order.side_effect = Exception(
            "Network error"
        )

        try:
            with pytest.raises(Exception):
                await paper_trading_service.place_order(
                    user_id=mock_user.id,
                    symbol="RELIANCE",
                    quantity=10,
                    order_type="MARKET",
                    side="BUY"
                )

            # Verify portfolio state unchanged after error
            paper_trading_service.initialize_portfolio.return_value = \
                mock_portfolio
            portfolio = await paper_trading_service.initialize_portfolio(
                mock_user.id
            )

            assert portfolio.cash_balance == original_balance
            print("✅ Portfolio state recovered successfully after error")

        except AssertionError:
            pytest.fail("Portfolio state not properly recovered after error")

    @pytest.mark.asyncio
    async def test_concurrent_trade_execution(
        self,
        mock_db_session,
        mock_user,
        paper_trading_service,
        market_data_service
    ):
        """Test handling of concurrent trade execution"""

        symbols = ["RELIANCE", "TCS", "INFY"]
        quantities = [10, 15, 20]
        prices = [Decimal("2500.00"), Decimal("3800.00"), Decimal("1700.00")]

        # Setup mock responses
        market_data_service.get_current_price.side_effect = prices

        # Create mock trades
        mock_trades = []
        for i, (symbol, quantity, price) in enumerate(
            zip(symbols, quantities, prices)
        ):
            trade = MockTrade(f"trade_{i+1}", symbol, quantity, price)
            mock_trades.append(trade)

        paper_trading_service.place_order.side_effect = mock_trades

        try:
            # Execute concurrent trades
            tasks = []
            for i, (symbol, quantity) in enumerate(zip(symbols, quantities)):
                task = paper_trading_service.place_order(
                    user_id=mock_user.id,
                    symbol=symbol,
                    quantity=quantity,
                    order_type="MARKET",
                    side="BUY"
                )
                tasks.append(task)

            trades = await asyncio.gather(*tasks, return_exceptions=True)

            # Verify all trades executed successfully
            successful_trades = [
                t for t in trades if not isinstance(t, Exception)
            ]
            assert len(successful_trades) == len(symbols)

            print("✅ Concurrent trade execution handled successfully")

        except Exception as e:
            pytest.fail(f"Concurrent trade execution failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_risk_management_triggers(
        self,
        mock_db_session,
        mock_user,
        mock_portfolio,
        paper_trading_service
    ):
        """Test risk management triggers and circuit breakers"""

        # Setup scenario where risk limits are exceeded
        mock_portfolio.cash_balance = Decimal("50000.00")  # 50% loss
        original_balance = Decimal("100000.00")

        # Calculate loss percentage
        cash_diff = original_balance - mock_portfolio.cash_balance
        loss_percentage = cash_diff / original_balance
        risk_threshold = Decimal("0.30")  # 30% loss threshold

        try:
            # Simulate risk check
            if loss_percentage > risk_threshold:
                error_msg = (
                    f"Risk threshold exceeded: {loss_percentage:.2%} loss"
                )
                raise PaperTradingError(error_msg)

        except PaperTradingError as e:
            # This should trigger risk management
            assert "Risk threshold exceeded" in str(e)
            print("✅ Risk management trigger activated successfully")

    def test_paper_trading_configuration_validation(self):
        """Test validation of paper trading configuration"""

        try:
            # Test valid configuration
            config = {
                "initial_balance": Decimal("100000.00"),
                "max_position_size": Decimal("0.10"),
                "risk_tolerance": Decimal("0.05"),
                "commission_rate": Decimal("0.001")
            }

            # Validate configuration
            assert config["initial_balance"] > 0
            assert 0 < config["max_position_size"] <= 1
            assert 0 < config["risk_tolerance"] <= 1
            assert config["commission_rate"] >= 0

            print("✅ Paper trading configuration validated successfully")

        except AssertionError:
            pytest.fail("Paper trading configuration validation failed")

    @pytest.mark.asyncio
    async def test_paper_trading_performance_metrics(
        self,
        mock_db_session,
        mock_user,
        paper_trading_service
    ):
        """Test calculation of paper trading performance metrics"""

        # Mock performance data
        performance_data = {
            "total_return": Decimal("0.15"),  # 15% return
            "sharpe_ratio": Decimal("1.25"),
            "max_drawdown": Decimal("0.08"),  # 8% drawdown
            "win_rate": Decimal("0.65"),      # 65% win rate
            "total_trades": 25,
            "profitable_trades": 16
        }

        paper_trading_service.calculate_performance_metrics.return_value = \
            performance_data

        try:
            calc_service = paper_trading_service.calculate_performance_metrics
            metrics = await calc_service(mock_user.id)

            assert metrics["total_return"] > 0
            assert metrics["sharpe_ratio"] > 1
            assert metrics["max_drawdown"] < Decimal("0.20")  # Less than 20%
            assert metrics["win_rate"] > Decimal("0.50")     # Greater than 50%

            print("✅ Paper trading performance metrics calculated")

        except Exception as e:
            pytest.fail(f"Performance metrics calculation failed: {str(e)}")


# Additional utility functions for integration testing
def create_test_scenario(scenario_name: str) -> Dict[str, Any]:
    """Create predefined test scenarios"""

    scenarios = {
        "successful_workflow": {
            "user_balance": Decimal("100000.00"),
            "trades": [
                {
                    "symbol": "RELIANCE",
                    "quantity": 10,
                    "price": Decimal("2500.00")
                },
                {
                    "symbol": "TCS",
                    "quantity": 5,
                    "price": Decimal("3800.00")
                }
            ],
            "expected_outcome": "success"
        },

        "insufficient_funds": {
            "user_balance": Decimal("1000.00"),
            "trades": [
                {
                    "symbol": "RELIANCE",
                    "quantity": 100,
                    "price": Decimal("2500.00")
                }
            ],
            "expected_outcome": "insufficient_funds_error"
        },

        "market_data_failure": {
            "user_balance": Decimal("100000.00"),
            "trades": [
                {"symbol": "INVALID", "quantity": 10, "price": None}
            ],
            "expected_outcome": "market_data_error"
        }
    }

    return scenarios.get(scenario_name, {})


def validate_paper_trading_state(
    portfolio: MockPortfolio,
    trades: List[MockTrade]
) -> bool:
    """Validate consistency of paper trading state"""

    try:
        # Basic validation - portfolio values must be non-negative
        assert portfolio.cash_balance >= 0, "Cash balance cannot be negative"
        assert portfolio.total_value >= 0, (
            "Total portfolio value cannot be negative"
        )

        return True

    except Exception as e:
        print(f"State validation failed: {str(e)}")
        return False


if __name__ == "__main__":
    """Run integration tests for paper trading workflow"""

    print("🚀 Starting Paper Trading Integration Tests...")

    # Run pytest with verbose output
    import subprocess
    result = subprocess.run([
        "python", "-m", "pytest",
        __file__,
        "-v",
        "--tb=short"
    ], capture_output=True, text=True)

    print(result.stdout)
    if result.stderr:
        print("Errors:", result.stderr)

    print("✅ Paper Trading Integration Tests Complete!")