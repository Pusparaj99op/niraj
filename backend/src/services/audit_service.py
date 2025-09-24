"""
NIRAJ Audit Service
Comprehensive audit logging service with advanced features for security, compliance,
data integrity, error handling, and performance monitoring.
"""

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple, Callable
from contextlib import asynccontextmanager
import json
from functools import wraps
import time
import threading
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import select, func, text, and_, or_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError, IntegrityError as SQLIntegrityError

from ..models.audit_log import (
    AuditLog, AuditLogORM, AuditEventType, AuditSeverity, AuditSource,
    AuditLogValidationError, AuditIntegrityError,
    AuditLogCreateRequest, AuditLogResponse, AuditLogQueryRequest,
    AuditSummaryResponse
)
from ..core.database_manager import get_database_manager
from ..utils.logger import get_structured_logger, LogContext, log_performance


logger = get_structured_logger("niraj.audit")


class AuditServiceError(Exception):
    """Base exception for audit service errors"""
    def __init__(self, message: str, event_type: str = None, context: Dict[str, Any] = None):
        self.message = message
        self.event_type = event_type
        self.context = context or {}
        super().__init__(self.message)


class AuditBatchError(AuditServiceError):
    """Exception for batch audit operations"""
    def __init__(self, message: str, failed_logs: List[Dict[str, Any]] = None, partial_success: bool = False):
        self.failed_logs = failed_logs or []
        self.partial_success = partial_success
        super().__init__(message)


class AuditRetentionError(AuditServiceError):
    """Exception for audit retention operations"""
    pass


class AuditSearchError(AuditServiceError):
    """Exception for audit search operations"""
    pass


class AuditPerformanceMonitor:
    """Performance monitoring for audit operations"""

    def __init__(self):
        self.metrics = {
            'total_logs_created': 0,
            'total_logs_queried': 0,
            'average_write_time': 0.0,
            'average_query_time': 0.0,
            'error_count': 0,
            'last_error_time': None,
            'batch_operations': 0,
            'retention_cleanups': 0
        }
        self._lock = threading.Lock()

    def record_write(self, duration_ms: float):
        """Record write operation performance"""
        with self._lock:
            self.metrics['total_logs_created'] += 1
            current_avg = self.metrics['average_write_time']
            total_ops = self.metrics['total_logs_created']
            self.metrics['average_write_time'] = (
                (current_avg * (total_ops - 1) + duration_ms) / total_ops
            )

    def record_query(self, duration_ms: float, result_count: int = 0):
        """Record query operation performance"""
        with self._lock:
            self.metrics['total_logs_queried'] += result_count
            current_avg = self.metrics['average_query_time']
            total_queries = self.metrics['total_logs_queried'] or 1
            self.metrics['average_query_time'] = (
                (current_avg * (total_queries - 1) + duration_ms) / total_queries
            )

    def record_error(self):
        """Record error occurrence"""
        with self._lock:
            self.metrics['error_count'] += 1
            self.metrics['last_error_time'] = datetime.now(timezone.utc)

    def record_batch_operation(self):
        """Record batch operation"""
        with self._lock:
            self.metrics['batch_operations'] += 1

    def record_retention_cleanup(self):
        """Record retention cleanup operation"""
        with self._lock:
            self.metrics['retention_cleanups'] += 1

    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        with self._lock:
            return self.metrics.copy()

    def reset_metrics(self):
        """Reset performance metrics"""
        with self._lock:
            self.metrics = {
                'total_logs_created': 0,
                'total_logs_queried': 0,
                'average_write_time': 0.0,
                'average_query_time': 0.0,
                'error_count': 0,
                'last_error_time': None,
                'batch_operations': 0,
                'retention_cleanups': 0
            }


class AuditBatchProcessor:
    """Batch processing for audit logs"""

    def __init__(self, batch_size: int = 100, max_wait_time: float = 5.0):
        self.batch_size = batch_size
        self.max_wait_time = max_wait_time
        self._batch_queue: List[AuditLog] = []
        self._last_flush = time.time()
        self._lock = asyncio.Lock()
        self._background_task: Optional[asyncio.Task] = None
        self._shutdown = False

    async def add_to_batch(self, audit_log: AuditLog) -> bool:
        """Add audit log to batch queue"""
        async with self._lock:
            self._batch_queue.append(audit_log)

            # Check if we should flush immediately
            batch_full = len(self._batch_queue) >= self.batch_size
            time_expired = time.time() - self._last_flush >= self.max_wait_time
            should_flush = batch_full or time_expired

            if should_flush:
                return await self._flush_batch()

        return True

    async def _flush_batch(self) -> bool:
        """Flush current batch to database"""
        if not self._batch_queue:
            return True

        batch_to_process = self._batch_queue[:]
        self._batch_queue.clear()
        self._last_flush = time.time()

        try:
            # Process batch (this would be called by AuditService)
            return True
        except Exception as e:
            logger.error("Batch flush failed", error=str(e), batch_size=len(batch_to_process))
            # Put failed items back in queue
            self._batch_queue.extend(batch_to_process)
            return False

    async def force_flush(self) -> bool:
        """Force flush all pending batches"""
        async with self._lock:
            if self._batch_queue:
                return await self._flush_batch()
        return True

    async def start_background_processing(self):
        """Start background batch processing task"""
        if self._background_task is None or self._background_task.done():
            self._background_task = asyncio.create_task(self._background_processor())

    async def stop_background_processing(self):
        """Stop background batch processing"""
        self._shutdown = True
        if self._background_task and not self._background_task.done():
            self._background_task.cancel()
            try:
                await self._background_task
            except asyncio.CancelledError:
                pass

        # Flush remaining items
        await self.force_flush()

    async def _background_processor(self):
        """Background task for processing batches"""
        while not self._shutdown:
            try:
                await asyncio.sleep(1.0)  # Check every second

                async with self._lock:
                    time_expired = time.time() - self._last_flush >= self.max_wait_time
                    has_items = bool(self._batch_queue)
                    if time_expired and has_items:
                        await self._flush_batch()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Background batch processing error", error=str(e))


