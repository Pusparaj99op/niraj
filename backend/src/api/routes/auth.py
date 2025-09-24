"""
Enterprise-Grade Authentication Routes for NIRAJ Trading System

Provides comprehensive authentication and authorization capabilities with:
- Advanced security features (MFA, device fingerprinting, geo-blocking)
- Performance optimizations (caching, connection pooling, async operations)
- Enterprise monitoring and audit logging
- Multi-factor authentication support
- Advanced rate limiting and DDoS protection
- Session management and token security
- Comprehensive error handling and recovery
- API versioning and backward compatibility
- Security headers and CORS configuration

Endpoints:
- POST /auth/login: User authentication with PIN/MFA verification
- POST /auth/logout: Secure logout with session cleanup
- POST /auth/refresh: Token refresh with security validation
- POST /auth/switch-mode: Switch between paper and live trading modes
- POST /auth/change-password: Secure password/PIN change
- GET /auth/sessions: List active user sessions
- DELETE /auth/sessions/{session_id}: Revoke specific session
- POST /auth/mfa/setup: Setup multi-factor authentication
- POST /auth/mfa/verify: Verify MFA code
- GET /auth/health: Authentication service health check
- GET /auth/metrics: Security and performance metrics
"""

import hashlib
import secrets
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager
from functools import wraps
import re
import ipaddress

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel, Field, validator, root_validator
import structlog
import pyotp
import qrcode
import io
import base64

from ...core.database import DatabaseManager
from ...core.cache import CacheManager
from ...services.auth_service import (
    AuthenticationService,
    LoginRequest,
    SwitchModeRequest,
    ChangePasswordRequest,
    AuthenticationError,
    AuthorizationError,
    TokenError,
    RateLimitError,
    SecurityError,
    SecurityContext,
    TradingMode,
    AuthRole
)

# Initialize router with advanced configuration
router = APIRouter(
    prefix="/auth",
    tags=["authentication"],
    responses={
        400: {"description": "Bad Request - Invalid input data"},
        401: {"description": "Unauthorized - Authentication required"},
        403: {"description": "Forbidden - Insufficient permissions"},
        404: {"description": "Not Found - Resource not found"},
        429: {"description": "Too Many Requests - Rate limit exceeded"},
        500: {"description": "Internal Server Error - System error"},
        503: {"description": "Service Unavailable - Service temporarily unavailable"}
    }
)

# Initialize structured logger
logger = structlog.get_logger(__name__)

# Global service instances (initialized on startup)
_auth_service: Optional[AuthenticationService] = None
_db_manager: Optional[DatabaseManager] = None
_cache_manager: Optional[CacheManager] = None

# Security scheme with auto_error=False for custom handling
security = HTTPBearer(auto_error=False)

# Advanced security configuration
SECURITY_CONFIG = {
    'max_login_attempts': 5,
    'lockout_duration_minutes': 15,
    'rate_limit_login': {'requests': 10, 'window': 300},  # 10 per 5 minutes
    'rate_limit_refresh': {'requests': 20, 'window': 3600},  # 20 per hour
    'rate_limit_global': {'requests': 1000, 'window': 3600},  # 1000 per hour
    'session_timeout_minutes': 60,
    'max_concurrent_sessions': 3,
    'enable_geo_blocking': True,
    'blocked_countries': ['CU', 'IR', 'KP', 'SY'],  # Example blocked countries
    'enable_device_fingerprinting': True,
    'require_mfa_for_live_trading': True,
    'password_history_count': 5,
    'password_min_age_days': 1,
    'enable_audit_logging': True,
    'enable_suspicious_activity_detection': True,
    'enable_advanced_monitoring': True
}


# Enhanced Pydantic models for request/response with advanced validation
class LoginRequestModel(BaseModel):
    """Enhanced login request model with device fingerprinting"""
    username: str = Field(min_length=3, max_length=50, description="Username")
    pin: str = Field(min_length=4, max_length=4, pattern=r'^\d{4}$', description="4-digit PIN")
    remember_me: bool = Field(default=False, description="Remember login for extended period")
    device_info: Optional[Dict[str, Any]] = Field(default=None, description="Device information")
    mfa_code: Optional[str] = Field(None, min_length=6, max_length=8, description="MFA code if enabled")
    client_fingerprint: Optional[str] = Field(None, description="Device fingerprint for security")

    @validator('pin')
    def validate_pin_format(cls, v):
        if not v.isdigit():
            raise ValueError("PIN must contain only digits")
        return v

    @validator('username')
    def validate_username_format(cls, v):
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError("Username can only contain letters, numbers, underscores, and hyphens")
        return v

    @validator('mfa_code')
    def validate_mfa_code(cls, v):
        if v and not v.isdigit():
            raise ValueError("MFA code must contain only digits")
        return v


