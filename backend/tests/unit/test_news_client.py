"""
Unit Tests for News API Client
Comprehensive test coverage for all news providers and error scenarios
"""

import asyncio
import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

import httpx
import feedparser

# Import the news client
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api.news_client import (
    NewsClient,
    NewsConfig,
    NewsAPIConfig,
    RSSFeedConfig,
    FinancialModelingPrepConfig,
    Article,
    NewsFilter,
    RateLimiter,
    NewsCache,
    NewsError,
    AuthenticationError,
    RateLimitError,
    ValidationError,
    NetworkError,
    ParsingError,
)


class TestNewsCache:
    """Test NewsCache functionality"""

    def test_cache_basic_operations(self):
        """Test basic cache set/get operations"""
        cache = NewsCache()

        # Test cache miss
        assert cache.get("provider", "endpoint", {"param": "value"}) is None

        # Test cache set/get
        data = {"test": "data"}
        cache.set("provider", "endpoint", {"param": "value"}, data, 5)

        cached_data = cache.get("provider", "endpoint", {"param": "value"})
        assert cached_data == data

    def test_cache_expiry(self):
        """Test cache expiration"""
        cache = NewsCache()

        # Set data with very short TTL
        data = {"test": "data"}
        cache.set("provider", "endpoint", {}, data, 0)  # Expire immediately

        # Should return None due to expiry
        assert cache.get("provider", "endpoint", {}) is None

    def test_cache_key_generation(self):
        """Test cache key generation for different parameters"""
        cache = NewsCache()

        # Same parameters should generate same key
        data1 = {"test": "data1"}
        data2 = {"test": "data2"}

        cache.set("provider", "endpoint", {"a": 1, "b": 2}, data1, 5)
        cache.set(
            "provider", "endpoint", {"b": 2, "a": 1}, data2, 5
        )  # Same params, different order

        # Should get the second data (overwrote first)
        result = cache.get("provider", "endpoint", {"a": 1, "b": 2})
        assert result == data2


class TestRateLimiter:
    """Test RateLimiter functionality"""

    @pytest.mark.asyncio
    async def test_rate_limiter_basic(self):
        """Test basic rate limiting"""
        limiter = RateLimiter(max_requests=2, window_seconds=1)

        # First two requests should be immediate
        await limiter.wait_if_needed()
        await limiter.wait_if_needed()

        # Third request should cause a delay
        start_time = asyncio.get_event_loop().time()
        await limiter.wait_if_needed()
        end_time = asyncio.get_event_loop().time()

        # Should have waited at least 1 second
        assert end_time - start_time >= 0.9  # Allow some tolerance

    @pytest.mark.asyncio
    async def test_rate_limiter_window_cleanup(self):
        """Test rate limiter cleans up old requests"""
        limiter = RateLimiter(max_requests=2, window_seconds=0.5)  # Very short window

        # Make two requests
        await limiter.wait_if_needed()
        await limiter.wait_if_needed()

        # Wait for window to expire
        await asyncio.sleep(0.6)

        # Should be able to make request immediately now
        start_time = asyncio.get_event_loop().time()
        await limiter.wait_if_needed()
        end_time = asyncio.get_event_loop().time()

        assert end_time - start_time < 0.1  # Should be immediate


class TestArticleModel:
    """Test Article Pydantic model"""

    def test_article_creation(self):
        """Test basic article creation"""
        article = Article(
            source="Test Source",
            provider="test",
            title="Test Title",
            url="https://example.com",
            published_at="2023-01-01T00:00:00Z",
        )

        assert article.source == "Test Source"
        assert article.provider == "test"
        assert article.title == "Test Title"
        assert article.url == "https://example.com"
        assert isinstance(article.published_at, datetime)

    def test_article_date_parsing(self):
        """Test various date format parsing"""
        formats_to_test = [
            "2023-01-01T00:00:00Z",
            "2023-01-01T00:00:00.000Z",
            "2023-01-01 00:00:00",
            "Sun, 01 Jan 2023 00:00:00 GMT",
        ]

        for date_str in formats_to_test:
            article = Article(
                source="Test",
                provider="test",
                title="Test",
                url="https://example.com",
                published_at=date_str,
            )
            assert isinstance(article.published_at, datetime)


