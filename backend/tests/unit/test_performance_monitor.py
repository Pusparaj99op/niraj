"""
Unit tests for performance optimization components
"""

import asyncio
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

# Import performance monitoring components
from src.utils.performance_monitor import (
    PerformanceTracker,
    PerformanceMetric,
    MetricType,
    ResourceMonitor,
    PerformanceOptimizer,
    PerformancePredictor,
    AnomalyDetector,
    PerformanceManager,
    PERFORMANCE_THRESHOLDS,
)


class TestPerformanceTracker:
    """Test cases for PerformanceTracker"""

    def setup_method(self):
        """Set up test fixtures"""
        self.tracker = PerformanceTracker()

    def test_add_metric(self):
        """Test adding a performance metric"""
        metric = PerformanceMetric(
            name="test.metric",
            value=100.0,
            metric_type=MetricType.GAUGE,
            timestamp=datetime.now(timezone.utc),
            labels={"test": "value"},
            metadata={"unit": "ms"},
        )

        self.tracker.add_metric(metric)

        # Verify metric was added
        assert "test.metric" in self.tracker._metrics
        assert len(self.tracker._metrics["test.metric"]) == 1
        assert self.tracker._metrics["test.metric"][0].value == 100.0

    def test_get_statistics(self):
        """Test getting statistics for a metric"""
        # Add some test metrics
        base_time = datetime.now(timezone.utc)
        for i in range(10):
            metric = PerformanceMetric(
                name="test.metric",
                value=float(i + 1),
                metric_type=MetricType.GAUGE,
                timestamp=base_time + timedelta(minutes=i),
            )
            self.tracker.add_metric(metric)

        stats = self.tracker.get_statistics("test.metric")

        assert stats is not None
        assert stats["count"] == 10
        assert stats["mean"] == 5.5
        assert stats["min"] == 1.0
        assert stats["max"] == 10.0

    def test_cleanup_old_metrics(self):
        """Test cleanup of old metrics"""
        base_time = datetime.now(timezone.utc)

        # Add old metric
        old_metric = PerformanceMetric(
            name="test.metric",
            value=1.0,
            metric_type=MetricType.GAUGE,
            timestamp=base_time - timedelta(days=40),  # Older than retention
        )
        self.tracker.add_metric(old_metric)

        # Add recent metric
        recent_metric = PerformanceMetric(
            name="test.metric",
            value=2.0,
            metric_type=MetricType.GAUGE,
            timestamp=base_time,
        )
        self.tracker.add_metric(recent_metric)

        # Cleanup old metrics
        self.tracker.cleanup_old_metrics()

        # Verify old metric was removed
        assert len(self.tracker._metrics["test.metric"]) == 1
        assert self.tracker._metrics["test.metric"][0].value == 2.0


class TestResourceMonitor:
    """Test cases for ResourceMonitor"""

    def setup_method(self):
        """Set up test fixtures"""
        self.tracker = PerformanceTracker()
        self.monitor = ResourceMonitor(self.tracker)

    @patch("psutil.cpu_percent")
    @patch("psutil.virtual_memory")
    @patch("psutil.disk_usage")
    @patch("psutil.net_io_counters")
    def test_collect_system_metrics(self, mock_net, mock_disk, mock_memory, mock_cpu):
        """Test collecting system metrics"""
        # Mock system calls
        mock_cpu.return_value = 50.0
        mock_memory.return_value = Mock(percent=60.0)
        mock_disk.return_value = Mock(percent=70.0)
        mock_net.return_value = Mock(bytes_sent=1000, bytes_recv=2000)

        # Collect metrics
        self.monitor._collect_system_metrics()

        # Verify metrics were recorded
        recent_metrics = self.tracker.get_recent_metrics(timedelta(minutes=1))

        assert "system.cpu.usage_percent" in recent_metrics
        assert "system.memory.usage_percent" in recent_metrics
        assert "system.disk.usage_percent" in recent_metrics

        # Check values
        cpu_metrics = recent_metrics["system.cpu.usage_percent"]
        assert cpu_metrics[0].value == 50.0

        memory_metrics = recent_metrics["system.memory.usage_percent"]
        assert memory_metrics[0].value == 60.0

    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self):
        """Test starting and stopping monitoring"""
        # Start monitoring
        await self.monitor.start_monitoring(interval=0.1)

        assert self.monitor._monitoring is True
        assert self.monitor._task is not None

        # Wait a bit for some metrics to be collected
        await asyncio.sleep(0.3)

        # Stop monitoring
        await self.monitor.stop_monitoring()

        assert self.monitor._monitoring is False
        assert self.monitor._task is None


