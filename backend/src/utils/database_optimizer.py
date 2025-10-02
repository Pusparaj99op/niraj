#!/usr/bin/env python3
"""
Advanced Database Performance Optimization System for NIRAJ Trading Platform

This module provides comprehensive database performance optimization including
intelligent indexing, query optimization, connection pooling optimization,
and advanced caching strategies.

Features:
- Intelligent query analysis and optimization - Dynamic index recommendation and creation - Advanced connection pool management - Query result caching with intelligent invalidation - Database performance monitoring and alerting - Automatic query plan analysis - Bulk operation optimization -
Database maintenance automation

Author: NIRAJ Development Team
Version: 1.0.0
"""

import asyncio
import hashlib
import json
import time
import threading
from collections import defaultdict
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set
import pickle
import zlib

# SQLAlchemy imports
from sqlalchemy import create_engine, text, event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool, QueuePool
from sqlalchemy.orm import sessionmaker

# Internal imports
from ..utils.logger import get_structured_logger
from ..core.cache import CacheManager

logger = get_structured_logger(__name__)


@dataclass
class QueryStats:
    """Query performance statistics"""

    query_hash: str
    normalized_query: str
    execution_count: int = 0
    total_time_ms: float = 0.0
    min_time_ms: float = float("inf")
    max_time_ms: float = 0.0
    avg_time_ms: float = 0.0
    last_executed: Optional[datetime] = None
    error_count: int = 0
    result_count_stats: Dict[str, int] = field(default_factory=dict)

    def update(
        self, execution_time_ms: float, result_count: int = 0, error: bool = False
    ):
        """Update statistics with new execution"""
        self.execution_count += 1
        self.last_executed = datetime.now(timezone.utc)

        if error:
            self.error_count += 1
            return

        self.total_time_ms += execution_time_ms
        self.min_time_ms = min(self.min_time_ms, execution_time_ms)
        self.max_time_ms = max(self.max_time_ms, execution_time_ms)
        self.avg_time_ms = self.total_time_ms / (
            self.execution_count - self.error_count
        )

        # Track result count distribution
        count_bucket = self._get_count_bucket(result_count)
        self.result_count_stats[count_bucket] = (
            self.result_count_stats.get(count_bucket, 0) + 1
        )

    def _get_count_bucket(self, count: int) -> str:
        """Get bucket for result count"""
        if count == 0:
            return "0"
        elif count <= 10:
            return "1-10"
        elif count <= 100:
            return "11-100"
        elif count <= 1000:
            return "101-1000"
        else:
            return "1000+"


@dataclass
class IndexRecommendation:
    """Index recommendation"""

    table_name: str
    columns: List[str]
    index_type: str  # 'btree', 'hash', 'partial', 'composite'
    estimated_benefit: float  # 0-1 score
    reason: str
    query_patterns: List[str]
    created: bool = False

    @property
    def index_name(self) -> str:
        """Generate index name"""
        cols = "_".join(self.columns)
        return f"idx_{self.table_name}_{cols}_{self.index_type}"


