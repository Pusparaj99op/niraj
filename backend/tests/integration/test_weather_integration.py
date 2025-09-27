"""
Integration tests for Weather API Client
Tests real API integration and key functionality
"""

import pytest
import asyncio
import os
from datetime import datetime

# Add path for imports
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../src"))

from api.weather_client import (
    WeatherClient,
    WeatherConfig,
    LocationQuery,
    WeatherUnits,
    WeatherError,
    AuthenticationError,
    DataNotFoundError,
    get_weather_for_trading,
    monitor_agricultural_weather,
)


class TestWeatherClientIntegration:
    """Integration tests for WeatherClient"""

    @pytest.fixture
    def api_key(self):
        """Get API key from environment or skip test"""
        api_key = os.getenv("WEATHER_API_KEY")
        if not api_key:
            pytest.skip("WEATHER_API_KEY environment variable not set")
        return api_key

    @pytest.fixture
    def weather_config(self, api_key):
        """Weather configuration for testing"""
        return WeatherConfig(
            api_key=api_key,
            timeout=15,
            max_retries=2,
            rate_limit_calls_per_minute=10,  # Conservative for testing
            enable_commodity_analysis=True,
            enable_agricultural_insights=True,
            enable_energy_insights=True,
        )

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_current_weather_mumbai(self, weather_config):
        """Test getting current weather for Mumbai"""
        async with WeatherClient(weather_config) as client:
            query = LocationQuery(city_name="Mumbai", country_code="IN")
            weather = await client.get_current_weather(query)

            # Verify basic weather data
            assert weather.location_name == "Mumbai"
            assert weather.country == "IN"
            assert isinstance(weather.temperature, (int, float))
            assert isinstance(weather.humidity, int)
            assert 0 <= weather.humidity <= 100
            assert len(weather.conditions) > 0
            assert isinstance(weather.timestamp, datetime)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_forecast_delhi(self, weather_config):
        """Test getting forecast for Delhi"""
        async with WeatherClient(weather_config) as client:
            query = LocationQuery(city_name="Delhi", country_code="IN")
            forecasts = await client.get_forecast(query, days=2)

            # Should have multiple forecast points
            assert len(forecasts) > 0
            assert len(forecasts) <= 16  # 2 days * 8 points per day

            # Verify forecast data
            for forecast in forecasts[:3]:  # Check first 3
                assert isinstance(forecast.temperature, (int, float))
                assert isinstance(forecast.humidity, int)
                assert isinstance(forecast.timestamp, datetime)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_trading_insights(self, weather_config):
        """Test trading insights calculation"""
        async with WeatherClient(weather_config) as client:
            query = LocationQuery(city_name="Mumbai", country_code="IN")
            insights = await client.get_trading_insights(query, include_forecast=True)

            # Verify insights structure
            assert insights is not None
            assert hasattr(insights, "crop_stress_index")
            assert hasattr(insights, "drought_indicator")
            assert hasattr(insights, "transportation_disruption_risk")
            assert hasattr(insights, "commodity_price_impact")

            # Risk level should be valid
            assert insights.transportation_disruption_risk in ["low", "medium", "high"]

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_multi_location_weather(self, weather_config):
        """Test multi-location weather retrieval"""
        async with WeatherClient(weather_config) as client:
            locations = [
                LocationQuery(city_name="Mumbai", country_code="IN"),
                LocationQuery(city_name="Delhi", country_code="IN"),
                LocationQuery(city_name="Bangalore", country_code="IN"),
            ]

            results = await client.get_multi_location_weather(
                locations, data_types=["current", "insights"]
            )

            # Should have data for all locations
            assert len(results) == 3

            # Verify each location has required data
            for location_name, data in results.items():
                assert "current" in data
                assert "insights" in data
                if data["current"]:  # If data was successfully retrieved
                    assert data["current"].country == "IN"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_search_locations(self, weather_config):
        """Test location search"""
        async with WeatherClient(weather_config) as client:
            results = await client.search_locations("Mumbai", limit=3)

            assert len(results) > 0
            assert len(results) <= 3

            # Should find Mumbai in results
            mumbai_found = any(
                "Mumbai" in result.get("name", "") or "Bombay" in result.get("name", "")
                for result in results
            )
            assert mumbai_found

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_coordinate_based_query(self, weather_config):
        """Test weather query using coordinates"""
        async with WeatherClient(weather_config) as client:
            # Mumbai coordinates
            query = LocationQuery(latitude=19.076, longitude=72.8777)
            weather = await client.get_current_weather(query)

            # Should get weather data
            assert weather is not None
            assert isinstance(weather.temperature, (int, float))
            assert weather.latitude == pytest.approx(19.076, abs=0.1)
            assert weather.longitude == pytest.approx(72.8777, abs=0.1)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_caching_behavior(self, weather_config):
        """Test that caching works correctly"""
        async with WeatherClient(weather_config) as client:
            query = LocationQuery(city_name="Mumbai", country_code="IN")

            # First request
            weather1 = await client.get_current_weather(query)
            cache_misses_1 = client.stats["cache_misses"]

            # Second request should hit cache
            weather2 = await client.get_current_weather(query)
            cache_hits = client.stats["cache_hits"]
            cache_misses_2 = client.stats["cache_misses"]

            # Should have same temperature (cached)
            assert weather1.temperature == weather2.temperature
            assert cache_hits > 0
            assert cache_misses_2 == cache_misses_1  # No new cache miss

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_health_check(self, weather_config):
        """Test API health check"""
        async with WeatherClient(weather_config) as client:
            health = await client.health_check()

            assert health["status"] in ["healthy", "degraded"]
            assert health["api_key_configured"] is True
            assert "api_connectivity" in health
            assert "cache_stats" in health

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_invalid_location_error(self, weather_config):
        """Test error handling for invalid location"""
        async with WeatherClient(weather_config) as client:
            query = LocationQuery(city_name="InvalidCityNameThatDoesNotExist")

            with pytest.raises(DataNotFoundError):
                await client.get_current_weather(query)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_client_statistics(self, weather_config):
        """Test client statistics tracking"""
        async with WeatherClient(weather_config) as client:
            query = LocationQuery(city_name="Mumbai", country_code="IN")
            await client.get_current_weather(query)

            stats = client.get_client_stats()

            assert stats["statistics"]["requests_made"] > 0
            assert len(stats["statistics"]["locations_queried"]) > 0
            assert "current" in stats["statistics"]["data_types_requested"]

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_utility_function_get_weather_for_trading(self, api_key):
        """Test utility function for quick trading weather"""
        result = await get_weather_for_trading("Mumbai", "IN", api_key)

        assert "current_weather" in result
        assert "trading_insights" in result
        assert "summary" in result

        summary = result["summary"]
        assert "Mumbai" in summary["location"]
        assert "IN" in summary["location"]
        assert isinstance(summary["temperature"], (int, float))
        assert isinstance(summary["conditions"], list)
        assert summary["risk_level"] in ["low", "medium", "high"]

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_utility_function_monitor_agricultural_weather(self, api_key):
        """Test agricultural monitoring utility function"""
        result = await monitor_agricultural_weather(["Mumbai", "Delhi"], api_key)

        assert "monitoring_summary" in result
        assert "detailed_data" in result

        summary = result["monitoring_summary"]
        assert summary["locations_monitored"] == 2
        assert isinstance(summary["average_crop_stress"], (int, float))

    @pytest.mark.asyncio
    async def test_no_api_key_configuration_error(self):
        """Test error when no API key is configured"""
        config = WeatherConfig()  # No API key

        async with WeatherClient(config) as client:
            query = LocationQuery(city_name="Mumbai")

            with pytest.raises(AuthenticationError, match="API key not configured"):
                await client.get_current_weather(query)


