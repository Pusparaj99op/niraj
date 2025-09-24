# Weather API Client Documentation

## Overview

The Weather API Client (`backend/src/api/weather_client.py`) is a comprehensive OpenWeatherMap API integration designed specifically for trading applications. It provides weather data analysis with focus on agricultural commodities, energy markets, and general trading insights.

## Features

### Core Functionality
- **Current Weather Data**: Real-time weather conditions for any location
- **Weather Forecasts**: Up to 5-day forecasts with 3-hour intervals
- **Location Search**: Find locations by name with geocoding
- **Multi-location Monitoring**: Concurrent weather data for multiple locations

### Trading-Focused Features
- **Commodity Analysis**: Weather impact assessment for agricultural commodities
- **Agricultural Insights**: Crop stress indicators, drought detection, frost risk
- **Energy Market Insights**: Heating/cooling degree days, renewable energy potential
- **Transportation Risk**: Weather-related disruption assessment

### Advanced Features
- **Intelligent Caching**: Different TTL for various data types
- **Rate Limiting**: Respects OpenWeatherMap API limits
- **Circuit Breaker**: Prevents cascade failures
- **Retry Logic**: Exponential backoff for transient errors
- **Comprehensive Error Handling**: Custom exceptions for different error types
- **Performance Monitoring**: Request statistics and health checks

## Configuration

Weather API settings are configured in `backend/config/development.yaml`:

```yaml
external_apis:
  weather:
    api_key: "${WEATHER_API_KEY:}"  # Set your OpenWeatherMap API key
    base_url: "https://api.openweathermap.org/data/2.5"
    timeout: 15
    max_retries: 3
    rate_limit_calls_per_minute: 50
    default_units: "metric"
    enable_commodity_analysis: true
    enable_agricultural_insights: true
    enable_energy_insights: true
```

Environment variable: `WEATHER_API_KEY=your_openweathermap_api_key`

## Usage Examples

### Basic Weather Query

```python
from api.weather_client import WeatherClient, WeatherConfig, LocationQuery

# Configure client
config = WeatherConfig(api_key="your_api_key")
client = WeatherClient(config)

# Get current weather
query = LocationQuery(city_name="Mumbai", country_code="IN")
weather = await client.get_current_weather(query)

print(f"Temperature: {weather.temperature}°C")
print(f"Humidity: {weather.humidity}%")
print(f"Conditions: {[c.description for c in weather.conditions]}")
```

### Trading Insights

```python
# Get trading-relevant insights
insights = await client.get_trading_insights(query)

print(f"Crop stress index: {insights.crop_stress_index}")
print(f"Drought indicator: {insights.drought_indicator}")
print(f"Transportation risk: {insights.transportation_disruption_risk}")
print(f"Commodity impacts: {insights.commodity_price_impact}")
```

### Multi-location Monitoring

```python
locations = [
    LocationQuery(city_name="Mumbai", country_code="IN"),
    LocationQuery(city_name="Delhi", country_code="IN"),
    LocationQuery(city_name="Bangalore", country_code="IN")
]

results = await client.get_multi_location_weather(
    locations,
    data_types=["current", "insights"]
)

for location, data in results.items():
    print(f"{location}: {data['current'].temperature}°C")
```

### Quick Utility Functions

```python
from api.weather_client import get_weather_for_trading, monitor_agricultural_weather

# Quick trading weather summary
result = await get_weather_for_trading("Mumbai", "IN", api_key)
print(result["summary"])

# Agricultural monitoring
agri_data = await monitor_agricultural_weather(["Mumbai", "Delhi"], api_key)
print(agri_data["monitoring_summary"])
```

## Trading Applications

### Agricultural Commodities
- **Crop Stress Monitoring**: High temperatures and low humidity indicate crop stress
- **Drought Detection**: Extended periods of low humidity and no precipitation
- **Frost Risk**: Temperatures below 2°C threaten crop yields
- **Growing Degree Days**: Heat accumulation for crop development