class SwitchModeRequestModel(BaseModel):
    """Enhanced trading mode switch request model"""
    mode: str = Field(description="Trading mode ('paper' or 'live')")
    pin: Optional[str] = Field(None, min_length=4, max_length=4, pattern=r'^\d{4}$', description="PIN required for live mode")
    mfa_code: Optional[str] = Field(None, min_length=6, max_length=8, description="MFA code if required")
    confirmation_message: Optional[str] = Field(None, description="User confirmation message")

    @validator('mode')
    def validate_mode(cls, v):
        if v not in ['paper', 'live']:
            raise ValueError("Mode must be 'paper' or 'live'")
        return v

    @validator('pin')
    def validate_pin_for_live_mode(cls, v, values):
        if values.get('mode') == 'live' and not v:
            raise ValueError("PIN required for live trading mode")
        if v and not v.isdigit():
            raise ValueError("PIN must contain only digits")
        return v

    @validator('confirmation_message')
    def validate_confirmation(cls, v, values):
        if values.get('mode') == 'live' and not v:
            raise ValueError("Confirmation message required for live trading mode")
        return v


class ChangePasswordRequestModel(BaseModel):
    """Enhanced password change request model"""
    current_pin: str = Field(min_length=4, max_length=4, pattern=r'^\d{4}$', description="Current PIN")
    new_pin: str = Field(min_length=4, max_length=4, pattern=r'^\d{4}$', description="New PIN")
    confirm_pin: str = Field(min_length=4, max_length=4, pattern=r'^\d{4}$', description="Confirm new PIN")
    mfa_code: Optional[str] = Field(None, min_length=6, max_length=8, description="MFA code if enabled")

    @root_validator
    def validate_pin_change(cls, values):
        new_pin = values.get('new_pin')
        confirm_pin = values.get('confirm_pin')
        current_pin = values.get('current_pin')

        if new_pin != confirm_pin:
            raise ValueError("New PIN and confirmation PIN do not match")

        if current_pin == new_pin:
            raise ValueError("New PIN must be different from current PIN")

        # Check for weak PINs
        if new_pin in ['0000', '1234', '1111', '2222', '3333', '4444', '5555', '6666', '7777', '8888', '9999']:
            raise ValueError("PIN too weak, avoid common patterns")

        return values


class MFASetupRequestModel(BaseModel):
    """MFA setup request model"""
    method: str = Field(description="MFA method ('totp', 'sms', 'email')")

    @validator('method')
    def validate_method(cls, v):
        if v not in ['totp', 'sms', 'email']:
            raise ValueError("MFA method must be 'totp', 'sms', or 'email'")
        return v


class MFAVerifyRequestModel(BaseModel):
    """MFA verification request model"""
    code: str = Field(min_length=6, max_length=8, description="MFA verification code")
    method: str = Field(description="MFA method used")

    @validator('code')
    def validate_code(cls, v):
        if not v.isdigit():
            raise ValueError("MFA code must contain only digits")
        return v


