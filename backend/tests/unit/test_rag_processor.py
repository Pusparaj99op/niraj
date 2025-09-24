"""
Test suite for RAG Processor

This module contains comprehensive tests for the RAG processor functionality
including unit tests, integration tests, and performance tests.
"""

import pytest
import asyncio
import tempfile
import os
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from typing import List, Dict, Any

from src.ai.rag_processor import (
    RAGProcessor, VectorDatabase, KnowledgeItem, KnowledgeType,
    RetrievalQuery, RetrievalMode, RagProcessorError, VectorDatabaseError,
    EmbeddingError, RetrievalError, IngestionError
)
from src.ai.gemma3_integration import AnalysisRequest, AnalysisType


class TestVectorDatabase:
    """Test cases for VectorDatabase class"""

    def setup_method(self):
        """Setup test database"""
        self.test_db_fd, self.test_db_path = tempfile.mkstemp(suffix='.db')
        os.close(self.test_db_fd)
        self.db = VectorDatabase(self.test_db_path)

    def teardown_method(self):
        """Cleanup test database"""
        if hasattr(self, 'db'):
            self.db.close()
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)

    def test_database_initialization(self):
        """Test database initialization"""
        assert self.db.connection is not None

        # Check if tables exist
        cursor = self.db.connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = [row[0] for row in cursor.fetchall()]

        expected_tables = ['knowledge_items', 'embeddings', 'search_index']
        for table in expected_tables:
            assert table in tables

    def test_store_and_retrieve_item(self):
        """Test storing and retrieving knowledge items"""
        # Create test knowledge item
        item = KnowledgeItem(
            id="test_001",
            content="Test market analysis content",
            knowledge_type=KnowledgeType.MARKET_NEWS,
            title="Test Analysis",
            symbols=["AAPL", "GOOGL"],
            sectors=["Technology"],
            tags=["bullish", "earnings"],
            metadata={"analyst": "test", "confidence": 0.85}
        )

        # Create test embedding
        embedding = [0.1, 0.2, 0.3, 0.4, 0.5]

        # Store item
        result = self.db.store_item(item, embedding)
        assert result is True

        # Verify item count
        assert self.db.get_item_count() == 1

    def test_similarity_search(self):
        """Test similarity search functionality"""
        # Store multiple test items
        items_and_embeddings = [
            (KnowledgeItem(
                id="search_001",
                content="Apple stock shows bullish momentum",
                knowledge_type=KnowledgeType.TECHNICAL_ANALYSIS,
                symbols=["AAPL"],
                sectors=["Technology"]
            ), [0.9, 0.1, 0.0, 0.0, 0.0]),
            (KnowledgeItem(
                id="search_002",
                content="Google earnings beat expectations",
                knowledge_type=KnowledgeType.MARKET_NEWS,
                symbols=["GOOGL"],
                sectors=["Technology"]
            ), [0.1, 0.9, 0.0, 0.0, 0.0]),
            (KnowledgeItem(
                id="search_003",
                content="Oil prices surge on supply concerns",
                knowledge_type=KnowledgeType.MARKET_NEWS,
                symbols=["OIL"],
                sectors=["Energy"]
            ), [0.0, 0.0, 0.9, 0.1, 0.0])
        ]

        for item, embedding in items_and_embeddings:
            self.db.store_item(item, embedding)

        # Test similarity search
        query_embedding = [0.8, 0.2, 0.0, 0.0, 0.0]  # Similar to first item
        results = self.db.similarity_search(query_embedding, top_k=2)

        assert len(results) == 2
        # First result should be most similar (search_001)
        assert results[0][0].id == "search_001"
        assert results[0][1] > results[1][1]  # Higher similarity score

    def test_similarity_search_with_filters(self):
        """Test similarity search with filters"""
        # Store items with different knowledge types and symbols
        items = [
            (KnowledgeItem(
                id="filter_001",
                content="Apple technical analysis",
                knowledge_type=KnowledgeType.TECHNICAL_ANALYSIS,
                symbols=["AAPL"]
            ), [0.5, 0.5, 0.0, 0.0, 0.0]),
            (KnowledgeItem(
                id="filter_002",
                content="Apple news update",
                knowledge_type=KnowledgeType.MARKET_NEWS,
                symbols=["AAPL"]
            ), [0.6, 0.4, 0.0, 0.0, 0.0]),
            (KnowledgeItem(
                id="filter_003",
                content="Google technical analysis",
                knowledge_type=KnowledgeType.TECHNICAL_ANALYSIS,
                symbols=["GOOGL"]
            ), [0.4, 0.6, 0.0, 0.0, 0.0])
        ]

        for item, embedding in items:
            self.db.store_item(item, embedding)

        # Test filter by knowledge type
        query_embedding = [0.5, 0.5, 0.0, 0.0, 0.0]
        filters = {'knowledge_types': [KnowledgeType.TECHNICAL_ANALYSIS]}
        results = self.db.similarity_search(query_embedding, top_k=10, filters=filters)

        assert len(results) == 2
        for item, score in results:
            assert item.knowledge_type == KnowledgeType.TECHNICAL_ANALYSIS

    def test_delete_item(self):
        """Test item deletion"""
        item = KnowledgeItem(
            id="delete_001",
            content="Test content to delete",
            knowledge_type=KnowledgeType.MARKET_NEWS
        )

        # Store and verify
        self.db.store_item(item, [0.1, 0.2, 0.3])
        assert self.db.get_item_count() == 1

        # Delete and verify
        result = self.db.delete_item("delete_001")
        assert result is True
        assert self.db.get_item_count() == 0