class TestPerformancePredictor:
    """Test cases for PerformancePredictor"""

    def setup_method(self):
        """Set up test fixtures"""
        self.tracker = PerformanceTracker()
        self.predictor = PerformancePredictor(self.tracker)

    def test_enable_predictive_analytics_without_ml(self):
        """Test enabling predictive analytics when ML libraries are not available"""
        # Assuming ML libraries are not available in test environment
        result = self.predictor.enable_predictive_analytics()
        assert result is False

    def test_record_metric_for_prediction_without_ml(self):
        """Test recording metrics when ML is not available"""
        timestamp = datetime.now(timezone.utc)

        # Should not raise exception
        self.predictor.record_metric_for_prediction("test.metric", 100.0, timestamp)

        # Data should not be stored since ML is not available
        assert len(self.predictor._training_data["test.metric"]) == 0

    def test_train_prediction_model_without_ml(self):
        """Test training model when ML is not available"""
        result = self.predictor.train_prediction_model("test.metric")
        assert result is False

    def test_predict_metric_without_ml(self):
        """Test prediction when ML is not available"""
        result = self.predictor.predict_metric("test.metric")
        assert result is None

    @patch("src.utils.performance_monitor.PerformancePredictor._ml_available", True)
    def test_with_mock_ml_available(self):
        """Test behavior when ML libraries are mocked as available"""
        # This would require more extensive mocking of numpy, sklearn, pandas
        # For now, just test that the attribute exists
        assert hasattr(self.predictor, "_ml_available")


class TestAnomalyDetector:
    """Test cases for AnomalyDetector"""

    def setup_method(self):
        """Set up test fixtures"""
        self.tracker = PerformanceTracker()
        self.detector = AnomalyDetector(self.tracker)

    def test_enable_anomaly_detection_without_ml(self):
        """Test enabling anomaly detection when ML libraries are not available"""
        result = self.detector.enable_anomaly_detection()
        assert result is False

    def test_detect_anomalies_without_baseline(self):
        """Test anomaly detection without baseline data"""
        result = self.detector.detect_anomalies("test.metric", 100.0)
        assert result is None

    def test_update_baselines(self):
        """Test updating baselines with mock data"""
        # Add some metrics to tracker
        base_time = datetime.now(timezone.utc)
        for i in range(15):
            metric = PerformanceMetric(
                name="test.metric",
                value=100.0 + i,  # Some variation
                metric_type=MetricType.GAUGE,
                timestamp=base_time + timedelta(hours=i),
            )
            self.tracker.add_metric(metric)

        # Update baselines
        self.detector.update_baselines(timedelta(hours=24))

        # Check that baseline was created
        assert "test.metric" in self.detector._metric_baselines
        baseline = self.detector._metric_baselines["test.metric"]

        assert "mean" in baseline
        assert "std" in baseline
        assert "min" in baseline
        assert "max" in baseline

    def test_detect_anomalies_with_baseline(self):
        """Test anomaly detection with baseline data"""
        # Set up baseline manually
        self.detector._metric_baselines["test.metric"] = {
            "mean": 100.0,
            "std": 10.0,
            "min": 80.0,
            "max": 120.0,
            "p95": 115.0,
            "p99": 118.0,
            "last_updated": datetime.now(timezone.utc),
        }

        # Test normal value
        result = self.detector.detect_anomalies("test.metric", 105.0)
        assert result is None

        # Test anomalous value (more than 3 sigma)
        result = self.detector.detect_anomalies("test.metric", 140.0)
        assert result is not None
        assert result["severity"] == "high"
        assert result["current_value"] == 140.0

    def test_get_recent_anomalies(self):
        """Test getting recent anomalies"""
        # Add a mock anomaly
        anomaly = {
            "metric_name": "test.metric",
            "current_value": 150.0,
            "severity": "high",
            "timestamp": datetime.now(timezone.utc),
            "description": "Test anomaly",
        }
        self.detector._anomalies.append(anomaly)

        # Get recent anomalies
        recent = self.detector.get_recent_anomalies(timedelta(hours=1))

        assert len(recent) == 1
        assert recent[0]["current_value"] == 150.0

    def test_get_anomaly_summary(self):
        """Test getting anomaly summary"""
        # Add mock anomalies
        base_time = datetime.now(timezone.utc)
        anomalies = [
            {"metric_name": "metric1", "severity": "high", "timestamp": base_time},
            {"metric_name": "metric1", "severity": "medium", "timestamp": base_time},
            {"metric_name": "metric2", "severity": "high", "timestamp": base_time},
        ]
        self.detector._anomalies.extend(anomalies)

        summary = self.detector.get_anomaly_summary()

        assert summary["total_anomalies_detected"] == 3
        assert summary["anomalies_by_severity"]["high"] == 2
        assert summary["anomalies_by_severity"]["medium"] == 1
        assert len(summary["most_anomalous_metrics"]) > 0


