#!/usr/bin/env python3
"""
Advanced Load Testing Framework for NIRAJ Trading Platform

This module provides comprehensive load testing capabilities including
stress testing, performance benchmarking, and system reliability testing.

Features:
- Configurable load testing scenarios
- Real-time performance monitoring
- Distributed load generation
- WebSocket load testing
- Database stress testing
- API endpoint benchmarking
- Resource utilization monitoring
- Automated performance analysis
- Load testing reports

Author: NIRAJ Development Team
Version: 1.0.0
"""

import asyncio
import aiohttp
import json
import time
import statistics
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple
import concurrent.futures
import websockets
import random
import string

# Internal imports
from ..utils.logger import get_structured_logger
from ..utils.performance_monitor import get_performance_manager

logger = get_structured_logger(__name__)


@dataclass
class LoadTestConfig:
    """Load test configuration"""

    name: str
    duration_seconds: int = 60
    concurrent_users: int = 10
    ramp_up_seconds: int = 10
    ramp_down_seconds: int = 10
    target_rps: Optional[int] = None  # Requests per second
    endpoints: List[Dict[str, Any]] = field(default_factory=list)
    websocket_endpoints: List[str] = field(default_factory=list)
    database_queries: List[str] = field(default_factory=list)
    think_time_min: float = 0.1
    think_time_max: float = 2.0
    timeout_seconds: int = 30
    headers: Dict[str, str] = field(default_factory=dict)
    auth_token: Optional[str] = None


@dataclass
class RequestResult:
    """Individual request result"""

    timestamp: datetime
    endpoint: str
    method: str
    status_code: int
    response_time_ms: float
    size_bytes: int
    success: bool
    error_message: Optional[str] = None
    user_id: Optional[str] = None


@dataclass
class LoadTestResults:
    """Load test results summary"""

    config: LoadTestConfig
    start_time: datetime
    end_time: datetime
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_bytes: int
    results: List[RequestResult] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        return (
            self.successful_requests / self.total_requests
            if self.total_requests > 0
            else 0.0
        )

    @property
    def duration_seconds(self) -> float:
        return (self.end_time - self.start_time).total_seconds()

    @property
    def requests_per_second(self) -> float:
        return (
            self.total_requests / self.duration_seconds
            if self.duration_seconds > 0
            else 0.0
        )


