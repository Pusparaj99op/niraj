"""
RAG Processor for NIRAJ Trading System

This module implements Retrieval-Augmented Generation (RAG) for enhanced AI trading analysis.
It provides capabilities to ingest, store, and retrieve market knowledge to augment AI responses
with relevant contextual information.
"""

import json
import time
import asyncio
import hashlib
import sqlite3
import structlog
from datetime import datetime, timedelta, timezone
from types import TracebackType
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Optional,
    Protocol,
    Sequence,
    Set,
    Tuple,
    TypedDict,
    Type,
    Union,
    cast,
)
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from numpy.typing import NDArray

from ..core.config import get_config
from .gemma3_integration import (
    Gemma3Client,
    AnalysisRequest,
    AnalysisResponse,
    AnalysisType,
)

# Configure structured logging
logger = structlog.get_logger(__name__)


FloatArray = NDArray[np.float64]


def _empty_str_list() -> List[str]:
    return []


def _empty_metadata_dict() -> Dict[str, Any]:
    return {}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _load_str_list(value: Optional[str]) -> List[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    if isinstance(parsed, list):
        elements = cast(List[Any], parsed)
        items: List[str] = []
        for element in elements:
            if isinstance(element, str):
                items.append(element)
        return items
    return []


def _load_metadata(value: Optional[str]) -> Dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    if isinstance(parsed, dict):
        return cast(Dict[str, Any], parsed)
    return {}


def _load_float_list(value: str) -> List[float]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    result: List[float] = []
    if isinstance(parsed, list):
        elements = cast(List[Any], parsed)
        for element in elements:
            try:
                result.append(float(element))
            except (TypeError, ValueError):
                continue
    return result


class EmbeddingModel(Protocol):
    def encode(self, texts: Sequence[str]) -> FloatArray:
        """Generate embeddings for the provided texts."""

        ...


class KnowledgeType(str, Enum):
    """Types of knowledge in the RAG system"""

    MARKET_NEWS = "market_news"
    TECHNICAL_ANALYSIS = "technical_analysis"
    FUNDAMENTAL_ANALYSIS = "fundamental_analysis"
    ECONOMIC_DATA = "economic_data"
    RESEARCH_REPORT = "research_report"
    TRADING_STRATEGY = "trading_strategy"
    RISK_ANALYSIS = "risk_analysis"
    MARKET_COMMENTARY = "market_commentary"
    REGULATORY_NEWS = "regulatory_news"
    EARNINGS_DATA = "earnings_data"
    ANALYST_RATING = "analyst_rating"
    PATTERN_RECOGNITION = "pattern_recognition"
    SECTOR_ANALYSIS = "sector_analysis"
    MACRO_ECONOMIC = "macro_economic"
    CRYPTOCURRENCY = "cryptocurrency"


class RetrievalMode(str, Enum):
    """Retrieval modes for different scenarios"""

    SEMANTIC_SEARCH = "semantic_search"  # Semantic similarity search
    KEYWORD_SEARCH = "keyword_search"  # Traditional keyword matching
    HYBRID_SEARCH = "hybrid_search"  # Combination of semantic and keyword
    TEMPORAL_SEARCH = "temporal_search"  # Time-based retrieval
    CONTEXTUAL_SEARCH = "contextual_search"  # Context-aware retrieval


class VectorSearchFilters(TypedDict, total=False):
    knowledge_types: List[KnowledgeType]
    symbols: List[str]
    time_range: Tuple[datetime, datetime]


class RagProcessorError(Exception):
    """Base exception for RAG processor errors"""

    def __init__(
        self, message: str, error_code: Optional[str] = None, context: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.context = context or {}
        super().__init__(self.message)


class VectorDatabaseError(RagProcessorError):
    """Exception for vector database operations"""

    pass


class EmbeddingError(RagProcessorError):
    """Exception for embedding generation errors"""

    pass


class RetrievalError(RagProcessorError):
    """Exception for knowledge retrieval errors"""

    pass


class IngestionError(RagProcessorError):
    """Exception for knowledge ingestion errors"""

    pass


@dataclass
class KnowledgeItem:
    """Individual knowledge item in the RAG system"""

    id: str
    content: str
    knowledge_type: KnowledgeType
    title: Optional[str] = None
    summary: Optional[str] = None
    source: Optional[str] = None
    timestamp: datetime = field(default_factory=_utc_now)
    symbols: List[str] = field(default_factory=_empty_str_list)
    sectors: List[str] = field(default_factory=_empty_str_list)
    tags: List[str] = field(default_factory=_empty_str_list)
    metadata: Dict[str, Any] = field(default_factory=_empty_metadata_dict)
    confidence_score: float = 1.0
    relevance_score: float = 0.0
    embedding: Optional[List[float]] = None
    content_hash: Optional[str] = None

    def __post_init__(self):
        """Post-initialization processing"""
        if not self.content_hash:
            self.content_hash = self._calculate_content_hash()

    def _calculate_content_hash(self) -> str:
        """Calculate hash of content for deduplication"""
        content_str = f"{self.content}{self.title or ''}{self.source or ''}"
        return hashlib.sha256(content_str.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "id": self.id,
            "content": self.content,
            "knowledge_type": self.knowledge_type.value,
            "title": self.title,
            "summary": self.summary,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "symbols": self.symbols,
            "sectors": self.sectors,
            "tags": self.tags,
            "metadata": self.metadata,
            "confidence_score": self.confidence_score,
            "relevance_score": self.relevance_score,
            "content_hash": self.content_hash,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeItem":
        """Create KnowledgeItem from dictionary"""
        return cls(
            id=data["id"],
            content=data["content"],
            knowledge_type=KnowledgeType(data["knowledge_type"]),
            title=data.get("title"),
            summary=data.get("summary"),
            source=data.get("source"),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            symbols=data.get("symbols", []),
            sectors=data.get("sectors", []),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
            confidence_score=data.get("confidence_score", 1.0),
            relevance_score=data.get("relevance_score", 0.0),
            content_hash=data.get("content_hash"),
        )


@dataclass
class RetrievalQuery:
    """Query for knowledge retrieval"""

    query_text: str
    knowledge_types: Optional[List[KnowledgeType]] = None
    symbols: Optional[List[str]] = None
    sectors: Optional[List[str]] = None
    time_range: Optional[Tuple[datetime, datetime]] = None
    max_results: int = 10
    min_relevance_score: float = 0.5
    retrieval_mode: RetrievalMode = RetrievalMode.SEMANTIC_SEARCH
    include_metadata: bool = True


@dataclass
class RetrievalResult:
    """Result from knowledge retrieval"""

    items: List[KnowledgeItem]
    query: RetrievalQuery
    total_found: int
    retrieval_time_ms: float
    metadata: Dict[str, Any] = field(default_factory=_empty_metadata_dict)


class VectorDatabase:
    """
    Vector database for storing and retrieving embeddings
    Using SQLite with vector similarity search
    """

    def __init__(self, db_path: str):
        """Initialize vector database"""
        self.db_path = db_path
        self.connection: Optional[sqlite3.Connection] = None
        self._init_database()

    def _init_database(self):
        """Initialize database schema"""
        try:
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.execute("PRAGMA foreign_keys = ON")

            # Create knowledge items table
            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS knowledge_items (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    knowledge_type TEXT NOT NULL,
                    title TEXT,
                    summary TEXT,
                    source TEXT,
                    timestamp TEXT NOT NULL,
                    symbols TEXT,  -- JSON array
                    sectors TEXT,  -- JSON array
                    tags TEXT,     -- JSON array
                    metadata TEXT, -- JSON object
                    confidence_score REAL DEFAULT 1.0,
                    relevance_score REAL DEFAULT 0.0,
                    content_hash TEXT UNIQUE,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    INDEX(knowledge_type),
                    INDEX(timestamp),
                    INDEX(content_hash)
                )
            """
            )

            # Create embeddings table
            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS embeddings (
                    item_id TEXT PRIMARY KEY,
                    embedding TEXT NOT NULL,  -- JSON array of floats
                    dimension INTEGER NOT NULL,
                    model_name TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (item_id) REFERENCES knowledge_items (id) ON DELETE CASCADE
                )
            """
            )

            # Create search index table for better performance
            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS search_index (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id TEXT NOT NULL,
                    term TEXT NOT NULL,
                    tf_idf_score REAL DEFAULT 0.0,
                    FOREIGN KEY (item_id) REFERENCES knowledge_items (id) ON DELETE CASCADE,
                    INDEX(term),
                    INDEX(item_id)
                )
            """
            )

            self.connection.commit()
            logger.info("Vector database initialized", db_path=self.db_path)

        except Exception as e:
            logger.error("Failed to initialize vector database", error=str(e))
            raise VectorDatabaseError(f"Database initialization failed: {str(e)}")

    def store_item(self, item: KnowledgeItem, embedding: List[float]) -> bool:
        """Store knowledge item with its embedding"""
        if not self.connection:
            raise VectorDatabaseError("Database connection is not available.")
        try:
            # Store knowledge item
            self.connection.execute(
                """
                INSERT OR REPLACE INTO knowledge_items
                (id, content, knowledge_type, title, summary, source, timestamp, symbols,
                 sectors, tags, metadata, confidence_score, relevance_score, content_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    item.id,
                    item.content,
                    item.knowledge_type.value,
                    item.title,
                    item.summary,
                    item.source,
                    item.timestamp.isoformat(),
                    json.dumps(item.symbols),
                    json.dumps(item.sectors),
                    json.dumps(item.tags),
                    json.dumps(item.metadata),
                    item.confidence_score,
                    item.relevance_score,
                    item.content_hash,
                ),
            )

            # Store embedding
            self.connection.execute(
                """
                INSERT OR REPLACE INTO embeddings
                (item_id, embedding, dimension, model_name)
                VALUES (?, ?, ?, ?)
            """,
                (
                    item.id,
                    json.dumps(embedding),
                    len(embedding),
                    "sentence-transformers",
                ),
            )

            self.connection.commit()
            return True

        except Exception as e:
            logger.error(
                "Failed to store knowledge item", item_id=item.id, error=str(e)
            )
            raise VectorDatabaseError(f"Failed to store item {item.id}: {str(e)}")

    def similarity_search(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filters: Optional[VectorSearchFilters] = None,
    ) -> List[Tuple[KnowledgeItem, float]]:
        """Perform similarity search"""
        if not self.connection:
            raise VectorDatabaseError("Database connection is not available.")
        try:
            query = (
                "SELECT k.id, k.content, k.knowledge_type, k.title, k.summary, k.source, "
                "k.timestamp, k.symbols, k.sectors, k.tags, k.metadata, "
                "k.confidence_score, e.embedding FROM knowledge_items k "
                "JOIN embeddings e ON k.id = e.item_id"
            )

            params: List[Any] = []
            conditions: List[str] = []

            if filters:
                knowledge_types = filters.get("knowledge_types")
                if knowledge_types:
                    placeholders = ",".join("?" for _ in knowledge_types)
                    conditions.append(f"k.knowledge_type IN ({placeholders})")
                    params.extend([kt.value for kt in knowledge_types])

                symbols = filters.get("symbols")
                if symbols:
                    symbol_conditions = ["k.symbols LIKE ?" for _ in symbols]
                    params.extend([f'%"{symbol}"%' for symbol in symbols])
                    if symbol_conditions:
                        conditions.append(f"({' OR '.join(symbol_conditions)})")

                time_range = filters.get("time_range")
                if time_range:
                    start_time, end_time = time_range
                    conditions.append("k.timestamp >= ? AND k.timestamp <= ?")
                    params.extend([start_time.isoformat(), end_time.isoformat()])

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            params_tuple: Tuple[Any, ...] = tuple(params)
            cursor = self.connection.execute(query, params_tuple)
            rows = cast(List[Tuple[Any, ...]], cursor.fetchall())

            results: List[Tuple[KnowledgeItem, float]] = []
            for row in rows:
                embedding_json = str(row[12])
                stored_embedding = _load_float_list(embedding_json)
                similarity = self._calculate_cosine_similarity(
                    query_embedding, stored_embedding
                )

                timestamp_str = str(row[6])
                item = KnowledgeItem(
                    id=str(row[0]),
                    content=str(row[1]),
                    knowledge_type=KnowledgeType(str(row[2])),
                    title=str(row[3]) if row[3] is not None else None,
                    summary=str(row[4]) if row[4] is not None else None,
                    source=str(row[5]) if row[5] is not None else None,
                    timestamp=datetime.fromisoformat(timestamp_str),
                    symbols=_load_str_list(cast(Optional[str], row[7])),
                    sectors=_load_str_list(cast(Optional[str], row[8])),
                    tags=_load_str_list(cast(Optional[str], row[9])),
                    metadata=_load_metadata(cast(Optional[str], row[10])),
                    confidence_score=float(row[11]),
                )
                item.relevance_score = similarity
                results.append((item, similarity))

            results.sort(key=lambda pair: pair[1], reverse=True)
            return results[:top_k]

        except Exception as e:
            logger.error("Similarity search failed", error=str(e))
            raise VectorDatabaseError(f"Similarity search failed: {str(e)}")

    def _calculate_cosine_similarity(
        self, vec1: List[float], vec2: List[float]
    ) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            vec1_np = np.array(vec1)
            vec2_np = np.array(vec2)

            dot_product = np.dot(vec1_np, vec2_np)
            magnitude1 = np.linalg.norm(vec1_np)
            magnitude2 = np.linalg.norm(vec2_np)

            if magnitude1 == 0 or magnitude2 == 0:
                return 0.0

            return dot_product / (magnitude1 * magnitude2)

        except Exception:
            return 0.0

    def get_item_count(self) -> int:
        """Get total number of items in database"""
        if not self.connection:
            return 0
        try:
            cursor = self.connection.execute("SELECT COUNT(*) FROM knowledge_items")
            count = cursor.fetchone()
            return count[0] if count else 0
        except Exception:
            return 0

    def delete_item(self, item_id: str) -> bool:
        """Delete knowledge item and its embedding"""
        if not self.connection:
            return False
        try:
            self.connection.execute(
                "DELETE FROM knowledge_items WHERE id = ?", (item_id,)
            )
            self.connection.commit()
            return True
        except Exception as e:
            logger.error("Failed to delete item", item_id=item_id, error=str(e))
            return False

    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()


class RAGProcessor:
    """
    Retrieval-Augmented Generation processor for NIRAJ trading system

    This class provides comprehensive RAG capabilities including knowledge ingestion,
    embedding generation, retrieval, and context augmentation for AI responses.
    """

    def __init__(self, gemma3_client: Optional[Gemma3Client] = None):
        """Initialize RAG processor"""
        self.gemma3_client = gemma3_client

        # Configuration
        self.db_path = get_config("ai.rag.database_path", "data/rag_knowledge.db")
        self.model_name = get_config("ai.rag.embedding_model", "all-MiniLM-L6-v2")
        self.max_context_length = get_config("ai.rag.max_context_length", 8000)
        self.default_top_k = get_config("ai.rag.default_top_k", 5)
        self.cache_ttl = get_config("ai.rag.cache_ttl", 3600)  # 1 hour

        # Initialize components
        self.vector_db: Optional[VectorDatabase] = None
        self.embedding_model: Optional[Any] = None
        self.executor = ThreadPoolExecutor(max_workers=4)

        # Performance tracking
        self.total_ingestions = 0
        self.successful_ingestions = 0
        self.total_retrievals = 0
        self.successful_retrievals = 0
        self.average_retrieval_time = 0.0

        logger.info(
            "RAG processor initialized",
            db_path=self.db_path,
            embedding_model=self.model_name,
            max_context_length=self.max_context_length,
        )

    async def __aenter__(self) -> "RAGProcessor":
        """Async context manager entry"""
        await self.initialize()
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        """Async context manager exit"""
        await self.cleanup()

    async def initialize(self):
        """Initialize RAG processor components"""
        try:
            # Initialize vector database
            self.vector_db = VectorDatabase(self.db_path)

            # Initialize embedding model in thread pool
            loop = asyncio.get_event_loop()
            self.embedding_model = await loop.run_in_executor(
                self.executor, self._load_embedding_model
            )

            logger.info("RAG processor components initialized successfully")

        except Exception as e:
            logger.error("Failed to initialize RAG processor", error=str(e))
            raise RagProcessorError(f"Initialization failed: {str(e)}")

    def _load_embedding_model(self):
        """Load sentence transformer model"""
        try:
            # Import here to avoid import errors if not installed
            from sentence_transformers import SentenceTransformer

            model = SentenceTransformer(self.model_name)
            logger.info("Embedding model loaded", model_name=self.model_name)
            return model
        except ImportError as e:
            logger.error("sentence-transformers not installed", error=str(e))
            raise EmbeddingError(
                "sentence-transformers library is required for RAG functionality"
            )
        except Exception as e:
            logger.error("Failed to load embedding model", error=str(e))
            raise EmbeddingError(f"Failed to load embedding model: {str(e)}")

    async def cleanup(self):
        """Cleanup resources"""
        try:
            if self.vector_db:
                self.vector_db.close()

            if self.executor:
                self.executor.shutdown(wait=True)

            logger.info("RAG processor cleanup completed")

        except Exception as e:
            logger.error("Error during cleanup", error=str(e))

    async def ingest_knowledge(self, items: List[KnowledgeItem]) -> Dict[str, Any]:
        """
        Ingest knowledge items into the RAG system

        Args:
            items: List of knowledge items to ingest

        Returns:
            Dictionary with ingestion results
        """
        if not self.vector_db or not self.embedding_model:
            await self.initialize()
            if not self.vector_db or not self.embedding_model:
                raise IngestionError("RAG Processor is not initialized.")

        start_time = time.time()
        successful_count = 0
        failed_count = 0
        errors: List[str] = []

        try:
            logger.info("Starting knowledge ingestion", item_count=len(items))

            # Process items in batches for better performance
            batch_size = 10
            for i in range(0, len(items), batch_size):
                batch = items[i : i + batch_size]

                try:
                    await self._process_batch(batch)
                    successful_count += len(batch)
                except Exception as e:
                    failed_count += len(batch)
                    errors.append(f"Batch {i//batch_size + 1}: {str(e)}")
                    logger.error(
                        "Batch processing failed",
                        batch_num=i // batch_size + 1,
                        error=str(e),
                    )

            processing_time = (time.time() - start_time) * 1000

            # Update metrics
            self.total_ingestions += len(items)
            self.successful_ingestions += successful_count

            result: Dict[str, Union[int, float, List[str]]] = {
                "total_items": len(items),
                "successful": successful_count,
                "failed": failed_count,
                "processing_time_ms": processing_time,
                "errors": errors,
                "database_size": self.vector_db.get_item_count() if self.vector_db else 0,
            }

            logger.info(
                "Knowledge ingestion completed",
                **{k: v for k, v in result.items() if k != "errors"},
            )

            return result

        except Exception as e:
            logger.error("Knowledge ingestion failed", error=str(e))
            raise IngestionError(f"Ingestion failed: {str(e)}")

    async def _process_batch(self, batch: List[KnowledgeItem]):
        """Process a batch of knowledge items"""
        if not self.embedding_model or not self.vector_db:
            raise IngestionError("RAG processor components are not initialized.")
        try:
            # Generate embeddings for the batch
            texts = [self._prepare_text_for_embedding(item) for item in batch]

            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                self.executor, self.embedding_model.encode, texts
            )

            # Store items with embeddings
            for item, embedding in zip(batch, embeddings):
                # Add preprocessing and validation
                processed_item = self._preprocess_knowledge_item(item)

                # Store in vector database
                self.vector_db.store_item(processed_item, embedding.tolist())

                logger.debug(
                    "Knowledge item stored",
                    item_id=item.id,
                    type=item.knowledge_type.value,
                )

        except Exception as e:
            logger.error("Batch processing failed", error=str(e))
            raise IngestionError(f"Batch processing failed: {str(e)}")

    def _prepare_text_for_embedding(self, item: KnowledgeItem) -> str:
        """Prepare text for embedding generation"""
        try:
            # Combine relevant text fields for better embeddings
            text_parts: List[str] = []

            if item.title:
                text_parts.append(f"Title: {item.title}")

            if item.summary:
                text_parts.append(f"Summary: {item.summary}")

            text_parts.append(f"Content: {item.content}")

            if item.symbols:
                text_parts.append(f"Symbols: {', '.join(item.symbols)}")

            if item.sectors:
                text_parts.append(f"Sectors: {', '.join(item.sectors)}")

            if item.tags:
                text_parts.append(f"Tags: {', '.join(item.tags)}")

            return " | ".join(text_parts)

        except Exception as e:
            logger.warning(
                "Failed to prepare text for embedding", item_id=item.id, error=str(e)
            )
            return item.content  # Fallback to content only

    def _preprocess_knowledge_item(self, item: KnowledgeItem) -> KnowledgeItem:
        """Preprocess and validate knowledge item"""
        try:
            # Clean and normalize content
            item.content = self._clean_text(item.content)

            if item.title:
                item.title = self._clean_text(item.title)

            if item.summary:
                item.summary = self._clean_text(item.summary)

            # Normalize symbols (uppercase)
            item.symbols = [
                symbol.upper().strip() for symbol in item.symbols if symbol.strip()
            ]

            # Normalize sectors
            item.sectors = [
                sector.title().strip() for sector in item.sectors if sector.strip()
            ]

            # Clean tags
            item.tags = [tag.lower().strip() for tag in item.tags if tag.strip()]

            # Validate content length
            if len(item.content) < 10:
                logger.warning("Knowledge item has very short content", item_id=item.id)
            elif len(item.content) > 50000:
                # Truncate very long content
                item.content = item.content[:50000] + "... [truncated]"
                logger.info("Truncated long content", item_id=item.id)

            return item

        except Exception as e:
            logger.error(
                "Failed to preprocess knowledge item", item_id=item.id, error=str(e)
            )
            return item  # Return original item if preprocessing fails

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        if not text:
            return ""

        # Remove excessive whitespace
        text = " ".join(text.split())

        # Remove common artifacts
        text = text.replace("\x00", "")  # Remove null characters
        text = text.replace("\r\n", "\n")  # Normalize line endings

        return text.strip()

    async def retrieve_knowledge(self, query: RetrievalQuery) -> RetrievalResult:
        """
        Retrieve relevant knowledge based on query

        Args:
            query: Retrieval query with search parameters

        Returns:
            RetrievalResult with found knowledge items
        """
        if not self.vector_db or not self.embedding_model:
            await self.initialize()
            if not self.vector_db or not self.embedding_model:
                raise RetrievalError("RAG Processor is not initialized.")

        start_time = time.time()
        self.total_retrievals += 1

        try:
            logger.debug(
                "Starting knowledge retrieval", query_text=query.query_text[:100]
            )

            # Generate query embedding
            loop = asyncio.get_event_loop()
            embedding_result = await loop.run_in_executor(
                self.executor, self.embedding_model.encode, [query.query_text]
            )
            embedding_array = cast(FloatArray, np.asarray(embedding_result, dtype=float))
            if embedding_array.size == 0:
                raise RetrievalError("Failed to generate query embedding.")
            query_vector = embedding_array[0].astype(float).tolist()

            # Prepare filters
            filters: VectorSearchFilters = {}
            if query.knowledge_types:
                filters["knowledge_types"] = list(query.knowledge_types)
            if query.symbols:
                filters["symbols"] = list(query.symbols)
            if query.time_range:
                filters["time_range"] = query.time_range

            # Perform similarity search
            search_results = self.vector_db.similarity_search(
                query_vector,
                top_k=query.max_results * 2,  # Get more results for filtering
                filters=filters,
            )

            # Filter by minimum relevance score
            filtered_results: List[Tuple[KnowledgeItem, float]] = [
                (item, score)
                for item, score in search_results
                if score >= query.min_relevance_score
            ]

            # Sort and limit results
            filtered_results.sort(key=lambda result_pair: result_pair[1], reverse=True)
            final_items = [item for item, _ in filtered_results[: query.max_results]]

            processing_time = (time.time() - start_time) * 1000

            # Update performance metrics
            self.successful_retrievals += 1
            self._update_retrieval_metrics(processing_time)

            result = RetrievalResult(
                items=final_items,
                query=query,
                total_found=len(search_results),
                retrieval_time_ms=processing_time,
                metadata=self._build_retrieval_metadata(filtered_results),
            )

            logger.info(
                "Knowledge retrieval completed",
                results_count=len(final_items),
                processing_time_ms=processing_time,
                avg_relevance=result.metadata["avg_relevance_score"],
            )

            return result

        except Exception as e:
            logger.error("Knowledge retrieval failed", error=str(e))
            raise RetrievalError(f"Retrieval failed: {str(e)}")

    def _update_retrieval_metrics(self, processing_time: float):
        """Update retrieval performance metrics"""
        try:
            if self.total_retrievals == 1:
                self.average_retrieval_time = processing_time
            else:
                total_time = (
                    self.average_retrieval_time * (self.total_retrievals - 1)
                    + processing_time
                )
                self.average_retrieval_time = total_time / self.total_retrievals
        except Exception:
            pass  # Don't fail the operation for metrics update

    def _build_retrieval_metadata(
        self, results: Sequence[Tuple[KnowledgeItem, float]]
    ) -> Dict[str, Union[int, float]]:
        scores = [float(score) for _, score in results]
        if not scores:
            return {
                "filtered_count": 0,
                "avg_relevance_score": 0.0,
                "max_relevance_score": 0.0,
                "min_relevance_score": 0.0,
            }

        return {
            "filtered_count": len(scores),
            "avg_relevance_score": float(np.mean(scores)),
            "max_relevance_score": float(max(scores)),
            "min_relevance_score": float(min(scores)),
        }

    async def augment_analysis(
        self, analysis_request: AnalysisRequest, max_context_items: Optional[int] = None
    ) -> AnalysisRequest:
        """
        Augment analysis request with relevant knowledge

        Args:
            analysis_request: Original analysis request
            max_context_items: Maximum number of context items to include

        Returns:
            Enhanced analysis request with knowledge context
        """
        try:
            max_items = max_context_items or self.default_top_k

            # Create retrieval query based on analysis request
            retrieval_query = self._create_retrieval_query_from_analysis(
                analysis_request, max_items
            )

            # Retrieve relevant knowledge
            retrieval_result = await self.retrieve_knowledge(retrieval_query)

            if not retrieval_result.items:
                logger.info("No relevant knowledge found for augmentation")
                return analysis_request

            # Build context from retrieved knowledge
            context = self._build_context_from_knowledge(
                retrieval_result.items, analysis_request.analysis_type
            )

            # Augment the analysis request
            enhanced_request = AnalysisRequest(
                analysis_type=analysis_request.analysis_type,
                input_data=analysis_request.input_data,
                context={
                    **(analysis_request.context or {}),
                    "retrieved_knowledge": context,
                    "knowledge_metadata": {
                        "items_count": len(retrieval_result.items),
                        "avg_relevance": retrieval_result.metadata.get(
                            "avg_relevance_score", 0.0
                        ),
                        "retrieval_time_ms": retrieval_result.retrieval_time_ms,
                    },
                },
                parameters=analysis_request.parameters,
                max_tokens=analysis_request.max_tokens,
                temperature=analysis_request.temperature,
                confidence_threshold=analysis_request.confidence_threshold,
                timeout=analysis_request.timeout,
            )

            logger.info(
                "Analysis request augmented with knowledge",
                knowledge_items=len(retrieval_result.items),
                context_size=len(str(context)),
            )

            return enhanced_request

        except Exception as e:
            logger.error("Failed to augment analysis request", error=str(e))
            # Return original request if augmentation fails
            return analysis_request

    def _create_retrieval_query_from_analysis(
        self, analysis_request: AnalysisRequest, max_results: int
    ) -> RetrievalQuery:
        """Create retrieval query from analysis request"""
        try:
            # Extract query text from input data
            input_data = analysis_request.input_data
            query_parts: List[str] = []

            # Extract relevant text from various fields
            for key, value in input_data.items():
                if isinstance(value, str) and value:
                    query_parts.append(f"{key}: {value}")
                elif key in {"symbol", "symbols"} and value is not None:
                    if isinstance(value, Iterable) and not isinstance(
                        value, (str, bytes)
                    ):
                        symbols_iter = cast(Iterable[Any], value)
                    else:
                        symbols_iter = [value]
                    symbol_values = [str(item).upper() for item in symbols_iter]
                    query_parts.append(f"symbols: {', '.join(symbol_values)}")

            query_text = (
                " ".join(query_parts)
                if query_parts
                else str(analysis_request.input_data)
            )

            # Determine relevant knowledge types
            knowledge_types = self._get_relevant_knowledge_types(
                analysis_request.analysis_type
            )

            # Extract symbols if available
            symbols: List[str] = []
            symbol_value = input_data.get("symbol")
            if symbol_value is not None:
                symbols.append(str(symbol_value).upper())

            symbols_value = input_data.get("symbols")
            if symbols_value is not None:
                if isinstance(symbols_value, Iterable) and not isinstance(
                    symbols_value, (str, bytes)
                ):
                    for symbol in cast(Iterable[Any], symbols_value):
                        symbols.append(str(symbol).upper())
                else:
                    symbols.append(str(symbols_value).upper())

            # Set time range for recent information
            end_time = _utc_now()
            time_range = (end_time - timedelta(days=30), end_time)

            return RetrievalQuery(
                query_text=query_text,
                knowledge_types=knowledge_types,
                symbols=symbols if symbols else None,
                time_range=time_range,
                max_results=max_results,
                min_relevance_score=0.3,
                retrieval_mode=RetrievalMode.SEMANTIC_SEARCH,
            )

        except Exception as e:
            logger.error("Failed to create retrieval query", error=str(e))
            # Return basic query as fallback
            return RetrievalQuery(
                query_text=str(analysis_request.input_data), max_results=max_results
            )

    def _get_relevant_knowledge_types(
        self, analysis_type: AnalysisType
    ) -> List[KnowledgeType]:
        """Get relevant knowledge types for analysis type"""
        knowledge_type_mapping = {
            AnalysisType.MARKET_SENTIMENT: [
                KnowledgeType.MARKET_NEWS,
                KnowledgeType.MARKET_COMMENTARY,
                KnowledgeType.ANALYST_RATING,
            ],
            AnalysisType.PRICE_PREDICTION: [
                KnowledgeType.TECHNICAL_ANALYSIS,
                KnowledgeType.FUNDAMENTAL_ANALYSIS,
                KnowledgeType.PATTERN_RECOGNITION,
                KnowledgeType.MARKET_NEWS,
            ],
            AnalysisType.TECHNICAL_ANALYSIS: [
                KnowledgeType.TECHNICAL_ANALYSIS,
                KnowledgeType.PATTERN_RECOGNITION,
                KnowledgeType.TRADING_STRATEGY,
            ],
            AnalysisType.NEWS_ANALYSIS: [
                KnowledgeType.MARKET_NEWS,
                KnowledgeType.REGULATORY_NEWS,
                KnowledgeType.EARNINGS_DATA,
            ],
            AnalysisType.RISK_ASSESSMENT: [
                KnowledgeType.RISK_ANALYSIS,
                KnowledgeType.MARKET_COMMENTARY,
                KnowledgeType.MACRO_ECONOMIC,
            ],
            AnalysisType.STRATEGY_RECOMMENDATION: [
                KnowledgeType.TRADING_STRATEGY,
                KnowledgeType.MARKET_COMMENTARY,
                KnowledgeType.TECHNICAL_ANALYSIS,
            ],
        }

        return knowledge_type_mapping.get(
            analysis_type,
            [
                KnowledgeType.MARKET_NEWS,
                KnowledgeType.TECHNICAL_ANALYSIS,
                KnowledgeType.MARKET_COMMENTARY,
            ],
        )

    def _build_context_from_knowledge(
        self, items: List[KnowledgeItem], analysis_type: AnalysisType
    ) -> Dict[str, Any]:
        """Build context from retrieved knowledge items"""
        try:
            relevant_information: List[Dict[str, Any]] = []
            sources: List[str] = []
            symbols_mentioned: Set[str] = set()
            sectors_mentioned: Set[str] = set()
            knowledge_types: Set[str] = set()
            earliest_timestamp: Optional[datetime] = None
            latest_timestamp: Optional[datetime] = None

            total_content_length = 0
            max_content_per_item = (
                self.max_context_length // len(items) if items else 1000
            )
            if not max_content_per_item:
                max_content_per_item = 1000

            for item in items:
                # Limit content length to prevent token overflow
                content = item.content
                if len(content) > max_content_per_item:
                    content = content[:max_content_per_item] + "..."

                # Skip if would exceed total context length
                if total_content_length + len(content) > self.max_context_length:
                    break

                info: Dict[str, Any] = {
                    "content": content,
                    "type": item.knowledge_type.value,
                    "title": item.title,
                    "source": item.source,
                    "timestamp": item.timestamp.isoformat(),
                    "relevance_score": round(item.relevance_score, 3),
                    "symbols": list(item.symbols),
                    "sectors": list(item.sectors),
                }

                relevant_information.append(info)
                total_content_length += len(content)

                # Aggregate metadata
                if item.source:
                    sources.append(item.source)
                symbols_mentioned.update(item.symbols)
                sectors_mentioned.update(item.sectors)
                knowledge_types.add(item.knowledge_type.value)

                item_timestamp = item.timestamp
                if earliest_timestamp is None or item_timestamp < earliest_timestamp:
                    earliest_timestamp = item_timestamp
                if latest_timestamp is None or item_timestamp > latest_timestamp:
                    latest_timestamp = item_timestamp

            # Prepare final context
            context: Dict[str, Any] = {
                "relevant_information": relevant_information,
                "sources": list(dict.fromkeys(sources)),
                "symbols_mentioned": sorted(symbols_mentioned),
                "sectors_mentioned": sorted(sectors_mentioned),
                "knowledge_types": sorted(knowledge_types),
                "time_range": {
                    "earliest": earliest_timestamp.isoformat()
                    if earliest_timestamp
                    else None,
                    "latest": latest_timestamp.isoformat()
                    if latest_timestamp
                    else None,
                },
            }

            return context

        except Exception as e:
            logger.error("Failed to build context from knowledge", error=str(e))
            return {"relevant_information": [], "error": str(e)}

    async def enhanced_analysis(
        self, analysis_request: AnalysisRequest
    ) -> AnalysisResponse:
        """
        Perform enhanced analysis using RAG

        Args:
            analysis_request: Analysis request

        Returns:
            Enhanced analysis response
        """
        try:
            if not self.gemma3_client:
                raise RagProcessorError(
                    "Gemma3 client not available for enhanced analysis"
                )

            # Augment request with knowledge
            enhanced_request = await self.augment_analysis(analysis_request)

            # Perform analysis with augmented context
            response = await self.gemma3_client.analyze(enhanced_request)

            # Add RAG metadata to response
            response.metadata["rag_enhanced"] = True
            ctx = enhanced_request.context or {}
            km = ctx.get("knowledge_metadata")
            if isinstance(km, dict):
                response.metadata.update(cast(Dict[str, Any], km))

            return response

        except Exception as e:
            logger.error("Enhanced analysis failed", error=str(e))
            # Fallback to regular analysis if RAG fails
            if self.gemma3_client:
                return await self.gemma3_client.analyze(analysis_request)
            else:
                raise RagProcessorError(f"Enhanced analysis failed: {str(e)}")

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get RAG processor performance metrics"""
        try:
            ingestion_success_rate = (
                self.successful_ingestions / self.total_ingestions
                if self.total_ingestions > 0
                else 0.0
            )

            retrieval_success_rate = (
                self.successful_retrievals / self.total_retrievals
                if self.total_retrievals > 0
                else 0.0
            )

            return {
                "ingestion": {
                    "total_ingestions": self.total_ingestions,
                    "successful_ingestions": self.successful_ingestions,
                    "success_rate": ingestion_success_rate,
                },
                "retrieval": {
                    "total_retrievals": self.total_retrievals,
                    "successful_retrievals": self.successful_retrievals,
                    "success_rate": retrieval_success_rate,
                    "average_retrieval_time_ms": self.average_retrieval_time,
                },
                "database": {
                    "total_items": (
                        self.vector_db.get_item_count() if self.vector_db else 0
                    ),
                    "database_path": self.db_path,
                },
                "configuration": {
                    "embedding_model": self.model_name,
                    "max_context_length": self.max_context_length,
                    "default_top_k": self.default_top_k,
                },
            }

        except Exception as e:
            logger.error("Failed to get performance metrics", error=str(e))
            return {"error": str(e)}

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on RAG processor"""
        try:
            components: Dict[str, Dict[str, Any]] = {}
            health: Dict[str, Any] = {
                "status": "healthy",
                "components": components,
                "timestamp": _utc_now().isoformat(),
            }

            # Check vector database
            try:
                if self.vector_db:
                    item_count = self.vector_db.get_item_count()
                    components["vector_database"] = {
                        "status": "healthy",
                        "item_count": item_count,
                    }
                else:
                    components["vector_database"] = {"status": "not_initialized"}
            except Exception as e:
                components["vector_database"] = {
                    "status": "unhealthy",
                    "error": str(e),
                }

            # Check embedding model
            try:
                if self.embedding_model:
                    # Test embedding generation
                    test_embedding = await asyncio.get_event_loop().run_in_executor(
                        self.executor, self.embedding_model.encode, ["test"]
                    )
                    components["embedding_model"] = {
                        "status": "healthy",
                        "model_name": self.model_name,
                        "embedding_dimension": len(test_embedding[0]),
                    }
                else:
                    components["embedding_model"] = {"status": "not_initialized"}
            except Exception as e:
                components["embedding_model"] = {
                    "status": "unhealthy",
                    "error": str(e),
                }

            # Check Gemma3 client
            if self.gemma3_client:
                gemma3_health = await self.gemma3_client.health_check()
                components["gemma3_client"] = gemma3_health
            else:
                components["gemma3_client"] = {"status": "not_configured"}

            # Determine overall status
            component_statuses: List[str] = [
                str(comp.get("status", "unknown")) for comp in components.values()
            ]
            if any(status == "unhealthy" for status in component_statuses):
                health["status"] = "unhealthy"
            elif any(
                status in ["not_initialized", "not_configured"]
                for status in component_statuses
            ):
                health["status"] = "degraded"

            # Add performance metrics
            health["metrics"] = self.get_performance_metrics()

            return health

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": _utc_now().isoformat(),
            }


