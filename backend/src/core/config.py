"""
NIRAJ Configuration Management System
Handles loading and managing configuration from YAML files and environment variables
"""
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional
import yaml
import structlog

logger = structlog.get_logger()


class Settings:
    """Simple settings class with environment variable support"""

    def __init__(self):
        # Application
        self.environment: str = os.getenv("ENVIRONMENT", "development")
        self.debug: bool = os.getenv("DEBUG", "false").lower() == "true"

        # Database
        self.database_url: str = os.getenv("DATABASE_URL", "sqlite:///./data/niraj.db")

        # Redis
        self.redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

        # JWT
        self.jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
        self.jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
        self.jwt_access_token_expire_minutes: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

        # Trading
        self.live_trading_pin: str = os.getenv("LIVE_TRADING_PIN", "1937")

        # External APIs
        self.angel_one_api_key: Optional[str] = os.getenv("ANGEL_ONE_API_KEY")
        self.angel_one_client_code: Optional[str] = os.getenv("ANGEL_ONE_CLIENT_CODE")
        self.angel_one_password: Optional[str] = os.getenv("ANGEL_ONE_PASSWORD")
        self.angel_one_totp_secret: Optional[str] = os.getenv("ANGEL_ONE_TOTP_SECRET")

        self.dhan_api_token: Optional[str] = os.getenv("DHAN_API_TOKEN")
        self.dhan_client_id: Optional[str] = os.getenv("DHAN_CLIENT_ID")

        self.news_api_key: Optional[str] = os.getenv("NEWS_API_KEY")
        self.weather_api_key: Optional[str] = os.getenv("WEATHER_API_KEY")

        # AI
        self.ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.ollama_model: str = os.getenv("OLLAMA_MODEL", "gemma3:4b-it-q4_K_M")


