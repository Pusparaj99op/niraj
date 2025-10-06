# RAG Trainable JSON Format - Usage Guide

## 🎯 Overview

All bank stocks historical data has been converted to **RAG (Retrieval-Augmented Generation) trainable JSON format**, optimized for:

- ✅ **Vector Embeddings**: Text descriptions ready for embedding generation
- ✅ **LLM Training**: Structured narrative format for fine-tuning
- ✅ **Semantic Search**: Context-rich entries for similarity search
- ✅ **Knowledge Graphs**: Relationship and temporal data
- ✅ **Hybrid Search**: Metadata + semantic capabilities

## 📊 Dataset Statistics

```
Total Banks:        20 (9 Public + 11 Private sector)
Daily Records:      103,387 (historical data)
Intraday Records:   28,855 (15-min data, last 60 days)
Total Records:      132,242
File Size:          ~320 MB (42 JSON files)
Date Range:         1996-2025 (up to 29 years)
```

## 📁 File Structure

```
historical/rag_json/
├── all_banks_rag_combined.json      (174 MB - Complete dataset)
├── RAG_README.md                     (Documentation)
│
├── HDFCBANK_daily_rag.json          (8.1 MB - 7,475 records)
├── HDFCBANK_15min_rag.json          (1.7 MB - 1,439 records)
│
├── SBI_daily_rag.json               (8.2 MB - 7,473 records)
├── SBI_15min_rag.json               (1.7 MB - 1,447 records)
│
└── ... (38 more bank-specific files)
```

## 🔍 JSON Entry Structure

Each record contains:

```json
{
  "id": "HDFCBANK_2025-01-15_daily",
  "symbol": "HDFCBANK",
  "bank_name": "HDFC Bank",
  "sector": "Private",
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
  
  "text": "HDFC Bank (HDFCBANK) stock on 2025-01-15 in daily timeframe: Opening at ₹625.50, the stock increased to close at ₹630.40, showing a 0.78% gain. The day's range was ₹623.20 to ₹632.75, with a volatility of 1.52%. Trading volume was 15,234,567 shares. This Private sector bank showed bullish market sentiment.",
  
  "context": {
    "year": 2025,
    "month": 1,
    "day": 15,
    "weekday": "Wednesday",
    "quarter": "Q1"
  },
  
  "embedding_fields": [
    "text",
    "HDFC Bank bullish daily",
    "HDFCBANK stock price 2025-01-15",
    "Private sector bank increased"
  ]
}
```

## 🚀 Quick Start Examples

### 1. Load Combined Dataset

```python
import json

# Load all data
with open('historical/rag_json/all_banks_rag_combined.json', 'r') as f:
    dataset = json.load(f)

# Access components
metadata = dataset['metadata']      # Dataset info
statistics = dataset['statistics']  # Record counts
banks_data = dataset['data']        # All bank records

print(f"Total records: {statistics['total_records']:,}")
print(f"Banks: {metadata['total_banks']}")
```

### 2. Load Individual Bank

```python
import json

# Load HDFC Bank daily data
with open('historical/rag_json/HDFCBANK_daily_rag.json', 'r') as f:
    hdfc_daily = json.load(f)

print(f"HDFC Bank daily records: {len(hdfc_daily):,}")
print(f"Date range: {hdfc_daily[0]['timestamp']} to {hdfc_daily[-1]['timestamp']}")

# Filter bullish days
bullish_days = [entry for entry in hdfc_daily if entry['metrics']['trend'] == 'bullish']
print(f"Bullish days: {len(bullish_days)}")
```

### 3. Generate Embeddings (OpenAI)

```python
import openai
import json

openai.api_key = "your-api-key"

# Load data
with open('historical/rag_json/SBI_daily_rag.json', 'r') as f:
    sbi_data = json.load(f)

# Generate embeddings for text field
embeddings = []
for entry in sbi_data[:100]:  # First 100 records
    response = openai.Embedding.create(
        model="text-embedding-ada-002",
        input=entry['text']
    )
    embeddings.append({
        'id': entry['id'],
        'symbol': entry['symbol'],
        'date': entry['timestamp'],
        'embedding': response['data'][0]['embedding']
    })

print(f"Generated {len(embeddings)} embeddings")
```

## 🔧 Integration Examples

### LangChain RAG Pipeline

