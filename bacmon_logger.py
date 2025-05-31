#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
BACmon Enhanced Logging and Error Handling Framework

This module provides a centralized, structured logging system for BACmon with:
1. JSON-formatted structured logging
2. Configuration-driven log levels and destinations
3. Log rotation and management
4. Custom exception classes with context
5. Error monitoring integration
6. Debugging aids and correlation IDs
"""

import os
import sys
import json
import time
import uuid
import logging
import logging.handlers
import threading
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, Union, Callable, List
from functools import wraps
from contextlib import contextmanager
from configparser import ConfigParser


# Log Categories
class LogCategory:
    """Standard log categories for BACmon operations"""
    SYSTEM = "system"
    MONITORING = "monitoring"
    API = "api"
    REDIS = "redis"
    ALERTS = "alerts"
    SECURITY = "security"
    PERFORMANCE = "performance"
    NETWORK = "network"
    CONFIG = "config"


# Custom Exception Classes
class BACmonError(Exception):
    """Base exception for all BACmon-specific errors"""
    def __init__(self, message: str, category: str = LogCategory.SYSTEM, 
                 context: Optional[Dict[str, Any]] = None, correlation_id: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.category = category
        self.context = context or {}
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.timestamp = time.time()


class BACmonConfigError(BACmonError):
    """Configuration-related errors"""
    def __init__(self, message: str, config_section: Optional[str] = None, 
                 config_key: Optional[str] = None, **kwargs):
        context = kwargs.get('context', {})
        context.update({
            'config_section': config_section,
            'config_key': config_key
        })
        kwargs['context'] = context
        super().__init__(message, LogCategory.CONFIG, **kwargs)


class BACmonRedisError(BACmonError):
    """Redis connectivity/operation errors"""
    def __init__(self, message: str, operation: Optional[str] = None, 
                 redis_key: Optional[str] = None, **kwargs):
        context = kwargs.get('context', {})
        context.update({
            'redis_operation': operation,
            'redis_key': redis_key
        })
        kwargs['context'] = context
        super().__init__(message, LogCategory.REDIS, **kwargs)


class BACmonNetworkError(BACmonError):
    """Network communication errors"""
    def __init__(self, message: str, host: Optional[str] = None, 
                 port: Optional[int] = None, protocol: Optional[str] = None, **kwargs):
        context = kwargs.get('context', {})
        context.update({
            'host': host,
            'port': port,
            'protocol': protocol
        })
        kwargs['context'] = context
        super().__init__(message, LogCategory.NETWORK, **kwargs)


class BACmonValidationError(BACmonError):
    """Data validation errors"""
    def __init__(self, message: str, field: Optional[str] = None, 
                 value: Optional[Any] = None, **kwargs):
        context = kwargs.get('context', {})
        context.update({
            'validation_field': field,
            'validation_value': str(value) if value is not None else None
        })
        kwargs['context'] = context
        super().__init__(message, LogCategory.SYSTEM, **kwargs)


# Thread-local storage for correlation context
_local = threading.local()


def get_correlation_id() -> str:
    """Get the current correlation ID for this thread"""
    if not hasattr(_local, 'correlation_id'):
        _local.correlation_id = str(uuid.uuid4())
    return _local.correlation_id


def set_correlation_id(correlation_id: str) -> None:
    """Set the correlation ID for this thread"""
    _local.correlation_id = correlation_id


@contextmanager
def correlation_context(correlation_id: Optional[str] = None):
    """Context manager for setting correlation ID within a block"""
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())
    
    old_id = getattr(_local, 'correlation_id', None)
    set_correlation_id(correlation_id)
    try:
        yield correlation_id
    finally:
        if old_id:
            set_correlation_id(old_id)
        elif hasattr(_local, 'correlation_id'):
            delattr(_local, 'correlation_id')


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging"""
    
    def __init__(self, include_extra: bool = True):
        super().__init__()
        self.include_extra = include_extra
    
    def format(self, record: logging.LogRecord) -> str:
        # Build the structured log entry
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat() + 'Z',
            'level': record.levelname,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'message': record.getMessage(),
            'correlation_id': get_correlation_id()
        }
        
        # Add category if present
        if hasattr(record, 'category'):
            log_entry['category'] = record.category
        
        # Add extra data if present
        if self.include_extra and hasattr(record, 'data'):
            log_entry['data'] = record.data
        
        # Add request ID if present
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
        
        # Add exception information if present
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        # Add timing information if present
        if hasattr(record, 'duration'):
            log_entry['duration_ms'] = record.duration
        
        return json.dumps(log_entry, default=str)


