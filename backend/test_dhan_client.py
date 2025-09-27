#!/usr/bin/env python3
"""
Simple test script for Dhan HQ API client
This is a basic validation script to ensure the client can be imported and initialized.
"""

import asyncio
import sys
import os

# Import after path setup to avoid import errors
from src.api.dhan_client import DhanClient, DhanConfig


async def test_dhan_client():
    """Test basic Dhan client functionality"""

    # Test client initialization
    print("Testing Dhan client initialization...")

    try:
        # Initialize with dummy credentials for structure validation
        config = DhanConfig()
        client = DhanClient(
            client_id="test_client_id", access_token="test_access_token", config=config
        )

        print("✅ Client initialized successfully")
        print(f"  - Base URL: {client.config.base_url}")
        print(f"  - Client ID: {client.client_id}")
        print(
            f"  - Rate limits: {client.config.rate_limit_per_second}/sec, {client.config.rate_limit_per_minute}/min"
        )

        # Test client stats
        stats = client.get_client_stats()
        print("✅ Client statistics retrieved")
        print(f"  - Session ID: {stats['session_id']}")
        print(f"  - Authentication status: {stats['is_authenticated']}")

        # Test token validation
        token_valid = client.validate_token()
        print(f"✅ Token validation: {'Valid' if token_valid else 'Invalid'}")

        # Test authentication status
        auth_status = client.get_authentication_status()
        print("✅ Authentication status retrieved")
        print(f"  - Has token: {auth_status['has_token']}")
        print(f"  - Token valid: {auth_status['token_valid']}")

        # Test epoch conversion utility
        epoch_time = 1640995200  # 2022-01-01 00:00:00
        readable_time = client.convert_epoch_to_datetime(epoch_time)
        print(f"✅ Epoch conversion works: {epoch_time} -> {readable_time}")

        # Cleanup
        await client.close()
        print("✅ Client closed successfully")

        print(
            "\n🎉 All basic tests passed! Dhan client structure is working correctly."
        )
        return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


async def test_error_classes():
    """Test custom exception classes"""

    print("\nTesting custom exception classes...")

    try:
        from src.api.dhan_client import DhanError, AuthenticationError, OrderError

        # Test base exception
        base_error = DhanError("Test error", "TEST001", 400, {"test": "data"})
        assert base_error.message == "Test error"
        assert base_error.error_code == "TEST001"
        assert base_error.status_code == 400
        print("✅ DhanError class works")

        # Test specific exceptions
        auth_error = AuthenticationError("Auth failed")
        assert isinstance(auth_error, DhanError)
        print("✅ AuthenticationError class works")

        order_error = OrderError("Order failed")
        assert isinstance(order_error, DhanError)
        print("✅ OrderError class works")

        print("✅ All exception classes working correctly")
        return True

    except Exception as e:
        print(f"❌ Exception class test failed: {e}")
        return False


async def main():
    """Main test function"""
    print("🚀 Starting Dhan HQ API Client Tests\n")

    # Run tests
    test_results = []
    test_results.append(await test_dhan_client())
    test_results.append(await test_error_classes())

    # Summary
    passed = sum(test_results)
    total = len(test_results)

    print(f"\n📊 Test Summary: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! T060 - Dhan HQ API client is ready for use.")
        return 0
    else:
        print("❌ Some tests failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