```python
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.docstore.document import Document
from langchain.chains import RetrievalQA
from langchain.llms import OpenAI
import json

# Load data
with open('historical/rag_json/all_banks_rag_combined.json', 'r') as f:
    dataset = json.load(f)

# Create documents
documents = []
for bank in dataset['data']:
    for entry in bank['daily_data']:
        doc = Document(
            page_content=entry['text'],
            metadata={
                'symbol': entry['symbol'],
                'bank_name': entry['bank_name'],
                'date': entry['timestamp'],
                'trend': entry['metrics']['trend'],
                'sector': entry['sector'],
                'close_price': entry['ohlcv']['close']
            }
        )
        documents.append(doc)

# Create vector store
embeddings = OpenAIEmbeddings()
vectorstore = Chroma.from_documents(
    documents=documents,
    embedding=embeddings,
    collection_name="bank_stocks"
)

# Create QA chain
qa_chain = RetrievalQA.from_chain_type(
    llm=OpenAI(temperature=0),
    chain_type="stuff",
    retriever=vectorstore.as_retriever(search_kwargs={"k": 5})
)

# Query
result = qa_chain.run("Show me bullish trends in HDFC Bank during 2024")
print(result)

# Semantic search
results = vectorstore.similarity_search(
    "When did private sector banks show strong growth?",
    k=10
)

for doc in results:
    print(f"{doc.metadata['bank_name']} ({doc.metadata['date']}): {doc.metadata['trend']}")
```

### LlamaIndex Integration

```python
from llama_index import Document, VectorStoreIndex, ServiceContext
from llama_index.llms import OpenAI
import json

# Load data
with open('historical/rag_json/HDFCBANK_daily_rag.json', 'r') as f:
    hdfc_data = json.load(f)

# Create documents
documents = [
    Document(
        text=entry['text'],
        metadata={
            'symbol': entry['symbol'],
            'date': entry['timestamp'],
            'trend': entry['metrics']['trend'],
            'price': entry['ohlcv']['close']
        }
    )
    for entry in hdfc_data
]

# Create index
service_context = ServiceContext.from_defaults(
    llm=OpenAI(model="gpt-4", temperature=0)
)
index = VectorStoreIndex.from_documents(
    documents,
    service_context=service_context
)

# Query engine
query_engine = index.as_query_engine()

# Ask questions
response = query_engine.query(
    "What was the trend of HDFC Bank stock in January 2025?"
)
print(response)

response = query_engine.query(
    "Find periods of high volatility in HDFC Bank"
)
print(response)
```

### Pinecone Vector Database

```python
import pinecone
import openai
import json

# Initialize Pinecone
pinecone.init(
    api_key="your-pinecone-api-key",
    environment="us-west1-gcp"
)

# Create or connect to index
index_name = "bank-stocks-rag"
if index_name not in pinecone.list_indexes():
    pinecone.create_index(
        name=index_name,
        dimension=1536,  # OpenAI embedding dimension
        metric="cosine"
    )

index = pinecone.Index(index_name)

# Load data
with open('historical/rag_json/all_banks_rag_combined.json', 'r') as f:
    dataset = json.load(f)

# Upsert to Pinecone (batch processing)
batch_size = 100
vectors = []

for bank in dataset['data']:
    for entry in bank['daily_data']:
        # Generate embedding
        response = openai.Embedding.create(
            model="text-embedding-ada-002",
            input=entry['text']
        )
        embedding = response['data'][0]['embedding']
        
        # Prepare vector
        vectors.append((
            entry['id'],
            embedding,
            {
                'symbol': entry['symbol'],
                'bank_name': entry['bank_name'],
                'date': entry['timestamp'],
                'trend': entry['metrics']['trend'],
                'sector': entry['sector'],
                'text': entry['text'][:500]  # Truncate for metadata
            }
        ))
        
        # Batch upsert
        if len(vectors) >= batch_size:
            index.upsert(vectors=vectors)
            vectors = []

# Upsert remaining
if vectors:
    index.upsert(vectors=vectors)

# Query
query_text = "Show me strong bullish trends in private sector banks"
query_embedding = openai.Embedding.create(
    model="text-embedding-ada-002",
    input=query_text
)['data'][0]['embedding']

results = index.query(
    vector=query_embedding,
    top_k=10,
    include_metadata=True
)

for match in results['matches']:
    print(f"{match['metadata']['bank_name']} ({match['metadata']['date']})")
    print(f"Trend: {match['metadata']['trend']}")
    print(f"Score: {match['score']:.4f}\n")
```

### Weaviate Integration

