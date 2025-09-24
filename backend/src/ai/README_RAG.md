# RAG Processor for NIRAJ Trading System

## Overview

The RAG (Retrieval-Augmented Generation) processor is a comprehensive system that enhances AI trading analysis by providing contextual market knowledge to improve the accuracy and relevance of AI-generated insights. It integrates seamlessly with the Gemma3 integration client to provide enhanced trading analysis capabilities.

## Features

### Core Capabilities
- **Knowledge Ingestion**: Ingest various types of market knowledge including news, technical analysis, research reports, and more
- **Vector-based Retrieval**: Use semantic similarity search to find relevant market knowledge
- **Context Augmentation**: Enhance AI analysis requests with relevant contextual information
- **Performance Monitoring**: Track ingestion and retrieval performance with comprehensive metrics
- **Error Handling**: Robust error handling with graceful fallbacks

### Knowledge Types Supported
- Market News (`MARKET_NEWS`)
- Technical Analysis (`TECHNICAL_ANALYSIS`)
- Fundamental Analysis (`FUNDAMENTAL_ANALYSIS`)
- Economic Data (`ECONOMIC_DATA`)
- Research Reports (`RESEARCH_REPORT`)
- Trading Strategies (`TRADING_STRATEGY`)
- Risk Analysis (`RISK_ANALYSIS`)
- Market Commentary (`MARKET_COMMENTARY`)
- Regulatory News (`REGULATORY_NEWS`)
- Earnings Data (`EARNINGS_DATA`)
- Analyst Ratings (`ANALYST_RATING`)
- Pattern Recognition (`PATTERN_RECOGNITION`)
- Sector Analysis (`SECTOR_ANALYSIS`)
- Macro Economic (`MACRO_ECONOMIC`)
- Cryptocurrency (`CRYPTOCURRENCY`)

## Architecture

### Components

1. **VectorDatabase**: SQLite-based vector storage with similarity search capabilities
2. **RAGProcessor**: Main processor class handling ingestion, retrieval, and augmentation
3. **KnowledgeItem**: Data structure representing individual knowledge pieces
4. **RetrievalQuery**: Query structure for knowledge retrieval
5. **Embedding Model**: Sentence-transformers model for generating embeddings

### Dependencies

The RAG processor requires the following dependencies (automatically managed in pyproject.toml):
- `sentence-transformers`: For generating text embeddings
- `numpy`: For vector operations and similarity calculations
- `sqlite3`: For knowledge storage (built-in Python)
- `structlog`: For structured logging

## Installation

The dependencies are managed through Poetry. Ensure the following are in your `pyproject.toml`:

```toml
sentence-transformers = "^2.2.2"
scikit-learn = "^1.3.0"
```

Then run:
```bash
poetry install
```

## Usage

### Basic Usage

```python
import asyncio
from src.ai.rag_processor import (
    RAGProcessor, KnowledgeItem, KnowledgeType,
    RetrievalQuery, AnalysisRequest, AnalysisType
)

async def example_usage():
    async with RAGProcessor() as rag_processor:
        # 1. Ingest Knowledge
        knowledge_items = [
            KnowledgeItem(
                id="news_001",
                content="Bank Nifty shows strong bullish momentum with RSI at 68.",
                knowledge_type=KnowledgeType.TECHNICAL_ANALYSIS,
                title="Bank Nifty Technical Analysis",
                symbols=["BANKNIFTY"],
                sectors=["Banking"],
                tags=["bullish", "rsi", "uptrend"]
            )
        ]

        result = await rag_processor.ingest_knowledge(knowledge_items)
        print(f"Ingested {result['successful']} items")

        # 2. Retrieve Knowledge
        query = RetrievalQuery(
            query_text="Bank Nifty technical analysis",
            symbols=["BANKNIFTY"],
            max_results=5
        )

        retrieval_result = await rag_processor.retrieve_knowledge(query)
        print(f"Found {len(retrieval_result.items)} relevant items")

        # 3. Enhanced Analysis (requires Gemma3 client)
        analysis_request = AnalysisRequest(
            analysis_type=AnalysisType.TECHNICAL_ANALYSIS,
            input_data={
                "symbol": "BANKNIFTY",
                "current_price": 45250.0,
                "indicators": {"rsi": 68.5}
            }
        )

        enhanced_response = await rag_processor.enhanced_analysis(analysis_request)
        print("Enhanced Analysis:", enhanced_response.result)

# Run the example
asyncio.run(example_usage())
```