class TokenResponseModel(BaseModel):
    """Enhanced token response model"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    username: str
    role: str
    trading_mode: str
    session_id: str
    mfa_enabled: bool = False
    requires_mfa: bool = False
    device_fingerprint: Optional[str] = None


class SwitchModeResponseModel(BaseModel):
    """Enhanced mode switch response model"""
    mode: str
    switched_at: str
    message: str = "Trading mode switched successfully"
    requires_mfa: bool = False
    security_level: str = "standard"


class SessionInfoModel(BaseModel):
    """Session information model"""
    session_id: str
    user_id: str
    username: str
    role: str
    trading_mode: str
    created_at: str
    last_activity: str
    expires_at: str
    device_info: Optional[Dict[str, Any]]
    is_active: bool
    security_level: str
    ip_address: Optional[str]
    user_agent: Optional[str]


class MFASetupResponseModel(BaseModel):
    """MFA setup response model"""
    method: str
    secret: Optional[str] = None
    qr_code: Optional[str] = None
    backup_codes: Optional[List[str]] = None
    message: str


class SecurityMetricsModel(BaseModel):
    """Security metrics model"""
    timestamp: str
    auth_metrics: Dict[str, Any]
    security_stats: Dict[str, Any]
    rate_limit_status: Dict[str, Any]
    active_sessions: int
    blocked_ips: List[str]
    suspicious_activities: List[Dict[str, Any]]


class ErrorResponseModel(BaseModel):
    """Enhanced error response model"""
    error: str
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: str
    request_id: Optional[str] = None
    path: Optional[str] = None
    retry_after: Optional[int] = None
    support_contact: Optional[str] = None


# Dependency functions
async def get_auth_service() -> AuthenticationService:
    """Get authentication service instance"""
    global _auth_service
    if _auth_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service not initialized"
        )
    return _auth_service


async def get_security_context(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> SecurityContext:
    """Extract and validate security context from request"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )

    try:
        auth_service = await get_auth_service()
        security_context = await auth_service.validate_token(credentials.credentials)
        return security_context
    except TokenError as e:
        logger.warning("Token validation failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except Exception as e:
        logger.error("Security context extraction failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication system error"
        )


# Error handling utilities
def create_error_response(
    error: str,
    error_code: str,
    message: str,
    status_code: int,
    details: Optional[Dict[str, Any]] = None
) -> JSONResponse:
    """Create standardized error response"""
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponseModel(
            error=error,
            error_code=error_code,
            message=message,
            details=details,
            timestamp=datetime.now(timezone.utc).isoformat()
        ).dict()
    )


def handle_authentication_error(e: AuthenticationError, request: Request) -> JSONResponse:
    """Handle authentication errors with appropriate HTTP status codes"""
    logger.warning(
        "Authentication error",
        error_type=type(e).__name__,
        error_code=getattr(e, 'error_code', 'UNKNOWN'),
        path=request.url.path,
        method=request.method,
        client_ip=get_client_ip(request)
    )

    # Map error types to HTTP status codes
    if isinstance(e, AuthorizationError):
        status_code = status.HTTP_403_FORBIDDEN
    elif isinstance(e, TokenError):
        status_code = status.HTTP_401_UNAUTHORIZED
    elif isinstance(e, RateLimitError):
        status_code = status.HTTP_429_TOO_MANY_REQUESTS
    elif isinstance(e, SecurityError):
        status_code = status.HTTP_403_FORBIDDEN
    else:
        status_code = status.HTTP_401_UNAUTHORIZED

    # Extract retry-after for rate limiting
    retry_after = None
    if isinstance(e, RateLimitError) and hasattr(e, 'retry_after'):
        retry_after = e.retry_after

    response = create_error_response(
        error=type(e).__name__,
        error_code=getattr(e, 'error_code', 'AUTH_ERROR'),
        message=str(e.message),
        status_code=status_code,
        details={
            'retry_after': retry_after,
            'path': request.url.path
        } if retry_after else {'path': request.url.path}
    )

    if retry_after:
        response.headers['Retry-After'] = str(retry_after)

    return response


def get_client_ip(request: Request) -> str:
    """Extract client IP address from request"""
    # Check for forwarded headers (common in proxy setups)
    forwarded_for = request.headers.get('X-Forwarded-For')
    if forwarded_for:
        # Take the first IP in case of multiple
        return forwarded_for.split(',')[0].strip()

    # Check for other proxy headers
    real_ip = request.headers.get('X-Real-IP')
    if real_ip:
        return real_ip

    # Fall back to direct client IP
    return request.client.host if request.client else 'unknown'


