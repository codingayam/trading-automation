"""
Retry logic utilities with exponential backoff for trading automation system.
Provides configurable retry mechanisms for API calls and other operations.
"""
import time
import random
from typing import Callable, Optional, Type, Tuple, Any, List
from functools import wraps
import asyncio

from src.utils.exceptions import RetryableError, RateLimitError, APIError
from src.utils.logging import get_logger
from config.settings import settings

logger = get_logger('retry')

class RetryConfig:
    """Configuration for retry behavior."""
    
    def __init__(self,
                 max_attempts: int = None,
                 backoff_factor: float = None,
                 max_delay: float = 300.0,
                 jitter: bool = True,
                 retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None):
        self.max_attempts = max_attempts or settings.api.retry_max_attempts
        self.backoff_factor = backoff_factor or settings.api.retry_backoff_factor
        self.max_delay = max_delay
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions or (
            RetryableError,
            RateLimitError,
            APIError,
            ConnectionError,
            TimeoutError
        )
    
    def calculate_delay(self, attempt: int, base_delay: float = 1.0) -> float:
        """Calculate delay for given attempt with exponential backoff."""
        delay = base_delay * (self.backoff_factor ** attempt)
        
        # Cap the delay
        delay = min(delay, self.max_delay)
        
        # Add jitter to prevent thundering herd
        if self.jitter:
            delay *= (0.5 + random.random() * 0.5)
        
        return delay

def retry_on_exception(config: Optional[RetryConfig] = None):
    """Decorator for retrying functions on specific exceptions."""
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(config.max_attempts):
                try:
                    result = func(*args, **kwargs)
                    
                    # Log successful retry if this wasn't the first attempt
                    if attempt > 0:
                        logger.info(
                            f"Function {func.__name__} succeeded after {attempt + 1} attempts",
                            function=func.__name__,
                            attempt=attempt + 1,
                            total_attempts=config.max_attempts
                        )
                    
                    return result
                    
                except Exception as e:
                    last_exception = e
                    
                    # Check if this exception should be retried
                    if not isinstance(e, config.retryable_exceptions):
                        logger.error(
                            f"Non-retryable exception in {func.__name__}",
                            exception=e,
                            function=func.__name__,
                            attempt=attempt + 1
                        )
                        raise
                    
                    # Don't retry on the last attempt
                    if attempt == config.max_attempts - 1:
                        logger.error(
                            f"Function {func.__name__} failed after {config.max_attempts} attempts",
                            exception=e,
                            function=func.__name__,
                            total_attempts=config.max_attempts
                        )
                        raise
                    
                    # Calculate delay and wait
                    delay = config.calculate_delay(attempt)
                    
                    # Special handling for rate limit errors
                    if isinstance(e, RateLimitError) and hasattr(e, 'retry_after') and e.retry_after:
                        delay = max(delay, e.retry_after)
                    
                    logger.warning(
                        f"Function {func.__name__} failed, retrying in {delay:.2f}s",
                        exception=e,
                        function=func.__name__,
                        attempt=attempt + 1,
                        delay=delay,
                        total_attempts=config.max_attempts
                    )
                    
                    time.sleep(delay)
            
            # This should never be reached, but just in case
            if last_exception:
                raise last_exception
        
        return wrapper
    return decorator

async def async_retry_on_exception(config: Optional[RetryConfig] = None):
    """Async decorator for retrying async functions on specific exceptions."""
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(config.max_attempts):
                try:
                    result = await func(*args, **kwargs)
                    
                    # Log successful retry if this wasn't the first attempt
                    if attempt > 0:
                        logger.info(
                            f"Async function {func.__name__} succeeded after {attempt + 1} attempts",
                            function=func.__name__,
                            attempt=attempt + 1,
                            total_attempts=config.max_attempts
                        )
                    
                    return result
                    
                except Exception as e:
                    last_exception = e
                    
                    # Check if this exception should be retried
                    if not isinstance(e, config.retryable_exceptions):
                        logger.error(
                            f"Non-retryable exception in async {func.__name__}",
                            exception=e,
                            function=func.__name__,
                            attempt=attempt + 1
                        )
                        raise
                    
                    # Don't retry on the last attempt
                    if attempt == config.max_attempts - 1:
                        logger.error(
                            f"Async function {func.__name__} failed after {config.max_attempts} attempts",
                            exception=e,
                            function=func.__name__,
                            total_attempts=config.max_attempts
                        )
                        raise
                    
                    # Calculate delay and wait
                    delay = config.calculate_delay(attempt)
                    
                    # Special handling for rate limit errors
                    if isinstance(e, RateLimitError) and hasattr(e, 'retry_after') and e.retry_after:
                        delay = max(delay, e.retry_after)
                    
                    logger.warning(
                        f"Async function {func.__name__} failed, retrying in {delay:.2f}s",
                        exception=e,
                        function=func.__name__,
                        attempt=attempt + 1,
                        delay=delay,
                        total_attempts=config.max_attempts
                    )
                    
                    await asyncio.sleep(delay)
            
            # This should never be reached, but just in case
            if last_exception:
                raise last_exception
        
        return wrapper
    return decorator

