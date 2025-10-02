"""
Configuration Management Service

Advanced configuration service with validation, caching, versioning, and error handling.
Provides comprehensive configuration management for the NIRAJ trading system.
"""

import asyncio
import json
import re
import threading
import time
import weakref
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import (
    Any,
    AsyncGenerator,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import uuid

import yaml
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..models.configuration import (
    Configuration,
    ConfigurationORM,
    ConfigType,
    ConfigCategory,
    ConfigEnvironment,
    ConfigScope,
    ConfigValidationError,
    ConfigNotFoundError,
    ConfigurationCreateRequest,
    ConfigurationUpdateRequest,
    ConfigurationResponse,
    ConfigurationQueryRequest,
    ConfigurationBulkResponse,
)
from ..core.database_manager import AdvancedDatabaseManager as DatabaseManager
from ..core.cache import CacheManager
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ConfigChangeType(Enum):
    """Configuration change types for audit trail"""

    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    ACTIVATED = "activated"
    DEACTIVATED = "deactivated"
    ENCRYPTED = "encrypted"
    DECRYPTED = "decrypted"


@dataclass
class ConfigChange:
    """Configuration change record"""

    config_id: str
    change_type: ConfigChangeType
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    user_id: Optional[str] = None
    reason: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConfigValidationRule:
    """Configuration validation rule"""

    key_pattern: str
    validator: Callable[[Any], bool]
    error_message: str
    apply_to_types: Set[ConfigType] = field(default_factory=set)


@dataclass
class ConfigCacheEntry:
    """Configuration cache entry"""

    config: Configuration
    cached_at: datetime
    ttl_seconds: int
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.utcnow)

    @property
    def is_expired(self) -> bool:
        return datetime.utcnow() > (
            self.cached_at + timedelta(seconds=self.ttl_seconds)
        )

    def touch(self):
        """Update access statistics"""
        self.access_count += 1
        self.last_accessed = datetime.utcnow()


T = TypeVar("T")