# Global RAG processor instance
rag_processor = RAGProcessor()


# Convenience functions
async def ingest_market_knowledge(items: List[KnowledgeItem]) -> Dict[str, Any]:
    """Ingest market knowledge items"""
    async with rag_processor:
        return await rag_processor.ingest_knowledge(items)


async def retrieve_market_knowledge(
    query: str,
    knowledge_types: Optional[List[KnowledgeType]] = None,
    symbols: Optional[List[str]] = None,
    max_results: int = 5,
) -> RetrievalResult:
    """Retrieve market knowledge"""
    retrieval_query = RetrievalQuery(
        query_text=query,
        knowledge_types=knowledge_types,
        symbols=symbols,
        max_results=max_results,
    )

    async with rag_processor:
        return await rag_processor.retrieve_knowledge(retrieval_query)


async def enhanced_market_analysis(
    analysis_request: AnalysisRequest,
) -> AnalysisResponse:
    """Perform enhanced market analysis with RAG"""
    from .gemma3_integration import gemma3_client

    rag_processor.gemma3_client = gemma3_client
    async with rag_processor:
        return await rag_processor.enhanced_analysis(analysis_request)


async def check_rag_health() -> Dict[str, Any]:
    """Check RAG processor health"""
    return await rag_processor.health_check()


