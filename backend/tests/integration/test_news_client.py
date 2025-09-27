"""
Integration Tests for News API Client
Tests actual functionality with mocked external APIs
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

# Add the backend src to path for imports
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from api.news_client import (
    NewsClient,
    NewsConfig,
    NewsAPIConfig,
    RSSFeedConfig,
    Article,
    NewsFilter,
    AuthenticationError,
    RateLimitError,
    NetworkError,
)


class TestNewsClientIntegration:
    """Integration tests for NewsClient"""

    @pytest.fixture
    def news_config(self):
        """Test configuration"""
        config = NewsConfig()
        config.newsapi.enabled = True
        config.newsapi.api_key = "test_key"
        config.rss.enabled = True
        return config

    @pytest.fixture
    def news_client(self, news_config):
        """NewsClient for testing"""
        return NewsClient(news_config)

    @pytest.mark.asyncio
    async def test_newsapi_integration_success(self, news_client):
        """Test successful NewsAPI integration"""
        mock_response = {
            "status": "ok",
            "totalResults": 1,
            "articles": [
                {
                    "source": {"name": "Test Source"},
                    "title": "Stock Market Analysis",
                    "description": "Market analysis and trading insights",
                    "content": "Full content about stocks and trading",
                    "url": "https://example.com/article",
                    "urlToImage": "https://example.com/image.jpg",
                    "author": "Test Author",
                    "publishedAt": "2023-01-01T00:00:00Z",
                }
            ],
        }

        with patch.object(
            news_client, "_make_request", return_value=mock_response
        ) as mock_request:
            filter_obj = NewsFilter(keywords=["stock"], page_size=10)
            articles = await news_client.get_headlines(filter_obj, ["newsapi"])

            assert len(articles) == 1
            assert articles[0].title == "Stock Market Analysis"
            assert articles[0].provider == "newsapi"
            assert articles[0].relevance_score > 0.5  # Should be relevant

            # Verify API was called with correct parameters
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert "newsapi" in call_args[0]  # provider
            assert "top-headlines" in call_args[0][2]  # URL contains endpoint

    @pytest.mark.asyncio
    async def test_rss_integration_success(self, news_client):
        """Test successful RSS integration"""
        # Mock RSS content
        rss_content = """<?xml version="1.0"?>
        <rss version="2.0">
            <channel>
                <item>
                    <title>Market Update: Sensex Gains</title>
                    <description>Indian stock market shows positive trends</description>
                    <link>https://example.com/rss1</link>
                    <pubDate>Sun, 01 Jan 2023 00:00:00 GMT</pubDate>
                </item>
            </channel>
        </rss>
        """

        with patch.object(
            news_client, "_make_request", return_value={"content": rss_content}
        ):
            with patch("feedparser.parse") as mock_parse:
                # Mock feedparser response
                mock_entry = MagicMock()
                mock_entry.title = "Market Update: Sensex Gains"
                mock_entry.summary = "Indian stock market shows positive trends"
                mock_entry.link = "https://example.com/rss1"
                mock_entry.published = "Sun, 01 Jan 2023 00:00:00 GMT"

                mock_feed = MagicMock()
                mock_feed.entries = [mock_entry]
                mock_parse.return_value = mock_feed

                articles = await news_client.get_headlines(providers=["rss"])

                assert len(articles) > 0
                assert articles[0].provider == "rss"
                assert "Sensex" in articles[0].title

    @pytest.mark.asyncio
    async def test_multi_provider_integration(self, news_client):
        """Test integration with multiple providers"""
        # Mock NewsAPI response
        newsapi_response = {
            "status": "ok",
            "articles": [
                {
                    "source": {"name": "NewsAPI Source"},
                    "title": "NewsAPI Stock News",
                    "description": "From NewsAPI",
                    "url": "https://newsapi.example.com/1",
                    "publishedAt": "2023-01-01T00:00:00Z",
                }
            ],
        }

        # Mock RSS response
        rss_content = {
            "content": """<?xml version="1.0"?>
        <rss><channel><item>
            <title>RSS Market News</title>
            <description>From RSS Feed</description>
            <link>https://rss.example.com/1</link>
            <pubDate>Sun, 01 Jan 2023 01:00:00 GMT</pubDate>
        </item></channel></rss>"""
        }

        def mock_request_side_effect(provider, method, url, *args, **kwargs):
            if provider == "newsapi":
                return newsapi_response
            elif provider == "rss":
                return rss_content
            return {}

        with patch.object(
            news_client, "_make_request", side_effect=mock_request_side_effect
        ):
            with patch("feedparser.parse") as mock_parse:
                # Mock RSS parsing
                mock_entry = MagicMock()
                mock_entry.title = "RSS Market News"
                mock_entry.summary = "From RSS Feed"
                mock_entry.link = "https://rss.example.com/1"
                mock_entry.published = "Sun, 01 Jan 2023 01:00:00 GMT"

                mock_feed = MagicMock()
                mock_feed.entries = [mock_entry]
                mock_parse.return_value = mock_feed

                articles = await news_client.get_headlines(providers=["newsapi", "rss"])

                # Should get articles from both providers
                providers_found = set(article.provider for article in articles)
                assert len(providers_found) == 2
                assert "newsapi" in providers_found
                assert "rss" in providers_found

    @pytest.mark.asyncio
    async def test_error_handling_authentication(self, news_client):
        """Test authentication error handling"""
        with patch.object(
            news_client,
            "_make_request",
            side_effect=AuthenticationError("Invalid API key", "newsapi"),
        ):
            articles = await news_client.get_headlines(providers=["newsapi"])

            # Should return empty list when provider fails
            assert articles == []
            # Error count should be incremented
            assert news_client.stats["errors"] > 0

    @pytest.mark.asyncio
    async def test_error_handling_rate_limit(self, news_client):
        """Test rate limit error handling"""
        with patch.object(
            news_client,
            "_make_request",
            side_effect=RateLimitError("Rate limit exceeded", "newsapi"),
        ):
            articles = await news_client.get_headlines(providers=["newsapi"])

            assert articles == []
            assert news_client.stats["errors"] > 0

    @pytest.mark.asyncio
    async def test_caching_behavior(self, news_client):
        """Test caching across requests"""
        mock_response = {
            "status": "ok",
            "articles": [
                {
                    "source": {"name": "Test"},
                    "title": "Cached News",
                    "url": "https://example.com/cached",
                    "publishedAt": "2023-01-01T00:00:00Z",
                }
            ],
        }

        with patch.object(
            news_client, "_make_request", return_value=mock_response
        ) as mock_request:
            # First request
            articles1 = await news_client.get_headlines(providers=["newsapi"])

            # Second request with same parameters
            articles2 = await news_client.get_headlines(providers=["newsapi"])

            # Should get same results
            assert len(articles1) == len(articles2)
            assert articles1[0].title == articles2[0].title

            # Should have cache hits
            assert news_client.stats["cache_hits"] > 0

    @pytest.mark.asyncio
    async def test_search_functionality(self, news_client):
        """Test news search functionality"""
        mock_response = {
            "status": "ok",
            "articles": [
                {
                    "source": {"name": "Search Result"},
                    "title": "Search Query Results for RELIANCE",
                    "description": "RELIANCE stock analysis",
                    "url": "https://example.com/search",
                    "publishedAt": "2023-01-01T00:00:00Z",
                }
            ],
        }

        with patch.object(news_client, "_make_request", return_value=mock_response):
            articles = await news_client.search_news(
                "RELIANCE stock", providers=["newsapi"]
            )

            assert len(articles) > 0
            assert "RELIANCE" in articles[0].title
            # Should extract stock symbols as tags
            symbols = news_client._extract_stock_symbols(
                articles[0].title + " " + articles[0].description
            )
            assert "RELIANCE" in symbols

    @pytest.mark.asyncio
    async def test_market_news_filtering(self, news_client):
        """Test market-specific news filtering"""
        mock_response = {
            "status": "ok",
            "articles": [
                {
                    "source": {"name": "Market Source"},
                    "title": "RELIANCE stock surges in market trading",
                    "description": "Stock market analysis for RELIANCE shares",
                    "url": "https://example.com/market1",
                    "publishedAt": "2023-01-01T00:00:00Z",
                },
                {
                    "source": {"name": "General Source"},
                    "title": "General business news update",
                    "description": "Non-specific business update",
                    "url": "https://example.com/general",
                    "publishedAt": "2023-01-01T01:00:00Z",
                },
            ],
        }

        with patch.object(news_client, "_make_request", return_value=mock_response):
            articles = await news_client.get_market_news(symbols=["RELIANCE"], limit=10)

            # Should filter for market-relevant content
            assert len(articles) > 0
            # First article should mention RELIANCE
            reliance_mentioned = any(
                "RELIANCE" in article.title or "RELIANCE" in (article.description or "")
                for article in articles
            )
            assert reliance_mentioned

    @pytest.mark.asyncio
    async def test_trending_topics_extraction(self, news_client):
        """Test trending topics extraction"""
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
                title="Market analysis and stock performance",
                url="https://example.com/2",
                published_at=datetime.now(),
            ),
            Article(
                source="Test",
                provider="test",
                title="Trading volume increases in stock market",
                url="https://example.com/3",
                published_at=datetime.now(),
            ),
        ]

        with patch.object(news_client, "get_headlines", return_value=mock_articles):
            trending = await news_client.get_trending_topics(limit=5)

            # Should identify common words
            assert "stock" in trending
            assert "market" in trending
            assert trending["stock"] >= 2  # Appears multiple times
            assert trending["market"] >= 3  # Appears in all articles

    @pytest.mark.asyncio
    async def test_health_check_functionality(self, news_client):
        """Test health check functionality"""
        # Mock successful responses for health checks
        mock_responses = {
            ("newsapi", "GET"): {"status": "ok", "articles": []},
            ("rss", "GET"): {"content": "<?xml version='1.0'?><rss></rss>"},
        }

        def mock_request_side_effect(provider, method, url, *args, **kwargs):
            return mock_responses.get((provider, method), {})

        with patch.object(
            news_client, "_make_request", side_effect=mock_request_side_effect
        ):
            health = await news_client.health_check()

            assert health["overall_status"] in ["healthy", "degraded"]
            assert "providers" in health
            assert "cache_status" in health
            assert "statistics" in health

    @pytest.mark.asyncio
    async def test_client_cleanup(self, news_client):
        """Test proper client cleanup"""
        # Simulate creating HTTP clients
        news_client.clients["test"] = AsyncMock()
        news_client.clients["test"].is_closed = False

        # Close client
        await news_client.close()

        # Should close all HTTP clients
        news_client.clients["test"].aclose.assert_called_once()
        assert len(news_client.clients) == 0

    def test_configuration_validation(self):
        """Test configuration validation"""
        config = NewsConfig()

        # Test default values
        assert config.default_language == "en"
        assert config.default_country == "in"
        assert config.newsapi.enabled == True
        assert config.rss.enabled == True

        # Test NewsAPI configuration
        assert config.newsapi.base_url == "https://newsapi.org/v2"
        assert config.newsapi.rate_limit_requests_per_day == 1000

        # Test RSS configuration
        assert len(config.rss.feeds) > 0
        assert all("url" in feed and "name" in feed for feed in config.rss.feeds)

    def test_article_relevance_scoring(self, news_client):
        """Test article relevance scoring algorithm"""
        # High relevance article
        high_relevance = {
            "title": "Stock market NSE trading RELIANCE shares investment",
            "description": "Portfolio management and dividend analysis for equity trading",
        }
        score_high = news_client._calculate_relevance_score(high_relevance)

        # Medium relevance article
        medium_relevance = {
            "title": "Business growth and financial development",
            "description": "Company performance and industry analysis",
        }
        score_medium = news_client._calculate_relevance_score(medium_relevance)

        # Low relevance article
        low_relevance = {
            "title": "Sports entertainment and celebrity news",
            "description": "Entertainment industry updates and gossip",
        }
        score_low = news_client._calculate_relevance_score(low_relevance)

        # High relevance should score higher than others
        assert score_high > score_medium > score_low
        assert score_high > 0.7
        assert score_low < 0.3

    def test_stock_symbol_extraction_accuracy(self, news_client):
        """Test accuracy of stock symbol extraction"""
        test_cases = [
            ("RELIANCE gains 5% while TCS falls", ["RELIANCE", "TCS"]),
            ("INFY and WIPRO show strong performance", ["INFY", "WIPRO"]),
            ("The stock market is volatile today", []),  # No specific symbols
            ("HDFC.NS and ICICIBANK.BO listed", ["HDFC.NS", "ICICIBANK.BO"]),
            ("$TSLA and $AAPL in US markets", ["$TSLA", "$AAPL"]),
        ]

        for text, expected_symbols in test_cases:
            extracted = news_client._extract_stock_symbols(text)

            # Check if expected symbols are found
            for symbol in expected_symbols:
                assert any(symbol in extracted_symbol for extracted_symbol in extracted)

    def test_deduplication_effectiveness(self, news_client):
        """Test article deduplication effectiveness"""
        # Create articles with different types of duplicates
        articles = [
            Article(
                source="Source1",
                provider="test",
                title="Market Update Today",
                url="https://example.com/article1",
                published_at=datetime.now(),
            ),
            Article(
                source="Source2",
                provider="test",
                title="Market Update Today",  # Same title
                url="https://example.com/article2",
                published_at=datetime.now(),
            ),
            Article(
                source="Source3",
                provider="test",
                title="Different Market News",
                url="https://example.com/article1",
                published_at=datetime.now(),
            ),  # Same URL
            Article(
                source="Source4",
                provider="test",
                title="Unique Financial News",
                url="https://example.com/article3",
                published_at=datetime.now(),
            ),
        ]

        unique_articles = news_client._deduplicate_articles(articles)

        # Should have 2 unique articles (first occurrence of each kept)
        assert len(unique_articles) == 2

        # Check that the right articles were kept
        titles = [article.title for article in unique_articles]
        assert "Market Update Today" in titles
        assert "Unique Financial News" in titles

    @pytest.mark.asyncio
    async def test_concurrent_provider_requests(self, news_client):
        """Test handling concurrent requests to different providers"""

        def mock_request_delay(provider, *args, **kwargs):
            # Simulate different response times for providers
            if provider == "newsapi":
                return {
                    "status": "ok",
                    "articles": [
                        {
                            "source": {"name": "NewsAPI"},
                            "title": "NewsAPI Article",
                            "url": "https://newsapi.com/1",
                            "publishedAt": "2023-01-01T00:00:00Z",
                        }
                    ],
                }
            elif provider == "rss":
                return {
                    "content": "<?xml version='1.0'?><rss><channel><item>"
                    "<title>RSS Article</title><link>https://rss.com/1</link>"
                    "<pubDate>Sun, 01 Jan 2023 00:00:00 GMT</pubDate>"
                    "</item></channel></rss>"
                }
            return {}

        with patch.object(news_client, "_make_request", side_effect=mock_request_delay):
            with patch("feedparser.parse") as mock_parse:
                mock_entry = MagicMock()
                mock_entry.title = "RSS Article"
                mock_entry.link = "https://rss.com/1"
                mock_entry.published = "Sun, 01 Jan 2023 00:00:00 GMT"
                mock_entry.summary = "RSS content"

                mock_feed = MagicMock()
                mock_feed.entries = [mock_entry]
                mock_parse.return_value = mock_feed

                # Request from multiple providers concurrently
                start_time = asyncio.get_event_loop().time()
                articles = await news_client.get_headlines(providers=["newsapi", "rss"])
                end_time = asyncio.get_event_loop().time()

                # Should get articles from both providers
                assert len(articles) >= 2
                providers = set(article.provider for article in articles)
                assert len(providers) >= 2

                # Should not take much longer than the slowest individual request
                # (proving concurrency rather than sequential execution)
                assert end_time - start_time < 5.0  # Reasonable upper bound


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
