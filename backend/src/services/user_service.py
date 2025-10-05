"""
Advanced User Management Service for NIRAJ Trading System

This service provides comprehensive user management capabilities including:
- Complete CRUD operations with advanced validation
- User profile management and preferences
- Trading settings and risk configuration
- Account security and PIN management
- User activity tracking and audit logging
- User search and filtering capabilities
- Bulk operations for administrative tasks
- Advanced error handling with detailed context
- Performance optimization with caching
- Multi-tenancy support for future expansion
"""

import json
import time
import asyncio
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Union, Tuple, Callable, TypedDict
from dataclasses import dataclass, field, asdict
import re
from functools import wraps

import bcrypt
from sqlalchemy.exc import IntegrityError as SQLIntegrityError
from sqlalchemy import and_, or_, func, text, desc, asc
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session
from sqlalchemy.future import select

from ..models.user import (
    User,
    UserORM,
    TradingMode,
    UserAuthenticationError,
    UserCreateRequest,
    UserResponse,
    PinChangeRequest,
    generate_default_preferences,
)
from ..models.audit_log import AuditEventType, AuditSeverity
from ..services.audit_service import get_audit_service
from ..core.database_manager import AdvancedDatabaseManager as DatabaseManager
from ..core.cache import CacheManager
from ..utils.logger import (
    get_logger,
    get_structured_logger,
    log_error,
    LogContext,
    log_performance,
)


# TypedDicts for more specific return types
class AuthenticationResponse(TypedDict):
    authenticated: bool
    user_id: str
    username: str
    session_id: str
    session_token: str
    trading_mode: TradingMode
    last_login: Optional[str]
    authenticated_at: str


class LogoutResponse(TypedDict):
    logged_out: bool
    session_id: str
    user_id: str
    logged_out_at: str


class SessionValidationResponse(TypedDict):
    valid: bool
    session_id: str
    user_id: str
    username: str
    trading_mode: TradingMode
    validated_at: str
    session_extended: bool


class PinChangeResponse(TypedDict):
    message: str
    changed_at: str


class BulkOperationResult(TypedDict):
    user_id: str
    error: str


class BulkOperationResponse(TypedDict):
    operation: str
    requested_count: int
    successful_count: int
    failed_count: int
    errors: List[BulkOperationResult]
    processed_user_ids: List[str]