class QueryNormalizer:
    """Normalize SQL queries for analysis"""

    @staticmethod
    def normalize_query(query: str) -> str:
        """Normalize query for pattern matching"""
        # Remove extra whitespace
        normalized = " ".join(query.split())

        # Convert to uppercase for consistency
        normalized = normalized.upper()

        # Replace literals with placeholders
        import re

        # Replace string literals
        normalized = re.sub(r"'[^']*'", "'?'", normalized)
        normalized = re.sub(r'"[^"]*"', '"?"', normalized)

        # Replace numeric literals
        normalized = re.sub(r"\b\d+\b", "?", normalized)

        # Replace parameter placeholders
        normalized = re.sub(r"%\([^)]+\)s", "?", normalized)
        normalized = re.sub(r"\$\d+", "?", normalized)

        # Replace IN clauses with multiple values
        normalized = re.sub(r"IN\s*\([^)]+\)", "IN (?)", normalized)

        return normalized

    @staticmethod
    def get_query_hash(query: str) -> str:
        """Get hash for normalized query"""
        normalized = QueryNormalizer.normalize_query(query)
        return hashlib.md5(normalized.encode()).hexdigest()

    @staticmethod
    def extract_tables(query: str) -> Set[str]:
        """Extract table names from query"""
        import re

        tables = set()

        # Find FROM clauses
        from_matches = re.finditer(r"\bFROM\s+(\w+)", query.upper())
        for match in from_matches:
            tables.add(match.group(1).lower())

        # Find JOIN clauses
        join_matches = re.finditer(r"\bJOIN\s+(\w+)", query.upper())
        for match in join_matches:
            tables.add(match.group(1).lower())

        # Find UPDATE/INSERT/DELETE tables
        dml_matches = re.finditer(
            r"\b(?:UPDATE|INSERT\s+INTO|DELETE\s+FROM)\s+(\w+)", query.upper()
        )
        for match in dml_matches:
            tables.add(match.group(1).lower())

        return tables

    @staticmethod
    def extract_where_columns(query: str) -> Set[str]:
        """Extract columns used in WHERE clauses"""
        import re

        columns = set()

        # Find WHERE clauses and extract column references
        where_pattern = (
            r"\bWHERE\s+(.+?)(?:\s+ORDER\s+BY|\s+GROUP\s+BY|\s+HAVING|\s+LIMIT|$)"
        )
        where_match = re.search(where_pattern, query.upper())

        if where_match:
            where_clause = where_match.group(1)

            # Extract column references (simplified pattern)
            col_pattern = r"\b([a-zA-Z_][a-zA-Z0-9_]*)\s*[=<>!]"
            for match in re.finditer(col_pattern, where_clause):
                columns.add(match.group(1).lower())

        return columns


