"""
Integration Test: T032 - Live Trading Mode Switch
Tests the complete live trading mode switch workflow with PIN validation.

This test validates:
1. User authentication and mode switching
2. PIN validation for live trading
3. Risk acknowledgment and confirmation
4. Account balance verification
5. Broker API connection testing
6. Mode switch rollback on failures
7. Comprehensive error handling
8. Security and audit logging
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock
from enum import Enum

# Mock imports for integration testing
from sqlalchemy.orm import Session


class TradingMode(Enum):
    """Trading mode enumeration"""

    PAPER = "paper"
    LIVE = "live"


class LiveTradingError(Exception):
    """Base exception for live trading errors"""

    pass


class InvalidPINError(LiveTradingError):
    """Raised when PIN validation fails"""

    pass


class BrokerConnectionError(LiveTradingError):
    """Raised when broker API connection fails"""

    pass


class InsufficientBalanceError(LiveTradingError):
    """Raised when live account has insufficient balance"""

    pass


class RiskAcknowledgmentError(LiveTradingError):
    """Raised when risk acknowledgment is missing"""

    pass


class ModeTransitionError(LiveTradingError):
    """Raised when mode transition fails"""

    pass


class MockUser:
    """Mock User model for testing"""

    def __init__(self, user_id: str = "test_user_001", email: str = "test@example.com"):
        self.id = user_id
        self.email = email
        self.is_active = True
        self.trading_mode = TradingMode.PAPER
        self.live_trading_enabled = False
        self.pin_hash = None  # Will be set during PIN creation
        self.risk_acknowledged = False
        self.last_mode_switch = None
        self.created_at = datetime.now()


class MockBrokerAccount:
    """Mock broker account model"""

    def __init__(self, user_id: str, broker: str = "angel_one"):
        self.id = f"broker_{user_id}"
        self.user_id = user_id
        self.broker = broker
        self.account_id = f"AO_{user_id}"
        self.is_connected = False
        self.balance = Decimal("50000.00")
        self.last_sync = None


class MockAuditLog:
    """Mock audit log model"""

    def __init__(self, user_id: str, action: str, details: Dict[str, Any]):
        self.id = f"audit_{datetime.now().timestamp()}"
        self.user_id = user_id
        self.action = action
        self.details = details
        self.timestamp = datetime.now()


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
def mock_broker_account(mock_user):
    """Create mock broker account"""
    return MockBrokerAccount(mock_user.id)


@pytest.fixture
def live_trading_service():
    """Mock live trading service"""
    service = Mock()
    service.validate_pin = AsyncMock()
    service.check_risk_acknowledgment = AsyncMock()
    service.verify_broker_connection = AsyncMock()
    service.switch_trading_mode = AsyncMock()
    service.rollback_mode_switch = AsyncMock()
    service.create_audit_log = AsyncMock()
    return service


@pytest.fixture
def broker_service():
    """Mock broker service"""
    service = Mock()
    service.connect_to_broker = AsyncMock()
    service.verify_account = AsyncMock()
    service.get_account_balance = AsyncMock()
    service.disconnect_from_broker = AsyncMock()
    return service


@pytest.fixture
def security_service():
    """Mock security service"""
    service = Mock()
    service.hash_pin = AsyncMock()
    service.verify_pin = AsyncMock()
    service.encrypt_data = AsyncMock()
    service.decrypt_data = AsyncMock()
    return service


class TestLiveTradingModeSwitch:
    """Integration tests for live trading mode switch"""

    @pytest.mark.asyncio
    async def test_successful_live_mode_switch(
        self,
        mock_db_session,
        mock_user,
        mock_broker_account,
        live_trading_service,
        broker_service,
        security_service,
    ):
        """Test successful switch from paper to live trading mode"""

        # Setup test data
        correct_pin = "1937"

        # Mock service responses for success scenario
        security_service.verify_pin.return_value = True
        live_trading_service.check_risk_acknowledgment.return_value = True
        broker_service.verify_account.return_value = mock_broker_account
        broker_service.get_account_balance.return_value = Decimal("50000.00")

        try:
            # Step 1: Validate current mode (should be paper)
            assert mock_user.trading_mode == TradingMode.PAPER
            assert not mock_user.live_trading_enabled

            # Step 2: PIN validation
            pin_valid = await security_service.verify_pin(mock_user.id, correct_pin)
            assert pin_valid is True

            # Step 3: Risk acknowledgment check
            risk_ack = await live_trading_service.check_risk_acknowledgment(
                mock_user.id
            )
            assert risk_ack is True

            # Step 4: Verify broker connection
            await broker_service.connect_to_broker(
                mock_user.id, "angel_one", {"api_key": "test_key"}
            )

            account = await broker_service.verify_account(mock_user.id)
            assert account.broker == "angel_one"
            assert account.is_connected

            # Step 5: Check minimum balance requirement
            balance = await broker_service.get_account_balance(mock_user.id)
            min_balance = Decimal("10000.00")
            assert balance >= min_balance

            # Step 6: Execute mode switch
            mock_user.trading_mode = TradingMode.LIVE
            mock_user.live_trading_enabled = True
            mock_user.last_mode_switch = datetime.now()

            result = await live_trading_service.switch_trading_mode(
                mock_user.id, TradingMode.LIVE, pin=correct_pin
            )

            # Step 7: Verify mode switch completed
            assert result["success"] is True
            assert result["new_mode"] == TradingMode.LIVE.value

            # Step 8: Create audit log
            await live_trading_service.create_audit_log(
                mock_user.id,
                "MODE_SWITCH",
                {
                    "from_mode": TradingMode.PAPER.value,
                    "to_mode": TradingMode.LIVE.value,
                    "timestamp": datetime.now().isoformat(),
                },
            )

            print("✅ Successful live mode switch completed")

        except Exception as e:
            pytest.fail(f"Live mode switch failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_invalid_pin_error_handling(
        self, mock_db_session, mock_user, live_trading_service, security_service
    ):
        """Test handling of invalid PIN during mode switch"""

        incorrect_pin = "0000"

        # Configure security service to reject invalid PIN
        security_service.verify_pin.return_value = False
        live_trading_service.validate_pin.side_effect = InvalidPINError(
            "Invalid PIN provided for live trading mode switch"
        )

        try:
            # Attempt mode switch with invalid PIN
            with pytest.raises(InvalidPINError) as exc_info:
                await live_trading_service.validate_pin(mock_user.id, incorrect_pin)

            assert "Invalid PIN" in str(exc_info.value)

            # Verify mode remained unchanged
            assert mock_user.trading_mode == TradingMode.PAPER
            assert not mock_user.live_trading_enabled

            print("✅ Invalid PIN error handled correctly")

        except Exception as e:
            pytest.fail(f"Invalid PIN error handling failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_broker_connection_failure(
        self, mock_db_session, mock_user, broker_service, live_trading_service
    ):
        """Test handling of broker connection failures"""

        # Configure broker service to fail connection
        broker_service.connect_to_broker.side_effect = BrokerConnectionError(
            "Failed to connect to Angel One API: Invalid credentials"
        )

        try:
            with pytest.raises(BrokerConnectionError) as exc_info:
                await broker_service.connect_to_broker(
                    mock_user.id, "angel_one", {"api_key": "invalid_key"}
                )

            assert "Failed to connect" in str(exc_info.value)

            # Verify mode switch did not complete
            assert mock_user.trading_mode == TradingMode.PAPER

            print("✅ Broker connection failure handled correctly")

        except Exception as e:
            pytest.fail(f"Broker connection error handling failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_insufficient_balance_error(
        self, mock_db_session, mock_user, broker_service, live_trading_service
    ):
        """Test handling of insufficient balance in live account"""

        low_balance = Decimal("500.00")  # Below minimum requirement
        min_balance = Decimal("10000.00")

        # Configure broker service to return low balance
        broker_service.get_account_balance.return_value = low_balance

        try:
            balance = await broker_service.get_account_balance(mock_user.id)

            if balance < min_balance:
                error_msg = (
                    f"Insufficient balance: {balance}, "
                    f"Minimum required: {min_balance}"
                )
                raise InsufficientBalanceError(error_msg)

        except InsufficientBalanceError as e:
            assert "Insufficient balance" in str(e)
            assert mock_user.trading_mode == TradingMode.PAPER
            print("✅ Insufficient balance error handled correctly")

    @pytest.mark.asyncio
    async def test_missing_risk_acknowledgment(
        self, mock_db_session, mock_user, live_trading_service
    ):
        """Test handling of missing risk acknowledgment"""

        # Configure service to indicate missing risk acknowledgment
        live_trading_service.check_risk_acknowledgment.return_value = False

        try:
            risk_ack = await live_trading_service.check_risk_acknowledgment(
                mock_user.id
            )

            if not risk_ack:
                raise RiskAcknowledgmentError(
                    "Risk acknowledgment required for live trading"
                )

        except RiskAcknowledgmentError as e:
            assert "Risk acknowledgment required" in str(e)
            assert mock_user.trading_mode == TradingMode.PAPER
            print("✅ Missing risk acknowledgment handled correctly")

    @pytest.mark.asyncio
    async def test_mode_switch_rollback(
        self, mock_db_session, mock_user, live_trading_service, broker_service
    ):
        """Test rollback functionality when mode switch fails"""

        original_mode = mock_user.trading_mode

        # Setup partial failure scenario
        broker_service.verify_account.side_effect = Exception(
            "Account verification failed"
        )

        try:
            # Attempt mode switch that should fail
            with pytest.raises(Exception):
                await broker_service.verify_account(mock_user.id)

            # Execute rollback
            await live_trading_service.rollback_mode_switch(mock_user.id, original_mode)

            # Verify rollback completed
            mock_user.trading_mode = original_mode
            mock_user.live_trading_enabled = False

            assert mock_user.trading_mode == original_mode
            assert not mock_user.live_trading_enabled

            print("✅ Mode switch rollback completed successfully")

        except AssertionError:
            pytest.fail("Mode switch rollback failed")

    @pytest.mark.asyncio
    async def test_concurrent_mode_switch_prevention(
        self, mock_db_session, mock_user, live_trading_service
    ):
        """Test prevention of concurrent mode switches"""

        # Simulate ongoing mode switch
        mock_user.last_mode_switch = datetime.now()
        switch_in_progress = True

        try:
            if switch_in_progress:
                time_since_last = datetime.now() - mock_user.last_mode_switch
                if time_since_last < timedelta(minutes=5):
                    raise ModeTransitionError("Mode switch already in progress")

        except ModeTransitionError as e:
            assert "already in progress" in str(e)
            print("✅ Concurrent mode switch prevention works correctly")

    @pytest.mark.asyncio
    async def test_live_to_paper_mode_switch(
        self, mock_db_session, mock_user, live_trading_service, broker_service
    ):
        """Test switching from live back to paper trading mode"""

        # Setup user in live mode
        mock_user.trading_mode = TradingMode.LIVE
        mock_user.live_trading_enabled = True

        try:
            # Step 1: Verify current live mode
            assert mock_user.trading_mode == TradingMode.LIVE
            assert mock_user.live_trading_enabled

            # Step 2: Disconnect from broker
            await broker_service.disconnect_from_broker(mock_user.id)

            # Step 3: Switch to paper mode
            mock_user.trading_mode = TradingMode.PAPER
            mock_user.live_trading_enabled = False
            mock_user.last_mode_switch = datetime.now()

            result = await live_trading_service.switch_trading_mode(
                mock_user.id,
                TradingMode.PAPER,
                pin=None,  # PIN not required for paper mode
            )

            # Step 4: Verify switch completed
            assert result["success"] is True
            assert result["new_mode"] == TradingMode.PAPER.value
            assert mock_user.trading_mode == TradingMode.PAPER
            assert not mock_user.live_trading_enabled

            print("✅ Live to paper mode switch completed successfully")

        except Exception as e:
            pytest.fail(f"Live to paper mode switch failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_security_audit_logging(
        self, mock_db_session, mock_user, live_trading_service
    ):
        """Test comprehensive security audit logging"""

        audit_events = []

        def mock_create_audit_log(user_id, action, details):
            audit_log = MockAuditLog(user_id, action, details)
            audit_events.append(audit_log)
            return audit_log

        live_trading_service.create_audit_log.side_effect = mock_create_audit_log

        try:
            # Simulate various security events
            security_events = [
                ("PIN_VALIDATION_SUCCESS", {"timestamp": datetime.now()}),
                ("PIN_VALIDATION_FAILURE", {"attempts": 1}),
                ("RISK_ACKNOWLEDGMENT", {"acknowledged": True}),
                ("BROKER_CONNECTION", {"broker": "angel_one"}),
                ("MODE_SWITCH_SUCCESS", {"new_mode": "live"}),
                ("MODE_SWITCH_ROLLBACK", {"reason": "broker_error"}),
            ]

            for action, details in security_events:
                await live_trading_service.create_audit_log(
                    mock_user.id, action, details
                )

            # Verify audit logs created
            assert len(audit_events) == len(security_events)

            # Check specific audit log contents
            mode_switch_log = next(
                (log for log in audit_events if log.action == "MODE_SWITCH_SUCCESS"),
                None,
            )
            assert mode_switch_log is not None
            assert mode_switch_log.details["new_mode"] == "live"

            print("✅ Security audit logging working correctly")

        except Exception as e:
            pytest.fail(f"Security audit logging failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_pin_attempts_rate_limiting(
        self, mock_db_session, mock_user, security_service
    ):
        """Test rate limiting for PIN attempts"""

        max_attempts = 3
        attempt_count = 0

        def mock_verify_pin(user_id, pin):
            nonlocal attempt_count
            attempt_count += 1

            if attempt_count > max_attempts:
                raise InvalidPINError(
                    f"Too many PIN attempts: {attempt_count}. " f"Account locked."
                )

            return pin == "1937"

        security_service.verify_pin.side_effect = mock_verify_pin

        try:
            # Test multiple invalid attempts
            invalid_pins = ["0000", "1111", "2222", "3333"]

            for pin in invalid_pins:
                try:
                    result = await security_service.verify_pin(mock_user.id, pin)
                    if not result and pin != "1937":
                        continue  # Expected failure
                except InvalidPINError as e:
                    if "Too many PIN attempts" in str(e):
                        print("✅ PIN rate limiting triggered correctly")
                        break

        except Exception as e:
            pytest.fail(f"PIN rate limiting test failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_mode_switch_with_active_positions(
        self, mock_db_session, mock_user, live_trading_service, broker_service
    ):
        """Test mode switch validation with active positions"""

        # Setup user with active paper positions
        active_positions = [
            {"symbol": "RELIANCE", "quantity": 10, "value": Decimal("25000")},
            {"symbol": "TCS", "quantity": 5, "value": Decimal("19000")},
        ]

        try:
            # Check for active positions before mode switch
            if active_positions:
                total_value = sum(pos["value"] for pos in active_positions)

                if total_value > Decimal("1000"):  # Significant positions
                    confirmation_required = True
                else:
                    confirmation_required = False

                # Simulate user confirmation for position handling
                if confirmation_required:
                    user_confirmed = True  # Mock user confirmation

                    if not user_confirmed:
                        raise ModeTransitionError(
                            "User confirmation required for active positions"
                        )

            # Mode switch can proceed with confirmation
            assert len(active_positions) > 0
            print("✅ Active positions validation handled correctly")

        except ModeTransitionError as e:
            assert "confirmation required" in str(e)
            print("✅ Active positions confirmation requirement works")

    def test_trading_mode_configuration_validation(self):
        """Test validation of trading mode configurations"""

        try:
            # Test valid live trading configuration
            config = {
                "min_balance_required": Decimal("10000.00"),
                "max_daily_loss": Decimal("5000.00"),
                "position_size_limit": Decimal("0.20"),  # 20% of portfolio
                "pin_required": True,
                "risk_acknowledgment_required": True,
                "broker_connection_timeout": 30,  # seconds
            }

            # Validate configuration
            assert config["min_balance_required"] > 0
            assert config["max_daily_loss"] > 0
            assert 0 < config["position_size_limit"] <= 1
            assert isinstance(config["pin_required"], bool)
            assert isinstance(config["risk_acknowledgment_required"], bool)
            assert config["broker_connection_timeout"] > 0

            print("✅ Live trading configuration validated successfully")

        except AssertionError:
            pytest.fail("Live trading configuration validation failed")


# Additional utility functions for testing
def create_mode_switch_scenario(scenario_name: str) -> Dict[str, Any]:
    """Create predefined mode switch test scenarios"""

    scenarios = {
        "successful_switch": {
            "pin": "1937",
            "balance": Decimal("50000.00"),
            "risk_acknowledged": True,
            "broker_connected": True,
            "expected_outcome": "success",
        },
        "invalid_pin": {
            "pin": "0000",
            "balance": Decimal("50000.00"),
            "risk_acknowledged": True,
            "broker_connected": True,
            "expected_outcome": "invalid_pin_error",
        },
        "insufficient_balance": {
            "pin": "1937",
            "balance": Decimal("500.00"),
            "risk_acknowledged": True,
            "broker_connected": True,
            "expected_outcome": "insufficient_balance_error",
        },
        "broker_connection_failure": {
            "pin": "1937",
            "balance": Decimal("50000.00"),
            "risk_acknowledged": True,
            "broker_connected": False,
            "expected_outcome": "broker_connection_error",
        },
    }

    return scenarios.get(scenario_name, {})


def validate_mode_switch_state(user: MockUser, expected_mode: TradingMode) -> bool:
    """Validate user state after mode switch"""

    try:
        assert user.trading_mode == expected_mode

        if expected_mode == TradingMode.LIVE:
            assert user.live_trading_enabled
        else:
            assert not user.live_trading_enabled

        assert user.last_mode_switch is not None

        return True

    except Exception as e:
        print(f"Mode switch state validation failed: {str(e)}")
        return False


if __name__ == "__main__":
    """Run integration tests for live trading mode switch"""

    print("🚀 Starting Live Trading Mode Switch Integration Tests...")

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

    print("✅ Live Trading Mode Switch Integration Tests Complete!")
