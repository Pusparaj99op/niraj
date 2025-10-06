# RAG Trainable JSON Format - Bank Stocks Data

## Overview
This folder contains bank stocks historical data converted to RAG (Retrieval-Augmented Generation) trainable JSON format, optimized for:
- Vector embedding generation
- LLM training and fine-tuning
- Semantic search systems
- Knowledge graph construction

## Files

### Combined Dataset
- **all_banks_rag_combined.json** - Complete dataset with metadata
  - Size: Contains all 132,242 records
  - Structure: Hierarchical with bank grouping
  - Includes: Metadata, statistics, all banks data

### Individual Bank Files
Each bank has two JSON files:
- **{SYMBOL}_daily_rag.json** - Daily timeframe data
- **{SYMBOL}_15min_rag.json** - 15-minute timeframe data

Total: 40 individual JSON files

## JSON Structure

### Entry Format
```json
{
  "id": "SBI_2025-01-15_daily",
  "symbol": "SBI",
  "bank_name": "State Bank of India",
  "sector": "Public",
  "type": "Bank",
  "timestamp": "2025-01-15",
  "timeframe": "daily",
  
  "ohlcv": {
    "open": 625.50,
    "high": 632.75,
    "low": 623.20,
    "close": 630.40,
    "volume": 15234567
  },
  
  "metrics": {
    "price_change": 4.90,
    "price_change_percent": 0.78,
    "volatility_percent": 1.52,
    "range": 9.55,
    "trend": "bullish"
  },
  
  "text": "State Bank of India (SBI) stock on 2025-01-15...",
  
  "context": {
    "year": 2025,
    "month": 1,
    "day": 15,
    "weekday": "Wednesday",
    "quarter": "Q1"
  },
  
  "embedding_fields": [
    "text",
    "State Bank of India bullish daily",
    "SBI stock price 2025-01-15",
    "Public sector bank increased"
  ]
}
```

## Fields Description

### Core Identifiers
- **id**: Unique identifier (symbol_date_timeframe)
- **symbol**: Stock ticker symbol
- **bank_name**: Full bank name
- **sector**: Public/Private sector
- **type**: Entity type (Bank)
- **timestamp**: Date/datetime of the record
- **timeframe**: daily or 15min

### Price Data (ohlcv)
- **open**: Opening price
- **high**: Highest price
- **low**: Lowest price
- **close**: Closing price
- **volume**: Trading volume

### Calculated Metrics
- **price_change**: Absolute price change
- **price_change_percent**: Percentage change
- **volatility_percent**: Daily/intraday volatility
- **range**: High-Low range
- **trend**: bullish/bearish/neutral

### Text Field (for Embeddings)
- Natural language description
- Context-rich narrative
- Suitable for vector embedding
- Includes sentiment and trends

### Context
- Temporal information (year, month, day, weekday)
- Quarter information
- Hour/minute (for intraday data)

### Embedding Fields
- Pre-formatted text variations
- Multiple perspectives
- Optimized for semantic search

## Usage Examples

### Load with Python
```python
import json

# Load combined dataset
with open('rag_json/all_banks_rag_combined.json', 'r') as f:
    dataset = json.load(f)

# Access metadata
metadata = dataset['metadata']
statistics = dataset['statistics']
banks_data = dataset['data']

# Load individual bank
with open('rag_json/HDFCBANK_daily_rag.json', 'r') as f:
    hdfc_daily = json.load(f)
```

### Generate Embeddings (OpenAI)
```python
import openai
import json

# Load data
with open('rag_json/SBI_daily_rag.json', 'r') as f:
    sbi_data = json.load(f)

# Generate embeddings
embeddings = []
for entry in sbi_data:
    response = openai.Embedding.create(
        model="text-embedding-ada-002",
        input=entry['text']
    )
    embeddings.append({
        'id': entry['id'],
        'embedding': response['data'][0]['embedding']
    })
```