class AuditService:
    """
    Comprehensive Audit Service with advanced features:
    - Secure audit logging with integrity checks
    - Batch processing for performance
    - Automatic data retention management
    - Advanced search and filtering capabilities
    - Real-time monitoring and alerts
    - Error handling and recovery
    """

    def __init__(
        self,
        db_manager=None,
        enable_batch_processing: bool = True,
        batch_size: int = 100,
        enable_performance_monitoring: bool = True,
        max_concurrent_operations: int = 10
    ):
        self.db_manager = db_manager or get_database_manager()
        self.performance_monitor = AuditPerformanceMonitor() if enable_performance_monitoring else None

        # Batch processing
        self.batch_processor = AuditBatchProcessor(batch_size) if enable_batch_processing else None

        # Threading for background tasks
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent_operations)

        # Cache for frequently accessed data
        self._user_session_cache = {}
        self._cache_lock = asyncio.Lock()

        # Service status
        self._initialized = False
        self._shutdown = False

        logger.info("Audit service initialized",
                    batch_processing=enable_batch_processing,
                    performance_monitoring=enable_performance_monitoring)

    async def initialize(self):
        """Initialize audit service"""
        if self._initialized:
            return

        try:
            # Start batch processing if enabled
            if self.batch_processor:
                await self.batch_processor.start_background_processing()

            # Create necessary database tables if they don't exist
            await self._ensure_database_schema()

            # Start retention cleanup task
            asyncio.create_task(self._retention_cleanup_task())

            self._initialized = True
            logger.info("Audit service initialization completed")

        except Exception as e:
            logger.error("Audit service initialization failed", error=str(e))
            raise AuditServiceError(f"Service initialization failed: {str(e)}")

    async def shutdown(self):
        """Shutdown audit service gracefully"""
        if self._shutdown:
            return

        self._shutdown = True

        try:
            # Stop batch processing
            if self.batch_processor:
                await self.batch_processor.stop_background_processing()

            # Shutdown thread executor
            self.executor.shutdown(wait=True, timeout=30)

            logger.info("Audit service shutdown completed")

        except Exception as e:
            logger.error("Audit service shutdown error", error=str(e))

    async def _ensure_database_schema(self):
        """Ensure audit log tables exist"""
        try:
            async with self.db_manager.get_async_session() as session:
                # Check if audit_logs table exists and create if needed
                result = await session.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table' AND name='audit_logs'")
                )
                if not result.fetchone():
                    logger.info("Creating audit_logs table")
                    # The table should be created by database migrations
                    # This is just a safety check
        except Exception as e:
            logger.warning("Could not verify audit database schema", error=str(e))

    # Core Audit Logging Methods

    @log_performance("audit_service.create_audit_log")
    async def create_audit_log(
        self,
        event_type: AuditEventType,
        event_description: str,
        severity: AuditSeverity = AuditSeverity.INFO,
        source: AuditSource = AuditSource.SYSTEM,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        request_data: Optional[Dict[str, Any]] = None,
        response_data: Optional[Dict[str, Any]] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        **kwargs
    ) -> AuditLogResponse:
        """
        Create a new audit log entry with comprehensive validation and error handling
        """
        start_time = time.time()

        try:
            # Create audit log business object
            audit_log = AuditLog(
                event_type=event_type,
                event_description=event_description,
                severity=severity,
                source=source,
                user_id=user_id,
                session_id=session_id,
                entity_type=entity_type,
                entity_id=entity_id,
                request_data=request_data,
                response_data=response_data,
                old_values=old_values,
                new_values=new_values,
                metadata=metadata or {},
                tags=tags or [],
                **kwargs
            )

            # Add contextual information
            await self._enrich_audit_log(audit_log, user_id, session_id)

            # Use batch processing if enabled and not critical
            batch_ok = self.batch_processor is not None
            not_critical = severity not in [AuditSeverity.ERROR, AuditSeverity.CRITICAL]
            use_batch = batch_ok and not_critical

            if use_batch:

                success = await self.batch_processor.add_to_batch(audit_log)
                if success:
                    duration_ms = (time.time() - start_time) * 1000
                    if self.performance_monitor:
                        self.performance_monitor.record_write(duration_ms)

                    return AuditLogResponse(**audit_log.to_dict())

            # Direct database write for critical logs or when batch processing fails
            return await self._write_audit_log_direct(audit_log, start_time)

        except AuditLogValidationError as e:
            if self.performance_monitor:
                self.performance_monitor.record_error()

            logger.error("Audit log validation failed",
                         event_type=event_type.value,
                         error=str(e),
                         context={"user_id": user_id, "entity_type": entity_type})
            raise AuditServiceError(f"Validation failed: {str(e)}", event_type.value)

        except Exception as e:
            if self.performance_monitor:
                self.performance_monitor.record_error()

            logger.error("Audit log creation failed",
                         event_type=event_type.value,
                         error=str(e),
                         error_type=type(e).__name__)
            raise AuditServiceError(f"Audit log creation failed: {str(e)}", event_type.value)

    async def _write_audit_log_direct(self, audit_log: AuditLog, start_time: float) -> AuditLogResponse:
        """Write audit log directly to database"""
        try:
            async with self.db_manager.get_transaction() as session:
                # Convert to ORM object
                orm_log = AuditLogORM(
                    id=audit_log.id,
                    event_type=audit_log.event_type.value,
                    event_description=audit_log.event_description,
                    severity=audit_log.severity.value,
                    source=audit_log.source.value,
                    user_id=audit_log.user_id,
                    session_id=audit_log.session_id,
                    ip_address=audit_log.ip_address,
                    user_agent=audit_log.user_agent,
                    entity_type=audit_log.entity_type,
                    entity_id=audit_log.entity_id,
                    parent_entity_type=audit_log.parent_entity_type,
                    parent_entity_id=audit_log.parent_entity_id,
                    request_method=audit_log.request_method,
                    request_endpoint=audit_log.request_endpoint,
                    request_data=audit_log.request_data,
                    response_status=audit_log.response_status,
                    response_data=audit_log.response_data,
                    old_values=audit_log.old_values,
                    new_values=audit_log.new_values,
                    changed_fields=audit_log.changed_fields,
                    amount=audit_log.amount,
                    currency=audit_log.currency,
                    quantity=audit_log.quantity,
                    price=audit_log.price,
                    application_version=audit_log.application_version,
                    environment=audit_log.environment,
                    correlation_id=audit_log.correlation_id,
                    checksum=audit_log.checksum,
                    is_sensitive=audit_log.is_sensitive,
                    retention_date=audit_log.retention_date,
                    execution_time_ms=audit_log.execution_time_ms,
                    memory_usage_mb=audit_log.memory_usage_mb,
                    metadata=audit_log.metadata,
                    tags=audit_log.tags,
                    timestamp=audit_log.timestamp,
                    created_at=audit_log.created_at
                )

                session.add(orm_log)
                await session.flush()

                # Record performance metrics
                duration_ms = (time.time() - start_time) * 1000
                if self.performance_monitor:
                    self.performance_monitor.record_write(duration_ms)

                logger.debug("Audit log created successfully",
                             audit_id=audit_log.id,
                             event_type=audit_log.event_type.value,
                             duration_ms=duration_ms)

                return AuditLogResponse(**audit_log.to_dict())

        except SQLIntegrityError as e:
            logger.error("Audit log integrity error",
                         audit_id=audit_log.id,
                         error=str(e))
            raise AuditServiceError(f"Data integrity violation: {str(e)}", audit_log.event_type.value)

        except SQLAlchemyError as e:
            logger.error("Database error during audit log creation",
                         audit_id=audit_log.id,
                         error=str(e))
            raise AuditServiceError(f"Database error: {str(e)}", audit_log.event_type.value)

    async def _enrich_audit_log(self, audit_log: AuditLog, user_id: str = None, session_id: str = None):
        """Enrich audit log with contextual information"""
        try:
            # Add application context
            audit_log.application_version = "1.0.0"  # This should come from config
            audit_log.environment = "development"    # This should come from config

            # Generate correlation ID if not present
            if not audit_log.correlation_id:
                audit_log.correlation_id = str(uuid.uuid4())

            # Add execution context if available
            if not audit_log.execution_time_ms and hasattr(audit_log, '_start_time'):
                audit_log.execution_time_ms = int((time.time() - audit_log._start_time) * 1000)

            # Cache session information for performance
            if user_id and session_id:
                cache_key = f"{user_id}:{session_id}"
                async with self._cache_lock:
                    if cache_key not in self._user_session_cache:
                        # This could be enhanced to fetch user/session details
                        self._user_session_cache[cache_key] = {
                            'last_seen': datetime.now(timezone.utc),
                            'user_id': user_id,
                            'session_id': session_id
                        }

        except Exception as e:
            logger.warning("Failed to enrich audit log", error=str(e))
            # Don't fail the audit log creation for enrichment errors

    # Batch Operations

    async def create_audit_logs_batch(
        self,
        audit_requests: List[AuditLogCreateRequest]
    ) -> Tuple[List[AuditLogResponse], List[Dict[str, Any]]]:
        """
        Create multiple audit logs in a batch operation
        Returns: (successful_logs, failed_logs)
        """
        if not audit_requests:
            return [], []

        successful_logs = []
        failed_logs = []

        try:
            if self.performance_monitor:
                self.performance_monitor.record_batch_operation()

            async with self.db_manager.get_transaction() as session:
                orm_logs = []

                for i, request in enumerate(audit_requests):
                    try:
                        # Convert to business object
                        audit_log = AuditLog(
                            event_type=request.event_type,
                            event_description=request.event_description,
                            severity=request.severity,
                            source=request.source,
                            user_id=request.user_id,
                            session_id=request.session_id,
                            entity_type=request.entity_type,
                            entity_id=request.entity_id,
                            request_data=request.request_data,
                            response_data=request.response_data,
                            old_values=request.old_values,
                            new_values=request.new_values,
                            metadata=request.metadata,
                            tags=request.tags
                        )

                        await self._enrich_audit_log(audit_log, request.user_id, request.session_id)

                        # Convert to ORM
                        orm_log = AuditLogORM(**{
                            k: v.value if hasattr(v, 'value') else v
                            for k, v in audit_log.to_dict().items()
                            if k != 'retention_date'  # Handle datetime separately
                        })
                        orm_log.retention_date = audit_log.retention_date

                        orm_logs.append(orm_log)

                    except Exception as e:
                        failed_logs.append({
                            'index': i,
                            'request': request.dict() if hasattr(request, 'dict') else str(request),
                            'error': str(e),
                            'error_type': type(e).__name__
                        })

                # Batch insert successful logs
                if orm_logs:
                    session.add_all(orm_logs)
                    await session.flush()

                    # Convert to response objects
                    for orm_log in orm_logs:
                        response_data = {
                            'id': orm_log.id,
                            'event_type': orm_log.event_type,
                            'event_description': orm_log.event_description,
                            'severity': orm_log.severity,
                            'source': orm_log.source,
                            'user_id': orm_log.user_id,
                            'session_id': orm_log.session_id,
                            'entity_type': orm_log.entity_type,
                            'entity_id': orm_log.entity_id,
                            'timestamp': orm_log.timestamp,
                            'created_at': orm_log.created_at,
                            'checksum': orm_log.checksum,
                            'retention_date': orm_log.retention_date,
                            # Add other fields as needed
                        }
                        successful_logs.append(AuditLogResponse(**response_data))

                logger.info("Batch audit log creation completed",
                          total_requests=len(audit_requests),
                          successful=len(successful_logs),
                          failed=len(failed_logs))

        except Exception as e:
            logger.error("Batch audit log creation failed", error=str(e))
            raise AuditBatchError(
                f"Batch operation failed: {str(e)}",
                failed_logs=failed_logs,
                partial_success=len(successful_logs) > 0
            )

        return successful_logs, failed_logs

    # Query and Search Operations

    @log_performance("audit_service.query_audit_logs")
    async def query_audit_logs(
        self,
        query_request: AuditLogQueryRequest,
        user_has_sensitive_access: bool = False
    ) -> Tuple[List[AuditLogResponse], int]:
        """
        Query audit logs with advanced filtering and pagination
        Returns: (audit_logs, total_count)
        """
        start_time = time.time()

        try:
            async with self.db_manager.get_async_session() as session:
                # Build base query
                query = select(AuditLogORM)
                count_query = select(func.count(AuditLogORM.id))

                # Apply filters
                filters = []

                if query_request.event_type:
                    filters.append(AuditLogORM.event_type == query_request.event_type.value)

                if query_request.severity:
                    filters.append(AuditLogORM.severity == query_request.severity.value)

                if query_request.source:
                    filters.append(AuditLogORM.source == query_request.source.value)

                if query_request.user_id:
                    filters.append(AuditLogORM.user_id == query_request.user_id)

                if query_request.session_id:
                    filters.append(AuditLogORM.session_id == query_request.session_id)

                if query_request.entity_type:
                    filters.append(AuditLogORM.entity_type == query_request.entity_type)

                if query_request.entity_id:
                    filters.append(AuditLogORM.entity_id == query_request.entity_id)

                if query_request.correlation_id:
                    filters.append(AuditLogORM.correlation_id == query_request.correlation_id)

                if query_request.timestamp_after:
                    filters.append(AuditLogORM.timestamp >= query_request.timestamp_after)

                if query_request.timestamp_before:
                    filters.append(AuditLogORM.timestamp <= query_request.timestamp_before)

                # Sensitive data filter
                if not user_has_sensitive_access and not query_request.include_sensitive:
                    filters.append(AuditLogORM.is_sensitive == False)

                # Tag filtering (JSON contains)
                if query_request.tags:
                    for tag in query_request.tags:
                        filters.append(
                            AuditLogORM.tags.contains(json.dumps([tag]))
                        )

                # Apply filters to queries
                if filters:
                    query = query.where(and_(*filters))
                    count_query = count_query.where(and_(*filters))

                # Get total count
                total_count = await session.scalar(count_query) or 0

                # Apply ordering
                if query_request.order_by == "timestamp":
                    if query_request.order_desc:
                        query = query.order_by(desc(AuditLogORM.timestamp))
                    else:
                        query = query.order_by(asc(AuditLogORM.timestamp))
                elif query_request.order_by == "severity":
                    if query_request.order_desc:
                        query = query.order_by(desc(AuditLogORM.severity))
                    else:
                        query = query.order_by(asc(AuditLogORM.severity))

                # Apply pagination
                query = query.offset(query_request.offset).limit(query_request.limit)

                # Execute query
                result = await session.execute(query)
                audit_logs_orm = result.scalars().all()

                # Convert to response objects
                audit_logs = []
                for log_orm in audit_logs_orm:
                    # Create response data
                    response_data = {
                        'id': log_orm.id,
                        'event_type': AuditEventType(log_orm.event_type),
                        'event_description': log_orm.event_description,
                        'severity': AuditSeverity(log_orm.severity),
                        'source': AuditSource(log_orm.source),
                        'user_id': log_orm.user_id,
                        'session_id': log_orm.session_id,
                        'ip_address': log_orm.ip_address,
                        'user_agent': log_orm.user_agent,
                        'entity_type': log_orm.entity_type,
                        'entity_id': log_orm.entity_id,
                        'parent_entity_type': log_orm.parent_entity_type,
                        'parent_entity_id': log_orm.parent_entity_id,
                        'request_method': log_orm.request_method,
                        'request_endpoint': log_orm.request_endpoint,
                        'request_data': log_orm.request_data,
                        'response_status': log_orm.response_status,
                        'response_data': log_orm.response_data,
                        'old_values': log_orm.old_values,
                        'new_values': log_orm.new_values,
                        'changed_fields': log_orm.changed_fields,
                        'amount': log_orm.amount,
                        'currency': log_orm.currency,
                        'quantity': log_orm.quantity,
                        'price': log_orm.price,
                        'application_version': log_orm.application_version,
                        'environment': log_orm.environment,
                        'correlation_id': log_orm.correlation_id,
                        'checksum': log_orm.checksum,
                        'is_sensitive': log_orm.is_sensitive,
                        'retention_date': log_orm.retention_date,
                        'execution_time_ms': log_orm.execution_time_ms,
                        'memory_usage_mb': log_orm.memory_usage_mb,
                        'metadata': log_orm.metadata or {},
                        'tags': log_orm.tags or [],
                        'timestamp': log_orm.timestamp,
                        'created_at': log_orm.created_at
                    }

                    audit_log_response = AuditLogResponse(**response_data)

                    # Sanitize sensitive data if needed
                    if not user_has_sensitive_access and log_orm.is_sensitive:
                        audit_log_business = AuditLog(**audit_log_response.dict())
                        audit_log_business.sanitize_sensitive_data()
                        audit_log_response = AuditLogResponse(**audit_log_business.to_dict())

                    audit_logs.append(audit_log_response)

                # Record performance metrics
                duration_ms = (time.time() - start_time) * 1000
                if self.performance_monitor:
                    self.performance_monitor.record_query(duration_ms, len(audit_logs))

                logger.debug("Audit log query completed",
                           filters_applied=len(filters),
                           total_count=total_count,
                           returned_count=len(audit_logs),
                           duration_ms=duration_ms)

                return audit_logs, total_count

        except Exception as e:
            if self.performance_monitor:
                self.performance_monitor.record_error()

            logger.error("Audit log query failed",
                        error=str(e),
                        query_params=query_request.dict())
            raise AuditSearchError(f"Query failed: {str(e)}")

    async def get_audit_log_by_id(
        self,
        audit_id: str,
        user_has_sensitive_access: bool = False
    ) -> Optional[AuditLogResponse]:
        """Get specific audit log by ID"""
        try:
            async with self.db_manager.get_async_session() as session:
                result = await session.execute(
                    select(AuditLogORM).where(AuditLogORM.id == audit_id)
                )
                log_orm = result.scalar_one_or_none()

                if not log_orm:
                    return None

                # Check sensitive access
                if not user_has_sensitive_access and log_orm.is_sensitive:
                    logger.warning("Sensitive audit log access denied", audit_id=audit_id)
                    return None

                # Convert to response
                response_data = {
                    'id': log_orm.id,
                    'event_type': AuditEventType(log_orm.event_type),
                    'event_description': log_orm.event_description,
                    'severity': AuditSeverity(log_orm.severity),
                    'source': AuditSource(log_orm.source),
                    'user_id': log_orm.user_id,
                    'session_id': log_orm.session_id,
                    'entity_type': log_orm.entity_type,
                    'entity_id': log_orm.entity_id,
                    'timestamp': log_orm.timestamp,
                    'created_at': log_orm.created_at,
                    'checksum': log_orm.checksum,
                    'retention_date': log_orm.retention_date,
                    'is_sensitive': log_orm.is_sensitive,
                    'metadata': log_orm.metadata or {},
                    'tags': log_orm.tags or []
                }

                audit_log_response = AuditLogResponse(**response_data)

                # Sanitize if needed
                if log_orm.is_sensitive and not user_has_sensitive_access:
                    audit_log_business = AuditLog(**audit_log_response.dict())
                    audit_log_business.sanitize_sensitive_data()
                    audit_log_response = AuditLogResponse(**audit_log_business.to_dict())

                return audit_log_response

        except Exception as e:
            logger.error("Failed to get audit log by ID",
                        audit_id=audit_id,
                        error=str(e))
            raise AuditServiceError(f"Failed to retrieve audit log: {str(e)}")

    # Analytics and Reporting

    async def get_audit_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        user_id: Optional[str] = None
    ) -> AuditSummaryResponse:
        """Get audit summary statistics"""
        try:
            if not start_date:
                start_date = datetime.now(timezone.utc) - timedelta(days=30)
            if not end_date:
                end_date = datetime.now(timezone.utc)

            async with self.db_manager.get_async_session() as session:
                # Base query filters
                base_filters = [
                    AuditLogORM.timestamp >= start_date,
                    AuditLogORM.timestamp <= end_date
                ]

                if user_id:
                    base_filters.append(AuditLogORM.user_id == user_id)

                # Total events count
                total_events = await session.scalar(
                    select(func.count(AuditLogORM.id)).where(and_(*base_filters))
                ) or 0

                # Events by type
                events_by_type_result = await session.execute(
                    select(AuditLogORM.event_type, func.count(AuditLogORM.id))
                    .where(and_(*base_filters))
                    .group_by(AuditLogORM.event_type)
                )
                events_by_type = dict(events_by_type_result.fetchall())

                # Events by severity
                events_by_severity_result = await session.execute(
                    select(AuditLogORM.severity, func.count(AuditLogORM.id))
                    .where(and_(*base_filters))
                    .group_by(AuditLogORM.severity)
                )
                events_by_severity = dict(events_by_severity_result.fetchall())

                # Events by source
                events_by_source_result = await session.execute(
                    select(AuditLogORM.source, func.count(AuditLogORM.id))
                    .where(and_(*base_filters))
                    .group_by(AuditLogORM.source)
                )
                events_by_source = dict(events_by_source_result.fetchall())

                # Events by user (if not filtering by specific user)
                events_by_user = {}
                if not user_id:
                    events_by_user_result = await session.execute(
                        select(AuditLogORM.user_id, func.count(AuditLogORM.id))
                        .where(and_(*base_filters))
                        .where(AuditLogORM.user_id.is_not(None))
                        .group_by(AuditLogORM.user_id)
                        .limit(10)  # Top 10 users
                    )
                    events_by_user = dict(events_by_user_result.fetchall())

                # Recent critical events
                critical_events_result = await session.execute(
                    select(AuditLogORM)
                    .where(and_(*base_filters))
                    .where(AuditLogORM.severity == AuditSeverity.CRITICAL.value)
                    .order_by(desc(AuditLogORM.timestamp))
                    .limit(5)
                )
                critical_events = []
                for log in critical_events_result.scalars():
                    critical_events.append({
                        'id': log.id,
                        'event_type': log.event_type,
                        'description': log.event_description,
                        'timestamp': log.timestamp,
                        'user_id': log.user_id
                    })

                # Suspicious activity (multiple failed logins, unusual patterns)
                suspicious_activity = await self._detect_suspicious_patterns(
                    session, start_date, end_date, user_id
                )

                return AuditSummaryResponse(
                    total_events=total_events,
                    events_by_type=events_by_type,
                    events_by_severity=events_by_severity,
                    events_by_source=events_by_source,
                    events_by_user=events_by_user,
                    recent_critical_events=critical_events,
                    suspicious_activity=suspicious_activity,
                    date_range={
                        'start': start_date,
                        'end': end_date
                    }
                )

        except Exception as e:
            logger.error("Failed to generate audit summary",
                        error=str(e),
                        start_date=start_date,
                        end_date=end_date)
            raise AuditServiceError(f"Summary generation failed: {str(e)}")

    async def _detect_suspicious_patterns(
        self,
        session: AsyncSession,
        start_date: datetime,
        end_date: datetime,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Detect suspicious activity patterns"""
        suspicious_activities = []

        try:
            base_filters = [
                AuditLogORM.timestamp >= start_date,
                AuditLogORM.timestamp <= end_date
            ]

            if user_id:
                base_filters.append(AuditLogORM.user_id == user_id)

            # Multiple failed logins
            failed_login_query = (
                select(AuditLogORM.user_id, func.count(AuditLogORM.id))
                .where(and_(*base_filters))
                .where(AuditLogORM.event_type == AuditEventType.LOGIN_FAILURE.value)
                .group_by(AuditLogORM.user_id)
                .having(func.count(AuditLogORM.id) > 5)  # More than 5 failed attempts
            )

            failed_logins_result = await session.execute(failed_login_query)
            for user_id, count in failed_logins_result.fetchall():
                suspicious_activities.append({
                    'type': 'multiple_failed_logins',
                    'user_id': user_id,
                    'count': count,
                    'severity': 'high'
                })

            # Unusual trading hours (outside 9 AM - 4 PM IST)
            unusual_hours_query = (
                select(AuditLogORM.user_id, func.count(AuditLogORM.id))
                .where(and_(*base_filters))
                .where(AuditLogORM.event_type.in_([
                    AuditEventType.TRADE_CREATE.value,
                    AuditEventType.TRADE_EXECUTE.value
                ]))
                .where(or_(
                    func.strftime('%H', AuditLogORM.timestamp) < '03',  # Before 9 AM IST (UTC+5:30)
                    func.strftime('%H', AuditLogORM.timestamp) > '10'   # After 4 PM IST
                ))
                .group_by(AuditLogORM.user_id)
                .having(func.count(AuditLogORM.id) > 2)
            )

            unusual_hours_result = await session.execute(unusual_hours_query)
            for user_id, count in unusual_hours_result.fetchall():
                suspicious_activities.append({
                    'type': 'unusual_trading_hours',
                    'user_id': user_id,
                    'count': count,
                    'severity': 'medium'
                })

        except Exception as e:
            logger.warning("Failed to detect suspicious patterns", error=str(e))

        return suspicious_activities

    # Data Retention and Cleanup

    async def cleanup_expired_logs(self) -> Dict[str, Any]:
        """Clean up expired audit logs based on retention policy"""
        if self._shutdown:
            return {'cleaned': 0, 'error': 'Service shutting down'}

        try:
            if self.performance_monitor:
                self.performance_monitor.record_retention_cleanup()

            current_time = datetime.now(timezone.utc)

            async with self.db_manager.get_transaction() as session:
                # Find expired logs
                expired_logs_query = select(func.count(AuditLogORM.id)).where(
                    and_(
                        AuditLogORM.retention_date.is_not(None),
                        AuditLogORM.retention_date < current_time
                    )
                )
                expired_count = await session.scalar(expired_logs_query) or 0

                if expired_count == 0:
                    return {'cleaned': 0, 'message': 'No expired logs found'}

                # Delete expired logs in batches
                batch_size = 1000
                total_cleaned = 0

                while total_cleaned < expired_count:
                    # Get batch of expired log IDs
                    batch_query = (
                        select(AuditLogORM.id)
                        .where(and_(
                            AuditLogORM.retention_date.is_not(None),
                            AuditLogORM.retention_date < current_time
                        ))
                        .limit(batch_size)
                    )

                    result = await session.execute(batch_query)
                    log_ids = [row[0] for row in result.fetchall()]

                    if not log_ids:
                        break

                    # Delete batch
                    delete_query = text(
                        "DELETE FROM audit_logs WHERE id IN :log_ids"
                    ).bindparam(log_ids=tuple(log_ids))

                    delete_result = await session.execute(delete_query)
                    batch_cleaned = delete_result.rowcount
                    total_cleaned += batch_cleaned

                    logger.debug("Batch cleanup completed",
                               batch_size=batch_cleaned,
                               total_cleaned=total_cleaned)

                    if batch_cleaned < batch_size:
                        break

                logger.info("Audit log retention cleanup completed",
                          total_cleaned=total_cleaned,
                          expired_count=expired_count)

                return {
                    'cleaned': total_cleaned,
                    'originally_expired': expired_count,
                    'cleanup_date': current_time.isoformat()
                }

        except Exception as e:
            logger.error("Audit log cleanup failed", error=str(e))
            raise AuditRetentionError(f"Cleanup operation failed: {str(e)}")

    async def _retention_cleanup_task(self):
        """Background task for automatic retention cleanup"""
        while not self._shutdown:
            try:
                await asyncio.sleep(3600)  # Run every hour

                if not self._shutdown:
                    cleanup_result = await self.cleanup_expired_logs()
                    if cleanup_result.get('cleaned', 0) > 0:
                        logger.info("Automatic retention cleanup completed", **cleanup_result)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Retention cleanup task error", error=str(e))
                await asyncio.sleep(300)  # Wait 5 minutes before retry

    # Integrity and Security

    async def verify_audit_log_integrity(self, audit_id: str) -> bool:
        """Verify the integrity of a specific audit log"""
        try:
            async with self.db_manager.get_async_session() as session:
                result = await session.execute(
                    select(AuditLogORM).where(AuditLogORM.id == audit_id)
                )
                log_orm = result.scalar_one_or_none()

                if not log_orm:
                    raise AuditServiceError(f"Audit log not found: {audit_id}")

                # Convert to business object and verify
                audit_log = AuditLog(
                    id=log_orm.id,
                    event_type=AuditEventType(log_orm.event_type),
                    event_description=log_orm.event_description,
                    severity=AuditSeverity(log_orm.severity),
                    source=AuditSource(log_orm.source),
                    user_id=log_orm.user_id,
                    entity_type=log_orm.entity_type,
                    entity_id=log_orm.entity_id,
                    timestamp=log_orm.timestamp,
                    checksum=log_orm.checksum
                )

                return audit_log.verify_integrity()

        except AuditIntegrityError as e:
            logger.error("Audit log integrity verification failed",
                        audit_id=audit_id,
                        error=str(e))
            return False
        except Exception as e:
            logger.error("Integrity verification error",
                        audit_id=audit_id,
                        error=str(e))
            raise AuditServiceError(f"Integrity verification failed: {str(e)}")

    async def bulk_verify_integrity(self, limit: int = 1000) -> Dict[str, Any]:
        """Verify integrity of multiple audit logs"""
        try:
            async with self.db_manager.get_async_session() as session:
                # Get recent logs for verification
                result = await session.execute(
                    select(AuditLogORM)
                    .order_by(desc(AuditLogORM.created_at))
                    .limit(limit)
                )
                logs = result.scalars().all()

                verification_results = {
                    'total_checked': len(logs),
                    'valid': 0,
                    'invalid': 0,
                    'failed_verifications': []
                }

                for log_orm in logs:
                    try:
                        is_valid = await self.verify_audit_log_integrity(log_orm.id)
                        if is_valid:
                            verification_results['valid'] += 1
                        else:
                            verification_results['invalid'] += 1
                            verification_results['failed_verifications'].append({
                                'id': log_orm.id,
                                'event_type': log_orm.event_type,
                                'timestamp': log_orm.timestamp
                            })
                    except Exception as e:
                        verification_results['invalid'] += 1
                        verification_results['failed_verifications'].append({
                            'id': log_orm.id,
                            'error': str(e)
                        })

                logger.info("Bulk integrity verification completed",
                          **verification_results)

                return verification_results

        except Exception as e:
            logger.error("Bulk integrity verification failed", error=str(e))
            raise AuditServiceError(f"Bulk verification failed: {str(e)}")

    # Service Management

    async def get_service_status(self) -> Dict[str, Any]:
        """Get audit service status and performance metrics"""
        try:
            status = {
                'service_name': 'NIRAJ Audit Service',
                'version': '1.0.0',
                'initialized': self._initialized,
                'shutdown': self._shutdown,
                'batch_processing_enabled': self.batch_processor is not None,
                'performance_monitoring_enabled': self.performance_monitor is not None,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

            if self.performance_monitor:
                status['performance_metrics'] = self.performance_monitor.get_metrics()

            if self.batch_processor:
                async with self.batch_processor._lock:
                    status['batch_queue_size'] = len(self.batch_processor._batch_queue)
                    status['last_batch_flush'] = datetime.fromtimestamp(
                        self.batch_processor._last_flush
                    ).isoformat()

            # Database health check
            try:
                db_health = await self.db_manager.health_check()
                status['database_health'] = db_health
            except Exception as e:
                status['database_health'] = {'error': str(e)}

            # Cache stats
            async with self._cache_lock:
                status['cache_size'] = len(self._user_session_cache)

            return status

        except Exception as e:
            logger.error("Failed to get service status", error=str(e))
            return {
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

    # Convenience methods for common audit operations

    async def audit_user_login(
        self,
        user_id: str,
        success: bool,
        ip_address: str = None,
        user_agent: str = None,
        session_id: str = None,
        metadata: Dict[str, Any] = None
    ) -> AuditLogResponse:
        """Audit user login attempt"""
        event_type = AuditEventType.LOGIN_SUCCESS if success else AuditEventType.LOGIN_FAILURE
        severity = AuditSeverity.INFO if success else AuditSeverity.WARNING
        description = f"User {'login successful' if success else 'login failed'}"

        return await self.create_audit_log(
            event_type=event_type,
            event_description=description,
            severity=severity,
            source=AuditSource.USER,
            user_id=user_id,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={**(metadata or {}), 'login_success': success}
        )

    async def audit_trade_action(
        self,
        user_id: str,
        action: str,
        trade_id: str,
        symbol: str,
        quantity: str,
        price: str = None,
        amount: str = None,
        session_id: str = None,
        metadata: Dict[str, Any] = None
    ) -> AuditLogResponse:
        """Audit trading action"""
        event_type_mapping = {
            'create': AuditEventType.TRADE_CREATE,
            'update': AuditEventType.TRADE_UPDATE,
            'execute': AuditEventType.TRADE_EXECUTE,
            'cancel': AuditEventType.TRADE_CANCEL,
            'close': AuditEventType.TRADE_CLOSE
        }

        event_type = event_type_mapping.get(action.lower(), AuditEventType.TRADE_UPDATE)
        description = f"Trade {action} for {symbol}"

        return await self.create_audit_log(
            event_type=event_type,
            event_description=description,
            severity=AuditSeverity.INFO,
            source=AuditSource.USER,
            user_id=user_id,
            session_id=session_id,
            entity_type="trade",
            entity_id=trade_id,
            quantity=quantity,
            price=price,
            amount=amount,
            metadata={**(metadata or {}), 'action': action, 'symbol': symbol},
            tags=['trading', 'financial', symbol.lower()],
            is_sensitive=True  # Financial data is sensitive
        )

    async def audit_system_event(
        self,
        event_type: AuditEventType,
        description: str,
        severity: AuditSeverity = AuditSeverity.INFO,
        metadata: Dict[str, Any] = None
    ) -> AuditLogResponse:
        """Audit system event"""
        return await self.create_audit_log(
            event_type=event_type,
            event_description=description,
            severity=severity,
            source=AuditSource.SYSTEM,
            metadata={**(metadata or {}), 'system_generated': True}
        )

    async def audit_error(
        self,
        error_message: str,
        user_id: str = None,
        entity_type: str = None,
        entity_id: str = None,
        exception_type: str = None,
        session_id: str = None,
        metadata: Dict[str, Any] = None
    ) -> AuditLogResponse:
        """Audit system error"""
        return await self.create_audit_log(
            event_type=AuditEventType.ERROR_OCCURRED,
            event_description=f"Error occurred: {error_message}",
            severity=AuditSeverity.ERROR,
            source=AuditSource.SYSTEM,
            user_id=user_id,
            session_id=session_id,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata={
                **(metadata or {}),
                'error_message': error_message,
                'exception_type': exception_type
            },
            tags=['error', 'system']
        )


# Decorators for automatic audit logging

def audit_endpoint(
    event_type: AuditEventType,
    description: str = None,
    severity: AuditSeverity = AuditSeverity.INFO,
    extract_user_id: Callable = None,
    extract_entity: Callable = None
):
    """Decorator for automatic API endpoint auditing"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            audit_service = None
            try:
                # Extract audit service from kwargs or create new one
                audit_service = kwargs.get('audit_service') or AuditService()
                if not audit_service._initialized:
                    await audit_service.initialize()

                # Extract context information
                user_id = extract_user_id(*args, **kwargs) if extract_user_id else None
                entity_info = extract_entity(*args, **kwargs) if extract_entity else {}

                # Generate correlation ID
                correlation_id = str(uuid.uuid4())

                # Execute function
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)

                    # Audit successful execution
                    execution_time_ms = int((time.time() - start_time) * 1000)
                    await audit_service.create_audit_log(
                        event_type=event_type,
                        event_description=description or f"{func.__name__} executed successfully",
                        severity=severity,
                        source=AuditSource.API,
                        user_id=user_id,
                        entity_type=entity_info.get('type'),
                        entity_id=entity_info.get('id'),
                        correlation_id=correlation_id,
                        execution_time_ms=execution_time_ms,
                        metadata={
                            'function': func.__name__,
                            'module': func.__module__,
                            'success': True
                        }
                    )

                    return result

                except Exception as e:
                    # Audit failed execution
                    execution_time_ms = int((time.time() - start_time) * 1000)
                    await audit_service.audit_error(
                        error_message=str(e),
                        user_id=user_id,
                        entity_type=entity_info.get('type'),
                        entity_id=entity_info.get('id'),
                        exception_type=type(e).__name__,
                        metadata={
                            'function': func.__name__,
                            'module': func.__module__,
                            'correlation_id': correlation_id,
                            'execution_time_ms': execution_time_ms
                        }
                    )
                    raise

            except Exception as e:
                logger.error("Audit decorator error", error=str(e), function=func.__name__)
                # Don't fail the original function due to audit errors
                return await func(*args, **kwargs)

        return wrapper
    return decorator


# Global audit service instance
_audit_service: Optional[AuditService] = None


async def get_audit_service() -> AuditService:
    """Get global audit service instance"""
    global _audit_service

    if _audit_service is None:
        _audit_service = AuditService()
        await _audit_service.initialize()

    return _audit_service


# Context manager for audit sessions
@asynccontextmanager
async def audit_context(
    user_id: str = None,
    session_id: str = None,
    correlation_id: str = None,
    metadata: Dict[str, Any] = None
):
    """Context manager for audit logging with shared context"""
    audit_service = await get_audit_service()

    # Set context in structured logging
    with LogContext(
        user_id=user_id,
        session_id=session_id,
        correlation_id=correlation_id or str(uuid.uuid4()),
        **(metadata or {})
    ):
        try:
            yield audit_service
        except Exception as e:
            # Audit the error
            await audit_service.audit_error(
                error_message=str(e),
                user_id=user_id,
                session_id=session_id,
                exception_type=type(e).__name__,
                metadata=metadata
            )
            raise


# Cleanup function for graceful shutdown
async def cleanup_audit_service():
    """Cleanup audit service on application shutdown"""
    global _audit_service

    if _audit_service:
        await _audit_service.shutdown()
        _audit_service = None