class TestPerformanceOptimizer:
    """Test cases for PerformanceOptimizer"""

    def setup_method(self):
        """Set up test fixtures"""
        self.tracker = PerformanceTracker()
        self.optimizer = PerformanceOptimizer(self.tracker)

    def test_analyze_performance_empty(self):
        """Test performance analysis with no data"""
        result = self.optimizer.analyze_performance(timedelta(hours=1))

        assert result["time_window_hours"] == 1.0
        assert result["recommendations"] == []
        assert result["critical_issues"] == []
        assert result["optimization_opportunities"] == []

    def test_analyze_performance_with_api_data(self):
        """Test performance analysis with API metrics"""
        # Add API response time metrics
        base_time = datetime.now(timezone.utc)
        for i in range(10):
            metric = PerformanceMetric(
                name="api.request.duration",
                value=2000.0 if i < 9 else 8000.0,  # One slow request
                metric_type=MetricType.HISTOGRAM,
                timestamp=base_time + timedelta(minutes=i),
            )
            self.tracker.add_metric(metric)

        result = self.optimizer.analyze_performance(timedelta(hours=1))

        assert "api_avg_response_time_ms" in result["metrics_summary"]
        assert len(result["optimization_opportunities"]) > 0

    def test_analyze_performance_with_db_data(self):
        """Test performance analysis with database metrics"""
        # Add database query time metrics
        base_time = datetime.now(timezone.utc)
        for i in range(10):
            metric = PerformanceMetric(
                name="database.query.duration",
                value=50.0 if i < 9 else 200.0,  # One slow query
                metric_type=MetricType.HISTOGRAM,
                timestamp=base_time + timedelta(minutes=i),
            )
            self.tracker.add_metric(metric)

        result = self.optimizer.analyze_performance(timedelta(hours=1))

        assert "db_avg_query_time_ms" in result["metrics_summary"]
        assert len(result["optimization_opportunities"]) > 0


