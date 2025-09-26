"""
Market Data API Routes for NIRAJ Trading System

Provides comprehensive market data endpoints including:
- Real-time quotes and LTP data
- Historical price data with multiple timeframes
- Volume and technical indicators
- Market status and trading hours
- Watchlist management
- Real-time streaming via WebSocket

Endpoints:
- GET /api/v1/market-data/{symbol}: Get current market data
- GET /api/v1/market-data/{symbol}/history: Get historical data
- GET /api/v1/market-data/{symbol}/ltp: Get last traded price
- GET /api/v1/market-data/quotes: Get multiple quotes
- GET /api/v1/market-data/status: Get market status
- POST /api/v1/market-data/watchlist: Manage watchlist
- GET /api/v1/market-data/indices: Get market indices
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
import structlog

from ...core.database import DatabaseManager
from ...core.cache import CacheManager
from ...api.auth_manager import AuthenticationManager
from ...api.angel_one_client import AngelOneClient
from ...api.dhan_client import DhanClient
from ...api.routes.auth import get_security_context, SecurityContext

# Initialize router
router = APIRouter(
    prefix="/market-data",
    tags=["market-data"],
    responses={
        400: {"description": "Bad Request - Invalid parameters"},
        401: {"description": "Unauthorized - Authentication required"},
        404: {"description": "Not Found - Symbol not found"},
        429: {"description": "Too Many Requests - Rate limit exceeded"},
        500: {"description": "Internal Server Error - System error"}
    }
)

# Initialize logger
logger = structlog.get_logger(__name__)

# Global service instances
_db_manager: Optional[DatabaseManager] = None
_cache_manager: Optional[CacheManager] = None
_auth_manager: Optional[AuthenticationManager] = None
_angel_client: Optional[AngelOneClient] = None
_dhan_client: Optional[DhanClient] = None


# Enums and Models
class TimeInterval(str, Enum):
    """Time intervals for market data"""
    ONE_MINUTE = "1m"
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    THIRTY_MINUTES = "30m"
    ONE_HOUR = "1h"
    FOUR_HOURS = "4h"
    ONE_DAY = "1d"
    ONE_WEEK = "1w"
    ONE_MONTH = "1M"


class MarketStatus(str, Enum):
    """Market status"""
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    PRE_OPEN = "PRE_OPEN"
    POST_CLOSE = "POST_CLOSE"
    HOLIDAY = "HOLIDAY"


class Exchange(str, Enum):
    """Exchange types"""
    NSE = "NSE"
    BSE = "BSE"
    NFO = "NFO"
    MCX = "MCX"
    CDS = "CDS"


# Request Models
class MarketDataRequest(BaseModel):
    """Market data request model"""
    symbol: str = Field(description="Trading symbol")
    exchange: Exchange = Field(default=Exchange.NSE, description="Exchange")
    interval: TimeInterval = Field(default=TimeInterval.FIFTEEN_MINUTES, description="Time interval")
    from_date: Optional[datetime] = Field(None, description="Start date for historical data")
    to_date: Optional[datetime] = Field(None, description="End date for historical data")
    limit: int = Field(default=100, ge=1, le=5000, description="Number of data points")


class QuotesRequest(BaseModel):
    """Multiple quotes request model"""
    symbols: List[str] = Field(description="List of trading symbols", max_length=50)
    exchange: Exchange = Field(default=Exchange.NSE, description="Exchange")


class WatchlistRequest(BaseModel):
    """Watchlist management request"""
    action: str = Field(description="Action: add, remove, or list")
    symbols: Optional[List[str]] = Field(None, description="Symbols to add/remove")
    watchlist_name: str = Field(default="default", description="Watchlist name")

    @field_validator('action')
    @classmethod
    def validate_action(cls, v):
        if v not in ["add", "remove", "list", "create", "delete"]:
            raise ValueError("Action must be add, remove, list, create, or delete")
        return v


# Response Models
class OHLCData(BaseModel):
    """OHLC data point"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    vwap: Optional[float] = None
    turnover: Optional[float] = None


class MarketDataResponse(BaseModel):
    """Market data response model"""
    symbol: str
    exchange: str
    interval: str
    data: List[OHLCData]
    last_updated: datetime
    total_records: int
    from_cache: bool = False


class LTPResponse(BaseModel):
    """Last traded price response"""
    symbol: str
    exchange: str
    ltp: float
    change: float
    change_percent: float
    volume: int
    high: float
    low: float
    open: float
    close: float
    timestamp: datetime
    market_status: MarketStatus