class TestNewsFilter:
    """Test NewsFilter validation"""

    def test_news_filter_defaults(self):
        """Test default values"""
        filter_obj = NewsFilter()

        assert filter_obj.sort_by == "publishedAt"
        assert filter_obj.page_size == 20
        assert filter_obj.page == 1

    def test_news_filter_validation(self):
        """Test field validation"""
        # Test page_size limit
        filter_obj = NewsFilter(page_size=150)  # Max should be 100
        assert filter_obj.page_size == 100  # Should be clamped

    def test_relevance_score_validation(self):
        """Test relevance score validation"""
        # Valid range
        filter_obj = NewsFilter(min_relevance_score=0.5)
        assert filter_obj.min_relevance_score == 0.5

        # Test bounds (should be between 0 and 1)
        with pytest.raises(ValueError):
            NewsFilter(min_relevance_score=1.5)


@pytest.fixture
def mock_httpx_client():
    """Fixture providing mocked httpx client"""
    client = AsyncMock(spec=httpx.AsyncClient)
    client.is_closed = False
    return client


@pytest.fixture
def sample_newsapi_response():
    """Sample NewsAPI response"""
    return {
        "status": "ok",
        "totalResults": 2,
        "articles": [
            {
                "source": {"id": "test-source", "name": "Test Source"},
                "title": "Test Stock Market News",
                "description": "Stock market analysis and trading insights",
                "content": "Full article content about market trends",
                "url": "https://example.com/article1",
                "urlToImage": "https://example.com/image1.jpg",
                "author": "Test Author",
                "publishedAt": "2023-01-01T00:00:00Z",
            },
            {
                "source": {"id": "another-source", "name": "Another Source"},
                "title": "Market Update: Nifty Gains",
                "description": "Indian stock markets show positive movement",
                "content": "Detailed market analysis",
                "url": "https://example.com/article2",
                "urlToImage": "https://example.com/image2.jpg",
                "author": "Market Analyst",
                "publishedAt": "2023-01-01T01:00:00Z",
            },
        ],
    }


@pytest.fixture
def sample_rss_feed():
    """Sample RSS feed content"""
    return """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
    <channel>
        <title>Test Feed</title>
        <description>Test RSS Feed</description>
        <item>
            <title>Stock Market Analysis</title>
            <description>Analysis of recent stock market movements</description>
            <link>https://example.com/rss1</link>
            <pubDate>Sun, 01 Jan 2023 00:00:00 GMT</pubDate>
            <author>RSS Author</author>
        </item>
        <item>
            <title>Trading Strategies</title>
            <description>Effective trading strategies for investors</description>
            <link>https://example.com/rss2</link>
            <pubDate>Sun, 01 Jan 2023 01:00:00 GMT</pubDate>
        </item>
    </channel>
</rss>
"""