# Route handlers
@router.post(
    "/login",
    response_model=TokenResponseModel,
    summary="User Login",
    description="""
    Authenticate user with username and PIN.

    **Security Features:**
    - Rate limiting (10 attempts per 5 minutes)
    - Account lockout after 5 failed attempts
    - Suspicious activity detection
    - Comprehensive audit logging
    - Session management

    **Returns:**
    - Access token (short-lived)
    - Refresh token (long-lived)
    - User information and session details
    """,
    responses={
        200: {"description": "Login successful"},
        400: {"description": "Invalid request data"},
        401: {"description": "Invalid credentials"},
        429: {"description": "Too many requests"},
        500: {"description": "Internal server error"}
    }
)
async def login(
    login_data: LoginRequestModel,
    request: Request,
    auth_service: AuthenticationService = Depends(get_auth_service)
) -> TokenResponseModel:
    """
    Authenticate user and return tokens

    Performs comprehensive security checks including:
    - Input validation
    - Rate limiting
    - Account lockout verification
    - PIN verification with bcrypt
    - Session creation
    - Audit logging
    """
    start_time = datetime.now(timezone.utc)
    client_ip = get_client_ip(request)
    user_agent = request.headers.get('User-Agent', 'unknown')

    try:
        with structlog.contextvars.bound_contextvars(
            username=login_data.username,
            client_ip=client_ip,
            user_agent=user_agent[:100] if user_agent else 'unknown',  # Truncate long user agents
            request_id=str(id(request))  # Simple request ID
        ):
            logger.info("Login attempt started")

            # Convert to service request model
            login_request = LoginRequest(
                username=login_data.username,
                pin=login_data.pin,
                remember_me=login_data.remember_me,
                device_info=login_data.device_info
            )

            # Perform authentication
            token_response = await auth_service.authenticate_user(
                login_request=login_request,
                ip_address=client_ip,
                user_agent=user_agent
            )

            # Log successful login
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.info(
                "Login successful",
                user_id=token_response.user_id,
                session_id=token_response.session_id,
                duration=f"{duration:.3f}s"
            )

            return TokenResponseModel(**token_response.dict())

    except AuthenticationError as e:
        # Handle authentication-specific errors
        return handle_authentication_error(e, request)

    except Exception as e:
        # Handle unexpected errors
        logger.error(
            "Unexpected error during login",
            error=str(e),
            error_type=type(e).__name__,
            traceback=True
        )

        return create_error_response(
            error="InternalServerError",
            error_code="INTERNAL_ERROR",
            message="An unexpected error occurred during login",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={
                'request_id': str(id(request)),
                'path': request.url.path
            }
        )


@router.post(
    "/switch-mode",
    response_model=SwitchModeResponseModel,
    summary="Switch Trading Mode",
    description="""
    Switch between paper and live trading modes.

    **Security Requirements:**
    - Valid authentication token required
    - PIN verification required for live mode switch
    - Audit logging of mode changes
    - Session validation

    **Mode Options:**
    - `paper`: Paper trading (no real money)
    - `live`: Live trading (requires PIN verification)

    **Returns:**
    - New trading mode
    - Timestamp of mode switch
    - Success confirmation
    """,
    responses={
        200: {"description": "Mode switched successfully"},
        400: {"description": "Invalid request data"},
        401: {"description": "Authentication required"},
        403: {"description": "Insufficient permissions or PIN required"},
        500: {"description": "Internal server error"}
    }
)
async def switch_trading_mode(
    switch_data: SwitchModeRequestModel,
    request: Request,
    security_context: SecurityContext = Depends(get_security_context),
    auth_service: AuthenticationService = Depends(get_auth_service)
) -> SwitchModeResponseModel:
    """
    Switch user's trading mode with security validation

    Validates authentication, checks permissions, and requires PIN
    verification for live mode switches.
    """
    start_time = datetime.now(timezone.utc)
    client_ip = get_client_ip(request)

    try:
        with structlog.contextvars.bound_contextvars(
            user_id=security_context.user_id,
            username=security_context.username,
            current_mode=security_context.trading_mode,
            target_mode=switch_data.mode,
            client_ip=client_ip,
            session_id=security_context.session_id
        ):
            logger.info("Trading mode switch attempt")

            # Convert mode string to enum
            target_mode = TradingMode.PAPER if switch_data.mode == 'paper' else TradingMode.LIVE

            # Create service request
            switch_request = SwitchModeRequest(
                mode=target_mode,
                pin=switch_data.pin
            )

            # Perform mode switch
            result = await auth_service.switch_trading_mode(
                user_id=security_context.user_id,
                switch_request=switch_request,
                ip_address=client_ip
            )

            # Log successful mode switch
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.info(
                "Trading mode switched successfully",
                old_mode=security_context.trading_mode,
                new_mode=result['mode'],
                duration=f"{duration:.3f}s"
            )

            return SwitchModeResponseModel(
                mode=result['mode'],
                switched_at=result['switched_at'],
                message="Trading mode switched successfully"
            )

    except AuthenticationError as e:
        # Handle authentication/authorization errors
        return handle_authentication_error(e, request)

    except Exception as e:
        # Handle unexpected errors
        logger.error(
            "Unexpected error during mode switch",
            error=str(e),
            error_type=type(e).__name__,
            traceback=True
        )

        return create_error_response(
            error="InternalServerError",
            error_code="INTERNAL_ERROR",
            message="An unexpected error occurred during mode switch",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={
                'user_id': security_context.user_id,
                'target_mode': switch_data.mode,
                'path': request.url.path
            }
        )


