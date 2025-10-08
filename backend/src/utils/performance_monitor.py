#!/usr/bin/env python3
"""
Advanced Performance Monitoring System for NIRAJ Trading Platform

This module provides comprehensive performance monitoring, profiling, and optimization
capabilities for the NIRAJ algorithmic trading system.

Features:
- Real-time performance metrics collection - Advanced profiling and analysis tools - Performance alerting and notification system - Automatic performance optimization recommendations - Resource utilization monitoring - Database query performance tracking - API endpoint response time monitoring - Memory usage analysis and optimization - CPU utilization monitoring - WebSocket connection performance tracking -
AI inference performance monitoring

Author: NIRAJ Development Team
Version: 1.0.0
"""

import asyncio
import gc
import os
import threading
import time
import tracemalloc
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from math import isfinite
from typing import (
    Any,
    Awaitable,
    Callable,
    Deque,
    Dict,
    List,
    Optional,
    TypedDict,
    TypeVar,
    cast,
)

# Third-party imports
import psutil
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import Pool

# Internal imports
from ..core.cache import CacheManager
from ..utils.logger import get_structured_logger

logger = get_structured_logger(__name__)

# Type definitions
F = TypeVar("F", bound=Callable[..., Any])
AF = TypeVar("AF", bound=Callable[..., Awaitable[Any]])


# Performance thresholds and constants
PERFORMANCE_THRESHOLDS = {
    "api_response_time": {"warning": 500, "critical": 1000},  # ms  # ms
    "database_query_time": {"warning": 100, "critical": 500},  # ms  # ms
    "memory_usage": {"warning": 80, "critical": 95},  # percentage  # percentage
    "cpu_usage": {"warning": 70, "critical": 90},  # percentage  # percentage
    "websocket_latency": {"warning": 50, "critical": 100},  # ms  # ms
    "ai_inference_time": {"warning": 2000, "critical": 5000},  # ms  # ms
}

METRICS_RETENTION_PERIOD = timedelta(hours=24)
ALERT_COOLDOWN_PERIOD = timedelta(minutes=5)


class MetricType:
    """Metric type constants"""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class PerformanceMetric:
    """Individual performance metric data structure"""

    name: str
    value: float
    metric_type: str
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceAlert:
    """Performance alert data structure"""

    metric_name: str
    threshold_type: str  # 'warning' or 'critical'
    current_value: float
    threshold_value: float
    timestamp: datetime
    description: str
    suggested_actions: List[str] = field(default_factory=list)


class QueryStatistics(TypedDict):
    count: int
    avg_time_ms: float
    min_time_ms: float
    max_time_ms: float
    total_time_ms: float
    last_executed: Optional[str]


class EndpointStatistics(TypedDict):
    request_count: int
    error_count: int
    error_rate: float
    avg_time_ms: float
    min_time_ms: float
    max_time_ms: float
    total_time_ms: float


class TrainingData(TypedDict):
    timestamp: datetime
    value: float
    hour: int
    day_of_week: int
    month: int


class PredictionModel(TypedDict):
    model: Any
    scaler: Any
    last_trained: datetime
    accuracy_score: float


class Prediction(TypedDict):
    metric_name: str
    predicted_value: float
    confidence_interval: float
    prediction_time: datetime
    model_accuracy: float
    hours_ahead: int


class PredictionData(TypedDict):
    timestamp: datetime
    prediction: Prediction
    actual_value: Optional[float]


class Anomaly(TypedDict):
    metric_name: str
    current_value: float
    expected_range: Dict[str, float]
    z_score: float
    severity: str
    timestamp: datetime
    description: str


