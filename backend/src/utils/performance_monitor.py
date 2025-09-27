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
import functools
import psutil
import time
import threading
import tracemalloc
import gc
from collections import defaultdict, deque
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Awaitable, Callable, Dict, List, Optional, TypeVar
import os

# Third-party imports
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import Pool

# Internal imports
from ..utils.logger import get_structured_logger
from ..core.cache import CacheManager

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


class PerformanceTracker:
    """Thread-safe performance metrics tracker"""

    def __init__(self, max_samples: int = 10000):
        self.max_samples = max_samples
        self._metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_samples))
        self._lock = threading.RLock()
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = defaultdict(float)
        self._histograms: Dict[str, List[float]] = defaultdict(list)

    def add_metric(self, metric: PerformanceMetric):
        """Add a performance metric"""
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
                    self._histograms[metric.name] = self._histograms[metric.name][
                        -1000:
                    ]

    def get_metrics(
        self, metric_name: str, limit: Optional[int] = None
    ) -> List[PerformanceMetric]:
        """Get metrics by name"""
        with self._lock:
            metrics = list(self._metrics[metric_name])
            if limit:
                metrics = metrics[-limit:]
            return metrics

    def get_recent_metrics(
        self, time_window: timedelta
    ) -> Dict[str, List[PerformanceMetric]]:
        """Get metrics within time window"""
        cutoff_time = datetime.now(timezone.utc) - time_window
        result = {}

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
                "count": n,
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