# Example usage and testing
async def example_usage():
    """Example usage of RAG processor"""

    # Example knowledge items
    knowledge_items = [
        KnowledgeItem(
            id="news_001",
            content="Bank Nifty shows strong bullish momentum with RSI at 68. Technical indicators suggest continuation of uptrend.",
            knowledge_type=KnowledgeType.TECHNICAL_ANALYSIS,
            title="Bank Nifty Technical Analysis",
            symbols=["BANKNIFTY"],
            sectors=["Banking"],
            tags=["bullish", "rsi", "uptrend"],
            metadata={"analyst": "NIRAJ", "confidence": 0.85},
        ),
        KnowledgeItem(
            id="news_002",
            content="RBI policy meeting expected to maintain status quo on interest rates. Banking stocks likely to remain stable.",
            knowledge_type=KnowledgeType.MARKET_NEWS,
            title="RBI Policy Impact on Banking Sector",
            symbols=["BANKNIFTY", "SBIN", "HDFCBANK"],
            sectors=["Banking"],
            tags=["rbi", "policy", "interest_rates"],
            metadata={"source": "Economic Times"},
        ),
    ]

    async with rag_processor:
        # Ingest knowledge
        ingestion_result = await rag_processor.ingest_knowledge(knowledge_items)
        print("Ingestion Result:", ingestion_result)

        # Retrieve knowledge
        retrieval_query = RetrievalQuery(
            query_text="Bank Nifty technical analysis",
            symbols=["BANKNIFTY"],
            max_results=5,
        )

        retrieval_result = await rag_processor.retrieve_knowledge(retrieval_query)
        print("Retrieved Items:", len(retrieval_result.items))

        # Enhanced analysis (if Gemma3 client is available)
        if rag_processor.gemma3_client:
            from .gemma3_integration import AnalysisRequest, AnalysisType

            analysis_request = AnalysisRequest(
                analysis_type=AnalysisType.TECHNICAL_ANALYSIS,
                input_data={
                    "symbol": "BANKNIFTY",
                    "current_price": 45250.0,
                    "indicators": {"rsi": 68.5, "macd": 0.15},
                },
            )

            enhanced_response = await rag_processor.enhanced_analysis(analysis_request)
            print("Enhanced Analysis:", enhanced_response.result)

        # Health check
        health = await rag_processor.health_check()
        print("Health Status:", health["status"])

        # Performance metrics
        metrics = rag_processor.get_performance_metrics()
        print("Performance Metrics:", metrics)


if __name__ == "__main__":
    # Run example usage
    asyncio.run(example_usage())
