"""
OpenWeatherMap API Client
A comprehensive client for weather data with robust error handling and monitoring
Designed for trading insights and agricultural/energy commodity analysis
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import hashlib
import secrets
from enum import Enum

import httpx
from pydantic import BaseModel, Field, field_validator

try:
    from ..utils.logger import get_logger, log_performance, LogContext  # type: ignore[assignment]
except ImportError:
    # Fallback for standalone usage
    import logging

    def get_logger(name: str) -> logging.Logger:
        """Simple logger fallback"""
        logger = logging.getLogger(name)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        return logger

    def log_performance(func_name: Optional[str] = None):
        """Simple performance logging decorator fallback"""

        def decorator(func):
            return func

        return decorator

    class LogContext:
        """Simple context manager fallback"""

        def __init__(self, **kwargs: Any) -> None:
            pass

        def __enter__(self) -> "LogContext":
            return self

        def __exit__(self, *args: Any) -> None:
            pass


class WeatherUnits(str, Enum):
    """Weather data units"""

    METRIC = "metric"  # Celsius, m/s, mm
    IMPERIAL = "imperial"  # Fahrenheit, mph, inches
    KELVIN = "kelvin"  # Kelvin, m/s, mm (default)


class WeatherLang(str, Enum):
    """Supported languages"""

    ENGLISH = "en"
    HINDI = "hi"
    MARATHI = "mr"
    BENGALI = "bn"
    GUJARATI = "gu"
    TAMIL = "ta"
    TELUGU = "te"


class WeatherConfig(BaseModel):
    """OpenWeatherMap API configuration"""

    api_key: Optional[str] = None
    base_url: str = Field(default="https://api.openweathermap.org/data/2.5")
    geocoding_url: str = Field(default="http://api.openweathermap.org/geo/1.0")
    onecall_url: str = Field(default="https://api.openweathermap.org/data/3.0")

    timeout: int = Field(default=15)
    max_retries: int = Field(default=3)
    retry_delay: float = Field(default=1.0)

    # Rate limiting (OpenWeatherMap allows 60 calls/minute for free tier)
    rate_limit_calls_per_minute: int = Field(default=50)  # Conservative limit
    rate_limit_calls_per_month: int = Field(default=1000000)  # Free tier limit

    # Cache settings
    current_weather_cache_minutes: int = Field(
        default=10
    )  # Current weather changes slowly
    forecast_cache_minutes: int = Field(default=60)  # Forecasts updated hourly
    alerts_cache_minutes: int = Field(default=5)  # Alerts are time-sensitive
    historical_cache_minutes: int = Field(default=1440)  # Historical data is static

    # Default settings
    default_units: WeatherUnits = Field(default=WeatherUnits.METRIC)
    default_language: WeatherLang = Field(default=WeatherLang.ENGLISH)

    # Trading-specific settings
    enable_commodity_analysis: bool = Field(default=True)
    enable_weather_alerts: bool = Field(default=True)
    enable_agricultural_insights: bool = Field(default=True)
    enable_energy_insights: bool = Field(default=True)


class WeatherCondition(BaseModel):
    """Weather condition details"""

    id: int
    main: str  # Rain, Snow, Clear, etc.
    description: str  # Light rain, heavy snow, etc.
    icon: str  # Weather icon ID


class CurrentWeather(BaseModel):
    """Current weather data model"""

    # Location
    location_name: str
    country: str
    latitude: float
    longitude: float
    timezone: int  # UTC offset in seconds

    # Weather data
    timestamp: datetime
    temperature: float
    feels_like: float
    pressure: int  # hPa
    humidity: int  # %
    visibility: Optional[int] = None  # meters
    uv_index: Optional[float] = None

    # Wind
    wind_speed: float  # m/s
    wind_direction: int  # degrees
    wind_gust: Optional[float] = None  # m/s

    # Precipitation
    rain_1h: Optional[float] = None  # mm
    rain_3h: Optional[float] = None  # mm
    snow_1h: Optional[float] = None  # mm
    snow_3h: Optional[float] = None  # mm

    # Weather conditions
    conditions: List[WeatherCondition]
    cloudiness: int  # %

    # Sun/Moon
    sunrise: datetime
    sunset: datetime

    # Additional data
    units: WeatherUnits
    raw_data: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("timestamp", "sunrise", "sunset", mode="before")
    @classmethod
    def parse_timestamp(cls, v):
        if isinstance(v, (int, float)):
            return datetime.fromtimestamp(v)
        return v


class WeatherForecast(BaseModel):
    """Weather forecast data model"""

    timestamp: datetime
    temperature: float
    feels_like: float
    temperature_min: float
    temperature_max: float

    pressure: int
    humidity: int

    wind_speed: float
    wind_direction: int
    wind_gust: Optional[float] = None

    rain: Optional[float] = None  # mm
    snow: Optional[float] = None  # mm

    conditions: List[WeatherCondition]
    cloudiness: int

    probability_of_precipitation: float  # 0-1

    @field_validator("timestamp", mode="before")
    @classmethod
    def parse_timestamp(cls, v):
        if isinstance(v, (int, float)):
            return datetime.fromtimestamp(v)
        return v


class WeatherAlert(BaseModel):
    """Weather alert/warning model"""

    sender_name: str
    event: str  # Alert type (e.g., "Thunderstorm", "Heat Wave")
    start: datetime
    end: datetime
    description: str
    tags: List[str] = Field(default_factory=list)

    @field_validator("start", "end", mode="before")
    @classmethod
    def parse_timestamp(cls, v):
        if isinstance(v, (int, float)):
            return datetime.fromtimestamp(v)
        return v


class WeatherInsights(BaseModel):
    """Trading-relevant weather insights"""

    # Agricultural impact
    crop_stress_index: Optional[float] = None  # 0-1, higher = more stress
    drought_indicator: Optional[bool] = None
    frost_risk: Optional[bool] = None
    growing_degree_days: Optional[float] = None

    # Energy impact
    heating_degree_days: Optional[float] = None
    cooling_degree_days: Optional[float] = None
    wind_power_potential: Optional[float] = None  # 0-1
    solar_power_potential: Optional[float] = None  # 0-1

    # General trading impact
    transportation_disruption_risk: Optional[str] = None  # low, medium, high
    commodity_price_impact: Dict[str, str] = Field(
        default_factory=dict
    )  # commodity -> impact

    # Alert summary
    active_alerts_count: int = 0
    high_priority_alerts: List[str] = Field(default_factory=list)


class LocationQuery(BaseModel):
    """Location query model"""

    # One of these must be provided
    city_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    zip_code: Optional[str] = None

    # Optional
    state_code: Optional[str] = None  # US state or country subdivision
    country_code: Optional[str] = None  # ISO 3166 country code

    @field_validator("city_name")
    @classmethod
    def validate_city_name(cls, v):
        if v and len(v.strip()) < 2:
            raise ValueError("City name must be at least 2 characters")
        return v.strip() if v else v

    def to_query_string(self) -> str:
        """Convert to OpenWeatherMap query string"""
        if self.latitude is not None and self.longitude is not None:
            return f"lat={self.latitude}&lon={self.longitude}"
        elif self.city_name:
            query = self.city_name
            if self.state_code:
                query += f",{self.state_code}"
            if self.country_code:
                query += f",{self.country_code}"
            return f"q={query}"
        elif self.zip_code:
            zip_query = self.zip_code
            if self.country_code:
                zip_query += f",{self.country_code}"
            return f"zip={zip_query}"
        else:
            raise ValueError("Must provide either coordinates, city name, or zip code")


class WeatherCache:
    """Intelligent caching system for weather data"""

    def __init__(self):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.expiry: Dict[str, datetime] = {}

    def _generate_key(self, endpoint: str, query: LocationQuery, **params) -> str:
        """Generate cache key from request parameters"""
        query_str = query.to_query_string()
        params_str = json.dumps(params, sort_keys=True, default=str)
        key_data = f"{endpoint}:{query_str}:{params_str}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def get(self, endpoint: str, query: LocationQuery, **params) -> Optional[Any]:
        """Get cached data if not expired"""
        key = self._generate_key(endpoint, query, **params)

        if key not in self.cache:
            return None

        if key in self.expiry and datetime.now() > self.expiry[key]:
            # Cache expired
            del self.cache[key]
            del self.expiry[key]
            return None

        return self.cache[key]

    def set(
        self, endpoint: str, query: LocationQuery, data: Any, ttl_minutes: int, **params
    ) -> None:
        """Cache data with TTL"""
        key = self._generate_key(endpoint, query, **params)
        self.cache[key] = data
        self.expiry[key] = datetime.now() + timedelta(minutes=ttl_minutes)

    def clear(self) -> None:
        """Clear all cache"""
        self.cache.clear()
        self.expiry.clear()

    def clear_expired(self) -> None:
        """Clear expired cache entries"""
        now = datetime.now()
        expired_keys = [key for key, exp_time in self.expiry.items() if now > exp_time]
        for key in expired_keys:
            self.cache.pop(key, None)
            self.expiry.pop(key, None)

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        now = datetime.now()
        expired_count = len([k for k, v in self.expiry.items() if now > v])

        return {
            "total_entries": len(self.cache),
            "expired_entries": expired_count,
            "active_entries": len(self.cache) - expired_count,
            "memory_size": len(json.dumps(self.cache, default=str)),
        }


class RateLimiter:
    """Rate limiting for OpenWeatherMap API"""

    def __init__(
        self, max_calls_per_minute: int = 50, max_calls_per_month: int = 1000000
    ):
        self.max_calls_per_minute = max_calls_per_minute
        self.max_calls_per_month = max_calls_per_month

        # Track calls per minute
        self.minute_calls: List[float] = []

        # Track calls per month (simplified - in production use persistent storage)
        self.month_calls = 0
        self.month_start = datetime.now().replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )

    async def wait_if_needed(self) -> None:
        """Wait if rate limit is exceeded"""
        now = time.time()

        # Reset monthly counter if new month
        current_month_start = datetime.now().replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        if current_month_start > self.month_start:
            self.month_calls = 0
            self.month_start = current_month_start

        # Check monthly limit
        if self.month_calls >= self.max_calls_per_month:
            raise WeatherError("Monthly API call limit exceeded")

        # Clean old calls (older than 1 minute)
        self.minute_calls = [
            call_time for call_time in self.minute_calls if now - call_time < 60
        ]

        # Check per-minute limit
        if len(self.minute_calls) >= self.max_calls_per_minute:
            oldest_call = min(self.minute_calls)
            wait_time = 60 - (now - oldest_call)
            if wait_time > 0:
                await asyncio.sleep(wait_time)
                # Clean again after waiting
                now = time.time()
                self.minute_calls = [
                    call_time for call_time in self.minute_calls if now - call_time < 60
                ]

        # Record this call
        self.minute_calls.append(now)
        self.month_calls += 1


class CircuitBreaker:
    """Circuit breaker pattern for API resilience"""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout

        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    async def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if self.state == "OPEN":
            if (
                self.last_failure_time
                and (datetime.now() - self.last_failure_time).seconds
                < self.recovery_timeout
            ):
                raise WeatherError(
                    "Circuit breaker OPEN - service temporarily unavailable"
                )
            else:
                self.state = "HALF_OPEN"

        try:
            result = await func(*args, **kwargs)
            # Success - reset circuit breaker
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
            return result

        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = datetime.now()

            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"

            raise e


# Exception classes
class WeatherError(Exception):
    """Base exception for Weather API errors"""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        status_code: Optional[int] = None,
        response_data: Optional[Dict] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.response_data = response_data or {}


class AuthenticationError(WeatherError):
    """API authentication errors"""

    pass


class RateLimitError(WeatherError):
    """Rate limit exceeded errors"""

    pass


class ValidationError(WeatherError):
    """Request validation errors"""

    pass


class NetworkError(WeatherError):
    """Network related errors"""

    pass


class DataNotFoundError(WeatherError):
    """Location/data not found errors"""

    pass


class WeatherClient:
    """
    Comprehensive OpenWeatherMap API Client for Trading Applications

    Features:
    - Complete weather data integration (current, forecast, historical, alerts) - Advanced error handling with circuit breaker pattern - Intelligent caching with different TTLs per data type - Rate limiting to respect API quotas - Trading-specific insights and analysis - Agricultural and energy market indicators - Multi-location monitoring capabilities - Async operations with connection pooling - Comprehensive logging and monitoring - Automatic retry with exponential backoff -
    Data validation and sanitization
    """

    def __init__(self, config: Optional[WeatherConfig] = None):
        """
        Initialize Weather client

        Args:
            config: Weather API configuration
        """
        self.config = config or WeatherConfig()
        self.logger = get_logger("niraj.weather")

        # Session management
        self.session_id = secrets.token_hex(16)
        self.client: Optional[httpx.AsyncClient] = None

        # Rate limiting and resilience
        self.rate_limiter = RateLimiter(
            max_calls_per_minute=self.config.rate_limit_calls_per_minute,
            max_calls_per_month=self.config.rate_limit_calls_per_month,
        )
        self.circuit_breaker = CircuitBreaker()

        # Caching
        self.cache = WeatherCache()

        # Statistics
        self.stats = {
            "requests_made": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "errors": 0,
            "locations_queried": set(),
            "data_types_requested": set(),
        }

        # Trading insights
        self.commodity_symbols = {
            "wheat": ["wheat", "grain", "agriculture"],
            "corn": ["corn", "maize", "grain"],
            "soybean": ["soy", "soybean", "agriculture"],
            "rice": ["rice", "grain"],
            "cotton": ["cotton", "fiber"],
            "sugar": ["sugar", "cane"],
            "coffee": ["coffee", "bean"],
            "crude_oil": ["energy", "oil"],
            "natural_gas": ["gas", "energy"],
            "coal": ["coal", "energy"],
        }

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self.client is None or self.client.is_closed:
            timeout = httpx.Timeout(self.config.timeout)
            limits = httpx.Limits(max_keepalive_connections=10, max_connections=50)

            self.client = httpx.AsyncClient(
                timeout=timeout,
                limits=limits,
                http2=True,
                follow_redirects=True,
                headers={
                    "User-Agent": "NIRAJ-Trading-System/1.0 (Weather Analytics)",
                    "Accept": "application/json",
                    "Accept-Encoding": "gzip, deflate",
                },
            )

        return self.client

    async def _make_request(
        self,
        endpoint: str,
        query: LocationQuery,
        params: Optional[Dict] = None,
        base_url: Optional[str] = None,
        cache_ttl: int = 10,
    ) -> Dict[str, Any]:
        """
        Make HTTP request with comprehensive error handling

        Args:
            endpoint: API endpoint
            query: Location query
            params: Additional parameters
            base_url: Override base URL
            cache_ttl: Cache TTL in minutes

        Returns:
            Response data as dictionary

        Raises:
            Various WeatherError subclasses based on error type
        """
        if not self.config.api_key:
            raise AuthenticationError("OpenWeatherMap API key not configured")

        # Check cache first
        cache_data = self.cache.get(endpoint, query, **(params or {}))
        if cache_data:
            self.stats["cache_hits"] += 1
            return cache_data

        self.stats["cache_misses"] += 1

        # Prepare request parameters
        request_params: Dict[str, Any] = params.copy() if params else {}
        request_params["appid"] = self.config.api_key

        # Parse query string and add to params
        query_string = query.to_query_string()
        for param_pair in query_string.split("&"):
            if "=" in param_pair:
                k, v = param_pair.split("=", 1)
                request_params[k] = v

        # Clean up params (convert k=v strings to dict if needed)
        clean_params: Dict[str, Any] = {}
        for key, value in request_params.items():
            if isinstance(value, str) and "=" in value and key not in ["appid", "q", "zip"]:
                k, v = value.split("=", 1)
                clean_params[k] = v
            else:
                clean_params[key] = value

        url = f"{base_url or self.config.base_url}/{endpoint}"

        # Use circuit breaker protection
        async def make_api_request():
            # Apply rate limiting
            await self.rate_limiter.wait_if_needed()

            client = await self._get_client()

            with LogContext(
                session_id=self.session_id,
                endpoint=endpoint,
                location=str(query.city_name or f"{query.latitude},{query.longitude}"),
                request_id=secrets.token_hex(8),
            ):
                self.logger.debug(f"Making weather API request to {endpoint}")

                for attempt in range(self.config.max_retries + 1):
                    try:
                        response = await client.get(url, params=clean_params)
                        self.stats["requests_made"] += 1

                        # Handle different response codes
                        if response.status_code == 200:
                            try:
                                data = response.json()
                                # Cache successful response
                                self.cache.set(
                                    endpoint, query, data, cache_ttl, **clean_params
                                )
                                return data
                            except json.JSONDecodeError as e:
                                raise WeatherError(f"Invalid JSON response: {e}")

                        elif response.status_code == 401:
                            raise AuthenticationError(
                                "Invalid API key", status_code=response.status_code
                            )

                        elif response.status_code == 404:
                            raise DataNotFoundError(
                                f"Location not found: {query.city_name or query.zip_code or 'coordinates'}",
                                status_code=response.status_code,
                            )

                        elif response.status_code == 429:
                            if attempt < self.config.max_retries:
                                wait_time = (2**attempt) * 2
                                self.logger.warning(
                                    f"Rate limit hit, waiting {wait_time}s"
                                )
                                await asyncio.sleep(wait_time)
                                continue
                            raise RateLimitError(
                                "API rate limit exceeded",
                                status_code=response.status_code,
                            )

                        elif response.status_code >= 500:
                            if attempt < self.config.max_retries:
                                wait_time = self.config.retry_delay * (2**attempt)
                                self.logger.warning(
                                    f"Server error, retrying in {wait_time}s"
                                )
                                await asyncio.sleep(wait_time)
                                continue
                            raise WeatherError(
                                f"Server error: {response.status_code}",
                                status_code=response.status_code,
                            )

                        else:
                            raise WeatherError(
                                f"HTTP {response.status_code}: {response.text[:200]}",
                                status_code=response.status_code,
                            )

                    except httpx.TimeoutException:
                        if attempt < self.config.max_retries:
                            wait_time = self.config.retry_delay * (2**attempt)
                            self.logger.warning(
                                f"Request timeout, retrying in {wait_time}s"
                            )
                            await asyncio.sleep(wait_time)
                            continue
                        raise NetworkError("Request timeout")

                    except httpx.NetworkError as e:
                        if attempt < self.config.max_retries:
                            wait_time = self.config.retry_delay * (2**attempt)
                            self.logger.warning(
                                f"Network error: {e}, retrying in {wait_time}s"
                            )
                            await asyncio.sleep(wait_time)
                            continue
                        raise NetworkError(f"Network error: {e}")

                raise WeatherError("All retry attempts failed")

        try:
            return await self.circuit_breaker.call(make_api_request)
        except Exception as e:
            self.stats["errors"] += 1
            self.logger.error(f"Weather API request failed: {e}")
            raise

    def _calculate_insights(
        self,
        current: Optional[CurrentWeather],
        forecasts: Optional[List[WeatherForecast]] = None,
        alerts: Optional[List[WeatherAlert]] = None,
    ) -> WeatherInsights:
        """Calculate trading-relevant weather insights"""
        insights = WeatherInsights()

        if not current:
            return insights

        # Agricultural insights
        if self.config.enable_agricultural_insights:
            # Crop stress index based on temperature and humidity
            if current.temperature > 35:  # High temperature stress
                insights.crop_stress_index = min(1.0, (current.temperature - 35) / 10)
            elif current.temperature < 5:  # Cold stress
                insights.crop_stress_index = min(1.0, (5 - current.temperature) / 10)

            # Drought indicator
            if current.humidity < 30 and current.rain_1h is None:
                insights.drought_indicator = True

            # Frost risk
            if current.temperature <= 2:
                insights.frost_risk = True

            # Growing degree days (simplified calculation)
            base_temp = 10  # Base temperature for most crops
            if current.temperature > base_temp:
                insights.growing_degree_days = current.temperature - base_temp

        # Energy insights
        if self.config.enable_energy_insights:
            # Heating degree days
            if current.temperature < 18:
                insights.heating_degree_days = 18 - current.temperature

            # Cooling degree days
            if current.temperature > 24:
                insights.cooling_degree_days = current.temperature - 24

            # Wind power potential (simplified)
            if 3 <= current.wind_speed <= 25:  # Optimal wind speed range
                insights.wind_power_potential = min(1.0, current.wind_speed / 15)

            # Solar power potential
            cloud_factor = (100 - current.cloudiness) / 100
            uv_factor = (
                min(1.0, (current.uv_index or 0) / 10) if current.uv_index else 0.5
            )
            insights.solar_power_potential = (cloud_factor + uv_factor) / 2

        # Transportation and commodity impacts
        severe_weather = any(
            c.main.lower() in ["thunderstorm", "snow", "fog"]
            for c in current.conditions
        )

        if severe_weather or current.wind_speed > 15:
            insights.transportation_disruption_risk = "high"
        elif current.rain_1h and current.rain_1h > 5:
            insights.transportation_disruption_risk = "medium"
        else:
            insights.transportation_disruption_risk = "low"

        # Commodity price impacts
        if self.config.enable_commodity_analysis:
            if insights.crop_stress_index and insights.crop_stress_index > 0.5:
                insights.commodity_price_impact.update(
                    {"wheat": "bullish", "corn": "bullish", "rice": "bullish"}
                )

            if insights.frost_risk:
                insights.commodity_price_impact.update(
                    {"orange_juice": "bullish", "coffee": "bullish", "sugar": "bullish"}
                )

            if current.temperature > 30:
                insights.commodity_price_impact.update(
                    {
                        "natural_gas": "bearish",  # Less heating demand
                        "electricity": "bullish",  # More cooling demand
                    }
                )

        # Alert analysis
        if alerts:
            insights.active_alerts_count = len(alerts)
            high_priority = [
                "Thunderstorm",
                "Tornado",
                "Hurricane",
                "Flood",
                "Heat Wave",
                "Cold Wave",
            ]
            insights.high_priority_alerts = [
                alert.event
                for alert in alerts
                if any(priority in alert.event for priority in high_priority)
            ]

        return insights

    # Public API Methods

    @log_performance("weather_get_current")
    async def get_current_weather(
        self,
        query: LocationQuery,
        units: Optional[WeatherUnits] = None,
        language: Optional[WeatherLang] = None,
    ) -> CurrentWeather:
        """
        Get current weather conditions

        Args:
            query: Location to query
            units: Temperature and speed units
            language: Response language

        Returns:
            Current weather data
        """
        params = {
            "units": (units or self.config.default_units).value,
            "lang": (language or self.config.default_language).value,
        }

        data = await self._make_request(
            "weather",
            query,
            params,
            cache_ttl=self.config.current_weather_cache_minutes,
        )

        # Convert to standardized model
        weather = CurrentWeather(
            location_name=data["name"],
            country=data["sys"]["country"],
            latitude=data["coord"]["lat"],
            longitude=data["coord"]["lon"],
            timezone=data["timezone"],
            timestamp=data["dt"],
            temperature=data["main"]["temp"],
            feels_like=data["main"]["feels_like"],
            pressure=data["main"]["pressure"],
            humidity=data["main"]["humidity"],
            visibility=data.get("visibility"),
            wind_speed=data["wind"]["speed"],
            wind_direction=data["wind"]["deg"],
            wind_gust=data["wind"].get("gust"),
            rain_1h=data.get("rain", {}).get("1h"),
            rain_3h=data.get("rain", {}).get("3h"),
            snow_1h=data.get("snow", {}).get("1h"),
            snow_3h=data.get("snow", {}).get("3h"),
            conditions=[
                WeatherCondition(
                    id=w["id"],
                    main=w["main"],
                    description=w["description"],
                    icon=w["icon"],
                )
                for w in data["weather"]
            ],
            cloudiness=data["clouds"]["all"],
            sunrise=data["sys"]["sunrise"],
            sunset=data["sys"]["sunset"],
            units=units or self.config.default_units,
            raw_data=data,
        )

        self.stats["locations_queried"].add(data["name"])
        self.stats["data_types_requested"].add("current")

        self.logger.info(f"Retrieved current weather for {weather.location_name}")
        return weather

    @log_performance("weather_get_forecast")
    async def get_forecast(
        self,
        query: LocationQuery,
        days: int = 5,
        units: Optional[WeatherUnits] = None,
        language: Optional[WeatherLang] = None,
    ) -> List[WeatherForecast]:
        """
        Get weather forecast

        Args:
            query: Location to query
            days: Number of days to forecast (1-5 for free tier)
            units: Temperature and speed units
            language: Response language

        Returns:
            List of weather forecasts
        """
        if days > 5:
            self.logger.warning(
                "Free tier supports max 5-day forecasts, limiting to 5 days"
            )
            days = 5

        params = {
            "cnt": days * 8,  # 8 forecasts per day (3-hour intervals)
            "units": (units or self.config.default_units).value,
            "lang": (language or self.config.default_language).value,
        }

        data = await self._make_request(
            "forecast", query, params, cache_ttl=self.config.forecast_cache_minutes
        )

        forecasts = []
        for item in data["list"]:
            forecast = WeatherForecast(
                timestamp=item["dt"],
                temperature=item["main"]["temp"],
                feels_like=item["main"]["feels_like"],
                temperature_min=item["main"]["temp_min"],
                temperature_max=item["main"]["temp_max"],
                pressure=item["main"]["pressure"],
                humidity=item["main"]["humidity"],
                wind_speed=item["wind"]["speed"],
                wind_direction=item["wind"]["deg"],
                wind_gust=item["wind"].get("gust"),
                rain=item.get("rain", {}).get("3h"),
                snow=item.get("snow", {}).get("3h"),
                conditions=[
                    WeatherCondition(
                        id=w["id"],
                        main=w["main"],
                        description=w["description"],
                        icon=w["icon"],
                    )
                    for w in item["weather"]
                ],
                cloudiness=item["clouds"]["all"],
                probability_of_precipitation=item.get("pop", 0),
            )
            forecasts.append(forecast)

        self.stats["data_types_requested"].add("forecast")
        self.logger.info(
            f"Retrieved {len(forecasts)} forecast points for {data['city']['name']}"
        )
        return forecasts

    @log_performance("weather_get_alerts")
    async def get_weather_alerts(self, query: LocationQuery) -> List[WeatherAlert]:
        """
        Get active weather alerts/warnings

        Args:
            query: Location to query

        Returns:
            List of active weather alerts
        """
        if not self.config.enable_weather_alerts:
            return []

        # This requires One Call API 3.0 (paid)
        # For free tier, we'll return empty list with a warning
        self.logger.warning(
            "Weather alerts require One Call API 3.0 (paid subscription)"
        )
        return []

    @log_performance("weather_get_insights")
    async def get_trading_insights(
        self, query: LocationQuery, include_forecast: bool = True
    ) -> WeatherInsights:
        """
        Get trading-relevant weather insights

        Args:
            query: Location to query
            include_forecast: Include forecast data in analysis

        Returns:
            Weather insights for trading decisions
        """
        # Get current weather
        current = await self.get_current_weather(query)

        # Get forecast if requested
        forecasts = None
        if include_forecast:
            try:
                forecasts = await self.get_forecast(query, days=3)
            except Exception as e:
                self.logger.warning(f"Failed to get forecast data: {e}")

        # Get alerts if available
        alerts = None
        if self.config.enable_weather_alerts:
            try:
                alerts = await self.get_weather_alerts(query)
            except Exception as e:
                self.logger.warning(f"Failed to get alerts: {e}")

        # Calculate insights
        insights = self._calculate_insights(current, forecasts, alerts)

        self.stats["data_types_requested"].add("insights")
        self.logger.info(f"Generated trading insights for {current.location_name}")
        return insights

    @log_performance("weather_multi_location")
    async def get_multi_location_weather(
        self, locations: List[LocationQuery], data_types: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get weather data for multiple locations

        Args:
            locations: List of locations to query
            data_types: Types of data to fetch (current, forecast, insights)

        Returns:
            Dictionary mapping location names to weather data
        """
        if data_types is None:
            data_types = ["current", "insights"]

        results = {}

        # Process locations concurrently
        tasks = []
        for location in locations:
            location_tasks = {}

            if "current" in data_types:
                location_tasks["current"] = self.get_current_weather(location)

            if "forecast" in data_types:
                location_tasks["forecast"] = self.get_forecast(location)

            if "insights" in data_types:
                location_tasks["insights"] = self.get_trading_insights(
                    location, include_forecast=False
                )

            tasks.append((location, location_tasks))

        # Execute all tasks
        for location, location_tasks in tasks:
            location_key = (
                location.city_name or f"{location.latitude},{location.longitude}"
            )
            results[location_key] = {}

            for data_type, task in location_tasks.items():
                try:
                    results[location_key][data_type] = await task
                except Exception as e:
                    self.logger.error(
                        f"Failed to get {data_type} for {location_key}: {e}"
                    )
                    results[location_key][data_type] = None

        self.logger.info(f"Retrieved weather data for {len(locations)} locations")
        return results

    async def search_locations(
        self, query: str, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for locations by name

        Args:
            query: Location search query
            limit: Maximum results to return

        Returns:
            List of matching locations with coordinates
        """
        params = {
            "q": query,
            "limit": min(limit, 5),  # API limit
            "appid": self.config.api_key,
        }

        client = await self._get_client()

        try:
            response = await client.get(
                f"{self.config.geocoding_url}/direct", params=params
            )

            if response.status_code == 200:
                locations = response.json()
                self.logger.info(f"Found {len(locations)} locations for query: {query}")
                return locations
            else:
                raise WeatherError(f"Location search failed: {response.status_code}")

        except Exception as e:
            self.logger.error(f"Location search error: {e}")
            raise

    async def health_check(self) -> Dict[str, Any]:
        """
        Check Weather API health and connectivity

        Returns:
            Health status information
        """
        health_status = {
            "status": "healthy",
            "api_key_configured": bool(self.config.api_key),
            "circuit_breaker_state": self.circuit_breaker.state,
            "cache_stats": self.cache.get_stats(),
            "rate_limiter": {
                "calls_this_minute": len(self.rate_limiter.minute_calls),
                "calls_this_month": self.rate_limiter.month_calls,
                "minute_limit": self.rate_limiter.max_calls_per_minute,
                "month_limit": self.rate_limiter.max_calls_per_month,
            },
            "statistics": self.stats.copy(),
        }

        if not self.config.api_key:
            health_status["status"] = "not_configured"
            health_status["message"] = "API key not configured"
            return health_status

        # Test API connectivity
        try:
            test_location = LocationQuery(city_name="London")
            await self.get_current_weather(test_location)
            health_status["api_connectivity"] = "working"
        except Exception as e:
            health_status["status"] = "degraded"
            health_status["api_connectivity"] = f"failed: {str(e)[:50]}"

        self.logger.info(f"Weather API health check: {health_status['status']}")
        return health_status

    def get_client_stats(self) -> Dict[str, Any]:
        """Get comprehensive client statistics"""
        stats = self.stats.copy()
        stats["locations_queried"] = list(stats["locations_queried"])
        stats["data_types_requested"] = list(stats["data_types_requested"])

        return {
            "session_id": self.session_id,
            "configuration": {
                "api_key_configured": bool(self.config.api_key),
                "default_units": self.config.default_units.value,
                "default_language": self.config.default_language.value,
                "features_enabled": {
                    "commodity_analysis": self.config.enable_commodity_analysis,
                    "weather_alerts": self.config.enable_weather_alerts,
                    "agricultural_insights": self.config.enable_agricultural_insights,
                    "energy_insights": self.config.enable_energy_insights,
                },
            },
            "statistics": stats,
            "cache_stats": self.cache.get_stats(),
            "circuit_breaker": {
                "state": self.circuit_breaker.state,
                "failure_count": self.circuit_breaker.failure_count,
                "last_failure": (
                    self.circuit_breaker.last_failure_time.isoformat()
                    if self.circuit_breaker.last_failure_time
                    else None
                ),
            },
        }

    async def clear_cache(self) -> None:
        """Clear all cached weather data"""
        self.cache.clear()
        self.logger.info("Weather cache cleared")

    async def close(self) -> None:
        """Close HTTP client and cleanup resources"""
        if self.client and not self.client.is_closed:
            await self.client.aclose()

        self.logger.info("Weather client closed")

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    def __del__(self):
        """Destructor - ensure cleanup"""
        try:
            if self.client and not self.client.is_closed:
                import warnings

                warnings.warn(
                    "Weather client was not properly closed. Use async context manager or call close() explicitly."
                )
        except Exception:
            pass


# Utility functions for easy usage


async def get_weather_for_trading(
    city: str, country: str = "IN", api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Quick weather data retrieval for trading analysis

    Args:
        city: City name
        country: Country code (default: India)
        api_key: OpenWeatherMap API key

    Returns:
        Combined weather and trading insights
    """
    config = WeatherConfig(api_key=api_key) if api_key else WeatherConfig()

    async with WeatherClient(config) as client:
        location = LocationQuery(city_name=city, country_code=country)

        # Get current weather and insights
        current = await client.get_current_weather(location)
        insights = await client.get_trading_insights(location)

        return {
            "current_weather": current,
            "trading_insights": insights,
            "summary": {
                "location": f"{current.location_name}, {current.country}",
                "temperature": current.temperature,
                "conditions": [c.description for c in current.conditions],
                "commodity_impacts": insights.commodity_price_impact,
                "risk_level": insights.transportation_disruption_risk,
                "alerts_count": insights.active_alerts_count,
            },
        }


async def monitor_agricultural_weather(
    locations: List[str], api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Monitor weather conditions for agricultural commodities

    Args:
        locations: List of city names to monitor
        api_key: OpenWeatherMap API key

    Returns:
        Agricultural weather summary
    """
    config = (
        WeatherConfig(
            api_key=api_key,
            enable_agricultural_insights=True,
            enable_commodity_analysis=True,
        )
        if api_key
        else WeatherConfig()
    )

    async with WeatherClient(config) as client:
        location_queries = [LocationQuery(city_name=city) for city in locations]

        results = await client.get_multi_location_weather(
            location_queries, data_types=["current", "insights"]
        )

        # Aggregate insights
        total_crop_stress = 0
        drought_locations = []
        frost_risk_locations = []
        high_impact_commodities = {}

        for location, data in results.items():
            if data.get("insights"):
                insights = data["insights"]

                if insights.crop_stress_index:
                    total_crop_stress += insights.crop_stress_index

                if insights.drought_indicator:
                    drought_locations.append(location)

                if insights.frost_risk:
                    frost_risk_locations.append(location)

                for commodity, impact in insights.commodity_price_impact.items():
                    if commodity not in high_impact_commodities:
                        high_impact_commodities[commodity] = []
                    high_impact_commodities[commodity].append((location, impact))

        return {
            "monitoring_summary": {
                "locations_monitored": len(locations),
                "average_crop_stress": (
                    total_crop_stress / len(locations) if locations else 0
                ),
                "drought_affected_locations": drought_locations,
                "frost_risk_locations": frost_risk_locations,
                "commodity_impacts": high_impact_commodities,
            },
            "detailed_data": results,
        }
