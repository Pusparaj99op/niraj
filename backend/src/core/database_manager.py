"""
NIRAJ Advanced Database Manager
Comprehensive database management system with connection pooling, error handling,
migrations, health monitoring, and advanced operations.
"""

import asyncio
import time
import hashlib
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, TypeVar, Union, Callable

from sqlalchemy import create_engine, text, event, inspect, func
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool, QueuePool
from sqlalchemy.exc import (
    IntegrityError as SQLIntegrityError,
    OperationalError,
    DisconnectionError,
)
from pydantic import BaseModel
import structlog
import backoff

from .database import metadata
from .config import get_config

logger = structlog.get_logger(__name__)

# Type variables for generic operations
T = TypeVar("T", bound=BaseModel)
ORM_T = TypeVar("ORM_T")


# Database exceptions
class DatabaseManagerError(Exception):
    """Base exception for database manager errors"""

    pass


class ConnectionError(DatabaseManagerError):
    """Database connection error"""

    pass


class MigrationError(DatabaseManagerError):
    """Database migration error"""

    pass


class TransactionError(DatabaseManagerError):
    """Database transaction error"""

    pass


class ValidationError(DatabaseManagerError):
    """Data validation error"""

    pass


class IntegrityError(DatabaseManagerError):
    """Data integrity error"""

    pass


# Migration models
class Migration(BaseModel):
    """Database migration model"""

    version: str
    name: str
    description: str
    up_sql: str
    down_sql: str
    checksum: str
    created_at: datetime


