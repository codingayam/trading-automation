"""
Custom exception classes and error handling framework for trading automation system.
Provides structured exception handling with logging and recovery mechanisms.
"""
from typing import Optional, Dict, Any
from datetime import datetime

class TradingSystemError(Exception):
    """Base exception class for all trading system errors."""
    
    def __init__(self, message: str, error_code: Optional[str] = None, 
                 context: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.context = context or {}
        self.cause = cause
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging."""
        return {
            'error_type': self.__class__.__name__,
            'error_code': self.error_code,
            'message': self.message,
            'context': self.context,
            'timestamp': self.timestamp.isoformat(),
            'cause': str(self.cause) if self.cause else None
        }

class ConfigurationError(TradingSystemError):
    """Raised when there are configuration-related errors."""
    pass

class DatabaseError(TradingSystemError):
    """Raised when database operations fail."""
    pass

class APIError(TradingSystemError):
    """Base class for API-related errors."""
    
    def __init__(self, message: str, api_name: str, status_code: Optional[int] = None,
                 response_data: Optional[Dict[str, Any]] = None, **kwargs):
        context = kwargs.get('context', {})
        context.update({
            'api_name': api_name,
            'status_code': status_code,
            'response_data': response_data
        })
        # Filter kwargs to only include those accepted by TradingSystemError
        filtered_kwargs = {k: v for k, v in kwargs.items() if k in ['error_code', 'context', 'cause']}
        super().__init__(message, context=context, **filtered_kwargs)
        self.api_name = api_name
        self.status_code = status_code
        self.response_data = response_data

class QuiverAPIError(APIError):
    """Raised when Quiver API operations fail."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, api_name='Quiver', **kwargs)

class AlpacaAPIError(APIError):
    """Raised when Alpaca API operations fail."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, api_name='Alpaca', **kwargs)

class YFinanceError(APIError):
    """Raised when yfinance operations fail."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, api_name='yfinance', **kwargs)

class TradingError(TradingSystemError):
    """Raised when trading operations fail."""
    
    def __init__(self, message: str, agent_id: Optional[str] = None, 
                 ticker: Optional[str] = None, order_id: Optional[str] = None, **kwargs):
        context = kwargs.get('context', {})
        context.update({
            'agent_id': agent_id,
            'ticker': ticker,
            'order_id': order_id
        })
        super().__init__(message, context=context, **kwargs)
        self.agent_id = agent_id
        self.ticker = ticker
        self.order_id = order_id

class AgentError(TradingSystemError):
    """Raised when agent operations fail."""
    
    def __init__(self, message: str, agent_id: Optional[str] = None, **kwargs):
        context = kwargs.get('context', {})
        context.update({'agent_id': agent_id})
        super().__init__(message, context=context, **kwargs)
        self.agent_id = agent_id

class PositionError(TradingSystemError):
    """Raised when position management fails."""
    
    def __init__(self, message: str, agent_id: Optional[str] = None, 
                 ticker: Optional[str] = None, **kwargs):
        context = kwargs.get('context', {})
        context.update({
            'agent_id': agent_id,
            'ticker': ticker
        })
        super().__init__(message, context=context, **kwargs)
        self.agent_id = agent_id
        self.ticker = ticker

class SchedulingError(TradingSystemError):
    """Raised when scheduling operations fail."""
    pass

class SchedulerError(SchedulingError):
    """Alias for SchedulingError - raised when scheduler operations fail."""
    pass

class ValidationError(TradingSystemError):
    """Raised when data validation fails."""
    
    def __init__(self, message: str, field: Optional[str] = None, 
                 value: Optional[Any] = None, **kwargs):
        context = kwargs.get('context', {})
        context.update({
            'field': field,
            'value': str(value) if value is not None else None
        })
        super().__init__(message, context=context, **kwargs)
        self.field = field
        self.value = value

class RateLimitError(APIError):
    """Raised when API rate limits are exceeded."""
    
    def __init__(self, message: str, api_name: str = "Unknown", retry_after: Optional[int] = None, **kwargs):
        context = kwargs.get('context', {})
        context.update({'retry_after': retry_after})
        # Filter out retry_after from kwargs before passing to parent
        filtered_kwargs = {k: v for k, v in kwargs.items() if k != 'retry_after'}
        super().__init__(message, api_name=api_name, context=context, **filtered_kwargs)
        self.retry_after = retry_after

class InsufficientFundsError(TradingError):
    """Raised when there are insufficient funds for a trade."""
    
    def __init__(self, message: str, required_amount: Optional[float] = None,
                 available_amount: Optional[float] = None, **kwargs):
        context = kwargs.get('context', {})
        context.update({
            'required_amount': required_amount,
            'available_amount': available_amount
        })
        super().__init__(message, context=context, **kwargs)
        self.required_amount = required_amount
        self.available_amount = available_amount

class MarketClosedError(TradingError):
    """Raised when attempting to trade during market closure."""
    pass

class InvalidTickerError(ValidationError):
    """Raised when an invalid ticker symbol is used."""
    
    def __init__(self, message: str, ticker: Optional[str] = None, **kwargs):
        super().__init__(message, field='ticker', value=ticker, **kwargs)
        self.ticker = ticker

class DataProcessingError(TradingSystemError):
    """Raised when data processing operations fail."""
    
    def __init__(self, message: str, data_source: Optional[str] = None, 
                 processing_step: Optional[str] = None, **kwargs):
        context = kwargs.get('context', {})
        context.update({
            'data_source': data_source,
            'processing_step': processing_step
        })
        super().__init__(message, context=context, **kwargs)
        self.data_source = data_source
        self.processing_step = processing_step

class DataValidationError(ValidationError):
    """Raised when data validation fails specifically for API data."""
    
    def __init__(self, message: str, data_source: Optional[str] = None, 
                 field: Optional[str] = None, value: Optional[Any] = None, **kwargs):
        context = kwargs.get('context', {})
        context.update({'data_source': data_source})
        super().__init__(message, field=field, value=value, context=context, **kwargs)
        self.data_source = data_source

class RetryableError(TradingSystemError):
    """Base class for errors that should be retried."""
    
    def __init__(self, message: str, max_retries: int = 3, **kwargs):
        super().__init__(message, **kwargs)
        self.max_retries = max_retries
        self.retry_count = 0

class NonRetryableError(TradingSystemError):
    """Base class for errors that should not be retried."""
    pass