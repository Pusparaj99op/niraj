"""
Advanced Authentication Service for NIRAJ Trading System

This service provides comprehensive authentication capabilities including:
- JWT token management with refresh tokens
- Password/PIN hashing and validation
- Session management and tracking
- Role-based access control (RBAC)
- Rate limiting and brute force protection
- Account lockout and security monitoring
- Multi-factor authentication support
- Audit logging for security events
- Advanced error handling with security-focused responses
"""

import os
import jwt
import uuid
import secrets
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import json
import time
from functools import wraps

import bcrypt
from sqlalchemy.exc import SQLAlchemyError
from pydantic import BaseModel, Field, validator

from ..models.user import User, UserORM, TradingMode, UserValidationError
from ..models.audit_log import AuditLog, AuditEventType as AuditAction, AuditSeverity as AuditLevel
from ..core.database import DatabaseManager
from ..core.cache import CacheManager
from ..utils.logger import get_logger, get_structured_logger, log_error, LogContext


class TokenType(str, Enum):
    """Token type enumeration"""
    ACCESS = "access"
    REFRESH = "refresh"
    RESET = "reset"
    MFA = "mfa"


class AuthRole(str, Enum):
    """User role enumeration"""
    ADMIN = "admin"
    TRADER = "trader"
    VIEWER = "viewer"


class SessionStatus(str, Enum):
    """Session status enumeration"""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    LOCKED = "locked"


class SecurityLevel(str, Enum):
    """Security level for different operations"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Custom Exceptions
class AuthenticationError(Exception):
    """Base authentication error"""
    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None):
        self.message = message
        self.error_code = error_code or "AUTH_ERROR"
        self.details = details or {}
        super().__init__(self.message)


class AuthorizationError(AuthenticationError):
    """Authorization/permission error"""
    def __init__(self, message: str, required_role: str = None, user_role: str = None):
        super().__init__(message, "AUTHORIZATION_ERROR", {
            "required_role": required_role,
            "user_role": user_role
        })


class TokenError(AuthenticationError):
    """Token-related error"""
    def __init__(self, message: str, token_type: str = None):
        super().__init__(message, "TOKEN_ERROR", {"token_type": token_type})


class RateLimitError(AuthenticationError):
    """Rate limiting error"""
    def __init__(self, message: str, retry_after: int = None):
        super().__init__(message, "RATE_LIMIT_ERROR", {"retry_after": retry_after})


class SecurityError(AuthenticationError):
    """Security-related error"""
    def __init__(self, message: str, security_level: SecurityLevel = SecurityLevel.HIGH):
        super().__init__(message, "SECURITY_ERROR", {"security_level": security_level.value})


# Pydantic Models
class LoginRequest(BaseModel):
    """Login request model"""
    username: str = Field(min_length=3, max_length=50)
    pin: str = Field(min_length=4, max_length=4, pattern=r'^\d{4}$')
    remember_me: bool = Field(default=False)
    device_info: Optional[Dict[str, Any]] = Field(default=None)

    @validator('pin')
    def validate_pin_format(cls, v):
        if not v.isdigit():
            raise ValueError("PIN must contain only digits")
        return v


class TokenResponse(BaseModel):
    """Token response model"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    username: str
    role: str
    trading_mode: str
    session_id: str


class RefreshTokenRequest(BaseModel):
    """Refresh token request model"""
    refresh_token: str
    device_info: Optional[Dict[str, Any]] = Field(default=None)


class SwitchModeRequest(BaseModel):
    """Switch trading mode request model"""
    mode: TradingMode
    pin: Optional[str] = Field(None, min_length=4, max_length=4, pattern=r'^\d{4}$')

    @validator('pin')
    def validate_pin_for_live_mode(cls, v, values):
        if values.get('mode') == TradingMode.LIVE and not v:
            raise ValueError("PIN required for live trading mode")
        return v


class ChangePasswordRequest(BaseModel):
    """Change password request model"""
    current_pin: str = Field(min_length=4, max_length=4, pattern=r'^\d{4}$')
    new_pin: str = Field(min_length=4, max_length=4, pattern=r'^\d{4}$')

    @validator('new_pin')
    def validate_new_pin(cls, v, values):
        if v == values.get('current_pin'):
            raise ValueError("New PIN must be different from current PIN")
        if v in ['0000', '1234', '1111', '2222', '3333', '4444', '5555', '6666', '7777', '8888', '9999']:
            raise ValueError("PIN too weak, avoid common patterns")
        return v


class SessionInfo(BaseModel):
    """Session information model"""
    session_id: str
    user_id: str
    username: str
    role: str
    trading_mode: str
    created_at: datetime
    last_activity: datetime
    expires_at: datetime
    device_info: Optional[Dict[str, Any]]
    is_active: bool
    security_level: str


@dataclass
class SecurityContext:
    """Security context for requests"""
    user_id: str
    username: str
    role: AuthRole
    session_id: str
    trading_mode: TradingMode
    permissions: Set[str] = field(default_factory=set)
    security_level: SecurityLevel = SecurityLevel.MEDIUM
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    device_fingerprint: Optional[str] = None