class PerformanceTracker:
    """Thread-safe performance metrics tracker"""

    def __init__(self, max_samples: int = 10000):
        self.max_samples = max_samples
        # Deque is bounded by max_samples; each entry is a PerformanceMetric
        self._metrics: Dict[str, Deque[PerformanceMetric]] = defaultdict(
            lambda: deque(maxlen=max_samples)
        )
        self._lock = threading.RLock()
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = defaultdict(float)
        self._histograms: Dict[str, List[float]] = defaultdict(list)

    def add_metric(self, metric: PerformanceMetric):
        """Add a performance metric"""
        # Input validation
        if not metric.name:
            logger.error("Invalid metric name", name=metric.name)
            return

        if not isfinite(metric.value):
            logger.error("Invalid metric value", name=metric.name, value=metric.value)
            return

        if metric.metric_type not in [
            MetricType.COUNTER,
            MetricType.GAUGE,
            MetricType.HISTOGRAM,
            MetricType.TIMER,
        ]:
            logger.error(
                "Invalid metric type",
                name=metric.name,
                metric_type=metric.metric_type,
            )
            return

        try:
            with self._lock:
                self._metrics[metric.name].append(metric)

                # Update type-specific storage
                if metric.metric_type == MetricType.COUNTER:
                    self._counters[metric.name] += metric.value
                elif metric.metric_type == MetricType.GAUGE:
                    self._gauges[metric.name] = metric.value
                elif metric.metric_type == MetricType.HISTOGRAM:
                    self._histograms[metric.name].append(metric.value)
                    # Keep only recent samples for histograms
                    if len(self._histograms[metric.name]) > 1000:
                        self._histograms[metric.name] = self._histograms[metric.name][-1000:]

        except Exception as e:
            logger.error("Failed to add metric", name=metric.name, error=str(e))

    def get_metrics(self, metric_name: str, limit: Optional[int] = None) -> List[PerformanceMetric]:
        """Get metrics by name"""
        with self._lock:
            metrics = list(self._metrics[metric_name])
            if limit:
                metrics = metrics[-limit:]
            return metrics

    def get_recent_metrics(self, time_window: timedelta) -> Dict[str, List[PerformanceMetric]]:
        """Get metrics within time window"""
        cutoff_time = datetime.now(timezone.utc) - time_window
        result: Dict[str, List[PerformanceMetric]] = {}

        with self._lock:
            for name, metrics in self._metrics.items():
                recent_metrics = [m for m in metrics if m.timestamp >= cutoff_time]
                if recent_metrics:
                    result[name] = recent_metrics

        return result

    def get_statistics(self, metric_name: str) -> Dict[str, float]:
        """Get statistical summary of metrics"""
        with self._lock:
            metrics = list(self._metrics[metric_name])
            if not metrics:
                return {}

            values = [m.value for m in metrics]
            values.sort()

            n = len(values)
            return {
                "count": float(n),
                "min": values[0],
                "max": values[-1],
                "mean": sum(values) / n,
                "median": values[n // 2],
                "p95": values[int(n * 0.95)] if n > 20 else values[-1],
                "p99": values[int(n * 0.99)] if n > 100 else values[-1],
            }

    def cleanup_old_metrics(self):
        """Remove old metrics beyond retention period"""
        cutoff_time = datetime.now(timezone.utc) - METRICS_RETENTION_PERIOD

        with self._lock:
            for name in list(self._metrics.keys()):
                # Filter out old metrics
                self._metrics[name] = deque(
                    (m for m in self._metrics[name] if m.timestamp >= cutoff_time),
                    maxlen=self.max_samples,
                )

                # Remove empty metric collections
                if not self._metrics[name]:
                    del self._metrics[name]

    def get_all_metrics(self) -> Dict[str, List[PerformanceMetric]]:
        """Get all metrics (public method for external access)"""
        with self._lock:
            return {name: list(metrics) for name, metrics in self._metrics.items()}


class ResourceMonitor:
    """System resource monitoring"""

    def __init__(self, tracker: PerformanceTracker):
        self.tracker = tracker
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task[None]] = None

    async def start_monitoring(self, interval: float = 30.0):
        """Start continuous resource monitoring"""
        if self._monitoring:
            return

        self._monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_loop(interval))
        logger.info("Resource monitoring started", interval=interval)

    async def stop_monitoring(self):
        """Stop resource monitoring"""
        self._monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Resource monitoring stopped")

    async def _monitor_loop(self, interval: float):
        """Main monitoring loop"""
        while self._monitoring:
            try:
                await self._collect_system_metrics()
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in resource monitoring", error=str(e))
                await asyncio.sleep(interval)

    async def _collect_system_metrics(self):
        """Collect system resource metrics"""
        timestamp = datetime.now(timezone.utc)

        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            load_avg = os.getloadavg() if hasattr(os, "getloadavg") else (0, 0, 0)

            # Validate CPU metrics
            if cpu_percent < 0 or cpu_percent > 100:
                logger.warning("Invalid CPU percentage", value=cpu_percent)
                cpu_percent = 0.0

            self.tracker.add_metric(
                PerformanceMetric(
                    name="system.cpu.usage_percent",
                    value=cpu_percent,
                    metric_type=MetricType.GAUGE,
                    timestamp=timestamp,
                    labels={"resource": "cpu"},
                )
            )

            if cpu_count is not None and cpu_count > 0:
                self.tracker.add_metric(
                    PerformanceMetric(
                        name="system.cpu.count",
                        value=cpu_count,
                        metric_type=MetricType.GAUGE,
                        timestamp=timestamp,
                        labels={"resource": "cpu"},
                    )
                )

            self.tracker.add_metric(
                PerformanceMetric(
                    name="system.cpu.load_avg_1min",
                    value=load_avg[0],
                    metric_type=MetricType.GAUGE,
                    timestamp=timestamp,
                    labels={"resource": "cpu", "period": "1min"},
                )
            )

            # Memory metrics
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()

            # Validate memory metrics
            if memory.percent < 0 or memory.percent > 100:
                logger.warning("Invalid memory percentage", value=memory.percent)
                memory = memory._replace(percent=0.0)

            self.tracker.add_metric(
                PerformanceMetric(
                    name="system.memory.usage_percent",
                    value=memory.percent,
                    metric_type=MetricType.GAUGE,
                    timestamp=timestamp,
                    labels={"resource": "memory", "type": "virtual"},
                )
            )

            self.tracker.add_metric(
                PerformanceMetric(
                    name="system.memory.available_bytes",
                    value=memory.available,
                    metric_type=MetricType.GAUGE,
                    timestamp=timestamp,
                    labels={"resource": "memory", "type": "virtual"},
                )
            )

            if swap.percent >= 0 and swap.percent <= 100:
                self.tracker.add_metric(
                    PerformanceMetric(
                        name="system.memory.swap.usage_percent",
                        value=swap.percent,
                        metric_type=MetricType.GAUGE,
                        timestamp=timestamp,
                        labels={"resource": "memory", "type": "swap"},
                    )
                )

            # Disk metrics
            try:
                disk = psutil.disk_usage("/")
                disk_io = psutil.disk_io_counters()

                disk_usage_percent = (disk.used / disk.total) * 100
                if disk_usage_percent >= 0 and disk_usage_percent <= 100:
                    self.tracker.add_metric(
                        PerformanceMetric(
                            name="system.disk.usage_percent",
                            value=disk_usage_percent,
                            metric_type=MetricType.GAUGE,
                            timestamp=timestamp,
                            labels={"resource": "disk", "mount": "/"},
                        )
                    )

                if disk_io:
                    self.tracker.add_metric(
                        PerformanceMetric(
                            name="system.disk.read_bytes_per_sec",
                            value=disk_io.read_bytes,
                            metric_type=MetricType.COUNTER,
                            timestamp=timestamp,
                            labels={"resource": "disk", "operation": "read"},
                        )
                    )
            except (OSError, PermissionError) as e:
                logger.warning("Failed to collect disk metrics", error=str(e))

            # Network metrics
            try:
                network = psutil.net_io_counters()
                if network:
                    self.tracker.add_metric(
                        PerformanceMetric(
                            name="system.network.bytes_sent",
                            value=network.bytes_sent,
                            metric_type=MetricType.COUNTER,
                            timestamp=timestamp,
                            labels={"resource": "network", "direction": "out"},
                        )
                    )

                    self.tracker.add_metric(
                        PerformanceMetric(
                            name="system.network.bytes_recv",
                            value=network.bytes_recv,
                            metric_type=MetricType.COUNTER,
                            timestamp=timestamp,
                            labels={"resource": "network", "direction": "in"},
                        )
                    )
            except (OSError, PermissionError) as e:
                logger.warning("Failed to collect network metrics", error=str(e))

            # Process-specific metrics
            try:
                process = psutil.Process()

                rss_memory = process.memory_info().rss
                if rss_memory >= 0:
                    self.tracker.add_metric(
                        PerformanceMetric(
                            name="process.memory.rss_bytes",
                            value=rss_memory,
                            metric_type=MetricType.GAUGE,
                            timestamp=timestamp,
                            labels={"resource": "process", "type": "memory"},
                        )
                    )

                cpu_usage = process.cpu_percent()
                if cpu_usage >= 0 and cpu_usage <= 100:
                    self.tracker.add_metric(
                        PerformanceMetric(
                            name="process.cpu.usage_percent",
                            value=cpu_usage,
                            metric_type=MetricType.GAUGE,
                            timestamp=timestamp,
                            labels={"resource": "process", "type": "cpu"},
                        )
                    )
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                logger.warning("Failed to collect process metrics", error=str(e))

            # Python-specific metrics
            try:
                gc_stats = gc.get_stats()
                for i, stat in enumerate(gc_stats):
                    collections = stat.get("collections", 0)
                    if collections >= 0:
                        self.tracker.add_metric(
                            PerformanceMetric(
                                name=f"python.gc.collections_gen{i}",
                                value=collections,
                                metric_type=MetricType.COUNTER,
                                timestamp=timestamp,
                                labels={
                                    "resource": "python",
                                    "type": "gc",
                                    "generation": str(i),
                                },
                            )
                        )
            except Exception as e:
                logger.warning("Failed to collect Python GC metrics", error=str(e))

        except Exception as e:
            logger.error("Failed to collect system metrics", error=str(e), exc_info=True)


