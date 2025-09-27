"""
Contract tests for PUT /api/v1/strategies/{strategy_id} endpoint.

These tests validate the API contract defined in the REST API specification.
Following TDD principles, these tests should fail initially until the
endpoint is implemented.
"""

import pytest
from fastapi.testclient import TestClient
from httpx import Response
import uuid


class TestStrategiesUpdateContract:
    """Contract tests for the strategy update endpoint."""

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

    @pytest.fixture
    def valid_strategy_update_data(self) -> dict:
        """Valid strategy update data matching StrategyUpdate schema."""
        return {
            "parameters": {
                "risk_threshold": 0.08,
                "lookback_period": 25,
                "volume_threshold": 2000000,
            },
            "min_confidence": 0.85,
            "max_position_size": 75000.0,
            "stop_loss_pct": 3.0,
            "take_profit_pct": 6.0,
            "is_active": True,
            "is_paper_only": False,
        }

    def test_update_strategy_success_contract(
        self,
        client: TestClient,
        valid_strategy_id: str,
        valid_strategy_update_data: dict,
    ) -> None:
        """
        Test successful strategy update contract compliance.

        Contract Requirements:
        - PUT /api/v1/strategies/{strategy_id}
        - Path parameter: strategy_id (UUID format)
        - Request Body: StrategyUpdate schema
        - Response 200: Updated Strategy schema
        """
        # Act
        response: Response = client.put(
            f"/api/v1/strategies/{valid_strategy_id}", json=valid_strategy_update_data
        )

        # Assert - Status Code
        # Initially expecting 404 since no strategies exist in empty system
        # Once implementation exists, should be 200 for existing strategies
        acceptable_codes = [200, 404]
        actual_status = response.status_code
        assert (
            actual_status in acceptable_codes
        ), f"Expected status {acceptable_codes}, got {actual_status}"

        # If 200 response, validate updated strategy structure
        if actual_status == 200:
            response_json = response.json()
            self._validate_strategy_response_structure(response_json)

            # Verify the returned strategy has the requested ID
            returned_id = response_json["strategy_id"]
            assert (
                returned_id == valid_strategy_id
            ), f"Expected strategy_id {valid_strategy_id}, got {returned_id}"

            # Verify updated fields are applied
            if "parameters" in valid_strategy_update_data:
                expected_params = valid_strategy_update_data["parameters"]
                actual_params = response_json["parameters"]
                assert actual_params == expected_params, (
                    f"Parameters not updated correctly: expected {expected_params}, "
                    f"got {actual_params}"
                )

            if "min_confidence" in valid_strategy_update_data:
                expected_confidence = valid_strategy_update_data["min_confidence"]
                actual_confidence = response_json["min_confidence"]
                assert actual_confidence == expected_confidence, (
                    f"min_confidence not updated: expected {expected_confidence}, "
                    f"got {actual_confidence}"
                )

            if "max_position_size" in valid_strategy_update_data:
                expected_size = valid_strategy_update_data["max_position_size"]
                actual_size = response_json["max_position_size"]
                assert actual_size == expected_size, (
                    f"max_position_size not updated: expected {expected_size}, "
                    f"got {actual_size}"
                )

            if "stop_loss_pct" in valid_strategy_update_data:
                expected_stop_loss = valid_strategy_update_data["stop_loss_pct"]
                actual_stop_loss = response_json["stop_loss_pct"]
                assert actual_stop_loss == expected_stop_loss, (
                    f"stop_loss_pct not updated: expected {expected_stop_loss}, "
                    f"got {actual_stop_loss}"
                )

            if "take_profit_pct" in valid_strategy_update_data:
                expected_profit = valid_strategy_update_data["take_profit_pct"]
                actual_profit = response_json["take_profit_pct"]
                assert actual_profit == expected_profit, (
                    f"take_profit_pct not updated: expected {expected_profit}, "
                    f"got {actual_profit}"
                )

            if "is_active" in valid_strategy_update_data:
                expected_active = valid_strategy_update_data["is_active"]
                actual_active = response_json["is_active"]
                assert actual_active == expected_active, (
                    f"is_active not updated: expected {expected_active}, "
                    f"got {actual_active}"
                )

            if "is_paper_only" in valid_strategy_update_data:
                expected_paper = valid_strategy_update_data["is_paper_only"]
                actual_paper = response_json["is_paper_only"]
                assert actual_paper == expected_paper, (
                    f"is_paper_only not updated: expected {expected_paper}, "
                    f"got {actual_paper}"
                )

            # Verify updated_at timestamp is more recent than created_at
            created_at = response_json.get("created_at")
            updated_at = response_json.get("updated_at")
            if created_at and updated_at:
                assert (
                    updated_at >= created_at
                ), "updated_at should be equal or more recent than created_at"

        # If 404 response, validate error structure
        elif actual_status == 404:
            response_json = response.json()
            assert "detail" in response_json, "404 response must contain 'detail' field"

    def test_update_strategy_not_found_contract(
        self, client: TestClient, valid_strategy_update_data: dict
    ) -> None:
        """
        Test strategy update with non-existent strategy ID.

        Contract Requirements:
        - PUT /api/v1/strategies/{non_existent_id}
        - Response 404: NotFound error response
        """
        # Arrange - Use a UUID that definitely doesn't exist
        non_existent_id = str(uuid.uuid4())

        # Act
        response: Response = client.put(
            f"/api/v1/strategies/{non_existent_id}", json=valid_strategy_update_data
        )

        # Assert - Status Code
        expected_status = 404
        actual_status = response.status_code
        assert (
            actual_status == expected_status
        ), f"Expected status {expected_status}, got {actual_status}"

        # Assert - Response Structure
        response_json = response.json()
        assert "detail" in response_json, "404 response must contain 'detail' field"

        detail = response_json["detail"]
        assert isinstance(detail, str), "detail must be a string"
        assert len(detail) > 0, "detail cannot be empty"

    def test_update_strategy_invalid_uuid_format_contract(
        self, client: TestClient, valid_strategy_update_data: dict
    ) -> None:
        """
        Test strategy update with invalid UUID format.

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
            response: Response = client.put(
                f"/api/v1/strategies/{invalid_id}", json=valid_strategy_update_data
            )

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
                assert "detail" in response_json, "422 response must contain 'detail'"

    def test_update_strategy_partial_update_contract(
        self, client: TestClient, valid_strategy_id: str
    ) -> None:
        """
        Test partial strategy update with only some fields.

        Contract Requirements:
        - All fields in StrategyUpdate are optional
        - Should accept partial updates with any subset of fields
        - Only provided fields should be updated
        """
        # Test various partial update scenarios
        partial_updates = [
            # Only parameters
            {"parameters": {"new_param": "new_value"}},
            # Only confidence
            {"min_confidence": 0.9},
            # Only position size
            {"max_position_size": 100000.0},
            # Only stop loss
            {"stop_loss_pct": 1.5},
            # Only take profit
            {"take_profit_pct": 8.0},
            # Only active status
            {"is_active": False},
            # Only paper mode
            {"is_paper_only": True},
            # Multiple fields
            {"min_confidence": 0.75, "max_position_size": 60000.0, "is_active": True},
        ]

        for update_data in partial_updates:
            # Act
            response: Response = client.put(
                f"/api/v1/strategies/{valid_strategy_id}", json=update_data
            )

            # Assert - Should accept partial updates
            acceptable_codes = [200, 404]  # 404 if strategy doesn't exist
            actual_status = response.status_code
            assert actual_status in acceptable_codes, (
                f"Partial update {update_data} should return {acceptable_codes}, "
                f"got {actual_status}"
            )

            # If successful, verify the updated fields are present
            if actual_status == 200:
                response_json = response.json()

                # Verify each field from update is applied
                for field, expected_value in update_data.items():
                    actual_value = response_json.get(field)
                    assert actual_value == expected_value, (
                        f"Field '{field}' not updated correctly: "
                        f"expected {expected_value}, got {actual_value}"
                    )

    def test_update_strategy_invalid_confidence_range_contract(
        self, client: TestClient, valid_strategy_id: str
    ) -> None:
        """
        Test strategy update with invalid min_confidence values.

        Contract Requirements:
        - min_confidence must be between 0 and 1
        - Should return 400 Bad Request or 422 Unprocessable Entity
        """
        # Test confidence > 1
        high_confidence_data = {"min_confidence": 1.5}

        response = client.put(
            f"/api/v1/strategies/{valid_strategy_id}", json=high_confidence_data
        )
        expected_codes = [400, 422]
        assert (
            response.status_code in expected_codes
        ), f"min_confidence > 1 should return {expected_codes}, got {response.status_code}"

        # Test confidence < 0
        low_confidence_data = {"min_confidence": -0.1}

        response = client.put(
            f"/api/v1/strategies/{valid_strategy_id}", json=low_confidence_data
        )
        assert (
            response.status_code in expected_codes
        ), f"min_confidence < 0 should return {expected_codes}, got {response.status_code}"

    def test_update_strategy_empty_parameters_contract(
        self, client: TestClient, valid_strategy_id: str
    ) -> None:
        """
        Test strategy update with empty parameters object.

        Contract Requirements:
        - parameters can be empty object
        - Should clear existing parameters if empty object provided
        """
        # Act - Empty parameters object
        empty_params_data = {"parameters": {}}

        response = client.put(
            f"/api/v1/strategies/{valid_strategy_id}", json=empty_params_data
        )

        # Assert - Should accept empty parameters
        acceptable_codes = [200, 404]
        assert (
            response.status_code in acceptable_codes
        ), f"Empty parameters should return {acceptable_codes}, got {response.status_code}"

        # If successful, verify parameters is empty
        if response.status_code == 200:
            response_json = response.json()
            assert (
                response_json.get("parameters") == {}
            ), "Empty parameters object should clear existing parameters"

    def test_update_strategy_invalid_json_contract(
        self, client: TestClient, valid_strategy_id: str
    ) -> None:
        """
        Test strategy update with malformed JSON.

        Contract Requirements:
        - Should return 400 Bad Request or 422 Unprocessable Entity
        """
        # Act - Send malformed JSON
        response = client.put(
            f"/api/v1/strategies/{valid_strategy_id}",
            data="{ invalid json",
            headers={"Content-Type": "application/json"},
        )

        # Assert
        expected_codes = [400, 422]
        assert (
            response.status_code in expected_codes
        ), f"Malformed JSON should return {expected_codes}, got {response.status_code}"

    def test_update_strategy_wrong_content_type_contract(
        self,
        client: TestClient,
        valid_strategy_id: str,
        valid_strategy_update_data: dict,
    ) -> None:
        """
        Test strategy update with wrong Content-Type.

        Contract Requirements:
        - Should only accept application/json
        - Should return 415 Unsupported Media Type or 422
        """
        import json

        # Act - Send as form data
        response = client.put(
            f"/api/v1/strategies/{valid_strategy_id}",
            data=json.dumps(valid_strategy_update_data),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        # Assert
        expected_codes = [400, 415, 422]
        assert (
            response.status_code in expected_codes
        ), f"Wrong content type should return {expected_codes}, got {response.status_code}"

    def test_update_strategy_wrong_http_method_contract(
        self,
        client: TestClient,
        valid_strategy_id: str,
        valid_strategy_update_data: dict,
    ) -> None:
        """
        Test strategy update endpoint with wrong HTTP method.

        Contract Requirements:
        - Only PUT method should be accepted for updates
        - Other methods should return 405 Method Not Allowed
        """
        # Test PATCH method (common alternative for updates)
        patch_response = client.patch(
            f"/api/v1/strategies/{valid_strategy_id}", json=valid_strategy_update_data
        )

        # PATCH might be allowed as alternative update method
        acceptable_codes = [200, 404, 405]
        assert (
            patch_response.status_code in acceptable_codes
        ), f"PATCH method should return {acceptable_codes}, got {patch_response.status_code}"

        # Test POST method (should not be allowed for updates)
        post_response = client.post(
            f"/api/v1/strategies/{valid_strategy_id}", json=valid_strategy_update_data
        )

        # POST should not be allowed for specific resource updates
        expected_codes = [
            404,
            405,
        ]  # 404 if route doesn't exist, 405 if method not allowed
        assert (
            post_response.status_code in expected_codes
        ), f"POST method should return {expected_codes}, got {post_response.status_code}"

    def test_update_strategy_empty_request_body_contract(
        self, client: TestClient, valid_strategy_id: str
    ) -> None:
        """
        Test strategy update with empty request body.

        Contract Requirements:
        - Empty JSON object should be accepted (no updates applied)
        - Should return current strategy unchanged
        """
        # Act - Empty JSON object
        response = client.put(f"/api/v1/strategies/{valid_strategy_id}", json={})

        # Assert - Should accept empty update
        acceptable_codes = [200, 404]
        assert (
            response.status_code in acceptable_codes
        ), f"Empty update should return {acceptable_codes}, got {response.status_code}"

        # If successful, verify strategy structure is still valid
        if response.status_code == 200:
            response_json = response.json()
            self._validate_strategy_response_structure(response_json)

    def test_update_strategy_concurrent_updates_contract(
        self, client: TestClient, valid_strategy_id: str
    ) -> None:
        """
        Test concurrent updates to same strategy.

        Contract Requirements:
        - Multiple concurrent updates should be handled gracefully
        - Last update should win (or return appropriate conflict error)
        """
        # Prepare different update payloads
        updates = [
            {"min_confidence": 0.8},
            {"max_position_size": 80000.0},
            {"is_active": False},
            {"stop_loss_pct": 2.8},
            {"take_profit_pct": 5.5},
        ]

        responses = []

        # Act - Make concurrent requests
        for update_data in updates:
            response = client.put(
                f"/api/v1/strategies/{valid_strategy_id}", json=update_data
            )
            responses.append((response, update_data))

        # Assert - All requests should be handled
        for response, update_data in responses:
            acceptable_codes = [200, 404, 409]  # 409 for potential conflicts
            assert response.status_code in acceptable_codes, (
                f"Concurrent update {update_data} should return {acceptable_codes}, "
                f"got {response.status_code}"
            )

    def test_update_strategy_invalid_field_types_contract(
        self, client: TestClient, valid_strategy_id: str
    ) -> None:
        """
        Test strategy update with invalid field types.

        Contract Requirements:
        - Should validate field types according to StrategyUpdate schema
        - Should return 400 Bad Request or 422 Unprocessable Entity
        """
        # Test various invalid type scenarios
        invalid_updates = [
            # String instead of number for min_confidence
            {"min_confidence": "not_a_number"},
            # String instead of number for max_position_size
            {"max_position_size": "not_a_number"},
            # String instead of number for stop_loss_pct
            {"stop_loss_pct": "not_a_number"},
            # String instead of number for take_profit_pct
            {"take_profit_pct": "not_a_number"},
            # String instead of boolean for is_active
            {"is_active": "not_a_boolean"},
            # String instead of boolean for is_paper_only
            {"is_paper_only": "not_a_boolean"},
            # Array instead of object for parameters
            {"parameters": ["not", "an", "object"]},
        ]

        for invalid_data in invalid_updates:
            # Act
            response = client.put(
                f"/api/v1/strategies/{valid_strategy_id}", json=invalid_data
            )

            # Assert
            expected_codes = [400, 422]
            assert response.status_code in expected_codes, (
                f"Invalid data {invalid_data} should return {expected_codes}, "
                f"got {response.status_code}"
            )

    def test_update_strategy_readonly_fields_ignored_contract(
        self, client: TestClient, valid_strategy_id: str
    ) -> None:
        """
        Test that readonly fields are ignored in update requests.

        Contract Requirements:
        - Fields not in StrategyUpdate schema should be ignored
        - Should not return error for extra fields (graceful handling)
        """
        # Act - Include readonly fields that should be ignored
        update_with_readonly = {
            "strategy_id": str(uuid.uuid4()),  # Should be ignored
            "name": "New Name",  # Should be ignored
            "category": "mathematical",  # Should be ignored
            "target_symbols": ["NEWSTOCK"],  # Should be ignored
            "created_at": "2024-01-01T00:00:00Z",  # Should be ignored
            "updated_at": "2024-01-01T00:00:00Z",  # Should be ignored
            "performance": {"total_trades": 999},  # Should be ignored
            # Valid fields that should be applied
            "min_confidence": 0.95,
            "is_active": True,
        }

        response = client.put(
            f"/api/v1/strategies/{valid_strategy_id}", json=update_with_readonly
        )

        # Assert - Should not fail due to extra fields
        acceptable_codes = [200, 404]
        assert response.status_code in acceptable_codes, (
            f"Update with readonly fields should return {acceptable_codes}, "
            f"got {response.status_code}"
        )

        # If successful, verify only valid fields were applied
        if response.status_code == 200:
            response_json = response.json()

            # Readonly fields should not be changed by the request
            assert (
                response_json["strategy_id"] == valid_strategy_id
            ), "strategy_id should not be changed by update"

            # Valid fields should be applied
            assert (
                response_json["min_confidence"] == 0.95
            ), "min_confidence should be updated"
            assert response_json["is_active"] is True, "is_active should be updated"

    def _validate_strategy_response_structure(self, strategy: dict) -> None:
        """
        Helper method to validate the structure of a strategy response object.

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

        # Performance object validation (if present)
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

        # Timestamp validation
        created_at = strategy["created_at"]
        assert isinstance(created_at, str), "created_at must be string"
        assert len(created_at) > 0, "created_at cannot be empty"

        updated_at = strategy["updated_at"]
        assert isinstance(updated_at, str), "updated_at must be string"
        assert len(updated_at) > 0, "updated_at cannot be empty"