class TestNewsClient:
    """Test NewsClient functionality"""

    @pytest.fixture
    def news_config(self):
        """News configuration for testing"""
        config = NewsConfig()
        config.newsapi.enabled = True
        config.newsapi.api_key = "test_key"
        config.rss.enabled = True
        return config

    @pytest.fixture
    def news_client(self, news_config):
        """NewsClient instance for testing"""
        return NewsClient(news_config)

    def test_client_initialization(self, news_client):
        """Test client initialization"""
        assert news_client.config is not None
        assert news_client.session_id is not None
        assert len(news_client.session_id) == 32  # 16 bytes hex = 32 chars
        assert "newsapi" in news_client.rate_limiters
        assert "rss" in news_client.rate_limiters
        assert news_client.stats["requests_made"] == 0

    def test_relevance_score_calculation(self, news_client):
        """Test relevance score calculation"""
        # High relevance article
        high_relevance = {
            "title": "Stock market trading analysis with NSE shares",
            "description": "Investment portfolio management and dividend analysis",
        }
        score = news_client._calculate_relevance_score(high_relevance)
        assert score > 0.7

        # Low relevance article
        low_relevance = {
            "title": "Sports news and entertainment updates",
            "description": "Celebrity gossip and movie reviews",
        }
        score = news_client._calculate_relevance_score(low_relevance)
        assert score < 0.3

    def test_stock_symbol_extraction(self, news_client):
        """Test stock symbol extraction from text"""
        text = "RELIANCE shares up 5%, TCS and INFY showing strong performance. $TSLA down in US markets."
        symbols = news_client._extract_stock_symbols(text)

        assert "RELIANCE" in symbols
        assert "TCS" in symbols
        assert "INFY" in symbols
        assert "$TSLA" in symbols or "TSLA" in symbols

    def test_article_standardization_newsapi(
        self, news_client, sample_newsapi_response
    ):
        """Test NewsAPI article standardization"""
        article_data = sample_newsapi_response["articles"][0]
        article = news_client._standardize_newsapi_article(article_data)

        assert article.source == "Test Source"
        assert article.provider == "newsapi"
        assert article.title == "Test Stock Market News"
        assert article.url == "https://example.com/article1"
        assert article.relevance_score is not None
        assert article.relevance_score > 0.5  # Should be high for stock market news

    @patch("feedparser.parse")
    def test_article_standardization_rss(self, mock_feedparser, news_client):
        """Test RSS article standardization"""
        # Mock feedparser entry
        mock_entry = MagicMock()
        mock_entry.title = "Stock Market Update"
        mock_entry.summary = "Latest stock market analysis"
        mock_entry.link = "https://example.com/rss1"
        mock_entry.published = "2023-01-01T00:00:00Z"
        mock_entry.author = "RSS Author"

        article = news_client._standardize_rss_article(mock_entry, "Test Feed")

        assert article.source == "Test Feed"
        assert article.provider == "rss"
        assert article.title == "Stock Market Update"
        assert article.url == "https://example.com/rss1"

    def test_article_deduplication(self, news_client):
        """Test article deduplication"""
        # Create duplicate articles
        articles = [
            Article(
                source="Source1",
                provider="test",
                title="Market News",
                url="https://example.com/1",
                published_at=datetime.now(),
            ),
            Article(
                source="Source2",
                provider="test",
                title="Market News",  # Same title
                url="https://example.com/2",
                published_at=datetime.now(),
            ),
            Article(
                source="Source3",
                provider="test",
                title="Different News",
                url="https://example.com/1",
                published_at=datetime.now(),  # Same URL
            ),
            Article(
                source="Source4",
                provider="test",
                title="Unique News",
                url="https://example.com/4",
                published_at=datetime.now(),
            ),
        ]

        unique_articles = news_client._deduplicate_articles(articles)

        # Should have 2 unique articles (first occurrence of each duplicate kept)
        assert len(unique_articles) == 2
        assert unique_articles[0].title == "Market News"
        assert unique_articles[1].title == "Unique News"

    def test_article_sorting(self, news_client):
        """Test article sorting"""
        # Create articles with different dates and relevance scores
        now = datetime.now()
        articles = [
            Article(
                source="Source1",
                provider="test",
                title="Old News",
                url="https://example.com/1",
                published_at=now - timedelta(hours=2),
                relevance_score=0.8,
            ),
            Article(
                source="Source2",
                provider="test",
                title="Recent News",
                url="https://example.com/2",
                published_at=now - timedelta(hours=1),
                relevance_score=0.6,
            ),
            Article(
                source="Source3",
                provider="test",
                title="Latest News",
                url="https://example.com/3",
                published_at=now,
                relevance_score=0.4,
            ),
        ]

        # Test sort by published date
        sorted_by_date = news_client._sort_articles(articles, "publishedAt")
        assert sorted_by_date[0].title == "Latest News"  # Most recent first

        # Test sort by relevance
        sorted_by_relevance = news_client._sort_articles(articles, "relevancy")
        assert sorted_by_relevance[0].title == "Old News"  # Highest relevance first

    def test_article_filtering(self, news_client):
        """Test article filtering"""
        # Create test articles
        now = datetime.now()
        articles = [
            Article(
                source="Source1",
                provider="test",
                title="Stock market RELIANCE gains",
                url="https://example.com/1",
                published_at=now - timedelta(hours=2),
                relevance_score=0.8,
            ),
            Article(
                source="Source2",
                provider="test",
                title="General business news",
                url="https://example.com/2",
                published_at=now - timedelta(hours=1),
                relevance_score=0.3,
            ),
            Article(
                source="Source3",
                provider="test",
                title="TCS stock analysis",
                url="https://example.com/3",
                published_at=now,
                relevance_score=0.7,
            ),
        ]

        # Test relevance score filtering
        news_filter = NewsFilter(min_relevance_score=0.5)
        filtered = news_client._apply_filters(articles, news_filter)
        assert len(filtered) == 2  # Only high relevance articles

        # Test stock symbol filtering
        news_filter = NewsFilter(stock_symbols=["RELIANCE"])
        filtered = news_client._apply_filters(articles, news_filter)
        assert len(filtered) == 1
        assert "RELIANCE" in filtered[0].title

        # Test keyword filtering
        news_filter = NewsFilter(keywords=["stock"])
        filtered = news_client._apply_filters(articles, news_filter)
        assert len(filtered) == 2  # Articles containing "stock"

        # Test date filtering
        news_filter = NewsFilter(from_date=now - timedelta(hours=1, minutes=30))
        filtered = news_client._apply_filters(articles, news_filter)
        assert len(filtered) == 2  # Articles from last 1.5 hours

    @pytest.mark.asyncio
    async def test_client_context_manager(self, news_config):
        """Test async context manager"""
        async with NewsClient(news_config) as client:
            assert client is not None
            assert not client.clients  # No clients created yet

        # Client should be closed after context exit
        # (Clients dict should be cleared in close method)

    def test_client_stats(self, news_client):
        """Test client statistics"""
        stats = news_client.get_client_stats()

        assert "session_id" in stats
        assert "configuration" in stats
        assert "statistics" in stats
        assert "rate_limits" in stats
        assert "cache_stats" in stats

        assert stats["statistics"]["requests_made"] == 0
        assert stats["statistics"]["articles_fetched"] == 0