class QuoteData(BaseModel):
    """Individual quote data"""
    symbol: str
    exchange: str
    ltp: float
    change: float
    change_percent: float
    volume: int
    high: float
    low: float
    open: float
    prev_close: float
    bid_price: Optional[float] = None
    ask_price: Optional[float] = None
    bid_qty: Optional[int] = None
    ask_qty: Optional[int] = None


class QuotesResponse(BaseModel):
    """Multiple quotes response"""
    quotes: List[QuoteData]
    timestamp: datetime
    total_quotes: int


class MarketStatusResponse(BaseModel):
    """Market status response"""
    market_status: MarketStatus
    timestamp: datetime
    trading_session: str
    next_session: Optional[datetime] = None
    exchanges: Dict[str, MarketStatus]


class WatchlistResponse(BaseModel):
    """Watchlist response"""
    watchlist_name: str
    symbols: List[str]
    total_symbols: int
    last_updated: datetime


class IndicesResponse(BaseModel):
    """Market indices response"""
    indices: List[QuoteData]
    timestamp: datetime


# Helper functions
async def get_market_service():
    """Get appropriate market data service based on user preference"""
    global _angel_client, _dhan_client, _auth_manager

    if not _auth_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Market data service not initialized"
        )

    # Try Angel One first, fallback to Dhan
    try:
        if _angel_client:
            return _angel_client
        elif _dhan_client:
            return _dhan_client
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No market data service available"
            )
    except Exception as e:
        logger.error("Error getting market service", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Market data service unavailable"
        )


def cache_key(prefix: str, *args) -> str:
    """Generate cache key"""
    return f"market:{prefix}:{':'.join(str(arg) for arg in args)}"


async def get_cached_data(key: str, ttl: int = 60) -> Optional[Dict[str, Any]]:
    """Get data from cache"""
    if not _cache_manager:
        return None

    try:
        return await _cache_manager.get(key)
    except Exception as e:
        logger.warning("Cache get failed", key=key, error=str(e))
        return None


async def set_cached_data(key: str, data: Dict[str, Any], ttl: int = 60):
    """Set data in cache"""
    if not _cache_manager:
        return

    try:
        await _cache_manager.set(key, data, ttl=ttl)
    except Exception as e:
        logger.warning("Cache set failed", key=key, error=str(e))