class QueryAnalyzer:
    """Analyze queries for optimization opportunities"""

    def __init__(self):
        self.query_stats: Dict[str, QueryStats] = {}
        self._lock = threading.RLock()

    def record_query_execution(
        self,
        query: str,
        execution_time_ms: float,
        result_count: int = 0,
        error: bool = False,
    ):
        """Record query execution statistics"""
        query_hash = QueryNormalizer.get_query_hash(query)
        normalized_query = QueryNormalizer.normalize_query(query)

        with self._lock:
            if query_hash not in self.query_stats:
                self.query_stats[query_hash] = QueryStats(
                    query_hash=query_hash, normalized_query=normalized_query
                )

            self.query_stats[query_hash].update(execution_time_ms, result_count, error)

    def get_slow_queries(
        self, threshold_ms: float = 100.0, min_executions: int = 5
    ) -> List[QueryStats]:
        """Get queries that are consistently slow"""
        with self._lock:
            slow_queries = []
            for stats in self.query_stats.values():
                if (
                    stats.execution_count >= min_executions
                    and stats.avg_time_ms >= threshold_ms
                ):
                    slow_queries.append(stats)

            # Sort by average execution time
            slow_queries.sort(key=lambda x: x.avg_time_ms, reverse=True)
            return slow_queries

    def get_frequent_queries(self, min_executions: int = 100) -> List[QueryStats]:
        """Get most frequently executed queries"""
        with self._lock:
            frequent_queries = []
            for stats in self.query_stats.values():
                if stats.execution_count >= min_executions:
                    frequent_queries.append(stats)

            # Sort by execution count
            frequent_queries.sort(key=lambda x: x.execution_count, reverse=True)
            return frequent_queries

    def analyze_index_opportunities(self) -> List[IndexRecommendation]:
        """Analyze queries to recommend indexes"""
        recommendations = []

        with self._lock:
            # Group queries by table
            table_queries = defaultdict(list)

            for stats in self.query_stats.values():
                tables = QueryNormalizer.extract_tables(stats.normalized_query)
                for table in tables:
                    table_queries[table].append(stats)

            # Analyze each table's query patterns
            for table_name, queries in table_queries.items():
                recommendations.extend(self._analyze_table_indexes(table_name, queries))

        # Sort by estimated benefit
        recommendations.sort(key=lambda x: x.estimated_benefit, reverse=True)
        return recommendations

    def _analyze_table_indexes(
        self, table_name: str, queries: List[QueryStats]
    ) -> List[IndexRecommendation]:
        """Analyze index opportunities for a specific table"""
        recommendations = []

        # Track column usage patterns
        where_columns = defaultdict(int)

        total_executions = 0
        slow_query_time = 0

        for query_stats in queries:
            query = query_stats.normalized_query
            executions = query_stats.execution_count
            total_executions += executions

            if query_stats.avg_time_ms > 100:  # Consider slow
                slow_query_time += query_stats.total_time_ms

            # Extract column patterns
            where_cols = QueryNormalizer.extract_where_columns(query)
            for col in where_cols:
                where_columns[col] += executions

        # Generate recommendations based on patterns

        # 1. Single column indexes for frequently filtered columns
        for column, usage_count in where_columns.items():
            if usage_count > total_executions * 0.1:  # Used in >10% of queries
                benefit = min(1.0, usage_count / total_executions)

                recommendations.append(
                    IndexRecommendation(
                        table_name=table_name,
                        columns=[column],
                        index_type="btree",
                        estimated_benefit=benefit
                        * 0.7,  # Single column indexes have moderate benefit
                        reason=f"Column {column} frequently used in WHERE clauses",
                        query_patterns=[
                            q.normalized_query
                            for q in queries
                            if column
                            in QueryNormalizer.extract_where_columns(q.normalized_query)
                        ][:3],
                    )
                )

        # 2. Composite indexes for commonly used column combinations
        if len(where_columns) >= 2:
            # Find columns that are often used together
            column_pairs = []
            for query_stats in queries:
                cols = list(
                    QueryNormalizer.extract_where_columns(query_stats.normalized_query)
                )
                if len(cols) >= 2:
                    for i in range(len(cols)):
                        for j in range(i + 1, len(cols)):
                            pair = tuple(sorted([cols[i], cols[j]]))
                            column_pairs.append((pair, query_stats.execution_count))

            # Count pair frequency
            pair_counts = defaultdict(int)
            for pair, count in column_pairs:
                pair_counts[pair] += count

            # Recommend composite indexes for frequent pairs
            for (col1, col2), count in pair_counts.items():
                if count > total_executions * 0.05:  # Used in >5% of queries
                    benefit = min(1.0, count / total_executions)

                    recommendations.append(
                        IndexRecommendation(
                            table_name=table_name,
                            columns=[col1, col2],
                            index_type="btree",
                            estimated_benefit=benefit
                            * 0.9,  # Composite indexes can have high benefit
                            reason=f"Columns {col1}, {col2} frequently used together",
                            query_patterns=[
                                q.normalized_query
                                for q in queries
                                if col1
                                in QueryNormalizer.extract_where_columns(
                                    q.normalized_query
                                )
                                and col2
                                in QueryNormalizer.extract_where_columns(
                                    q.normalized_query
                                )
                            ][:3],
                        )
                    )

        return recommendations

    def get_query_summary(self) -> Dict[str, Any]:
        """Get summary of query analysis"""
        with self._lock:
            total_queries = len(self.query_stats)
            total_executions = sum(
                stats.execution_count for stats in self.query_stats.values()
            )
            total_time = sum(stats.total_time_ms for stats in self.query_stats.values())
            total_errors = sum(stats.error_count for stats in self.query_stats.values())

            slow_queries = self.get_slow_queries()
            frequent_queries = self.get_frequent_queries(min_executions=10)

            return {
                "total_unique_queries": total_queries,
                "total_executions": total_executions,
                "total_time_ms": total_time,
                "avg_time_ms": (
                    total_time / total_executions if total_executions > 0 else 0
                ),
                "total_errors": total_errors,
                "error_rate": (
                    total_errors / total_executions if total_executions > 0 else 0
                ),
                "slow_queries_count": len(slow_queries),
                "frequent_queries_count": len(frequent_queries),
                "top_slow_queries": [
                    {
                        "query": stats.normalized_query[:200],
                        "avg_time_ms": stats.avg_time_ms,
                        "execution_count": stats.execution_count,
                    }
                    for stats in slow_queries[:5]
                ],
                "top_frequent_queries": [
                    {
                        "query": stats.normalized_query[:200],
                        "execution_count": stats.execution_count,
                        "avg_time_ms": stats.avg_time_ms,
                    }
                    for stats in frequent_queries[:5]
                ],
            }