class ResourceMonitor:
    """System resource monitoring"""

    def __init__(self, tracker: PerformanceTracker):
        self.tracker = tracker
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None

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

            self.tracker.add_metric(
                PerformanceMetric(
                    name="system.cpu.usage_percent",
                    value=cpu_percent,
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

            # Disk metrics
            disk = psutil.disk_usage("/")
            disk_io = psutil.disk_io_counters()

            self.tracker.add_metric(
                PerformanceMetric(
                    name="system.disk.usage_percent",
                    value=(disk.used / disk.total) * 100,
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

            # Network metrics
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

            # Process-specific metrics
            process = psutil.Process()

            self.tracker.add_metric(
                PerformanceMetric(
                    name="process.memory.rss_bytes",
                    value=process.memory_info().rss,
                    metric_type=MetricType.GAUGE,
                    timestamp=timestamp,
                    labels={"resource": "process", "type": "memory"},
                )
            )

            self.tracker.add_metric(
                PerformanceMetric(
                    name="process.cpu.usage_percent",
                    value=process.cpu_percent(),
                    metric_type=MetricType.GAUGE,
                    timestamp=timestamp,
                    labels={"resource": "process", "type": "cpu"},
                )
            )

            # Python-specific metrics
            gc_stats = gc.get_stats()
            for i, stat in enumerate(gc_stats):
                self.tracker.add_metric(
                    PerformanceMetric(
                        name=f"python.gc.collections_gen{i}",
                        value=stat["collections"],
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
            logger.error("Failed to collect system metrics", error=str(e))


class DatabasePerformanceMonitor:
    """Database performance monitoring"""

    def __init__(self, tracker: PerformanceTracker):
        self.tracker = tracker
        self._query_stats: Dict[str, Dict] = defaultdict(
            lambda: {
                "count": 0,
                "total_time": 0.0,
                "min_time": float("inf"),
                "max_time": 0.0,
                "last_executed": None,
            }
        )
        self._lock = threading.RLock()

    def setup_sqlalchemy_monitoring(self, engine: Engine):
        """Set up SQLAlchemy event monitoring"""

        @event.listens_for(engine, "before_cursor_execute")
        def before_cursor_execute(
            conn, cursor, statement, parameters, context, executemany
        ):
            context._query_start_time = time.time()

        @event.listens_for(engine, "after_cursor_execute")
        def after_cursor_execute(
            conn, cursor, statement, parameters, context, executemany
        ):
            if hasattr(context, "_query_start_time"):
                duration = (
                    time.time() - context._query_start_time
                ) * 1000  # Convert to ms
                self._record_query_performance(statement, duration)

        @event.listens_for(Pool, "connect")
        def on_connect(dbapi_conn, connection_record):
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
        def on_checkout(dbapi_conn, connection_record, connection_proxy):
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

    def get_query_statistics(self) -> Dict[str, Dict]:
        """Get query performance statistics"""
        with self._lock:
            stats = {}
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
        self._endpoint_stats: Dict[str, Dict] = defaultdict(
            lambda: {
                "request_count": 0,
                "error_count": 0,
                "total_time": 0.0,
                "min_time": float("inf"),
                "max_time": 0.0,
            }
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

        # Record request count
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

        # Check for slow requests
        if duration_ms > PERFORMANCE_THRESHOLDS["api_response_time"]["warning"]:
            logger.warning(
                "Slow API request detected",
                endpoint=endpoint,
                method=method,
                duration_ms=duration_ms,
                status_code=status_code,
            )

    def get_endpoint_statistics(self) -> Dict[str, Dict]:
        """Get API endpoint statistics"""
        with self._lock:
            stats = {}
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

    def take_snapshot(self, name: str = None) -> Optional[Any]:
        """Take memory snapshot"""
        if not self._profiling:
            return None

        snapshot = tracemalloc.take_snapshot()
        self._snapshots.append((name or f"snapshot_{len(self._snapshots)}", snapshot))

        # Get current memory usage
        current, peak = tracemalloc.get_traced_memory()

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

    def analyze_top_allocations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Analyze top memory allocations"""
        if not self._snapshots:
            return []

        snapshot = self._snapshots[-1][1]  # Latest snapshot
        top_stats = snapshot.statistics("lineno")

        allocations = []
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

        comparison = {
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
        self._notification_callbacks: List[Callable] = []
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None

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
        now = datetime.now(timezone.utc)
        recent_metrics = self.tracker.get_recent_metrics(timedelta(minutes=5))

        for metric_name, metrics in recent_metrics.items():
            if not metrics:
                continue

            # Get latest metric value
            latest_metric = metrics[-1]

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

    class PerformancePredictor:
        """Predictive analytics for performance metrics using machine learning"""

        def __init__(self, tracker: PerformanceTracker):
            self.tracker = tracker
            self._prediction_models: Dict[str, Any] = {}
            self._training_data: Dict[str, List] = defaultdict(list)
            self._predictions: Dict[str, List] = defaultdict(list)
            self._lock = threading.RLock()

            # Try to import ML libraries
            self._ml_available = False
            try:
                import numpy as np
                from sklearn.linear_model import LinearRegression
                from sklearn.preprocessing import StandardScaler
                import pandas as pd

                self._ml_available = True
                self.np = np
                self.LinearRegression = LinearRegression
                self.StandardScaler = StandardScaler
                self.pd = pd
            except ImportError:
                logger.warning("ML libraries not available for predictive analytics")

        def enable_predictive_analytics(self):
            """Enable predictive analytics if ML libraries are available"""
            if not self._ml_available:
                logger.warning(
                    "Cannot enable predictive analytics - ML libraries not installed"
                )
                return False

            logger.info("Predictive analytics enabled")
            return True

        def record_metric_for_prediction(
            self, metric_name: str, value: float, timestamp: datetime
        ):
            """Record metric data for predictive modeling"""
            if not self._ml_available:
                return

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
                X = []
                y = []

                for i in range(6, len(df)):  # Start from index 6 to have enough history
                    features = [
                        df.iloc[i]["hour"],
                        df.iloc[i]["day_of_week"],
                        df.iloc[i - 1]["value"],  # Previous value
                        (
                            df.iloc[i - 6]["value"]
                            if i >= 6
                            else df.iloc[i - 1]["value"]
                        ),  # 6 hours ago
                    ]
                    X.append(features)
                    y.append(df.iloc[i]["value"])

                if len(X) < 10:
                    return False

                X = self.np.array(X)
                y = self.np.array(y)

                # Scale features
                scaler = self.StandardScaler()
                X_scaled = scaler.fit_transform(X)

                # Train model
                model = self.LinearRegression()
                model.fit(X_scaled, y)

                with self._lock:
                    self._prediction_models[metric_name] = {
                        "model": model,
                        "scaler": scaler,
                        "last_trained": datetime.now(timezone.utc),
                        "accuracy_score": model.score(X_scaled, y),
                    }

                logger.info(
                    "Prediction model trained",
                    metric=metric_name,
                    data_points=len(X),
                    accuracy=model.score(X_scaled, y),
                )

                return True

            except Exception as e:
                logger.error(
                    "Failed to train prediction model", metric=metric_name, error=str(e)
                )
                return False

        def predict_metric(
            self, metric_name: str, hours_ahead: int = 1
        ) -> Optional[Dict[str, Any]]:
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
                features = [
                    now.hour,
                    now.weekday(),
                    recent_data[-1]["value"],  # Most recent value
                    (
                        recent_data[-6]["value"]
                        if len(recent_data) >= 6
                        else recent_data[0]["value"]
                    ),
                ]

                X_pred = self.np.array([features])
                X_pred_scaled = scaler.transform(X_pred)

                prediction = model.predict(X_pred_scaled)[0]

                # Calculate confidence interval (simplified)
                confidence_interval = prediction * 0.15  # 15% confidence interval

                result = {
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
                return {}

            # Find predictions that now have actual values
            validated_predictions = []

            for pred_data in predictions:
                if pred_data["actual_value"] is not None:
                    validated_predictions.append(pred_data)

            if not validated_predictions:
                return {"status": "no_validated_predictions"}

            # Calculate accuracy metrics
            errors = []
            for pred in validated_predictions:
                predicted = pred["prediction"]["predicted_value"]
                actual = pred["actual_value"]
                error = abs(predicted - actual)
                errors.append(error)

            avg_error = self.np.mean(errors)
            max_error = self.np.max(errors)
            accuracy = 1 - (
                avg_error
                / self.np.mean([p["actual_value"] for p in validated_predictions])
            )

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
            insights = {
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
            slope = self.np.polyfit(x, y, 1)[0]
            return slope

        def get_anomaly_predictions(
            self, time_window: timedelta = timedelta(hours=24)
        ) -> List[Dict[str, Any]]:
            """Get predictions that indicate potential anomalies"""
            anomalies = []
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
            self._metric_baselines: Dict[str, Dict[str, float]] = {}
            self._anomalies: List[Dict[str, Any]] = []
            self._lock = threading.RLock()

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
                logger.warning(
                    "ML libraries not available for advanced anomaly detection"
                )

        def enable_anomaly_detection(self):
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
                    baseline = {
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
        ) -> Optional[Dict[str, Any]]:
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
                z_score = 0
            else:
                z_score = abs(current_value - mean) / std
                is_anomaly = z_score > 3  # 3 sigma rule

            if is_anomaly:
                anomaly = {
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
                        "critical"
                        if z_score > 5
                        else "high" if z_score > 3 else "medium"
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
        ) -> List[Dict[str, Any]]:
            """Get recent anomalies"""
            cutoff_time = datetime.now(timezone.utc) - time_window

            with self._lock:
                return [a for a in self._anomalies if a["timestamp"] >= cutoff_time]

        def get_anomaly_summary(self) -> Dict[str, Any]:
            """Get anomaly detection summary"""
            recent_anomalies = self.get_recent_anomalies(timedelta(hours=24))

            summary = {
                "total_anomalies_detected": len(recent_anomalies),
                "anomalies_by_severity": {},
                "anomalies_by_metric": {},
                "most_anomalous_metrics": [],
            }

            # Group by severity
            severity_counts = {}
            for anomaly in recent_anomalies:
                severity = anomaly["severity"]
                severity_counts[severity] = severity_counts.get(severity, 0) + 1

            summary["anomalies_by_severity"] = severity_counts

            # Group by metric
            metric_counts = {}
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


# Performance monitoring decorators
def monitor_performance(
    operation_name: Optional[str] = None,
    include_args: bool = False,
    include_result: bool = False,
    timeout_threshold: Optional[float] = None,
):
    """Decorator for monitoring function performance"""

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            name = operation_name or f"{func.__module__}.{func.__name__}"
            start_time = time.time()
            start_memory = 0

            # Start memory tracking if enabled
            if tracemalloc.is_tracing():
                start_memory = tracemalloc.get_traced_memory()[0]

            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000

                # Calculate memory usage
                memory_used = 0
                if tracemalloc.is_tracing():
                    memory_used = tracemalloc.get_traced_memory()[0] - start_memory

                # Record performance metric
                if hasattr(func, "_performance_tracker"):
                    tracker = func._performance_tracker
                    tracker.add_metric(
                        PerformanceMetric(
                            name=f"function.{name}.duration_ms",
                            value=duration_ms,
                            metric_type=MetricType.HISTOGRAM,
                            timestamp=datetime.now(timezone.utc),
                            labels={"function": name, "success": "true"},
                            metadata={
                                "args_count": len(args) if include_args else None,
                                "kwargs_count": len(kwargs) if include_args else None,
                                "memory_used_bytes": (
                                    memory_used if memory_used > 0 else None
                                ),
                                "has_result": include_result and result is not None,
                            },
                        )
                    )

                # Check timeout threshold
                if timeout_threshold and duration_ms > timeout_threshold:
                    logger.warning(
                        "Function execution exceeded timeout threshold",
                        function=name,
                        duration_ms=duration_ms,
                        threshold_ms=timeout_threshold,
                    )

                logger.debug(
                    "Function performance recorded",
                    function=name,
                    duration_ms=duration_ms,
                    memory_used_bytes=memory_used,
                )

                return result

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000

                # Record error metric
                if hasattr(func, "_performance_tracker"):
                    tracker = func._performance_tracker
                    tracker.add_metric(
                        PerformanceMetric(
                            name=f"function.{name}.duration_ms",
                            value=duration_ms,
                            metric_type=MetricType.HISTOGRAM,
                            timestamp=datetime.now(timezone.utc),
                            labels={
                                "function": name,
                                "success": "false",
                                "error_type": type(e).__name__,
                            },
                            metadata={"error_message": str(e)[:200]},
                        )
                    )

                logger.error(
                    "Function execution failed",
                    function=name,
                    duration_ms=duration_ms,
                    error=str(e),
                )

                raise

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            name = operation_name or f"{func.__module__}.{func.__name__}"
            start_time = time.time()
            start_memory = 0

            # Start memory tracking if enabled
            if tracemalloc.is_tracing():
                start_memory = tracemalloc.get_traced_memory()[0]

            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000

                # Calculate memory usage
                memory_used = 0
                if tracemalloc.is_tracing():
                    memory_used = tracemalloc.get_traced_memory()[0] - start_memory

                # Record performance metric
                if hasattr(func, "_performance_tracker"):
                    tracker = func._performance_tracker
                    tracker.add_metric(
                        PerformanceMetric(
                            name=f"function.{name}.duration_ms",
                            value=duration_ms,
                            metric_type=MetricType.HISTOGRAM,
                            timestamp=datetime.now(timezone.utc),
                            labels={"function": name, "success": "true"},
                            metadata={
                                "args_count": len(args) if include_args else None,
                                "kwargs_count": len(kwargs) if include_args else None,
                                "memory_used_bytes": (
                                    memory_used if memory_used > 0 else None
                                ),
                                "has_result": include_result and result is not None,
                            },
                        )
                    )

                # Check timeout threshold
                if timeout_threshold and duration_ms > timeout_threshold:
                    logger.warning(
                        "Async function execution exceeded timeout threshold",
                        function=name,
                        duration_ms=duration_ms,
                        threshold_ms=timeout_threshold,
                    )

                logger.debug(
                    "Async function performance recorded",
                    function=name,
                    duration_ms=duration_ms,
                    memory_used_bytes=memory_used,
                )

                return result

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000

                # Record error metric
                if hasattr(func, "_performance_tracker"):
                    tracker = func._performance_tracker
                    tracker.add_metric(
                        PerformanceMetric(
                            name=f"function.{name}.duration_ms",
                            value=duration_ms,
                            metric_type=MetricType.HISTOGRAM,
                            timestamp=datetime.now(timezone.utc),
                            labels={
                                "function": name,
                                "success": "false",
                                "error_type": type(e).__name__,
                            },
                            metadata={"error_message": str(e)[:200]},
                        )
                    )

                logger.error(
                    "Async function execution failed",
                    function=name,
                    duration_ms=duration_ms,
                    error=str(e),
                )

                raise

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


@contextmanager
def performance_context(
    tracker: PerformanceTracker,
    operation_name: str,
    labels: Optional[Dict[str, str]] = None,
):
    """Context manager for performance monitoring"""
    start_time = time.time()
    start_memory = 0

    if tracemalloc.is_tracing():
        start_memory = tracemalloc.get_traced_memory()[0]

    try:
        yield

        duration_ms = (time.time() - start_time) * 1000
        memory_used = 0

        if tracemalloc.is_tracing():
            memory_used = tracemalloc.get_traced_memory()[0] - start_memory

        tracker.add_metric(
            PerformanceMetric(
                name=f"operation.{operation_name}.duration_ms",
                value=duration_ms,
                metric_type=MetricType.HISTOGRAM,
                timestamp=datetime.now(timezone.utc),
                labels=labels or {},
                metadata={
                    "success": True,
                    "memory_used_bytes": memory_used if memory_used > 0 else None,
                },
            )
        )

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000

        tracker.add_metric(
            PerformanceMetric(
                name=f"operation.{operation_name}.duration_ms",
                value=duration_ms,
                metric_type=MetricType.HISTOGRAM,
                timestamp=datetime.now(timezone.utc),
                labels=labels or {},
                metadata={
                    "success": False,
                    "error_type": type(e).__name__,
                    "error_message": str(e)[:200],
                },
            )
        )

        raise


@asynccontextmanager
async def async_performance_context(
    tracker: PerformanceTracker,
    operation_name: str,
    labels: Optional[Dict[str, str]] = None,
):
    """Async context manager for performance monitoring"""
    start_time = time.time()
    start_memory = 0

    if tracemalloc.is_tracing():
        start_memory = tracemalloc.get_traced_memory()[0]

    try:
        yield

        duration_ms = (time.time() - start_time) * 1000
        memory_used = 0

        if tracemalloc.is_tracing():
            memory_used = tracemalloc.get_traced_memory()[0] - start_memory

        tracker.add_metric(
            PerformanceMetric(
                name=f"operation.{operation_name}.duration_ms",
                value=duration_ms,
                metric_type=MetricType.HISTOGRAM,
                timestamp=datetime.now(timezone.utc),
                labels=labels or {},
                metadata={
                    "success": True,
                    "memory_used_bytes": memory_used if memory_used > 0 else None,
                },
            )
        )

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000

        tracker.add_metric(
            PerformanceMetric(
                name=f"operation.{operation_name}.duration_ms",
                value=duration_ms,
                metric_type=MetricType.HISTOGRAM,
                timestamp=datetime.now(timezone.utc),
                labels=labels or {},
                metadata={
                    "success": False,
                    "error_type": type(e).__name__,
                    "error_message": str(e)[:200],
                },
            )
        )

        raise


class PerformanceManager:
    def __init__(self, tracker: PerformanceTracker):
        self.tracker = tracker
        self._prediction_models: Dict[str, Any] = {}
        self._training_data: Dict[str, List] = defaultdict(list)
        self._predictions: Dict[str, List] = defaultdict(list)
        self._lock = threading.RLock()

        # Try to import ML libraries
        self._ml_available = False
        try:
            import numpy as np
            from sklearn.linear_model import LinearRegression
            from sklearn.preprocessing import StandardScaler
            import pandas as pd

            self._ml_available = True
            self.np = np
            self.LinearRegression = LinearRegression
            self.StandardScaler = StandardScaler
            self.pd = pd
        except ImportError:
            logger.warning("ML libraries not available for predictive analytics")

    def enable_predictive_analytics(self):
        """Enable predictive analytics if ML libraries are available"""
        if not self._ml_available:
            logger.warning(
                "Cannot enable predictive analytics - ML libraries not installed"
            )
            return False

        logger.info("Predictive analytics enabled")
        return True

    def record_metric_for_prediction(
        self, metric_name: str, value: float, timestamp: datetime
    ):
        """Record metric data for predictive modeling"""
        if not self._ml_available:
            return

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
                d for d in self._training_data[metric_name] if d["timestamp"] >= cutoff
            ]

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
            X = []
            y = []

            for i in range(6, len(df)):  # Start from index 6 to have enough history
                features = [
                    df.iloc[i]["hour"],
                    df.iloc[i]["day_of_week"],
                    df.iloc[i - 1]["value"],  # Previous value
                    (
                        df.iloc[i - 6]["value"] if i >= 6 else df.iloc[i - 1]["value"]
                    ),  # 6 hours ago
                ]
                X.append(features)
                y.append(df.iloc[i]["value"])

            if len(X) < 10:
                return False

            X = self.np.array(X)
            y = self.np.array(y)

            # Scale features
            scaler = self.StandardScaler()
            X_scaled = scaler.fit_transform(X)

            # Train model
            model = self.LinearRegression()
            model.fit(X_scaled, y)

            with self._lock:
                self._prediction_models[metric_name] = {
                    "model": model,
                    "scaler": scaler,
                    "last_trained": datetime.now(timezone.utc),
                    "accuracy_score": model.score(X_scaled, y),
                }

            logger.info(
                "Prediction model trained",
                metric=metric_name,
                data_points=len(X),
                accuracy=model.score(X_scaled, y),
            )

            return True

        except Exception as e:
            logger.error(
                "Failed to train prediction model", metric=metric_name, error=str(e)
            )
            return False

    def predict_metric(
        self, metric_name: str, hours_ahead: int = 1
    ) -> Optional[Dict[str, Any]]:
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
            features = [
                now.hour,
                now.weekday(),
                recent_data[-1]["value"],  # Most recent value
                (
                    recent_data[-6]["value"]
                    if len(recent_data) >= 6
                    else recent_data[0]["value"]
                ),
            ]

            X_pred = self.np.array([features])
            X_pred_scaled = scaler.transform(X_pred)

            prediction = model.predict(X_pred_scaled)[0]

            # Calculate confidence interval (simplified)
            confidence_interval = prediction * 0.15  # 15% confidence interval

            result = {
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
            logger.error("Failed to predict metric", metric=metric_name, error=str(e))
            return None

    def validate_predictions(self, metric_name: str) -> Dict[str, Any]:
        """Validate prediction accuracy"""
        if not self._ml_available or metric_name not in self._predictions:
            return {}

        predictions = self._predictions[metric_name]
        if not predictions:
            return {}

        # Find predictions that now have actual values
        validated_predictions = []

        for pred_data in predictions:
            if pred_data["actual_value"] is not None:
                validated_predictions.append(pred_data)

        if not validated_predictions:
            return {"status": "no_validated_predictions"}

        # Calculate accuracy metrics
        errors = []
        for pred in validated_predictions:
            predicted = pred["prediction"]["predicted_value"]
            actual = pred["actual_value"]
            error = abs(predicted - actual)
            errors.append(error)

        avg_error = self.np.mean(errors)
        max_error = self.np.max(errors)
        accuracy = 1 - (
            avg_error / self.np.mean([p["actual_value"] for p in validated_predictions])
        )

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
        insights = {
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
                if pred["predicted_value"] > pred["confidence_interval"] * 3:  # 3 sigma
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
        slope = self.np.polyfit(x, y, 1)[0]
        return slope

    def get_anomaly_predictions(
        self, time_window: timedelta = timedelta(hours=24)
    ) -> List[Dict[str, Any]]:
        """Get predictions that indicate potential anomalies"""
        anomalies = []
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


class PerformancePredictor:
    """Predictive analytics for performance metrics using machine learning"""

    def __init__(self, tracker: PerformanceTracker):
        self.tracker = tracker
        self._prediction_models: Dict[str, Any] = {}
        self._training_data: Dict[str, List] = defaultdict(list)
        self._predictions: Dict[str, List] = defaultdict(list)
        self._lock = threading.RLock()

        # Try to import ML libraries
        self._ml_available = False
        try:
            import numpy as np
            from sklearn.linear_model import LinearRegression
            from sklearn.preprocessing import StandardScaler
            import pandas as pd

            self._ml_available = True
            self.np = np
            self.LinearRegression = LinearRegression
            self.StandardScaler = StandardScaler
            self.pd = pd
        except ImportError:
            logger.warning("ML libraries not available for predictive analytics")

    def enable_predictive_analytics(self):
        """Enable predictive analytics if ML libraries are available"""
        if not self._ml_available:
            logger.warning(
                "Cannot enable predictive analytics - ML libraries not installed"
            )
            return False

        logger.info("Predictive analytics enabled")
        return True

    def record_metric_for_prediction(
        self, metric_name: str, value: float, timestamp: datetime
    ):
        """Record metric data for predictive modeling"""
        if not self._ml_available:
            return

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
                d for d in self._training_data[metric_name] if d["timestamp"] >= cutoff
            ]

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
            X = []
            y = []

            for i in range(6, len(df)):  # Start from index 6 to have enough history
                features = [
                    df.iloc[i]["hour"],
                    df.iloc[i]["day_of_week"],
                    df.iloc[i - 1]["value"],  # Previous value
                    (
                        df.iloc[i - 6]["value"] if i >= 6 else df.iloc[i - 1]["value"]
                    ),  # 6 hours ago
                ]
                X.append(features)
                y.append(df.iloc[i]["value"])

            if len(X) < 10:
                return False

            X = self.np.array(X)
            y = self.np.array(y)

            # Scale features
            scaler = self.StandardScaler()
            X_scaled = scaler.fit_transform(X)

            # Train model
            model = self.LinearRegression()
            model.fit(X_scaled, y)

            with self._lock:
                self._prediction_models[metric_name] = {
                    "model": model,
                    "scaler": scaler,
                    "last_trained": datetime.now(timezone.utc),
                    "accuracy_score": model.score(X_scaled, y),
                }

            logger.info(
                "Prediction model trained",
                metric=metric_name,
                data_points=len(X),
                accuracy=model.score(X_scaled, y),
            )

            return True

        except Exception as e:
            logger.error(
                "Failed to train prediction model", metric=metric_name, error=str(e)
            )
            return False

    def predict_metric(
        self, metric_name: str, hours_ahead: int = 1
    ) -> Optional[Dict[str, Any]]:
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
            features = [
                now.hour,
                now.weekday(),
                recent_data[-1]["value"],  # Most recent value
                (
                    recent_data[-6]["value"]
                    if len(recent_data) >= 6
                    else recent_data[0]["value"]
                ),
            ]

            X_pred = self.np.array([features])
            X_pred_scaled = scaler.transform(X_pred)

            prediction = model.predict(X_pred_scaled)[0]

            # Calculate confidence interval (simplified)
            confidence_interval = prediction * 0.15  # 15% confidence interval

            result = {
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
            logger.error("Failed to predict metric", metric=metric_name, error=str(e))
            return None

    def validate_predictions(self, metric_name: str) -> Dict[str, Any]:
        """Validate prediction accuracy"""
        if not self._ml_available or metric_name not in self._predictions:
            return {}

        predictions = self._predictions[metric_name]
        if not predictions:
            return {}

        # Find predictions that now have actual values
        validated_predictions = []

        for pred_data in predictions:
            if pred_data["actual_value"] is not None:
                validated_predictions.append(pred_data)

        if not validated_predictions:
            return {"status": "no_validated_predictions"}

        # Calculate accuracy metrics
        errors = []
        for pred in validated_predictions:
            predicted = pred["prediction"]["predicted_value"]
            actual = pred["actual_value"]
            error = abs(predicted - actual)
            errors.append(error)

        avg_error = self.np.mean(errors)
        max_error = self.np.max(errors)
        accuracy = 1 - (
            avg_error / self.np.mean([p["actual_value"] for p in validated_predictions])
        )

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
        insights = {
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
                if pred["predicted_value"] > pred["confidence_interval"] * 3:  # 3 sigma
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
        slope = self.np.polyfit(x, y, 1)[0]
        return slope

    def get_anomaly_predictions(
        self, time_window: timedelta = timedelta(hours=24)
    ) -> List[Dict[str, Any]]:
        """Get predictions that indicate potential anomalies"""
        anomalies = []
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
        self._metric_baselines: Dict[str, Dict[str, float]] = {}
        self._anomalies: List[Dict[str, Any]] = []
        self._lock = threading.RLock()

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

    def enable_anomaly_detection(self):
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
                baseline = {
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
    ) -> Optional[Dict[str, Any]]:
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
            z_score = 0
        else:
            z_score = abs(current_value - mean) / std
            is_anomaly = z_score > 3  # 3 sigma rule

        if is_anomaly:
            anomaly = {
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
    ) -> List[Dict[str, Any]]:
        """Get recent anomalies"""
        cutoff_time = datetime.now(timezone.utc) - time_window

        with self._lock:
            return [a for a in self._anomalies if a["timestamp"] >= cutoff_time]

    def get_anomaly_summary(self) -> Dict[str, Any]:
        """Get anomaly detection summary"""
        recent_anomalies = self.get_recent_anomalies(timedelta(hours=24))

        summary = {
            "total_anomalies_detected": len(recent_anomalies),
            "anomalies_by_severity": {},
            "anomalies_by_metric": {},
            "most_anomalous_metrics": [],
        }

        # Group by severity
        severity_counts = {}
        for anomaly in recent_anomalies:
            severity = anomaly["severity"]
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        summary["anomalies_by_severity"] = severity_counts

        # Group by metric
        metric_counts = {}
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
        self.predictor = PerformancePredictor(self.tracker)
        self.anomaly_detector = AnomalyDetector(self.tracker)
        self.cache_manager = cache_manager

        self._initialized = False
        self._background_tasks: List[asyncio.Task] = []

        logger.info("Performance manager initialized")

    async def initialize(self, config: Optional[Dict[str, Any]] = None):
        """Initialize performance monitoring system"""
        if self._initialized:
            return

        config = config or {}

        # Start resource monitoring
        if config.get("enable_resource_monitoring", True):
            await self.resource_monitor.start_monitoring(
                interval=config.get("resource_monitoring_interval", 30.0)
            )

        # Start memory profiling
        if config.get("enable_memory_profiling", True):
            self.memory_profiler.start_profiling()

        # Start alert monitoring
        if config.get("enable_alerting", True):
            await self.alert_manager.start_monitoring(
                check_interval=config.get("alert_check_interval", 60.0)
            )

        # Set up cleanup task
        cleanup_task = asyncio.create_task(
            self._cleanup_loop(config.get("cleanup_interval", 300.0))
        )
        self._background_tasks.append(cleanup_task)

        self._initialized = True
        logger.info("Performance monitoring system initialized", config=config)

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
def setup_fastapi_monitoring(app, performance_manager: PerformanceManager):
    """Set up FastAPI performance monitoring middleware"""

    @app.middleware("http")
    async def performance_monitoring_middleware(request, call_next):
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
    "PerformancePredictor",
    "AnomalyDetector",
    "PerformanceMetric",
    "PerformanceAlert",
    "MetricType",
    "monitor_performance",
    "performance_context",
    "async_performance_context",
    "get_performance_manager",
    "initialize_performance_monitoring",
    "setup_fastapi_monitoring",
    "PERFORMANCE_THRESHOLDS",
]