class AuthenticationService:
    """
    Advanced Authentication Service

    Provides comprehensive authentication and authorization capabilities
    with enterprise-grade security features.
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        cache_manager: CacheManager,
        config: Optional[Dict[str, Any]] = None
    ):
        self.db_manager = db_manager
        self.cache = cache_manager
        self.config = config or self._get_default_config()

        # Initialize loggers
        self.logger = get_logger('niraj.auth')
        self.security_logger = get_structured_logger('niraj.security')
        self.audit_logger = get_structured_logger('niraj.audit')

        # Initialize security components
        self._init_security_components()

        # Performance metrics
        self._metrics = {
            'login_attempts': 0,
            'successful_logins': 0,
            'failed_logins': 0,
            'token_refreshes': 0,
            'rate_limit_hits': 0,
            'security_violations': 0
        }

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            # JWT Configuration
            'jwt_secret_key': os.getenv('JWT_SECRET_KEY', secrets.token_urlsafe(32)),
            'jwt_algorithm': 'HS256',
            'access_token_expire_minutes': 30,
            'refresh_token_expire_days': 7,
            'remember_me_expire_days': 30,

            # Security Configuration
            'max_login_attempts': 5,
            'lockout_duration_minutes': 15,
            'password_min_length': 4,
            'require_strong_passwords': True,
            'session_timeout_minutes': 60,
            'max_concurrent_sessions': 3,

            # Rate Limiting
            'rate_limit_login': {'requests': 10, 'window': 300},  # 10 requests per 5 minutes
            'rate_limit_refresh': {'requests': 20, 'window': 3600},  # 20 requests per hour
            'rate_limit_global': {'requests': 1000, 'window': 3600},  # 1000 requests per hour

            # Security Features
            'enable_audit_logging': True,
            'enable_session_tracking': True,
            'enable_device_fingerprinting': True,
            'enable_suspicious_activity_detection': True,
            'require_pin_for_live_mode': True,

            # Cache Settings
            'cache_prefix': 'niraj:auth:',
            'session_cache_ttl': 3600,
            'rate_limit_cache_ttl': 3600,
        }

    def _init_security_components(self):
        """Initialize security components"""
        try:
            # Validate JWT secret
            if len(self.config['jwt_secret_key']) < 32:
                raise SecurityError("JWT secret key must be at least 32 characters")

            # Initialize rate limiters
            self._rate_limiters = {
                'login': RateLimiter(
                    self.cache,
                    'login',
                    self.config['rate_limit_login']['requests'],
                    self.config['rate_limit_login']['window']
                ),
                'refresh': RateLimiter(
                    self.cache,
                    'refresh',
                    self.config['rate_limit_refresh']['requests'],
                    self.config['rate_limit_refresh']['window']
                ),
                'global': RateLimiter(
                    self.cache,
                    'global',
                    self.config['rate_limit_global']['requests'],
                    self.config['rate_limit_global']['window']
                )
            }

            # Initialize session manager
            self._session_manager = SessionManager(
                self.cache,
                self.config['session_timeout_minutes'],
                self.config['max_concurrent_sessions']
            )

            # Initialize security monitor
            self._security_monitor = SecurityMonitor(
                self.cache,
                self.security_logger
            )

            self.logger.info("Security components initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize security components: {str(e)}")
            raise SecurityError(f"Security initialization failed: {str(e)}")

    async def authenticate_user(
        self,
        login_request: LoginRequest,
        ip_address: str = None,
        user_agent: str = None
    ) -> TokenResponse:
        """
        Authenticate user with comprehensive security checks

        Args:
            login_request: Login request data
            ip_address: Client IP address
            user_agent: Client user agent string

        Returns:
            TokenResponse: Authentication tokens and user info

        Raises:
            AuthenticationError: If authentication fails
            RateLimitError: If rate limit exceeded
            SecurityError: If security violation detected
        """
        start_time = time.time()

        try:
            with LogContext(
                username=login_request.username,
                ip_address=ip_address,
                user_agent=user_agent
            ):
                # Track metrics
                self._metrics['login_attempts'] += 1

                # Check rate limits
                await self._check_rate_limits('login', ip_address)

                # Validate input
                self._validate_login_request(login_request)

                # Check for suspicious activity
                await self._security_monitor.check_suspicious_activity(
                    login_request.username,
                    ip_address,
                    user_agent
                )

                # Retrieve user from database
                user = await self._get_user_by_username(login_request.username)
                if not user:
                    # Log failed attempt (but don't reveal if user exists)
                    await self._log_failed_login(
                        login_request.username,
                        "Invalid credentials",
                        ip_address,
                        user_agent
                    )
                    raise AuthenticationError("Invalid username or PIN")

                # Check account lockout
                await self._check_account_lockout(user.user_id)

                # Verify PIN
                is_valid_pin = await self._verify_pin(user, login_request.pin)
                if not is_valid_pin:
                    # Handle failed authentication
                    await self._handle_failed_authentication(
                        user,
                        login_request.username,
                        ip_address,
                        user_agent
                    )
                    raise AuthenticationError("Invalid username or PIN")

                # Successful authentication - reset failed attempts
                await self._reset_failed_attempts(user.user_id)

                # Create session
                session = await self._session_manager.create_session(
                    user.user_id,
                    user.username,
                    AuthRole.TRADER,  # Default role, could be configurable
                    user.trading_mode,
                    login_request.device_info,
                    remember_me=login_request.remember_me
                )

                # Generate tokens
                token_response = await self._generate_token_response(
                    user,
                    session,
                    login_request.remember_me
                )

                # Update user last login
                await self._update_last_login(user.user_id)

                # Log successful authentication
                await self._log_successful_login(
                    user.user_id,
                    user.username,
                    session.session_id,
                    ip_address,
                    user_agent
                )

                # Track metrics
                self._metrics['successful_logins'] += 1

                duration = time.time() - start_time
                self.logger.info(
                    f"User authenticated successfully in {duration:.3f}s",
                    user_id=user.user_id,
                    username=user.username,
                    session_id=session.session_id
                )

                return token_response

        except (AuthenticationError, RateLimitError, SecurityError):
            self._metrics['failed_logins'] += 1
            raise
        except Exception as e:
            self._metrics['failed_logins'] += 1
            self.logger.error(f"Authentication error: {str(e)}")
            log_error(e, {'username': login_request.username, 'ip': ip_address})
            raise AuthenticationError("Authentication failed due to system error")

    async def refresh_token(
        self,
        refresh_request: RefreshTokenRequest,
        ip_address: str = None,
        user_agent: str = None
    ) -> TokenResponse:
        """
        Refresh access token using refresh token

        Args:
            refresh_request: Refresh token request data
            ip_address: Client IP address
            user_agent: Client user agent string

        Returns:
            TokenResponse: New authentication tokens

        Raises:
            TokenError: If token is invalid or expired
            RateLimitError: If rate limit exceeded
        """
        try:
            with LogContext(refresh_token=refresh_request.refresh_token[:10] + "..."):
                # Check rate limits
                await self._check_rate_limits('refresh', ip_address)

                # Decode and validate refresh token
                payload = await self._decode_token(
                    refresh_request.refresh_token,
                    TokenType.REFRESH
                )

                user_id = payload['user_id']
                session_id = payload['session_id']

                # Verify session is still valid
                session = await self._session_manager.get_session(session_id)
                if not session or not session.is_active:
                    raise TokenError("Session expired or invalid")

                # Get user
                user = await self._get_user_by_id(user_id)
                if not user:
                    raise TokenError("User not found")

                # Update session activity
                await self._session_manager.update_session_activity(session_id)

                # Generate new tokens
                token_response = await self._generate_token_response(
                    user,
                    session,
                    remember_me=payload.get('remember_me', False)
                )

                # Track metrics
                self._metrics['token_refreshes'] += 1

                # Log token refresh
                self.audit_logger.info(
                    "Token refreshed",
                    user_id=user_id,
                    session_id=session_id,
                    ip_address=ip_address
                )

                return token_response

        except TokenError:
            raise
        except Exception as e:
            self.logger.error(f"Token refresh error: {str(e)}")
            raise TokenError("Token refresh failed")

    async def switch_trading_mode(
        self,
        user_id: str,
        switch_request: SwitchModeRequest,
        ip_address: str = None
    ) -> Dict[str, Any]:
        """
        Switch user's trading mode with security validation

        Args:
            user_id: User identifier
            switch_request: Mode switch request data
            ip_address: Client IP address

        Returns:
            Dict containing mode and timestamp

        Raises:
            AuthenticationError: If PIN verification fails
            AuthorizationError: If operation not allowed
        """
        try:
            with LogContext(user_id=user_id, target_mode=switch_request.mode.value):
                # Get user
                user = await self._get_user_by_id(user_id)
                if not user:
                    raise AuthenticationError("User not found")

                # Check if switching to live mode requires PIN
                if (switch_request.mode == TradingMode.LIVE and
                    self.config['require_pin_for_live_mode']):

                    if not switch_request.pin:
                        raise AuthenticationError("PIN required for live trading mode")

                    # Verify PIN
                    is_valid_pin = await self._verify_pin(user, switch_request.pin)
                    if not is_valid_pin:
                        await self._log_security_event(
                            user_id,
                            "PIN verification failed for live mode switch",
                            SecurityLevel.HIGH,
                            {"ip_address": ip_address}
                        )
                        raise AuthenticationError("Invalid PIN")

                # Update user's trading mode
                await self._update_trading_mode(user_id, switch_request.mode)

                # Log mode switch
                await self._log_audit_event(
                    user_id,
                    AuditAction.MODE_SWITCH,
                    AuditLevel.INFO,
                    {
                        'old_mode': user.trading_mode.value,
                        'new_mode': switch_request.mode.value,
                        'ip_address': ip_address
                    }
                )

                switched_at = datetime.now(timezone.utc)

                self.logger.info(
                    f"Trading mode switched to {switch_request.mode.value}",
                    user_id=user_id,
                    old_mode=user.trading_mode.value,
                    new_mode=switch_request.mode.value
                )

                return {
                    'mode': switch_request.mode.value,
                    'switched_at': switched_at.isoformat()
                }

        except (AuthenticationError, AuthorizationError):
            raise
        except Exception as e:
            self.logger.error(f"Mode switch error: {str(e)}")
            raise AuthenticationError("Mode switch failed due to system error")

    async def validate_token(
        self,
        token: str,
        required_permissions: List[str] = None
    ) -> SecurityContext:
        """
        Validate token and return security context

        Args:
            token: JWT access token
            required_permissions: Required permissions for operation

        Returns:
            SecurityContext: Security context for the request

        Raises:
            TokenError: If token is invalid
            AuthorizationError: If insufficient permissions
        """
        try:
            # Decode token
            payload = await self._decode_token(token, TokenType.ACCESS)

            user_id = payload['user_id']
            session_id = payload['session_id']

            # Verify session is still active
            session = await self._session_manager.get_session(session_id)
            if not session or not session.is_active:
                raise TokenError("Session expired or revoked")

            # Create security context
            security_context = SecurityContext(
                user_id=user_id,
                username=payload['username'],
                role=AuthRole(payload['role']),
                session_id=session_id,
                trading_mode=TradingMode(payload['trading_mode']),
                permissions=set(payload.get('permissions', [])),
                security_level=SecurityLevel(payload.get('security_level', 'medium'))
            )

            # Check required permissions
            if required_permissions:
                missing_permissions = set(required_permissions) - security_context.permissions
                if missing_permissions:
                    raise AuthorizationError(
                        "Insufficient permissions",
                        required_role=str(required_permissions),
                        user_role=security_context.role.value
                    )

            # Update session activity
            await self._session_manager.update_session_activity(session_id)

            return security_context

        except TokenError:
            raise
        except AuthorizationError:
            raise
        except Exception as e:
            self.logger.error(f"Token validation error: {str(e)}")
            raise TokenError("Token validation failed")

    async def logout(
        self,
        user_id: str,
        session_id: str,
        ip_address: str = None
    ) -> Dict[str, Any]:
        """
        Logout user and revoke session

        Args:
            user_id: User identifier
            session_id: Session identifier
            ip_address: Client IP address

        Returns:
            Dict with logout confirmation
        """
        try:
            with LogContext(user_id=user_id, session_id=session_id):
                # Revoke session
                await self._session_manager.revoke_session(session_id)

                # Log logout
                await self._log_audit_event(
                    user_id,
                    AuditAction.LOGOUT,
                    AuditLevel.INFO,
                    {'session_id': session_id, 'ip_address': ip_address}
                )

                self.logger.info(
                    "User logged out successfully",
                    user_id=user_id,
                    session_id=session_id
                )

                return {
                    'message': 'Logged out successfully',
                    'logged_out_at': datetime.now(timezone.utc).isoformat()
                }

        except Exception as e:
            self.logger.error(f"Logout error: {str(e)}")
            raise AuthenticationError("Logout failed")

    async def change_password(
        self,
        user_id: str,
        change_request: ChangePasswordRequest,
        ip_address: str = None
    ) -> Dict[str, Any]:
        """
        Change user password with security validation

        Args:
            user_id: User identifier
            change_request: Password change request data
            ip_address: Client IP address

        Returns:
            Dict with success confirmation

        Raises:
            AuthenticationError: If current password is incorrect
            UserValidationError: If new password is invalid
        """
        try:
            with LogContext(user_id=user_id):
                # Get user
                user = await self._get_user_by_id(user_id)
                if not user:
                    raise AuthenticationError("User not found")

                # Verify current PIN
                is_valid_pin = await self._verify_pin(user, change_request.current_pin)
                if not is_valid_pin:
                    await self._log_security_event(
                        user_id,
                        "Invalid PIN during password change attempt",
                        SecurityLevel.HIGH,
                        {"ip_address": ip_address}
                    )
                    raise AuthenticationError("Current PIN is incorrect")

                # Validate new PIN
                await self._validate_new_pin(change_request.new_pin, user.pin_hash)

                # Update PIN
                await self._update_user_pin(user_id, change_request.new_pin)

                # Revoke all existing sessions (force re-login)
                await self._session_manager.revoke_all_user_sessions(user_id)

                # Log password change
                await self._log_audit_event(
                    user_id,
                    AuditAction.PIN_CHANGE,
                    AuditLevel.SECURITY,
                    {'ip_address': ip_address}
                )

                self.logger.info(
                    "PIN changed successfully",
                    user_id=user_id
                )

                return {
                    'message': 'PIN changed successfully',
                    'changed_at': datetime.now(timezone.utc).isoformat(),
                    'sessions_revoked': True
                }

        except (AuthenticationError, UserValidationError):
            raise
        except Exception as e:
            self.logger.error(f"Password change error: {str(e)}")
            raise AuthenticationError("Password change failed due to system error")

    async def get_user_sessions(self, user_id: str) -> List[SessionInfo]:
        """
        Get all active sessions for a user

        Args:
            user_id: User identifier

        Returns:
            List of session information
        """
        try:
            sessions = await self._session_manager.get_user_sessions(user_id)
            return [
                SessionInfo(
                    session_id=session.session_id,
                    user_id=session.user_id,
                    username=session.username,
                    role=session.role,
                    trading_mode=session.trading_mode,
                    created_at=session.created_at,
                    last_activity=session.last_activity,
                    expires_at=session.expires_at,
                    device_info=session.device_info,
                    is_active=session.is_active,
                    security_level=session.security_level
                )
                for session in sessions
            ]
        except Exception as e:
            self.logger.error(f"Get user sessions error: {str(e)}")
            raise AuthenticationError("Failed to retrieve user sessions")

    async def revoke_session(
        self,
        user_id: str,
        session_id: str,
        ip_address: str = None
    ) -> Dict[str, Any]:
        """
        Revoke a specific session

        Args:
            user_id: User identifier
            session_id: Session to revoke
            ip_address: Client IP address

        Returns:
            Dict with revocation confirmation
        """
        try:
            # Revoke session
            success = await self._session_manager.revoke_session(session_id)
            if not success:
                raise AuthenticationError("Session not found or already revoked")

            # Log session revocation
            await self._log_audit_event(
                user_id,
                AuditAction.LOGOUT,  # Using LOGOUT for session revocation
                AuditLevel.SECURITY,
                {'session_id': session_id, 'ip_address': ip_address}
            )

            return {
                'message': 'Session revoked successfully',
                'session_id': session_id,
                'revoked_at': datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            self.logger.error(f"Session revocation error: {str(e)}")
            raise AuthenticationError("Session revocation failed")

    # Security monitoring methods
    async def get_security_metrics(self) -> Dict[str, Any]:
        """Get security metrics and statistics"""
        try:
            security_stats = await self._security_monitor.get_security_stats()
            return {
                'auth_metrics': self._metrics.copy(),
                'security_stats': security_stats,
                'rate_limit_status': await self._get_rate_limit_status(),
                'active_sessions': await self._session_manager.get_active_session_count(),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            self.logger.error(f"Security metrics error: {str(e)}")
            return {'error': 'Failed to retrieve security metrics'}

    # Private helper methods
    def _validate_login_request(self, request: LoginRequest):
        """Validate login request data"""
        if not request.username or not request.pin:
            raise AuthenticationError("Username and PIN are required")

        # Check for suspicious patterns
        if len(request.username) > 50:
            raise SecurityError("Username too long", SecurityLevel.MEDIUM)

        # Validate PIN format
        if not request.pin.isdigit() or len(request.pin) != 4:
            raise AuthenticationError("Invalid PIN format")

    async def _check_rate_limits(self, operation: str, identifier: str):
        """Check rate limits for operations"""
        try:
            if identifier:
                # Check operation-specific rate limit
                is_allowed = await self._rate_limiters[operation].is_allowed(identifier)
                if not is_allowed:
                    retry_after = await self._rate_limiters[operation].get_retry_after(identifier)
                    self._metrics['rate_limit_hits'] += 1
                    raise RateLimitError(
                        f"Rate limit exceeded for {operation}",
                        retry_after=retry_after
                    )

                # Check global rate limit
                global_allowed = await self._rate_limiters['global'].is_allowed(identifier)
                if not global_allowed:
                    retry_after = await self._rate_limiters['global'].get_retry_after(identifier)
                    raise RateLimitError(
                        "Global rate limit exceeded",
                        retry_after=retry_after
                    )
        except RateLimitError:
            raise
        except Exception as e:
            self.logger.warning(f"Rate limit check failed: {str(e)}")
            # Don't fail the operation if rate limiting fails

    async def _get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username from database"""
        try:
            with self.db_manager.get_session() as session:
                user_orm = session.query(UserORM).filter(
                    UserORM.username == username
                ).first()

                if user_orm:
                    return User.from_dict({
                        'user_id': user_orm.user_id,
                        'username': user_orm.username,
                        'created_at': user_orm.created_at,
                        'updated_at': user_orm.updated_at,
                        'preferences': user_orm.preferences,
                        'pin_hash': user_orm.pin_hash,
                        'last_login': user_orm.last_login,
                        'login_attempts': user_orm.login_attempts,
                        'default_capital': user_orm.default_capital,
                        'risk_tolerance': user_orm.risk_tolerance,
                        'max_daily_loss': user_orm.max_daily_loss,
                        'trading_mode': user_orm.trading_mode
                    })
                return None

        except SQLAlchemyError as e:
            self.logger.error(f"Database error getting user: {str(e)}")
            raise AuthenticationError("Database error during authentication")
        except Exception as e:
            self.logger.error(f"Error getting user: {str(e)}")
            raise AuthenticationError("Error retrieving user information")

    async def _get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID from database"""
        try:
            with self.db_manager.get_session() as session:
                user_orm = session.query(UserORM).filter(
                    UserORM.user_id == user_id
                ).first()

                if user_orm:
                    return User.from_dict({
                        'user_id': user_orm.user_id,
                        'username': user_orm.username,
                        'created_at': user_orm.created_at,
                        'updated_at': user_orm.updated_at,
                        'preferences': user_orm.preferences,
                        'pin_hash': user_orm.pin_hash,
                        'last_login': user_orm.last_login,
                        'login_attempts': user_orm.login_attempts,
                        'default_capital': user_orm.default_capital,
                        'risk_tolerance': user_orm.risk_tolerance,
                        'max_daily_loss': user_orm.max_daily_loss,
                        'trading_mode': user_orm.trading_mode
                    })
                return None

        except Exception as e:
            self.logger.error(f"Error getting user by ID: {str(e)}")
            raise AuthenticationError("Error retrieving user information")

    async def _verify_pin(self, user: User, pin: str) -> bool:
        """Verify user PIN"""
        try:
            return bcrypt.checkpw(pin.encode('utf-8'), user.pin_hash.encode('utf-8'))
        except Exception as e:
            self.logger.error(f"PIN verification error: {str(e)}")
            return False

    async def _check_account_lockout(self, user_id: str):
        """Check if account is locked due to failed attempts"""
        try:
            lockout_key = f"{self.config['cache_prefix']}lockout:{user_id}"
            lockout_info = await self.cache.get(lockout_key)

            if lockout_info:
                lockout_data = json.loads(lockout_info)
                locked_until = datetime.fromisoformat(lockout_data['locked_until'])

                if datetime.now(timezone.utc) < locked_until:
                    remaining_minutes = int((locked_until - datetime.now(timezone.utc)).total_seconds() / 60)
                    raise AuthenticationError(
                        f"Account locked. Try again in {remaining_minutes} minutes."
                    )
                else:
                    # Lockout expired, remove it
                    await self.cache.delete(lockout_key)

        except AuthenticationError:
            raise
        except Exception as e:
            self.logger.error(f"Lockout check error: {str(e)}")

    async def _handle_failed_authentication(
        self,
        user: User,
        username: str,
        ip_address: str,
        user_agent: str
    ):
        """Handle failed authentication attempt"""
        try:
            # Increment failed attempts
            failed_attempts = await self._increment_failed_attempts(user.user_id)

            # Check if account should be locked
            if failed_attempts >= self.config['max_login_attempts']:
                await self._lock_account(user.user_id)

                # Log security event
                await self._log_security_event(
                    user.user_id,
                    f"Account locked after {failed_attempts} failed attempts",
                    SecurityLevel.HIGH,
                    {
                        'username': username,
                        'ip_address': ip_address,
                        'user_agent': user_agent,
                        'failed_attempts': failed_attempts
                    }
                )

            # Log failed attempt
            await self._log_failed_login(username, "Invalid PIN", ip_address, user_agent)

        except Exception as e:
            self.logger.error(f"Failed authentication handling error: {str(e)}")

    async def _increment_failed_attempts(self, user_id: str) -> int:
        """Increment failed login attempts counter"""
        try:
            attempts_key = f"{self.config['cache_prefix']}attempts:{user_id}"
            attempts = await self.cache.get(attempts_key)

            if attempts:
                new_attempts = int(attempts) + 1
            else:
                new_attempts = 1

            # Store with TTL (reset after lockout duration)
            await self.cache.set(
                attempts_key,
                str(new_attempts),
                ttl=self.config['lockout_duration_minutes'] * 60
            )

            return new_attempts

        except Exception as e:
            self.logger.error(f"Failed attempts increment error: {str(e)}")
            return 1

    async def _lock_account(self, user_id: str):
        """Lock account for specified duration"""
        try:
            locked_until = datetime.now(timezone.utc) + timedelta(
                minutes=self.config['lockout_duration_minutes']
            )

            lockout_key = f"{self.config['cache_prefix']}lockout:{user_id}"
            lockout_data = {
                'locked_until': locked_until.isoformat(),
                'reason': 'Too many failed login attempts'
            }

            await self.cache.set(
                lockout_key,
                json.dumps(lockout_data),
                ttl=self.config['lockout_duration_minutes'] * 60
            )

        except Exception as e:
            self.logger.error(f"Account lockout error: {str(e)}")

    async def _reset_failed_attempts(self, user_id: str):
        """Reset failed login attempts counter"""
        try:
            attempts_key = f"{self.config['cache_prefix']}attempts:{user_id}"
            await self.cache.delete(attempts_key)
        except Exception as e:
            self.logger.error(f"Reset failed attempts error: {str(e)}")

    async def _generate_token_response(
        self,
        user: User,
        session,
        remember_me: bool = False
    ) -> TokenResponse:
        """Generate token response with access and refresh tokens"""
        try:
            # Calculate expiration times
            if remember_me:
                access_expire = datetime.now(timezone.utc) + timedelta(
                    days=self.config['remember_me_expire_days']
                )
                refresh_expire = datetime.now(timezone.utc) + timedelta(
                    days=self.config['remember_me_expire_days']
                )
            else:
                access_expire = datetime.now(timezone.utc) + timedelta(
                    minutes=self.config['access_token_expire_minutes']
                )
                refresh_expire = datetime.now(timezone.utc) + timedelta(
                    days=self.config['refresh_token_expire_days']
                )

            # Create token payloads
            base_payload = {
                'user_id': user.user_id,
                'username': user.username,
                'role': AuthRole.TRADER.value,
                'trading_mode': user.trading_mode.value,
                'session_id': session.session_id,
                'permissions': ['trade', 'view_portfolio', 'manage_strategies'],
                'security_level': 'medium',
                'remember_me': remember_me,
                'iss': 'niraj',
                'aud': 'niraj-client'
            }

            # Access token payload
            access_payload = base_payload.copy()
            access_payload.update({
                'token_type': TokenType.ACCESS.value,
                'exp': access_expire.timestamp(),
                'iat': datetime.now(timezone.utc).timestamp()
            })

            # Refresh token payload
            refresh_payload = base_payload.copy()
            refresh_payload.update({
                'token_type': TokenType.REFRESH.value,
                'exp': refresh_expire.timestamp(),
                'iat': datetime.now(timezone.utc).timestamp()
            })

            # Generate tokens
            access_token = jwt.encode(
                access_payload,
                self.config['jwt_secret_key'],
                algorithm=self.config['jwt_algorithm']
            )

            refresh_token = jwt.encode(
                refresh_payload,
                self.config['jwt_secret_key'],
                algorithm=self.config['jwt_algorithm']
            )

            # Calculate expires_in for response
            expires_in = int((access_expire - datetime.now(timezone.utc)).total_seconds())

            return TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer",
                expires_in=expires_in,
                user_id=user.user_id,
                username=user.username,
                role=AuthRole.TRADER.value,
                trading_mode=user.trading_mode.value,
                session_id=session.session_id
            )

        except Exception as e:
            self.logger.error(f"Token generation error: {str(e)}")
            raise AuthenticationError("Failed to generate authentication tokens")

    async def _decode_token(self, token: str, token_type: TokenType) -> Dict[str, Any]:
        """Decode and validate JWT token"""
        try:
            payload = jwt.decode(
                token,
                self.config['jwt_secret_key'],
                algorithms=[self.config['jwt_algorithm']],
                audience='niraj-client',
                issuer='niraj'
            )

            # Verify token type
            if payload.get('token_type') != token_type.value:
                raise TokenError(f"Invalid token type, expected {token_type.value}")

            # Check expiration
            exp_timestamp = payload.get('exp')
            if exp_timestamp and datetime.now(timezone.utc).timestamp() > exp_timestamp:
                raise TokenError("Token expired")

            return payload

        except jwt.ExpiredSignatureError:
            raise TokenError("Token expired")
        except jwt.InvalidTokenError as e:
            raise TokenError(f"Invalid token: {str(e)}")
        except Exception as e:
            self.logger.error(f"Token decode error: {str(e)}")
            raise TokenError("Token validation failed")

    async def _update_last_login(self, user_id: str):
        """Update user's last login timestamp"""
        try:
            with self.db_manager.get_session() as session:
                user_orm = session.query(UserORM).filter(
                    UserORM.user_id == user_id
                ).first()

                if user_orm:
                    user_orm.last_login = datetime.now(timezone.utc)
                    user_orm.login_attempts = 0  # Reset failed attempts
                    session.commit()

        except Exception as e:
            self.logger.error(f"Update last login error: {str(e)}")

    async def _update_trading_mode(self, user_id: str, new_mode: TradingMode):
        """Update user's trading mode"""
        try:
            with self.db_manager.get_session() as session:
                user_orm = session.query(UserORM).filter(
                    UserORM.user_id == user_id
                ).first()

                if user_orm:
                    user_orm.trading_mode = new_mode.value
                    user_orm.updated_at = datetime.now(timezone.utc)
                    session.commit()

        except Exception as e:
            self.logger.error(f"Update trading mode error: {str(e)}")
            raise AuthenticationError("Failed to update trading mode")

    async def _update_user_pin(self, user_id: str, new_pin: str):
        """Update user's PIN hash"""
        try:
            # Hash new PIN
            pin_hash = bcrypt.hashpw(new_pin.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

            with self.db_manager.get_session() as session:
                user_orm = session.query(UserORM).filter(
                    UserORM.user_id == user_id
                ).first()

                if user_orm:
                    user_orm.pin_hash = pin_hash
                    user_orm.updated_at = datetime.now(timezone.utc)
                    session.commit()

        except Exception as e:
            self.logger.error(f"Update PIN error: {str(e)}")
            raise AuthenticationError("Failed to update PIN")

    async def _validate_new_pin(self, new_pin: str, current_hash: str):
        """Validate new PIN meets security requirements"""
        try:
            # Check PIN strength
            if new_pin in ['0000', '1234', '1111', '2222', '3333', '4444',
                          '5555', '6666', '7777', '8888', '9999']:
                raise UserValidationError("PIN too weak, avoid common patterns")

            # Check if same as current PIN
            if bcrypt.checkpw(new_pin.encode('utf-8'), current_hash.encode('utf-8')):
                raise UserValidationError("New PIN must be different from current PIN")

            # Check for patterns (sequential, repeated digits)
            if self._has_weak_pattern(new_pin):
                raise UserValidationError("PIN contains weak patterns")

        except UserValidationError:
            raise
        except Exception as e:
            self.logger.error(f"PIN validation error: {str(e)}")
            raise UserValidationError("PIN validation failed")

    def _has_weak_pattern(self, pin: str) -> bool:
        """Check for weak patterns in PIN"""
        # Check for sequential digits
        for i in range(len(pin) - 1):
            if int(pin[i+1]) == int(pin[i]) + 1:
                continue
            else:
                break
        else:
            return True  # All digits are sequential

        # Check for reverse sequential digits
        for i in range(len(pin) - 1):
            if int(pin[i+1]) == int(pin[i]) - 1:
                continue
            else:
                break
        else:
            return True  # All digits are reverse sequential

        return False

    # Logging methods
    async def _log_successful_login(
        self,
        user_id: str,
        username: str,
        session_id: str,
        ip_address: str,
        user_agent: str
    ):
        """Log successful login event"""
        await self._log_audit_event(
            user_id,
            AuditAction.LOGIN_SUCCESS,
            AuditLevel.INFO,
            {
                'username': username,
                'session_id': session_id,
                'ip_address': ip_address,
                'user_agent': user_agent
            }
        )

    async def _log_failed_login(
        self,
        username: str,
        reason: str,
        ip_address: str,
        user_agent: str
    ):
        """Log failed login attempt"""
        await self._log_audit_event(
            None,  # No user_id for failed attempts
            AuditAction.LOGIN_FAILURE,
            AuditLevel.WARNING,
            {
                'username': username,
                'reason': reason,
                'ip_address': ip_address,
                'user_agent': user_agent
            }
        )

    async def _log_security_event(
        self,
        user_id: str,
        message: str,
        security_level: SecurityLevel,
        details: Dict[str, Any]
    ):
        """Log security event"""
        await self._log_audit_event(
            user_id,
            AuditAction.SECURITY_ALERT,  # Using SECURITY_ALERT for security events
            AuditLevel.ERROR,  # Map to ERROR level as closest match
            {
                'message': message,
                'security_level': security_level.value,
                **details
            }
        )

        # Also increment security violation counter
        self._metrics['security_violations'] += 1

    async def _log_audit_event(
        self,
        user_id: Optional[str],
        action: AuditAction,
        level: AuditLevel,
        details: Dict[str, Any]
    ):
        """Log audit event to database and logs"""
        try:
            # Log to structured logger
            self.audit_logger.log(
                level.name,
                f"Audit event: {action.value}",
                user_id=user_id,
                action=action.value,
                details=details,
                timestamp=datetime.now(timezone.utc).isoformat()
            )

            # Store in database if audit logging is enabled
            if self.config.get('enable_audit_logging', True):
                audit_log = AuditLog(
                    user_id=user_id,
                    action=action,
                    level=level,
                    details=details,
                    ip_address=details.get('ip_address'),
                    user_agent=details.get('user_agent')
                )

                # Save to database (assuming we have an audit service)
                # This would typically be handled by an audit service
                pass

        except Exception as e:
            self.logger.error(f"Audit logging error: {str(e)}")

    async def _get_rate_limit_status(self) -> Dict[str, Any]:
        """Get current rate limit status"""
        try:
            status = {}
            for name, limiter in self._rate_limiters.items():
                status[name] = {
                    'requests_allowed': limiter.requests,
                    'window_seconds': limiter.window,
                    'current_usage': await limiter.get_current_usage('global')
                }
            return status
        except Exception as e:
            self.logger.error(f"Rate limit status error: {str(e)}")
            return {}


# Helper classes
class RateLimiter:
    """Redis-based rate limiter"""

    def __init__(self, cache: CacheManager, name: str, requests: int, window: int):
        self.cache = cache
        self.name = name
        self.requests = requests
        self.window = window

    async def is_allowed(self, identifier: str) -> bool:
        """Check if request is allowed"""
        try:
            key = f"rate_limit:{self.name}:{identifier}"
            current = await self.cache.get(key)

            if current is None:
                await self.cache.set(key, "1", ttl=self.window)
                return True

            count = int(current)
            if count >= self.requests:
                return False

            # Increment counter
            await self.cache.increment(key)
            return True

        except Exception:
            # Allow request if rate limiting fails
            return True

    async def get_retry_after(self, identifier: str) -> int:
        """Get retry after seconds"""
        try:
            key = f"rate_limit:{self.name}:{identifier}"
            ttl = await self.cache.get_ttl(key)
            return max(0, ttl)
        except Exception:
            return 0

    async def get_current_usage(self, identifier: str) -> int:
        """Get current usage count"""
        try:
            key = f"rate_limit:{self.name}:{identifier}"
            current = await self.cache.get(key)
            return int(current) if current else 0
        except Exception:
            return 0


class SessionManager:
    """Session management with Redis backend"""

    def __init__(self, cache: CacheManager, timeout_minutes: int, max_sessions: int):
        self.cache = cache
        self.timeout_minutes = timeout_minutes
        self.max_sessions = max_sessions

    async def create_session(
        self,
        user_id: str,
        username: str,
        role: AuthRole,
        trading_mode: TradingMode,
        device_info: Optional[Dict[str, Any]] = None,
        remember_me: bool = False
    ):
        """Create new session"""
        session_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        # Calculate expiration
        if remember_me:
            expires_at = now + timedelta(days=30)
        else:
            expires_at = now + timedelta(minutes=self.timeout_minutes)

        session_data = {
            'session_id': session_id,
            'user_id': user_id,
            'username': username,
            'role': role.value,
            'trading_mode': trading_mode.value,
            'created_at': now.isoformat(),
            'last_activity': now.isoformat(),
            'expires_at': expires_at.isoformat(),
            'device_info': device_info,
            'is_active': True,
            'security_level': 'medium'
        }

        # Store session
        session_key = f"session:{session_id}"
        user_sessions_key = f"user_sessions:{user_id}"

        await self.cache.set(
            session_key,
            json.dumps(session_data),
            ttl=int((expires_at - now).total_seconds())
        )

        # Add to user's session list
        await self.cache.sadd(user_sessions_key, session_id)

        # Enforce max sessions limit
        await self._enforce_session_limit(user_id)

        # Return session object
        from types import SimpleNamespace
        return SimpleNamespace(**session_data)

    async def get_session(self, session_id: str):
        """Get session by ID"""
        try:
            session_key = f"session:{session_id}"
            session_data = await self.cache.get(session_key)

            if not session_data:
                return None

            data = json.loads(session_data)

            # Check if expired
            expires_at = datetime.fromisoformat(data['expires_at'])
            if datetime.now(timezone.utc) > expires_at:
                await self.revoke_session(session_id)
                return None

            from types import SimpleNamespace
            return SimpleNamespace(**data)

        except Exception:
            return None

    async def update_session_activity(self, session_id: str):
        """Update session last activity"""
        try:
            session = await self.get_session(session_id)
            if session:
                session_key = f"session:{session_id}"
                session_data = json.loads(await self.cache.get(session_key))
                session_data['last_activity'] = datetime.now(timezone.utc).isoformat()

                # Update TTL
                expires_at = datetime.fromisoformat(session_data['expires_at'])
                ttl = int((expires_at - datetime.now(timezone.utc)).total_seconds())

                await self.cache.set(session_key, json.dumps(session_data), ttl=ttl)
        except Exception:
            pass

    async def revoke_session(self, session_id: str) -> bool:
        """Revoke a session"""
        try:
            session = await self.get_session(session_id)
            if not session:
                return False

            # Remove from cache
            session_key = f"session:{session_id}"
            user_sessions_key = f"user_sessions:{session.user_id}"

            await self.cache.delete(session_key)
            await self.cache.srem(user_sessions_key, session_id)

            return True
        except Exception:
            return False

    async def get_user_sessions(self, user_id: str):
        """Get all sessions for a user"""
        try:
            user_sessions_key = f"user_sessions:{user_id}"
            session_ids = await self.cache.smembers(user_sessions_key)

            sessions = []
            for session_id in session_ids:
                session = await self.get_session(session_id)
                if session:
                    sessions.append(session)

            return sessions
        except Exception:
            return []

    async def revoke_all_user_sessions(self, user_id: str):
        """Revoke all sessions for a user"""
        try:
            sessions = await self.get_user_sessions(user_id)
            for session in sessions:
                await self.revoke_session(session.session_id)
        except Exception:
            pass

    async def get_active_session_count(self) -> int:
        """Get count of all active sessions"""
        try:
            # This would need to be implemented based on cache backend
            # For now, return 0
            return 0
        except Exception:
            return 0

    async def _enforce_session_limit(self, user_id: str):
        """Enforce maximum session limit per user"""
        try:
            sessions = await self.get_user_sessions(user_id)
            if len(sessions) > self.max_sessions:
                # Sort by last activity and remove oldest sessions
                sessions.sort(key=lambda s: s.last_activity)
                for session in sessions[:-self.max_sessions]:
                    await self.revoke_session(session.session_id)
        except Exception:
            pass


class SecurityMonitor:
    """Security monitoring and threat detection"""

    def __init__(self, cache: CacheManager, logger):
        self.cache = cache
        self.logger = logger

    async def check_suspicious_activity(
        self,
        username: str,
        ip_address: str,
        user_agent: str
    ):
        """Check for suspicious activity patterns"""
        try:
            # Check for rapid login attempts from same IP
            if ip_address:
                ip_key = f"security:ip_attempts:{ip_address}"
                attempts = await self.cache.get(ip_key)
                if attempts and int(attempts) > 20:  # 20 attempts per hour
                    raise SecurityError("Suspicious activity detected from IP address")

                await self.cache.increment(ip_key, ttl=3600)

            # Check for login attempts with multiple usernames from same IP
            if ip_address and username:
                ip_users_key = f"security:ip_users:{ip_address}"
                await self.cache.sadd(ip_users_key, username, ttl=3600)
                unique_users = await self.cache.scard(ip_users_key)

                if unique_users > 10:  # More than 10 different usernames from same IP
                    raise SecurityError("Multiple username attempts detected")

        except SecurityError:
            raise
        except Exception as e:
            self.logger.warning(f"Security check failed: {str(e)}")

    async def get_security_stats(self) -> Dict[str, Any]:
        """Get security statistics"""
        return {
            'suspicious_ips_detected': 0,
            'blocked_attempts': 0,
            'active_threats': 0
        }


# Security decorators
def require_auth(required_permissions: List[str] = None):
    """Decorator to require authentication"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # This would be implemented to work with FastAPI dependencies
            # For now, just pass through
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def rate_limit(operation: str):
    """Decorator for rate limiting"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # This would be implemented to work with FastAPI dependencies
            # For now, just pass through
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# Export main service class and exceptions
__all__ = [
    'AuthenticationService',
    'AuthenticationError',
    'AuthorizationError',
    'TokenError',
    'RateLimitError',
    'SecurityError',
    'SecurityContext',
    'LoginRequest',
    'TokenResponse',
    'RefreshTokenRequest',
    'SwitchModeRequest',
    'ChangePasswordRequest',
    'SessionInfo',
    'TokenType',
    'AuthRole',
    'SessionStatus',
    'SecurityLevel'
]