class RetryContext:
    """Context manager for retry operations with custom logic."""
    
    def __init__(self, config: Optional[RetryConfig] = None, operation_name: str = "operation"):
        self.config = config or RetryConfig()
        self.operation_name = operation_name
        self.attempt = 0
        self.last_exception = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            # Operation succeeded
            if self.attempt > 0:
                logger.info(
                    f"Operation {self.operation_name} succeeded after {self.attempt + 1} attempts",
                    operation=self.operation_name,
                    attempt=self.attempt + 1
                )
            return False
        
        # Operation failed
        self.last_exception = exc_val
        
        # Check if should retry
        if not isinstance(exc_val, self.config.retryable_exceptions):
            logger.error(
                f"Non-retryable exception in {self.operation_name}",
                exception=exc_val,
                operation=self.operation_name,
                attempt=self.attempt + 1
            )
            return False
        
        # Check if we've exhausted retries
        if self.attempt >= self.config.max_attempts - 1:
            logger.error(
                f"Operation {self.operation_name} failed after {self.config.max_attempts} attempts",
                exception=exc_val,
                operation=self.operation_name,
                total_attempts=self.config.max_attempts
            )
            return False
        
        # Calculate delay and wait
        delay = self.config.calculate_delay(self.attempt)
        
        # Special handling for rate limit errors
        if isinstance(exc_val, RateLimitError) and hasattr(exc_val, 'retry_after') and exc_val.retry_after:
            delay = max(delay, exc_val.retry_after)
        
        logger.warning(
            f"Operation {self.operation_name} failed, retrying in {delay:.2f}s",
            exception=exc_val,
            operation=self.operation_name,
            attempt=self.attempt + 1,
            delay=delay,
            total_attempts=self.config.max_attempts
        )
        
        time.sleep(delay)
        self.attempt += 1
        return True  # Suppress exception and continue
    
    def should_continue(self) -> bool:
        """Check if we should continue retrying."""
        return self.attempt < self.config.max_attempts

def retry_operation(operation: Callable, config: Optional[RetryConfig] = None, 
                   operation_name: str = "operation", *args, **kwargs) -> Any:
    """Retry an operation with the given configuration."""
    if config is None:
        config = RetryConfig()
    
    last_exception = None
    
    for attempt in range(config.max_attempts):
        try:
            result = operation(*args, **kwargs)
            
            # Log successful retry if this wasn't the first attempt
            if attempt > 0:
                logger.info(
                    f"Operation {operation_name} succeeded after {attempt + 1} attempts",
                    operation=operation_name,
                    attempt=attempt + 1,
                    total_attempts=config.max_attempts
                )
            
            return result
            
        except Exception as e:
            last_exception = e
            
            # Check if this exception should be retried
            if not isinstance(e, config.retryable_exceptions):
                logger.error(
                    f"Non-retryable exception in {operation_name}",
                    exception=e,
                    operation=operation_name,
                    attempt=attempt + 1
                )
                raise
            
            # Don't retry on the last attempt
            if attempt == config.max_attempts - 1:
                logger.error(
                    f"Operation {operation_name} failed after {config.max_attempts} attempts",
                    exception=e,
                    operation=operation_name,
                    total_attempts=config.max_attempts
                )
                raise
            
            # Calculate delay and wait
            delay = config.calculate_delay(attempt)
            
            # Special handling for rate limit errors
            if isinstance(e, RateLimitError) and hasattr(e, 'retry_after') and e.retry_after:
                delay = max(delay, e.retry_after)
            
            logger.warning(
                f"Operation {operation_name} failed, retrying in {delay:.2f}s",
                exception=e,
                operation=operation_name,
                attempt=attempt + 1,
                delay=delay,
                total_attempts=config.max_attempts
            )
            
            time.sleep(delay)
    
    # This should never be reached, but just in case
    if last_exception:
        raise last_exception

# Predefined retry configurations for common scenarios
API_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    backoff_factor=2.0,
    max_delay=60.0,
    retryable_exceptions=(APIError, ConnectionError, TimeoutError, RateLimitError)
)

DATABASE_RETRY_CONFIG = RetryConfig(
    max_attempts=2,
    backoff_factor=1.5,
    max_delay=10.0,
    retryable_exceptions=(Exception,)  # Retry most database errors
)

TRADING_RETRY_CONFIG = RetryConfig(
    max_attempts=2,
    backoff_factor=3.0,
    max_delay=30.0,
    retryable_exceptions=(APIError, ConnectionError, RateLimitError)
)