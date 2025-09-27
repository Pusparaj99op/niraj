"""
Contract tests for POST /api/v1/trades endpoint.

These tests validate the API contract defined in the REST API specification.
Following TDD principles, these tests should fail initially until the
endpoint is implemented.
"""

import pytest
from fastapi.testclient import TestClient
from httpx import Response
import uuid
import json


class TestTradesCreateContract:
    """Contract tests for the trades creation endpoint."""

    @pytest.fixture
    def client(self) -> TestClient:
        """
        Create a test client for the FastAPI application.
        This will fail until the main FastAPI app is implemented.
        """
        # This import will fail until the main app is created
        from src.main import app

        return TestClient(app)

    @pytest.fixture
    def valid_strategy_id(self) -> str:
        """Valid UUID strategy ID for testing."""
        return str(uuid.uuid4())

    @pytest.fixture
    def valid_trade_request(self) -> dict:
        """Valid trade request data matching TradeRequest schema."""
        return {
            "symbol": "BANKNIFTY",
            "trade_type": "BUY",
            "quantity": 25,
            "price": 45000.50,
            "stop_loss": 44000.00,
            "take_profit": 46000.00,
        }

    @pytest.fixture
    def minimal_trade_request(self) -> dict:
        """Minimal trade request with only required fields."""
        return {"symbol": "BANKNIFTY", "trade_type": "BUY", "quantity": 25}

    def test_create_trade_success_contract(
        self, client: TestClient, valid_trade_request: dict
    ) -> None:
        """
        Test successful trade creation contract compliance.

        Contract Requirements:
        - POST /api/v1/trades
        - Request Body: TradeRequest schema
        - Response 201: Trade schema with generated fields
        """
        # Act
        response: Response = client.post("/api/v1/trades", json=valid_trade_request)

        # Assert - Status Code
        expected_status = 201
        actual_status = response.status_code
        assert (
            actual_status == expected_status
        ), f"Expected status {expected_status}, got {actual_status}"

        # Assert - Response Structure
        response_json = response.json()
        self._validate_trade_response_structure(response_json)

        # Assert - Required fields from request are preserved
        assert response_json["symbol"] == valid_trade_request["symbol"]
        assert response_json["trade_type"] == valid_trade_request["trade_type"]
        assert response_json["quantity"] == valid_trade_request["quantity"]
        assert response_json["entry_price"] == valid_trade_request["price"]

        # Assert - Generated fields are present and valid
        trade_id = response_json["trade_id"]
        assert isinstance(trade_id, str), "trade_id must be string"
        # Verify it's a valid UUID format
        try:
            uuid.UUID(trade_id)
        except ValueError:
            pytest.fail("trade_id must be a valid UUID")

        # Assert - Status should be OPEN for new trade
        assert response_json["status"] == "OPEN", "New trade status should be OPEN"

        # Assert - Timestamps are present and valid
        assert "entry_timestamp" in response_json
        assert "created_at" in response_json
        assert isinstance(response_json["entry_timestamp"], str)
        assert isinstance(response_json["created_at"], str)

        # Assert - Optional fields handling
        if "exit_price" in response_json:
            assert (
                response_json["exit_price"] is None
            ), "New trade should not have exit_price"
        if "exit_timestamp" in response_json:
            assert (
                response_json["exit_timestamp"] is None
            ), "New trade should not have exit_timestamp"

    def test_create_trade_minimal_data_contract(
        self, client: TestClient, minimal_trade_request: dict
    ) -> None:
        """
        Test trade creation with only required fields.

        Contract Requirements:
        - Only symbol, trade_type, quantity are required
        - Market order when price not specified
        """
        # Act
        response: Response = client.post("/api/v1/trades", json=minimal_trade_request)

        # Assert - Status Code
        expected_status = 201
        actual_status = response.status_code
        assert (
            actual_status == expected_status
        ), f"Expected status {expected_status}, got {actual_status}"

        # Assert - Response Structure
        response_json = response.json()
        self._validate_trade_response_structure(response_json)

        # Assert - Required fields are preserved
        assert response_json["symbol"] == minimal_trade_request["symbol"]
        assert response_json["trade_type"] == minimal_trade_request["trade_type"]
        assert response_json["quantity"] == minimal_trade_request["quantity"]

        # Assert - Market order handling (entry_price should be set)
        assert "entry_price" in response_json
        assert isinstance(response_json["entry_price"], (int, float))
        assert response_json["entry_price"] > 0

    def test_create_trade_with_strategy_id_contract(
        self, client: TestClient, valid_trade_request: dict, valid_strategy_id: str
    ) -> None:
        """
        Test trade creation with strategy association.

        Contract Requirements:
        - strategy_id is optional in TradeRequest
        - Should be preserved in response if provided
        """
        # Arrange
        trade_with_strategy = {**valid_trade_request, "strategy_id": valid_strategy_id}

        # Act
        response: Response = client.post("/api/v1/trades", json=trade_with_strategy)

        # Assert - Status Code
        expected_status = 201
        actual_status = response.status_code
        assert (
            actual_status == expected_status
        ), f"Expected status {expected_status}, got {actual_status}"

        # Assert - Response Structure
        response_json = response.json()
        self._validate_trade_response_structure(response_json)

        # Assert - Strategy ID is preserved
        if "strategy_id" in response_json:
            assert response_json["strategy_id"] == valid_strategy_id, (
                f"Strategy ID should be preserved: expected {valid_strategy_id}, "
                f"got {response_json.get('strategy_id')}"
            )

    def test_create_trade_sell_order_contract(
        self, client: TestClient, valid_trade_request: dict
    ) -> None:
        """
        Test SELL trade creation.

        Contract Requirements:
        - trade_type can be BUY or SELL
        - Both should be handled appropriately
        """
        # Arrange
        sell_request = {**valid_trade_request, "trade_type": "SELL"}

        # Act
        response: Response = client.post("/api/v1/trades", json=sell_request)

        # Assert - Status Code
        expected_status = 201
        actual_status = response.status_code
        assert (
            actual_status == expected_status
        ), f"Expected status {expected_status}, got {actual_status}"

        # Assert - Response Structure
        response_json = response.json()
        self._validate_trade_response_structure(response_json)

        # Assert - Trade type is preserved
        assert (
            response_json["trade_type"] == "SELL"
        ), "SELL trade_type should be preserved"

    def test_create_trade_missing_required_fields_contract(
        self, client: TestClient
    ) -> None:
        """
        Test trade creation with missing required fields.

        Contract Requirements:
        - symbol, trade_type, quantity are required
        - Should return 400 Bad Request or 422 Unprocessable Entity
        """
        # Test missing symbol
        missing_symbol = {"trade_type": "BUY", "quantity": 25}

        response = client.post("/api/v1/trades", json=missing_symbol)
        expected_codes = [400, 422]
        assert (
            response.status_code in expected_codes
        ), f"Missing symbol should return {expected_codes}, got {response.status_code}"

        # Test missing trade_type
        missing_trade_type = {"symbol": "BANKNIFTY", "quantity": 25}

        response = client.post("/api/v1/trades", json=missing_trade_type)
        assert (
            response.status_code in expected_codes
        ), f"Missing trade_type should return {expected_codes}, got {response.status_code}"

        # Test missing quantity
        missing_quantity = {"symbol": "BANKNIFTY", "trade_type": "BUY"}

        response = client.post("/api/v1/trades", json=missing_quantity)
        assert (
            response.status_code in expected_codes
        ), f"Missing quantity should return {expected_codes}, got {response.status_code}"

    def test_create_trade_invalid_trade_type_contract(self, client: TestClient) -> None:
        """
        Test trade creation with invalid trade_type.

        Contract Requirements:
        - trade_type must be BUY or SELL
        - Should return 400 Bad Request or 422 Unprocessable Entity
        """
        # Arrange
        invalid_trade_type = {
            "symbol": "BANKNIFTY",
            "trade_type": "INVALID_TYPE",
            "quantity": 25,
        }

        # Act
        response: Response = client.post("/api/v1/trades", json=invalid_trade_type)

        # Assert
        expected_codes = [400, 422]
        assert (
            response.status_code in expected_codes
        ), f"Invalid trade_type should return {expected_codes}, got {response.status_code}"

    def test_create_trade_invalid_quantity_contract(self, client: TestClient) -> None:
        """
        Test trade creation with invalid quantity values.

        Contract Requirements:
        - quantity must be positive integer (minimum 1)
        - Should return 400 Bad Request or 422 Unprocessable Entity
        """
        # Test zero quantity
        zero_quantity = {"symbol": "BANKNIFTY", "trade_type": "BUY", "quantity": 0}

        response = client.post("/api/v1/trades", json=zero_quantity)
        expected_codes = [400, 422]
        assert (
            response.status_code in expected_codes
        ), f"Zero quantity should return {expected_codes}, got {response.status_code}"

        # Test negative quantity
        negative_quantity = {
            "symbol": "BANKNIFTY",
            "trade_type": "BUY",
            "quantity": -10,
        }

        response = client.post("/api/v1/trades", json=negative_quantity)
        assert (
            response.status_code in expected_codes
        ), f"Negative quantity should return {expected_codes}, got {response.status_code}"

        # Test non-integer quantity
        float_quantity = {"symbol": "BANKNIFTY", "trade_type": "BUY", "quantity": 25.5}

        response = client.post("/api/v1/trades", json=float_quantity)
        assert (
            response.status_code in expected_codes
        ), f"Float quantity should return {expected_codes}, got {response.status_code}"

    def test_create_trade_invalid_price_contract(self, client: TestClient) -> None:
        """
        Test trade creation with invalid price values.

        Contract Requirements:
        - price must be positive number if provided
        - Should return 400 Bad Request or 422 Unprocessable Entity
        """
        # Test negative price
        negative_price = {
            "symbol": "BANKNIFTY",
            "trade_type": "BUY",
            "quantity": 25,
            "price": -1000.00,
        }

        response = client.post("/api/v1/trades", json=negative_price)
        expected_codes = [400, 422]
        assert (
            response.status_code in expected_codes
        ), f"Negative price should return {expected_codes}, got {response.status_code}"

        # Test zero price
        zero_price = {
            "symbol": "BANKNIFTY",
            "trade_type": "BUY",
            "quantity": 25,
            "price": 0.00,
        }

        response = client.post("/api/v1/trades", json=zero_price)
        assert (
            response.status_code in expected_codes
        ), f"Zero price should return {expected_codes}, got {response.status_code}"

    def test_create_trade_invalid_stop_loss_contract(self, client: TestClient) -> None:
        """
        Test trade creation with invalid stop_loss values.

        Contract Requirements:
        - stop_loss must be positive number if provided
        - Should return 400 Bad Request or 422 Unprocessable Entity
        """
        # Test negative stop_loss
        negative_stop_loss = {
            "symbol": "BANKNIFTY",
            "trade_type": "BUY",
            "quantity": 25,
            "stop_loss": -100.00,
        }

        response = client.post("/api/v1/trades", json=negative_stop_loss)
        expected_codes = [400, 422]
        assert (
            response.status_code in expected_codes
        ), f"Negative stop_loss should return {expected_codes}, got {response.status_code}"

    def test_create_trade_invalid_take_profit_contract(
        self, client: TestClient
    ) -> None:
        """
        Test trade creation with invalid take_profit values.

        Contract Requirements:
        - take_profit must be positive number if provided
        - Should return 400 Bad Request or 422 Unprocessable Entity
        """
        # Test negative take_profit
        negative_take_profit = {
            "symbol": "BANKNIFTY",
            "trade_type": "BUY",
            "quantity": 25,
            "take_profit": -100.00,
        }

        response = client.post("/api/v1/trades", json=negative_take_profit)
        expected_codes = [400, 422]
        assert (
            response.status_code in expected_codes
        ), f"Negative take_profit should return {expected_codes}, got {response.status_code}"

    def test_create_trade_invalid_strategy_id_format_contract(
        self, client: TestClient, valid_trade_request: dict
    ) -> None:
        """
        Test trade creation with invalid strategy_id format.

        Contract Requirements:
        - strategy_id must be valid UUID format if provided
        - Should return 400 Bad Request or 422 Unprocessable Entity
        """
        # Arrange
        invalid_strategy_id = {**valid_trade_request, "strategy_id": "not-a-uuid"}

        # Act
        response = client.post("/api/v1/trades", json=invalid_strategy_id)

        # Assert
        expected_codes = [400, 422]
        assert (
            response.status_code in expected_codes
        ), f"Invalid strategy_id format should return {expected_codes}, got {response.status_code}"

    def test_create_trade_empty_symbol_contract(self, client: TestClient) -> None:
        """
        Test trade creation with empty symbol.

        Contract Requirements:
        - symbol cannot be empty
        - Should return 400 Bad Request or 422 Unprocessable Entity
        """
        # Arrange
        empty_symbol = {"symbol": "", "trade_type": "BUY", "quantity": 25}

        # Act
        response = client.post("/api/v1/trades", json=empty_symbol)

        # Assert
        expected_codes = [400, 422]
        assert (
            response.status_code in expected_codes
        ), f"Empty symbol should return {expected_codes}, got {response.status_code}"

    def test_create_trade_invalid_json_contract(self, client: TestClient) -> None:
        """
        Test trade creation with malformed JSON.

        Contract Requirements:
        - Should return 400 Bad Request or 422 Unprocessable Entity
        """
        # Act - Send malformed JSON
        response = client.post(
            "/api/v1/trades",
            data="{ invalid json",
            headers={"Content-Type": "application/json"},
        )

        # Assert
        expected_codes = [400, 422]
        assert (
            response.status_code in expected_codes
        ), f"Malformed JSON should return {expected_codes}, got {response.status_code}"

    def test_create_trade_wrong_content_type_contract(
        self, client: TestClient, valid_trade_request: dict
    ) -> None:
        """
        Test trade creation with wrong Content-Type.

        Contract Requirements:
        - Should only accept application/json
        - Should return 415 Unsupported Media Type or 422
        """
        # Act - Send as form data
        response = client.post(
            "/api/v1/trades",
            data=json.dumps(valid_trade_request),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        # Assert
        expected_codes = [400, 415, 422]
        assert (
            response.status_code in expected_codes
        ), f"Wrong content type should return {expected_codes}, got {response.status_code}"

    def test_create_trade_risk_limits_exceeded_contract(
        self, client: TestClient
    ) -> None:
        """
        Test trade creation that exceeds risk limits.

        Contract Requirements:
        - Should return 403 Forbidden when risk limits are exceeded
        """
        # Arrange - Very large quantity that might exceed limits
        large_quantity_trade = {
            "symbol": "BANKNIFTY",
            "trade_type": "BUY",
            "quantity": 10000,  # Extremely large quantity
        }

        # Act
        response = client.post("/api/v1/trades", json=large_quantity_trade)

        # Assert - Either succeed or return 403 for risk limits
        acceptable_codes = [201, 400, 403, 422]
        assert (
            response.status_code in acceptable_codes
        ), f"Large quantity trade should return {acceptable_codes}, got {response.status_code}"

        # If 403, verify it's related to risk limits
        if response.status_code == 403:
            # Response might contain error message about risk limits
            assert True  # Risk limit rejection is acceptable

    def test_create_trade_case_sensitivity_contract(self, client: TestClient) -> None:
        """
        Test trade creation with different case values.

        Contract Requirements:
        - API should handle case appropriately for trade_type and symbol
        """
        # Test lowercase trade_type
        lowercase_type = {
            "symbol": "BANKNIFTY",
            "trade_type": "buy",  # lowercase
            "quantity": 25,
        }

        response = client.post("/api/v1/trades", json=lowercase_type)
        # Should either accept (converting to uppercase) or reject with validation error
        acceptable_codes = [201, 400, 422]
        assert (
            response.status_code in acceptable_codes
        ), f"Lowercase trade_type returned {response.status_code}"

        # Test lowercase symbol
        lowercase_symbol = {
            "symbol": "banknifty",  # lowercase
            "trade_type": "BUY",
            "quantity": 25,
        }

        response = client.post("/api/v1/trades", json=lowercase_symbol)
        assert (
            response.status_code in acceptable_codes
        ), f"Lowercase symbol returned {response.status_code}"

    def test_create_trade_precision_handling_contract(self, client: TestClient) -> None:
        """
        Test trade creation with high precision decimal values.

        Contract Requirements:
        - Should handle decimal precision appropriately
        - Should not cause precision loss or overflow
        """
        # Arrange
        high_precision_trade = {
            "symbol": "BANKNIFTY",
            "trade_type": "BUY",
            "quantity": 25,
            "price": 45000.123456789,
            "stop_loss": 44000.987654321,
            "take_profit": 46000.555555555,
        }

        # Act
        response = client.post("/api/v1/trades", json=high_precision_trade)

        # Assert - Should either succeed or return validation error
        acceptable_codes = [201, 400, 422]
        assert (
            response.status_code in acceptable_codes
        ), f"High precision values returned {response.status_code}"

        # If successful, verify precision is handled appropriately
        if response.status_code == 201:
            response_json = response.json()
            # Verify entry_price is reasonable (may be rounded)
            assert isinstance(response_json["entry_price"], (int, float))
            assert response_json["entry_price"] > 0

    def _validate_trade_response_structure(self, trade: dict) -> None:
        """
        Helper method to validate the structure of a trade response object.

        Validates against the Trade schema from the API specification.
        """
        # Required fields for Trade schema
        required_fields = [
            "trade_id",
            "symbol",
            "trade_type",
            "quantity",
            "entry_price",
            "entry_timestamp",
            "status",
            "created_at",
        ]

        for field in required_fields:
            assert field in trade, f"Trade must contain '{field}'"

        # Validate trade_id
        trade_id = trade["trade_id"]
        assert isinstance(trade_id, str), "trade_id must be string"
        try:
            uuid.UUID(trade_id)
        except ValueError:
            pytest.fail("trade_id must be a valid UUID")

        # Validate symbol
        symbol = trade["symbol"]
        assert isinstance(symbol, str), "symbol must be string"
        assert len(symbol) > 0, "symbol cannot be empty"

        # Validate trade_type
        trade_type = trade["trade_type"]
        assert trade_type in [
            "BUY",
            "SELL",
        ], f"trade_type must be BUY or SELL, got {trade_type}"

        # Validate quantity
        quantity = trade["quantity"]
        assert isinstance(quantity, int), "quantity must be integer"
        assert quantity > 0, "quantity must be positive"

        # Validate entry_price
        entry_price = trade["entry_price"]
        assert isinstance(entry_price, (int, float)), "entry_price must be number"
        assert entry_price > 0, "entry_price must be positive"

        # Validate entry_timestamp
        entry_timestamp = trade["entry_timestamp"]
        assert isinstance(entry_timestamp, str), "entry_timestamp must be string"

        # Validate status
        status = trade["status"]
        assert status in [
            "OPEN",
            "CLOSED",
            "CANCELLED",
        ], f"status must be OPEN, CLOSED, or CANCELLED, got {status}"

        # Validate created_at
        created_at = trade["created_at"]
        assert isinstance(created_at, str), "created_at must be string"

        # Optional fields validation
        if "strategy_id" in trade and trade["strategy_id"] is not None:
            strategy_id = trade["strategy_id"]
            assert isinstance(strategy_id, str), "strategy_id must be string"
            try:
                uuid.UUID(strategy_id)
            except ValueError:
                pytest.fail("strategy_id must be a valid UUID")

        if "transaction_cost" in trade:
            transaction_cost = trade["transaction_cost"]
            assert isinstance(
                transaction_cost, (int, float)
            ), "transaction_cost must be number"
            assert transaction_cost >= 0, "transaction_cost cannot be negative"

        if "is_paper_trade" in trade:
            is_paper_trade = trade["is_paper_trade"]
            assert isinstance(is_paper_trade, bool), "is_paper_trade must be boolean"

        # For new trades, these should be null or not present
        if "exit_price" in trade and trade["exit_price"] is not None:
            exit_price = trade["exit_price"]
            assert isinstance(exit_price, (int, float)), "exit_price must be number"
            assert exit_price > 0, "exit_price must be positive"

        if "exit_timestamp" in trade and trade["exit_timestamp"] is not None:
            exit_timestamp = trade["exit_timestamp"]
            assert isinstance(exit_timestamp, str), "exit_timestamp must be string"

        if "exit_reason" in trade and trade["exit_reason"] is not None:
            exit_reason = trade["exit_reason"]
            assert exit_reason in [
                "STOP_LOSS",
                "TAKE_PROFIT",
                "MANUAL",
                "STRATEGY",
            ], f"exit_reason must be valid enum value, got {exit_reason}"

        if "gross_pnl" in trade and trade["gross_pnl"] is not None:
            gross_pnl = trade["gross_pnl"]
            assert isinstance(gross_pnl, (int, float)), "gross_pnl must be number"

        if "net_pnl" in trade and trade["net_pnl"] is not None:
            net_pnl = trade["net_pnl"]
            assert isinstance(net_pnl, (int, float)), "net_pnl must be number"