class TestKnowledgeItem:
    """Test cases for KnowledgeItem class"""

    def test_knowledge_item_creation(self):
        """Test knowledge item creation and validation"""
        item = KnowledgeItem(
            id="item_001",
            content="Test content for market analysis",
            knowledge_type=KnowledgeType.MARKET_ANALYSIS,
            title="Test Market Analysis",
            symbols=["AAPL", "MSFT"],
            sectors=["Technology"],
            tags=["bullish", "analysis"]
        )

        assert item.id == "item_001"
        assert item.knowledge_type == KnowledgeType.MARKET_ANALYSIS
        assert len(item.symbols) == 2
        assert item.content_hash is not None

    def test_knowledge_item_serialization(self):
        """Test knowledge item serialization and deserialization"""
        original_item = KnowledgeItem(
            id="serial_001",
            content="Test serialization content",
            knowledge_type=KnowledgeType.TECHNICAL_ANALYSIS,
            title="Serialization Test",
            symbols=["TEST"],
            metadata={"test": "value"}
        )

        # Serialize to dict
        item_dict = original_item.to_dict()
        assert isinstance(item_dict, dict)
        assert item_dict['id'] == "serial_001"
        assert item_dict['knowledge_type'] == KnowledgeType.TECHNICAL_ANALYSIS.value

        # Deserialize from dict
        restored_item = KnowledgeItem.from_dict(item_dict)
        assert restored_item.id == original_item.id
        assert restored_item.content == original_item.content
        assert restored_item.knowledge_type == original_item.knowledge_type

    def test_content_hash_consistency(self):
        """Test that content hash is consistent"""
        item1 = KnowledgeItem(
            id="hash_001",
            content="Same content",
            knowledge_type=KnowledgeType.MARKET_NEWS,
            title="Same title"
        )

        item2 = KnowledgeItem(
            id="hash_002",
            content="Same content",
            knowledge_type=KnowledgeType.MARKET_NEWS,
            title="Same title"
        )

        # Same content should produce same hash
        assert item1.content_hash == item2.content_hash

        # Different content should produce different hash
        item3 = KnowledgeItem(
            id="hash_003",
            content="Different content",
            knowledge_type=KnowledgeType.MARKET_NEWS,
            title="Same title"
        )

        assert item1.content_hash != item3.content_hash


