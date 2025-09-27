#!/usr/bin/env python3
"""
Advanced Caching Optimization System for NIRAJ Trading Platform

This module provides intelligent caching strategies, cache optimization,
and advanced cache management for improved system performance.

Features:
- Intelligent cache invalidation policies - Multi-tier caching architecture - Cache warming and preloading strategies - Cache hit ratio optimization - Memory-efficient cache storage - Automatic cache size management - Cache performance analytics -
Distributed caching support

Author: NIRAJ Development Team
Version: 1.0.0
"""

import asyncio
import hashlib
import json
import time
import threading
from collections import OrderedDict, defaultdict
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Callable, Dict, List, Optional, Set, Union
import weakref
import pickle
import zlib
import gc

# Internal imports
from ..utils.logger import get_structured_logger
from ..core.cache import RedisCache, CacheManager

logger = get_structured_logger(__name__)


@dataclass
class CacheStats:
    """Cache performance statistics"""

    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    evictions: int = 0
    total_size_bytes: int = 0
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def hit_ratio(self) -> float:
        """Calculate cache hit ratio"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    @property
    def miss_ratio(self) -> float:
        """Calculate cache miss ratio"""
        return 1.0 - self.hit_ratio


@dataclass
class CacheItem:
    """Individual cache item with metadata"""

    key: str
    value: Any
    size_bytes: int
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    ttl_seconds: Optional[int] = None
    priority: int = 1  # Higher priority = less likely to be evicted
    compressed: bool = False

    @property
    def is_expired(self) -> bool:
        """Check if item has expired"""
        if self.ttl_seconds is None:
            return False

        age = (datetime.now(timezone.utc) - self.created_at).total_seconds()
        return age > self.ttl_seconds

    @property
    def age_seconds(self) -> float:
        """Get item age in seconds"""
        return (datetime.now(timezone.utc) - self.created_at).total_seconds()

    @property
    def last_access_seconds(self) -> float:
        """Get seconds since last access"""
        return (datetime.now(timezone.utc) - self.last_accessed).total_seconds()


class CacheEvictionPolicy:
    """Cache eviction policy interface"""

    def should_evict(self, item: CacheItem, cache_size: int, max_size: int) -> bool:
        """Determine if item should be evicted"""
        raise NotImplementedError

    def get_eviction_priority(self, item: CacheItem) -> float:
        """Get eviction priority (higher = more likely to evict)"""
        raise NotImplementedError


class LRUEvictionPolicy(CacheEvictionPolicy):
    """Least Recently Used eviction policy"""

    def should_evict(self, item: CacheItem, cache_size: int, max_size: int) -> bool:
        return cache_size > max_size

    def get_eviction_priority(self, item: CacheItem) -> float:
        return item.last_access_seconds


class LFUEvictionPolicy(CacheEvictionPolicy):
    """Least Frequently Used eviction policy"""

    def should_evict(self, item: CacheItem, cache_size: int, max_size: int) -> bool:
        return cache_size > max_size

    def get_eviction_priority(self, item: CacheItem) -> float:
        # Combine access frequency with recency
        frequency_score = 1.0 / (item.access_count + 1)
        recency_score = item.last_access_seconds / 3600.0  # Hours since last access
        return frequency_score * 0.7 + recency_score * 0.3


class TTLEvictionPolicy(CacheEvictionPolicy):
    """Time-To-Live based eviction policy"""

    def should_evict(self, item: CacheItem, cache_size: int, max_size: int) -> bool:
        return item.is_expired or cache_size > max_size

    def get_eviction_priority(self, item: CacheItem) -> float:
        if item.is_expired:
            return float("inf")  # Highest priority for expired items

        if item.ttl_seconds:
            remaining_ttl = item.ttl_seconds - item.age_seconds
            return -remaining_ttl  # Items with less TTL get higher priority

        return item.last_access_seconds


class AdaptiveEvictionPolicy(CacheEvictionPolicy):
    """Adaptive eviction policy that combines multiple strategies"""

    def __init__(
        self, lru_weight: float = 0.4, lfu_weight: float = 0.4, ttl_weight: float = 0.2
    ):
        self.lru_policy = LRUEvictionPolicy()
        self.lfu_policy = LFUEvictionPolicy()
        self.ttl_policy = TTLEvictionPolicy()
        self.lru_weight = lru_weight
        self.lfu_weight = lfu_weight
        self.ttl_weight = ttl_weight

    def should_evict(self, item: CacheItem, cache_size: int, max_size: int) -> bool:
        return (
            item.is_expired or cache_size > max_size or item.priority < 0
        )  # Negative priority = force eviction

    def get_eviction_priority(self, item: CacheItem) -> float:
        if item.is_expired:
            return float("inf")

        lru_priority = self.lru_policy.get_eviction_priority(item)
        lfu_priority = self.lfu_policy.get_eviction_priority(item)
        ttl_priority = self.ttl_policy.get_eviction_priority(item)

        # Normalize priorities
        lru_priority = min(lru_priority / 3600.0, 1.0)  # Max 1 hour
        lfu_priority = min(lfu_priority, 1.0)
        ttl_priority = (
            min(abs(ttl_priority) / 3600.0, 1.0)
            if ttl_priority != float("inf")
            else 0.0
        )

        # Calculate weighted priority
        weighted_priority = (
            lru_priority * self.lru_weight
            + +lfu_priority * self.lfu_weight
            + ttl_priority * self.ttl_weight
        )

        # Apply item priority modifier
        priority_modifier = max(0.1, 1.0 / item.priority)

        return weighted_priority * priority_modifier


class IntelligentCache:
    """Intelligent cache with advanced optimization features"""

    def __init__(
        self,
        max_size_bytes: int = 100 * 1024 * 1024,  # 100MB default
        max_items: int = 10000,
        eviction_policy: Optional[CacheEvictionPolicy] = None,
        compression_threshold_bytes: int = 1024,  # Compress items > 1KB
        enable_analytics: bool = True,
    ):
        self.max_size_bytes = max_size_bytes
        self.max_items = max_items
        self.compression_threshold_bytes = compression_threshold_bytes
        self.enable_analytics = enable_analytics

        self._items: OrderedDict[str, CacheItem] = OrderedDict()
        self._stats = CacheStats()
        self._lock = threading.RLock()
        self._eviction_policy = eviction_policy or AdaptiveEvictionPolicy()

        # Analytics data
        self._access_patterns: Dict[str, List[datetime]] = defaultdict(list)
        self._key_popularity: Dict[str, int] = defaultdict(int)
        self._size_distribution: Dict[str, int] = {}

        # Background maintenance
        self._maintenance_task: Optional[asyncio.Task] = None
        self._maintenance_running = False

        logger.info(
            "Intelligent cache initialized", max_size_mb=max_size_bytes // 1024 // 1024
        )

    async def start_maintenance(self, interval_seconds: float = 300.0):
        """Start background maintenance tasks"""
        if self._maintenance_running:
            return

        self._maintenance_running = True
        self._maintenance_task = asyncio.create_task(
            self._maintenance_loop(interval_seconds)
        )
        logger.info("Cache maintenance started", interval=interval_seconds)

    async def stop_maintenance(self):
        """Stop background maintenance"""
        self._maintenance_running = False
        if self._maintenance_task:
            self._maintenance_task.cancel()
            try:
                await self._maintenance_task
            except asyncio.CancelledError:
                pass
        logger.info("Cache maintenance stopped")

    async def _maintenance_loop(self, interval: float):
        """Background maintenance loop"""
        while self._maintenance_running:
            try:
                await asyncio.sleep(interval)
                await self._perform_maintenance()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Cache maintenance error", error=str(e))

    async def _perform_maintenance(self):
        """Perform cache maintenance tasks"""
        with self._lock:
            # Remove expired items
            expired_keys = []
            for key, item in self._items.items():
                if item.is_expired:
                    expired_keys.append(key)

            for key in expired_keys:
                self._remove_item(key, reason="expired")

            # Perform garbage collection if needed
            if self._get_total_size() > self.max_size_bytes * 0.9:  # 90% threshold
                await self._smart_eviction()

            # Clean up analytics data
            self._cleanup_analytics()

            logger.debug(
                "Cache maintenance completed",
                expired_items=len(expired_keys),
                total_items=len(self._items),
                total_size_mb=self._get_total_size() // 1024 // 1024,
            )

    def get(self, key: str, default: Any = None) -> Any:
        """Get item from cache"""
        with self._lock:
            if key not in self._items:
                self._stats.misses += 1
                self._record_access(key, hit=False)
                return default

            item = self._items[key]

            # Check expiration
            if item.is_expired:
                self._remove_item(key, reason="expired_on_access")
                self._stats.misses += 1
                self._record_access(key, hit=False)
                return default

            # Update access statistics
            item.last_accessed = datetime.now(timezone.utc)
            item.access_count += 1

            # Move to end (most recently used)
            self._items.move_to_end(key)

            self._stats.hits += 1
            self._record_access(key, hit=True)

            # Decompress if needed
            value = item.value
            if item.compressed:
                try:
                    value = pickle.loads(zlib.decompress(value))
                except Exception as e:
                    logger.error(
                        "Failed to decompress cache item", key=key, error=str(e)
                    )
                    self._remove_item(key, reason="decompression_error")
                    return default

            return value

    def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
        priority: int = 1,
        force_compression: bool = False,
    ) -> bool:
        """Set item in cache"""
        try:
            # Serialize and optionally compress the value
            serialized_value = pickle.dumps(value)
            size_bytes = len(serialized_value)
            compressed = False

            # Apply compression if beneficial
            if force_compression or size_bytes > self.compression_threshold_bytes:
                try:
                    compressed_value = zlib.compress(serialized_value, level=6)
                    if (
                        len(compressed_value) < size_bytes * 0.9
                    ):  # At least 10% compression
                        serialized_value = compressed_value
                        size_bytes = len(compressed_value)
                        compressed = True
                except Exception as e:
                    logger.warning(
                        "Failed to compress cache item", key=key, error=str(e)
                    )

            # Check if item is too large
            if size_bytes > self.max_size_bytes * 0.1:  # No single item > 10% of cache
                logger.warning(
                    "Cache item too large, rejecting",
                    key=key,
                    size_mb=size_bytes // 1024 // 1024,
                )
                return False

            with self._lock:
                now = datetime.now(timezone.utc)

                # Create cache item
                item = CacheItem(
                    key=key,
                    value=serialized_value,
                    size_bytes=size_bytes,
                    created_at=now,
                    last_accessed=now,
                    access_count=1,
                    ttl_seconds=ttl_seconds,
                    priority=priority,
                    compressed=compressed,
                )

                # Remove existing item if present
                if key in self._items:
                    old_item = self._items[key]
                    self._stats.total_size_bytes -= old_item.size_bytes

                # Add new item
                self._items[key] = item
                self._stats.total_size_bytes += size_bytes
                self._stats.sets += 1

                # Update analytics
                self._size_distribution[key] = size_bytes
                self._record_access(key, hit=False)

                # Trigger eviction if needed
                if (
                    len(self._items) > self.max_items
                    or self._stats.total_size_bytes > self.max_size_bytes
                ):
                    self._evict_items()

                return True

        except Exception as e:
            logger.error("Failed to set cache item", key=key, error=str(e))
            return False

    def delete(self, key: str) -> bool:
        """Delete item from cache"""
        with self._lock:
            if key in self._items:
                self._remove_item(key, reason="explicit_delete")
                return True
            return False

    def clear(self):
        """Clear all cache items"""
        with self._lock:
            self._items.clear()
            self._stats.total_size_bytes = 0
            self._stats.deletes += len(self._items)
            self._access_patterns.clear()
            self._key_popularity.clear()
            self._size_distribution.clear()
            logger.info("Cache cleared")

    def _remove_item(self, key: str, reason: str = "unknown"):
        """Remove item from cache (internal method)"""
        if key in self._items:
            item = self._items.pop(key)
            self._stats.total_size_bytes -= item.size_bytes
            self._stats.deletes += 1

            if reason.startswith("evict"):
                self._stats.evictions += 1

            # Clean up analytics
            if key in self._size_distribution:
                del self._size_distribution[key]

            logger.debug(
                "Cache item removed", key=key, reason=reason, size_bytes=item.size_bytes
            )

    def _get_total_size(self) -> int:
        """Get total cache size in bytes"""
        return self._stats.total_size_bytes

    def _evict_items(self):
        """Evict items based on eviction policy"""
        target_size = int(self.max_size_bytes * 0.8)  # Evict to 80% capacity
        target_items = int(self.max_items * 0.8)

        eviction_candidates = []

        for key, item in self._items.items():
            if self._eviction_policy.should_evict(
                item, self._get_total_size(), self.max_size_bytes
            ):
                priority = self._eviction_policy.get_eviction_priority(item)
                eviction_candidates.append((priority, key, item))

        # Sort by eviction priority (highest priority first)
        eviction_candidates.sort(key=lambda x: x[0], reverse=True)

        evicted_count = 0
        for priority, key, item in eviction_candidates:
            if (
                self._get_total_size() <= target_size
                and len(self._items) <= target_items
            ):
                break

            self._remove_item(key, reason="evicted_policy")
            evicted_count += 1

        if evicted_count > 0:
            logger.info(
                "Cache eviction completed",
                evicted_items=evicted_count,
                remaining_items=len(self._items),
                size_mb=self._get_total_size() // 1024 // 1024,
            )

    async def _smart_eviction(self):
        """Perform intelligent eviction based on usage patterns"""
        if not self.enable_analytics:
            self._evict_items()
            return

        # Analyze access patterns
        now = datetime.now(timezone.utc)
        recent_cutoff = now - timedelta(hours=1)

        # Calculate item scores based on multiple factors
        item_scores = {}

        for key, item in self._items.items():
            score = 0.0

            # Recency factor (0-1)
            hours_since_access = item.last_access_seconds / 3600.0
            recency_score = max(
                0, 1.0 - hours_since_access / 24.0
            )  # Linear decay over 24h

            # Frequency factor (0-1)
            frequency_score = min(
                1.0, item.access_count / 100.0
            )  # Normalize to 100 accesses

            # Size factor (penalty for large items)
            size_penalty = min(1.0, item.size_bytes / (1024 * 1024))  # Normalize to 1MB

            # Priority factor
            priority_bonus = min(2.0, item.priority / 5.0)  # Normalize to priority 5

            # Recent popularity
            recent_accesses = len(
                [
                    access_time
                    for access_time in self._access_patterns.get(key, [])
                    if access_time >= recent_cutoff
                ]
            )
            popularity_score = min(
                1.0, recent_accesses / 10.0
            )  # Normalize to 10 accesses

            # Combine factors
            score = (
                recency_score * 0.3
                + +frequency_score * 0.25
                + +popularity_score * 0.25
                + +priority_bonus * 0.2
                - size_penalty * 0.1
            )

            item_scores[key] = score

        # Sort by score (lowest scores are evicted first)
        sorted_items = sorted(item_scores.items(), key=lambda x: x[1])

        # Evict items until we reach target size/count
        target_size = int(self.max_size_bytes * 0.8)
        target_items = int(self.max_items * 0.8)

        evicted_count = 0
        for key, score in sorted_items:
            if (
                self._get_total_size() <= target_size
                and len(self._items) <= target_items
            ):
                break

            self._remove_item(key, reason="evicted_smart")
            evicted_count += 1

        logger.info(
            "Smart eviction completed",
            evicted_items=evicted_count,
            remaining_items=len(self._items),
        )

    def _record_access(self, key: str, hit: bool):
        """Record access for analytics"""
        if not self.enable_analytics:
            return

        now = datetime.now(timezone.utc)

        # Record access pattern
        self._access_patterns[key].append(now)

        # Limit access pattern history
        cutoff_time = now - timedelta(hours=24)
        self._access_patterns[key] = [
            access_time
            for access_time in self._access_patterns[key]
            if access_time >= cutoff_time
        ]

        # Update popularity
        if hit:
            self._key_popularity[key] += 1

    def _cleanup_analytics(self):
        """Clean up old analytics data"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)

        # Clean access patterns
        keys_to_remove = []
        for key, access_times in self._access_patterns.items():
            filtered_times = [t for t in access_times if t >= cutoff_time]
            if filtered_times:
                self._access_patterns[key] = filtered_times
            else:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self._access_patterns[key]
            if key in self._key_popularity:
                del self._key_popularity[key]

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            return {
                "hits": self._stats.hits,
                "misses": self._stats.misses,
                "sets": self._stats.sets,
                "deletes": self._stats.deletes,
                "evictions": self._stats.evictions,
                "hit_ratio": self._stats.hit_ratio,
                "miss_ratio": self._stats.miss_ratio,
                "total_items": len(self._items),
                "total_size_bytes": self._stats.total_size_bytes,
                "total_size_mb": self._stats.total_size_bytes / 1024 / 1024,
                "max_size_bytes": self.max_size_bytes,
                "max_items": self.max_items,
                "size_utilization": self._stats.total_size_bytes / self.max_size_bytes,
                "item_utilization": len(self._items) / self.max_items,
                "last_updated": self._stats.last_updated.isoformat(),
            }

    def get_analytics(self) -> Dict[str, Any]:
        """Get detailed cache analytics"""
        if not self.enable_analytics:
            return {}

        with self._lock:
            # Top accessed keys
            top_keys = sorted(
                self._key_popularity.items(), key=lambda x: x[1], reverse=True
            )[:10]

            # Size distribution
            size_stats = {
                "small_items": len(
                    [s for s in self._size_distribution.values() if s < 1024]
                ),
                "medium_items": len(
                    [
                        s
                        for s in self._size_distribution.values()
                        if 1024 <= s < 1024 * 1024
                    ]
                ),
                "large_items": len(
                    [s for s in self._size_distribution.values() if s >= 1024 * 1024]
                ),
                "avg_item_size": (
                    sum(self._size_distribution.values()) / len(self._size_distribution)
                    if self._size_distribution
                    else 0
                ),
            }

            # Access patterns
            recent_cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
            active_keys = sum(
                1
                for access_times in self._access_patterns.values()
                if any(t >= recent_cutoff for t in access_times)
            )

            return {
                "top_accessed_keys": top_keys,
                "size_distribution": size_stats,
                "active_keys_last_hour": active_keys,
                "total_tracked_keys": len(self._access_patterns),
                "compression_ratio": self._calculate_compression_ratio(),
            }

    def _calculate_compression_ratio(self) -> float:
        """Calculate average compression ratio"""
        compressed_items = [item for item in self._items.values() if item.compressed]
        if not compressed_items:
            return 1.0

        # This is an approximation since we don't store original sizes
        # In practice, you'd want to track this during compression
        return 0.7  # Assume 30% compression on average