# API Endpoints
@router.get(
    "/{symbol}",
    response_model=MarketDataResponse,
    summary="Get Market Data",
    description="""
    Get current or historical market data for a symbol.

    **Features:**
    - Real-time and historical data
    - Multiple time intervals
    - OHLC data with volume
    - Caching for performance
    - Rate limiting protection
    """
)
async def get_market_data(
    symbol: str,
    exchange: Exchange = Query(default=Exchange.NSE, description="Exchange"),
    interval: TimeInterval = Query(default=TimeInterval.FIFTEEN_MINUTES, description="Time interval"),
    from_date: Optional[datetime] = Query(None, description="Start date (ISO format)"),
    to_date: Optional[datetime] = Query(None, description="End date (ISO format)"),
    limit: int = Query(default=100, ge=1, le=5000, description="Number of data points"),
    security_context: SecurityContext = Depends(get_security_context)
) -> MarketDataResponse:
    """Get market data for a symbol"""

    start_time = datetime.now(timezone.utc)

    try:
        with structlog.contextvars.bound_contextvars(
            user_id=security_context.user_id,
            symbol=symbol.upper(),
            exchange=exchange.value,
            interval=interval.value
        ):
            logger.info("Market data request")

            # Validate symbol
            symbol = symbol.upper().strip()
            if not symbol:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Symbol is required"
                )

            # Check cache first for real-time data
            cache_ttl = 30 if not from_date else 300  # 30s for real-time, 5m for historical
            cache_key_str = cache_key("data", symbol, exchange.value, interval.value, from_date, to_date, limit)

            cached_data = await get_cached_data(cache_key_str, cache_ttl)
            if cached_data:
                logger.info("Returning cached market data")
                return MarketDataResponse(**cached_data, from_cache=True)

            # Get market service
            market_service = await get_market_service()

            # Set default date range if not provided
            if not to_date:
                to_date = datetime.now(timezone.utc)
            if not from_date:
                if interval in [TimeInterval.ONE_MINUTE, TimeInterval.FIVE_MINUTES]:
                    from_date = to_date - timedelta(days=1)
                elif interval in [TimeInterval.FIFTEEN_MINUTES, TimeInterval.THIRTY_MINUTES]:
                    from_date = to_date - timedelta(days=7)
                elif interval == TimeInterval.ONE_HOUR:
                    from_date = to_date - timedelta(days=30)
                else:
                    from_date = to_date - timedelta(days=365)

            # Fetch data from broker API
            if hasattr(market_service, 'get_historical_data'):
                raw_data = await market_service.get_historical_data(
                    exchange=exchange.value,
                    symboltoken=symbol,  # In real implementation, you'd need to get token
                    interval=interval.value,
                    fromdate=from_date.strftime("%Y-%m-%d %H:%M"),
                    todate=to_date.strftime("%Y-%m-%d %H:%M")
                )
            else:
                # Fallback to LTP for current data
                raw_data = await market_service.get_ltp_data(
                    exchange=exchange.value,
                    tradingsymbol=symbol,
                    symboltoken=symbol
                )

                # Convert LTP to OHLC format
                current_time = datetime.now(timezone.utc)
                raw_data = {
                    'data': [{
                        'timestamp': current_time.isoformat(),
                        'open': raw_data.get('ltp', 0),
                        'high': raw_data.get('ltp', 0),
                        'low': raw_data.get('ltp', 0),
                        'close': raw_data.get('ltp', 0),
                        'volume': raw_data.get('volume', 0),
                        'vwap': raw_data.get('ltp', 0)
                    }]
                }

            # Process and format data
            ohlc_data = []
            for point in raw_data.get('data', []):
                try:
                    ohlc_data.append(OHLCData(
                        timestamp=datetime.fromisoformat(point['timestamp'].replace('Z', '+00:00')),
                        open=float(point.get('open', 0)),
                        high=float(point.get('high', 0)),
                        low=float(point.get('low', 0)),
                        close=float(point.get('close', 0)),
                        volume=int(point.get('volume', 0)),
                        vwap=float(point.get('vwap', 0)) if point.get('vwap') else None,
                        turnover=float(point.get('turnover', 0)) if point.get('turnover') else None
                    ))
                except (ValueError, KeyError) as e:
                    logger.warning("Skipping invalid data point", error=str(e), data=point)
                    continue

            # Apply limit
            if len(ohlc_data) > limit:
                ohlc_data = ohlc_data[-limit:]

            # Create response
            response = MarketDataResponse(
                symbol=symbol,
                exchange=exchange.value,
                interval=interval.value,
                data=ohlc_data,
                last_updated=datetime.now(timezone.utc),
                total_records=len(ohlc_data),
                from_cache=False
            )

            # Cache the response
            await set_cached_data(cache_key_str, response.dict(exclude={'from_cache'}), cache_ttl)

            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.info(
                "Market data retrieved successfully",
                records=len(ohlc_data),
                duration=f"{duration:.3f}s"
            )

            return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Market data retrieval failed", error=str(e), traceback=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve market data"
        )


@router.get(
    "/{symbol}/ltp",
    response_model=LTPResponse,
    summary="Get Last Traded Price",
    description="""
    Get real-time last traded price and basic market data for a symbol.

    **Features:**
    - Real-time LTP data
    - Price change calculations
    - Market status information
    - High-frequency updates
    """
)
async def get_ltp(
    symbol: str,
    exchange: Exchange = Query(default=Exchange.NSE, description="Exchange"),
    security_context: SecurityContext = Depends(get_security_context)
) -> LTPResponse:
    """Get last traded price for a symbol"""

    try:
        with structlog.contextvars.bound_contextvars(
            user_id=security_context.user_id,
            symbol=symbol.upper(),
            exchange=exchange.value
        ):
            logger.info("LTP request")

            symbol = symbol.upper().strip()

            # Check cache (short TTL for LTP)
            cache_key_str = cache_key("ltp", symbol, exchange.value)
            cached_data = await get_cached_data(cache_key_str, ttl=5)  # 5 second cache

            if cached_data:
                return LTPResponse(**cached_data)

            # Get market service
            market_service = await get_market_service()

            # Fetch LTP data
            ltp_data = await market_service.get_ltp_data(
                exchange=exchange.value,
                tradingsymbol=symbol,
                symboltoken=symbol  # In real implementation, map symbol to token
            )

            # Calculate change and change percent
            ltp = float(ltp_data.get('ltp', 0))
            prev_close = float(ltp_data.get('close', ltp))
            change = ltp - prev_close
            change_percent = (change / prev_close * 100) if prev_close != 0 else 0

            # Determine market status (simplified)
            current_time = datetime.now(timezone.utc)
            market_status = MarketStatus.OPEN  # In real implementation, check actual market hours

            response = LTPResponse(
                symbol=symbol,
                exchange=exchange.value,
                ltp=ltp,
                change=change,
                change_percent=change_percent,
                volume=int(ltp_data.get('volume', 0)),
                high=float(ltp_data.get('high', ltp)),
                low=float(ltp_data.get('low', ltp)),
                open=float(ltp_data.get('open', ltp)),
                close=prev_close,
                timestamp=current_time,
                market_status=market_status
            )

            # Cache response
            await set_cached_data(cache_key_str, response.dict(), ttl=5)

            logger.info("LTP retrieved successfully", ltp=ltp)
            return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("LTP retrieval failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve LTP data"
        )