class OptimizedConnectionPool:
    """Optimized database connection pool"""

    def __init__(
        self,
        database_url: str,
        pool_size: int = 20,
        max_overflow: int = 10,
        pool_timeout: int = 30,
        pool_recycle: int = 3600,
        enable_monitoring: bool = True,
    ):
        self.database_url = database_url
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.pool_recycle = pool_recycle
        self.enable_monitoring = enable_monitoring

        # Connection pool statistics
        self.stats = {
            "connections_created": 0,
            "connections_closed": 0,
            "connections_checked_out": 0,
            "connections_checked_in": 0,
            "connection_errors": 0,
            "pool_timeouts": 0,
            "active_connections": 0,
            "pool_size": pool_size,
        }

        self._lock = threading.RLock()
        self._engine: Optional[Engine] = None
        self._session_factory: Optional[sessionmaker] = None

    def create_engine(self) -> Engine:
        """Create optimized database engine"""
        if self._engine is not None:
            return self._engine

        # Engine configuration for optimal performance
        engine_config = {
            "poolclass": QueuePool,
            "pool_size": self.pool_size,
            "max_overflow": self.max_overflow,
            "pool_timeout": self.pool_timeout,
            "pool_recycle": self.pool_recycle,
            "pool_pre_ping": True,  # Validate connections before use
            "echo": False,  # Set to True for SQL debugging
        }

        # SQLite-specific optimizations
        if "sqlite" in self.database_url.lower():
            engine_config.update(
                {
                    "poolclass": StaticPool,
                    "connect_args": {
                        "check_same_thread": False,
                        "timeout": 20,
                        "isolation_level": None,  # Use autocommit mode
                    },
                }
            )

        self._engine = create_engine(self.database_url, **engine_config)

        # Set up event listeners for monitoring
        if self.enable_monitoring:
            self._setup_monitoring()

        # Set up query optimization
        self._setup_query_optimization()

        logger.info(
            "Optimized database engine created",
            pool_size=self.pool_size,
            max_overflow=self.max_overflow,
        )

        return self._engine

    def _setup_monitoring(self):
        """Set up connection pool monitoring"""
        if not self._engine:
            return

        @event.listens_for(self._engine, "connect")
        def on_connect(dbapi_conn, connection_record):
            with self._lock:
                self.stats["connections_created"] += 1
                self.stats["active_connections"] += 1

            # SQLite-specific optimizations
            if "sqlite" in self.database_url.lower():
                cursor = dbapi_conn.cursor()
                # Enable WAL mode for better concurrency
                cursor.execute("PRAGMA journal_mode=WAL")
                # Optimize for performance
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.execute("PRAGMA cache_size=10000")
                cursor.execute("PRAGMA temp_store=MEMORY")
                cursor.execute("PRAGMA mmap_size=268435456")  # 256MB
                cursor.close()

        @event.listens_for(self._engine, "close")
        def on_close(dbapi_conn, connection_record):
            with self._lock:
                self.stats["connections_closed"] += 1
                self.stats["active_connections"] = max(
                    0, self.stats["active_connections"] - 1
                )

        @event.listens_for(self._engine.pool, "checkout")
        def on_checkout(dbapi_conn, connection_record, connection_proxy):
            with self._lock:
                self.stats["connections_checked_out"] += 1

        @event.listens_for(self._engine.pool, "checkin")
        def on_checkin(dbapi_conn, connection_record):
            with self._lock:
                self.stats["connections_checked_in"] += 1

    def _setup_query_optimization(self):
        """Set up query optimization and monitoring"""
        if not self._engine:
            return

        query_analyzer = QueryAnalyzer()

        @event.listens_for(self._engine, "before_cursor_execute")
        def before_cursor_execute(
            conn, cursor, statement, parameters, context, executemany
        ):
            context._query_start_time = time.time()

        @event.listens_for(self._engine, "after_cursor_execute")
        def after_cursor_execute(
            conn, cursor, statement, parameters, context, executemany
        ):
            if hasattr(context, "_query_start_time"):
                execution_time_ms = (time.time() - context._query_start_time) * 1000
                result_count = cursor.rowcount if hasattr(cursor, "rowcount") else 0

                query_analyzer.record_query_execution(
                    statement, execution_time_ms, result_count
                )

                # Log slow queries
                if execution_time_ms > 1000:  # > 1 second
                    logger.warning(
                        "Slow query detected",
                        query=statement[:200],
                        execution_time_ms=execution_time_ms,
                        result_count=result_count,
                    )

        # Store analyzer for later access
        self._query_analyzer = query_analyzer

    def get_session_factory(self) -> sessionmaker:
        """Get SQLAlchemy session factory"""
        if self._session_factory is None:
            engine = self.create_engine()
            self._session_factory = sessionmaker(bind=engine)

        return self._session_factory

    @asynccontextmanager
    async def get_async_session(self):
        """Get async database session (for compatibility)"""
        # Note: This is a sync implementation for compatibility
        # In a real async setup, you'd use asyncio-compatible pools
        session = self.get_session_factory()()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        with self._lock:
            pool_info = {}

            if self._engine and hasattr(self._engine.pool, "size"):
                pool_info.update(
                    {
                        "pool_size": self._engine.pool.size(),
                        "checked_in": self._engine.pool.checkedin(),
                        "checked_out": self._engine.pool.checkedout(),
                        "overflow": self._engine.pool.overflow(),
                        "invalidated": self._engine.pool.invalidated(),
                    }
                )

            return {
                **self.stats,
                **pool_info,
                "efficiency": self.stats["connections_checked_in"]
                / max(1, self.stats["connections_checked_out"]),
                "error_rate": self.stats["connection_errors"]
                / max(1, self.stats["connections_created"]),
            }

    def get_query_analysis(self) -> Dict[str, Any]:
        """Get query analysis results"""
        if hasattr(self, "_query_analyzer"):
            return self._query_analyzer.get_query_summary()
        return {}

    def get_index_recommendations(self) -> List[IndexRecommendation]:
        """Get index recommendations"""
        if hasattr(self, "_query_analyzer"):
            return self._query_analyzer.analyze_index_opportunities()
        return []