### Energy Markets
- **Heating Demand**: Temperatures below 18°C increase heating demand
- **Cooling Demand**: Temperatures above 24°C increase cooling demand
- **Wind Power**: Optimal wind speeds (3-25 m/s) for wind power generation
- **Solar Potential**: Clear skies and high UV index improve solar efficiency

### Transportation & Logistics
- **Disruption Risk**: Severe weather conditions affecting supply chains
- **Seasonal Patterns**: Weather trends affecting commodity availability

## Error Handling

The client provides specific error types for different scenarios:

```python
from api.weather_client import (
    AuthenticationError,    # Invalid API key
    RateLimitError,        # API quota exceeded
    DataNotFoundError,     # Invalid location
    NetworkError,          # Connection issues
    WeatherError          # General API errors
)

try:
    weather = await client.get_current_weather(query)
except AuthenticationError:
    print("Check your API key")
except DataNotFoundError:
    print("Location not found")
except RateLimitError:
    print("API quota exceeded, wait before retry")
except NetworkError:
    print("Network connection issue")
```

## Performance & Scaling

### Caching Strategy
- **Current Weather**: 10 minutes TTL (weather changes slowly)
- **Forecasts**: 60 minutes TTL (updated hourly)
- **Alerts**: 5 minutes TTL (time-sensitive)
- **Historical**: 24 hours TTL (static data)

### Rate Limiting
- **Free Tier**: 60 calls/minute, 1000 calls/day
- **Conservative Limits**: 50 calls/minute to avoid issues
- **Monthly Tracking**: Prevents exceeding monthly quotas

### Circuit Breaker
- **Failure Threshold**: 5 consecutive failures trigger open state
- **Recovery Timeout**: 60 seconds before attempting recovery
- **Health Monitoring**: Automatic service status tracking

## Testing

### Unit Tests
```bash
# Run unit tests
cd backend
python -m pytest tests/unit/test_weather_client.py -v
```

### Integration Tests
```bash
# Set API key for integration tests
export WEATHER_API_KEY=your_openweathermap_api_key

# Run integration tests
python -m pytest tests/integration/test_weather_integration.py -v -m integration
```

## API Key Setup

1. **Sign up** at [OpenWeatherMap](https://openweathermap.org/api)
2. **Get API key** from your account dashboard
3. **Set environment variable**: `export WEATHER_API_KEY=your_key`
4. **Update config**: Add key to `development.yaml` or `.env` file

## Limitations

### Free Tier Limits
- 60 calls/minute
- 1,000 calls/day
- No historical data access
- No weather alerts (requires paid plan)

### Data Coverage
- Global weather data available
- 3-hour forecast intervals
- 5-day forecast limit (free tier)
- Some remote locations may have limited data

## Monitoring & Health Checks

```python
# Check API health
health = await client.health_check()
print(f"Status: {health['status']}")
print(f"API connectivity: {health['api_connectivity']}")

# Get client statistics
stats = client.get_client_stats()
print(f"Requests made: {stats['statistics']['requests_made']}")
print(f"Cache hit rate: {stats['cache_stats']['entries']}")
```

## Integration with NIRAJ Trading System

The Weather API client integrates seamlessly with the NIRAJ trading system:

1. **Configuration**: Uses centralized config system
2. **Logging**: Integrates with NIRAJ logging framework
3. **Error Handling**: Follows NIRAJ error handling patterns
4. **Async Operations**: Compatible with FastAPI async endpoints
5. **Monitoring**: Provides health checks for system monitoring

## Future Enhancements

- **Paid API Features**: Weather alerts, historical data, higher limits
- **Machine Learning**: Weather pattern prediction for trading
- **Custom Indicators**: More sophisticated agricultural and energy indicators
- **Real-time Alerts**: Push notifications for significant weather events
- **Satellite Imagery**: Integration with weather satellite data

---

**Task T062 Status**: ✅ **COMPLETED**

The Weather API client is now fully implemented with comprehensive features, error handling, testing, and documentation. It provides advanced weather analytics specifically designed for trading applications with focus on agricultural commodities and energy markets.
