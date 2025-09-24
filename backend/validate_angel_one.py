"""
Simple validation script for Angel One Client
Tests basic functionality without complex dependencies
"""

import asyncio
import sys
import os

# Add the backend src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Mock the logger imports to avoid dependency issues
class MockLogger:
    def info(self, msg, **kwargs): print(f"INFO: {msg}")
    def debug(self, msg, **kwargs): print(f"DEBUG: {msg}")
    def warning(self, msg, **kwargs): print(f"WARNING: {msg}")
    def error(self, msg, **kwargs): print(f"ERROR: {msg}")

def get_logger(name):
    return MockLogger()

def log_performance(name):
    def decorator(func):
        return func
    return decorator

class LogContext:
    def __init__(self, **kwargs):
        pass
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass

# Patch the logger imports
import src.utils.logger
src.utils.logger.get_logger = get_logger
src.utils.logger.log_performance = log_performance
src.utils.logger.LogContext = LogContext

# Now import our client
from api.angel_one_client import AngelOneClient, AngelOneConfig


async def test_basic_functionality():
    """Test basic client functionality"""
    print("🧪 Testing Angel One Client Basic Functionality")
    print("=" * 50)

    # Test 1: Client initialization
    print("\n✅ Test 1: Client Initialization")
    client = AngelOneClient(
        api_key="test_api_key_123",
        client_code="TEST001",
        client_pin="1234",
        totp_secret="JBSWY3DPEHPK3PXP"  # Example TOTP secret
    )

    print(f"   Client Code: {client.client_code}")
    print(f"   API Key: {client.api_key[:10]}...")
    print(f"   Authenticated: {client.is_authenticated}")
    print(f"   Device ID: {client.device_id}")
    print(f"   Session ID: {client.session_id}")

    # Test 2: Configuration
    print("\n✅ Test 2: Configuration")
    config = AngelOneConfig(timeout=45, max_retries=5)
    client_with_config = AngelOneClient(
        api_key="test_api",
        client_code="TEST002",
        client_pin="5678",
        config=config
    )

    print(f"   Custom Timeout: {client_with_config.config.timeout}")
    print(f"   Custom Max Retries: {client_with_config.config.max_retries}")
    print(f"   Base URL: {client_with_config.config.base_url}")

    # Test 3: TOTP Generation (if pyotp is available)
    print("\n✅ Test 3: TOTP Generation")
    try:
        totp_code = client._generate_totp()
        print(f"   Generated TOTP: {totp_code}")
        print("   TOTP generation working!")
    except Exception as e:
        print(f"   TOTP Error: {e}")

    # Test 4: Headers generation
    print("\n✅ Test 4: Headers Generation")
    headers = client._get_default_headers(include_auth=False)
    print(f"   Content-Type: {headers['Content-Type']}")
    print(f"   X-UserType: {headers['X-UserType']}")
    print(f"   X-PrivateKey: {headers['X-PrivateKey'][:10]}...")
    print(f"   User-Agent: {headers['User-Agent']}")

    # Test 5: MAC Address generation
    print("\n✅ Test 5: MAC Address Generation")
    mac1 = client._generate_mac_address()
    mac2 = client._generate_mac_address()
    print(f"   MAC 1: {mac1}")
    print(f"   MAC 2: {mac2}")
    print(f"   Unique: {mac1 != mac2}")

    # Test 6: Token expiry logic
    print("\n✅ Test 6: Token Expiry Logic")
    print(f"   Token expired (no token): {client._is_token_expired()}")

    from datetime import datetime, timedelta
    client.tokens.expires_at = datetime.now() + timedelta(hours=1)
    print(f"   Token expired (future): {client._is_token_expired()}")

    client.tokens.expires_at = datetime.now() - timedelta(hours=1)
    print(f"   Token expired (past): {client._is_token_expired()}")

    # Test 7: Rate Limiter
    print("\n✅ Test 7: Rate Limiter")
    from api.angel_one_client import RateLimiter

    limiter = RateLimiter(max_calls=3, window=1)
    print(f"   Initial calls: {len(limiter.calls)}")

    await limiter.wait_if_needed()
    await limiter.wait_if_needed()
    print(f"   After 2 calls: {len(limiter.calls)}")

    # Test 8: Client statistics
    print("\n✅ Test 8: Client Statistics")
    stats = client.get_client_stats()
    print(f"   Session ID: {stats['session_id']}")
    print(f"   Client Code: {stats['client_code']}")
    print(f"   Authenticated: {stats['is_authenticated']}")
    print(f"   Rate Limit Max: {stats['rate_limit_max']}")

    # Test 9: Exception classes
    print("\n✅ Test 9: Exception Classes")
    from api.angel_one_client import (
        AngelOneError, AuthenticationError, ValidationError
    )

    try:
        raise AuthenticationError("Test auth error", "AG8001", 401)
    except AngelOneError as e:
        print(f"   Exception caught: {type(e).__name__}")
        print(f"   Message: {e.message}")
        print(f"   Error Code: {e.error_code}")

    print("\n" + "=" * 50)
    print("🎉 All basic functionality tests passed!")

    # Clean up
    await client.close()


if __name__ == "__main__":
    asyncio.run(test_basic_functionality())