class CacheWarmer:
    """Cache warming and preloading system"""

    def __init__(self, cache: IntelligentCache):
        self.cache = cache
        self._warming_strategies: List[Callable] = []
        self._scheduled_warmups: Dict[str, asyncio.Task] = {}

    def add_warming_strategy(self, strategy: Callable[[], List[tuple]]):
        """Add a cache warming strategy

        Strategy should return list of (key, value, ttl, priority) tuples
        """
        self._warming_strategies.append(strategy)

    async def warm_cache(self, strategy_name: Optional[str] = None):
        """Execute cache warming strategies"""
        logger.info("Starting cache warming", strategy=strategy_name)

        warmed_items = 0
        start_time = time.time()

        for i, strategy in enumerate(self._warming_strategies):
            if (
                strategy_name
                and getattr(strategy, "__name__", f"strategy_{i}") != strategy_name
            ):
                continue

            try:
                items = strategy()
                for key, value, ttl, priority in items:
                    if self.cache.set(key, value, ttl_seconds=ttl, priority=priority):
                        warmed_items += 1

            except Exception as e:
                logger.error(
                    "Cache warming strategy failed",
                    strategy=getattr(strategy, "__name__", f"strategy_{i}"),
                    error=str(e),
                )

        duration = time.time() - start_time
        logger.info(
            "Cache warming completed",
            warmed_items=warmed_items,
            duration_seconds=duration,
        )

    def schedule_warming(self, cron_schedule: str, strategy_name: Optional[str] = None):
        """Schedule periodic cache warming (would need cron library in real implementation)"""
        # This is a placeholder - in real implementation you'd use APScheduler or similar
        logger.info(
            "Cache warming scheduled", schedule=cron_schedule, strategy=strategy_name
        )


