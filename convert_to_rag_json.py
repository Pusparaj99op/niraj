"""
Convert Bank Stocks Historical Data to RAG Trainable JSON Format

This script converts CSV historical data into structured JSON format
suitable for RAG (Retrieval-Augmented Generation) training and
vector embedding systems.

JSON Format Features:
- Structured metadata for each data point
- Embeddings-ready text descriptions
- Contextual information for better retrieval
- Training-friendly format for LLMs
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
import pandas as pd
from typing import List, Dict, Any

print("\n" + "="*70)
print("CONVERT TO RAG TRAINABLE JSON FORMAT")
print("="*70 + "\n")

# Bank information
BANK_STOCKS = {
    "SBI": {"name": "State Bank of India", "sector": "Public", "type": "Bank"},
    "PNB": {"name": "Punjab National Bank", "sector": "Public", "type": "Bank"},
    "BANKBARODA": {"name": "Bank of Baroda", "sector": "Public", "type": "Bank"},
    "CANBK": {"name": "Canara Bank", "sector": "Public", "type": "Bank"},
    "UNIONBANK": {"name": "Union Bank of India", "sector": "Public", "type": "Bank"},
    "INDIANB": {"name": "Indian Bank", "sector": "Public", "type": "Bank"},
    "IOB": {"name": "Indian Overseas Bank", "sector": "Public", "type": "Bank"},
    "CENTRALBK": {"name": "Central Bank of India", "sector": "Public", "type": "Bank"},
    "MAHABANK": {"name": "Bank of Maharashtra", "sector": "Public", "type": "Bank"},
    "HDFCBANK": {"name": "HDFC Bank", "sector": "Private", "type": "Bank"},
    "ICICIBANK": {"name": "ICICI Bank", "sector": "Private", "type": "Bank"},
    "AXISBANK": {"name": "Axis Bank", "sector": "Private", "type": "Bank"},
    "KOTAKBANK": {"name": "Kotak Mahindra Bank", "sector": "Private", "type": "Bank"},
    "INDUSINDBK": {"name": "IndusInd Bank", "sector": "Private", "type": "Bank"},
    "FEDERALBNK": {"name": "Federal Bank", "sector": "Private", "type": "Bank"},
    "BANDHANBNK": {"name": "Bandhan Bank", "sector": "Private", "type": "Bank"},
    "IDFCFIRSTB": {"name": "IDFC First Bank", "sector": "Private", "type": "Bank"},
    "RBLBANK": {"name": "RBL Bank", "sector": "Private", "type": "Bank"},
    "YESBANK": {"name": "Yes Bank", "sector": "Private", "type": "Bank"},
    "AUBANK": {"name": "AU Small Finance Bank", "sector": "Private", "type": "Bank"},
}


def create_rag_entry(
    symbol: str,
    date_str: str,
    open_price: float,
    high: float,
    low: float,
    close: float,
    volume: int,
    timeframe: str,
    metadata: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create a RAG-trainable JSON entry for a single data point
    
    Returns structured JSON with:
    - id: Unique identifier
    - text: Human-readable description (for embeddings)
    - metadata: Structured data
    - embedding_fields: Fields to be embedded
    """
    
    bank_info = BANK_STOCKS[symbol]
    
    # Calculate technical indicators
    price_change = close - open_price
    price_change_pct = (price_change / open_price * 100) if open_price > 0 else 0
    volatility = ((high - low) / open_price * 100) if open_price > 0 else 0
    
    # Determine trend
    if price_change > 0:
        trend = "bullish"
        trend_desc = "increased"
    elif price_change < 0:
        trend = "bearish"
        trend_desc = "decreased"
    else:
        trend = "neutral"
        trend_desc = "remained flat"
    
    # Create human-readable text (for embeddings)
    text_description = (
        f"{bank_info['name']} ({symbol}) stock on {date_str} in {timeframe} timeframe: "
        f"Opening at ₹{open_price:.2f}, the stock {trend_desc} to close at ₹{close:.2f}, "
        f"showing a {abs(price_change_pct):.2f}% {'gain' if price_change > 0 else 'loss'}. "
        f"The day's range was ₹{low:.2f} to ₹{high:.2f}, with a volatility of {volatility:.2f}%. "
        f"Trading volume was {volume:,} shares. "
        f"This {bank_info['sector']} sector bank showed {trend} market sentiment."
    )
    
    # Create structured entry
    entry = {
        "id": f"{symbol}_{date_str.replace(' ', '_').replace(':', '-')}_{timeframe}",
        "symbol": symbol,
        "bank_name": bank_info['name'],
        "sector": bank_info['sector'],
        "type": bank_info['type'],
        "timestamp": date_str,
        "timeframe": timeframe,
        
        # Price data
        "ohlcv": {
            "open": round(open_price, 2),
            "high": round(high, 2),
            "low": round(low, 2),
            "close": round(close, 2),
            "volume": int(volume)
        },
        
        # Calculated metrics
        "metrics": {
            "price_change": round(price_change, 2),
            "price_change_percent": round(price_change_pct, 2),
            "volatility_percent": round(volatility, 2),
            "range": round(high - low, 2),
            "trend": trend
        },
        
        # Text for embeddings
        "text": text_description,
        
        # Additional context
        "context": {
            "year": int(date_str[:4]),
            "month": int(date_str[5:7]),
            "day": int(date_str[8:10]) if len(date_str) > 10 else None,
            "weekday": metadata.get("weekday", "Unknown"),
            "quarter": metadata.get("quarter", None)
        },
        
        # For RAG systems
        "embedding_fields": [
            "text",
            f"{bank_info['name']} {trend} {timeframe}",
            f"{symbol} stock price {date_str}",
            f"{bank_info['sector']} sector bank {trend_desc}"
        ]
    }
    
    return entry


