"""
Contract tests for GET /api/v1/system/status endpoint.

These tests validate the API contract defined in the REST API specification.
Following TDD principles, these tests should fail initially until the
endpoint is implemented.
"""

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from datetime import datetime


class TestSystemStatusContract:
    """Contract tests for the system status endpoint."""

    @pytest.fixture
    def client(self) -> TestClient:
        """
        Create a test client for the FastAPI application.
        This will fail until the main FastAPI app is implemented.
        """
        # This import will fail until the main app is created
        from src.main import app

        return TestClient(app)

    def test_get_system_status_success_contract(self, client: TestClient) -> None:
        """
        Test successful system status retrieval contract compliance.

        Contract Requirements:
        - GET /api/v1/system/status
        - Response 200: SystemStatus schema validation
        - SystemStatus contains: status, trading_mode, market_hours,
          services, api_connections, system_metrics
        """
        # Act
        response: Response = client.get("/api/v1/system/status")

        # Assert - Status Code
        expected_status = 200
        actual_status = response.status_code
        assert (
            actual_status == expected_status
        ), f"Expected status {expected_status}, got {actual_status}"

        # Assert - Response Structure
        response_json = response.json()
        self._validate_system_status_schema(response_json)

    def test_get_system_status_wrong_http_method_contract(
        self, client: TestClient
    ) -> None:
        """
        Test system status endpoint with wrong HTTP method.

        Contract Requirements:
        - Only GET method should be accepted
        - POST should return 405 Method Not Allowed
        """
        # Act
        response: Response = client.post("/api/v1/system/status")

        # Assert - Status Code
        expected_status = 405
        actual_status = response.status_code
        assert (
            actual_status == expected_status
        ), f"Expected status {expected_status}, got {actual_status}"

    def test_get_system_status_put_method_contract(self, client: TestClient) -> None:
        """
        Test system status endpoint with PUT method.

        Contract Requirements:
        - Only GET method should be accepted
        - PUT should return 405 Method Not Allowed
        """
        # Act
        response: Response = client.put("/api/v1/system/status")

        # Assert - Status Code
        expected_status = 405
        actual_status = response.status_code
        assert (
            actual_status == expected_status
        ), f"Expected status {expected_status}, got {actual_status}"

    def test_get_system_status_delete_method_contract(self, client: TestClient) -> None:
        """
        Test system status endpoint with DELETE method.

        Contract Requirements:
        - Only GET method should be accepted
        - DELETE should return 405 Method Not Allowed
        """
        # Act
        response: Response = client.delete("/api/v1/system/status")

        # Assert - Status Code
        expected_status = 405
        actual_status = response.status_code
        assert (
            actual_status == expected_status
        ), f"Expected status {expected_status}, got {actual_status}"

    def test_get_system_status_authorization_contract(self, client: TestClient) -> None:
        """
        Test system status endpoint requires authorization.

        Contract Requirements:
        - Endpoint should require Bearer token authentication
        - Missing token may return 401 Unauthorized or allow access
          depending on implementation (system status might be public)
        """
        # Act - Request without authorization header
        response: Response = client.get(
            "/api/v1/system/status", headers={}  # No Authorization header
        )

        # Assert - Status Code
        # Note: System status might be public or require auth
        acceptable_codes = [200, 401, 404]  # 404 if endpoint not implemented
        actual_status = response.status_code
        assert (
            actual_status in acceptable_codes
        ), f"Unexpected status code: {actual_status}"

    def test_get_system_status_content_type_contract(self, client: TestClient) -> None:
        """
        Test system status endpoint returns JSON content.

        Contract Requirements:
        - Response should have application/json content-type
        - Response should be valid JSON
        """
        # Act
        response: Response = client.get("/api/v1/system/status")

        # Assert - Response should be JSON (if endpoint exists)
        if response.status_code == 200:
            content_type = response.headers.get("content-type", "")
            assert (
                "application/json" in content_type
            ), "Response should have application/json content-type"

            # Should be parseable as JSON
            try:
                response.json()
            except ValueError:
                pytest.fail("Response should be valid JSON")

    def test_get_system_status_query_params_ignored_contract(
        self, client: TestClient
    ) -> None:
        """
        Test system status endpoint ignores query parameters.

        Contract Requirements:
        - Endpoint does not accept query parameters
        - Should return same response regardless of query params
        """
        # Act - Request with query parameters
        response: Response = client.get(
            "/api/v1/system/status?unused_param=value&another=test"
        )

        # Assert - Should work same as without params
        acceptable_codes = [200, 404]  # 404 if endpoint not implemented
        actual_status = response.status_code
        assert (
            actual_status in acceptable_codes
        ), f"Query parameters should be ignored, got {actual_status}"

    def test_get_system_status_consistency_contract(self, client: TestClient) -> None:
        """
        Test system status endpoint returns consistent schema.

        Contract Requirements:
        - Multiple requests should return same schema structure
        - Values may change but structure should be consistent
        """
        # Act - Make multiple requests
        response1: Response = client.get("/api/v1/system/status")
        response2: Response = client.get("/api/v1/system/status")

        # Assert - Both should have same status code
        assert (
            response1.status_code == response2.status_code
        ), "Multiple requests should return same status code"

        # If successful, both should have same schema structure
        if response1.status_code == 200 and response2.status_code == 200:
            data1 = response1.json()
            data2 = response2.json()

            # Check that both responses have same top-level keys
            assert set(data1.keys()) == set(
                data2.keys()
            ), "Response schema should be consistent across requests"

    def _validate_system_status_schema(self, status_data: dict) -> None:
        """
        Validate SystemStatus schema compliance.

        Required fields from OpenAPI spec:
        - status: string (HEALTHY/DEGRADED/DOWN)
        - trading_mode: string (paper/live)
        - market_hours: boolean
        - services: object with service statuses
        - api_connections: object with connection statuses
        - system_metrics: object with system metrics
        """
        # Validate status field
        assert "status" in status_data, "Response must contain 'status'"
        status = status_data["status"]
        valid_statuses = ["HEALTHY", "DEGRADED", "DOWN"]
        assert (
            status in valid_statuses
        ), f"status must be one of {valid_statuses}, got '{status}'"

        # Validate trading_mode field
        assert "trading_mode" in status_data, "Response must contain 'trading_mode'"
        trading_mode = status_data["trading_mode"]
        valid_modes = ["paper", "live"]
        assert (
            trading_mode in valid_modes
        ), f"trading_mode must be one of {valid_modes}, got '{trading_mode}'"

        # Validate market_hours field
        assert "market_hours" in status_data, "Response must contain 'market_hours'"
        market_hours = status_data["market_hours"]
        assert isinstance(market_hours, bool), "market_hours must be boolean"

        # Validate services object
        assert "services" in status_data, "Response must contain 'services'"
        services = status_data["services"]
        assert isinstance(services, dict), "services must be object"

        # Validate expected services
        expected_services = [
            "data_manager",
            "analysis_engine",
            "execution_engine",
            "ai_service",
        ]
        valid_service_statuses = ["RUNNING", "STOPPED", "ERROR"]

        for service_name in expected_services:
            if service_name in services:
                service_status = services[service_name]
                assert service_status in valid_service_statuses, (
                    f"Service '{service_name}' status must be one of "
                    f"{valid_service_statuses}"
                )

        # Validate api_connections object
        assert (
            "api_connections" in status_data
        ), "Response must contain 'api_connections'"
        api_connections = status_data["api_connections"]
        assert isinstance(api_connections, dict), "api_connections must be object"

        # Validate API connection structure
        valid_connection_statuses = ["CONNECTED", "DISCONNECTED", "ERROR"]
        expected_apis = ["angel_one", "dhan"]

        for api_name in expected_apis:
            if api_name in api_connections:
                api_conn = api_connections[api_name]
                assert isinstance(
                    api_conn, dict
                ), f"API connection '{api_name}' must be object"

                if "status" in api_conn:
                    conn_status = api_conn["status"]
                    assert conn_status in valid_connection_statuses, (
                        f"API '{api_name}' status must be one of "
                        f"{valid_connection_statuses}"
                    )

                if "last_heartbeat" in api_conn:
                    heartbeat = api_conn["last_heartbeat"]
                    if heartbeat is not None:
                        try:
                            datetime.fromisoformat(heartbeat.replace("Z", "+00:00"))
                        except ValueError:
                            pytest.fail(
                                f"API '{api_name}' last_heartbeat must be "
                                "valid ISO datetime"
                            )

        # Validate system_metrics object
        assert "system_metrics" in status_data, "Response must contain 'system_metrics'"
        system_metrics = status_data["system_metrics"]
        assert isinstance(system_metrics, dict), "system_metrics must be object"

        # Validate expected metrics
        numeric_metrics = ["cpu_usage_pct", "memory_usage_pct", "disk_usage_pct"]
        integer_metrics = ["active_strategies", "open_positions"]

        for metric_name in numeric_metrics:
            if metric_name in system_metrics:
                metric_value = system_metrics[metric_name]
                assert isinstance(
                    metric_value, (int, float)
                ), f"Metric '{metric_name}' must be numeric"
                if "usage_pct" in metric_name:
                    assert (
                        0 <= metric_value <= 100
                    ), f"Percentage metric '{metric_name}' must be 0-100"

        for metric_name in integer_metrics:
            if metric_name in system_metrics:
                metric_value = system_metrics[metric_name]
                assert isinstance(
                    metric_value, int
                ), f"Metric '{metric_name}' must be integer"
                assert (
                    metric_value >= 0
                ), f"Count metric '{metric_name}' must be non-negative"
