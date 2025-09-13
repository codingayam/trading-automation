"""
Logging configuration and utilities for trading automation system.
Provides structured logging with rotation, levels, and performance monitoring.
"""
import os
import logging
import logging.handlers
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import json
import traceback
from functools import wraps
import time

from config.settings import settings

class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging with JSON output."""
    
    def __init__(self):
        super().__init__()
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add extra fields if present
        if hasattr(record, 'agent_id'):
            log_entry['agent_id'] = record.agent_id
        if hasattr(record, 'ticker'):
            log_entry['ticker'] = record.ticker
        if hasattr(record, 'trade_id'):
            log_entry['trade_id'] = record.trade_id
        if hasattr(record, 'execution_time'):
            log_entry['execution_time'] = record.execution_time
        if hasattr(record, 'api_endpoint'):
            log_entry['api_endpoint'] = record.api_endpoint
        if hasattr(record, 'response_time'):
            log_entry['response_time'] = record.response_time
        
        # Add exception information if present
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        return json.dumps(log_entry)

class TradingLogger:
    """Enhanced logger for trading system with structured logging."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.name = name
    
    def info(self, message: str, **kwargs):
        """Log info message with optional structured data."""
        extra = {k: v for k, v in kwargs.items() if v is not None}
        self.logger.info(message, extra=extra)
    
    def debug(self, message: str, **kwargs):
        """Log debug message with optional structured data."""
        extra = {k: v for k, v in kwargs.items() if v is not None}
        self.logger.debug(message, extra=extra)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with optional structured data."""
        extra = {k: v for k, v in kwargs.items() if v is not None}
        self.logger.warning(message, extra=extra)
    
    def error(self, message: str, exception: Optional[Exception] = None, **kwargs):
        """Log error message with optional exception and structured data."""
        extra = {k: v for k, v in kwargs.items() if v is not None}
        if exception:
            self.logger.error(message, exc_info=exception, extra=extra)
        else:
            self.logger.error(message, extra=extra)
    
    def trade_execution(self, agent_id: str, ticker: str, action: str, 
                       quantity: float, price: Optional[float] = None, 
                       order_id: Optional[str] = None, **kwargs):
        """Log trade execution with structured trade data."""
        self.info(
            f"Trade execution: {action} {quantity} shares of {ticker}",
            agent_id=agent_id,
            ticker=ticker,
            action=action,
            quantity=quantity,
            price=price,
            order_id=order_id,
            **kwargs
        )
    
    def api_call(self, endpoint: str, response_time: float, 
                status_code: Optional[int] = None, **kwargs):
        """Log API call with performance metrics."""
        self.info(
            f"API call to {endpoint} completed in {response_time:.3f}s",
            api_endpoint=endpoint,
            response_time=response_time,
            status_code=status_code,
            **kwargs
        )
    
    def performance_metric(self, metric_name: str, value: float, 
                          agent_id: Optional[str] = None, **kwargs):
        """Log performance metrics."""
        self.info(
            f"Performance metric {metric_name}: {value}",
            metric_name=metric_name,
            metric_value=value,
            agent_id=agent_id,
            **kwargs
        )

def setup_logging() -> None:
    """Set up logging configuration for the trading system."""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.logging.level.upper()))
    
    # Clear any existing handlers to avoid duplicate logs
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    if settings.is_production:
        # On Railway (production), log JSON directly to the console/stdout
        console_handler = logging.StreamHandler()
        formatter = StructuredFormatter()
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        
        logger = get_logger('system')
        logger.info(
            "Production logging configured (JSON to console)",
            log_level=settings.logging.level
        )
    else:
        # In development, log text to console and JSON to files
        log_dir = Path(settings.logging.full_path)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Console handler with simple text format
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
        
        # File handler with structured JSON format
        log_file = log_dir / 'trading_automation.log'
        file_handler = logging.handlers.TimedRotatingFileHandler(
            filename=log_file,
            when='midnight',
            interval=1,
            backupCount=settings.logging.retention_days,
            encoding='utf-8'
        )
        file_handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(file_handler)
        
        # Set up separate log files for different components
        _setup_component_loggers(log_dir)
        
        logger = get_logger('system')
        logger.info(
            "Development logging configured (text to console, JSON to files)",
            log_level=settings.logging.level,
            log_path=str(log_file)
        )

def _setup_component_loggers(log_dir: Path) -> None:
    """Set up specialized loggers for different system components."""
    
    # Agent execution logger
    agent_logger = logging.getLogger('agents')
    agent_handler = logging.handlers.TimedRotatingFileHandler(
        filename=log_dir / 'agents.log',
        when='midnight',
        interval=1,
        backupCount=settings.logging.retention_days,
        encoding='utf-8'
    )
    agent_handler.setFormatter(StructuredFormatter())
    agent_logger.addHandler(agent_handler)
    
    # API calls logger
    api_logger = logging.getLogger('api')
    api_handler = logging.handlers.TimedRotatingFileHandler(
        filename=log_dir / 'api.log',
        when='midnight', 
        interval=1,
        backupCount=settings.logging.retention_days,
        encoding='utf-8'
    )
    api_handler.setFormatter(StructuredFormatter())
    api_logger.addHandler(api_handler)
    
    # Trading execution logger
    trading_logger = logging.getLogger('trading')
    trading_handler = logging.handlers.TimedRotatingFileHandler(
        filename=log_dir / 'trading.log',
        when='midnight',
        interval=1, 
        backupCount=settings.logging.retention_days,
        encoding='utf-8'
    )
    trading_handler.setFormatter(StructuredFormatter())
    trading_logger.addHandler(trading_handler)
    
    # Performance metrics logger
    performance_logger = logging.getLogger('performance')
    performance_handler = logging.handlers.TimedRotatingFileHandler(
        filename=log_dir / 'performance.log',
        when='midnight',
        interval=1,
        backupCount=settings.logging.retention_days,
        encoding='utf-8'
    )
    performance_handler.setFormatter(StructuredFormatter())
    performance_logger.addHandler(performance_handler)

def get_logger(name: str) -> TradingLogger:
    """Get a structured logger instance."""
    return TradingLogger(name)

def log_execution_time(logger_name: Optional[str] = None):
    """Decorator to log function execution time."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger(logger_name or func.__module__)
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                logger.info(
                    f"Function {func.__name__} completed",
                    function=func.__name__,
                    execution_time=execution_time,
                    status='success'
                )
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(
                    f"Function {func.__name__} failed",
                    exception=e,
                    function=func.__name__,
                    execution_time=execution_time,
                    status='error'
                )
                raise
        
        return wrapper
    return decorator

def log_api_call(endpoint: str, logger_name: Optional[str] = None):
    """Decorator to log API calls with timing and error handling."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger(logger_name or 'api')
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                response_time = time.time() - start_time
                
                # Extract status code if present in result
                status_code = None
                if hasattr(result, 'status_code'):
                    status_code = result.status_code
                elif isinstance(result, tuple) and len(result) > 1:
                    if hasattr(result[1], 'status_code'):
                        status_code = result[1].status_code
                
                logger.api_call(
                    endpoint=endpoint,
                    response_time=response_time,
                    status_code=status_code,
                    status='success'
                )
                return result
            except Exception as e:
                response_time = time.time() - start_time
                logger.error(
                    f"API call to {endpoint} failed",
                    exception=e,
                    api_endpoint=endpoint,
                    response_time=response_time,
                    status='error'
                )
                raise
        
        return wrapper
    return decorator

# Initialize logging on module import
if not logging.getLogger().handlers:
    setup_logging()