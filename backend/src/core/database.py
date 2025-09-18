"""
NIRAJ Database Configuration and Schema
SQLite database setup with SQLAlchemy ORM
"""
from typing import AsyncGenerator, Optional
import os
from pathlib import Path
from contextlib import asynccontextmanager

from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker
import structlog

logger = structlog.get_logger()

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/niraj.db")
ASYNC_DATABASE_URL = os.getenv("ASYNC_DATABASE_URL", "sqlite+aiosqlite:///./data/niraj.db")

# Create data directory if it doesn't exist
data_dir = Path("./data")
data_dir.mkdir(exist_ok=True)

# SQLAlchemy configuration
metadata = MetaData()
Base = declarative_base(metadata=metadata)

# Synchronous engine for migrations and setup
sync_engine = create_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL query logging
    pool_pre_ping=True,
    pool_recycle=3600,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

# Asynchronous engine for application runtime
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=3600,
    connect_args={"check_same_thread": False} if "sqlite" in ASYNC_DATABASE_URL else {}
)

# Session makers
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)
AsyncSessionLocal = async_sessionmaker(
    async_engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)


def get_sync_session():
    """Get synchronous database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Get asynchronous database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for database sessions"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error("Database session error", error=str(e))
            raise
        finally:
            await session.close()


async def init_database():
    """Initialize database with all tables"""
    try:
        # Import all models to ensure they are registered
        from src.models import (
            user, security, market_data, technical_indicator,
            strategy, strategy_signal, trade, portfolio,
            ai_model, ai_prediction, risk_metric, audit_log, configuration
        )
        
        # Create all tables
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error("Failed to initialize database", error=str(e))
        raise


async def drop_database():
    """Drop all database tables (use with caution!)"""
    try:
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            
        logger.warning("Database dropped successfully")
        
    except Exception as e:
        logger.error("Failed to drop database", error=str(e))
        raise


async def recreate_database():
    """Drop and recreate database (development only!)"""
    logger.warning("Recreating database - all data will be lost!")
    await drop_database()
    await init_database()


class DatabaseManager:
    """Database manager for NIRAJ system"""
    
    def __init__(self):
        self.sync_engine = sync_engine
        self.async_engine = async_engine
        self.sync_session_factory = SessionLocal
        self.async_session_factory = AsyncSessionLocal
    
    async def health_check(self) -> bool:
        """Check database connectivity"""
        try:
            async with self.async_session_factory() as session:
                await session.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error("Database health check failed", error=str(e))
            return False
    
    async def get_table_counts(self) -> dict:
        """Get row counts for all tables (development/monitoring)"""
        counts = {}
        try:
            async with self.async_session_factory() as session:
                # This would be populated as models are created
                # Example: counts['users'] = await session.execute(select(func.count(User.id))).scalar()
                pass
        except Exception as e:
            logger.error("Failed to get table counts", error=str(e))
        
        return counts
    
    def backup_database(self, backup_path: Optional[str] = None) -> str:
        """Create database backup (SQLite only)"""
        if "sqlite" not in DATABASE_URL:
            raise NotImplementedError("Backup only supported for SQLite")
        
        if backup_path is None:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"./data/backups/niraj_backup_{timestamp}.db"
        
        # Create backup directory
        backup_dir = Path(backup_path).parent
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            import shutil
            db_path = DATABASE_URL.replace("sqlite:///", "")
            shutil.copy2(db_path, backup_path)
            logger.info("Database backup created", backup_path=backup_path)
            return backup_path
        except Exception as e:
            logger.error("Database backup failed", error=str(e))
            raise


# Global database manager instance
db_manager = DatabaseManager()

# Database dependency for FastAPI
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions"""
    async for session in get_async_session():
        yield session


# Configuration for different environments
DATABASE_CONFIGS = {
    "development": {
        "echo": True,
        "pool_pre_ping": True,
    },
    "production": {
        "echo": False,
        "pool_pre_ping": True,
        "pool_recycle": 1800,
    },
    "testing": {
        "echo": False,
        "database_url": "sqlite+aiosqlite:///./data/test_niraj.db"
    }
}