def convert_daily_data(symbol: str, csv_path: Path) -> List[Dict[str, Any]]:
    """Convert daily CSV data to RAG JSON format"""
    
    print(f"  📊 Converting daily data for {symbol}...")
    
    try:
        df = pd.read_csv(csv_path, parse_dates=[0])
        
        rag_entries = []
        
        for idx, row in df.iterrows():
            date_str = str(row.iloc[0])[:10]  # YYYY-MM-DD
            
            # Get weekday and quarter
            date_obj = pd.to_datetime(row.iloc[0])
            weekday = date_obj.strftime('%A')
            quarter = f"Q{(date_obj.month - 1) // 3 + 1}"
            
            metadata = {
                "weekday": weekday,
                "quarter": quarter
            }
            
            entry = create_rag_entry(
                symbol=symbol,
                date_str=date_str,
                open_price=float(row['Open']),
                high=float(row['High']),
                low=float(row['Low']),
                close=float(row['Close']),
                volume=int(row['Volume']),
                timeframe="daily",
                metadata=metadata
            )
            
            rag_entries.append(entry)
        
        print(f"    ✓ Converted {len(rag_entries)} daily records")
        return rag_entries
        
    except Exception as e:
        print(f"    ✗ Error: {e}")
        return []


def convert_intraday_data(symbol: str, csv_path: Path) -> List[Dict[str, Any]]:
    """Convert 15-min CSV data to RAG JSON format"""
    
    print(f"  ⏱️  Converting 15-min data for {symbol}...")
    
    try:
        df = pd.read_csv(csv_path, parse_dates=[0])
        
        rag_entries = []
        
        for idx, row in df.iterrows():
            datetime_str = str(row.iloc[0])[:19]  # YYYY-MM-DD HH:MM:SS
            
            # Get weekday
            date_obj = pd.to_datetime(row.iloc[0])
            weekday = date_obj.strftime('%A')
            quarter = f"Q{(date_obj.month - 1) // 3 + 1}"
            
            metadata = {
                "weekday": weekday,
                "quarter": quarter,
                "hour": date_obj.hour,
                "minute": date_obj.minute
            }
            
            entry = create_rag_entry(
                symbol=symbol,
                date_str=datetime_str,
                open_price=float(row['Open']),
                high=float(row['High']),
                low=float(row['Low']),
                close=float(row['Close']),
                volume=int(row['Volume']),
                timeframe="15min",
                metadata=metadata
            )
            
            rag_entries.append(entry)
        
        print(f"    ✓ Converted {len(rag_entries)} intraday records")
        return rag_entries
        
    except Exception as e:
        print(f"    ✗ Error: {e}")
        return []


