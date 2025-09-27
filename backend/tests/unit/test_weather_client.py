"""
Comprehensive tests for Weather API Client
Tests all functionality including error handling, caching, rate limiting, and trading insights
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch
import httpx

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../src"))

from src.api.weather_client import (
    WeatherClient,
    WeatherConfig,
    LocationQuery,
    WeatherUnits,
    WeatherLang,
    CurrentWeather,
    WeatherForecast,
    WeatherAlert,
    WeatherInsights,
    WeatherError,
    AuthenticationError,
    RateLimitError,
    ValidationError,
    NetworkError,
    DataNotFoundError,
    WeatherCache,
    RateLimiter,
    CircuitBreaker,
    get_weather_for_trading,
    monitor_agricultural_weather,
)


class TestWeatherConfig:
    """Test WeatherConfig model"""

    def test_default_config(self):
        """Test default configuration values"""
        config = WeatherConfig()

        assert config.api_key is None
        assert config.base_url == "https://api.openweathermap.org/data/2.5"
        assert config.timeout == 15
        assert config.max_retries == 3
        assert config.default_units == WeatherUnits.METRIC
        assert config.default_language == WeatherLang.ENGLISH
        assert config.enable_commodity_analysis is True
        assert config.enable_agricultural_insights is True
        assert config.enable_energy_insights is True

    def test_custom_config(self):
        """Test custom configuration"""
        config = WeatherConfig(
            api_key="test_key",
            timeout=30,
            default_units=WeatherUnits.IMPERIAL,
            enable_commodity_analysis=False,
        )

        assert config.api_key == "test_key"
        assert config.timeout == 30
        assert config.default_units == WeatherUnits.IMPERIAL
        assert config.enable_commodity_analysis is False


class TestLocationQuery:
    """Test LocationQuery model"""

    def test_city_query(self):
        """Test city-based query"""
        query = LocationQuery(city_name="Mumbai", country_code="IN")
        query_string = query.to_query_string()

        assert "q=Mumbai,IN" in query_string

    def test_coordinate_query(self):
        """Test coordinate-based query"""
        query = LocationQuery(latitude=19.076, longitude=72.8777)
        query_string = query.to_query_string()

        assert "lat=19.076" in query_string
        assert "lon=72.8777" in query_string

    def test_zip_query(self):
        """Test zip code query"""
        query = LocationQuery(zip_code="400001", country_code="IN")
        query_string = query.to_query_string()

        assert "zip=400001,IN" in query_string

    def test_invalid_query(self):
        """Test validation of invalid query"""
        query = LocationQuery()

        with pytest.raises(ValueError, match="Must provide either coordinates"):
            query.to_query_string()

    def test_city_name_validation(self):
        """Test city name validation"""
        with pytest.raises(ValueError, match="City name must be at least 2 characters"):
            LocationQuery(city_name="A")


class TestWeatherCache:
    """Test weather caching functionality"""

    def test_cache_operations(self):
        """Test basic cache operations"""
        cache = WeatherCache()

        query = LocationQuery(city_name="Delhi")
        data = {"temp": 25, "humidity": 60}

        # Set and get
        cache.set("weather", query, data, ttl_minutes=10)
        cached_data = cache.get("weather", query)

        assert cached_data == data

    def test_cache_expiry(self):
        """Test cache expiry"""
        cache = WeatherCache()

        query = LocationQuery(city_name="Delhi")
        data = {"temp": 25}

        # Set with short TTL
        cache.set("weather", query, data, ttl_minutes=0)

        # Should be expired immediately
        cached_data = cache.get("weather", query)
        assert cached_data is None

    def test_cache_key_generation(self):
        """Test cache key generation for different queries"""
        cache = WeatherCache()

        query1 = LocationQuery(city_name="Delhi")
        query2 = LocationQuery(city_name="Mumbai")

        data1 = {"temp": 25}
        data2 = {"temp": 30}

        cache.set("weather", query1, data1, ttl_minutes=10)
        cache.set("weather", query2, data2, ttl_minutes=10)

        assert cache.get("weather", query1) == data1
        assert cache.get("weather", query2) == data2

    def test_cache_stats(self):
        """Test cache statistics"""
        cache = WeatherCache()

        query = LocationQuery(city_name="Delhi")
        cache.set("weather", query, {"temp": 25}, ttl_minutes=10)

        stats = cache.get_stats()
        assert stats["total_entries"] == 1
        assert stats["active_entries"] == 1


class TestRateLimiter:
    """Test rate limiting functionality"""

    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """Test rate limiting behavior"""
        limiter = RateLimiter(max_calls_per_minute=2, max_calls_per_month=100)

        # First two calls should pass immediately
        await limiter.wait_if_needed()
        await limiter.wait_if_needed()

        # Third call should cause a delay (mocked time)
        start_time = asyncio.get_event_loop().time()
        with patch("time.time", return_value=start_time):
            await limiter.wait_if_needed()

        assert len(limiter.minute_calls) <= 2


class TestCircuitBreaker:
    """Test circuit breaker functionality"""

    @pytest.mark.asyncio
    async def test_circuit_breaker_states(self):
        """Test circuit breaker state transitions"""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=1)

        # Mock function that fails
        mock_func = AsyncMock(side_effect=Exception("Test error"))

        # First failure - circuit should remain closed
        with pytest.raises(Exception):
            await breaker.call(mock_func)
        assert breaker.state == "CLOSED"

        # Second failure - circuit should open
        with pytest.raises(Exception):
            await breaker.call(mock_func)
        assert breaker.state == "OPEN"

        # Immediate call should fail due to open circuit
        with pytest.raises(WeatherError, match="Circuit breaker OPEN"):
            await breaker.call(mock_func)


class TestWeatherClient:
    """Test WeatherClient functionality"""

    @pytest.fixture
    def weather_config(self):
        """Test configuration"""
        return WeatherConfig(api_key="test_api_key", timeout=10, max_retries=2)

    @pytest.fixture
    def mock_response_current_weather(self):
        """Mock response for current weather"""
        return {
            "coord": {"lon": 72.8777, "lat": 19.076},
            "weather": [
                {"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}
            ],
            "main": {
                "temp": 25.5,
                "feels_like": 27.2,
                "temp_min": 24.0,
                "temp_max": 27.0,
                "pressure": 1013,
                "humidity": 65,
            },
            "wind": {"speed": 3.5, "deg": 180, "gust": 5.2},
            "clouds": {"all": 10},
            "dt": 1640995200,
            "sys": {"country": "IN", "sunrise": 1640995200, "sunset": 1640995200},
            "timezone": 19800,
            "name": "Mumbai",
        }

    @pytest.fixture
    def mock_response_forecast(self):
        """Mock response for forecast"""
        return {
            "list": [
                {
                    "dt": 1640995200,
                    "main": {
                        "temp": 25.5,
                        "feels_like": 27.2,
                        "temp_min": 24.0,
                        "temp_max": 27.0,
                        "pressure": 1013,
                        "humidity": 65,
                    },
                    "weather": [
                        {
                            "id": 800,
                            "main": "Clear",
                            "description": "clear sky",
                            "icon": "01d",
                        }
                    ],
                    "clouds": {"all": 10},
                    "wind": {"speed": 3.5, "deg": 180},
                    "pop": 0.1,
                }
            ],
            "city": {
                "name": "Mumbai",
                "coord": {"lat": 19.076, "lon": 72.8777},
                "country": "IN",
            },
        }

    @pytest.mark.asyncio
    async def test_get_current_weather_success(
        self, weather_config, mock_response_current_weather
    ):
        """Test successful current weather retrieval"""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_current_weather
            mock_get.return_value = mock_response

            async with WeatherClient(weather_config) as client:
                query = LocationQuery(city_name="Mumbai")
                weather = await client.get_current_weather(query)

                assert isinstance(weather, CurrentWeather)
                assert weather.location_name == "Mumbai"
                assert weather.country == "IN"
                assert weather.temperature == 25.5
                assert weather.humidity == 65
                assert len(weather.conditions) == 1
                assert weather.conditions[0].main == "Clear"

    @pytest.mark.asyncio
    async def test_get_forecast_success(self, weather_config, mock_response_forecast):
        """Test successful forecast retrieval"""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_forecast
            mock_get.return_value = mock_response

            async with WeatherClient(weather_config) as client:
                query = LocationQuery(city_name="Mumbai")
                forecasts = await client.get_forecast(query, days=1)

                assert isinstance(forecasts, list)
                assert len(forecasts) == 1
                assert isinstance(forecasts[0], WeatherForecast)
                assert forecasts[0].temperature == 25.5

    @pytest.mark.asyncio
    async def test_authentication_error(self, weather_config):
        """Test authentication error handling"""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.json.return_value = {"message": "Invalid API key"}
            mock_get.return_value = mock_response

            async with WeatherClient(weather_config) as client:
                query = LocationQuery(city_name="Mumbai")

                with pytest.raises(AuthenticationError):
                    await client.get_current_weather(query)

    @pytest.mark.asyncio
    async def test_location_not_found_error(self, weather_config):
        """Test location not found error"""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.json.return_value = {"message": "City not found"}
            mock_get.return_value = mock_response

            async with WeatherClient(weather_config) as client:
                query = LocationQuery(city_name="InvalidCity")

                with pytest.raises(DataNotFoundError):
                    await client.get_current_weather(query)

    @pytest.mark.asyncio
    async def test_rate_limit_error_with_retry(self, weather_config):
        """Test rate limit error with retry logic"""
        with patch("httpx.AsyncClient.get") as mock_get:
            # First call returns rate limit error
            # Second call succeeds
            mock_response_error = Mock()
            mock_response_error.status_code = 429
            mock_response_error.json.return_value = {"message": "Rate limit exceeded"}

            mock_response_success = Mock()
            mock_response_success.status_code = 200
            mock_response_success.json.return_value = {
                "coord": {"lon": 72.8777, "lat": 19.076},
                "weather": [
                    {
                        "id": 800,
                        "main": "Clear",
                        "description": "clear sky",
                        "icon": "01d",
                    }
                ],
                "main": {
                    "temp": 25.5,
                    "feels_like": 27.2,
                    "temp_min": 24.0,
                    "temp_max": 27.0,
                    "pressure": 1013,
                    "humidity": 65,
                },
                "wind": {"speed": 3.5, "deg": 180},
                "clouds": {"all": 10},
                "dt": 1640995200,
                "sys": {"country": "IN", "sunrise": 1640995200, "sunset": 1640995200},
                "timezone": 19800,
                "name": "Mumbai",
            }

            mock_get.side_effect = [mock_response_error, mock_response_success]

            async with WeatherClient(weather_config) as client:
                query = LocationQuery(city_name="Mumbai")

                # Should succeed after retry
                weather = await client.get_current_weather(query)
                assert weather.location_name == "Mumbai"

    @pytest.mark.asyncio
    async def test_network_error_with_retry(self, weather_config):
        """Test network error with retry"""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.side_effect = [
                httpx.NetworkError("Connection failed"),
                httpx.NetworkError("Connection failed"),
                Mock(
                    status_code=200,
                    json=lambda: {
                        "name": "Mumbai",
                        "coord": {"lat": 19, "lon": 72},
                        "main": {"temp": 25},
                        "weather": [
                            {
                                "id": 800,
                                "main": "Clear",
                                "description": "clear",
                                "icon": "01d",
                            }
                        ],
                        "wind": {"speed": 3, "deg": 180},
                        "clouds": {"all": 0},
                        "dt": 1640995200,
                        "sys": {
                            "country": "IN",
                            "sunrise": 1640995200,
                            "sunset": 1640995200,
                        },
                        "timezone": 19800,
                    },
                ),
            ]

            async with WeatherClient(weather_config) as client:
                query = LocationQuery(city_name="Mumbai")

                # Should succeed after retries
                weather = await client.get_current_weather(query)
                assert weather.location_name == "Mumbai"

    @pytest.mark.asyncio
    async def test_timeout_error(self, weather_config):
        """Test timeout error handling"""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.side_effect = httpx.TimeoutException("Request timeout")

            async with WeatherClient(weather_config) as client:
                query = LocationQuery(city_name="Mumbai")

                with pytest.raises(NetworkError, match="Request timeout"):
                    await client.get_current_weather(query)

    @pytest.mark.asyncio
    async def test_caching_functionality(
        self, weather_config, mock_response_current_weather
    ):
        """Test caching reduces API calls"""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_current_weather
            mock_get.return_value = mock_response

            async with WeatherClient(weather_config) as client:
                query = LocationQuery(city_name="Mumbai")

                # First call should make API request
                weather1 = await client.get_current_weather(query)
                assert mock_get.call_count == 1

                # Second call should use cache
                weather2 = await client.get_current_weather(query)
                assert mock_get.call_count == 1  # No additional API call

                assert weather1.temperature == weather2.temperature
                assert client.stats["cache_hits"] == 1

    @pytest.mark.asyncio
    async def test_trading_insights_calculation(
        self, weather_config, mock_response_current_weather
    ):
        """Test trading insights calculation"""
        # Modify mock data for testing insights
        mock_data = mock_response_current_weather.copy()
        mock_data["main"]["temp"] = 40  # High temperature for crop stress
        mock_data["main"]["humidity"] = 25  # Low humidity for drought

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_data
            mock_get.return_value = mock_response

            async with WeatherClient(weather_config) as client:
                query = LocationQuery(city_name="Mumbai")
                insights = await client.get_trading_insights(query)

                assert isinstance(insights, WeatherInsights)
                assert insights.crop_stress_index is not None
                assert (
                    insights.crop_stress_index > 0
                )  # High temperature should cause stress
                assert (
                    insights.drought_indicator is True
                )  # Low humidity should indicate drought
                assert len(insights.commodity_price_impact) > 0

    @pytest.mark.asyncio
    async def test_multi_location_weather(
        self, weather_config, mock_response_current_weather
    ):
        """Test multi-location weather retrieval"""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_current_weather
            mock_get.return_value = mock_response

            async with WeatherClient(weather_config) as client:
                locations = [
                    LocationQuery(city_name="Mumbai"),
                    LocationQuery(city_name="Delhi"),
                ]

                results = await client.get_multi_location_weather(
                    locations, data_types=["current", "insights"]
                )

                assert len(results) == 2
                assert "Mumbai" in results
                assert "current" in results["Mumbai"]
                assert "insights" in results["Mumbai"]

    @pytest.mark.asyncio
    async def test_search_locations(self, weather_config):
        """Test location search functionality"""
        mock_search_results = [
            {
                "name": "Mumbai",
                "lat": 19.076,
                "lon": 72.8777,
                "country": "IN",
                "state": "Maharashtra",
            }
        ]

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_search_results
            mock_get.return_value = mock_response

            async with WeatherClient(weather_config) as client:
                results = await client.search_locations("Mumbai")

                assert len(results) == 1
                assert results[0]["name"] == "Mumbai"
                assert results[0]["country"] == "IN"

    @pytest.mark.asyncio
    async def test_health_check(self, weather_config, mock_response_current_weather):
        """Test health check functionality"""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_current_weather
            mock_get.return_value = mock_response

            async with WeatherClient(weather_config) as client:
                health = await client.health_check()

                assert health["status"] == "healthy"
                assert health["api_key_configured"] is True
                assert health["api_connectivity"] == "working"
                assert "cache_stats" in health
                assert "rate_limiter" in health

    @pytest.mark.asyncio
    async def test_client_stats(self, weather_config):
        """Test client statistics"""
        async with WeatherClient(weather_config) as client:
            stats = client.get_client_stats()

            assert "session_id" in stats
            assert "configuration" in stats
            assert "statistics" in stats
            assert "cache_stats" in stats
            assert "circuit_breaker" in stats

    @pytest.mark.asyncio
    async def test_no_api_key_error(self):
        """Test error when no API key is configured"""
        config = WeatherConfig()  # No API key

        async with WeatherClient(config) as client:
            query = LocationQuery(city_name="Mumbai")

            with pytest.raises(AuthenticationError, match="API key not configured"):
                await client.get_current_weather(query)


class TestUtilityFunctions:
    """Test utility functions"""

    @pytest.mark.asyncio
    async def test_get_weather_for_trading(self):
        """Test quick weather for trading function"""
        mock_current_data = {
            "coord": {"lon": 77.2090, "lat": 28.6139},
            "weather": [
                {"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}
            ],
            "main": {
                "temp": 25.5,
                "feels_like": 27.2,
                "temp_min": 24.0,
                "temp_max": 27.0,
                "pressure": 1013,
                "humidity": 65,
            },
            "wind": {"speed": 3.5, "deg": 180},
            "clouds": {"all": 10},
            "dt": 1640995200,
            "sys": {"country": "IN", "sunrise": 1640995200, "sunset": 1640995200},
            "timezone": 19800,
            "name": "Delhi",
        }

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_current_data
            mock_get.return_value = mock_response

            result = await get_weather_for_trading("Delhi", "IN", "test_api_key")

            assert "current_weather" in result
            assert "trading_insights" in result
            assert "summary" in result
            assert result["summary"]["location"] == "Delhi, IN"

    @pytest.mark.asyncio
    async def test_monitor_agricultural_weather(self):
        """Test agricultural weather monitoring"""
        mock_current_data = {
            "coord": {"lon": 77.2090, "lat": 28.6139},
            "weather": [
                {"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}
            ],
            "main": {
                "temp": 38.0,
                "feels_like": 40.0,
                "temp_min": 35.0,
                "temp_max": 40.0,
                "pressure": 1013,
                "humidity": 25,
            },
            "wind": {"speed": 3.5, "deg": 180},
            "clouds": {"all": 10},
            "dt": 1640995200,
            "sys": {"country": "IN", "sunrise": 1640995200, "sunset": 1640995200},
            "timezone": 19800,
            "name": "Delhi",
        }

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_current_data
            mock_get.return_value = mock_response

            result = await monitor_agricultural_weather(
                ["Delhi", "Mumbai"], "test_api_key"
            )

            assert "monitoring_summary" in result
            assert "detailed_data" in result
            assert result["monitoring_summary"]["locations_monitored"] == 2
            assert result["monitoring_summary"]["average_crop_stress"] > 0


class TestErrorScenarios:
    """Test various error scenarios and edge cases"""

    @pytest.mark.asyncio
    async def test_invalid_json_response(self):
        """Test handling of invalid JSON response"""
        config = WeatherConfig(api_key="test_key")

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
            mock_get.return_value = mock_response

            async with WeatherClient(config) as client:
                query = LocationQuery(city_name="Mumbai")

                with pytest.raises(WeatherError, match="Invalid JSON response"):
                    await client.get_current_weather(query)

    @pytest.mark.asyncio
    async def test_server_error_max_retries(self):
        """Test server error with max retries exceeded"""
        config = WeatherConfig(api_key="test_key", max_retries=1)

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            mock_get.return_value = mock_response

            async with WeatherClient(config) as client:
                query = LocationQuery(city_name="Mumbai")

                with pytest.raises(WeatherError, match="Server error: 500"):
                    await client.get_current_weather(query)

                # Should have tried max_retries + 1 times
                assert mock_get.call_count == 2

    @pytest.mark.asyncio
    async def test_unexpected_http_status(self):
        """Test unexpected HTTP status code"""
        config = WeatherConfig(api_key="test_key")

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 418  # I'm a teapot
            mock_response.text = "I'm a teapot"
            mock_get.return_value = mock_response

            async with WeatherClient(config) as client:
                query = LocationQuery(city_name="Mumbai")

                with pytest.raises(WeatherError, match="HTTP 418"):
                    await client.get_current_weather(query)

    def test_weather_condition_validation(self):
        """Test weather condition model validation"""
        # Test valid weather condition
        condition = {
            "id": 800,
            "main": "Clear",
            "description": "clear sky",
            "icon": "01d",
        }

        # This should not raise an exception
        from api.weather_client import WeatherCondition

        weather_condition = WeatherCondition(**condition)
        assert weather_condition.main == "Clear"

    def test_current_weather_timestamp_conversion(self):
        """Test timestamp conversion in CurrentWeather model"""
        weather_data = {
            "location_name": "Mumbai",
            "country": "IN",
            "latitude": 19.076,
            "longitude": 72.8777,
            "timezone": 19800,
            "timestamp": 1640995200,  # Unix timestamp
            "temperature": 25.5,
            "feels_like": 27.2,
            "pressure": 1013,
            "humidity": 65,
            "wind_speed": 3.5,
            "wind_direction": 180,
            "conditions": [],
            "cloudiness": 10,
            "sunrise": 1640995200,
            "sunset": 1640995200,
            "units": WeatherUnits.METRIC,
        }

        weather = CurrentWeather(**weather_data)
        assert isinstance(weather.timestamp, datetime)
        assert isinstance(weather.sunrise, datetime)
        assert isinstance(weather.sunset, datetime)


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
