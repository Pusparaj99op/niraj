"""
Contract tests for GET /api/v1/strategies endpoint.

These tests validate the API contract defined in the REST API specification.
Following TDD principles, these tests should fail initially until the
endpoint is implemented.
"""

import pytest
from fastapi.testclient import TestClient
from httpx import Response
import uuid


class TestStrategiesListContract:
    """Contract tests for the strategies list endpoint."""

    @pytest.fixture
    def client(self) -> TestClient:
        """
        Create a test client for the FastAPI application.
        This will fail until the main FastAPI app is implemented.
        """
        # This import will fail until the main app is created
        from src.main import app

        return TestClient(app)

    def test_list_strategies_success_contract(self, client: TestClient) -> None:
        """
        Test successful strategies list contract compliance.

        Contract Requirements:
        - GET /api/v1/strategies
        - Response 200: {
            "strategies": [Strategy...],
            "total": integer
          }
        """
        # Act
        response: Response = client.get("/api/v1/strategies")

        # Assert - Status Code
        expected_status = 200
        actual_status = response.status_code
        assert (
            actual_status == expected_status
        ), f"Expected status {expected_status}, got {actual_status}"

        # Assert - Response Structure
        response_json = response.json()

        # Verify all required fields are present
        required_fields = ["strategies", "total"]
        for field in required_fields:
            assert field in response_json, f"Response must contain '{field}'"

        # Verify field types
        strategies = response_json["strategies"]
        assert isinstance(strategies, list), "strategies must be an array"

        total = response_json["total"]
        assert isinstance(total, int), "total must be integer"
        assert total >= 0, "total must be non-negative"

        # If strategies array is not empty, validate strategy structure
        if len(strategies) > 0:
            strategy = strategies[0]
            self._validate_strategy_structure(strategy)

    def test_list_strategies_with_category_filter_contract(
        self, client: TestClient
    ) -> None:
        """
        Test strategies list with category filter contract compliance.

        Contract Requirements:
        - GET /api/v1/strategies?category=predatory
        - Should return only strategies of specified category
        """
        # Arrange
        category = "predatory"

        # Act
        response: Response = client.get(
            "/api/v1/strategies", params={"category": category}
        )

        # Assert - Status Code
        expected_status = 200
        actual_status = response.status_code
        assert (
            actual_status == expected_status
        ), f"Expected status {expected_status}, got {actual_status}"

        # Assert - Response Structure
        response_json = response.json()
        assert "strategies" in response_json, "Response must contain 'strategies'"

        strategies = response_json["strategies"]
        assert isinstance(strategies, list), "strategies must be an array"

        # Verify all returned strategies have the correct category
        for strategy in strategies:
            self._validate_strategy_structure(strategy)
            assert strategy["category"] == category, (
                f"Strategy {strategy.get('strategy_id')} has category "
                f"{strategy.get('category')}, expected {category}"
            )

    def test_list_strategies_with_active_filter_contract(
        self, client: TestClient
    ) -> None:
        """
        Test strategies list with is_active filter contract compliance.

        Contract Requirements:
        - GET /api/v1/strategies?is_active=true
        - Should return only active strategies
        """
        # Arrange
        is_active = True

        # Act
        response: Response = client.get(
            "/api/v1/strategies", params={"is_active": is_active}
        )

        # Assert - Status Code
        expected_status = 200
        actual_status = response.status_code
        assert (
            actual_status == expected_status
        ), f"Expected status {expected_status}, got {actual_status}"

        # Assert - Response Structure
        response_json = response.json()
        assert "strategies" in response_json, "Response must contain 'strategies'"

        strategies = response_json["strategies"]
        assert isinstance(strategies, list), "strategies must be an array"

        # Verify all returned strategies have the correct active status
        for strategy in strategies:
            self._validate_strategy_structure(strategy)
            assert strategy["is_active"] == is_active, (
                f"Strategy {strategy.get('strategy_id')} has is_active "
                f"{strategy.get('is_active')}, expected {is_active}"
            )

    def test_list_strategies_combined_filters_contract(
        self, client: TestClient
    ) -> None:
        """
        Test strategies list with combined category and active filters.

        Contract Requirements:
        - GET /api/v1/strategies?category=quantitative&is_active=false
        - Should return only strategies matching both criteria
        """
        # Arrange
        category = "quantitative"
        is_active = False

        # Act
        response: Response = client.get(
            "/api/v1/strategies", params={"category": category, "is_active": is_active}
        )

        # Assert - Status Code
        expected_status = 200
        actual_status = response.status_code
        assert (
            actual_status == expected_status
        ), f"Expected status {expected_status}, got {actual_status}"

        # Assert - Response Structure
        response_json = response.json()
        assert "strategies" in response_json, "Response must contain 'strategies'"

        strategies = response_json["strategies"]
        assert isinstance(strategies, list), "strategies must be an array"

        # Verify all returned strategies match both criteria
        for strategy in strategies:
            self._validate_strategy_structure(strategy)
            assert strategy["category"] == category, (
                f"Strategy category mismatch: expected {category}, "
                f"got {strategy.get('category')}"
            )
            assert strategy["is_active"] == is_active, (
                f"Strategy active status mismatch: expected {is_active}, "
                f"got {strategy.get('is_active')}"
            )

    def test_list_strategies_invalid_category_contract(
        self, client: TestClient
    ) -> None:
        """
        Test strategies list with invalid category parameter.

        Contract Requirements:
        - Invalid category should be handled gracefully
        - Should return 400 Bad Request or empty results
        """
        # Arrange
        invalid_category = "invalid_category"

        # Act
        response: Response = client.get(
            "/api/v1/strategies", params={"category": invalid_category}
        )

        # Assert - Status Code (400 for validation error is acceptable)
        expected_codes = [200, 400, 422]
        actual_status = response.status_code
        assert (
            actual_status in expected_codes
        ), f"Expected status {expected_codes}, got {actual_status}"

        # If status is 200, verify empty results
        if actual_status == 200:
            response_json = response.json()
            assert "strategies" in response_json, "Response must contain 'strategies'"
            strategies = response_json["strategies"]
            assert isinstance(strategies, list), "strategies must be an array"
            assert len(strategies) == 0, "Invalid category should return empty results"

    def test_list_strategies_empty_result_contract(self, client: TestClient) -> None:
        """
        Test strategies list when no strategies exist.

        Contract Requirements:
        - Should return empty array with total = 0
        """
        # Act
        response: Response = client.get("/api/v1/strategies")

        # Assert - Status Code
        expected_status = 200
        actual_status = response.status_code
        assert (
            actual_status == expected_status
        ), f"Expected status {expected_status}, got {actual_status}"

        # Assert - Response Structure for empty results
        response_json = response.json()
        assert "strategies" in response_json, "Response must contain 'strategies'"
        assert "total" in response_json, "Response must contain 'total'"

        strategies = response_json["strategies"]
        total = response_json["total"]

        assert isinstance(strategies, list), "strategies must be an array"
        assert isinstance(total, int), "total must be integer"
        assert len(strategies) == 0, "strategies array should be empty"
        assert total == 0, "total should be 0 when no strategies exist"

    def test_list_strategies_wrong_http_method_contract(
        self, client: TestClient
    ) -> None:
        """
        Test strategies endpoint with wrong HTTP method.

        Contract Requirements:
        - Only GET method should be accepted
        - POST should return 405 Method Not Allowed
        """
        # Act
        response: Response = client.post("/api/v1/strategies")

        # Assert - Status Code
        expected_status = 405
        actual_status = response.status_code
        assert (
            actual_status == expected_status
        ), f"Expected status {expected_status}, got {actual_status}"

    def _validate_strategy_structure(self, strategy: dict) -> None:
        """
        Helper method to validate the structure of a strategy object.

        Validates against the Strategy schema from the API specification.
        """
        # Required fields for Strategy schema
        required_fields = [
            "strategy_id",
            "name",
            "category",
            "target_symbols",
            "is_active",
            "is_paper_only",
            "created_at",
            "updated_at",
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
            "predatory",
            "quantitative",
            "psychological",
            "mathematical",
            "extreme",
        ], f"category must be one of the valid values, got {category}"

        target_symbols = strategy["target_symbols"]
        assert isinstance(target_symbols, list), "target_symbols must be an array"
        assert len(target_symbols) > 0, "target_symbols cannot be empty"
        for symbol in target_symbols:
            assert isinstance(symbol, str), "each target_symbol must be string"

        is_active = strategy["is_active"]
        assert isinstance(is_active, bool), "is_active must be boolean"

        is_paper_only = strategy["is_paper_only"]
        assert isinstance(is_paper_only, bool), "is_paper_only must be boolean"

        # Optional fields validation
        if "description" in strategy:
            assert isinstance(
                strategy["description"], str
            ), "description must be string"

        if "parameters" in strategy:
            assert isinstance(strategy["parameters"], dict), "parameters must be object"

        if "min_confidence" in strategy:
            min_conf = strategy["min_confidence"]
            assert isinstance(min_conf, (int, float)), "min_confidence must be number"
            assert 0 <= min_conf <= 1, "min_confidence must be between 0 and 1"

        if "max_position_size" in strategy:
            assert isinstance(
                strategy["max_position_size"], (int, float)
            ), "max_position_size must be number"

        if "stop_loss_pct" in strategy:
            assert isinstance(
                strategy["stop_loss_pct"], (int, float)
            ), "stop_loss_pct must be number"

        if "take_profit_pct" in strategy:
            assert isinstance(
                strategy["take_profit_pct"], (int, float)
            ), "take_profit_pct must be number"

        # Performance object validation
        if "performance" in strategy:
            performance = strategy["performance"]
            assert isinstance(performance, dict), "performance must be object"

            perf_fields = [
                "total_trades",
                "win_rate",
                "total_pnl",
                "sharpe_ratio",
                "max_drawdown",
            ]
            for field in perf_fields:
                if field in performance:
                    if field == "total_trades":
                        assert isinstance(
                            performance[field], int
                        ), f"{field} must be integer"
                    else:
                        assert isinstance(
                            performance[field], (int, float)
                        ), f"{field} must be number"