class TestWeatherClientPerformance:
    """Performance tests for WeatherClient"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.performance
    async def test_concurrent_requests(self):
        """Test concurrent weather requests"""
        api_key = os.getenv("WEATHER_API_KEY")
        if not api_key:
            pytest.skip("WEATHER_API_KEY environment variable not set")

        config = WeatherConfig(api_key=api_key)

        async with WeatherClient(config) as client:
            # Create multiple location queries
            locations = [
                LocationQuery(city_name="Mumbai", country_code="IN"),
                LocationQuery(city_name="Delhi", country_code="IN"),
                LocationQuery(city_name="Bangalore", country_code="IN"),
                LocationQuery(city_name="Chennai", country_code="IN"),
                LocationQuery(city_name="Kolkata", country_code="IN"),
            ]

            # Measure time for concurrent requests
            start_time = asyncio.get_event_loop().time()

            results = await client.get_multi_location_weather(
                locations, data_types=["current"]
            )

            end_time = asyncio.get_event_loop().time()
            duration = end_time - start_time

            # Should complete in reasonable time (less than 30 seconds for 5 locations)
            assert duration < 30.0
            assert len(results) == 5

            # At least some requests should succeed
            successful_requests = sum(
                1 for data in results.values() if data.get("current") is not None
            )
            assert successful_requests > 0


if __name__ == "__main__":
    # Run only integration tests
    pytest.main([__file__, "-v", "-m", "integration"])