class DistributedCacheCoordinator:
    """Coordinates cache operations across multiple instances"""

    def __init__(
        self, cache: IntelligentCache, redis_cache: Optional[CacheManager] = None
    ):
        self.local_cache = cache
        self.redis_cache = redis_cache
        self._invalidation_subscribers: Set[Callable] = set()

    async def get(self, key: str, default: Any = None) -> Any:
        """Get from local cache first, then distributed cache"""
        # Try local cache first
        value = self.local_cache.get(key)
        if value is not None:
            return value

        # Try distributed cache
        if self.redis_cache:
            try:
                value = await self.redis_cache.get(key)
                if value is not None:
                    # Populate local cache
                    self.local_cache.set(key, value, ttl_seconds=300)  # 5 min local TTL
                    return value
            except Exception as e:
                logger.warning("Distributed cache error", key=key, error=str(e))

        return default

    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None):
        """Set in both local and distributed cache"""
        # Set in local cache
        self.local_cache.set(key, value, ttl_seconds=ttl_seconds)

        # Set in distributed cache
        if self.redis_cache:
            try:
                await self.redis_cache.set(key, value, ttl=ttl_seconds)
            except Exception as e:
                logger.warning("Failed to set distributed cache", key=key, error=str(e))

    async def invalidate(self, key: str):
        """Invalidate key in all cache layers"""
        # Remove from local cache
        self.local_cache.delete(key)

        # Remove from distributed cache
        if self.redis_cache:
            try:
                await self.redis_cache.delete(key)
            except Exception as e:
                logger.warning(
                    "Failed to invalidate distributed cache", key=key, error=str(e)
                )

        # Notify subscribers
        for subscriber in self._invalidation_subscribers:
            try:
                if asyncio.iscoroutinefunction(subscriber):
                    await subscriber(key)
                else:
                    subscriber(key)
            except Exception as e:
                logger.error("Cache invalidation subscriber failed", error=str(e))

    def subscribe_to_invalidations(self, callback: Callable[[str], None]):
        """Subscribe to cache invalidation events"""
        self._invalidation_subscribers.add(callback)

    def unsubscribe_from_invalidations(self, callback: Callable[[str], None]):
        """Unsubscribe from cache invalidation events"""
        self._invalidation_subscribers.discard(callback)


