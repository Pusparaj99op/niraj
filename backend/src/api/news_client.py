"""
News API Client
A comprehensive client for multiple news APIs with robust error handling and monitoring
Supports NewsAPI, Financial Modeling Prep, Alpha Vantage News, and custom RSS feeds
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import hashlib
import secrets
import re
from urllib.parse import urlparse

import httpx
import feedparser
from pydantic import BaseModel, Field, field_validator

try:
    from ..utils.logger import get_logger, log_performance, LogContext
except ImportError:
    # Fallback for standalone usage
    import logging

    def get_logger(name: str) -> logging.Logger:
        """Simple logger fallback"""
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
        """Simple performance logging decorator fallback"""

        def decorator(func):
            return func

        return decorator

    class LogContext:
        """Simple context manager fallback"""

        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass


class NewsAPIConfig(BaseModel):
    """NewsAPI.org configuration"""

    enabled: bool = Field(default=True)
    base_url: str = Field(default="https://newsapi.org/v2")
    api_key: Optional[str] = None
    timeout: int = Field(default=15)
    max_retries: int = Field(default=3)
    retry_delay: float = Field(default=1.0)
    rate_limit_requests_per_day: int = Field(default=1000)  # Free tier limit
    rate_limit_requests_per_hour: int = Field(default=100)
    cache_duration_minutes: int = Field(default=15)


class FinancialModelingPrepConfig(BaseModel):
    """Financial Modeling Prep configuration"""

    enabled: bool = Field(default=False)
    base_url: str = Field(default="https://financialmodelingprep.com/api/v3")
    api_key: Optional[str] = None
    timeout: int = Field(default=20)
    max_retries: int = Field(default=3)
    retry_delay: float = Field(default=1.0)
    rate_limit_requests_per_minute: int = Field(default=250)  # Varies by plan
    cache_duration_minutes: int = Field(default=30)


class AlphaVantageConfig(BaseModel):
    """Alpha Vantage News configuration"""

    enabled: bool = Field(default=False)
    base_url: str = Field(default="https://www.alphavantage.co/query")
    api_key: Optional[str] = None
    timeout: int = Field(default=15)
    max_retries: int = Field(default=3)
    retry_delay: float = Field(default=1.0)
    rate_limit_requests_per_minute: int = Field(default=5)  # Free tier limit
    cache_duration_minutes: int = Field(default=60)


class RSSFeedConfig(BaseModel):
    """RSS Feed configuration"""

    enabled: bool = Field(default=True)
    feeds: List[Dict[str, str]] = Field(
        default_factory=lambda: [
            {
                "name": "Economic Times Markets",
                "url": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
            },
            {
                "name": "Moneycontrol Markets",
                "url": "https://www.moneycontrol.com/rss/markets.xml",
            },
            {
                "name": "Business Standard Markets",
                "url": "https://www.business-standard.com/rss/markets-106.rss",
            },
            {
                "name": "Reuters Business",
                "url": "https://feeds.reuters.com/reuters/businessNews",
            },
            {
                "name": "Yahoo Finance",
                "url": "https://feeds.finance.yahoo.com/rss/2.0/headline",
            },
        ]
    )
    timeout: int = Field(default=20)
    max_retries: int = Field(default=3)
    retry_delay: float = Field(default=2.0)
    cache_duration_minutes: int = Field(default=10)  # RSS feeds update frequently


class NewsConfig(BaseModel):
    """Complete News API configuration"""

    default_language: str = Field(default="en")
    default_country: str = Field(default="in")  # India focus
    default_category: str = Field(default="business")
    max_articles_per_request: int = Field(default=100)
    enable_sentiment_analysis: bool = Field(
        default=False
    )  # Can be enabled with AI integration
    enable_content_filtering: bool = Field(default=True)

    # Source configurations
    newsapi: NewsAPIConfig = Field(default_factory=NewsAPIConfig)
    fmp: FinancialModelingPrepConfig = Field(
        default_factory=FinancialModelingPrepConfig
    )
    alphavantage: AlphaVantageConfig = Field(default_factory=AlphaVantageConfig)
    rss: RSSFeedConfig = Field(default_factory=RSSFeedConfig)


class Article(BaseModel):
    """Standardized article model"""

    source: str
    provider: str  # NewsAPI, FMP, RSS, etc.
    title: str
    description: Optional[str] = None
    content: Optional[str] = None
    url: str
    image_url: Optional[str] = None
    author: Optional[str] = None
    published_at: datetime
    category: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    sentiment_score: Optional[float] = None  # -1 to 1, if sentiment analysis enabled
    relevance_score: Optional[float] = None  # 0 to 1, calculated relevance to trading

    @field_validator("published_at", mode="before")
    @classmethod
    def parse_published_at(cls, v):
        if isinstance(v, str):
            # Handle various date formats
            formats = [
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%dT%H:%M:%S.%fZ",
                "%Y-%m-%d %H:%M:%S",
                "%a, %d %b %Y %H:%M:%S %Z",
                "%a, %d %b %Y %H:%M:%S %z",
            ]
            for fmt in formats:
                try:
                    return datetime.strptime(v, fmt)
                except ValueError:
                    continue
            # Fallback to current time if parsing fails
            return datetime.now()
        return v


class NewsFilter(BaseModel):
    """News filtering and search parameters"""

    keywords: Optional[List[str]] = None
    exclude_keywords: Optional[List[str]] = None
    sources: Optional[List[str]] = None  # Specific news sources
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    category: Optional[str] = None
    language: Optional[str] = None
    country: Optional[str] = None
    sort_by: str = Field(default="publishedAt")  # publishedAt, relevancy, popularity
    page_size: int = Field(default=20, le=100)
    page: int = Field(default=1)

    # Trading-specific filters
    min_relevance_score: Optional[float] = Field(default=None, ge=0, le=1)
    stock_symbols: Optional[List[str]] = None  # Filter by stock symbols mentioned
    market_sectors: Optional[List[str]] = None  # Filter by market sectors


class RateLimiter:
    """Multi-provider rate limiting implementation"""

    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: List[float] = []

    async def wait_if_needed(self) -> None:
        """Wait if rate limit is exceeded"""
        now = time.time()

        # Clean old requests
        self.requests = [
            req_time
            for req_time in self.requests
            if now - req_time < self.window_seconds
        ]

        if len(self.requests) >= self.max_requests:
            # Calculate wait time
            oldest_request = min(self.requests)
            wait_time = self.window_seconds - (now - oldest_request)
            if wait_time > 0:
                await asyncio.sleep(wait_time)
                # Clean again after waiting
                now = time.time()
                self.requests = [
                    req_time
                    for req_time in self.requests
                    if now - req_time < self.window_seconds
                ]

        # Record this request
        self.requests.append(now)


class NewsCache:
    """In-memory cache for news articles"""

    def __init__(self):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.expiry: Dict[str, datetime] = {}

    def _generate_key(
        self, provider: str, endpoint: str, params: Dict[str, Any]
    ) -> str:
        """Generate cache key from request parameters"""
        sorted_params = json.dumps(params, sort_keys=True, default=str)
        return hashlib.md5(
            f"{provider}:{endpoint}:{sorted_params}".encode()
        ).hexdigest()

    def get(
        self, provider: str, endpoint: str, params: Dict[str, Any]
    ) -> Optional[Any]:
        """Get cached data if not expired"""
        key = self._generate_key(provider, endpoint, params)

        if key not in self.cache:
            return None

        if key in self.expiry and datetime.now() > self.expiry[key]:
            # Cache expired
            del self.cache[key]
            del self.expiry[key]
            return None

        return self.cache[key]

    def set(
        self,
        provider: str,
        endpoint: str,
        params: Dict[str, Any],
        data: Any,
        ttl_minutes: int,
    ) -> None:
        """Cache data with TTL"""
        key = self._generate_key(provider, endpoint, params)
        self.cache[key] = data
        self.expiry[key] = datetime.now() + timedelta(minutes=ttl_minutes)

    def clear(self) -> None:
        """Clear all cache"""
        self.cache.clear()
        self.expiry.clear()

    def clear_expired(self) -> None:
        """Clear expired cache entries"""
        now = datetime.now()
        expired_keys = [key for key, exp_time in self.expiry.items() if now > exp_time]
        for key in expired_keys:
            self.cache.pop(key, None)
            self.expiry.pop(key, None)


class NewsError(Exception):
    """Base exception for News API errors"""

    def __init__(
        self,
        message: str,
        provider: Optional[str] = None,
        error_code: Optional[str] = None,
        status_code: Optional[int] = None,
        response_data: Optional[Dict] = None,
    ):
        super().__init__(message)
        self.message = message
        self.provider = provider
        self.error_code = error_code
        self.status_code = status_code
        self.response_data = response_data or {}


class AuthenticationError(NewsError):
    """API authentication errors"""

    pass


class RateLimitError(NewsError):
    """Rate limit exceeded errors"""

    pass


class ValidationError(NewsError):
    """Request validation errors"""

    pass


class NetworkError(NewsError):
    """Network related errors"""

    pass


class ParsingError(NewsError):
    """Data parsing errors"""

    pass


class NewsClient:
    """
    Comprehensive Multi-Provider News Client

    Features:
    - Support for multiple news providers (NewsAPI, FMP, Alpha Vantage, RSS) - Advanced error handling with provider-specific exceptions - Multi-level rate limiting per provider - Intelligent caching with per-provider TTL - Article standardization and deduplication - Trading-focused content filtering and relevance scoring - Async operations with proper connection pooling - Comprehensive logging and monitoring - Content sentiment analysis (when AI is enabled) -
    RSS feed parsing and normalization
    """

    def __init__(self, config: Optional[NewsConfig] = None):
        """
        Initialize News client with multi-provider support

        Args:
            config: News configuration with provider settings
        """
        self.config = config or NewsConfig()
        self.logger = get_logger("niraj.news")

        # Session management
        self.session_id = secrets.token_hex(16)
        self.clients: Dict[str, httpx.AsyncClient] = {}

        # Rate limiters per provider
        self.rate_limiters = {
            "newsapi": RateLimiter(
                max_requests=min(
                    self.config.newsapi.rate_limit_requests_per_hour,
                    self.config.newsapi.rate_limit_requests_per_day // 24,
                ),
                window_seconds=3600,
            ),
            "fmp": RateLimiter(
                max_requests=self.config.fmp.rate_limit_requests_per_minute,
                window_seconds=60,
            ),
            "alphavantage": RateLimiter(
                max_requests=self.config.alphavantage.rate_limit_requests_per_minute,
                window_seconds=60,
            ),
            "rss": RateLimiter(
                max_requests=60, window_seconds=60  # Conservative for RSS feeds
            ),
        }

        # Caching
        self.cache = NewsCache()

        # Article deduplication
        self.seen_articles: set = set()  # Track article URLs to avoid duplicates

        # Statistics
        self.stats = {
            "requests_made": 0,
            "articles_fetched": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "errors": 0,
            "providers_used": set(),
        }

    async def _get_client(self, provider: str, timeout: int = 15) -> httpx.AsyncClient:
        """Get or create HTTP client for specific provider"""
        if provider not in self.clients or self.clients[provider].is_closed:
            limits = httpx.Limits(max_keepalive_connections=10, max_connections=50)
            timeout_config = httpx.Timeout(timeout)

            self.clients[provider] = httpx.AsyncClient(
                timeout=timeout_config,
                limits=limits,
                http2=True,
                follow_redirects=True,
                headers={
                    "User-Agent": "NIRAJ-Trading-System/1.0 (News Aggregator)",
                    "Accept": "application/json",
                    "Accept-Encoding": "gzip, deflate",
                },
            )

        return self.clients[provider]

    async def _make_request(
        self,
        provider: str,
        method: str,
        url: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        timeout: int = 15,
        retries: int = 3,
        cache_ttl: int = 15,
    ) -> Dict[str, Any]:
        """
        Make HTTP request with error handling, retries, and caching

        Args:
            provider: Provider name for rate limiting and caching
            method: HTTP method
            url: Request URL
            params: Query parameters
            headers: Additional headers
            timeout: Request timeout
            retries: Number of retries
            cache_ttl: Cache TTL in minutes

        Returns:
            Response data as dictionary

        Raises:
            Various NewsError subclasses based on error type
        """
        # Check cache first
        cache_key = f"{method}:{url}"
        cached_data = self.cache.get(provider, cache_key, params or {})
        if cached_data:
            self.stats["cache_hits"] += 1
            return cached_data

        self.stats["cache_misses"] += 1

        # Apply rate limiting
        if provider in self.rate_limiters:
            await self.rate_limiters[provider].wait_if_needed()

        client = await self._get_client(provider, timeout)

        with LogContext(
            session_id=self.session_id,
            provider=provider,
            method=method,
            url=urlparse(url).path,
            request_id=secrets.token_hex(8),
        ):
            self.logger.debug(
                f"Making {method} request to {provider}: {urlparse(url).path}"
            )

            for attempt in range(retries + 1):
                try:
                    # Make request
                    if method.upper() == "GET":
                        response = await client.get(url, params=params, headers=headers)
                    elif method.upper() == "POST":
                        response = await client.post(url, json=params, headers=headers)
                    else:
                        raise ValidationError(
                            f"Unsupported HTTP method: {method}", provider
                        )

                    self.stats["requests_made"] += 1
                    self.stats["providers_used"].add(provider)

                    # Handle response
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            # Cache successful response
                            self.cache.set(
                                provider, cache_key, params or {}, data, cache_ttl
                            )
                            return data
                        except json.JSONDecodeError:
                            # Some providers return non-JSON data
                            text_data = response.text
                            result = {
                                "content": text_data,
                                "content_type": response.headers.get("content-type"),
                            }
                            self.cache.set(
                                provider, cache_key, params or {}, result, cache_ttl
                            )
                            return result

                    elif response.status_code == 401:
                        raise AuthenticationError(
                            f"Authentication failed for {provider}",
                            provider,
                            status_code=response.status_code,
                        )

                    elif response.status_code == 403:
                        raise AuthenticationError(
                            f"API key invalid or insufficient permissions for {provider}",
                            provider,
                            status_code=response.status_code,
                        )

                    elif response.status_code == 429:
                        if attempt < retries:
                            wait_time = (
                                2**attempt
                            ) * 2  # Exponential backoff for rate limits
                            self.logger.warning(
                                f"{provider} rate limit hit, waiting {wait_time}s"
                            )
                            await asyncio.sleep(wait_time)
                            continue
                        raise RateLimitError(
                            f"Rate limit exceeded for {provider}",
                            provider,
                            status_code=response.status_code,
                        )

                    elif response.status_code >= 500:
                        if attempt < retries:
                            wait_time = (2**attempt) * 1.5
                            self.logger.warning(
                                f"{provider} server error, retrying in {wait_time}s"
                            )
                            await asyncio.sleep(wait_time)
                            continue
                        raise NewsError(
                            f"Server error from {provider}: {response.status_code}",
                            provider,
                            status_code=response.status_code,
                        )

                    else:
                        raise NewsError(
                            f"HTTP {response.status_code} from {provider}: {response.text[:100]}",
                            provider,
                            status_code=response.status_code,
                        )

                except httpx.TimeoutException:
                    if attempt < retries:
                        wait_time = 2**attempt
                        self.logger.warning(
                            f"{provider} timeout, retrying in {wait_time}s"
                        )
                        await asyncio.sleep(wait_time)
                        continue
                    raise NetworkError(f"Timeout connecting to {provider}", provider)

                except httpx.NetworkError as e:
                    if attempt < retries:
                        wait_time = 2**attempt
                        self.logger.warning(
                            f"{provider} network error: {e}, retrying in {wait_time}s"
                        )
                        await asyncio.sleep(wait_time)
                        continue
                    raise NetworkError(
                        f"Network error connecting to {provider}: {e}", provider
                    )

            raise NewsError(f"All retry attempts failed for {provider}", provider)

    def _calculate_relevance_score(self, article: Dict[str, Any]) -> float:
        """
        Calculate relevance score for trading/finance based on content

        Args:
            article: Article data dictionary

        Returns:
            Relevance score between 0 and 1
        """
        # Trading/finance related keywords with weights
        finance_keywords = {
            # High relevance
            "stock": 1.0,
            "market": 1.0,
            "trading": 1.0,
            "shares": 1.0,
            "equity": 1.0,
            "bond": 1.0,
            "commodity": 1.0,
            "currency": 1.0,
            "nse": 1.0,
            "bse": 1.0,
            "sensex": 1.0,
            "nifty": 1.0,
            "investment": 0.9,
            "investor": 0.9,
            "portfolio": 0.9,
            "dividend": 0.9,
            "earnings": 0.9,
            "revenue": 0.9,
            "profit": 0.9,
            # Medium relevance
            "financial": 0.8,
            "economy": 0.8,
            "economic": 0.8,
            "fiscal": 0.8,
            "banking": 0.8,
            "insurance": 0.8,
            "mutual fund": 0.8,
            "rbi": 0.8,
            "sebi": 0.8,
            "fed": 0.8,
            "central bank": 0.8,
            # Lower relevance
            "business": 0.6,
            "company": 0.6,
            "corporate": 0.6,
            "industry": 0.6,
            "growth": 0.5,
            "development": 0.5,
            "inflation": 0.7,
            "gdp": 0.7,
        }

        # Get title and description
        title = article.get("title", "").lower()
        description = article.get("description", "").lower()
        content = f"{title} {description}"

        # Calculate score
        score = 0.0
        keyword_matches = 0

        for keyword, weight in finance_keywords.items():
            if keyword in content:
                score += weight
                keyword_matches += 1

        # Normalize score (max possible score based on keyword matches)
        if keyword_matches > 0:
            max_possible = min(keyword_matches * 1.0, 5.0)  # Cap at 5 keywords
            score = min(score / max_possible, 1.0)

        # Boost score if multiple finance terms present
        if keyword_matches >= 3:
            score = min(score * 1.2, 1.0)

        return round(score, 3)

    def _extract_stock_symbols(self, text: str) -> List[str]:
        """
        Extract potential stock symbols from text

        Args:
            text: Text content to analyze

        Returns:
            List of potential stock symbols found
        """
        # Common patterns for Indian stock symbols
        patterns = [
            r"\b[A-Z]{2,6}\b",  # Basic pattern for symbols
            r"\$[A-Z]{1,5}\b",  # Symbols with $ prefix
            r"\b[A-Z]+\.NS\b",  # NSE symbols
            r"\b[A-Z]+\.BO\b",  # BSE symbols
        ]

        symbols = set()
        text_upper = text.upper()

        for pattern in patterns:
            matches = re.findall(pattern, text_upper)
            symbols.update(matches)

        # Filter out common words that might match pattern
        common_words = {
            "THE",
            "AND",
            "FOR",
            "ARE",
            "BUT",
            "NOT",
            "YOU",
            "ALL",
            "CAN",
            "HER",
            "WAS",
            "ONE",
            "OUR",
            "HAD",
            "BY",
            "TWO",
            "WHO",
            "OIL",
            "NEW",
            "MAY",
            "HAS",
            "HIS",
            "FROM",
            "THEY",
            "SHE",
            "OR",
            "AN",
            "MY",
            "SO",
            "UP",
            "OUT",
            "IF",
            "ABOUT",
            "GET",
            "GO",
            "ME",
            "US",
            "AM",
            "ON",
            "NO",
            "TO",
        }

        return [
            symbol
            for symbol in symbols
            if symbol not in common_words and len(symbol) >= 2
        ]

    def _standardize_newsapi_article(self, article: Dict[str, Any]) -> Article:
        """Convert NewsAPI article to standardized format"""
        return Article(
            source=article.get("source", {}).get("name", "Unknown"),
            provider="newsapi",
            title=article.get("title", ""),
            description=article.get("description"),
            content=article.get("content"),
            url=article.get("url", ""),
            image_url=article.get("urlToImage"),
            author=article.get("author"),
            published_at=article.get("publishedAt", datetime.now().isoformat()),
            category="business",  # NewsAPI business category
            relevance_score=self._calculate_relevance_score(article),
        )

    def _standardize_fmp_article(self, article: Dict[str, Any]) -> Article:
        """Convert Financial Modeling Prep article to standardized format"""
        return Article(
            source=article.get("site", "Financial Modeling Prep"),
            provider="fmp",
            title=article.get("title", ""),
            description=(
                article.get("text", "")[:200] + "..." if article.get("text") else None
            ),
            content=article.get("text"),
            url=article.get("url", ""),
            image_url=article.get("image"),
            author=None,  # FMP doesn't provide author
            published_at=article.get("publishedDate", datetime.now().isoformat()),
            category="financial",
            relevance_score=self._calculate_relevance_score(article),
        )

    def _standardize_rss_article(self, entry: Any, feed_name: str) -> Article:
        """Convert RSS feed entry to standardized format"""
        return Article(
            source=feed_name,
            provider="rss",
            title=getattr(entry, "title", ""),
            description=getattr(entry, "summary", None),
            content=getattr(entry, "description", getattr(entry, "summary", None)),
            url=getattr(entry, "link", ""),
            image_url=None,  # RSS feeds may not have images
            author=getattr(entry, "author", None),
            published_at=getattr(entry, "published", datetime.now().isoformat()),
            category="business",
            relevance_score=self._calculate_relevance_score(
                {
                    "title": getattr(entry, "title", ""),
                    "description": getattr(entry, "summary", ""),
                }
            ),
        )

    # Public API Methods

    @log_performance("news_get_headlines")
    async def get_headlines(
        self,
        news_filter: Optional[NewsFilter] = None,
        providers: Optional[List[str]] = None,
    ) -> List[Article]:
        """
        Get top headlines from multiple providers

        Args:
            news_filter: Filtering parameters
            providers: List of providers to use (newsapi, fmp, rss)

        Returns:
            List of standardized Article objects
        """
        if news_filter is None:
            news_filter = NewsFilter()

        if providers is None:
            providers = ["newsapi", "rss"]  # Default providers

        all_articles = []

        # NewsAPI Headlines
        if (
            "newsapi" in providers
            and self.config.newsapi.enabled
            and self.config.newsapi.api_key
        ):
            try:
                newsapi_articles = await self._get_newsapi_headlines(news_filter)
                all_articles.extend(newsapi_articles)
            except Exception as e:
                self.logger.error(f"Failed to fetch NewsAPI headlines: {e}")
                self.stats["errors"] += 1

        # RSS Feed Headlines
        if "rss" in providers and self.config.rss.enabled:
            try:
                rss_articles = await self._get_rss_headlines(news_filter)
                all_articles.extend(rss_articles)
            except Exception as e:
                self.logger.error(f"Failed to fetch RSS headlines: {e}")
                self.stats["errors"] += 1

        # Financial Modeling Prep
        if "fmp" in providers and self.config.fmp.enabled and self.config.fmp.api_key:
            try:
                fmp_articles = await self._get_fmp_news(news_filter)
                all_articles.extend(fmp_articles)
            except Exception as e:
                self.logger.error(f"Failed to fetch FMP news: {e}")
                self.stats["errors"] += 1

        # Remove duplicates and sort by relevance/time
        unique_articles = self._deduplicate_articles(all_articles)
        sorted_articles = self._sort_articles(unique_articles, news_filter.sort_by)

        # Apply additional filtering
        filtered_articles = self._apply_filters(sorted_articles, news_filter)

        self.stats["articles_fetched"] += len(filtered_articles)
        self.logger.info(
            f"Fetched {len(filtered_articles)} unique articles from {len(providers)} providers"
        )

        return filtered_articles

    async def _get_newsapi_headlines(self, news_filter: NewsFilter) -> List[Article]:
        """Fetch headlines from NewsAPI"""
        params = {
            "apiKey": self.config.newsapi.api_key,
            "pageSize": min(news_filter.page_size, 100),
            "page": news_filter.page,
            "sortBy": news_filter.sort_by,
        }

        # Add filters
        if news_filter.keywords:
            params["q"] = " OR ".join(news_filter.keywords)

        if news_filter.category:
            params["category"] = news_filter.category
        else:
            params["category"] = self.config.default_category

        if news_filter.country:
            params["country"] = news_filter.country
        else:
            params["country"] = self.config.default_country

        if news_filter.language:
            params["language"] = news_filter.language
        else:
            params["language"] = self.config.default_language

        if news_filter.sources:
            params["sources"] = ",".join(news_filter.sources)

        url = f"{self.config.newsapi.base_url}/top-headlines"

        response = await self._make_request(
            "newsapi",
            "GET",
            url,
            params,
            timeout=self.config.newsapi.timeout,
            retries=self.config.newsapi.max_retries,
            cache_ttl=self.config.newsapi.cache_duration_minutes,
        )

        articles = []
        for article_data in response.get("articles", []):
            try:
                article = self._standardize_newsapi_article(article_data)
                articles.append(article)
            except Exception as e:
                self.logger.warning(f"Failed to parse NewsAPI article: {e}")
                continue

        return articles

    async def _get_rss_headlines(self, news_filter: NewsFilter) -> List[Article]:
        """Fetch headlines from RSS feeds"""
        articles = []

        for feed_config in self.config.rss.feeds:
            try:
                feed_name = feed_config["name"]
                feed_url = feed_config["url"]

                # Make request to RSS feed
                response = await self._make_request(
                    "rss",
                    "GET",
                    feed_url,
                    timeout=self.config.rss.timeout,
                    retries=self.config.rss.max_retries,
                    cache_ttl=self.config.rss.cache_duration_minutes,
                )

                # Parse RSS content
                if "content" in response:
                    feed = feedparser.parse(response["content"])

                    for entry in feed.entries[: news_filter.page_size]:
                        try:
                            article = self._standardize_rss_article(entry, feed_name)
                            articles.append(article)
                        except Exception as e:
                            self.logger.warning(
                                f"Failed to parse RSS entry from {feed_name}: {e}"
                            )
                            continue

            except Exception as e:
                self.logger.error(
                    f"Failed to fetch RSS feed {feed_config['name']}: {e}"
                )
                continue

        return articles

    async def _get_fmp_news(self, news_filter: NewsFilter) -> List[Article]:
        """Fetch news from Financial Modeling Prep"""
        params = {
            "apikey": self.config.fmp.api_key,
            "limit": min(news_filter.page_size, 100),
            "page": news_filter.page - 1,  # FMP uses 0-based pages
        }

        # Add date filters if specified
        if news_filter.from_date:
            params["from"] = news_filter.from_date.strftime("%Y-%m-%d")
        if news_filter.to_date:
            params["to"] = news_filter.to_date.strftime("%Y-%m-%d")

        url = f"{self.config.fmp.base_url}/fmp/articles"

        response = await self._make_request(
            "fmp",
            "GET",
            url,
            params,
            timeout=self.config.fmp.timeout,
            retries=self.config.fmp.max_retries,
            cache_ttl=self.config.fmp.cache_duration_minutes,
        )

        articles = []
        for article_data in response if isinstance(response, list) else []:
            try:
                article = self._standardize_fmp_article(article_data)
                articles.append(article)
            except Exception as e:
                self.logger.warning(f"Failed to parse FMP article: {e}")
                continue

        return articles

    def _deduplicate_articles(self, articles: List[Article]) -> List[Article]:
        """Remove duplicate articles based on URL and title similarity"""
        unique_articles = []
        seen_urls = set()
        seen_titles = set()

        for article in articles:
            # Skip if URL already seen
            if article.url in seen_urls:
                continue

            # Check for similar titles (simple approach)
            title_key = re.sub(r"[^\w\s]", "", article.title.lower()).strip()
            if title_key in seen_titles:
                continue

            seen_urls.add(article.url)
            seen_titles.add(title_key)
            unique_articles.append(article)

        return unique_articles

    def _sort_articles(self, articles: List[Article], sort_by: str) -> List[Article]:
        """Sort articles by specified criteria"""
        if sort_by == "publishedAt":
            return sorted(articles, key=lambda x: x.published_at, reverse=True)
        elif sort_by == "relevancy":
            return sorted(articles, key=lambda x: x.relevance_score or 0, reverse=True)
        elif sort_by == "popularity":
            # Use relevance score as proxy for popularity
            return sorted(articles, key=lambda x: x.relevance_score or 0, reverse=True)
        else:
            return articles

    def _apply_filters(
        self, articles: List[Article], news_filter: NewsFilter
    ) -> List[Article]:
        """Apply additional filters to articles"""
        filtered = articles

        # Filter by minimum relevance score
        if news_filter.min_relevance_score is not None:
            filtered = [
                a
                for a in filtered
                if (a.relevance_score or 0) >= news_filter.min_relevance_score
            ]

        # Filter by stock symbols mentioned
        if news_filter.stock_symbols:
            symbol_filtered = []
            for article in filtered:
                content_text = f"{article.title} {article.description or ''}"
                symbols = self._extract_stock_symbols(content_text)
                if any(symbol in news_filter.stock_symbols for symbol in symbols):
                    # Add found symbols as tags
                    article.tags.extend(symbols)
                    symbol_filtered.append(article)
            filtered = symbol_filtered

        # Filter by date range
        if news_filter.from_date:
            filtered = [a for a in filtered if a.published_at >= news_filter.from_date]

        if news_filter.to_date:
            filtered = [a for a in filtered if a.published_at <= news_filter.to_date]

        # Filter by keywords
        if news_filter.keywords:
            keyword_filtered = []
            for article in filtered:
                content_text = f"{article.title} {article.description or ''}".lower()
                if any(
                    keyword.lower() in content_text for keyword in news_filter.keywords
                ):
                    keyword_filtered.append(article)
            filtered = keyword_filtered

        # Exclude keywords
        if news_filter.exclude_keywords:
            exclude_filtered = []
            for article in filtered:
                content_text = f"{article.title} {article.description or ''}".lower()
                if not any(
                    keyword.lower() in content_text
                    for keyword in news_filter.exclude_keywords
                ):
                    exclude_filtered.append(article)
            filtered = exclude_filtered

        return filtered

    @log_performance("news_search")
    async def search_news(
        self,
        query: str,
        news_filter: Optional[NewsFilter] = None,
        providers: Optional[List[str]] = None,
    ) -> List[Article]:
        """
        Search for news articles by query

        Args:
            query: Search query string
            news_filter: Additional filtering parameters
            providers: List of providers to search

        Returns:
            List of matching articles
        """
        if news_filter is None:
            news_filter = NewsFilter()

        # Add query to keywords
        news_filter.keywords = news_filter.keywords or []
        news_filter.keywords.append(query)

        return await self.get_headlines(news_filter, providers)

    @log_performance("news_get_market_news")
    async def get_market_news(
        self,
        symbols: Optional[List[str]] = None,
        sectors: Optional[List[str]] = None,
        limit: int = 50,
    ) -> List[Article]:
        """
        Get market-specific news articles

        Args:
            symbols: Stock symbols to filter by
            sectors: Market sectors to filter by
            limit: Maximum articles to return

        Returns:
            List of market-related articles
        """
        # Create market-focused filter
        market_filter = NewsFilter(
            keywords=[
                "stock",
                "market",
                "trading",
                "shares",
                "nse",
                "bse",
                "sensex",
                "nifty",
            ],
            category="business",
            min_relevance_score=0.3,
            stock_symbols=symbols,
            market_sectors=sectors,
            page_size=limit,
            sort_by="relevancy",
        )

        return await self.get_headlines(market_filter)

    async def get_trending_topics(self, limit: int = 10) -> Dict[str, int]:
        """
        Get trending topics from recent news

        Args:
            limit: Maximum topics to return

        Returns:
            Dictionary of trending topics with counts
        """
        # Get recent articles
        recent_filter = NewsFilter(
            from_date=datetime.now() - timedelta(hours=24), page_size=100
        )

        articles = await self.get_headlines(recent_filter)

        # Extract and count topics from titles
        word_counts = {}
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "from",
            "up",
            "about",
            "into",
            "through",
            "during",
            "before",
            "after",
            "above",
            "below",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "must",
            "can",
            "this",
            "that",
        }

        for article in articles:
            words = re.findall(r"\b\w+\b", article.title.lower())
            for word in words:
                if len(word) > 3 and word not in stop_words:
                    word_counts[word] = word_counts.get(word, 0) + 1

        # Return top trending topics
        trending = dict(
            sorted(word_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
        )

        self.logger.info(f"Identified {len(trending)} trending topics")
        return trending

    async def health_check(self) -> Dict[str, Any]:
        """
        Check health of all enabled news providers

        Returns:
            Health status for each provider
        """
        health_status = {
            "overall_status": "healthy",
            "providers": {},
            "cache_status": {},
            "statistics": self.stats.copy(),
        }

        # Check NewsAPI
        if self.config.newsapi.enabled:
            try:
                if self.config.newsapi.api_key:
                    # Simple request to check API key validity
                    await self._make_request(
                        "newsapi",
                        "GET",
                        f"{self.config.newsapi.base_url}/top-headlines",
                        {
                            "apiKey": self.config.newsapi.api_key,
                            "pageSize": 1,
                            "country": "us",
                        },
                        cache_ttl=1,  # Short cache for health check
                    )
                    health_status["providers"]["newsapi"] = "healthy"
                else:
                    health_status["providers"]["newsapi"] = "not_configured"
            except Exception as e:
                health_status["providers"]["newsapi"] = f"error: {str(e)[:50]}"
                health_status["overall_status"] = "degraded"

        # Check RSS feeds (test first feed)
        if self.config.rss.enabled and self.config.rss.feeds:
            try:
                test_feed = self.config.rss.feeds[0]
                await self._make_request("rss", "GET", test_feed["url"], cache_ttl=1)
                health_status["providers"]["rss"] = "healthy"
            except Exception as e:
                health_status["providers"]["rss"] = f"error: {str(e)[:50]}"
                health_status["overall_status"] = "degraded"

        # Check FMP
        if self.config.fmp.enabled and self.config.fmp.api_key:
            try:
                await self._make_request(
                    "fmp",
                    "GET",
                    f"{self.config.fmp.base_url}/fmp/articles",
                    {"apikey": self.config.fmp.api_key, "limit": 1},
                    cache_ttl=1,
                )
                health_status["providers"]["fmp"] = "healthy"
            except Exception as e:
                health_status["providers"]["fmp"] = f"error: {str(e)[:50]}"
                health_status["overall_status"] = "degraded"

        # Cache statistics
        health_status["cache_status"] = {
            "cached_entries": len(self.cache.cache),
            "expired_entries": len(
                [k for k, v in self.cache.expiry.items() if datetime.now() > v]
            ),
        }

        self.logger.info(f"Health check completed: {health_status['overall_status']}")
        return health_status

    def get_client_stats(self) -> Dict[str, Any]:
        """Get comprehensive client statistics"""
        return {
            "session_id": self.session_id,
            "configuration": {
                "enabled_providers": [
                    provider
                    for provider in ["newsapi", "fmp", "alphavantage", "rss"]
                    if getattr(self.config, provider).enabled
                ],
                "cache_enabled": True,
                "default_language": self.config.default_language,
                "default_country": self.config.default_country,
            },
            "statistics": self.stats.copy(),
            "rate_limits": {
                provider: {
                    "requests_in_window": len(limiter.requests),
                    "max_requests": limiter.max_requests,
                    "window_seconds": limiter.window_seconds,
                }
                for provider, limiter in self.rate_limiters.items()
            },
            "cache_stats": {
                "entries": len(self.cache.cache),
                "expired_entries": len(
                    [k for k, v in self.cache.expiry.items() if datetime.now() > v]
                ),
            },
        }

    async def clear_cache(self) -> None:
        """Clear all cached data"""
        self.cache.clear()
        self.seen_articles.clear()
        self.logger.info("News cache cleared")

    async def close(self) -> None:
        """Close all HTTP clients and cleanup resources"""
        for provider, client in self.clients.items():
            if not client.is_closed:
                await client.aclose()

        self.clients.clear()
        self.logger.info("News client closed")

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    def __del__(self):
        """Destructor - ensure cleanup"""
        try:
            for client in self.clients.values():
                if not client.is_closed:
                    import warnings

                    warnings.warn(
                        "News client was not properly closed. Use async context manager or call close() explicitly."
                    )
        except Exception:
            pass