class ConnectionPool:
    """Advanced connection pool with health monitoring"""

    def __init__(
        self,
        database_url: str,
        pool_size: int = 10,
        max_overflow: int = 20,
        pool_timeout: int = 30,
        pool_recycle: int = 3600,
        pool_pre_ping: bool = True,
    ):
        self.database_url = database_url
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.pool_recycle = pool_recycle
        self.pool_pre_ping = pool_pre_ping

        self._sync_engine = None
        self._async_engine = None
        self._health_check_interval = 60  # seconds
        self._last_health_check = 0
        self._is_healthy = True

    def get_sync_engine(self) -> Any:
        """Get synchronous database engine with connection pooling"""
        if self._sync_engine is None:
            connect_args = {}
            engine_kwargs = {
                "pool_recycle": self.pool_recycle,
                "pool_pre_ping": self.pool_pre_ping,
                "echo": get_config("database.echo", False),
            }

            if "sqlite" in self.database_url:
                connect_args = {"check_same_thread": False}
                engine_kwargs.update(
                    {"poolclass": StaticPool, "connect_args": connect_args}
                )
            else:
                engine_kwargs.update(
                    {
                        "poolclass": QueuePool,
                        "pool_size": self.pool_size,
                        "max_overflow": self.max_overflow,
                        "pool_timeout": self.pool_timeout,
                        "connect_args": connect_args,
                    }
                )

            self._sync_engine = create_engine(self.database_url, **engine_kwargs)

            # Add connection event listeners
            event.listen(self._sync_engine, "connect", self._on_connect)
            event.listen(self._sync_engine, "checkout", self._on_checkout)
            event.listen(self._sync_engine, "checkin", self._on_checkin)

        return self._sync_engine

    def get_async_engine(self) -> AsyncEngine:
        """Get asynchronous database engine with connection pooling"""
        if self._async_engine is None:
            async_url = self.database_url
            if "sqlite:" in async_url and "aiosqlite" not in async_url:
                async_url = async_url.replace("sqlite:", "sqlite+aiosqlite:")

            engine_kwargs = {
                "pool_recycle": self.pool_recycle,
                "pool_pre_ping": self.pool_pre_ping,
                "echo": get_config("database.echo", False),
            }

            if "sqlite" in async_url:
                engine_kwargs["connect_args"] = {"check_same_thread": False}
            else:
                engine_kwargs.update(
                    {
                        "pool_size": self.pool_size,
                        "max_overflow": self.max_overflow,
                        "pool_timeout": self.pool_timeout,
                    }
                )

            self._async_engine = create_async_engine(async_url, **engine_kwargs)

        return self._async_engine

    def _on_connect(self, dbapi_conn, connection_record):
        """Connection event handler"""
        logger.debug("Database connection established")

    def _on_checkout(self, dbapi_conn, connection_record, connection_proxy):
        """Connection checkout event handler"""
        connection_record.checkout_time = time.time()

    def _on_checkin(self, dbapi_conn, connection_record):
        """Connection checkin event handler"""
        if hasattr(connection_record, "checkout_time"):
            duration = time.time() - connection_record.checkout_time
            logger.debug("Connection checked in", duration=duration)

    async def health_check(self) -> bool:
        """Check connection pool health"""
        current_time = time.time()

        if current_time - self._last_health_check < self._health_check_interval:
            return self._is_healthy

        try:
            async_engine = self.get_async_engine()
            async with async_engine.begin() as conn:
                await conn.execute(text("SELECT 1"))

            self._is_healthy = True
            self._last_health_check = current_time
            logger.debug("Database health check passed")

        except Exception as e:
            self._is_healthy = False
            logger.error("Database health check failed", error=str(e))

        return self._is_healthy

    def get_pool_status(self) -> Dict[str, Any]:
        """Get connection pool status"""
        sync_engine = self.get_sync_engine()
        pool = sync_engine.pool

        # Handle different pool types
        if hasattr(pool, "size"):
            # QueuePool and similar
            return {
                "pool_size": pool.size(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "checked_in": pool.checkedin(),
                "invalid": getattr(pool, "_invalidated", 0),
                "is_healthy": self._is_healthy,
                "last_health_check": datetime.fromtimestamp(self._last_health_check),
                "pool_type": type(pool).__name__,
            }
        else:
            # StaticPool (SQLite)
            return {
                "pool_size": self.pool_size,
                "checked_out": getattr(pool, "_checkedout", 0),
                "overflow": 0,  # StaticPool doesn't have overflow
                "checked_in": 0,  # StaticPool manages connections differently
                "invalid": 0,
                "is_healthy": self._is_healthy,
                "last_health_check": datetime.fromtimestamp(self._last_health_check),
                "pool_type": type(pool).__name__,
            }


class TransactionManager:
    """Advanced transaction manager with retry logic"""

    def __init__(self, session_factory):
        self.session_factory = session_factory

    @asynccontextmanager
    async def transaction(
        self, isolation_level: Optional[str] = None, rollback_on_exception: bool = True
    ):
        """Async transaction context manager"""
        async with self.session_factory() as session:
            if isolation_level:
                await session.execute(
                    text(f"SET TRANSACTION ISOLATION LEVEL {isolation_level}")
                )

            try:
                yield session
                await session.commit()
                logger.debug("Transaction committed successfully")

            except Exception as e:
                if rollback_on_exception:
                    await session.rollback()
                    logger.error("Transaction rolled back", error=str(e))
                raise TransactionError(f"Transaction failed: {str(e)}") from e

    @backoff.on_exception(
        backoff.expo, (OperationalError, DisconnectionError), max_tries=3, max_time=30
    )
    async def execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """Execute database operation with retry logic"""
        try:
            return await func(*args, **kwargs)
        except (OperationalError, DisconnectionError) as e:
            logger.warning("Database operation failed, retrying", error=str(e))
            raise
        except Exception as e:
            logger.error("Database operation failed permanently", error=str(e))
            raise TransactionError(f"Operation failed: {str(e)}") from e


class MigrationManager:
    """Database migration manager"""

    def __init__(self, connection_pool: ConnectionPool):
        self.connection_pool = connection_pool
        self.migrations_dir = Path("migrations")
        self.migrations_dir.mkdir(exist_ok=True)

    async def initialize_migration_table(self):
        """Initialize migration tracking table"""
        async_engine = self.connection_pool.get_async_engine()

        migration_table_sql = """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version VARCHAR(255) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            checksum VARCHAR(64) NOT NULL,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            execution_time_ms INTEGER
        )
        """

        async with async_engine.begin() as conn:
            await conn.execute(text(migration_table_sql))

        logger.info("Migration table initialized")

    def _calculate_checksum(self, sql_content: str) -> str:
        """Calculate checksum for migration content"""
        return hashlib.sha256(sql_content.encode()).hexdigest()

    def _load_migration_files(self) -> List[Migration]:
        """Load migration files from directory"""
        migrations = []

        for migration_file in sorted(self.migrations_dir.glob("*.sql")):
            parts = migration_file.stem.split("_", 2)
            if len(parts) >= 2:
                version = parts[0]
                name = "_".join(parts[1:])

                content = migration_file.read_text()
                up_sql, down_sql = self._parse_migration_content(content)

                migration = Migration(
                    version=version,
                    name=name,
                    description=f"Migration {version}: {name}",
                    up_sql=up_sql,
                    down_sql=down_sql,
                    checksum=self._calculate_checksum(up_sql),
                    created_at=datetime.now(timezone.utc),
                )

                migrations.append(migration)

        return migrations

    def _parse_migration_content(self, content: str) -> tuple[str, str]:
        """Parse migration file content into up and down SQL"""
        lines = content.split("\n")
        up_sql_lines = []
        down_sql_lines = []
        current_section = "up"

        for line in lines:
            line = line.strip()
            if line.lower().startswith("-- down"):
                current_section = "down"
                continue
            elif line.lower().startswith("-- up"):
                current_section = "up"
                continue

            if current_section == "up":
                up_sql_lines.append(line)
            else:
                down_sql_lines.append(line)

        up_sql = "\n".join(up_sql_lines).strip()
        down_sql = "\n".join(down_sql_lines).strip()

        return up_sql, down_sql

    async def get_applied_migrations(self) -> List[str]:
        """Get list of applied migration versions"""
        async_engine = self.connection_pool.get_async_engine()

        try:
            async with async_engine.begin() as conn:
                result = await conn.execute(
                    text("SELECT version FROM schema_migrations ORDER BY version")
                )
                return [row[0] for row in result]
        except Exception as e:
            logger.error("Failed to get applied migrations", error=str(e))
            return []

    async def apply_migration(self, migration: Migration) -> bool:
        """Apply a single migration"""
        async_engine = self.connection_pool.get_async_engine()
        start_time = time.time()

        try:
            async with async_engine.begin() as conn:
                # Execute migration SQL
                if migration.up_sql:
                    await conn.execute(text(migration.up_sql))

                # Record migration in tracking table
                execution_time = int((time.time() - start_time) * 1000)
                await conn.execute(
                    text(
                        """
                        INSERT INTO schema_migrations
                        (version, name, description, checksum, execution_time_ms)
                        VALUES (:version, :name, :description, :checksum, :execution_time)
                    """
                    ),
                    {
                        "version": migration.version,
                        "name": migration.name,
                        "description": migration.description,
                        "checksum": migration.checksum,
                        "execution_time": execution_time,
                    },
                )

            logger.info(
                "Migration applied successfully",
                version=migration.version,
                execution_time_ms=execution_time,
            )
            return True

        except Exception as e:
            logger.error("Migration failed", version=migration.version, error=str(e))
            raise MigrationError(
                f"Failed to apply migration {migration.version}: {str(e)}"
            )

    async def rollback_migration(self, version: str) -> bool:
        """Rollback a specific migration"""
        migrations = self._load_migration_files()
        migration_to_rollback = None

        for migration in migrations:
            if migration.version == version:
                migration_to_rollback = migration
                break

        if not migration_to_rollback:
            raise MigrationError(f"Migration {version} not found")

        if not migration_to_rollback.down_sql:
            raise MigrationError(f"Migration {version} has no rollback SQL")

        async_engine = self.connection_pool.get_async_engine()

        try:
            async with async_engine.begin() as conn:
                # Execute rollback SQL
                await conn.execute(text(migration_to_rollback.down_sql))

                # Remove migration record
                await conn.execute(
                    text("DELETE FROM schema_migrations WHERE version = :version"),
                    {"version": version},
                )

            logger.info("Migration rolled back successfully", version=version)
            return True

        except Exception as e:
            logger.error("Migration rollback failed", version=version, error=str(e))
            raise MigrationError(f"Failed to rollback migration {version}: {str(e)}")

    async def migrate(self, target_version: Optional[str] = None) -> List[str]:
        """Apply pending migrations up to target version"""
        await self.initialize_migration_table()

        available_migrations = self._load_migration_files()
        applied_migrations = await self.get_applied_migrations()

        pending_migrations = [
            m for m in available_migrations if m.version not in applied_migrations
        ]

        if target_version:
            pending_migrations = [
                m for m in pending_migrations if m.version <= target_version
            ]

        applied_versions = []
        for migration in sorted(pending_migrations, key=lambda m: m.version):
            await self.apply_migration(migration)
            applied_versions.append(migration.version)

        logger.info("Migrations completed", applied_count=len(applied_versions))
        return applied_versions


class DatabaseHealthMonitor:
    """Database health monitoring and alerting"""

    def __init__(self, connection_pool: ConnectionPool):
        self.connection_pool = connection_pool
        self.metrics = {
            "connection_count": 0,
            "query_count": 0,
            "error_count": 0,
            "average_response_time": 0.0,
            "last_error": None,
            "uptime": datetime.now(timezone.utc),
        }
        self._monitoring = False

    async def start_monitoring(self, interval: int = 60):
        """Start background health monitoring"""
        self._monitoring = True

        while self._monitoring:
            try:
                await self._collect_metrics()
                await asyncio.sleep(interval)
            except Exception as e:
                logger.error("Health monitoring error", error=str(e))
                await asyncio.sleep(interval)

    def stop_monitoring(self):
        """Stop health monitoring"""
        self._monitoring = False

    async def _collect_metrics(self):
        """Collect database metrics"""
        try:
            # Check connection pool health
            pool_status = self.connection_pool.get_pool_status()
            self.metrics["connection_count"] = pool_status["checked_out"]

            # Measure query response time
            start_time = time.time()
            is_healthy = await self.connection_pool.health_check()
            response_time = (time.time() - start_time) * 1000

            if is_healthy:
                self.metrics["average_response_time"] = (
                    self.metrics["average_response_time"] + response_time
                ) / 2
            else:
                self.metrics["error_count"] += 1
                self.metrics["last_error"] = datetime.now(timezone.utc)

            logger.debug("Health metrics collected", metrics=self.metrics)

        except Exception as e:
            self.metrics["error_count"] += 1
            self.metrics["last_error"] = datetime.now(timezone.utc)
            logger.error("Failed to collect health metrics", error=str(e))

    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status"""
        uptime_seconds = (
            datetime.now(timezone.utc) - self.metrics["uptime"]
        ).total_seconds()

        return {
            "is_healthy": self.connection_pool._is_healthy,
            "uptime_seconds": uptime_seconds,
            "connection_pool": self.connection_pool.get_pool_status(),
            "metrics": self.metrics.copy(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


class AdvancedDatabaseManager:
    """Advanced database manager with comprehensive features"""

    def __init__(
        self,
        database_url: Optional[str] = None,
        pool_size: int = 10,
        max_overflow: int = 20,
    ):
        self.database_url = database_url or get_config("database.url")

        # Initialize components
        self.connection_pool = ConnectionPool(
            database_url=self.database_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
        )

        self.transaction_manager = TransactionManager(
            self.connection_pool.get_async_engine().begin
        )

        self.migration_manager = MigrationManager(self.connection_pool)
        self.health_monitor = DatabaseHealthMonitor(self.connection_pool)

        # Session factories
        self.async_session_factory = async_sessionmaker(
            self.connection_pool.get_async_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )

        self.sync_session_factory = sessionmaker(
            bind=self.connection_pool.get_sync_engine(),
            autocommit=False,
            autoflush=False,
        )

        logger.info("Advanced Database Manager initialized", url=self.database_url)

    # Context managers for sessions
    @asynccontextmanager
    async def get_async_session(self):
        """Get async database session with automatic cleanup"""
        async with self.async_session_factory() as session:
            try:
                yield session
            except Exception as e:
                await session.rollback()
                logger.error("Session error, rolled back", error=str(e))
                raise
            finally:
                await session.close()

    @asynccontextmanager
    async def get_transaction(self, isolation_level: Optional[str] = None):
        """Get transactional session with automatic commit/rollback"""
        async with self.transaction_manager.transaction(isolation_level) as session:
            yield session

    # CRUD operations with error handling
    async def create(self, session: AsyncSession, obj: ORM_T) -> ORM_T:
        """Create a new database record"""
        try:
            session.add(obj)
            await session.flush()
            await session.refresh(obj)
            logger.debug("Record created", model=obj.__class__.__name__)
            return obj
        except SQLIntegrityError as e:
            await session.rollback()
            raise IntegrityError(f"Data integrity violation: {str(e)}") from e
        except Exception as e:
            await session.rollback()
            raise DatabaseManagerError(f"Failed to create record: {str(e)}") from e

    async def read(
        self, session: AsyncSession, model: Type[ORM_T], obj_id: Union[int, str]
    ) -> Optional[ORM_T]:
        """Read a database record by ID"""
        try:
            result = await session.get(model, obj_id)
            if result:
                logger.debug("Record found", model=model.__name__, id=obj_id)
            else:
                logger.debug("Record not found", model=model.__name__, id=obj_id)
            return result
        except Exception as e:
            raise DatabaseManagerError(f"Failed to read record: {str(e)}") from e

    async def update(
        self, session: AsyncSession, obj: ORM_T, update_data: Dict[str, Any]
    ) -> ORM_T:
        """Update a database record"""
        try:
            for key, value in update_data.items():
                if hasattr(obj, key):
                    setattr(obj, key, value)

            await session.flush()
            await session.refresh(obj)
            logger.debug("Record updated", model=obj.__class__.__name__)
            return obj
        except SQLIntegrityError as e:
            await session.rollback()
            raise IntegrityError(f"Data integrity violation: {str(e)}") from e
        except Exception as e:
            await session.rollback()
            raise DatabaseManagerError(f"Failed to update record: {str(e)}") from e

    async def delete(self, session: AsyncSession, obj: ORM_T) -> bool:
        """Delete a database record"""
        try:
            await session.delete(obj)
            await session.flush()
            logger.debug("Record deleted", model=obj.__class__.__name__)
            return True
        except Exception as e:
            await session.rollback()
            raise DatabaseManagerError(f"Failed to delete record: {str(e)}") from e

    async def bulk_insert(
        self, session: AsyncSession, model: Type[ORM_T], data_list: List[Dict[str, Any]]
    ) -> List[ORM_T]:
        """Bulk insert records for better performance"""
        try:
            objects = [model(**data) for data in data_list]
            session.add_all(objects)
            await session.flush()

            # Refresh objects to get generated IDs
            for obj in objects:
                await session.refresh(obj)

            logger.info(
                "Bulk insert completed", model=model.__name__, count=len(objects)
            )
            return objects

        except SQLIntegrityError as e:
            await session.rollback()
            raise IntegrityError(f"Bulk insert integrity violation: {str(e)}") from e
        except Exception as e:
            await session.rollback()
            raise DatabaseManagerError(f"Bulk insert failed: {str(e)}") from e

    # Advanced query methods
    async def execute_raw_sql(
        self, session: AsyncSession, sql: str, params: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Execute raw SQL with parameters"""
        try:
            if params:
                result = await session.execute(text(sql), params)
            else:
                result = await session.execute(text(sql))

            logger.debug("Raw SQL executed", sql=sql[:100])
            return result

        except Exception as e:
            await session.rollback()
            raise DatabaseManagerError(f"Raw SQL execution failed: {str(e)}") from e

    async def count_records(
        self,
        session: AsyncSession,
        model: Type[ORM_T],
        filters: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Count records with optional filters"""
        try:
            query = session.query(func.count(model.id))

            if filters:
                for key, value in filters.items():
                    if hasattr(model, key):
                        query = query.filter(getattr(model, key) == value)

            result = await query.scalar()
            logger.debug("Count query executed", model=model.__name__, count=result)
            return result or 0

        except Exception as e:
            raise DatabaseManagerError(f"Count query failed: {str(e)}") from e

    # Database administration
    async def initialize_database(self) -> bool:
        """Initialize database with all tables and default data"""
        try:
            # Create all tables
            async_engine = self.connection_pool.get_async_engine()
            async with async_engine.begin() as conn:
                await conn.run_sync(metadata.create_all)

            # Run migrations
            await self.migration_manager.migrate()

            logger.info("Database initialized successfully")
            return True

        except Exception as e:
            logger.error("Database initialization failed", error=str(e))
            raise DatabaseManagerError(
                f"Database initialization failed: {str(e)}"
            ) from e

    async def backup_database(self, backup_path: Optional[str] = None) -> str:
        """Create database backup"""
        if "sqlite" not in self.database_url:
            raise NotImplementedError("Backup currently only supports SQLite")

        if backup_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"./data/backups/niraj_backup_{timestamp}.db"

        backup_dir = Path(backup_path).parent
        backup_dir.mkdir(parents=True, exist_ok=True)

        try:
            import shutil

            source_db = self.database_url.replace("sqlite:///", "")
            shutil.copy2(source_db, backup_path)

            logger.info("Database backup created", backup_path=backup_path)
            return backup_path

        except Exception as e:
            raise DatabaseManagerError(f"Backup failed: {str(e)}") from e

    async def restore_database(self, backup_path: str) -> bool:
        """Restore database from backup"""
        if "sqlite" not in self.database_url:
            raise NotImplementedError("Restore currently only supports SQLite")

        if not Path(backup_path).exists():
            raise DatabaseManagerError(f"Backup file not found: {backup_path}")

        try:
            import shutil

            target_db = self.database_url.replace("sqlite:///", "")

            # Stop monitoring during restore
            self.health_monitor.stop_monitoring()

            # Close all connections
            await self.connection_pool.get_async_engine().dispose()

            # Restore backup
            shutil.copy2(backup_path, target_db)

            # Reinitialize connection pool
            self.connection_pool = ConnectionPool(
                database_url=self.database_url,
                pool_size=self.connection_pool.pool_size,
                max_overflow=self.connection_pool.max_overflow,
            )

            logger.info("Database restored successfully", backup_path=backup_path)
            return True

        except Exception as e:
            raise DatabaseManagerError(f"Restore failed: {str(e)}") from e

    # Health and monitoring
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive database health check"""
        health_status = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database_url": self.database_url.split("@")[-1],  # Hide credentials
            "connection_pool": self.connection_pool.get_pool_status(),
            "is_healthy": False,
            "response_time_ms": 0,
            "error": None,
        }

        start_time = time.time()

        try:
            # Test database connectivity
            is_connected = await self.connection_pool.health_check()

            if is_connected:
                # Test basic operations
                async with self.get_async_session() as session:
                    await session.execute(text("SELECT 1"))

                health_status["is_healthy"] = True
                health_status["response_time_ms"] = round(
                    (time.time() - start_time) * 1000, 2
                )

        except Exception as e:
            health_status["error"] = str(e)
            health_status["response_time_ms"] = round(
                (time.time() - start_time) * 1000, 2
            )

        return health_status

    async def get_database_info(self) -> Dict[str, Any]:
        """Get comprehensive database information"""
        try:
            async with self.get_async_session() as session:
                # Get database version
                version_result = await session.execute(
                    text(
                        "SELECT sqlite_version()"
                        if "sqlite" in self.database_url
                        else "SELECT version()"
                    )
                )
                db_version = version_result.scalar()

                # Get table information
                inspector = inspect(self.connection_pool.get_sync_engine())
                tables = inspector.get_table_names()

                table_info = {}
                for table in tables:
                    columns = inspector.get_columns(table)
                    table_info[table] = {
                        "columns": len(columns),
                        "column_names": [col["name"] for col in columns],
                    }

                return {
                    "database_version": db_version,
                    "total_tables": len(tables),
                    "table_names": tables,
                    "table_info": table_info,
                    "connection_pool_status": self.connection_pool.get_pool_status(),
                    "health_status": await self.health_check(),
                }

        except Exception as e:
            raise DatabaseManagerError(f"Failed to get database info: {str(e)}") from e

    # Cleanup and shutdown
    async def cleanup(self):
        """Clean up resources"""
        try:
            self.health_monitor.stop_monitoring()

            # Close async engine
            if hasattr(self, "connection_pool") and self.connection_pool._async_engine:
                await self.connection_pool._async_engine.dispose()

            # Close sync engine
            if hasattr(self, "connection_pool") and self.connection_pool._sync_engine:
                self.connection_pool._sync_engine.dispose()

            logger.info("Database manager cleanup completed")

        except Exception as e:
            logger.error("Cleanup error", error=str(e))


# Global database manager instance
db_manager = None


def get_database_manager() -> AdvancedDatabaseManager:
    """Get global database manager instance"""
    global db_manager

    if db_manager is None:
        db_manager = AdvancedDatabaseManager()

    return db_manager


# FastAPI dependency
async def get_db_session():
    """FastAPI dependency for database sessions"""
    db_manager = get_database_manager()
    async with db_manager.get_async_session() as session:
        yield session


# Utility functions
async def init_database():
    """Initialize database - convenience function"""
    db_manager = get_database_manager()
    return await db_manager.initialize_database()


async def health_check():
    """Database health check - convenience function"""
    db_manager = get_database_manager()
    return await db_manager.health_check()


async def create_backup(backup_path: Optional[str] = None) -> str:
    """Create database backup - convenience function"""
    db_manager = get_database_manager()
    return await db_manager.backup_database(backup_path)


# Event handlers for application lifecycle
async def startup_handler():
    """Application startup handler"""
    try:
        db_manager = get_database_manager()

        # Initialize database
        await db_manager.initialize_database()

        # Start health monitoring
        asyncio.create_task(db_manager.health_monitor.start_monitoring())

        logger.info("Database manager startup completed")

    except Exception as e:
        logger.error("Database manager startup failed", error=str(e))
        raise


async def shutdown_handler():
    """Application shutdown handler"""
    try:
        if db_manager:
            await db_manager.cleanup()

        logger.info("Database manager shutdown completed")

    except Exception as e:
        logger.error("Database manager shutdown failed", error=str(e))