@pytest.mark.asyncio
class TestNewsClientHTTPMethods:
    """Test NewsClient HTTP methods with mocked responses"""

    @pytest.fixture
    def news_client(self):
        """NewsClient with test configuration"""
        config = NewsConfig()
        config.newsapi.enabled = True
        config.newsapi.api_key = "test_key"
        return NewsClient(config)

    @patch("httpx.AsyncClient")
    async def test_make_request_success(
        self, mock_client_class, news_client, sample_newsapi_response
    ):
        """Test successful HTTP request"""
        # Setup mock
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_newsapi_response
        mock_client.get.return_value = mock_response
        mock_client.is_closed = False
        mock_client_class.return_value = mock_client

        # Make request
        result = await news_client._make_request(
            "newsapi", "GET", "https://api.example.com/test", {"param": "value"}
        )

        assert result == sample_newsapi_response
        assert news_client.stats["requests_made"] == 1
        assert news_client.stats["cache_misses"] == 1

    @patch("httpx.AsyncClient")
    async def test_make_request_authentication_error(
        self, mock_client_class, news_client
    ):
        """Test authentication error handling"""
        # Setup mock
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": "Unauthorized"}
        mock_client.get.return_value = mock_response
        mock_client.is_closed = False
        mock_client_class.return_value = mock_client

        # Should raise AuthenticationError
        with pytest.raises(AuthenticationError) as exc_info:
            await news_client._make_request(
                "newsapi", "GET", "https://api.example.com/test"
            )

        assert exc_info.value.provider == "newsapi"
        assert exc_info.value.status_code == 401

    @patch("httpx.AsyncClient")
    async def test_make_request_rate_limit_error(self, mock_client_class, news_client):
        """Test rate limit error handling"""
        # Setup mock
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status_code = 429
        mock_response.json.return_value = {"error": "Rate limit exceeded"}
        mock_client.get.return_value = mock_response
        mock_client.is_closed = False
        mock_client_class.return_value = mock_client

        # Should raise RateLimitError
        with pytest.raises(RateLimitError) as exc_info:
            await news_client._make_request(
                "newsapi",
                "GET",
                "https://api.example.com/test",
                retries=0,  # Disable retries for faster test
            )

        assert exc_info.value.provider == "newsapi"
        assert exc_info.value.status_code == 429

    @patch("httpx.AsyncClient")
    async def test_make_request_network_error(self, mock_client_class, news_client):
        """Test network error handling"""
        # Setup mock
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.NetworkError("Connection failed")
        mock_client.is_closed = False
        mock_client_class.return_value = mock_client

        # Should raise NetworkError
        with pytest.raises(NetworkError) as exc_info:
            await news_client._make_request(
                "newsapi",
                "GET",
                "https://api.example.com/test",
                retries=0,  # Disable retries for faster test
            )

        assert "Connection failed" in str(exc_info.value)
        assert exc_info.value.provider == "newsapi"

    @patch("httpx.AsyncClient")
    async def test_make_request_timeout_error(self, mock_client_class, news_client):
        """Test timeout error handling"""
        # Setup mock
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.TimeoutException("Request timeout")
        mock_client.is_closed = False
        mock_client_class.return_value = mock_client

        # Should raise NetworkError
        with pytest.raises(NetworkError) as exc_info:
            await news_client._make_request(
                "newsapi",
                "GET",
                "https://api.example.com/test",
                retries=0,  # Disable retries for faster test
            )

        assert "Timeout" in str(exc_info.value)
        assert exc_info.value.provider == "newsapi"

    @patch("httpx.AsyncClient")
    async def test_make_request_retry_logic(self, mock_client_class, news_client):
        """Test retry logic for server errors"""
        # Setup mock to fail twice then succeed
        mock_client = AsyncMock()
        mock_client.is_closed = False
        mock_client_class.return_value = mock_client

        # Create responses: 500, 500, 200
        error_response1 = AsyncMock()
        error_response1.status_code = 500
        error_response1.json.return_value = {"error": "Server error"}

        error_response2 = AsyncMock()
        error_response2.status_code = 500
        error_response2.json.return_value = {"error": "Server error"}

        success_response = AsyncMock()
        success_response.status_code = 200
        success_response.json.return_value = {"status": "ok", "data": "success"}

        mock_client.get.side_effect = [
            error_response1,
            error_response2,
            success_response,
        ]

        # Should succeed after retries
        result = await news_client._make_request(
            "newsapi", "GET", "https://api.example.com/test", retries=3
        )

        assert result["status"] == "ok"
        assert result["data"] == "success"
        assert mock_client.get.call_count == 3

    @patch("httpx.AsyncClient")
    async def test_caching_behavior(self, mock_client_class, news_client):
        """Test request caching"""
        # Setup mock
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        mock_client.get.return_value = mock_response
        mock_client.is_closed = False
        mock_client_class.return_value = mock_client

        # First request
        result1 = await news_client._make_request(
            "newsapi", "GET", "https://api.example.com/test", {"param": "value"}
        )

        # Second request with same parameters
        result2 = await news_client._make_request(
            "newsapi", "GET", "https://api.example.com/test", {"param": "value"}
        )

        # Should get same result
        assert result1 == result2

        # But only one actual HTTP request should be made (second from cache)
        assert mock_client.get.call_count == 1
        assert news_client.stats["cache_hits"] == 1
        assert news_client.stats["cache_misses"] == 1


