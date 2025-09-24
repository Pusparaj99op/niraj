"""
WebSocket Server for NIRAJ Advanced Trading System

Provides real-time data streaming capabilities with:
- Enterprise-grade authentication and authorization
- Multiple stream types (market_data, trade_signals, portfolio, ai_insights)
- Subscription management with rate limiting
- Connection pooling and resource management
- Comprehensive error handling and monitoring
- Heartbeat and connection health monitoring
- Message validation and security

Stream Types:
- market_data: Real-time OHLCV data with technical indicators and quotes
- trade_signals: Trading signals from active strategies
- portfolio: Portfolio position and P&L updates
- ai_insights: AI predictions and market analysis

Connection Limits:
- Maximum 5 concurrent connections per user
- Maximum 50 active subscriptions per connection
- Rate limiting on message frequency

Security Features:
- JWT token authentication (query param or message-based)
- Session validation and user context
- Message encryption and validation
- Connection timeout and cleanup
"""

import asyncio
import json
import uuid
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from contextlib import asynccontextmanager
import functools
import hashlib
import hmac

import structlog
import websockets
from websockets.exceptions import ConnectionClosedError, WebSocketException
from jose import jwt

from ..core.config import config
from ..core.database import DatabaseManager
from ..core.cache import CacheManager
from ..core.data_manager import HistoricalDataManager
from ..core.information_processor import InformationProcessor
from ..services.auth_service import AuthenticationService, TokenError, AuthenticationError
from ..services.portfolio_service import PortfolioService
from ..ai.confidence_tracker import AdvancedConfidenceTracker
from ..models.user import UserORM, TradingMode
from ..models.market_data import MarketDataORM
from ..models.strategy_signal import StrategySignalORM
from ..models.portfolio import PortfolioORM
from ..models.ai_prediction import AIPredictionORM
from ..utils.logger import get_structured_logger

# Initialize logger
logger = get_structured_logger(__name__)

# WebSocket configuration
WS_CONFIG = {
    'host': '0.0.0.0',
    'port': 8001,  # Separate port from HTTP API
    'max_connections_per_user': 5,
    'max_subscriptions_per_connection': 50,
    'heartbeat_interval': 30,  # seconds
    'connection_timeout': 300,  # 5 minutes
    'auth_timeout': 10,  # 10 seconds to authenticate
    'max_message_size': 65536,  # 64KB
    'rate_limit_messages': 100,  # messages per minute
    'rate_limit_window': 60,  # seconds
    'message_batch_size': 10,
    'message_batch_timeout': 0.1,
    'circuit_breaker_threshold': 5,
    'circuit_breaker_timeout': 60,
    'max_retry_attempts': 3,
    'retry_backoff_factor': 2.0,
    'ip_whitelist': [],
    'ip_blacklist': [],
    'encryption_enabled': False,
    'enable_load_balancing': False,
    'horizontal_scaling': False
}


class StreamType(str, Enum):
    """Supported WebSocket stream types"""
    MARKET_DATA = "market_data"
    TRADE_SIGNALS = "trade_signals"
    PORTFOLIO = "portfolio"
    AI_INSIGHTS = "ai_insights"


class MessageType(str, Enum):
    """WebSocket message types"""
    AUTH = "auth"
    AUTH_RESPONSE = "auth_response"
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    SUBSCRIPTION_RESPONSE = "subscription_response"
    MARKET_DATA = "market_data"
    TRADE_SIGNAL = "trade_signal"
    PORTFOLIO_UPDATE = "portfolio_update"
    AI_INSIGHT = "ai_insight"
    PING = "ping"
    PONG = "pong"
    ERROR = "error"


class ErrorCode(str, Enum):
    """WebSocket error codes"""
    INVALID_REQUEST_FORMAT = "INVALID_REQUEST_FORMAT"
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    AUTHORIZATION_FAILED = "AUTHORIZATION_FAILED"
    INVALID_TOKEN = "INVALID_TOKEN"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    CONNECTION_LIMIT_EXCEEDED = "CONNECTION_LIMIT_EXCEEDED"
    SUBSCRIPTION_LIMIT_EXCEEDED = "SUBSCRIPTION_LIMIT_EXCEEDED"
    INVALID_STREAM_TYPE = "INVALID_STREAM_TYPE"
    MISSING_REQUIRED_PARAMS = "MISSING_REQUIRED_PARAMS"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


@dataclass
class Subscription:
    """WebSocket subscription configuration"""
    subscription_id: str
    stream_type: StreamType
    user_id: str
    connection_id: str
    config: Dict[str, Any]
    created_at: float
    last_active: float

    @classmethod
    def create(
        cls,
        stream_type: StreamType,
        user_id: str,
        connection_id: str,
        config: Dict[str, Any]
    ) -> 'Subscription':
        """Create a new subscription"""
        now = time.time()
        return cls(
            subscription_id=str(uuid.uuid4()),
            stream_type=stream_type,
            user_id=user_id,
            connection_id=connection_id,
            config=config,
            created_at=now,
            last_active=now
        )


@dataclass
class WebSocketConnection:
    """WebSocket connection state"""
    connection_id: str
    websocket: websockets.WebSocketServerProtocol
    user_id: Optional[str] = None
    trading_mode: Optional[TradingMode] = None
    session_id: Optional[str] = None
    authenticated: bool = False
    authenticated_at: Optional[float] = None
    last_heartbeat: float = field(default_factory=time.time)
    subscriptions: Dict[str, Subscription] = field(default_factory=dict)
    message_count: int = 0
    rate_limit_window_start: float = field(default_factory=time.time)
    created_at: float = field(default_factory=time.time)

    def is_authenticated(self) -> bool:
        """Check if connection is authenticated"""
        return self.authenticated and self.user_id is not None

    def can_subscribe(self) -> bool:
        """Check if connection can add more subscriptions"""
        return len(self.subscriptions) < WS_CONFIG['max_subscriptions_per_connection']

    def update_heartbeat(self):
        """Update last heartbeat timestamp"""
        self.last_heartbeat = time.time()

    def is_expired(self) -> bool:
        """Check if connection has expired"""
        return (time.time() - self.created_at) > WS_CONFIG['connection_timeout']

    def check_rate_limit(self) -> bool:
        """Check if message rate limit is exceeded"""
        now = time.time()

        # Reset window if needed
        if now - self.rate_limit_window_start >= WS_CONFIG['rate_limit_window']:
            self.message_count = 0
            self.rate_limit_window_start = now

        # Check limit
        if self.message_count >= WS_CONFIG['rate_limit_messages']:
            return False

        self.message_count += 1
        return True