class VirtualUser:
    """Virtual user for load testing"""

    def __init__(
        self, user_id: str, config: LoadTestConfig, session: aiohttp.ClientSession
    ):
        self.user_id = user_id
        self.config = config
        self.session = session
        self.results: List[RequestResult] = []
        self._running = False

    async def run(self):
        """Run virtual user scenario"""
        self._running = True
        logger.debug("Virtual user started", user_id=self.user_id)

        try:
            while self._running:
                # Execute HTTP requests
                for endpoint_config in self.config.endpoints:
                    if not self._running:
                        break

                    await self._execute_http_request(endpoint_config)

                    # Think time between requests
                    think_time = random.uniform(
                        self.config.think_time_min, self.config.think_time_max
                    )
                    await asyncio.sleep(think_time)

                # Execute WebSocket tests
                for ws_endpoint in self.config.websocket_endpoints:
                    if not self._running:
                        break

                    await self._execute_websocket_test(ws_endpoint)

        except Exception as e:
            logger.error("Virtual user error", user_id=self.user_id, error=str(e))
        finally:
            logger.debug("Virtual user stopped", user_id=self.user_id)

    async def _execute_http_request(self, endpoint_config: Dict[str, Any]):
        """Execute HTTP request"""
        method = endpoint_config.get("method", "GET")
        url = endpoint_config["url"]
        data = endpoint_config.get("data")
        params = endpoint_config.get("params")

        start_time = time.time()
        timestamp = datetime.now(timezone.utc)

        headers = self.config.headers.copy()
        if self.config.auth_token:
            headers["Authorization"] = f"Bearer {self.config.auth_token}"

        try:
            async with self.session.request(
                method=method,
                url=url,
                json=data,
                params=params,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds),
            ) as response:
                content = await response.read()
                response_time_ms = (time.time() - start_time) * 1000

                result = RequestResult(
                    timestamp=timestamp,
                    endpoint=url,
                    method=method,
                    status_code=response.status,
                    response_time_ms=response_time_ms,
                    size_bytes=len(content),
                    success=200 <= response.status < 400,
                    user_id=self.user_id,
                )

                self.results.append(result)

        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000

            result = RequestResult(
                timestamp=timestamp,
                endpoint=url,
                method=method,
                status_code=0,
                response_time_ms=response_time_ms,
                size_bytes=0,
                success=False,
                error_message=str(e),
                user_id=self.user_id,
            )

            self.results.append(result)

    async def _execute_websocket_test(self, ws_endpoint: str):
        """Execute WebSocket test"""
        start_time = time.time()
        timestamp = datetime.now(timezone.utc)

        try:
            # Add auth token if available
            extra_headers = {}
            if self.config.auth_token:
                extra_headers["Authorization"] = f"Bearer {self.config.auth_token}"

            async with websockets.connect(
                ws_endpoint,
                extra_headers=extra_headers,
                timeout=self.config.timeout_seconds,
            ) as websocket:
                # Send test message
                test_message = {
                    "type": "test",
                    "user_id": self.user_id,
                    "timestamp": timestamp.isoformat(),
                }

                await websocket.send(json.dumps(test_message))

                # Wait for response
                response = await websocket.recv()
                response_time_ms = (time.time() - start_time) * 1000

                result = RequestResult(
                    timestamp=timestamp,
                    endpoint=ws_endpoint,
                    method="WS",
                    status_code=200,  # WebSocket doesn't have status codes
                    response_time_ms=response_time_ms,
                    size_bytes=len(response.encode("utf-8")),
                    success=True,
                    user_id=self.user_id,
                )

                self.results.append(result)

        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000

            result = RequestResult(
                timestamp=timestamp,
                endpoint=ws_endpoint,
                method="WS",
                status_code=0,
                response_time_ms=response_time_ms,
                size_bytes=0,
                success=False,
                error_message=str(e),
                user_id=self.user_id,
            )

            self.results.append(result)

    def stop(self):
        """Stop virtual user"""
        self._running = False


