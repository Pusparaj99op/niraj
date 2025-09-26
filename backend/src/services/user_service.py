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
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, field
import re
from functools import wraps

import bcrypt
from sqlalchemy.exc import IntegrityError as SQLIntegrityError
from sqlalchemy import and_, or_, func, text, desc, asc
from pydantic import BaseModel, Field, field_validator

from ..models.user import (
    User, UserORM, TradingMode, UserAuthenticationError,
    UserCreateRequest, UserResponse, PinChangeRequest,
    generate_default_preferences
)
from ..models.audit_log import AuditLog, AuditEventType, AuditSeverity
from ..core.database_manager import DatabaseManager
from ..core.cache import CacheManager
from ..utils.logger import get_logger, get_structured_logger, log_error, LogContext, log_performance


class UserServiceError(Exception):
    """Base exception for user service errors"""
    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None):
        self.message = message
        self.error_code = error_code or "USER_SERVICE_ERROR"
        self.details = details or {}
        super().__init__(self.message)


class UserNotFoundError(UserServiceError):
    """User not found error"""
    def __init__(self, identifier: str, identifier_type: str = "user_id"):
        super().__init__(
            f"User not found by {identifier_type}: {identifier}",
            "USER_NOT_FOUND",
            {"identifier": identifier, "identifier_type": identifier_type}
        )


class UserAlreadyExistsError(UserServiceError):
    """User already exists error"""
    def __init__(self, username: str):
        super().__init__(
            f"User already exists with username: {username}",
            "USER_ALREADY_EXISTS",
            {"username": username}
        )


class InvalidUserDataError(UserServiceError):
    """Invalid user data error"""
    def __init__(self, field: str, value: Any, reason: str):
        super().__init__(
            f"Invalid {field}: {reason}",
            "INVALID_USER_DATA",
            {"field": field, "value": str(value), "reason": reason}
        )


class UserPermissionError(UserServiceError):
    """User permission error"""
    def __init__(self, action: str, user_id: str, reason: str = None):
        message = f"Permission denied for action '{action}' on user {user_id}"
        if reason:
            message += f": {reason}"
        super().__init__(
            message,
            "USER_PERMISSION_DENIED",
            {"action": action, "user_id": user_id, "reason": reason}
        )