class UserServiceError(Exception):
    """Base exception for user service errors

    All optional parameters are explicitly typed as Optional to satisfy static type
    checkers (mypy/Pylance) running in strict/no implicit optional modes.
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.message: str = message
        self.error_code: str = error_code or "USER_SERVICE_ERROR"
        self.details: Dict[str, Any] = details or {}
        super().__init__(self.message)


class UserNotFoundError(UserServiceError):
    """User not found error"""

    def __init__(self, identifier: str, identifier_type: str = "user_id"):
        super().__init__(
            f"User not found by {identifier_type}: {identifier}",
            "USER_NOT_FOUND",
            {"identifier": identifier, "identifier_type": identifier_type},
        )


class UserAlreadyExistsError(UserServiceError):
    """User already exists error"""

    def __init__(self, username: str):
        super().__init__(
            f"User already exists with username: {username}",
            "USER_ALREADY_EXISTS",
            {"username": username},
        )


class InvalidUserDataError(UserServiceError):
    """Invalid user data error"""

    def __init__(self, field: str, value: Any, reason: str):
        super().__init__(
            f"Invalid {field}: {reason}",
            "INVALID_USER_DATA",
            {"field": field, "value": str(value), "reason": reason},
        )


class UserPermissionError(UserServiceError):
    """User permission error"""

    def __init__(self, action: str, user_id: str, reason: Optional[str] = None) -> None:
        message = f"Permission denied for action '{action}' on user {user_id}"
        if reason:
            message += f": {reason}"
        super().__init__(
            message,
            "USER_PERMISSION_DENIED",
            {"action": action, "user_id": user_id, "reason": reason},
        )


class UserAccountLockedError(UserServiceError):
    """User account locked error"""

    def __init__(self, user_id: str, locked_until: Optional[datetime] = None) -> None:
        message = f"User account {user_id} is locked"
        if locked_until:
            message += f" until {locked_until.isoformat()}"
        super().__init__(
            message,
            "USER_ACCOUNT_LOCKED",
            {
                "user_id": user_id,
                "locked_until": locked_until.isoformat() if locked_until else None,
                "lock_reason": "Too many failed login attempts",
            },
        )


class UserValidationError(UserServiceError):
    """User validation error"""

    def __init__(
        self,
        field: str,
        value: Any,
        reason: str,
        suggestions: Optional[List[str]] = None,
    ) -> None:
        super().__init__(
            f"Validation failed for {field}: {reason}",
            "USER_VALIDATION_ERROR",
            {
                "field": field,
                "value": str(value),
                "reason": reason,
                "suggestions": suggestions or [],
            },
        )


class UserAuthorizationError(UserServiceError):
    """User authorization error"""

    def __init__(
        self, action: str, user_id: str, required_permissions: Optional[List[str]] = None
    ) -> None:
        super().__init__(
            f"User {user_id} is not authorized to perform action: {action}",
            "USER_AUTHORIZATION_ERROR",
            {
                "user_id": user_id,
                "action": action,
                "required_permissions": required_permissions or [],
            },
        )


class UserRateLimitError(UserServiceError):
    """User rate limit exceeded error"""

    def __init__(
        self,
        user_id: str,
        action: str,
        limit: int,
        window_seconds: int,
        reset_time: datetime,
    ) -> None:
        super().__init__(
            f"Rate limit exceeded for {action}. Limit: {limit} per {window_seconds}s",
            "USER_RATE_LIMIT_ERROR",
            {
                "user_id": user_id,
                "action": action,
                "limit": limit,
                "window_seconds": window_seconds,
                "reset_time": reset_time.isoformat(),
                "retry_after": int(
                    (reset_time - datetime.now(timezone.utc)).total_seconds()
                ),
            },
        )


class UserSessionError(UserServiceError):
    """User session error"""

    def __init__(
        self, session_id: str, reason: str, user_id: Optional[str] = None
    ) -> None:
        super().__init__(
            f"Session error: {reason}",
            "USER_SESSION_ERROR",
            {
                "session_id": session_id,
                "user_id": user_id,
                "reason": reason,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )


# Pydantic Models for Advanced Operations
class UserSearchRequest(BaseModel):
    """User search request model"""

    query: Optional[str] = None
    username_pattern: Optional[str] = None
    trading_mode: Optional[TradingMode] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    last_login_after: Optional[datetime] = None
    last_login_before: Optional[datetime] = None
    min_capital: Optional[Decimal] = None
    max_capital: Optional[Decimal] = None
    risk_tolerance_min: Optional[float] = Field(None, ge=0.0, le=1.0)
    risk_tolerance_max: Optional[float] = Field(None, ge=0.0, le=1.0)
    include_inactive: bool = Field(default=False)
    limit: int = Field(default=50, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)
    sort_by: str = Field(default="created_at")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")


class UserStatsResponse(BaseModel):
    """User statistics response model"""

    total_users: int
    active_users: int
    inactive_users: int
    paper_traders: int
    live_traders: int
    users_created_today: int
    users_created_this_week: int
    users_created_this_month: int
    average_capital: Decimal
    average_risk_tolerance: float
    most_active_hours: List[int]
    trading_mode_distribution: Dict[str, int]
    risk_tolerance_distribution: Dict[str, int]


class UserActivityResponse(BaseModel):
    """User activity response model"""

    user_id: str
    username: str
    last_login: Optional[datetime]
    total_logins: int
    login_attempts: int
    account_created: datetime
    days_since_creation: int
    trading_mode: TradingMode
    is_active: bool
    last_activity: Optional[datetime]
    session_count: int


class BulkUserOperation(BaseModel):
    """Bulk user operation model"""

    operation: str = Field(
        pattern="^(update|delete|activate|deactivate|reset_attempts)$"
    )
    user_ids: List[str]
    update_data: Optional[Dict[str, Any]] = None
    reason: Optional[str] = None


class UserProfileUpdate(BaseModel):
    """Comprehensive user profile update model"""

    username: Optional[str] = Field(
        None, min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$"
    )
    default_capital: Optional[Decimal] = Field(
        None, gt=0, max_digits=15, decimal_places=2
    )
    risk_tolerance: Optional[float] = Field(None, ge=0.0, le=1.0)
    max_daily_loss: Optional[Decimal] = Field(
        None, gt=0, max_digits=15, decimal_places=2
    )
    preferences: Optional[Dict[str, Any]] = None

    @field_validator("username")
    @classmethod
    def validate_username_format(cls, v):
        if v and not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError(
                "Username can only contain letters, numbers, underscores, and hyphens"
            )
        return v

    @field_validator("preferences")
    @classmethod
    def validate_preferences_structure(cls, v):
        if v is not None:
            # Validate JSON serializability
            try:
                json.dumps(v)
            except (TypeError, ValueError):
                raise ValueError("Preferences must be JSON serializable")

            # Validate that all keys are strings
            for key in v.keys():
                if not isinstance(key, str):
                    raise ValueError("All preference keys must be strings")

        return v


@dataclass
class UserOperationContext:
    """Context for user operations"""

    operation: str
    user_id: Optional[str] = None
    operator_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class AdvancedUserService:
    """
    Advanced User Management Service

    Provides comprehensive user management capabilities with enterprise-grade
    features including advanced validation, security, performance optimization,
    and detailed audit logging.
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        cache_manager: Optional[CacheManager] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        self.db_manager = db_manager
        self.cache: Optional[CacheManager] = cache_manager
        self.config: Dict[str, Any] = config or self._get_default_config()

        # Initialize loggers
        self.logger = get_logger("niraj.user_service")
        self.audit_logger = get_structured_logger("niraj.user_audit")
        self.performance_logger = get_structured_logger("niraj.user_performance")

        # Performance metrics
        self._metrics: Dict[str, Union[int, float]] = {
            "users_created": 0,
            "users_updated": 0,
            "users_deleted": 0,
            "failed_operations": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "average_response_time": 0.0,
        }

        # Initialize caching
        self._init_caching()

        # Use structured logging via audit/performance loggers if they support keyword context
        try:
            self.logger.info("Advanced User Service initialized")
        except Exception:
            pass

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            # Caching settings
            "cache_enabled": True,
            "cache_ttl": 300,  # 5 minutes
            "cache_prefix": "niraj:users:",
            "batch_cache_size": 100,
            # Validation settings
            "strict_validation": True,
            "allow_duplicate_emails": False,
            "require_strong_pins": True,
            "pin_history_limit": 5,
            # Security settings
            "max_login_attempts": 5,
            "account_lockout_duration": 900,  # 15 minutes
            "password_expiry_days": 90,
            "require_pin_change_on_first_login": False,
            # Performance settings
            "bulk_operation_batch_size": 500,
            "search_result_limit": 1000,
            "enable_query_optimization": True,
            # Audit settings
            "enable_audit_logging": True,
            "audit_sensitive_operations": True,
            "log_performance_metrics": True,
        }

    def _init_caching(self):
        """Initialize caching system"""
        if not self.cache or not self.config.get("cache_enabled", True):
            self.logger.warning("Caching disabled or cache manager not available")
            return

        self._cache_keys: Dict[str, Union[str, Callable[[str], str]]] = {
            "user_by_id": lambda user_id: f"{self.config['cache_prefix']}id:{user_id}",
            "user_by_username": lambda username: f"{self.config['cache_prefix']}username:{username}",
            "user_stats": f"{self.config['cache_prefix']}stats",
            "user_search": lambda query_hash: f"{self.config['cache_prefix']}search:{query_hash}",
            "user_activity": lambda user_id: f"{self.config['cache_prefix']}activity:{user_id}",
        }

    # Authentication Methods
    @log_performance("user_service.authenticate_user")
    async def authenticate_user(
        self,
        username: str,
        pin: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        context: Optional[UserOperationContext] = None,
    ) -> AuthenticationResponse:
        """
        Authenticate user with PIN and create session

        Args:
            username: Username to authenticate
            pin: PIN for authentication
            ip_address: Client IP address
            user_agent: Client user agent
            context: Operation context

        Returns:
            Dict containing authentication result with session info

        Raises:
            UserNotFoundError: If user not found
            UserAuthenticationError: If authentication fails
            UserAccountLockedError: If account is locked
        """
        try:
            with LogContext(
                operation="authenticate_user",
                username=username,
                ip_address=ip_address,
            ):
                # Get user by username
                user = await self.get_user_by_username(username)

                # Check if account is locked
                if user.login_attempts >= self.config.get("max_login_attempts", 5):
                    lockout_duration = self.config.get("account_lockout_duration", 900)
                    if user.updated_at:
                        locked_until = user.updated_at + timedelta(seconds=lockout_duration)

                        if datetime.now(timezone.utc) < locked_until:
                            raise UserAccountLockedError(user.user_id, locked_until)

                    # Reset attempts if lockout period has passed
                    await self._reset_login_attempts(user.user_id)

                # Verify PIN
                # Need the hashed pin; UserResponse does not expose pin_hash, so fetch ORM
                user_pin_hash: Optional[str] = None
                async with self.db_manager.get_async_session() as session:
                    user_orm = await self.db_manager.read(session, UserORM, user.user_id)
                    if user_orm:
                        user_pin_hash = user_orm.pin_hash  # type: ignore[assignment]

                if not user_pin_hash or not bcrypt.checkpw(
                    pin.encode("utf-8"), user_pin_hash.encode("utf-8")
                ):
                    # Increment failed attempts
                    await self._increment_login_attempts(user.user_id)

                    # Create audit log for failed attempt
                    await self._create_audit_log(
                        None,  # No session yet
                        user.user_id,
                        AuditEventType.SECURITY_ALERT,
                        AuditSeverity.WARNING,
                        {
                            "event": "Failed login attempt",
                            "ip_address": ip_address,
                            "user_agent": user_agent,
                            "attempts_remaining": max(
                                0,
                                self.config.get("max_login_attempts", 5)
                                - (user.login_attempts + 1),
                            ),
                        },
                    )

                    attempts_remaining = max(
                        0,
                        self.config.get("max_login_attempts", 5) - (user.login_attempts + 1),
                    )

                    if attempts_remaining == 0:
                        raise UserAccountLockedError(
                            user.user_id,
                            datetime.now(timezone.utc) + timedelta(
                                seconds=self.config.get("account_lockout_duration", 900)
                            )
                        )

                    raise UserAuthenticationError(
                        f"Invalid PIN. {attempts_remaining} attempts remaining.",
                        attempts=attempts_remaining,
                    )

                # Authentication successful
                session_id = self._generate_session_id()
                session_token = self._generate_session_token()

                # Update user login info
                async with self.db_manager.get_transaction() as session:
                    user_orm = await self.db_manager.read(session, UserORM, user.user_id)
                    if user_orm:
                        await self.db_manager.update(
                            session,
                            user_orm,
                            {
                                "last_login": datetime.now(timezone.utc),
                                "login_attempts": 0,  # Reset on successful login
                                "updated_at": datetime.now(timezone.utc),
                            },
                        )

                    # Create audit log for successful login
                    await self._create_audit_log(
                        session,
                        user.user_id,
                        AuditEventType.LOGIN_SUCCESS,
                        AuditSeverity.INFO,
                        {
                            "ip_address": ip_address,
                            "user_agent": user_agent,
                            "session_id": session_id,
                        },
                    )

                # Cache session info
                await self._cache_session(session_id, user.user_id, session_token)

                # Clear user cache to refresh login info
                await self._invalidate_user_cache(user.user_id, user.username)

                try:
                    self.logger.info(
                        f"User authenticated successfully user_id={user.user_id} username={username}"
                    )
                except Exception:
                    pass

                return {
                    "authenticated": True,
                    "user_id": user.user_id,
                    "username": user.username,
                    "session_id": session_id,
                    "session_token": session_token,
                    "trading_mode": user.trading_mode,
                    "last_login": user.last_login.isoformat() if user.last_login else None,
                    "authenticated_at": datetime.now(timezone.utc).isoformat(),
                }

        except (UserNotFoundError, UserAuthenticationError, UserAccountLockedError):
            raise
        except Exception as e:
            self.logger.error(f"Authentication failed: {str(e)}")
            log_error(e, {"username": username})
            raise UserServiceError(f"Authentication failed: {str(e)}")

    @log_performance("user_service.logout_user")
    async def logout_user(
        self,
        session_id: str,
        context: Optional[UserOperationContext] = None,
    ) -> LogoutResponse:
        """
        Logout user and invalidate session

        Args:
            session_id: Session to invalidate
            context: Operation context

        Returns:
            Dict containing logout confirmation

        Raises:
            UserSessionError: If session invalidation fails
        """
        try:
            with LogContext(operation="logout_user", session_id=session_id):
                # Get user from session
                user_id = await self._get_user_from_session(session_id)
                if not user_id:
                    raise UserSessionError(session_id, "Invalid session")

                # Invalidate session
                await self._invalidate_session(session_id)

                # Create audit log
                await self._create_audit_log(
                    None,
                    user_id,
                    AuditEventType.LOGOUT,
                    AuditSeverity.INFO,
                    {
                        "action": "logout",
                        "session_id": session_id,
                        "ip_address": context.ip_address if context else None,
                    },
                )

                try:
                    self.logger.info(f"User logged out user_id={user_id} session_id={session_id}")
                except Exception:
                    pass

                return {
                    "logged_out": True,
                    "session_id": session_id,
                    "user_id": user_id,
                    "logged_out_at": datetime.now(timezone.utc).isoformat(),
                }

        except UserSessionError:
            raise
        except Exception as e:
            self.logger.error(f"Logout failed: {str(e)}")
            log_error(e, {"session_id": session_id})
            raise UserServiceError(f"Logout failed: {str(e)}")

    @log_performance("user_service.validate_session")
    async def validate_session(
        self,
        session_id: str,
        session_token: Optional[str] = None,
        extend_session: bool = True,
    ) -> SessionValidationResponse:
        """
        Validate user session

        Args:
            session_id: Session ID to validate
            session_token: Session token for additional validation
            extend_session: Whether to extend session TTL

        Returns:
            Dict containing validation result

        Raises:
            UserSessionError: If session is invalid
        """
        try:
            with LogContext(operation="validate_session", session_id=session_id):
                # Get user from session
                user_id = await self._get_user_from_session(session_id)
                if not user_id:
                    raise UserSessionError(session_id, "Session not found or expired")

                # Validate token if provided
                if session_token:
                    cached_token = await self._get_session_token(session_id)
                    if cached_token != session_token:
                        raise UserSessionError(session_id, "Invalid session token")

                # Get user info
                user = await self.get_user(user_id)

                # Extend session if requested
                if extend_session:
                    await self._extend_session(session_id)

                return {
                    "valid": True,
                    "session_id": session_id,
                    "user_id": user.user_id,
                    "username": user.username,
                    "trading_mode": user.trading_mode,
                    "validated_at": datetime.now(timezone.utc).isoformat(),
                    "session_extended": extend_session,
                }

        except UserSessionError:
            raise
        except Exception as e:
            self.logger.error(f"Session validation failed: {str(e)}")
            log_error(e, {"session_id": session_id})
            raise UserServiceError(f"Session validation failed: {str(e)}")

    # Session Management Helpers
    def _generate_session_id(self) -> str:
        """Generate unique session ID"""
        import uuid
        return str(uuid.uuid4())

    def _generate_session_token(self) -> str:
        """Generate session token"""
        import secrets
        return secrets.token_urlsafe(32)

    async def _cache_session(self, session_id: str, user_id: str, token: str):
        """Cache session information"""
        if not self.cache:
            return

        try:
            session_key = f"{self.config['cache_prefix']}session:{session_id}"
            token_key = f"{self.config['cache_prefix']}token:{session_id}"

            session_data: Dict[str, str] = {
                "user_id": user_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "last_activity": datetime.now(timezone.utc).isoformat(),
            }

            # Session TTL (24 hours)
            ttl = 86400

            await asyncio.gather(
                self.cache.set(session_key, json.dumps(session_data), ttl=ttl),
                self.cache.set(token_key, token, ttl=ttl),
                # Keep track of user's active sessions (limit to 5)
                self._add_user_session(user_id, session_id),
                return_exceptions=True,
            )
        except Exception as e:
            self.logger.warning(f"Failed to cache session: {str(e)}")

    async def _get_user_from_session(self, session_id: str) -> Optional[str]:
        """Get user ID from session"""
        if not self.cache:
            return None

        try:
            session_key = f"{self.config['cache_prefix']}session:{session_id}"
            cached_data = await self.cache.get(session_key)

            if cached_data:
                session_data: Dict[str, str]
                if isinstance(cached_data, str):
                    session_data = json.loads(cached_data)
                elif isinstance(cached_data, dict):
                    session_data = cached_data
                else:
                    return None

                return session_data.get("user_id")

            return None
        except Exception as e:
            self.logger.warning(f"Failed to get session: {str(e)}")
            return None

    async def _get_session_token(self, session_id: str) -> Optional[str]:
        """Get session token"""
        if not self.cache:
            return None

        try:
            token_key = f"{self.config['cache_prefix']}token:{session_id}"
            token = await self.cache.get(token_key)
            return str(token) if token else None
        except Exception as e:
            self.logger.warning(f"Failed to get session token: {str(e)}")
            return None

    async def _invalidate_session(self, session_id: str):
        """Invalidate session"""
        if not self.cache:
            return

        try:
            session_key = f"{self.config['cache_prefix']}session:{session_id}"
            token_key = f"{self.config['cache_prefix']}token:{session_id}"

            # Get user_id to remove from user sessions
            user_id = await self._get_user_from_session(session_id)
            if user_id:
                await self._remove_user_session(user_id, session_id)

            await asyncio.gather(
                self.cache.delete(session_key),
                self.cache.delete(token_key),
                return_exceptions=True,
            )
        except Exception as e:
            self.logger.warning(f"Failed to invalidate session: {str(e)}")

    async def _extend_session(self, session_id: str):
        """Extend session TTL"""
        if not self.cache:
            return

        try:
            session_key = f"{self.config['cache_prefix']}session:{session_id}"
            cached_data = await self.cache.get(session_key)

            if cached_data:
                session_data: Dict[str, str]
                if isinstance(cached_data, str):
                    session_data = json.loads(cached_data)
                elif isinstance(cached_data, dict):
                    session_data = cached_data
                else:
                    return

                # Update last activity
                session_data["last_activity"] = datetime.now(timezone.utc).isoformat()

                # Extend TTL (24 hours from now)
                ttl = 86400
                await self.cache.set(session_key, json.dumps(session_data), ttl=ttl)
        except Exception as e:
            self.logger.warning(f"Failed to extend session: {str(e)}")

    async def _add_user_session(self, user_id: str, session_id: str):
        """Add session to user's active sessions"""
        if not self.cache:
            return

        try:
            user_session_key = f"{self.config['cache_prefix']}user_sessions:{user_id}"
            cached_sessions = await self.cache.get(user_session_key)

            sessions: List[str]
            if cached_sessions:
                if isinstance(cached_sessions, str):
                    sessions = json.loads(cached_sessions)
                elif isinstance(cached_sessions, list):
                    sessions = cached_sessions
                else:
                    sessions = []
            else:
                sessions = []

            # Add new session
            if session_id not in sessions:
                sessions.append(session_id)

            # Keep only last 5 sessions
            sessions = sessions[-5:]

            ttl = 86400  # 24 hours
            await self.cache.set(user_session_key, json.dumps(sessions), ttl=ttl)
        except Exception as e:
            self.logger.warning(f"Failed to add user session: {str(e)}")

    async def _remove_user_session(self, user_id: str, session_id: str):
        """Remove session from user's active sessions"""
        if not self.cache:
            return

        try:
            user_session_key = f"{self.config['cache_prefix']}user_sessions:{user_id}"
            cached_sessions = await self.cache.get(user_session_key)

            if cached_sessions:
                sessions: List[str]
                if isinstance(cached_sessions, str):
                    sessions = json.loads(cached_sessions)
                elif isinstance(cached_sessions, list):
                    sessions = cached_sessions
                else:
                    return

                # Remove session
                if session_id in sessions:
                    sessions.remove(session_id)

                ttl = 86400  # 24 hours
                await self.cache.set(user_session_key, json.dumps(sessions), ttl=ttl)
        except Exception as e:
            self.logger.warning(f"Failed to remove user session: {str(e)}")

    async def _increment_login_attempts(self, user_id: str):
        """Increment login attempts counter"""
        async with self.db_manager.get_transaction() as session:
            user_orm = await self.db_manager.read(session, UserORM, user_id)
            if user_orm:
                await self.db_manager.update(
                    session,
                    user_orm,
                    {
                        "login_attempts": user_orm.login_attempts + 1,
                        "updated_at": datetime.now(timezone.utc),
                    },
                )

    async def _reset_login_attempts(self, user_id: str):
        """Reset login attempts counter"""
        async with self.db_manager.get_transaction() as session:
            user_orm = await self.db_manager.read(session, UserORM, user_id)
            if user_orm:
                await self.db_manager.update(
                    session,
                    user_orm,
                    {
                        "login_attempts": 0,
                        "updated_at": datetime.now(timezone.utc),
                    },
                )

    @log_performance("user_service.create_user")
    async def create_user(
        self,
        user_data: UserCreateRequest,
        context: Optional[UserOperationContext] = None,
    ) -> UserResponse:
        """
        Create a new user with comprehensive validation and security checks

        Args:
            user_data: User creation data
            context: Operation context for audit logging

        Returns:
            UserResponse: Created user data (excluding sensitive information)

        Raises:
            UserAlreadyExistsError: If username already exists
            InvalidUserDataError: If user data is invalid
            UserServiceError: If creation fails
        """
        start_time = time.time()

        try:
            with LogContext(
                operation="create_user",
                username=user_data.username,
                operator_id=context.operator_id if context else None,
                ip_address=context.ip_address if context else None,
            ):
                # Validate user data
                await self._validate_user_creation_data(user_data)

                # Check username availability
                await self._check_username_availability(user_data.username)

                # Create User entity
                user = User.create_user(
                    username=user_data.username,
                    pin=user_data.pin,
                    default_capital=user_data.default_capital,
                    risk_tolerance=user_data.risk_tolerance,
                    max_daily_loss=user_data.max_daily_loss,
                    preferences=user_data.preferences or generate_default_preferences(),
                )

                # Save to database
                async with self.db_manager.get_transaction() as session:
                    user_orm = UserORM(
                        user_id=user.user_id,
                        username=user.username,
                        created_at=user.created_at,
                        updated_at=user.updated_at,
                        preferences=user.preferences,
                        pin_hash=user.pin_hash,
                        last_login=user.last_login,
                        login_attempts=user.login_attempts,
                        default_capital=user.default_capital,
                        risk_tolerance=user.risk_tolerance,
                        max_daily_loss=user.max_daily_loss,
                        trading_mode=user.trading_mode.value,
                    )

                    await self.db_manager.create(session, user_orm)

                    # Create audit log entry
                    if self.config.get("enable_audit_logging", True):
                        await self._create_audit_log(
                            session,
                            user.user_id,
                            AuditEventType.CONFIG_CHANGE,  # Using CONFIG_CHANGE for user creation
                            AuditSeverity.INFO,
                            {
                                "username": user.username,
                                "trading_mode": user.trading_mode.value,
                                "operator_id": context.operator_id if context else None,
                                "ip_address": context.ip_address if context else None,
                                "action": "user_created",
                            },
                        )

                # Cache the user data
                await self._cache_user_data(UserResponse.from_orm(user_orm))

                # Create response
                user_response = UserResponse.from_orm(user_orm)

                # Update metrics
                self._metrics["users_created"] = (
                    self._metrics.get("users_created", 0) + 1
                )

                # Log successful creation
                duration = time.time() - start_time
                try:
                    self.logger.info(
                        f"User created successfully in {duration:.3f}s user_id={user.user_id} username={user.username}"
                    )
                except Exception:
                    pass

                return user_response

        except (UserAlreadyExistsError, InvalidUserDataError):
            self._metrics["failed_operations"] = (
                self._metrics.get("failed_operations", 0) + 1
            )
            raise
        except SQLIntegrityError as e:
            self._metrics["failed_operations"] = (
                self._metrics.get("failed_operations", 0) + 1
            )
            if "username" in str(e).lower():
                raise UserAlreadyExistsError(user_data.username)
            raise UserServiceError(f"Database integrity error: {str(e)}")
        except Exception as e:
            self._metrics["failed_operations"] = (
                self._metrics.get("failed_operations", 0) + 1
            )
            self.logger.error(f"User creation failed: {str(e)}")
            log_error(e, {"username": user_data.username})
            raise UserServiceError(f"User creation failed: {str(e)}")

    @log_performance("user_service.get_user")
    async def get_user(
        self, user_id: str, include_sensitive: bool = False
    ) -> UserResponse:
        """
        Get user by ID with caching support

        Args:
            user_id: User identifier
            include_sensitive: Whether to include sensitive data

        Returns:
            UserResponse: User data

        Raises:
            UserNotFoundError: If user not found
            UserServiceError: If retrieval fails
        """
        try:
            with LogContext(operation="get_user", user_id=user_id):
                # Try cache first
                cached_user = await self._get_user_from_cache(user_id)
                if cached_user:
                    self._metrics["cache_hits"] = (
                        self._metrics.get("cache_hits", 0) + 1
                    )
                    return cached_user

                self._metrics["cache_misses"] = (
                    self._metrics.get("cache_misses", 0) + 1
                )

                # Get from database
                async with self.db_manager.get_async_session() as session:
                    user_orm = await self.db_manager.read(session, UserORM, user_id)

                    if not user_orm:
                        raise UserNotFoundError(user_id)

                    user_response = UserResponse.from_orm(user_orm)

                    # Cache the result
                    await self._cache_user_data(user_response)

                    return user_response

        except UserNotFoundError:
            raise
        except Exception as e:
            self.logger.error(f"User retrieval failed: {str(e)}")
            log_error(e, {"user_id": user_id})
            raise UserServiceError(f"User retrieval failed: {str(e)}")

    @log_performance("user_service.get_user_by_username")
    async def get_user_by_username(
        self, username: str, include_sensitive: bool = False
    ) -> UserResponse:
        """
        Get user by username with caching support

        Args:
            username: Username
            include_sensitive: Whether to include sensitive data

        Returns:
            UserResponse: User data

        Raises:
            UserNotFoundError: If user not found
            UserServiceError: If retrieval fails
        """
        try:
            with LogContext(operation="get_user_by_username", username=username):
                # Try cache first
                cache_key_func = self._cache_keys.get("user_by_username")
                if self.cache and callable(cache_key_func):
                    cache_key = cache_key_func(username)
                    cached_user_id = await self.cache.get(cache_key)
                    if cached_user_id and isinstance(cached_user_id, str):
                        self._metrics["cache_hits"] = (
                            self._metrics.get("cache_hits", 0) + 1
                        )
                        return await self.get_user(cached_user_id, include_sensitive)

                self._metrics["cache_misses"] = (
                    self._metrics.get("cache_misses", 0) + 1
                )

                # Get from database
                async with self.db_manager.get_async_session() as session:
                    result = await session.execute(
                        text("SELECT * FROM users WHERE username = :username"),
                        {"username": username},
                    )
                    row = result.first()

                    if not row:
                        raise UserNotFoundError(username, "username")

                    # Convert row to UserORM
                    user_orm = UserORM(**row._asdict())
                    user_response = UserResponse.from_orm(user_orm)

                    # Cache both user data and username->id mapping
                    await self._cache_user_data(user_response)
                    if self.cache and callable(cache_key_func):
                        await self.cache.set(
                            cache_key_func(username),
                            user_response.user_id,
                            ttl=self.config.get("cache_ttl", 300),
                        )

                    return user_response

        except UserNotFoundError:
            raise
        except Exception as e:
            self.logger.error(f"User retrieval by username failed: {str(e)}")
            log_error(e, {"username": username})
            raise UserServiceError(f"User retrieval by username failed: {str(e)}")

    @log_performance("user_service.update_user")
    async def update_user(
        self,
        user_id: str,
        update_data: UserProfileUpdate,
        context: Optional[UserOperationContext] = None,
    ) -> UserResponse:
        """
        Update user profile with comprehensive validation

        Args:
            user_id: User identifier
            update_data: Update data
            context: Operation context for audit logging

        Returns:
            UserResponse: Updated user data

        Raises:
            UserNotFoundError: If user not found
            InvalidUserDataError: If update data is invalid
            UserServiceError: If update fails
        """
        start_time = time.time()

        try:
            with LogContext(
                operation="update_user",
                user_id=user_id,
                operator_id=context.operator_id if context else None,
            ):
                # Validate update data
                await self._validate_user_update_data(user_id, update_data)

                # Get current user
                current_user = await self.get_user(user_id)

                # Prepare update dictionary
                update_dict: Dict[str, Any] = {}
                changes: List[str] = []

                if (
                    update_data.username
                    and update_data.username != current_user.username
                ):
                    await self._check_username_availability(update_data.username)
                    update_dict["username"] = update_data.username
                    changes.append(
                        f"username: {current_user.username} -> {update_data.username}"
                    )

                if update_data.default_capital is not None:
                    update_dict["default_capital"] = update_data.default_capital
                    changes.append(
                        f"default_capital: {current_user.default_capital} -> {update_data.default_capital}"
                    )

                if update_data.risk_tolerance is not None:
                    update_dict["risk_tolerance"] = update_data.risk_tolerance
                    changes.append(
                        f"risk_tolerance: {current_user.risk_tolerance} -> {update_data.risk_tolerance}"
                    )

                if update_data.max_daily_loss is not None:
                    update_dict["max_daily_loss"] = update_data.max_daily_loss
                    changes.append(
                        f"max_daily_loss: {current_user.max_daily_loss} -> {update_data.max_daily_loss}"
                    )

                if update_data.preferences is not None:
                    # Merge with existing preferences
                    merged_preferences = current_user.preferences.copy()
                    merged_preferences.update(update_data.preferences)
                    update_dict["preferences"] = merged_preferences
                    changes.append("preferences updated")

                if not update_dict:
                    return current_user  # No changes to apply

                update_dict["updated_at"] = datetime.now(timezone.utc)

                # Update in database
                async with self.db_manager.get_transaction() as session:
                    user_orm = await self.db_manager.read(session, UserORM, user_id)
                    if not user_orm:
                        raise UserNotFoundError(user_id)

                    # Apply updates
                    updated_user = await self.db_manager.update(
                        session, user_orm, update_dict
                    )

                    # Create audit log entry
                    if self.config.get("enable_audit_logging", True):
                        await self._create_audit_log(
                            session,
                            user_id,
                            AuditEventType.CONFIG_CHANGE,  # Using CONFIG_CHANGE for user update
                            AuditSeverity.INFO,
                            {
                                "action": "user_updated",
                                "changes": changes,
                                "operator_id": context.operator_id if context else None,
                                "ip_address": context.ip_address if context else None,
                                "reason": context.reason if context else None,
                            },
                        )

                # Clear cache
                await self._invalidate_user_cache(user_id, current_user.username)

                # Create response
                user_response = UserResponse.from_orm(updated_user)

                # Cache updated data
                await self._cache_user_data(user_response)

                # Update metrics
                self._metrics["users_updated"] = (
                    self._metrics.get("users_updated", 0) + 1
                )

                # Log successful update
                duration = time.time() - start_time
                try:
                    self.logger.info(
                        f"User updated successfully in {duration:.3f}s user_id={user_id} changes={changes}"
                    )
                except Exception:
                    pass

                return user_response

        except (UserNotFoundError, InvalidUserDataError, UserAlreadyExistsError):
            self._metrics["failed_operations"] = (
                self._metrics.get("failed_operations", 0) + 1
            )
            raise
        except Exception as e:
            self._metrics["failed_operations"] = (
                self._metrics.get("failed_operations", 0) + 1
            )
            self.logger.error(f"User update failed: {str(e)}")
            log_error(e, {"user_id": user_id})
            raise UserServiceError(f"User update failed: {str(e)}")

    @log_performance("user_service.delete_user")
    async def delete_user(
        self,
        user_id: str,
        context: Optional[UserOperationContext] = None,
        soft_delete: bool = True,
    ) -> bool:
        """
        Delete user (soft or hard delete)

        Args:
            user_id: User identifier
            context: Operation context for audit logging
            soft_delete: Whether to perform soft delete

        Returns:
            bool: True if successful

        Raises:
            UserNotFoundError: If user not found
            UserServiceError: If deletion fails
        """
        try:
            with LogContext(
                operation="delete_user",
                user_id=user_id,
                operator_id=context.operator_id if context else None,
                soft_delete=soft_delete,
            ):
                # Get user first to validate existence
                user = await self.get_user(user_id)

                async with self.db_manager.get_transaction() as session:
                    user_orm = await self.db_manager.read(session, UserORM, user_id)
                    if not user_orm:
                        raise UserNotFoundError(user_id)

                    if soft_delete:
                        # Soft delete - mark as inactive
                        preferences = user_orm.preferences or {}
                        preferences.update(
                            {
                                "_deleted": True,
                                "_deleted_at": datetime.now(timezone.utc).isoformat(),
                            }
                        )
                        await self.db_manager.update(
                            session,
                            user_orm,
                            {
                                "updated_at": datetime.now(timezone.utc),
                                "preferences": preferences,
                            },
                        )
                        operation_type = AuditEventType.CONFIG_CHANGE  # User deactivation
                    else:
                        # Hard delete
                        await self.db_manager.delete(session, user_orm)
                        operation_type = AuditEventType.CONFIG_CHANGE  # User deletion

                    # Create audit log entry
                    if self.config.get("enable_audit_logging", True):
                        await self._create_audit_log(
                            session,
                            user_id,
                            operation_type,
                            AuditSeverity.WARNING,
                            {
                                "action": (
                                    "soft_delete" if soft_delete else "hard_delete"
                                ),
                                "username": user.username,
                                "operator_id": context.operator_id if context else None,
                                "ip_address": context.ip_address if context else None,
                                "reason": context.reason if context else None,
                            },
                        )

                # Clear cache
                await self._invalidate_user_cache(user_id, user.username)

                # Update metrics
                self._metrics["users_deleted"] = (
                    self._metrics.get("users_deleted", 0) + 1
                )

                try:
                    self.logger.info(
                        f"User {'soft' if soft_delete else 'hard'} deleted successfully user_id={user_id} username={user.username}"
                    )
                except Exception:
                    pass

                return True

        except UserNotFoundError:
            raise
        except Exception as e:
            self._metrics["failed_operations"] = (
                self._metrics.get("failed_operations", 0) + 1
            )
            self.logger.error(f"User deletion failed: {str(e)}")
            log_error(e, {"user_id": user_id})
            raise UserServiceError(f"User deletion failed: {str(e)}")

    # Advanced User Management Features
    @log_performance("user_service.search_users")
    async def search_users(
        self, search_request: UserSearchRequest
    ) -> Tuple[List[UserResponse], int]:
        """
        Advanced user search with filtering and pagination

        Args:
            search_request: Search criteria and pagination

        Returns:
            Tuple[List[UserResponse], int]: Users matching criteria and total count

        Raises:
            UserServiceError: If search fails
        """
        try:
            with LogContext(operation="search_users", query=search_request.query):
                # Generate cache key for search results
                search_hash = self._generate_search_hash(search_request)
                cache_key_func = self._cache_keys.get("user_search")
                cache_key = (
                    cache_key_func(search_hash)
                    if callable(cache_key_func)
                    else f"fallback_search_key:{search_hash}"
                )

                # Try cache first
                if self.cache:
                    cached_result = await self.cache.get(cache_key)
                    if cached_result and isinstance(cached_result, str):
                        self._metrics["cache_hits"] = (
                            self._metrics.get("cache_hits", 0) + 1
                        )
                        cached_data = json.loads(cached_result)
                        return (
                            [
                                UserResponse(**user_data)
                                for user_data in cached_data["users"]
                            ],
                            cached_data["total_count"],
                        )

                self._metrics["cache_misses"] = (
                    self._metrics.get("cache_misses", 0) + 1
                )

                async with self.db_manager.get_async_session() as session:
                    # Build query
                    query = select(UserORM)

                    # Apply filters
                    if search_request.query:
                        query = query.where(
                            UserORM.username.contains(search_request.query)
                        )

                    if search_request.username_pattern:
                        query = query.where(
                            UserORM.username.like(search_request.username_pattern)
                        )

                    if search_request.trading_mode:
                        query = query.where(
                            UserORM.trading_mode == search_request.trading_mode.value
                        )

                    if search_request.created_after:
                        query = query.where(
                            UserORM.created_at >= search_request.created_after
                        )

                    if search_request.created_before:
                        query = query.where(
                            UserORM.created_at <= search_request.created_before
                        )

                    if search_request.last_login_after:
                        query = query.where(
                            UserORM.last_login >= search_request.last_login_after
                        )

                    if search_request.last_login_before:
                        query = query.where(
                            UserORM.last_login <= search_request.last_login_before
                        )

                    if search_request.min_capital:
                        query = query.where(
                            UserORM.default_capital >= search_request.min_capital
                        )

                    if search_request.max_capital:
                        query = query.where(
                            UserORM.default_capital <= search_request.max_capital
                        )

                    if search_request.risk_tolerance_min is not None:
                        query = query.where(
                            UserORM.risk_tolerance >= search_request.risk_tolerance_min
                        )

                    if search_request.risk_tolerance_max is not None:
                        query = query.where(
                            UserORM.risk_tolerance <= search_request.risk_tolerance_max
                        )

                    # Exclude soft-deleted users unless explicitly requested
                    if not search_request.include_inactive:
                        query = query.where(
                            or_(
                                UserORM.preferences.is_(None),
                                UserORM.preferences.astext.contains('"_deleted": true')
                                .is_not(True),
                            )
                        )

                    # Get total count
                    count_query = select(func.count()).select_from(query.alias())
                    total_count_result = await session.execute(count_query)
                    total_count = total_count_result.scalar_one()

                    # Apply sorting
                    sort_column = getattr(
                        UserORM, search_request.sort_by, UserORM.created_at
                    )
                    if search_request.sort_order == "desc":
                        query = query.order_by(desc(sort_column))
                    else:
                        query = query.order_by(asc(sort_column))

                    # Apply pagination
                    query = query.offset(search_request.offset).limit(
                        search_request.limit
                    )

                    # Execute query
                    result = await session.execute(query)
                    users = result.scalars().all()

                    # Convert to response models
                    user_responses = [UserResponse.from_orm(user) for user in users]

                    # Cache results
                    if self.cache and isinstance(cache_key, str):
                        cache_data = {
                            "users": [user.dict() for user in user_responses],
                            "total_count": total_count,
                        }
                        await self.cache.set(
                            cache_key,
                            json.dumps(cache_data, default=str),
                            ttl=60,  # Short TTL for search results
                        )

                    try:
                        self.logger.info(
                            f"User search completed found={len(user_responses)} total={total_count} query={search_request.query}"
                        )
                    except Exception:
                        pass

                    return user_responses, total_count

        except Exception as e:
            self.logger.error(f"User search failed: {str(e)}")
            log_error(e, {"search_request": search_request.dict()})
            raise UserServiceError(f"User search failed: {str(e)}")

    @log_performance("user_service.get_user_statistics")
    async def get_user_statistics(self) -> UserStatsResponse:
        """
        Get comprehensive user statistics

        Returns:
            UserStatsResponse: User statistics

        Raises:
            UserServiceError: If statistics retrieval fails
        """
        try:
            with LogContext(operation="get_user_statistics"):
                # Try cache first
                cache_key = self._cache_keys.get("user_stats")
                if self.cache and isinstance(cache_key, str):
                    cached_stats = await self.cache.get(cache_key)
                    if cached_stats and isinstance(cached_stats, str):
                        self._metrics["cache_hits"] = (
                            self._metrics.get("cache_hits", 0) + 1
                        )
                        return UserStatsResponse(**json.loads(cached_stats))

                self._metrics["cache_misses"] = (
                    self._metrics.get("cache_misses", 0) + 1
                )

                async with self.db_manager.get_async_session() as session:
                    # Calculate various statistics
                    now = datetime.now(timezone.utc)
                    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
                    week_start = today - timedelta(days=today.weekday())
                    month_start = today.replace(day=1)

                    # Total users
                    total_users_result = await session.execute(
                        select(func.count(UserORM.user_id))
                    )
                    total_users = total_users_result.scalar_one()

                    # Active users (not soft-deleted)
                    active_users_query = select(func.count(UserORM.user_id)).where(
                        or_(
                            UserORM.preferences.is_(None),
                            UserORM.preferences.astext.contains('"_deleted": true')
                            .is_not(True),
                        )
                    )
                    active_users_result = await session.execute(active_users_query)
                    active_users = active_users_result.scalar_one()

                    inactive_users = total_users - active_users

                    # Trading mode distribution
                    paper_traders_result = await session.execute(
                        select(func.count(UserORM.user_id)).where(
                            UserORM.trading_mode == TradingMode.PAPER.value
                        )
                    )
                    paper_traders = paper_traders_result.scalar_one()

                    live_traders_result = await session.execute(
                        select(func.count(UserORM.user_id)).where(
                            UserORM.trading_mode == TradingMode.LIVE.value
                        )
                    )
                    live_traders = live_traders_result.scalar_one()

                    # Users created today/week/month
                    users_today_result = await session.execute(
                        select(func.count(UserORM.user_id)).where(
                            UserORM.created_at >= today
                        )
                    )
                    users_today = users_today_result.scalar_one()

                    users_week_result = await session.execute(
                        select(func.count(UserORM.user_id)).where(
                            UserORM.created_at >= week_start
                        )
                    )
                    users_week = users_week_result.scalar_one()

                    users_month_result = await session.execute(
                        select(func.count(UserORM.user_id)).where(
                            UserORM.created_at >= month_start
                        )
                    )
                    users_month = users_month_result.scalar_one()

                    # Average capital and risk tolerance
                    capital_stats_result = await session.execute(
                        select(
                            func.avg(UserORM.default_capital),
                            func.avg(UserORM.risk_tolerance),
                        )
                    )
                    capital_stats = capital_stats_result.first()

                    avg_capital = (
                        capital_stats[0] if capital_stats else Decimal("0.00")
                    )
                    avg_risk_tolerance = capital_stats[1] if capital_stats else 0.0

                    # Most active hours (placeholder - would need login history)
                    most_active_hours = list(range(9, 16))  # Market hours

                    # Trading mode distribution
                    trading_mode_dist = {
                        TradingMode.PAPER.value: paper_traders,
                        TradingMode.LIVE.value: live_traders,
                    }

                    # Risk tolerance distribution
                    low_risk_result = await session.execute(
                        select(func.count(UserORM.user_id)).where(
                            UserORM.risk_tolerance < 0.3
                        )
                    )
                    medium_risk_result = await session.execute(
                        select(func.count(UserORM.user_id)).where(
                            and_(
                                UserORM.risk_tolerance >= 0.3,
                                UserORM.risk_tolerance < 0.7,
                            )
                        )
                    )
                    high_risk_result = await session.execute(
                        select(func.count(UserORM.user_id)).where(
                            UserORM.risk_tolerance >= 0.7
                        )
                    )
                    risk_tolerance_dist = {
                        "low": low_risk_result.scalar_one(),
                        "medium": medium_risk_result.scalar_one(),
                        "high": high_risk_result.scalar_one(),
                    }

                    # Create statistics response
                    stats = UserStatsResponse(
                        total_users=total_users,
                        active_users=active_users,
                        inactive_users=inactive_users,
                        paper_traders=paper_traders,
                        live_traders=live_traders,
                        users_created_today=users_today,
                        users_created_this_week=users_week,
                        users_created_this_month=users_month,
                        average_capital=avg_capital,
                        average_risk_tolerance=avg_risk_tolerance,
                        most_active_hours=most_active_hours,
                        trading_mode_distribution=trading_mode_dist,
                        risk_tolerance_distribution=risk_tolerance_dist,
                    )

                    # Cache statistics
                    if self.cache and isinstance(cache_key, str):
                        await self.cache.set(
                            cache_key, stats.json(), ttl=300  # 5 minutes
                        )

                    try:
                        self.logger.info("User statistics retrieved")
                    except Exception:
                        pass
                    return stats

        except Exception as e:
            self.logger.error(f"User statistics retrieval failed: {str(e)}")
            log_error(e)
            raise UserServiceError(f"User statistics retrieval failed: {str(e)}")

    @log_performance("user_service.change_user_pin")
    async def change_user_pin(
        self,
        user_id: str,
        pin_change_request: PinChangeRequest,
        context: Optional[UserOperationContext] = None,
    ) -> PinChangeResponse:
        """
        Change user PIN with security validation

        Args:
            user_id: User identifier
            pin_change_request: PIN change data
            context: Operation context for audit logging

        Returns:
            Dict containing success confirmation

        Raises:
            UserNotFoundError: If user not found
            UserAuthenticationError: If current PIN is invalid
            InvalidUserDataError: If new PIN is invalid
            UserServiceError: If PIN change fails
        """
        try:
            with LogContext(
                operation="change_user_pin",
                user_id=user_id,
                operator_id=context.operator_id if context else None,
            ):
                async with self.db_manager.get_transaction() as session:
                    user_orm = await self.db_manager.read(session, UserORM, user_id)
                    if not user_orm:
                        raise UserNotFoundError(user_id)

                    # Get pin_hash as string
                    pin_hash_value: Optional[str] = str(user_orm.pin_hash) if user_orm.pin_hash else None  # type: ignore[arg-type]

                    # Verify current PIN
                    if not pin_hash_value or not bcrypt.checkpw(
                        pin_change_request.old_pin.encode("utf-8"),
                        pin_hash_value.encode("utf-8"),
                    ):
                        # Log security event
                        await self._create_audit_log(
                            session,
                            user_id,
                            AuditEventType.SECURITY_ALERT,
                            AuditSeverity.WARNING,
                            {
                                "event": "Invalid PIN during PIN change attempt",
                                "ip_address": context.ip_address if context else None,
                                "operator_id": context.operator_id if context else None,
                            },
                        )
                        raise UserAuthenticationError("Current PIN is incorrect")

                    # Validate new PIN
                    await self._validate_new_pin(
                        pin_change_request.new_pin, pin_hash_value
                    )

                    # Hash new PIN
                    new_pin_hash = bcrypt.hashpw(
                        pin_change_request.new_pin.encode("utf-8"), bcrypt.gensalt()
                    ).decode("utf-8")

                    # Update PIN
                    await self.db_manager.update(
                        session,
                        user_orm,
                        {
                            "pin_hash": new_pin_hash,
                            "updated_at": datetime.now(timezone.utc),
                            "login_attempts": 0,  # Reset failed attempts
                        },
                    )

                    # Create audit log
                    await self._create_audit_log(
                        session,
                        user_id,
                        AuditEventType.PIN_CHANGE,  # Using PIN_CHANGE instead of SECURITY_PIN_CHANGE
                        AuditSeverity.INFO,
                        {
                            "action": "PIN changed",
                            "operator_id": context.operator_id if context else None,
                            "ip_address": context.ip_address if context else None,
                        },
                    )

                # Clear user cache
                await self._invalidate_user_cache(user_id, str(user_orm.username))  # type: ignore[arg-type]

                try:
                    self.logger.info(f"PIN changed successfully user_id={user_id}")
                except Exception:
                    pass

                return {
                    "message": "PIN changed successfully",
                    "changed_at": datetime.now(timezone.utc).isoformat(),
                }

        except (UserNotFoundError, UserAuthenticationError, InvalidUserDataError):
            raise
        except Exception as e:
            self.logger.error(f"PIN change failed: {str(e)}")
            log_error(e, {"user_id": user_id})
            raise UserServiceError(f"PIN change failed: {str(e)}")

    @log_performance("user_service.bulk_user_operation")
    async def bulk_user_operation(
        self,
        operation: BulkUserOperation,
        context: Optional[UserOperationContext] = None,
    ) -> BulkOperationResponse:
        """
        Perform bulk operations on multiple users

        Args:
            operation: Bulk operation details
            context: Operation context for audit logging

        Returns:
            Dict containing operation results

        Raises:
            UserServiceError: If bulk operation fails
        """
        try:
            with LogContext(
                operation="bulk_user_operation",
                bulk_operation=operation.operation,
                user_count=len(operation.user_ids),
            ):
                results: BulkOperationResponse = {
                    "operation": operation.operation,
                    "requested_count": len(operation.user_ids),
                    "successful_count": 0,
                    "failed_count": 0,
                    "errors": [],
                    "processed_user_ids": [],
                }

                batch_size = self.config.get("bulk_operation_batch_size", 500)

                # Process in batches
                for i in range(0, len(operation.user_ids), batch_size):
                    batch_user_ids = operation.user_ids[i : i + batch_size]

                    async with self.db_manager.get_transaction() as session:
                        for user_id in batch_user_ids:
                            try:
                                user_orm = await self.db_manager.read(
                                    session, UserORM, user_id
                                )
                                if not user_orm:
                                    results["errors"].append(
                                        {"user_id": user_id, "error": "User not found"}
                                    )
                                    results["failed_count"] += 1
                                    continue

                                # Perform operation
                                if operation.operation == "update":
                                    if operation.update_data:
                                        update_dict = operation.update_data.copy()
                                        update_dict["updated_at"] = datetime.now(
                                            timezone.utc
                                        )
                                        await self.db_manager.update(
                                            session, user_orm, update_dict
                                        )

                                elif operation.operation == "delete":
                                    # Soft delete
                                    preferences = user_orm.preferences or {}
                                    preferences.update(
                                        {
                                            "_deleted": True,
                                            "_deleted_at": datetime.now(
                                                timezone.utc
                                            ).isoformat(),
                                        }
                                    )
                                    await self.db_manager.update(
                                        session,
                                        user_orm,
                                        {
                                            "preferences": preferences,
                                            "updated_at": datetime.now(timezone.utc),
                                        },
                                    )

                                elif operation.operation == "reset_attempts":
                                    await self.db_manager.update(
                                        session,
                                        user_orm,
                                        {
                                            "login_attempts": 0,
                                            "updated_at": datetime.now(timezone.utc),
                                        },
                                    )

                                # Create audit log
                                if self.config.get("enable_audit_logging", True):
                                    await self._create_audit_log(
                                        session,
                                        user_id,
                                        AuditEventType.CONFIG_CHANGE,  # Using CONFIG_CHANGE for bulk operations
                                        AuditSeverity.INFO,
                                        {
                                            "action": "bulk_user_operation",
                                            "bulk_operation": operation.operation,
                                            "reason": operation.reason,
                                            "operator_id": (
                                                context.operator_id if context else None
                                            ),
                                        },
                                    )

                                results["successful_count"] += 1
                                results["processed_user_ids"].append(user_id)

                                # Clear cache for this user
                                username_value = str(user_orm.username) if user_orm.username else None  # type: ignore[arg-type]
                                if username_value:
                                    await self._invalidate_user_cache(
                                        user_id, username_value
                                    )

                            except Exception as e:
                                results["errors"].append(
                                    {"user_id": user_id, "error": str(e)}
                                )
                                results["failed_count"] += 1

                try:
                    self.logger.info(
                        f"Bulk operation completed op={operation.operation} success={results['successful_count']} failed={results['failed_count']}"
                    )
                except Exception:
                    pass

                return results

        except Exception as e:
            self.logger.error(f"Bulk operation failed: {str(e)}")
            log_error(e, {"operation": operation.operation})
            raise UserServiceError(f"Bulk operation failed: {str(e)}")

    # Utility and Helper Methods
    async def _validate_user_creation_data(self, user_data: UserCreateRequest):
        """Validate user creation data"""
        try:
            # Validate username format
            if not re.match(r"^[a-zA-Z0-9_-]+$", user_data.username):
                raise InvalidUserDataError(
                    "username",
                    user_data.username,
                    "Username can only contain letters, numbers, underscores, and hyphens",
                )

            # Validate PIN strength
            if self.config.get("require_strong_pins", True):
                if len(user_data.pin) != 4 or not user_data.pin.isdigit():
                    raise InvalidUserDataError(
                        "pin", user_data.pin, "PIN must be a 4-digit number"
                    )

                if user_data.pin in [
                    "0000",
                    "1234",
                    "1111",
                    "2222",
                    "3333",
                    "4444",
                    "5555",
                    "6666",
                    "7777",
                    "8888",
                    "9999",
                ]:
                    raise InvalidUserDataError(
                        "pin", user_data.pin, "PIN too weak, avoid common patterns"
                    )

                if len(set(user_data.pin)) == 1:
                    raise InvalidUserDataError(
                        "pin", user_data.pin, "PIN cannot have all same digits"
                    )

            # Validate financial parameters
            if user_data.default_capital <= 0:
                raise InvalidUserDataError(
                    "default_capital", user_data.default_capital, "Must be positive"
                )

            if not 0.0 <= user_data.risk_tolerance <= 1.0:
                raise InvalidUserDataError(
                    "risk_tolerance",
                    user_data.risk_tolerance,
                    "Must be between 0.0 and 1.0",
                )

            if user_data.max_daily_loss <= 0:
                raise InvalidUserDataError(
                    "max_daily_loss", user_data.max_daily_loss, "Must be positive"
                )

            # Validate preferences
            if user_data.preferences:
                try:
                    json.dumps(user_data.preferences)
                except (TypeError, ValueError):
                    raise InvalidUserDataError(
                        "preferences",
                        user_data.preferences,
                        "Must be JSON serializable",
                    )

        except InvalidUserDataError:
            raise
        except Exception as e:
            raise InvalidUserDataError("validation", str(user_data), str(e))

    async def _validate_user_update_data(
        self, user_id: str, update_data: UserProfileUpdate
    ):
        """Validate user update data"""
        try:
            if update_data.username:
                if not re.match(r"^[a-zA-Z0-9_-]+$", update_data.username):
                    raise InvalidUserDataError(
                        "username",
                        update_data.username,
                        "Username can only contain letters, numbers, underscores, and hyphens",
                    )

            if update_data.default_capital is not None and update_data.default_capital <= 0:
                raise InvalidUserDataError(
                    "default_capital",
                    update_data.default_capital,
                    "Must be positive",
                )

            if (
                update_data.risk_tolerance is not None
                and not 0.0 <= update_data.risk_tolerance <= 1.0
            ):
                raise InvalidUserDataError(
                    "risk_tolerance",
                    update_data.risk_tolerance,
                    "Must be between 0.0 and 1.0",
                )

            if (
                update_data.max_daily_loss is not None
                and update_data.max_daily_loss <= 0
            ):
                raise InvalidUserDataError(
                    "max_daily_loss", update_data.max_daily_loss, "Must be positive"
                )

            if update_data.preferences:
                try:
                    json.dumps(update_data.preferences)
                except (TypeError, ValueError):
                    raise InvalidUserDataError(
                        "preferences",
                        update_data.preferences,
                        "Must be JSON serializable",
                    )

        except InvalidUserDataError:
            raise
        except Exception as e:
            raise InvalidUserDataError("validation", str(update_data), str(e))

    async def _validate_new_pin(self, new_pin: str, current_pin_hash: Optional[str]):
        """Validate new PIN"""
        if self.config.get("require_strong_pins", True):
            if len(new_pin) != 4 or not new_pin.isdigit():
                raise InvalidUserDataError(
                    "pin", new_pin, "PIN must be a 4-digit number"
                )

            if new_pin in [
                "0000",
                "1234",
                "1111",
                "2222",
                "3333",
                "4444",
                "5555",
                "6666",
                "7777",
                "8888",
                "9999",
            ]:
                raise InvalidUserDataError(
                    "pin", new_pin, "PIN too weak, avoid common patterns"
                )

            if len(set(new_pin)) == 1:
                raise InvalidUserDataError(
                    "pin", new_pin, "PIN cannot have all same digits"
                )

        if current_pin_hash and bcrypt.checkpw(
            new_pin.encode("utf-8"), current_pin_hash.encode("utf-8")
        ):
            raise InvalidUserDataError(
                "pin", new_pin, "New PIN cannot be the same as the old PIN"
            )

    async def _check_username_availability(self, username: str):
        """Check if username is available"""
        try:
            await self.get_user_by_username(username)
            # If it doesn't raise UserNotFoundError, then it exists
            raise UserAlreadyExistsError(username)
        except UserNotFoundError:
            # This is the desired outcome
            return

    async def _create_audit_log(
        self,
        session: Optional[Session],
        user_id: str,
        event_type: AuditEventType,
        severity: AuditSeverity,
        details: Dict[str, Any],
    ):
        """Create an audit log entry"""
        if not self.config.get("enable_audit_logging", True):
            return

        try:
            audit_service = await get_audit_service()
            details_with_context = details.copy()

            log_method: Callable = audit_service.create_audit_log

            await log_method(
                event_type=event_type,
                event_description=details_with_context.pop("description", str(event_type.name)),
                severity=severity,
                user_id=user_id,
                metadata=details_with_context,
            )
        except Exception as e:
            self.logger.error(f"Failed to create audit log: {str(e)}")

    async def _cache_user_data(self, user_data: Union[User, UserResponse]):
        """Cache user data"""
        if not self.cache:
            return

        try:
            user_id = user_data.user_id
            cache_key_func = self._cache_keys.get("user_by_id")
            if callable(cache_key_func):
                cache_key = cache_key_func(user_id)

                json_data = ""
                if isinstance(user_data, UserResponse):
                    json_data = user_data.json()
                elif isinstance(user_data, User):
                    json_data = json.dumps(asdict(user_data), default=str)

                await self.cache.set(
                    cache_key,
                    json_data,
                    ttl=self.config.get("cache_ttl", 300),
                )
        except Exception as e:
            self.logger.warning(f"Failed to cache user data: {str(e)}")

    async def _get_user_from_cache(self, user_id: str) -> Optional[UserResponse]:
        """Get user data from cache"""
        if not self.cache:
            return None

        try:
            cache_key_func = self._cache_keys.get("user_by_id")
            if callable(cache_key_func):
                cache_key = cache_key_func(user_id)
                cached_data = await self.cache.get(cache_key)
                if cached_data and isinstance(cached_data, str):
                    return UserResponse.parse_raw(cached_data)
            return None
        except Exception as e:
            self.logger.warning(f"Failed to get user from cache: {str(e)}")
            return None

    async def _invalidate_user_cache(self, user_id: str, username: Optional[str]):
        """Invalidate user cache"""
        if not self.cache:
            return

        try:
            tasks = []
            cache_key_id_func = self._cache_keys.get("user_by_id")
            if callable(cache_key_id_func):
                tasks.append(self.cache.delete(cache_key_id_func(user_id)))

            if username:
                cache_key_username_func = self._cache_keys.get("user_by_username")
                if callable(cache_key_username_func):
                    tasks.append(
                        self.cache.delete(cache_key_username_func(username))
                    )

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            self.logger.warning(f"Failed to invalidate user cache: {str(e)}")

    def _generate_search_hash(self, search_request: UserSearchRequest) -> str:
        """Generate a hash for a search request"""
        import hashlib

        # Use a stable representation of the search request
        search_str = json.dumps(search_request.dict(), sort_keys=True, default=str)
        return hashlib.md5(search_str.encode("utf-8")).hexdigest()

    def get_performance_metrics(self) -> Dict[str, Union[int, float]]:
        """Get performance metrics"""
        return self._metrics.copy()

    def reset_performance_metrics(self):
        """Reset performance metrics"""
        for key in self._metrics:
            self._metrics[key] = 0 if isinstance(self._metrics[key], int) else 0.0
        self.logger.info("Performance metrics have been reset.")


