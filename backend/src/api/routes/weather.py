"""
Weather API Routes for NIRAJ Trading System

Provides weather data for commodity and agricultural trading analysis:
- Current weather conditions
- Weather forecasts
- Agricultural insights
- Commodity price impact analysis
- Trading-relevant weather alerts
- Multi-location monitoring

Endpoints:
- GET /api/v1/weather/current: Get current weather
- GET /api/v1/weather/forecast: Get weather forecast
- GET /api/v1/weather/insights: Get trading insights
- GET /api/v1/weather/alerts: Get weather alerts
- POST /api/v1/weather/locations: Monitor multiple locations
- GET /api/v1/weather/commodities: Get commodity weather impact
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
import structlog

from ...core.database import DatabaseManager
from ...core.cache import CacheManager
from ...api.weather_client import (
    WeatherClient, WeatherConfig, LocationQuery,
    CurrentWeather, WeatherForecast, WeatherInsights, WeatherAlert
)
from ...api.routes.auth import get_security_context, SecurityContext

# Initialize router
router = APIRouter(
    prefix="/weather",
    tags=["weather"],
    responses={
        400: {"description": "Bad Request - Invalid parameters"},
        401: {"description": "Unauthorized - Authentication required"},
        404: {"description": "Not Found - Location not found"},
        429: {"description": "Too Many Requests - Rate limit exceeded"},
        503: {"description": "Service Unavailable - Weather service down"},
        500: {"description": "Internal Server Error - System error"}
    }
)

# Initialize logger
logger = structlog.get_logger(__name__)

# Global service instances
_db_manager: Optional[DatabaseManager] = None
_cache_manager: Optional[CacheManager] = None
_weather_client: Optional[WeatherClient] = None


# Enums
class WeatherUnits(str, Enum):
    """Weather units"""
    METRIC = "metric"
    IMPERIAL = "imperial"
    KELVIN = "kelvin"


class ForecastDays(int, Enum):
    """Available forecast days"""
    ONE = 1
    THREE = 3
    FIVE = 5
    SEVEN = 7


# Request Models
class LocationRequest(BaseModel):
    """Location request model"""
    city: str = Field(description="City name", min_length=1, max_length=100)
    country: str = Field(default="IN", description="Country code", min_length=2, max_length=2)
    state: Optional[str] = Field(None, description="State/region", max_length=100)

    @field_validator('city')
    @classmethod
    def validate_city(cls, v):
        return v.strip().title()

    @field_validator('country')
    @classmethod
    def validate_country(cls, v):
        return v.upper().strip()


class MultiLocationRequest(BaseModel):
    """Multiple locations monitoring request"""
    locations: List[LocationRequest] = Field(description="List of locations", max_length=10)
    data_types: Optional[List[str]] = Field(
        default=["current", "forecast", "alerts"],
        description="Types of data to fetch"
    )
    include_insights: bool = Field(default=True, description="Include trading insights")


class CommodityWeatherRequest(BaseModel):
    """Commodity weather impact request"""
    commodities: List[str] = Field(description="Commodity symbols", max_length=20)
    regions: Optional[List[str]] = Field(None, description="Specific regions to monitor")
    forecast_days: ForecastDays = Field(default=ForecastDays.THREE, description="Forecast period")


# Response Models
class CurrentWeatherResponse(BaseModel):
    """Current weather response"""
    location_name: str
    country: str
    coordinates: Dict[str, float]
    temperature: float
    feels_like: float
    humidity: int
    pressure: float
    visibility: Optional[float]
    uv_index: Optional[float]
    wind_speed: float
    wind_direction: int
    conditions: List[Dict[str, str]]
    sunrise: Optional[datetime]
    sunset: Optional[datetime]
    timestamp: datetime
    units: str


class ForecastResponse(BaseModel):
    """Weather forecast response"""
    location_name: str
    country: str
    forecasts: List[Dict[str, Any]]
    total_days: int
    timestamp: datetime
    units: str


class WeatherInsightsResponse(BaseModel):
    """Weather insights response"""
    location_name: str
    country: str
    insights: Dict[str, Any]
    risk_factors: Dict[str, float]
    commodity_impacts: Dict[str, Dict[str, Any]]
    recommendations: List[str]
    confidence_score: float
    timestamp: datetime


class WeatherAlertsResponse(BaseModel):
    """Weather alerts response"""
    location_name: str
    country: str
    alerts: List[Dict[str, Any]]
    total_alerts: int
    severity_levels: Dict[str, int]
    timestamp: datetime


class MultiLocationResponse(BaseModel):
    """Multiple locations response"""
    locations: Dict[str, Dict[str, Any]]
    summary: Dict[str, Any]
    total_locations: int
    successful_requests: int
    failed_requests: int
    timestamp: datetime


class CommodityWeatherResponse(BaseModel):
    """Commodity weather impact response"""
    commodities: Dict[str, Dict[str, Any]]
    regional_summary: Dict[str, Dict[str, Any]]
    overall_impact: Dict[str, float]
    alerts: List[Dict[str, Any]]
    recommendations: List[str]
    timestamp: datetime


# Helper functions
async def get_weather_client() -> WeatherClient:
    """Get weather client instance"""
    global _weather_client

    if not _weather_client:
        try:
            config = WeatherConfig()  # Use default configuration
            _weather_client = WeatherClient(config)
            logger.info("Weather client initialized")
        except Exception as e:
            logger.error("Failed to initialize weather client", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Weather service unavailable"
            )

    return _weather_client


def cache_key(prefix: str, *args) -> str:
    """Generate cache key for weather data"""
    return f"weather:{prefix}:{':'.join(str(arg) for arg in args)}"


async def get_cached_weather(key: str, ttl: int = 600) -> Optional[Dict[str, Any]]:
    """Get cached weather data"""
    if not _cache_manager:
        return None

    try:
        return await _cache_manager.get(key)
    except Exception as e:
        logger.warning("Weather cache get failed", key=key, error=str(e))
        return None


async def set_cached_weather(key: str, data: Dict[str, Any], ttl: int = 600):
    """Set cached weather data"""
    if not _cache_manager:
        return

    try:
        await _cache_manager.set(key, data, ttl=ttl)
    except Exception as e:
        logger.warning("Weather cache set failed", key=key, error=str(e))


def current_weather_to_response(weather: CurrentWeather, units: str) -> CurrentWeatherResponse:
    """Convert CurrentWeather to response model"""
    return CurrentWeatherResponse(
        location_name=weather.location_name,
        country=weather.country,
        coordinates={
            "latitude": weather.coordinates.latitude,
            "longitude": weather.coordinates.longitude
        },
        temperature=weather.temperature,
        feels_like=weather.feels_like,
        humidity=weather.humidity,
        pressure=weather.pressure,
        visibility=weather.visibility,
        uv_index=weather.uv_index,
        wind_speed=weather.wind_speed,
        wind_direction=weather.wind_direction,
        conditions=[{
            "main": condition.main,
            "description": condition.description,
            "icon": condition.icon
        } for condition in weather.conditions],
        sunrise=weather.sunrise,
        sunset=weather.sunset,
        timestamp=weather.timestamp,
        units=units
    )


# API Endpoints
@router.get(
    "/current",
    response_model=CurrentWeatherResponse,
    summary="Get Current Weather",
    description="""
    Get current weather conditions for a location.

    **Features:**
    - Real-time weather data
    - Multiple unit systems
    - Comprehensive conditions
    - Location coordinates
    - Sunrise/sunset times
    """
)
async def get_current_weather(
    city: str = Query(description="City name"),
    country: str = Query(default="IN", description="Country code"),
    state: Optional[str] = Query(None, description="State/region"),
    units: WeatherUnits = Query(default=WeatherUnits.METRIC, description="Unit system"),
    security_context: SecurityContext = Depends(get_security_context)
) -> CurrentWeatherResponse:
    """Get current weather for a location"""

    try:
        with structlog.contextvars.bound_contextvars(
            user_id=security_context.user_id,
            city=city,
            country=country,
            units=units.value
        ):
            logger.info("Current weather request")

            # Validate and normalize location
            city = city.strip().title()
            country = country.upper().strip()

            # Check cache
            cache_key_str = cache_key("current", city, country, state, units.value)
            cached_data = await get_cached_weather(cache_key_str, ttl=300)  # 5 minute cache

            if cached_data:
                logger.info("Returning cached weather data")
                return CurrentWeatherResponse(**cached_data)

            # Get weather client
            weather_client = await get_weather_client()

            # Create location query
            location_query = LocationQuery(
                city_name=city,
                country_code=country,
                state_code=state
            )

            # Fetch current weather
            current_weather = await weather_client.get_current_weather(location_query)

            # Convert to response
            response = current_weather_to_response(current_weather, units.value)

            # Cache response
            await set_cached_weather(cache_key_str, response.dict(), ttl=300)

            logger.info(
                "Current weather retrieved",
                location=f"{city}, {country}",
                temperature=current_weather.temperature
            )

            return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Current weather retrieval failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve current weather"
        )


@router.get(
    "/forecast",
    response_model=ForecastResponse,
    summary="Get Weather Forecast",
    description="""
    Get weather forecast for a location.

    **Features:**
    - Multi-day forecasts
    - Hourly and daily data
    - Temperature trends
    - Precipitation forecasts
    - Weather conditions
    """
)
async def get_weather_forecast(
    city: str = Query(description="City name"),
    country: str = Query(default="IN", description="Country code"),
    days: ForecastDays = Query(default=ForecastDays.THREE, description="Number of days"),
    units: WeatherUnits = Query(default=WeatherUnits.METRIC, description="Unit system"),
    include_hourly: bool = Query(default=False, description="Include hourly data"),
    security_context: SecurityContext = Depends(get_security_context)
) -> ForecastResponse:
    """Get weather forecast for a location"""

    try:
        with structlog.contextvars.bound_contextvars(
            user_id=security_context.user_id,
            city=city,
            country=country,
            days=days.value
        ):
            logger.info("Weather forecast request")

            city = city.strip().title()
            country = country.upper().strip()

            # Check cache
            cache_key_str = cache_key("forecast", city, country, days.value, units.value, include_hourly)
            cached_data = await get_cached_weather(cache_key_str, ttl=1800)  # 30 minute cache

            if cached_data:
                logger.info("Returning cached forecast data")
                return ForecastResponse(**cached_data)

            # Get weather client
            weather_client = await get_weather_client()

            # Create location query
            location_query = LocationQuery(
                city_name=city,
                country_code=country
            )

            # Fetch forecast
            forecasts = await weather_client.get_forecast(location_query, days=days.value)

            # Convert forecasts to response format
            forecast_data = []
            for forecast in forecasts:
                forecast_dict = {
                    "date": forecast.date.isoformat(),
                    "temperature": {
                        "min": forecast.temperature_min,
                        "max": forecast.temperature_max,
                        "avg": (forecast.temperature_min + forecast.temperature_max) / 2
                    },
                    "humidity": forecast.humidity,
                    "pressure": forecast.pressure,
                    "wind_speed": forecast.wind_speed,
                    "wind_direction": forecast.wind_direction,
                    "precipitation": {
                        "probability": forecast.precipitation_probability,
                        "amount": forecast.precipitation_amount
                    },
                    "conditions": [{
                        "main": condition.main,
                        "description": condition.description,
                        "icon": condition.icon
                    } for condition in forecast.conditions],
                    "uv_index": forecast.uv_index
                }

                # Add hourly data if requested
                if include_hourly and hasattr(forecast, 'hourly_data'):
                    forecast_dict["hourly"] = forecast.hourly_data

                forecast_data.append(forecast_dict)

            response = ForecastResponse(
                location_name=f"{city}",
                country=country,
                forecasts=forecast_data,
                total_days=len(forecast_data),
                timestamp=datetime.now(timezone.utc),
                units=units.value
            )

            # Cache response
            await set_cached_weather(cache_key_str, response.dict(), ttl=1800)

            logger.info(
                "Weather forecast retrieved",
                location=f"{city}, {country}",
                days=len(forecast_data)
            )

            return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Weather forecast retrieval failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve weather forecast"
        )


@router.get(
    "/insights",
    response_model=WeatherInsightsResponse,
    summary="Get Trading Weather Insights",
    description="""
    Get weather insights relevant for trading decisions.

    **Features:**
    - Agricultural impact analysis
    - Commodity price implications
    - Transportation risk assessment
    - Energy market impacts
    - Trading recommendations
    """
)
async def get_weather_insights(
    city: str = Query(description="City name"),
    country: str = Query(default="IN", description="Country code"),
    include_forecast: bool = Query(default=True, description="Include forecast in analysis"),
    focus_commodities: Optional[List[str]] = Query(None, description="Specific commodities to analyze"),
    security_context: SecurityContext = Depends(get_security_context)
) -> WeatherInsightsResponse:
    """Get weather insights for trading"""

    try:
        with structlog.contextvars.bound_contextvars(
            user_id=security_context.user_id,
            city=city,
            country=country,
            include_forecast=include_forecast
        ):
            logger.info("Weather insights request")

            city = city.strip().title()
            country = country.upper().strip()

            # Check cache
            cache_key_str = cache_key("insights", city, country, include_forecast, str(focus_commodities))
            cached_data = await get_cached_weather(cache_key_str, ttl=900)  # 15 minute cache

            if cached_data:
                logger.info("Returning cached insights")
                return WeatherInsightsResponse(**cached_data)

            # Get weather client
            weather_client = await get_weather_client()

            # Create location query
            location_query = LocationQuery(
                city_name=city,
                country_code=country
            )

            # Get trading insights
            insights = await weather_client.get_trading_insights(
                location_query,
                include_forecast=include_forecast
            )

            # Process insights data
            insights_data = {
                "crop_stress_index": insights.crop_stress_index,
                "drought_indicator": insights.drought_indicator,
                "flood_risk": insights.flood_risk,
                "frost_risk": insights.frost_risk,
                "heatwave_indicator": insights.heatwave_indicator,
                "transportation_disruption_risk": insights.transportation_disruption_risk,
                "energy_demand_impact": insights.energy_demand_impact
            }

            # Risk factors
            risk_factors = {
                "agricultural_risk": insights.crop_stress_index,
                "weather_volatility": 0.5,  # Calculate based on forecast variance
                "transportation_risk": insights.transportation_disruption_risk,
                "energy_impact": abs(insights.energy_demand_impact)
            }

            # Commodity impacts
            commodity_impacts = insights.commodity_price_impact or {}

            # Generate recommendations
            recommendations = []
            if insights.crop_stress_index > 0.7:
                recommendations.append("High crop stress detected - monitor agricultural commodity prices")
            if insights.drought_indicator:
                recommendations.append("Drought conditions may impact water-intensive crops")
            if insights.transportation_disruption_risk > 0.5:
                recommendations.append("Weather may disrupt transportation - consider logistics impacts")
            if abs(insights.energy_demand_impact) > 0.3:
                impact_type = "increase" if insights.energy_demand_impact > 0 else "decrease"
                recommendations.append(f"Weather conditions may {impact_type} energy demand")

            # Calculate confidence score
            confidence_score = 0.8  # Simplified calculation

            response = WeatherInsightsResponse(
                location_name=f"{city}",
                country=country,
                insights=insights_data,
                risk_factors=risk_factors,
                commodity_impacts=commodity_impacts,
                recommendations=recommendations,
                confidence_score=confidence_score,
                timestamp=datetime.now(timezone.utc)
            )

            # Cache response
            await set_cached_weather(cache_key_str, response.dict(), ttl=900)

            logger.info(
                "Weather insights retrieved",
                location=f"{city}, {country}",
                recommendations=len(recommendations),
                confidence=confidence_score
            )

            return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Weather insights retrieval failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve weather insights"
        )


@router.get(
    "/alerts",
    response_model=WeatherAlertsResponse,
    summary="Get Weather Alerts",
    description="""
    Get weather alerts and warnings for a location.

    **Features:**
    - Government weather alerts
    - Severity classification
    - Impact assessment
    - Time-sensitive warnings
    - Trading relevance scoring
    """
)
async def get_weather_alerts(
    city: str = Query(description="City name"),
    country: str = Query(default="IN", description="Country code"),
    include_expired: bool = Query(default=False, description="Include expired alerts"),
    min_severity: str = Query(default="moderate", description="Minimum severity level"),
    security_context: SecurityContext = Depends(get_security_context)
) -> WeatherAlertsResponse:
    """Get weather alerts for a location"""

    try:
        with structlog.contextvars.bound_contextvars(
            user_id=security_context.user_id,
            city=city,
            country=country,
            min_severity=min_severity
        ):
            logger.info("Weather alerts request")

            city = city.strip().title()
            country = country.upper().strip()

            # Check cache
            cache_key_str = cache_key("alerts", city, country, include_expired, min_severity)
            cached_data = await get_cached_weather(cache_key_str, ttl=300)  # 5 minute cache

            if cached_data:
                logger.info("Returning cached alerts")
                return WeatherAlertsResponse(**cached_data)

            # Get weather client
            weather_client = await get_weather_client()

            # Create location query
            location_query = LocationQuery(
                city_name=city,
                country_code=country
            )

            # Get weather alerts
            try:
                alerts = await weather_client.get_weather_alerts(location_query)
            except Exception as e:
                logger.warning("Weather alerts not available", error=str(e))
                alerts = []

            # Process alerts
            alert_data = []
            severity_counts = {"minor": 0, "moderate": 0, "severe": 0, "extreme": 0}

            for alert in alerts:
                alert_dict = {
                    "id": alert.id,
                    "title": alert.title,
                    "description": alert.description,
                    "severity": alert.severity,
                    "urgency": alert.urgency,
                    "certainty": alert.certainty,
                    "areas": alert.areas,
                    "start_time": alert.start_time.isoformat() if alert.start_time else None,
                    "end_time": alert.end_time.isoformat() if alert.end_time else None,
                    "event_type": alert.event_type,
                    "trading_relevance": getattr(alert, 'trading_relevance', 0.5)
                }

                # Count severity levels
                if alert.severity in severity_counts:
                    severity_counts[alert.severity] += 1

                alert_data.append(alert_dict)

            response = WeatherAlertsResponse(
                location_name=f"{city}",
                country=country,
                alerts=alert_data,
                total_alerts=len(alert_data),
                severity_levels=severity_counts,
                timestamp=datetime.now(timezone.utc)
            )

            # Cache response
            await set_cached_weather(cache_key_str, response.dict(), ttl=300)

            logger.info(
                "Weather alerts retrieved",
                location=f"{city}, {country}",
                alerts=len(alert_data),
                severe_alerts=severity_counts.get("severe", 0) + severity_counts.get("extreme", 0)
            )

            return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Weather alerts retrieval failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve weather alerts"
        )


@router.post(
    "/locations",
    response_model=MultiLocationResponse,
    summary="Monitor Multiple Locations",
    description="""
    Get weather data for multiple locations simultaneously.

    **Features:**
    - Batch weather requests
    - Parallel processing
    - Aggregated insights
    - Regional comparisons
    - Efficient API usage
    """
)
async def monitor_multiple_locations(
    request: MultiLocationRequest,
    units: WeatherUnits = Query(default=WeatherUnits.METRIC, description="Unit system"),
    security_context: SecurityContext = Depends(get_security_context)
) -> MultiLocationResponse:
    """Monitor weather for multiple locations"""

    try:
        with structlog.contextvars.bound_contextvars(
            user_id=security_context.user_id,
            locations_count=len(request.locations),
            data_types=request.data_types
        ):
            logger.info("Multi-location weather request")

            if not request.locations:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="At least one location is required"
                )

            # Get weather client
            weather_client = await get_weather_client()

            # Process locations
            location_data = {}
            successful_requests = 0
            failed_requests = 0

            for location_req in request.locations:
                location_key = f"{location_req.city}, {location_req.country}"

                try:
                    location_query = LocationQuery(
                        city_name=location_req.city,
                        country_code=location_req.country,
                        state_code=location_req.state
                    )

                    location_info = {"location": location_key}

                    # Get requested data types
                    if "current" in request.data_types:
                        current = await weather_client.get_current_weather(location_query)
                        location_info["current"] = current_weather_to_response(current, units.value).dict()

                    if "forecast" in request.data_types:
                        forecasts = await weather_client.get_forecast(location_query, days=3)
                        location_info["forecast"] = [
                            {
                                "date": f.date.isoformat(),
                                "temp_min": f.temperature_min,
                                "temp_max": f.temperature_max,
                                "conditions": [{"main": c.main, "description": c.description} for c in f.conditions]
                            } for f in forecasts
                        ]

                    if "insights" in request.data_types and request.include_insights:
                        insights = await weather_client.get_trading_insights(location_query, include_forecast=False)
                        location_info["insights"] = {
                            "crop_stress_index": insights.crop_stress_index,
                            "drought_indicator": insights.drought_indicator,
                            "transportation_risk": insights.transportation_disruption_risk
                        }

                    location_data[location_key] = location_info
                    successful_requests += 1

                except Exception as e:
                    logger.warning("Failed to get weather for location", location=location_key, error=str(e))
                    location_data[location_key] = {
                        "location": location_key,
                        "error": str(e),
                        "status": "failed"
                    }
                    failed_requests += 1

            # Generate summary
            summary = {
                "total_locations": len(request.locations),
                "successful": successful_requests,
                "failed": failed_requests,
                "data_types_requested": request.data_types,
                "average_temperature": 0.0,
                "locations_with_alerts": 0,
                "high_risk_locations": 0
            }

            # Calculate summary statistics
            temperatures = []
            for loc_data in location_data.values():
                if "current" in loc_data and "temperature" in loc_data["current"]:
                    temperatures.append(loc_data["current"]["temperature"])

                if "insights" in loc_data:
                    insights = loc_data["insights"]
                    if (insights.get("crop_stress_index", 0) > 0.7 or
                        insights.get("transportation_risk", 0) > 0.5):
                        summary["high_risk_locations"] += 1

            if temperatures:
                summary["average_temperature"] = sum(temperatures) / len(temperatures)

            response = MultiLocationResponse(
                locations=location_data,
                summary=summary,
                total_locations=len(request.locations),
                successful_requests=successful_requests,
                failed_requests=failed_requests,
                timestamp=datetime.now(timezone.utc)
            )

            logger.info(
                "Multi-location weather completed",
                successful=successful_requests,
                failed=failed_requests,
                avg_temp=summary["average_temperature"]
            )

            return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Multi-location weather failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve multi-location weather"
        )


@router.get(
    "/commodities",
    response_model=CommodityWeatherResponse,
    summary="Get Commodity Weather Impact",
    description="""
    Get weather impact analysis for specific commodities.

    **Features:**
    - Commodity-specific analysis
    - Regional weather monitoring
    - Price impact assessment
    - Production forecasts
    - Risk recommendations
    """
)
async def get_commodity_weather_impact(
    commodities: List[str] = Query(description="Commodity symbols (e.g., WHEAT,CORN,SOYBEAN)"),
    regions: Optional[List[str]] = Query(None, description="Specific regions"),
    forecast_days: ForecastDays = Query(default=ForecastDays.SEVEN, description="Forecast period"),
    security_context: SecurityContext = Depends(get_security_context)
) -> CommodityWeatherResponse:
    """Get weather impact for commodities"""

    try:
        with structlog.contextvars.bound_contextvars(
            user_id=security_context.user_id,
            commodities=commodities[:5],  # Limit logging
            forecast_days=forecast_days.value
        ):
            logger.info("Commodity weather impact request")

            if not commodities:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="At least one commodity is required"
                )

            # Check cache
            cache_key_str = cache_key("commodities", str(commodities), str(regions), forecast_days.value)
            cached_data = await get_cached_weather(cache_key_str, ttl=3600)  # 1 hour cache

            if cached_data:
                logger.info("Returning cached commodity analysis")
                return CommodityWeatherResponse(**cached_data)

            # Get weather client
            weather_client = await get_weather_client()

            # Commodity-specific production regions (simplified mapping)
            commodity_regions = {
                "WHEAT": ["Punjab, IN", "Haryana, IN", "Uttar Pradesh, IN"],
                "RICE": ["West Bengal, IN", "Punjab, IN", "Odisha, IN"],
                "CORN": ["Karnataka, IN", "Andhra Pradesh, IN", "Maharashtra, IN"],
                "SOYBEAN": ["Madhya Pradesh, IN", "Maharashtra, IN", "Rajasthan, IN"],
                "COTTON": ["Gujarat, IN", "Maharashtra, IN", "Telangana, IN"],
                "SUGAR": ["Uttar Pradesh, IN", "Maharashtra, IN", "Karnataka, IN"]
            }

            commodity_data = {}
            regional_summary = {}
            overall_impact = {"price_impact": 0.0, "production_risk": 0.0, "supply_risk": 0.0}
            alerts = []
            recommendations = []

            for commodity in commodities:
                commodity = commodity.upper().strip()

                # Get relevant regions for this commodity
                relevant_regions = regions or commodity_regions.get(commodity, ["Delhi, IN"])

                commodity_info = {
                    "commodity": commodity,
                    "regions_monitored": relevant_regions,
                    "weather_impact": {},
                    "risk_assessment": {},
                    "production_forecast": "stable"  # Simplified
                }

                region_impacts = []

                for region in relevant_regions:
                    try:
                        # Parse region (city, country)
                        if "," in region:
                            city, country = region.split(",", 1)
                            city = city.strip()
                            country = country.strip()
                        else:
                            city = region.strip()
                            country = "IN"

                        location_query = LocationQuery(
                            city_name=city,
                            country_code=country
                        )

                        # Get weather insights for this region
                        insights = await weather_client.get_trading_insights(
                            location_query,
                            include_forecast=True
                        )

                        region_impact = {
                            "location": region,
                            "crop_stress": insights.crop_stress_index,
                            "drought_risk": insights.drought_indicator,
                            "flood_risk": insights.flood_risk,
                            "temperature_stress": 1.0 if insights.crop_stress_index > 0.7 else 0.0
                        }

                        region_impacts.append(region_impact)
                        regional_summary[region] = region_impact

                        # Generate alerts for high risk
                        if insights.crop_stress_index > 0.8:
                            alerts.append({
                                "type": "HIGH_CROP_STRESS",
                                "commodity": commodity,
                                "region": region,
                                "severity": "high",
                                "message": f"High crop stress detected in {region} for {commodity}"
                            })

                        if insights.drought_indicator:
                            alerts.append({
                                "type": "DROUGHT_WARNING",
                                "commodity": commodity,
                                "region": region,
                                "severity": "moderate",
                                "message": f"Drought conditions detected in {region}"
                            })

                    except Exception as e:
                        logger.warning("Failed to get weather for region", region=region, error=str(e))
                        continue

                # Calculate commodity-level impacts
                if region_impacts:
                    avg_crop_stress = sum(r["crop_stress"] for r in region_impacts) / len(region_impacts)
                    drought_regions = sum(1 for r in region_impacts if r["drought_risk"])

                    commodity_info["weather_impact"] = {
                        "average_crop_stress": avg_crop_stress,
                        "drought_affected_regions": drought_regions,
                        "total_regions": len(region_impacts),
                        "high_risk_regions": sum(1 for r in region_impacts if r["crop_stress"] > 0.7)
                    }

                    commodity_info["risk_assessment"] = {
                        "production_risk": min(avg_crop_stress * 1.2, 1.0),
                        "supply_chain_risk": drought_regions / len(region_impacts) if region_impacts else 0,
                        "price_volatility_risk": avg_crop_stress * 0.8
                    }

                    # Update overall impact
                    overall_impact["price_impact"] += commodity_info["risk_assessment"]["price_volatility_risk"]
                    overall_impact["production_risk"] += commodity_info["risk_assessment"]["production_risk"]
                    overall_impact["supply_risk"] += commodity_info["risk_assessment"]["supply_chain_risk"]

                commodity_data[commodity] = commodity_info

            # Normalize overall impact
            num_commodities = len(commodities)
            if num_commodities > 0:
                overall_impact = {k: v / num_commodities for k, v in overall_impact.items()}

            # Generate recommendations
            if overall_impact["price_impact"] > 0.6:
                recommendations.append("High price volatility expected - consider hedging strategies")
            if overall_impact["production_risk"] > 0.7:
                recommendations.append("Production risks elevated - monitor supply forecasts closely")
            if len(alerts) > 3:
                recommendations.append("Multiple weather alerts active - review commodity exposure")

            response = CommodityWeatherResponse(
                commodities=commodity_data,
                regional_summary=regional_summary,
                overall_impact=overall_impact,
                alerts=alerts,
                recommendations=recommendations,
                timestamp=datetime.now(timezone.utc)
            )

            # Cache response
            await set_cached_weather(cache_key_str, response.dict(), ttl=3600)

            logger.info(
                "Commodity weather analysis completed",
                commodities=len(commodity_data),
                alerts=len(alerts),
                overall_risk=overall_impact["price_impact"]
            )

            return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Commodity weather analysis failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze commodity weather impact"
        )


# Health check endpoint
@router.get(
    "/health",
    summary="Weather Service Health Check",
    description="Check the health status of weather service and API"
)
async def weather_health_check(
    security_context: SecurityContext = Depends(get_security_context)
) -> Dict[str, Any]:
    """Check weather service health"""

    try:
        # Get weather client
        weather_client = await get_weather_client()

        # Perform health check
        health_status = await weather_client.health_check()

        logger.info("Weather health check completed", status=health_status.get("status"))
        return health_status

    except Exception as e:
        logger.error("Weather health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# Initialization function
def init_weather_routes(
    db_manager: DatabaseManager,
    cache_manager: CacheManager,
    weather_config: Optional[WeatherConfig] = None
) -> APIRouter:
    """Initialize weather routes"""
    global _db_manager, _cache_manager, _weather_client

    _db_manager = db_manager
    _cache_manager = cache_manager

    # Initialize weather client with config
    try:
        config = weather_config or WeatherConfig()
        _weather_client = WeatherClient(config)
        logger.info("Weather routes initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize weather client", error=str(e))
        _weather_client = None

    return router


# Export
__all__ = [
    "router",
    "init_weather_routes",
    "LocationRequest",
    "MultiLocationRequest",
    "CommodityWeatherRequest",
    "CurrentWeatherResponse",
    "ForecastResponse",
    "WeatherInsightsResponse",
    "WeatherAlertsResponse",
    "MultiLocationResponse",
    "CommodityWeatherResponse",
    "WeatherUnits",
    "ForecastDays"
]