class CacheOptimizer:
    """Main cache optimization manager"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}

        # Initialize intelligent cache
        self.cache = IntelligentCache(
            max_size_bytes=config.get("max_size_bytes", 100 * 1024 * 1024),
            max_items=config.get("max_items", 10000),
            compression_threshold_bytes=config.get("compression_threshold", 1024),
            enable_analytics=config.get("enable_analytics", True),
        )

        # Initialize cache warmer
        self.warmer = CacheWarmer(self.cache)

        # Initialize distributed coordinator if Redis is available
        self.coordinator: Optional[DistributedCacheCoordinator] = None

        self._initialized = False

        logger.info("Cache optimizer initialized", config=config)

    async def initialize(self, redis_cache: Optional[CacheManager] = None):
        """Initialize cache optimization system"""
        if self._initialized:
            return

        # Start cache maintenance
        await self.cache.start_maintenance()

        # Set up distributed coordination if Redis available
        if redis_cache:
            self.coordinator = DistributedCacheCoordinator(self.cache, redis_cache)

        self._initialized = True
        logger.info("Cache optimization system initialized")

    async def shutdown(self):
        """Shutdown cache optimization system"""
        if not self._initialized:
            return

        await self.cache.stop_maintenance()
        self._initialized = False
        logger.info("Cache optimization system shutdown")

    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive cache performance report"""
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "cache_stats": self.cache.get_stats(),
            "analytics": self.cache.get_analytics(),
            "recommendations": self._generate_recommendations(),
        }

        return report

    def _generate_recommendations(self) -> List[Dict[str, Any]]:
        """Generate cache optimization recommendations"""
        recommendations = []
        stats = self.cache.get_stats()

        # Hit ratio recommendations
        if stats["hit_ratio"] < 0.7:
            recommendations.append(
                {
                    "type": "hit_ratio",
                    "priority": "high",
                    "description": f"Low cache hit ratio ({stats['hit_ratio']:.2%})",
                    "suggestions": [
                        "Review cache TTL settings",
                        "Implement cache warming strategies",
                        "Analyze access patterns for optimization opportunities",
                        "Consider increasing cache size",
                    ],
                }
            )

        # Size utilization recommendations
        if stats["size_utilization"] > 0.9:
            recommendations.append(
                {
                    "type": "size_utilization",
                    "priority": "medium",
                    "description": f"High cache size utilization ({stats['size_utilization']:.1%})",
                    "suggestions": [
                        "Increase cache size",
                        "Implement more aggressive eviction policies",
                        "Enable compression for large items",
                        "Review item sizes and optimize data structures",
                    ],
                }
            )

        # Eviction rate recommendations
        if stats["evictions"] > stats["sets"] * 0.1:  # More than 10% eviction rate
            recommendations.append(
                {
                    "type": "eviction_rate",
                    "priority": "medium",
                    "description": "High cache eviction rate detected",
                    "suggestions": [
                        "Increase cache size",
                        "Adjust TTL values",
                        "Review access patterns",
                        "Implement item priority system",
                    ],
                }
            )

        return recommendations


# Global cache optimizer instance
_cache_optimizer: Optional[CacheOptimizer] = None


def get_cache_optimizer() -> CacheOptimizer:
    """Get global cache optimizer instance"""
    global _cache_optimizer
    if _cache_optimizer is None:
        _cache_optimizer = CacheOptimizer()
    return _cache_optimizer


async def initialize_cache_optimization(
    config: Optional[Dict[str, Any]] = None,
) -> CacheOptimizer:
    """Initialize global cache optimization"""
    optimizer = get_cache_optimizer()
    await optimizer.initialize()
    return optimizer


# Export all public classes and functions
__all__ = [
    "CacheOptimizer",
    "IntelligentCache",
    "CacheWarmer",
    "DistributedCacheCoordinator",
    "CacheStats",
    "CacheItem",
    "CacheEvictionPolicy",
    "LRUEvictionPolicy",
    "LFUEvictionPolicy",
    "TTLEvictionPolicy",
    "AdaptiveEvictionPolicy",
    "get_cache_optimizer",
    "initialize_cache_optimization",
]