@router.post(
    "/quotes",
    response_model=QuotesResponse,
    summary="Get Multiple Quotes",
    description="""
    Get quotes for multiple symbols in a single request.

    **Features:**
    - Batch quote retrieval
    - Efficient processing
    - Parallel API calls
    - Error handling per symbol
    """
)
async def get_quotes(
    request: QuotesRequest,
    security_context: SecurityContext = Depends(get_security_context)
) -> QuotesResponse:
    """Get quotes for multiple symbols"""

    try:
        with structlog.contextvars.bound_contextvars(
            user_id=security_context.user_id,
            symbols_count=len(request.symbols),
            exchange=request.exchange.value
        ):
            logger.info("Multiple quotes request")

            if not request.symbols:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Symbols list is required"
                )

            # Get market service
            market_service = await get_market_service()

            # Fetch quotes concurrently
            async def fetch_quote(symbol: str) -> Optional[QuoteData]:
                try:
                    symbol = symbol.upper().strip()
                    ltp_data = await market_service.get_ltp_data(
                        exchange=request.exchange.value,
                        tradingsymbol=symbol,
                        symboltoken=symbol
                    )

                    ltp = float(ltp_data.get('ltp', 0))
                    prev_close = float(ltp_data.get('close', ltp))
                    change = ltp - prev_close
                    change_percent = (change / prev_close * 100) if prev_close != 0 else 0

                    return QuoteData(
                        symbol=symbol,
                        exchange=request.exchange.value,
                        ltp=ltp,
                        change=change,
                        change_percent=change_percent,
                        volume=int(ltp_data.get('volume', 0)),
                        high=float(ltp_data.get('high', ltp)),
                        low=float(ltp_data.get('low', ltp)),
                        open=float(ltp_data.get('open', ltp)),
                        prev_close=prev_close,
                        bid_price=float(ltp_data.get('bid', 0)) if ltp_data.get('bid') else None,
                        ask_price=float(ltp_data.get('ask', 0)) if ltp_data.get('ask') else None,
                        bid_qty=int(ltp_data.get('bidqty', 0)) if ltp_data.get('bidqty') else None,
                        ask_qty=int(ltp_data.get('askqty', 0)) if ltp_data.get('askqty') else None
                    )
                except Exception as e:
                    logger.warning("Failed to fetch quote", symbol=symbol, error=str(e))
                    return None

            # Execute concurrent requests
            tasks = [fetch_quote(symbol) for symbol in request.symbols]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Filter successful results
            quotes = [result for result in results if isinstance(result, QuoteData)]

            response = QuotesResponse(
                quotes=quotes,
                timestamp=datetime.now(timezone.utc),
                total_quotes=len(quotes)
            )

            logger.info(
                "Multiple quotes retrieved",
                requested=len(request.symbols),
                successful=len(quotes)
            )

            return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Multiple quotes retrieval failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve quotes"
        )