class BACmonLogger:
    """Enhanced logger for BACmon with structured logging and configuration support"""
    
    def __init__(self, name: str = 'bacmon', config: Optional[ConfigParser] = None):
        self.name = name
        self.logger = logging.getLogger(name)
        self.config = config
        self._configured = False
        self._setup_lock = threading.Lock()
        
        # Performance tracking
        self._operation_start_times: Dict[str, float] = {}
    
    def configure(self, config: Optional[ConfigParser] = None) -> None:
        """Configure the logger based on configuration settings"""
        with self._setup_lock:
            if self._configured:
                return
            
            if config:
                self.config = config
            
            # Set default configuration if none provided
            if not self.config:
                self._setup_default_config()
            else:
                self._setup_from_config()
            
            self._configured = True
    
    def _setup_default_config(self) -> None:
        """Setup default logging configuration"""
        self.logger.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(StructuredFormatter())
        self.logger.addHandler(console_handler)
        
        # Prevent propagation to root logger
        self.logger.propagate = False
    
    def _setup_from_config(self) -> None:
        """Setup logging from configuration file"""
        if not self.config.has_section('Logging'):
            self._setup_default_config()
            return
        
        # Get configuration values
        level = self.config.get('Logging', 'level', fallback='INFO').upper()
        log_format = self.config.get('Logging', 'format', fallback='json').lower()
        console_enabled = self.config.getboolean('Logging', 'console_enabled', fallback=True)
        file_enabled = self.config.getboolean('Logging', 'file_enabled', fallback=True)
        
        # Set logger level
        self.logger.setLevel(getattr(logging, level))
        
        # Setup formatters
        if log_format == 'json':
            formatter = StructuredFormatter()
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        
        # Console handler
        if console_enabled:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(getattr(logging, level))
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
        
        # File handler with rotation
        if file_enabled:
            log_file = self.config.get('Logging', 'log_file', fallback='/var/log/bacmon/bacmon.log')
            max_size_mb = self.config.getint('Logging', 'max_size_mb', fallback=50)
            max_files = self.config.getint('Logging', 'max_files', fallback=10)
            
            # Ensure log directory exists
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=max_size_mb * 1024 * 1024,
                backupCount=max_files
            )
            file_handler.setLevel(getattr(logging, level))
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
        
        # Error file handler
        error_log = self.config.get('Logging', 'error_log', fallback=None)
        if error_log:
            os.makedirs(os.path.dirname(error_log), exist_ok=True)
            error_handler = logging.handlers.RotatingFileHandler(
                error_log,
                maxBytes=50 * 1024 * 1024,
                backupCount=5
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(formatter)
            self.logger.addHandler(error_handler)
        
        # Prevent propagation to root logger
        self.logger.propagate = False
    
    def _log(self, level: int, message: str, category: str = LogCategory.SYSTEM,
             data: Optional[Dict[str, Any]] = None, exc_info: bool = False,
             request_id: Optional[str] = None, **kwargs) -> None:
        """Internal logging method with structured data support"""
        if not self._configured:
            self.configure()
        
        extra = {
            'category': category,
            'data': data or {}
        }
        
        if request_id:
            extra['request_id'] = request_id
        
        self.logger.log(level, message, exc_info=exc_info, extra=extra, **kwargs)
    
    def debug(self, message: str, category: str = LogCategory.SYSTEM,
              data: Optional[Dict[str, Any]] = None, **kwargs) -> None:
        """Log debug message"""
        self._log(logging.DEBUG, message, category, data, **kwargs)
    
    def info(self, message: str, category: str = LogCategory.SYSTEM,
             data: Optional[Dict[str, Any]] = None, **kwargs) -> None:
        """Log info message"""
        self._log(logging.INFO, message, category, data, **kwargs)
    
    def warning(self, message: str, category: str = LogCategory.SYSTEM,
                data: Optional[Dict[str, Any]] = None, **kwargs) -> None:
        """Log warning message"""
        self._log(logging.WARNING, message, category, data, **kwargs)
    
    def error(self, message: str, category: str = LogCategory.SYSTEM,
              data: Optional[Dict[str, Any]] = None, exc_info: bool = True, **kwargs) -> None:
        """Log error message"""
        self._log(logging.ERROR, message, category, data, exc_info=exc_info, **kwargs)
    
    def critical(self, message: str, category: str = LogCategory.SYSTEM,
                 data: Optional[Dict[str, Any]] = None, exc_info: bool = True, **kwargs) -> None:
        """Log critical message"""
        self._log(logging.CRITICAL, message, category, data, exc_info=exc_info, **kwargs)
    
    def exception(self, message: str, category: str = LogCategory.SYSTEM,
                  data: Optional[Dict[str, Any]] = None, **kwargs) -> None:
        """Log exception with traceback"""
        self._log(logging.ERROR, message, category, data, exc_info=True, **kwargs)
    
    def start_operation(self, operation: str) -> str:
        """Start timing an operation and return operation ID"""
        operation_id = str(uuid.uuid4())
        self._operation_start_times[operation_id] = time.time()
        self.debug(f"Started operation: {operation}", 
                  category=LogCategory.PERFORMANCE,
                  data={'operation': operation, 'operation_id': operation_id})
        return operation_id
    
    def end_operation(self, operation_id: str, operation: str, 
                     success: bool = True, data: Optional[Dict[str, Any]] = None) -> float:
        """End timing an operation and log the duration"""
        if operation_id in self._operation_start_times:
            duration = (time.time() - self._operation_start_times[operation_id]) * 1000
            del self._operation_start_times[operation_id]
            
            log_data = {
                'operation': operation,
                'operation_id': operation_id,
                'duration_ms': duration,
                'success': success
            }
            if data:
                log_data.update(data)
            
            level = logging.INFO if success else logging.WARNING
            message = f"Completed operation: {operation}"
            if not success:
                message = f"Failed operation: {operation}"
            
            self._log(level, message, LogCategory.PERFORMANCE, log_data)
            return duration
        else:
            self.warning(f"Unknown operation ID for end_operation: {operation_id}",
                        category=LogCategory.PERFORMANCE)
            return 0.0


# Global logger instance
_global_logger: Optional[BACmonLogger] = None


def get_logger(name: str = 'bacmon', config: Optional[ConfigParser] = None) -> BACmonLogger:
    """Get the global logger instance"""
    global _global_logger
    if _global_logger is None:
        _global_logger = BACmonLogger(name, config)
    return _global_logger


def configure_logging(config: Optional[ConfigParser] = None) -> BACmonLogger:
    """Configure the global logging system"""
    logger = get_logger(config=config)
    logger.configure(config)
    return logger


# Decorator for automatic error context and timing
def error_context(category: str = LogCategory.SYSTEM, operation: Optional[str] = None,
                 log_entry: bool = True, log_exit: bool = True):
    """Decorator to add error context and timing to functions"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger()
            operation_name = operation or f"{func.__module__}.{func.__name__}"
            
            if log_entry:
                logger.debug(f"Entering {operation_name}", category=category,
                           data={'args_count': len(args), 'kwargs_keys': list(kwargs.keys())})
            
            operation_id = logger.start_operation(operation_name)
            
            try:
                result = func(*args, **kwargs)
                logger.end_operation(operation_id, operation_name, success=True)
                
                if log_exit:
                    logger.debug(f"Exiting {operation_name}", category=category,
                               data={'success': True})
                
                return result
            
            except Exception as e:
                logger.end_operation(operation_id, operation_name, success=False,
                                   data={'error_type': type(e).__name__, 'error_message': str(e)})
                
                # Log the error with context
                logger.exception(f"Error in {operation_name}: {str(e)}", category=category,
                               data={'function': operation_name, 'error_type': type(e).__name__})
                raise
        
        return wrapper
    return decorator


def timed_operation(category: str = LogCategory.PERFORMANCE, operation: Optional[str] = None):
    """Decorator for timing operations without error handling"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger()
            operation_name = operation or f"{func.__module__}.{func.__name__}"
            
            operation_id = logger.start_operation(operation_name)
            try:
                result = func(*args, **kwargs)
                logger.end_operation(operation_id, operation_name, success=True)
                return result
            except Exception as e:
                logger.end_operation(operation_id, operation_name, success=False,
                                   data={'error_type': type(e).__name__})
                raise
        
        return wrapper
    return decorator


# Context manager for request tracking
@contextmanager
def request_context(request_id: Optional[str] = None, operation: Optional[str] = None):
    """Context manager for tracking API requests"""
    if request_id is None:
        request_id = str(uuid.uuid4())
    
    logger = get_logger()
    
    with correlation_context(request_id):
        if operation:
            operation_id = logger.start_operation(operation)
            
        try:
            yield request_id
        finally:
            if operation:
                logger.end_operation(operation_id, operation)


# Convenience function for logging Redis operations
def log_redis_operation(operation: str, key: Optional[str] = None, 
                       success: bool = True, duration_ms: Optional[float] = None,
                       error: Optional[Exception] = None) -> None:
    """Log Redis operation with standardized format"""
    logger = get_logger()
    
    data = {
        'redis_operation': operation,
        'redis_key': key,
        'success': success
    }
    
    if duration_ms is not None:
        data['duration_ms'] = duration_ms
    
    if success:
        logger.info(f"Redis operation completed: {operation}", 
                   category=LogCategory.REDIS, data=data)
    else:
        if error:
            data['error_type'] = type(error).__name__
            data['error_message'] = str(error)
        
        logger.error(f"Redis operation failed: {operation}",
                    category=LogCategory.REDIS, data=data, exc_info=bool(error))


# Health check for logging system
def logging_health_check() -> Dict[str, Any]:
    """Perform health check on logging system"""
    logger = get_logger()
    
    health_status = {
        'status': 'healthy',
        'configured': logger._configured,
        'handlers': len(logger.logger.handlers),
        'level': logger.logger.level,
        'issues': []
    }
    
    # Check if any handlers are present
    if len(logger.logger.handlers) == 0:
        health_status['status'] = 'unhealthy'
        health_status['issues'].append('No log handlers configured')
    
    # Test logging functionality
    try:
        logger.debug("Health check test message", category=LogCategory.SYSTEM)
    except Exception as e:
        health_status['status'] = 'unhealthy'
        health_status['issues'].append(f"Failed to write test log: {str(e)}")
    
    return health_status 