"""
Contract tests for POST /api/v1/auth/login endpoint.

These tests validate the API contract defined in the REST API specification.
Following TDD principles, these tests should fail initially until the
endpoint is implemented.
"""

import pytest
from fastapi.testclient import TestClient
from httpx import Response
import uuid


class TestAuthLoginContract:
    """Contract tests for the auth login endpoint."""

    @pytest.fixture
    def client(self) -> TestClient:
        """
        Create a test client for the FastAPI application.
        This will fail until the main FastAPI app is implemented.
        """
        # This import will fail until the main app is created
        from src.main import app

        return TestClient(app)

    def test_login_success_contract(self, client: TestClient) -> None:
        """
        Test successful login contract compliance.

        Contract Requirements:
        - POST /api/v1/auth/login
        - Request: {"username": str, "password": str}
        - Response 200: {
            "access_token": str,
            "token_type": str,
            "expires_in": int,
            "user_id": str
          }
        """
        # Arrange
        login_data = {"username": "pranay", "password": "secure_password"}

        # Act
        response: Response = client.post("/api/v1/auth/login", json=login_data)

        # Assert - Status Code
        expected_status = 200
        actual_status = response.status_code
        assert (
            actual_status == expected_status
        ), f"Expected status {expected_status}, got {actual_status}"

        # Assert - Response Structure
        response_json = response.json()

        # Verify all required fields are present
        required_fields = ["access_token", "token_type", "expires_in", "user_id"]
        for field in required_fields:
            assert field in response_json, f"Response must contain '{field}'"

        # Verify field types and formats
        access_token = response_json["access_token"]
        assert isinstance(access_token, str), "access_token must be string"
        assert len(access_token) > 0, "access_token cannot be empty"

        token_type = response_json["token_type"]
        assert token_type == "bearer", "token_type must be 'bearer'"

        expires_in = response_json["expires_in"]
        assert isinstance(expires_in, int), "expires_in must be integer"
        assert expires_in > 0, "expires_in must be positive"

        user_id = response_json["user_id"]
        assert isinstance(user_id, str), "user_id must be string"

        # Verify user_id is a valid UUID format
        try:
            uuid.UUID(user_id)
        except ValueError:
            pytest.fail("user_id must be a valid UUID")

    def test_login_invalid_credentials_contract(self, client: TestClient) -> None:
        """
        Test login with invalid credentials contract compliance.

        Contract Requirements:
        - POST /api/v1/auth/login with invalid credentials
        - Response 401: {"error": str}
        """
        # Arrange
        invalid_login_data = {"username": "invalid_user", "password": "wrong_password"}

        # Act
        response: Response = client.post("/api/v1/auth/login", json=invalid_login_data)

        # Assert - Status Code
        expected_status = 401
        actual_status = response.status_code
        assert (
            actual_status == expected_status
        ), f"Expected status {expected_status}, got {actual_status}"

        # Assert - Response Structure
        response_json = response.json()
        assert "error" in response_json, "401 response must contain 'error' field"

        error_msg = response_json["error"]
        assert isinstance(error_msg, str), "error must be string"
        assert len(error_msg) > 0, "error message cannot be empty"

    def test_login_missing_username_contract(self, client: TestClient) -> None:
        """
        Test login request without username.

        Contract Requirements:
        - Request must include both username and password
        - Should return 400 or 422 for validation error
        """
        # Arrange
        incomplete_data = {"password": "secure_password"}

        # Act
        response: Response = client.post("/api/v1/auth/login", json=incomplete_data)

        # Assert - Status Code (422 for validation error is acceptable)
        expected_codes = [400, 422]
        actual_status = response.status_code
        assert (
            actual_status in expected_codes
        ), f"Expected status {expected_codes}, got {actual_status}"

        # Assert - Response contains error information
        response_json = response.json()
        has_error_info = "error" in response_json or "detail" in response_json
        assert has_error_info, "Response must contain error information"

    def test_login_missing_password_contract(self, client: TestClient) -> None:
        """
        Test login request without password.

        Contract Requirements:
        - Request must include both username and password
        - Should return 400 or 422 for validation error
        """
        # Arrange
        incomplete_data = {"username": "pranay"}

        # Act
        response: Response = client.post("/api/v1/auth/login", json=incomplete_data)

        # Assert - Status Code (422 for validation error is acceptable)
        expected_codes = [400, 422]
        actual_status = response.status_code
        assert (
            actual_status in expected_codes
        ), f"Expected status {expected_codes}, got {actual_status}"

        # Assert - Response contains error information
        response_json = response.json()
        has_error_info = "error" in response_json or "detail" in response_json
        assert has_error_info, "Response must contain error information"

    def test_login_empty_request_body_contract(self, client: TestClient) -> None:
        """
        Test login request with empty JSON body.

        Contract Requirements:
        - Request must be valid JSON with required fields
        - Should return 400 or 422 for validation error
        """
        # Act
        response: Response = client.post("/api/v1/auth/login", json={})

        # Assert - Status Code
        expected_codes = [400, 422]
        actual_status = response.status_code
        assert (
            actual_status in expected_codes
        ), f"Expected status {expected_codes}, got {actual_status}"

        # Assert - Response contains error information
        response_json = response.json()
        has_error_info = "error" in response_json or "detail" in response_json
        assert has_error_info, "Response must contain error information"

    def test_login_invalid_json_contract(self, client: TestClient) -> None:
        """
        Test login request with invalid JSON.

        Contract Requirements:
        - Request must be valid JSON
        - Should return 400 or 422 for malformed request
        """
        # Act
        response: Response = client.post(
            "/api/v1/auth/login",
            data="invalid json content",
            headers={"Content-Type": "application/json"},
        )

        # Assert - Status Code
        expected_codes = [400, 422]
        actual_status = response.status_code
        assert (
            actual_status in expected_codes
        ), f"Expected status {expected_codes}, got {actual_status}"

    def test_login_wrong_http_method_contract(self, client: TestClient) -> None:
        """
        Test login endpoint with wrong HTTP method.

        Contract Requirements:
        - Only POST method should be accepted
        - GET should return 405 Method Not Allowed
        """
        # Act
        response: Response = client.get("/api/v1/auth/login")

        # Assert - Status Code
        expected_status = 405
        actual_status = response.status_code
        assert (
            actual_status == expected_status
        ), f"Expected status {expected_status}, got {actual_status}"

    def test_login_content_type_validation(self, client: TestClient) -> None:
        """
        Test login endpoint content-type validation.

        Contract Requirements:
        - Endpoint should accept application/json
        - Other content types may be rejected
        """
        # Arrange
        login_data = {"username": "pranay", "password": "secure_password"}

        # Act - Test with correct content type
        response: Response = client.post(
            "/api/v1/auth/login",
            json=login_data,
            headers={"Content-Type": "application/json"},
        )

        # Assert - Should work with application/json
        # Note: This test will fail until implementation exists
        # The actual assertion depends on whether the endpoint exists
        acceptable_codes = [200, 401, 404]
        actual_status = response.status_code
        assert (
            actual_status in acceptable_codes
        ), f"Unexpected status code: {actual_status}"