class QueryCache:
    """Intelligent query result caching"""

    def __init__(
        self, cache_manager: Optional[CacheManager] = None, max_memory_mb: int = 100
    ):
        self.cache_manager = cache_manager
        self.max_memory_bytes = max_memory_mb * 1024 * 1024

        # Local memory cache for frequently accessed results
        self._memory_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "evictions": 0,
            "memory_usage_bytes": 0,
        }
        self._lock = threading.RLock()

        # Cache TTL settings by query type
        self._ttl_settings = {
            "SELECT": 300,  # 5 minutes for read queries
            "COUNT": 600,  # 10 minutes for count queries
            "AGGREGATE": 900,  # 15 minutes for aggregation queries
            "DEFAULT": 180,  # 3 minutes default
        }

    def get_cache_key(self, query: str, params: Optional[Dict] = None) -> str:
        """Generate cache key for query"""
        query_hash = QueryNormalizer.get_query_hash(query)
        if params:
            params_str = json.dumps(sorted(params.items()), default=str)
            params_hash = hashlib.md5(params_str.encode()).hexdigest()
            return f"query:{query_hash}:{params_hash}"
        return f"query:{query_hash}"

    def _get_query_type(self, query: str) -> str:
        """Determine query type for TTL selection"""
        query_upper = query.strip().upper()

        if query_upper.startswith("SELECT"):
            if (
                "COUNT(" in query_upper
                or "SUM(" in query_upper
                or "AVG(" in query_upper
            ):
                return "AGGREGATE"
            elif "COUNT(*)" in query_upper:
                return "COUNT"
            return "SELECT"

        return "DEFAULT"

    async def get(self, query: str, params: Optional[Dict] = None) -> Optional[Any]:
        """Get cached query result"""
        cache_key = self.get_cache_key(query, params)

        # Try memory cache first
        with self._lock:
            if cache_key in self._memory_cache:
                cache_item = self._memory_cache[cache_key]

                # Check expiration
                if datetime.now(timezone.utc) < cache_item["expires_at"]:
                    self._cache_stats["hits"] += 1
                    cache_item["last_accessed"] = datetime.now(timezone.utc)
                    return cache_item["result"]
                else:
                    # Remove expired item
                    self._remove_from_memory_cache(cache_key)

        # Try distributed cache if available
        if self.cache_manager:
            try:
                result = await self.cache_manager.get(cache_key)
                if result is not None:
                    # Store in memory cache for faster access
                    await self._store_in_memory_cache(cache_key, result, query)
                    self._cache_stats["hits"] += 1
                    return result
            except Exception as e:
                logger.warning("Error accessing distributed cache", error=str(e))

        self._cache_stats["misses"] += 1
        return None

    async def set(
        self,
        query: str,
        result: Any,
        params: Optional[Dict] = None,
        ttl_override: Optional[int] = None,
    ):
        """Cache query result"""
        cache_key = self.get_cache_key(query, params)
        query_type = self._get_query_type(query)
        ttl = ttl_override or self._ttl_settings.get(
            query_type, self._ttl_settings["DEFAULT"]
        )

        # Store in memory cache
        await self._store_in_memory_cache(cache_key, result, query, ttl)

        # Store in distributed cache if available
        if self.cache_manager:
            try:
                await self.cache_manager.set(cache_key, result, ttl=ttl)
            except Exception as e:
                logger.warning("Error storing in distributed cache", error=str(e))

        self._cache_stats["sets"] += 1

    async def _store_in_memory_cache(
        self, cache_key: str, result: Any, query: str, ttl: int = 300
    ):
        """Store result in memory cache"""
        # Serialize and compress if large
        serialized_result = pickle.dumps(result)
        compressed = False

        if len(serialized_result) > 1024:  # Compress if > 1KB
            try:
                compressed_result = zlib.compress(serialized_result)
                if (
                    len(compressed_result) < len(serialized_result) * 0.8
                ):  # At least 20% compression
                    serialized_result = compressed_result
                    compressed = True
            except Exception:
                pass  # Use uncompressed if compression fails

        cache_item = {
            "result": result,
            "serialized_result": serialized_result,
            "compressed": compressed,
            "size_bytes": len(serialized_result),
            "created_at": datetime.now(timezone.utc),
            "last_accessed": datetime.now(timezone.utc),
            "expires_at": datetime.now(timezone.utc) + timedelta(seconds=ttl),
            "query_type": self._get_query_type(query),
        }

        with self._lock:
            # Check if we need to evict items to make space
            new_size = (
                self._cache_stats["memory_usage_bytes"] + cache_item["size_bytes"]
            )
            if new_size > self.max_memory_bytes:
                await self._evict_items(cache_item["size_bytes"])

            self._memory_cache[cache_key] = cache_item
            self._cache_stats["memory_usage_bytes"] += cache_item["size_bytes"]

    def _remove_from_memory_cache(self, cache_key: str):
        """Remove item from memory cache"""
        if cache_key in self._memory_cache:
            item = self._memory_cache.pop(cache_key)
            self._cache_stats["memory_usage_bytes"] -= item["size_bytes"]

    async def _evict_items(self, needed_bytes: int):
        """Evict items from memory cache to make space"""
        # Sort items by priority (LRU + size + query type)
        items_by_priority = []

        for cache_key, cache_item in self._memory_cache.items():
            # Calculate eviction priority
            age_hours = (
                datetime.now(timezone.utc) - cache_item["last_accessed"]
            ).total_seconds() / 3600
            size_penalty = cache_item["size_bytes"] / (1024 * 1024)  # Size in MB

            # Query type priority (lower is more important)
            type_priority = {
                "AGGREGATE": 1,  # Keep aggregations longer
                "COUNT": 2,
                "SELECT": 3,
                "DEFAULT": 4,
            }.get(cache_item["query_type"], 4)

            priority = age_hours + size_penalty + type_priority
            items_by_priority.append((priority, cache_key, cache_item))

        # Sort by priority (higher priority = evict first)
        items_by_priority.sort(key=lambda x: x[0], reverse=True)

        # Evict items until we have enough space
        freed_bytes = 0
        for priority, cache_key, cache_item in items_by_priority:
            self._remove_from_memory_cache(cache_key)
            freed_bytes += cache_item["size_bytes"]
            self._cache_stats["evictions"] += 1

            if freed_bytes >= needed_bytes:
                break

        logger.debug(
            "Cache eviction completed",
            freed_bytes=freed_bytes,
            evicted_items=len(
                [x for x in items_by_priority if x[1] not in self._memory_cache]
            ),
        )

    async def invalidate_pattern(self, pattern: str):
        """Invalidate cache entries matching pattern"""
        keys_to_remove = []

        with self._lock:
            for cache_key in self._memory_cache.keys():
                if pattern in cache_key:
                    keys_to_remove.append(cache_key)

        for cache_key in keys_to_remove:
            self._remove_from_memory_cache(cache_key)

        # Also invalidate in distributed cache if available
        if self.cache_manager:
            try:
                # This would need implementation in cache manager
                # await self.cache_manager.invalidate_pattern(pattern)
                pass
            except Exception as e:
                logger.warning(
                    "Error invalidating distributed cache pattern", error=str(e)
                )

        logger.info(
            "Cache invalidation completed",
            pattern=pattern,
            invalidated_keys=len(keys_to_remove),
        )

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            hit_ratio = self._cache_stats["hits"] / max(
                1, self._cache_stats["hits"] + self._cache_stats["misses"]
            )

            return {
                **self._cache_stats,
                "hit_ratio": hit_ratio,
                "items_count": len(self._memory_cache),
                "memory_usage_mb": self._cache_stats["memory_usage_bytes"]
                / 1024
                / 1024,
                "memory_utilization": self._cache_stats["memory_usage_bytes"]
                / self.max_memory_bytes,
            }


