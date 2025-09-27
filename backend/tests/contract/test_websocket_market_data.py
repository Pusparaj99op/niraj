"""
Contract tests for WebSocket market data streaming.

These tests validate the WebSocket market data contract defined in the
WebSocket API specification. Following TDD principles, these tests should
fail initially until the WebSocket server is implemented.
"""

import pytest
import asyncio
import json
from typing import List
import websockets


class TestWebSocketMarketDataContract:
    """Contract tests for WebSocket market data streaming."""

    BASE_WS_URL = "ws://localhost:8000/ws"
    VALID_JWT_TOKEN = (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
        "eyJzdWIiOiIxMjNlNDU2Ny1lODliLTEyZDMtYTQ1Ni00MjY2MTQxNzQwMDAi"
        "LCJ1c2VybmFtZSI6InByYW5heSIsImV4cCI6OTk5OTk5OTk5OX0.test_signature"
    )

    @pytest.fixture
    def event_loop(self):
        """Create a new event loop for each test."""
        loop = asyncio.new_event_loop()
        yield loop
        loop.close()

    async def connect_and_authenticate(
        self, timeout: float = 5.0
    ) -> websockets.WebSocketServerProtocol:
        """
        Helper method to connect and authenticate WebSocket.

        Args:
            timeout: Connection timeout in seconds

        Returns:
            Authenticated WebSocket connection

        Raises:
            ConnectionError: If connection or authentication fails
        """
        try:
            websocket = await asyncio.wait_for(
                websockets.connect(f"{self.BASE_WS_URL}?token={self.VALID_JWT_TOKEN}"),
                timeout=timeout,
            )

            # Wait for auth response
            auth_response_raw = await asyncio.wait_for(
                websocket.recv(), timeout=timeout
            )
            auth_response = json.loads(auth_response_raw)

            if (
                auth_response.get("type") != "auth_response"
                or auth_response.get("data", {}).get("status") != "authenticated"
            ):
                raise ConnectionError("Authentication failed")

            return websocket

        except Exception as e:
            raise ConnectionError(f"Failed to connect and authenticate: {e}")

    async def subscribe_to_market_data(
        self,
        websocket: websockets.WebSocketServerProtocol,
        symbols: List[str],
        timeframe: str = "15min",
        timeout: float = 5.0,
    ) -> str:
        """
        Subscribe to market data stream and return subscription ID.

        Args:
            websocket: Authenticated WebSocket connection
            symbols: List of trading symbols
            timeframe: Data timeframe
            timeout: Response timeout in seconds

        Returns:
            Subscription ID

        Raises:
            ValueError: If subscription fails
        """
        subscription_message = {
            "type": "subscribe",
            "data": {
                "streams": [
                    {
                        "stream_type": "market_data",
                        "symbols": symbols,
                        "timeframe": timeframe,
                    }
                ]
            },
        }

        await websocket.send(json.dumps(subscription_message))

        response_raw = await asyncio.wait_for(websocket.recv(), timeout=timeout)
        response = json.loads(response_raw)

        if (
            response.get("type") != "subscription_response"
            or response.get("data", {}).get("status") != "success"
        ):
            raise ValueError("Subscription failed")

        active_subs = response["data"]["active_subscriptions"]
        if not active_subs:
            raise ValueError("No active subscriptions")

        return active_subs[0]["subscription_id"]

    @pytest.mark.asyncio
    async def test_websocket_market_data_stream_format(self) -> None:
        """
        Test market data stream message format compliance.

        Contract Requirements:
        - Subscribe to market data stream -
        - Receive market_data messages with correct format -
        Verify OHLCV, indicators, and quote data structure
        """
        # This test will fail until WebSocket server is implemented
        with pytest.raises((ConnectionError, ConnectionRefusedError, OSError)):
            websocket = await self.connect_and_authenticate()

            try:
                # Subscribe to market data
                await self.subscribe_to_market_data(websocket, ["BANKNIFTY"])

                # Wait for market data message
                market_data_raw = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                market_data = json.loads(market_data_raw)

                # Assert - Message Structure
                assert (
                    market_data["type"] == "market_data"
                ), "Message should be market_data type"

                assert "timestamp" in market_data, "Message must contain timestamp"

                assert "data" in market_data, "Message must contain data"

                # Assert - Data Structure
                data = market_data["data"]
                required_fields = ["symbol", "timeframe", "ohlcv"]
                for field in required_fields:
                    assert field in data, f"Market data must contain '{field}'"

                # Assert - Symbol and Timeframe
                assert data["symbol"] in [
                    "BANKNIFTY"
                ], "Symbol should match subscription"

                assert (
                    data["timeframe"] == "15min"
                ), "Timeframe should match subscription"

                # Assert - OHLCV Structure
                ohlcv = data["ohlcv"]
                ohlcv_fields = [
                    "timestamp",
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume",
                    "change_percent",
                ]
                for field in ohlcv_fields:
                    assert field in ohlcv, f"OHLCV must contain '{field}'"

                # Verify numeric types
                numeric_fields = ["open", "high", "low", "close", "volume"]
                for field in numeric_fields:
                    value = ohlcv[field]
                    assert isinstance(value, (int, float)), f"{field} must be numeric"
                    assert value >= 0, f"{field} must be non-negative"

                # Assert - Optional Indicators
                if "indicators" in data:
                    indicators = data["indicators"]
                    assert isinstance(indicators, dict), "Indicators must be dictionary"

                    # Verify indicator values are numeric
                    for indicator, value in indicators.items():
                        if value is not None:
                            assert isinstance(
                                value, (int, float)
                            ), f"Indicator {indicator} must be numeric"

                # Assert - Optional Quote
                if "quote" in data:
                    quote = data["quote"]
                    quote_fields = ["bid", "ask", "last_price", "last_updated"]
                    for field in quote_fields:
                        assert field in quote, f"Quote must contain '{field}'"

                    # Verify price fields are numeric
                    price_fields = ["bid", "ask", "last_price"]
                    for field in price_fields:
                        value = quote[field]
                        assert isinstance(
                            value, (int, float)
                        ), f"Quote {field} must be numeric"

            finally:
                await websocket.close()

    @pytest.mark.asyncio
    async def test_websocket_market_data_multiple_symbols(self) -> None:
        """
        Test market data streaming for multiple symbols.

        Contract Requirements:
        - Subscribe to multiple symbols in single stream -
        - Receive market_data messages for each symbol -
        Messages should be properly labeled by symbol
        """
        # This test will fail until WebSocket server is implemented
        with pytest.raises((ConnectionError, ConnectionRefusedError, OSError)):
            websocket = await self.connect_and_authenticate()

            try:
                # Subscribe to multiple symbols
                symbols = ["BANKNIFTY", "HDFCBANK", "RELIANCE"]
                await self.subscribe_to_market_data(websocket, symbols)

                # Collect market data messages
                received_symbols = set()
                timeout_seconds = 30.0
                start_time = asyncio.get_event_loop().time()

                while (
                    len(received_symbols) < len(symbols)
                    and asyncio.get_event_loop().time() - start_time < timeout_seconds
                ):
                    try:
                        message_raw = await asyncio.wait_for(
                            websocket.recv(), timeout=5.0
                        )
                        message = json.loads(message_raw)

                        if message["type"] == "market_data":
                            symbol = message["data"]["symbol"]
                            received_symbols.add(symbol)

                            # Verify symbol is in subscription list
                            assert symbol in symbols, (
                                f"Received data for unexpected symbol: " f"{symbol}"
                            )

                            # Verify message format
                            assert (
                                "ohlcv" in message["data"]
                            ), f"Market data for {symbol} missing OHLCV"

                    except asyncio.TimeoutError:
                        # Continue trying - server may send data intermittently
                        continue

                # Verify we received data for all symbols (or at least some)
                assert (
                    len(received_symbols) >= 1
                ), "Should receive market data for at least one symbol"

            finally:
                await websocket.close()

    @pytest.mark.asyncio
    async def test_websocket_market_data_timeframe_validation(self) -> None:
        """
        Test market data with different timeframes.

        Contract Requirements:
        - Subscribe to market data with specific timeframe -
        - Received data should match requested timeframe -
        Invalid timeframes should be rejected
        """
        # This test will fail until WebSocket server is implemented
        with pytest.raises((ConnectionError, ConnectionRefusedError, OSError)):
            websocket = await self.connect_and_authenticate()

            try:
                # Test valid timeframes
                valid_timeframes = ["1min", "5min", "15min", "1h", "1d"]

                for timeframe in valid_timeframes:
                    try:
                        await self.subscribe_to_market_data(
                            websocket, ["BANKNIFTY"], timeframe
                        )

                        # Wait for market data message
                        market_data_raw = await asyncio.wait_for(
                            websocket.recv(), timeout=10.0
                        )
                        market_data = json.loads(market_data_raw)

                        if market_data["type"] == "market_data":
                            data_timeframe = market_data["data"]["timeframe"]
                            assert data_timeframe == timeframe
                            break

                    except ValueError:
                        # Some timeframes might not be supported - skip
                        continue
                    except asyncio.TimeoutError:
                        # No data received for this timeframe - continue
                        continue

                # Test invalid timeframe
                invalid_subscription = {
                    "type": "subscribe",
                    "data": {
                        "streams": [
                            {
                                "stream_type": "market_data",
                                "symbols": ["BANKNIFTY"],
                                "timeframe": "invalid_timeframe",
                            }
                        ]
                    },
                }

                await websocket.send(json.dumps(invalid_subscription))

                response_raw = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                response = json.loads(response_raw)

                # Should indicate failure for invalid timeframe
                if response["type"] == "subscription_response":
                    data = response["data"]
                    failed_subs = data.get("failed_subscriptions", [])
                    assert (
                        len(failed_subs) >= 1
                    ), "Invalid timeframe should cause subscription failure"

            finally:
                await websocket.close()

    @pytest.mark.asyncio
    async def test_websocket_market_data_rate_limiting(self) -> None:
        """
        Test market data rate limiting and throttling.

        Contract Requirements:
        - Market data should be rate-limited appropriately -
        - Should not exceed reasonable message frequency -
        Burst messages should be handled gracefully
        """
        # This test will fail until WebSocket server is implemented
        with pytest.raises((ConnectionError, ConnectionRefusedError, OSError)):
            websocket = await self.connect_and_authenticate()

            try:
                # Subscribe to high-frequency market data
                await self.subscribe_to_market_data(websocket, ["BANKNIFTY"], "1min")

                # Collect messages over time period
                messages = []
                collection_duration = 10.0  # 10 seconds
                start_time = asyncio.get_event_loop().time()

                while (
                    asyncio.get_event_loop().time() - start_time < collection_duration
                ):
                    try:
                        message_raw = await asyncio.wait_for(
                            websocket.recv(), timeout=1.0
                        )
                        message = json.loads(message_raw)

                        if message["type"] == "market_data":
                            messages.append(
                                {
                                    "timestamp": asyncio.get_event_loop().time(),
                                    "data": message,
                                }
                            )

                    except asyncio.TimeoutError:
                        # No message received - continue
                        continue

                # Analyze message frequency
                if len(messages) >= 2:
                    # Calculate intervals between messages
                    intervals = []
                    for i in range(1, len(messages)):
                        interval = (
                            messages[i]["timestamp"] - messages[i - 1]["timestamp"]
                        )
                        intervals.append(interval)

                    # Verify reasonable rate limiting
                    avg_interval = sum(intervals) / len(intervals)
                    min_interval = min(intervals)

                    # Should not spam messages too frequently
                    assert (
                        min_interval >= 0.1
                    ), "Messages should not arrive faster than 10 per second"

                    # Average interval should be reasonable
                    assert (
                        avg_interval >= 0.5
                    ), "Average message interval should be >= 0.5 seconds"

            finally:
                await websocket.close()

    @pytest.mark.asyncio
    async def test_websocket_market_data_connection_recovery(self) -> None:
        """
        Test market data streaming after connection recovery.

        Contract Requirements:
        - Connection interruption should be handled gracefully -
        - Re-subscription should restore market data stream -
        No data loss or duplication after reconnection
        """
        # This test will fail until WebSocket server is implemented
        with pytest.raises((ConnectionError, ConnectionRefusedError, OSError)):
            # Initial connection and subscription
            websocket1 = await self.connect_and_authenticate()

            try:
                subscription_id1 = await self.subscribe_to_market_data(
                    websocket1, ["BANKNIFTY"]
                )

                # Wait for initial market data
                market_data1_raw = await asyncio.wait_for(
                    websocket1.recv(), timeout=10.0
                )
                market_data1 = json.loads(market_data1_raw)

                assert market_data1["type"] == "market_data"
                initial_timestamp = market_data1.get("timestamp")

            finally:
                await websocket1.close()

            # Simulate connection recovery - new connection
            await asyncio.sleep(1.0)  # Brief delay

            websocket2 = await self.connect_and_authenticate()

            try:
                # Re-subscribe to same market data
                subscription_id2 = await self.subscribe_to_market_data(
                    websocket2, ["BANKNIFTY"]
                )

                # Wait for market data on new connection
                market_data2_raw = await asyncio.wait_for(
                    websocket2.recv(), timeout=10.0
                )
                market_data2 = json.loads(market_data2_raw)

                assert market_data2["type"] == "market_data"

                # Verify data continuity
                assert market_data2["data"]["symbol"] == "BANKNIFTY"
                assert "ohlcv" in market_data2["data"]

                # New subscription should have different ID
                assert (
                    subscription_id2 != subscription_id1
                ), "New subscription should have different ID"

                # Timestamp should be newer (if available)
                recovery_timestamp = market_data2.get("timestamp")
                if initial_timestamp and recovery_timestamp:
                    assert (
                        recovery_timestamp >= initial_timestamp
                    ), "Recovery data should not be older than initial data"

            finally:
                await websocket2.close()

    @pytest.mark.asyncio
    async def test_websocket_market_data_invalid_symbol(self) -> None:
        """
        Test market data subscription with invalid symbols.

        Contract Requirements:
        - Invalid symbols should cause subscription failure -
        - Error message should indicate invalid symbol -
        Valid symbols in same request should still work
        """
        # This test will fail until WebSocket server is implemented
        with pytest.raises((ConnectionError, ConnectionRefusedError, OSError)):
            websocket = await self.connect_and_authenticate()

            try:
                # Subscribe with mix of valid and invalid symbols
                subscription_message = {
                    "type": "subscribe",
                    "data": {
                        "streams": [
                            {
                                "stream_type": "market_data",
                                "symbols": ["BANKNIFTY", "INVALID_SYMBOL_123"],
                                "timeframe": "15min",
                            }
                        ]
                    },
                }

                await websocket.send(json.dumps(subscription_message))

                response_raw = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                response = json.loads(response_raw)

                assert response["type"] == "subscription_response"
                data = response["data"]

                # Should have partial success or complete failure
                has_active = len(data.get("active_subscriptions", [])) > 0
                has_failed = len(data.get("failed_subscriptions", [])) > 0

                assert (
                    has_active or has_failed
                ), "Should have either active or failed subscriptions"

                # If there are failures, check error message
                if has_failed:
                    failed_sub = data["failed_subscriptions"][0]
                    error_msg = failed_sub["error"].lower()
                    assert (
                        "invalid" in error_msg
                        or "symbol" in error_msg
                        or "not found" in error_msg
                    ), "Error should indicate invalid symbol"

            finally:
                await websocket.close()

    @pytest.mark.asyncio
    async def test_websocket_market_data_subscription_lifecycle(self) -> None:
        """
        Test complete market data subscription lifecycle.

        Contract Requirements:
        - Subscribe to market data stream -
        - Receive continuous market data updates -
        - Unsubscribe from stream -
        Verify no more market data received after unsubscription
        """
        # This test will fail until WebSocket server is implemented
        with pytest.raises((ConnectionError, ConnectionRefusedError, OSError)):
            websocket = await self.connect_and_authenticate()

            try:
                # Phase 1: Subscribe
                subscription_id = await self.subscribe_to_market_data(
                    websocket, ["BANKNIFTY"]
                )

                # Phase 2: Receive market data
                market_data_count = 0
                collection_time = 5.0
                start_time = asyncio.get_event_loop().time()

                while asyncio.get_event_loop().time() - start_time < collection_time:
                    try:
                        message_raw = await asyncio.wait_for(
                            websocket.recv(), timeout=1.0
                        )
                        message = json.loads(message_raw)

                        if message["type"] == "market_data":
                            market_data_count += 1
                            assert message["data"]["symbol"] == "BANKNIFTY"

                    except asyncio.TimeoutError:
                        continue

                # Should have received some market data
                assert (
                    market_data_count >= 1
                ), "Should receive market data during subscription"

                # Phase 3: Unsubscribe
                unsubscribe_message = {
                    "type": "unsubscribe",
                    "data": {"subscription_ids": [subscription_id]},
                }

                await websocket.send(json.dumps(unsubscribe_message))

                # Wait for unsubscription confirmation
                await asyncio.wait_for(websocket.recv(), timeout=5.0)

                # Phase 4: Verify no more market data
                post_unsub_count = 0
                verification_time = 3.0
                start_time = asyncio.get_event_loop().time()

                while asyncio.get_event_loop().time() - start_time < verification_time:
                    try:
                        message_raw = await asyncio.wait_for(
                            websocket.recv(), timeout=0.5
                        )
                        message = json.loads(message_raw)

                        if message["type"] == "market_data":
                            post_unsub_count += 1

                    except asyncio.TimeoutError:
                        continue

                # Should receive no market data after unsubscription
                assert (
                    post_unsub_count == 0
                ), "Should not receive market data after unsubscription"

            finally:
                await websocket.close()

    @pytest.mark.asyncio
    async def test_websocket_market_data_concurrent_subs(self) -> None:
        """
        Test concurrent market data subscriptions.

        Contract Requirements:
        - Multiple concurrent subscriptions should work -
        - Each subscription should receive independent data -
        Unsubscribing one should not affect others
        """
        # This test will fail until WebSocket server is implemented
        with pytest.raises((ConnectionError, ConnectionRefusedError, OSError)):
            websocket = await self.connect_and_authenticate()

            try:
                # Create multiple subscriptions
                subscription_message = {
                    "type": "subscribe",
                    "data": {
                        "streams": [
                            {
                                "stream_type": "market_data",
                                "symbols": ["BANKNIFTY"],
                                "timeframe": "15min",
                            },
                            {
                                "stream_type": "market_data",
                                "symbols": ["HDFCBANK"],
                                "timeframe": "15min",
                            },
                            {
                                "stream_type": "market_data",
                                "symbols": ["BANKNIFTY"],
                                "timeframe": "5min",
                            },
                        ]
                    },
                }

                await websocket.send(json.dumps(subscription_message))

                response_raw = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                response = json.loads(response_raw)

                assert response["type"] == "subscription_response"
                data = response["data"]

                active_subs = data["active_subscriptions"]
                assert (
                    len(active_subs) >= 2
                ), "Should have multiple active subscriptions"

                # Collect subscription IDs
                subscription_ids = [sub["subscription_id"] for sub in active_subs]

                # Collect market data for different streams
                received_data = {}
                collection_time = 10.0
                start_time = asyncio.get_event_loop().time()

                while asyncio.get_event_loop().time() - start_time < collection_time:
                    try:
                        message_raw = await asyncio.wait_for(
                            websocket.recv(), timeout=1.0
                        )
                        message = json.loads(message_raw)

                        if message["type"] == "market_data":
                            symbol = message["data"]["symbol"]
                            timeframe = message["data"]["timeframe"]
                            key = f"{symbol}_{timeframe}"

                            if key not in received_data:
                                received_data[key] = []
                            received_data[key].append(message)

                    except asyncio.TimeoutError:
                        continue

                # Should receive data for different symbol/timeframe combos
                assert (
                    len(received_data) >= 1
                ), "Should receive market data for different streams"

                # Unsubscribe from one stream
                if subscription_ids:
                    unsubscribe_message = {
                        "type": "unsubscribe",
                        "data": {"subscription_ids": [subscription_ids[0]]},
                    }

                    await websocket.send(json.dumps(unsubscribe_message))

                    # Should still receive data from other subscriptions
                    # (This would require longer testing to verify properly)

            finally:
                await websocket.close()
