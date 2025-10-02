"""
Contract tests for POST /api/v1/strategies/{id}/backtest endpoint.

These tests validate the API contract defined in the REST API specification.
Following TDD principles, these tests should fail initially until the
endpoint is implemented.
"""

import pytest
from fastapi.testclient import TestClient
from httpx import Response
import uuid


class TestStrategiesBacktestContract:
    """Contract tests for the strategies backtest endpoint."""

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
    def valid_backtest_request(self) -> dict:
        """Valid backtest request data matching the schema."""
        return {
            "start_date": "2025-01-01",
            "end_date": "2025-09-17",
            "initial_capital": 100000.00,
            "symbols": ["BANKNIFTY", "HDFCBANK"],
        }

    def test_run_backtest_success_contract(
        self, client: TestClient, valid_strategy_id: str, valid_backtest_request: dict
    ) -> None:
        """
        Test successful backtest execution contract compliance.

        Contract Requirements:
        - POST /api/v1/strategies/{strategy_id}/backtest -
        - Path Parameter: strategy_id (UUID) -
        - Request Body: BacktestRequest schema -
        Response 200: BacktestResult schema
        """
        # Act
        response: Response = client.post(
            f"/api/v1/strategies/{valid_strategy_id}/backtest",
            json=valid_backtest_request,
        )

        # Assert - Status Code
        expected_status = 200
        actual_status = response.status_code
        assert (
            actual_status == expected_status
        ), f"Expected status {expected_status}, got {actual_status}"

        # Assert - Response Structure
        response_json = response.json()
        self._validate_backtest_result_structure(response_json)

        # Assert - Required fields from request are preserved
        assert response_json["strategy_id"] == valid_strategy_id
        assert (
            response_json["period"]["start_date"]
            == valid_backtest_request["start_date"]
        )
        assert response_json["period"]["end_date"] == valid_backtest_request["end_date"]
        assert (
            response_json["initial_capital"]
            == valid_backtest_request["initial_capital"]
        )

        # Assert - Generated fields are present and valid
        backtest_id = response_json["backtest_id"]
        assert isinstance(backtest_id, str), "backtest_id must be string"
        # Verify it's a valid UUID format
        try:
            uuid.UUID(backtest_id)
        except ValueError:
            pytest.fail("backtest_id must be a valid UUID")

        # Assert - Final capital is present and valid
        final_capital = response_json["final_capital"]
        assert isinstance(final_capital, (int, float)), "final_capital must be number"
        assert final_capital >= 0, "final_capital cannot be negative"

        # Assert - Performance metrics are present
        assert "performance_metrics" in response_json
        self._validate_performance_metrics_structure(
            response_json["performance_metrics"]
        )

        # Assert - Trades array is present
        assert "trades" in response_json
        assert isinstance(response_json["trades"], list), "trades must be array"

        # Assert - Equity curve is present
        assert "equity_curve" in response_json
        assert isinstance(
            response_json["equity_curve"], list
        ), "equity_curve must be array"

    def test_run_backtest_minimal_data_contract(
        self, client: TestClient, valid_strategy_id: str
    ) -> None:
        """
        Test backtest with only required fields.

        Contract Requirements:
        - Only start_date, end_date, initial_capital are required -
        symbols is optional and should default to strategy's target_symbols
        """
        # Arrange - Only required fields
        minimal_request = {
            "start_date": "2025-01-01",
            "end_date": "2025-09-17",
            "initial_capital": 100000.00,
        }

        # Act
        response: Response = client.post(
            f"/api/v1/strategies/{valid_strategy_id}/backtest", json=minimal_request
        )

        # Assert - Status Code
        expected_status = 200
        actual_status = response.status_code
        assert (
            actual_status == expected_status
        ), f"Expected status {expected_status}, got {actual_status}"

        # Assert - Response Structure
        response_json = response.json()
        self._validate_backtest_result_structure(response_json)

        # Assert - Required fields are preserved
        assert response_json["strategy_id"] == valid_strategy_id
        assert response_json["period"]["start_date"] == minimal_request["start_date"]
        assert response_json["period"]["end_date"] == minimal_request["end_date"]
        assert response_json["initial_capital"] == minimal_request["initial_capital"]

    def test_run_backtest_invalid_strategy_id_contract(
        self, client: TestClient, valid_backtest_request: dict
    ) -> None:
        """
        Test backtest with invalid strategy ID.

        Contract Requirements:
        - strategy_id must be a valid UUID -
        Should return 400 Bad Request or 422 Unprocessable Entity for invalid UUID format
        """
        # Test with non-UUID string
        invalid_id = "not-a-uuid"
        response = client.post(
            f"/api/v1/strategies/{invalid_id}/backtest", json=valid_backtest_request
        )

        expected_codes = [400, 422]
        assert (
            response.status_code in expected_codes
        ), f"Invalid strategy ID should return {expected_codes}, got {response.status_code}"

    def test_run_backtest_nonexistent_strategy_contract(
        self, client: TestClient, valid_backtest_request: dict
    ) -> None:
        """
        Test backtest with non-existent strategy ID.

        Contract Requirements:
        - Should return 404 Not Found for non-existent strategy
        """
        # Use a valid UUID format but non-existent strategy
        nonexistent_id = str(uuid.uuid4())

        response = client.post(
            f"/api/v1/strategies/{nonexistent_id}/backtest", json=valid_backtest_request
        )

        expected_status = 404
        assert (
            response.status_code == expected_status
        ), f"Non-existent strategy should return {expected_status}, got {response.status_code}"

    def test_run_backtest_missing_required_fields_contract(
        self, client: TestClient, valid_strategy_id: str
    ) -> None:
        """
        Test backtest with missing required fields.

        Contract Requirements:
        - start_date, end_date, initial_capital are required -
        Should return 400 Bad Request or 422 Unprocessable Entity
        """
        # Test missing start_date
        missing_start_date = {"end_date": "2025-09-17", "initial_capital": 100000.00}

        response = client.post(
            f"/api/v1/strategies/{valid_strategy_id}/backtest", json=missing_start_date
        )

        expected_codes = [400, 422]
        assert (
            response.status_code in expected_codes
        ), f"Missing start_date should return {expected_codes}, got {response.status_code}"

        # Test missing end_date
        missing_end_date = {"start_date": "2025-01-01", "initial_capital": 100000.00}

        response = client.post(
            f"/api/v1/strategies/{valid_strategy_id}/backtest", json=missing_end_date
        )

        assert (
            response.status_code in expected_codes
        ), f"Missing end_date should return {expected_codes}, got {response.status_code}"

        # Test missing initial_capital
        missing_capital = {"start_date": "2025-01-01", "end_date": "2025-09-17"}

        response = client.post(
            f"/api/v1/strategies/{valid_strategy_id}/backtest", json=missing_capital
        )

        assert (
            response.status_code in expected_codes
        ), f"Missing initial_capital should return {expected_codes}, got {response.status_code}"

    def test_run_backtest_invalid_date_format_contract(
        self, client: TestClient, valid_strategy_id: str
    ) -> None:
        """
        Test backtest with invalid date formats.

        Contract Requirements:
        - start_date and end_date must be in YYYY-MM-DD format -
        Should return 400 Bad Request or 422 Unprocessable Entity
        """
        # Test invalid start_date format
        invalid_start_date = {
            "start_date": "01/01/2025",  # Wrong format
            "end_date": "2025-09-17",
            "initial_capital": 100000.00,
        }

        response = client.post(
            f"/api/v1/strategies/{valid_strategy_id}/backtest", json=invalid_start_date
        )

        expected_codes = [400, 422]
        assert (
            response.status_code in expected_codes
        ), f"Invalid date format should return {expected_codes}, got {response.status_code}"

        # Test invalid end_date format
        invalid_end_date = {
            "start_date": "2025-01-01",
            "end_date": "17-09-2025",  # Wrong format
            "initial_capital": 100000.00,
        }

        response = client.post(
            f"/api/v1/strategies/{valid_strategy_id}/backtest", json=invalid_end_date
        )

        assert (
            response.status_code in expected_codes
        ), f"Invalid date format should return {expected_codes}, got {response.status_code}"

    def test_run_backtest_invalid_date_range_contract(
        self, client: TestClient, valid_strategy_id: str
    ) -> None:
        """
        Test backtest with invalid date range (end_date before start_date).

        Contract Requirements:
        - end_date must be after start_date -
        Should return 400 Bad Request or 422 Unprocessable Entity
        """
        # Arrange - end_date before start_date
        invalid_range = {
            "start_date": "2025-09-17",
            "end_date": "2025-01-01",
            "initial_capital": 100000.00,
        }

        # Act
        response = client.post(
            f"/api/v1/strategies/{valid_strategy_id}/backtest", json=invalid_range
        )

        # Assert
        expected_codes = [400, 422]
        assert (
            response.status_code in expected_codes
        ), f"Invalid date range should return {expected_codes}, got {response.status_code}"

    def test_run_backtest_invalid_initial_capital_contract(
        self, client: TestClient, valid_strategy_id: str
    ) -> None:
        """
        Test backtest with invalid initial capital values.

        Contract Requirements:
        - initial_capital must be a positive number -
        Should return 400 Bad Request or 422 Unprocessable Entity
        """
        # Test negative capital
        negative_capital = {
            "start_date": "2025-01-01",
            "end_date": "2025-09-17",
            "initial_capital": -1000.00,
        }

        response = client.post(
            f"/api/v1/strategies/{valid_strategy_id}/backtest", json=negative_capital
        )

        expected_codes = [400, 422]
        assert (
            response.status_code in expected_codes
        ), f"Negative capital should return {expected_codes}, got {response.status_code}"

        # Test zero capital
        zero_capital = {
            "start_date": "2025-01-01",
            "end_date": "2025-09-17",
            "initial_capital": 0.00,
        }

        response = client.post(
            f"/api/v1/strategies/{valid_strategy_id}/backtest", json=zero_capital
        )

        assert (
            response.status_code in expected_codes
        ), f"Zero capital should return {expected_codes}, got {response.status_code}"

    def test_run_backtest_empty_symbols_array_contract(
        self, client: TestClient, valid_strategy_id: str
    ) -> None:
        """
        Test backtest with empty symbols array.

        Contract Requirements:
        - symbols array should not be empty if provided -
        Should return 400 Bad Request or 422 Unprocessable Entity or use strategy defaults
        """
        # Arrange
        empty_symbols = {
            "start_date": "2025-01-01",
            "end_date": "2025-09-17",
            "initial_capital": 100000.00,
            "symbols": [],
        }

        # Act
        response = client.post(
            f"/api/v1/strategies/{valid_strategy_id}/backtest", json=empty_symbols
        )

        # Assert - Either reject or use strategy defaults
        acceptable_codes = [
            200,
            400,
            422,
        ]  # Some systems may fall back to strategy symbols
        assert (
            response.status_code in acceptable_codes
        ), f"Empty symbols should return {acceptable_codes}, got {response.status_code}"

    def test_run_backtest_invalid_json_contract(
        self, client: TestClient, valid_strategy_id: str
    ) -> None:
        """
        Test backtest with malformed JSON.

        Contract Requirements:
        - Should return 400 Bad Request or 422 Unprocessable Entity
        """
        # Act - Send malformed JSON
        response = client.post(
            f"/api/v1/strategies/{valid_strategy_id}/backtest",
            data="{ invalid json",
            headers={"Content-Type": "application/json"},
        )

        # Assert
        expected_codes = [400, 422]
        assert (
            response.status_code in expected_codes
        ), f"Malformed JSON should return {expected_codes}, got {response.status_code}"

    def test_run_backtest_wrong_content_type_contract(
        self, client: TestClient, valid_strategy_id: str, valid_backtest_request: dict
    ) -> None:
        """
        Test backtest with wrong Content-Type.

        Contract Requirements:
        - Should only accept application/json -
        Should return 415 Unsupported Media Type or 422
        """
        import json

        # Act - Send as form data
        response = client.post(
            f"/api/v1/strategies/{valid_strategy_id}/backtest",
            data=json.dumps(valid_backtest_request),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        # Assert
        expected_codes = [400, 415, 422]
        assert (
            response.status_code in expected_codes
        ), f"Wrong content type should return {expected_codes}, got {response.status_code}"

    def test_run_backtest_future_dates_contract(
        self, client: TestClient, valid_strategy_id: str
    ) -> None:
        """
        Test backtest with future dates.

        Contract Requirements:
        - Dates in the future might be rejected or handled differently -
        Should either process or return appropriate error
        """
        from datetime import datetime, timedelta

        # Get future dates
        future_start = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        future_end = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")

        future_dates = {
            "start_date": future_start,
            "end_date": future_end,
            "initial_capital": 100000.00,
        }

        response = client.post(
            f"/api/v1/strategies/{valid_strategy_id}/backtest", json=future_dates
        )

        # Assert - Either accept or reject with appropriate status
        acceptable_codes = [200, 400, 422]
        assert (
            response.status_code in acceptable_codes
        ), f"Future dates should return {acceptable_codes}, got {response.status_code}"

    def test_run_backtest_large_initial_capital_contract(
        self, client: TestClient, valid_strategy_id: str
    ) -> None:
        """
        Test backtest with very large initial capital.

        Contract Requirements:
        - Should handle large numbers appropriately -
        Should not cause overflow or precision errors
        """
        # Arrange - Very large capital
        large_capital = {
            "start_date": "2025-01-01",
            "end_date": "2025-09-17",
            "initial_capital": 999999999.99,
        }

        # Act
        response = client.post(
            f"/api/v1/strategies/{valid_strategy_id}/backtest", json=large_capital
        )

        # Assert - Should either process or return appropriate error
        acceptable_codes = [200, 400, 422]
        assert (
            response.status_code in acceptable_codes
        ), f"Large capital should return {acceptable_codes}, got {response.status_code}"

        # If successful, verify precision is maintained
        if response.status_code == 200:
            response_json = response.json()
            assert (
                response_json["initial_capital"] == large_capital["initial_capital"]
            ), "Large capital precision should be maintained"

    def test_run_backtest_invalid_symbols_format_contract(
        self, client: TestClient, valid_strategy_id: str
    ) -> None:
        """
        Test backtest with invalid symbols format.

        Contract Requirements:
        - symbols must be array of strings -
        Should return 400 Bad Request or 422 Unprocessable Entity for invalid formats
        """
        # Test with non-array symbols
        non_array_symbols = {
            "start_date": "2025-01-01",
            "end_date": "2025-09-17",
            "initial_capital": 100000.00,
            "symbols": "BANKNIFTY",  # Should be array
        }

        response = client.post(
            f"/api/v1/strategies/{valid_strategy_id}/backtest", json=non_array_symbols
        )

        expected_codes = [400, 422]
        assert (
            response.status_code in expected_codes
        ), f"Non-array symbols should return {expected_codes}, got {response.status_code}"

        # Test with non-string elements in array
        non_string_symbols = {
            "start_date": "2025-01-01",
            "end_date": "2025-09-17",
            "initial_capital": 100000.00,
            "symbols": [123, "BANKNIFTY"],  # 123 should be string
        }

        response = client.post(
            f"/api/v1/strategies/{valid_strategy_id}/backtest", json=non_string_symbols
        )

        assert (
            response.status_code in expected_codes
        ), f"Non-string symbols should return {expected_codes}, got {response.status_code}"

    def _validate_backtest_result_structure(self, result: dict) -> None:
        """
        Helper method to validate the structure of a backtest result object.

        Validates against the BacktestResult schema from the API specification.
        """
        # Required fields for BacktestResult schema
        required_fields = [
            "strategy_id",
            "backtest_id",
            "period",
            "initial_capital",
            "final_capital",
            "performance_metrics",
            "trades",
            "equity_curve",
        ]

        for field in required_fields:
            assert field in result, f"BacktestResult must contain '{field}'"

        # Validate strategy_id
        strategy_id = result["strategy_id"]
        assert isinstance(strategy_id, str), "strategy_id must be string"
        try:
            uuid.UUID(strategy_id)
        except ValueError:
            pytest.fail("strategy_id must be a valid UUID")

        # Validate backtest_id
        backtest_id = result["backtest_id"]
        assert isinstance(backtest_id, str), "backtest_id must be string"
        try:
            uuid.UUID(backtest_id)
        except ValueError:
            pytest.fail("backtest_id must be a valid UUID")

        # Validate period object
        period = result["period"]
        assert isinstance(period, dict), "period must be object"
        assert "start_date" in period, "period must contain start_date"
        assert "end_date" in period, "period must contain end_date"
        assert isinstance(period["start_date"], str), "start_date must be string"
        assert isinstance(period["end_date"], str), "end_date must be string"

        # Validate initial_capital and final_capital
        initial_capital = result["initial_capital"]
        assert isinstance(
            initial_capital, (int, float)
        ), "initial_capital must be number"
        assert initial_capital > 0, "initial_capital must be positive"

        final_capital = result["final_capital"]
        assert isinstance(final_capital, (int, float)), "final_capital must be number"
        assert final_capital >= 0, "final_capital cannot be negative"

        # Validate performance_metrics
        assert isinstance(
            result["performance_metrics"], dict
        ), "performance_metrics must be object"

        # Validate trades array
        trades = result["trades"]
        assert isinstance(trades, list), "trades must be array"

        # Validate equity_curve array
        equity_curve = result["equity_curve"]
        assert isinstance(equity_curve, list), "equity_curve must be array"

        # Validate equity curve items structure
        for curve_point in equity_curve:
            assert isinstance(curve_point, dict), "equity curve point must be object"
            assert "date" in curve_point, "curve point must contain date"
            assert (
                "portfolio_value" in curve_point
            ), "curve point must contain portfolio_value"
            assert isinstance(
                curve_point["date"], str
            ), "curve point date must be string"
            assert isinstance(
                curve_point["portfolio_value"], (int, float)
            ), "portfolio_value must be number"

    def _validate_performance_metrics_structure(self, metrics: dict) -> None:
        """
        Helper method to validate the structure of performance metrics object.

        This should contain typical backtest performance indicators.
        """
        # Performance metrics should be a dictionary
        assert isinstance(metrics, dict), "performance_metrics must be object"

        # Common performance metrics that should be present
        expected_metrics = [
            "total_return",
            "annualized_return",
            "volatility",
            "sharpe_ratio",
            "max_drawdown",
            "win_rate",
            "total_trades",
        ]

        # At least some of these metrics should be present
        present_metrics = [metric for metric in expected_metrics if metric in metrics]
        assert (
            len(present_metrics) > 0
        ), f"At least some performance metrics should be present: {expected_metrics}"

        # Validate data types for present metrics
        for metric, value in metrics.items():
            if metric == "total_trades":
                assert isinstance(value, int), f"{metric} must be integer"
                assert value >= 0, f"{metric} cannot be negative"
            else:
                assert isinstance(value, (int, float)), f"{metric} must be number"

        # Validate specific ranges for some metrics
        if "win_rate" in metrics:
            win_rate = metrics["win_rate"]
            assert 0 <= win_rate <= 1, "win_rate must be between 0 and 1"

        if "max_drawdown" in metrics:
            max_drawdown = metrics["max_drawdown"]
            assert max_drawdown <= 0, "max_drawdown should be negative or zero"