```python
import weaviate
import json

# Connect to Weaviate
client = weaviate.Client("http://localhost:8080")

# Define schema
schema = {
    "class": "BankStock",
    "description": "Historical bank stock data",
    "vectorizer": "text2vec-openai",
    "moduleConfig": {
        "text2vec-openai": {
            "model": "ada",
            "type": "text"
        }
    },
    "properties": [
        {"name": "symbol", "dataType": ["text"]},
        {"name": "bankName", "dataType": ["text"]},
        {"name": "sector", "dataType": ["text"]},
        {"name": "timestamp", "dataType": ["date"]},
        {"name": "timeframe", "dataType": ["text"]},
        {"name": "text", "dataType": ["text"]},
        {"name": "trend", "dataType": ["text"]},
        {"name": "closePrice", "dataType": ["number"]},
        {"name": "volume", "dataType": ["int"]},
        {"name": "volatility", "dataType": ["number"]}
    ]
}

# Create class
client.schema.create_class(schema)

# Load and insert data
with open('historical/rag_json/HDFCBANK_daily_rag.json', 'r') as f:
    hdfc_data = json.load(f)

# Batch import
with client.batch as batch:
    for entry in hdfc_data:
        properties = {
            "symbol": entry['symbol'],
            "bankName": entry['bank_name'],
            "sector": entry['sector'],
            "timestamp": entry['timestamp'],
            "timeframe": entry['timeframe'],
            "text": entry['text'],
            "trend": entry['metrics']['trend'],
            "closePrice": entry['ohlcv']['close'],
            "volume": entry['ohlcv']['volume'],
            "volatility": entry['metrics']['volatility_percent']
        }
        batch.add_data_object(properties, "BankStock")

# Semantic search
result = client.query.get(
    "BankStock",
    ["symbol", "bankName", "timestamp", "trend", "text"]
).with_near_text({
    "concepts": ["bullish private sector banks strong growth"]
}).with_limit(5).do()

for item in result['data']['Get']['BankStock']:
    print(f"{item['bankName']} ({item['timestamp']})")
    print(f"Trend: {item['trend']}\n")
```

## 📈 Advanced Use Cases

### 1. Time-Series Analysis

```python
import json
import pandas as pd

# Load data
with open('historical/rag_json/HDFCBANK_daily_rag.json', 'r') as f:
    data = json.load(f)

# Convert to DataFrame
df = pd.DataFrame([
    {
        'date': entry['timestamp'],
        'close': entry['ohlcv']['close'],
        'volume': entry['ohlcv']['volume'],
        'trend': entry['metrics']['trend'],
        'volatility': entry['metrics']['volatility_percent']
    }
    for entry in data
])

df['date'] = pd.to_datetime(df['date'])
df = df.set_index('date')

# Analyze trends
print("Trend distribution:")
print(df['trend'].value_counts())

# High volatility periods
high_vol = df[df['volatility'] > 5.0]
print(f"\nHigh volatility days: {len(high_vol)}")
```

### 2. Multi-Bank Comparison

```python
import json
from collections import defaultdict

# Load multiple banks
banks = ['HDFCBANK', 'ICICIBANK', 'AXISBANK']
bank_data = {}

for bank in banks:
    with open(f'historical/rag_json/{bank}_daily_rag.json', 'r') as f:
        bank_data[bank] = json.load(f)

# Compare trends on specific date
target_date = '2025-01-15'

for bank, data in bank_data.items():
    entry = next((e for e in data if e['timestamp'] == target_date), None)
    if entry:
        print(f"{entry['bank_name']}:")
        print(f"  Trend: {entry['metrics']['trend']}")
        print(f"  Change: {entry['metrics']['price_change_percent']:.2f}%")
        print(f"  Volume: {entry['ohlcv']['volume']:,}\n")
```

### 3. Sentiment Analysis Training

```python
import json
from sklearn.model_selection import train_test_split

# Load data
with open('historical/rag_json/all_banks_rag_combined.json', 'r') as f:
    dataset = json.load(f)

# Extract text and labels
texts = []
labels = []

for bank in dataset['data']:
    for entry in bank['daily_data']:
        texts.append(entry['text'])
        labels.append(entry['metrics']['trend'])

# Split data
X_train, X_test, y_train, y_test = train_test_split(
    texts, labels, test_size=0.2, random_state=42
)

print(f"Training samples: {len(X_train)}")
print(f"Test samples: {len(X_test)}")

# Label distribution
from collections import Counter
print("\nLabel distribution:")
print(Counter(y_train))
```

### 4. RAG-Based Chatbot

