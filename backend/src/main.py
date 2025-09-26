"""
NIRAJ Advanced Trading System - Main FastAPI Application

Comprehensive algorithmic trading platform with AI-powered strategies,
enterprise-grade security, and real-time execution capabilities.

Features:
- Advanced authentication and authorization
- Strategy management and backtesting
- Real-time market data processing
- AI-powered trading signals
- Risk management and execution
- Comprehensive monitoring and logging
- Enterprise security features

API Versions:
- v1: Current stable API
"""

import asyncio
import os
from contextlib import asynccontextmanager
from typing import Optional, Any

from fastapi import FastAPI, Request, status, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import structlog
import uvicorn

from .core.config import config
from .core.database import DatabaseManager
try:
    from .core.cache import CacheManager
    CACHE_AVAILABLE = True
except ImportError:
    CacheManager = None
    CACHE_AVAILABLE = False
try:
    from .ai.gemma3_integration import Gemma3Client
    AI_AVAILABLE = True
except ImportError:
    Gemma3Client = None
    AI_AVAILABLE = False
try:
    from .api.websocket_server import init_websocket_server, shutdown_websocket_server
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
from .api.routes.auth import init_auth_routes, SecurityHeadersMiddleware
from .api.routes.strategies import init_strategy_routes
from .api.routes.trades import init_trade_routes
from .api.routes.portfolio import init_portfolio_routes
from .api.routes.system import init_system_routes
from .api.routes.market_data import init_market_data_routes
from .api.routes.news import init_news_routes
from .api.routes.weather import init_weather_routes
from .api.routes.ai_analysis import init_ai_routes
from .api.routes.technical_indicators import init_indicators_routes

# Configure structured logging
logger = structlog.get_logger(__name__)

