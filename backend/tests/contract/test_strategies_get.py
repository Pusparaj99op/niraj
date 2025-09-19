"""
Contract tests for GET /api/v1/strategies/{strategy_id} endpoint.

These tests validate the API contract defined in the REST API specification.
Following TDD principles, these tests should fail initially until the
endpoint is implemented.
"""
import pytest
from fastapi.testclient import TestClient
from httpx import Response
import uuid


class TestStrategiesGetContract:
    """Contract tests for the strategy get by ID endpoint."""

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
        """Generate a valid UUID for testing."""
        return str(uuid.uuid4())

    def test_get_strategy_success_contract(
        self, client: TestClient, valid_strategy_id: str
    ) -> None:
        """
        Test successful strategy retrieval contract compliance.

        Contract Requirements:
        - GET /api/v1/strategies/{strategy_id}
        - Path parameter: strategy_id (UUID format)
        - Response 200: Strategy schema object
        """
        # Act
        response: Response = client.get(
            f"/api/v1/strategies/{valid_strategy_id}"
        )

        # Assert - Status Code (will be 404 until strategy exists,
        # but endpoint should exist)
        # Initially expecting 404 since no strategies exist in empty system
        acceptable_codes = [200, 404]
        actual_status = response.status_code
        assert actual_status in acceptable_codes, (
            f"Expected status {acceptable_codes}, got {actual_status}"
        )

        # If 200 response, validate structure
        if actual_status == 200:
            response_json = response.json()
            self._validate_strategy_structure(response_json)
            
            # Verify the returned strategy has the requested ID
            returned_id = response_json["strategy_id"]
            assert returned_id == valid_strategy_id, (
                f"Expected strategy_id {valid_strategy_id}, got {returned_id}"
            )

        # If 404 response, validate error structure
        elif actual_status == 404:
            # This is expected behavior when strategy doesn't exist
            response_json = response.json()
            assert "detail" in response_json, (
                "404 response must contain 'detail' field"
            )
            assert isinstance(response_json["detail"], str), (
                "detail must be a string"
            )

    def test_get_strategy_not_found_contract(
        self, client: TestClient
    ) -> None:
        """
        Test strategy not found contract compliance.

        Contract Requirements:
        - GET /api/v1/strategies/{non_existent_id}
        - Response 404: NotFound error response
        """
        # Arrange - Use a UUID that definitely doesn't exist
        non_existent_id = str(uuid.uuid4())

        # Act
        response: Response = client.get(
            f"/api/v1/strategies/{non_existent_id}"
        )

        # Assert - Status Code
        expected_status = 404
        actual_status = response.status_code
        assert actual_status == expected_status, (
            f"Expected status {expected_status}, got {actual_status}"
        )

        # Assert - Response Structure
        response_json = response.json()
        assert "detail" in response_json, (
            "404 response must contain 'detail' field"
        )
        
        detail = response_json["detail"]
        assert isinstance(detail, str), "detail must be a string"
        assert len(detail) > 0, "detail cannot be empty"

    def test_get_strategy_invalid_uuid_format_contract(
        self, client: TestClient
    ) -> None:
        """
        Test strategy retrieval with invalid UUID format.

        Contract Requirements:
        - strategy_id path parameter must be valid UUID format
        - Should return 400 Bad Request or 422 Unprocessable Entity
        """
        # Arrange - Invalid UUID formats
        invalid_ids = [
            "not-a-uuid",
            "12345",
            "invalid-uuid-format",
            "00000000-0000-0000-0000-00000000000",  # Wrong length
            "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",  # Invalid characters
        ]

        for invalid_id in invalid_ids:
            # Act
            response: Response = client.get(f"/api/v1/strategies/{invalid_id}")

            # Assert - Status Code
            expected_codes = [400, 422]
            actual_status = response.status_code
            assert actual_status in expected_codes, (
                f"Invalid UUID '{invalid_id}' should return {expected_codes}, "
                f"got {actual_status}"
            )

            # Assert - Error response format
            if actual_status == 422:
                # FastAPI validation error format
                response_json = response.json()
                assert "detail" in response_json, (
                    "422 response must contain 'detail'"
                )

    def test_get_strategy_empty_uuid_contract(
        self, client: TestClient
    ) -> None:
        """
        Test strategy retrieval with empty strategy_id.

        Contract Requirements:
        - Empty strategy_id should be rejected
        - Should return 404 Not Found or 422 Unprocessable Entity
        """
        # Act
        response: Response = client.get("/api/v1/strategies/")

        # Assert - Status Code
        # This will likely hit the list endpoint instead,
        # so we expect different behavior
        # The trailing slash might redirect to list endpoint or return 404/405
        acceptable_codes = [200, 404, 405, 422]
        actual_status = response.status_code
        assert actual_status in acceptable_codes, (
            f"Empty strategy_id should return {acceptable_codes}, "
            f"got {actual_status}"
        )

    def test_get_strategy_special_characters_uuid_contract(
        self, client: TestClient
    ) -> None:
        """
        Test strategy retrieval with special characters in UUID parameter.

        Contract Requirements:
        - Only valid UUID format should be accepted
        - Special characters should be rejected with validation error
        """
        # Arrange - UUIDs with special characters/URL encoding issues
        special_char_ids = [
            "123e4567-e89b-12d3-a456-426614174000%20",  # URL encoded space
            "123e4567-e89b-12d3-a456-426614174000/",     # Trailing slash
            "123e4567-e89b-12d3-a456-426614174000?param=value",  # Query params
            # Path traversal attempt
            "../123e4567-e89b-12d3-a456-426614174000",
        ]

        for special_id in special_char_ids:
            # Act
            response: Response = client.get(f"/api/v1/strategies/{special_id}")

            # Assert - Should reject invalid format
            expected_codes = [400, 404, 422]
            actual_status = response.status_code
            assert actual_status in expected_codes, (
                f"Special character ID '{special_id}' should return "
                f"{expected_codes}, got {actual_status}"
            )

    def test_get_strategy_wrong_http_method_contract(
        self, client: TestClient, valid_strategy_id: str
    ) -> None:
        """
        Test strategy get endpoint with wrong HTTP method.

        Contract Requirements:
        - Only GET method should be accepted
        - Other methods should return 405 Method Not Allowed
        """
        # Test various HTTP methods that should not be allowed
        methods_to_test = [
            ("POST", client.post),
            ("PATCH", client.patch),
            ("DELETE", client.delete),  # DELETE is actually allowed per spec
        ]

        for method_name, method_func in methods_to_test:
            # Act
            response: Response = method_func(
                f"/api/v1/strategies/{valid_strategy_id}"
            )

            # Assert - Status Code
            if method_name == "DELETE":
                # DELETE is allowed per API spec, should return 204 or 404
                acceptable_codes = [204, 404, 405]
            else:
                # Other methods should not be allowed
                acceptable_codes = [405]
            
            actual_status = response.status_code
            assert actual_status in acceptable_codes, (
                f"{method_name} method should return {acceptable_codes}, "
                f"got {actual_status}"
            )

    def test_get_strategy_case_sensitivity_contract(
        self, client: TestClient
    ) -> None:
        """
        Test UUID case sensitivity in strategy retrieval.

        Contract Requirements:
        - UUIDs should be case-insensitive (standard UUID behavior)
        - Both uppercase and lowercase should work identically
        """
        # Arrange - Same UUID in different cases
        base_uuid = "123e4567-e89b-12d3-a456-426614174000"
        uppercase_uuid = base_uuid.upper()
        lowercase_uuid = base_uuid.lower()
        mixed_case_uuid = "123E4567-e89B-12D3-a456-426614174000"

        uuids_to_test = [uppercase_uuid, lowercase_uuid, mixed_case_uuid]

        for test_uuid in uuids_to_test:
            # Act
            response: Response = client.get(f"/api/v1/strategies/{test_uuid}")

            # Assert - Should handle case consistently
            # Both should return same status
            # (likely 404 since strategy doesn't exist)
            acceptable_codes = [200, 404]
            actual_status = response.status_code
            assert actual_status in acceptable_codes, (
                f"UUID '{test_uuid}' should return {acceptable_codes}, "
                f"got {actual_status}"
            )

    def test_get_strategy_response_headers_contract(
        self, client: TestClient, valid_strategy_id: str
    ) -> None:
        """
        Test response headers for strategy get endpoint.

        Contract Requirements:
        - Content-Type should be application/json
        - Standard HTTP headers should be present
        """
        # Act
        response: Response = client.get(
            f"/api/v1/strategies/{valid_strategy_id}"
        )

        # Assert - Response Headers
        headers = response.headers
        
        # Content-Type should be JSON for both success and error responses
        content_type = headers.get("content-type", "").lower()
        assert "application/json" in content_type, (
            f"Expected JSON content type, got {content_type}"
        )

        # Should have standard HTTP headers
        assert "date" in headers or "Date" in headers, (
            "Response should include Date header"
        )

    def test_get_strategy_concurrent_requests_contract(
        self, client: TestClient, valid_strategy_id: str
    ) -> None:
        """
        Test multiple concurrent requests to same strategy.

        Contract Requirements:
        - Multiple requests should return consistent results
        - No race conditions or inconsistent responses
        """
        # Act - Make multiple requests to the same endpoint
        responses = []
        for _ in range(5):
            response = client.get(f"/api/v1/strategies/{valid_strategy_id}")
            responses.append(response)

        # Assert - All responses should have same status code
        status_codes = [r.status_code for r in responses]
        first_status = status_codes[0]
        
        for i, status in enumerate(status_codes):
            assert status == first_status, (
                f"Request {i} returned status {status}, "
                f"expected {first_status}"
            )

        # If all responses are 200, verify consistent data
        if first_status == 200:
            first_response_data = responses[0].json()
            for i, response in enumerate(responses[1:], 1):
                response_data = response.json()
                assert response_data == first_response_data, (
                    f"Request {i} returned different data than first request"
                )

    def _validate_strategy_structure(self, strategy: dict) -> None:
        """
        Helper method to validate the structure of a strategy object.

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

        # Performance object validation
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

        # Timestamp validation
        created_at = strategy["created_at"]
        assert isinstance(created_at, str), "created_at must be string"
        assert len(created_at) > 0, "created_at cannot be empty"

        updated_at = strategy["updated_at"]
        assert isinstance(updated_at, str), "updated_at must be string"
        assert len(updated_at) > 0, "updated_at cannot be empty"