class ConfigManager:
    """Configuration manager for NIRAJ system"""

    def __init__(self, config_dir: str = "config", environment: Optional[str] = None):
        self.config_dir = Path(config_dir)
        self.environment = environment or os.getenv("ENVIRONMENT", "development")
        self.settings = Settings()
        self._config_data = {}
        self._loaded = False

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file and environment variables"""
        if self._loaded:
            return self._config_data

        try:
            config_file = self.config_dir / f"{self.environment}.yaml"

            if not config_file.exists():
                logger.warning(
                    "Config file not found, using defaults",
                    file=str(config_file)
                )
                self._config_data = self._get_default_config()
            else:
                with open(config_file, 'r', encoding='utf-8') as f:
                    raw_config = yaml.safe_load(f)

                # Substitute environment variables
                self._config_data = self._substitute_env_vars(raw_config)

                logger.info("Configuration loaded",
                           environment=self.environment,
                           config_file=str(config_file))

            # Override with Pydantic settings (from env vars)
            self._merge_pydantic_settings()

            self._loaded = True
            return self._config_data

        except Exception as e:
            logger.error("Failed to load configuration", error=str(e))
            raise

    def _substitute_env_vars(self, data: Any) -> Any:
        """Recursively substitute environment variables in config data"""
        if isinstance(data, dict):
            return {k: self._substitute_env_vars(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._substitute_env_vars(item) for item in data]
        elif isinstance(data, str):
            return self._substitute_env_var_string(data)
        else:
            return data

    def _substitute_env_var_string(self, value: str) -> Any:
        """Substitute environment variables in a string"""
        # Pattern: ${VAR_NAME} or ${VAR_NAME:default_value}
        env_var_pattern = r'\$\{([^}:]+)(?::([^}]*))?\}'

        def replace_match(match):
            var_name = match.group(1)
            default_value = match.group(2)

            env_value = os.getenv(var_name)
            if env_value is not None:
                return env_value
            elif default_value is not None:
                return default_value
            else:
                logger.warning(f"Environment variable {var_name} not found")
                return match.group(0)  # Return original if no value found

        result = re.sub(env_var_pattern, replace_match, value)

        # Try to convert to appropriate type
        if result.lower() in ('true', 'false'):
            return result.lower() == 'true'
        elif result.isdigit():
            return int(result)
        elif '.' in result and result.replace('.', '').isdigit() and result.count('.') == 1:
            # Only convert to float if it's a simple decimal number (one dot, digits only)
            return float(result)
        else:
            return result

    def _merge_pydantic_settings(self):
        """Merge Pydantic settings into config data"""
        # Map pydantic settings to config structure
        mappings = {
            'database.url': self.settings.database_url,
            'redis.url': self.settings.redis_url,
            'auth.secret_key': self.settings.jwt_secret_key,
            'auth.algorithm': self.settings.jwt_algorithm,
            'auth.access_token_expire_minutes': self.settings.jwt_access_token_expire_minutes,
            'auth.live_trading_pin': self.settings.live_trading_pin,
            'ai.ollama.base_url': self.settings.ollama_base_url,
            'ai.ollama.model': self.settings.ollama_model,
            'application.environment': self.settings.environment,
            'application.debug': self.settings.debug,
        }

        for config_path, value in mappings.items():
            if value is not None:
                self._set_nested_value(self._config_data, config_path, value)

    def _set_nested_value(self, data: dict, path: str, value: Any):
        """Set nested dictionary value using dot notation"""
        keys = path.split('.')
        current = data

        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        current[keys[-1]] = value

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration if no config file exists"""
        return {
            'application': {
                'name': 'NIRAJ',
                'version': '0.1.0',
                'environment': self.environment,
                'debug': self.environment == 'development'
            },
            'server': {
                'host': 'localhost',
                'port': 8000,
                'reload': self.environment == 'development'
            },
            'database': {
                'url': self.settings.database_url
            },
            'redis': {
                'url': self.settings.redis_url
            },
            'auth': {
                'secret_key': self.settings.jwt_secret_key,
                'algorithm': self.settings.jwt_algorithm,
                'access_token_expire_minutes': self.settings.jwt_access_token_expire_minutes
            }
        }

    def get(self, path: str, default: Any = None) -> Any:
        """Get configuration value using dot notation"""
        if not self._loaded:
            self.load_config()

        keys = path.split('.')
        current = self._config_data

        try:
            for key in keys:
                current = current[key]
            return current
        except (KeyError, TypeError):
            return default

    def set(self, path: str, value: Any):
        """Set configuration value using dot notation"""
        if not self._loaded:
            self.load_config()

        self._set_nested_value(self._config_data, path, value)

    def get_all(self) -> Dict[str, Any]:
        """Get all configuration data"""
        if not self._loaded:
            self.load_config()
        return self._config_data.copy()

    def reload(self):
        """Reload configuration from file"""
        self._loaded = False
        self._config_data = {}
        return self.load_config()

    def validate_config(self) -> bool:
        """Validate configuration completeness"""
        if not self._loaded:
            self.load_config()

        required_keys = [
            'application.name',
            'database.url',
            'redis.url',
            'auth.secret_key'
        ]

        missing_keys = []
        for key in required_keys:
            if self.get(key) is None:
                missing_keys.append(key)

        if missing_keys:
            logger.error("Missing required configuration keys", keys=missing_keys)
            return False

        logger.info("Configuration validation passed")
        return True

    def export_env_template(self, output_file: str = ".env.template"):
        """Export environment variable template"""
        template_vars = [
            "# NIRAJ Environment Variables Template",
            "",
            "# Database",
            "DATABASE_URL=sqlite:///./data/niraj.db",
            "",
            "# Redis",
            "REDIS_URL=redis://localhost:6379/0",
            "",
            "# JWT Authentication",
            "JWT_SECRET_KEY=your-super-secure-secret-key-here",
            "JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440",
            "",
            "# Trading",
            "LIVE_TRADING_PIN=1937",
            "",
            "# External APIs",
            "ANGEL_ONE_API_KEY=your-angel-one-api-key",
            "ANGEL_ONE_CLIENT_CODE=your-client-code",
            "ANGEL_ONE_PASSWORD=your-password",
            "ANGEL_ONE_TOTP_SECRET=your-totp-secret",
            "",
            "DHAN_API_TOKEN=your-dhan-token",
            "DHAN_CLIENT_ID=your-dhan-client-id",
            "",
            "NEWS_API_KEY=your-news-api-key",
            "WEATHER_API_KEY=your-weather-api-key",
            "",
            "# AI Configuration",
            "OLLAMA_BASE_URL=http://localhost:11434",
            "OLLAMA_MODEL=gemma3:4b-it-q4_K_M",
            "",
            "# Application",
            "ENVIRONMENT=development",
            "DEBUG=true"
        ]

        with open(output_file, 'w') as f:
            f.write('\n'.join(template_vars))

        logger.info("Environment template exported", file=output_file)


