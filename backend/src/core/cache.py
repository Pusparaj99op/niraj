"""
NIRAJ Redis Cache Configuration
Redis setup for caching and real-time data storage
"""

import json
import pickle
from typing import Any, Optional, Dict, List, AsyncGenerator
import os
from contextlib import asynccontextmanager

import redis.asyncio as redis
import structlog

logger = structlog.get_logger()

# Redis configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REDIS_MAX_CONNECTIONS = int(os.getenv("REDIS_MAX_CONNECTIONS", "20"))
REDIS_RETRY_ON_TIMEOUT = True
REDIS_SOCKET_KEEPALIVE = True
REDIS_SOCKET_KEEPALIVE_OPTIONS = {}

# Cache key prefixes
CACHE_PREFIXES = {
    "market_data": "md:",
    "user_session": "session:",
    "api_rate_limit": "rate:",
    "strategy_signals": "signals:",
    "portfolio": "portfolio:",
    "ai_predictions": "ai:",
    "system_status": "status:",
    "websocket": "ws:",
    "temp_data": "temp:",
}

# Default TTL values (in seconds)
DEFAULT_TTL = {
    "market_data": 300,  # 5 minutes
    "user_session": 86400,  # 24 hours
    "api_rate_limit": 3600,  # 1 hour
    "strategy_signals": 1800,  # 30 minutes
    "portfolio": 600,  # 10 minutes
    "ai_predictions": 900,  # 15 minutes
    "system_status": 60,  # 1 minute
    "websocket": 300,  # 5 minutes
    "temp_data": 300,  # 5 minutes
}