class DatabasePerformanceMonitor:
    """Database performance monitoring"""

    def __init__(self, tracker: PerformanceTracker):
        self.tracker = tracker
        self._query_stats: Dict[str, QueryPerformanceStats] = defaultdict(
            lambda: cast(QueryPerformanceStats, {
                "count": 0,
                "total_time": 0.0,
                "min_time": float("inf"),
                "max_time": 0.0,
                "last_executed": None,
            })
        )
        self._lock = threading.RLock()

    def setup_sqlalchemy_monitoring(self, engine: Engine):
        """Set up SQLAlchemy event monitoring"""

        @event.listens_for(engine, "before_cursor_execute")
        def before_cursor_execute(  # pyright: ignore[reportUnusedFunction]
            conn: Any, cursor: Any, statement: Any, parameters: Any, context: Any, executemany: Any
        ):
            context._query_start_time = time.time()

        @event.listens_for(engine, "after_cursor_execute")
        def after_cursor_execute(  # pyright: ignore[reportUnusedFunction]
            conn: Any, cursor: Any, statement: Any, parameters: Any, context: Any, executemany: Any
        ):
            if hasattr(context, "_query_start_time"):
                duration = (
                    time.time() - context._query_start_time
                ) * 1000  # Convert to ms
                self._record_query_performance(statement, duration)

        @event.listens_for(Pool, "connect")
        def on_connect(dbapi_conn: Any, connection_record: Any):  # pyright: ignore[reportUnusedFunction]
            self.tracker.add_metric(
                PerformanceMetric(
                    name="database.connections.created",
                    value=1,
                    metric_type=MetricType.COUNTER,
                    timestamp=datetime.now(timezone.utc),
                    labels={"database": "main"},
                )
            )

        @event.listens_for(Pool, "checkout")
        def on_checkout(dbapi_conn: Any, connection_record: Any, connection_proxy: Any):  # pyright: ignore[reportUnusedFunction]
            self.tracker.add_metric(
                PerformanceMetric(
                    name="database.connections.checked_out",
                    value=1,
                    metric_type=MetricType.COUNTER,
                    timestamp=datetime.now(timezone.utc),
                    labels={"database": "main"},
                )
            )

        logger.info("SQLAlchemy performance monitoring enabled")

    def _record_query_performance(self, statement: str, duration_ms: float):
        """Record individual query performance"""
        # Input validation
        if not statement.strip():
            logger.warning("Invalid statement provided for query performance recording")
            return

        if duration_ms < 0 or not isfinite(duration_ms):
            logger.warning(
                "Invalid duration provided for query performance recording",
                duration=duration_ms,
            )
            return

        try:
            # Normalize statement for grouping
            normalized_stmt = self._normalize_statement(statement)

            with self._lock:
                stats = self._query_stats[normalized_stmt]
                stats["count"] += 1
                stats["total_time"] += duration_ms
                stats["min_time"] = min(stats["min_time"], duration_ms)
                stats["max_time"] = max(stats["max_time"], duration_ms)
                stats["last_executed"] = datetime.now(timezone.utc)

            # Record metric
            self.tracker.add_metric(
                PerformanceMetric(
                    name="database.query.duration_ms",
                    value=duration_ms,
                    metric_type=MetricType.HISTOGRAM,
                    timestamp=datetime.now(timezone.utc),
                    labels={
                        "database": "main",
                        "query_type": self._get_query_type(statement),
                    },
                    metadata={"statement": normalized_stmt[:200]},  # Truncate for storage
                )
            )

            # Check for slow queries
            if duration_ms > PERFORMANCE_THRESHOLDS["database_query_time"]["warning"]:
                logger.warning(
                    "Slow database query detected",
                    duration_ms=duration_ms,
                    statement=normalized_stmt[:200],
                )

        except Exception as e:
            logger.error("Failed to record query performance", error=str(e), statement=statement[:100])

    def _normalize_statement(self, statement: str) -> str:
        """Normalize SQL statement for grouping"""
        # Remove extra whitespace and normalize
        normalized = " ".join(statement.split())

        # Replace parameter placeholders with generic placeholder
        import re

        normalized = re.sub(r"%\([^)]+\)s", "?", normalized)  # Named parameters
        normalized = re.sub(r"\?", "?", normalized)  # Positional parameters
        normalized = re.sub(r"\d+", "N", normalized)  # Numbers
        normalized = re.sub(r"'[^']*'", "'...'", normalized)  # String literals

        return normalized[:500]  # Limit length

    def _get_query_type(self, statement: str) -> str:
        """Extract query type from statement"""
        statement = statement.strip().upper()
        if statement.startswith("SELECT"):
            return "SELECT"
        elif statement.startswith("INSERT"):
            return "INSERT"
        elif statement.startswith("UPDATE"):
            return "UPDATE"
        elif statement.startswith("DELETE"):
            return "DELETE"
        elif statement.startswith("CREATE"):
            return "CREATE"
        elif statement.startswith("DROP"):
            return "DROP"
        elif statement.startswith("ALTER"):
            return "ALTER"
        else:
            return "OTHER"

    def get_query_statistics(self) -> Dict[str, QueryStatistics]:
        """Get query performance statistics"""
        with self._lock:
            stats: Dict[str, QueryStatistics] = {}
            for statement, data in self._query_stats.items():
                if data["count"] > 0:
                    stats[statement] = {
                        "count": data["count"],
                        "avg_time_ms": data["total_time"] / data["count"],
                        "min_time_ms": data["min_time"],
                        "max_time_ms": data["max_time"],
                        "total_time_ms": data["total_time"],
                        "last_executed": (
                            data["last_executed"].isoformat()
                            if data["last_executed"]
                            else None
                        ),
                    }
            return stats


class APIPerformanceMonitor:
    """API endpoint performance monitoring"""

    def __init__(self, tracker: PerformanceTracker):
        self.tracker = tracker
        self._endpoint_stats: Dict[str, EndpointStats] = defaultdict(
            lambda: cast(EndpointStats, {
                "request_count": 0,
                "error_count": 0,
                "total_time": 0.0,
                "min_time": float("inf"),
                "max_time": 0.0,
            })
        )
        self._lock = threading.RLock()

    def record_request(
        self,
        endpoint: str,
        method: str,
        duration_ms: float,
        status_code: int,
        user_id: Optional[str] = None,
    ):
        """Record API request performance"""
        # Input validation
        if not endpoint:
            logger.warning("Invalid endpoint provided", endpoint=endpoint)
            endpoint = "/unknown"

        if not method:
            logger.warning("Invalid method provided", method=method)
            method = "UNKNOWN"

        if duration_ms < 0:
            logger.warning("Invalid duration provided", duration_ms=duration_ms)
            duration_ms = 0.0

        if status_code < 100 or status_code > 599:
            logger.warning("Invalid status code provided", status_code=status_code)
            status_code = 500

        endpoint_key = f"{method} {endpoint}"
        timestamp = datetime.now(timezone.utc)

        with self._lock:
            stats = self._endpoint_stats[endpoint_key]
            stats["request_count"] += 1
            stats["total_time"] += duration_ms
            stats["min_time"] = min(stats["min_time"], duration_ms)
            stats["max_time"] = max(stats["max_time"], duration_ms)

            if status_code >= 400:
                stats["error_count"] += 1

        # Record detailed metric
        try:
            self.tracker.add_metric(
                PerformanceMetric(
                    name="api.request.duration_ms",
                    value=duration_ms,
                    metric_type=MetricType.HISTOGRAM,
                    timestamp=timestamp,
                    labels={
                        "endpoint": endpoint,
                        "method": method,
                        "status_code": str(status_code),
                        "status_class": f"{status_code // 100}xx",
                    },
                    metadata={"user_id": user_id, "timestamp": timestamp.isoformat()},
                )
            )
        except Exception as e:
            logger.error("Failed to record API duration metric", error=str(e))

        # Record request count
        try:
            self.tracker.add_metric(
                PerformanceMetric(
                    name="api.requests.total",
                    value=1,
                    metric_type=MetricType.COUNTER,
                    timestamp=timestamp,
                    labels={
                        "endpoint": endpoint,
                        "method": method,
                        "status_code": str(status_code),
                    },
                )
            )
        except Exception as e:
            logger.error("Failed to record API request count metric", error=str(e))

        # Check for slow requests
        if duration_ms > PERFORMANCE_THRESHOLDS["api_response_time"]["warning"]:
            logger.warning(
                "Slow API request detected",
                endpoint=endpoint,
                method=method,
                duration_ms=duration_ms,
                status_code=status_code,
            )

    def get_endpoint_statistics(self) -> Dict[str, EndpointStatistics]:
        """Get API endpoint statistics"""
        with self._lock:
            stats: Dict[str, EndpointStatistics] = {}
            for endpoint, data in self._endpoint_stats.items():
                if data["request_count"] > 0:
                    stats[endpoint] = {
                        "request_count": data["request_count"],
                        "error_count": data["error_count"],
                        "error_rate": data["error_count"] / data["request_count"],
                        "avg_time_ms": data["total_time"] / data["request_count"],
                        "min_time_ms": data["min_time"],
                        "max_time_ms": data["max_time"],
                        "total_time_ms": data["total_time"],
                    }
            return stats