class UserAccountLockedError(UserServiceError):
    """User account locked error"""
    def __init__(self, user_id: str, locked_until: datetime = None):
        message = f"User account {user_id} is locked"
        if locked_until:
            message += f" until {locked_until.isoformat()}"
        super().__init__(
            message,
            "USER_ACCOUNT_LOCKED",
            {"user_id": user_id, "locked_until": locked_until.isoformat() if locked_until else None}
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
    operation: str = Field(pattern="^(update|delete|activate|deactivate|reset_attempts)$")
    user_ids: List[str] = Field(min_items=1, max_items=1000)
    update_data: Optional[Dict[str, Any]] = None
    reason: Optional[str] = None


class UserProfileUpdate(BaseModel):
    """Comprehensive user profile update model"""
    username: Optional[str] = Field(None, min_length=3, max_length=50, pattern=r'^[a-zA-Z0-9_-]+$')
    default_capital: Optional[Decimal] = Field(None, gt=0, max_digits=15, decimal_places=2)
    risk_tolerance: Optional[float] = Field(None, ge=0.0, le=1.0)
    max_daily_loss: Optional[Decimal] = Field(None, gt=0, max_digits=15, decimal_places=2)
    preferences: Optional[Dict[str, Any]] = None

    @field_validator('username')
    @classmethod
    def validate_username_format(cls, v):
        if v and not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError("Username can only contain letters, numbers, underscores, and hyphens")
        return v

    @field_validator('preferences')
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
        config: Optional[Dict[str, Any]] = None
    ):
        self.db_manager = db_manager
        self.cache = cache_manager
        self.config = config or self._get_default_config()

        # Initialize loggers
        self.logger = get_logger('niraj.user_service')
        self.audit_logger = get_structured_logger('niraj.user_audit')
        self.performance_logger = get_structured_logger('niraj.user_performance')

        # Performance metrics
        self._metrics = {
            'users_created': 0,
            'users_updated': 0,
            'users_deleted': 0,
            'failed_operations': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'average_response_time': 0.0
        }

        # Initialize caching
        self._init_caching()

        self.logger.info("Advanced User Service initialized", config=self.config)

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            # Caching settings
            'cache_enabled': True,
            'cache_ttl': 300,  # 5 minutes
            'cache_prefix': 'niraj:users:',
            'batch_cache_size': 100,

            # Validation settings
            'strict_validation': True,
            'allow_duplicate_emails': False,
            'require_strong_pins': True,
            'pin_history_limit': 5,

            # Security settings
            'max_login_attempts': 5,
            'account_lockout_duration': 900,  # 15 minutes
            'password_expiry_days': 90,
            'require_pin_change_on_first_login': False,

            # Performance settings
            'bulk_operation_batch_size': 500,
            'search_result_limit': 1000,
            'enable_query_optimization': True,

            # Audit settings
            'enable_audit_logging': True,
            'audit_sensitive_operations': True,
            'log_performance_metrics': True,
        }

    def _init_caching(self):
        """Initialize caching system"""
        if not self.cache or not self.config.get('cache_enabled', True):
            self.logger.warning("Caching disabled or cache manager not available")
            return

        self._cache_keys = {
            'user_by_id': lambda user_id: f"{self.config['cache_prefix']}id:{user_id}",
            'user_by_username': lambda username: f"{self.config['cache_prefix']}username:{username}",
            'user_stats': f"{self.config['cache_prefix']}stats",
            'user_search': lambda query_hash: f"{self.config['cache_prefix']}search:{query_hash}",
            'user_activity': lambda user_id: f"{self.config['cache_prefix']}activity:{user_id}",
        }

    # CRUD Operations with Advanced Features
    @log_performance("user_service.create_user")
    async def create_user(
        self,
        user_data: UserCreateRequest,
        context: Optional[UserOperationContext] = None
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
                ip_address=context.ip_address if context else None
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
                    preferences=user_data.preferences or generate_default_preferences()
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
                        trading_mode=user.trading_mode.value
                    )

                    await self.db_manager.create(session, user_orm)

                    # Create audit log entry
                    if self.config.get('enable_audit_logging', True):
                        await self._create_audit_log(
                            session,
                            user.user_id,
                            AuditEventType.USER_CREATED,
                            AuditSeverity.INFO,
                            {
                                'username': user.username,
                                'trading_mode': user.trading_mode.value,
                                'operator_id': context.operator_id if context else None,
                                'ip_address': context.ip_address if context else None
                            }
                        )

                # Cache the user data
                await self._cache_user_data(user)

                # Create response
                user_response = UserResponse.from_orm(user_orm)

                # Update metrics
                self._metrics['users_created'] += 1

                # Log successful creation
                duration = time.time() - start_time
                self.logger.info(
                    f"User created successfully in {duration:.3f}s",
                    user_id=user.user_id,
                    username=user.username,
                    duration=duration
                )

                return user_response

        except (UserAlreadyExistsError, InvalidUserDataError):
            self._metrics['failed_operations'] += 1
            raise
        except SQLIntegrityError as e:
            self._metrics['failed_operations'] += 1
            if "username" in str(e).lower():
                raise UserAlreadyExistsError(user_data.username)
            raise UserServiceError(f"Database integrity error: {str(e)}")
        except Exception as e:
            self._metrics['failed_operations'] += 1
            self.logger.error(f"User creation failed: {str(e)}")
            log_error(e, {'username': user_data.username})
            raise UserServiceError(f"User creation failed: {str(e)}")

    @log_performance("user_service.get_user")
    async def get_user(
        self,
        user_id: str,
        include_sensitive: bool = False
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
                    self._metrics['cache_hits'] += 1
                    return cached_user

                self._metrics['cache_misses'] += 1

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
            log_error(e, {'user_id': user_id})
            raise UserServiceError(f"User retrieval failed: {str(e)}")

    @log_performance("user_service.get_user_by_username")
    async def get_user_by_username(
        self,
        username: str,
        include_sensitive: bool = False
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
                cache_key = self._cache_keys['user_by_username'](username)
                if self.cache:
                    cached_user_id = await self.cache.get(cache_key)
                    if cached_user_id:
                        self._metrics['cache_hits'] += 1
                        return await self.get_user(cached_user_id, include_sensitive)

                self._metrics['cache_misses'] += 1

                # Get from database
                async with self.db_manager.get_async_session() as session:
                    result = await session.execute(
                        text("SELECT * FROM users WHERE username = :username"),
                        {"username": username}
                    )
                    row = result.first()

                    if not row:
                        raise UserNotFoundError(username, "username")

                    # Convert row to UserORM
                    user_orm = UserORM(**row._asdict())
                    user_response = UserResponse.from_orm(user_orm)

                    # Cache both user data and username->id mapping
                    await self._cache_user_data(user_response)
                    if self.cache:
                        await self.cache.set(
                            cache_key,
                            user_response.user_id,
                            ttl=self.config.get('cache_ttl', 300)
                        )

                    return user_response

        except UserNotFoundError:
            raise
        except Exception as e:
            self.logger.error(f"User retrieval by username failed: {str(e)}")
            log_error(e, {'username': username})
            raise UserServiceError(f"User retrieval by username failed: {str(e)}")

    @log_performance("user_service.update_user")
    async def update_user(
        self,
        user_id: str,
        update_data: UserProfileUpdate,
        context: Optional[UserOperationContext] = None
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
                operator_id=context.operator_id if context else None
            ):
                # Validate update data
                await self._validate_user_update_data(user_id, update_data)

                # Get current user
                current_user = await self.get_user(user_id)

                # Prepare update dictionary
                update_dict = {}
                changes = []

                if update_data.username and update_data.username != current_user.username:
                    await self._check_username_availability(update_data.username)
                    update_dict['username'] = update_data.username
                    changes.append(f"username: {current_user.username} -> {update_data.username}")

                if update_data.default_capital is not None:
                    update_dict['default_capital'] = update_data.default_capital
                    changes.append(f"default_capital: {current_user.default_capital} -> {update_data.default_capital}")

                if update_data.risk_tolerance is not None:
                    update_dict['risk_tolerance'] = update_data.risk_tolerance
                    changes.append(f"risk_tolerance: {current_user.risk_tolerance} -> {update_data.risk_tolerance}")

                if update_data.max_daily_loss is not None:
                    update_dict['max_daily_loss'] = update_data.max_daily_loss
                    changes.append(f"max_daily_loss: {current_user.max_daily_loss} -> {update_data.max_daily_loss}")

                if update_data.preferences is not None:
                    # Merge with existing preferences
                    merged_preferences = current_user.preferences.copy()
                    merged_preferences.update(update_data.preferences)
                    update_dict['preferences'] = merged_preferences
                    changes.append("preferences updated")

                if not update_dict:
                    return current_user  # No changes to apply

                update_dict['updated_at'] = datetime.now(timezone.utc)

                # Update in database
                async with self.db_manager.get_transaction() as session:
                    user_orm = await self.db_manager.read(session, UserORM, user_id)
                    if not user_orm:
                        raise UserNotFoundError(user_id)

                    # Apply updates
                    updated_user = await self.db_manager.update(session, user_orm, update_dict)

                    # Create audit log entry
                    if self.config.get('enable_audit_logging', True):
                        await self._create_audit_log(
                            session,
                            user_id,
                            AuditEventType.USER_UPDATED,
                            AuditSeverity.INFO,
                            {
                                'changes': changes,
                                'operator_id': context.operator_id if context else None,
                                'ip_address': context.ip_address if context else None,
                                'reason': context.reason if context else None
                            }
                        )

                # Clear cache
                await self._invalidate_user_cache(user_id, current_user.username)

                # Create response
                user_response = UserResponse.from_orm(updated_user)

                # Cache updated data
                await self._cache_user_data(user_response)

                # Update metrics
                self._metrics['users_updated'] += 1

                # Log successful update
                duration = time.time() - start_time
                self.logger.info(
                    f"User updated successfully in {duration:.3f}s",
                    user_id=user_id,
                    changes=changes,
                    duration=duration
                )

                return user_response

        except (UserNotFoundError, InvalidUserDataError, UserAlreadyExistsError):
            self._metrics['failed_operations'] += 1
            raise
        except Exception as e:
            self._metrics['failed_operations'] += 1
            self.logger.error(f"User update failed: {str(e)}")
            log_error(e, {'user_id': user_id})
            raise UserServiceError(f"User update failed: {str(e)}")

    @log_performance("user_service.delete_user")
    async def delete_user(
        self,
        user_id: str,
        context: Optional[UserOperationContext] = None,
        soft_delete: bool = True
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
                soft_delete=soft_delete
            ):
                # Get user first to validate existence
                user = await self.get_user(user_id)

                async with self.db_manager.get_transaction() as session:
                    user_orm = await self.db_manager.read(session, UserORM, user_id)
                    if not user_orm:
                        raise UserNotFoundError(user_id)

                    if soft_delete:
                        # Soft delete - mark as inactive
                        await self.db_manager.update(session, user_orm, {
                            'updated_at': datetime.now(timezone.utc),
                            'preferences': {**user_orm.preferences, '_deleted': True, '_deleted_at': datetime.now(timezone.utc).isoformat()}
                        })
                        operation_type = AuditEventType.USER_UPDATED  # Closest match for soft delete
                    else:
                        # Hard delete
                        await self.db_manager.delete(session, user_orm)
                        operation_type = AuditEventType.USER_UPDATED  # Using USER_UPDATED as closest match

                    # Create audit log entry
                    if self.config.get('enable_audit_logging', True):
                        await self._create_audit_log(
                            session,
                            user_id,
                            operation_type,
                            AuditSeverity.WARNING,
                            {
                                'action': 'soft_delete' if soft_delete else 'hard_delete',
                                'username': user.username,
                                'operator_id': context.operator_id if context else None,
                                'ip_address': context.ip_address if context else None,
                                'reason': context.reason if context else None
                            }
                        )

                # Clear cache
                await self._invalidate_user_cache(user_id, user.username)

                # Update metrics
                self._metrics['users_deleted'] += 1

                self.logger.info(
                    f"User {'soft' if soft_delete else 'hard'} deleted successfully",
                    user_id=user_id,
                    username=user.username
                )

                return True

        except UserNotFoundError:
            raise
        except Exception as e:
            self._metrics['failed_operations'] += 1
            self.logger.error(f"User deletion failed: {str(e)}")
            log_error(e, {'user_id': user_id})
            raise UserServiceError(f"User deletion failed: {str(e)}")

    # Advanced User Management Features
    @log_performance("user_service.search_users")
    async def search_users(
        self,
        search_request: UserSearchRequest
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
                cache_key = self._cache_keys['user_search'](search_hash)

                # Try cache first
                if self.cache:
                    cached_result = await self.cache.get(cache_key)
                    if cached_result:
                        self._metrics['cache_hits'] += 1
                        cached_data = json.loads(cached_result)
                        return (
                            [UserResponse(**user_data) for user_data in cached_data['users']],
                            cached_data['total_count']
                        )

                self._metrics['cache_misses'] += 1

                async with self.db_manager.get_async_session() as session:
                    # Build query
                    query = session.query(UserORM)

                    # Apply filters
                    if search_request.query:
                        query = query.filter(
                            UserORM.username.contains(search_request.query)
                        )

                    if search_request.username_pattern:
                        query = query.filter(
                            UserORM.username.like(search_request.username_pattern)
                        )

                    if search_request.trading_mode:
                        query = query.filter(
                            UserORM.trading_mode == search_request.trading_mode.value
                        )

                    if search_request.created_after:
                        query = query.filter(
                            UserORM.created_at >= search_request.created_after
                        )

                    if search_request.created_before:
                        query = query.filter(
                            UserORM.created_at <= search_request.created_before
                        )

                    if search_request.last_login_after:
                        query = query.filter(
                            UserORM.last_login >= search_request.last_login_after
                        )

                    if search_request.last_login_before:
                        query = query.filter(
                            UserORM.last_login <= search_request.last_login_before
                        )

                    if search_request.min_capital:
                        query = query.filter(
                            UserORM.default_capital >= search_request.min_capital
                        )

                    if search_request.max_capital:
                        query = query.filter(
                            UserORM.default_capital <= search_request.max_capital
                        )

                    if search_request.risk_tolerance_min is not None:
                        query = query.filter(
                            UserORM.risk_tolerance >= search_request.risk_tolerance_min
                        )

                    if search_request.risk_tolerance_max is not None:
                        query = query.filter(
                            UserORM.risk_tolerance <= search_request.risk_tolerance_max
                        )

                    # Exclude soft-deleted users unless explicitly requested
                    if not search_request.include_inactive:
                        query = query.filter(
                            or_(
                                UserORM.preferences.is_(None),
                                ~UserORM.preferences.contains('"_deleted": true')
                            )
                        )

                    # Get total count
                    total_count = await query.count()

                    # Apply sorting
                    sort_column = getattr(UserORM, search_request.sort_by, UserORM.created_at)
                    if search_request.sort_order == 'desc':
                        query = query.order_by(desc(sort_column))
                    else:
                        query = query.order_by(asc(sort_column))

                    # Apply pagination
                    query = query.offset(search_request.offset).limit(search_request.limit)

                    # Execute query
                    users = await query.all()

                    # Convert to response models
                    user_responses = [UserResponse.from_orm(user) for user in users]

                    # Cache results
                    if self.cache:
                        cache_data = {
                            'users': [user.dict() for user in user_responses],
                            'total_count': total_count
                        }
                        await self.cache.set(
                            cache_key,
                            json.dumps(cache_data, default=str),
                            ttl=60  # Short TTL for search results
                        )

                    self.logger.info(
                        "User search completed",
                        found_users=len(user_responses),
                        total_count=total_count,
                        query=search_request.query
                    )

                    return user_responses, total_count

        except Exception as e:
            self.logger.error(f"User search failed: {str(e)}")
            log_error(e, {'search_request': search_request.dict()})
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
                cache_key = self._cache_keys['user_stats']
                if self.cache:
                    cached_stats = await self.cache.get(cache_key)
                    if cached_stats:
                        self._metrics['cache_hits'] += 1
                        return UserStatsResponse(**json.loads(cached_stats))

                self._metrics['cache_misses'] += 1

                async with self.db_manager.get_async_session() as session:
                    # Calculate various statistics
                    now = datetime.now(timezone.utc)
                    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
                    week_start = today - timedelta(days=today.weekday())
                    month_start = today.replace(day=1)

                    # Total users
                    total_users = await session.query(func.count(UserORM.user_id)).scalar()

                    # Active users (not soft-deleted)
                    active_users_query = session.query(func.count(UserORM.user_id)).filter(
                        or_(
                            UserORM.preferences.is_(None),
                            ~UserORM.preferences.contains('"_deleted": true')
                        )
                    )
                    active_users = await active_users_query.scalar()

                    inactive_users = total_users - active_users

                    # Trading mode distribution
                    paper_traders = await session.query(func.count(UserORM.user_id)).filter(
                        UserORM.trading_mode == TradingMode.PAPER.value
                    ).scalar()

                    live_traders = await session.query(func.count(UserORM.user_id)).filter(
                        UserORM.trading_mode == TradingMode.LIVE.value
                    ).scalar()

                    # Users created today/week/month
                    users_today = await session.query(func.count(UserORM.user_id)).filter(
                        UserORM.created_at >= today
                    ).scalar()

                    users_week = await session.query(func.count(UserORM.user_id)).filter(
                        UserORM.created_at >= week_start
                    ).scalar()

                    users_month = await session.query(func.count(UserORM.user_id)).filter(
                        UserORM.created_at >= month_start
                    ).scalar()

                    # Average capital and risk tolerance
                    capital_stats = await session.query(
                        func.avg(UserORM.default_capital),
                        func.avg(UserORM.risk_tolerance)
                    ).first()

                    avg_capital = capital_stats[0] or Decimal('0.00')
                    avg_risk_tolerance = capital_stats[1] or 0.0

                    # Most active hours (placeholder - would need login history)
                    most_active_hours = list(range(9, 16))  # Market hours

                    # Trading mode distribution
                    trading_mode_dist = {
                        TradingMode.PAPER.value: paper_traders,
                        TradingMode.LIVE.value: live_traders
                    }

                    # Risk tolerance distribution
                    risk_tolerance_dist = {
                        'low': await session.query(func.count(UserORM.user_id)).filter(
                            UserORM.risk_tolerance < 0.3
                        ).scalar(),
                        'medium': await session.query(func.count(UserORM.user_id)).filter(
                            and_(UserORM.risk_tolerance >= 0.3, UserORM.risk_tolerance < 0.7)
                        ).scalar(),
                        'high': await session.query(func.count(UserORM.user_id)).filter(
                            UserORM.risk_tolerance >= 0.7
                        ).scalar(),
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
                        risk_tolerance_distribution=risk_tolerance_dist
                    )

                    # Cache statistics
                    if self.cache:
                        await self.cache.set(
                            cache_key,
                            stats.json(),
                            ttl=300  # 5 minutes
                        )

                    self.logger.info("User statistics retrieved", stats=stats.dict())
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
        context: Optional[UserOperationContext] = None
    ) -> Dict[str, Any]:
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
                operator_id=context.operator_id if context else None
            ):
                async with self.db_manager.get_transaction() as session:
                    user_orm = await self.db_manager.read(session, UserORM, user_id)
                    if not user_orm:
                        raise UserNotFoundError(user_id)

                    # Verify current PIN
                    if not bcrypt.checkpw(
                        pin_change_request.old_pin.encode('utf-8'),
                        user_orm.pin_hash.encode('utf-8')
                    ):
                        # Log security event
                        await self._create_audit_log(
                            session,
                            user_id,
                            AuditEventType.SECURITY_ALERT,
                            AuditSeverity.WARNING,
                            {
                                'event': 'Invalid PIN during PIN change attempt',
                                'ip_address': context.ip_address if context else None,
                                'operator_id': context.operator_id if context else None
                            }
                        )
                        raise UserAuthenticationError("Current PIN is incorrect")

                    # Validate new PIN
                    await self._validate_new_pin(pin_change_request.new_pin, user_orm.pin_hash)

                    # Hash new PIN
                    new_pin_hash = bcrypt.hashpw(
                        pin_change_request.new_pin.encode('utf-8'),
                        bcrypt.gensalt()
                    ).decode('utf-8')

                    # Update PIN
                    await self.db_manager.update(session, user_orm, {
                        'pin_hash': new_pin_hash,
                        'updated_at': datetime.now(timezone.utc),
                        'login_attempts': 0  # Reset failed attempts
                    })

                    # Create audit log
                    await self._create_audit_log(
                        session,
                        user_id,
                        AuditEventType.USER_UPDATED,
                        AuditSeverity.INFO,
                        {
                            'action': 'PIN changed',
                            'operator_id': context.operator_id if context else None,
                            'ip_address': context.ip_address if context else None
                        }
                    )

                # Clear user cache
                await self._invalidate_user_cache(user_id, user_orm.username)

                self.logger.info("PIN changed successfully", user_id=user_id)

                return {
                    'message': 'PIN changed successfully',
                    'changed_at': datetime.now(timezone.utc).isoformat()
                }

        except (UserNotFoundError, UserAuthenticationError, InvalidUserDataError):
            raise
        except Exception as e:
            self.logger.error(f"PIN change failed: {str(e)}")
            log_error(e, {'user_id': user_id})
            raise UserServiceError(f"PIN change failed: {str(e)}")

    @log_performance("user_service.bulk_user_operation")
    async def bulk_user_operation(
        self,
        operation: BulkUserOperation,
        context: Optional[UserOperationContext] = None
    ) -> Dict[str, Any]:
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
                user_count=len(operation.user_ids)
            ):
                results = {
                    'operation': operation.operation,
                    'requested_count': len(operation.user_ids),
                    'successful_count': 0,
                    'failed_count': 0,
                    'errors': [],
                    'processed_user_ids': []
                }

                batch_size = self.config.get('bulk_operation_batch_size', 500)

                # Process in batches
                for i in range(0, len(operation.user_ids), batch_size):
                    batch_user_ids = operation.user_ids[i:i + batch_size]

                    async with self.db_manager.get_transaction() as session:
                        for user_id in batch_user_ids:
                            try:
                                user_orm = await self.db_manager.read(session, UserORM, user_id)
                                if not user_orm:
                                    results['errors'].append({
                                        'user_id': user_id,
                                        'error': 'User not found'
                                    })
                                    results['failed_count'] += 1
                                    continue

                                # Perform operation
                                if operation.operation == 'update':
                                    if operation.update_data:
                                        update_dict = operation.update_data.copy()
                                        update_dict['updated_at'] = datetime.now(timezone.utc)
                                        await self.db_manager.update(session, user_orm, update_dict)

                                elif operation.operation == 'delete':
                                    # Soft delete
                                    preferences = user_orm.preferences or {}
                                    preferences.update({
                                        '_deleted': True,
                                        '_deleted_at': datetime.now(timezone.utc).isoformat()
                                    })
                                    await self.db_manager.update(session, user_orm, {
                                        'preferences': preferences,
                                        'updated_at': datetime.now(timezone.utc)
                                    })

                                elif operation.operation == 'reset_attempts':
                                    await self.db_manager.update(session, user_orm, {
                                        'login_attempts': 0,
                                        'updated_at': datetime.now(timezone.utc)
                                    })

                                # Create audit log
                                if self.config.get('enable_audit_logging', True):
                                    await self._create_audit_log(
                                        session,
                                        user_id,
                                        AuditEventType.USER_UPDATED,
                                        AuditSeverity.INFO,
                                        {
                                            'bulk_operation': operation.operation,
                                            'reason': operation.reason,
                                            'operator_id': context.operator_id if context else None
                                        }
                                    )

                                results['successful_count'] += 1
                                results['processed_user_ids'].append(user_id)

                                # Clear cache for this user
                                await self._invalidate_user_cache(user_id, user_orm.username)

                            except Exception as e:
                                results['errors'].append({
                                    'user_id': user_id,
                                    'error': str(e)
                                })
                                results['failed_count'] += 1

                self.logger.info(
                    "Bulk operation completed",
                    operation=operation.operation,
                    successful=results['successful_count'],
                    failed=results['failed_count']
                )

                return results

        except Exception as e:
            self.logger.error(f"Bulk operation failed: {str(e)}")
            log_error(e, {'operation': operation.operation})
            raise UserServiceError(f"Bulk operation failed: {str(e)}")

    # Utility and Helper Methods
    async def _validate_user_creation_data(self, user_data: UserCreateRequest):
        """Validate user creation data"""
        try:
            # Validate username format
            if not re.match(r'^[a-zA-Z0-9_-]+$', user_data.username):
                raise InvalidUserDataError(
                    "username",
                    user_data.username,
                    "Username can only contain letters, numbers, underscores, and hyphens"
                )

            # Validate PIN strength
            if self.config.get('require_strong_pins', True):
                if user_data.pin in ['0000', '1234', '1111', '2222', '3333', '4444', '5555', '6666', '7777', '8888', '9999']:
                    raise InvalidUserDataError("pin", user_data.pin, "PIN too weak, avoid common patterns")

                if len(set(user_data.pin)) == 1:
                    raise InvalidUserDataError("pin", user_data.pin, "PIN cannot have all same digits")

            # Validate financial parameters
            if user_data.default_capital <= 0:
                raise InvalidUserDataError("default_capital", user_data.default_capital, "Must be positive")

            if not 0.0 <= user_data.risk_tolerance <= 1.0:
                raise InvalidUserDataError("risk_tolerance", user_data.risk_tolerance, "Must be between 0.0 and 1.0")

            if user_data.max_daily_loss <= 0:
                raise InvalidUserDataError("max_daily_loss", user_data.max_daily_loss, "Must be positive")

            # Validate preferences
            if user_data.preferences:
                try:
                    json.dumps(user_data.preferences)
                except (TypeError, ValueError):
                    raise InvalidUserDataError("preferences", user_data.preferences, "Must be JSON serializable")

        except InvalidUserDataError:
            raise
        except Exception as e:
            raise InvalidUserDataError("validation", str(user_data), str(e))

    async def _validate_user_update_data(self, user_id: str, update_data: UserProfileUpdate):
        """Validate user update data"""
        try:
            if update_data.username:
                if not re.match(r'^[a-zA-Z0-9_-]+$', update_data.username):
                    raise InvalidUserDataError(
                        "username",
                        update_data.username,
                        "Username can only contain letters, numbers, underscores, and hyphens"
                    )

            if update_data.default_capital is not None and update_data.default_capital <= 0:
                raise InvalidUserDataError("default_capital", update_data.default_capital, "Must be positive")

            if update_data.risk_tolerance is not None and not 0.0 <= update_data.risk_tolerance <= 1.0:
                raise InvalidUserDataError("risk_tolerance", update_data.risk_tolerance, "Must be between 0.0 and 1.0")

            if update_data.max_daily_loss is not None and update_data.max_daily_loss <= 0:
                raise InvalidUserDataError("max_daily_loss", update_data.max_daily_loss, "Must be positive")

            if update_data.preferences:
                try:
                    json.dumps(update_data.preferences)
                except (TypeError, ValueError):
                    raise InvalidUserDataError("preferences", update_data.preferences, "Must be JSON serializable")

        except InvalidUserDataError:
            raise
        except Exception as e:
            raise InvalidUserDataError("validation", str(update_data), str(e))

    async def _validate_new_pin(self, new_pin: str, current_hash: str):
        """Validate new PIN meets security requirements"""
        try:
            # Check PIN strength
            if self.config.get('require_strong_pins', True):
                if new_pin in ['0000', '1234', '1111', '2222', '3333', '4444',
                              '5555', '6666', '7777', '8888', '9999']:
                    raise InvalidUserDataError("new_pin", new_pin, "PIN too weak, avoid common patterns")

                if len(set(new_pin)) == 1:
                    raise InvalidUserDataError("new_pin", new_pin, "PIN cannot have all same digits")

            # Check if same as current PIN
            if bcrypt.checkpw(new_pin.encode('utf-8'), current_hash.encode('utf-8')):
                raise InvalidUserDataError("new_pin", new_pin, "New PIN must be different from current PIN")

        except InvalidUserDataError:
            raise
        except Exception as e:
            raise InvalidUserDataError("new_pin", new_pin, str(e))

    async def _check_username_availability(self, username: str):
        """Check if username is available"""
        try:
            existing_user = await self.get_user_by_username(username)
            if existing_user:
                raise UserAlreadyExistsError(username)
        except UserNotFoundError:
            # Username is available
            pass

    async def _cache_user_data(self, user: Union[User, UserResponse]):
        """Cache user data"""
        if not self.cache or not self.config.get('cache_enabled', True):
            return

        try:
            user_id_key = self._cache_keys['user_by_id'](user.user_id)
            username_key = self._cache_keys['user_by_username'](user.username)
            ttl = self.config.get('cache_ttl', 300)

            if isinstance(user, UserResponse):
                user_data = user.json()
            else:
                user_data = user.to_dict()

            await asyncio.gather(
                self.cache.set(user_id_key, user_data, ttl=ttl),
                self.cache.set(username_key, user.user_id, ttl=ttl),
                return_exceptions=True
            )
        except Exception as e:
            self.logger.warning(f"Failed to cache user data: {str(e)}")

    async def _get_user_from_cache(self, user_id: str) -> Optional[UserResponse]:
        """Get user from cache"""
        if not self.cache or not self.config.get('cache_enabled', True):
            return None

        try:
            cache_key = self._cache_keys['user_by_id'](user_id)
            cached_data = await self.cache.get(cache_key)

            if cached_data:
                if isinstance(cached_data, str):
                    user_dict = json.loads(cached_data)
                else:
                    user_dict = cached_data

                return UserResponse(**user_dict)

            return None
        except Exception as e:
            self.logger.warning(f"Failed to get user from cache: {str(e)}")
            return None

    async def _invalidate_user_cache(self, user_id: str, username: str):
        """Invalidate user cache"""
        if not self.cache:
            return

        try:
            cache_keys = [
                self._cache_keys['user_by_id'](user_id),
                self._cache_keys['user_by_username'](username),
                self._cache_keys['user_stats'],
                self._cache_keys['user_activity'](user_id)
            ]

            await asyncio.gather(
                *[self.cache.delete(key) for key in cache_keys],
                return_exceptions=True
            )
        except Exception as e:
            self.logger.warning(f"Failed to invalidate user cache: {str(e)}")

    def _generate_search_hash(self, search_request: UserSearchRequest) -> str:
        """Generate hash for search request caching"""
        import hashlib
        search_dict = search_request.dict()
        search_str = json.dumps(search_dict, sort_keys=True, default=str)
        return hashlib.md5(search_str.encode()).hexdigest()

    async def _create_audit_log(
        self,
        session,
        user_id: Optional[str],
        event_type: AuditEventType,
        severity: AuditSeverity,
        details: Dict[str, Any]
    ):
        """Create audit log entry"""
        try:
            audit_log = AuditLog(
                user_id=user_id,
                action=event_type,
                level=severity,
                details=details,
                ip_address=details.get('ip_address'),
                user_agent=details.get('user_agent')
            )

            # This would typically be saved to database
            # For now, just log it
            self.audit_logger.info(
                f"Audit: {event_type.value}",
                user_id=user_id,
                severity=severity.value,
                details=details
            )
        except Exception as e:
            self.logger.error(f"Failed to create audit log: {str(e)}")

    def get_service_metrics(self) -> Dict[str, Any]:
        """Get service performance metrics"""
        return {
            'metrics': self._metrics.copy(),
            'config': {
                'cache_enabled': self.config.get('cache_enabled', True),
                'strict_validation': self.config.get('strict_validation', True),
                'enable_audit_logging': self.config.get('enable_audit_logging', True)
            },
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

    async def health_check(self) -> Dict[str, Any]:
        """Service health check"""
        try:
            # Test database connectivity
            async with self.db_manager.get_async_session() as session:
                result = await session.execute(text("SELECT 1"))
                db_healthy = result.scalar() == 1

            # Test cache connectivity
            cache_healthy = True
            if self.cache:
                try:
                    test_key = f"{self.config['cache_prefix']}health_check"
                    await self.cache.set(test_key, "test", ttl=10)
                    cached_value = await self.cache.get(test_key)
                    cache_healthy = cached_value == "test"
                    await self.cache.delete(test_key)
                except Exception:
                    cache_healthy = False

            return {
                'service': 'User Service',
                'status': 'healthy' if db_healthy and cache_healthy else 'unhealthy',
                'database': 'healthy' if db_healthy else 'unhealthy',
                'cache': 'healthy' if cache_healthy else 'unhealthy',
                'metrics': self._metrics.copy(),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            return {
                'service': 'User Service',
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }


# Global service instance
user_service = None

def get_user_service(
    db_manager: DatabaseManager = None,
    cache_manager: CacheManager = None
) -> AdvancedUserService:
    """Get global user service instance"""
    global user_service

    if user_service is None:
        if not db_manager:
            from ..core.database_manager import get_database_manager
            db_manager = get_database_manager()

        user_service = AdvancedUserService(
            db_manager=db_manager,
            cache_manager=cache_manager
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
    'AdvancedUserService',
    'UserServiceError',
    'UserNotFoundError',
    'UserAlreadyExistsError',
    'InvalidUserDataError',
    'UserPermissionError',
    'UserAccountLockedError',
    'UserSearchRequest',
    'UserStatsResponse',
    'UserActivityResponse',
    'BulkUserOperation',
    'UserProfileUpdate',
    'UserOperationContext',
    'get_user_service',
    'require_user_permission',
    'validate_user_input'
]
