"""
Angel One SmartAPI Client
A comprehensive client for Angel One's SmartAPI with robust error handling and monitoring
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
import hashlib
import secrets

import httpx
import pyotp
from pydantic import BaseModel, Field

from ..utils.logger import get_logger, log_performance, LogContext


class AngelOneConfig(BaseModel):
    """Angel One API configuration"""

    base_url: str = Field(default="https://apiconnect.angelone.in")
    timeout: int = Field(default=30)
    max_retries: int = Field(default=3)
    retry_delay: float = Field(default=1.0)
    rate_limit_calls: int = Field(default=100)  # calls per minute
    rate_limit_window: int = Field(default=60)  # seconds

    # Required headers
    x_user_type: str = Field(default="USER")
    x_source_id: str = Field(default="WEB")
    content_type: str = Field(default="application/json")
    accept: str = Field(default="application/json")


class AuthTokens(BaseModel):
    """Angel One authentication tokens"""

    jwt_token: Optional[str] = None
    refresh_token: Optional[str] = None
    feed_token: Optional[str] = None
    client_code: Optional[str] = None
    expires_at: Optional[datetime] = None


class RateLimiter:
    """Rate limiting implementation"""

    def __init__(self, max_calls: int = 100, window: int = 60):
        self.max_calls = max_calls
        self.window = window
        self.calls: List[float] = []

    async def wait_if_needed(self) -> None:
        """Wait if rate limit is exceeded"""
        now = time.time()

        # Remove old calls outside the window
        self.calls = [
            call_time for call_time in self.calls if now - call_time < self.window
        ]

        if len(self.calls) >= self.max_calls:
            # Calculate wait time
            oldest_call = min(self.calls)
            wait_time = self.window - (now - oldest_call)
            if wait_time > 0:
                await asyncio.sleep(wait_time)
                # Remove the oldest call after waiting
                self.calls.remove(oldest_call)

        # Record this call
        self.calls.append(now)


class AngelOneError(Exception):
    """Base exception for Angel One API errors"""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        status_code: Optional[int] = None,
        response_data: Optional[Dict] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.response_data = response_data or {}


class AuthenticationError(AngelOneError):
    """Authentication related errors"""

    pass


class AuthorizationError(AngelOneError):
    """Authorization related errors"""

    pass


class RateLimitError(AngelOneError):
    """Rate limit exceeded errors"""

    pass


class ValidationError(AngelOneError):
    """Request validation errors"""

    pass


class NetworkError(AngelOneError):
    """Network related errors"""

    pass


class ServerError(AngelOneError):
    """Server side errors"""

    pass


class AngelOneClient:
    """
    Comprehensive Angel One SmartAPI Client

    Features:
    - Async HTTP operations with proper connection management
    - Automatic token refresh and session management
    - Comprehensive error handling with custom exceptions
    - Rate limiting to prevent API abuse
    - Request/response logging and monitoring
    - Retry logic with exponential backoff
    - Method implementations for all major API endpoints
    """

    def __init__(
        self,
        api_key: str,
        client_code: str,
        client_pin: str,
        totp_secret: Optional[str] = None,
        config: Optional[AngelOneConfig] = None,
    ):
        """
        Initialize Angel One client

        Args:
            api_key: API key from Angel One
            client_code: Client code (user ID)
            client_pin: Client PIN or password
            totp_secret: TOTP secret for 2FA (optional)
            config: Client configuration
        """
        self.api_key = api_key
        self.client_code = client_code
        self.client_pin = client_pin
        self.totp_secret = totp_secret

        self.config = config or AngelOneConfig()
        self.logger = get_logger("niraj.angel_one")

        # Authentication state
        self.tokens = AuthTokens()
        self.is_authenticated = False
        self.session_id = secrets.token_hex(16)

        # HTTP client
        self.client: Optional[httpx.AsyncClient] = None

        # Rate limiting
        self.rate_limiter = RateLimiter(
            max_calls=self.config.rate_limit_calls, window=self.config.rate_limit_window
        )

        # Device fingerprint for security
        self.device_id = self._generate_device_id()
        self.mac_address = self._generate_mac_address()

    def _generate_device_id(self) -> str:
        """Generate a unique device ID"""
        return hashlib.md5(f"{self.client_code}_{time.time()}".encode()).hexdigest()

    def _generate_mac_address(self) -> str:
        """Generate a MAC address for headers"""
        return "02:00:00:%02x:%02x:%02x" % (
            secrets.randbelow(256),
            secrets.randbelow(256),
            secrets.randbelow(256),
        )

    def _get_client_ips(self) -> Tuple[str, str]:
        """Get client IP addresses (mock implementation)"""
        # In production, these should be real IP addresses
        return "192.168.1.1", "203.0.113.1"

    def _generate_totp(self) -> str:
        """Generate TOTP code if secret is available"""
        if not self.totp_secret:
            raise AuthenticationError("TOTP secret not provided")

        totp = pyotp.TOTP(self.totp_secret)
        return totp.now()

    def _get_default_headers(self, include_auth: bool = False) -> Dict[str, str]:
        """Get default headers for API requests"""
        local_ip, public_ip = self._get_client_ips()

        headers = {
            "Content-Type": self.config.content_type,
            "Accept": self.config.accept,
            "X-UserType": self.config.x_user_type,
            "X-SourceID": self.config.x_source_id,
            "X-ClientLocalIP": local_ip,
            "X-ClientPublicIP": public_ip,
            "X-MACAddress": self.mac_address,
            "X-PrivateKey": self.api_key,
            "User-Agent": "NIRAJ-Trading-System/1.0",
        }

        if include_auth and self.tokens.jwt_token:
            headers["Authorization"] = f"Bearer {self.tokens.jwt_token}"

        return headers

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self.client is None or self.client.is_closed:
            timeout = httpx.Timeout(self.config.timeout)
            limits = httpx.Limits(max_keepalive_connections=20, max_connections=100)

            self.client = httpx.AsyncClient(
                timeout=timeout, limits=limits, http2=True, follow_redirects=True
            )

        return self.client

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        include_auth: bool = True,
        retries: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Make HTTP request with error handling and retries

        Args:
            method: HTTP method
            endpoint: API endpoint
            data: Request body data
            params: Query parameters
            include_auth: Whether to include authentication headers
            retries: Number of retries (defaults to config value)

        Returns:
            Response data as dictionary

        Raises:
            Various AngelOneError subclasses based on error type
        """
        if retries is None:
            retries = self.config.max_retries

        # Check rate limit
        await self.rate_limiter.wait_if_needed()

        url = f"{self.config.base_url}{endpoint}"
        headers = self._get_default_headers(include_auth=include_auth)

        client = await self._get_client()

        # Log request details
        with LogContext(
            session_id=self.session_id,
            client_code=self.client_code,
            method=method,
            endpoint=endpoint,
            request_id=secrets.token_hex(8),
        ):
            self.logger.debug(f"Making {method} request to {endpoint}")

            for attempt in range(retries + 1):
                try:
                    # Make request
                    if method.upper() == "GET":
                        response = await client.get(url, headers=headers, params=params)
                    elif method.upper() == "POST":
                        response = await client.post(
                            url, headers=headers, json=data, params=params
                        )
                    elif method.upper() == "PUT":
                        response = await client.put(
                            url, headers=headers, json=data, params=params
                        )
                    elif method.upper() == "DELETE":
                        response = await client.delete(
                            url, headers=headers, params=params
                        )
                    else:
                        raise ValidationError(f"Unsupported HTTP method: {method}")

                    # Parse response
                    try:
                        response_data = response.json()
                    except (json.JSONDecodeError, ValueError) as e:
                        self.logger.error(f"Failed to parse JSON response: {e}")
                        raise ServerError(
                            f"Invalid JSON response: {response.text[:200]}"
                        )

                    # Log response
                    self.logger.debug(f"Response status: {response.status_code}")

                    # Handle different response codes
                    if response.status_code == 200:
                        if response_data.get("status"):
                            self.logger.debug("Request successful")
                            return response_data
                        else:
                            # API returned error in success response
                            error_code = response_data.get("errorcode", "UNKNOWN")
                            error_message = response_data.get(
                                "message", "Unknown error"
                            )

                            self.logger.error(
                                f"API error: {error_code} - {error_message}"
                            )

                            # Map specific error codes to exceptions
                            if error_code in ["AG8001", "AG8002", "AG8003"]:
                                raise AuthenticationError(
                                    error_message,
                                    error_code,
                                    response.status_code,
                                    response_data,
                                )
                            elif error_code in ["AG8004", "AG8005"]:
                                raise AuthorizationError(
                                    error_message,
                                    error_code,
                                    response.status_code,
                                    response_data,
                                )
                            elif error_code == "AG8006":
                                raise ValidationError(
                                    error_message,
                                    error_code,
                                    response.status_code,
                                    response_data,
                                )
                            else:
                                raise AngelOneError(
                                    error_message,
                                    error_code,
                                    response.status_code,
                                    response_data,
                                )

                    elif response.status_code == 401:
                        raise AuthenticationError(
                            "Authentication failed",
                            status_code=response.status_code,
                            response_data=response_data,
                        )

                    elif response.status_code == 403:
                        raise AuthorizationError(
                            "Authorization failed",
                            status_code=response.status_code,
                            response_data=response_data,
                        )

                    elif response.status_code == 429:
                        raise RateLimitError(
                            "Rate limit exceeded",
                            status_code=response.status_code,
                            response_data=response_data,
                        )

                    elif response.status_code >= 500:
                        if attempt < retries:
                            wait_time = self.config.retry_delay * (2**attempt)
                            self.logger.warning(
                                f"Server error {response.status_code}, retrying in {wait_time}s"
                            )
                            await asyncio.sleep(wait_time)
                            continue
                        raise ServerError(
                            f"Server error: {response.status_code}",
                            status_code=response.status_code,
                            response_data=response_data,
                        )

                    else:
                        raise AngelOneError(
                            f"HTTP {response.status_code}: {response.text[:200]}",
                            status_code=response.status_code,
                        )

                except httpx.TimeoutException:
                    if attempt < retries:
                        wait_time = self.config.retry_delay * (2**attempt)
                        self.logger.warning(
                            f"Request timeout, retrying in {wait_time}s"
                        )
                        await asyncio.sleep(wait_time)
                        continue
                    raise NetworkError("Request timeout")

                except httpx.NetworkError as e:
                    if attempt < retries:
                        wait_time = self.config.retry_delay * (2**attempt)
                        self.logger.warning(
                            f"Network error: {e}, retrying in {wait_time}s"
                        )
                        await asyncio.sleep(wait_time)
                        continue
                    raise NetworkError(f"Network error: {e}")

            # Should not reach here
            raise AngelOneError("All retry attempts failed")

    def _is_token_expired(self) -> bool:
        """Check if current token is expired"""
        if not self.tokens.expires_at:
            return True

        # Add 5 minute buffer before actual expiry
        return datetime.now() >= (self.tokens.expires_at - timedelta(minutes=5))

    @log_performance("angel_one_login")
    async def login(self, totp_code: Optional[str] = None) -> Dict[str, Any]:
        """
        Authenticate with Angel One API

        Args:
            totp_code: TOTP code (if not provided, will try to generate from secret)

        Returns:
            Login response data

        Raises:
            AuthenticationError: If login fails
        """
        self.logger.info("Attempting Angel One login")

        # Generate TOTP if not provided
        if not totp_code:
            if self.totp_secret:
                totp_code = self._generate_totp()
                self.logger.debug("Generated TOTP from secret")
            else:
                raise AuthenticationError(
                    "TOTP code required but not provided and no secret configured"
                )

        login_data = {
            "clientcode": self.client_code,
            "password": self.client_pin,
            "totp": totp_code,
        }

        try:
            response = await self._make_request(
                "POST",
                "/rest/auth/angelbroking/user/v1/loginByPassword",
                data=login_data,
                include_auth=False,
            )

            # Extract tokens
            data = response.get("data", {})
            self.tokens.jwt_token = data.get("jwtToken")
            self.tokens.refresh_token = data.get("refreshToken")
            self.tokens.feed_token = data.get("feedToken")
            self.tokens.client_code = self.client_code

            # Set expiry (tokens are valid for 28 hours)
            self.tokens.expires_at = datetime.now() + timedelta(hours=28)

            self.is_authenticated = True

            self.logger.info("Successfully authenticated with Angel One")

            return response

        except Exception as e:
            self.logger.error(f"Login failed: {e}")
            self.is_authenticated = False
            raise

    @log_performance("angel_one_refresh_token")
    async def refresh_token(self) -> Dict[str, Any]:
        """
        Refresh JWT token using refresh token

        Returns:
            Token refresh response data

        Raises:
            AuthenticationError: If token refresh fails
        """
        if not self.tokens.refresh_token:
            raise AuthenticationError("No refresh token available")

        self.logger.info("Refreshing Angel One token")

        refresh_data = {"refreshToken": self.tokens.refresh_token}

        try:
            response = await self._make_request(
                "POST",
                "/rest/auth/angelbroking/jwt/v1/generateTokens",
                data=refresh_data,
                include_auth=True,
            )

            # Update tokens
            data = response.get("data", {})
            self.tokens.jwt_token = data.get("jwtToken")
            self.tokens.refresh_token = data.get("refreshToken")
            self.tokens.feed_token = data.get("feedToken")

            # Update expiry
            self.tokens.expires_at = datetime.now() + timedelta(hours=28)

            self.logger.info("Successfully refreshed Angel One token")

            return response

        except Exception as e:
            self.logger.error(f"Token refresh failed: {e}")
            self.is_authenticated = False
            raise

    async def _ensure_authenticated(self) -> None:
        """Ensure we have a valid authentication token"""
        if not self.is_authenticated or self._is_token_expired():
            if self.tokens.refresh_token and not self._is_token_expired():
                await self.refresh_token()
            else:
                await self.login()

    @log_performance("angel_one_logout")
    async def logout(self) -> Dict[str, Any]:
        """
        Logout and invalidate session

        Returns:
            Logout response data
        """
        if not self.is_authenticated:
            self.logger.warning("Already logged out")
            return {"status": True, "message": "Already logged out"}

        self.logger.info("Logging out from Angel One")

        logout_data = {"clientcode": self.client_code}

        try:
            response = await self._make_request(
                "POST",
                "/rest/secure/angelbroking/user/v1/logout",
                data=logout_data,
                include_auth=True,
            )

            # Clear tokens
            self.tokens = AuthTokens()
            self.is_authenticated = False

            self.logger.info("Successfully logged out from Angel One")

            return response

        except Exception as e:
            self.logger.error(f"Logout failed: {e}")
            # Clear tokens anyway
            self.tokens = AuthTokens()
            self.is_authenticated = False
            raise

    async def close(self) -> None:
        """Close HTTP client and cleanup resources"""
        if self.client and not self.client.is_closed:
            await self.client.aclose()

        self.logger.info("Angel One client closed")

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    def __del__(self):
        """Destructor - ensure cleanup"""
        try:
            if self.client and not self.client.is_closed:
                # Can't use await in __del__, so just close synchronously
                import warnings

                warnings.warn(
                    "Angel One client was not properly closed. Use async context manager or call close() explicitly."
                )
        except Exception:
            pass

    # Continued in next part due to length...

    # Additional API Methods Implementation

    # Profile and User Methods

    @log_performance("angel_one_get_profile")
    async def get_profile(self) -> Dict[str, Any]:
        """
        Get user profile information

        Returns:
            User profile data
        """
        await self._ensure_authenticated()

        response = await self._make_request(
            "GET", "/rest/secure/angelbroking/user/v1/getProfile", include_auth=True
        )

        self.logger.debug("Retrieved user profile")
        return response

    @log_performance("angel_one_get_rms")
    async def get_rms_limits(self) -> Dict[str, Any]:
        """
        Get Risk Management System (RMS) limits

        Returns:
            RMS limits and margin information
        """
        await self._ensure_authenticated()

        response = await self._make_request(
            "GET", "/rest/secure/angelbroking/user/v1/getRMS", include_auth=True
        )

        self.logger.debug("Retrieved RMS limits")
        return response

    # Market Data Methods
    @log_performance("angel_one_get_ltp")
    async def get_ltp_data(
        self, exchange: str, tradingsymbol: str, symboltoken: str
    ) -> Dict[str, Any]:
        """
        Get Last Traded Price (LTP) data

        Args:
            exchange: Exchange name (NSE, BSE, NFO, etc.)
            tradingsymbol: Trading symbol
            symboltoken: Symbol token

        Returns:
            LTP data
        """
        await self._ensure_authenticated()

        data = {
            "exchange": exchange,
            "tradingsymbol": tradingsymbol,
            "symboltoken": symboltoken,
        }

        response = await self._make_request(
            "POST",
            "/rest/secure/angelbroking/order/v1/getLTPData",
            data=data,
            include_auth=True,
        )

        self.logger.debug(f"Retrieved LTP for {tradingsymbol}")
        return response

    @log_performance("angel_one_get_quotes")
    async def get_quotes(
        self, exchange: str, tradingsymbol: str, symboltoken: str
    ) -> Dict[str, Any]:
        """
        Get detailed quote data for a symbol

        Args:
            exchange: Exchange name
            tradingsymbol: Trading symbol
            symboltoken: Symbol token

        Returns:
            Quote data with OHLC, volume, etc.
        """
        await self._ensure_authenticated()

        data = {
            "exchange": exchange,
            "tradingsymbol": tradingsymbol,
            "symboltoken": symboltoken,
        }

        response = await self._make_request(
            "POST",
            "/rest/secure/angelbroking/market/v1/getQuotes",
            data=data,
            include_auth=True,
        )

        self.logger.debug(f"Retrieved quotes for {tradingsymbol}")
        return response

    @log_performance("angel_one_get_historical_data")
    async def get_historical_data(
        self, exchange: str, symboltoken: str, interval: str, fromdate: str, todate: str
    ) -> Dict[str, Any]:
        """
        Get historical candle data

        Args:
            exchange: Exchange name
            symboltoken: Symbol token
            interval: Time interval (ONE_MINUTE, THREE_MINUTE, FIVE_MINUTE, etc.)
            fromdate: Start date (YYYY-MM-DD HH:MM format)
            todate: End date (YYYY-MM-DD HH:MM format)

        Returns:
            Historical OHLC data
        """
        await self._ensure_authenticated()

        data = {
            "exchange": exchange,
            "symboltoken": symboltoken,
            "interval": interval,
            "fromdate": fromdate,
            "todate": todate,
        }

        response = await self._make_request(
            "POST",
            "/rest/secure/angelbroking/historical/v1/getCandleData",
            data=data,
            include_auth=True,
        )

        self.logger.debug(f"Retrieved historical data for token {symboltoken}")
        return response

    # Trading Methods
    @log_performance("angel_one_place_order")
    async def place_order(
        self,
        variety: str,
        tradingsymbol: str,
        symboltoken: str,
        transactiontype: str,
        exchange: str,
        ordertype: str,
        producttype: str,
        duration: str,
        price: str,
        squareoff: str = "0",
        stoploss: str = "0",
        quantity: str = "1",
    ) -> Dict[str, Any]:
        """
        Place a trading order

        Args:
            variety: Order variety (NORMAL, STOPLOSS, AMO, etc.)
            tradingsymbol: Trading symbol
            symboltoken: Symbol token
            transactiontype: BUY or SELL
            exchange: Exchange name
            ordertype: MARKET, LIMIT, STOPLOSS_LIMIT, etc.
            producttype: DELIVERY, INTRADAY, MARGIN
            duration: DAY, IOC
            price: Order price
            squareoff: Square off value for bracket orders
            stoploss: Stop loss value
            quantity: Order quantity

        Returns:
            Order placement response with order ID
        """
        await self._ensure_authenticated()

        data = {
            "variety": variety,
            "tradingsymbol": tradingsymbol,
            "symboltoken": symboltoken,
            "transactiontype": transactiontype,
            "exchange": exchange,
            "ordertype": ordertype,
            "producttype": producttype,
            "duration": duration,
            "price": price,
            "squareoff": squareoff,
            "stoploss": stoploss,
            "quantity": quantity,
        }

        response = await self._make_request(
            "POST",
            "/rest/secure/angelbroking/order/v1/placeOrder",
            data=data,
            include_auth=True,
        )

        order_id = response.get("data", {}).get("orderid")
        self.logger.info(f"Placed order {order_id} for {quantity} {tradingsymbol}")
        return response

    @log_performance("angel_one_modify_order")
    async def modify_order(
        self,
        variety: str,
        orderid: str,
        ordertype: str,
        producttype: str,
        duration: str,
        price: str,
        quantity: str,
        tradingsymbol: str,
        symboltoken: str,
        exchange: str,
    ) -> Dict[str, Any]:
        """
        Modify an existing order

        Args:
            variety: Order variety
            orderid: Order ID to modify
            ordertype: New order type
            producttype: Product type
            duration: Duration
            price: New price
            quantity: New quantity
            tradingsymbol: Trading symbol
            symboltoken: Symbol token
            exchange: Exchange name

        Returns:
            Order modification response
        """
        await self._ensure_authenticated()

        data = {
            "variety": variety,
            "orderid": orderid,
            "ordertype": ordertype,
            "producttype": producttype,
            "duration": duration,
            "price": price,
            "quantity": quantity,
            "tradingsymbol": tradingsymbol,
            "symboltoken": symboltoken,
            "exchange": exchange,
        }

        response = await self._make_request(
            "POST",
            "/rest/secure/angelbroking/order/v1/modifyOrder",
            data=data,
            include_auth=True,
        )

        self.logger.info(f"Modified order {orderid}")
        return response

    @log_performance("angel_one_cancel_order")
    async def cancel_order(self, variety: str, orderid: str) -> Dict[str, Any]:
        """
        Cancel an existing order

        Args:
            variety: Order variety
            orderid: Order ID to cancel

        Returns:
            Order cancellation response
        """
        await self._ensure_authenticated()

        data = {"variety": variety, "orderid": orderid}

        response = await self._make_request(
            "POST",
            "/rest/secure/angelbroking/order/v1/cancelOrder",
            data=data,
            include_auth=True,
        )

        self.logger.info(f"Cancelled order {orderid}")
        return response

    @log_performance("angel_one_get_order_book")
    async def get_order_book(self) -> Dict[str, Any]:
        """
        Get order book (all orders for the day)

        Returns:
            Order book with all orders
        """
        await self._ensure_authenticated()

        response = await self._make_request(
            "GET", "/rest/secure/angelbroking/order/v1/getOrderBook", include_auth=True
        )

        self.logger.debug("Retrieved order book")
        return response

    @log_performance("angel_one_get_trade_book")
    async def get_trade_book(self) -> Dict[str, Any]:
        """
        Get trade book (all executed trades for the day)

        Returns:
            Trade book with all trades
        """
        await self._ensure_authenticated()

        response = await self._make_request(
            "GET", "/rest/secure/angelbroking/order/v1/getTradeBook", include_auth=True
        )

        self.logger.debug("Retrieved trade book")
        return response

    @log_performance("angel_one_get_order_status")
    async def get_order_status(self, orderid: str) -> Dict[str, Any]:
        """
        Get status of a specific order

        Args:
            orderid: Order ID to check

        Returns:
            Order status details
        """
        await self._ensure_authenticated()

        response = await self._make_request(
            "GET",
            f"/rest/secure/angelbroking/order/v1/details/{orderid}",
            include_auth=True,
        )

        self.logger.debug(f"Retrieved status for order {orderid}")
        return response

    # Portfolio Methods
    @log_performance("angel_one_get_holdings")
    async def get_holdings(self) -> Dict[str, Any]:
        """
        Get holdings (positions in delivery)

        Returns:
            Holdings data
        """
        await self._ensure_authenticated()

        response = await self._make_request(
            "GET",
            "/rest/secure/angelbroking/portfolio/v1/getHolding",
            include_auth=True,
        )

        self.logger.debug("Retrieved holdings")
        return response

    @log_performance("angel_one_get_all_holdings")
    async def get_all_holdings(self) -> Dict[str, Any]:
        """
        Get all holdings with detailed information

        Returns:
            Detailed holdings data
        """
        await self._ensure_authenticated()

        response = await self._make_request(
            "GET",
            "/rest/secure/angelbroking/portfolio/v1/getAllHolding",
            include_auth=True,
        )

        self.logger.debug("Retrieved all holdings")
        return response

    @log_performance("angel_one_get_positions")
    async def get_positions(self) -> Dict[str, Any]:
        """
        Get positions (intraday and carry forward positions)

        Returns:
            Positions data
        """
        await self._ensure_authenticated()

        response = await self._make_request(
            "GET", "/rest/secure/angelbroking/order/v1/getPosition", include_auth=True
        )

        self.logger.debug("Retrieved positions")
        return response

    @log_performance("angel_one_convert_position")
    async def convert_position(
        self,
        exchange: str,
        oldproducttype: str,
        newproducttype: str,
        tradingsymbol: str,
        transactiontype: str,
        quantity: str,
        type: str,
    ) -> Dict[str, Any]:
        """
        Convert position from one product type to another

        Args:
            exchange: Exchange name
            oldproducttype: Current product type
            newproducttype: New product type
            tradingsymbol: Trading symbol
            transactiontype: BUY or SELL
            quantity: Quantity to convert
            type: Position type

        Returns:
            Position conversion response
        """
        await self._ensure_authenticated()

        data = {
            "exchange": exchange,
            "oldproducttype": oldproducttype,
            "newproducttype": newproducttype,
            "tradingsymbol": tradingsymbol,
            "transactiontype": transactiontype,
            "quantity": quantity,
            "type": type,
        }

        response = await self._make_request(
            "POST",
            "/rest/secure/angelbroking/portfolio/v1/convertPosition",
            data=data,
            include_auth=True,
        )

        self.logger.info(f"Converted position for {tradingsymbol}")
        return response

    # GTT (Good Till Trigger) Methods
    @log_performance("angel_one_create_gtt_rule")
    async def create_gtt_rule(
        self,
        tradingsymbol: str,
        symboltoken: str,
        exchange: str,
        producttype: str,
        transactiontype: str,
        quantity: str,
        price: str,
        triggerprice: str,
        timeperiod: str,
    ) -> Dict[str, Any]:
        """
        Create GTT (Good Till Trigger) rule

        Args:
            tradingsymbol: Trading symbol
            symboltoken: Symbol token
            exchange: Exchange name
            producttype: Product type
            transactiontype: BUY or SELL
            quantity: Quantity
            price: Order price
            triggerprice: Trigger price
            timeperiod: Time period for rule

        Returns:
            GTT rule creation response
        """
        await self._ensure_authenticated()

        data = {
            "tradingsymbol": tradingsymbol,
            "symboltoken": symboltoken,
            "exchange": exchange,
            "producttype": producttype,
            "transactiontype": transactiontype,
            "quantity": quantity,
            "price": price,
            "triggerprice": triggerprice,
            "timeperiod": timeperiod,
        }

        response = await self._make_request(
            "POST",
            "/rest/secure/angelbroking/gtt/v1/createRule",
            data=data,
            include_auth=True,
        )

        rule_id = response.get("data", {}).get("id")
        self.logger.info(f"Created GTT rule {rule_id}")
        return response

    # Utility Methods
    async def get_instruments(
        self, exchange: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get instrument master (symbol information)

        Args:
            exchange: Specific exchange (optional)

        Returns:
            List of instruments
        """
        # This would typically be a CSV download, simplified for demo
        await self._ensure_authenticated()

        endpoint = "/rest/secure/angelbroking/master/v1/allInstruments"
        if exchange:
            endpoint += f"?exchange={exchange}"

        response = await self._make_request("GET", endpoint, include_auth=True)

        self.logger.debug(f"Retrieved instruments for exchange: {exchange or 'all'}")
        return response.get("data", [])

    async def search_scrips(self, search_text: str) -> Dict[str, Any]:
        """
        Search for trading symbols

        Args:
            search_text: Text to search for

        Returns:
            Search results
        """
        await self._ensure_authenticated()

        data = {"search": search_text}

        response = await self._make_request(
            "POST",
            "/rest/secure/angelbroking/order/v1/searchScrip",
            data=data,
            include_auth=True,
        )

        self.logger.debug(f"Searched for scrips: {search_text}")
        return response

    # Health Check
    async def health_check(self) -> Dict[str, Any]:
        """
        Check API health and connectivity

        Returns:
            Health status
        """
        try:
            if self.is_authenticated:
                # If authenticated, try to get profile as health check
                response = await self.get_profile()
                return {
                    "status": "healthy",
                    "authenticated": True,
                    "message": "API connection and authentication working",
                }
            else:
                # Just check basic connectivity without authentication
                client = await self._get_client()
                response = await client.get(f"{self.config.base_url}/docs")

                return {
                    "status": "healthy" if response.status_code == 200 else "degraded",
                    "authenticated": False,
                    "message": "Basic connectivity working",
                }

        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {"status": "unhealthy", "authenticated": False, "error": str(e)}

    # Statistics and monitoring
    def get_client_stats(self) -> Dict[str, Any]:
        """
        Get client statistics for monitoring

        Returns:
            Client statistics
        """
        return {
            "session_id": self.session_id,
            "client_code": self.client_code,
            "is_authenticated": self.is_authenticated,
            "token_expires_at": (
                self.tokens.expires_at.isoformat() if self.tokens.expires_at else None
            ),
            "api_calls_in_window": len(self.rate_limiter.calls),
            "rate_limit_max": self.config.rate_limit_calls,
            "rate_limit_window": self.config.rate_limit_window,
            "device_id": self.device_id,
        }