class MemoryProfiler:
    """Memory usage profiling and optimization"""

    def __init__(self, tracker: PerformanceTracker):
        self.tracker = tracker
        self._profiling = False
        self._snapshots: List[Any] = []

    def start_profiling(self):
        """Start memory profiling"""
        if not self._profiling:
            tracemalloc.start()
            self._profiling = True
            logger.info("Memory profiling started")

    def stop_profiling(self):
        """Stop memory profiling"""
        if self._profiling:
            tracemalloc.stop()
            self._profiling = False
            logger.info("Memory profiling stopped")

    def take_snapshot(self, name: Optional[str] = None) -> Optional[Any]:
        """Take memory snapshot"""
        if not self._profiling:
            logger.warning("Memory profiling not active, cannot take snapshot")
            return None

        if name is None:
            name = f"snapshot_{len(self._snapshots)}"

        try:
            snapshot = tracemalloc.take_snapshot()
            self._snapshots.append((name, snapshot))

            # Get current memory usage
            current, peak = tracemalloc.get_traced_memory()

            # Validate memory values
            if current < 0 or peak < 0:
                logger.warning("Invalid memory values from tracemalloc", current=current, peak=peak)
                return snapshot

            self.tracker.add_metric(
                PerformanceMetric(
                    name="memory.traced.current_bytes",
                    value=current,
                    metric_type=MetricType.GAUGE,
                    timestamp=datetime.now(timezone.utc),
                    labels={"type": "traced"},
                    metadata={"snapshot": name},
                )
            )

            self.tracker.add_metric(
                PerformanceMetric(
                    name="memory.traced.peak_bytes",
                    value=peak,
                    metric_type=MetricType.GAUGE,
                    timestamp=datetime.now(timezone.utc),
                    labels={"type": "traced"},
                    metadata={"snapshot": name},
                )
            )

            return snapshot

        except Exception as e:
            logger.error("Failed to take memory snapshot", error=str(e))
            return None

    def analyze_top_allocations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Analyze top memory allocations"""
        if not self._snapshots:
            return []

        snapshot = self._snapshots[-1][1]  # Latest snapshot
        top_stats = snapshot.statistics("lineno")

        allocations: List[Dict[str, Any]] = []
        for index, stat in enumerate(top_stats[:limit]):
            allocations.append(
                {
                    "rank": index + 1,
                    "size_mb": stat.size / 1024 / 1024,
                    "count": stat.count,
                    "filename": (
                        stat.traceback.format()[-1] if stat.traceback else "Unknown"
                    ),
                }
            )

        return allocations

    def compare_snapshots(self, name1: str, name2: str) -> Optional[Dict[str, Any]]:
        """Compare two memory snapshots"""
        snap1 = None
        snap2 = None

        for name, snapshot in self._snapshots:
            if name == name1:
                snap1 = snapshot
            elif name == name2:
                snap2 = snapshot

        if not (snap1 and snap2):
            return None

        top_stats = snap2.compare_to(snap1, "lineno")

        comparison: Dict[str, Any] = {
            "total_size_diff_mb": sum(stat.size_diff for stat in top_stats)
            / 1024
            / 1024,
            "total_count_diff": sum(stat.count_diff for stat in top_stats),
            "top_differences": [],
        }

        for stat in top_stats[:10]:
            comparison["top_differences"].append(
                {
                    "size_diff_mb": stat.size_diff / 1024 / 1024,
                    "count_diff": stat.count_diff,
                    "filename": (
                        stat.traceback.format()[-1] if stat.traceback else "Unknown"
                    ),
                }
            )

        return comparison


class AlertManager:
    """Performance alerting and notification system"""

    def __init__(self, tracker: PerformanceTracker):
        self.tracker = tracker
        self._alerts: List[PerformanceAlert] = []
        self._alert_history: Dict[str, datetime] = {}
        self._notification_callbacks: List[Callable[[PerformanceAlert], None]] = []
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task[None]] = None

    def add_notification_callback(self, callback: Callable[[PerformanceAlert], None]):
        """Add notification callback for alerts"""
        self._notification_callbacks.append(callback)

    async def start_monitoring(self, check_interval: float = 60.0):
        """Start alert monitoring"""
        if self._monitoring:
            return

        self._monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_loop(check_interval))
        logger.info("Alert monitoring started", interval=check_interval)

    async def stop_monitoring(self):
        """Stop alert monitoring"""
        self._monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Alert monitoring stopped")

    async def _monitor_loop(self, interval: float):
        """Main alert monitoring loop"""
        while self._monitoring:
            try:
                await self._check_alerts()
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in alert monitoring", error=str(e))
                await asyncio.sleep(interval)

    async def _check_alerts(self):
        """Check for performance alerts"""
        try:
            now = datetime.now(timezone.utc)
            recent_metrics = self.tracker.get_recent_metrics(timedelta(minutes=5))

            for metric_name, metrics in recent_metrics.items():
                if not metrics:
                    continue

                try:
                    # Get latest metric value
                    latest_metric = metrics[-1]

                    # Validate metric value
                    if not hasattr(latest_metric, "value") or not isfinite(
                        latest_metric.value
                    ):
                        logger.warning(
                            "Invalid metric value for alert checking",
                            metric=metric_name,
                            value=getattr(latest_metric, "value", None),
                        )
                        continue

                    # Check thresholds based on metric name
                    alert_key = self._get_alert_key(metric_name)
                    if alert_key in PERFORMANCE_THRESHOLDS:
                        thresholds = PERFORMANCE_THRESHOLDS[alert_key]

                        alert = None
                        if latest_metric.value >= thresholds["critical"]:
                            alert = PerformanceAlert(
                                metric_name=metric_name,
                                threshold_type="critical",
                                current_value=latest_metric.value,
                                threshold_value=thresholds["critical"],
                                timestamp=now,
                                description=f"Critical performance threshold exceeded for {metric_name}",
                                suggested_actions=self._get_suggested_actions(
                                    metric_name, "critical"
                                ),
                            )
                        elif latest_metric.value >= thresholds["warning"]:
                            alert = PerformanceAlert(
                                metric_name=metric_name,
                                threshold_type="warning",
                                current_value=latest_metric.value,
                                threshold_value=thresholds["warning"],
                                timestamp=now,
                                description=f"Performance warning threshold exceeded for {metric_name}",
                                suggested_actions=self._get_suggested_actions(
                                    metric_name, "warning"
                                ),
                            )

                        if alert:
                            await self._handle_alert(alert)

                except Exception as e:
                    logger.error("Error checking alerts for metric", metric=metric_name, error=str(e))
                    continue

        except Exception as e:
            logger.error("Failed to check alerts", error=str(e))

    def _get_alert_key(self, metric_name: str) -> str:
        """Map metric name to alert threshold key"""
        if "api.request.duration" in metric_name:
            return "api_response_time"
        elif "database.query.duration" in metric_name:
            return "database_query_time"
        elif "system.memory.usage_percent" in metric_name:
            return "memory_usage"
        elif "system.cpu.usage_percent" in metric_name:
            return "cpu_usage"
        elif "websocket.latency" in metric_name:
            return "websocket_latency"
        elif "ai.inference.duration" in metric_name:
            return "ai_inference_time"
        else:
            return metric_name

    def _get_suggested_actions(
        self, metric_name: str, threshold_type: str
    ) -> List[str]:
        """Get suggested actions for performance alerts"""
        actions = []

        if "api.request.duration" in metric_name:
            actions = [
                "Review API endpoint implementation for bottlenecks",
                "Check database query performance",
                "Consider implementing response caching",
                "Review concurrent request handling",
            ]
        elif "database.query.duration" in metric_name:
            actions = [
                "Analyze slow query logs",
                "Review database indexes",
                "Consider query optimization",
                "Check connection pool settings",
            ]
        elif "system.memory.usage" in metric_name:
            actions = [
                "Review memory-intensive operations",
                "Check for memory leaks",
                "Consider increasing available memory",
                "Review caching strategies",
            ]
        elif "system.cpu.usage" in metric_name:
            actions = [
                "Review CPU-intensive operations",
                "Consider implementing async processing",
                "Check for blocking operations",
                "Review resource allocation",
            ]

        if threshold_type == "critical":
            actions.insert(0, "IMMEDIATE ACTION REQUIRED")

        return actions

    async def _handle_alert(self, alert: PerformanceAlert):
        """Handle performance alert"""
        alert_key = f"{alert.metric_name}_{alert.threshold_type}"

        # Check cooldown period
        if alert_key in self._alert_history:
            last_alert = self._alert_history[alert_key]
            if datetime.now(timezone.utc) - last_alert < ALERT_COOLDOWN_PERIOD:
                return  # Skip alert due to cooldown

        # Record alert
        self._alerts.append(alert)
        self._alert_history[alert_key] = alert.timestamp

        # Log alert
        logger.warning(
            "Performance alert triggered",
            metric=alert.metric_name,
            threshold_type=alert.threshold_type,
            current_value=alert.current_value,
            threshold_value=alert.threshold_value,
            suggested_actions=alert.suggested_actions,
        )

        # Notify callbacks
        for callback in self._notification_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert)
                else:
                    callback(alert)
            except Exception as e:
                logger.error("Alert notification callback failed", error=str(e))

    def get_recent_alerts(
        self, time_window: timedelta = timedelta(hours=1)
    ) -> List[PerformanceAlert]:
        """Get recent alerts"""
        cutoff_time = datetime.now(timezone.utc) - time_window
        return [alert for alert in self._alerts if alert.timestamp >= cutoff_time]


class PerformanceOptimizer:
    """Automatic performance optimization suggestions and actions"""

    def __init__(self, tracker: PerformanceTracker):
        self.tracker = tracker
        # ML-related structures (kept minimal to avoid dependency errors if libs absent)
        self._ml_available: bool = False
        self._training_data: Dict[str, List[TrainingData]] = defaultdict(list)
        self._prediction_models: Dict[str, PredictionModel] = {}
        self._predictions: Dict[str, List[PredictionData]] = defaultdict(list)
        self._lock = threading.Lock()
        try:  # Best-effort optional imports
            import numpy as np  # type: ignore
            from sklearn.linear_model import LinearRegression  # type: ignore
            from sklearn.preprocessing import StandardScaler  # type: ignore
            import pandas as pd  # type: ignore

            self._ml_available = True
            self.np = np  # type: ignore[attr-defined]
            self.LinearRegression = LinearRegression  # type: ignore[attr-defined]
            self.StandardScaler = StandardScaler  # type: ignore[attr-defined]
            self.pd = pd  # type: ignore[attr-defined]
        except Exception:
            # Silently ignore import issues; predictive capabilities remain disabled
            pass

    def analyze_performance(self, time_window: timedelta) -> Dict[str, Any]:
        """Analyze performance and return insights."""
        # This is a placeholder implementation.
        # In a real-world scenario, this would involve more complex analysis.
        return {
            "summary": "Performance analysis placeholder.",
            "recommendations": ["Review slow queries.", "Optimize memory usage."],
        }

    def record_metric_for_prediction(self, metric_name: str, value: float, timestamp: datetime) -> None:
        """Record metric data for predictive modeling"""
        if not self._ml_available:
            return

        # Input validation
        if not metric_name.strip():
            logger.warning("Invalid metric name for prediction recording")
            return

        if not isfinite(value):
            logger.warning(
                "Invalid metric value for prediction recording",
                metric=metric_name,
                value=value,
            )
            return

        try:
            with self._lock:
                self._training_data[metric_name].append(
                    {
                        "timestamp": timestamp,
                        "value": value,
                        "hour": timestamp.hour,
                        "day_of_week": timestamp.weekday(),
                        "month": timestamp.month,
                    }
                )

                # Keep only recent data (last 30 days)
                cutoff = datetime.now(timezone.utc) - timedelta(days=30)
                self._training_data[metric_name] = [
                    d
                    for d in self._training_data[metric_name]
                    if d["timestamp"] >= cutoff
                ]

        except Exception as e:
            logger.error("Failed to record metric for prediction", metric=metric_name, error=str(e))

    def train_prediction_model(self, metric_name: str) -> bool:
        """Train prediction model for a metric"""
        if not self._ml_available or metric_name not in self._training_data:
            return False

        try:
            data = self._training_data[metric_name]
            if len(data) < 24:  # Need at least 24 hours of data
                return False

            # Prepare training data
            df = self.pd.DataFrame(data)
            df["timestamp_unix"] = df["timestamp"].astype(self.np.int64) // 10**9

            # Features: hour, day_of_week, recent trend
            x_train: List[List[Any]] = []
            y_train: List[Any] = []

            for i in range(6, len(df)):  # Start from index 6 to have enough history
                features: List[Any] = [
                    df.iloc[i]["hour"],
                    df.iloc[i]["day_of_week"],
                    df.iloc[i - 1]["value"],  # Previous value
                    (
                        df.iloc[i - 6]["value"]
                        if i >= 6
                        else df.iloc[i - 1]["value"]
                    ),  # 6 hours ago
                ]
                x_train.append(features)
                y_train.append(df.iloc[i]["value"])

            if len(x_train) < 10:
                return False

            x_train_np = self.np.array(x_train)
            y_train_np = self.np.array(y_train)

            # Scale features
            scaler = self.StandardScaler()
            x_scaled = scaler.fit_transform(x_train_np)

            # Train model
            model = self.LinearRegression()
            model.fit(x_scaled, y_train_np)

            with self._lock:
                self._prediction_models[metric_name] = {
                    "model": model,
                    "scaler": scaler,
                    "last_trained": datetime.now(timezone.utc),
                    "accuracy_score": model.score(x_scaled, y_train_np),
                }

            logger.info(
                "Prediction model trained",
                metric=metric_name,
                data_points=len(x_train),
                accuracy=model.score(x_scaled, y_train_np),
            )

            return True

        except Exception as e:
            logger.error(
                "Failed to train prediction model", metric=metric_name, error=str(e)
            )
            return False

    def predict_metric(self, metric_name: str, hours_ahead: int = 1) -> Optional[Prediction]:
        """Predict future metric values"""
        if not self._ml_available or metric_name not in self._prediction_models:
            return None

        try:
            model_data = self._prediction_models[metric_name]
            model = model_data["model"]
            scaler = model_data["scaler"]

            # Get recent data for prediction
            recent_data = (
                self._training_data[metric_name][-6:]
                if len(self._training_data[metric_name]) >= 6
                else self._training_data[metric_name]
            )

            if len(recent_data) < 2:
                return None

            # Prepare prediction features
            now = datetime.now(timezone.utc)
            features: List[Any] = [
                now.hour,
                now.weekday(),
                recent_data[-1]["value"],  # Most recent value
                (
                    recent_data[-6]["value"]
                    if len(recent_data) >= 6
                    else recent_data[0]["value"]
                ),
            ]

            x_pred = self.np.array([features])
            x_pred_scaled = scaler.transform(x_pred)

            prediction = model.predict(x_pred_scaled)[0]

            # Calculate confidence interval (simplified)
            confidence_interval = prediction * 0.15  # 15% confidence interval

            result: Prediction = {
                "metric_name": metric_name,
                "predicted_value": max(0, prediction),  # Ensure non-negative
                "confidence_interval": confidence_interval,
                "prediction_time": now + timedelta(hours=hours_ahead),
                "model_accuracy": model_data["accuracy_score"],
                "hours_ahead": hours_ahead,
            }

            # Store prediction for analysis
            with self._lock:
                self._predictions[metric_name].append(
                    {
                        "timestamp": now,
                        "prediction": result,
                        "actual_value": None,  # Will be filled when actual value is available
                    }
                )

                # Keep only recent predictions
                cutoff = now - timedelta(days=7)
                self._predictions[metric_name] = [
                    p
                    for p in self._predictions[metric_name]
                    if p["timestamp"] >= cutoff
                ]

            return result

        except Exception as e:
            logger.error(
                "Failed to predict metric", metric=metric_name, error=str(e)
            )
            return None

    def validate_predictions(self, metric_name: str) -> Dict[str, Any]:
        """Validate prediction accuracy"""
        if not self._ml_available or metric_name not in self._predictions:
            return {}

        predictions = self._predictions[metric_name]
        if not predictions:
            return {"status": "no_validated_predictions"}

        # Find predictions that now have actual values
        validated_predictions: List[PredictionData] = []

        for pred_data in predictions:
            if pred_data["actual_value"] is not None:
                validated_predictions.append(pred_data)

        if not validated_predictions:
            return {"status": "no_validated_predictions"}

        # Calculate accuracy metrics
        errors: List[Any] = []
        for pred in validated_predictions:
            predicted = pred["prediction"]["predicted_value"]
            actual = pred["actual_value"]
            if actual is not None:
                error = abs(predicted - actual)
                errors.append(error)

        avg_error = self.np.mean(errors)
        max_error = self.np.max(errors)
        actual_values = [
            p["actual_value"] for p in validated_predictions if p["actual_value"] is not None
        ]
        accuracy = 1 - (avg_error / self.np.mean(actual_values))

        return {
            "metric_name": metric_name,
            "predictions_validated": len(validated_predictions),
            "average_error": avg_error,
            "max_error": max_error,
            "accuracy_score": max(0, accuracy),  # Ensure non-negative
            "last_validated": (
                validated_predictions[-1]["timestamp"]
                if validated_predictions
                else None
            ),
        }

    def get_prediction_insights(self) -> Dict[str, Any]:
        """Get insights from predictive analytics"""
        insights: Dict[str, Any] = {
            "models_trained": len(self._prediction_models),
            "metrics_with_predictions": list(self._prediction_models.keys()),
            "prediction_accuracy": {},
            "anomaly_predictions": [],
            "trend_predictions": [],
        }

        # Get accuracy for each metric
        for metric_name in self._prediction_models.keys():
            accuracy = self.validate_predictions(metric_name)
            if accuracy:
                insights["prediction_accuracy"][metric_name] = accuracy

        # Generate insights based on predictions
        for metric_name, predictions in self._predictions.items():
            if not predictions:
                continue

            recent_predictions = predictions[-10:]  # Last 10 predictions

            # Check for anomaly predictions
            for pred_data in recent_predictions:
                pred = pred_data["prediction"]
                if (
                    pred["predicted_value"] > pred["confidence_interval"] * 3
                ):  # 3 sigma
                    insights["anomaly_predictions"].append(
                        {
                            "metric": metric_name,
                            "predicted_value": pred["predicted_value"],
                            "timestamp": pred["prediction_time"],
                            "severity": "high",
                        }
                    )

            # Check for trend predictions
            if len(recent_predictions) >= 5:
                values = [
                    p["prediction"]["predicted_value"] for p in recent_predictions
                ]
                trend = self._calculate_trend(values)

                if abs(trend) > 0.1:  # Significant trend
                    insights["trend_predictions"].append(
                        {
                            "metric": metric_name,
                            "trend": "increasing" if trend > 0 else "decreasing",
                            "magnitude": abs(trend),
                            "period": "recent_predictions",
                        }
                    )

        return insights

    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate trend slope"""
        if len(values) < 2:
            return 0.0

        x = self.np.arange(len(values))
        y = self.np.array(values)

        # Simple linear regression slope
        slope: float = self.np.polyfit(x, y, 1)[0]
        return slope

    def get_anomaly_predictions(self, time_window: timedelta = timedelta(hours=24)) -> List[Dict[str, Any]]:
        """Get predictions that indicate potential anomalies"""
        anomalies: List[Dict[str, Any]] = []
        cutoff_time = datetime.now(timezone.utc) - time_window

        for metric_name, predictions in self._predictions.items():
            for pred_data in predictions:
                if pred_data["timestamp"] < cutoff_time:
                    continue

                pred = pred_data["prediction"]

                # Check if prediction exceeds normal bounds
                if pred["predicted_value"] > (
                    pred.get("baseline", 0) + pred["confidence_interval"] * 2
                ):
                    anomalies.append(
                        {
                            "metric_name": metric_name,
                            "predicted_value": pred["predicted_value"],
                            "baseline": pred.get("baseline", 0),
                            "confidence_interval": pred["confidence_interval"],
                            "timestamp": pred["prediction_time"],
                            "severity": (
                                "high"
                                if pred["predicted_value"]
                                > pred.get("baseline", 0)
                                + pred["confidence_interval"] * 3
                                else "medium"
                            ),
                        }
                    )

        return sorted(anomalies, key=lambda x: x["predicted_value"], reverse=True)