### Convenience Functions

For common operations, use the convenience functions:

```python
from src.ai.rag_processor import (
    ingest_market_knowledge,
    retrieve_market_knowledge,
    enhanced_market_analysis,
    check_rag_health
)

# Ingest knowledge items
result = await ingest_market_knowledge(knowledge_items)

# Retrieve knowledge
results = await retrieve_market_knowledge(
    query="market sentiment analysis",
    knowledge_types=[KnowledgeType.MARKET_NEWS],
    symbols=["AAPL", "GOOGL"],
    max_results=10
)

# Enhanced analysis
enhanced_response = await enhanced_market_analysis(analysis_request)

# Health check
health = await check_rag_health()
```

## Configuration

Configure the RAG processor through the application configuration system:

```yaml
ai:
  rag:
    database_path: "data/rag_knowledge.db"
    embedding_model: "all-MiniLM-L6-v2"
    max_context_length: 8000
    default_top_k: 5
    cache_ttl: 3600
```

### Configuration Options

- `database_path`: Path to SQLite database for knowledge storage
- `embedding_model`: Sentence-transformers model name (default: "all-MiniLM-L6-v2")
- `max_context_length`: Maximum context length for augmented analysis
- `default_top_k`: Default number of results to retrieve
- `cache_ttl`: Cache time-to-live in seconds

## Knowledge Management

### Ingesting Knowledge

```python
# Create knowledge items
items = [
    KnowledgeItem(
        id="unique_id",
        content="Your knowledge content here",
        knowledge_type=KnowledgeType.MARKET_NEWS,
        title="Optional title",
        summary="Optional summary",
        source="Data source",
        symbols=["AAPL", "GOOGL"],  # Related symbols
        sectors=["Technology"],     # Related sectors
        tags=["earnings", "bullish"], # Tags for categorization
        metadata={"confidence": 0.85, "analyst": "John Doe"}
    )
]

# Ingest the items
result = await rag_processor.ingest_knowledge(items)
```

### Retrieving Knowledge

```python
# Create a retrieval query
query = RetrievalQuery(
    query_text="Apple earnings analysis",
    knowledge_types=[KnowledgeType.EARNINGS_DATA, KnowledgeType.ANALYST_RATING],
    symbols=["AAPL"],
    time_range=(start_date, end_date),  # Optional time filter
    max_results=10,
    min_relevance_score=0.5,
    retrieval_mode=RetrievalMode.SEMANTIC_SEARCH
)

# Retrieve knowledge
result = await rag_processor.retrieve_knowledge(query)

# Access retrieved items
for item in result.items:
    print(f"Title: {item.title}")
    print(f"Content: {item.content}")
    print(f"Relevance: {item.relevance_score}")
```

## Performance Monitoring

The RAG processor provides comprehensive performance metrics:

```python
# Get performance metrics
metrics = rag_processor.get_performance_metrics()

print("Ingestion Metrics:")
print(f"- Total ingestions: {metrics['ingestion']['total_ingestions']}")
print(f"- Success rate: {metrics['ingestion']['success_rate']:.2%}")

print("Retrieval Metrics:")
print(f"- Total retrievals: {metrics['retrieval']['total_retrievals']}")
print(f"- Average time: {metrics['retrieval']['average_retrieval_time_ms']:.2f}ms")

print("Database Info:")
print(f"- Total items: {metrics['database']['total_items']}")
```