### LangChain Integration
```python
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.docstore.document import Document
import json

# Load data
with open('rag_json/all_banks_rag_combined.json', 'r') as f:
    dataset = json.load(f)

# Create documents
documents = []
for bank in dataset['data']:
    for entry in bank['daily_data']:
        doc = Document(
            page_content=entry['text'],
            metadata={
                'symbol': entry['symbol'],
                'date': entry['timestamp'],
                'trend': entry['metrics']['trend']
            }
        )
        documents.append(doc)

# Create vector store
embeddings = OpenAIEmbeddings()
vectorstore = Chroma.from_documents(documents, embeddings)

# Query
results = vectorstore.similarity_search(
    "Show me bullish trends in HDFC Bank",
    k=5
)
```

### LlamaIndex Integration
```python
from llama_index import Document, VectorStoreIndex
import json

# Load data
with open('rag_json/HDFCBANK_daily_rag.json', 'r') as f:
    hdfc_data = json.load(f)

# Create documents
documents = [
    Document(
        text=entry['text'],
        metadata=entry['context']
    )
    for entry in hdfc_data
]

# Create index
index = VectorStoreIndex.from_documents(documents)

# Query
query_engine = index.as_query_engine()
response = query_engine.query(
    "What was the trend of HDFC Bank in January 2025?"
)
```

### Pinecone Vector Database
```python
import pinecone
import openai
import json

# Initialize Pinecone
pinecone.init(api_key="your-api-key", environment="us-west1-gcp")
index = pinecone.Index("bank-stocks")

# Load data
with open('rag_json/all_banks_rag_combined.json', 'r') as f:
    dataset = json.load(f)

# Upsert to Pinecone
for bank in dataset['data']:
    for entry in bank['daily_data']:
        # Generate embedding
        response = openai.Embedding.create(
            model="text-embedding-ada-002",
            input=entry['text']
        )
        embedding = response['data'][0]['embedding']
        
        # Upsert
        index.upsert([(
            entry['id'],
            embedding,
            entry  # metadata
        )])
```

## Statistics

- **Total Banks**: 20
- **Daily Records**: 103,387
- **Intraday Records**: 28,855
- **Total Records**: 132,242
- **Timeframes**: 2 (daily, 15min)

## Use Cases

### 1. RAG Systems
- Semantic search over financial data
- Context-aware query answering
- Historical pattern retrieval

### 2. LLM Training
- Fine-tuning on financial narratives
- Market sentiment analysis
- Trend prediction models

### 3. Vector Databases
- Similarity search
- Clustering analysis
- Anomaly detection

### 4. Knowledge Graphs
- Entity relationships
- Temporal patterns
- Sector analysis

## Embedding Strategies

### Text Field
- Primary field for semantic embeddings
- Rich context and narrative
- Best for general-purpose search

### Embedding Fields
- Multiple perspectives
- Specialized queries
- Granular search capabilities

### Hybrid Approach
- Combine text + structured data
- Metadata filtering + semantic search
- Multi-modal retrieval

## Data Quality

✅ **Verified**
- No duplicate IDs
- Valid JSON format
- Complete fields
- Calculated metrics verified
- Text descriptions accurate

## Integration Tips

1. **Vector Store**: Use `id` as primary key
2. **Embeddings**: Focus on `text` field
3. **Filtering**: Use `sector`, `trend`, `context` fields
4. **Chunking**: Each entry is pre-chunked
5. **Metadata**: Rich metadata for hybrid search

## File Sizes

- Individual bank JSON: 2-10 MB each
- Combined JSON: ~200-300 MB
- Total folder: ~300-400 MB

## Version

- **Version**: 1.0
- **Created**: 2025-10-05
- **Format**: RAG-compatible JSON
- **Encoding**: UTF-8

## Support

For questions or issues:
1. Check NIRAJ documentation
2. Review conversion script: `convert_to_rag_json.py`
3. Validate JSON format with schema

---

**NIRAJ Advanced Trading System**  
**RAG Data Module**  
**Ready for AI/ML Integration**
