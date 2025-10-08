"""
NIRAJ Logging Framework
Structured logging setup with multiple handlers and formats
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Callable, TypeVar, ParamSpec, Coroutine
import logging
import logging.handlers
from datetime import datetime

import structlog
from structlog.stdlib import BoundLogger, LoggerFactory

P = ParamSpec("P")
R = TypeVar("R")


class ColoredFormatter(logging.Formatter):
    """Colored console formatter for development"""

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        log_color = self.COLORS.get(record.levelname, "")
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)


class NirajLogger:
    """NIRAJ logging system manager"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._get_default_config()
        self._configured = False

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default logging configuration"""
        environment = os.getenv("ENVIRONMENT", "development")

        if environment == "development":
            return {
                "level": "DEBUG",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "file": "logs/niraj.log",
                "max_file_size": "10MB",
                "backup_count": 5,
                "console_enabled": True,
                "file_enabled": True,
                "structured_logging": True,
                "loggers": [
                    {"name": "niraj", "level": "DEBUG"},
                    {"name": "trading", "level": "DEBUG"},
                    {"name": "ai", "level": "DEBUG"},
                ],
            }
        elif environment == "production":
            return {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "file": "/var/log/niraj/niraj.log",
                "max_file_size": "50MB",
                "backup_count": 10,
                "console_enabled": False,
                "file_enabled": True,
                "structured_logging": True,
                "loggers": [
                    {"name": "niraj", "level": "INFO"},
                    {"name": "trading", "level": "INFO"},
                    {"name": "ai", "level": "WARNING"},
                ],
            }
        else:  # testing
            return {
                "level": "DEBUG",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "file": "logs/test_niraj.log",
                "max_file_size": "1MB",
                "backup_count": 2,
                "console_enabled": True,
                "file_enabled": True,
                "structured_logging": True,
                "loggers": [
                    {"name": "niraj", "level": "DEBUG"},
                    {"name": "trading", "level": "DEBUG"},
                    {"name": "ai", "level": "DEBUG"},
                ],
            }

    def configure(self) -> logging.Logger:
        """Configure logging system"""
        if self._configured:
            return logging.getLogger("niraj")

        # Create logs directory
        log_file = Path(self.config["file"])
        log_file.parent.mkdir(parents=True, exist_ok=True)

        # Configure structlog
        if self.config.get("structured_logging", True):
            log_level_str = self.config.get("level", "INFO")
            log_level = getattr(logging, log_level_str.upper(), logging.INFO)
            if not isinstance(log_level, int):
                log_level = logging.INFO

            structlog.configure(
                processors=[
                    structlog.contextvars.merge_contextvars,
                    structlog.processors.TimeStamper(fmt="iso"),
                    structlog.processors.add_log_level,
                    structlog.processors.StackInfoRenderer(),
                    (
                        structlog.dev.ConsoleRenderer()
                        if self.config.get("console_enabled", True)
                        else structlog.processors.JSONRenderer()
                    ),
                ],
                wrapper_class=structlog.make_filtering_bound_logger(log_level),
                logger_factory=LoggerFactory(),
                cache_logger_on_first_use=True,
            )

        # Configure standard library logging
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self.config["level"].upper(), logging.INFO))

        # Remove existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Console handler
        if self.config.get("console_enabled", True):
            console_handler = logging.StreamHandler(sys.stdout)
            if os.getenv("ENVIRONMENT", "development") == "development":
                console_formatter = ColoredFormatter(self.config["format"])
            else:
                console_formatter = logging.Formatter(self.config["format"])
            console_handler.setFormatter(console_formatter)
            console_handler.setLevel(getattr(logging, self.config["level"].upper(), logging.INFO))
            root_logger.addHandler(console_handler)

        # File handler with rotation
        if self.config.get("file_enabled", True):
            # Parse max file size
            max_bytes = self._parse_size(self.config.get("max_file_size", "10MB"))
            backup_count = self.config.get("backup_count", 5)

            file_handler = logging.handlers.RotatingFileHandler(
                str(self.config["file"]),
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding="utf-8",
            )
            file_formatter = logging.Formatter(self.config["format"])
            file_handler.setFormatter(file_formatter)
            file_handler.setLevel(getattr(logging, self.config["level"].upper(), logging.INFO))
            root_logger.addHandler(file_handler)

        # Configure specific loggers
        for logger_config in self.config.get("loggers", []):
            logger_name = logger_config["name"]
            logger_level = logger_config["level"]

            specific_logger = logging.getLogger(logger_name)
            specific_logger.setLevel(getattr(logging, logger_level.upper(), logging.INFO))

        # Configure third-party loggers
        self._configure_third_party_loggers()

        self._configured = True

        # Create main NIRAJ logger
        niraj_logger = logging.getLogger("niraj")
        niraj_logger.info(
            f"Logging system configured with level={self.config['level']}, file={self.config['file']}"
        )

        return niraj_logger

    def _parse_size(self, size_str: str) -> int:
        """Parse size string to bytes"""
        size_str = size_str.upper().strip()

        multipliers = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3}

        for suffix, multiplier in multipliers.items():
            if size_str.endswith(suffix):
                number = size_str[: -len(suffix)]
                try:
                    return int(float(number) * multiplier)
                except ValueError:
                    # Handle edge case where suffix parsing fails
                    return 10 * 1024**2  # Default to 10MB

        # Default to bytes if no suffix
        try:
            return int(size_str)
        except ValueError:
            return 10 * 1024**2  # Default to 10MB

    def _configure_third_party_loggers(self):
        """Configure third-party library loggers"""
        # Reduce noise from third-party libraries
        noisy_loggers = [
            "httpx",
            "httpcore",
            "urllib3",
            "asyncio",
            "websockets",
            "redis",
            "sqlalchemy.engine",
            "sqlalchemy.dialects",
            "ollama",
        ]

        for logger_name in noisy_loggers:
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.WARNING)

        # Special handling for database logging
        if self.config.get("database_logging", False):
            logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)

    def get_logger(self, name: str) -> logging.Logger:
        """Get a logger by name"""
        if not self._configured:
            self.configure()
        return logging.getLogger(name)

    def is_configured(self) -> bool:
        """Check if logger is configured"""
        return self._configured

    def add_handler(self, handler: logging.Handler, logger_name: Optional[str] = None):
        """Add a custom handler"""
        if not self._configured:
            self.configure()

        target_logger = (
            logging.getLogger(logger_name) if logger_name else logging.getLogger()
        )
        target_logger.addHandler(handler)

    def set_level(self, level: str, logger_name: Optional[str] = None):
        """Set logging level"""
        if not self._configured:
            self.configure()

        target_logger = (
            logging.getLogger(logger_name) if logger_name else logging.getLogger()
        )
        target_logger.setLevel(getattr(logging, level.upper(), logging.INFO))


class TradingLogHandler(logging.Handler):
    """Custom log handler for trading activities"""

    def __init__(self, log_file: str = "logs/trading.log"):
        super().__init__()
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a trading log record"""
        # Use getattr with hasattr for type-safe attribute access
        if hasattr(record, "trade_data"):
            # Special handling for trade records
            timestamp = datetime.now().isoformat()
            trade_data = getattr(record, "trade_data", {})
            trade_entry: Dict[str, Any] = {
                "timestamp": timestamp,
                "level": record.levelname,
                "message": record.getMessage(),
                "trade_data": trade_data,
            }

            with open(self.log_file, "a", encoding="utf-8") as f:
                import json

                f.write(json.dumps(trade_entry) + "\n")