class AnomalyDetector:
    """Anomaly detection for performance metrics"""

    def __init__(self, tracker: PerformanceTracker):
        self.tracker = tracker
        self._metric_baselines: Dict[str, Dict[str, Any]] = {}
        self._anomalies: List[Anomaly] = []
        self._lock = threading.Lock()

        # Try to import ML libraries for advanced anomaly detection
        self._ml_available = False
        try:
            from sklearn.ensemble import IsolationForest
            from sklearn.preprocessing import StandardScaler
            import numpy as np

            self._ml_available = True
            self.IsolationForest = IsolationForest
            self.StandardScaler = StandardScaler
            self.np = np
        except ImportError:
            logger.warning("ML libraries not available for advanced anomaly detection")

    def enable_anomaly_detection(self) -> bool:
        """Enable anomaly detection"""
        if not self._ml_available:
            logger.warning(
                "Cannot enable advanced anomaly detection - ML libraries not installed"
            )
            return False

        logger.info("Anomaly detection enabled")
        return True

    def update_baselines(self, time_window: timedelta = timedelta(hours=24)):
        """Update baseline values for anomaly detection"""
        recent_metrics = self.tracker.get_recent_metrics(time_window)

        with self._lock:
            for metric_name, metrics in recent_metrics.items():
                if not metrics:
                    continue

                values = [m.value for m in metrics]

                if len(values) < 10:  # Need minimum data points
                    continue

                # Calculate statistical baselines
                baseline: Dict[str, Any] = {
                    "mean": self.np.mean(values),
                    "std": self.np.std(values),
                    "min": min(values),
                    "max": max(values),
                    "p95": self.np.percentile(values, 95),
                    "p99": self.np.percentile(values, 99),
                    "last_updated": datetime.now(timezone.utc),
                }

                self._metric_baselines[metric_name] = baseline

        logger.debug("Baselines updated", metrics_count=len(self._metric_baselines))

    def detect_anomalies(
        self, metric_name: str, current_value: float
    ) -> Optional[Anomaly]:
        """Detect if current value is anomalous"""
        if metric_name not in self._metric_baselines:
            return None

        baseline = self._metric_baselines[metric_name]

        # Simple statistical anomaly detection
        mean = baseline["mean"]
        std = baseline["std"]

        if std == 0:
            # No variation in baseline, check against mean
            is_anomaly = abs(current_value - mean) > (mean * 0.1)  # 10% deviation
            z_score = 0.0
        else:
            z_score = abs(current_value - mean) / std
            is_anomaly = z_score > 3  # 3 sigma rule

        if is_anomaly:
            anomaly: Anomaly = {
                "metric_name": metric_name,
                "current_value": current_value,
                "expected_range": {
                    "mean": mean,
                    "std": std,
                    "min_normal": mean - 2 * std,
                    "max_normal": mean + 2 * std,
                },
                "z_score": z_score,
                "severity": (
                    "critical" if z_score > 5 else "high" if z_score > 3 else "medium"
                ),
                "timestamp": datetime.now(timezone.utc),
                "description": f"Anomalous value detected for {metric_name}: {current_value} (expected ~{mean:.2f})",
            }

            with self._lock:
                self._anomalies.append(anomaly)

                # Keep only recent anomalies
                cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
                self._anomalies = [
                    a for a in self._anomalies if a["timestamp"] >= cutoff
                ]

            return anomaly

        return None

    def get_recent_anomalies(
        self, time_window: timedelta = timedelta(hours=1)
    ) -> List[Anomaly]:
        """Get recent anomalies"""
        cutoff_time = datetime.now(timezone.utc) - time_window

        with self._lock:
            return [a for a in self._anomalies if a["timestamp"] >= cutoff_time]

    def get_anomaly_summary(self) -> Dict[str, Any]:
        """Get anomaly detection summary"""
        recent_anomalies = self.get_recent_anomalies(timedelta(hours=24))

        summary: Dict[str, Any] = {
            "total_anomalies_detected": len(recent_anomalies),
            "anomalies_by_severity": {},
            "anomalies_by_metric": {},
            "most_anomalous_metrics": [],
        }

        # Group by severity
        severity_counts: Dict[str, int] = {}
        for anomaly in recent_anomalies:
            severity = anomaly["severity"]
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        summary["anomalies_by_severity"] = severity_counts

        # Group by metric
        metric_counts: Dict[str, int] = {}
        for anomaly in recent_anomalies:
            metric = anomaly["metric_name"]
            metric_counts[metric] = metric_counts.get(metric, 0) + 1

        summary["anomalies_by_metric"] = metric_counts

        # Find most anomalous metrics
        if metric_counts:
            sorted_metrics = sorted(
                metric_counts.items(), key=lambda x: x[1], reverse=True
            )
            summary["most_anomalous_metrics"] = sorted_metrics[:5]

        return summary


