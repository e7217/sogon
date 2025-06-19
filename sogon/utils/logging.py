"""
Centralized logging configuration and utilities
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from ..config import get_settings


def setup_logging(
    console_level: Optional[str] = None,
    file_level: Optional[str] = None,
    log_file: Optional[str] = None
) -> None:
    """
    Setup centralized logging configuration
    
    Args:
        console_level: Console log level override
        file_level: File log level override  
        log_file: Log file path override
    """
    settings = get_settings()
    
    # Use settings or overrides
    console_level = console_level or settings.log_level
    file_level = file_level or "DEBUG"
    log_file = log_file or settings.log_file
    
    # Clear existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    # Console handler - INFO level and above with simple format
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, console_level.upper()))
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    
    # File handler - DEBUG level and above with detailed format
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=settings.log_max_bytes,
        backupCount=settings.log_backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(getattr(logging, file_level.upper()))
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    
    # Configure root logger
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger.setLevel(logging.DEBUG)
    
    # Suppress some noisy loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("yt_dlp").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    logger = logging.getLogger(__name__)
    logger.info("Logging configured successfully")
    logger.debug(f"Console level: {console_level}, File level: {file_level}")
    logger.debug(f"Log file: {log_file}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the given name
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        logging.Logger: Configured logger instance
    """
    return logging.getLogger(name)


class LogContext:
    """
    Context manager for temporary logging configuration changes
    """
    
    def __init__(self, logger: logging.Logger, level: str):
        """
        Initialize log context
        
        Args:
            logger: Logger to modify
            level: Temporary log level
        """
        self.logger = logger
        self.new_level = getattr(logging, level.upper())
        self.original_level = logger.level
    
    def __enter__(self):
        """Enter context - set new log level"""
        self.logger.setLevel(self.new_level)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context - restore original log level"""
        self.logger.setLevel(self.original_level)


def with_log_level(logger: logging.Logger, level: str):
    """
    Create a context manager for temporary log level change
    
    Args:
        logger: Logger to modify
        level: Temporary log level
        
    Returns:
        LogContext: Context manager
    """
    return LogContext(logger, level)


class StructuredLogger:
    """
    Structured logging wrapper for consistent log formatting
    """
    
    def __init__(self, logger: logging.Logger):
        """
        Initialize structured logger
        
        Args:
            logger: Base logger to wrap
        """
        self.logger = logger
    
    def info(self, message: str, **kwargs):
        """Log info message with structured data"""
        self._log(logging.INFO, message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug message with structured data"""
        self._log(logging.DEBUG, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with structured data"""
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message with structured data"""
        self._log(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message with structured data"""
        self._log(logging.CRITICAL, message, **kwargs)
    
    def _log(self, level: int, message: str, **kwargs):
        """Internal log method with structured data"""
        if kwargs:
            structured_data = " | ".join(f"{k}={v}" for k, v in kwargs.items())
            full_message = f"{message} | {structured_data}"
        else:
            full_message = message
        
        self.logger.log(level, full_message)


def get_structured_logger(name: str) -> StructuredLogger:
    """
    Get a structured logger with the given name
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        StructuredLogger: Structured logger instance
    """
    logger = logging.getLogger(name)
    return StructuredLogger(logger)


def log_function_call(logger: logging.Logger):
    """
    Decorator to log function calls with parameters and results
    
    Args:
        logger: Logger to use for logging
        
    Returns:
        Decorator function
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Log function entry
            args_str = ", ".join(str(arg) for arg in args)
            kwargs_str = ", ".join(f"{k}={v}" for k, v in kwargs.items())
            params = ", ".join(filter(None, [args_str, kwargs_str]))
            
            logger.debug(f"Calling {func.__name__}({params})")
            
            try:
                result = func(*args, **kwargs)
                logger.debug(f"{func.__name__} completed successfully")
                return result
            except Exception as e:
                logger.error(f"{func.__name__} failed: {e}")
                raise
        
        return wrapper
    return decorator