@pytest.mark.asyncio
class TestNewsClientPublicAPI:
    """Test NewsClient public API methods"""

    @pytest.fixture
    def news_client(self):
        """NewsClient with RSS enabled (no API keys required)"""
        config = NewsConfig()
        config.rss.enabled = True
        config.newsapi.enabled = False  # Disable to avoid API key requirements
        return NewsClient(config)

    @patch("src.api.news_client.NewsClient._get_rss_headlines")
    async def test_get_headlines(self, mock_rss_headlines, news_client):
        """Test get_headlines method"""
        # Mock RSS headlines
        mock_articles = [
            Article(
                source="Test Feed",
                provider="rss",
                title="Stock Market Update",
                url="https://example.com/1",
                published_at=datetime.now(),
                relevance_score=0.8,
            ),
            Article(
                source="Test Feed",
                provider="rss",
                title="Business News",
                url="https://example.com/2",
                published_at=datetime.now(),
                relevance_score=0.6,
            ),
        ]
        mock_rss_headlines.return_value = mock_articles

        # Test get headlines
        result = await news_client.get_headlines()

        assert len(result) == 2
        assert all(isinstance(article, Article) for article in result)
        assert (
            result[0].relevance_score >= result[1].relevance_score
        )  # Should be sorted

    @patch("src.api.news_client.NewsClient.get_headlines")
    async def test_search_news(self, mock_get_headlines, news_client):
        """Test search_news method"""
        mock_get_headlines.return_value = []

        await news_client.search_news("stock market")

        # Should call get_headlines with query in keywords
        mock_get_headlines.assert_called_once()
        args, kwargs = mock_get_headlines.call_args
        news_filter = args[0] if args else kwargs.get("news_filter")
        assert "stock market" in news_filter.keywords

    @patch("src.api.news_client.NewsClient.get_headlines")
    async def test_get_market_news(self, mock_get_headlines, news_client):
        """Test get_market_news method"""
        mock_get_headlines.return_value = []

        await news_client.get_market_news(symbols=["RELIANCE", "TCS"], limit=30)

        # Should call get_headlines with market-specific filter
        mock_get_headlines.assert_called_once()
        args, kwargs = mock_get_headlines.call_args
        news_filter = args[0] if args else kwargs.get("news_filter")

        assert news_filter.stock_symbols == ["RELIANCE", "TCS"]
        assert news_filter.page_size == 30
        assert news_filter.min_relevance_score == 0.3
        assert "stock" in news_filter.keywords

    @patch("src.api.news_client.NewsClient.get_headlines")
    async def test_get_trending_topics(self, mock_get_headlines, news_client):
        """Test get_trending_topics method"""
        # Mock articles with repeated words
        mock_articles = [
            Article(
                source="Test",
                provider="test",
                title="Stock market gains today",
                url="https://example.com/1",
                published_at=datetime.now(),
            ),
            Article(
                source="Test",
                provider="test",
                title="Market analysis shows growth",
                url="https://example.com/2",
                published_at=datetime.now(),
            ),
            Article(
                source="Test",
                provider="test",
                title="Stock prices rise in market",
                url="https://example.com/3",
                published_at=datetime.now(),
            ),
        ]
        mock_get_headlines.return_value = mock_articles

        trending = await news_client.get_trending_topics(limit=5)

        # "market" and "stock" should be top trending
        assert "market" in trending
        assert "stock" in trending
        assert trending["market"] >= 2  # Appears in multiple articles

    async def test_health_check(self, news_client):
        """Test health_check method"""
        # Note: This test will make actual network requests to RSS feeds
        # In a real test environment, you might want to mock this too
        health = await news_client.health_check()

        assert "overall_status" in health
        assert "providers" in health
        assert "cache_status" in health
        assert "statistics" in health

    def test_get_client_stats(self, news_client):
        """Test get_client_stats method"""
        stats = news_client.get_client_stats()

        required_keys = [
            "session_id",
            "configuration",
            "statistics",
            "rate_limits",
            "cache_stats",
        ]

        for key in required_keys:
            assert key in stats

        assert isinstance(stats["configuration"]["enabled_providers"], list)
        assert isinstance(stats["statistics"], dict)

    async def test_clear_cache(self, news_client):
        """Test clear_cache method"""
        # Add some data to cache
        news_client.cache.set("test", "endpoint", {}, {"data": "test"}, 5)
        news_client.seen_articles.add("https://example.com")

        assert len(news_client.cache.cache) == 1
        assert len(news_client.seen_articles) == 1

        # Clear cache
        await news_client.clear_cache()

        assert len(news_client.cache.cache) == 0
        assert len(news_client.seen_articles) == 0


