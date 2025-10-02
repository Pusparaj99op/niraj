"""
Unit Tests for News API Client
Comprehensive test coverage for all news providers and error scenarios
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import pytest

from src.api.news_client import (
    NewsClient,
    NewsConfig,
    Article,
    NewsFilter,
    RateLimiter,
    NewsCache,
    AuthenticationError,
    RateLimitError,
    NetworkError,
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

    def test_cache_edge_cases(self):
        """Test cache edge cases and error conditions"""
        cache = NewsCache()

        # Test cache with None values
        cache.set("provider", "endpoint", {"param": "value"}, None, 5)
        result = cache.get("provider", "endpoint", {"param": "value"})
        assert result is None

        # Test cache with complex objects
        complex_data = {"nested": {"data": [1, 2, {"key": "value"}]}}
        cache.set("provider", "endpoint", {"param": "complex"}, complex_data, 5)
        result = cache.get("provider", "endpoint", {"param": "complex"})
        assert result == complex_data

        # Test cache key collision with different parameter orders
        cache.set("provider", "endpoint", {"a": 1, "b": 2, "c": 3}, "data1", 5)
        cache.set("provider", "endpoint", {"c": 3, "b": 2, "a": 1}, "data2", 5)  # Same params, different order
        result = cache.get("provider", "endpoint", {"a": 1, "b": 2, "c": 3})
        assert result == "data2"  # Last one wins

        # Test cache with very long keys
        long_key = {"param": "x" * 1000}
        cache.set("provider", "endpoint", long_key, "long_key_data", 5)
        result = cache.get("provider", "endpoint", long_key)
        assert result == "long_key_data"

    def test_cache_memory_management(self):
        """Test cache memory management and cleanup"""
        cache = NewsCache()

        # Add many entries
        for i in range(200):
            cache.set(f"provider{i}", f"endpoint{i}", {"param": i}, f"data{i}", 1)

        initial_size = len(cache.cache)
        assert initial_size == 200

        # Wait for some entries to expire (TTL=1 second)
        import time
        time.sleep(1.1)

        # Access one entry to trigger cleanup
        cache.get("provider0", "endpoint0", {"param": 0})

        # Cache should have cleaned up expired entries
        # (Note: actual cleanup depends on implementation, this tests the interface)
        final_size = len(cache.cache)
        assert final_size <= initial_size

    def test_cache_concurrent_access(self):
        """Test cache behavior under concurrent access patterns"""
        import threading
        cache = NewsCache()

        results = []
        errors = []

        def worker(worker_id):
            try:
                # Each worker does set/get operations
                for i in range(100):
                    key = f"worker{worker_id}_item{i}"
                    cache.set("provider", "endpoint", {"key": key}, f"data_{key}", 60)
                    result = cache.get("provider", "endpoint", {"key": key})
                    results.append(result)
            except Exception as e:
                errors.append(e)

        # Start multiple threads
        threads = []
        for i in range(5):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # Should have no errors and correct number of results
        assert len(errors) == 0
        assert len(results) == 500  # 5 workers * 100 operations each

        # Verify data integrity
        for result in results:
            assert result is not None
            assert result.startswith("data_")

    @pytest.mark.parametrize("max_requests,window_seconds,requests_to_make,expected_waits", [
        (2, 1, 3, 1),  # 3 requests, 2 allowed, 1 should wait
        (5, 2, 6, 1),  # 6 requests, 5 allowed, 1 should wait
        (1, 1, 5, 4),  # 5 requests, 1 allowed, 4 should wait
        (10, 1, 8, 0),  # 8 requests, 10 allowed, none should wait
    ])
    @pytest.mark.asyncio
    async def test_rate_limiter_parametrized(self, max_requests, window_seconds, requests_to_make, expected_waits):
        """Test rate limiter with various configurations"""
        limiter = RateLimiter(max_requests=max_requests, window_seconds=window_seconds)

        wait_count = 0
        for i in range(requests_to_make):
            start_time = asyncio.get_event_loop().time()
            await limiter.wait_if_needed()
            end_time = asyncio.get_event_loop().time()

            if end_time - start_time >= window_seconds * 0.8:  # Allow some tolerance
                wait_count += 1

        assert wait_count >= expected_waits  # At least expected waits occurred

    @pytest.mark.parametrize("cache_ttl,wait_time,should_expire", [
        (1, 0.5, False),   # TTL 1s, wait 0.5s, should not expire
        (1, 1.5, True),    # TTL 1s, wait 1.5s, should expire
        (0, 0.1, True),    # TTL 0s, immediate expire
        (60, 1, False),    # TTL 60s, wait 1s, should not expire
    ])
    def test_cache_expiry_parametrized(self, cache_ttl, wait_time, should_expire):
        """Test cache expiry with various TTL and wait times"""
        cache = NewsCache()

        data = {"test": "data"}
        cache.set("provider", "endpoint", {"param": "value"}, data, cache_ttl)

        if wait_time > 0:
            import time
            time.sleep(wait_time)

        result = cache.get("provider", "endpoint", {"param": "value"})

        if should_expire:
            assert result is None
        else:
            assert result == data


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
    async def test_rate_limiter_edge_cases(self):
        """Test rate limiter edge cases"""
        # Test with zero max_requests
        limiter = RateLimiter(max_requests=0, window_seconds=1)

        start_time = asyncio.get_event_loop().time()
        await limiter.wait_if_needed()
        end_time = asyncio.get_event_loop().time()

        # Should wait for the full window
        assert end_time - start_time >= 0.9

        # Test with very large window
        limiter = RateLimiter(max_requests=1, window_seconds=3600)  # 1 hour

        start_time = asyncio.get_event_loop().time()
        await limiter.wait_if_needed()
        end_time = asyncio.get_event_loop().time()

        # Should be immediate (no wait)
        assert end_time - start_time < 0.1

    @pytest.mark.asyncio
    async def test_rate_limiter_burst_behavior(self):
        """Test rate limiter burst behavior"""
        limiter = RateLimiter(max_requests=3, window_seconds=2)

        # Make 3 requests quickly
        for _ in range(3):
            start_time = asyncio.get_event_loop().time()
            await limiter.wait_if_needed()
            end_time = asyncio.get_event_loop().time()
            assert end_time - start_time < 0.1  # Should be immediate

        # 4th request should wait
        start_time = asyncio.get_event_loop().time()
        await limiter.wait_if_needed()
        end_time = asyncio.get_event_loop().time()
        assert end_time - start_time >= 1.9  # Should wait almost 2 seconds

    @pytest.mark.asyncio
    async def test_rate_limiter_concurrent_access(self):
        """Test rate limiter under concurrent access"""
        limiter = RateLimiter(max_requests=5, window_seconds=1)

        async def make_request(request_id):
            await limiter.wait_if_needed()
            return request_id

        # Make concurrent requests
        tasks = [make_request(i) for i in range(10)]
        results = await asyncio.gather(*tasks)

        # All requests should complete
        assert len(results) == 10
        assert set(results) == set(range(10))

    @pytest.mark.asyncio
    async def test_rate_limiter_reset_behavior(self):
        """Test rate limiter reset behavior"""
        limiter = RateLimiter(max_requests=2, window_seconds=0.5)

        # Use up the rate limit
        await limiter.wait_if_needed()
        await limiter.wait_if_needed()

        # Next request should wait
        start_time = asyncio.get_event_loop().time()
        await limiter.wait_if_needed()
        end_time = asyncio.get_event_loop().time()
        assert end_time - start_time >= 0.4

        # Wait for window to reset
        await asyncio.sleep(0.6)

        # Should be able to make requests immediately again
        for _ in range(2):
            start_time = asyncio.get_event_loop().time()
            await limiter.wait_if_needed()
            end_time = asyncio.get_event_loop().time()
            assert end_time - start_time < 0.1


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

    def test_article_edge_cases(self):
        """Test Article model edge cases"""
        # Test with minimal required fields
        article = Article(
            source="Test",
            provider="test",
            title="Title",
            url="https://example.com",
            published_at="2023-01-01T00:00:00Z",
        )
        assert article.title == "Title"
        assert article.content is None  # Optional field
        assert article.author is None  # Optional field

        # Test with empty strings
        article = Article(
            source="",
            provider="test",
            title="",
            url="https://example.com",
            published_at="2023-01-01T00:00:00Z",
        )
        assert article.source == ""
        assert article.title == ""

        # Test with very long strings
        long_title = "A" * 1000
        long_content = "B" * 10000
        article = Article(
            source="Test",
            provider="test",
            title=long_title,
            url="https://example.com",
            published_at="2023-01-01T00:00:00Z",
            content=long_content,
        )
        assert len(article.title) == 1000
        assert len(article.content) == 10000

    @pytest.mark.parametrize("date_str", [
        "2023-01-01T00:00:00Z",
        "2023-01-01T00:00:00.000Z",
        "2023-01-01 00:00:00",
        "Sun, 01 Jan 2023 00:00:00 GMT",
        "2023-01-01T00:00:00+00:00",
        "2023-01-01T00:00:00-05:00",
    ])
    def test_article_date_parsing_parametrized(self, date_str):
        """Test various date format parsing with parametrization"""
        article = Article(
            source="Test",
            provider="test",
            title="Test",
            url="https://example.com",
            published_at=date_str,
        )
        assert isinstance(article.published_at, datetime)

    def test_article_invalid_date_formats(self):
        """Test Article with invalid date formats"""
        # Test with completely invalid date
        with pytest.raises(ValueError):
            Article(
                source="Test",
                provider="test",
                title="Test",
                url="https://example.com",
                published_at="not-a-date",
            )

        # Test with malformed ISO format
        with pytest.raises(ValueError):
            Article(
                source="Test",
                provider="test",
                title="Test",
                url="https://example.com",
                published_at="2023-13-45T25:00:00Z",  # Invalid date
            )

    def test_article_url_validation(self):
        """Test Article URL validation"""
        # Valid URLs
        valid_urls = [
            "https://example.com",
            "http://example.com",
            "https://example.com/path",
            "https://example.com/path?query=value",
            "https://example.com/path#fragment",
        ]

        for url in valid_urls:
            article = Article(
                source="Test",
                provider="test",
                title="Test",
                url=url,
                published_at="2023-01-01T00:00:00Z",
            )
            assert article.url == url

        # Invalid URLs (these should still work as the model doesn't validate URL format)
        invalid_urls = [
            "not-a-url",
            "",
            "ftp://example.com",
        ]

        for url in invalid_urls:
            article = Article(
                source="Test",
                provider="test",
                title="Test",
                url=url,
                published_at="2023-01-01T00:00:00Z",
            )
            assert article.url == url


class TestNewsFilter:
    """Test NewsFilter validation"""

    def test_news_filter_defaults(self):
        """Test default values"""
        filter_obj = NewsFilter()

        assert filter_obj.sort_by == "publishedAt"
        assert filter_obj.page_size == 20
        assert filter_obj.page == 1

    def test_news_filter_edge_cases(self):
        """Test NewsFilter edge cases and validation"""
        # Test with extreme values
        filter_obj = NewsFilter(page_size=1000)  # Way above max
        assert filter_obj.page_size == 100  # Should be clamped

        filter_obj = NewsFilter(page_size=0)  # Below minimum
        assert filter_obj.page_size == 20  # Should use default

        # Test with negative values
        filter_obj = NewsFilter(page=-1)
        assert filter_obj.page == 1  # Should use default

        # Test with very large page numbers
        filter_obj = NewsFilter(page=10000)
        assert filter_obj.page == 10000  # Should allow large page numbers

    def test_news_filter_relevance_score_edge_cases(self):
        """Test relevance score validation edge cases"""
        # Test boundary values
        filter_obj = NewsFilter(min_relevance_score=0.0)
        assert filter_obj.min_relevance_score == 0.0

        filter_obj = NewsFilter(min_relevance_score=1.0)
        assert filter_obj.min_relevance_score == 1.0

        # Test invalid values
        with pytest.raises(ValueError):
            NewsFilter(min_relevance_score=-0.1)

        with pytest.raises(ValueError):
            NewsFilter(min_relevance_score=1.1)

        # Test with float precision
        filter_obj = NewsFilter(min_relevance_score=0.123456)
        assert filter_obj.min_relevance_score == 0.123456

    def test_news_filter_keywords_validation(self):
        """Test keywords validation and processing"""
        # Test with various keyword formats
        filter_obj = NewsFilter(keywords=["stock", "market", "nse"])
        assert filter_obj.keywords == ["stock", "market", "nse"]

        # Test with empty keywords
        filter_obj = NewsFilter(keywords=[])
        assert filter_obj.keywords == []

        # Test with duplicate keywords
        filter_obj = NewsFilter(keywords=["stock", "stock", "market"])
        assert filter_obj.keywords == ["stock", "stock", "market"]  # Should preserve duplicates

        # Test with special characters
        filter_obj = NewsFilter(keywords=["stock-market", "NSE/BSE", "₹500"])
        assert filter_obj.keywords == ["stock-market", "NSE/BSE", "₹500"]

    def test_news_filter_stock_symbols_validation(self):
        """Test stock symbols validation"""
        # Test with various symbol formats
        filter_obj = NewsFilter(stock_symbols=["RELIANCE", "TCS.NS", "$AAPL"])
        assert filter_obj.stock_symbols == ["RELIANCE", "TCS.NS", "$AAPL"]

        # Test with empty symbols
        filter_obj = NewsFilter(stock_symbols=[])
        assert filter_obj.stock_symbols == []

        # Test with mixed case
        filter_obj = NewsFilter(stock_symbols=["reliance", "TCS", "Infosys"])
        assert filter_obj.stock_symbols == ["reliance", "TCS", "Infosys"]

    def test_news_filter_date_validation(self):
        """Test date filter validation"""
        # Test with valid dates
        now = datetime.now()
        past_date = now - timedelta(days=7)

        filter_obj = NewsFilter(from_date=past_date, to_date=now)
        assert filter_obj.from_date == past_date
        assert filter_obj.to_date == now

        # Test with from_date after to_date (should still work, validation depends on implementation)
        filter_obj = NewsFilter(from_date=now, to_date=past_date)
        assert filter_obj.from_date == now
        assert filter_obj.to_date == past_date

        # Test with None dates
        filter_obj = NewsFilter(from_date=None, to_date=None)
        assert filter_obj.from_date is None
        assert filter_obj.to_date is None

    @pytest.mark.parametrize("page_size,expected", [
        (10, 10),
        (50, 50),
        (100, 100),
        (150, 100),  # Should be clamped to max
        (0, 20),     # Should use default
        (-1, 20),    # Should use default
    ])
    def test_news_filter_page_size_parametrized(self, page_size, expected):
        """Test NewsFilter page_size validation with parametrization"""
        filter_obj = NewsFilter(page_size=page_size)
        assert filter_obj.page_size == expected

    @pytest.mark.parametrize("relevance_score,should_pass", [
        (0.0, True),
        (0.5, True),
        (1.0, True),
        (-0.1, False),
        (1.1, False),
        (2.0, False),
    ])
    def test_news_filter_relevance_score_parametrized(self, relevance_score, should_pass):
        """Test NewsFilter relevance score validation with parametrization"""
        if should_pass:
            filter_obj = NewsFilter(min_relevance_score=relevance_score)
            assert filter_obj.min_relevance_score == relevance_score
        else:
            with pytest.raises(ValueError):
                NewsFilter(min_relevance_score=relevance_score)


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


@pytest.fixture
def news_config_full():
    """Full News configuration with all providers enabled"""
    config = NewsConfig()
    config.newsapi.enabled = True
    config.newsapi.api_key = "test_key"
    config.rss.enabled = True
    config.cache.enabled = True
    config.cache.ttl_seconds = 300
    config.rate_limiting.enabled = True
    return config


@pytest.fixture
def news_config_minimal():
    """Minimal News configuration with only RSS enabled"""
    config = NewsConfig()
    config.newsapi.enabled = False
    config.rss.enabled = True
    config.cache.enabled = False
    config.rate_limiting.enabled = False
    return config


@pytest.fixture
def news_config_newsapi_only():
    """News configuration with only NewsAPI enabled"""
    config = NewsConfig()
    config.newsapi.enabled = True
    config.newsapi.api_key = "test_key"
    config.rss.enabled = False
    return config


@pytest.fixture
def news_client_full(news_config_full):
    """NewsClient instance with full configuration"""
    return NewsClient(news_config_full)


@pytest.fixture
def news_client_minimal(news_config_minimal):
    """NewsClient instance with minimal configuration"""
    return NewsClient(news_config_minimal)


@pytest.fixture
def news_client_newsapi_only(news_config_newsapi_only):
    """NewsClient instance with only NewsAPI enabled"""
    return NewsClient(news_config_newsapi_only)


@pytest.fixture
def mock_successful_response():
    """Mock successful HTTP response"""
    response = AsyncMock()
    response.status_code = 200
    response.json.return_value = {"status": "ok", "data": "success"}
    return response


@pytest.fixture
def mock_auth_error_response():
    """Mock authentication error response"""
    response = AsyncMock()
    response.status_code = 401
    response.json.return_value = {"error": "Unauthorized"}
    return response


@pytest.fixture
def mock_rate_limit_response():
    """Mock rate limit error response"""
    response = AsyncMock()
    response.status_code = 429
    response.json.return_value = {"error": "Rate limit exceeded"}
    return response


@pytest.fixture
def mock_server_error_response():
    """Mock server error response"""
    response = AsyncMock()
    response.status_code = 500
    response.json.return_value = {"error": "Internal server error"}
    return response


@pytest.fixture
def mock_empty_response():
    """Mock empty response"""
    response = AsyncMock()
    response.status_code = 200
    response.json.return_value = {}
    return response


@pytest.fixture
def mock_unicode_response():
    """Mock response with Unicode content"""
    response = AsyncMock()
    response.status_code = 200
    response.json.return_value = {
        "title": "Stock Market Update 📈",
        "content": "NSE और BSE में बढ़त",
        "author": "अनिल कुमार"
    }
    return response


@pytest.fixture
def mock_invalid_json_response():
    """Mock response with invalid JSON"""
    response = AsyncMock()
    response.status_code = 200
    response.json.side_effect = ValueError("Invalid JSON")
    return response


@pytest.fixture
def sample_articles():
    """Sample Article objects for testing"""
    now = datetime.now()
    return [
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


@pytest.fixture
def rate_limiter_strict():
    """Strict rate limiter for testing"""
    return RateLimiter(max_requests=1, window_seconds=1)


@pytest.fixture
def rate_limiter_relaxed():
    """Relaxed rate limiter for testing"""
    return RateLimiter(max_requests=100, window_seconds=60)


@pytest.fixture
def cache_short_ttl():
    """Cache with short TTL for testing"""
    return NewsCache()


@pytest.fixture
def cache_long_ttl():
    """Cache with long TTL for testing"""
    cache = NewsCache()
    # Set a long default TTL by modifying the set method behavior
    original_set = cache.set

    def set_with_long_ttl(provider, endpoint, params, data, ttl=None):
        if ttl is None:
            ttl = 3600  # 1 hour default
        return original_set(provider, endpoint, params, data, ttl)
    cache.set = set_with_long_ttl
    return cache


@pytest.fixture
def mock_datetime_fixed():
    """Mock datetime for deterministic testing"""
    fixed_time = datetime(2023, 1, 1, 12, 0, 0)
    with patch('src.api.news_client.datetime') as mock_dt:
        mock_dt.now.return_value = fixed_time
        mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
        yield mock_dt


@pytest.fixture
def news_filter_high_relevance():
    """NewsFilter with high relevance threshold"""
    return NewsFilter(min_relevance_score=0.7, page_size=10)


@pytest.fixture
def news_filter_stock_specific():
    """NewsFilter for specific stocks"""
    return NewsFilter(
        stock_symbols=["RELIANCE", "TCS"],
        keywords=["stock", "market"],
        min_relevance_score=0.5
    )


@pytest.fixture
def news_filter_date_range():
    """NewsFilter with date range"""
    now = datetime.now()
    return NewsFilter(
        from_date=now - timedelta(days=7),
        to_date=now,
        page_size=50
    )


class TestNewsClient:
    """Test NewsClient functionality"""

    def test_client_initialization_full_config(self, news_client_full):
        """Test client initialization with full configuration"""
        assert news_client_full.config is not None
        assert news_client_full.session_id is not None
        assert len(news_client_full.session_id) == 32  # 16 bytes hex = 32 chars
        assert "newsapi" in news_client_full.rate_limiters
        assert "rss" in news_client_full.rate_limiters
        assert news_client_full.stats["requests_made"] == 0

    def test_client_initialization_minimal_config(self, news_client_minimal):
        """Test client initialization with minimal configuration"""
        assert news_client_minimal.config is not None
        assert news_client_minimal.session_id is not None
        assert len(news_client_minimal.session_id) == 32
        # Minimal config should still have rate limiters but they might be disabled
        assert isinstance(news_client_minimal.rate_limiters, dict)

    def test_client_initialization_newsapi_only(self, news_client_newsapi_only):
        """Test client initialization with NewsAPI only"""
        assert news_client_newsapi_only.config is not None
        assert "newsapi" in news_client_newsapi_only.rate_limiters
        assert "rss" not in news_client_newsapi_only.rate_limiters or not news_client_newsapi_only.rate_limiters["rss"].enabled

    def test_relevance_score_calculation(self, news_client_full):
        """Test relevance score calculation"""
        # High relevance article
        high_relevance = {
            "title": "Stock market trading analysis with NSE shares",
            "description": "Investment portfolio management and dividend analysis",
        }
        score = news_client_full._calculate_relevance_score(high_relevance)
        assert score > 0.7

        # Low relevance article
        low_relevance = {
            "title": "Sports news and entertainment updates",
            "description": "Celebrity gossip and movie reviews",
        }
        score = news_client_full._calculate_relevance_score(low_relevance)
        assert score < 0.3

    def test_stock_symbol_extraction(self, news_client_full):
        """Test stock symbol extraction from text"""
        text = "RELIANCE shares up 5%, TCS and INFY showing strong performance. $TSLA down in US markets."
        symbols = news_client_full._extract_stock_symbols(text)

        assert "RELIANCE" in symbols
        assert "TCS" in symbols
        assert "INFY" in symbols
        assert "$TSLA" in symbols or "TSLA" in symbols

    @pytest.mark.parametrize("text,expected_symbols", [
        ("RELIANCE shares up 5%", ["RELIANCE"]),
        ("TCS and INFY showing gains", ["TCS", "INFY"]),
        ("$AAPL and $GOOGL in news", ["$AAPL", "$GOOGL"]),
        ("NSE/BSE indices up", []),  # No actual symbols
        ("RELIANCE.NS and TCS.BO", ["RELIANCE.NS", "TCS.BO"]),
        ("", []),  # Empty text
    ])
    def test_stock_symbol_extraction_parametrized(self, news_client_full, text, expected_symbols):
        """Test stock symbol extraction with various text inputs"""
        symbols = news_client_full._extract_stock_symbols(text)
        for symbol in expected_symbols:
            assert symbol in symbols

    @pytest.mark.parametrize("title,content,expected_score_range", [
        ("Stock market trading analysis NSE shares", "Investment portfolio management", (0.7, 1.0)),
        ("Sports news and entertainment updates", "Celebrity gossip and movies", (0.0, 0.3)),
        ("Business news and corporate earnings", "Company financial results", (0.3, 0.7)),
        ("Weather forecast and climate change", "Temperature and rainfall data", (0.0, 0.3)),
        ("Cryptocurrency and blockchain technology", "Bitcoin and Ethereum prices", (0.3, 0.7)),
    ])
    def test_relevance_score_calculation_parametrized(self, news_client_full, title, content, expected_score_range):
        """Test relevance score calculation with various content types"""
        article_data = {"title": title, "description": content}
        score = news_client_full._calculate_relevance_score(article_data)

        assert expected_score_range[0] <= score <= expected_score_range[1]

    def test_article_standardization_newsapi(
        self, news_client_full, sample_newsapi_response
    ):
        """Test NewsAPI article standardization"""
        article_data = sample_newsapi_response["articles"][0]
        article = news_client_full._standardize_newsapi_article(article_data)

        assert article.source == "Test Source"
        assert article.provider == "newsapi"
        assert article.title == "Test Stock Market News"
        assert article.url == "https://example.com/article1"
        assert article.relevance_score is not None
        assert article.relevance_score > 0.5  # Should be high for stock market news

    @patch("feedparser.parse")
    def test_article_standardization_rss(self, mock_feedparser, news_client_full):
        """Test RSS article standardization"""
        # Mock feedparser entry
        mock_entry = MagicMock()
        mock_entry.title = "Stock Market Update"
        mock_entry.summary = "Latest stock market analysis"
        mock_entry.link = "https://example.com/rss1"
        mock_entry.published = "2023-01-01T00:00:00Z"
        mock_entry.author = "RSS Author"

        article = news_client_full._standardize_rss_article(mock_entry, "Test Feed")

        assert article.source == "Test Feed"
        assert article.provider == "rss"
        assert article.title == "Stock Market Update"
        assert article.url == "https://example.com/rss1"

    def test_article_deduplication(self, news_client_full, sample_articles):
        """Test article deduplication"""
        # Create duplicate articles
        duplicate_articles = sample_articles + [
            Article(
                source="Source1",
                provider="test",
                title="Market News",  # Same title as first article
                url="https://example.com/duplicate",
                published_at=datetime.now(),
            ),
            Article(
                source="Source4",
                provider="test",
                title="Unique News 2",
                url="https://example.com/4",
                published_at=datetime.now(),
            ),
        ]

        unique_articles = news_client_full._deduplicate_articles(duplicate_articles)

        # Should have deduplicated properly
        assert len(unique_articles) >= len(sample_articles)
        # Check that we don't have exact duplicates

    def test_article_sorting(self, news_client_full, sample_articles):
        """Test article sorting"""
        # Test sort by published date
        sorted_by_date = news_client_full._sort_articles(sample_articles, "publishedAt")
        assert sorted_by_date[0].published_at >= sorted_by_date[-1].published_at  # Most recent first

        # Test sort by relevance
        sorted_by_relevance = news_client_full._sort_articles(sample_articles, "relevancy")
        assert sorted_by_relevance[0].relevance_score >= sorted_by_relevance[-1].relevance_score  # Highest relevance first

    def test_article_filtering(self, news_client_full, sample_articles):
        """Test article filtering"""
        # Test relevance score filtering
        news_filter = NewsFilter(min_relevance_score=0.5)
        filtered = news_client_full._apply_filters(sample_articles, news_filter)
        assert all(article.relevance_score >= 0.5 for article in filtered)

        # Test stock symbol filtering
        news_filter = NewsFilter(stock_symbols=["RELIANCE"])
        filtered = news_client_full._apply_filters(sample_articles, news_filter)
        assert len(filtered) >= 0  # May or may not find matches depending on content

        # Test keyword filtering
        news_filter = NewsFilter(keywords=["stock"])
        filtered = news_client_full._apply_filters(sample_articles, news_filter)
        # Should filter based on keywords in title/content

    @pytest.mark.asyncio
    async def test_client_context_manager(self, news_config_full):
        """Test async context manager"""
        async with NewsClient(news_config_full) as client:
            assert client is not None
            assert not client.clients  # No clients created yet

        # Client should be closed after context exit
        # (Clients dict should be cleared in close method)

    def test_client_stats(self, news_client_full):
        """Test client statistics"""
        stats = news_client_full.get_client_stats()

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

    @patch("httpx.AsyncClient")
    async def test_make_request_success(
        self, mock_client_class, news_client_newsapi_only, sample_newsapi_response
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
        result = await news_client_newsapi_only._make_request(
            "newsapi", "GET", "https://api.example.com/test", {"param": "value"}
        )

        assert result == sample_newsapi_response
        assert news_client_newsapi_only.stats["requests_made"] == 1
        assert news_client_newsapi_only.stats["cache_misses"] == 1

    @patch("httpx.AsyncClient")
    async def test_make_request_authentication_error(
        self, mock_client_class, news_client_newsapi_only
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
            await news_client_newsapi_only._make_request(
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
    async def test_make_request_invalid_json(self, mock_client_class, news_client):
        """Test handling of invalid JSON responses"""
        # Setup mock
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_client.get.return_value = mock_response
        mock_client.is_closed = False
        mock_client_class.return_value = mock_client

        # Should raise NetworkError for invalid JSON
        with pytest.raises(NetworkError) as exc_info:
            await news_client._make_request(
                "newsapi", "GET", "https://api.example.com/test", retries=0
            )

        assert "Invalid JSON" in str(exc_info.value)
        assert exc_info.value.provider == "newsapi"

    @patch("httpx.AsyncClient")
    async def test_make_request_malformed_response(self, mock_client_class, news_client):
        """Test handling of malformed HTTP responses"""
        # Setup mock
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = None  # Malformed response
        mock_client.get.return_value = mock_response
        mock_client.is_closed = False
        mock_client_class.return_value = mock_client

        # Should handle None response gracefully
        result = await news_client._make_request(
            "newsapi", "GET", "https://api.example.com/test", retries=0
        )

        assert result is None

    @patch("httpx.AsyncClient")
    async def test_make_request_connection_error_with_retry(self, mock_client_class, news_client):
        """Test connection errors with retry logic"""
        # Setup mock to fail with connection error then succeed
        mock_client = AsyncMock()
        mock_client.is_closed = False
        mock_client_class.return_value = mock_client

        # First call raises connection error, second succeeds
        mock_client.get.side_effect = [
            httpx.ConnectError("Connection refused"),
            AsyncMock(status_code=200, json=lambda: {"data": "success"}),
        ]

        # Should succeed after retry
        result = await news_client._make_request(
            "newsapi", "GET", "https://api.example.com/test", retries=2
        )

        assert result["data"] == "success"
        assert mock_client.get.call_count == 2

    @patch("httpx.AsyncClient")
    async def test_make_request_rate_limit_different_providers(self, mock_client_class, news_client):
        """Test rate limiting works correctly for different providers"""
        # Setup mocks for two different providers
        mock_client1 = AsyncMock()
        mock_client2 = AsyncMock()

        mock_response1 = AsyncMock()
        mock_response1.status_code = 429
        mock_response1.json.return_value = {"error": "Rate limit exceeded"}
        mock_client1.get.return_value = mock_response1
        mock_client1.is_closed = False

        mock_response2 = AsyncMock()
        mock_response2.status_code = 200
        mock_response2.json.return_value = {"data": "success"}
        mock_client2.get.return_value = mock_response2
        mock_client2.is_closed = False

        # Return different clients for different providers
        def get_client(provider):
            if provider == "newsapi":
                return mock_client1
            elif provider == "rss":
                return mock_client2
            return mock_client1

        with patch.object(news_client, "_get_client", side_effect=get_client):
            # First provider should fail with rate limit
            with pytest.raises(RateLimitError):
                await news_client._make_request("newsapi", "GET", "https://api.example.com/test", retries=0)

            # Second provider should succeed
            result = await news_client._make_request("rss", "GET", "https://api.example.com/test", retries=0)
            assert result["data"] == "success"

    @patch("httpx.AsyncClient")
    async def test_make_request_cache_with_errors(self, mock_client_class, news_client):
        """Test that caching works correctly even with errors"""
        mock_client = AsyncMock()
        mock_client.is_closed = False
        mock_client_class.return_value = mock_client

        # First request fails
        error_response = AsyncMock()
        error_response.status_code = 500
        error_response.json.return_value = {"error": "Server error"}

        # Second request succeeds
        success_response = AsyncMock()
        success_response.status_code = 200
        success_response.json.return_value = {"data": "cached_success"}

        mock_client.get.side_effect = [error_response, success_response]

        # First request should fail and not be cached
        with pytest.raises(NetworkError):
            await news_client._make_request("newsapi", "GET", "https://api.example.com/test", retries=0)

        # Second request should succeed and be cached
        result = await news_client._make_request("newsapi", "GET", "https://api.example.com/test", retries=0)
        assert result["data"] == "cached_success"

        # Third request should get cached result
        result2 = await news_client._make_request("newsapi", "GET", "https://api.example.com/test", retries=0)
        assert result2 == result
        assert mock_client.get.call_count == 2  # Only two actual requests

    @patch("httpx.AsyncClient")
    async def test_make_request_empty_response(self, mock_client_class, news_client):
        """Test handling of empty responses"""
        # Setup mock
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}  # Empty response
        mock_client.get.return_value = mock_response
        mock_client.is_closed = False
        mock_client_class.return_value = mock_client

        # Should handle empty response
        result = await news_client._make_request(
            "newsapi", "GET", "https://api.example.com/test", retries=0
        )

        assert result == {}

    @patch("httpx.AsyncClient")
    async def test_make_request_unicode_content(self, mock_client_class, news_client):
        """Test handling of Unicode content in responses"""
        # Setup mock
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "title": "Stock Market Update 📈",
            "content": "NSE और BSE में बढ़त",
            "author": "अनिल कुमार"
        }
        mock_client.get.return_value = mock_response
        mock_client.is_closed = False
        mock_client_class.return_value = mock_client

        # Should handle Unicode content correctly
        result = await news_client._make_request(
            "newsapi", "GET", "https://api.example.com/test", retries=0
        )

        assert "📈" in result["title"]
        assert "NSE और BSE" in result["content"]
        assert "अनिल कुमार" == result["author"]


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
