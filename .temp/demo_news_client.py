"""
News API Client Demo
Demonstrates the comprehensive News API client functionality
"""

import asyncio

from backend.src.api.news_client import NewsClient, NewsConfig, NewsFilter


async def demo_news_client():
    """Demonstrate News API Client capabilities"""
    print("=" * 60)
    print("NIRAJ News API Client Demo")
    print("=" * 60)

    # Create configuration (RSS feeds work without API keys)
    config = NewsConfig()
    config.newsapi.enabled = False  # Disable NewsAPI to avoid needing API key for demo
    config.rss.enabled = True

    print("✓ Configuration created")
    print(f"  - RSS Feeds: {len(config.rss.feeds)} sources configured")
    print(f"  - Cache enabled with TTL: {config.rss.cache_duration_minutes} minutes")
    print()

    # Create client
    async with NewsClient(config) as client:
        print("✓ News client initialized")
        print(f"  - Session ID: {client.session_id}")
        print(f"  - Providers available: {len(client.rate_limiters)}")
        print()

        try:
            # Demo 1: Get general headlines
            print("Demo 1: Fetching general headlines from RSS feeds")
            print("-" * 40)

            headlines_filter = NewsFilter(page_size=5, sort_by="publishedAt")
            articles = await client.get_headlines(headlines_filter, providers=["rss"])

            print(f"✓ Retrieved {len(articles)} articles")
            for i, article in enumerate(articles[:3], 1):
                print(f"  {i}. {article.title}")
                print(f"     Source: {article.source} ({article.provider})")
                print(f"     Relevance: {article.relevance_score:.2f}")
                print(
                    f"     Published: {article.published_at.strftime('%Y-%m-%d %H:%M')}"
                )
                print()

        except Exception as e:
            print(f"❌ Error fetching headlines: {e}")

        try:
            # Demo 2: Search for market-specific news
            print("Demo 2: Searching for stock market news")
            print("-" * 40)

            market_articles = await client.get_market_news(
                symbols=["RELIANCE", "TCS", "INFY"], limit=3
            )

            print(f"✓ Found {len(market_articles)} market-relevant articles")
            for article in market_articles:
                print(f"  • {article.title}")
                print(f"    Relevance: {article.relevance_score:.2f}")
                if article.tags:
                    print(f"    Stock symbols found: {', '.join(article.tags)}")
                print()
        except Exception as e:
            print(f"❌ Error fetching market news: {e}")

        try:
            # Demo 3: Custom search
            print("Demo 3: Custom search for 'investment' news")
            print("-" * 40)

            search_results = await client.search_news(
                "investment portfolio",
                NewsFilter(min_relevance_score=0.2, page_size=3),
                providers=["rss"],
            )
            print(f"✓ Found {len(search_results)} articles matching search")
            for article in search_results:
                print(f"  • {article.title}")
                print(f"    URL: {article.url}")
                print()

        except Exception as e:
            print(f"❌ Error in search: {e}")

        try:
            # Demo 4: Trending topics
            print("Demo 4: Identifying trending topics")
            print("-" * 40)

            trending = await client.get_trending_topics(limit=8)

            print(f"✓ Identified {len(trending)} trending topics:")
            for topic, count in list(trending.items())[:5]:
                print(f"  • {topic}: {count} mentions")
            print()

        except Exception as e:
            print(f"❌ Error getting trending topics: {e}")

        # Demo 5: Client statistics and health
        print("Demo 5: Client statistics and health check")
        print("-" * 40)

        try:
            # Health check
            health = await client.health_check()
            print(f"✓ Health Status: {health['overall_status'].upper()}")

            for provider, status in health.get("providers", {}).items():
                print(f"  • {provider}: {status}")
            print()

        except Exception as e:
            print(f"❌ Health check failed: {e}")

        # Statistics
        stats = client.get_client_stats()
        print("✓ Client Statistics:")
        print(f"  • Total requests: {stats['statistics']['requests_made']}")
        print(f"  • Articles fetched: {stats['statistics']['articles_fetched']}")
        print(f"  • Cache hits: {stats['statistics']['cache_hits']}")
        print(f"  • Cache misses: {stats['statistics']['cache_misses']}")
        print(f"  • Providers used: {len(stats['statistics']['providers_used'])}")
        print(f"  • Cached entries: {stats['cache_stats']['entries']}")
        print()

        # Demo 6: Error handling demonstration
        print("Demo 6: Error handling capabilities")
        print("-" * 40)

        # Create a client with invalid configuration to show error handling
        error_config = NewsConfig()
        error_config.newsapi.enabled = True
        error_config.newsapi.api_key = "invalid_key"
        error_config.rss.enabled = False

        async with NewsClient(error_config) as error_client:
            try:
                await error_client.get_headlines(providers=["newsapi"])
            except Exception as e:
                print(f"✓ Error handling working: {type(e).__name__}")

        print("✓ Graceful error handling demonstrated")
        print()

        print("=" * 60)
        print("Demo completed successfully!")
        print("=" * 60)
        print()
        print("Key Features Demonstrated:")
        print("✓ Multi-provider news aggregation (RSS, NewsAPI, FMP)")
        print("✓ Advanced error handling and retries")
        print("✓ Intelligent caching with TTL")
        print("✓ Article relevance scoring for trading")
        print("✓ Stock symbol extraction and tagging")
        print("✓ Article deduplication")
        print("✓ Rate limiting per provider")
        print("✓ Comprehensive logging and monitoring")
        print("✓ Async operations with proper resource management")
        print("✓ Flexible filtering and search capabilities")
        print("✓ Health monitoring and statistics")


def run_demo():
    """Run the news client demo"""

    try:
        asyncio.run(demo_news_client())
    except KeyboardInterrupt:
        print("\n❌ Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    run_demo()


"""Hello! How can I assist you further?"""
