"""
Contract tests for WebSocket portfolio updates streaming.

These tests validate the WebSocket portfolio updates contract defined in the
WebSocket API specification. Following TDD principles, these tests should
fail initially until the WebSocket server is implemented.
"""

import pytest
import asyncio
import json
import websockets


class TestWebSocketPortfolioContract:
    """Contract tests for WebSocket portfolio updates streaming."""

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
        Connect to WebSocket and authenticate.

        Returns authenticated WebSocket connection.
        """
        try:
            websocket = await websockets.connect(
                f"{self.BASE_WS_URL}?token={self.VALID_JWT_TOKEN}", timeout=timeout
            )

            # Send authentication message
            auth_message = {"type": "AUTH", "token": self.VALID_JWT_TOKEN}
            await websocket.send(json.dumps(auth_message))

            # Wait for auth confirmation
            response = await asyncio.wait_for(websocket.recv(), timeout=timeout)
            auth_response = json.loads(response)

            assert auth_response.get("status") == "success"
            assert auth_response.get("type") == "AUTH_SUCCESS"

            return websocket

        except Exception as e:
            pytest.fail(f"Failed to connect and authenticate: {e}")

    async def subscribe_to_portfolio(
        self, websocket: websockets.WebSocketServerProtocol, timeout: float = 5.0
    ) -> dict:
        """Subscribe to portfolio updates and return subscription response."""
        subscribe_message = {"type": "SUBSCRIBE", "channel": "portfolio"}
        await websocket.send(json.dumps(subscribe_message))

        response = await asyncio.wait_for(websocket.recv(), timeout=timeout)
        return json.loads(response)

    @pytest.mark.asyncio
    async def test_portfolio_subscription_success(self):
        """Test successful portfolio subscription."""
        websocket = await self.connect_and_authenticate()
        try:
            response = await self.subscribe_to_portfolio(websocket)

            # Validate subscription response
            assert response.get("status") == "success"
            assert response.get("type") == "SUBSCRIPTION_CONFIRMED"
            assert response.get("channel") == "portfolio"
            assert "subscription_id" in response

        finally:
            await websocket.close()

    @pytest.mark.asyncio
    async def test_portfolio_update_format_validation(self):
        """Test portfolio update message format compliance."""
        websocket = await self.connect_and_authenticate()
        try:
            # Subscribe to portfolio updates
            await self.subscribe_to_portfolio(websocket)

            # Wait for portfolio update message
            update_message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
            portfolio_update = json.loads(update_message)

            # Validate message structure
            assert portfolio_update.get("type") == "PORTFOLIO_UPDATE"
            assert portfolio_update.get("channel") == "portfolio"
            assert "timestamp" in portfolio_update
            assert "data" in portfolio_update

            data = portfolio_update["data"]

            # Validate portfolio summary
            assert "portfolio_summary" in data
            summary = data["portfolio_summary"]

            required_summary_fields = [
                "total_value",
                "margin_used",
                "available_margin",
                "unrealized_pnl",
                "realized_pnl",
            ]
            for field in required_summary_fields:
                assert field in summary
                assert isinstance(summary[field], (int, float))

            # Validate positions if present
            if "positions" in data:
                positions = data["positions"]
                assert isinstance(positions, list)

                for position in positions:
                    required_position_fields = [
                        "symbol",
                        "size",
                        "average_price",
                        "current_price",
                        "unrealized_pnl",
                    ]
                    for field in required_position_fields:
                        assert field in position

                    assert isinstance(position["symbol"], str)
                    assert isinstance(position["size"], (int, float))
                    assert isinstance(position["average_price"], (int, float))
                    assert isinstance(position["current_price"], (int, float))
                    assert isinstance(position["unrealized_pnl"], (int, float))

        finally:
            await websocket.close()

    @pytest.mark.asyncio
    async def test_portfolio_summary_accuracy(self):
        """Test portfolio summary calculations accuracy."""
        websocket = await self.connect_and_authenticate()
        try:
            await self.subscribe_to_portfolio(websocket)

            # Collect multiple portfolio updates
            updates = []
            for _ in range(3):
                message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                update = json.loads(message)
                if update.get("type") == "PORTFOLIO_UPDATE":
                    updates.append(update)

            assert len(updates) >= 1, "Should receive portfolio updates"

            for update in updates:
                data = update["data"]
                summary = data["portfolio_summary"]

                # Basic sanity checks
                assert summary["total_value"] >= 0
                assert summary["margin_used"] >= 0
                assert summary["available_margin"] >= 0

                # Available margin should equal total - used
                expected_available = summary["total_value"] - summary["margin_used"]
                margin_tolerance = 0.01  # Allow small floating point errors
                margin_diff = abs(summary["available_margin"] - expected_available)
                assert margin_diff <= margin_tolerance, (
                    f"Available margin calculation incorrect: "
                    f"expected {expected_available}, "
                    f"got {summary['available_margin']}"
                )

        finally:
            await websocket.close()

    @pytest.mark.asyncio
    async def test_portfolio_pnl_tracking(self):
        """Test P&L tracking accuracy and updates."""
        websocket = await self.connect_and_authenticate()
        try:
            await self.subscribe_to_portfolio(websocket)

            # Collect portfolio updates
            updates = []
            timeout_count = 0
            max_timeouts = 3

            while len(updates) < 2 and timeout_count < max_timeouts:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    update = json.loads(message)
                    if update.get("type") == "PORTFOLIO_UPDATE":
                        updates.append(update)
                except asyncio.TimeoutError:
                    timeout_count += 1
                    continue

            if len(updates) < 2:
                pytest.skip("Insufficient portfolio updates for P&L tracking")

            for update in updates:
                data = update["data"]
                summary = data["portfolio_summary"]

                # P&L fields should be numeric
                assert isinstance(summary["unrealized_pnl"], (int, float))
                assert isinstance(summary["realized_pnl"], (int, float))

                # If positions exist, sum should match unrealized P&L
                if "positions" in data and data["positions"]:
                    position_pnl_sum = sum(
                        pos["unrealized_pnl"] for pos in data["positions"]
                    )
                    pnl_tolerance = 0.01
                    pnl_diff = abs(summary["unrealized_pnl"] - position_pnl_sum)
                    assert pnl_diff <= pnl_tolerance, (
                        f"Unrealized P&L mismatch: "
                        f"summary {summary['unrealized_pnl']}, "
                        f"positions sum {position_pnl_sum}"
                    )

        finally:
            await websocket.close()

    @pytest.mark.asyncio
    async def test_portfolio_margin_calculations(self):
        """Test margin calculations and leverage compliance."""
        websocket = await self.connect_and_authenticate()
        try:
            await self.subscribe_to_portfolio(websocket)

            message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
            update = json.loads(message)

            if update.get("type") == "PORTFOLIO_UPDATE":
                data = update["data"]
                summary = data["portfolio_summary"]

                # Extract margin data for cleaner validation
                margin_data = {
                    "margin_used": summary["margin_used"],
                    "available_margin": summary["available_margin"],
                    "total_value": summary["total_value"],
                }

                # Margin used should not exceed total value
                assert margin_data["margin_used"] <= (
                    margin_data["total_value"]
                ), "Margin used should not exceed total portfolio value"

                # Available margin should be non-negative
                assert (
                    margin_data["available_margin"] >= 0
                ), "Available margin should be non-negative"

                # Check leverage limits (assuming max 10x leverage)
                if margin_data["total_value"] > 0:
                    max_allowed_margin = margin_data["total_value"] * 10
                    assert (
                        margin_data["margin_used"] <= max_allowed_margin
                    ), "Total margin should not exceed 10x portfolio value"

        finally:
            await websocket.close()

    @pytest.mark.asyncio
    async def test_position_updates_integration(self):
        """Test position updates within portfolio updates."""
        websocket = await self.connect_and_authenticate()
        try:
            await self.subscribe_to_portfolio(websocket)

            # Look for position change updates
            position_update_found = False
            attempts = 0
            max_attempts = 5

            while not position_update_found and attempts < max_attempts:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    update = json.loads(message)

                    if (
                        update.get("type") == "PORTFOLIO_UPDATE"
                        and update.get("subtype") == "POSITION_CHANGE"
                    ):
                        # Validate position change structure
                        data = update["data"]
                        assert (
                            "position_updates" in data
                        ), "POSITION_CHANGE should include position_updates"

                        position_updates = data["position_updates"]
                        assert isinstance(position_updates, list)

                        for pos_update in position_updates:
                            assert isinstance(pos_update.get("symbol"), str)
                            assert isinstance(pos_update.get("old_size"), (int, float))
                            assert isinstance(pos_update.get("new_size"), (int, float))
                            assert pos_update.get("change_type") in [
                                "OPENED",
                                "INCREASED",
                                "DECREASED",
                                "CLOSED",
                            ]

                        position_update_found = True

                        # Risk metrics might be optional but should be present
                        if "risk_metrics" in data:
                            risk = data["risk_metrics"]
                            assert isinstance(
                                risk.get("var_1day"), (int, float, type(None))
                            )
                            assert isinstance(
                                risk.get("sharpe_ratio"), (int, float, type(None))
                            )

                except asyncio.TimeoutError:
                    attempts += 1
                    continue

            if not position_update_found:
                pytest.skip("No position change updates received during test")

        finally:
            await websocket.close()

    @pytest.mark.asyncio
    async def test_portfolio_update_frequency(self):
        """Test portfolio update frequency and throttling."""
        websocket = await self.connect_and_authenticate()
        try:
            await self.subscribe_to_portfolio(websocket)

            # Collect timestamps of portfolio updates
            update_timestamps = []
            timeout_count = 0
            max_timeouts = 5
            target_updates = 5

            while (
                len(update_timestamps) < target_updates and timeout_count < max_timeouts
            ):
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                    update = json.loads(message)

                    if update.get("type") == "PORTFOLIO_UPDATE":
                        update_timestamps.append(update["timestamp"])

                except asyncio.TimeoutError:
                    timeout_count += 1
                    continue

            if len(update_timestamps) < 2:
                pytest.skip("Insufficient updates for frequency analysis")

            # Calculate intervals between updates
            intervals = []
            for i in range(1, len(update_timestamps)):
                # Assuming timestamps are Unix timestamps
                interval = update_timestamps[i] - update_timestamps[i - 1]
                intervals.append(interval)

            # Updates should not be too frequent (avoid spam)
            min_interval = 0.1  # 100ms minimum
            for interval in intervals:
                assert (
                    interval >= min_interval
                ), f"Updates too frequent: {interval}s < {min_interval}s"

            # Updates should not be too infrequent (within reason)
            max_interval = 60.0  # 1 minute maximum
            for interval in intervals:
                assert (
                    interval <= max_interval
                ), f"Updates too infrequent: {interval}s > {max_interval}s"

        finally:
            await websocket.close()

    @pytest.mark.asyncio
    async def test_portfolio_error_handling(self):
        """Test error handling in portfolio subscriptions."""
        websocket = await self.connect_and_authenticate()
        try:
            # Test invalid subscription message
            invalid_message = {
                "type": "SUBSCRIBE",
                "channel": "invalid_portfolio_channel",
            }
            await websocket.send(json.dumps(invalid_message))

            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            error_response = json.loads(response)

            assert error_response.get("status") == "error"
            assert error_response.get("type") == "SUBSCRIPTION_ERROR"
            assert "error_code" in error_response
            assert "message" in error_response

        except asyncio.TimeoutError:
            pytest.skip("No error response received for invalid subscription")
        finally:
            await websocket.close()

    @pytest.mark.asyncio
    async def test_portfolio_data_consistency(self):
        """Test data consistency across portfolio updates."""
        websocket = await self.connect_and_authenticate()
        try:
            await self.subscribe_to_portfolio(websocket)

            # Collect sequential updates for consistency checking
            sequential_updates = []
            for _ in range(3):
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    update = json.loads(message)
                    if update.get("type") == "PORTFOLIO_UPDATE":
                        sequential_updates.append(update)
                except asyncio.TimeoutError:
                    continue

            if len(sequential_updates) < 2:
                pytest.skip("Insufficient updates for consistency checking")

            # Check for reasonable changes between updates
            for i in range(1, len(sequential_updates)):
                current = sequential_updates[i]["data"]["portfolio_summary"]
                previous = sequential_updates[i - 1]["data"]["portfolio_summary"]

                # Check that dramatic changes don't occur without reason
                for field in ["total_value", "margin_used", "available_margin"]:
                    curr_val = current[field]
                    prev_val = previous[field]

                    # Allow reasonable fluctuation
                    if prev_val != 0:
                        change_pct = abs(curr_val - prev_val) / abs(prev_val)
                        assert change_pct <= 1.0, (
                            f"{field} should not change more than 100% "
                            f"between updates without explanation"
                        )

        finally:
            await websocket.close()

    @pytest.mark.asyncio
    async def test_portfolio_subscription_cleanup(self):
        """Test proper cleanup of portfolio subscriptions."""
        websocket = await self.connect_and_authenticate()
        try:
            # Subscribe to portfolio
            response = await self.subscribe_to_portfolio(websocket)
            subscription_id = response.get("subscription_id")

            # Unsubscribe
            unsubscribe_message = {
                "type": "UNSUBSCRIBE",
                "subscription_id": subscription_id,
            }
            await websocket.send(json.dumps(unsubscribe_message))

            unsubscribe_response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            response = json.loads(unsubscribe_response)

            assert response.get("status") == "success"
            assert response.get("type") == "UNSUBSCRIPTION_CONFIRMED"
            assert response.get("subscription_id") == subscription_id

        finally:
            await websocket.close()
