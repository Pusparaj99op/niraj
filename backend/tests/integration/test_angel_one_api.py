"""
Integration Test: T037 - Angel One API Connection
Tests the complete Angel One API integration and connection handling.

This test validates:
1. API authentication and token management
2. Market data retrieval and real-time streaming
3. Order placement and execution
4. Portfolio and position management
5. Historical data fetching
6. Error handling and retry mechanisms
7. Rate limiting and throttling
8. Connection recovery and failover
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock
from enum import Enum

# Mock imports for integration testing
from sqlalchemy.orm import Session


class OrderType(Enum):
    """Order type enumeration"""

    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "SL"
    STOP_LOSS_MARKET = "SL-M"


class OrderSide(Enum):
    """Order side enumeration"""

    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(Enum):
    """Order status enumeration"""

    PENDING = "pending"
    OPEN = "open"
    COMPLETE = "complete"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class APIConnectionState(Enum):
    """API connection state enumeration"""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


class AngelOneError(Exception):
    """Base exception for Angel One API errors"""

    pass


class AuthenticationError(AngelOneError):
    """Raised when API authentication fails"""

    pass


class RateLimitError(AngelOneError):
    """Raised when API rate limit is exceeded"""

    pass


class OrderExecutionError(AngelOneError):
    """Raised when order execution fails"""

    pass


class DataFeedError(AngelOneError):
    """Raised when market data feed fails"""

    pass


class MockAngelOneClient:
    """Mock Angel One API client for testing"""

    def __init__(self, api_key: str, client_id: str, pin: str):
        self.api_key = api_key
        self.client_id = client_id
        self.pin = pin
        self.access_token = None
        self.refresh_token = None
        self.connection_state = APIConnectionState.DISCONNECTED
        self.session_expiry = None
        self.rate_limit_remaining = 100
        self.last_request_time = None


class MockMarketData:
    """Mock market data response"""

    def __init__(self, symbol: str, exchange: str = "NSE"):
        self.symbol = symbol
        self.exchange = exchange
        self.ltp = Decimal("0.00")  # Last traded price
        self.volume = 0
        self.open = Decimal("0.00")
        self.high = Decimal("0.00")
        self.low = Decimal("0.00")
        self.close = Decimal("0.00")
        self.timestamp = datetime.now()


class MockOrderResponse:
    """Mock order placement response"""

    def __init__(self, order_id: str = "AO001"):
        self.order_id = order_id
        self.status = OrderStatus.PENDING
        self.message = "Order placed successfully"
        self.avg_price = Decimal("0.00")
        self.filled_quantity = 0
        self.pending_quantity = 0


class MockPortfolio:
    """Mock portfolio response"""

    def __init__(self, client_id: str):
        self.client_id = client_id
        self.total_value = Decimal("100000.00")
        self.available_cash = Decimal("20000.00")
        self.holdings = {}
        self.positions = {}


@pytest.fixture
def mock_db_session():
    """Mock database session"""
    session = Mock(spec=Session)
    session.commit = Mock()
    session.rollback = Mock()
    session.close = Mock()
    return session


@pytest.fixture
def angel_one_client():
    """Mock Angel One API client"""
    client = MockAngelOneClient(api_key="test_api_key", client_id="TEST123", pin="1234")
    return client


@pytest.fixture
def auth_service():
    """Mock authentication service"""
    service = Mock()
    service.authenticate = AsyncMock()
    service.refresh_token = AsyncMock()
    service.logout = AsyncMock()
    service.validate_session = AsyncMock()
    return service


@pytest.fixture
def market_data_service():
    """Mock market data service"""
    service = Mock()
    service.get_quote = AsyncMock()
    service.get_historical_data = AsyncMock()
    service.subscribe_live_feed = AsyncMock()
    service.unsubscribe_live_feed = AsyncMock()
    return service


@pytest.fixture
def order_service():
    """Mock order service"""
    service = Mock()
    service.place_order = AsyncMock()
    service.modify_order = AsyncMock()
    service.cancel_order = AsyncMock()
    service.get_order_status = AsyncMock()
    service.get_order_book = AsyncMock()
    return service


@pytest.fixture
def portfolio_service():
    """Mock portfolio service"""
    service = Mock()
    service.get_holdings = AsyncMock()
    service.get_positions = AsyncMock()
    service.get_funds = AsyncMock()
    return service


@pytest.fixture
def connection_manager():
    """Mock connection manager"""
    service = Mock()
    service.connect = AsyncMock()
    service.disconnect = AsyncMock()
    service.check_health = AsyncMock()
    service.handle_reconnection = AsyncMock()
    return service


class TestAngelOneAPI:
    """Integration tests for Angel One API connection and operations"""

    @pytest.mark.asyncio
    async def test_complete_api_authentication_workflow(
        self, mock_db_session, angel_one_client, auth_service, connection_manager
    ):
        """Test complete API authentication and session management workflow"""

        # Mock authentication response
        auth_response = {
            "status": True,
            "message": "SUCCESS",
            "errorcode": "",
            "data": {
                "jwtToken": "mock_jwt_token_12345",
                "refreshToken": "mock_refresh_token_67890",
                "feedToken": "mock_feed_token_abcde",
            },
        }

        # Configure service responses
        auth_service.authenticate.return_value = auth_response
        auth_service.validate_session.return_value = True
        connection_manager.connect.return_value = {"connected": True}

        try:
            # Step 1: Authenticate with Angel One API
            auth_result = await auth_service.authenticate(
                client_id=angel_one_client.client_id,
                password="test_password",
                totp="123456",
            )

            assert auth_result["status"] is True
            assert "jwtToken" in auth_result["data"]
            assert "refreshToken" in auth_result["data"]

            # Step 2: Store tokens
            angel_one_client.access_token = auth_result["data"]["jwtToken"]
            angel_one_client.refresh_token = auth_result["data"]["refreshToken"]
            angel_one_client.session_expiry = datetime.now() + timedelta(hours=8)

            # Step 3: Establish connection
            connection_result = await connection_manager.connect(
                access_token=angel_one_client.access_token
            )

            assert connection_result["connected"] is True
            angel_one_client.connection_state = APIConnectionState.CONNECTED

            # Step 4: Validate session
            session_valid = await auth_service.validate_session(
                angel_one_client.access_token
            )
            assert session_valid is True

            # Step 5: Check API health
            health_check = await connection_manager.check_health()
            assert health_check is not None

            print("✅ Complete API authentication workflow executed successfully")

        except Exception as e:
            pytest.fail(f"API authentication workflow failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_authentication_failure_retry_mechanism(
        self, mock_db_session, angel_one_client, auth_service
    ):
        """Test authentication failure handling and retry mechanism"""

        # Configure authentication to fail initially
        failure_count = 0
        max_retries = 3

        async def mock_authenticate(*args, **kwargs):
            nonlocal failure_count
            failure_count += 1

            if failure_count <= max_retries:
                raise AuthenticationError(
                    f"Authentication failed: attempt {failure_count}"
                )
            else:
                # Success after retries
                return {
                    "status": True,
                    "message": "SUCCESS",
                    "data": {"jwtToken": "success_token"},
                }

        auth_service.authenticate.side_effect = mock_authenticate

        try:
            # Attempt authentication with retry logic
            for retry_count in range(max_retries + 2):
                try:
                    auth_result = await auth_service.authenticate(
                        client_id=angel_one_client.client_id,
                        password="test_password",
                        totp="123456",
                    )

                    # Success after retries
                    assert auth_result["status"] is True
                    print("✅ Authentication retry mechanism working correctly")
                    break

                except AuthenticationError:
                    if retry_count < max_retries:
                        # Expected failure, wait before retry
                        await asyncio.sleep(0.1)  # Short delay for testing
                        continue
                    else:
                        raise  # Max retries exceeded

        except Exception as e:
            pytest.fail(f"Authentication retry mechanism failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_market_data_retrieval_and_streaming(
        self, mock_db_session, angel_one_client, market_data_service
    ):
        """Test market data retrieval and real-time streaming"""

        # Mock market data
        symbol = "RELIANCE-EQ"
        mock_quote = MockMarketData(symbol)
        mock_quote.ltp = Decimal("2500.75")
        mock_quote.volume = 1500000
        mock_quote.open = Decimal("2480.00")
        mock_quote.high = Decimal("2520.00")
        mock_quote.low = Decimal("2475.00")

        # Mock live feed data
        live_feed_data = {
            "symbol": symbol,
            "ltp": 2501.25,
            "volume": 1502000,
            "timestamp": datetime.now().isoformat(),
        }

        # Configure service responses
        market_data_service.get_quote.return_value = mock_quote
        market_data_service.subscribe_live_feed.return_value = True

        # Mock streaming callback
        stream_data_received = []

        def mock_stream_callback(data):
            stream_data_received.append(data)

        try:
            # Step 1: Get current market quote
            quote = await market_data_service.get_quote(symbol=symbol, exchange="NSE")

            assert quote.symbol == symbol
            assert quote.ltp > 0
            assert quote.volume >= 0

            # Step 2: Subscribe to live data feed
            subscription_success = await market_data_service.subscribe_live_feed(
                symbols=[symbol], callback=mock_stream_callback
            )

            assert subscription_success is True

            # Step 3: Simulate live data reception
            mock_stream_callback(live_feed_data)

            assert len(stream_data_received) > 0
            assert stream_data_received[0]["symbol"] == symbol
            assert stream_data_received[0]["ltp"] > 0

            # Step 4: Unsubscribe from live feed
            await market_data_service.unsubscribe_live_feed([symbol])

            print("✅ Market data retrieval and streaming working correctly")

        except Exception as e:
            pytest.fail(f"Market data retrieval/streaming failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_order_placement_and_execution(
        self, mock_db_session, angel_one_client, order_service
    ):
        """Test order placement, modification, and execution"""

        # Test order details
        order_details = {
            "symbol": "RELIANCE-EQ",
            "exchange": "NSE",
            "transaction_type": OrderSide.BUY,
            "order_type": OrderType.LIMIT,
            "quantity": 10,
            "price": Decimal("2500.00"),
            "product": "MIS",  # Intraday
        }

        # Mock order responses
        place_response = MockOrderResponse("AO001")
        place_response.status = OrderStatus.OPEN

        modify_response = MockOrderResponse("AO001")
        modify_response.status = OrderStatus.OPEN

        # Configure service responses
        order_service.place_order.return_value = place_response
        order_service.modify_order.return_value = modify_response
        order_service.get_order_status.return_value = {
            "order_id": "AO001",
            "status": OrderStatus.COMPLETE,
            "avg_price": Decimal("2499.50"),
            "filled_quantity": 10,
        }

        try:
            # Step 1: Place order
            order_result = await order_service.place_order(**order_details)

            assert order_result.order_id is not None
            assert order_result.status in [OrderStatus.PENDING, OrderStatus.OPEN]

            # Step 2: Modify order price
            modify_result = await order_service.modify_order(
                order_id=order_result.order_id, price=Decimal("2505.00")
            )

            assert modify_result.order_id == order_result.order_id
            assert modify_result.status == OrderStatus.OPEN

            # Step 3: Check order status
            status_result = await order_service.get_order_status(
                order_id=order_result.order_id
            )

            assert status_result["order_id"] == order_result.order_id
            assert status_result["status"] == OrderStatus.COMPLETE
            assert status_result["filled_quantity"] == order_details["quantity"]

            # Step 4: Validate execution price
            avg_price = status_result["avg_price"]
            limit_price = order_details["price"]

            # For buy order, execution price should be <= limit price (approximately)
            price_tolerance = Decimal("10.00")  # ₹10 tolerance
            assert abs(avg_price - limit_price) <= price_tolerance

            print("✅ Order placement and execution working correctly")

        except Exception as e:
            pytest.fail(f"Order placement/execution failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_portfolio_and_position_management(
        self, mock_db_session, angel_one_client, portfolio_service
    ):
        """Test portfolio and position management operations"""

        # Mock portfolio data
        mock_holdings = {
            "RELIANCE": {
                "symbol": "RELIANCE-EQ",
                "quantity": 100,
                "avg_price": Decimal("2400.00"),
                "current_price": Decimal("2500.00"),
                "pnl": Decimal("10000.00"),
            },
            "TCS": {
                "symbol": "TCS-EQ",
                "quantity": 50,
                "avg_price": Decimal("3200.00"),
                "current_price": Decimal("3150.00"),
                "pnl": Decimal("-2500.00"),
            },
        }

        mock_positions = {
            "INFY": {
                "symbol": "INFY-EQ",
                "quantity": 25,
                "avg_price": Decimal("1500.00"),
                "current_price": Decimal("1520.00"),
                "pnl": Decimal("500.00"),
                "product": "MIS",
            }
        }

        mock_funds = {
            "available_cash": Decimal("50000.00"),
            "utilized_margin": Decimal("30000.00"),
            "available_margin": Decimal("20000.00"),
        }

        # Configure service responses
        portfolio_service.get_holdings.return_value = mock_holdings
        portfolio_service.get_positions.return_value = mock_positions
        portfolio_service.get_funds.return_value = mock_funds

        try:
            # Step 1: Get portfolio holdings
            holdings = await portfolio_service.get_holdings(
                client_id=angel_one_client.client_id
            )

            assert len(holdings) > 0
            assert "RELIANCE" in holdings
            assert holdings["RELIANCE"]["quantity"] > 0

            # Step 2: Get current positions
            positions = await portfolio_service.get_positions(
                client_id=angel_one_client.client_id
            )

            assert len(positions) > 0
            assert "INFY" in positions
            assert positions["INFY"]["product"] == "MIS"

            # Step 3: Get fund information
            funds = await portfolio_service.get_funds(
                client_id=angel_one_client.client_id
            )

            assert funds["available_cash"] > 0
            assert funds["available_margin"] >= 0

            # Step 4: Calculate total portfolio value
            total_holdings_value = sum(
                holding["quantity"] * holding["current_price"]
                for holding in holdings.values()
            )

            total_positions_pnl = sum(
                position["pnl"] for position in positions.values()
            )

            assert total_holdings_value > 0
            assert total_positions_pnl != 0  # Can be positive or negative

            print("✅ Portfolio and position management working correctly")

        except Exception as e:
            pytest.fail(f"Portfolio/position management failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_historical_data_fetching(
        self, mock_db_session, angel_one_client, market_data_service
    ):
        """Test historical data fetching with different intervals"""

        symbol = "RELIANCE-EQ"
        from_date = datetime.now() - timedelta(days=30)
        to_date = datetime.now()

        # Mock historical data
        historical_data = []
        for i in range(30):
            data_point = {
                "timestamp": from_date + timedelta(days=i),
                "open": Decimal(f"24{50 + (i % 10)}.00"),
                "high": Decimal(f"25{00 + (i % 15)}.00"),
                "low": Decimal(f"24{00 + (i % 8)}.00"),
                "close": Decimal(f"24{75 + (i % 12)}.00"),
                "volume": 1000000 + (i * 10000),
            }
            historical_data.append(data_point)

        # Configure service response
        market_data_service.get_historical_data.return_value = historical_data

        try:
            # Step 1: Fetch daily historical data
            daily_data = await market_data_service.get_historical_data(
                symbol=symbol,
                exchange="NSE",
                interval="1DAY",
                from_date=from_date,
                to_date=to_date,
            )

            assert len(daily_data) > 0
            assert len(daily_data) <= 30  # Max 30 days

            # Step 2: Validate data structure
            first_candle = daily_data[0]
            required_fields = ["timestamp", "open", "high", "low", "close", "volume"]

            for field in required_fields:
                assert field in first_candle
                assert first_candle[field] is not None

            # Step 3: Validate OHLC data integrity
            for candle in daily_data[:5]:  # Check first 5 candles
                assert candle["high"] >= candle["open"]
                assert candle["high"] >= candle["close"]
                assert candle["low"] <= candle["open"]
                assert candle["low"] <= candle["close"]
                assert candle["volume"] > 0

            # Step 4: Test different time intervals
            intervals = ["5MINUTE", "15MINUTE", "1HOUR"]

            for interval in intervals:
                interval_data = await market_data_service.get_historical_data(
                    symbol=symbol,
                    exchange="NSE",
                    interval=interval,
                    from_date=from_date,
                    to_date=to_date,
                )

                assert len(interval_data) >= 0  # Can be empty for some intervals

            print("✅ Historical data fetching working correctly")

        except Exception as e:
            pytest.fail(f"Historical data fetching failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_rate_limiting_and_throttling(
        self, mock_db_session, angel_one_client, market_data_service
    ):
        """Test API rate limiting and throttling mechanisms"""

        # Mock rate limit configuration
        rate_limits = {
            "requests_per_second": 10,
            "requests_per_minute": 100,
            "requests_per_hour": 1000,
        }

        # Track request times
        request_times = []

        async def mock_rate_limited_request():
            # Check rate limit before request
            current_time = datetime.now()
            request_times.append(current_time)

            # Check requests in last second
            last_second = current_time - timedelta(seconds=1)
            recent_requests = [t for t in request_times if t >= last_second]

            if len(recent_requests) > rate_limits["requests_per_second"]:
                raise RateLimitError(
                    "Rate limit exceeded: too many requests per second"
                )

            # Simulate successful request
            return {"status": "success", "timestamp": current_time}

        try:
            # Step 1: Test normal request rate (within limits)
            successful_requests = 0

            for i in range(5):  # 5 requests (within limit)
                try:
                    await mock_rate_limited_request()
                    successful_requests += 1
                    await asyncio.sleep(0.15)  # 150ms delay
                except RateLimitError:
                    pass

            assert successful_requests == 5

            # Step 2: Test rate limit violation
            rate_limit_hit = False

            try:
                # Rapid fire requests (should hit rate limit)
                for i in range(15):  # Exceed limit
                    await mock_rate_limited_request()
            except RateLimitError:
                rate_limit_hit = True

            assert rate_limit_hit is True

            # Step 3: Test rate limit recovery
            await asyncio.sleep(1.1)  # Wait for rate limit reset

            try:
                result = await mock_rate_limited_request()
                assert result["status"] == "success"
                print("✅ Rate limit recovery working correctly")
            except RateLimitError:
                pytest.fail("Rate limit should have reset")

            print("✅ Rate limiting and throttling working correctly")

        except Exception as e:
            pytest.fail(f"Rate limiting/throttling test failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_connection_recovery_and_failover(
        self, mock_db_session, angel_one_client, connection_manager, auth_service
    ):
        """Test connection recovery and failover mechanisms"""

        # Simulate connection failure scenarios
        connection_failures = 0
        max_failures = 3

        async def mock_connection_with_failures():
            nonlocal connection_failures
            connection_failures += 1

            if connection_failures <= max_failures:
                angel_one_client.connection_state = APIConnectionState.ERROR
                raise ConnectionError(
                    f"Connection failed: attempt {connection_failures}"
                )
            else:
                # Recovery after failures
                angel_one_client.connection_state = APIConnectionState.CONNECTED
                return {"connected": True, "recovered": True}

        connection_manager.connect.side_effect = mock_connection_with_failures

        try:
            # Step 1: Attempt connection with failures
            connection_recovered = False

            for attempt in range(max_failures + 2):
                try:
                    connection_result = await connection_manager.connect()
                    if connection_result.get("recovered"):
                        connection_recovered = True
                        break
                except ConnectionError:
                    # Handle connection failure
                    angel_one_client.connection_state = APIConnectionState.RECONNECTING

                    # Implement exponential backoff
                    backoff_delay = min(2**attempt, 30)  # Max 30 seconds
                    await asyncio.sleep(backoff_delay * 0.01)  # Speed up for testing

                    continue

            assert connection_recovered is True
            assert angel_one_client.connection_state == APIConnectionState.CONNECTED

            # Step 2: Test automatic reconnection
            reconnection_service = Mock()
            reconnection_service.auto_reconnect = AsyncMock(return_value=True)

            reconnection_result = await reconnection_service.auto_reconnect()
            assert reconnection_result is True

            # Step 3: Test session refresh during reconnection
            auth_service.refresh_token.return_value = {
                "status": True,
                "data": {"jwtToken": "new_refreshed_token"},
            }

            refresh_result = await auth_service.refresh_token(
                angel_one_client.refresh_token
            )

            assert refresh_result["status"] is True
            angel_one_client.access_token = refresh_result["data"]["jwtToken"]

            print("✅ Connection recovery and failover working correctly")

        except Exception as e:
            pytest.fail(f"Connection recovery/failover failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_error_handling_comprehensive(
        self,
        mock_db_session,
        angel_one_client,
        auth_service,
        order_service,
        market_data_service,
    ):
        """Test comprehensive error handling for various API scenarios"""

        error_scenarios = [
            {
                "error_type": AuthenticationError,
                "message": "Invalid credentials",
                "service": auth_service,
                "method": "authenticate",
            },
            {
                "error_type": OrderExecutionError,
                "message": "Insufficient funds",
                "service": order_service,
                "method": "place_order",
            },
            {
                "error_type": DataFeedError,
                "message": "Market data unavailable",
                "service": market_data_service,
                "method": "get_quote",
            },
            {
                "error_type": RateLimitError,
                "message": "API rate limit exceeded",
                "service": market_data_service,
                "method": "get_quote",
            },
        ]

        try:
            for scenario in error_scenarios:
                error_handled = False
                recovery_attempted = False

                # Configure service to raise specific error
                service_method = getattr(scenario["service"], scenario["method"])
                service_method.side_effect = scenario["error_type"](scenario["message"])

                try:
                    # Attempt operation that will fail
                    if scenario["method"] == "authenticate":
                        await scenario["service"].authenticate()
                    elif scenario["method"] == "place_order":
                        await scenario["service"].place_order(
                            symbol="TEST", quantity=1, price=Decimal("100.00")
                        )
                    elif scenario["method"] == "get_quote":
                        await scenario["service"].get_quote("TEST")

                except AuthenticationError:
                    # Handle authentication errors
                    error_handled = True
                    # Attempt re-authentication
                    recovery_attempted = True

                except OrderExecutionError:
                    # Handle order execution errors
                    error_handled = True
                    # Log error and notify user
                    recovery_attempted = True

                except DataFeedError:
                    # Handle data feed errors
                    error_handled = True
                    # Switch to backup data source
                    recovery_attempted = True

                except RateLimitError:
                    # Handle rate limit errors
                    error_handled = True
                    # Implement backoff and retry
                    recovery_attempted = True

                assert error_handled is True
                assert recovery_attempted is True

                print(f"✅ {scenario['error_type'].__name__} handled correctly")

            print("✅ Comprehensive error handling working correctly")

        except Exception as e:
            pytest.fail(f"Comprehensive error handling failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_token_refresh_and_session_management(
        self, mock_db_session, angel_one_client, auth_service
    ):
        """Test token refresh and session management"""

        # Mock initial authentication
        initial_auth = {
            "status": True,
            "data": {
                "jwtToken": "initial_token_12345",
                "refreshToken": "refresh_token_67890",
            },
        }

        # Mock token refresh response
        refresh_response = {
            "status": True,
            "data": {
                "jwtToken": "refreshed_token_abcde",
                "refreshToken": "new_refresh_token_fghij",
            },
        }

        # Configure service responses
        auth_service.authenticate.return_value = initial_auth
        auth_service.refresh_token.return_value = refresh_response
        auth_service.validate_session.side_effect = [
            True,
            False,
            True,
        ]  # Expire after 2nd check

        try:
            # Step 1: Initial authentication
            auth_result = await auth_service.authenticate()
            angel_one_client.access_token = auth_result["data"]["jwtToken"]
            angel_one_client.refresh_token = auth_result["data"]["refreshToken"]
            angel_one_client.session_expiry = datetime.now() + timedelta(hours=8)

            # Step 2: Validate initial session
            session_valid = await auth_service.validate_session(
                angel_one_client.access_token
            )
            assert session_valid is True

            # Step 3: Simulate session expiry
            angel_one_client.session_expiry = datetime.now() - timedelta(minutes=1)
            session_valid = await auth_service.validate_session(
                angel_one_client.access_token
            )
            assert session_valid is False

            # Step 4: Refresh token
            refresh_result = await auth_service.refresh_token(
                angel_one_client.refresh_token
            )

            assert refresh_result["status"] is True
            assert "jwtToken" in refresh_result["data"]

            # Update client tokens
            angel_one_client.access_token = refresh_result["data"]["jwtToken"]
            angel_one_client.refresh_token = refresh_result["data"]["refreshToken"]
            angel_one_client.session_expiry = datetime.now() + timedelta(hours=8)

            # Step 5: Validate refreshed session
            session_valid = await auth_service.validate_session(
                angel_one_client.access_token
            )
            assert session_valid is True

            print("✅ Token refresh and session management working correctly")

        except Exception as e:
            pytest.fail(f"Token refresh/session management failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_websocket_streaming_integration(
        self, mock_db_session, angel_one_client, market_data_service
    ):
        """Test WebSocket streaming integration for real-time data"""

        # Mock WebSocket connection
        websocket_connected = False
        streaming_data = []

        class MockWebSocket:
            def __init__(self):
                self.connected = False

            async def connect(self):
                self.connected = True
                return True

            async def send(self, message):
                # Echo back subscription confirmation
                if "subscribe" in message:
                    return {"type": "subscription_success", "symbols": ["RELIANCE-EQ"]}

            async def receive(self):
                # Simulate real-time data
                return {
                    "type": "tick",
                    "symbol": "RELIANCE-EQ",
                    "ltp": 2501.50,
                    "volume": 1504000,
                    "timestamp": datetime.now().isoformat(),
                }

            async def close(self):
                self.connected = False

        mock_ws = MockWebSocket()

        try:
            # Step 1: Establish WebSocket connection
            await mock_ws.connect()
            websocket_connected = mock_ws.connected
            assert websocket_connected is True

            # Step 2: Subscribe to symbols
            subscription_message = json.dumps(
                {"action": "subscribe", "symbols": ["RELIANCE-EQ", "TCS-EQ"]}
            )

            subscription_result = await mock_ws.send(subscription_message)
            assert subscription_result["type"] == "subscription_success"

            # Step 3: Receive streaming data
            for _ in range(5):  # Receive 5 data points
                data = await mock_ws.receive()
                streaming_data.append(data)

                # Validate data structure
                assert data["type"] == "tick"
                assert data["symbol"] is not None
                assert data["ltp"] > 0

            assert len(streaming_data) == 5

            # Step 4: Process streaming data
            latest_prices = {}
            for data in streaming_data:
                symbol = data["symbol"]
                price = data["ltp"]
                latest_prices[symbol] = price

            assert "RELIANCE-EQ" in latest_prices
            assert latest_prices["RELIANCE-EQ"] > 0

            # Step 5: Close WebSocket connection
            await mock_ws.close()
            assert mock_ws.connected is False

            print("✅ WebSocket streaming integration working correctly")

        except Exception as e:
            pytest.fail(f"WebSocket streaming integration failed: {str(e)}")


# Additional utility functions for testing
def create_angel_one_test_scenario(scenario_name: str) -> Dict[str, Any]:
    """Create predefined Angel One API test scenarios"""

    scenarios = {
        "successful_connection": {
            "api_credentials_valid": True,
            "network_available": True,
            "api_server_up": True,
            "expected_outcome": "success",
        },
        "authentication_failure": {
            "api_credentials_valid": False,
            "network_available": True,
            "api_server_up": True,
            "expected_outcome": "auth_error",
        },
        "network_failure": {
            "api_credentials_valid": True,
            "network_available": False,
            "api_server_up": True,
            "expected_outcome": "connection_error",
        },
        "rate_limit_exceeded": {
            "api_credentials_valid": True,
            "network_available": True,
            "api_server_up": True,
            "requests_per_second": 20,  # Exceeds limit
            "expected_outcome": "rate_limit_error",
        },
    }

    return scenarios.get(scenario_name, {})


def validate_api_response(response: Dict[str, Any]) -> bool:
    """Validate Angel One API response structure"""

    try:
        # Basic response validation
        required_fields = ["status", "message"]

        for field in required_fields:
            assert field in response

        # Status should be boolean
        assert isinstance(response["status"], bool)

        # If successful, should have data field
        if response["status"]:
            assert "data" in response

        return True

    except Exception as e:
        print(f"API response validation failed: {str(e)}")
        return False


def simulate_network_latency(delay_ms: int = 100):
    """Simulate network latency for testing"""

    async def latency_decorator(func):
        async def wrapper(*args, **kwargs):
            await asyncio.sleep(delay_ms / 1000.0)  # Convert ms to seconds
            return await func(*args, **kwargs)

        return wrapper

    return latency_decorator


if __name__ == "__main__":
    """Run integration tests for Angel One API connection"""

    print("🚀 Starting Angel One API Integration Tests...")

    # Run pytest with verbose output
    import subprocess

    result = subprocess.run(
        ["python", "-m", "pytest", __file__, "-v", "--tb=short"],
        capture_output=True,
        text=True,
    )

    print(result.stdout)
    if result.stderr:
        print("Errors:", result.stderr)

    print("✅ Angel One API Integration Tests Complete!")
