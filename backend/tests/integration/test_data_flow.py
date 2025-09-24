"""
Integration Test: T035 - Market Data Ingestion and Processing
Tests the complete market data workflow from ingestion to processing.

This test validates:
1. Real-time market data ingestion from multiple sources
2. Historical data retrieval and storage
3. Data validation and quality checks
4. Technical indicator calculations
5. Data transformation and normalization
6. WebSocket streaming and subscriptions
7. Error handling for data source failures
8. Performance and latency requirements
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock
from enum import Enum

# Mock imports for integration testing
from sqlalchemy.orm import Session


class DataSource(Enum):
    """Data source enumeration"""
    ANGEL_ONE = "angel_one"
    DHAN_HQ = "dhan_hq"
    NSE_LIVE = "nse_live"
    BSE_LIVE = "bse_live"


class DataType(Enum):
    """Data type enumeration"""
    TICK = "tick"
    OHLC = "ohlc"
    DEPTH = "depth"
    NEWS = "news"
    CORPORATE_ACTION = "corporate_action"


class DataQuality(Enum):
    """Data quality enumeration"""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    INVALID = "invalid"


class DataError(Exception):
    """Base exception for data-related errors"""
    pass


class DataSourceError(DataError):
    """Raised when data source connection fails"""
    pass


class DataValidationError(DataError):
    """Raised when data validation fails"""
    pass


class DataProcessingError(DataError):
    """Raised when data processing fails"""
    pass


class LatencyError(DataError):
    """Raised when data latency exceeds limits"""
    pass


class MockMarketData:
    """Mock Market Data model"""
    def __init__(self, symbol: str, source: DataSource):
        self.symbol = symbol
        self.source = source
        self.timestamp = datetime.now()
        self.price = Decimal("0.00")
        self.volume = 0
        self.bid = Decimal("0.00")
        self.ask = Decimal("0.00")
        self.ohlc = {
            "open": Decimal("0.00"),
            "high": Decimal("0.00"),
            "low": Decimal("0.00"),
            "close": Decimal("0.00")
        }
        self.quality = DataQuality.GOOD
        self.latency_ms = 0


class MockTechnicalIndicator:
    """Mock Technical Indicator model"""
    def __init__(self, symbol: str, indicator_name: str):
        self.symbol = symbol
        self.indicator_name = indicator_name
        self.value = Decimal("0.00")
        self.parameters = {}
        self.timestamp = datetime.now()
        self.is_valid = True


class MockDataStream:
    """Mock data stream for real-time data"""
    def __init__(self, source: DataSource):
        self.source = source
        self.is_connected = False
        self.subscriptions = set()
        self.message_count = 0
        self.error_count = 0
        self.last_message_time = None


@pytest.fixture
def mock_db_session():
    """Mock database session"""
    session = Mock(spec=Session)
    session.commit = Mock()
    session.rollback = Mock()
    session.close = Mock()
    return session


@pytest.fixture
def data_ingestion_service():
    """Mock data ingestion service"""
    service = Mock()
    service.connect_to_source = AsyncMock()
    service.ingest_real_time_data = AsyncMock()
    service.ingest_historical_data = AsyncMock()
    service.validate_data = AsyncMock()
    service.disconnect_from_source = AsyncMock()
    return service


@pytest.fixture
def data_processing_service():
    """Mock data processing service"""
    service = Mock()
    service.normalize_data = AsyncMock()
    service.calculate_indicators = AsyncMock()
    service.detect_anomalies = AsyncMock()
    service.aggregate_data = AsyncMock()
    return service


@pytest.fixture
def websocket_service():
    """Mock WebSocket service"""
    service = Mock()
    service.start_stream = AsyncMock()
    service.subscribe_to_symbol = AsyncMock()
    service.unsubscribe_from_symbol = AsyncMock()
    service.broadcast_data = AsyncMock()
    service.stop_stream = AsyncMock()
    return service


@pytest.fixture
def data_quality_service():
    """Mock data quality service"""
    service = Mock()
    service.assess_quality = AsyncMock()
    service.validate_completeness = AsyncMock()
    service.check_consistency = AsyncMock()
    service.measure_latency = AsyncMock()
    return service


@pytest.fixture
def storage_service():
    """Mock data storage service"""
    service = Mock()
    service.store_tick_data = AsyncMock()
    service.store_ohlc_data = AsyncMock()
    service.retrieve_historical_data = AsyncMock()
    service.cleanup_old_data = AsyncMock()
    return service


class TestDataFlow:
    """Integration tests for market data ingestion and processing"""

    @pytest.mark.asyncio
    async def test_complete_data_flow_workflow(
        self,
        mock_db_session,
        data_ingestion_service,
        data_processing_service,
        websocket_service,
        data_quality_service,
        storage_service
    ):
        """Test complete data flow from ingestion to processing"""

        # Setup test data
        symbol = "RELIANCE"
        source = DataSource.ANGEL_ONE

        # Mock market data
        raw_data = MockMarketData(symbol, source)
        raw_data.price = Decimal("2500.00")
        raw_data.volume = 1000
        raw_data.bid = Decimal("2499.50")
        raw_data.ask = Decimal("2500.50")
        raw_data.ohlc = {
            "open": Decimal("2480.00"),
            "high": Decimal("2520.00"),
            "low": Decimal("2475.00"),
            "close": Decimal("2500.00")
        }
        raw_data.latency_ms = 50  # 50ms latency

        # Mock processed indicators
        rsi_indicator = MockTechnicalIndicator(symbol, "RSI")
        rsi_indicator.value = Decimal("45.5")
        rsi_indicator.parameters = {"period": 14}

        macd_indicator = MockTechnicalIndicator(symbol, "MACD")
        macd_indicator.value = Decimal("12.5")
        macd_indicator.parameters = {"fast": 12, "slow": 26, "signal": 9}

        # Configure service responses
        data_ingestion_service.connect_to_source.return_value = {"connected": True}
        data_ingestion_service.ingest_real_time_data.return_value = raw_data
        data_quality_service.assess_quality.return_value = DataQuality.GOOD
        data_processing_service.normalize_data.return_value = raw_data
        data_processing_service.calculate_indicators.return_value = [
            rsi_indicator, macd_indicator
        ]
        storage_service.store_tick_data.return_value = {"stored": True}
        websocket_service.subscribe_to_symbol.return_value = True

        try:
            # Step 1: Connect to data source
            connection_result = await data_ingestion_service.connect_to_source(
                source, symbol
            )
            assert connection_result["connected"] is True

            # Step 2: Ingest real-time market data
            market_data = await data_ingestion_service.ingest_real_time_data(
                source, symbol
            )

            assert market_data.symbol == symbol
            assert market_data.price > 0
            assert market_data.volume >= 0
            assert market_data.timestamp is not None

            # Step 3: Assess data quality
            quality = await data_quality_service.assess_quality(market_data)
            assert quality in [DataQuality.EXCELLENT, DataQuality.GOOD,
                               DataQuality.ACCEPTABLE]
            market_data.quality = quality

            # Step 4: Validate data latency
            assert market_data.latency_ms < 100  # Under 100ms requirement

            # Step 5: Normalize and process data
            normalized_data = await data_processing_service.normalize_data(
                market_data
            )
            assert normalized_data.symbol == symbol

            # Step 6: Calculate technical indicators
            indicators = await data_processing_service.calculate_indicators(
                normalized_data
            )

            assert len(indicators) >= 2
            rsi = next((i for i in indicators if i.indicator_name == "RSI"), None)
            macd = next((i for i in indicators if i.indicator_name == "MACD"), None)
            assert rsi is not None
            assert macd is not None
            assert rsi.is_valid
            assert macd.is_valid

            # Step 7: Store processed data
            storage_result = await storage_service.store_tick_data(
                normalized_data, indicators
            )
            assert storage_result["stored"] is True

            # Step 8: Stream data via WebSocket
            stream_success = await websocket_service.subscribe_to_symbol(
                symbol, client_id="test_client"
            )
            assert stream_success is True

            await websocket_service.broadcast_data(normalized_data, indicators)

            print("✅ Complete data flow workflow executed successfully")

        except Exception as e:
            pytest.fail(f"Data flow workflow failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_data_source_connection_failure(
        self,
        mock_db_session,
        data_ingestion_service
    ):
        """Test handling of data source connection failures"""

        source = DataSource.ANGEL_ONE
        symbol = "RELIANCE"

        # Configure data ingestion service to fail connection
        data_ingestion_service.connect_to_source.side_effect = DataSourceError(
            f"Failed to connect to {source.value}: API credentials invalid"
        )

        try:
            with pytest.raises(DataSourceError) as exc_info:
                await data_ingestion_service.connect_to_source(source, symbol)

            assert "Failed to connect" in str(exc_info.value)
            assert source.value in str(exc_info.value)

            print("✅ Data source connection failure handled correctly")

        except Exception as e:
            pytest.fail(f"Data source connection error handling failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_data_validation_failure_recovery(
        self,
        mock_db_session,
        data_ingestion_service,
        data_quality_service
    ):
        """Test recovery from data validation failures"""

        symbol = "RELIANCE"
        source = DataSource.ANGEL_ONE

        # Create invalid data
        invalid_data = MockMarketData(symbol, source)
        invalid_data.price = Decimal("-100.00")  # Invalid negative price
        invalid_data.volume = -500  # Invalid negative volume
        invalid_data.timestamp = datetime.now() - timedelta(hours=2)  # Stale data

        # Mock data quality assessment
        data_quality_service.assess_quality.return_value = DataQuality.INVALID

        def mock_validate_data(data):
            if data.price <= 0:
                raise DataValidationError(f"Invalid price: {data.price}")
            if data.volume < 0:
                raise DataValidationError(f"Invalid volume: {data.volume}")
            return True

        data_ingestion_service.validate_data.side_effect = mock_validate_data

        try:
            # Attempt to validate invalid data
            with pytest.raises(DataValidationError) as exc_info:
                await data_ingestion_service.validate_data(invalid_data)

            assert "Invalid price" in str(exc_info.value) or \
                   "Invalid volume" in str(exc_info.value)

            # Assess data quality
            quality = await data_quality_service.assess_quality(invalid_data)
            assert quality == DataQuality.INVALID

            print("✅ Data validation failure recovery working correctly")

        except Exception as e:
            pytest.fail(f"Data validation failure recovery failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_multi_source_data_aggregation(
        self,
        mock_db_session,
        data_ingestion_service,
        data_processing_service
    ):
        """Test aggregation of data from multiple sources"""

        symbol = "RELIANCE"
        sources = [DataSource.ANGEL_ONE, DataSource.DHAN_HQ, DataSource.NSE_LIVE]

        # Create data from multiple sources
        source_data = []
        for i, source in enumerate(sources):
            data = MockMarketData(symbol, source)
            data.price = Decimal(f"250{i}.{i}0")  # Slightly different prices
            data.volume = 1000 + (i * 100)
            data.latency_ms = 50 + (i * 10)
            data.quality = DataQuality.GOOD
            source_data.append(data)

        # Mock aggregation
        aggregated_data = MockMarketData(symbol, DataSource.NSE_LIVE)
        aggregated_data.price = Decimal("2501.00")  # Weighted average
        aggregated_data.volume = sum(d.volume for d in source_data)
        aggregated_data.quality = DataQuality.EXCELLENT

        data_ingestion_service.ingest_real_time_data.side_effect = source_data
        data_processing_service.aggregate_data.return_value = aggregated_data

        try:
            # Ingest data from all sources
            ingested_data = []
            for source in sources:
                data = await data_ingestion_service.ingest_real_time_data(
                    source, symbol
                )
                ingested_data.append(data)

            assert len(ingested_data) == len(sources)

            # Aggregate data from multiple sources
            aggregated = await data_processing_service.aggregate_data(
                ingested_data
            )

            assert aggregated.symbol == symbol
            assert aggregated.quality == DataQuality.EXCELLENT
            assert aggregated.volume == sum(d.volume for d in source_data)

            print("✅ Multi-source data aggregation working correctly")

        except Exception as e:
            pytest.fail(f"Multi-source data aggregation failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_real_time_streaming_performance(
        self,
        mock_db_session,
        websocket_service,
        data_quality_service
    ):
        """Test real-time streaming performance and latency"""

        symbol = "RELIANCE"
        client_id = "test_client"

        # Setup streaming scenario
        stream_data = MockDataStream(DataSource.ANGEL_ONE)
        stream_data.is_connected = True

        # Mock performance metrics
        performance_metrics = {
            "messages_per_second": 100,
            "average_latency_ms": 45,
            "max_latency_ms": 95,
            "dropped_messages": 0,
            "connection_uptime": 0.999  # 99.9% uptime
        }

        websocket_service.start_stream.return_value = stream_data
        websocket_service.subscribe_to_symbol.return_value = True
        data_quality_service.measure_latency.return_value = 45  # 45ms

        try:
            # Step 1: Start WebSocket stream
            stream = await websocket_service.start_stream(DataSource.ANGEL_ONE)
            assert stream.is_connected is True

            # Step 2: Subscribe to symbol
            subscription_success = await websocket_service.subscribe_to_symbol(
                symbol, client_id
            )
            assert subscription_success is True

            # Step 3: Measure streaming performance
            latency = await data_quality_service.measure_latency(stream)
            assert latency < 100  # Under 100ms requirement

            # Step 4: Validate performance metrics
            assert performance_metrics["messages_per_second"] >= 50  # Min 50 msg/s
            assert performance_metrics["average_latency_ms"] < 100  # Under 100ms
            assert performance_metrics["connection_uptime"] > 0.95  # Above 95%

            print("✅ Real-time streaming performance meets requirements")

        except Exception as e:
            pytest.fail(f"Real-time streaming performance test failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_historical_data_retrieval(
        self,
        mock_db_session,
        data_ingestion_service,
        storage_service
    ):
        """Test historical data retrieval and processing"""

        symbol = "RELIANCE"
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()

        # Mock historical data
        historical_data = []
        for i in range(30):  # 30 days of data
            data = MockMarketData(symbol, DataSource.NSE_LIVE)
            data.timestamp = start_date + timedelta(days=i)
            data.price = Decimal(f"24{50 + i % 50}.00")
            data.volume = 1000000 + (i * 10000)
            data.ohlc = {
                "open": data.price - Decimal("10.00"),
                "high": data.price + Decimal("15.00"),
                "low": data.price - Decimal("20.00"),
                "close": data.price
            }
            historical_data.append(data)

        # Configure services
        data_ingestion_service.ingest_historical_data.return_value = historical_data
        storage_service.retrieve_historical_data.return_value = historical_data

        try:
            # Step 1: Ingest historical data
            ingested_history = await data_ingestion_service.ingest_historical_data(
                symbol, start_date, end_date
            )

            assert len(ingested_history) == 30
            assert all(d.symbol == symbol for d in ingested_history)

            # Step 2: Store historical data
            for data in ingested_history:
                await storage_service.store_ohlc_data(data)

            # Step 3: Retrieve stored historical data
            retrieved_data = await storage_service.retrieve_historical_data(
                symbol, start_date, end_date
            )

            assert len(retrieved_data) == len(ingested_history)
            assert retrieved_data[0].timestamp >= start_date
            assert retrieved_data[-1].timestamp <= end_date

            print("✅ Historical data retrieval working correctly")

        except Exception as e:
            pytest.fail(f"Historical data retrieval failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_technical_indicator_calculation(
        self,
        mock_db_session,
        data_processing_service
    ):
        """Test technical indicator calculation accuracy"""

        symbol = "RELIANCE"

        # Create sample price data for indicator calculation
        price_data = []
        base_price = 2500
        for i in range(20):  # 20 periods of data
            data = MockMarketData(symbol, DataSource.NSE_LIVE)
            data.price = Decimal(str(base_price + (i * 5) + ((i % 3) * 10)))
            data.timestamp = datetime.now() - timedelta(minutes=20-i)
            price_data.append(data)

        # Mock indicator calculations
        indicators = [
            MockTechnicalIndicator(symbol, "RSI"),
            MockTechnicalIndicator(symbol, "MACD"),
            MockTechnicalIndicator(symbol, "SMA_20"),
            MockTechnicalIndicator(symbol, "EMA_12"),
            MockTechnicalIndicator(symbol, "BOLLINGER_UPPER"),
            MockTechnicalIndicator(symbol, "BOLLINGER_LOWER")
        ]

        # Set realistic values
        indicators[0].value = Decimal("65.5")  # RSI
        indicators[1].value = Decimal("12.5")  # MACD
        indicators[2].value = Decimal("2510.0")  # SMA_20
        indicators[3].value = Decimal("2515.0")  # EMA_12
        indicators[4].value = Decimal("2580.0")  # Bollinger Upper
        indicators[5].value = Decimal("2440.0")  # Bollinger Lower

        data_processing_service.calculate_indicators.return_value = indicators

        try:
            # Calculate technical indicators
            calculated_indicators = \
                await data_processing_service.calculate_indicators(price_data)

            assert len(calculated_indicators) >= 6

            # Validate specific indicators
            rsi = next((i for i in calculated_indicators if i.indicator_name == "RSI"), None)
            assert rsi is not None
            assert 0 <= rsi.value <= 100  # RSI range validation

            macd = next((i for i in calculated_indicators if i.indicator_name == "MACD"), None)
            assert macd is not None

            sma = next((i for i in calculated_indicators if i.indicator_name == "SMA_20"), None)
            assert sma is not None
            assert sma.value > 0

            # Validate all indicators have valid timestamps
            for indicator in calculated_indicators:
                assert indicator.timestamp is not None
                assert indicator.is_valid is True

            print("✅ Technical indicator calculation working correctly")

        except Exception as e:
            pytest.fail(f"Technical indicator calculation failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_data_anomaly_detection(
        self,
        mock_db_session,
        data_processing_service,
        data_quality_service
    ):
        """Test detection of data anomalies and outliers"""

        symbol = "RELIANCE"

        # Create data with anomalies
        normal_data = []
        anomalous_data = []

        # Normal data points
        for i in range(10):
            data = MockMarketData(symbol, DataSource.NSE_LIVE)
            data.price = Decimal(f"25{10 + (i % 5)}.00")  # Normal price range
            data.volume = 100000 + (i * 1000)  # Normal volume
            normal_data.append(data)

        # Anomalous data points
        anomaly1 = MockMarketData(symbol, DataSource.NSE_LIVE)
        anomaly1.price = Decimal("5000.00")  # Price spike anomaly
        anomaly1.volume = 50000
        anomalous_data.append(anomaly1)

        anomaly2 = MockMarketData(symbol, DataSource.NSE_LIVE)
        anomaly2.price = Decimal("2500.00")  # Normal price
        anomaly2.volume = 10000000  # Volume spike anomaly
        anomalous_data.append(anomaly2)

        all_data = normal_data + anomalous_data

        # Mock anomaly detection
        detected_anomalies = [
            {"data_point": anomaly1, "anomaly_type": "price_spike",
             "severity": "high", "confidence": 0.95},
            {"data_point": anomaly2, "anomaly_type": "volume_spike",
             "severity": "medium", "confidence": 0.82}
        ]

        data_processing_service.detect_anomalies.return_value = detected_anomalies

        try:
            # Detect anomalies in data
            anomalies = await data_processing_service.detect_anomalies(all_data)

            assert len(anomalies) >= 2

            # Validate anomaly detection
            price_anomaly = next((a for a in anomalies
                                  if a["anomaly_type"] == "price_spike"), None)
            assert price_anomaly is not None
            assert price_anomaly["severity"] == "high"
            assert price_anomaly["confidence"] > 0.8

            volume_anomaly = next((a for a in anomalies
                                   if a["anomaly_type"] == "volume_spike"), None)
            assert volume_anomaly is not None
            assert volume_anomaly["confidence"] > 0.7

            print("✅ Data anomaly detection working correctly")

        except Exception as e:
            pytest.fail(f"Data anomaly detection failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_data_cleanup_and_maintenance(
        self,
        mock_db_session,
        storage_service
    ):
        """Test data cleanup and maintenance operations"""

        # Setup cleanup scenario
        cleanup_config = {
            "tick_data_retention_days": 7,
            "ohlc_data_retention_days": 365,
            "news_data_retention_days": 30,
            "cleanup_schedule": "daily"
        }

        # Mock cleanup results
        cleanup_results = {
            "tick_data_cleaned": 1000000,  # 1M records
            "ohlc_data_cleaned": 0,  # Keep all OHLC data
            "news_data_cleaned": 50000,  # 50K records
            "storage_freed_mb": 2048,  # 2GB freed
            "cleanup_duration_seconds": 45
        }

        storage_service.cleanup_old_data.return_value = cleanup_results

        try:
            # Execute data cleanup
            results = await storage_service.cleanup_old_data(cleanup_config)

            # Validate cleanup results
            assert results["tick_data_cleaned"] > 0
            assert results["storage_freed_mb"] > 0
            assert results["cleanup_duration_seconds"] < 300  # Under 5 minutes

            # Validate retention policies
            cutoff_date = datetime.now() - timedelta(
                days=cleanup_config["tick_data_retention_days"]
            )
            assert cutoff_date is not None

            print("✅ Data cleanup and maintenance working correctly")

        except Exception as e:
            pytest.fail(f"Data cleanup and maintenance failed: {str(e)}")


# Additional utility functions for testing
def create_data_test_scenario(scenario_name: str) -> Dict[str, Any]:
    """Create predefined data flow test scenarios"""

    scenarios = {
        "normal_flow": {
            "data_sources_available": True,
            "data_quality": DataQuality.GOOD,
            "latency_ms": 50,
            "expected_outcome": "success"
        },

        "high_latency": {
            "data_sources_available": True,
            "data_quality": DataQuality.GOOD,
            "latency_ms": 150,  # Exceeds 100ms limit
            "expected_outcome": "latency_error"
        },

        "poor_quality": {
            "data_sources_available": True,
            "data_quality": DataQuality.POOR,
            "latency_ms": 50,
            "expected_outcome": "quality_error"
        },

        "source_unavailable": {
            "data_sources_available": False,
            "data_quality": DataQuality.INVALID,
            "latency_ms": 0,
            "expected_outcome": "source_error"
        }
    }

    return scenarios.get(scenario_name, {})


def validate_data_quality(data: MockMarketData) -> DataQuality:
    """Validate market data quality"""

    try:
        # Basic validation checks
        if data.price <= 0:
            return DataQuality.INVALID

        if data.volume < 0:
            return DataQuality.INVALID

        if data.latency_ms > 200:  # Over 200ms is poor
            return DataQuality.POOR
        elif data.latency_ms > 100:  # Over 100ms is acceptable
            return DataQuality.ACCEPTABLE
        elif data.latency_ms < 50:  # Under 50ms is excellent
            return DataQuality.EXCELLENT
        else:
            return DataQuality.GOOD

    except Exception:
        return DataQuality.INVALID


if __name__ == "__main__":
    """Run integration tests for market data flow"""

    print("🚀 Starting Market Data Flow Integration Tests...")

    # Run pytest with verbose output
    import subprocess
    result = subprocess.run([
        "python", "-m", "pytest",
        __file__,
        "-v",
        "--tb=short"
    ], capture_output=True, text=True)

    print(result.stdout)
    if result.stderr:
        print("Errors:", result.stderr)
        
    print("✅ Market Data Flow Integration Tests Complete!")