# Global service instance
user_service = None


def get_user_service(
    db_manager: DatabaseManager, cache_manager: Optional[CacheManager]
) -> AdvancedUserService:
    """
    Factory function to get an instance of the AdvancedUserService.
    This helps with dependency injection and testing.

    Args:
        db_manager: Database manager instance
        cache_manager: Cache manager instance (optional)

    Returns:
        AdvancedUserService: Configured user service instance
    """
    global user_service

    if user_service is None:
        user_service = AdvancedUserService(
            db_manager=db_manager, cache_manager=cache_manager
        )

    return user_service


# Utility decorators
def require_user_permission(action: str):
    """Decorator to require specific user permission"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # This would be implemented with actual permission checking
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def validate_user_input(validation_func: Callable):
    """Decorator to validate user input"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract and validate input data
            return await func(*args, **kwargs)

        return wrapper

    return decorator


# Export classes and functions
__all__ = [
    "AdvancedUserService",
    "UserServiceError",
    "UserNotFoundError",
    "UserAlreadyExistsError",
    "InvalidUserDataError",
    "UserPermissionError",
    "UserAccountLockedError",
    "UserValidationError",
    "UserAuthorizationError",
    "UserRateLimitError",
    "UserSessionError",
    "UserSearchRequest",
    "UserStatsResponse",
    "UserActivityResponse",
    "BulkUserOperation",
    "UserProfileUpdate",
    "UserOperationContext",
    "get_user_service",
    "require_user_permission",
    "validate_user_input",
]
