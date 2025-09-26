"""
News API Routes for NIRAJ Trading System

Provides access to news data from multiple sources including:
- General market headlines
- Company-specific news
- Sector-based news filtering
- News sentiment analysis
- Trending topics identification
- Real-time news feeds

Endpoints:
- GET /api/v1/news/headlines: Get general news headlines
- GET /api/v1/news/search: Search news by keywords
- GET /api/v1/news/market: Get market-specific news
- GET /api/v1/news/company/{symbol}: Get company-specific news
- GET /api/v1/news/trending: Get trending topics
- GET /api/v1/news/sources: Get available news sources
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
import structlog

from ...core.database import DatabaseManager
from ...core.cache import CacheManager
from ...api.news_client import NewsClient, NewsConfig, NewsFilter, Article
from ...api.routes.auth import get_security_context, SecurityContext

# Initialize router
router = APIRouter(
    prefix="/news",
    tags=["news"],
    responses={
        400: {"description": "Bad Request - Invalid parameters"},
        401: {"description": "Unauthorized - Authentication required"},
        404: {"description": "Not Found - No news found"},
        429: {"description": "Too Many Requests - Rate limit exceeded"},
        500: {"description": "Internal Server Error - System error"}
    }
)

# Initialize logger
logger = structlog.get_logger(__name__)

# Global service instances
_db_manager: Optional[DatabaseManager] = None
_cache_manager: Optional[CacheManager] = None
_news_client: Optional[NewsClient] = None


# Enums
class NewsCategory(str, Enum):
    """News categories"""
    BUSINESS = "business"
    TECHNOLOGY = "technology"
    GENERAL = "general"
    HEALTH = "health"
    SCIENCE = "science"
    SPORTS = "sports"
    ENTERTAINMENT = "entertainment"


class NewsSortBy(str, Enum):
    """News sorting options"""
    RELEVANCY = "relevancy"
    POPULARITY = "popularity"
    PUBLISHED_AT = "publishedAt"


class NewsProvider(str, Enum):
    """News providers"""
    NEWSAPI = "newsapi"
    RSS = "rss"
    FMP = "fmp"
    ALPHAVANTAGE = "alphavantage"


# Request Models
class NewsSearchRequest(BaseModel):
    """News search request model"""
    query: str = Field(description="Search query", min_length=1, max_length=500)
    from_date: Optional[datetime] = Field(None, description="Start date for news")
    to_date: Optional[datetime] = Field(None, description="End date for news")
    language: str = Field(default="en", description="Language code")
    sort_by: NewsSortBy = Field(default=NewsSortBy.PUBLISHED_AT, description="Sort order")
    page_size: int = Field(default=20, ge=1, le=100, description="Number of articles")
    page: int = Field(default=1, ge=1, description="Page number")


class MarketNewsRequest(BaseModel):
    """Market news request model"""
    symbols: Optional[List[str]] = Field(None, description="Stock symbols to filter by")
    sectors: Optional[List[str]] = Field(None, description="Market sectors to filter by")
    keywords: Optional[List[str]] = Field(None, description="Additional keywords")
    min_relevance_score: float = Field(default=0.3, ge=0.0, le=1.0, description="Minimum relevance score")
    limit: int = Field(default=50, ge=1, le=100, description="Maximum articles")


# Response Models
class NewsArticleResponse(BaseModel):
    """News article response model"""
    id: str
    title: str
    description: Optional[str]
    content: Optional[str]
    url: str
    image_url: Optional[str]
    source: str
    provider: str
    author: Optional[str]
    published_at: datetime
    relevance_score: float
    sentiment_score: Optional[float] = None
    tags: List[str] = []
    stock_symbols: List[str] = []
    market_sectors: List[str] = []


class NewsResponse(BaseModel):
    """News response model"""
    articles: List[NewsArticleResponse]
    total_results: int
    page: int
    page_size: int
    has_more: bool
    sources_used: List[str]
    query_time_ms: int
    cached: bool = False


class TrendingTopicsResponse(BaseModel):
    """Trending topics response"""
    topics: Dict[str, int]
    total_topics: int
    timestamp: datetime
    time_period: str


class NewsSourcesResponse(BaseModel):
    """News sources response"""
    sources: List[Dict[str, Any]]
    total_sources: int
    enabled_providers: List[str]


class CompanyNewsResponse(BaseModel):
    """Company-specific news response"""
    symbol: str
    company_name: Optional[str]
    articles: List[NewsArticleResponse]
    total_articles: int
    sentiment_summary: Dict[str, Any]
    timestamp: datetime


# Helper functions
async def get_news_client() -> NewsClient:
    """Get news client instance"""
    global _news_client

    if not _news_client:
        try:
            config = NewsConfig()  # Use default configuration
            _news_client = NewsClient(config)
            logger.info("News client initialized")
        except Exception as e:
            logger.error("Failed to initialize news client", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="News service unavailable"
            )

    return _news_client


def article_to_response(article: Article) -> NewsArticleResponse:
    """Convert Article model to response model"""
    return NewsArticleResponse(
        id=article.id,
        title=article.title,
        description=article.description,
        content=article.content,
        url=article.url,
        image_url=article.image_url,
        source=article.source,
        provider=article.provider,
        author=article.author,
        published_at=article.published_at,
        relevance_score=article.relevance_score,
        sentiment_score=article.sentiment_score,
        tags=article.tags,
        stock_symbols=article.stock_symbols,
        market_sectors=article.market_sectors
    )


def cache_key(prefix: str, *args) -> str:
    """Generate cache key for news data"""
    return f"news:{prefix}:{':'.join(str(arg) for arg in args)}"


async def get_cached_news(key: str, ttl: int = 300) -> Optional[Dict[str, Any]]:
    """Get cached news data"""
    if not _cache_manager:
        return None

    try:
        return await _cache_manager.get(key)
    except Exception as e:
        logger.warning("Cache get failed", key=key, error=str(e))
        return None


async def set_cached_news(key: str, data: Dict[str, Any], ttl: int = 300):
    """Set cached news data"""
    if not _cache_manager:
        return

    try:
        await _cache_manager.set(key, data, ttl=ttl)
    except Exception as e:
        logger.warning("Cache set failed", key=key, error=str(e))


# API Endpoints
@router.get(
    "/headlines",
    response_model=NewsResponse,
    summary="Get News Headlines",
    description="""
    Get general news headlines with optional filtering.

    **Features:**
    - Multiple news sources
    - Category filtering
    - Date range filtering
    - Caching for performance
    - Pagination support
    """
)
async def get_headlines(
    category: NewsCategory = Query(default=NewsCategory.BUSINESS, description="News category"),
    country: str = Query(default="in", description="Country code"),
    language: str = Query(default="en", description="Language code"),
    page_size: int = Query(default=20, ge=1, le=100, description="Articles per page"),
    page: int = Query(default=1, ge=1, description="Page number"),
    providers: Optional[List[NewsProvider]] = Query(None, description="News providers to use"),
    security_context: SecurityContext = Depends(get_security_context)
) -> NewsResponse:
    """Get news headlines"""

    start_time = datetime.now(timezone.utc)

    try:
        with structlog.contextvars.bound_contextvars(
            user_id=security_context.user_id,
            category=category.value,
            page=page,
            page_size=page_size
        ):
            logger.info("News headlines request")

            # Check cache
            cache_key_str = cache_key("headlines", category.value, country, language, page_size, page)
            cached_data = await get_cached_news(cache_key_str, ttl=300)  # 5 minute cache

            if cached_data:
                logger.info("Returning cached headlines")
                return NewsResponse(**cached_data, cached=True)

            # Get news client
            news_client = await get_news_client()

            # Create news filter
            news_filter = NewsFilter(
                category=category.value,
                country=country,
                language=language,
                page_size=page_size,
                sort_by="publishedAt"
            )

            # Convert providers enum to strings
            provider_names = [p.value for p in providers] if providers else None

            # Fetch headlines
            articles = await news_client.get_headlines(
                news_filter=news_filter,
                providers=provider_names
            )

            # Convert to response format
            article_responses = [article_to_response(article) for article in articles]

            # Calculate pagination
            total_results = len(article_responses)
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_articles = article_responses[start_idx:end_idx]

            # Get sources used
            sources_used = list(set(article.provider for article in articles))

            response = NewsResponse(
                articles=paginated_articles,
                total_results=total_results,
                page=page,
                page_size=page_size,
                has_more=end_idx < total_results,
                sources_used=sources_used,
                query_time_ms=int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000),
                cached=False
            )

            # Cache response
            await set_cached_news(cache_key_str, response.dict(exclude={'cached'}), ttl=300)

            logger.info(
                "Headlines retrieved successfully",
                articles=len(paginated_articles),
                sources=len(sources_used)
            )

            return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Headlines retrieval failed", error=str(e), traceback=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve headlines"
        )


@router.get(
    "/search",
    response_model=NewsResponse,
    summary="Search News",
    description="""
    Search news articles by keywords and filters.

    **Features:**
    - Keyword search across multiple sources
    - Date range filtering
    - Relevance scoring
    - Advanced filtering options
    """
)
async def search_news(
    q: str = Query(description="Search query", min_length=1, max_length=500),
    from_date: Optional[datetime] = Query(None, description="Start date (ISO format)"),
    to_date: Optional[datetime] = Query(None, description="End date (ISO format)"),
    language: str = Query(default="en", description="Language code"),
    sort_by: NewsSortBy = Query(default=NewsSortBy.RELEVANCY, description="Sort order"),
    page_size: int = Query(default=20, ge=1, le=100, description="Articles per page"),
    page: int = Query(default=1, ge=1, description="Page number"),
    providers: Optional[List[NewsProvider]] = Query(None, description="News providers"),
    security_context: SecurityContext = Depends(get_security_context)
) -> NewsResponse:
    """Search news articles"""

    start_time = datetime.now(timezone.utc)

    try:
        with structlog.contextvars.bound_contextvars(
            user_id=security_context.user_id,
            query=q[:50],  # Truncate for logging
            page=page,
            page_size=page_size
        ):
            logger.info("News search request")

            # Validate date range
            if from_date and to_date and from_date > to_date:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="from_date must be before to_date"
                )

            # Check cache
            cache_key_str = cache_key("search", q, from_date, to_date, language, sort_by.value, page_size, page)
            cached_data = await get_cached_news(cache_key_str, ttl=600)  # 10 minute cache for searches

            if cached_data:
                logger.info("Returning cached search results")
                return NewsResponse(**cached_data, cached=True)

            # Get news client
            news_client = await get_news_client()

            # Create news filter
            news_filter = NewsFilter(
                from_date=from_date,
                to_date=to_date,
                language=language,
                sort_by=sort_by.value,
                page_size=page_size * 2  # Get more to account for filtering
            )

            # Convert providers
            provider_names = [p.value for p in providers] if providers else None

            # Search news
            articles = await news_client.search_news(
                query=q,
                news_filter=news_filter,
                providers=provider_names
            )

            # Convert to response format
            article_responses = [article_to_response(article) for article in articles]

            # Apply pagination
            total_results = len(article_responses)
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_articles = article_responses[start_idx:end_idx]

            sources_used = list(set(article.provider for article in articles))

            response = NewsResponse(
                articles=paginated_articles,
                total_results=total_results,
                page=page,
                page_size=page_size,
                has_more=end_idx < total_results,
                sources_used=sources_used,
                query_time_ms=int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000),
                cached=False
            )

            # Cache response
            await set_cached_news(cache_key_str, response.dict(exclude={'cached'}), ttl=600)

            logger.info(
                "News search completed",
                articles=len(paginated_articles),
                total=total_results,
                sources=len(sources_used)
            )

            return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("News search failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search news"
        )


@router.get(
    "/market",
    response_model=NewsResponse,
    summary="Get Market News",
    description="""
    Get market-specific news with stock symbol and sector filtering.

    **Features:**
    - Stock symbol filtering
    - Sector-based filtering
    - Market relevance scoring
    - Business news focus
    """
)
async def get_market_news(
    symbols: Optional[List[str]] = Query(None, description="Stock symbols (e.g., RELIANCE,TCS)"),
    sectors: Optional[List[str]] = Query(None, description="Market sectors"),
    keywords: Optional[List[str]] = Query(None, description="Additional keywords"),
    min_relevance: float = Query(default=0.3, ge=0.0, le=1.0, description="Minimum relevance score"),
    limit: int = Query(default=50, ge=1, le=100, description="Maximum articles"),
    security_context: SecurityContext = Depends(get_security_context)
) -> NewsResponse:
    """Get market-specific news"""

    start_time = datetime.now(timezone.utc)

    try:
        with structlog.contextvars.bound_contextvars(
            user_id=security_context.user_id,
            symbols=symbols[:5] if symbols else None,  # Limit logging
            sectors=sectors,
            limit=limit
        ):
            logger.info("Market news request")

            # Normalize symbols
            if symbols:
                symbols = [s.upper().strip() for s in symbols]

            # Check cache
            cache_key_str = cache_key("market", str(symbols), str(sectors), str(keywords), min_relevance, limit)
            cached_data = await get_cached_news(cache_key_str, ttl=180)  # 3 minute cache

            if cached_data:
                logger.info("Returning cached market news")
                return NewsResponse(**cached_data, cached=True)

            # Get news client
            news_client = await get_news_client()

            # Fetch market news
            articles = await news_client.get_market_news(
                symbols=symbols,
                sectors=sectors,
                limit=limit
            )

            # Filter by relevance score
            filtered_articles = [
                article for article in articles
                if article.relevance_score >= min_relevance
            ]

            # Convert to response format
            article_responses = [article_to_response(article) for article in filtered_articles]

            sources_used = list(set(article.provider for article in filtered_articles))

            response = NewsResponse(
                articles=article_responses,
                total_results=len(article_responses),
                page=1,
                page_size=len(article_responses),
                has_more=False,
                sources_used=sources_used,
                query_time_ms=int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000),
                cached=False
            )

            # Cache response
            await set_cached_news(cache_key_str, response.dict(exclude={'cached'}), ttl=180)

            logger.info(
                "Market news retrieved",
                articles=len(article_responses),
                filtered_from=len(articles),
                sources=len(sources_used)
            )

            return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Market news retrieval failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve market news"
        )


@router.get(
    "/company/{symbol}",
    response_model=CompanyNewsResponse,
    summary="Get Company News",
    description="""
    Get news articles specific to a company or stock symbol.

    **Features:**
    - Company-specific filtering
    - Sentiment analysis summary
    - Stock symbol recognition
    - Relevance scoring
    """
)
async def get_company_news(
    symbol: str,
    limit: int = Query(default=30, ge=1, le=100, description="Maximum articles"),
    days: int = Query(default=7, ge=1, le=30, description="Days to look back"),
    min_relevance: float = Query(default=0.4, ge=0.0, le=1.0, description="Minimum relevance"),
    security_context: SecurityContext = Depends(get_security_context)
) -> CompanyNewsResponse:
    """Get company-specific news"""

    start_time = datetime.now(timezone.utc)

    try:
        symbol = symbol.upper().strip()

        with structlog.contextvars.bound_contextvars(
            user_id=security_context.user_id,
            symbol=symbol,
            limit=limit,
            days=days
        ):
            logger.info("Company news request")

            # Check cache
            cache_key_str = cache_key("company", symbol, limit, days, min_relevance)
            cached_data = await get_cached_news(cache_key_str, ttl=300)

            if cached_data:
                logger.info("Returning cached company news")
                return CompanyNewsResponse(**cached_data)

            # Get news client
            news_client = await get_news_client()

            # Create date range
            to_date = datetime.now(timezone.utc)
            from_date = to_date - timedelta(days=days)

            # Search for company news
            articles = await news_client.search_news(
                query=symbol,
                news_filter=NewsFilter(
                    stock_symbols=[symbol],
                    from_date=from_date,
                    to_date=to_date,
                    min_relevance_score=min_relevance,
                    page_size=limit,
                    sort_by="publishedAt"
                )
            )

            # Filter and sort by relevance
            relevant_articles = [
                article for article in articles
                if symbol in article.stock_symbols or symbol.lower() in article.title.lower()
            ]
            relevant_articles.sort(key=lambda x: x.relevance_score, reverse=True)

            # Convert to response format
            article_responses = [article_to_response(article) for article in relevant_articles[:limit]]

            # Calculate sentiment summary
            sentiment_scores = [a.sentiment_score for a in relevant_articles if a.sentiment_score is not None]
            sentiment_summary = {
                "total_articles": len(article_responses),
                "articles_with_sentiment": len(sentiment_scores),
                "average_sentiment": sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0.0,
                "positive_articles": len([s for s in sentiment_scores if s > 0.1]) if sentiment_scores else 0,
                "negative_articles": len([s for s in sentiment_scores if s < -0.1]) if sentiment_scores else 0,
                "neutral_articles": len([s for s in sentiment_scores if -0.1 <= s <= 0.1]) if sentiment_scores else 0
            }

            response = CompanyNewsResponse(
                symbol=symbol,
                company_name=None,  # Could be looked up from database
                articles=article_responses,
                total_articles=len(article_responses),
                sentiment_summary=sentiment_summary,
                timestamp=datetime.now(timezone.utc)
            )

            # Cache response
            await set_cached_news(cache_key_str, response.dict(), ttl=300)

            logger.info(
                "Company news retrieved",
                symbol=symbol,
                articles=len(article_responses),
                avg_sentiment=sentiment_summary["average_sentiment"]
            )

            return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Company news retrieval failed", symbol=symbol, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve company news"
        )


@router.get(
    "/trending",
    response_model=TrendingTopicsResponse,
    summary="Get Trending Topics",
    description="""
    Get trending topics and keywords from recent news.

    **Features:**
    - Topic frequency analysis
    - Time-based trending
    - Market-focused topics
    - Keyword extraction
    """
)
async def get_trending_topics(
    limit: int = Query(default=20, ge=1, le=50, description="Number of topics"),
    hours: int = Query(default=24, ge=1, le=168, description="Time window in hours"),
    security_context: SecurityContext = Depends(get_security_context)
) -> TrendingTopicsResponse:
    """Get trending topics"""

    try:
        with structlog.contextvars.bound_contextvars(
            user_id=security_context.user_id,
            limit=limit,
            hours=hours
        ):
            logger.info("Trending topics request")

            # Check cache
            cache_key_str = cache_key("trending", limit, hours)
            cached_data = await get_cached_news(cache_key_str, ttl=1800)  # 30 minute cache

            if cached_data:
                logger.info("Returning cached trending topics")
                return TrendingTopicsResponse(**cached_data)

            # Get news client
            news_client = await get_news_client()

            # Get trending topics
            trending_topics = await news_client.get_trending_topics(limit=limit)

            response = TrendingTopicsResponse(
                topics=trending_topics,
                total_topics=len(trending_topics),
                timestamp=datetime.now(timezone.utc),
                time_period=f"{hours} hours"
            )

            # Cache response
            await set_cached_news(cache_key_str, response.dict(), ttl=1800)

            logger.info("Trending topics retrieved", topics=len(trending_topics))
            return response

    except Exception as e:
        logger.error("Trending topics retrieval failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve trending topics"
        )


@router.get(
    "/sources",
    response_model=NewsSourcesResponse,
    summary="Get News Sources",
    description="""
    Get information about available news sources and providers.

    **Features:**
    - Available news sources
    - Provider status
    - Source capabilities
    - Configuration info
    """
)
async def get_news_sources(
    security_context: SecurityContext = Depends(get_security_context)
) -> NewsSourcesResponse:
    """Get available news sources"""

    try:
        with structlog.contextvars.bound_contextvars(
            user_id=security_context.user_id
        ):
            logger.info("News sources request")

            # Check cache
            cache_key_str = cache_key("sources")
            cached_data = await get_cached_news(cache_key_str, ttl=3600)  # 1 hour cache

            if cached_data:
                return NewsSourcesResponse(**cached_data)

            # Get news client
            news_client = await get_news_client()

            # Get client stats to determine available sources
            stats = news_client.get_client_stats()

            # Mock sources data (in real implementation, query actual sources)
            sources = [
                {
                    "id": "newsapi",
                    "name": "NewsAPI.org",
                    "description": "Professional news aggregation service",
                    "category": "general",
                    "language": "en",
                    "country": "us",
                    "enabled": True
                },
                {
                    "id": "economic-times",
                    "name": "Economic Times",
                    "description": "Indian business and financial news",
                    "category": "business",
                    "language": "en",
                    "country": "in",
                    "enabled": True
                },
                {
                    "id": "moneycontrol",
                    "name": "Moneycontrol",
                    "description": "Indian financial markets news",
                    "category": "business",
                    "language": "en",
                    "country": "in",
                    "enabled": True
                }
            ]

            enabled_providers = ["newsapi", "rss", "fmp"]

            response = NewsSourcesResponse(
                sources=sources,
                total_sources=len(sources),
                enabled_providers=enabled_providers
            )

            # Cache response
            await set_cached_news(cache_key_str, response.dict(), ttl=3600)

            logger.info("News sources retrieved", sources=len(sources))
            return response

    except Exception as e:
        logger.error("News sources retrieval failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve news sources"
        )


# Health check endpoint
@router.get(
    "/health",
    summary="News Service Health Check",
    description="Check the health status of news providers and services"
)
async def news_health_check(
    security_context: SecurityContext = Depends(get_security_context)
) -> Dict[str, Any]:
    """Check news service health"""

    try:
        # Get news client
        news_client = await get_news_client()

        # Perform health check
        health_status = await news_client.health_check()

        logger.info("News health check completed", status=health_status.get("overall_status"))
        return health_status

    except Exception as e:
        logger.error("News health check failed", error=str(e))
        return {
            "overall_status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# Initialization function
def init_news_routes(
    db_manager: DatabaseManager,
    cache_manager: CacheManager,
    news_config: Optional[NewsConfig] = None
) -> APIRouter:
    """Initialize news routes"""
    global _db_manager, _cache_manager, _news_client

    _db_manager = db_manager
    _cache_manager = cache_manager

    # Initialize news client with config
    try:
        config = news_config or NewsConfig()
        _news_client = NewsClient(config)
        logger.info("News routes initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize news client", error=str(e))
        _news_client = None

    return router


# Export
__all__ = [
    "router",
    "init_news_routes",
    "NewsSearchRequest",
    "MarketNewsRequest",
    "NewsResponse",
    "NewsArticleResponse",
    "CompanyNewsResponse",
    "TrendingTopicsResponse",
    "NewsSourcesResponse",
    "NewsCategory",
    "NewsSortBy",
    "NewsProvider"
]