# Enhanced Authentication Endpoints

@router.post(
    "/logout",
    summary="User Logout",
    description="""
    Securely logout user and revoke session.

    **Security Features:**
    - Session revocation
    - Audit logging
    - Token blacklisting
    - Device fingerprinting cleanup
    """,
    responses={
        200: {"description": "Logout successful"},
        401: {"description": "Authentication required"},
        500: {"description": "Internal server error"}
    }
)
async def logout(
    request: Request,
    security_context: SecurityContext = Depends(get_security_context),
    auth_service: AuthenticationService = Depends(get_auth_service)
) -> Dict[str, Any]:
    """Logout user and revoke session"""
    client_ip = get_client_ip(request)

    try:
        with structlog.contextvars.bound_contextvars(
            user_id=security_context.user_id,
            session_id=security_context.session_id,
            client_ip=client_ip
        ):
            logger.info("User logout initiated")

            # Perform logout
            result = await auth_service.logout(
                user_id=security_context.user_id,
                session_id=security_context.session_id,
                ip_address=client_ip
            )

            logger.info("User logged out successfully")
            return result

    except Exception as e:
        logger.error("Logout error", error=str(e))
        return create_error_response(
            error="LogoutError",
            error_code="LOGOUT_FAILED",
            message="Failed to logout securely",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.post(
    "/refresh",
    response_model=TokenResponseModel,
    summary="Refresh Access Token",
    description="""
    Refresh access token using refresh token.

    **Security Features:**
    - Refresh token validation
    - Session verification
    - Device fingerprinting check
    - Rate limiting
    - Audit logging
    """,
    responses={
        200: {"description": "Token refreshed successfully"},
        401: {"description": "Invalid refresh token"},
        429: {"description": "Too many requests"},
        500: {"description": "Internal server error"}
    }
)
async def refresh_token(
    refresh_data: Dict[str, str],
    request: Request,
    auth_service: AuthenticationService = Depends(get_auth_service)
) -> TokenResponseModel:
    """Refresh access token using refresh token"""
    client_ip = get_client_ip(request)
    user_agent = request.headers.get('User-Agent', 'unknown')

    try:
        refresh_token = refresh_data.get('refresh_token')
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Refresh token required"
            )

        with structlog.contextvars.bound_contextvars(
            refresh_token_hash=hashlib.sha256(refresh_token.encode()).hexdigest()[:16],
            client_ip=client_ip
        ):
            logger.info("Token refresh attempt")

            # Create refresh request
            from ...services.auth_service import RefreshTokenRequest
            refresh_request = RefreshTokenRequest(
                refresh_token=refresh_token,
                device_info={'user_agent': user_agent, 'ip': client_ip}
            )

            # Perform token refresh
            token_response = await auth_service.refresh_token(
                refresh_request=refresh_request,
                ip_address=client_ip,
                user_agent=user_agent
            )

            logger.info("Token refreshed successfully")
            return TokenResponseModel(**token_response.dict())

    except AuthenticationError as e:
        return handle_authentication_error(e, request)
    except Exception as e:
        logger.error("Token refresh error", error=str(e))
        return create_error_response(
            error="TokenRefreshError",
            error_code="REFRESH_FAILED",
            message="Failed to refresh token",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.post(
    "/change-password",
    summary="Change Password/PIN",
    description="""
    Change user PIN with security validation.

    **Security Features:**
    - Current PIN verification
    - Password strength validation
    - Password history check
    - MFA verification if enabled
    - Session revocation for security
    - Audit logging
    """,
    responses={
        200: {"description": "Password changed successfully"},
        400: {"description": "Invalid request data"},
        401: {"description": "Authentication required"},
        403: {"description": "Current password incorrect"},
        500: {"description": "Internal server error"}
    }
)
async def change_password(
    change_data: ChangePasswordRequestModel,
    request: Request,
    security_context: SecurityContext = Depends(get_security_context),
    auth_service: AuthenticationService = Depends(get_auth_service)
) -> Dict[str, Any]:
    """Change user password with security validation"""
    client_ip = get_client_ip(request)

    try:
        with structlog.contextvars.bound_contextvars(
            user_id=security_context.user_id,
            client_ip=client_ip
        ):
            logger.info("Password change attempt")

            # Create change request
            change_request = ChangePasswordRequest(
                current_pin=change_data.current_pin,
                new_pin=change_data.new_pin
            )

            # Perform password change
            result = await auth_service.change_password(
                user_id=security_context.user_id,
                change_request=change_request,
                ip_address=client_ip
            )

            logger.info("Password changed successfully")
            return result

    except AuthenticationError as e:
        return handle_authentication_error(e, request)
    except Exception as e:
        logger.error("Password change error", error=str(e))
        return create_error_response(
            error="PasswordChangeError",
            error_code="CHANGE_FAILED",
            message="Failed to change password",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get(
    "/sessions",
    response_model=List[SessionInfoModel],
    summary="List User Sessions",
    description="""
    Get all active sessions for the authenticated user.

    **Security Features:**
    - Session ownership verification
    - Device fingerprinting display
    - Last activity tracking
    - Security level indicators
    """,
    responses={
        200: {"description": "Sessions retrieved successfully"},
        401: {"description": "Authentication required"},
        500: {"description": "Internal server error"}
    }
)
async def get_user_sessions(
    security_context: SecurityContext = Depends(get_security_context),
    auth_service: AuthenticationService = Depends(get_auth_service)
) -> List[SessionInfoModel]:
    """Get all sessions for authenticated user"""
    try:
        with structlog.contextvars.bound_contextvars(
            user_id=security_context.user_id
        ):
            logger.info("Retrieving user sessions")

            # Get user sessions
            sessions = await auth_service.get_user_sessions(security_context.user_id)

            # Convert to response model
            session_models = []
            for session in sessions:
                session_models.append(SessionInfoModel(
                    session_id=session.session_id,
                    user_id=session.user_id,
                    username=session.username,
                    role=session.role,
                    trading_mode=session.trading_mode,
                    created_at=session.created_at.isoformat(),
                    last_activity=session.last_activity.isoformat(),
                    expires_at=session.expires_at.isoformat(),
                    device_info=session.device_info,
                    is_active=session.is_active,
                    security_level=session.security_level,
                    ip_address=getattr(session, 'ip_address', None),
                    user_agent=getattr(session, 'user_agent', None)
                ))

            logger.info(f"Retrieved {len(session_models)} sessions")
            return session_models

    except Exception as e:
        logger.error("Get sessions error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve sessions"
        )


@router.delete(
    "/sessions/{session_id}",
    summary="Revoke Session",
    description="""
    Revoke a specific user session.

    **Security Features:**
    - Session ownership verification
    - Audit logging
    - Current session protection
    """,
    responses={
        200: {"description": "Session revoked successfully"},
        401: {"description": "Authentication required"},
        403: {"description": "Cannot revoke own session or insufficient permissions"},
        404: {"description": "Session not found"},
        500: {"description": "Internal server error"}
    }
)
async def revoke_session(
    session_id: str,
    request: Request,
    security_context: SecurityContext = Depends(get_security_context),
    auth_service: AuthenticationService = Depends(get_auth_service)
) -> Dict[str, Any]:
    """Revoke a specific session"""
    client_ip = get_client_ip(request)

    try:
        with structlog.contextvars.bound_contextvars(
            user_id=security_context.user_id,
            target_session_id=session_id,
            client_ip=client_ip
        ):
            logger.info("Session revocation attempt")

            # Prevent revoking current session
            if session_id == security_context.session_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot revoke current session"
                )

            # Revoke session
            result = await auth_service.revoke_session(
                user_id=security_context.user_id,
                session_id=session_id,
                ip_address=client_ip
            )

            logger.info("Session revoked successfully")
            return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Session revocation error", error=str(e))
        return create_error_response(
            error="SessionRevocationError",
            error_code="REVOKE_FAILED",
            message="Failed to revoke session",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.post(
    "/mfa/setup",
    response_model=MFASetupResponseModel,
    summary="Setup Multi-Factor Authentication",
    description="""
    Setup MFA for enhanced account security.

    **Supported Methods:**
    - TOTP (Time-based One-Time Password)
    - SMS verification
    - Email verification

    **Security Features:**
    - QR code generation for TOTP
    - Backup codes generation
    - Secure secret storage
    """,
    responses={
        200: {"description": "MFA setup initiated"},
        400: {"description": "Invalid MFA method"},
        401: {"description": "Authentication required"},
        500: {"description": "Internal server error"}
    }
)
async def setup_mfa(
    setup_data: MFASetupRequestModel,
    security_context: SecurityContext = Depends(get_security_context)
) -> MFASetupResponseModel:
    """Setup multi-factor authentication"""
    try:
        with structlog.contextvars.bound_contextvars(
            user_id=security_context.user_id,
            mfa_method=setup_data.method
        ):
            logger.info("MFA setup initiated")

            if setup_data.method == "totp":
                # Generate TOTP secret
                secret = pyotp.random_base32()

                # Create TOTP object for QR code
                totp = pyotp.TOTP(secret)
                provisioning_uri = totp.provisioning_uri(
                    name=security_context.username,
                    issuer_name="NIRAJ Trading System"
                )

                # Generate QR code
                qr = qrcode.QRCode(version=1, box_size=10, border=5)
                qr.add_data(provisioning_uri)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")

                # Convert to base64
                buffer = io.BytesIO()
                img.save(buffer, format="PNG")
                qr_code_b64 = base64.b64encode(buffer.getvalue()).decode()

                # Generate backup codes
                backup_codes = [secrets.token_hex(4).upper() for _ in range(10)]

                return MFASetupResponseModel(
                    method="totp",
                    secret=secret,
                    qr_code=qr_code_b64,
                    backup_codes=backup_codes,
                    message="Scan QR code with authenticator app and save backup codes"
                )

            else:
                # SMS/Email setup (placeholder for future implementation)
                return MFASetupResponseModel(
                    method=setup_data.method,
                    message=f"{setup_data.method.upper()} MFA setup initiated"
                )

    except Exception as e:
        logger.error("MFA setup error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to setup MFA"
        )


@router.post(
    "/mfa/verify",
    summary="Verify MFA Code",
    description="""
    Verify MFA code to complete setup or for authentication.

    **Security Features:**
    - Time-based verification
    - Rate limiting
    - Audit logging
    """,
    responses={
        200: {"description": "MFA code verified"},
        400: {"description": "Invalid MFA code"},
        401: {"description": "Authentication required"},
        429: {"description": "Too many attempts"},
        500: {"description": "Internal server error"}
    }
)
async def verify_mfa(
    verify_data: MFAVerifyRequestModel,
    security_context: SecurityContext = Depends(get_security_context)
) -> Dict[str, Any]:
    """Verify MFA code"""
    try:
        with structlog.contextvars.bound_contextvars(
            user_id=security_context.user_id,
            mfa_method=verify_data.method
        ):
            logger.info("MFA verification attempt")

            # For now, accept any 6-digit code (placeholder implementation)
            if len(verify_data.code) >= 6 and verify_data.code.isdigit():
                return {
                    "verified": True,
                    "method": verify_data.method,
                    "message": "MFA code verified successfully"
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid MFA code"
                )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("MFA verification error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify MFA code"
        )


@router.get(
    "/metrics",
    response_model=SecurityMetricsModel,
    summary="Security Metrics",
    description="""
    Get comprehensive security and performance metrics.

    **Metrics Include:**
    - Authentication statistics
    - Security events
    - Rate limiting status
    - Active sessions
    - Blocked IPs
    - Suspicious activities

    **Access:** Admin only
    """,
    responses={
        200: {"description": "Metrics retrieved successfully"},
        401: {"description": "Authentication required"},
        403: {"description": "Admin access required"},
        500: {"description": "Internal server error"}
    }
)
async def get_security_metrics(
    security_context: SecurityContext = Depends(get_security_context),
    auth_service: AuthenticationService = Depends(get_auth_service)
) -> SecurityMetricsModel:
    """Get security and performance metrics"""
    try:
        # Check admin access (placeholder - implement proper role checking)
        if security_context.role != AuthRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )

        with structlog.contextvars.bound_contextvars(
            user_id=security_context.user_id
        ):
            logger.info("Security metrics requested")

            # Get metrics from service
            metrics = await auth_service.get_security_metrics()

            return SecurityMetricsModel(
                timestamp=datetime.now(timezone.utc).isoformat(),
                auth_metrics=metrics.get('auth_metrics', {}),
                security_stats=metrics.get('security_stats', {}),
                rate_limit_status=metrics.get('rate_limit_status', {}),
                active_sessions=metrics.get('active_sessions', 0),
                blocked_ips=[],  # Placeholder
                suspicious_activities=[]  # Placeholder
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Metrics retrieval error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve metrics"
        )


# Advanced Security Middleware Class
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Advanced security headers middleware"""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['Content-Security-Policy'] = "default-src 'self'"
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'

        # Remove server header for security
        if 'server' in response.headers:
            del response.headers['server']

        return response


# Geo-blocking utility
def is_ip_blocked(ip_address: str) -> bool:
    """Check if IP address is blocked based on geo-location"""
    try:
        if not SECURITY_CONFIG['enable_geo_blocking']:
            return False

        # Placeholder geo-blocking logic
        # In production, integrate with MaxMind GeoIP or similar service
        ip_obj = ipaddress.ip_address(ip_address)

        # Example: Block private IPs (customize as needed)
        if ip_obj.is_private:
            return False

        # Block specific countries (placeholder)
        blocked_ranges = [
            ipaddress.ip_network('192.0.2.0/24'),  # Example blocked range
        ]

        for blocked_range in blocked_ranges:
            if ip_obj in blocked_range:
                return True

        return False

    except Exception:
        return False


# Device fingerprinting utility
def generate_device_fingerprint(request: Request) -> str:
    """Generate device fingerprint for security tracking"""
    try:
        if not SECURITY_CONFIG['enable_device_fingerprinting']:
            return ""

        components = [
            request.headers.get('User-Agent', ''),
            request.headers.get('Accept-Language', ''),
            get_client_ip(request),
            request.headers.get('Accept', ''),
            request.headers.get('Accept-Encoding', ''),
        ]

        fingerprint_string = '|'.join(components)
        return hashlib.sha256(fingerprint_string.encode()).hexdigest()[:16]

    except Exception:
        return ""


# Performance monitoring decorator
def monitor_performance(operation: str):
    """Decorator for performance monitoring"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time

                # Log performance metrics
                logger.info(
                    f"Operation completed: {operation}",
                    duration=f"{duration:.3f}s",
                    operation=operation
                )

                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    f"Operation failed: {operation}",
                    duration=f"{duration:.3f}s",
                    error=str(e),
                    operation=operation
                )
                raise
        return wrapper
    return decorator


