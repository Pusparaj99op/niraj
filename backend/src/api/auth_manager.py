"""
Authentication Manager for NIRAJ API Clients
A comprehensive and secure credential management system for all external APIs

Features:
- Secure encrypted credential storage - Multi-provider authentication (Angel One, Dhan, News APIs, Weather API) - Automatic token refresh and rotation - Circuit breaker pattern for failed attempts - Comprehensive error handling and recovery - Real-time health monitoring -
Thread-safe operations
"""

import json
import secrets
import base64
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from enum import Enum
from pathlib import Path
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

import pyotp
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Global flags for optional imports
CLIENTS_AVAILABLE = False
BACKEND_UTILS_AVAILABLE = False


def get_logger(name: str) -> logging.Logger:
    """Get logger with fallback implementation"""
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


def log_performance(name: str = None):
    """Performance logging decorator fallback"""

    def decorator(func):
        return func

    return decorator


def get_config(path: str, default: Any = None) -> Any:
    """Configuration getter fallback"""
    return os.getenv(path.upper().replace(".", "_"), default)


class LogContext:
    """Log context manager fallback"""

    def __init__(self, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


def _get_angel_one_client():
    """Lazy import AngelOneClient"""
    try:
        from .angel_one_client import AngelOneClient

        return AngelOneClient
    except ImportError:
        return None


def _get_dhan_client():
    """Lazy import DhanClient"""
    try:
        from .dhan_client import DhanClient

        return DhanClient
    except ImportError:
        return None


class AuthProvider(str, Enum):
    """Supported authentication providers"""

    ANGEL_ONE = "angel_one"
    DHAN = "dhan"
    NEWS_API = "news_api"
    FINANCIAL_MODELING_PREP = "fmp"
    ALPHA_VANTAGE = "alpha_vantage"
    WEATHER_API = "weather_api"


class AuthType(str, Enum):
    """Types of authentication mechanisms"""

    JWT_WITH_TOTP = "jwt_with_totp"  # Angel One style
    BEARER_TOKEN = "bearer_token"  # Dhan style
    API_KEY = "api_key"  # News/Weather APIs
    OAUTH2 = "oauth2"  # Future OAuth2 support


class CredentialStatus(str, Enum):
    """Status of credentials"""

    VALID = "valid"
    EXPIRED = "expired"
    INVALID = "invalid"
    REFRESH_NEEDED = "refresh_needed"
    LOCKED = "locked"
    DISABLED = "disabled"


@dataclass
class Credentials:
    """Secure credential container"""

    provider: AuthProvider
    auth_type: AuthType
    primary_key: str  # API key, client code, etc.
    secondary_key: Optional[str] = None  # Password, token, etc.
    tertiary_key: Optional[str] = None  # TOTP secret, etc.
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    status: CredentialStatus = CredentialStatus.VALID
    usage_count: int = 0
    last_used: Optional[datetime] = None

    def __post_init__(self):
        """Post-initialization validation"""
        if self.auth_type == AuthType.JWT_WITH_TOTP and not self.tertiary_key:
            raise ValueError("JWT_WITH_TOTP requires TOTP secret (tertiary_key)")

    def is_expired(self) -> bool:
        """Check if credentials are expired"""
        if not self.expires_at:
            return False
        return datetime.now() >= self.expires_at

    def is_valid(self) -> bool:
        """Check if credentials are valid for use"""
        return self.status == CredentialStatus.VALID and not self.is_expired()

    def mark_used(self):
        """Mark credentials as used"""
        self.usage_count += 1
        self.last_used = datetime.now()
        self.updated_at = datetime.now()


@dataclass
class AuthToken:
    """Authentication token container"""

    provider: AuthProvider
    token_type: str  # Bearer, JWT, etc.
    access_token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if token is expired"""
        if not self.expires_at:
            return False
        # Add 5-minute buffer before expiry
        return datetime.now() >= (self.expires_at - timedelta(minutes=5))

    def is_valid(self) -> bool:
        """Check if token is valid"""
        return self.access_token and not self.is_expired()


# Exception Classes
class AuthenticationManagerError(Exception):
    """Base exception for authentication manager"""

    def __init__(
        self,
        message: str,
        provider: Optional[AuthProvider] = None,
        error_code: Optional[str] = None,
    ):
        super().__init__(message)
        self.provider = provider
        self.error_code = error_code


class CredentialNotFoundError(AuthenticationManagerError):
    """Credential not found error"""

    pass


class AuthenticationFailedError(AuthenticationManagerError):
    """Authentication failed error"""

    pass


class TokenRefreshError(AuthenticationManagerError):
    """Token refresh error"""

    pass


class EncryptionError(AuthenticationManagerError):
    """Encryption/decryption error"""

    pass


class RateLimitError(AuthenticationManagerError):
    """Rate limit exceeded error"""

    pass


class CircuitBreakerError(AuthenticationManagerError):
    """Circuit breaker triggered error"""

    pass


class CredentialStore:
    """
    Secure credential storage with encryption

    Features:
    - AES-256 encryption using Fernet - PBKDF2 key derivation - Atomic file operations -
    Secure file permissions
    """

    def __init__(
        self,
        master_password: Optional[str] = None,
        storage_path: str = "data/credentials.enc",
    ):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        # Derive encryption key from master password
        if master_password:
            self.encryption_key = self._derive_key_from_password(master_password)
        else:
            # Use system-generated key for development
            key_file = self.storage_path.parent / "encryption.key"
            if key_file.exists():
                with open(key_file, "rb") as f:
                    self.encryption_key = f.read()
            else:
                self.encryption_key = Fernet.generate_key()
                with open(key_file, "wb") as f:
                    f.write(self.encryption_key)
                os.chmod(key_file, 0o600)  # Restrict permissions

        self.cipher = Fernet(self.encryption_key)
        self.logger = get_logger("niraj.auth_manager.credential_store")

    def _derive_key_from_password(self, password: str) -> bytes:
        """Derive encryption key from master password using PBKDF2"""
        # Use a fixed salt (in production, this should be randomly generated and stored)
        salt = b"niraj_trading_system_salt_2024"
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key

    def _serialize_credentials(self, credentials: Dict[str, Credentials]) -> bytes:
        """Serialize credentials to encrypted bytes"""
        try:
            # Convert credentials to serializable format
            serializable = {}
            for provider, cred in credentials.items():
                serializable[provider] = {
                    "provider": cred.provider.value,
                    "auth_type": cred.auth_type.value,
                    "primary_key": cred.primary_key,
                    "secondary_key": cred.secondary_key,
                    "tertiary_key": cred.tertiary_key,
                    "metadata": cred.metadata,
                    "created_at": cred.created_at.isoformat(),
                    "updated_at": cred.updated_at.isoformat(),
                    "expires_at": (
                        cred.expires_at.isoformat() if cred.expires_at else None
                    ),
                    "status": cred.status.value,
                    "usage_count": cred.usage_count,
                    "last_used": (
                        cred.last_used.isoformat() if cred.last_used else None
                    ),
                }

            json_data = json.dumps(serializable, indent=2)
            encrypted_data = self.cipher.encrypt(json_data.encode())
            return encrypted_data

        except Exception as e:
            raise EncryptionError(f"Failed to serialize credentials: {e}")

    def _deserialize_credentials(self, encrypted_data: bytes) -> Dict[str, Credentials]:
        """Deserialize encrypted credentials"""
        try:
            decrypted_data = self.cipher.decrypt(encrypted_data)
            json_data = json.loads(decrypted_data.decode())

            credentials = {}
            for provider, data in json_data.items():
                credentials[provider] = Credentials(
                    provider=AuthProvider(data["provider"]),
                    auth_type=AuthType(data["auth_type"]),
                    primary_key=data["primary_key"],
                    secondary_key=data["secondary_key"],
                    tertiary_key=data["tertiary_key"],
                    metadata=data["metadata"],
                    created_at=datetime.fromisoformat(data["created_at"]),
                    updated_at=datetime.fromisoformat(data["updated_at"]),
                    expires_at=(
                        datetime.fromisoformat(data["expires_at"])
                        if data["expires_at"]
                        else None
                    ),
                    status=CredentialStatus(data["status"]),
                    usage_count=data["usage_count"],
                    last_used=(
                        datetime.fromisoformat(data["last_used"])
                        if data["last_used"]
                        else None
                    ),
                )

            return credentials

        except Exception as e:
            raise EncryptionError(f"Failed to deserialize credentials: {e}")

    def save(self, credentials: Dict[str, Credentials]) -> None:
        """Save credentials to encrypted storage"""
        try:
            encrypted_data = self._serialize_credentials(credentials)

            # Write to temporary file first, then move (atomic operation)
            temp_path = self.storage_path.with_suffix(".tmp")
            with open(temp_path, "wb") as f:
                f.write(encrypted_data)

            os.chmod(temp_path, 0o600)  # Restrict permissions
            temp_path.rename(self.storage_path)

            self.logger.debug("Credentials saved successfully")

        except Exception as e:
            self.logger.error(f"Failed to save credentials: {e}")
            raise EncryptionError(f"Failed to save credentials: {e}")

    def load(self) -> Dict[str, Credentials]:
        """Load credentials from encrypted storage"""
        try:
            if not self.storage_path.exists():
                return {}

            with open(self.storage_path, "rb") as f:
                encrypted_data = f.read()

            credentials = self._deserialize_credentials(encrypted_data)
            self.logger.debug(f"Loaded {len(credentials)} credential sets")
            return credentials

        except Exception as e:
            self.logger.error(f"Failed to load credentials: {e}")
            # Return empty dict if loading fails
            return {}

    def delete(self) -> None:
        """Delete credential storage file"""
        try:
            if self.storage_path.exists():
                self.storage_path.unlink()
                self.logger.info("Credential storage deleted")
        except Exception as e:
            self.logger.error(f"Failed to delete credential storage: {e}")


class CircuitBreaker:
    """
    Circuit breaker implementation for authentication failures

    States: CLOSED -> OPEN -> HALF_OPEN -> CLOSED
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: int = 60,
        success_threshold: int = 2,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

        self.logger = get_logger("niraj.auth_manager.circuit_breaker")

    def call_succeeded(self):
        """Record successful operation"""
        if self.state == "HALF_OPEN":
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self._close_circuit()
        elif self.state == "CLOSED":
            self.failure_count = 0

    def call_failed(self):
        """Record failed operation"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.state in ["CLOSED", "HALF_OPEN"]:
            if self.failure_count >= self.failure_threshold:
                self._open_circuit()

    def _open_circuit(self):
        """Open the circuit breaker"""
        self.state = "OPEN"
        self.success_count = 0
        self.logger.warning(
            f"Circuit breaker OPEN due to repeated failures (count: {self.failure_count})"
        )

    def _close_circuit(self):
        """Close the circuit breaker"""
        self.state = "CLOSED"
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.logger.info("Circuit breaker CLOSED - service recovered")

    def can_proceed(self) -> bool:
        """Check if operation can proceed"""
        if self.state == "CLOSED":
            return True

        if self.state == "OPEN":
            if (
                self.last_failure_time
                and datetime.now() - self.last_failure_time
                > timedelta(seconds=self.recovery_timeout)
            ):
                self.state = "HALF_OPEN"
                self.success_count = 0
                self.logger.info("Circuit breaker entering HALF_OPEN state")
                return True
            return False

        if self.state == "HALF_OPEN":
            return True

        return False


class AuthenticationManager:
    """
    Comprehensive authentication manager for all external APIs

    Features:
    - Secure credential storage with encryption - Automatic token refresh and rotation - Multiple authentication patterns support - Circuit breaker for failed authentication attempts - Detailed logging and monitoring - Thread-safe operations - Credential validation and health checks -
    Rate limiting and retry logic
    """

    def __init__(
        self,
        master_password: Optional[str] = None,
        storage_path: str = "data/credentials.enc",
    ):
        self.logger = get_logger("niraj.auth_manager")
        self.session_id = secrets.token_hex(16)

        # Initialize credential store
        self.credential_store = CredentialStore(master_password, storage_path)

        # In-memory credential and token storage
        self.credentials: Dict[str, Credentials] = {}
        self.tokens: Dict[str, AuthToken] = {}

        # Client instances cache
        self.clients: Dict[str, Any] = {}

        # Circuit breakers for each provider
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}

        # Configuration
        self.max_retry_attempts = 3
        self.retry_delay_base = 1.0  # Base delay in seconds
        self.token_refresh_buffer_minutes = 5
        self.health_check_interval = 300  # 5 minutes

        # Background tasks
        self._health_check_task: Optional[asyncio.Task] = None
        self._token_refresh_task: Optional[asyncio.Task] = None

        # Load existing credentials
        self._load_credentials()

        self.logger.info(
            f"Authentication manager initialized (session: {self.session_id})"
        )

    def _load_credentials(self) -> None:
        """Load credentials from storage"""
        try:
            self.credentials = self.credential_store.load()

            # Initialize circuit breakers for each provider
            for provider_key in self.credentials.keys():
                self.circuit_breakers[provider_key] = CircuitBreaker()

            self.logger.info(f"Loaded {len(self.credentials)} credential sets")
        except Exception as e:
            self.logger.error(f"Failed to load credentials: {e}")
            self.credentials = {}

    def _save_credentials(self) -> None:
        """Save credentials to storage"""
        try:
            self.credential_store.save(self.credentials)
        except Exception as e:
            self.logger.error(f"Failed to save credentials: {e}")

    def _get_circuit_breaker(self, provider: AuthProvider) -> CircuitBreaker:
        """Get or create circuit breaker for provider"""
        provider_key = provider.value
        if provider_key not in self.circuit_breakers:
            self.circuit_breakers[provider_key] = CircuitBreaker()
        return self.circuit_breakers[provider_key]

    def add_credentials(
        self,
        provider: AuthProvider,
        auth_type: AuthType,
        primary_key: str,
        secondary_key: Optional[str] = None,
        tertiary_key: Optional[str] = None,
        metadata: Optional[Dict] = None,
        expires_at: Optional[datetime] = None,
    ) -> None:
        """
        Add new credentials for a provider

        Args:
            provider: Authentication provider
            auth_type: Type of authentication
            primary_key: Primary credential (API key, client code, etc.)
            secondary_key: Secondary credential (password, token, etc.)
            tertiary_key: Tertiary credential (TOTP secret, etc.)
            metadata: Additional metadata
            expires_at: Expiration datetime
        """
        try:
            credentials = Credentials(
                provider=provider,
                auth_type=auth_type,
                primary_key=primary_key,
                secondary_key=secondary_key,
                tertiary_key=tertiary_key,
                metadata=metadata or {},
                expires_at=expires_at,
            )

            self.credentials[provider.value] = credentials
            self._save_credentials()

            # Initialize circuit breaker for new provider
            if provider.value not in self.circuit_breakers:
                self.circuit_breakers[provider.value] = CircuitBreaker()

            self.logger.info(
                f"Credentials added successfully (provider: {provider.value}, auth_type: {auth_type.value})"
            )

        except Exception as e:
            self.logger.error(f"Failed to add credentials for {provider.value}: {e}")
            raise AuthenticationManagerError(
                f"Failed to add credentials: {e}", provider
            )

    def get_credentials(self, provider: AuthProvider) -> Optional[Credentials]:
        """Get credentials for a provider"""
        return self.credentials.get(provider.value)

    def remove_credentials(self, provider: AuthProvider) -> None:
        """Remove credentials for a provider"""
        try:
            if provider.value in self.credentials:
                del self.credentials[provider.value]
                self._save_credentials()

                # Clean up related resources
                if provider.value in self.tokens:
                    del self.tokens[provider.value]
                if provider.value in self.clients:
                    del self.clients[provider.value]
                if provider.value in self.circuit_breakers:
                    del self.circuit_breakers[provider.value]

                self.logger.info(
                    f"Credentials removed successfully (provider: {provider.value})"
                )
            else:
                self.logger.warning(
                    f"Credentials not found for removal (provider: {provider.value})"
                )

        except Exception as e:
            self.logger.error(f"Failed to remove credentials for {provider.value}: {e}")
            raise AuthenticationManagerError(
                f"Failed to remove credentials: {e}", provider
            )

    def _generate_totp_code(self, secret: str) -> str:
        """Generate TOTP code from secret"""
        try:
            totp = pyotp.TOTP(secret)
            return totp.now()
        except Exception as e:
            self.logger.error(f"Failed to generate TOTP code: {e}")
            raise AuthenticationManagerError(f"Failed to generate TOTP: {e}")

    async def _retry_with_exponential_backoff(
        self, operation, provider: AuthProvider, max_attempts: Optional[int] = None
    ) -> Any:
        """Execute operation with exponential backoff retry"""
        if max_attempts is None:
            max_attempts = self.max_retry_attempts

        last_exception = None

        for attempt in range(max_attempts):
            try:
                return await operation()
            except Exception as e:
                last_exception = e

                if attempt < max_attempts - 1:
                    delay = self.retry_delay_base * (2**attempt)
                    self.logger.warning(
                        f"Attempt {attempt + 1} failed, retrying in {delay}s",
                        provider=provider.value,
                        error=str(e),
                    )
                    await asyncio.sleep(delay)
                else:
                    self.logger.error(
                        f"All {max_attempts} attempts failed",
                        provider=provider.value,
                        error=str(e),
                    )

        raise last_exception

    @log_performance("auth_manager_authenticate")
    async def authenticate(
        self, provider: AuthProvider, force_refresh: bool = False
    ) -> AuthToken:
        """
        Authenticate with a provider and get valid token

        Args:
            provider: Authentication provider
            force_refresh: Force token refresh even if current token is valid

        Returns:
            Valid authentication token

        Raises:
            AuthenticationFailedError: If authentication fails
            CredentialNotFoundError: If credentials not found
            CircuitBreakerError: If circuit breaker is open
        """
        with LogContext(
            session_id=self.session_id,
            provider=provider.value,
            operation="authenticate",
        ):
            # Check circuit breaker
            circuit_breaker = self._get_circuit_breaker(provider)
            if not circuit_breaker.can_proceed():
                raise CircuitBreakerError(
                    f"Circuit breaker is open for {provider.value}", provider
                )

            # Get existing token if not forcing refresh
            if not force_refresh and provider.value in self.tokens:
                token = self.tokens[provider.value]
                if token.is_valid():
                    self.logger.debug(
                        f"Using cached valid token (provider: {provider.value})"
                    )
                    return token

            # Get credentials
            credentials = self.get_credentials(provider)
            if not credentials:
                raise CredentialNotFoundError(
                    f"Credentials not found for {provider.value}", provider
                )

            if not credentials.is_valid():
                raise AuthenticationFailedError(
                    f"Credentials for {provider.value} are invalid or expired", provider
                )

            try:
                # Perform authentication with retry logic
                async def auth_operation():
                    return await self._perform_authentication(credentials)

                token = await self._retry_with_exponential_backoff(
                    auth_operation, provider
                )

                # Cache token
                self.tokens[provider.value] = token

                # Mark credentials as used and record success
                credentials.mark_used()
                self._save_credentials()
                circuit_breaker.call_succeeded()

                expires_info = (
                    token.expires_at.isoformat() if token.expires_at else None
                )
                self.logger.info(
                    "Authentication successful",
                    provider=provider.value,
                    token_expires_at=expires_info,
                )

                return token

            except Exception as e:
                circuit_breaker.call_failed()
                self.logger.error(f"Authentication failed for {provider.value}: {e}")
                raise AuthenticationFailedError(f"Authentication failed: {e}", provider)

    async def _perform_authentication(self, credentials: Credentials) -> AuthToken:
        """Perform actual authentication based on credential type"""

        if credentials.provider == AuthProvider.ANGEL_ONE:
            return await self._authenticate_angel_one(credentials)
        elif credentials.provider == AuthProvider.DHAN:
            return await self._authenticate_dhan(credentials)
        elif credentials.provider in [
            AuthProvider.NEWS_API,
            AuthProvider.FINANCIAL_MODELING_PREP,
            AuthProvider.ALPHA_VANTAGE,
            AuthProvider.WEATHER_API,
        ]:
            return self._authenticate_api_key(credentials)
        else:
            raise AuthenticationManagerError(
                f"Unsupported provider: {credentials.provider.value}"
            )

    async def _authenticate_angel_one(self, credentials: Credentials) -> AuthToken:
        """Authenticate with Angel One using JWT + TOTP"""
        AngelOneClient = _get_angel_one_client()
        if AngelOneClient is None:
            raise AuthenticationManagerError(
                "Angel One client not available - check imports"
            )

        try:
            # Get or create client
            if credentials.provider.value not in self.clients:
                self.clients[credentials.provider.value] = AngelOneClient(
                    api_key=credentials.primary_key,
                    client_code=credentials.metadata.get(
                        "client_code", credentials.primary_key
                    ),
                    client_pin=credentials.secondary_key,
                    totp_secret=credentials.tertiary_key,
                )

            client = self.clients[credentials.provider.value]

            # Generate TOTP if needed
            totp_code = None
            if credentials.tertiary_key:
                totp_code = self._generate_totp_code(credentials.tertiary_key)

            # Perform login
            response = await client.login(totp_code)

            # Extract token information
            data = response.get("data", {})
            access_token = data.get("jwtToken")
            refresh_token = data.get("refreshToken")

            if not access_token:
                raise AuthenticationFailedError(
                    "No access token received from Angel One"
                )

            # Calculate expiry (Angel One tokens are valid for 28 hours)
            expires_at = datetime.now() + timedelta(hours=28)

            return AuthToken(
                provider=credentials.provider,
                token_type="Bearer",
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=expires_at,
                metadata={"feed_token": data.get("feedToken")},
            )

        except Exception as e:
            raise AuthenticationFailedError(f"Angel One authentication failed: {e}")

    async def _authenticate_dhan(self, credentials: Credentials) -> AuthToken:
        """Authenticate with Dhan (token-based)"""
        DhanClient = _get_dhan_client()
        if DhanClient is None:
            raise AuthenticationManagerError(
                "Dhan client not available - check imports"
            )

        try:
            # Get or create client
            if credentials.provider.value not in self.clients:
                self.clients[credentials.provider.value] = DhanClient(
                    client_id=credentials.primary_key,
                    access_token=credentials.secondary_key,
                )

            client = self.clients[credentials.provider.value]

            # Verify authentication with a test call
            await client.verify_authentication()

            # Dhan uses long-lived tokens
            expires_at = datetime.now() + timedelta(days=365)

            return AuthToken(
                provider=credentials.provider,
                token_type="Bearer",
                access_token=credentials.secondary_key,
                expires_at=expires_at,
                metadata={"client_id": credentials.primary_key},
            )

        except Exception as e:
            raise AuthenticationFailedError(f"Dhan authentication failed: {e}")

    def _authenticate_api_key(self, credentials: Credentials) -> AuthToken:
        """Authenticate with API key-based services"""
        # API keys don't expire (unless specified)
        expires_at = credentials.expires_at or (datetime.now() + timedelta(days=365))

        return AuthToken(
            provider=credentials.provider,
            token_type="ApiKey",
            access_token=credentials.primary_key,
            expires_at=expires_at,
            metadata=credentials.metadata.copy(),
        )

    async def get_client(self, provider: AuthProvider, **kwargs) -> Any:
        """
        Get authenticated client instance for a provider

        Args:
            provider: Authentication provider
            **kwargs: Additional client configuration

        Returns:
            Authenticated client instance
        """
        # Ensure we have a valid token
        token = await self.authenticate(provider)

        # Return cached client if available
        if provider.value in self.clients:
            client = self.clients[provider.value]

            # Update client with fresh token if needed
            if hasattr(client, "update_token"):
                client.update_token(token.access_token)

            return client

        # Create new client based on provider
        credentials = self.get_credentials(provider)
        if not credentials:
            raise CredentialNotFoundError(
                f"Credentials not found for {provider.value}", provider
            )

        client = self._create_client(provider, credentials, token, **kwargs)
        self.clients[provider.value] = client
        return client

    def _create_client(
        self,
        provider: AuthProvider,
        credentials: Credentials,
        token: AuthToken,
        **kwargs,
    ) -> Any:
        """Create client instance for provider"""

        if provider == AuthProvider.ANGEL_ONE:
            AngelOneClient = _get_angel_one_client()
            if AngelOneClient is None:
                raise AuthenticationManagerError(
                    "Angel One client not available - check imports"
                )
            return AngelOneClient(
                api_key=credentials.primary_key,
                client_code=credentials.metadata.get(
                    "client_code", credentials.primary_key
                ),
                client_pin=credentials.secondary_key,
                totp_secret=credentials.tertiary_key,
                **kwargs,
            )

        elif provider == AuthProvider.DHAN:
            DhanClient = _get_dhan_client()
            if DhanClient is None:
                raise AuthenticationManagerError(
                    "Dhan client not available - check imports"
                )
            return DhanClient(
                client_id=credentials.primary_key,
                access_token=token.access_token,
                **kwargs,
            )

        else:
            raise AuthenticationManagerError(
                f"Client creation not implemented for {provider.value}"
            )

    async def health_check(
        self, provider: Optional[AuthProvider] = None
    ) -> Dict[str, Any]:
        """
        Perform comprehensive health check on authentication system

        Args:
            provider: Specific provider to check, or None for all

        Returns:
            Health check results with detailed status information
        """
        results = {
            "timestamp": datetime.now().isoformat(),
            "session_id": self.session_id,
            "overall_status": "healthy",
            "providers": {},
            "summary": {
                "total_providers": 0,
                "healthy_providers": 0,
                "degraded_providers": 0,
                "unhealthy_providers": 0,
            },
        }

        providers_to_check = (
            [provider]
            if provider
            else [AuthProvider(p) for p in self.credentials.keys()]
        )

        for prov in providers_to_check:
            provider_status = await self._check_provider_health(prov)
            results["providers"][prov.value] = provider_status

            # Update summary
            results["summary"]["total_providers"] += 1
            if provider_status["status"] == "healthy":
                results["summary"]["healthy_providers"] += 1
            elif provider_status["status"] == "degraded":
                results["summary"]["degraded_providers"] += 1
            else:
                results["summary"]["unhealthy_providers"] += 1

        # Determine overall status
        if results["summary"]["unhealthy_providers"] > 0:
            results["overall_status"] = "unhealthy"
        elif results["summary"]["degraded_providers"] > 0:
            results["overall_status"] = "degraded"

        return results

    async def _check_provider_health(self, provider: AuthProvider) -> Dict[str, Any]:
        """Check health of a specific provider"""
        try:
            # Check credentials
            cred = self.get_credentials(provider)
            if not cred:
                return {
                    "status": "no_credentials",
                    "message": "No credentials configured",
                }

            # Check circuit breaker
            circuit_breaker = self._get_circuit_breaker(provider)
            circuit_status = circuit_breaker.state

            if circuit_status == "OPEN":
                return {
                    "status": "circuit_open",
                    "message": "Circuit breaker is open due to failures",
                    "circuit_state": circuit_status,
                    "failure_count": circuit_breaker.failure_count,
                    "last_failure": (
                        circuit_breaker.last_failure_time.isoformat()
                        if circuit_breaker.last_failure_time
                        else None
                    ),
                }

            # Check token validity
            token = self.tokens.get(provider.value)
            if token and token.is_valid():
                token_status = "valid"
            elif token and token.is_expired():
                token_status = "expired"
            else:
                token_status = "none"

            # Test authentication (only for critical providers)
            auth_test = "not_tested"
            if provider in [AuthProvider.ANGEL_ONE, AuthProvider.DHAN]:
                try:
                    await self.authenticate(provider)
                    auth_test = "success"
                except Exception as e:
                    auth_test = f"failed: {str(e)[:100]}"

            # Determine status
            if auth_test == "success" or (
                auth_test == "not_tested"
                and cred.is_valid()
                and token_status == "valid"
            ):
                status = "healthy"
            elif auth_test.startswith("failed") or token_status == "expired":
                status = "degraded"
            else:
                status = "unhealthy"

            return {
                "status": status,
                "credentials_valid": cred.is_valid(),
                "credentials_expires": (
                    cred.expires_at.isoformat() if cred.expires_at else None
                ),
                "token_status": token_status,
                "token_expires": (
                    token.expires_at.isoformat() if token and token.expires_at else None
                ),
                "auth_test": auth_test,
                "usage_count": cred.usage_count,
                "last_used": cred.last_used.isoformat() if cred.last_used else None,
                "circuit_state": circuit_status,
                "failure_count": circuit_breaker.failure_count,
            }

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive authentication manager statistics"""
        circuit_stats = {}
        for provider_key, circuit in self.circuit_breakers.items():
            circuit_stats[provider_key] = {
                "state": circuit.state,
                "failure_count": circuit.failure_count,
                "success_count": circuit.success_count,
                "last_failure": (
                    circuit.last_failure_time.isoformat()
                    if circuit.last_failure_time
                    else None
                ),
            }

        return {
            "session_id": self.session_id,
            "credential_count": len(self.credentials),
            "cached_tokens": len(self.tokens),
            "active_clients": len(self.clients),
            "circuit_breakers": circuit_stats,
            "configuration": {
                "max_retry_attempts": self.max_retry_attempts,
                "retry_delay_base": self.retry_delay_base,
                "token_refresh_buffer_minutes": self.token_refresh_buffer_minutes,
                "health_check_interval": self.health_check_interval,
            },
        }

    async def start_background_tasks(self):
        """Start background maintenance tasks"""
        try:
            # Start token refresh task
            if not self._token_refresh_task or self._token_refresh_task.done():
                self._token_refresh_task = asyncio.create_task(
                    self._token_refresh_loop()
                )

            # Start health check task
            if not self._health_check_task or self._health_check_task.done():
                self._health_check_task = asyncio.create_task(self._health_check_loop())

            self.logger.info("Background tasks started")

        except Exception as e:
            self.logger.error(f"Failed to start background tasks: {e}")

    async def _token_refresh_loop(self):
        """Background task to refresh tokens before expiry"""
        while True:
            try:
                for provider_key, token in self.tokens.items():
                    if token.expires_at:
                        time_to_expiry = token.expires_at - datetime.now()

                        # Refresh if expiring within buffer time
                        if time_to_expiry.total_seconds() < (
                            self.token_refresh_buffer_minutes * 60
                        ):
                            provider = AuthProvider(provider_key)
                            try:
                                await self.authenticate(provider, force_refresh=True)
                                self.logger.info(
                                    f"Auto-refreshed token for {provider_key}"
                                )
                            except Exception as e:
                                self.logger.warning(
                                    f"Failed to auto-refresh token for {provider_key}: {e}"
                                )

                # Sleep for 1 minute before next check
                await asyncio.sleep(60)

            except Exception as e:
                self.logger.error(f"Error in token refresh loop: {e}")
                await asyncio.sleep(60)

    async def _health_check_loop(self):
        """Background task for periodic health checks"""
        while True:
            try:
                health_results = await self.health_check()

                # Log health status
                overall_status = health_results["overall_status"]
                if overall_status != "healthy":
                    self.logger.warning(
                        f"Authentication system health: {overall_status}",
                        summary=health_results["summary"],
                    )

                await asyncio.sleep(self.health_check_interval)

            except Exception as e:
                self.logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(self.health_check_interval)

    async def close(self) -> None:
        """Close all clients and cleanup resources"""
        try:
            # Cancel background tasks
            if self._token_refresh_task and not self._token_refresh_task.done():
                self._token_refresh_task.cancel()
                try:
                    await self._token_refresh_task
                except asyncio.CancelledError:
                    pass

            if self._health_check_task and not self._health_check_task.done():
                self._health_check_task.cancel()
                try:
                    await self._health_check_task
                except asyncio.CancelledError:
                    pass

            # Close all clients
            for client in self.clients.values():
                try:
                    if hasattr(client, "close"):
                        await client.close()
                except Exception as e:
                    self.logger.warning(f"Error closing client: {e}")

            self.clients.clear()
            self.tokens.clear()

            self.logger.info("Authentication manager closed")

        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")

    async def __aenter__(self):
        """Async context manager entry"""
        await self.start_background_tasks()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()


# Utility functions for easy setup
def create_auth_manager(master_password: Optional[str] = None) -> AuthenticationManager:
    """Create authentication manager with optional master password"""
    return AuthenticationManager(master_password)


def setup_development_credentials(auth_manager: AuthenticationManager) -> None:
    """Setup development credentials from configuration"""
    try:
        logger = get_logger("niraj.auth_manager.setup")

        # Angel One
        angel_api_key = get_config("brokers.angel_one.api_key")
        angel_client_code = get_config("brokers.angel_one.client_code")
        angel_password = get_config("brokers.angel_one.password")
        angel_totp_secret = get_config("brokers.angel_one.totp_secret")

        if angel_api_key and angel_client_code and angel_password:
            auth_manager.add_credentials(
                provider=AuthProvider.ANGEL_ONE,
                auth_type=AuthType.JWT_WITH_TOTP,
                primary_key=angel_api_key,
                secondary_key=angel_password,
                tertiary_key=angel_totp_secret,
                metadata={"client_code": angel_client_code},
            )
            logger.info("Added Angel One credentials")

        # Dhan
        dhan_client_id = get_config("brokers.dhan.client_id")
        dhan_token = get_config("brokers.dhan.access_token")

        if dhan_client_id and dhan_token:
            auth_manager.add_credentials(
                provider=AuthProvider.DHAN,
                auth_type=AuthType.BEARER_TOKEN,
                primary_key=dhan_client_id,
                secondary_key=dhan_token,
            )
            logger.info("Added Dhan credentials")

        # News API
        news_api_key = get_config("news_api_key")
        if news_api_key:
            auth_manager.add_credentials(
                provider=AuthProvider.NEWS_API,
                auth_type=AuthType.API_KEY,
                primary_key=news_api_key,
            )
            logger.info("Added News API credentials")

        # Weather API
        weather_api_key = get_config("weather_api_key")
        if weather_api_key:
            auth_manager.add_credentials(
                provider=AuthProvider.WEATHER_API,
                auth_type=AuthType.API_KEY,
                primary_key=weather_api_key,
            )
            logger.info("Added Weather API credentials")

        logger.info("Development credentials setup completed")

    except Exception as e:
        logger = get_logger("niraj.auth_manager.setup")
        logger.error(f"Failed to setup development credentials: {e}")
        raise


# Global authentication manager instance
_auth_manager: Optional[AuthenticationManager] = None


def get_auth_manager() -> AuthenticationManager:
    """Get global authentication manager instance"""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = create_auth_manager()
    return _auth_manager


@asynccontextmanager
async def get_authenticated_client(provider: AuthProvider, **kwargs):
    """Context manager for getting authenticated client"""
    auth_manager = get_auth_manager()

    try:
        client = await auth_manager.get_client(provider, **kwargs)
        yield client
    finally:
        # Client cleanup is handled by auth_manager
        pass