class TestRAGProcessor:
    """Test cases for RAGProcessor class"""

    def setup_method(self):
        """Setup test RAG processor"""
        # Create temporary database
        self.test_db_fd, self.test_db_path = tempfile.mkstemp(suffix='.db')
        os.close(self.test_db_fd)

        # Mock the configuration
        with patch('src.ai.rag_processor.get_config') as mock_config:
            mock_config.side_effect = lambda key, default: {
                'ai.rag.database_path': self.test_db_path,
                'ai.rag.embedding_model': 'all-MiniLM-L6-v2',
                'ai.rag.max_context_length': 4000,
                'ai.rag.default_top_k': 3,
                'ai.rag.cache_ttl': 3600
            }.get(key, default)

            self.rag_processor = RAGProcessor()

    def teardown_method(self):
        """Cleanup test RAG processor"""
        if hasattr(self, 'rag_processor'):
            asyncio.run(self.rag_processor.cleanup())
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test RAG processor initialization"""
        with patch.object(self.rag_processor, '_load_embedding_model') as mock_load:
            mock_load.return_value = Mock()

            await self.rag_processor.initialize()

            assert self.rag_processor.vector_db is not None
            assert self.rag_processor.embedding_model is not None

    @pytest.mark.asyncio
    async def test_knowledge_ingestion(self):
        """Test knowledge ingestion process"""
        # Mock embedding model
        mock_model = Mock()
        mock_model.encode.return_value = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]

        with patch.object(self.rag_processor, '_load_embedding_model', return_value=mock_model):
            await self.rag_processor.initialize()

            # Create test knowledge items
            items = [
                KnowledgeItem(
                    id="ingest_001",
                    content="Test ingestion content 1",
                    knowledge_type=KnowledgeType.MARKET_NEWS,
                    symbols=["AAPL"]
                ),
                KnowledgeItem(
                    id="ingest_002",
                    content="Test ingestion content 2",
                    knowledge_type=KnowledgeType.TECHNICAL_ANALYSIS,
                    symbols=["GOOGL"]
                )
            ]

            # Test ingestion
            result = await self.rag_processor.ingest_knowledge(items)

            assert result['total_items'] == 2
            assert result['successful'] == 2
            assert result['failed'] == 0
            assert self.rag_processor.vector_db.get_item_count() == 2

    @pytest.mark.asyncio
    async def test_knowledge_retrieval(self):
        """Test knowledge retrieval process"""
        # Mock embedding model
        mock_model = Mock()
        mock_model.encode.side_effect = [
            # For ingestion
            [[0.9, 0.1, 0.0], [0.1, 0.9, 0.0], [0.0, 0.1, 0.9]],
            # For query
            [[0.8, 0.2, 0.0]]
        ]

        with patch.object(self.rag_processor, '_load_embedding_model', return_value=mock_model):
            await self.rag_processor.initialize()

            # Ingest test knowledge
            items = [
                KnowledgeItem(
                    id="retrieve_001",
                    content="Apple shows strong performance",
                    knowledge_type=KnowledgeType.MARKET_NEWS,
                    symbols=["AAPL"]
                ),
                KnowledgeItem(
                    id="retrieve_002",
                    content="Google beats earnings expectations",
                    knowledge_type=KnowledgeType.MARKET_NEWS,
                    symbols=["GOOGL"]
                ),
                KnowledgeItem(
                    id="retrieve_003",
                    content="Oil prices decline on oversupply",
                    knowledge_type=KnowledgeType.MARKET_NEWS,
                    symbols=["OIL"]
                )
            ]

            await self.rag_processor.ingest_knowledge(items)

            # Test retrieval
            query = RetrievalQuery(
                query_text="Apple stock performance",
                max_results=2,
                min_relevance_score=0.0
            )

            result = await self.rag_processor.retrieve_knowledge(query)

            assert len(result.items) <= 2
            assert result.total_found >= 0
            assert result.retrieval_time_ms > 0

            # Most relevant should be Apple-related
            if result.items:
                assert "AAPL" in result.items[0].symbols or "Apple" in result.items[0].content

    @pytest.mark.asyncio
    async def test_analysis_augmentation(self):
        """Test analysis augmentation with knowledge"""
        # Mock embedding model and Gemma3 client
        mock_model = Mock()
        mock_model.encode.side_effect = [
            [[0.5, 0.5, 0.0]],  # For ingestion
            [[0.6, 0.4, 0.0]]   # For query
        ]

        mock_gemma3_client = Mock()

        with patch.object(self.rag_processor, '_load_embedding_model', return_value=mock_model):
            await self.rag_processor.initialize()

            # Ingest relevant knowledge
            items = [
                KnowledgeItem(
                    id="augment_001",
                    content="AAPL technical indicators suggest bullish trend",
                    knowledge_type=KnowledgeType.TECHNICAL_ANALYSIS,
                    symbols=["AAPL"],
                    tags=["bullish", "technical"]
                )
            ]

            await self.rag_processor.ingest_knowledge(items)

            # Create analysis request
            analysis_request = AnalysisRequest(
                analysis_type=AnalysisType.TECHNICAL_ANALYSIS,
                input_data={
                    "symbol": "AAPL",
                    "current_price": 150.0,
                    "indicators": {"rsi": 65.0}
                }
            )

            # Test augmentation
            enhanced_request = await self.rag_processor.augment_analysis(analysis_request)

            assert enhanced_request.analysis_type == analysis_request.analysis_type
            assert enhanced_request.input_data == analysis_request.input_data
            assert 'retrieved_knowledge' in enhanced_request.context
            assert 'knowledge_metadata' in enhanced_request.context

    @pytest.mark.asyncio
    async def test_enhanced_analysis(self):
        """Test enhanced analysis with RAG"""
        # Mock embedding model
        mock_model = Mock()
        mock_model.encode.side_effect = [
            [[0.5, 0.5, 0.0]],  # For ingestion
            [[0.6, 0.4, 0.0]]   # For query
        ]

        # Mock Gemma3 client
        mock_gemma3_client = AsyncMock()
        mock_response = Mock()
        mock_response.result = {"analysis": "Enhanced analysis result"}
        mock_response.metadata = {}
        mock_gemma3_client.analyze.return_value = mock_response

        self.rag_processor.gemma3_client = mock_gemma3_client

        with patch.object(self.rag_processor, '_load_embedding_model', return_value=mock_model):
            await self.rag_processor.initialize()

            # Create analysis request
            analysis_request = AnalysisRequest(
                analysis_type=AnalysisType.MARKET_SENTIMENT,
                input_data={
                    "text": "Market sentiment analysis request",
                    "symbols": ["AAPL", "GOOGL"]
                }
            )

            # Test enhanced analysis
            response = await self.rag_processor.enhanced_analysis(analysis_request)

            assert response.result == {"analysis": "Enhanced analysis result"}
            mock_gemma3_client.analyze.assert_called_once()

    def test_text_preprocessing(self):
        """Test text preprocessing utilities"""
        # Test clean text
        dirty_text = "  This is  a   test   text\r\n\x00with artifacts  "
        clean_text = self.rag_processor._clean_text(dirty_text)

        assert clean_text == "This is a test text with artifacts"

    def test_knowledge_item_preprocessing(self):
        """Test knowledge item preprocessing"""
        item = KnowledgeItem(
            id="preprocess_001",
            content="  Content with  extra   spaces  ",
            knowledge_type=KnowledgeType.MARKET_NEWS,
            symbols=["  aapl  ", "GOOGL", ""],
            sectors=["technology", ""],
            tags=["BULLISH", "  Analysis  ", ""]
        )

        processed_item = self.rag_processor._preprocess_knowledge_item(item)

        assert processed_item.content == "Content with extra spaces"
        assert "AAPL" in processed_item.symbols
        assert "GOOGL" in processed_item.symbols
        assert "" not in processed_item.symbols
        assert "Technology" in processed_item.sectors
        assert "bullish" in processed_item.tags
        assert "analysis" in processed_item.tags

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling in various scenarios"""
        # Test initialization failure
        with patch.object(self.rag_processor, '_load_embedding_model', side_effect=Exception("Model load failed")):
            with pytest.raises(RagProcessorError):
                await self.rag_processor.initialize()

    @pytest.mark.asyncio
    async def test_performance_metrics(self):
        """Test performance metrics tracking"""
        mock_model = Mock()
        mock_model.encode.return_value = [[0.1, 0.2, 0.3]]

        with patch.object(self.rag_processor, '_load_embedding_model', return_value=mock_model):
            await self.rag_processor.initialize()

            # Perform some operations to generate metrics
            items = [KnowledgeItem(
                id="metrics_001",
                content="Test metrics content",
                knowledge_type=KnowledgeType.MARKET_NEWS
            )]

            await self.rag_processor.ingest_knowledge(items)

            query = RetrievalQuery(query_text="test query")
            await self.rag_processor.retrieve_knowledge(query)

            # Get performance metrics
            metrics = self.rag_processor.get_performance_metrics()

            assert 'ingestion' in metrics
            assert 'retrieval' in metrics
            assert 'database' in metrics
            assert 'configuration' in metrics

            assert metrics['ingestion']['total_ingestions'] > 0
            assert metrics['retrieval']['total_retrievals'] > 0

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check functionality"""
        mock_model = Mock()
        mock_model.encode.return_value = [[0.1, 0.2, 0.3]]

        with patch.object(self.rag_processor, '_load_embedding_model', return_value=mock_model):
            await self.rag_processor.initialize()

            health = await self.rag_processor.health_check()

            assert 'status' in health
            assert 'components' in health
            assert 'timestamp' in health
            assert 'metrics' in health

            # Check component health
            assert 'vector_database' in health['components']
            assert 'embedding_model' in health['components']


class TestRetrievalQuery:
    """Test cases for RetrievalQuery class"""

    def test_retrieval_query_creation(self):
        """Test retrieval query creation"""
        query = RetrievalQuery(
            query_text="Test query",
            knowledge_types=[KnowledgeType.MARKET_NEWS],
            symbols=["AAPL"],
            max_results=5,
            min_relevance_score=0.7
        )

        assert query.query_text == "Test query"
        assert len(query.knowledge_types) == 1
        assert query.symbols[0] == "AAPL"
        assert query.max_results == 5
        assert query.min_relevance_score == 0.7

    def test_retrieval_query_defaults(self):
        """Test retrieval query with default values"""
        query = RetrievalQuery(query_text="Simple query")

        assert query.knowledge_types is None
        assert query.symbols is None
        assert query.max_results == 10
        assert query.min_relevance_score == 0.5
        assert query.retrieval_mode == RetrievalMode.SEMANTIC_SEARCH


class TestIntegration:
    """Integration tests for RAG processor with external components"""

    def setup_method(self):
        """Setup integration test environment"""
        self.test_db_fd, self.test_db_path = tempfile.mkstemp(suffix='.db')
        os.close(self.test_db_fd)

    def teardown_method(self):
        """Cleanup integration test environment"""
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)

    @pytest.mark.asyncio
    async def test_full_rag_pipeline(self):
        """Test complete RAG pipeline from ingestion to analysis"""
        # This would be a comprehensive integration test
        # For now, we'll test the basic pipeline components

        with patch('src.ai.rag_processor.get_config') as mock_config:
            mock_config.side_effect = lambda key, default: {
                'ai.rag.database_path': self.test_db_path,
                'ai.rag.embedding_model': 'all-MiniLM-L6-v2',
                'ai.rag.max_context_length': 4000,
                'ai.rag.default_top_k': 3,
                'ai.rag.cache_ttl': 3600
            }.get(key, default)

            rag_processor = RAGProcessor()

            # Mock embedding model
            mock_model = Mock()
            mock_model.encode.side_effect = [
                [[0.8, 0.1, 0.1], [0.1, 0.8, 0.1]],  # For ingestion
                [[0.7, 0.2, 0.1]]  # For retrieval
            ]

            with patch.object(rag_processor, '_load_embedding_model', return_value=mock_model):
                async with rag_processor:
                    # 1. Ingest knowledge
                    knowledge_items = [
                        KnowledgeItem(
                            id="pipeline_001",
                            content="AAPL shows strong quarterly results with revenue beating expectations",
                            knowledge_type=KnowledgeType.EARNINGS_DATA,
                            title="Apple Q4 Results",
                            symbols=["AAPL"],
                            sectors=["Technology"],
                            metadata={"quarter": "Q4", "year": "2023"}
                        ),
                        KnowledgeItem(
                            id="pipeline_002",
                            content="Technical analysis indicates AAPL is approaching key resistance level",
                            knowledge_type=KnowledgeType.TECHNICAL_ANALYSIS,
                            title="AAPL Technical Update",
                            symbols=["AAPL"],
                            tags=["resistance", "bullish"]
                        )
                    ]

                    ingestion_result = await rag_processor.ingest_knowledge(knowledge_items)
                    assert ingestion_result['successful'] == 2

                    # 2. Retrieve relevant knowledge
                    query = RetrievalQuery(
                        query_text="Apple financial performance and technical analysis",
                        symbols=["AAPL"],
                        max_results=5
                    )

                    retrieval_result = await rag_processor.retrieve_knowledge(query)
                    assert len(retrieval_result.items) > 0

                    # 3. Test augmentation
                    analysis_request = AnalysisRequest(
                        analysis_type=AnalysisType.FUNDAMENTAL_ANALYSIS,
                        input_data={
                            "symbol": "AAPL",
                            "metrics": {"revenue_growth": 0.08, "pe_ratio": 25.5}
                        }
                    )

                    enhanced_request = await rag_processor.augment_analysis(analysis_request)

                    assert 'retrieved_knowledge' in enhanced_request.context
                    knowledge_context = enhanced_request.context['retrieved_knowledge']
                    assert 'relevant_information' in knowledge_context
                    assert len(knowledge_context['relevant_information']) > 0


class TestPerformance:
    """Performance tests for RAG processor"""

    def setup_method(self):
        """Setup performance test environment"""
        self.test_db_fd, self.test_db_path = tempfile.mkstemp(suffix='.db')
        os.close(self.test_db_fd)

    def teardown_method(self):
        """Cleanup performance test environment"""
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_large_batch_ingestion_performance(self):
        """Test performance with large batch ingestion"""
        with patch('src.ai.rag_processor.get_config') as mock_config:
            mock_config.side_effect = lambda key, default: {
                'ai.rag.database_path': self.test_db_path,
                'ai.rag.embedding_model': 'all-MiniLM-L6-v2',
                'ai.rag.max_context_length': 4000,
                'ai.rag.default_top_k': 3,
                'ai.rag.cache_ttl': 3600
            }.get(key, default)

            rag_processor = RAGProcessor()

            # Mock embedding model
            mock_model = Mock()
            # Generate embeddings for 100 items
            mock_embeddings = [[0.1 * i, 0.2 * i, 0.3 * i] for i in range(100)]
            mock_model.encode.return_value = mock_embeddings

            with patch.object(rag_processor, '_load_embedding_model', return_value=mock_model):
                async with rag_processor:
                    # Create 100 test items
                    items = []
                    for i in range(100):
                        item = KnowledgeItem(
                            id=f"perf_{i:03d}",
                            content=f"Performance test content {i} with market analysis data",
                            knowledge_type=KnowledgeType.MARKET_NEWS,
                            symbols=[f"SYM{i % 10}"],
                            tags=[f"tag{i % 5}"]
                        )
                        items.append(item)

                    # Measure ingestion time
                    start_time = asyncio.get_event_loop().time()
                    result = await rag_processor.ingest_knowledge(items)
                    end_time = asyncio.get_event_loop().time()

                    processing_time = (end_time - start_time) * 1000  # Convert to ms

                    assert result['successful'] == 100
                    assert result['failed'] == 0
                    assert processing_time < 10000  # Should complete within 10 seconds

                    # Test retrieval performance
                    query = RetrievalQuery(query_text="market analysis", max_results=10)

                    start_time = asyncio.get_event_loop().time()
                    retrieval_result = await rag_processor.retrieve_knowledge(query)
                    end_time = asyncio.get_event_loop().time()

                    retrieval_time = (end_time - start_time) * 1000

                    assert len(retrieval_result.items) <= 10
                    assert retrieval_time < 1000  # Should complete within 1 second


@pytest.mark.asyncio
async def test_convenience_functions():
    """Test convenience functions"""
    # These tests would require mocking the global rag_processor instance
    # For now, we'll test that they can be imported without errors
    from src.ai.rag_processor import (
        ingest_market_knowledge,
        retrieve_market_knowledge,
        enhanced_market_analysis,
        check_rag_health
    )

    # Basic import test
    assert callable(ingest_market_knowledge)
    assert callable(retrieve_market_knowledge)
    assert callable(enhanced_market_analysis)
    assert callable(check_rag_health)


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