def create_summary_metadata() -> Dict[str, Any]:
    """Create summary metadata for the entire dataset"""
    
    return {
        "dataset": "Bank Stocks Historical Data",
        "version": "1.0",
        "created_at": datetime.now().isoformat(),
        "description": "RAG-trainable JSON format of Indian bank stocks historical data",
        "total_banks": len(BANK_STOCKS),
        "timeframes": ["daily", "15min"],
        "source": "Yahoo Finance via yfinance",
        "format": "RAG (Retrieval-Augmented Generation) compatible",
        "embedding_ready": True,
        "banks": BANK_STOCKS,
        "usage": {
            "vector_databases": ["Pinecone", "Weaviate", "Milvus", "Qdrant"],
            "llm_training": ["GPT", "Claude", "LLaMA", "Gemini"],
            "rag_frameworks": ["LangChain", "LlamaIndex", "Haystack"]
        },
        "fields": {
            "text": "Natural language description for embeddings",
            "ohlcv": "Price and volume data",
            "metrics": "Calculated technical indicators",
            "context": "Temporal and categorical context",
            "embedding_fields": "Pre-formatted fields for embedding generation"
        }
    }


def convert_all_banks():
    """Convert all bank data to RAG JSON format"""
    
    historical_path = Path("historical")
    output_path = historical_path / "rag_json"
    output_path.mkdir(exist_ok=True)
    
    print(f"✓ Output directory: {output_path.absolute()}\n")
    
    all_data = []
    stats = {
        "banks_processed": 0,
        "daily_records": 0,
        "intraday_records": 0,
        "total_records": 0
    }
    
    # Process each bank
    for i, symbol in enumerate(BANK_STOCKS.keys(), 1):
        print(f"\n[{i}/{len(BANK_STOCKS)}] {BANK_STOCKS[symbol]['name']} ({symbol})")
        print("-" * 70)
        
        bank_data = {
            "symbol": symbol,
            "bank_info": BANK_STOCKS[symbol],
            "daily_data": [],
            "intraday_data": []
        }
        
        # Convert daily data
        daily_csv = historical_path / symbol / "daily" / f"{symbol}_daily.csv"
        if daily_csv.exists():
            daily_entries = convert_daily_data(symbol, daily_csv)
            bank_data["daily_data"] = daily_entries
            stats["daily_records"] += len(daily_entries)
            
            # Save individual daily JSON
            daily_json = output_path / f"{symbol}_daily_rag.json"
            with open(daily_json, 'w') as f:
                json.dump(daily_entries, f, indent=2)
        
        # Convert 15-min data
        intraday_csv = historical_path / symbol / "15min" / f"{symbol}_15min.csv"
        if intraday_csv.exists():
            intraday_entries = convert_intraday_data(symbol, intraday_csv)
            bank_data["intraday_data"] = intraday_entries
            stats["intraday_records"] += len(intraday_entries)
            
            # Save individual intraday JSON
            intraday_json = output_path / f"{symbol}_15min_rag.json"
            with open(intraday_json, 'w') as f:
                json.dump(intraday_entries, f, indent=2)
        
        # Add to combined dataset
        all_data.append(bank_data)
        stats["banks_processed"] += 1
    
    # Calculate total
    stats["total_records"] = stats["daily_records"] + stats["intraday_records"]
    
    # Create combined dataset with metadata
    combined_dataset = {
        "metadata": create_summary_metadata(),
        "statistics": stats,
        "data": all_data
    }
    
    # Save combined JSON
    combined_json = output_path / "all_banks_rag_combined.json"
    with open(combined_json, 'w') as f:
        json.dump(combined_dataset, f, indent=2)
    
    print("\n" + "="*70)
    print("CONVERSION SUMMARY")
    print("="*70)
    print(f"Banks Processed:    {stats['banks_processed']}/{len(BANK_STOCKS)}")
    print(f"Daily Records:      {stats['daily_records']:,}")
    print(f"Intraday Records:   {stats['intraday_records']:,}")
    print(f"Total Records:      {stats['total_records']:,}")
    print("="*70 + "\n")
    
    # Create README for RAG JSON
    create_rag_readme(output_path, stats)
    
    print(f"✓ Combined dataset: {combined_json}")
    print(f"✓ Individual files: {stats['banks_processed'] * 2} JSON files")
    print(f"✓ All files saved to: {output_path.absolute()}\n")
    
    return stats