class DatabaseOptimizer:
    """Main database optimization coordinator"""

    def __init__(
        self,
        database_url: str,
        cache_manager: Optional[CacheManager] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        self.database_url = database_url
        self.cache_manager = cache_manager
        self.config = config or {}

        # Initialize components
        self.connection_pool = OptimizedConnectionPool(
            database_url=database_url,
            pool_size=self.config.get("pool_size", 20),
            max_overflow=self.config.get("max_overflow", 10),
            pool_timeout=self.config.get("pool_timeout", 30),
            pool_recycle=self.config.get("pool_recycle", 3600),
            enable_monitoring=self.config.get("enable_monitoring", True),
        )

        self.query_cache = QueryCache(
            cache_manager=cache_manager,
            max_memory_mb=self.config.get("cache_memory_mb", 100),
        )

        self._initialized = False
        self._maintenance_task: Optional[asyncio.Task] = None

        logger.info(
            "Database optimizer initialized", database_url=database_url[:50] + "..."
        )

    async def initialize(self):
        """Initialize database optimizer"""
        if self._initialized:
            return

        # Create database engine
        self.connection_pool.create_engine()

        # Start maintenance tasks
        if self.config.get("enable_maintenance", True):
            self._maintenance_task = asyncio.create_task(
                self._maintenance_loop(
                    self.config.get("maintenance_interval", 1800)
                )  # 30 minutes
            )

        self._initialized = True
        logger.info("Database optimizer initialized")

    async def shutdown(self):
        """Shutdown database optimizer"""
        if not self._initialized:
            return

        if self._maintenance_task:
            self._maintenance_task.cancel()
            try:
                await self._maintenance_task
            except asyncio.CancelledError:
                pass

        self._initialized = False
        logger.info("Database optimizer shutdown completed")

    async def _maintenance_loop(self, interval: float):
        """Background maintenance loop"""
        while True:
            try:
                await asyncio.sleep(interval)
                await self._perform_maintenance()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Database maintenance error", error=str(e))

    async def _perform_maintenance(self):
        """Perform database maintenance tasks"""
        logger.info("Starting database maintenance")

        try:
            # Analyze and apply index recommendations
            await self._apply_index_recommendations()

            # Clean up query cache
            await self._cleanup_query_cache()

            # Update statistics
            await self._update_database_statistics()

            logger.info("Database maintenance completed")

        except Exception as e:
            logger.error("Database maintenance failed", error=str(e))

    async def _apply_index_recommendations(self):
        """Apply index recommendations automatically"""
        recommendations = self.connection_pool.get_index_recommendations()

        # Only apply high-benefit recommendations automatically
        auto_apply_threshold = self.config.get("auto_index_threshold", 0.8)

        applied_count = 0
        for rec in recommendations:
            if rec.estimated_benefit >= auto_apply_threshold and not rec.created:
                try:
                    await self._create_index(rec)
                    rec.created = True
                    applied_count += 1
                except Exception as e:
                    logger.error(
                        "Failed to create index",
                        index_name=rec.index_name,
                        error=str(e),
                    )

        if applied_count > 0:
            logger.info(
                "Automatic index creation completed", created_indexes=applied_count
            )

    async def _create_index(self, recommendation: IndexRecommendation):
        """Create database index"""
        engine = self.connection_pool.create_engine()

        # Generate index creation SQL
        columns_str = ", ".join(recommendation.columns)

        if recommendation.index_type == "btree":
            sql = f"CREATE INDEX IF NOT EXISTS {recommendation.index_name} ON {recommendation.table_name} ({columns_str})"
        elif recommendation.index_type == "hash":
            # SQLite doesn't support hash indexes, use btree
            sql = f"CREATE INDEX IF NOT EXISTS {recommendation.index_name} ON {recommendation.table_name} ({columns_str})"
        else:
            sql = f"CREATE INDEX IF NOT EXISTS {recommendation.index_name} ON {recommendation.table_name} ({columns_str})"

        with engine.connect() as conn:
            conn.execute(text(sql))
            conn.commit()

        logger.info(
            "Index created",
            index_name=recommendation.index_name,
            table=recommendation.table_name,
            columns=recommendation.columns,
        )

    async def _cleanup_query_cache(self):
        """Clean up expired cache entries"""
        # Query cache has its own cleanup, just trigger stats update
        stats = self.query_cache.get_cache_stats()
        logger.debug("Query cache stats", **stats)

    async def _update_database_statistics(self):
        """Update database statistics for query optimization"""
        engine = self.connection_pool.create_engine()

        try:
            if "sqlite" in self.database_url.lower():
                with engine.connect() as conn:
                    # SQLite: Analyze all tables
                    conn.execute(text("ANALYZE"))
                    conn.commit()

            logger.debug("Database statistics updated")

        except Exception as e:
            logger.error("Failed to update database statistics", error=str(e))

    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive database performance report"""
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "connection_pool": self.connection_pool.get_pool_stats(),
            "query_analysis": self.connection_pool.get_query_analysis(),
            "query_cache": self.query_cache.get_cache_stats(),
            "index_recommendations": [
                {
                    "table": rec.table_name,
                    "columns": rec.columns,
                    "type": rec.index_type,
                    "benefit": rec.estimated_benefit,
                    "reason": rec.reason,
                    "created": rec.created,
                }
                for rec in self.connection_pool.get_index_recommendations()[:10]
            ],
            "optimization_summary": self._generate_optimization_summary(),
        }

    def _generate_optimization_summary(self) -> Dict[str, Any]:
        """Generate optimization recommendations summary"""
        pool_stats = self.connection_pool.get_pool_stats()
        query_analysis = self.connection_pool.get_query_analysis()
        cache_stats = self.query_cache.get_cache_stats()

        recommendations = []

        # Pool optimization recommendations
        if pool_stats.get("efficiency", 1.0) < 0.8:
            recommendations.append(
                {
                    "type": "connection_pool",
                    "priority": "medium",
                    "description": "Low connection pool efficiency",
                    "suggestion": "Consider adjusting pool size or connection timeout settings",
                }
            )

        # Query optimization recommendations
        slow_queries_count = query_analysis.get("slow_queries_count", 0)
        if slow_queries_count > 0:
            recommendations.append(
                {
                    "type": "query_performance",
                    "priority": "high",
                    "description": f"{slow_queries_count} slow queries detected",
                    "suggestion": "Review and optimize slow queries, consider adding indexes",
                }
            )

        # Cache optimization recommendations
        if cache_stats.get("hit_ratio", 0) < 0.6:
            recommendations.append(
                {
                    "type": "query_cache",
                    "priority": "medium",
                    "description": f'Low cache hit ratio: {cache_stats.get("hit_ratio", 0):.2%}',
                    "suggestion": "Review cache TTL settings and query patterns",
                }
            )

        return {
            "total_recommendations": len(recommendations),
            "high_priority": len(
                [r for r in recommendations if r["priority"] == "high"]
            ),
            "recommendations": recommendations,
        }


# Global database optimizer instance
_database_optimizer: Optional[DatabaseOptimizer] = None


def get_database_optimizer() -> DatabaseOptimizer:
    """Get global database optimizer instance"""
    global _database_optimizer
    if _database_optimizer is None:
        raise RuntimeError(
            "Database optimizer not initialized. Call initialize_database_optimization first."
        )
    return _database_optimizer


async def initialize_database_optimization(
    database_url: str,
    cache_manager: Optional[CacheManager] = None,
    config: Optional[Dict[str, Any]] = None,
) -> DatabaseOptimizer:
    """Initialize global database optimization"""
    global _database_optimizer
    _database_optimizer = DatabaseOptimizer(database_url, cache_manager, config)
    await _database_optimizer.initialize()
    return _database_optimizer


# Export all public classes and functions
__all__ = [
    "DatabaseOptimizer",
    "OptimizedConnectionPool",
    "QueryCache",
    "QueryAnalyzer",
    "QueryNormalizer",
    "QueryStats",
    "IndexRecommendation",
    "get_database_optimizer",
    "initialize_database_optimization",
]
