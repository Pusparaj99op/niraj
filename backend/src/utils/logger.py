"""
NIRAJ Logging Framework
Structured logging setup with multiple handlers and formats
"""
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional
import logging
import logging.handlers
from datetime import datetime

import structlog
from structlog.stdlib import LoggerFactory


class ColoredFormatter(logging.Formatter):
    """Colored console formatter for development"""

    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'

    def format(self, record):
        log_color = self.COLORS.get(record.levelname, '')
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
                'level': 'DEBUG',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'file': 'logs/niraj.log',
                'max_file_size': '10MB',
                'backup_count': 5,
                'console_enabled': True,
                'file_enabled': True,
                'structured_logging': True,
                'loggers': [
                    {'name': 'niraj', 'level': 'DEBUG'},
                    {'name': 'trading', 'level': 'DEBUG'},
                    {'name': 'ai', 'level': 'DEBUG'}
                ]
            }
        elif environment == "production":
            return {
                'level': 'INFO',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'file': '/var/log/niraj/niraj.log',
                'max_file_size': '50MB',
                'backup_count': 10,
                'console_enabled': False,
                'file_enabled': True,
                'structured_logging': True,
                'loggers': [
                    {'name': 'niraj', 'level': 'INFO'},
                    {'name': 'trading', 'level': 'INFO'},
                    {'name': 'ai', 'level': 'WARNING'}
                ]
            }
        else:  # testing
            return {
                'level': 'DEBUG',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'file': 'logs/test_niraj.log',
                'max_file_size': '1MB',
                'backup_count': 2,
                'console_enabled': True,
                'file_enabled': True,
                'structured_logging': True,
                'loggers': [
                    {'name': 'niraj', 'level': 'DEBUG'},
                    {'name': 'trading', 'level': 'DEBUG'},
                    {'name': 'ai', 'level': 'DEBUG'}
                ]
            }

    def configure(self) -> logging.Logger:
        """Configure logging system"""
        if self._configured:
            return logging.getLogger('niraj')

        # Create logs directory
        log_file = Path(self.config['file'])
        log_file.parent.mkdir(parents=True, exist_ok=True)

        # Configure structlog
        if self.config.get('structured_logging', True):
            structlog.configure(
                processors=[
                    structlog.contextvars.merge_contextvars,
                    structlog.processors.TimeStamper(fmt="ISO"),
                    structlog.processors.add_log_level,
                    structlog.processors.StackInfoRenderer(),
                    structlog.dev.ConsoleRenderer() if self.config.get('console_enabled', True)
                    else structlog.processors.JSONRenderer()
                ],
                wrapper_class=structlog.make_filtering_bound_logger(
                    logging.getLevelName(self.config['level'])
                ),
                logger_factory=LoggerFactory(),
                cache_logger_on_first_use=True,
            )

        # Configure standard library logging
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.getLevelName(self.config['level']))

        # Remove existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Console handler
        if self.config.get('console_enabled', True):
            console_handler = logging.StreamHandler(sys.stdout)
            if os.getenv('ENVIRONMENT', 'development') == 'development':
                console_formatter = ColoredFormatter(self.config['format'])
            else:
                console_formatter = logging.Formatter(self.config['format'])
            console_handler.setFormatter(console_formatter)
            console_handler.setLevel(logging.getLevelName(self.config['level']))
            root_logger.addHandler(console_handler)

        # File handler with rotation
        if self.config.get('file_enabled', True):
            # Parse max file size
            max_bytes = self._parse_size(self.config.get('max_file_size', '10MB'))
            backup_count = self.config.get('backup_count', 5)

            file_handler = logging.handlers.RotatingFileHandler(
                self.config['file'],
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_formatter = logging.Formatter(self.config['format'])
            file_handler.setFormatter(file_formatter)
            file_handler.setLevel(logging.getLevelName(self.config['level']))
            root_logger.addHandler(file_handler)

        # Configure specific loggers
        for logger_config in self.config.get('loggers', []):
            logger_name = logger_config['name']
            logger_level = logger_config['level']

            specific_logger = logging.getLogger(logger_name)
            specific_logger.setLevel(logging.getLevelName(logger_level))

        # Configure third-party loggers
        self._configure_third_party_loggers()

        self._configured = True

        # Create main NIRAJ logger
        niraj_logger = logging.getLogger('niraj')
        niraj_logger.info(f"Logging system configured with level={self.config['level']}, file={self.config['file']}")

        return niraj_logger

    def _parse_size(self, size_str: str) -> int:
        """Parse size string to bytes"""
        size_str = size_str.upper().strip()

        multipliers = {
            'B': 1,
            'KB': 1024,
            'MB': 1024 ** 2,
            'GB': 1024 ** 3
        }

        for suffix, multiplier in multipliers.items():
            if size_str.endswith(suffix):
                number = size_str[:-len(suffix)]
                try:
                    return int(float(number) * multiplier)
                except ValueError:
                    # Handle edge case where suffix parsing fails
                    return 10 * 1024 ** 2  # Default to 10MB

        # Default to bytes if no suffix
        try:
            return int(size_str)
        except ValueError:
            return 10 * 1024 ** 2  # Default to 10MB

    def _configure_third_party_loggers(self):
        """Configure third-party library loggers"""
        # Reduce noise from third-party libraries
        noisy_loggers = [
            'httpx',
            'httpcore',
            'urllib3',
            'asyncio',
            'websockets',
            'redis',
            'sqlalchemy.engine',
            'sqlalchemy.dialects',
            'ollama'
        ]

        for logger_name in noisy_loggers:
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.WARNING)

        # Special handling for database logging
        if self.config.get('database_logging', False):
            logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

    def get_logger(self, name: str) -> logging.Logger:
        """Get a logger by name"""
        if not self._configured:
            self.configure()
        return logging.getLogger(name)

    def add_handler(self, handler: logging.Handler, logger_name: Optional[str] = None):
        """Add a custom handler"""
        if not self._configured:
            self.configure()

        target_logger = logging.getLogger(logger_name) if logger_name else logging.getLogger()
        target_logger.addHandler(handler)

    def set_level(self, level: str, logger_name: Optional[str] = None):
        """Set logging level"""
        if not self._configured:
            self.configure()

        target_logger = logging.getLogger(logger_name) if logger_name else logging.getLogger()
        target_logger.setLevel(logging.getLevelName(level))