@router.get(
    "/status",
    response_model=MarketStatusResponse,
    summary="Get Market Status",
    description="""
    Get current market status and trading session information.

    **Features:**
    - Real-time market status
    - Trading session information
    - Exchange-specific status
    - Next session timing
    """
)
async def get_market_status(
    security_context: SecurityContext = Depends(get_security_context)
) -> MarketStatusResponse:
    """Get current market status"""

    try:
        with structlog.contextvars.bound_contextvars(
            user_id=security_context.user_id
        ):
            logger.info("Market status request")

            # Check cache
            cache_key_str = cache_key("status")
            cached_status = await get_cached_data(cache_key_str, ttl=60)

            if cached_status:
                return MarketStatusResponse(**cached_status)

            # Get current time in IST
            current_time = datetime.now(timezone.utc)

            # Simplified market status logic (in real implementation, use actual market calendar)
            hour = current_time.hour
            weekday = current_time.weekday()

            # Basic market hours check (9:15 AM to 3:30 PM IST)
            if weekday >= 5:  # Weekend
                market_status = MarketStatus.CLOSED
                trading_session = "Weekend"
            elif 3 <= hour < 9:  # Before market hours
                market_status = MarketStatus.CLOSED
                trading_session = "Pre-market"
            elif 9 <= hour < 15:  # Market hours
                market_status = MarketStatus.OPEN
                trading_session = "Regular"
            else:  # After market hours
                market_status = MarketStatus.CLOSED
                trading_session = "Post-market"

            # Exchange-specific status (simplified)
            exchanges = {
                "NSE": market_status,
                "BSE": market_status,
                "NFO": market_status,
                "MCX": MarketStatus.OPEN if 9 <= hour < 23 else MarketStatus.CLOSED  # Commodity markets
            }

            response = MarketStatusResponse(
                market_status=market_status,
                timestamp=current_time,
                trading_session=trading_session,
                next_session=None,  # Calculate next session time
                exchanges=exchanges
            )

            # Cache response
            await set_cached_data(cache_key_str, response.dict(), ttl=60)

            logger.info("Market status retrieved", status=market_status.value)
            return response

    except Exception as e:
        logger.error("Market status retrieval failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve market status"
        )


@router.post(
    "/watchlist",
    response_model=WatchlistResponse,
    summary="Manage Watchlist",
    description="""
    Create, update, or retrieve user watchlists.

    **Actions:**
    - `create`: Create new watchlist
    - `add`: Add symbols to watchlist
    - `remove`: Remove symbols from watchlist
    - `list`: Get watchlist contents
    - `delete`: Delete entire watchlist
    """
)
async def manage_watchlist(
    request: WatchlistRequest,
    security_context: SecurityContext = Depends(get_security_context)
) -> WatchlistResponse:
    """Manage user watchlist"""

    try:
        with structlog.contextvars.bound_contextvars(
            user_id=security_context.user_id,
            action=request.action,
            watchlist=request.watchlist_name
        ):
            logger.info("Watchlist management request")

            if not _db_manager:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Database service unavailable"
                )

            # Get current watchlist from database
            watchlist_key = f"watchlist:{security_context.user_id}:{request.watchlist_name}"

            if request.action == "list":
                # Get existing watchlist
                cached_watchlist = await get_cached_data(watchlist_key, ttl=300)
                if cached_watchlist:
                    symbols = cached_watchlist.get('symbols', [])
                else:
                    # Fetch from database (placeholder implementation)
                    symbols = []  # In real implementation, query database

                return WatchlistResponse(
                    watchlist_name=request.watchlist_name,
                    symbols=symbols,
                    total_symbols=len(symbols),
                    last_updated=datetime.now(timezone.utc)
                )

            elif request.action == "create":
                # Create new watchlist
                symbols = request.symbols or []

                watchlist_data = {
                    'symbols': symbols,
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'user_id': security_context.user_id
                }

                await set_cached_data(watchlist_key, watchlist_data, ttl=86400)  # 24 hours

                return WatchlistResponse(
                    watchlist_name=request.watchlist_name,
                    symbols=symbols,
                    total_symbols=len(symbols),
                    last_updated=datetime.now(timezone.utc)
                )

            elif request.action == "add":
                if not request.symbols:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Symbols required for add action"
                    )

                # Get existing watchlist
                existing_data = await get_cached_data(watchlist_key, ttl=300) or {'symbols': []}
                existing_symbols = set(existing_data.get('symbols', []))

                # Add new symbols
                new_symbols = [s.upper().strip() for s in request.symbols]
                existing_symbols.update(new_symbols)

                updated_symbols = list(existing_symbols)
                watchlist_data = {
                    'symbols': updated_symbols,
                    'updated_at': datetime.now(timezone.utc).isoformat(),
                    'user_id': security_context.user_id
                }

                await set_cached_data(watchlist_key, watchlist_data, ttl=86400)

                return WatchlistResponse(
                    watchlist_name=request.watchlist_name,
                    symbols=updated_symbols,
                    total_symbols=len(updated_symbols),
                    last_updated=datetime.now(timezone.utc)
                )

            elif request.action == "remove":
                if not request.symbols:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Symbols required for remove action"
                    )

                # Get existing watchlist
                existing_data = await get_cached_data(watchlist_key, ttl=300) or {'symbols': []}
                existing_symbols = set(existing_data.get('symbols', []))

                # Remove symbols
                symbols_to_remove = set(s.upper().strip() for s in request.symbols)
                existing_symbols -= symbols_to_remove

                updated_symbols = list(existing_symbols)
                watchlist_data = {
                    'symbols': updated_symbols,
                    'updated_at': datetime.now(timezone.utc).isoformat(),
                    'user_id': security_context.user_id
                }

                await set_cached_data(watchlist_key, watchlist_data, ttl=86400)

                return WatchlistResponse(
                    watchlist_name=request.watchlist_name,
                    symbols=updated_symbols,
                    total_symbols=len(updated_symbols),
                    last_updated=datetime.now(timezone.utc)
                )

            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid action"
                )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Watchlist management failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to manage watchlist"
        )