## Health Monitoring

Monitor the health of the RAG processor:

```python
health = await rag_processor.health_check()

print(f"Overall Status: {health['status']}")
print(f"Vector Database: {health['components']['vector_database']['status']}")
print(f"Embedding Model: {health['components']['embedding_model']['status']}")

if health['status'] != 'healthy':
    print("Issues detected:", health.get('error'))
```

## Error Handling

The RAG processor includes comprehensive error handling:

```python
from src.ai.rag_processor import (
    RagProcessorError, VectorDatabaseError,
    EmbeddingError, RetrievalError, IngestionError
)

try:
    await rag_processor.ingest_knowledge(items)
except IngestionError as e:
    print(f"Ingestion failed: {e.message}")
    print(f"Context: {e.context}")
except RagProcessorError as e:
    print(f"RAG processor error: {e.message}")
```

## Testing

The RAG processor includes a comprehensive test suite:

```bash
# Run all tests
pytest backend/tests/unit/test_rag_processor.py -v

# Run specific test categories
pytest backend/tests/unit/test_rag_processor.py::TestVectorDatabase -v
pytest backend/tests/unit/test_rag_processor.py::TestRAGProcessor -v
pytest backend/tests/unit/test_rag_processor.py::TestIntegration -v

# Run performance tests
pytest backend/tests/unit/test_rag_processor.py::TestPerformance -v -m slow
```

## Integration with Gemma3

The RAG processor integrates seamlessly with the Gemma3 client:

```python
from src.ai.gemma3_integration import gemma3_client
from src.ai.rag_processor import rag_processor

# Set up the integration
rag_processor.gemma3_client = gemma3_client

# Use enhanced analysis
async with rag_processor:
    response = await rag_processor.enhanced_analysis(analysis_request)
```

## Best Practices

### Knowledge Ingestion
1. **Batch Processing**: Ingest knowledge in batches of 10-50 items for optimal performance
2. **Content Quality**: Ensure content is clean and well-formatted
3. **Metadata**: Include relevant symbols, sectors, and tags for better retrieval
4. **Deduplication**: The system automatically handles content deduplication via hashing

### Retrieval Optimization
1. **Relevance Threshold**: Set appropriate `min_relevance_score` to filter low-quality results
2. **Result Limits**: Use reasonable `max_results` limits to avoid information overload
3. **Temporal Filtering**: Use time ranges for recent information when relevant
4. **Knowledge Type Filtering**: Specify relevant knowledge types to improve precision

### Performance Optimization
1. **Connection Pooling**: Use async context managers for proper resource management
2. **Caching**: The system includes built-in caching for frequent queries
3. **Model Loading**: Embedding models are loaded once and reused
4. **Database Optimization**: SQLite database includes appropriate indexes for fast queries

## Troubleshooting

### Common Issues

1. **Model Loading Errors**
   ```
   Solution: Ensure sentence-transformers is installed and model name is correct
   ```

2. **Database Connection Issues**
   ```
   Solution: Check database path permissions and disk space
   ```

3. **Memory Issues with Large Datasets**
   ```
   Solution: Process data in smaller batches, increase system memory
   ```

4. **Slow Retrieval Performance**
   ```
   Solution: Check database indexes, reduce result count, optimize queries
   ```

## Future Enhancements

Planned improvements include:
- Integration with ChromaDB for better vector storage
- Support for multiple embedding models
- Real-time knowledge updates via streaming
- Advanced filtering and ranking algorithms
- Integration with external knowledge sources
- Distributed processing capabilities

## Contributing

When contributing to the RAG processor:
1. Add comprehensive tests for new features
2. Update documentation for API changes
3. Follow the existing error handling patterns
4. Include performance considerations
5. Add logging for debugging and monitoring

## License

Part of the NIRAJ Trading System. See main project license for details.
