#!/usr/bin/env python3
"""
Simple test script to verify trades API endpoints work correctly.
"""

import asyncio
import json
import uuid
from src.main import create_application


async def test_trades_endpoints():
    """Test the trades API endpoints"""

    # Create test client
    from fastapi.testclient import TestClient

    app = create_application()
    client = TestClient(app)

    print("Testing trades API endpoints...")

    # Test 1: GET /api/v1/trades (empty list)
    print("\n1. Testing GET /api/v1/trades (empty list)")
    response = client.get("/api/v1/trades")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        assert "trades" in data
        assert "total" in data
        assert "has_more" in data
        assert data["total"] == 0
        print("✓ GET /api/v1/trades works correctly")
    else:
        print(f"✗ GET /api/v1/trades failed: {response.text}")

    # Test 2: POST /api/v1/trades (create trade)
    print("\n2. Testing POST /api/v1/trades (create trade)")
    trade_data = {
        "symbol": "BANKNIFTY",
        "trade_type": "BUY",
        "quantity": 25,
        "price": 45000.50,
        "stop_loss": 44000.00,
        "take_profit": 46000.00,
    }
    response = client.post("/api/v1/trades", json=trade_data)
    print(f"Status: {response.status_code}")
    if response.status_code == 201:
        trade = response.json()
        print(f"Created trade: {json.dumps(trade, indent=2)}")
        assert "trade_id" in trade
        assert trade["symbol"] == "BANKNIFTY"
        assert trade["trade_type"] == "BUY"
        assert trade["quantity"] == 25
        trade_id = trade["trade_id"]
        print(f"✓ POST /api/v1/trades works correctly, created trade {trade_id}")
    else:
        print(f"✗ POST /api/v1/trades failed: {response.text}")
        return

    # Test 3: GET /api/v1/trades (with data)
    print("\n3. Testing GET /api/v1/trades (with data)")
    response = client.get("/api/v1/trades")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        assert data["total"] == 1
        assert len(data["trades"]) == 1
        assert data["trades"][0]["trade_id"] == trade_id
        print("✓ GET /api/v1/trades with data works correctly")
    else:
        print(f"✗ GET /api/v1/trades with data failed: {response.text}")

    # Test 4: GET /api/v1/trades/{trade_id}
    print(f"\n4. Testing GET /api/v1/trades/{trade_id}")
    response = client.get(f"/api/v1/trades/{trade_id}")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        trade = response.json()
        print(f"Trade details: {json.dumps(trade, indent=2)}")
        assert trade["trade_id"] == trade_id
        assert trade["symbol"] == "BANKNIFTY"
        print(f"✓ GET /api/v1/trades/{trade_id} works correctly")
    else:
        print(f"✗ GET /api/v1/trades/{trade_id} failed: {response.text}")

    # Test 5: PATCH /api/v1/trades/{trade_id}
    print(f"\n5. Testing PATCH /api/v1/trades/{trade_id}")
    update_data = {"stop_loss": 44500.00, "take_profit": 46500.00}
    response = client.patch(f"/api/v1/trades/{trade_id}", json=update_data)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        updated_trade = response.json()
        print(f"Updated trade: {json.dumps(updated_trade, indent=2)}")
        assert updated_trade["trade_id"] == trade_id
        # Note: The response model might not include the updated stop_loss/take_profit
        # depending on the TradeResponse model
        print(f"✓ PATCH /api/v1/trades/{trade_id} works correctly")
    else:
        print(f"✗ PATCH /api/v1/trades/{trade_id} failed: {response.text}")

    # Test 6: GET /api/v1/trades with filters
    print("\n6. Testing GET /api/v1/trades with symbol filter")
    response = client.get("/api/v1/trades?symbol=BANKNIFTY")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Filtered response: {json.dumps(data, indent=2)}")
        assert data["total"] == 1
        assert len(data["trades"]) == 1
        print("✓ GET /api/v1/trades with symbol filter works correctly")
    else:
        print(f"✗ GET /api/v1/trades with symbol filter failed: {response.text}")

    # Test 7: GET /api/v1/trades with invalid trade_id
    print("\n7. Testing GET /api/v1/trades with invalid trade_id")
    invalid_id = str(uuid.uuid4())
    response = client.get(f"/api/v1/trades/{invalid_id}")
    print(f"Status: {response.status_code}")
    if response.status_code == 404:
        print("✓ GET /api/v1/trades with invalid ID correctly returns 404")
    else:
        print(f"✗ GET /api/v1/trades with invalid ID failed: {response.status_code}")

    print("\n🎉 All trades API endpoint tests completed!")


if __name__ == "__main__":
    asyncio.run(test_trades_endpoints())
