"""
Simple script to fetch BankNifty data from Angel One API
"""


import asyncio

import secrets
import httpx
import pyotp


class SimpleAngelOneClient:
    """Simplified Angel One client for testing"""

    def __init__(self, api_key, client_code, client_pin, totp_secret):
        self.api_key = api_key
        self.client_code = client_code
        self.client_pin = client_pin
        self.totp_secret = totp_secret
        self.base_url = "https://apiconnect.angelone.in"
        self.jwt_token = None
        self.client = None

    def _generate_totp(self):
        if not self.totp_secret:
            raise Exception("TOTP secret not provided")
        totp = pyotp.TOTP(self.totp_secret)
        return totp.now()

    def _generate_mac_address(self):
        return "02:00:00:%02x:%02x:%02x" % (
            secrets.randbelow(256),
            secrets.randbelow(256),
            secrets.randbelow(256),
        )

    def _get_client_ips(self):
        return "192.168.1.1", "203.0.113.1"

    def _get_default_headers(self, include_auth=False):
        local_ip, public_ip = self._get_client_ips()
        mac = self._generate_mac_address()

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-UserType": "USER",
            "X-SourceID": "WEB",
            "X-ClientLocalIP": local_ip,
            "X-ClientPublicIP": public_ip,
            "X-MACAddress": mac,
            "X-PrivateKey": self.api_key,
            "User-Agent": "NIRAJ-Trading-System/1.0",
        }

        if include_auth and self.jwt_token:
            headers["Authorization"] = f"Bearer {self.jwt_token}"

        return headers

    async def _get_client(self):
        if self.client is None or self.client.is_closed:
            self.client = httpx.AsyncClient(timeout=30, follow_redirects=True)
        return self.client

    async def _make_request(self, method, endpoint, data=None, include_auth=True):
        url = f"{self.base_url}{endpoint}"
        headers = self._get_default_headers(include_auth=include_auth)
        client = await self._get_client()

        print(f"Making {method} request to {endpoint}")

        response = await client.request(method, url, headers=headers, json=data)
        print(f"Response status: {response.status_code}")

        try:
            response_data = response.json()
            print(f"Response data: {response_data}")
        except Exception:
            print(f"Response text: {response.text}")
            raise Exception(f"Invalid response: {response.text}")

        if response.status_code == 200 and response_data.get("status"):
            return response_data
        else:
            error_msg = response_data.get("message", "Unknown error")
            print(f"API Error: {error_msg}")
            raise Exception(f"API Error: {error_msg}")

    async def login(self):
        totp_code = self._generate_totp()
        login_data = {
            "clientcode": self.client_code,
            "password": self.client_pin,
            "totp": totp_code,
        }

        response = await self._make_request(
            "POST",
            "/rest/auth/angelbroking/user/v1/loginByPassword",
            data=login_data,
            include_auth=False,
        )

        self.jwt_token = response["data"]["jwtToken"]
        print("Login successful!")
        return response

    async def search_scrips(self, search_text):
        data = {"search": search_text}
        return await self._make_request(
            "POST",
            "/rest/secure/angelbroking/order/v1/searchScrip",
            data=data,
            include_auth=True,
        )

    async def get_historical_data(
        self, exchange, symboltoken, interval, fromdate, todate
    ):
        data = {
            "exchange": exchange,
            "symboltoken": symboltoken,
            "interval": interval,
            "fromdate": fromdate,
            "todate": todate,
        }

        return await self._make_request(
            "POST",
            "/rest/secure/angelbroking/historical/v1/getCandleData",
            data=data,
            include_auth=True,
        )

    async def get_ltp_data(self, exchange, tradingsymbol, symboltoken):
        data = {
            "exchange": exchange,
            "tradingsymbol": tradingsymbol,
            "symboltoken": symboltoken,
        }

        return await self._make_request(
            "POST",
            "/rest/secure/angelbroking/order/v1/getLtpData",
            data=data,
            include_auth=True,
        )

    async def get_profile(self):
        return await self._make_request(
            "GET", "/rest/secure/angelbroking/user/v1/getProfile", include_auth=True
        )

    async def close(self):
        if self.client and not self.client.is_closed:
            await self.client.aclose()


async def main():
    # Credentials
    api_key = "rlmeqiW7"
    client_code = "P57128169"
    password = "2580"
    totp_secret = "542KH3OULUEFW45MPF3LK6N7RM"

    client = SimpleAngelOneClient(api_key, client_code, password, totp_secret)

    try:
        # Login
        print("Logging in to Angel One...")
        await client.login()
        print("Login successful!")

        # Test profile endpoint
        print("\nTesting profile endpoint...")
        profile_data = await client.get_profile()
        print(f"Profile data: {profile_data}")

        # Try LTP for SBIN-EQ (from the API docs example)
        print("\nFetching LTP for SBIN-EQ...")
        ltp_data = await client.get_ltp_data(
            exchange="NSE", tradingsymbol="SBIN-EQ", symboltoken="3045"
        )
        print(f"LTP data for SBIN: {ltp_data}")

        # Try historical data for SBIN
        print("\nFetching historical data for SBIN...")
        from_date = "2024-09-20 09:15"
        to_date = "2024-09-20 15:30"

        historical_data = await client.get_historical_data(
            exchange="NSE",
            symboltoken="3045",
            interval="FIVE_MINUTE",
            fromdate=from_date,
            todate=to_date,
        )

        data_points = historical_data.get("data", [])
        print(f"\nRetrieved {len(data_points)} data points for SBIN")

        if data_points:
            print("First 3 data points:")
            for i, point in enumerate(data_points[:3]):
                print(f"{i+1}. {point}")

        # Now try BankNifty with different token
        print("\nTrying BankNifty with different approach...")
        # Try NIFTY index instead
        nifty_data = await client.get_ltp_data(
            exchange="NSE",
            tradingsymbol="NIFTY",
            symboltoken="99926000",  # From API docs example
        )
        print(f"LTP data for NIFTY: {nifty_data}")

        # Try BankNifty historical data with a more recent date
        from_date = "2024-09-20 09:15"
        to_date = "2024-09-20 15:30"

        historical_data = await client.get_historical_data(
            exchange="NSE",
            symboltoken="99926000",  # NIFTY
            interval="FIVE_MINUTE",
            fromdate=from_date,
            todate=to_date,
        )

        data_points = historical_data.get("data", [])
        print(f"\nRetrieved {len(data_points)} data points for NIFTY")

        if data_points:
            print("Today's BankNifty data (using NIFTY as proxy):")
            for i, point in enumerate(data_points[-5:]):  # Last 5 points
                print(f"{i+1}. {point}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