```python
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.chains import ConversationalRetrievalChain
from langchain.llms import OpenAI
from langchain.memory import ConversationBufferMemory
import json

# Load data
with open('historical/rag_json/all_banks_rag_combined.json', 'r') as f:
    dataset = json.load(f)

# Create documents
from langchain.docstore.document import Document

documents = []
for bank in dataset['data']:
    for entry in bank['daily_data'][:1000]:  # Sample
        doc = Document(
            page_content=entry['text'],
            metadata=entry
        )
        documents.append(doc)

# Create vector store
embeddings = OpenAIEmbeddings()
vectorstore = FAISS.from_documents(documents, embeddings)

# Create conversational chain
memory = ConversationBufferMemory(
    memory_key="chat_history",
    return_messages=True
)

qa = ConversationalRetrievalChain.from_llm(
    llm=OpenAI(temperature=0),
    retriever=vectorstore.as_retriever(),
    memory=memory
)

# Interactive chat
while True:
    query = input("You: ")
    if query.lower() in ['exit', 'quit']:
        break
    
    result = qa({"question": query})
    print(f"Bot: {result['answer']}\n")
```

## 🎯 Best Practices

### 1. Embedding Generation
- **Primary Field**: Use `text` field for main embeddings
- **Batch Processing**: Process 100-1000 records at a time
- **Caching**: Store embeddings to avoid regeneration
- **Model Choice**: text-embedding-ada-002 recommended

### 2. Vector Database
- **Indexing**: Use `id` as unique identifier
- **Metadata**: Store essential fields (symbol, date, trend)
- **Chunking**: Each entry is pre-chunked (no splitting needed)
- **Filtering**: Use metadata filters for hybrid search

### 3. LLM Training
- **Context Window**: Each entry fits in 500 tokens
- **Fine-tuning**: Use `text` field as training examples
- **Validation**: Use 20% data for validation
- **Augmentation**: Combine multiple entries for context

### 4. Performance Optimization
- **Lazy Loading**: Load specific banks instead of combined file
- **Pagination**: Process data in batches
- **Indexing**: Pre-index frequently queried fields
- **Caching**: Cache embeddings and search results

## 📚 Field Reference

| Field | Type | Purpose | Example |
|-------|------|---------|---------|
| `id` | string | Unique identifier | "HDFCBANK_2025-01-15_daily" |
| `symbol` | string | Stock ticker | "HDFCBANK" |
| `bank_name` | string | Full name | "HDFC Bank" |
| `sector` | string | Public/Private | "Private" |
| `timestamp` | string | Date/datetime | "2025-01-15" |
| `timeframe` | string | Data frequency | "daily" or "15min" |
| `ohlcv` | object | Price/volume | {open, high, low, close, volume} |
| `metrics` | object | Calculated data | {price_change, trend, volatility} |
| `text` | string | Embedding text | Natural language description |
| `context` | object | Temporal info | {year, month, weekday, quarter} |
| `embedding_fields` | array | Alt. texts | Multiple text variations |

## 🔍 Query Examples

### Find Bullish Trends
```python
bullish = [e for e in data if e['metrics']['trend'] == 'bullish']
```

### High Volume Days
```python
high_vol = [e for e in data if e['ohlcv']['volume'] > 10000000]
```

### Volatile Periods
```python
volatile = [e for e in data if e['metrics']['volatility_percent'] > 5.0]
```

### Date Range
```python
jan_2025 = [e for e in data if e['timestamp'].startswith('2025-01')]
```

### Private Sector Banks
```python
private = [e for e in data if e['sector'] == 'Private']
```

## 📦 File Sizes

- **Combined**: 174 MB (all 132,242 records)
- **Individual Daily**: 2-8 MB per bank
- **Individual 15-min**: 1.6-1.7 MB per bank
- **Total**: ~320 MB (42 files)

## ✅ Validation

All data has been validated for:
- ✅ Unique IDs (no duplicates)
- ✅ Valid JSON format
- ✅ Complete fields
- ✅ Accurate calculations
- ✅ Consistent formatting

## 🚀 Next Steps

1. **Choose Integration**: Select vector DB or RAG framework
2. **Generate Embeddings**: Process text fields
3. **Build Index**: Create searchable vector store
4. **Test Queries**: Validate semantic search
5. **Deploy**: Integrate with your application

## 📞 Support

- **Documentation**: See `RAG_README.md` in the rag_json folder
- **Script**: `convert_to_rag_json.py` for regeneration
- **Format**: Standard JSON, UTF-8 encoded

---

**NIRAJ Advanced Trading System**  
**RAG Data Module v1.0**  
**Ready for AI/ML Production**
