"""
Dhan HQ API Client
A comprehensive client for Dhan HQ API with robust error handling and monitoring
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import hashlib
import secrets
import logging

import httpx
from pydantic import BaseModel, Field

# Handle imports for both package and standalone usage
try:
    from ..utils.logger import get_logger, log_performance, LogContext  # type: ignore[assignment]
except ImportError:
    # Fallback for standalone usage
    def get_logger(name: str) -> logging.Logger:
        """Simple logger fallback"""
        logger = logging.getLogger(name)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        return logger

    def log_performance(func_name: Optional[str] = None):
        """Simple performance logging decorator fallback"""

        def decorator(func):
            return func

        return decorator

    class LogContext:
        """Simple context manager fallback"""

        def __init__(self, **kwargs: Any) -> None:
            pass

        def __enter__(self) -> "LogContext":
            return self

        def __exit__(self, *args: Any) -> None:
            pass


class DhanConfig(BaseModel):
    """Dhan API configuration"""

    base_url: str = Field(default="https://api.dhan.co")
    timeout: int = Field(default=30)
    max_retries: int = Field(default=3)
    retry_delay: float = Field(default=1.0)

    # Rate limits based on Dhan documentation
    rate_limit_per_second: int = Field(default=25)
    rate_limit_per_minute: int = Field(default=250)
    rate_limit_per_hour: int = Field(default=1000)
    rate_limit_per_day: int = Field(default=7000)

    # Required headers
    content_type: str = Field(default="application/json")
    accept: str = Field(default="application/json")


class AuthTokens(BaseModel):
    """Dhan authentication tokens"""

    access_token: Optional[str] = None
    client_id: Optional[str] = None
    user_id: Optional[str] = None
    expires_at: Optional[datetime] = None
    token_type: str = Field(default="Bearer")


class RateLimiter:
    """Multi-level rate limiting implementation for Dhan API"""

    def __init__(
        self,
        per_second: int = 25,
        per_minute: int = 250,
        per_hour: int = 1000,
        per_day: int = 7000,
    ):
        self.per_second = per_second
        self.per_minute = per_minute
        self.per_hour = per_hour
        self.per_day = per_day

        # Track calls at different time windows
        self.calls_per_second: List[float] = []
        self.calls_per_minute: List[float] = []
        self.calls_per_hour: List[float] = []
        self.calls_per_day: List[float] = []

    def _clean_old_calls(self, call_list: List[float], window_seconds: int) -> None:
        """Remove calls outside the time window"""
        now = time.time()
        while call_list and now - call_list[0] >= window_seconds:
            call_list.pop(0)

    async def wait_if_needed(self) -> None:
        """Wait if any rate limit is exceeded"""
        now = time.time()

        # Clean old calls
        self._clean_old_calls(self.calls_per_second, 1)
        self._clean_old_calls(self.calls_per_minute, 60)
        self._clean_old_calls(self.calls_per_hour, 3600)
        self._clean_old_calls(self.calls_per_day, 86400)

        # Check limits and wait if needed
        wait_times = []

        if len(self.calls_per_second) >= self.per_second:
            wait_times.append(1.0 - (now - self.calls_per_second[0]))

        if len(self.calls_per_minute) >= self.per_minute:
            wait_times.append(60.0 - (now - self.calls_per_minute[0]))

        if len(self.calls_per_hour) >= self.per_hour:
            wait_times.append(3600.0 - (now - self.calls_per_hour[0]))

        if len(self.calls_per_day) >= self.per_day:
            wait_times.append(86400.0 - (now - self.calls_per_day[0]))

        if wait_times:
            max_wait = max(wait_times)
            if max_wait > 0:
                await asyncio.sleep(max_wait)
                # Re-clean after waiting
                self._clean_old_calls(self.calls_per_second, 1)
                self._clean_old_calls(self.calls_per_minute, 60)
                self._clean_old_calls(self.calls_per_hour, 3600)
                self._clean_old_calls(self.calls_per_day, 86400)

        # Record this call
        now = time.time()
        self.calls_per_second.append(now)
        self.calls_per_minute.append(now)
        self.calls_per_hour.append(now)
        self.calls_per_day.append(now)


class DhanError(Exception):
    """Base exception for Dhan API errors"""

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


class AuthenticationError(DhanError):
    """Authentication related errors"""

    pass


class AuthorizationError(DhanError):
    """Authorization related errors"""

    pass


class RateLimitError(DhanError):
    """Rate limit exceeded errors"""

    pass


class ValidationError(DhanError):
    """Request validation errors"""

    pass


class NetworkError(DhanError):
    """Network related errors"""

    pass


class ServerError(DhanError):
    """Server side errors"""

    pass


class OrderError(DhanError):
    """Order related errors"""

    pass


class DhanClient:
    """
    Comprehensive Dhan HQ API Client

    Features:
    - Async HTTP operations with proper connection management - Multi-level rate limiting (per second/minute/hour/day) - Comprehensive error handling with custom exceptions - Request/response logging and monitoring - Retry logic with exponential backoff - Method implementations for all major API endpoints -
    Session management and token handling
    """

    def __init__(
        self,
        client_id: str,
        access_token: str,
        config: Optional[DhanConfig] = None,
    ):
        """
        Initialize Dhan client

        Args:
            client_id: Client ID from Dhan
            access_token: Access token from Dhan (obtained via web interface)
            config: Client configuration
        """
        self.client_id = client_id
        self.access_token = access_token

        self.config = config or DhanConfig()
        self.logger = get_logger("niraj.dhan")

        # Authentication state
        self.tokens = AuthTokens(
            client_id=client_id,
            access_token=access_token,
            expires_at=datetime.now()
            + timedelta(days=365),  # Dhan tokens are long-lived
        )
        self.is_authenticated = True  # Dhan uses pre-generated tokens
        self.session_id = secrets.token_hex(16)

        # HTTP client
        self.client: Optional[httpx.AsyncClient] = None

        # Multi-level rate limiting
        self.rate_limiter = RateLimiter(
            per_second=self.config.rate_limit_per_second,
            per_minute=self.config.rate_limit_per_minute,
            per_hour=self.config.rate_limit_per_hour,
            per_day=self.config.rate_limit_per_day,
        )

        # Device fingerprint for security
        self.device_id = self._generate_device_id()

    def _generate_device_id(self) -> str:
        """Generate a unique device ID"""
        return hashlib.md5(f"{self.client_id}_{time.time()}".encode()).hexdigest()

    def _get_default_headers(self, include_auth: bool = True) -> Dict[str, str]:
        """Get default headers for API requests"""
        headers = {
            "Content-Type": self.config.content_type,
            "Accept": self.config.accept,
            "User-Agent": "NIRAJ-Trading-System/1.0",
        }

        if include_auth and self.tokens.access_token:
            headers["access-token"] = self.tokens.access_token

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
            Various DhanError subclasses based on error type
        """
        if retries is None:
            retries = self.config.max_retries

        # Check rate limits
        await self.rate_limiter.wait_if_needed()

        url = f"{self.config.base_url}{endpoint}"
        headers = self._get_default_headers(include_auth=include_auth)

        client = await self._get_client()

        # Log request details
        with LogContext(
            session_id=self.session_id,
            client_id=self.client_id,
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
                        self.logger.debug("Request successful")
                        return response_data

                    elif response.status_code == 400:
                        error_message = response_data.get(
                            "internalErrorMessage", "Bad Request"
                        )
                        error_code = response_data.get("errorCode", "BAD_REQUEST")

                        self.logger.error(
                            f"Validation error: {error_code} - {error_message}"
                        )
                        raise ValidationError(
                            error_message,
                            error_code,
                            response.status_code,
                            response_data,
                        )

                    elif response.status_code == 401:
                        error_message = response_data.get(
                            "internalErrorMessage", "Authentication failed"
                        )
                        raise AuthenticationError(
                            error_message,
                            status_code=response.status_code,
                            response_data=response_data,
                        )

                    elif response.status_code == 403:
                        error_message = response_data.get(
                            "internalErrorMessage", "Authorization failed"
                        )
                        raise AuthorizationError(
                            error_message,
                            status_code=response.status_code,
                            response_data=response_data,
                        )

                    elif response.status_code == 429:
                        error_message = response_data.get(
                            "internalErrorMessage", "Rate limit exceeded"
                        )
                        raise RateLimitError(
                            error_message,
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

                        error_message = response_data.get(
                            "internalErrorMessage",
                            f"Server error: {response.status_code}",
                        )
                        raise ServerError(
                            error_message,
                            status_code=response.status_code,
                            response_data=response_data,
                        )

                    else:
                        error_message = response_data.get(
                            "internalErrorMessage", f"HTTP {response.status_code}"
                        )
                        raise DhanError(
                            f"{error_message}: {response.text[:200]}",
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
            raise DhanError("All retry attempts failed")

    async def close(self) -> None:
        """Close HTTP client and cleanup resources"""
        if self.client and not self.client.is_closed:
            await self.client.aclose()

        self.logger.info("Dhan client closed")

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
                    "Dhan client was not properly closed. Use async context manager or call close() explicitly."
                )
        except Exception:
            pass

    # Health Check and Utility Methods
    async def health_check(self) -> Dict[str, Any]:
        """
        Check API health and connectivity

        Returns:
            Health status
        """
        try:
            # Try a simple API call to check connectivity
            response = await self.get_fund_limits()
            return {
                "status": "healthy",
                "authenticated": True,
                "message": "API connection and authentication working",
                "response_time_ms": response.get("_response_time_ms", 0),
            }

        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "authenticated": False,
                "error": str(e),
            }

    def get_client_stats(self) -> Dict[str, Any]:
        """
        Get client statistics for monitoring

        Returns:
            Client statistics
        """
        return {
            "session_id": self.session_id,
            "client_id": self.client_id,
            "is_authenticated": self.is_authenticated,
            "token_expires_at": (
                self.tokens.expires_at.isoformat() if self.tokens.expires_at else None
            ),
            "calls_per_second": len(self.rate_limiter.calls_per_second),
            "calls_per_minute": len(self.rate_limiter.calls_per_minute),
            "calls_per_hour": len(self.rate_limiter.calls_per_hour),
            "calls_per_day": len(self.rate_limiter.calls_per_day),
            "rate_limits": {
                "per_second": self.config.rate_limit_per_second,
                "per_minute": self.config.rate_limit_per_minute,
                "per_hour": self.config.rate_limit_per_hour,
                "per_day": self.config.rate_limit_per_day,
            },
            "device_id": self.device_id,
        }

    # Authentication Methods

    def validate_token(self) -> bool:
        """
        Validate current access token

        Returns:
            True if token is valid, False otherwise
        """
        return (
            self.tokens.access_token is not None
            and self.tokens.expires_at is not None
            and datetime.now() < self.tokens.expires_at
        )

    def update_token(self, access_token: str) -> None:
        """
        Update access token (for token rotation)

        Args:
            access_token: New access token
        """
        self.tokens.access_token = access_token
        self.tokens.expires_at = datetime.now() + timedelta(
            days=365
        )  # Long-lived tokens
        self.is_authenticated = True

        self.logger.info("Updated Dhan access token")

    async def verify_authentication(self) -> Dict[str, Any]:
        """
        Verify authentication by making a test API call

        Returns:
            User information if authenticated

        Raises:
            AuthenticationError: If authentication fails
        """
        try:
            # Use fund limits as a simple authentication check
            await self.get_fund_limits()

            self.logger.info("Authentication verified successfully")
            return {
                "status": "authenticated",
                "client_id": self.client_id,
                "message": "Authentication successful",
                "verified_at": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Authentication verification failed: {e}")
            self.is_authenticated = False
            raise AuthenticationError(f"Authentication verification failed: {e}")

    def invalidate_session(self) -> None:
        """
        Invalidate current session (logout equivalent)
        Note: Dhan API doesn't have explicit logout, so we just clear local state
        """
        # Clear sensitive information
        self.tokens.access_token = None
        self.tokens.expires_at = None
        self.is_authenticated = False

        # Generate new session ID
        self.session_id = secrets.token_hex(16)

        self.logger.info("Dhan session invalidated")

    def get_authentication_status(self) -> Dict[str, Any]:
        """
        Get current authentication status

        Returns:
            Authentication status information
        """
        return {
            "is_authenticated": self.is_authenticated,
            "has_token": self.tokens.access_token is not None,
            "token_expires_at": (
                self.tokens.expires_at.isoformat() if self.tokens.expires_at else None
            ),
            "client_id": self.client_id,
            "session_id": self.session_id,
            "token_valid": self.validate_token(),
        }

    # Trading Methods

    @log_performance("dhan_place_order")
    async def place_order(
        self,
        transaction_type: str,
        exchange_segment: str,
        product_type: str,
        order_type: str,
        validity: str,
        trading_symbol: str,
        security_id: str,
        quantity: int,
        price: Optional[float] = None,
        trigger_price: Optional[float] = None,
        disclosed_quantity: Optional[int] = None,
        correlation_id: Optional[str] = None,
        after_market_order: bool = False,
        amo_time: Optional[str] = None,
        bo_profit_value: Optional[float] = None,
        bo_stop_loss_value: Optional[float] = None,
        drv_expiry_date: Optional[str] = None,
        drv_option_type: Optional[str] = None,
        drv_strike_price: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Place a new order

        Args:
            transaction_type: BUY or SELL
            exchange_segment: NSE_EQ, NSE_FNO, NSE_CURRENCY, BSE_EQ, BSE_FNO, BSE_CURRENCY, MCX_COMM
            product_type: CNC, INTRADAY, MARGIN, MTF, CO, BO
            order_type: LIMIT, MARKET, STOP_LOSS, STOP_LOSS_MARKET
            validity: DAY, IOC
            trading_symbol: Trading symbol
            security_id: Security identifier
            quantity: Number of shares/contracts
            price: Order price (required for LIMIT orders)
            trigger_price: Trigger price (required for STOP_LOSS orders)
            disclosed_quantity: Visible quantity (optional)
            correlation_id: User tracking ID (optional)
            after_market_order: AMO flag
            amo_time: AMO time
            bo_profit_value: Bracket order profit value
            bo_stop_loss_value: Bracket order stop loss value
            drv_expiry_date: Derivative expiry date
            drv_option_type: Option type (CALL/PUT)
            drv_strike_price: Strike price

        Returns:
            Order placement response with order ID

        Raises:
            OrderError: If order placement fails
        """
        order_data: Dict[str, Any] = {
            "dhanClientId": self.client_id,
            "transactionType": transaction_type,
            "exchangeSegment": exchange_segment,
            "productType": product_type,
            "orderType": order_type,
            "validity": validity,
            "tradingSymbol": trading_symbol,
            "securityId": security_id,
            "quantity": str(quantity),
        }

        # Add optional parameters
        if correlation_id:
            order_data["correlationId"] = correlation_id
        if disclosed_quantity is not None:
            order_data["disclosedQuantity"] = str(disclosed_quantity)
        if price is not None:
            order_data["price"] = str(price)
        if trigger_price is not None:
            order_data["triggerPrice"] = str(trigger_price)

        order_data["afterMarketOrder"] = after_market_order

        if amo_time:
            order_data["amoTime"] = amo_time
        if bo_profit_value is not None:
            order_data["boProfitValue"] = str(bo_profit_value)
        if bo_stop_loss_value is not None:
            order_data["boStopLossValue"] = str(bo_stop_loss_value)
        if drv_expiry_date:
            order_data["drvExpiryDate"] = drv_expiry_date
        if drv_option_type:
            order_data["drvOptionType"] = drv_option_type
        if drv_strike_price is not None:
            order_data["drvStrikePrice"] = drv_strike_price

        try:
            response = await self._make_request("POST", "/orders", data=order_data)

            order_id = response.get("orderId")
            order_status = response.get("orderStatus")

            self.logger.info(f"Placed order {order_id} with status {order_status}")
            return response

        except Exception as e:
            self.logger.error(f"Order placement failed: {e}")
            if isinstance(e, DhanError):
                raise OrderError(
                    f"Order placement failed: {e.message}",
                    e.error_code,
                    e.status_code,
                    e.response_data,
                )
            else:
                raise OrderError(f"Order placement failed: {str(e)}")

    @log_performance("dhan_modify_order")
    async def modify_order(
        self,
        order_id: str,
        order_type: str,
        quantity: int,
        price: float,
        validity: str,
        disclosed_quantity: Optional[int] = None,
        trigger_price: Optional[float] = None,
        leg_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Modify a pending order

        Args:
            order_id: Order ID to modify
            order_type: LIMIT, MARKET, STOP_LOSS, STOP_LOSS_MARKET
            quantity: New quantity
            price: New price
            validity: DAY, IOC
            disclosed_quantity: New disclosed quantity (optional)
            trigger_price: New trigger price (optional)
            leg_name: Leg name for bracket/cover orders (optional)

        Returns:
            Order modification response

        Raises:
            OrderError: If order modification fails
        """
        modify_data = {
            "dhanClientId": self.client_id,
            "orderId": order_id,
            "orderType": order_type,
            "quantity": str(quantity),
            "price": str(price),
            "validity": validity,
        }

        # Add optional parameters
        if disclosed_quantity is not None:
            modify_data["disclosedQuantity"] = str(disclosed_quantity)
        if trigger_price is not None:
            modify_data["triggerPrice"] = str(trigger_price)
        if leg_name:
            modify_data["legName"] = leg_name

        try:
            response = await self._make_request(
                "PUT", f"/orders/{order_id}", data=modify_data
            )

            self.logger.info(f"Modified order {order_id}")
            return response

        except Exception as e:
            self.logger.error(f"Order modification failed: {e}")
            if isinstance(e, DhanError):
                raise OrderError(
                    f"Order modification failed: {e.message}",
                    e.error_code,
                    e.status_code,
                    e.response_data,
                )
            else:
                raise OrderError(f"Order modification failed: {str(e)}")

    @log_performance("dhan_cancel_order")
    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """
        Cancel a pending order

        Args:
            order_id: Order ID to cancel

        Returns:
            Order cancellation response

        Raises:
            OrderError: If order cancellation fails
        """
        try:
            response = await self._make_request("DELETE", f"/orders/{order_id}")

            self.logger.info(f"Cancelled order {order_id}")
            return response

        except Exception as e:
            self.logger.error(f"Order cancellation failed: {e}")
            if isinstance(e, DhanError):
                raise OrderError(
                    f"Order cancellation failed: {e.message}",
                    e.error_code,
                    e.status_code,
                    e.response_data,
                )
            else:
                raise OrderError(f"Order cancellation failed: {str(e)}")

    @log_performance("dhan_place_slice_order")
    async def place_slice_order(
        self,
        transaction_type: str,
        exchange_segment: str,
        product_type: str,
        order_type: str,
        validity: str,
        trading_symbol: str,
        security_id: str,
        quantity: int,
        price: Optional[float] = None,
        trigger_price: Optional[float] = None,
        disclosed_quantity: Optional[int] = None,
        correlation_id: Optional[str] = None,
        after_market_order: bool = False,
        amo_time: Optional[str] = None,
        bo_profit_value: Optional[float] = None,
        bo_stop_loss_value: Optional[float] = None,
        drv_expiry_date: Optional[str] = None,
        drv_option_type: Optional[str] = None,
        drv_strike_price: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Place a slice order (for quantities over freeze limit)

        Args:
            Same as place_order method

        Returns:
            Slice order placement response

        Raises:
            OrderError: If slice order placement fails
        """
        order_data: Dict[str, Any] = {
            "dhanClientId": self.client_id,
            "transactionType": transaction_type,
            "exchangeSegment": exchange_segment,
            "productType": product_type,
            "orderType": order_type,
            "validity": validity,
            "tradingSymbol": trading_symbol,
            "securityId": security_id,
            "quantity": str(quantity),
        }

        # Add optional parameters (same as place_order)
        if correlation_id:
            order_data["correlationId"] = correlation_id
        if disclosed_quantity is not None:
            order_data["disclosedQuantity"] = str(disclosed_quantity)
        if price is not None:
            order_data["price"] = str(price)
        if trigger_price is not None:
            order_data["triggerPrice"] = str(trigger_price)

        order_data["afterMarketOrder"] = after_market_order

        if amo_time:
            order_data["amoTime"] = amo_time
        if bo_profit_value is not None:
            order_data["boProfitValue"] = str(bo_profit_value)
        if bo_stop_loss_value is not None:
            order_data["boStopLossValue"] = str(bo_stop_loss_value)
        if drv_expiry_date:
            order_data["drvExpiryDate"] = drv_expiry_date
        if drv_option_type:
            order_data["drvOptionType"] = drv_option_type
        if drv_strike_price is not None:
            order_data["drvStrikePrice"] = drv_strike_price

        try:
            response = await self._make_request(
                "POST", "/orders/slicing", data=order_data
            )

            self.logger.info("Placed slice order successfully")
            return response

        except Exception as e:
            self.logger.error(f"Slice order placement failed: {e}")
            if isinstance(e, DhanError):
                raise OrderError(
                    f"Slice order placement failed: {e.message}",
                    e.error_code,
                    e.status_code,
                    e.response_data,
                )
            else:
                raise OrderError(f"Slice order placement failed: {str(e)}")

    @log_performance("dhan_get_order_list")
    async def get_order_list(self) -> List[Dict[str, Any]]:
        """
        Get list of all orders for the day

        Returns:
            List of all orders

        Raises:
            DhanError: If request fails
        """
        try:
            response = await self._make_request("GET", "/orders")

            self.logger.debug("Retrieved order list")
            return response if isinstance(response, list) else [response]

        except Exception as e:
            self.logger.error(f"Failed to get order list: {e}")
            raise

    @log_performance("dhan_get_order_by_id")
    async def get_order_by_id(self, order_id: str) -> Dict[str, Any]:
        """
        Get order details by order ID

        Args:
            order_id: Order ID to retrieve

        Returns:
            Order details

        Raises:
            DhanError: If request fails
        """
        try:
            response = await self._make_request("GET", f"/orders/{order_id}")

            self.logger.debug(f"Retrieved order details for {order_id}")
            return response

        except Exception as e:
            self.logger.error(f"Failed to get order {order_id}: {e}")
            raise

    @log_performance("dhan_get_order_by_correlation_id")
    async def get_order_by_correlation_id(self, correlation_id: str) -> Dict[str, Any]:
        """
        Get order details by correlation ID

        Args:
            correlation_id: Correlation ID to retrieve

        Returns:
            Order details

        Raises:
            DhanError: If request fails
        """
        try:
            response = await self._make_request(
                "GET", f"/orders/external/{correlation_id}"
            )

            self.logger.debug(
                f"Retrieved order details for correlation ID {correlation_id}"
            )
            return response

        except Exception as e:
            self.logger.error(
                f"Failed to get order by correlation ID {correlation_id}: {e}"
            )
            raise

    @log_performance("dhan_get_trade_book")
    async def get_trade_book(
        self, order_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get trade book (executed trades)

        Args:
            order_id: Optional order ID to get trades for specific order

        Returns:
            List of trades

        Raises:
            DhanError: If request fails
        """
        try:
            endpoint = f"/trades/{order_id}" if order_id else "/trades"
            response = await self._make_request("GET", endpoint)

            self.logger.debug("Retrieved trade book")
            return response if isinstance(response, list) else [response]

        except Exception as e:
            self.logger.error(f"Failed to get trade book: {e}")
            raise

    # Portfolio Methods

    @log_performance("dhan_get_holdings")
    async def get_holdings(self) -> List[Dict[str, Any]]:
        """
        Get holdings (positions in delivery)

        Returns:
            List of holdings with details

        Raises:
            DhanError: If request fails
        """
        try:
            response = await self._make_request("GET", "/holdings")

            self.logger.debug("Retrieved holdings")
            return response if isinstance(response, list) else [response]

        except Exception as e:
            self.logger.error(f"Failed to get holdings: {e}")
            raise

    @log_performance("dhan_get_positions")
    async def get_positions(self) -> List[Dict[str, Any]]:
        """
        Get positions (open positions including F&O carryforward)

        Returns:
            List of positions with details

        Raises:
            DhanError: If request fails
        """
        try:
            response = await self._make_request("GET", "/positions")

            self.logger.debug("Retrieved positions")
            return response if isinstance(response, list) else [response]

        except Exception as e:
            self.logger.error(f"Failed to get positions: {e}")
            raise

    @log_performance("dhan_convert_position")
    async def convert_position(
        self,
        from_product_type: str,
        to_product_type: str,
        exchange_segment: str,
        position_type: str,
        security_id: str,
        trading_symbol: str,
        convert_qty: int,
    ) -> Dict[str, Any]:
        """
        Convert position from one product type to another

        Args:
            from_product_type: Current product type (CNC, INTRADAY, MARGIN, CO, BO)
            to_product_type: Desired product type (CNC, INTRADAY, MARGIN, CO, BO)
            exchange_segment: Exchange segment
            position_type: LONG, SHORT, CLOSED
            security_id: Security identifier
            trading_symbol: Trading symbol
            convert_qty: Quantity to convert

        Returns:
            Position conversion response

        Raises:
            DhanError: If conversion fails
        """
        convert_data = {
            "dhanClientId": self.client_id,
            "fromProductType": from_product_type,
            "toProductType": to_product_type,
            "exchangeSegment": exchange_segment,
            "positionType": position_type,
            "securityId": security_id,
            "tradingSymbol": trading_symbol,
            "convertQty": str(convert_qty),
        }

        try:
            response = await self._make_request(
                "POST", "/positions/convert", data=convert_data
            )

            self.logger.info(f"Converted position for {trading_symbol}")
            return response

        except Exception as e:
            self.logger.error(f"Position conversion failed: {e}")
            raise

    # Market Data Methods

    @log_performance("dhan_historical_daily_data")
    async def get_historical_daily_data(
        self,
        symbol: str,
        exchange_segment: str,
        instrument_type: str,
        from_date: str,
        to_date: str,
        expiry_code: Optional[int] = 0,
    ) -> Dict[str, Any]:
        """
        Get historical daily OHLC data

        Args:
            symbol: Symbol of the instrument
            exchange_segment: NSE_EQ, NSE_FNO, NSE_CURRENCY, BSE_EQ, MCX_COMM, IDX_I
            instrument_type: EQUITY, FUTCOM, FUTCUR, FUTIDX, FUTSTKINDEX
            from_date: Start date (YYYY-MM-DD format)
            to_date: End date (YYYY-MM-DD format, non-inclusive)
            expiry_code: Expiry code for derivatives (optional)

        Returns:
            Historical OHLC data with open, high, low, close, volume, start_Time arrays

        Raises:
            DhanError: If request fails
        """
        data: Dict[str, Any] = {
            "symbol": symbol,
            "exchangeSegment": exchange_segment,
            "instrument": instrument_type,
            "fromDate": from_date,
            "toDate": to_date,
        }

        if expiry_code is not None:
            data["expiryCode"] = expiry_code

        try:
            response = await self._make_request("POST", "/charts/historical", data=data)

            self.logger.debug(f"Retrieved historical daily data for {symbol}")
            return response

        except Exception as e:
            self.logger.error(f"Failed to get historical daily data: {e}")
            raise

    @log_performance("dhan_intraday_minute_data")
    async def get_intraday_minute_data(
        self,
        security_id: str,
        exchange_segment: str,
        instrument_type: str,
    ) -> Dict[str, Any]:
        """
        Get intraday minute OHLC data (1-minute candles for current day)

        Args:
            security_id: Security identifier
            exchange_segment: NSE_EQ, NSE_FNO, NSE_CURRENCY, BSE_EQ, MCX_COMM
            instrument_type: EQUITY, FUTCOM, FUTCUR, FUTIDX, FUTSTKINDEX

        Returns:
            Intraday minute OHLC data

        Raises:
            DhanError: If request fails
        """
        data = {
            "securityId": security_id,
            "exchangeSegment": exchange_segment,
            "instrument": instrument_type,
        }

        try:
            response = await self._make_request("POST", "/charts/intraday", data=data)

            self.logger.debug(f"Retrieved intraday minute data for {security_id}")
            return response

        except Exception as e:
            self.logger.error(f"Failed to get intraday minute data: {e}")
            raise

    @log_performance("dhan_get_market_quote")
    async def get_market_quote(
        self,
        security_ids: List[str],
        quote_type: str = "Ticker",
    ) -> List[Dict[str, Any]]:
        """
        Get market quotes for instruments (V2 API feature)

        Args:
            security_ids: List of security IDs (up to 1000 instruments)
            quote_type: Quote type - "Ticker", "Quote", "Full"

        Returns:
            Market quote data

        Raises:
            DhanError: If request fails
        """
        data = {
            "instruments": [
                {"exchangeSegment": "NSE", "securityId": sid} for sid in security_ids
            ],
            "quoteType": quote_type,
        }

        try:
            response = await self._make_request("POST", "/marketQuote", data=data)

            self.logger.debug(
                f"Retrieved market quotes for {len(security_ids)} instruments"
            )
            return response if isinstance(response, list) else [response]

        except Exception as e:
            self.logger.error(f"Failed to get market quotes: {e}")
            raise

    @log_performance("dhan_get_option_chain")
    async def get_option_chain(
        self,
        underlying_security_id: str,
        exchange_segment: str,
        expiry_code: int,
    ) -> Dict[str, Any]:
        """
        Get option chain data for an underlying (V2 API feature)

        Args:
            underlying_security_id: Security ID of underlying
            exchange_segment: NSE_FNO, BSE_FNO
            expiry_code: Expiry code

        Returns:
            Option chain data with OI, greeks, volume, bid/ask data

        Raises:
            DhanError: If request fails
        """
        data = {
            "underlyingSecurityId": underlying_security_id,
            "exchangeSegment": exchange_segment,
            "expiryCode": expiry_code,
        }

        try:
            response = await self._make_request("POST", "/optionChain", data=data)

            self.logger.debug(f"Retrieved option chain for {underlying_security_id}")
            return response

        except Exception as e:
            self.logger.error(f"Failed to get option chain: {e}")
            raise

    def convert_epoch_to_datetime(self, epoch_time: int) -> str:
        """
        Convert epoch time to readable datetime string

        Args:
            epoch_time: Epoch timestamp

        Returns:
            Formatted datetime string
        """
        return datetime.fromtimestamp(epoch_time).strftime("%Y-%m-%d %H:%M:%S")

    # Funds and Statement Methods

    @log_performance("dhan_get_fund_limits")
    async def get_fund_limits(self) -> Dict[str, Any]:
        """
        Get fund limits and account balance information

        Returns:
            Fund limit details including available balance, margin utilization, etc.

        Raises:
            DhanError: If request fails
        """
        try:
            response = await self._make_request("GET", "/fundlimit")

            self.logger.debug("Retrieved fund limits")
            return response

        except Exception as e:
            self.logger.error(f"Failed to get fund limits: {e}")
            raise

    @log_performance("dhan_margin_calculator")
    async def margin_calculator(
        self,
        exchange_segment: str,
        transaction_type: str,
        quantity: int,
        product_type: str,
        security_id: str,
        price: float,
        trigger_price: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Calculate margin requirements for an order

        Args:
            exchange_segment: NSE_EQ, NSE_FNO, BSE_EQ, BSE_FNO, MCX_COMM
            transaction_type: BUY, SELL
            quantity: Number of shares/contracts
            product_type: CNC, INTRADAY, MARGIN, MTF, CO, BO
            security_id: Security identifier
            price: Order price
            trigger_price: Trigger price (required for SL orders)

        Returns:
            Margin calculation details including total margin, span, exposure, etc.

        Raises:
            DhanError: If request fails
        """
        data = {
            "dhanClientId": self.client_id,
            "exchangeSegment": exchange_segment,
            "transactionType": transaction_type,
            "quantity": quantity,
            "productType": product_type,
            "securityId": security_id,
            "price": price,
        }

        if trigger_price is not None:
            data["triggerPrice"] = trigger_price

        try:
            response = await self._make_request("POST", "/margincalculator", data=data)

            self.logger.debug(f"Calculated margin for {security_id}")
            return response

        except Exception as e:
            self.logger.error(f"Failed to calculate margin: {e}")
            raise

    # Utility Methods

    async def fetch_security_list(
        self, list_type: str = "compact"
    ) -> List[Dict[str, Any]]:
        """
        Fetch instrument/security list

        Args:
            list_type: Type of list to fetch (compact/full)

        Returns:
            List of securities/instruments

        Raises:
            DhanError: If request fails
        """
        try:
            # This would typically be an API call, but is often a CSV download
            # For now, implementing as a placeholder
            response = await self._make_request("GET", f"/instruments?type={list_type}")

            self.logger.debug(f"Retrieved {list_type} security list")
            return response if isinstance(response, list) else [response]

        except Exception as e:
            self.logger.error(f"Failed to fetch security list: {e}")
            raise

    async def get_kill_switch_status(self) -> Dict[str, Any]:
        """
        Get kill switch status (V2 API feature)

        Returns:
            Kill switch status

        Raises:
            DhanError: If request fails
        """
        try:
            response = await self._make_request("GET", "/killSwitch")

            self.logger.debug("Retrieved kill switch status")
            return response

        except Exception as e:
            self.logger.error(f"Failed to get kill switch status: {e}")
            raise

    async def set_kill_switch(self, status: str) -> Dict[str, Any]:
        """
        Set kill switch status (V2 API feature)

        Args:
            status: ACTIVATE or DEACTIVATE

        Returns:
            Kill switch response

        Raises:
            DhanError: If request fails
        """
        data = {
            "dhanClientId": self.client_id,
            "killSwitchStatus": status,
        }

        try:
            response = await self._make_request("POST", "/killSwitch", data=data)

            self.logger.info(f"Set kill switch to {status}")
            return response

        except Exception as e:
            self.logger.error(f"Failed to set kill switch: {e}")
            raise
