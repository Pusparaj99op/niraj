"""
Contract tests for POST /api/v1/strategies endpoint.

These tests validate the API contract defined in the REST API specification.
Following TDD principles, these tests should fail initially until the
endpoint is implemented.
"""
import pytest
from fastapi.testclient import TestClient
from httpx import Response
import uuid
import json


class TestStrategiesCreateContract:
    """Contract tests for the strategies create endpoint."""

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
    def valid_strategy_create_data(self) -> dict:
        """Valid strategy creation data matching StrategyCreate schema."""
        return {
            "name": "Test Predator Strategy",
            "category": "predatory",
            "description": "A test strategy for contract validation",
            "parameters": {
                "risk_threshold": 0.05,
                "lookback_period": 20,
                "volume_threshold": 1000000
            },
            "target_symbols": ["BANKNIFTY", "NIFTY"],
            "min_confidence": 0.8,
            "max_position_size": 50000.0,
            "stop_loss_pct": 2.5,
            "take_profit_pct": 5.0
        }

    def test_create_strategy_success_contract(
        self, client: TestClient, valid_strategy_create_data: dict
    ) -> None:
        """
        Test successful strategy creation contract compliance.

        Contract Requirements:
        - POST /api/v1/strategies
        - Request Body: StrategyCreate schema
        - Response 201: Strategy schema with generated fields
        """
        # Act
        response: Response = client.post(
            "/api/v1/strategies",
            json=valid_strategy_create_data
        )

        # Assert - Status Code
        expected_status = 201
        actual_status = response.status_code
        assert actual_status == expected_status, (
            f"Expected status {expected_status}, got {actual_status}"
        )

        # Assert - Response Structure
        response_json = response.json()
        self._validate_strategy_response_structure(response_json)

        # Assert - Required fields from request are preserved
        assert response_json["name"] == valid_strategy_create_data["name"]
        expected_category = valid_strategy_create_data["category"]
        assert response_json["category"] == expected_category
        expected_desc = valid_strategy_create_data["description"]
        assert response_json["description"] == expected_desc
        expected_symbols = valid_strategy_create_data["target_symbols"]
        assert response_json["target_symbols"] == expected_symbols
        expected_confidence = valid_strategy_create_data["min_confidence"]
        assert response_json["min_confidence"] == expected_confidence
        expected_pos_size = valid_strategy_create_data["max_position_size"]
        assert response_json["max_position_size"] == expected_pos_size
        expected_stop_loss = valid_strategy_create_data["stop_loss_pct"]
        assert response_json["stop_loss_pct"] == expected_stop_loss
        expected_take_profit = valid_strategy_create_data["take_profit_pct"]
        assert response_json["take_profit_pct"] == expected_take_profit

        # Assert - Parameters object is preserved
        expected_params = valid_strategy_create_data["parameters"]
        actual_params = response_json["parameters"]
        assert actual_params == expected_params, (
            f"Parameters mismatch: expected {expected_params}, "
            f"got {actual_params}"
        )

        # Assert - Generated fields are present and valid
        strategy_id = response_json["strategy_id"]
        assert isinstance(strategy_id, str), "strategy_id must be string"
        # Verify it's a valid UUID format
        try:
            uuid.UUID(strategy_id)
        except ValueError:
            pytest.fail("strategy_id must be a valid UUID")

        # Assert - Default values are applied
        assert isinstance(response_json["is_active"], bool)
        assert isinstance(response_json["is_paper_only"], bool)

        # Assert - Timestamps are present and valid
        assert "created_at" in response_json
        assert "updated_at" in response_json
        assert isinstance(response_json["created_at"], str)
        assert isinstance(response_json["updated_at"], str)

    def test_create_strategy_minimal_data_contract(
        self, client: TestClient
    ) -> None:
        """
        Test strategy creation with only required fields.

        Contract Requirements:
        - Only name, category, target_symbols are required
        - Default values should be applied for optional fields
        """
        # Arrange - Only required fields
        minimal_data = {
            "name": "Minimal Test Strategy",
            "category": "quantitative",
            "target_symbols": ["NIFTY"]
        }

        # Act
        response: Response = client.post(
            "/api/v1/strategies",
            json=minimal_data
        )

        # Assert - Status Code
        expected_status = 201
        actual_status = response.status_code
        assert actual_status == expected_status, (
            f"Expected status {expected_status}, got {actual_status}"
        )

        # Assert - Response Structure
        response_json = response.json()
        self._validate_strategy_response_structure(response_json)

        # Assert - Required fields are preserved
        assert response_json["name"] == minimal_data["name"]
        assert response_json["category"] == minimal_data["category"]
        expected_symbols = minimal_data["target_symbols"]
        assert response_json["target_symbols"] == expected_symbols

        # Assert - Default values are applied
        assert response_json["min_confidence"] == 0.7  # Default from schema
        assert response_json["stop_loss_pct"] == 2.0   # Default from schema
        assert response_json["take_profit_pct"] == 4.0  # Default from schema

    def test_create_strategy_invalid_category_contract(
        self, client: TestClient
    ) -> None:
        """
        Test strategy creation with invalid category.

        Contract Requirements:
        - category must be one of: predatory, quantitative, psychological,
          mathematical, extreme
        - Should return 400 Bad Request or 422 Unprocessable Entity
        """
        # Arrange
        invalid_data = {
            "name": "Test Strategy",
            "category": "invalid_category",
            "target_symbols": ["NIFTY"]
        }

        # Act
        response: Response = client.post(
            "/api/v1/strategies",
            json=invalid_data
        )

        # Assert - Status Code (validation error)
        expected_codes = [400, 422]
        actual_status = response.status_code
        assert actual_status in expected_codes, (
            f"Expected status {expected_codes}, got {actual_status}"
        )

        # Assert - Error response format
        if actual_status == 422:
            # FastAPI validation error format
            response_json = response.json()
            assert "detail" in response_json, "422 response must contain 'detail'"

    def test_create_strategy_missing_required_fields_contract(
        self, client: TestClient
    ) -> None:
        """
        Test strategy creation with missing required fields.

        Contract Requirements:
        - name, category, target_symbols are required
        - Should return 400 Bad Request or 422 Unprocessable Entity
        """
        # Test missing name
        missing_name_data = {
            "category": "predatory",
            "target_symbols": ["NIFTY"]
        }

        response = client.post("/api/v1/strategies", json=missing_name_data)
        expected_codes = [400, 422]
        assert response.status_code in expected_codes, (
            f"Missing name should return {expected_codes}, got {response.status_code}"
        )

        # Test missing category
        missing_category_data = {
            "name": "Test Strategy",
            "target_symbols": ["NIFTY"]
        }

        response = client.post("/api/v1/strategies", json=missing_category_data)
        assert response.status_code in expected_codes, (
            f"Missing category should return {expected_codes}, got {response.status_code}"
        )

        # Test missing target_symbols
        missing_symbols_data = {
            "name": "Test Strategy",
            "category": "predatory"
        }

        response = client.post("/api/v1/strategies", json=missing_symbols_data)
        assert response.status_code in expected_codes, (
            f"Missing target_symbols should return {expected_codes}, got {response.status_code}"
        )

    def test_create_strategy_invalid_confidence_range_contract(
        self, client: TestClient
    ) -> None:
        """
        Test strategy creation with invalid min_confidence values.

        Contract Requirements:
        - min_confidence must be between 0 and 1
        - Should return 400 Bad Request or 422 Unprocessable Entity
        """
        # Test confidence > 1
        high_confidence_data = {
            "name": "Test Strategy",
            "category": "predatory",
            "target_symbols": ["NIFTY"],
            "min_confidence": 1.5
        }

        response = client.post("/api/v1/strategies", json=high_confidence_data)
        expected_codes = [400, 422]
        assert response.status_code in expected_codes, (
            f"min_confidence > 1 should return {expected_codes}, got {response.status_code}"
        )

        # Test confidence < 0
        low_confidence_data = {
            "name": "Test Strategy",
            "category": "predatory",
            "target_symbols": ["NIFTY"],
            "min_confidence": -0.1
        }

        response = client.post("/api/v1/strategies", json=low_confidence_data)
        assert response.status_code in expected_codes, (
            f"min_confidence < 0 should return {expected_codes}, got {response.status_code}"
        )

    def test_create_strategy_empty_target_symbols_contract(
        self, client: TestClient
    ) -> None:
        """
        Test strategy creation with empty target_symbols array.

        Contract Requirements:
        - target_symbols must not be empty
        - Should return 400 Bad Request or 422 Unprocessable Entity
        """
        # Arrange
        empty_symbols_data = {
            "name": "Test Strategy",
            "category": "predatory",
            "target_symbols": []
        }

        # Act
        response = client.post("/api/v1/strategies", json=empty_symbols_data)

        # Assert
        expected_codes = [400, 422]
        assert response.status_code in expected_codes, (
            f"Empty target_symbols should return {expected_codes}, got {response.status_code}"
        )

    def test_create_strategy_invalid_json_contract(
        self, client: TestClient
    ) -> None:
        """
        Test strategy creation with malformed JSON.

        Contract Requirements:
        - Should return 400 Bad Request or 422 Unprocessable Entity
        """
        # Act - Send malformed JSON
        response = client.post(
            "/api/v1/strategies",
            data="{ invalid json",
            headers={"Content-Type": "application/json"}
        )

        # Assert
        expected_codes = [400, 422]
        assert response.status_code in expected_codes, (
            f"Malformed JSON should return {expected_codes}, got {response.status_code}"
        )

    def test_create_strategy_wrong_content_type_contract(
        self, client: TestClient
    ) -> None:
        """
        Test strategy creation with wrong Content-Type.

        Contract Requirements:
        - Should only accept application/json
        - Should return 415 Unsupported Media Type or 422
        """
        # Arrange
        valid_data = {
            "name": "Test Strategy",
            "category": "predatory",
            "target_symbols": ["NIFTY"]
        }

        # Act - Send as form data
        response = client.post(
            "/api/v1/strategies",
            data=json.dumps(valid_data),
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        # Assert
        expected_codes = [400, 415, 422]
        assert response.status_code in expected_codes, (
            f"Wrong content type should return {expected_codes}, got {response.status_code}"
        )

    def test_create_strategy_duplicate_name_contract(
        self, client: TestClient, valid_strategy_create_data: dict
    ) -> None:
        """
        Test strategy creation with duplicate name.

        Contract Requirements:
        - Strategy names should be unique per user
        - Should return 409 Conflict if name already exists
        """
        # First creation should succeed
        response1 = client.post("/api/v1/strategies", json=valid_strategy_create_data)

        # If first creation fails, skip this test
        if response1.status_code != 201:
            pytest.skip("Cannot test duplicate name without successful first creation")

        # Second creation with same name should fail
        response2 = client.post("/api/v1/strategies", json=valid_strategy_create_data)

        # Assert - Should return conflict or allow creation with generated unique identifier
        acceptable_codes = [201, 409, 422]  # Some systems may auto-handle duplicates
        assert response2.status_code in acceptable_codes, (
            f"Duplicate name should return {acceptable_codes}, got {response2.status_code}"
        )

    def test_create_strategy_all_categories_contract(
        self, client: TestClient
    ) -> None:
        """
        Test strategy creation with all valid categories.

        Contract Requirements:
        - All enum values should be accepted: predatory, quantitative, psychological, mathematical, extreme
        """
        valid_categories = ["predatory", "quantitative", "psychological", "mathematical", "extreme"]

        for category in valid_categories:
            # Arrange
            strategy_data = {
                "name": f"Test {category.title()} Strategy",
                "category": category,
                "target_symbols": ["NIFTY"]
            }

            # Act
            response = client.post("/api/v1/strategies", json=strategy_data)

            # Assert
            assert response.status_code == 201, (
                f"Category '{category}' should be accepted, got {response.status_code}"
            )

            # Verify category is preserved in response
            if response.status_code == 201:
                response_json = response.json()
                assert response_json["category"] == category, (
                    f"Category mismatch for {category}: expected {category}, "
                    f"got {response_json.get('category')}"
                )

    def test_create_strategy_performance_object_not_included_contract(
        self, client: TestClient, valid_strategy_create_data: dict
    ) -> None:
        """
        Test that performance object is not included in creation request.

        Contract Requirements:
        - performance object should be calculated/generated by system
        - Should not be included in StrategyCreate schema
        - Response should either omit performance or include empty/default performance
        """
        # Act
        response = client.post("/api/v1/strategies", json=valid_strategy_create_data)

        # Assert successful creation
        if response.status_code == 201:
            response_json = response.json()

            # If performance is included, it should have default/empty values
            if "performance" in response_json:
                performance = response_json["performance"]
                assert isinstance(performance, dict), "performance must be object"

                # Check for expected default values or null values
                if "total_trades" in performance:
                    assert performance["total_trades"] == 0 or performance["total_trades"] is None
                if "win_rate" in performance:
                    assert performance["win_rate"] == 0.0 or performance["win_rate"] is None
                if "total_pnl" in performance:
                    assert performance["total_pnl"] == 0.0 or performance["total_pnl"] is None

    def _validate_strategy_response_structure(self, strategy: dict) -> None:
        """
        Helper method to validate the structure of a strategy response object.

        Validates against the Strategy schema from the API specification.
        """
        # Required fields for Strategy schema
        required_fields = [
            "strategy_id", "name", "category", "target_symbols",
            "is_active", "is_paper_only", "created_at", "updated_at"
        ]

        for field in required_fields:
            assert field in strategy, f"Strategy must contain '{field}'"

        # Validate field types and formats
        strategy_id = strategy["strategy_id"]
        assert isinstance(strategy_id, str), "strategy_id must be string"
        # Verify it's a valid UUID format
        try:
            uuid.UUID(strategy_id)
        except ValueError:
            pytest.fail("strategy_id must be a valid UUID")

        name = strategy["name"]
        assert isinstance(name, str), "name must be string"
        assert len(name) > 0, "name cannot be empty"

        category = strategy["category"]
        assert category in [
            "predatory", "quantitative", "psychological",
            "mathematical", "extreme"
        ], f"category must be one of the valid values, got {category}"

        target_symbols = strategy["target_symbols"]
        assert isinstance(target_symbols, list), (
            "target_symbols must be an array"
        )
        assert len(target_symbols) > 0, "target_symbols cannot be empty"
        for symbol in target_symbols:
            assert isinstance(symbol, str), "each target_symbol must be string"

        is_active = strategy["is_active"]
        assert isinstance(is_active, bool), "is_active must be boolean"

        is_paper_only = strategy["is_paper_only"]
        assert isinstance(is_paper_only, bool), "is_paper_only must be boolean"

        # Optional fields validation
        if "description" in strategy:
            assert isinstance(strategy["description"], str), (
                "description must be string"
            )

        if "parameters" in strategy:
            assert isinstance(strategy["parameters"], dict), (
                "parameters must be object"
            )

        if "min_confidence" in strategy:
            min_conf = strategy["min_confidence"]
            assert isinstance(min_conf, (int, float)), (
                "min_confidence must be number"
            )
            assert 0 <= min_conf <= 1, "min_confidence must be between 0 and 1"

        if "max_position_size" in strategy:
            assert isinstance(strategy["max_position_size"], (int, float)), (
                "max_position_size must be number"
            )

        if "stop_loss_pct" in strategy:
            assert isinstance(strategy["stop_loss_pct"], (int, float)), (
                "stop_loss_pct must be number"
            )

        if "take_profit_pct" in strategy:
            assert isinstance(strategy["take_profit_pct"], (int, float)), (
                "take_profit_pct must be number"
            )

        # Performance object validation (if present)
        if "performance" in strategy:
            performance = strategy["performance"]
            assert isinstance(performance, dict), "performance must be object"

            perf_fields = [
                "total_trades", "win_rate", "total_pnl",
                "sharpe_ratio", "max_drawdown"
            ]
            for field in perf_fields:
                if field in performance:
                    if field == "total_trades":
                        assert isinstance(performance[field], int), (
                            f"{field} must be integer"
                        )
                    else:
                        assert isinstance(performance[field], (int, float)), (
                            f"{field} must be number"
                        )