class AILogHandler(logging.Handler):
    """Custom log handler for AI activities"""

    def __init__(self, log_file: str = "logs/ai.log"):
        super().__init__()
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, record: logging.LogRecord) -> None:
        """Emit an AI log record"""
        # Use getattr with hasattr for type-safe attribute access
        if hasattr(record, "ai_data"):
            # Special handling for AI records
            timestamp = datetime.now().isoformat()
            ai_data = getattr(record, "ai_data", {})
            ai_entry: Dict[str, Any] = {
                "timestamp": timestamp,
                "level": record.levelname,
                "message": record.getMessage(),
                "ai_data": ai_data,
            }

            with open(self.log_file, "a", encoding="utf-8") as f:
                import json

                f.write(json.dumps(ai_entry) + "\n")


# Global logger manager
logger_manager = NirajLogger()


def configure_logging(config: Optional[Dict[str, Any]] = None) -> logging.Logger:
    """Configure logging system"""
    if config:
        logger_manager.config.update(config)
    return logger_manager.configure()


def get_logger(name: str = "niraj") -> logging.Logger:
    """Get a logger instance"""
    return logger_manager.get_logger(name)


def get_structured_logger(name: str = "niraj") -> BoundLogger:
    """Get a structured logger instance"""
    if not logger_manager.is_configured():
        logger_manager.configure()
    return structlog.get_logger(name)


