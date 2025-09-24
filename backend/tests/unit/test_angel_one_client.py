"""
Test file for Angel One SmartAPI Client
Comprehensive tests for all functionality with mocking
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
import json

import httpx

from src.api.angel_one_client import (
    AngelOneClient,
    AngelOneConfig,
    AuthTokens,
    AngelOneError,
    AuthenticationError,
    AuthorizationError,
    RateLimitError,
    ValidationError,
    NetworkError,
    ServerError,
    RateLimiter
)


class TestAngelOneConfig:
    """Test configuration model"""

    def test_default_config(self):
        config = AngelOneConfig()
        assert config.base_url == "https://apiconnect.angelone.in"
        assert config.timeout == 30
        assert config.max_retries == 3
        assert config.rate_limit_calls == 100

    def test_custom_config(self):
        config = AngelOneConfig(
            base_url="https://test.api.com",
            timeout=60,
            max_retries=5
        )
        assert config.base_url == "https://test.api.com"
        assert config.timeout == 60
        assert config.max_retries == 5


class TestAuthTokens:
    """Test authentication tokens model"""

    def test_empty_tokens(self):
        tokens = AuthTokens()
        assert tokens.jwt_token is None
        assert tokens.refresh_token is None
        assert tokens.feed_token is None

    def test_tokens_with_data(self):
        tokens = AuthTokens(
            jwt_token="test_jwt",
            refresh_token="test_refresh",
            client_code="TEST123"
        )
        assert tokens.jwt_token == "test_jwt"
        assert tokens.refresh_token == "test_refresh"
        assert tokens.client_code == "TEST123"


class TestRateLimiter:
    """Test rate limiting functionality"""

    @pytest.mark.asyncio
    async def test_rate_limiter_allows_calls(self):
        limiter = RateLimiter(max_calls=5, window=60)

        # Should allow initial calls
        for _ in range(5):
            await limiter.wait_if_needed()

        # Check that calls were recorded
        assert len(limiter.calls) == 5

    @pytest.mark.asyncio
    async def test_rate_limiter_blocks_excess_calls(self):
        limiter = RateLimiter(max_calls=2, window=1)

        # Make maximum allowed calls
        await limiter.wait_if_needed()
        await limiter.wait_if_needed()

        # Next call should be delayed
        import time
        start_time = time.time()
        await limiter.wait_if_needed()
        end_time = time.time()

        # Should have waited
        assert end_time - start_time > 0.5


class TestAngelOneClient:
    """Test Angel One client functionality"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return AngelOneClient(
            api_key="test_api_key",
            client_code="TEST123",
            client_pin="1234",
            totp_secret="TESTSECRET123456"
        )

    @pytest.fixture
    def mock_http_client(self):
        """Mock HTTP client"""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        return mock_client

    def test_client_initialization(self, client):
        """Test client initialization"""
        assert client.api_key == "test_api_key"
        assert client.client_code == "TEST123"
        assert client.client_pin == "1234"
        assert client.totp_secret == "TESTSECRET123456"
        assert not client.is_authenticated
        assert isinstance(client.config, AngelOneConfig)

    def test_generate_device_id(self, client):
        """Test device ID generation"""
        device_id = client._generate_device_id()
        assert isinstance(device_id, str)
        assert len(device_id) == 32  # MD5 hash length

    def test_generate_mac_address(self, client):
        """Test MAC address generation"""
        mac_address = client._generate_mac_address()
        assert isinstance(mac_address, str)
        assert mac_address.startswith("02:00:00:")
        assert len(mac_address.split(":")) == 6

    @patch('pyotp.TOTP')
    def test_generate_totp(self, mock_totp_class, client):
        """Test TOTP generation"""
        mock_totp = MagicMock()
        mock_totp.now.return_value = "123456"
        mock_totp_class.return_value = mock_totp

        totp_code = client._generate_totp()
        assert totp_code == "123456"
        mock_totp_class.assert_called_once_with(client.totp_secret)

    def test_generate_totp_no_secret(self):
        """Test TOTP generation without secret"""
        client = AngelOneClient(
            api_key="test",
            client_code="test",
            client_pin="test"
        )

        with pytest.raises(AuthenticationError):
            client._generate_totp()

    def test_get_default_headers(self, client):
        """Test default headers generation"""
        headers = client._get_default_headers(include_auth=False)

        assert headers['Content-Type'] == 'application/json'
        assert headers['Accept'] == 'application/json'
        assert headers['X-UserType'] == 'USER'
        assert headers['X-SourceID'] == 'WEB'
        assert headers['X-PrivateKey'] == 'test_api_key'
        assert headers['User-Agent'] == 'NIRAJ-Trading-System/1.0'
        assert 'Authorization' not in headers

    def test_get_default_headers_with_auth(self, client):
        """Test headers with authentication"""
        client.tokens.jwt_token = "test_jwt_token"
        headers = client._get_default_headers(include_auth=True)

        assert headers['Authorization'] == 'Bearer test_jwt_token'

    def test_is_token_expired_no_token(self, client):
        """Test token expiry check without token"""
        assert client._is_token_expired() is True

    def test_is_token_expired_valid_token(self, client):
        """Test token expiry check with valid token"""
        client.tokens.expires_at = datetime.now() + timedelta(hours=1)
        assert client._is_token_expired() is False

    def test_is_token_expired_expired_token(self, client):
        """Test token expiry check with expired token"""
        client.tokens.expires_at = datetime.now() - timedelta(hours=1)
        assert client._is_token_expired() is True

    @pytest.mark.asyncio
    async def test_make_request_success(self, client, mock_http_client):
        """Test successful API request"""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": True,
            "message": "SUCCESS",
            "data": {"test": "data"}
        }
        mock_http_client.post = AsyncMock(return_value=mock_response)

        with patch.object(client, '_get_client', return_value=mock_http_client):
            result = await client._make_request("POST", "/test", data={"key": "value"})

        assert result["status"] is True
        assert result["data"]["test"] == "data"

    @pytest.mark.asyncio
    async def test_make_request_api_error(self, client, mock_http_client):
        """Test API error response"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": False,
            "message": "Invalid request",
            "errorcode": "AG8006"
        }
        mock_http_client.post = AsyncMock(return_value=mock_response)

        with patch.object(client, '_get_client', return_value=mock_http_client):
            with pytest.raises(ValidationError):
                await client._make_request("POST", "/test", data={"key": "value"})

    @pytest.mark.asyncio
    async def test_make_request_http_401(self, client, mock_http_client):
        """Test HTTP 401 response"""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": "Unauthorized"}
        mock_http_client.post = AsyncMock(return_value=mock_response)

        with patch.object(client, '_get_client', return_value=mock_http_client):
            with pytest.raises(AuthenticationError):
                await client._make_request("POST", "/test")

    @pytest.mark.asyncio
    async def test_make_request_http_403(self, client, mock_http_client):
        """Test HTTP 403 response"""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.json.return_value = {"error": "Forbidden"}
        mock_http_client.post = AsyncMock(return_value=mock_response)

        with patch.object(client, '_get_client', return_value=mock_http_client):
            with pytest.raises(AuthorizationError):
                await client._make_request("POST", "/test")

    @pytest.mark.asyncio
    async def test_make_request_http_429(self, client, mock_http_client):
        """Test HTTP 429 (Rate Limit) response"""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.json.return_value = {"error": "Too many requests"}
        mock_http_client.post = AsyncMock(return_value=mock_response)

        with patch.object(client, '_get_client', return_value=mock_http_client):
            with pytest.raises(RateLimitError):
                await client._make_request("POST", "/test")

    @pytest.mark.asyncio
    async def test_make_request_http_500_with_retry(self, client, mock_http_client):
        """Test HTTP 500 with retry logic"""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": "Internal server error"}
        mock_http_client.post = AsyncMock(return_value=mock_response)

        with patch.object(client, '_get_client', return_value=mock_http_client):
            with pytest.raises(ServerError):
                await client._make_request("POST", "/test", retries=1)

        # Should have made 2 attempts (initial + 1 retry)
        assert mock_http_client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_make_request_network_error(self, client, mock_http_client):
        """Test network error handling"""
        mock_http_client.post = AsyncMock(side_effect=httpx.NetworkError("Connection failed"))

        with patch.object(client, '_get_client', return_value=mock_http_client):
            with pytest.raises(NetworkError):
                await client._make_request("POST", "/test", retries=1)

    @pytest.mark.asyncio
    async def test_make_request_timeout_error(self, client, mock_http_client):
        """Test timeout error handling"""
        mock_http_client.post = AsyncMock(side_effect=httpx.TimeoutException("Request timeout"))

        with patch.object(client, '_get_client', return_value=mock_http_client):
            with pytest.raises(NetworkError):
                await client._make_request("POST", "/test", retries=1)

    @pytest.mark.asyncio
    async def test_login_success(self, client):
        """Test successful login"""
        mock_response = {
            "status": True,
            "message": "SUCCESS",
            "data": {
                "jwtToken": "test_jwt_token",
                "refreshToken": "test_refresh_token",
                "feedToken": "test_feed_token"
            }
        }

        with patch.object(client, '_make_request', return_value=mock_response) as mock_request:
            with patch.object(client, '_generate_totp', return_value="123456"):
                result = await client.login()

        assert client.is_authenticated is True
        assert client.tokens.jwt_token == "test_jwt_token"
        assert client.tokens.refresh_token == "test_refresh_token"
        assert client.tokens.feed_token == "test_feed_token"
        assert result == mock_response

        # Verify request was made with correct parameters
        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        assert args[0] == "POST"
        assert args[1] == "/rest/auth/angelbroking/user/v1/loginByPassword"
        assert kwargs["data"]["clientcode"] == "TEST123"
        assert kwargs["data"]["totp"] == "123456"

    @pytest.mark.asyncio
    async def test_login_with_totp_code(self, client):
        """Test login with provided TOTP code"""
        mock_response = {
            "status": True,
            "message": "SUCCESS",
            "data": {
                "jwtToken": "test_jwt",
                "refreshToken": "test_refresh",
                "feedToken": "test_feed"
            }
        }

        with patch.object(client, '_make_request', return_value=mock_response):
            await client.login(totp_code="654321")

        assert client.is_authenticated is True

    @pytest.mark.asyncio
    async def test_refresh_token_success(self, client):
        """Test successful token refresh"""
        client.tokens.refresh_token = "old_refresh_token"

        mock_response = {
            "status": True,
            "message": "SUCCESS",
            "data": {
                "jwtToken": "new_jwt_token",
                "refreshToken": "new_refresh_token",
                "feedToken": "new_feed_token"
            }
        }

        with patch.object(client, '_make_request', return_value=mock_response):
            result = await client.refresh_token()

        assert client.tokens.jwt_token == "new_jwt_token"
        assert client.tokens.refresh_token == "new_refresh_token"
        assert client.tokens.feed_token == "new_feed_token"
        assert result == mock_response

    @pytest.mark.asyncio
    async def test_refresh_token_no_refresh_token(self, client):
        """Test token refresh without refresh token"""
        with pytest.raises(AuthenticationError):
            await client.refresh_token()

    @pytest.mark.asyncio
    async def test_logout_success(self, client):
        """Test successful logout"""
        client.is_authenticated = True
        client.tokens.jwt_token = "test_token"

        mock_response = {
            "status": True,
            "message": "SUCCESS",
            "data": ""
        }

        with patch.object(client, '_make_request', return_value=mock_response):
            result = await client.logout()

        assert client.is_authenticated is False
        assert client.tokens.jwt_token is None
        assert result == mock_response

    @pytest.mark.asyncio
    async def test_logout_not_authenticated(self, client):
        """Test logout when not authenticated"""
        result = await client.logout()

        assert result["status"] is True
        assert "already logged out" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_ensure_authenticated_valid_token(self, client):
        """Test ensure authenticated with valid token"""
        client.is_authenticated = True
        client.tokens.expires_at = datetime.now() + timedelta(hours=1)

        await client._ensure_authenticated()

        # Should not trigger login or refresh
        assert client.is_authenticated is True

    @pytest.mark.asyncio
    async def test_ensure_authenticated_expired_token(self, client):
        """Test ensure authenticated with expired token"""
        client.is_authenticated = True
        client.tokens.expires_at = datetime.now() - timedelta(hours=1)
        client.tokens.refresh_token = "test_refresh"

        with patch.object(client, 'refresh_token') as mock_refresh:
            await client._ensure_authenticated()
            mock_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_ensure_authenticated_no_token(self, client):
        """Test ensure authenticated without any token"""
        with patch.object(client, 'login') as mock_login:
            await client._ensure_authenticated()
            mock_login.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_profile(self, client):
        """Test get profile endpoint"""
        mock_response = {
            "status": True,
            "data": {
                "clientcode": "TEST123",
                "name": "Test User",
                "email": "test@example.com"
            }
        }

        with patch.object(client, '_ensure_authenticated'):
            with patch.object(client, '_make_request', return_value=mock_response):
                result = await client.get_profile()

        assert result == mock_response

    @pytest.mark.asyncio
    async def test_place_order(self, client):
        """Test place order endpoint"""
        mock_response = {
            "status": True,
            "data": {
                "orderid": "123456789"
            }
        }

        with patch.object(client, '_ensure_authenticated'):
            with patch.object(client, '_make_request', return_value=mock_response) as mock_request:
                result = await client.place_order(
                    variety="NORMAL",
                    tradingsymbol="RELIANCE",
                    symboltoken="2885",
                    transactiontype="BUY",
                    exchange="NSE",
                    ordertype="MARKET",
                    producttype="INTRADAY",
                    duration="DAY",
                    price="0",
                    quantity="1"
                )

        assert result == mock_response

        # Verify request parameters
        args, kwargs = mock_request.call_args
        assert kwargs["data"]["tradingsymbol"] == "RELIANCE"
        assert kwargs["data"]["transactiontype"] == "BUY"
        assert kwargs["data"]["quantity"] == "1"

    @pytest.mark.asyncio
    async def test_get_historical_data(self, client):
        """Test get historical data endpoint"""
        mock_response = {
            "status": True,
            "data": [
                ["2023-01-01T09:15:00+05:30", 100.0, 105.0, 95.0, 102.0, 1000]
            ]
        }

        with patch.object(client, '_ensure_authenticated'):
            with patch.object(client, '_make_request', return_value=mock_response):
                result = await client.get_historical_data(
                    exchange="NSE",
                    symboltoken="2885",
                    interval="ONE_MINUTE",
                    fromdate="2023-01-01 09:15",
                    todate="2023-01-01 15:30"
                )

        assert result == mock_response

    @pytest.mark.asyncio
    async def test_health_check_authenticated(self, client):
        """Test health check when authenticated"""
        client.is_authenticated = True

        with patch.object(client, 'get_profile', return_value={"status": True}):
            result = await client.health_check()

        assert result["status"] == "healthy"
        assert result["authenticated"] is True

    @pytest.mark.asyncio
    async def test_health_check_not_authenticated(self, client):
        """Test health check when not authenticated"""
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch.object(client, '_get_client') as mock_get_client:
            mock_http_client = AsyncMock()
            mock_http_client.get = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_http_client

            result = await client.health_check()

        assert result["status"] == "healthy"
        assert result["authenticated"] is False

    @pytest.mark.asyncio
    async def test_health_check_error(self, client):
        """Test health check with error"""
        client.is_authenticated = True

        with patch.object(client, 'get_profile', side_effect=Exception("Test error")):
            result = await client.health_check()

        assert result["status"] == "unhealthy"
        assert "Test error" in result["error"]

    def test_get_client_stats(self, client):
        """Test client statistics"""
        client.is_authenticated = True
        client.tokens.expires_at = datetime.now()

        stats = client.get_client_stats()

        assert "session_id" in stats
        assert stats["client_code"] == "TEST123"
        assert stats["is_authenticated"] is True
        assert "token_expires_at" in stats
        assert "api_calls_in_window" in stats

    @pytest.mark.asyncio
    async def test_context_manager(self, client):
        """Test async context manager"""
        async with client as ctx_client:
            assert ctx_client == client

        # Client should be closed after context
        # Note: In real usage, the HTTP client would be closed


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