@router.get(
    "/indices",
    response_model=IndicesResponse,
    summary="Get Market Indices",
    description="""
    Get current values for major market indices.

    **Indices Included:**
    - NIFTY 50
    - SENSEX
    - BANK NIFTY
    - NIFTY IT
    - NIFTY AUTO
    - And more...
    """
)
async def get_indices(
    security_context: SecurityContext = Depends(get_security_context)
) -> IndicesResponse:
    """Get market indices data"""

    try:
        with structlog.contextvars.bound_contextvars(
            user_id=security_context.user_id
        ):
            logger.info("Market indices request")

            # Check cache
            cache_key_str = cache_key("indices")
            cached_indices = await get_cached_data(cache_key_str, ttl=30)  # 30 second cache

            if cached_indices:
                return IndicesResponse(**cached_indices)

            # Major Indian indices
            index_symbols = [
                "NIFTY",
                "SENSEX",
                "BANKNIFTY",
                "NIFTYIT",
                "NIFTYAUTO",
                "NIFTYPHARMA",
                "NIFTYREALTY",
                "NIFTYMETAL"
            ]

            # Get market service
            market_service = await get_market_service()

            # Fetch indices data
            indices_data = []
            for symbol in index_symbols:
                try:
                    ltp_data = await market_service.get_ltp_data(
                        exchange="NSE",
                        tradingsymbol=symbol,
                        symboltoken=symbol
                    )

                    ltp = float(ltp_data.get('ltp', 0))
                    prev_close = float(ltp_data.get('close', ltp))
                    change = ltp - prev_close
                    change_percent = (change / prev_close * 100) if prev_close != 0 else 0

                    indices_data.append(QuoteData(
                        symbol=symbol,
                        exchange="NSE",
                        ltp=ltp,
                        change=change,
                        change_percent=change_percent,
                        volume=int(ltp_data.get('volume', 0)),
                        high=float(ltp_data.get('high', ltp)),
                        low=float(ltp_data.get('low', ltp)),
                        open=float(ltp_data.get('open', ltp)),
                        prev_close=prev_close
                    ))
                except Exception as e:
                    logger.warning("Failed to fetch index data", symbol=symbol, error=str(e))
                    continue

            response = IndicesResponse(
                indices=indices_data,
                timestamp=datetime.now(timezone.utc)
            )

            # Cache response
            await set_cached_data(cache_key_str, response.dict(), ttl=30)

            logger.info("Market indices retrieved", count=len(indices_data))
            return response

    except Exception as e:
        logger.error("Market indices retrieval failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve market indices"
        )


# Initialization function
def init_market_data_routes(
    db_manager: DatabaseManager,
    cache_manager: CacheManager,
    auth_manager: AuthenticationManager,
    angel_client: Optional[AngelOneClient] = None,
    dhan_client: Optional[DhanClient] = None
) -> APIRouter:
    """Initialize market data routes"""
    global _db_manager, _cache_manager, _auth_manager, _angel_client, _dhan_client

    _db_manager = db_manager
    _cache_manager = cache_manager
    _auth_manager = auth_manager
    _angel_client = angel_client
    _dhan_client = dhan_client

    logger.info("Market data routes initialized")
    return router


# Export
__all__ = [
    "router",
    "init_market_data_routes",
    "MarketDataRequest",
    "QuotesRequest",
    "WatchlistRequest",
    "MarketDataResponse",
    "LTPResponse",
    "QuotesResponse",
    "MarketStatusResponse",
    "WatchlistResponse",
    "IndicesResponse",
    "TimeInterval",
    "MarketStatus",
    "Exchange"
]