class LoadTestEngine:
    """Main load testing engine"""

    def __init__(self):
        self.performance_manager = get_performance_manager()
        self._active_tests: Dict[str, Dict] = {}

    async def run_load_test(self, config: LoadTestConfig) -> LoadTestResults:
        """Run a complete load test"""
        logger.info(
            "Starting load test", name=config.name, users=config.concurrent_users
        )

        start_time = datetime.now(timezone.utc)

        # Track active test
        test_id = f"{config.name}_{start_time.strftime('%Y%m%d_%H%M%S')}"
        self._active_tests[test_id] = {
            "config": config,
            "start_time": start_time,
            "users": [],
            "status": "running",
        }

        try:
            # Create HTTP session
            connector = aiohttp.TCPConnector(limit=config.concurrent_users * 2)
            timeout = aiohttp.ClientTimeout(total=config.timeout_seconds)

            async with aiohttp.ClientSession(
                connector=connector, timeout=timeout
            ) as session:
                # Create virtual users
                users = []
                for i in range(config.concurrent_users):
                    user_id = f"user_{i:04d}"
                    user = VirtualUser(user_id, config, session)
                    users.append(user)

                self._active_tests[test_id]["users"] = users

                # Start users with ramp-up
                user_tasks = []
                if config.ramp_up_seconds > 0:
                    ramp_delay = config.ramp_up_seconds / config.concurrent_users
                    for i, user in enumerate(users):
                        # Start user after delay
                        await asyncio.sleep(ramp_delay)
                        task = asyncio.create_task(user.run())
                        user_tasks.append(task)
                else:
                    # Start all users immediately
                    user_tasks = [asyncio.create_task(user.run()) for user in users]

                # Run for specified duration
                await asyncio.sleep(config.duration_seconds)

                # Stop users with ramp-down
                if config.ramp_down_seconds > 0:
                    ramp_delay = config.ramp_down_seconds / config.concurrent_users
                    for user in users:
                        user.stop()
                        await asyncio.sleep(ramp_delay)
                else:
                    # Stop all users immediately
                    for user in users:
                        user.stop()

                # Wait for all users to finish
                await asyncio.gather(*user_tasks, return_exceptions=True)

                # Collect results
                all_results = []
                for user in users:
                    all_results.extend(user.results)

                end_time = datetime.now(timezone.utc)

                # Create test results
                successful_requests = sum(1 for r in all_results if r.success)
                failed_requests = len(all_results) - successful_requests
                total_bytes = sum(r.size_bytes for r in all_results)

                results = LoadTestResults(
                    config=config,
                    start_time=start_time,
                    end_time=end_time,
                    total_requests=len(all_results),
                    successful_requests=successful_requests,
                    failed_requests=failed_requests,
                    total_bytes=total_bytes,
                    results=all_results,
                )

                self._active_tests[test_id]["status"] = "completed"
                self._active_tests[test_id]["results"] = results

                logger.info(
                    "Load test completed",
                    name=config.name,
                    total_requests=len(all_results),
                    success_rate=results.success_rate,
                    avg_rps=results.requests_per_second,
                )

                return results

        except Exception as e:
            logger.error("Load test failed", name=config.name, error=str(e))
            self._active_tests[test_id]["status"] = "failed"
            self._active_tests[test_id]["error"] = str(e)
            raise
        finally:
            # Clean up old test records
            self._cleanup_old_tests()

    def _cleanup_old_tests(self):
        """Clean up old test records"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)

        tests_to_remove = []
        for test_id, test_data in self._active_tests.items():
            if test_data["start_time"] < cutoff_time:
                tests_to_remove.append(test_id)

        for test_id in tests_to_remove:
            del self._active_tests[test_id]

    def get_active_tests(self) -> Dict[str, Dict]:
        """Get currently active tests"""
        return self._active_tests.copy()


class LoadTestAnalyzer:
    """Load test results analyzer"""

    @staticmethod
    def analyze_results(results: LoadTestResults) -> Dict[str, Any]:
        """Analyze load test results"""
        if not results.results:
            return {"error": "No results to analyze"}

        # Response time statistics
        response_times = [r.response_time_ms for r in results.results if r.success]

        response_stats = {}
        if response_times:
            response_stats = {
                "min_ms": min(response_times),
                "max_ms": max(response_times),
                "mean_ms": statistics.mean(response_times),
                "median_ms": statistics.median(response_times),
                "p90_ms": LoadTestAnalyzer._percentile(response_times, 90),
                "p95_ms": LoadTestAnalyzer._percentile(response_times, 95),
                "p99_ms": LoadTestAnalyzer._percentile(response_times, 99),
                "stdev_ms": (
                    statistics.stdev(response_times) if len(response_times) > 1 else 0
                ),
            }

        # Status code distribution
        status_codes = defaultdict(int)
        for result in results.results:
            status_codes[result.status_code] += 1

        # Error analysis
        errors = defaultdict(int)
        for result in results.results:
            if not result.success and result.error_message:
                errors[result.error_message] += 1

        # Endpoint performance
        endpoint_stats = defaultdict(
            lambda: {
                "count": 0,
                "success_count": 0,
                "total_time_ms": 0,
                "min_time_ms": float("inf"),
                "max_time_ms": 0,
            }
        )

        for result in results.results:
            key = f"{result.method} {result.endpoint}"
            stats = endpoint_stats[key]
            stats["count"] += 1
            if result.success:
                stats["success_count"] += 1
                stats["total_time_ms"] += result.response_time_ms
                stats["min_time_ms"] = min(
                    stats["min_time_ms"], result.response_time_ms
                )
                stats["max_time_ms"] = max(
                    stats["max_time_ms"], result.response_time_ms
                )

        # Calculate averages for endpoints
        endpoint_performance = {}
        for endpoint, stats in endpoint_stats.items():
            success_rate = (
                stats["success_count"] / stats["count"] if stats["count"] > 0 else 0
            )
            avg_time = (
                stats["total_time_ms"] / stats["success_count"]
                if stats["success_count"] > 0
                else 0
            )

            endpoint_performance[endpoint] = {
                "requests": stats["count"],
                "success_rate": success_rate,
                "avg_response_time_ms": avg_time,
                "min_response_time_ms": (
                    stats["min_time_ms"] if stats["min_time_ms"] != float("inf") else 0
                ),
                "max_response_time_ms": stats["max_time_ms"],
            }

        # Throughput over time (per second buckets)
        throughput_timeline = LoadTestAnalyzer._calculate_throughput_timeline(results)

        # Performance assessment
        assessment = LoadTestAnalyzer._assess_performance(results, response_stats)

        return {
            "summary": {
                "test_name": results.config.name,
                "duration_seconds": results.duration_seconds,
                "total_requests": results.total_requests,
                "successful_requests": results.successful_requests,
                "failed_requests": results.failed_requests,
                "success_rate": results.success_rate,
                "requests_per_second": results.requests_per_second,
                "total_bytes": results.total_bytes,
                "avg_bytes_per_request": (
                    results.total_bytes / results.total_requests
                    if results.total_requests > 0
                    else 0
                ),
            },
            "response_time_stats": response_stats,
            "status_code_distribution": dict(status_codes),
            "error_summary": dict(errors),
            "endpoint_performance": endpoint_performance,
            "throughput_timeline": throughput_timeline,
            "performance_assessment": assessment,
        }

    @staticmethod
    def _percentile(data: List[float], percentile: int) -> float:
        """Calculate percentile"""
        sorted_data = sorted(data)
        k = (len(sorted_data) - 1) * percentile / 100
        f = int(k)
        c = k - f

        if f + 1 < len(sorted_data):
            return sorted_data[f] + c * (sorted_data[f + 1] - sorted_data[f])
        else:
            return sorted_data[f]

    @staticmethod
    def _calculate_throughput_timeline(
        results: LoadTestResults,
    ) -> List[Dict[str, Any]]:
        """Calculate throughput over time"""
        if not results.results:
            return []

        # Group results by second
        timeline = defaultdict(lambda: {"requests": 0, "errors": 0})

        start_time = results.start_time
        for result in results.results:
            seconds_from_start = int((result.timestamp - start_time).total_seconds())
            timeline[seconds_from_start]["requests"] += 1
            if not result.success:
                timeline[seconds_from_start]["errors"] += 1

        # Convert to list
        timeline_list = []
        for second in sorted(timeline.keys()):
            data = timeline[second]
            timeline_list.append(
                {
                    "second": second,
                    "requests": data["requests"],
                    "errors": data["errors"],
                    "rps": data["requests"],
                    "error_rate": (
                        data["errors"] / data["requests"] if data["requests"] > 0 else 0
                    ),
                }
            )

        return timeline_list

    @staticmethod
    def _assess_performance(
        results: LoadTestResults, response_stats: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Assess overall performance"""
        assessment = {"overall_grade": "A", "issues": [], "recommendations": []}

        # Check success rate
        if results.success_rate < 0.95:
            assessment["overall_grade"] = "C" if results.success_rate < 0.8 else "B"
            assessment["issues"].append(f"Low success rate: {results.success_rate:.2%}")
            assessment["recommendations"].append(
                "Investigate and fix errors causing request failures"
            )

        # Check response times
        if response_stats and response_stats.get("p95_ms", 0) > 2000:
            assessment["overall_grade"] = (
                "C"
                if assessment["overall_grade"] == "A"
                else assessment["overall_grade"]
            )
            assessment["issues"].append(
                f"High P95 response time: {response_stats['p95_ms']:.1f}ms"
            )
            assessment["recommendations"].append(
                "Optimize slow endpoints and database queries"
            )

        # Check throughput
        target_rps = results.config.target_rps
        if target_rps and results.requests_per_second < target_rps * 0.8:
            assessment["overall_grade"] = (
                "B"
                if assessment["overall_grade"] == "A"
                else assessment["overall_grade"]
            )
            assessment["issues"].append(
                f"Low throughput: {results.requests_per_second:.1f} RPS (target: {target_rps})"
            )
            assessment["recommendations"].append(
                "Investigate performance bottlenecks and scale resources"
            )

        # Performance grade mapping
        if assessment["overall_grade"] == "A":
            assessment["description"] = "Excellent performance"
        elif assessment["overall_grade"] == "B":
            assessment["description"] = "Good performance with minor issues"
        else:
            assessment["description"] = "Poor performance requiring attention"

        return assessment


