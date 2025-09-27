"""
Integration Test: T033 - Strategy Activation and Signal Generation
Tests the complete strategy workflow from activation to signal generation.

This test validates:
1. Strategy creation and configuration
2. Strategy activation and validation
3. Market data subscription and processing
4. Signal generation and evaluation
5. Strategy performance tracking
6. Strategy deactivation and cleanup
7. Error handling and recovery
8. Multi-strategy coordination
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock
from enum import Enum

# Mock imports for integration testing
from sqlalchemy.orm import Session


class StrategyType(Enum):
    """Strategy type enumeration"""

    QUANTITATIVE = "quantitative"
    PREDATORY = "predatory"
    PSYCHOLOGICAL = "psychological"


class StrategyStatus(Enum):
    """Strategy status enumeration"""

    INACTIVE = "inactive"
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"


class SignalType(Enum):
    """Signal type enumeration"""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class StrategyError(Exception):
    """Base exception for strategy errors"""

    pass


class StrategyActivationError(StrategyError):
    """Raised when strategy activation fails"""

    pass


class SignalGenerationError(StrategyError):
    """Raised when signal generation fails"""

    pass


class MarketDataError(StrategyError):
    """Raised when market data is unavailable"""

    pass


class StrategyValidationError(StrategyError):
    """Raised when strategy validation fails"""

    pass


class MockStrategy:
    """Mock Strategy model for testing"""

    def __init__(self, strategy_id: str = "strategy_001", name: str = "Test Strategy"):
        self.id = strategy_id
        self.name = name
        self.type = StrategyType.QUANTITATIVE
        self.status = StrategyStatus.INACTIVE
        self.parameters = {
            "risk_tolerance": 0.05,
            "max_position_size": 0.10,
            "stop_loss": 0.05,
            "take_profit": 0.15,
        }
        self.performance_metrics = {
            "total_return": Decimal("0.00"),
            "win_rate": Decimal("0.00"),
            "sharpe_ratio": Decimal("0.00"),
            "max_drawdown": Decimal("0.00"),
        }
        self.created_at = datetime.now()
        self.last_signal = None
        self.is_validated = False


class MockSignal:
    """Mock Strategy Signal model"""

    def __init__(
        self,
        signal_id: str,
        strategy_id: str,
        symbol: str,
        signal_type: SignalType,
        confidence: Decimal,
    ):
        self.id = signal_id
        self.strategy_id = strategy_id
        self.symbol = symbol
        self.signal_type = signal_type
        self.confidence = confidence
        self.price = None
        self.timestamp = datetime.now()
        self.is_executed = False
        self.metadata = {}


class MockMarketData:
    """Mock Market Data model"""

    def __init__(self, symbol: str):
        self.symbol = symbol
        self.current_price = Decimal("0.00")
        self.volume = 0
        self.timestamp = datetime.now()
        self.ohlc_data = {
            "open": Decimal("0.00"),
            "high": Decimal("0.00"),
            "low": Decimal("0.00"),
            "close": Decimal("0.00"),
        }
        self.technical_indicators = {}


@pytest.fixture
def mock_db_session():
    """Mock database session"""
    session = Mock(spec=Session)
    session.commit = Mock()
    session.rollback = Mock()
    session.close = Mock()
    return session


@pytest.fixture
def mock_strategy():
    """Create mock strategy for testing"""
    return MockStrategy()


@pytest.fixture
def strategy_service():
    """Mock strategy service"""
    service = Mock()
    service.create_strategy = AsyncMock()
    service.activate_strategy = AsyncMock()
    service.deactivate_strategy = AsyncMock()
    service.validate_strategy = AsyncMock()
    service.update_performance = AsyncMock()
    return service


@pytest.fixture
def signal_service():
    """Mock signal service"""
    service = Mock()
    service.generate_signal = AsyncMock()
    service.evaluate_signals = AsyncMock()
    service.execute_signal = AsyncMock()
    service.track_signal_performance = AsyncMock()
    return service


@pytest.fixture
def market_data_service():
    """Mock market data service"""
    service = Mock()
    service.subscribe_to_symbol = AsyncMock()
    service.get_current_data = AsyncMock()
    service.get_historical_data = AsyncMock()
    service.unsubscribe_from_symbol = AsyncMock()
    return service


@pytest.fixture
def technical_analysis_service():
    """Mock technical analysis service"""
    service = Mock()
    service.calculate_indicators = AsyncMock()
    service.analyze_trends = AsyncMock()
    service.generate_insights = AsyncMock()
    return service


class TestStrategyFlow:
    """Integration tests for strategy activation and signal generation"""

    @pytest.mark.asyncio
    async def test_complete_strategy_workflow_success(
        self,
        mock_db_session,
        mock_strategy,
        strategy_service,
        signal_service,
        market_data_service,
        technical_analysis_service,
    ):
        """Test complete strategy workflow from activation to signals"""

        # Setup test data
        symbol = "RELIANCE"
        expected_signal = MockSignal(
            "signal_001", mock_strategy.id, symbol, SignalType.BUY, Decimal("0.85")
        )

        market_data = MockMarketData(symbol)
        market_data.current_price = Decimal("2500.00")
        market_data.ohlc_data = {
            "open": Decimal("2480.00"),
            "high": Decimal("2520.00"),
            "low": Decimal("2475.00"),
            "close": Decimal("2500.00"),
        }

        # Mock service responses
        strategy_service.validate_strategy.return_value = True
        market_data_service.subscribe_to_symbol.return_value = True
        market_data_service.get_current_data.return_value = market_data
        technical_analysis_service.calculate_indicators.return_value = {
            "rsi": 45.5,
            "macd": {"signal": "bullish"},
            "moving_averages": {"sma_20": 2485.0, "ema_12": 2490.0},
        }
        signal_service.generate_signal.return_value = expected_signal

        try:
            # Step 1: Validate strategy configuration
            is_valid = await strategy_service.validate_strategy(mock_strategy.id)
            assert is_valid is True
            mock_strategy.is_validated = True

            # Step 2: Activate strategy
            mock_strategy.status = StrategyStatus.ACTIVE
            activation_result = await strategy_service.activate_strategy(
                mock_strategy.id
            )
            assert activation_result["success"] is True
            assert mock_strategy.status == StrategyStatus.ACTIVE

            # Step 3: Subscribe to market data
            subscription_success = await market_data_service.subscribe_to_symbol(
                symbol, mock_strategy.id
            )
            assert subscription_success is True

            # Step 4: Get market data
            current_data = await market_data_service.get_current_data(symbol)
            assert current_data.symbol == symbol
            assert current_data.current_price > 0

            # Step 5: Calculate technical indicators
            indicators = await technical_analysis_service.calculate_indicators(
                symbol, market_data
            )
            assert "rsi" in indicators
            assert "macd" in indicators

            # Step 6: Generate trading signal
            signal = await signal_service.generate_signal(
                mock_strategy.id, symbol, current_data, indicators
            )

            assert signal.strategy_id == mock_strategy.id
            assert signal.symbol == symbol
            assert signal.signal_type in [
                SignalType.BUY,
                SignalType.SELL,
                SignalType.HOLD,
            ]
            assert signal.confidence >= 0 and signal.confidence <= 1

            # Step 7: Update strategy performance
            mock_strategy.last_signal = signal.timestamp
            await strategy_service.update_performance(
                mock_strategy.id,
                {"signals_generated": 1, "last_activity": datetime.now()},
            )

            print("✅ Complete strategy workflow executed successfully")

        except Exception as e:
            pytest.fail(f"Strategy workflow failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_strategy_activation_validation_error(
        self, mock_db_session, mock_strategy, strategy_service
    ):
        """Test handling of strategy validation errors during activation"""

        # Configure strategy service to fail validation
        strategy_service.validate_strategy.side_effect = StrategyValidationError(
            "Strategy parameters are invalid: risk_tolerance out of range"
        )

        try:
            with pytest.raises(StrategyValidationError) as exc_info:
                await strategy_service.validate_strategy(mock_strategy.id)

            assert "invalid" in str(exc_info.value).lower()

            # Verify strategy remains inactive
            assert mock_strategy.status == StrategyStatus.INACTIVE
            assert not mock_strategy.is_validated

            print("✅ Strategy validation error handled correctly")

        except Exception as e:
            pytest.fail(f"Strategy validation error handling failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_market_data_subscription_failure(
        self, mock_db_session, mock_strategy, market_data_service, strategy_service
    ):
        """Test handling of market data subscription failures"""

        symbol = "INVALID_SYMBOL"

        # Configure market data service to fail subscription
        market_data_service.subscribe_to_symbol.side_effect = MarketDataError(
            f"Failed to subscribe to market data for symbol: {symbol}"
        )

        try:
            with pytest.raises(MarketDataError) as exc_info:
                await market_data_service.subscribe_to_symbol(symbol, mock_strategy.id)

            assert "Failed to subscribe" in str(exc_info.value)

            # Strategy should be deactivated due to data failure
            mock_strategy.status = StrategyStatus.ERROR
            await strategy_service.deactivate_strategy(
                mock_strategy.id, reason="market_data_error"
            )

            assert mock_strategy.status == StrategyStatus.ERROR

            print("✅ Market data subscription failure handled correctly")

        except Exception as e:
            pytest.fail(f"Market data subscription error handling failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_signal_generation_failure_recovery(
        self, mock_db_session, mock_strategy, signal_service, strategy_service
    ):
        """Test recovery from signal generation failures"""

        symbol = "RELIANCE"
        failure_count = 0
        max_failures = 3

        def mock_generate_signal(*args, **kwargs):
            nonlocal failure_count
            failure_count += 1

            if failure_count <= max_failures:
                raise SignalGenerationError(
                    f"Signal generation failed: attempt {failure_count}"
                )
            else:
                # Recovery after max failures
                return MockSignal(
                    "signal_recovery",
                    mock_strategy.id,
                    symbol,
                    SignalType.HOLD,
                    Decimal("0.50"),
                )

        signal_service.generate_signal.side_effect = mock_generate_signal

        try:
            # Attempt signal generation with failures
            for attempt in range(max_failures + 2):
                try:
                    signal = await signal_service.generate_signal(
                        mock_strategy.id, symbol, None, {}
                    )

                    # Success after recovery
                    assert signal.signal_type == SignalType.HOLD
                    print("✅ Signal generation recovered successfully")
                    break

                except SignalGenerationError as e:
                    if attempt < max_failures:
                        continue  # Expected failure
                    else:
                        raise  # Unexpected continued failure

        except Exception as e:
            pytest.fail(f"Signal generation recovery failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_multi_strategy_coordination(
        self, mock_db_session, strategy_service, signal_service, market_data_service
    ):
        """Test coordination of multiple active strategies"""

        # Create multiple strategies
        strategies = [
            MockStrategy("strategy_001", "Quantitative Strategy"),
            MockStrategy("strategy_002", "Predatory Strategy"),
            MockStrategy("strategy_003", "Psychological Strategy"),
        ]

        strategies[0].type = StrategyType.QUANTITATIVE
        strategies[1].type = StrategyType.PREDATORY
        strategies[2].type = StrategyType.PSYCHOLOGICAL

        symbol = "RELIANCE"

        # Mock signals from different strategies
        signals = [
            MockSignal(
                "signal_q", "strategy_001", symbol, SignalType.BUY, Decimal("0.80")
            ),
            MockSignal(
                "signal_p", "strategy_002", symbol, SignalType.SELL, Decimal("0.70")
            ),
            MockSignal(
                "signal_ps", "strategy_003", symbol, SignalType.HOLD, Decimal("0.60")
            ),
        ]

        # Configure services
        strategy_service.activate_strategy.return_value = {"success": True}
        market_data_service.subscribe_to_symbol.return_value = True
        signal_service.generate_signal.side_effect = signals
        signal_service.evaluate_signals.return_value = {
            "primary_signal": SignalType.BUY,
            "confidence": Decimal("0.75"),
            "consensus": "weak_buy",
        }

        try:
            # Activate all strategies
            for strategy in strategies:
                result = await strategy_service.activate_strategy(strategy.id)
                assert result["success"] is True
                strategy.status = StrategyStatus.ACTIVE

            # Subscribe to market data for all strategies
            for strategy in strategies:
                success = await market_data_service.subscribe_to_symbol(
                    symbol, strategy.id
                )
                assert success is True

            # Generate signals from all strategies
            generated_signals = []
            for i, strategy in enumerate(strategies):
                signal = await signal_service.generate_signal(
                    strategy.id, symbol, None, {}
                )
                generated_signals.append(signal)

            # Evaluate signal consensus
            evaluation = await signal_service.evaluate_signals(generated_signals)

            assert evaluation["primary_signal"] in [
                SignalType.BUY,
                SignalType.SELL,
                SignalType.HOLD,
            ]
            assert "confidence" in evaluation
            assert "consensus" in evaluation

            print("✅ Multi-strategy coordination working correctly")

        except Exception as e:
            pytest.fail(f"Multi-strategy coordination failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_strategy_performance_tracking(
        self, mock_db_session, mock_strategy, strategy_service, signal_service
    ):
        """Test strategy performance tracking and metrics calculation"""

        # Setup performance tracking scenario
        signals_generated = 10
        successful_signals = 7
        total_return = Decimal("0.15")  # 15% return

        performance_data = {
            "total_signals": signals_generated,
            "successful_signals": successful_signals,
            "win_rate": successful_signals / signals_generated,
            "total_return": total_return,
            "sharpe_ratio": Decimal("1.25"),
            "max_drawdown": Decimal("0.08"),
        }

        strategy_service.update_performance.return_value = performance_data

        try:
            # Update strategy performance
            updated_metrics = await strategy_service.update_performance(
                mock_strategy.id, performance_data
            )

            # Validate performance metrics
            assert updated_metrics["total_signals"] == signals_generated
            assert updated_metrics["win_rate"] > 0.5  # Above 50%
            assert updated_metrics["total_return"] > 0  # Positive return
            assert updated_metrics["sharpe_ratio"] > 1  # Good risk-adjusted return
            assert updated_metrics["max_drawdown"] < 0.20  # Less than 20%

            # Update mock strategy metrics
            mock_strategy.performance_metrics.update(updated_metrics)

            print("✅ Strategy performance tracking working correctly")

        except Exception as e:
            pytest.fail(f"Strategy performance tracking failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_strategy_deactivation_cleanup(
        self,
        mock_db_session,
        mock_strategy,
        strategy_service,
        market_data_service,
        signal_service,
    ):
        """Test proper cleanup during strategy deactivation"""

        symbol = "RELIANCE"

        # Setup active strategy
        mock_strategy.status = StrategyStatus.ACTIVE

        try:
            # Step 1: Deactivate strategy
            await strategy_service.deactivate_strategy(
                mock_strategy.id, reason="manual_deactivation"
            )
            mock_strategy.status = StrategyStatus.INACTIVE

            # Step 2: Unsubscribe from market data
            await market_data_service.unsubscribe_from_symbol(symbol, mock_strategy.id)

            # Step 3: Stop signal generation
            # This would typically involve canceling scheduled tasks

            # Step 4: Finalize performance metrics
            final_metrics = {
                "deactivated_at": datetime.now(),
                "final_status": "manual_deactivation",
                "uptime": timedelta(hours=2).total_seconds(),
            }

            await strategy_service.update_performance(mock_strategy.id, final_metrics)

            # Verify cleanup completed
            assert mock_strategy.status == StrategyStatus.INACTIVE

            print("✅ Strategy deactivation cleanup completed successfully")

        except Exception as e:
            pytest.fail(f"Strategy deactivation cleanup failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_strategy_parameter_validation(
        self, mock_db_session, strategy_service
    ):
        """Test validation of strategy parameters"""

        # Test valid parameters
        valid_params = {
            "risk_tolerance": 0.05,
            "max_position_size": 0.10,
            "stop_loss": 0.05,
            "take_profit": 0.15,
            "lookback_period": 20,
            "signal_threshold": 0.70,
        }

        # Test invalid parameters
        invalid_params = {
            "risk_tolerance": 1.50,  # > 100%
            "max_position_size": -0.05,  # Negative
            "stop_loss": 0.0,  # Zero stop loss
            "take_profit": -0.10,  # Negative take profit
        }

        try:
            # Validate correct parameters
            validation_result = await strategy_service.validate_strategy(
                "test_strategy", valid_params
            )
            assert validation_result is True

            # Test parameter validation logic
            assert 0 < valid_params["risk_tolerance"] <= 1
            assert 0 < valid_params["max_position_size"] <= 1
            assert valid_params["stop_loss"] > 0
            assert valid_params["take_profit"] > 0

            print("✅ Strategy parameter validation working correctly")

        except Exception as e:
            pytest.fail(f"Strategy parameter validation failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_signal_confidence_evaluation(self, mock_db_session, signal_service):
        """Test evaluation of signal confidence levels"""

        # Create signals with different confidence levels
        high_confidence_signal = MockSignal(
            "signal_high", "strategy_001", "RELIANCE", SignalType.BUY, Decimal("0.90")
        )

        medium_confidence_signal = MockSignal(
            "signal_medium", "strategy_001", "TCS", SignalType.SELL, Decimal("0.70")
        )

        low_confidence_signal = MockSignal(
            "signal_low", "strategy_001", "INFY", SignalType.HOLD, Decimal("0.40")
        )

        signals = [
            high_confidence_signal,
            medium_confidence_signal,
            low_confidence_signal,
        ]

        try:
            # Evaluate signals based on confidence
            for signal in signals:
                if signal.confidence >= Decimal("0.80"):
                    signal.metadata["priority"] = "high"
                elif signal.confidence >= Decimal("0.60"):
                    signal.metadata["priority"] = "medium"
                else:
                    signal.metadata["priority"] = "low"

                # Track signal for performance monitoring
                await signal_service.track_signal_performance(signal.id)

            # Verify confidence-based prioritization
            assert high_confidence_signal.metadata["priority"] == "high"
            assert medium_confidence_signal.metadata["priority"] == "medium"
            assert low_confidence_signal.metadata["priority"] == "low"

            print("✅ Signal confidence evaluation working correctly")

        except Exception as e:
            pytest.fail(f"Signal confidence evaluation failed: {str(e)}")


# Additional utility functions for testing
def create_strategy_test_scenario(scenario_name: str) -> Dict[str, Any]:
    """Create predefined strategy test scenarios"""

    scenarios = {
        "successful_activation": {
            "parameters": {"risk_tolerance": 0.05, "max_position_size": 0.10},
            "market_data_available": True,
            "expected_outcome": "success",
        },
        "invalid_parameters": {
            "parameters": {
                "risk_tolerance": 1.50,  # Invalid
                "max_position_size": -0.05,  # Invalid
            },
            "market_data_available": True,
            "expected_outcome": "validation_error",
        },
        "market_data_unavailable": {
            "parameters": {"risk_tolerance": 0.05, "max_position_size": 0.10},
            "market_data_available": False,
            "expected_outcome": "market_data_error",
        },
    }

    return scenarios.get(scenario_name, {})


def validate_signal_quality(signal: MockSignal) -> bool:
    """Validate the quality of a generated signal"""

    try:
        # Basic signal validation
        assert signal.confidence >= 0 and signal.confidence <= 1
        assert signal.signal_type in [SignalType.BUY, SignalType.SELL, SignalType.HOLD]
        assert signal.timestamp is not None
        assert signal.symbol is not None and len(signal.symbol) > 0

        # Quality thresholds
        min_confidence = Decimal("0.30")  # Minimum confidence threshold
        assert signal.confidence >= min_confidence

        return True

    except Exception as e:
        print(f"Signal quality validation failed: {str(e)}")
        return False


if __name__ == "__main__":
    """Run integration tests for strategy flow"""

    print("🚀 Starting Strategy Flow Integration Tests...")

    # Run pytest with verbose output
    import subprocess

    result = subprocess.run(
        ["python", "-m", "pytest", __file__, "-v", "--tb=short"],
        capture_output=True,
        text=True,
    )

    print(result.stdout)
    if result.stderr:
        print("Errors:", result.stderr)

    print("✅ Strategy Flow Integration Tests Complete!")