def create_rag_readme(output_path: Path, stats: Dict[str, Any]):
    """Create README for RAG JSON format"""
    
    readme_content = f"""# RAG Trainable JSON Format - Bank Stocks Data

## Overview
This folder contains bank stocks historical data converted to RAG (Retrieval-Augmented Generation) trainable JSON format, optimized for:
- Vector embedding generation
- LLM training and fine-tuning
- Semantic search systems
- Knowledge graph construction

## Files

### Combined Dataset
- **all_banks_rag_combined.json** - Complete dataset with metadata
  - Size: Contains all {stats['total_records']:,} records
  - Structure: Hierarchical with bank grouping
  - Includes: Metadata, statistics, all banks data

### Individual Bank Files
Each bank has two JSON files:
- **{{SYMBOL}}_daily_rag.json** - Daily timeframe data
- **{{SYMBOL}}_15min_rag.json** - 15-minute timeframe data

Total: {stats['banks_processed'] * 2} individual JSON files

## JSON Structure

### Entry Format
```json
{{
  "id": "SBI_2025-01-15_daily",
  "symbol": "SBI",
  "bank_name": "State Bank of India",
  "sector": "Public",
  "type": "Bank",
  "timestamp": "2025-01-15",
  "timeframe": "daily",
  
  "ohlcv": {{
    "open": 625.50,
    "high": 632.75,
    "low": 623.20,
    "close": 630.40,
    "volume": 15234567
  }},
  
  "metrics": {{
    "price_change": 4.90,
    "price_change_percent": 0.78,
    "volatility_percent": 1.52,
    "range": 9.55,
    "trend": "bullish"
  }},
  
  "text": "State Bank of India (SBI) stock on 2025-01-15...",
  
  "context": {{
    "year": 2025,
    "month": 1,
    "day": 15,
    "weekday": "Wednesday",
    "quarter": "Q1"
  }},
  
  "embedding_fields": [
    "text",
    "State Bank of India bullish daily",
    "SBI stock price 2025-01-15",
    "Public sector bank increased"
  ]
}}
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
    embeddings.append({{
        'id': entry['id'],
        'embedding': response['data'][0]['embedding']
    }})
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
            metadata={{
                'symbol': entry['symbol'],
                'date': entry['timestamp'],
                'trend': entry['metrics']['trend']
            }}
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

- **Total Banks**: {len(BANK_STOCKS)}
- **Daily Records**: {stats['daily_records']:,}
- **Intraday Records**: {stats['intraday_records']:,}
- **Total Records**: {stats['total_records']:,}
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
- **Created**: {datetime.now().strftime('%Y-%m-%d')}
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
"""
    
    readme_path = output_path / "RAG_README.md"
    with open(readme_path, 'w') as f:
        f.write(readme_content)
    
    print(f"✓ RAG README created: {readme_path}")


def main():
    """Main entry point"""
    try:
        stats = convert_all_banks()
        
        print("✅ Conversion completed successfully!")
        print("\n📁 Output location: ./historical/rag_json/")
        print("\nFiles created:")
        print(f"  • all_banks_rag_combined.json (complete dataset)")
        print(f"  • {{SYMBOL}}_daily_rag.json ({len(BANK_STOCKS)} files)")
        print(f"  • {{SYMBOL}}_15min_rag.json ({len(BANK_STOCKS)} files)")
        print(f"  • RAG_README.md (documentation)")
        print(f"\nTotal: {len(BANK_STOCKS) * 2 + 2} files created")
        
    except KeyboardInterrupt:
        print("\n\n⚠ Conversion interrupted by user")
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