# Global configuration manager instance
config = ConfigManager()


# Convenience functions
def get_config(path: str, default: Any = None) -> Any:
    """Get configuration value"""
    return config.get(path, default)


def load_config(environment: Optional[str] = None) -> Dict[str, Any]:
    """Load configuration"""
    if environment:
        config.environment = environment
    return config.load_config()


def validate_config() -> bool:
    """Validate configuration"""
    return config.validate_config()


# Configuration sections for easy access
class AppConfig:
    @property
    def name(self) -> str:
        return get_config('application.name', 'NIRAJ')

    @property
    def version(self) -> str:
        return get_config('application.version', '0.1.0')

    @property
    def environment(self) -> str:
        return get_config('application.environment', 'development')

    @property
    def debug(self) -> bool:
        return get_config('application.debug', False)


class ServerConfig:
    @property
    def host(self) -> str:
        return get_config('server.host', 'localhost')

    @property
    def port(self) -> int:
        return get_config('server.port', 8000)

    @property
    def reload(self) -> bool:
        return get_config('server.reload', False)


class DatabaseConfig:
    @property
    def url(self) -> str:
        return get_config('database.url')

    @property
    def echo(self) -> bool:
        return get_config('database.echo', False)


class TradingConfig:
    @property
    def default_mode(self) -> str:
        return get_config('trading.default_mode', 'paper')

    @property
    def max_position_size(self) -> int:
        return get_config('trading.max_position_size', 100000)

    @property
    def risk_percentage(self) -> float:
        return get_config('trading.risk_percentage', 2.0)


class WeatherAPIConfig:
    @property
    def api_key(self) -> Optional[str]:
        return get_config('external_apis.weather.api_key') or config.settings.weather_api_key

    @property
    def base_url(self) -> str:
        return get_config('external_apis.weather.base_url', 'https://api.openweathermap.org/data/2.5')

    @property
    def geocoding_url(self) -> str:
        return get_config('external_apis.weather.geocoding_url', 'http://api.openweathermap.org/geo/1.0')

    @property
    def timeout(self) -> int:
        return get_config('external_apis.weather.timeout', 15)

    @property
    def max_retries(self) -> int:
        return get_config('external_apis.weather.max_retries', 3)

    @property
    def rate_limit_calls_per_minute(self) -> int:
        return get_config('external_apis.weather.rate_limit_calls_per_minute', 50)

    @property
    def enable_commodity_analysis(self) -> bool:
        return get_config('external_apis.weather.enable_commodity_analysis', True)

    @property
    def enable_agricultural_insights(self) -> bool:
        return get_config('external_apis.weather.enable_agricultural_insights', True)

    @property
    def enable_energy_insights(self) -> bool:
        return get_config('external_apis.weather.enable_energy_insights', True)


# Configuration objects
app_config = AppConfig()
server_config = ServerConfig()
database_config = DatabaseConfig()
trading_config = TradingConfig()
weather_config = WeatherAPIConfig()