# Performance and stress tests
@pytest.mark.asyncio
class TestNewsClientPerformance:
    """Test NewsClient performance and stress scenarios"""

    @pytest.fixture
    def news_client(self):
        config = NewsConfig()
        config.rss.enabled = True
        return NewsClient(config)

    async def test_concurrent_requests(self, news_client):
        """Test handling of concurrent requests"""
        with patch.object(news_client, "_make_request") as mock_request:
            mock_request.return_value = {"articles": []}

            # Make multiple concurrent requests
            tasks = []
            for i in range(10):
                task = news_client.get_headlines(NewsFilter(page_size=5))
                tasks.append(task)

            results = await asyncio.gather(*tasks)

            # All requests should complete successfully
            assert len(results) == 10
            assert all(isinstance(result, list) for result in results)

    async def test_rate_limiting_under_load(self, news_client):
        """Test rate limiting behavior under load"""
        # Create a very restrictive rate limiter
        news_client.rate_limiters["test"] = RateLimiter(
            max_requests=2, window_seconds=1
        )

        with patch.object(news_client, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"articles": []}
            mock_client.get.return_value = mock_response
            mock_client.is_closed = False
            mock_get_client.return_value = mock_client

            # Make requests that would exceed rate limit
            start_time = asyncio.get_event_loop().time()

            for _ in range(3):
                await news_client._make_request("test", "GET", "https://example.com")

            end_time = asyncio.get_event_loop().time()

            # Should have taken at least 1 second due to rate limiting
            assert end_time - start_time >= 0.9

    def test_memory_usage_with_large_cache(self, news_client):
        """Test memory usage with large cache"""
        # Add many entries to cache
        for i in range(1000):
            news_client.cache.set(
                "provider",
                f"endpoint_{i}",
                {"param": i},
                {"large_data": "x" * 1000},
                60,
            )

        # Cache should have all entries
        assert len(news_client.cache.cache) == 1000

        # Clear cache to free memory
        news_client.cache.clear()
        assert len(news_client.cache.cache) == 0


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
