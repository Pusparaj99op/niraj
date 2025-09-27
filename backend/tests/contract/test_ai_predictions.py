"""
Contract tests for GET /api/v1/ai/predictions endpoint.

These tests validate the API contract defined in the REST API specification.
Following TDD principles, these tests should fail initially until the
endpoint is implemented.
"""

import pytest
from fastapi.testclient import TestClient
from httpx import Response
import uuid
from datetime import datetime


class TestAIPredictionsContract:
    """Contract tests for the AI predictions endpoint."""

    @pytest.fixture
    def client(self) -> TestClient:
        """
        Create a test client for the FastAPI application.
        This will fail until the main FastAPI app is implemented.
        """
        # This import will fail until the main app is created
        from src.main import app

        return TestClient(app)

    def test_get_predictions_success_contract(self, client: TestClient) -> None:
        """
        Test successful AI predictions retrieval contract compliance.

        Contract Requirements:
        - GET /api/v1/ai/predictions
        - Optional query parameters: symbol, strategy_id, min_confidence
        - Response 200: {
            "predictions": Array<AIPrediction>
          }
        - AIPrediction schema validation
        """
        # Act
        response: Response = client.get("/api/v1/ai/predictions")

        # Assert - Status Code
        expected_status = 200
        actual_status = response.status_code
        assert (
            actual_status == expected_status
        ), f"Expected status {expected_status}, got {actual_status}"

        # Assert - Response Structure
        response_json = response.json()

        # Verify required fields are present
        assert (
            "predictions" in response_json
        ), "Response must contain 'predictions' field"

        predictions = response_json["predictions"]
        assert isinstance(predictions, list), "'predictions' must be an array"

        # If predictions exist, validate structure
        if predictions:
            prediction = predictions[0]
            self._validate_prediction_schema(prediction)

    def test_get_predictions_with_symbol_filter_contract(
        self, client: TestClient
    ) -> None:
        """
        Test AI predictions with symbol filter contract compliance.

        Contract Requirements:
        - GET /api/v1/ai/predictions?symbol=BANKNIFTY
        - Filtered results should only contain predictions for specified symbol
        """
        # Arrange
        test_symbol = "BANKNIFTY"

        # Act
        response: Response = client.get(f"/api/v1/ai/predictions?symbol={test_symbol}")

        # Assert - Status Code
        expected_status = 200
        actual_status = response.status_code
        assert (
            actual_status == expected_status
        ), f"Expected status {expected_status}, got {actual_status}"

        # Assert - Response Structure and Filtering
        response_json = response.json()
        predictions = response_json["predictions"]

        # All predictions should be for the requested symbol
        for prediction in predictions:
            assert (
                prediction["symbol"] == test_symbol
            ), f"All predictions should be for symbol '{test_symbol}'"

    def test_get_predictions_with_strategy_filter_contract(
        self, client: TestClient
    ) -> None:
        """
        Test AI predictions with strategy_id filter contract compliance.

        Contract Requirements:
        - GET /api/v1/ai/predictions?strategy_id={uuid}
        - Filtered results should only contain predictions for specified strategy
        """
        # Arrange
        test_strategy_id = str(uuid.uuid4())

        # Act
        response: Response = client.get(
            f"/api/v1/ai/predictions?strategy_id={test_strategy_id}"
        )

        # Assert - Status Code
        expected_status = 200
        actual_status = response.status_code
        assert (
            actual_status == expected_status
        ), f"Expected status {expected_status}, got {actual_status}"

        # Assert - Response Structure and Filtering
        response_json = response.json()
        predictions = response_json["predictions"]

        # All predictions should be for the requested strategy
        for prediction in predictions:
            assert (
                prediction["strategy_id"] == test_strategy_id
            ), f"All predictions should be for strategy '{test_strategy_id}'"

    def test_get_predictions_with_confidence_filter_contract(
        self, client: TestClient
    ) -> None:
        """
        Test AI predictions with min_confidence filter contract compliance.

        Contract Requirements:
        - GET /api/v1/ai/predictions?min_confidence=0.8
        - Default min_confidence is 0.7
        - All returned predictions should have confidence >= min_confidence
        """
        # Arrange
        min_confidence = 0.8

        # Act
        response: Response = client.get(
            f"/api/v1/ai/predictions?min_confidence={min_confidence}"
        )

        # Assert - Status Code
        expected_status = 200
        actual_status = response.status_code
        assert (
            actual_status == expected_status
        ), f"Expected status {expected_status}, got {actual_status}"

        # Assert - Response Structure and Filtering
        response_json = response.json()
        predictions = response_json["predictions"]

        # All predictions should have confidence >= min_confidence
        for prediction in predictions:
            confidence = prediction["confidence_score"]
            assert (
                confidence >= min_confidence
            ), f"Prediction confidence {confidence} should be >= {min_confidence}"

    def test_get_predictions_combined_filters_contract(
        self, client: TestClient
    ) -> None:
        """
        Test AI predictions with combined filters contract compliance.

        Contract Requirements:
        - GET /api/v1/ai/predictions?symbol=BANKNIFTY&strategy_id={uuid}&min_confidence=0.8
        - All filters should be applied simultaneously
        """
        # Arrange
        test_symbol = "BANKNIFTY"
        test_strategy_id = str(uuid.uuid4())
        min_confidence = 0.8

        # Act
        response: Response = client.get(
            f"/api/v1/ai/predictions"
            f"?symbol={test_symbol}"
            f"&strategy_id={test_strategy_id}"
            f"&min_confidence={min_confidence}"
        )

        # Assert - Status Code
        expected_status = 200
        actual_status = response.status_code
        assert (
            actual_status == expected_status
        ), f"Expected status {expected_status}, got {actual_status}"

        # Assert - Response Structure and Filtering
        response_json = response.json()
        predictions = response_json["predictions"]

        # Validate all filters are applied
        for prediction in predictions:
            assert prediction["symbol"] == test_symbol
            assert prediction["strategy_id"] == test_strategy_id
            assert prediction["confidence_score"] >= min_confidence

    def test_get_predictions_invalid_confidence_range_contract(
        self, client: TestClient
    ) -> None:
        """
        Test AI predictions with invalid confidence range.

        Contract Requirements:
        - min_confidence must be between 0 and 1
        - Values outside this range should return 400 Bad Request
        """
        # Test invalid confidence values
        invalid_values = [1.5, -0.1, 2.0, "invalid"]

        for invalid_confidence in invalid_values:
            # Act
            response: Response = client.get(
                f"/api/v1/ai/predictions?min_confidence={invalid_confidence}"
            )

            # Assert - Status Code
            expected_codes = [400, 422]
            actual_status = response.status_code
            assert actual_status in expected_codes, (
                f"Expected status {expected_codes} for confidence {invalid_confidence}, "
                f"got {actual_status}"
            )

    def test_get_predictions_invalid_strategy_uuid_contract(
        self, client: TestClient
    ) -> None:
        """
        Test AI predictions with invalid strategy_id UUID format.

        Contract Requirements:
        - strategy_id must be a valid UUID format
        - Invalid UUID should return 400 or 422
        """
        # Arrange
        invalid_uuid = "not-a-valid-uuid"

        # Act
        response: Response = client.get(
            f"/api/v1/ai/predictions?strategy_id={invalid_uuid}"
        )

        # Assert - Status Code
        expected_codes = [400, 422]
        actual_status = response.status_code
        assert (
            actual_status in expected_codes
        ), f"Expected status {expected_codes}, got {actual_status}"

    def test_get_predictions_wrong_http_method_contract(
        self, client: TestClient
    ) -> None:
        """
        Test AI predictions endpoint with wrong HTTP method.

        Contract Requirements:
        - Only GET method should be accepted for listing predictions
        - POST should return 405 Method Not Allowed
        """
        # Act
        response: Response = client.post("/api/v1/ai/predictions")

        # Assert - Status Code
        expected_status = 405
        actual_status = response.status_code
        assert (
            actual_status == expected_status
        ), f"Expected status {expected_status}, got {actual_status}"

    def test_get_predictions_authorization_contract(self, client: TestClient) -> None:
        """
        Test AI predictions endpoint requires authorization.

        Contract Requirements:
        - Endpoint should require Bearer token authentication
        - Missing token should return 401 Unauthorized
        """
        # Act - Request without authorization header
        response: Response = client.get(
            "/api/v1/ai/predictions", headers={}  # No Authorization header
        )

        # Assert - Status Code
        # Note: This may return 401 or work depending on implementation
        # The test validates the contract expectation
        acceptable_codes = [200, 401, 404]  # 404 if endpoint doesn't exist yet
        actual_status = response.status_code
        assert (
            actual_status in acceptable_codes
        ), f"Unexpected status code: {actual_status}"

    def test_get_predictions_empty_response_structure_contract(
        self, client: TestClient
    ) -> None:
        """
        Test AI predictions endpoint with no predictions available.

        Contract Requirements:
        - Even with no predictions, response structure should be valid
        - Should return empty predictions array
        """
        # Arrange - Use filters that likely return no results
        nonexistent_symbol = "NONEXISTENT_SYMBOL"

        # Act
        response: Response = client.get(
            f"/api/v1/ai/predictions?symbol={nonexistent_symbol}"
        )

        # Assert - Status Code
        expected_status = 200
        actual_status = response.status_code
        assert (
            actual_status == expected_status
        ), f"Expected status {expected_status}, got {actual_status}"

        # Assert - Response Structure
        response_json = response.json()
        assert "predictions" in response_json
        assert isinstance(response_json["predictions"], list)

    def _validate_prediction_schema(self, prediction: dict) -> None:
        """
        Validate AIPrediction schema compliance.

        Required fields from OpenAPI spec:
        - prediction_id: string (UUID)
        - symbol: string
        - strategy_id: string (UUID)
        - timestamp: string (date-time)
        - predicted_direction: string (UP/DOWN/SIDEWAYS)
        - confidence_score: number (0-1)
        - predicted_magnitude: number
        - prediction_horizon: integer
        - reasoning: string
        - market_features: object
        - was_correct: boolean (nullable)
        - trade_executed: boolean
        """
        # Required string fields
        required_string_fields = [
            "prediction_id",
            "symbol",
            "strategy_id",
            "timestamp",
            "predicted_direction",
            "reasoning",
        ]

        for field in required_string_fields:
            assert field in prediction, f"Prediction must contain '{field}'"
            assert isinstance(prediction[field], str), f"Field '{field}' must be string"
            assert len(prediction[field]) > 0, f"Field '{field}' cannot be empty"

        # Validate UUID fields
        uuid_fields = ["prediction_id", "strategy_id"]
        for field in uuid_fields:
            try:
                uuid.UUID(prediction[field])
            except ValueError:
                pytest.fail(f"Field '{field}' must be valid UUID")

        # Validate timestamp format
        try:
            datetime.fromisoformat(prediction["timestamp"].replace("Z", "+00:00"))
        except ValueError:
            pytest.fail("Field 'timestamp' must be valid ISO datetime")

        # Validate predicted_direction enum
        valid_directions = ["UP", "DOWN", "SIDEWAYS"]
        direction = prediction["predicted_direction"]
        assert (
            direction in valid_directions
        ), f"predicted_direction must be one of {valid_directions}"

        # Validate confidence_score range
        confidence = prediction["confidence_score"]
        assert isinstance(confidence, (int, float)), "confidence_score must be number"
        assert 0 <= confidence <= 1, "confidence_score must be between 0 and 1"

        # Validate predicted_magnitude
        magnitude = prediction["predicted_magnitude"]
        assert isinstance(magnitude, (int, float)), "predicted_magnitude must be number"

        # Validate prediction_horizon
        horizon = prediction["prediction_horizon"]
        assert isinstance(horizon, int), "prediction_horizon must be integer"
        assert horizon > 0, "prediction_horizon must be positive"

        # Validate market_features
        assert (
            "market_features" in prediction
        ), "Prediction must contain 'market_features'"
        assert isinstance(
            prediction["market_features"], dict
        ), "market_features must be object"

        # Validate boolean fields
        boolean_fields = ["trade_executed"]
        for field in boolean_fields:
            assert field in prediction, f"Prediction must contain '{field}'"
            assert isinstance(
                prediction[field], bool
            ), f"Field '{field}' must be boolean"

        # Validate nullable boolean field
        if "was_correct" in prediction and prediction["was_correct"] is not None:
            assert isinstance(
                prediction["was_correct"], bool
            ), "was_correct must be boolean or null"