class LoadTestReporter:
    """Load test report generator"""

    @staticmethod
    def generate_html_report(analysis: Dict[str, Any], output_file: str):
        """Generate HTML report"""
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>NIRAJ Load Test Report</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .header { background: #f0f0f0; padding: 20px; border-radius: 5px; }
                .section { margin: 20px 0; }
                .metrics { display: flex; flex-wrap: wrap; gap: 20px; }
                .metric { background: #f9f9f9; padding: 15px; border-radius: 5px; min-width: 200px; }
                .metric h3 { margin: 0 0 10px 0; color: #333; }
                .metric .value { font-size: 24px; font-weight: bold; color: #007acc; }
                .grade-A { color: green; }
                .grade-B { color: orange; }
                .grade-C { color: red; }
                table { width: 100%; border-collapse: collapse; margin: 10px 0; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #f2f2f2; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>NIRAJ Load Test Report</h1>
                <p><strong>Test:</strong> {test_name}</p>
                <p><strong>Duration:</strong> {duration} seconds</p>
                <p><strong>Grade:</strong> <span class="grade-{grade}">{grade}</span> - {grade_description}</p>
            </div>

            <div class="section">
                <h2>Summary Metrics</h2>
                <div class="metrics">
                    <div class="metric">
                        <h3>Total Requests</h3>
                        <div class="value">{total_requests:,}</div>
                    </div>
                    <div class="metric">
                        <h3>Success Rate</h3>
                        <div class="value">{success_rate:.1%}</div>
                    </div>
                    <div class="metric">
                        <h3>RPS</h3>
                        <div class="value">{rps:.1f}</div>
                    </div>
                    <div class="metric">
                        <h3>Avg Response Time</h3>
                        <div class="value">{avg_response_time:.0f}ms</div>
                    </div>
                    <div class="metric">
                        <h3>P95 Response Time</h3>
                        <div class="value">{p95_response_time:.0f}ms</div>
                    </div>
                </div>
            </div>

            <div class="section">
                <h2>Response Time Statistics</h2>
                <table>
                    <tr><th>Metric</th><th>Value (ms)</th></tr>
                    <tr><td>Minimum</td><td>{min_time:.1f}</td></tr>
                    <tr><td>Average</td><td>{avg_time:.1f}</td></tr>
                    <tr><td>Median</td><td>{median_time:.1f}</td></tr>
                    <tr><td>P90</td><td>{p90_time:.1f}</td></tr>
                    <tr><td>P95</td><td>{p95_time:.1f}</td></tr>
                    <tr><td>P99</td><td>{p99_time:.1f}</td></tr>
                    <tr><td>Maximum</td><td>{max_time:.1f}</td></tr>
                </table>
            </div>

            {endpoint_table}

            {issues_section}

            {recommendations_section}
        </body>
        </html>
        """

        # Extract data for template
        summary = analysis["summary"]
        response_stats = analysis.get("response_time_stats", {})
        assessment = analysis.get("performance_assessment", {})

        # Build endpoint performance table
        endpoint_table = ""
        if analysis.get("endpoint_performance"):
            endpoint_table = """
            <div class="section">
                <h2>Endpoint Performance</h2>
                <table>
                    <tr><th>Endpoint</th><th>Requests</th><th>Success Rate</th><th>Avg Time (ms)</th></tr>
            """
            for endpoint, stats in analysis["endpoint_performance"].items():
                endpoint_table += f"""
                    <tr>
                        <td>{endpoint}</td>
                        <td>{stats['requests']:,}</td>
                        <td>{stats['success_rate']:.1%}</td>
                        <td>{stats['avg_response_time_ms']:.1f}</td>
                    </tr>
                """
            endpoint_table += "</table></div>"

        # Build issues section
        issues_section = ""
        if assessment.get("issues"):
            issues_section = '<div class="section"><h2>Issues Found</h2><ul>'
            for issue in assessment["issues"]:
                issues_section += f"<li>{issue}</li>"
            issues_section += "</ul></div>"

        # Build recommendations section
        recommendations_section = ""
        if assessment.get("recommendations"):
            recommendations_section = (
                '<div class="section"><h2>Recommendations</h2><ul>'
            )
            for rec in assessment["recommendations"]:
                recommendations_section += f"<li>{rec}</li>"
            recommendations_section += "</ul></div>"

        # Fill template
        html_content = html_template.format(
            test_name=summary.get("test_name", "Unknown"),
            duration=summary.get("duration_seconds", 0),
            grade=assessment.get("overall_grade", "N/A"),
            grade_description=assessment.get("description", "No assessment"),
            total_requests=summary.get("total_requests", 0),
            success_rate=summary.get("success_rate", 0),
            rps=summary.get("requests_per_second", 0),
            avg_response_time=response_stats.get("mean_ms", 0),
            p95_response_time=response_stats.get("p95_ms", 0),
            min_time=response_stats.get("min_ms", 0),
            avg_time=response_stats.get("mean_ms", 0),
            median_time=response_stats.get("median_ms", 0),
            p90_time=response_stats.get("p90_ms", 0),
            p95_time=response_stats.get("p95_ms", 0),
            p99_time=response_stats.get("p99_ms", 0),
            max_time=response_stats.get("max_ms", 0),
            endpoint_table=endpoint_table,
            issues_section=issues_section,
            recommendations_section=recommendations_section,
        )

        # Write to file
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        logger.info("HTML report generated", output_file=output_file)


class LoadTestFramework:
    """Main load testing framework"""

    def __init__(self):
        self.engine = LoadTestEngine()
        self.analyzer = LoadTestAnalyzer()
        self.reporter = LoadTestReporter()

    async def run_comprehensive_test(
        self, base_url: str, auth_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Run comprehensive load test suite"""
        logger.info("Starting comprehensive load test suite", base_url=base_url)

        # Define test scenarios
        scenarios = [
            # Light load test
            LoadTestConfig(
                name="light_load",
                duration_seconds=60,
                concurrent_users=5,
                endpoints=[
                    {"method": "GET", "url": f"{base_url}/api/v1/system/status"},
                    {"method": "GET", "url": f"{base_url}/api/v1/portfolio"},
                    {"method": "GET", "url": f"{base_url}/api/v1/strategies"},
                ],
                auth_token=auth_token,
            ),
            # Medium load test
            LoadTestConfig(
                name="medium_load",
                duration_seconds=120,
                concurrent_users=20,
                target_rps=50,
                endpoints=[
                    {"method": "GET", "url": f"{base_url}/api/v1/system/status"},
                    {"method": "GET", "url": f"{base_url}/api/v1/portfolio"},
                    {"method": "GET", "url": f"{base_url}/api/v1/strategies"},
                    {"method": "GET", "url": f"{base_url}/api/v1/trades"},
                    {"method": "GET", "url": f"{base_url}/api/v1/ai/predictions"},
                ],
                auth_token=auth_token,
            ),
            # Heavy load test
            LoadTestConfig(
                name="heavy_load",
                duration_seconds=180,
                concurrent_users=50,
                target_rps=100,
                ramp_up_seconds=30,
                ramp_down_seconds=30,
                endpoints=[
                    {"method": "GET", "url": f"{base_url}/api/v1/system/status"},
                    {"method": "GET", "url": f"{base_url}/api/v1/portfolio"},
                    {"method": "GET", "url": f"{base_url}/api/v1/strategies"},
                    {"method": "GET", "url": f"{base_url}/api/v1/trades"},
                    {"method": "GET", "url": f"{base_url}/api/v1/ai/predictions"},
                    {
                        "method": "POST",
                        "url": f"{base_url}/api/v1/strategies",
                        "data": {"name": "test_strategy", "type": "test"},
                    },
                ],
                websocket_endpoints=[f'{base_url.replace("http", "ws")}/ws'],
                auth_token=auth_token,
            ),
        ]

        all_results = {}

        # Run each scenario
        for scenario in scenarios:
            try:
                results = await self.engine.run_load_test(scenario)
                analysis = self.analyzer.analyze_results(results)
                all_results[scenario.name] = {"results": results, "analysis": analysis}

                # Generate individual report
                report_file = f"load_test_report_{scenario.name}.html"
                self.reporter.generate_html_report(analysis, report_file)

            except Exception as e:
                logger.error(
                    "Load test scenario failed", scenario=scenario.name, error=str(e)
                )
                all_results[scenario.name] = {"error": str(e)}

        # Generate summary report
        summary_analysis = self._generate_summary_analysis(all_results)
        self.reporter.generate_html_report(
            summary_analysis, "load_test_summary_report.html"
        )

        logger.info("Comprehensive load test suite completed")
        return all_results

    def _generate_summary_analysis(self, all_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary analysis across all test scenarios"""
        summary = {
            "summary": {
                "test_name": "Comprehensive Load Test Suite",
                "total_scenarios": len(all_results),
                "successful_scenarios": 0,
                "failed_scenarios": 0,
                "total_requests": 0,
                "total_duration_seconds": 0,
                "overall_success_rate": 0,
                "avg_requests_per_second": 0,
            },
            "scenario_results": [],
            "performance_assessment": {
                "overall_grade": "A",
                "issues": [],
                "recommendations": [],
                "description": "All scenarios completed successfully",
            },
        }

        total_requests = 0
        total_successful = 0
        total_duration = 0
        total_rps = 0

        for scenario_name, scenario_data in all_results.items():
            if "error" in scenario_data:
                summary["summary"]["failed_scenarios"] += 1
                summary["scenario_results"].append(
                    {
                        "name": scenario_name,
                        "status": "failed",
                        "error": scenario_data["error"],
                    }
                )
                continue

            summary["summary"]["successful_scenarios"] += 1

            analysis = scenario_data["analysis"]
            scenario_summary = analysis["summary"]

            total_requests += scenario_summary["total_requests"]
            total_successful += scenario_summary["successful_requests"]
            total_duration += scenario_summary["duration_seconds"]
            total_rps += scenario_summary["requests_per_second"]

            summary["scenario_results"].append(
                {
                    "name": scenario_name,
                    "status": "success",
                    "requests": scenario_summary["total_requests"],
                    "success_rate": scenario_summary["success_rate"],
                    "rps": scenario_summary["requests_per_second"],
                    "grade": analysis["performance_assessment"]["overall_grade"],
                }
            )

        # Calculate overall metrics
        if total_requests > 0:
            summary["summary"]["total_requests"] = total_requests
            summary["summary"]["overall_success_rate"] = (
                total_successful / total_requests
            )
            summary["summary"]["total_duration_seconds"] = total_duration
            summary["summary"]["avg_requests_per_second"] = (
                total_rps / len(summary["scenario_results"])
                if summary["scenario_results"]
                else 0
            )

        # Assess overall performance
        if summary["summary"]["failed_scenarios"] > 0:
            summary["performance_assessment"]["overall_grade"] = "C"
            summary["performance_assessment"]["description"] = "Some scenarios failed"
            summary["performance_assessment"]["issues"].append(
                f"{summary['summary']['failed_scenarios']} scenarios failed"
            )

        if summary["summary"]["overall_success_rate"] < 0.95:
            summary["performance_assessment"]["overall_grade"] = (
                "B"
                if summary["performance_assessment"]["overall_grade"] == "A"
                else summary["performance_assessment"]["overall_grade"]
            )
            summary["performance_assessment"]["issues"].append(
                f"Low overall success rate: {summary['summary']['overall_success_rate']:.2%}"
            )

        return summary


# Global load test framework instance
_load_test_framework: Optional[LoadTestFramework] = None


def get_load_test_framework() -> LoadTestFramework:
    """Get global load test framework instance"""
    global _load_test_framework
    if _load_test_framework is None:
        _load_test_framework = LoadTestFramework()
    return _load_test_framework


# Utility functions for quick testing
async def quick_load_test(
    base_url: str, concurrent_users: int = 10, duration_seconds: int = 60
) -> Dict[str, Any]:
    """Run a quick load test"""
    framework = get_load_test_framework()

    config = LoadTestConfig(
        name="quick_test",
        duration_seconds=duration_seconds,
        concurrent_users=concurrent_users,
        endpoints=[
            {"method": "GET", "url": f"{base_url}/api/v1/system/status"},
        ],
    )

    results = await framework.engine.run_load_test(config)
    analysis = framework.analyzer.analyze_results(results)

    return {"results": results, "analysis": analysis}


# Export all public classes and functions
__all__ = [
    "LoadTestFramework",
    "LoadTestEngine",
    "LoadTestAnalyzer",
    "LoadTestReporter",
    "LoadTestConfig",
    "LoadTestResults",
    "RequestResult",
    "VirtualUser",
    "get_load_test_framework",
    "quick_load_test",
]