# Global service instances
_db_manager: Optional[DatabaseManager] = None
_cache_manager: Optional[Any] = None
_ai_integration: Optional[Any] = None
_websocket_server: Optional[Any] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager

    Handles startup and shutdown of services and background tasks
    """
    logger.info("Starting NIRAJ Trading System")

    try:
        # Initialize remaining async services
        await initialize_services()

        # Start background tasks
        await start_background_tasks()

        logger.info("NIRAJ Trading System started successfully")

    except Exception as e:
        logger.error("Failed to start NIRAJ Trading System", error=str(e))
        raise

    yield

    # Shutdown
    logger.info("Shutting down NIRAJ Trading System")

    try:
        await shutdown_services()
        logger.info("NIRAJ Trading System shut down gracefully")

    except Exception as e:
        logger.error("Error during shutdown", error=str(e))


async def initialize_services():
    """Initialize all core services"""
    global _db_manager, _cache_manager, _ai_integration, _websocket_server

    try:
        # Services are already initialized in create_application()
        # Only initialize WebSocket server here

        # Initialize WebSocket server
        if WEBSOCKET_AVAILABLE and _db_manager:
            try:
                from .services.auth_service import AuthenticationService
                auth_service = AuthenticationService(_db_manager, _cache_manager)
                _websocket_server = await init_websocket_server(
                    _db_manager, _cache_manager, auth_service
                )
                logger.info("WebSocket server initialized")
            except Exception as e:
                logger.warning("WebSocket server not available", error=str(e))
                _websocket_server = None
        else:
            logger.warning("WebSocket server not available - websockets not installed or db_manager not ready")
            _websocket_server = None

        logger.info("Core services initialized successfully")

    except Exception as e:
        logger.error("Failed to initialize services", error=str(e))
        raise


async def start_background_tasks():
    """Start all background tasks and services"""
    try:
        # Start database maintenance tasks
        if _db_manager and hasattr(_db_manager, 'start_background_tasks'):
            await _db_manager.start_background_tasks()

        # Start cache maintenance tasks
        if _cache_manager and hasattr(_cache_manager, 'start_background_tasks'):
            await _cache_manager.start_background_tasks()

        # Start AI background tasks
        if _ai_integration and hasattr(_ai_integration, 'start_background_tasks'):
            await _ai_integration.start_background_tasks()

        logger.info("Background tasks started successfully")

    except Exception as e:
        logger.error("Failed to start background tasks", error=str(e))
        raise


async def shutdown_services():
    """Shutdown all services gracefully"""
    try:
        # Shutdown AI integration
        if _ai_integration:
            await _ai_integration.close()

        # Shutdown WebSocket server
        if _websocket_server:
            await shutdown_websocket_server()

        # Shutdown cache manager
        if _cache_manager:
            await _cache_manager.close()

        # Shutdown database manager
        if _db_manager:
            await _db_manager.close()

        logger.info("Services shut down gracefully")

    except Exception as e:
        logger.error("Error during service shutdown", error=str(e))


def create_application() -> FastAPI:
    """
    Create and configure the FastAPI application

    Returns:
        Configured FastAPI application instance
    """
    # Load configuration
    config.load_config()

    # Initialize core services here instead of in lifespan
    global _db_manager, _cache_manager, _ai_integration, _websocket_server

    try:
        # Load configuration
        config.load_config()

        # Initialize database manager
        _db_manager = DatabaseManager()
        # Note: Database URL is configured via environment/config files
        if hasattr(_db_manager, 'initialize'):
            # Cannot use asyncio.run here as we're not in sync context
            pass

        # Initialize cache manager
        if CACHE_AVAILABLE:
            _cache_manager = CacheManager(
                redis_url=config.get('redis_url', 'redis://localhost:6379')
            )
        else:
            logger.warning("Cache manager not available - Redis not installed")
            _cache_manager = None

        # Initialize AI integration (optional)
        try:
            _ai_integration = Gemma3Client()
            logger.info("AI integration initialized")
        except Exception as e:
            logger.warning("AI integration not available", error=str(e))
            _ai_integration = None

        # Initialize WebSocket server
        if WEBSOCKET_AVAILABLE:
            try:
                _websocket_server = None  # Cannot initialize websocket here without async
                logger.info("WebSocket server will be initialized in lifespan")
            except Exception as e:
                logger.warning("WebSocket server not available", error=str(e))
                _websocket_server = None
        else:
            logger.warning("WebSocket server not available - websockets not installed")
            _websocket_server = None

        logger.info("Core services initialized successfully")

    except Exception as e:
        logger.error("Failed to initialize services", error=str(e))
        raise

    # Create FastAPI app
    app = FastAPI(
        title="NIRAJ Advanced Trading System API",
        description="""
        Enterprise-grade algorithmic trading platform with AI-powered strategies.

        ## Features

        * **Advanced Authentication**: Multi-factor authentication, session management, enterprise security
        * **Strategy Management**: Create, update, delete, and backtest trading strategies
        * **AI Integration**: Gemma3-powered trading signals and market analysis
        * **Real-time Processing**: WebSocket connections for live market data
        * **Risk Management**: Comprehensive risk controls and position sizing
        * **Performance Analytics**: Detailed backtesting and performance metrics

        ## API Versions

        * **v1** (current): Stable production API
        """,
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.get('cors_origins', ["http://localhost:3000"]),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # Add trusted host middleware
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=config.get('trusted_hosts', ["*"])
    )

    # Add security headers middleware
    app.add_middleware(SecurityHeadersMiddleware)

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Global exception handler for unhandled errors"""
        logger.error(
            "Unhandled exception",
            error=str(exc),
            error_type=type(exc).__name__,
            path=request.url.path,
            method=request.method
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "InternalServerError",
                "message": "An unexpected error occurred",
                "path": request.url.path
            }
        )

    # Health check endpoint
    @app.get(
        "/health",
        summary="Health Check",
        description="Check the health status of all system components"
    )
    async def health_check():
        """System health check endpoint"""
        health_status = {
            "status": "healthy",
            "timestamp": asyncio.get_event_loop().time(),
            "services": {}
        }

        try:
            # Check database health
            if _db_manager:
                db_health = await _db_manager.health_check()
                health_status["services"]["database"] = db_health
            else:
                health_status["services"]["database"] = {"status": "not_initialized"}

            # Check cache health
            if _cache_manager:
                cache_health = await _cache_manager.health_check()
                health_status["services"]["cache"] = cache_health
            else:
                health_status["services"]["cache"] = {"status": "not_initialized"}

            # Check AI integration health
            if _ai_integration:
                ai_health = await _ai_integration.health_check()
                health_status["services"]["ai"] = ai_health
            else:
                health_status["services"]["ai"] = {"status": "not_available"}

            # Determine overall health
            services_healthy = all(
                service.get("status") == "healthy"
                for service in health_status["services"].values()
                if isinstance(service, dict)
            )

            if not services_healthy:
                health_status["status"] = "degraded"

        except Exception as e:
            logger.error("Health check failed", error=str(e))
            health_status["status"] = "unhealthy"
            health_status["error"] = str(e)

        status_code = status.HTTP_200_OK if health_status["status"] == "healthy" else status.HTTP_503_SERVICE_UNAVAILABLE
        return JSONResponse(status_code=status_code, content=health_status)

    # System info endpoint
    @app.get(
        "/info",
        summary="System Information",
        description="Get system version and configuration information"
    )
    async def system_info():
        """System information endpoint"""
        return {
            "name": "NIRAJ Advanced Trading System",
            "version": "1.0.0",
            "description": "AI-powered algorithmic trading platform",
            "features": [
                "Advanced Authentication",
                "Strategy Management",
                "AI Integration",
                "Real-time Processing",
                "Risk Management",
                "Performance Analytics"
            ],
            "api_version": "v1",
            "environment": os.getenv("ENVIRONMENT", "development")
        }

    # WebSocket endpoint for real-time data streaming
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket, token: Optional[str] = None):
        """WebSocket endpoint for real-time data streaming"""
        if not _websocket_server:
            await websocket.close(code=1011)  # Internal server error
            return

        # Accept the connection
        await websocket.accept()

        # Create a path-like string for the WebSocket server
        path = f"/ws?token={token}" if token else "/ws"

        # Delegate to the WebSocket server
        try:
            await _websocket_server.handle_connection(websocket, path)
        except Exception as e:
            logger.error("WebSocket connection error", error=str(e))
            try:
                await websocket.close(code=1011)
            except Exception:
                pass

    # Initialize and include API routes
    try:
        # Authentication routes
        auth_router = init_auth_routes(_db_manager, _cache_manager)
        app.include_router(auth_router, prefix="/api/v1")

        # Strategy management routes
        strategy_router = init_strategy_routes(_db_manager, _cache_manager, _ai_integration)
        app.include_router(strategy_router, prefix="/api/v1")

        # Trade management routes
        trade_router = init_trade_routes(_db_manager, _cache_manager)
        app.include_router(trade_router, prefix="/api/v1")

        # Portfolio management routes
        portfolio_router = init_portfolio_routes(_db_manager, _cache_manager)
        app.include_router(portfolio_router, prefix="/api/v1")

        # System and AI routes
        system_router = init_system_routes(_db_manager, _cache_manager, _ai_integration)
        app.include_router(system_router, prefix="/api/v1")

        # Market data routes
        try:
            from .api.auth_manager import AuthenticationManager
            from .api.angel_one_client import AngelOneClient
            from .api.dhan_client import DhanClient

            # Initialize broker clients (if credentials available)
            auth_manager = AuthenticationManager()

            # Setup development credentials
            try:
                from .api.auth_manager import setup_development_credentials
                setup_development_credentials(auth_manager)
                logger.info("Development credentials setup completed")
            except Exception as e:
                logger.warning("Failed to setup development credentials", error=str(e))

            # Clients will be created on-demand via auth_manager
            angel_client = AngelOneClient(
                api_key=config.get('brokers.angel_one.api_key', 'dummy_angel_api_key'),
                client_code=config.get('brokers.angel_one.client_code', 'dummy_client_code'),
                client_pin=config.get('brokers.angel_one.password', 'dummy_password'),
                totp_secret=config.get('brokers.angel_one.totp_secret')
            )
            dhan_client = DhanClient(
                client_id=config.get('brokers.dhan.client_id', 'dummy_dhan_client_id'),
                access_token=config.get('brokers.dhan.access_token', 'dummy_dhan_token')
            )

            market_data_router = init_market_data_routes(
                _db_manager, _cache_manager, auth_manager, angel_client, dhan_client
            )
            app.include_router(market_data_router, prefix="/api/v1")

        except Exception as e:
            logger.warning("Market data routes not initialized", error=str(e))

        # News routes
        try:
            news_router = init_news_routes(_db_manager, _cache_manager)
            app.include_router(news_router, prefix="/api/v1")
        except Exception as e:
            logger.warning("News routes not initialized", error=str(e))

        # Weather routes
        try:
            weather_router = init_weather_routes(_db_manager, _cache_manager)
            app.include_router(weather_router, prefix="/api/v1")
        except Exception as e:
            logger.warning("Weather routes not initialized", error=str(e))

        # AI analysis routes
        try:
            ai_router = init_ai_routes(_db_manager, _cache_manager, _ai_integration)
            app.include_router(ai_router, prefix="/api/v1")
        except Exception as e:
            logger.warning("AI analysis routes not initialized", error=str(e))

        # Technical indicators routes
        try:
            indicators_router = init_indicators_routes(_db_manager, _cache_manager)
            app.include_router(indicators_router, prefix="/api/v1")
        except Exception as e:
            logger.warning("Technical indicators routes not initialized", error=str(e))

        logger.info("API routes initialized successfully")

    except Exception as e:
        logger.error("Failed to initialize API routes", error=str(e))
        raise

    return app


# Create the FastAPI application instance
app = create_application()


def main():
    """Main entry point for running the application"""
    config.load_config()

    # Get server configuration
    host = config.get('host', '0.0.0.0')
    port = config.get('port', 8000)
    workers = config.get('workers', 1)
    reload = config.get('reload', True)
    environment = config.get('environment', 'development')

    logger.info(
        "Starting NIRAJ server",
        host=host,
        port=port,
        workers=workers,
        reload=reload,
        environment=environment
    )

    # Run the server
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        workers=workers,
        reload=reload,
        log_level="info"
    )


if __name__ == "__main__":
    main()


# Export the app for external usage (e.g., testing, deployment)
__all__ = [
    "app",
    "create_application",
    "lifespan",
    "main"
]