class PerformanceManager:
    """Main performance monitoring and optimization manager"""

    def __init__(self, cache_manager: Optional[CacheManager] = None):
        self.tracker = PerformanceTracker()
        self.resource_monitor = ResourceMonitor(self.tracker)
        self.db_monitor = DatabasePerformanceMonitor(self.tracker)
        self.api_monitor = APIPerformanceMonitor(self.tracker)
        self.memory_profiler = MemoryProfiler(self.tracker)
        self.alert_manager = AlertManager(self.tracker)
        self.optimizer = PerformanceOptimizer(self.tracker)
        self.anomaly_detector = AnomalyDetector(self.tracker)
        self.cache_manager = cache_manager

        self._initialized = False
        self._background_tasks: List[asyncio.Task[Any]] = []

        logger.info("Performance manager initialized")

    def _validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize configuration parameters"""
        if not isinstance(config, dict):
            raise TypeError("Configuration must be a dictionary")

        validated_config = {}

        # Boolean flags
        bool_keys = ["enable_resource_monitoring", "enable_memory_profiling", "enable_alerting"]
        for key in bool_keys:
            value = config.get(key, True)
            if not isinstance(value, bool):
                logger.warning(f"Invalid boolean value for {key}: {value}, using default")
                value = True
            validated_config[key] = value

        # Numeric values with validation
        numeric_defaults = {
            "resource_monitoring_interval": (30.0, 1.0, 3600.0),  # default, min, max
            "alert_check_interval": (60.0, 10.0, 3600.0),
            "cleanup_interval": (300.0, 60.0, 86400.0),  # 1 min to 24 hours
        }

        for key, (default, min_val, max_val) in numeric_defaults.items():
            value = config.get(key, default)
            if not isinstance(value, (int, float)) or value < min_val or value > max_val:
                logger.warning(f"Invalid value for {key}: {value}, using default {default}")
                value = default
            validated_config[key] = value

        return validated_config

    async def _emergency_shutdown(self):
        """Emergency shutdown in case of initialization failure"""
        try:
            if hasattr(self.resource_monitor, '_monitoring') and self.resource_monitor._monitoring:
                await self.resource_monitor.stop_monitoring()
            if hasattr(self.alert_manager, '_monitoring') and self.alert_manager._monitoring:
                await self.alert_manager.stop_monitoring()
            if hasattr(self.memory_profiler, '_profiling') and self.memory_profiler._profiling:
                self.memory_profiler.stop_profiling()

            # Cancel any background tasks
            for task in self._background_tasks:
                if not task.done():
                    task.cancel()
                    try:
                        await asyncio.wait_for(task, timeout=5.0)
                    except asyncio.TimeoutError:
                        logger.warning("Background task did not cancel within timeout")

            self._background_tasks.clear()
            self._initialized = False
        except Exception as e:
            logger.error("Error during emergency shutdown", error=str(e))

    async def initialize(self, config: Optional[Dict[str, Any]] = None):
        """Initialize performance monitoring system"""
        if self._initialized:
            logger.warning("Performance monitoring system already initialized")
            return

        # Validate configuration
        config = self._validate_config(config or {})

        try:
            # Start resource monitoring
            if config.get("enable_resource_monitoring", True):
                interval = config.get("resource_monitoring_interval", 30.0)
                if not isinstance(interval, (int, float)) or interval <= 0:
                    raise ValueError(f"Invalid resource_monitoring_interval: {interval}")
                await self.resource_monitor.start_monitoring(interval=interval)

            # Start memory profiling
            if config.get("enable_memory_profiling", True):
                self.memory_profiler.start_profiling()

                await self.alert_manager.start_monitoring(check_interval=check_interval)

            # Set up cleanup task
            cleanup_interval = config.get("cleanup_interval", 300.0)
            if not isinstance(cleanup_interval, (int, float)) or cleanup_interval <= 0:
                raise ValueError(f"Invalid cleanup_interval: {cleanup_interval}")
            cleanup_task = asyncio.create_task(self._cleanup_loop(cleanup_interval))
            self._background_tasks.append(cleanup_task)

            self._initialized = True
            logger.info("Performance monitoring system initialized successfully", config=config)

        except Exception as e:
            logger.error("Failed to initialize performance monitoring system", error=str(e), config=config)
            # Attempt cleanup on failure
            await self._emergency_shutdown()
            raise

    async def shutdown(self):
        """Shutdown performance monitoring system"""
        if not self._initialized:
            return

        logger.info("Shutting down performance monitoring system")

        # Stop monitoring components
        await self.resource_monitor.stop_monitoring()
        await self.alert_manager.stop_monitoring()
        self.memory_profiler.stop_profiling()

        # Cancel background tasks
        for task in self._background_tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        self._background_tasks.clear()
        self._initialized = False

        logger.info("Performance monitoring system shutdown complete")

    async def _cleanup_loop(self, interval: float):
        """Background cleanup loop"""
        while True:
            try:
                await asyncio.sleep(interval)

                # Cleanup old metrics
                self.tracker.cleanup_old_metrics()

                # Force garbage collection periodically
                collected = gc.collect()
                if collected > 0:
                    logger.debug(
                        "Garbage collection completed", objects_collected=collected
                    )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in cleanup loop", error=str(e))

    def setup_database_monitoring(self, engine: Engine):
        """Set up database performance monitoring"""
        self.db_monitor.setup_sqlalchemy_monitoring(engine)
        logger.info("Database performance monitoring enabled")

    def get_performance_summary(
        self, time_window: timedelta = timedelta(hours=1)
    ) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        summary = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "time_window_hours": time_window.total_seconds() / 3600,
            "system_metrics": {},
            "api_metrics": {},
            "database_metrics": {},
            "recent_alerts": [],
            "performance_analysis": {},
            "recommendations": [],
        }

        # Get recent metrics
        recent_metrics = self.tracker.get_recent_metrics(time_window)

        # System metrics summary
        for metric_name in ["system.cpu.usage_percent", "system.memory.usage_percent"]:
            if metric_name in recent_metrics:
                stats = self.tracker.get_statistics(metric_name)
                summary["system_metrics"][metric_name] = stats

        # API metrics summary
        summary["api_metrics"] = self.api_monitor.get_endpoint_statistics()

        # Database metrics summary
        summary["database_metrics"] = self.db_monitor.get_query_statistics()

        # Recent alerts
        summary["recent_alerts"] = [
            {
                "metric_name": alert.metric_name,
                "threshold_type": alert.threshold_type,
                "current_value": alert.current_value,
                "threshold_value": alert.threshold_value,
                "timestamp": alert.timestamp.isoformat(),
                "description": alert.description,
                "suggested_actions": alert.suggested_actions,
            }
            for alert in self.alert_manager.get_recent_alerts(time_window)
        ]

        # Performance analysis
        summary["performance_analysis"] = self.optimizer.analyze_performance(
            time_window
        )

        return summary

    def get_health_status(self) -> Dict[str, Any]:
        """Get overall system health status"""
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "performance_monitoring": {
                "initialized": self._initialized,
                "resource_monitoring": self.resource_monitor._monitoring,
                "memory_profiling": self.memory_profiler._profiling,
                "alert_monitoring": self.alert_manager._monitoring,
                "background_tasks": len(self._background_tasks),
            },
            "metrics_count": sum(
                len(metrics) for metrics in self.tracker._metrics.values()
            ),
            "recent_alerts_count": len(self.alert_manager.get_recent_alerts()),
            "system_status": "healthy" if self._initialized else "not_initialized",
        }


# Global performance manager instance
_performance_manager: Optional[PerformanceManager] = None


def get_performance_manager() -> PerformanceManager:
    """Get global performance manager instance"""
    global _performance_manager
    if _performance_manager is None:
        _performance_manager = PerformanceManager()
    return _performance_manager


def initialize_performance_monitoring(
    config: Optional[Dict[str, Any]] = None,
) -> PerformanceManager:
    """Initialize global performance monitoring"""
    manager = get_performance_manager()
    asyncio.create_task(manager.initialize(config))
    return manager


# Utility functions for FastAPI integration
def setup_fastapi_monitoring(app: Any, performance_manager: "PerformanceManager"):
    """Set up FastAPI performance monitoring middleware"""

    @app.middleware("http")
    async def performance_monitoring_middleware(  # pyright: ignore[reportUnusedFunction]
        request: Any, call_next: Any
    ):
        start_time = time.time()

        # Extract request info
        method = request.method
        url_path = request.url.path
        user_id = getattr(request.state, "user_id", None)

        try:
            response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000

            # Record API performance
            performance_manager.api_monitor.record_request(
                endpoint=url_path,
                method=method,
                duration_ms=duration_ms,
                status_code=response.status_code,
                user_id=user_id,
            )

            return response

        except Exception:
            duration_ms = (time.time() - start_time) * 1000

            # Record error
            performance_manager.api_monitor.record_request(
                endpoint=url_path,
                method=method,
                duration_ms=duration_ms,
                status_code=500,
                user_id=user_id,
            )

            raise

    logger.info("FastAPI performance monitoring middleware enabled")


# Export all public classes and functions
__all__ = [
    "PerformanceManager",
    "PerformanceTracker",
    "ResourceMonitor",
    "DatabasePerformanceMonitor",
    "APIPerformanceMonitor",
    "MemoryProfiler",
    "AlertManager",
    "PerformanceOptimizer",
    "AnomalyDetector",
    "PerformanceMetric",
    "PerformanceAlert",
    "MetricType",
    "get_performance_manager",
    "initialize_performance_monitoring",
    "setup_fastapi_monitoring",
    "PERFORMANCE_THRESHOLDS",
]