class ConfigurationService:
    """
    Advanced Configuration Management Service

    Features:
    - Multi-environment support
    - Hierarchical configuration with scope inheritance
    - Real-time configuration updates with notifications
    - Advanced validation and type coercion
    - Encryption for sensitive data
    - Configuration versioning and rollback
    - Intelligent caching with TTL and invalidation
    - Bulk operations and batch processing
    - Configuration templates and profiles
    - Import/export with multiple formats
    - Audit trail and change tracking
    - Performance monitoring and metrics
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        cache_manager: Optional[CacheManager] = None,
        encryption_key: Optional[str] = None,
        default_cache_ttl: int = 300,  # 5 minutes
        enable_notifications: bool = True,
        max_cache_entries: int = 10000,
        config_file_path: Optional[str] = None,
    ):
        # Validate inputs
        if db_manager is None:
            raise ValueError("db_manager is required and cannot be None")

        if default_cache_ttl < 0:
            raise ValueError("default_cache_ttl must be non-negative")

        if max_cache_entries < 0:
            raise ValueError("max_cache_entries must be non-negative")

        if config_file_path and not isinstance(config_file_path, str):
            raise ValueError("config_file_path must be a string or None")

        if encryption_key and not isinstance(encryption_key, str):
            raise ValueError("encryption_key must be a string or None")

        self.db_manager: DatabaseManager = db_manager
        self.cache_manager: Optional[CacheManager] = cache_manager
        self.encryption_key: str = encryption_key or self._generate_encryption_key()
        self.default_cache_ttl: int = default_cache_ttl
        self.enable_notifications: bool = enable_notifications
        self.max_cache_entries: int = max_cache_entries
        self.config_file_path: Optional[str] = config_file_path

        # Internal state
        self._cache: Dict[str, ConfigCacheEntry] = {}
        self._cache_lock: threading.RLock = threading.RLock()
        self._validation_rules: List[ConfigValidationRule] = []
        self._change_listeners: List[Callable[[ConfigChange], None]] = []
        self._listeners_lock: threading.RLock = threading.RLock()
        self._metrics: Dict[str, Any] = defaultdict(int)
        self._last_cache_cleanup: datetime = datetime.utcnow()

        # Weak references to avoid circular dependencies
        self._observers: "weakref.WeakSet[Any]" = weakref.WeakSet()

        # Initialize service
        self._initialize_service()

        logger.info(
            "ConfigurationService initialized. Cache TTL: %s, Max Cache Entries: %s, Encryption: %s, Notifications: %s",
            default_cache_ttl,
            max_cache_entries,
            "enabled" if encryption_key else "disabled",
            "enabled" if enable_notifications else "disabled",
        )

    def _initialize_service(self):
        """Initialize the configuration service"""
        try:
            # Register default validation rules
            self._register_default_validation_rules()

            # Start background cleanup task if needed
            if self.cache_manager is None:
                self._start_cache_cleanup_task()

            # Load configuration file if provided
            if self.config_file_path and Path(self.config_file_path).exists():
                asyncio.create_task(self._load_config_file())

        except Exception as e:
            logger.error("Failed to initialize ConfigurationService: %s", e)
            raise

    def _generate_encryption_key(self) -> str:
        """Generate a new encryption key"""
        return hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()

    def _register_default_validation_rules(self):
        """Register default validation rules"""
        rules = [
            # URL validation
            ConfigValidationRule(
                key_pattern=r".*\.url$",
                validator=lambda v: self._validate_url(v),
                error_message="Invalid URL format",
                apply_to_types={ConfigType.STRING, ConfigType.URL},
            ),
            # Email validation
            ConfigValidationRule(
                key_pattern=r".*\.email$",
                validator=lambda v: self._validate_email(v),
                error_message="Invalid email format",
                apply_to_types={ConfigType.STRING, ConfigType.EMAIL},
            ),
            # Port validation
            ConfigValidationRule(
                key_pattern=r".*\.port$",
                validator=lambda v: isinstance(v, int) and 1 <= v <= 65535,
                error_message="Port must be between 1 and 65535",
                apply_to_types={ConfigType.INTEGER},
            ),
            # Percentage validation
            ConfigValidationRule(
                key_pattern=r".*\.percent.*",
                validator=lambda v: isinstance(v, (int, float)) and 0 <= v <= 100,
                error_message="Percentage must be between 0 and 100",
                apply_to_types={ConfigType.PERCENTAGE, ConfigType.FLOAT},
            ),
            # API key validation (length check)
            ConfigValidationRule(
                key_pattern=r".*\.(api_key|token|secret)$",
                validator=lambda v: len(str(v)) >= 8,
                error_message="API key must be at least 8 characters long",
                apply_to_types={
                    ConfigType.API_KEY,
                    ConfigType.PASSWORD,
                    ConfigType.STRING,
                },
            ),
        ]

        for rule in rules:
            self.add_validation_rule(rule)

    def _validate_url(self, url: Any) -> bool:
        """Validate URL format"""
        if not isinstance(url, str):
            return False
        url_pattern = r"^https?://(?:[-\w.])+(?::[0-9]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?$"
        return bool(re.match(url_pattern, url))

    def _validate_email(self, email: Any) -> bool:
        """Validate email format"""
        if not isinstance(email, str):
            return False
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(email_pattern, email))

    def _start_cache_cleanup_task(self):
        """Start background cache cleanup task"""

        def cleanup_task():
            while True:
                try:
                    time.sleep(60)  # Run every minute
                    self._cleanup_expired_cache_entries()
                except Exception as e:
                    logger.error("Cache cleanup task error: %s", e)

        cleanup_thread = threading.Thread(target=cleanup_task, daemon=True)
        cleanup_thread.start()

    def _cleanup_expired_cache_entries(self):
        """Clean up expired cache entries"""
        if datetime.utcnow() - self._last_cache_cleanup < timedelta(minutes=5):
            return

        with self._cache_lock:
            now = datetime.utcnow()
            expired_keys = [
                key
                for key, entry in self._cache.items()
                if now > (entry.cached_at + timedelta(seconds=entry.ttl_seconds))
            ]

            for key in expired_keys:
                if key in self._cache:
                    del self._cache[key]
                    self._metrics["cache_evictions"] += 1

            # Also cleanup least recently used if cache is too large
            if len(self._cache) > self.max_cache_entries:
                sorted_entries = sorted(
                    self._cache.items(), key=lambda x: x[1].last_accessed
                )

                excess_count = len(self._cache) - self.max_cache_entries
                for key, _ in sorted_entries[:excess_count]:
                    if key in self._cache:
                        del self._cache[key]
                        self._metrics["cache_evictions"] += 1

            self._last_cache_cleanup = now

            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

    async def _load_config_file(self):
        """Load configuration from file"""
        if not self.config_file_path:
            return
        try:
            with open(self.config_file_path, "r") as f:
                if self.config_file_path.endswith(
                    ".yaml"
                ) or self.config_file_path.endswith(".yml"):
                    config_data = yaml.safe_load(f)
                else:
                    config_data = json.load(f)

            if isinstance(config_data, dict):
                await self.import_configurations(config_data, overwrite=False)
                logger.info(f"Loaded configuration from {self.config_file_path}")
            else:
                logger.warning("Config file does not contain a dictionary.")

        except Exception as e:
            logger.error(f"Failed to load config file: {str(e)}")

    # Core CRUD Operations

    async def create_configuration(
        self, request: ConfigurationCreateRequest, user_id: Optional[str] = None
    ) -> ConfigurationResponse:
        """Create a new configuration"""
        if request is None:
            raise ValueError("ConfigurationCreateRequest cannot be None")

        try:
            # Validate request
            await self._validate_configuration_request(request)

            # Check if configuration already exists
            existing = await self.get_configuration(
                request.key,
                request.environment.value,
                request.scope.value,
                request.scope_id,
            )

            if existing:
                raise ConfigValidationError(
                    f"Configuration with key '{request.key}' already exists",
                    key=request.key,
                )

            # Create configuration object
            config = Configuration(
                id=str(uuid.uuid4()),
                key=request.key,
                category=request.category,
                environment=request.environment,
                scope=request.scope,
                scope_id=request.scope_id,
                value=request.value,
                config_type=request.config_type,
                name=request.name,
                description=request.description,
                default_value=request.default_value,
                validation_rules=request.validation_rules,
                is_required=request.is_required,
                is_readonly=request.is_readonly,
                is_sensitive=request.is_sensitive,
                effective_from=request.effective_from,
                effective_until=request.effective_until,
                config_metadata=request.config_metadata or {},
                tags=request.tags or [],
                created_by=user_id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )

            # Apply custom validation rules
            await self._apply_validation_rules(config)

            # Save to database
            async with self._get_db_session() as session:
                orm_config = self._config_to_orm(config)
                session.add(orm_config)
                await session.commit()
                await session.refresh(orm_config)
                config.id = cast(str, orm_config.id)

            # Update cache
            self._update_cache(config)

            # Record change
            change = ConfigChange(
                config_id=config.id,
                change_type=ConfigChangeType.CREATED,
                new_value=config.get_display_value(),
                user_id=user_id,
                reason="Configuration created",
            )
            await self._record_change(change)

            # Notify listeners
            await self._notify_change(change)

            self._metrics["configurations_created"] += 1

            logger.info(
                "Configuration created: key=%s, id=%s, user_id=%s",
                config.key,
                config.id,
                user_id,
            )

            return ConfigurationResponse.model_validate(config.to_dict())

        except Exception as e:
            logger.error("Failed to create configuration: %s", e)
            if isinstance(e, (ConfigValidationError, ConfigNotFoundError)):
                raise
            raise ConfigValidationError(f"Failed to create configuration: {str(e)}")

    async def get_configuration(
        self,
        key: str,
        environment: str = "global",
        scope: str = "system",
        scope_id: Optional[str] = None,
        include_sensitive: bool = False,
        use_cache: bool = True,
    ) -> Optional[ConfigurationResponse]:
        """Get configuration by key with scope hierarchy"""
        if not key or not isinstance(key, str):
            raise ValueError("key must be a non-empty string")

        if not environment or not isinstance(environment, str):
            raise ValueError("environment must be a non-empty string")

        if not scope or not isinstance(scope, str):
            raise ValueError("scope must be a non-empty string")

        try:
            cache_key = self._generate_cache_key(key, environment, scope, scope_id)

            # Try cache first
            if use_cache:
                cached_config = self._get_from_cache(cache_key)
                if cached_config:
                    self._metrics["cache_hits"] += 1
                    return ConfigurationResponse.model_validate(
                        cached_config.to_dict(include_sensitive=include_sensitive)
                    )
                self._metrics["cache_misses"] += 1

            # Search with scope hierarchy (most specific to least specific)
            search_configs: List[Tuple[str, str, str, Optional[str]]] = [
                (key, environment, scope, scope_id),
                (key, environment, scope, None),
                (key, environment, "system", None),
                (key, "global", scope, scope_id),
                (key, "global", scope, None),
                (key, "global", "system", None),
            ]

            async with self._get_db_session() as session:
                for (
                    search_key,
                    search_env,
                    search_scope,
                    search_scope_id,
                ) in search_configs:
                    stmt = (
                        select(ConfigurationORM)
                        .where(ConfigurationORM.key == search_key)
                        .where(ConfigurationORM.environment == search_env)
                        .where(ConfigurationORM.scope == search_scope)
                        .where(ConfigurationORM.is_active.is_(True))
                    )

                    if search_scope_id:
                        stmt = stmt.where(ConfigurationORM.scope_id == search_scope_id)
                    else:
                        stmt = stmt.where(ConfigurationORM.scope_id.is_(None))

                    result = await session.execute(stmt)
                    orm_config = result.scalars().first()

                    if orm_config:
                        config = self._orm_to_config(orm_config)

                        # Check if effective
                        if config.is_effective():
                            # Update cache with original search key
                            if use_cache:
                                self._update_cache(config, cache_key)

                            self._metrics["configurations_retrieved"] += 1

                            return ConfigurationResponse.model_validate(
                                config.to_dict(include_sensitive=include_sensitive)
                            )

            return None

        except Exception as e:
            logger.error("Failed to get configuration for key '%s': %s", key, e)
            if isinstance(e, (ConfigValidationError, ConfigNotFoundError)):
                raise
            raise ConfigNotFoundError(f"Failed to get configuration: {str(e)}", key=key)

    async def update_configuration(
        self,
        key: str,
        request: ConfigurationUpdateRequest,
        environment: str = "global",
        scope: str = "system",
        scope_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> ConfigurationResponse:
        """Update existing configuration"""
        if not key or not isinstance(key, str):
            raise ValueError("key must be a non-empty string")

        if request is None:
            raise ValueError("ConfigurationUpdateRequest cannot be None")

        try:
            async with self._get_db_session() as session:
                stmt = (
                    select(ConfigurationORM)
                    .where(ConfigurationORM.key == key)
                    .where(ConfigurationORM.environment == environment)
                    .where(ConfigurationORM.scope == scope)
                    .where(ConfigurationORM.is_active.is_(True))
                )

                if scope_id:
                    stmt = stmt.where(ConfigurationORM.scope_id == scope_id)
                else:
                    stmt = stmt.where(ConfigurationORM.scope_id.is_(None))

                result = await session.execute(stmt)
                orm_config = result.scalars().first()

                if not orm_config:
                    raise ConfigNotFoundError(
                        f"Configuration '{key}' not found in database"
                    )

                # Check if readonly
                if cast(bool, orm_config.is_readonly):
                    raise ConfigValidationError(f"Configuration '{key}' is read-only")

                # Store old values for audit
                old_config = self._orm_to_config(orm_config)
                old_value = old_config.get_display_value(include_sensitive=True)

                update_data = request.model_dump(exclude_unset=True)

                # Update fields
                if "value" in update_data:
                    # Validate new value
                    temp_config = Configuration(
                        id=cast(str, orm_config.id),
                        key=cast(str, orm_config.key),
                        config_type=ConfigType(cast(str, orm_config.config_type)),
                        value=update_data["value"],
                        validation_rules=cast(
                            Optional[Dict[str, Any]], orm_config.validation_rules
                        ),
                        category=ConfigCategory(cast(str, orm_config.category)),
                        environment=ConfigEnvironment(
                            cast(str, orm_config.environment)
                        ),
                        scope=ConfigScope(cast(str, orm_config.scope)),
                    )
                    temp_config.validate_value()

                    orm_config.previous_value = orm_config.value
                    orm_config.value = update_data["value"]

                for field_name, field_value in update_data.items():
                    if hasattr(orm_config, field_name) and field_name != "value":
                        setattr(orm_config, field_name, field_value)

                # Update audit fields
                setattr(orm_config, "updated_by", user_id)
                setattr(orm_config, "updated_at", datetime.utcnow())
                setattr(orm_config, "change_reason", request.change_reason)
                setattr(orm_config, "version", cast(int, orm_config.version) + 1)

                await session.commit()
                await session.refresh(orm_config)

                # Convert back to domain object
                updated_config = self._orm_to_config(orm_config)

                # Apply validation rules
                await self._apply_validation_rules(updated_config)

                # Update cache
                self._invalidate_cache(key, environment, scope, scope_id)
                self._update_cache(updated_config)

                # Record change
                change = ConfigChange(
                    config_id=updated_config.id,
                    change_type=ConfigChangeType.UPDATED,
                    old_value=old_value,
                    new_value=updated_config.get_display_value(include_sensitive=True),
                    user_id=user_id,
                    reason=request.change_reason or "Configuration updated",
                )
                await self._record_change(change)

                # Notify listeners
                await self._notify_change(change)

                self._metrics["configurations_updated"] += 1

                logger.info(
                    "Configuration updated: key=%s, id=%s, user_id=%s",
                    key,
                    updated_config.id,
                    user_id,
                )

                return ConfigurationResponse.model_validate(updated_config.to_dict())

        except Exception as e:
            logger.error("Failed to update configuration for key '%s': %s", key, e)
            if isinstance(e, (ConfigValidationError, ConfigNotFoundError)):
                raise
            raise ConfigValidationError(f"Failed to update configuration: {str(e)}")

    async def delete_configuration(
        self,
        key: str,
        environment: str = "global",
        scope: str = "system",
        scope_id: Optional[str] = None,
        user_id: Optional[str] = None,
        soft_delete: bool = True,
    ) -> bool:
        """Delete configuration (soft or hard delete)"""
        if not key or not isinstance(key, str):
            raise ValueError("key must be a non-empty string")

        try:
            async with self._get_db_session() as session:
                stmt = (
                    select(ConfigurationORM)
                    .where(ConfigurationORM.key == key)
                    .where(ConfigurationORM.environment == environment)
                    .where(ConfigurationORM.scope == scope)
                )

                if scope_id:
                    stmt = stmt.where(ConfigurationORM.scope_id == scope_id)
                else:
                    stmt = stmt.where(ConfigurationORM.scope_id.is_(None))

                result = await session.execute(stmt)
                orm_config = result.scalars().first()

                if not orm_config:
                    raise ConfigNotFoundError(f"Configuration '{key}' not found")

                # Check if readonly
                if cast(bool, orm_config.is_readonly):
                    raise ConfigValidationError(f"Configuration '{key}' is read-only")

                old_value = orm_config.value
                config_id = cast(str, orm_config.id)

                if soft_delete:
                    # Soft delete - mark as inactive
                    setattr(orm_config, "is_active", False)
                    setattr(orm_config, "updated_by", user_id)
                    setattr(orm_config, "updated_at", datetime.utcnow())
                    setattr(
                        orm_config,
                        "change_reason",
                        "Configuration deleted (soft)",
                    )
                else:
                    # Hard delete - remove from database
                    await session.delete(orm_config)

                await session.commit()

                # Remove from cache
                self._invalidate_cache(key, environment, scope, scope_id)

                # Record change
                change = ConfigChange(
                    config_id=config_id,
                    change_type=ConfigChangeType.DELETED,
                    old_value=old_value,
                    user_id=user_id,
                    reason=f"Configuration deleted ({'soft' if soft_delete else 'hard'})",
                )
                await self._record_change(change)

                # Notify listeners
                await self._notify_change(change)

                self._metrics["configurations_deleted"] += 1

                logger.info(
                    "Configuration deleted: key=%s, soft_delete=%s, user_id=%s",
                    key,
                    soft_delete,
                    user_id,
                )

                return True

        except Exception as e:
            logger.error("Failed to delete configuration for key '%s': %s", key, e)
            if isinstance(e, (ConfigValidationError, ConfigNotFoundError)):
                raise
            return False

    # Advanced Query Operations

    async def query_configurations(
        self, request: ConfigurationQueryRequest
    ) -> List[ConfigurationResponse]:
        """Query configurations with advanced filtering"""
        if request is None:
            raise ValueError("ConfigurationQueryRequest cannot be None")

        try:
            async with self._get_db_session() as session:
                stmt = select(ConfigurationORM)

                # Apply filters
                if request.key:
                    stmt = stmt.where(ConfigurationORM.key == request.key)

                if request.category:
                    stmt = stmt.where(
                        ConfigurationORM.category == request.category.value
                    )

                if request.environment:
                    stmt = stmt.where(
                        ConfigurationORM.environment == request.environment.value
                    )

                if request.scope:
                    stmt = stmt.where(ConfigurationORM.scope == request.scope.value)

                if request.scope_id:
                    stmt = stmt.where(ConfigurationORM.scope_id == request.scope_id)

                if request.config_type:
                    stmt = stmt.where(
                        ConfigurationORM.config_type == request.config_type.value
                    )

                if request.is_required is not None:
                    stmt = stmt.where(
                        ConfigurationORM.is_required == request.is_required
                    )

                if request.is_sensitive is not None:
                    stmt = stmt.where(
                        ConfigurationORM.is_sensitive == request.is_sensitive
                    )

                if not request.include_inactive:
                    stmt = stmt.where(ConfigurationORM.is_active.is_(True))

                # Pattern matching for keys
                if request.key_pattern:
                    stmt = stmt.where(
                        ConfigurationORM.key.like(f"%{request.key_pattern}%")
                    )

                # Tag filtering
                if request.tags:
                    for tag in request.tags:
                        stmt = stmt.where(ConfigurationORM.tags.contains([tag]))

                # Pagination
                if request.offset:
                    stmt = stmt.offset(request.offset)
                if request.limit:
                    stmt = stmt.limit(request.limit)

                # Order by key
                stmt = stmt.order_by(ConfigurationORM.key)

                result = await session.execute(stmt)
                orm_configs = result.scalars().all()

                # Convert to response objects
                configs = []
                for orm_config in orm_configs:
                    config = self._orm_to_config(orm_config)
                    if config.is_effective():
                        config_dict = config.to_dict(
                            include_sensitive=request.include_sensitive_values
                        )
                        configs.append(
                            ConfigurationResponse.model_validate(config_dict)
                        )

                self._metrics["configurations_queried"] += 1

                logger.debug(f"Queried {len(configs)} configurations")

                return configs

        except Exception as e:
            logger.error("Failed to query configurations: %s", e)
            raise ConfigValidationError(f"Failed to query configurations: {str(e)}")

    async def get_configurations_bulk(
        self,
        keys: List[str],
        environment: str = "global",
        scope: str = "system",
        scope_id: Optional[str] = None,
        include_sensitive: bool = False,
    ) -> ConfigurationBulkResponse:
        """Get multiple configurations in bulk"""
        if keys is None:
            raise ValueError("keys cannot be None")

        if not isinstance(keys, list):
            raise ValueError("keys must be a list")

        try:
            configs: Dict[str, Any] = {}
            tasks = [
                self.get_configuration(
                    key, environment, scope, scope_id, include_sensitive
                )
                for key in keys
            ]
            results = await asyncio.gather(*tasks)

            for key, config in zip(keys, results):
                if config:
                    configs[key] = config.value

            return ConfigurationBulkResponse(
                configs=configs,
                total_count=len(configs),
                environment=ConfigEnvironment(environment),
                scope=ConfigScope(scope),
            )

        except Exception as e:
            logger.error("Failed to get bulk configurations: %s", e)
            raise ConfigValidationError(f"Failed to get bulk configurations: {str(e)}")

    # Convenience Methods

    async def get_configuration_value(
        self,
        key: str,
        default: Optional[T] = None,
        environment: str = "global",
        scope: str = "system",
        scope_id: Optional[str] = None,
        expected_type: Optional[type[T]] = None,
    ) -> Optional[T]:
        """Get configuration value with type conversion and fallback"""
        if not key or not isinstance(key, str):
            raise ValueError("key must be a non-empty string")

        try:
            config = await self.get_configuration(key, environment, scope, scope_id)
            if not config or config.value is None:
                return default

            value = config.value

            # Type conversion if requested
            if expected_type:
                return self._get_typed_value(key, value, expected_type)

            return cast(T, value)

        except Exception as e:
            logger.debug(
                "Failed to get configuration value for key '%s', using default. Error: %s",
                key,
                e,
            )
            return default

    async def set_configuration_value(
        self,
        key: str,
        value: Any,
        environment: str = "global",
        scope: str = "system",
        scope_id: Optional[str] = None,
        user_id: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> bool:
        """Set configuration value (create or update)"""
        if not key or not isinstance(key, str):
            raise ValueError("key must be a non-empty string")

        try:
            existing = await self.get_configuration(key, environment, scope, scope_id)

            if existing:
                # Update existing
                request = ConfigurationUpdateRequest(
                    value=value,
                    change_reason=reason,
                    name=None,
                    description=None,
                    validation_rules=None,
                    is_readonly=None,
                    effective_from=None,
                    effective_until=None,
                    config_metadata=None,
                    tags=None,
                    updated_by=None,
                )
                await self.update_configuration(
                    key, request, environment, scope, scope_id, user_id
                )
            else:
                # Create new with basic settings
                request = ConfigurationCreateRequest(
                    key=key,
                    name=key.replace(".", " ").replace("_", " ").title(),
                    value=value,
                    config_type=self._infer_config_type(value),
                    category=self._infer_category(key),
                    environment=ConfigEnvironment(environment),
                    scope=ConfigScope(scope),
                    scope_id=scope_id,
                    description=None,
                    default_value=None,
                    validation_rules=None,
                    is_required=False,
                    is_readonly=False,
                    is_sensitive=False,
                    effective_from=None,
                    effective_until=None,
                    config_metadata=None,
                    tags=None,
                    created_by=None,
                )
                await self.create_configuration(request, user_id)

            return True

        except Exception as e:
            logger.error("Failed to set configuration value for key '%s': %s", key, e)
            return False

    def _infer_config_type(self, value: Any) -> ConfigType:
        """Infer configuration type from value"""
        if isinstance(value, bool):
            return ConfigType.BOOLEAN
        elif isinstance(value, int):
            return ConfigType.INTEGER
        elif isinstance(value, float):
            return ConfigType.FLOAT
        elif isinstance(value, dict):
            return ConfigType.JSON_OBJECT
        elif isinstance(value, list):
            return ConfigType.JSON_ARRAY
        else:
            return ConfigType.STRING

    def _infer_category(self, key: str) -> ConfigCategory:
        """Infer category from key"""
        key_lower = key.lower()

        if any(word in key_lower for word in ["db", "database"]):
            return ConfigCategory.DATABASE
        elif any(word in key_lower for word in ["cache", "redis"]):
            return ConfigCategory.CACHE
        elif any(word in key_lower for word in ["auth", "jwt", "token"]):
            return ConfigCategory.SECURITY
        elif any(word in key_lower for word in ["trade", "trading"]):
            return ConfigCategory.TRADING
        elif any(word in key_lower for word in ["risk"]):
            return ConfigCategory.RISK_MANAGEMENT
        elif any(word in key_lower for word in ["ai", "ml", "model"]):
            return ConfigCategory.AI_ENGINE
        elif any(word in key_lower for word in ["broker", "api"]):
            return ConfigCategory.BROKER_API
        elif any(word in key_lower for word in ["log"]):
            return ConfigCategory.LOGGING
        elif any(word in key_lower for word in ["ui", "frontend"]):
            return ConfigCategory.UI_SETTINGS
        else:
            return ConfigCategory.SYSTEM

    # Validation and Rules

    def add_validation_rule(self, rule: ConfigValidationRule):
        """Add custom validation rule"""
        if rule is None:
            raise ValueError("rule cannot be None")

        if not isinstance(rule, ConfigValidationRule):
            raise ValueError("rule must be a ConfigValidationRule instance")

        self._validation_rules.append(rule)
        logger.info(f"Added validation rule for pattern: {rule.key_pattern}")

    async def _validate_configuration_request(
        self, request: ConfigurationCreateRequest
    ):
        """Validate configuration request"""
        if not request.key or not request.key.strip():
            raise ConfigValidationError("Configuration key is required")

        if not request.name or not request.name.strip():
            raise ConfigValidationError("Configuration name is required")

        # Validate key format
        if not self._is_valid_key_format(request.key):
            raise ConfigValidationError(
                "Invalid key format. Use alphanumeric characters, dots, underscores, and hyphens only"
            )

    def _is_valid_key_format(self, key: str) -> bool:
        """Validate key format"""
        if not key or not key.strip():
            return False

        key = key.strip().lower()
        return bool(re.match(r"^[a-z0-9._-]+$", key))

    async def _apply_validation_rules(self, config: Configuration):
        """Apply custom validation rules"""
        for rule in self._validation_rules:
            if re.match(rule.key_pattern, config.key, re.IGNORECASE):
                if not rule.apply_to_types or config.config_type in rule.apply_to_types:
                    if not rule.validator(config.value):
                        raise ConfigValidationError(
                            f"{rule.error_message} for key '{config.key}'",
                            key=config.key,
                        )

    # Cache Management

    def _generate_cache_key(
        self, key: str, environment: str, scope: str, scope_id: Optional[str]
    ) -> str:
        """Generate cache key"""
        return f"config:{key}:{environment}:{scope}:{scope_id or 'null'}"

    def _get_from_cache(self, cache_key: str) -> Optional[Configuration]:
        """Get configuration from cache"""
        with self._cache_lock:
            entry = self._cache.get(cache_key)
            if entry and not entry.is_expired:
                entry.touch()
                return entry.config
            elif entry:
                # Remove expired entry
                del self._cache[cache_key]
                self._metrics["cache_evictions"] += 1
        return None

    def _update_cache(self, config: Configuration, cache_key: Optional[str] = None):
        """Update cache with configuration"""
        if not cache_key:
            cache_key = self._generate_cache_key(
                config.key,
                config.environment.value,
                config.scope.value,
                config.scope_id,
            )

        with self._cache_lock:
            entry = ConfigCacheEntry(
                config=config,
                cached_at=datetime.utcnow(),
                ttl_seconds=self.default_cache_ttl,
            )
            self._cache[cache_key] = entry
            self._metrics["cache_updates"] += 1

    def _invalidate_cache(
        self,
        key: str,
        environment: Optional[str] = None,
        scope: Optional[str] = None,
        scope_id: Optional[str] = None,
    ):
        """Invalidate cache entries."""
        with self._cache_lock:
            if environment and scope:
                # Invalidate specific entry
                cache_key = self._generate_cache_key(key, environment, scope, scope_id)
                if cache_key in self._cache:
                    del self._cache[cache_key]
                    self._metrics["cache_invalidations"] += 1
            else:
                # Invalidate all entries for a key across all scopes and environments
                keys_to_remove = [
                    k for k in self._cache if k.startswith(f"config:{key}:")
                ]
                for k in keys_to_remove:
                    if k in self._cache:
                        del self._cache[k]
                        self._metrics["cache_invalidations"] += 1

    def clear_cache(self):
        """Clear all cache entries"""
        with self._cache_lock:
            cleared_count = len(self._cache)
            self._cache.clear()
            self._metrics["cache_clears"] += 1
            self._metrics["cache_evictions"] += cleared_count
            logger.info(f"Cleared {cleared_count} cache entries")

    # Change Tracking and Notifications

    def add_change_listener(self, listener: Callable[[ConfigChange], None]):
        """Add configuration change listener"""
        if listener is None:
            raise ValueError("listener cannot be None")

        if not callable(listener):
            raise ValueError("listener must be callable")

        with self._listeners_lock:
            self._change_listeners.append(listener)

    async def _record_change(self, change: ConfigChange):
        """Record configuration change"""
        try:
            # Could store in database for audit trail
            self._metrics["changes_recorded"] += 1
            logger.debug(
                "Configuration change recorded: config_id=%s, type=%s",
                change.config_id,
                change.change_type.value,
            )
        except Exception as e:
            logger.error("Failed to record change: %s", e)

    async def _notify_change(self, change: ConfigChange):
        """Notify change listeners"""
        if not self.enable_notifications:
            return

        try:
            with self._listeners_lock:
                listeners = self._change_listeners.copy()

            for listener in listeners:
                try:
                    if asyncio.iscoroutinefunction(listener):
                        await listener(change)
                    else:
                        listener(change)
                except Exception as e:
                    logger.error("Change listener failed: %s", e)

            self._metrics["notifications_sent"] += 1
        except Exception as e:
            logger.error("Failed to notify change listeners: %s", e)

    # Import/Export

    async def import_configurations(
        self,
        data: Dict[str, Any],
        environment: str = "global",
        scope: str = "system",
        overwrite: bool = False,
        user_id: Optional[str] = None,
    ) -> Tuple[int, int]:
        """Import configurations from dictionary"""
        if data is None:
            raise ValueError("data cannot be None")

        if not isinstance(data, dict):
            raise ValueError("data must be a dictionary")

        try:
            created_count = 0
            updated_count = 0

            for key, value in data.items():
                try:
                    existing = await self.get_configuration(key, environment, scope)

                    if existing and not overwrite:
                        continue
                    elif existing and overwrite:
                        # Update existing
                        request = ConfigurationUpdateRequest(
                            value=value,
                            change_reason="Bulk import",
                            name=None,
                            description=None,
                            validation_rules=None,
                            is_readonly=None,
                            effective_from=None,
                            effective_until=None,
                            config_metadata=None,
                            tags=None,
                            updated_by=None,
                        )
                        await self.update_configuration(
                            key, request, environment, scope, user_id=user_id
                        )
                        updated_count += 1
                    else:
                        # Create new
                        request = ConfigurationCreateRequest(
                            key=key,
                            name=key.replace(".", " ").replace("_", " ").title(),
                            value=value,
                            config_type=self._infer_config_type(value),
                            category=self._infer_category(key),
                            environment=ConfigEnvironment(environment),
                            scope=ConfigScope(scope),
                            scope_id=None,
                            description=None,
                            default_value=None,
                            validation_rules=None,
                            is_required=False,
                            is_readonly=False,
                            is_sensitive=False,
                            effective_from=None,
                            effective_until=None,
                            config_metadata=None,
                            tags=None,
                            created_by=None,
                        )
                        await self.create_configuration(request, user_id)
                        created_count += 1

                except Exception as e:
                    logger.warning(f"Failed to import configuration {key}: {str(e)}")
                    continue

            logger.info(
                f"Import completed: {created_count} created, {updated_count} updated"
            )
            return created_count, updated_count

        except Exception as e:
            logger.error("Failed to import configurations: %s", e)
            raise ConfigValidationError(f"Import failed: {str(e)}")

    async def export_configurations(
        self,
        environment: str = "global",
        scope: str = "system",
        include_sensitive: bool = False,
        format: str = "dict",
    ) -> Union[Dict[str, Any], str]:
        """Export configurations"""
        if format not in ["dict", "json", "yaml"]:
            raise ValueError("format must be one of: dict, json, yaml")

        try:
            request = ConfigurationQueryRequest(
                environment=ConfigEnvironment(environment),
                scope=ConfigScope(scope),
                include_inactive=False,
                include_sensitive_values=include_sensitive,
                limit=10000,
                key=None,
                category=None,
                scope_id=None,
                config_type=None,
                is_required=None,
                is_sensitive=None,
                is_active=None,
                key_pattern=None,
                tags=None,
                offset=None,
            )

            configs = await self.query_configurations(request)

            export_dict = {config.key: config.value for config in configs}

            if format == "dict":
                return export_dict
            elif format == "json":
                return json.dumps(export_dict, indent=2, default=str)
            elif format == "yaml":
                return yaml.dump(export_dict, default_flow_style=False)
            else:
                # This case is already handled by the initial check, but as a safeguard:
                raise ValueError(f"Unsupported export format: {format}")

        except Exception as e:
            logger.error("Failed to export configurations: %s", e)
            raise ConfigValidationError(f"Export failed: {str(e)}")

    # Utility Methods

    @asynccontextmanager
    async def _get_db_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session with proper cleanup"""
        async with self.db_manager.get_async_session() as session:
            yield session

    def _config_to_orm(self, config: Configuration) -> ConfigurationORM:
        """Convert domain object to ORM"""
        return ConfigurationORM(
            id=config.id,
            key=config.key,
            category=config.category.value,
            environment=config.environment.value,
            scope=config.scope.value,
            scope_id=config.scope_id,
            value=config.value,
            config_type=config.config_type.value,
            encrypted_value=config.encrypted_value,
            is_encrypted=config.is_encrypted,
            name=config.name,
            description=config.description,
            default_value=config.default_value,
            validation_rules=config.validation_rules,
            is_required=config.is_required,
            is_readonly=config.is_readonly,
            is_sensitive=config.is_sensitive,
            version=config.version,
            previous_value=config.previous_value,
            change_reason=config.change_reason,
            is_active=config.is_active,
            effective_from=config.effective_from,
            effective_until=config.effective_until,
            created_by=config.created_by,
            updated_by=config.updated_by,
            config_metadata=config.config_metadata,
            tags=config.tags,
            created_at=config.created_at,
            updated_at=config.updated_at,
        )

    def _orm_to_config(self, orm_config: "ConfigurationORM") -> "Configuration":
        """Converts a ConfigurationORM object to a Configuration dataclass."""
        return Configuration(
            id=cast(str, orm_config.id),
            key=cast(str, orm_config.key),
            category=cast(ConfigCategory, orm_config.category),
            environment=cast(ConfigEnvironment, orm_config.environment),
            scope=cast(ConfigScope, orm_config.scope),
            scope_id=cast(Optional[str], orm_config.scope_id),
            value=orm_config.value,
            config_type=cast(ConfigType, orm_config.config_type),
            encrypted_value=cast(Optional[str], orm_config.encrypted_value),
            is_encrypted=cast(bool, orm_config.is_encrypted),
            name=cast(str, orm_config.name),
            description=cast(Optional[str], orm_config.description),
            default_value=orm_config.default_value,
            validation_rules=cast(Optional[Dict[str, Any]], orm_config.validation_rules),
            is_required=cast(bool, orm_config.is_required),
            is_readonly=cast(bool, orm_config.is_readonly),
            is_sensitive=cast(bool, orm_config.is_sensitive),
            version=cast(int, orm_config.version),
            previous_value=orm_config.previous_value,
            change_reason=cast(Optional[str], orm_config.change_reason),
            is_active=cast(bool, orm_config.is_active),
            effective_from=cast(Optional[datetime], orm_config.effective_from),
            effective_until=cast(Optional[datetime], orm_config.effective_until),
            created_by=cast(Optional[str], orm_config.created_by),
            updated_by=cast(Optional[str], orm_config.updated_by),
            config_metadata=cast(Dict[str, Any], orm_config.config_metadata or {}),
            tags=cast(List[str], orm_config.tags or []),
            created_at=cast(datetime, orm_config.created_at),
            updated_at=cast(datetime, orm_config.updated_at),
        )

    # Metrics and Monitoring

    def get_metrics(self) -> Dict[str, Any]:
        """Get service metrics"""
        with self._cache_lock:
            cache_size = len(self._cache)
            cache_usage_sample = {
                entry.config.key: {
                    "access_count": entry.access_count,
                    "last_accessed": entry.last_accessed.isoformat(),
                    "is_expired": entry.is_expired,
                }
                for entry in list(self._cache.values())[:10]  # Top 10 for brevity
            }

        return {
            "cache_size": cache_size,
            "cache_usage_sample": cache_usage_sample,
            "validation_rules_count": len(self._validation_rules),
            "change_listeners_count": len(self._change_listeners),
            "metrics": dict(self._metrics),
        }

    def get_health_status(self) -> Dict[str, Any]:
        """Get service health status"""
        uptime_seconds = (datetime.utcnow() - self._last_cache_cleanup).total_seconds()
        return {
            "status": "healthy",
            "cache_enabled": self.cache_manager is not None or hasattr(
                self, "_cache_cleanup_thread"
            ),
            "cache_size": len(self._cache),
            "encryption_enabled": bool(self.encryption_key),
            "notifications_enabled": self.enable_notifications,
            "uptime_seconds": uptime_seconds,
        }

    def _get_typed_value(
        self, key: str, value: Any, expected_type: Type[T]
    ) -> Optional[T]:
        """Converts a value to the expected type."""
        if value is None:
            return None

        try:
            # Handle primitive types with explicit conversion
            if expected_type is bool:
                if isinstance(value, str):
                    return cast(T, value.lower() in ("true", "1", "yes", "on"))
                return cast(T, bool(value))
            if expected_type is str:
                return cast(T, str(value))
            if expected_type is int:
                return cast(T, int(value))
            if expected_type is float:
                return cast(T, float(value))

            # For other types, we assume the stored value is already compatible
            # and just needs to be cast to the expected type. This avoids the
            # "Expected 0 positional arguments" error with `expected_type(value)`.
            return cast(T, value)
        except (ValueError, TypeError) as e:
            raise ConfigValidationError(
                f"Type conversion failed for key '{key}'. "
                f"Could not convert value '{value}' to type '{expected_type.__name__}'. "
                f"Original error: {e}",
                key=key,
            )
        except Exception as e:
            # Catch any other unexpected exception during type conversion
            logger.warning(
                "Unexpected error during type conversion for key '%s': %s. Returning value as-is.",
                key,
                e,
            )
            return cast(T, value)