# Convenience functions for different types of logging
def log_trade(message: str, trade_data: Dict[str, Any], level: str = "INFO") -> None:
    """Log trading activity"""
    logger = get_logger("trading")
    level_num = getattr(logging, level.upper(), logging.INFO)
    if not isinstance(level_num, int):
        level_num = logging.INFO
    log_record = logger.makeRecord("trading", level_num, "", 0, message, (), None)
    setattr(log_record, "trade_data", trade_data)
    logger.handle(log_record)


def log_ai(message: str, ai_data: Dict[str, Any], level: str = "INFO") -> None:
    """Log AI activity"""
    logger = get_logger("ai")
    level_num = getattr(logging, level.upper(), logging.INFO)
    if not isinstance(level_num, int):
        level_num = logging.INFO
    log_record = logger.makeRecord("ai", level_num, "", 0, message, (), None)
    setattr(log_record, "ai_data", ai_data)
    logger.handle(log_record)


def log_system_event(event: str, details: Dict[str, Any], level: str = "INFO") -> None:
    """Log system events"""
    logger = get_structured_logger("niraj.system")
    log_func = getattr(logger, level.lower(), logger.info)
    log_func(event, **details)


def log_error(error: Exception, context: Optional[Dict[str, Any]] = None) -> None:
    """Log errors with context"""
    logger = get_structured_logger("niraj.error")
    logger.error(
        "Error occurred",
        error=str(error),
        error_type=type(error).__name__,
        context=context or {},
    )


# Context managers for logging
class LogContext:
    """Context manager for adding context to logs"""

    def __init__(self, **context: Any):
        self.context = context

    def __enter__(self) -> "LogContext":
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(**self.context)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        structlog.contextvars.clear_contextvars()


# Performance logging decorator
def log_performance(
    func_name: Optional[str] = None,
) -> Callable[[Callable[P, R]], Callable[P, Coroutine[Any, Any, R]] | Callable[P, R]]:
    """Decorator to log function performance"""

    def decorator(func: Callable[P, R]) -> Callable[P, Coroutine[Any, Any, R]] | Callable[P, R]:
        import functools
        import time

        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            name = func_name or f"{func.__module__}.{func.__name__}"
            start_time = time.time()

            try:
                result: R = await func(*args, **kwargs)  # type: ignore
                duration = time.time() - start_time

                logger = get_structured_logger("niraj.performance")
                logger.info(
                    "Function completed",
                    function=name,
                    duration_seconds=duration,
                    success=True,
                )

                return result
            except Exception as e:
                duration = time.time() - start_time

                logger = get_structured_logger("niraj.performance")
                logger.error(
                    "Function failed",
                    function=name,
                    duration_seconds=duration,
                    error=str(e),
                    success=False,
                )
                raise

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            name = func_name or f"{func.__module__}.{func.__name__}"
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time

                logger = get_structured_logger("niraj.performance")
                logger.info(
                    "Function completed",
                    function=name,
                    duration_seconds=duration,
                    success=True,
                )

                return result
            except Exception as e:
                duration = time.time() - start_time

                logger = get_structured_logger("niraj.performance")
                logger.error(
                    "Function failed",
                    function=name,
                    duration_seconds=duration,
                    error=str(e),
                    success=False,
                )
                raise

        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# Initialize logging on import
if not logger_manager.is_configured():
    configure_logging()