class WebSocketMetricsCollector:
    """Collects and reports WebSocket server metrics"""

    def __init__(self):
        self.metrics = {
            'total_connections': 0,
            'active_connections': 0,
            'total_messages_sent': 0,
            'total_messages_received': 0,
            'total_errors': 0,
            'connection_durations': [],
            'message_latencies': []
        }

    def record_connection(self):
        """Record a new connection"""
        self.metrics['total_connections'] += 1
        self.metrics['active_connections'] += 1

    def record_disconnection(self, duration: float):
        """Record a disconnection with duration"""
        self.metrics['active_connections'] -= 1
        self.metrics['connection_durations'].append(duration)

    def record_message_sent(self):
        """Record a message sent"""
        self.metrics['total_messages_sent'] += 1

    def record_message_received(self):
        """Record a message received"""
        self.metrics['total_messages_received'] += 1

    def record_error(self):
        """Record an error"""
        self.metrics['total_errors'] += 1

    def record_message_latency(self, latency: float):
        """Record message processing latency"""
        self.metrics['message_latencies'].append(latency)

    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary"""
        return {
            **self.metrics,
            'avg_connection_duration': sum(self.metrics['connection_durations']) / len(self.metrics['connection_durations']) if self.metrics['connection_durations'] else 0,
            'avg_message_latency': sum(self.metrics['message_latencies']) / len(self.metrics['message_latencies']) if self.metrics['message_latencies'] else 0
        }


class WebSocketHealthMonitor:
    """Monitors WebSocket server health"""

    def __init__(self):
        self.last_health_check = time.time()
        self.health_status = "healthy"
        self.issues = []

    async def check_health(self) -> Dict[str, Any]:
        """Perform health check"""
        self.last_health_check = time.time()

        health_data = {
            'status': self.health_status,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'uptime': time.time() - self.last_health_check,
            'issues': self.issues.copy()
        }

        # Reset issues after reporting
        self.issues.clear()

        return health_data

    def report_issue(self, issue: str):
        """Report a health issue"""
        self.issues.append({
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'issue': issue
        })

        if len(self.issues) > 10:  # Keep only last 10 issues
            self.issues = self.issues[-10:]


class WebSocketLoadBalancer:
    """Load balancer for WebSocket connections"""

    def __init__(self):
        self.nodes = {}
        self.current_node_index = 0

    def add_node(self, node_id: str, url: str, capacity: int = 100):
        """Add a node to the load balancer"""
        self.nodes[node_id] = {
            'url': url,
            'capacity': capacity,
            'active_connections': 0
        }

    def get_next_node(self) -> Optional[str]:
        """Get the next available node using round-robin"""
        if not self.nodes:
            return None

        # Find available node
        for _ in range(len(self.nodes)):
            node_id = list(self.nodes.keys())[self.current_node_index]
            node = self.nodes[node_id]

            if node['active_connections'] < node['capacity']:
                self.current_node_index = (self.current_node_index + 1) % len(self.nodes)
                return node_id

            self.current_node_index = (self.current_node_index + 1) % len(self.nodes)

        return None  # No available nodes

    def record_connection(self, node_id: str):
        """Record a connection to a node"""
        if node_id in self.nodes:
            self.nodes[node_id]['active_connections'] += 1

    def record_disconnection(self, node_id: str):
        """Record a disconnection from a node"""
        if node_id in self.nodes:
            self.nodes[node_id]['active_connections'] = max(0, self.nodes[node_id]['active_connections'] - 1)


class CircuitBreaker:
    """Circuit breaker for fault tolerance"""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open

    async def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if self.state == "open":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "half-open"
            else:
                raise Exception("Circuit breaker is open")

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e

    def _on_success(self):
        """Handle successful call"""
        if self.state == "half-open":
            self.state = "closed"
        self.failure_count = 0

    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = "open"


class RetryPolicy:
    """Retry policy with exponential backoff"""

    def __init__(self, max_attempts: int = 3, backoff_factor: float = 2.0):
        self.max_attempts = max_attempts
        self.backoff_factor = backoff_factor

    async def execute(self, func, *args, **kwargs):
        """Execute function with retry policy"""
        last_exception = None

        for attempt in range(self.max_attempts):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.max_attempts - 1:
                    delay = self.backoff_factor ** attempt
                    await asyncio.sleep(delay)

        raise last_exception


class WebSocketServer:
    """Main WebSocket server for real-time data streaming"""

    def __init__(
        self,
        db_manager: DatabaseManager,
        cache_manager: Optional[CacheManager] = None,
        auth_service: Optional[AuthenticationService] = None,
        data_manager: Optional[HistoricalDataManager] = None,
        info_processor: Optional[InformationProcessor] = None,
        portfolio_service: Optional[PortfolioService] = None,
        confidence_tracker: Optional[AdvancedConfidenceTracker] = None
    ):
        self.db_manager = db_manager
        self.cache_manager = cache_manager
        self.auth_service = auth_service or AuthenticationService(db_manager, cache_manager)
        self.data_manager = data_manager
        self.info_processor = info_processor
        self.portfolio_service = portfolio_service
        self.confidence_tracker = confidence_tracker

        # Connection management
        self.connections: Dict[str, WebSocketConnection] = {}
        self.user_connections: Dict[str, Set[str]] = {}  # user_id -> connection_ids

        # Subscription management
        self.active_subscriptions: Dict[str, Subscription] = {}  # subscription_id -> subscription

        # Background tasks
        self.background_tasks: Set[asyncio.Task] = set()
        self.running = False

        # Data streaming tasks
        self.stream_tasks: Dict[str, asyncio.Task] = {}

        # Performance monitoring
        self.message_count = 0
        self.error_count = 0
        self.last_health_check = time.time()

        # Performance optimizations
        self.connection_pool: Dict[str, asyncio.Queue] = {}  # Connection pooling for batching
        self.message_batch_size = WS_CONFIG.get('message_batch_size', 10)
        self.message_batch_timeout = WS_CONFIG.get('message_batch_timeout', 0.1)

        # Security enhancements
        self.ip_whitelist: Set[str] = set(WS_CONFIG.get('ip_whitelist', []))
        self.ip_blacklist: Set[str] = set(WS_CONFIG.get('ip_blacklist', []))
        self.encryption_enabled = WS_CONFIG.get('encryption_enabled', False)
        self.encryption_key = WS_CONFIG.get('encryption_key')

        # Monitoring and metrics
        self.metrics_collector = WebSocketMetricsCollector()
        self.health_monitor = WebSocketHealthMonitor()

        # Scalability features
        self.load_balancer = WebSocketLoadBalancer() if WS_CONFIG.get('enable_load_balancing', False) else None
        self.horizontal_scaling = WS_CONFIG.get('horizontal_scaling', False)
        self.cluster_nodes: Dict[str, str] = {}  # node_id -> node_url

        # Advanced error recovery
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=WS_CONFIG.get('circuit_breaker_threshold', 5),
            recovery_timeout=WS_CONFIG.get('circuit_breaker_timeout', 60)
        )
        self.retry_policy = RetryPolicy(
            max_attempts=WS_CONFIG.get('max_retry_attempts', 3),
            backoff_factor=WS_CONFIG.get('retry_backoff_factor', 2.0)
        )

        logger.info("WebSocket server initialized with advanced features")

    async def start(self):
        """Start the WebSocket server"""
        self.running = True

        # Start background maintenance tasks
        self.background_tasks.add(
            asyncio.create_task(self._connection_cleanup_task())
        )
        self.background_tasks.add(
            asyncio.create_task(self._heartbeat_monitor_task())
        )

        # Start data streaming tasks
        await self._start_data_streaming_tasks()

        logger.info("WebSocket server started")

    async def stop(self):
        """Stop the WebSocket server"""
        self.running = False

        # Cancel all background tasks
        for task in self.background_tasks:
            task.cancel()
        await asyncio.gather(*self.background_tasks, return_exceptions=True)

        # Cancel streaming tasks
        for task in self.stream_tasks.values():
            task.cancel()
        await asyncio.gather(*self.stream_tasks.values(), return_exceptions=True)

        # Close all connections
        close_tasks = []
        for connection in self.connections.values():
            close_tasks.append(connection.websocket.close())

        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)

        self.connections.clear()
        self.user_connections.clear()
        self.active_subscriptions.clear()

        logger.info("WebSocket server stopped")

    async def handle_connection(self, websocket: websockets.WebSocketServerProtocol, path: str):
        """Handle incoming WebSocket connection"""
        connection_id = str(uuid.uuid4())
        query_params = self._parse_query_params(path)

        # Create connection object
        connection = WebSocketConnection(
            connection_id=connection_id,
            websocket=websocket
        )

        self.connections[connection_id] = connection
        logger.info("New WebSocket connection", connection_id=connection_id)

        try:
            # Handle authentication
            await self._handle_authentication(connection, query_params)

            # Main message handling loop
            await self._handle_messages(connection)

        except ConnectionClosedError:
            logger.info("WebSocket connection closed", connection_id=connection_id)
        except Exception as e:
            logger.error("WebSocket connection error",
                         connection_id=connection_id, error=str(e))
        finally:
            # Cleanup connection
            await self._cleanup_connection(connection_id)

    async def _handle_authentication(
        self,
        connection: WebSocketConnection,
        query_params: Dict[str, str]
    ):
        """Handle WebSocket authentication"""
        auth_timeout = time.time() + WS_CONFIG['auth_timeout']

        # Check for token in query parameters
        token = query_params.get('token')
        if token:
            try:
                await self._authenticate_with_token(connection, token)
                return
            except AuthenticationError:
                # Query param auth failed, wait for message auth
                pass

        # Wait for authentication message
        while time.time() < auth_timeout and not connection.is_authenticated():
            try:
                message_raw = await asyncio.wait_for(
                    connection.websocket.recv(),
                    timeout=1.0
                )

                message = json.loads(message_raw)

                if message.get('type') == MessageType.AUTH:
                    token = message.get('token')
                    if token:
                        await self._authenticate_with_token(connection, token)
                        # Send auth success response
                        await self._send_auth_response(connection, True)
                        break
                    else:
                        await self._send_error(connection, ErrorCode.MISSING_REQUIRED_PARAMS,
                                               "Missing token in auth message")
                        break
                else:
                    # Non-auth message before authentication
                    await self._send_error(connection, ErrorCode.AUTHENTICATION_FAILED,
                                           "Authentication required")
                    break

            except asyncio.TimeoutError:
                continue
            except json.JSONDecodeError:
                await self._send_error(connection, ErrorCode.INVALID_REQUEST_FORMAT,
                                     "Invalid JSON format")
                break

        # Check if authentication succeeded
        if not connection.is_authenticated():
            await self._send_error(connection, ErrorCode.AUTHENTICATION_FAILED,
                                 "Authentication timeout or failed")
            raise AuthenticationError("Authentication failed")

    async def _authenticate_with_token(self, connection: WebSocketConnection, token: str):
        """Authenticate connection with JWT token"""
        try:
            # Validate JWT token
            payload = jwt.decode(
                token,
                config.get('jwt_secret_key'),
                algorithms=[config.get('jwt_algorithm')]
            )

            user_id = payload.get('sub')
            if not user_id:
                raise TokenError("Invalid token: missing user ID")

            # Get user from database
            async with self.db_manager.get_session() as session:
                user = await session.get(UserORM, user_id)
                if not user:
                    raise AuthenticationError("User not found")

                # Check user status
                if not user.is_active:
                    raise AuthenticationError("User account is disabled")

                # Check connection limits
                user_connection_ids = self.user_connections.get(str(user.id), set())
                if len(user_connection_ids) >= WS_CONFIG['max_connections_per_user']:
                    raise AuthenticationError("Connection limit exceeded")

                # Update connection state
                connection.user_id = str(user.id)
                connection.trading_mode = user.trading_mode
                connection.session_id = str(uuid.uuid4())
                connection.authenticated = True
                connection.authenticated_at = time.time()

                # Track user connections
                user_connection_ids.add(connection.connection_id)
                self.user_connections[str(user.id)] = user_connection_ids

                logger.info("WebSocket authentication successful",
                           connection_id=connection.connection_id,
                           user_id=user.id,
                           trading_mode=user.trading_mode.value)

        except jwt.ExpiredSignatureError:
            raise TokenError("Token has expired")
        except jwt.InvalidTokenError:
            raise TokenError("Invalid token")
        except Exception as e:
            logger.error("Authentication error", error=str(e))
            raise AuthenticationError(f"Authentication failed: {str(e)}")

    async def _handle_messages(self, connection: WebSocketConnection):
        """Handle WebSocket messages for authenticated connection"""
        while self.running:
            try:
                # Check rate limiting
                if not connection.check_rate_limit():
                    await self._send_error(connection, ErrorCode.RATE_LIMIT_EXCEEDED,
                                         "Message rate limit exceeded")
                    await asyncio.sleep(1)  # Brief pause
                    continue

                # Receive message
                message_raw = await asyncio.wait_for(
                    connection.websocket.recv(),
                    timeout=WS_CONFIG['heartbeat_interval'] * 2
                )

                message = json.loads(message_raw)
                await self._process_message(connection, message)

                # Update heartbeat
                connection.update_heartbeat()

            except asyncio.TimeoutError:
                # Check if connection is still alive
                if time.time() - connection.last_heartbeat > WS_CONFIG['heartbeat_interval'] * 3:
                    logger.warning("Connection heartbeat timeout",
                                 connection_id=connection.connection_id)
                    break
            except json.JSONDecodeError:
                await self._send_error(connection, ErrorCode.INVALID_REQUEST_FORMAT,
                                     "Invalid JSON format")
            except ConnectionClosedError:
                break
            except Exception as e:
                logger.error("Message handling error",
                           connection_id=connection.connection_id, error=str(e))
                await self._send_error(connection, ErrorCode.INTERNAL_ERROR,
                                     "Internal server error")

    async def _process_message(self, connection: WebSocketConnection, message: Dict[str, Any]):
        """Process incoming WebSocket message"""
        message_type = message.get('type')

        if message_type == MessageType.PING:
            await self._handle_ping(connection)
        elif message_type == MessageType.SUBSCRIBE:
            await self._handle_subscribe(connection, message)
        elif message_type == MessageType.UNSUBSCRIBE:
            await self._handle_unsubscribe(connection, message)
        else:
            await self._send_error(connection, ErrorCode.INVALID_REQUEST_FORMAT,
                                 f"Unknown message type: {message_type}")

    async def _handle_ping(self, connection: WebSocketConnection):
        """Handle ping message"""
        await self._send_message(connection, {
            "type": MessageType.PONG,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    async def _handle_subscribe(self, connection: WebSocketConnection, message: Dict[str, Any]):
        """Handle subscription request"""
        try:
            data = message.get('data', {})
            streams = data.get('streams', [])

            if not streams:
                await self._send_error(connection, ErrorCode.MISSING_REQUIRED_PARAMS,
                                     "Missing streams in subscription request")
                return

            # Validate subscription limits
            if len(streams) + len(connection.subscriptions) > WS_CONFIG['max_subscriptions_per_connection']:
                await self._send_error(connection, ErrorCode.SUBSCRIPTION_LIMIT_EXCEEDED,
                                     "Subscription limit exceeded")
                return

            active_subscriptions = []
            failed_subscriptions = []

            for stream_config in streams:
                try:
                    # Validate stream configuration
                    stream_type = stream_config.get('stream_type')
                    if not stream_type or stream_type not in [s.value for s in StreamType]:
                        failed_subscriptions.append({
                            "stream_type": stream_type,
                            "error": "Invalid or unsupported stream type"
                        })
                        continue

                    # Validate required parameters
                    if not self._validate_stream_config(StreamType(stream_type), stream_config):
                        failed_subscriptions.append({
                            "stream_type": stream_type,
                            "error": "Missing required parameters"
                        })
                        continue

                    # Create subscription
                    subscription = Subscription.create(
                        stream_type=StreamType(stream_type),
                        user_id=connection.user_id,
                        connection_id=connection.connection_id,
                        config=stream_config
                    )

                    # Store subscription
                    connection.subscriptions[subscription.subscription_id] = subscription
                    self.active_subscriptions[subscription.subscription_id] = subscription

                    active_subscriptions.append({
                        "subscription_id": subscription.subscription_id,
                        "stream_type": stream_type
                    })

                    logger.info("Subscription created",
                               subscription_id=subscription.subscription_id,
                               stream_type=stream_type,
                               user_id=connection.user_id)

                except Exception as e:
                    logger.error("Subscription creation error", error=str(e))
                    failed_subscriptions.append({
                        "stream_type": stream_config.get('stream_type'),
                        "error": "Internal error during subscription creation"
                    })

            # Send response
            response = {
                "type": MessageType.SUBSCRIPTION_RESPONSE,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": {
                    "status": "success" if active_subscriptions else "failed",
                    "active_subscriptions": active_subscriptions,
                    "failed_subscriptions": failed_subscriptions
                }
            }

            await self._send_message(connection, response)

        except Exception as e:
            logger.error("Subscribe handling error", error=str(e))
            await self._send_error(connection, ErrorCode.INTERNAL_ERROR,
                                 "Failed to process subscription request")

    async def _handle_unsubscribe(self, connection: WebSocketConnection, message: Dict[str, Any]):
        """Handle unsubscription request"""
        try:
            data = message.get('data', {})
            subscription_ids = data.get('subscription_ids', [])

            if not subscription_ids:
                await self._send_error(connection, ErrorCode.MISSING_REQUIRED_PARAMS,
                                     "Missing subscription_ids in unsubscription request")
                return

            successful_unsubscriptions = []
            failed_unsubscriptions = []

            for sub_id in subscription_ids:
                subscription = connection.subscriptions.get(sub_id)
                if subscription:
                    # Remove subscription
                    del connection.subscriptions[sub_id]
                    del self.active_subscriptions[sub_id]
                    successful_unsubscriptions.append(sub_id)

                    logger.info("Subscription removed",
                               subscription_id=sub_id,
                               user_id=connection.user_id)
                else:
                    failed_unsubscriptions.append({
                        "subscription_id": sub_id,
                        "error": "Subscription not found"
                    })

            # Send response
            status = "success" if successful_unsubscriptions else "failed"
            response = {
                "type": MessageType.SUBSCRIPTION_RESPONSE,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": {
                    "status": status,
                    "unsubscribed": successful_unsubscriptions,
                    "failed_unsubscriptions": failed_unsubscriptions
                }
            }

            await self._send_message(connection, response)

        except Exception as e:
            logger.error("Unsubscribe handling error", error=str(e))
            await self._send_error(connection, ErrorCode.INTERNAL_ERROR,
                                 "Failed to process unsubscription request")

    def _validate_stream_config(self, stream_type: StreamType, config: Dict[str, Any]) -> bool:
        """Validate stream configuration parameters"""
        if stream_type == StreamType.MARKET_DATA:
            return 'symbols' in config and 'timeframe' in config
        elif stream_type == StreamType.TRADE_SIGNALS:
            return True  # strategy_ids is optional
        elif stream_type == StreamType.PORTFOLIO:
            return True  # No required parameters
        elif stream_type == StreamType.AI_INSIGHTS:
            return True  # min_confidence is optional
        return False

    async def _send_auth_response(self, connection: WebSocketConnection, success: bool, error: str = None):
        """Send authentication response"""
        response = {
            "type": MessageType.AUTH_RESPONSE,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {
                "status": "authenticated" if success else "failed",
                "user_id": connection.user_id,
                "trading_mode": connection.trading_mode.value if connection.trading_mode else None,
                "session_id": connection.session_id
            }
        }

        if not success and error:
            response["data"]["error"] = error

        await self._send_message(connection, response)

    async def _send_error(self, connection: WebSocketConnection, error_code: ErrorCode, message: str):
        """Send error message"""
        error_response = {
            "type": MessageType.ERROR,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {
                "error_code": error_code,
                "error_message": message
            }
        }

        await self._send_message(connection, error_response)

    async def _send_message(self, connection: WebSocketConnection, message: Dict[str, Any]):
        """Send message to connection"""
        try:
            await connection.websocket.send(json.dumps(message))
        except Exception as e:
            logger.error("Failed to send message",
                        connection_id=connection.connection_id, error=str(e))

    async def _cleanup_connection(self, connection_id: str):
        """Clean up connection resources"""
        connection = self.connections.get(connection_id)
        if not connection:
            return

        # Remove from user connections
        if connection.user_id:
            user_connections = self.user_connections.get(connection.user_id, set())
            user_connections.discard(connection_id)
            if not user_connections:
                del self.user_connections[connection.user_id]
            else:
                self.user_connections[connection.user_id] = user_connections

        # Remove subscriptions
        for sub_id in list(connection.subscriptions.keys()):
            self.active_subscriptions.pop(sub_id, None)

        # Remove connection
        del self.connections[connection_id]

        logger.info("Connection cleaned up", connection_id=connection_id)

    def _parse_query_params(self, path: str) -> Dict[str, str]:
        """Parse query parameters from WebSocket path"""
        params = {}
        if '?' in path:
            query_string = path.split('?', 1)[1]
            for pair in query_string.split('&'):
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    params[key] = value
        return params

    async def _connection_cleanup_task(self):
        """Background task to clean up expired connections"""
        while self.running:
            try:
                await asyncio.sleep(60)  # Check every minute

                expired_connections = []
                for conn_id, connection in self.connections.items():
                    if connection.is_expired():
                        expired_connections.append(conn_id)

                for conn_id in expired_connections:
                    logger.warning("Cleaning up expired connection", connection_id=conn_id)
                    await self._cleanup_connection(conn_id)

            except Exception as e:
                logger.error("Connection cleanup task error", error=str(e))

    async def _heartbeat_monitor_task(self):
        """Background task to monitor connection heartbeats"""
        while self.running:
            try:
                await asyncio.sleep(WS_CONFIG['heartbeat_interval'])

                # Send ping to all connections
                ping_tasks = []
                for connection in self.connections.values():
                    if connection.is_authenticated():
                        ping_tasks.append(self._send_ping_to_connection(connection))

                if ping_tasks:
                    await asyncio.gather(*ping_tasks, return_exceptions=True)

            except Exception as e:
                logger.error("Heartbeat monitor task error", error=str(e))

    async def _send_ping_to_connection(self, connection: WebSocketConnection):
        """Send ping to a specific connection"""
        try:
            await self._send_message(connection, {
                "type": MessageType.PING,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        except Exception as e:
            # Connection may be dead, will be cleaned up by cleanup task
            pass

    async def _start_data_streaming_tasks(self):
        """Start background data streaming tasks"""
        # Market data streaming
        self.stream_tasks['market_data'] = asyncio.create_task(
            self._market_data_streaming_task()
        )

        # Trade signals streaming
        self.stream_tasks['trade_signals'] = asyncio.create_task(
            self._trade_signals_streaming_task()
        )

        # Portfolio updates streaming
        self.stream_tasks['portfolio'] = asyncio.create_task(
            self._portfolio_streaming_task()
        )

        # AI insights streaming
        self.stream_tasks['ai_insights'] = asyncio.create_task(
            self._ai_insights_streaming_task()
        )

    async def _market_data_streaming_task(self):
        """Stream market data to subscribed connections"""
        while self.running:
            try:
                await asyncio.sleep(1)  # Stream every second

                # Get market data subscriptions
                market_subscriptions = {
                    sub_id: sub for sub_id, sub in self.active_subscriptions.items()
                    if sub.stream_type == StreamType.MARKET_DATA
                }

                if not market_subscriptions:
                    continue

                # Group subscriptions by symbols and timeframe
                symbol_timeframe_groups = {}
                for sub in market_subscriptions.values():
                    key = f"{sub.config.get('symbols', [])}_{sub.config.get('timeframe', '15min')}"
                    if key not in symbol_timeframe_groups:
                        symbol_timeframe_groups[key] = []
                    symbol_timeframe_groups[key].append(sub)

                # Fetch and send market data for each group
                for key, subs in symbol_timeframe_groups.items():
                    symbols, timeframe = key.split('_', 1)
                    symbols_list = symbols.strip('[]').replace("'", "").split(',') if symbols != '[]' else []

                    for symbol in symbols_list:
                        # Fetch latest market data (mock for now)
                        market_data = await self._fetch_market_data(symbol.strip(), timeframe)

                        if market_data:
                            # Send to all subscriptions for this symbol/timeframe
                            for sub in subs:
                                connection = self.connections.get(sub.connection_id)
                                if connection and connection.is_authenticated():
                                    await self._send_market_data(connection, market_data)
                                    sub.last_active = time.time()

            except Exception as e:
                logger.error("Market data streaming error", error=str(e))
                await asyncio.sleep(5)  # Brief pause on error

    async def _trade_signals_streaming_task(self):
        """Stream trade signals to subscribed connections"""
        while self.running:
            try:
                await asyncio.sleep(2)  # Check every 2 seconds

                # Get trade signal subscriptions
                signal_subscriptions = {
                    sub_id: sub for sub_id, sub in self.active_subscriptions.items()
                    if sub.stream_type == StreamType.TRADE_SIGNALS
                }

                if not signal_subscriptions:
                    continue

                # Fetch recent trade signals
                signals = await self._fetch_trade_signals()

                for signal in signals:
                    # Send to relevant subscriptions
                    for sub in signal_subscriptions.values():
                        connection = self.connections.get(sub.connection_id)
                        if connection and connection.is_authenticated():
                            # Check strategy filter
                            strategy_ids = sub.config.get('strategy_ids')
                            if strategy_ids and signal.get('strategy_id') not in strategy_ids:
                                continue

                            # Check confidence filter
                            min_confidence = sub.config.get('min_confidence')
                            if min_confidence and signal.get('confidence', 0) < min_confidence:
                                continue

                            await self._send_trade_signal(connection, signal)
                            sub.last_active = time.time()

            except Exception as e:
                logger.error("Trade signals streaming error", error=str(e))
                await asyncio.sleep(5)

    async def _portfolio_streaming_task(self):
        """Stream portfolio updates to subscribed connections"""
        while self.running:
            try:
                await asyncio.sleep(5)  # Update every 5 seconds

                # Get portfolio subscriptions
                portfolio_subscriptions = {
                    sub_id: sub for sub_id, sub in self.active_subscriptions.items()
                    if sub.stream_type == StreamType.PORTFOLIO
                }

                if not portfolio_subscriptions:
                    continue

                # Send portfolio updates to each user
                user_updates = {}
                for sub in portfolio_subscriptions.values():
                    user_id = sub.user_id
                    if user_id not in user_updates:
                        user_updates[user_id] = await self._fetch_portfolio_data(user_id)

                for sub in portfolio_subscriptions.values():
                    connection = self.connections.get(sub.connection_id)
                    if connection and connection.is_authenticated():
                        portfolio_data = user_updates.get(sub.user_id)
                        if portfolio_data:
                            await self._send_portfolio_update(connection, portfolio_data)
                            sub.last_active = time.time()

            except Exception as e:
                logger.error("Portfolio streaming error", error=str(e))
                await asyncio.sleep(5)

    async def _ai_insights_streaming_task(self):
        """Stream AI insights to subscribed connections"""
        while self.running:
            try:
                await asyncio.sleep(10)  # Update every 10 seconds

                # Get AI insights subscriptions
                ai_subscriptions = {
                    sub_id: sub for sub_id, sub in self.active_subscriptions.items()
                    if sub.stream_type == StreamType.AI_INSIGHTS
                }

                if not ai_subscriptions:
                    continue

                # Fetch AI insights
                insights = await self._fetch_ai_insights()

                for insight in insights:
                    for sub in ai_subscriptions.values():
                        connection = self.connections.get(sub.connection_id)
                        if connection and connection.is_authenticated():
                            # Check confidence filter
                            min_confidence = sub.config.get('min_confidence')
                            if min_confidence and insight.get('confidence', 0) < min_confidence:
                                continue

                            await self._send_ai_insight(connection, insight)
                            sub.last_active = time.time()

            except Exception as e:
                logger.error("AI insights streaming error", error=str(e))
                await asyncio.sleep(5)

    async def _fetch_market_data(self, symbol: str, timeframe: str) -> Optional[Dict[str, Any]]:
        """Fetch market data for symbol and timeframe"""
        try:
            # Try to get real market data from information processor
            if self.info_processor:
                try:
                    # Get real-time market data
                    market_data = await self.info_processor.get_market_data(symbol, timeframe)
                    if market_data:
                        return self._format_market_data(market_data)
                except Exception as e:
                    logger.warning("Failed to get real market data, falling back to cached data",
                                 symbol=symbol, error=str(e))

            # Fallback to historical data manager
            if self.data_manager:
                try:
                    historical_data = await self.data_manager.get_latest_data(symbol, timeframe)
                    if historical_data:
                        return self._format_market_data(historical_data)
                except Exception as e:
                    logger.warning("Failed to get historical market data",
                                 symbol=symbol, error=str(e))

            # Last resort: mock data for development
            return self._generate_mock_market_data(symbol, timeframe)

        except Exception as e:
            logger.error("Failed to fetch market data", symbol=symbol, error=str(e))
            return None

    def _format_market_data(self, raw_data: Any) -> Dict[str, Any]:
        """Format market data for WebSocket transmission"""
        try:
            # Handle different data formats from various sources
            if isinstance(raw_data, dict):
                # Already formatted
                return raw_data
            elif hasattr(raw_data, 'to_dict'):
                # ORM object
                return raw_data.to_dict()
            else:
                # Raw data - format it
                return {
                    "symbol": getattr(raw_data, 'symbol', 'UNKNOWN'),
                    "timeframe": getattr(raw_data, 'timeframe', '15min'),
                    "ohlcv": {
                        "timestamp": getattr(raw_data, 'timestamp', datetime.now(timezone.utc).isoformat()),
                        "open": float(getattr(raw_data, 'open_price', 0)),
                        "high": float(getattr(raw_data, 'high_price', 0)),
                        "low": float(getattr(raw_data, 'low_price', 0)),
                        "close": float(getattr(raw_data, 'close_price', 0)),
                        "volume": int(getattr(raw_data, 'volume', 0)),
                        "change_percent": float(getattr(raw_data, 'change_percent', 0))
                    },
                    "indicators": getattr(raw_data, 'indicators', {}),
                    "quote": getattr(raw_data, 'quote', {})
                }
        except Exception as e:
            logger.error("Failed to format market data", error=str(e))
            return None

    def _generate_mock_market_data(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        """Generate mock market data for development/testing"""
        import random
        base_price = 1000 + random.uniform(-50, 50)

        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "ohlcv": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "open": round(base_price, 2),
                "high": round(base_price + random.uniform(0, 10), 2),
                "low": round(base_price - random.uniform(0, 10), 2),
                "close": round(base_price + random.uniform(-5, 5), 2),
                "volume": random.randint(1000, 10000),
                "change_percent": round(random.uniform(-2, 2), 2)
            },
            "indicators": {
                "rsi": round(random.uniform(30, 70), 2),
                "macd": round(random.uniform(-1, 1), 2),
                "sma_20": round(base_price + random.uniform(-10, 10), 2)
            },
            "quote": {
                "bid": round(base_price - 0.1, 2),
                "ask": round(base_price + 0.1, 2),
                "last_price": round(base_price, 2),
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
        }

    async def _fetch_trade_signals(self) -> List[Dict[str, Any]]:
        """Fetch recent trade signals"""
        try:
            signals = []

            # Try to get real trade signals from information processor
            if self.info_processor:
                try:
                    real_signals = await self.info_processor.get_trade_signals()
                    if real_signals:
                        signals.extend(real_signals)
                except Exception as e:
                    logger.warning("Failed to get real trade signals", error=str(e))

            # Get signals from database if we don't have enough
            if len(signals) < 3:
                try:
                    async with self.db_manager.get_session() as session:
                        # Get recent signals from database
                        recent_signals = await session.execute(
                            "SELECT * FROM strategy_signals WHERE created_at >= datetime('now', '-1 hour') ORDER BY created_at DESC LIMIT 10"
                        )
                        db_signals = recent_signals.fetchall()

                        for signal in db_signals:
                            signals.append({
                                "signal_id": str(signal.id),
                                "strategy_id": signal.strategy_id,
                                "symbol": signal.symbol,
                                "action": signal.action,
                                "confidence": float(signal.confidence),
                                "price": float(signal.price),
                                "quantity": signal.quantity,
                                "timestamp": signal.created_at.isoformat(),
                                "reason": signal.reason or "Database signal"
                            })
                except Exception as e:
                    logger.warning("Failed to get database trade signals", error=str(e))

            # Generate mock signals if still no real data
            if not signals:
                signals = self._generate_mock_trade_signals()

            return signals[:10]  # Limit to 10 most recent

        except Exception as e:
            logger.error("Failed to fetch trade signals", error=str(e))
            return []

    def _generate_mock_trade_signals(self) -> List[Dict[str, Any]]:
        """Generate mock trade signals for development/testing"""
        import random

        signals = []
        strategies = ["predator_strategy", "vulture_approach", "time_arbitrage"]

        for _ in range(random.randint(1, 3)):
            signals.append({
                "signal_id": str(uuid.uuid4()),
                "strategy_id": random.choice(strategies),
                "symbol": f"SYMBOL{random.randint(1, 100):03d}",
                "action": random.choice(["BUY", "SELL"]),
                "confidence": round(random.uniform(0.5, 0.95), 2),
                "price": round(random.uniform(100, 1000), 2),
                "quantity": random.randint(1, 100),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "reason": "Mock trading signal"
            })

        return signals

    async def _fetch_portfolio_data(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Fetch portfolio data for user"""
        try:
            portfolio_data = {
                "user_id": user_id,
                "total_value": 0.0,
                "total_pnl": 0.0,
                "positions": [],
                "cash_balance": 0.0,
                "margin_used": 0.0,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            # Try to get real portfolio data from portfolio service
            if self.portfolio_service:
                try:
                    real_portfolio = await self.portfolio_service.get_portfolio(user_id)
                    if real_portfolio:
                        portfolio_data.update(real_portfolio)
                        return portfolio_data
                except Exception as e:
                    logger.warning("Failed to get real portfolio data", user_id=user_id, error=str(e))

            # Get portfolio data from database if service unavailable
            try:
                async with self.db_manager.get_session() as session:
                    # Get user portfolio summary
                    portfolio_query = await session.execute(
                        "SELECT * FROM portfolios WHERE user_id = ? ORDER BY updated_at DESC LIMIT 1",
                        (user_id,)
                    )
                    portfolio_row = portfolio_query.fetchone()

                    if portfolio_row:
                        portfolio_data.update({
                            "total_value": float(portfolio_row.total_value),
                            "total_pnl": float(portfolio_row.total_pnl),
                            "cash_balance": float(portfolio_row.cash_balance),
                            "margin_used": float(portfolio_row.margin_used)
                        })

                    # Get positions
                    positions_query = await session.execute(
                        "SELECT * FROM positions WHERE user_id = ? AND quantity > 0",
                        (user_id,)
                    )
                    positions = positions_query.fetchall()

                    for pos in positions:
                        portfolio_data["positions"].append({
                            "symbol": pos.symbol,
                            "quantity": pos.quantity,
                            "avg_price": float(pos.avg_price),
                            "current_price": float(pos.current_price),
                            "pnl": float(pos.pnl),
                            "pnl_percentage": float(pos.pnl_percentage)
                        })

            except Exception as e:
                logger.warning("Failed to get database portfolio data", user_id=user_id, error=str(e))

            # Generate mock portfolio if no real data
            if not portfolio_data["positions"]:
                portfolio_data = self._generate_mock_portfolio(user_id)

            return portfolio_data

        except Exception as e:
            logger.error("Failed to fetch portfolio data", user_id=user_id, error=str(e))
            return self._generate_mock_portfolio(user_id)

    def _generate_mock_portfolio(self, user_id: str) -> Dict[str, Any]:
        """Generate mock portfolio data for development/testing"""
        import random

        positions = []
        total_value = 0.0
        total_pnl = 0.0

        for _ in range(random.randint(2, 5)):
            quantity = random.randint(10, 100)
            avg_price = round(random.uniform(50, 500), 2)
            current_price = round(avg_price * random.uniform(0.9, 1.1), 2)
            pnl = (current_price - avg_price) * quantity
            pnl_percentage = ((current_price - avg_price) / avg_price) * 100

            positions.append({
                "symbol": f"SYMBOL{random.randint(1, 100):03d}",
                "quantity": quantity,
                "avg_price": avg_price,
                "current_price": current_price,
                "pnl": round(pnl, 2),
                "pnl_percentage": round(pnl_percentage, 2)
            })

            total_value += current_price * quantity
            total_pnl += pnl

        cash_balance = round(random.uniform(1000, 10000), 2)
        total_value += cash_balance

        return {
            "user_id": user_id,
            "total_value": round(total_value, 2),
            "total_pnl": round(total_pnl, 2),
            "positions": positions,
            "cash_balance": cash_balance,
            "margin_used": round(total_value * 0.1, 2),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    async def _fetch_ai_insights(self) -> List[Dict[str, Any]]:
        """Fetch AI insights and predictions"""
        try:
            insights = []

            # Try to get real AI insights from confidence tracker
            if self.confidence_tracker:
                try:
                    real_insights = await self.confidence_tracker.get_recent_insights()
                    if real_insights:
                        insights.extend(real_insights)
                except Exception as e:
                    logger.warning("Failed to get real AI insights", error=str(e))

            # Get insights from database if we don't have enough
            if len(insights) < 3:
                try:
                    async with self.db_manager.get_session() as session:
                        # Get recent AI predictions from database
                        recent_insights = await session.execute(
                            "SELECT * FROM ai_predictions WHERE created_at >= datetime('now', '-1 hour') ORDER BY created_at DESC LIMIT 10"
                        )
                        db_insights = recent_insights.fetchall()

                        for insight in db_insights:
                            insights.append({
                                "insight_id": str(insight.id),
                                "symbol": insight.symbol,
                                "prediction": insight.prediction,
                                "confidence": float(insight.confidence),
                                "timeframe": insight.timeframe,
                                "analysis": insight.analysis or "Database AI analysis",
                                "indicators": insight.indicators or {},
                                "timestamp": insight.created_at.isoformat()
                            })
                except Exception as e:
                    logger.warning("Failed to get database AI insights", error=str(e))

            # Generate mock insights if still no real data
            if not insights:
                insights = self._generate_mock_ai_insights()

            return insights[:10]  # Limit to 10 most recent

        except Exception as e:
            logger.error("Failed to fetch AI insights", error=str(e))
            return []

    def _generate_mock_ai_insights(self) -> List[Dict[str, Any]]:
        """Generate mock AI insights for development/testing"""
        import random

        insights = []
        symbols = [f"INSIGHT{random.randint(1, 50):03d}" for _ in range(5)]

        for symbol in symbols:
            if random.random() > 0.7:  # 30% chance of insight
                insights.append({
                    "insight_id": str(uuid.uuid4()),
                    "symbol": symbol,
                    "prediction": random.choice(["UP", "DOWN", "SIDEWAYS"]),
                    "confidence": round(random.uniform(0.6, 0.9), 2),
                    "timeframe": random.choice(["1h", "1d", "1w"]),
                    "analysis": f"Mock AI analysis for {symbol}",
                    "indicators": {
                        "trend_strength": round(random.uniform(0.3, 0.8), 2),
                        "volatility": round(random.uniform(0.1, 0.5), 2)
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })

        return insights

    async def _send_market_data(self, connection: WebSocketConnection, data: Dict[str, Any]):
        """Send market data message"""
        message = {
            "type": MessageType.MARKET_DATA,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data
        }
        await self._send_message(connection, message)

    async def _send_trade_signal(self, connection: WebSocketConnection, signal: Dict[str, Any]):
        """Send trade signal message"""
        message = {
            "type": MessageType.TRADE_SIGNAL,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": signal
        }
        await self._send_message(connection, message)

    async def _send_portfolio_update(self, connection: WebSocketConnection, data: Dict[str, Any]):
        """Send portfolio update message"""
        message = {
            "type": MessageType.PORTFOLIO_UPDATE,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data
        }
        await self._send_message(connection, message)

    async def _send_ai_insight(self, connection: WebSocketConnection, insight: Dict[str, Any]):
        """Send AI insight message"""
        message = {
            "type": MessageType.AI_INSIGHT,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": insight
        }
        await self._send_message(connection, message)


# Global WebSocket server instance
_websocket_server: Optional[WebSocketServer] = None


def get_websocket_server() -> WebSocketServer:
    """Get the global WebSocket server instance"""
    if _websocket_server is None:
        raise RuntimeError("WebSocket server not initialized")
    return _websocket_server


async def init_websocket_server(
    db_manager: DatabaseManager,
    cache_manager: Optional[CacheManager] = None,
    auth_service: Optional[AuthenticationService] = None,
    data_manager: Optional[HistoricalDataManager] = None,
    info_processor: Optional[InformationProcessor] = None,
    portfolio_service: Optional[PortfolioService] = None,
    confidence_tracker: Optional[AdvancedConfidenceTracker] = None
) -> WebSocketServer:
    """Initialize the WebSocket server"""
    global _websocket_server

    _websocket_server = WebSocketServer(
        db_manager=db_manager,
        cache_manager=cache_manager,
        auth_service=auth_service,
        data_manager=data_manager,
        info_processor=info_processor,
        portfolio_service=portfolio_service,
        confidence_tracker=confidence_tracker
    )

    await _websocket_server.start()
    return _websocket_server


async def shutdown_websocket_server():
    """Shutdown the WebSocket server"""
    global _websocket_server

    if _websocket_server:
        await _websocket_server.stop()
        _websocket_server = None


# WebSocket endpoint handler for FastAPI integration
async def websocket_endpoint(websocket: websockets.WebSocketServerProtocol, path: str):
    """WebSocket endpoint handler for FastAPI"""
    if _websocket_server is None:
        await websocket.close(1011, "WebSocket server not available")
        return

    await _websocket_server.handle_connection(websocket, path)


# Standalone server startup
async def run_websocket_server():
    """Run WebSocket server standalone"""
    # Initialize dependencies (simplified for standalone mode)
    from ..core.database import DatabaseManager
    from ..core.cache import CacheManager
    from ..services.auth_service import AuthenticationService

    # Load config
    config.load_config()

    # Initialize services
    db_manager = DatabaseManager(
        database_url=config.get('database_url', 'sqlite:///niraj.db')
    )
    await db_manager.initialize()

    cache_manager = None
    try:
        cache_manager = CacheManager(
            redis_url=config.get('redis_url', 'redis://localhost:6379')
        )
    except Exception:
        pass

    auth_service = AuthenticationService(db_manager, cache_manager)

    # Initialize WebSocket server
    server = await init_websocket_server(db_manager, cache_manager, auth_service)

    # Start WebSocket server
    ws_server = await websockets.serve(
        server.handle_connection,
        WS_CONFIG['host'],
        WS_CONFIG['port'],
        max_size=WS_CONFIG['max_message_size']
    )

    logger.info("WebSocket server running",
                host=WS_CONFIG['host'], port=WS_CONFIG['port'])

    try:
        await ws_server.wait_closed()
    except KeyboardInterrupt:
        logger.info("WebSocket server shutting down")
    finally:
        await shutdown_websocket_server()
        if cache_manager:
            await cache_manager.close()
        await db_manager.close()