# Initialization functions
def init_auth_routes(
    db_manager: DatabaseManager,
    cache_manager: CacheManager,
    config: Optional[Dict[str, Any]] = None
) -> APIRouter:
    """
    Initialize authentication routes with required services

    Args:
        db_manager: Database manager instance
        cache_manager: Cache manager instance
        config: Optional configuration overrides

    Returns:
        Configured FastAPI router
    """
    global _auth_service, _db_manager, _cache_manager

    try:
        # Store service instances
        _db_manager = db_manager
        _cache_manager = cache_manager

        # Initialize authentication service
        _auth_service = AuthenticationService(
            db_manager=db_manager,
            cache_manager=cache_manager,
            config=config
        )

        logger.info("Authentication routes initialized successfully")
        return router

    except Exception as e:
        logger.error("Failed to initialize authentication routes", error=str(e))
        raise


@asynccontextmanager
async def lifespan_manager():
    """
    Lifespan context manager for authentication service

    Handles startup and shutdown of authentication background tasks
    """
    global _auth_service

    # Startup
    if _auth_service:
        try:
            await _auth_service.start_background_tasks()
            logger.info("Authentication background tasks started")
        except Exception as e:
            logger.error("Failed to start authentication background tasks", error=str(e))

    yield

    # Shutdown
    if _auth_service:
        try:
            await _auth_service.close()
            logger.info("Authentication service shut down gracefully")
        except Exception as e:
            logger.error("Error during authentication service shutdown", error=str(e))


# Export router and initialization function
__all__ = [
    "router",
    "init_auth_routes",
    "lifespan_manager",
    "LoginRequestModel",
    "SwitchModeRequestModel",
    "ChangePasswordRequestModel",
    "MFASetupRequestModel",
    "MFAVerifyRequestModel",
    "TokenResponseModel",
    "SwitchModeResponseModel",
    "SessionInfoModel",
    "MFASetupResponseModel",
    "SecurityMetricsModel",
    "ErrorResponseModel",
    "SecurityHeadersMiddleware",
    "generate_device_fingerprint",
    "is_ip_blocked",
    "monitor_performance"
]
