"""
Contract tests for GET /api/v1/market-data/{symbol} endpoint.

These tests validate the API contract defined in the REST API specification.
Following TDD principles, these tests should fail initially until the
endpoint is implemented.
"""

import pytest
from fastapi.testclient import TestClient
from httpx import Response


class TestMarketDataGetContract:
    """Contract tests for the market data get endpoint."""

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
    def valid_symbol(self) -> str:
        """Valid symbol for testing."""
        return "BANKNIFTY"

    def test_get_market_data_success_contract(
        self, client: TestClient, valid_symbol: str
    ) -> None:
        """
        Test successful market data retrieval contract compliance.

        Contract Requirements:
        - GET /api/v1/market-data/{symbol}
        - Path Parameter: symbol (string)
        - Response 200: Market data with OHLCV data array
        """
        # Act
        response: Response = client.get(f"/api/v1/market-data/{valid_symbol}")

        # Assert - Status Code
        expected_status = 200
        assert (
            response.status_code == expected_status
        ), f"Expected status {expected_status}, got {response.status_code}"

        # Assert - Response Structure
        response_json = response.json()
        self._validate_market_data_response_structure(response_json, valid_symbol)

    def test_get_market_data_with_timeframe_contract(
        self, client: TestClient, valid_symbol: str
    ) -> None:
        """
        Test market data retrieval with timeframe parameter.

        Contract Requirements:
        - timeframe query parameter (1min, 5min, 15min, 1hour, 1day)
        - Default should be 15min if not specified
        """
        timeframes = ["1min", "5min", "15min", "1hour", "1day"]

        for timeframe in timeframes:
            # Act
            response = client.get(
                f"/api/v1/market-data/{valid_symbol}?timeframe={timeframe}"
            )

            # Assert - Status Code
            expected_status = 200
            assert response.status_code == expected_status, (
                f"Timeframe {timeframe}: expected {expected_status}, "
                f"got {response.status_code}"
            )

            # Assert - Response Structure
            response_json = response.json()
            self._validate_market_data_response_structure(response_json, valid_symbol)

            # Assert - Timeframe is reflected in response
            if "timeframe" in response_json:
                assert response_json["timeframe"] == timeframe, (
                    f"Response timeframe should match requested: "
                    f"expected {timeframe}, got {response_json['timeframe']}"
                )

    def test_get_market_data_with_date_range_contract(
        self, client: TestClient, valid_symbol: str
    ) -> None:
        """
        Test market data retrieval with date range parameters.

        Contract Requirements:
        - start_date and end_date query parameters
        - Should filter data within specified range
        """
        # Act
        response = client.get(
            f"/api/v1/market-data/{valid_symbol}"
            "?start_date=2025-01-01T00:00:00Z&end_date=2025-09-19T23:59:59Z"
        )

        # Assert - Status Code
        expected_status = 200
        assert response.status_code == expected_status, (
            f"Date range query: expected {expected_status}, "
            f"got {response.status_code}"
        )

        # Assert - Response Structure
        response_json = response.json()
        self._validate_market_data_response_structure(response_json, valid_symbol)

    def test_get_market_data_with_limit_contract(
        self, client: TestClient, valid_symbol: str
    ) -> None:
        """
        Test market data retrieval with limit parameter.

        Contract Requirements:
        - limit query parameter (1 to 10000, default 1000)
        - Should limit number of data points returned
        """
        # Test with small limit
        response = client.get(f"/api/v1/market-data/{valid_symbol}?limit=10")

        # Assert - Status Code
        expected_status = 200
        assert response.status_code == expected_status, (
            f"Limit query: expected {expected_status}, " f"got {response.status_code}"
        )

        # Assert - Response Structure
        response_json = response.json()
        self._validate_market_data_response_structure(response_json, valid_symbol)

        # Assert - Data array should respect limit
        if "data" in response_json:
            data_points = len(response_json["data"])
            assert (
                data_points <= 10
            ), f"Data points should be limited to 10, got {data_points}"

    def test_get_market_data_invalid_symbol_contract(self, client: TestClient) -> None:
        """
        Test market data retrieval with invalid symbol.

        Contract Requirements:
        - Should handle invalid symbols gracefully
        - Should return appropriate error status
        """
        # Test with non-existent symbol
        invalid_symbol = "INVALIDSYMBOL"
        response = client.get(f"/api/v1/market-data/{invalid_symbol}")

        # Assert - Should return appropriate error status
        acceptable_codes = [400, 404]
        assert response.status_code in acceptable_codes, (
            f"Invalid symbol should return {acceptable_codes}, "
            f"got {response.status_code}"
        )

        # If error response, should contain error details
        if response.status_code in [400, 404]:
            response_json = response.json()
            possible_error_fields = ["detail", "error", "message"]
            has_error_field = any(
                field in response_json for field in possible_error_fields
            )
            assert (
                has_error_field or len(response_json) == 0
            ), "Error response should contain error details or be empty"

    def test_get_market_data_empty_symbol_contract(self, client: TestClient) -> None:
        """
        Test market data retrieval with empty symbol.

        Contract Requirements:
        - Empty symbol should be handled appropriately
        - Should return validation error or 404
        """
        # Act - Empty symbol (this might result in different endpoint)
        response = client.get("/api/v1/market-data/")

        # Assert - Should not succeed with 200
        assert response.status_code != 200, "Empty symbol should not return success"

        # Common responses for empty/missing path parameters
        acceptable_codes = [400, 404, 405, 422]
        assert response.status_code in acceptable_codes, (
            f"Empty symbol should return {acceptable_codes}, "
            f"got {response.status_code}"
        )

    def test_get_market_data_invalid_timeframe_contract(
        self, client: TestClient, valid_symbol: str
    ) -> None:
        """
        Test market data retrieval with invalid timeframe.

        Contract Requirements:
        - timeframe must be one of: 1min, 5min, 15min, 1hour, 1day
        - Should return validation error for invalid values
        """
        invalid_timeframes = ["30sec", "2min", "invalid", "1week"]

        for invalid_timeframe in invalid_timeframes:
            # Act
            response = client.get(
                f"/api/v1/market-data/{valid_symbol}" f"?timeframe={invalid_timeframe}"
            )

            # Assert - Should return validation error
            acceptable_codes = [400, 422]
            assert response.status_code in acceptable_codes, (
                f"Invalid timeframe '{invalid_timeframe}' should return "
                f"{acceptable_codes}, got {response.status_code}"
            )

    def test_get_market_data_invalid_limit_contract(
        self, client: TestClient, valid_symbol: str
    ) -> None:
        """
        Test market data retrieval with invalid limit values.

        Contract Requirements:
        - limit must be 1 to 10000
        - Should return validation error for out-of-range values
        """
        invalid_limits = [0, -1, 10001, 50000]

        for invalid_limit in invalid_limits:
            # Act
            response = client.get(
                f"/api/v1/market-data/{valid_symbol}?limit={invalid_limit}"
            )

            # Assert - Should return validation error
            acceptable_codes = [400, 422]
            assert response.status_code in acceptable_codes, (
                f"Invalid limit {invalid_limit} should return "
                f"{acceptable_codes}, got {response.status_code}"
            )

    def test_get_market_data_invalid_date_format_contract(
        self, client: TestClient, valid_symbol: str
    ) -> None:
        """
        Test market data retrieval with invalid date formats.

        Contract Requirements:
        - start_date and end_date must be valid ISO datetime format
        - Should return validation error for invalid formats
        """
        invalid_dates = ["2025-13-01", "invalid-date", "2025/01/01"]

        for invalid_date in invalid_dates:
            # Act
            response = client.get(
                f"/api/v1/market-data/{valid_symbol}" f"?start_date={invalid_date}"
            )

            # Assert - Should return validation error
            acceptable_codes = [400, 422]
            assert response.status_code in acceptable_codes, (
                f"Invalid date '{invalid_date}' should return "
                f"{acceptable_codes}, got {response.status_code}"
            )

    def test_get_market_data_special_characters_symbol_contract(
        self, client: TestClient
    ) -> None:
        """
        Test market data retrieval with special characters in symbol.

        Contract Requirements:
        - Special characters in symbol should be handled appropriately
        - Should return validation error or 404
        """
        special_symbols = ["TEST@SYMBOL", "WITH SPACE", "WITH/SLASH", "WITH%PERCENT"]

        for special_symbol in special_symbols:
            # Act
            response = client.get(f"/api/v1/market-data/{special_symbol}")

            # Assert - Should not cause server error
            assert (
                response.status_code < 500
            ), f"Special symbol '{special_symbol}' should not cause server error"

            # Should return appropriate error
            acceptable_codes = [400, 404, 422]
            assert response.status_code in acceptable_codes, (
                f"Special symbol '{special_symbol}' should return "
                f"{acceptable_codes}, got {response.status_code}"
            )

    def test_get_market_data_case_sensitivity_contract(
        self, client: TestClient
    ) -> None:
        """
        Test market data retrieval with different case symbols.

        Contract Requirements:
        - Symbol case handling should be consistent
        - Both uppercase and lowercase should be handled appropriately
        """
        # Test with different cases of the same symbol
        symbols = ["BANKNIFTY", "banknifty", "BankNifty"]

        for symbol in symbols:
            # Act
            response = client.get(f"/api/v1/market-data/{symbol}")

            # Assert - Should handle consistently
            acceptable_codes = [200, 400, 404]
            assert (
                response.status_code in acceptable_codes
            ), f"Symbol '{symbol}' returned {response.status_code}"

    def test_get_market_data_performance_contract(
        self, client: TestClient, valid_symbol: str
    ) -> None:
        """
        Test market data retrieval performance characteristics.

        Contract Requirements:
        - Should respond within reasonable time
        - Should not cause timeout or performance issues
        """
        import time

        # Act - Measure response time
        start_time = time.time()
        response = client.get(f"/api/v1/market-data/{valid_symbol}")
        end_time = time.time()

        response_time = end_time - start_time

        # Assert - Response time should be reasonable (less than 10 seconds)
        assert (
            response_time < 10.0
        ), f"Response time {response_time:.2f}s should be under 10 seconds"

        # Assert - Should get a valid HTTP response
        assert (
            200 <= response.status_code < 600
        ), f"Should return valid HTTP status code, got {response.status_code}"

    def test_get_market_data_response_headers_contract(
        self, client: TestClient, valid_symbol: str
    ) -> None:
        """
        Test market data response headers.

        Contract Requirements:
        - Should return appropriate Content-Type
        - Should have standard HTTP headers
        """
        # Act
        response = client.get(f"/api/v1/market-data/{valid_symbol}")

        # Assert - Content-Type header for JSON responses
        if response.status_code == 200:
            content_type = response.headers.get("content-type", "")
            assert (
                "application/json" in content_type.lower()
            ), f"Response should have JSON content-type, got {content_type}"

    def test_get_market_data_authentication_contract(
        self, client: TestClient, valid_symbol: str
    ) -> None:
        """
        Test market data retrieval authentication requirements.

        Contract Requirements:
        - May require authentication (Bearer token)
        - Should handle missing authentication appropriately
        """
        # Act - Request without authentication
        response = client.get(f"/api/v1/market-data/{valid_symbol}")

        # Assert - Should either succeed (if no auth required) or return 401
        acceptable_codes = [200, 401]
        assert (
            response.status_code in acceptable_codes
        ), f"Expected {acceptable_codes}, got {response.status_code}"

        # If 401, should have appropriate error response
        if response.status_code == 401:
            response_json = response.json()
            possible_error_fields = ["detail", "error", "message"]
            has_error_field = any(
                field in response_json for field in possible_error_fields
            )
            assert (
                has_error_field or len(response_json) == 0
            ), "401 response should contain error details or be empty"

    def _validate_market_data_response_structure(
        self, market_data: dict, expected_symbol: str
    ) -> None:
        """
        Helper method to validate market data response structure.

        Validates against the market data response schema from API specification.
        """
        # Required fields based on API specification
        required_fields = ["symbol", "data"]

        for field in required_fields:
            assert field in market_data, f"Market data must contain '{field}'"

        # Validate symbol
        symbol = market_data["symbol"]
        assert isinstance(symbol, str), "symbol must be string"
        assert len(symbol) > 0, "symbol cannot be empty"
        # Symbol should match requested (case might be normalized)
        assert symbol.upper() == expected_symbol.upper(), (
            f"Response symbol should match requested: "
            f"expected {expected_symbol}, got {symbol}"
        )

        # Validate data array
        data = market_data["data"]
        assert isinstance(data, list), "data must be a list"

        # If data is not empty, validate OHLCV structure
        for ohlcv in data:
            self._validate_ohlcv_structure(ohlcv)

        # Optional fields validation
        if "timeframe" in market_data:
            timeframe = market_data["timeframe"]
            assert isinstance(timeframe, str), "timeframe must be string"
            valid_timeframes = ["1min", "5min", "15min", "1hour", "1day"]
            assert (
                timeframe in valid_timeframes
            ), f"timeframe must be one of {valid_timeframes}, got {timeframe}"

    def _validate_ohlcv_structure(self, ohlcv: dict) -> None:
        """
        Helper method to validate OHLCV data structure.

        Validates against the OHLCV schema from API specification.
        """
        # Required fields for OHLCV schema
        required_fields = ["timestamp", "open", "high", "low", "close", "volume"]

        for field in required_fields:
            assert field in ohlcv, f"OHLCV must contain '{field}'"

        # Validate timestamp
        timestamp = ohlcv["timestamp"]
        assert isinstance(timestamp, str), "timestamp must be string"

        # Validate price fields
        price_fields = ["open", "high", "low", "close"]
        for field in price_fields:
            value = ohlcv[field]
            assert isinstance(value, (int, float)), f"{field} must be number"
            assert value > 0, f"{field} must be positive"

        # Validate volume
        volume = ohlcv["volume"]
        assert isinstance(volume, int), "volume must be integer"
        assert volume >= 0, "volume cannot be negative"

        # Validate price logic
        high = ohlcv["high"]
        low = ohlcv["low"]
        open_price = ohlcv["open"]
        close_price = ohlcv["close"]

        assert high >= low, "high must be >= low"
        assert high >= open_price, "high must be >= open"
        assert high >= close_price, "high must be >= close"
        assert low <= open_price, "low must be <= open"
        assert low <= close_price, "low must be <= close"

        # Optional change_percent field
        if "change_percent" in ohlcv:
            change_percent = ohlcv["change_percent"]
            assert isinstance(
                change_percent, (int, float)
            ), "change_percent must be number"