class TradingLogHandler(logging.Handler):
    """Custom log handler for trading activities"""

    def __init__(self, log_file: str = "logs/trading.log"):
        super().__init__()
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, record):
        """Emit a trading log record"""
        if hasattr(record, 'trade_data'):
            # Special handling for trade records
            timestamp = datetime.now().isoformat()
            trade_entry = {
                'timestamp': timestamp,
                'level': record.levelname,
                'message': record.getMessage(),
                'trade_data': record.trade_data
            }

            with open(self.log_file, 'a', encoding='utf-8') as f:
                import json
                f.write(json.dumps(trade_entry) + '\n')


class AILogHandler(logging.Handler):
    """Custom log handler for AI activities"""

    def __init__(self, log_file: str = "logs/ai.log"):
        super().__init__()
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, record):
        """Emit an AI log record"""
        if hasattr(record, 'ai_data'):
            # Special handling for AI records
            timestamp = datetime.now().isoformat()
            ai_entry = {
                'timestamp': timestamp,
                'level': record.levelname,
                'message': record.getMessage(),
                'ai_data': record.ai_data
            }

            with open(self.log_file, 'a', encoding='utf-8') as f:
                import json
                f.write(json.dumps(ai_entry) + '\n')


# Global logger manager
logger_manager = NirajLogger()


def configure_logging(config: Optional[Dict[str, Any]] = None) -> logging.Logger:
    """Configure logging system"""
    if config:
        logger_manager.config.update(config)
    return logger_manager.configure()


def get_logger(name: str = 'niraj') -> logging.Logger:
    """Get a logger instance"""
    return logger_manager.get_logger(name)


def get_structured_logger(name: str = 'niraj'):
    """Get a structured logger instance"""
    if not logger_manager._configured:
        logger_manager.configure()
    return structlog.get_logger(name)


# Convenience functions for different types of logging
def log_trade(message: str, trade_data: Dict[str, Any], level: str = 'INFO'):
    """Log trading activity"""
    logger = get_logger('trading')
    log_record = logger.makeRecord(
        'trading',
        logging.getLevelName(level),
        '', 0, message, (), None
    )
    log_record.trade_data = trade_data
    logger.handle(log_record)


def log_ai(message: str, ai_data: Dict[str, Any], level: str = 'INFO'):
    """Log AI activity"""
    logger = get_logger('ai')
    log_record = logger.makeRecord(
        'ai',
        logging.getLevelName(level),
        '', 0, message, (), None
    )
    log_record.ai_data = ai_data
    logger.handle(log_record)


def log_system_event(event: str, details: Dict[str, Any], level: str = 'INFO'):
    """Log system events"""
    logger = get_structured_logger('niraj.system')
    log_func = getattr(logger, level.lower())
    log_func(event, **details)


def log_error(error: Exception, context: Dict[str, Any] = None):
    """Log errors with context"""
    logger = get_structured_logger('niraj.error')
    logger.error(
        "Error occurred",
        error=str(error),
        error_type=type(error).__name__,
        context=context or {}
    )


# Context managers for logging
class LogContext:
    """Context manager for adding context to logs"""

    def __init__(self, **context):
        self.context = context

    def __enter__(self):
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(**self.context)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        structlog.contextvars.clear_contextvars()


# Performance logging decorator
def log_performance(func_name: Optional[str] = None):
    """Decorator to log function performance"""
    def decorator(func):
        import functools
        import time

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            name = func_name or f"{func.__module__}.{func.__name__}"
            start_time = time.time()

            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time

                logger = get_structured_logger('niraj.performance')
                logger.info("Function completed",
                          function=name,
                          duration_seconds=duration,
                          success=True)

                return result
            except Exception as e:
                duration = time.time() - start_time

                logger = get_structured_logger('niraj.performance')
                logger.error("Function failed",
                           function=name,
                           duration_seconds=duration,
                           error=str(e),
                           success=False)
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            name = func_name or f"{func.__module__}.{func.__name__}"
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time

                logger = get_structured_logger('niraj.performance')
                logger.info("Function completed",
                          function=name,
                          duration_seconds=duration,
                          success=True)

                return result
            except Exception as e:
                duration = time.time() - start_time

                logger = get_structured_logger('niraj.performance')
                logger.error("Function failed",
                           function=name,
                           duration_seconds=duration,
                           error=str(e),
                           success=False)
                raise

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# Initialize logging on import
if not logger_manager._configured:
    configure_logging()