class RedisCache:
    """Redis cache manager for NIRAJ system"""

    def __init__(self, redis_url: str = REDIS_URL):
        self.redis_url = redis_url
        self.redis_pool: Optional[redis.ConnectionPool] = None
        self.redis_client: Optional[redis.Redis] = None
        self._connected = False

    async def connect(self):
        """Establish Redis connection"""
        try:
            self.redis_pool = redis.ConnectionPool.from_url(
                self.redis_url,
                max_connections=REDIS_MAX_CONNECTIONS,
                retry_on_timeout=REDIS_RETRY_ON_TIMEOUT,
                socket_keepalive=REDIS_SOCKET_KEEPALIVE,
                socket_keepalive_options=REDIS_SOCKET_KEEPALIVE_OPTIONS,
            )

            self.redis_client = redis.Redis(
                connection_pool=self.redis_pool, decode_responses=True
            )

            # Test connection
            await self.redis_client.ping()
            self._connected = True
            logger.info("Redis connection established")

        except Exception as e:
            logger.error("Failed to connect to Redis", error=str(e))
            self._connected = False
            raise

    async def disconnect(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
        if self.redis_pool:
            await self.redis_pool.disconnect()

        self._connected = False
        logger.info("Redis connection closed")

    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[redis.Redis, None]:
        """Get Redis connection context manager"""
        if not self._connected:
            await self.connect()

        if self.redis_client is None:
            raise RuntimeError("Redis client is not initialized")

        try:
            yield self.redis_client
        except redis.ConnectionError as e:
            logger.error("Redis connection error", error=str(e))
            await self.connect()  # Reconnect
            if self.redis_client is None:
                raise RuntimeError("Failed to reconnect to Redis")
            yield self.redis_client

    def _make_key(self, prefix: str, key: str) -> str:
        """Generate cache key with prefix"""
        return f"{CACHE_PREFIXES.get(prefix, prefix)}{key}"

    async def set(
        self,
        key: str,
        value: Any,
        prefix: str = "temp_data",
        ttl: Optional[int] = None,
        serialize: str = "json",
    ) -> bool:
        """Set cache value"""
        try:
            full_key = self._make_key(prefix, key)

            # Serialize value
            try:
                if serialize == "json":
                    serialized_value = json.dumps(value, default=str)
                elif serialize == "pickle":
                    serialized_value = pickle.dumps(value)
                else:
                    serialized_value = str(value)
            except Exception as e:
                logger.error("Serialization failed", key=key, serialize=serialize, error=str(e))
                return False

            # Set TTL
            if ttl is None:
                ttl = DEFAULT_TTL.get(prefix, DEFAULT_TTL["temp_data"])

            async with self.get_connection() as redis_client:
                result: bool = await redis_client.setex(full_key, ttl, serialized_value)

            logger.debug("Cache set", key=full_key, ttl=ttl)
            return bool(result)

        except Exception as e:
            logger.error("Cache set failed", key=key, error=str(e))
            return False

    async def get(
        self,
        key: str,
        prefix: str = "temp_data",
        deserialize: str = "json",
        default: Any = None,
    ) -> Any:
        """Get cache value"""
        try:
            full_key = self._make_key(prefix, key)

            async with self.get_connection() as redis_client:
                value: Optional[str] = await redis_client.get(full_key)

            if value is None:
                return default

            # Deserialize value
            try:
                if deserialize == "json":
                    return json.loads(value)
                elif deserialize == "pickle":
                    # For pickle, we need the raw bytes. We must re-fetch without decoding.
                    async with self.get_connection() as redis_client:
                        # Temporarily get a client that doesn't decode responses
                        raw_client = redis.Redis(connection_pool=self.redis_pool, decode_responses=False)
                        value_bytes: Optional[bytes] = await raw_client.get(full_key)
                        await raw_client.close()

                    if value_bytes is None:
                        return default
                    return pickle.loads(value_bytes)
                else:
                    return value
            except Exception as e:
                logger.error("Deserialization failed", key=key, deserialize=deserialize, error=str(e))
                return default

        except Exception as e:
            logger.error("Cache get failed", key=key, error=str(e))
            return default

    async def delete(self, key: str, prefix: str = "temp_data") -> bool:
        """Delete cache key"""
        try:
            full_key = self._make_key(prefix, key)

            async with self.get_connection() as redis_client:
                result: int = await redis_client.delete(full_key)

            logger.debug("Cache delete", key=full_key)
            return bool(result)

        except Exception as e:
            logger.error("Cache delete failed", key=key, error=str(e))
            return False

    async def exists(self, key: str, prefix: str = "temp_data") -> bool:
        """Check if cache key exists"""
        try:
            full_key = self._make_key(prefix, key)

            async with self.get_connection() as redis_client:
                result: int = await redis_client.exists(full_key)

            return bool(result)

        except Exception as e:
            logger.error("Cache exists check failed", key=key, error=str(e))
            return False

    async def expire(self, key: str, ttl: int, prefix: str = "temp_data") -> bool:
        """Set a TTL on a key."""
        try:
            full_key = self._make_key(prefix, key)
            async with self.get_connection() as redis_client:
                result: bool = await redis_client.expire(full_key, ttl)
            return result
        except Exception as e:
            logger.error("Cache expire failed", key=key, error=str(e))
            return False

    async def increment(
        self, key: str, prefix: str = "temp_data", amount: int = 1
    ) -> int:
        """Increment cache value"""
        try:
            full_key = self._make_key(prefix, key)

            async with self.get_connection() as redis_client:
                result: int = await redis_client.incrby(full_key, amount)

            return result

        except Exception as e:
            logger.error("Cache increment failed", key=key, error=str(e))
            return 0

    async def set_hash(
        self,
        key: str,
        mapping: Dict[str, Any],
        prefix: str = "temp_data",
        ttl: Optional[int] = None,
    ) -> bool:
        """Set hash cache value"""
        try:
            full_key = self._make_key(prefix, key)

            # Convert values to strings
            try:
                string_mapping = {k: json.dumps(v, default=str) for k, v in mapping.items()}
            except Exception as e:
                logger.error("Hash serialization failed", key=key, error=str(e))
                return False

            async with self.get_connection() as redis_client:
                await redis_client.hset(full_key, mapping=string_mapping)

                if ttl is None:
                    ttl = DEFAULT_TTL.get(prefix, DEFAULT_TTL["temp_data"])
                await redis_client.expire(full_key, ttl)

            logger.debug("Cache hash set", key=full_key, fields=len(mapping))
            return True

        except Exception as e:
            logger.error("Cache hash set failed", key=key, error=str(e))
            return False

    async def get_hash(self, key: str, prefix: str = "temp_data") -> Dict[str, Any]:
        """Get hash cache value"""
        try:
            full_key = self._make_key(prefix, key)

            async with self.get_connection() as redis_client:
                hash_data: Dict[str, str] = await redis_client.hgetall(full_key)

            # Deserialize values
            result = {}
            for k, v in hash_data.items():
                try:
                    result[k] = json.loads(v)
                except Exception as e:
                    logger.warning("Failed to deserialize hash value", key=k, error=str(e))
                    result[k] = v

            return result

        except Exception as e:
            logger.error("Cache hash get failed", key=key, error=str(e))
            return {}

    async def publish(self, channel: str, message: Any) -> int:
        """Publish message to Redis channel"""
        try:
            try:
                serialized_message = json.dumps(message, default=str)
            except Exception as e:
                logger.error("Message serialization failed", channel=channel, error=str(e))
                return 0

            async with self.get_connection() as redis_client:
                result: int = await redis_client.publish(channel, serialized_message)

            logger.debug("Message published", channel=channel, subscribers=result)
            return result

        except Exception as e:
            logger.error("Message publish failed", channel=channel, error=str(e))
            return 0

    async def subscribe(self, *channels: str):
        """Subscribe to Redis channels"""
        try:
            async with self.get_connection() as redis_client:
                pubsub = redis_client.pubsub()
                await pubsub.subscribe(*channels)
                return pubsub

        except Exception as e:
            logger.error("Channel subscribe failed", channels=channels, error=str(e))
            return None

    async def health_check(self) -> bool:
        """Check Redis connectivity"""
        try:
            async with self.get_connection() as redis_client:
                response: bool = await redis_client.ping()
                return response is True
        except Exception as e:
            logger.error("Redis health check failed", error=str(e))
            return False

    async def get_stats(self) -> Dict[str, Any]:
        """Get Redis statistics"""
        try:
            async with self.get_connection() as redis_client:
                info: Dict[str, Any] = await redis_client.info()

                return {
                    "connected_clients": info.get("connected_clients", 0),
                    "used_memory_human": info.get("used_memory_human", "0B"),
                    "used_memory_peak_human": info.get("used_memory_peak_human", "0B"),
                    "total_commands_processed": info.get("total_commands_processed", 0),
                    "keyspace_hits": info.get("keyspace_hits", 0),
                    "keyspace_misses": info.get("keyspace_misses", 0),
                    "uptime_in_seconds": info.get("uptime_in_seconds", 0),
                }
        except Exception as e:
            logger.error("Failed to get Redis stats", error=str(e))
            return {}

    async def clear_prefix(self, prefix: str) -> int:
        """Clear all keys with given prefix"""
        try:
            pattern = f"{CACHE_PREFIXES.get(prefix, prefix)}*"

            async with self.get_connection() as redis_client:
                keys: List[str] = await redis_client.keys(pattern)
                if keys:
                    result: int = await redis_client.delete(*keys)
                    logger.info(
                        "Cache prefix cleared", prefix=prefix, keys_deleted=result
                    )
                    return result
                return 0

        except Exception as e:
            logger.error("Cache prefix clear failed", prefix=prefix, error=str(e))
            return 0

    async def get_ttl(self, key: str, prefix: str = "temp_data") -> int:
        """Get TTL for a cache key"""
        try:
            full_key = self._make_key(prefix, key)

            async with self.get_connection() as redis_client:
                ttl: int = await redis_client.ttl(full_key)
                return ttl if ttl >= 0 else -1  # -1 if key doesn't exist or no TTL

        except Exception as e:
            logger.error("Cache TTL get failed", key=key, error=str(e))
            return -1

    async def sadd(self, key: str, *values: Any, prefix: str = "temp_data") -> int:
        """Add members to a set."""
        try:
            full_key = self._make_key(prefix, key)
            # Redis `sadd` expects string values, so we serialize them.
            str_values = [json.dumps(v, default=str) for v in values]
            async with self.get_connection() as redis_client:
                return redis_client.sadd(full_key, *str_values)
        except Exception as e:
            logger.error("Cache sadd failed", key=key, error=str(e))
            return 0

    async def srem(self, key: str, *values: Any, prefix: str = "temp_data") -> int:
        """Remove members from a set."""
        try:
            full_key = self._make_key(prefix, key)
            str_values = [json.dumps(v, default=str) for v in values]
            async with self.get_connection() as redis_client:
                return redis_client.srem(full_key, *str_values)
        except Exception as e:
            logger.error("Cache srem failed", key=key, error=str(e))
            return 0

    async def sismember(self, key: str, value: Any, prefix: str = "temp_data") -> bool:
        """Check if a member exists in a set."""
        try:
            full_key = self._make_key(prefix, key)
            str_value = json.dumps(value, default=str)
            async with self.get_connection() as redis_client:
                result: int = await redis_client.sismember(full_key, str_value)
                return bool(result)
        except Exception as e:
            logger.error("Cache sismember failed", key=key, error=str(e))
            return False

    async def scard(self, key: str, prefix: str = "temp_data") -> int:
        """Get the number of members in a set."""
        try:
            full_key = self._make_key(prefix, key)
            async with self.get_connection() as redis_client:
                return await redis_client.scard(full_key)
        except Exception as e:
            logger.error("Cache scard failed", key=key, error=str(e))
            return 0

    async def smembers(self, key: str, prefix: str = "temp_data") -> set:
        """Get all members of a set."""
        try:
            full_key = self._make_key(prefix, key)
            async with self.get_connection() as redis_client:
                members: set[str] = await redis_client.smembers(full_key)
                return {json.loads(m) for m in members}
        except Exception as e:
            logger.error("Cache smembers failed", key=key, error=str(e))
            return set()


# Market data specific cache functions
class MarketDataCache:
    """Market data specific caching functions"""

    def __init__(self, cache: RedisCache):
        self.cache = cache

    async def cache_market_data(
        self, symbol: str, timeframe: str, data: List[Dict]
    ) -> bool:
        """Cache market data for symbol and timeframe"""
        key = f"{symbol}:{timeframe}"
        return await self.cache.set(key, data, prefix="market_data")

    async def get_market_data(self, symbol: str, timeframe: str) -> List[Dict]:
        """Get cached market data"""
        key = f"{symbol}:{timeframe}"
        return await self.cache.get(key, prefix="market_data", default=[])

    async def cache_latest_price(
        self, symbol: str, price: float, timestamp: str
    ) -> bool:
        """Cache latest price for symbol"""
        key = f"{symbol}:latest"
        data = {"price": price, "timestamp": timestamp}
        return await self.cache.set(
            key, data, prefix="market_data", ttl=60
        )  # 1 minute TTL

    async def get_latest_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get cached latest price for symbol"""
        key = f"{symbol}:latest"
        return await self.cache.get(key, prefix="market_data", default=None)


# Global cache instances
redis_cache = RedisCache()
market_data_cache = MarketDataCache(redis_cache)


class CacheManager:
    """Cache manager providing unified interface for caching operations"""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_cache = RedisCache(redis_url=redis_url)

    async def connect(self):
        """Connect to Redis"""
        await self.redis_cache.connect()

    async def disconnect(self):
        """Disconnect from Redis"""
        await self.redis_cache.disconnect()

    async def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache"""
        return await self.redis_cache.get(key, default=default)

    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Set value in cache with TTL"""
        return await self.redis_cache.set(key, value, ttl=ttl)

    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        return await self.redis_cache.delete(key)

    async def health_check(self):
        """Check cache health"""
        return await self.redis_cache.health_check()

    async def start_background_tasks(self):
        """Start background maintenance tasks"""
        # Redis cache doesn't have background tasks currently
        pass

    async def close(self):
        """Close cache connections"""
        await self.redis_cache.disconnect()

    async def expire(self, key: str, ttl: int, prefix: str = "temp_data") -> bool:
        """Set a TTL on a key."""
        return await self.redis_cache.expire(key, ttl, prefix=prefix)

    async def increment(self, key: str, prefix: str = "temp_data", amount: int = 1) -> int:
        """Increment a value in the cache."""
        return await self.redis_cache.increment(key, prefix=prefix, amount=amount)

    async def sadd(self, key: str, *values: Any, prefix: str = "temp_data") -> int:
        """Add members to a set in the cache."""
        return await self.redis_cache.sadd(key, *values, prefix=prefix)

    async def srem(self, key: str, *values: Any, prefix: str = "temp_data") -> int:
        """Remove members from a set in the cache."""
        return await self.redis_cache.srem(key, *values, prefix=prefix)

    async def sismember(self, key: str, value: Any, prefix: str = "temp_data") -> bool:
        """Check if a member exists in a set in the cache."""
        return await self.redis_cache.sismember(key, value, prefix=prefix)

    async def scard(self, key: str, prefix: str = "temp_data") -> int:
        """Get the number of members in a set in the cache."""
        return await self.redis_cache.scard(key, prefix=prefix)

    async def smembers(self, key: str, prefix: str = "temp_data") -> set:
        """Get all members of a set from the cache."""
        return await self.redis_cache.smembers(key, prefix=prefix)

    async def get_ttl(self, key: str, prefix: str = "temp_data") -> int:
        """Get the TTL of a key in the cache."""
        return await self.redis_cache.get_ttl(key, prefix=prefix)


# FastAPI dependency
async def get_cache() -> RedisCache:
    """FastAPI dependency for Redis cache"""
    if not redis_cache._connected:
        await redis_cache.connect()
    return redis_cache


# Application lifecycle
async def init_cache():
    """Initialize cache connection"""
    await redis_cache.connect()
    logger.info("Cache system initialized")


async def cleanup_cache():
    """Cleanup cache connections"""
    await redis_cache.disconnect()
    logger.info("Cache system cleaned up")


# Cache decorators and utilities
def cache_key(*args, **kwargs) -> str:
    """Generate cache key from arguments"""
    key_parts = []
    key_parts.extend(str(arg) for arg in args)
    key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
    return ":".join(key_parts)


async def cached_function(func, cache_prefix: str, ttl: int = 300, *args, **kwargs):
    """Generic function caching"""
    key = cache_key(func.__name__, *args, **kwargs)

    # Try to get from cache
    result = await redis_cache.get(key, prefix=cache_prefix)
    if result is not None:
        return result

    # Execute function and cache result
    result = await func(*args, **kwargs)
    await redis_cache.set(key, result, prefix=cache_prefix, ttl=ttl)

    return result