class TestPerformanceManager:
    """Test cases for PerformanceManager"""

    def setup_method(self):
        """Set up test fixtures"""
        self.manager = PerformanceManager()

    def test_initialization(self):
        """Test PerformanceManager initialization"""
        assert self.manager.tracker is not None
        assert self.manager.resource_monitor is not None
        assert self.manager.db_monitor is not None
        assert self.manager.api_monitor is not None
        assert self.manager.memory_profiler is not None
        assert self.manager.alert_manager is not None
        assert self.manager.optimizer is not None
        assert self.manager.predictor is not None
        assert self.manager.anomaly_detector is not None
        assert self.manager._initialized is False

    @pytest.mark.asyncio
    async def test_initialize_shutdown(self):
        """Test initialization and shutdown"""
        # Initialize
        await self.manager.initialize()

        assert self.manager._initialized is True
        assert len(self.manager._background_tasks) > 0

        # Shutdown
        await self.manager.shutdown()

        assert self.manager._initialized is False
        assert len(self.manager._background_tasks) == 0

    def test_get_performance_summary(self):
        """Test getting performance summary"""
        summary = self.manager.get_performance_summary()

        assert "timestamp" in summary
        assert "time_window_hours" in summary
        assert "system_metrics" in summary
        assert "api_metrics" in summary
        assert "database_metrics" in summary
        assert "recent_alerts" in summary
        assert "performance_analysis" in summary

    def test_get_health_status(self):
        """Test getting health status"""
        status = self.manager.get_health_status()

        assert "timestamp" in status
        assert "performance_monitoring" in status
        assert "metrics_count" in status
        assert "recent_alerts_count" in status
        assert "system_status" in status


class TestPerformanceThresholds:
    """Test cases for performance thresholds"""

    def test_thresholds_defined(self):
        """Test that performance thresholds are properly defined"""
        assert "api_response_time" in PERFORMANCE_THRESHOLDS
        assert "database_query_time" in PERFORMANCE_THRESHOLDS
        assert "memory_usage" in PERFORMANCE_THRESHOLDS
        assert "cpu_usage" in PERFORMANCE_THRESHOLDS

        # Check threshold structure
        api_thresholds = PERFORMANCE_THRESHOLDS["api_response_time"]
        assert "warning" in api_thresholds
        assert "critical" in api_thresholds

    def test_threshold_values_reasonable(self):
        """Test that threshold values are reasonable"""
        # API response time should be in milliseconds
        api_thresholds = PERFORMANCE_THRESHOLDS["api_response_time"]
        assert api_thresholds["warning"] > 100  # At least 100ms
        assert api_thresholds["critical"] > api_thresholds["warning"]

        # Memory usage should be percentage
        memory_thresholds = PERFORMANCE_THRESHOLDS["memory_usage"]
        assert 0 < memory_thresholds["warning"] < 100
        assert 0 < memory_thresholds["critical"] < 100
        assert memory_thresholds["critical"] > memory_thresholds["warning"]


# Integration tests
class TestPerformanceMonitoringIntegration:
    """Integration tests for the complete performance monitoring system"""

    def setup_method(self):
        """Set up test fixtures"""
        self.manager = PerformanceManager()

    @pytest.mark.asyncio
    async def test_full_monitoring_cycle(self):
        """Test a complete monitoring cycle"""
        # Initialize the system
        config = {
            "enable_resource_monitoring": False,  # Disable to avoid psutil dependency in tests
            "enable_memory_profiling": False,
            "enable_alerting": False,
        }

        await self.manager.initialize(config)

        # Add some test metrics
        base_time = datetime.now(timezone.utc)
        for i in range(5):
            metric = PerformanceMetric(
                name="test.api.response_time",
                value=100.0 + i * 10,
                metric_type=MetricType.HISTOGRAM,
                timestamp=base_time + timedelta(minutes=i),
            )
            self.manager.tracker.add_metric(metric)

        # Get performance summary
        summary = self.manager.get_performance_summary()

        assert summary is not None
        assert len(summary["performance_analysis"]) > 0

        # Shutdown
        await self.manager.shutdown()

    def test_component_interaction(self):
        """Test interaction between different components"""
        # Add metrics that should trigger analysis
        base_time = datetime.now(timezone.utc)

        # Add high API response times
        for i in range(10):
            metric = PerformanceMetric(
                name="api.request.duration",
                value=5000.0,  # 5 seconds - should trigger warning
                metric_type=MetricType.HISTOGRAM,
                timestamp=base_time + timedelta(minutes=i),
            )
            self.manager.tracker.add_metric(metric)

        # Analyze performance
        analysis = self.manager.optimizer.analyze_performance(timedelta(hours=1))

        # Should detect performance issues
        assert len(analysis["optimization_opportunities"]) > 0
        assert "api_avg_response_time_ms" in analysis["metrics_summary"]


if __name__ == "__main__":
    pytest.main([__file__])
