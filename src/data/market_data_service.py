"""
Market Data Service using yfinance for supplementary market data and calculations.
Handles price data fetching, caching, validation, and return calculations.
"""
import time
import yfinance as yf
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
import pandas as pd
import numpy as np
from threading import Lock
import pytz

from config.settings import settings
from src.utils.logging import get_logger
from src.utils.exceptions import APIError, DataValidationError
from src.utils.monitoring import metrics_collector

logger = get_logger(__name__)

@dataclass
class PriceData:
    """Price data structure."""
    ticker: str
    current_price: float
    open_price: float
    high_price: float
    low_price: float
    volume: int
    timestamp: datetime
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None

@dataclass
class ReturnData:
    """Return calculation data structure."""
    ticker: str
    current_price: float
    reference_price: float
    return_amount: float
    return_percent: float
    period_type: str  # "1d", "since_open", etc.
    calculation_time: datetime

class MarketDataService:
    """
    Market Data Service using yfinance for price data and return calculations.
    
    Features:
    - Current price fetching with caching (15-minute cache)
    - Historical price data for return calculations
    - Ticker symbol validation and error handling
    - Dividend and split adjustment handling
    - Market hours detection and handling
    - Price data validation and sanity checks
    - Fallback mechanisms when data is unavailable
    - Batch price fetching for multiple tickers
    - Return calculation utilities (1-day, since-open)
    - Market holidays and weekend data gaps handling
    """
    
    def __init__(self):
        """Initialize Market Data Service."""
        self.cache_ttl = 900  # 15 minutes
        self.price_cache = {}
        self.info_cache = {}
        self.cache_lock = Lock()
        
        # Market hours (Eastern Time)
        self.market_tz = pytz.timezone('US/Eastern')
        self.market_open = 9, 30  # 9:30 AM
        self.market_close = 16, 0  # 4:00 PM
        
        # Validation thresholds
        self.max_price_change_percent = 50.0  # Maximum daily price change for validation
        self.min_price = 0.01  # Minimum valid price
        self.max_price = 100000.0  # Maximum valid price
        
        logger.info("Initialized Market Data Service with 15-minute cache")
    
    def _is_market_open(self) -> bool:
        """
        Check if market is currently open.
        
        Returns:
            True if market is open
        """
        now = datetime.now(self.market_tz)
        
        # Check if weekend
        if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False
        
        # Check market hours
        market_open = now.replace(hour=self.market_open[0], minute=self.market_open[1], second=0, microsecond=0)
        market_close = now.replace(hour=self.market_close[0], minute=self.market_close[1], second=0, microsecond=0)
        
        return market_open <= now <= market_close
    
    def _get_last_trading_day(self) -> date:
        """
        Get the last trading day (excluding weekends).
        
        Returns:
            Last trading day as date
        """
        today = date.today()
        
        # If today is Monday, last trading day is Friday
        if today.weekday() == 0:  # Monday
            return today - timedelta(days=3)
        # If today is Sunday, last trading day is Friday
        elif today.weekday() == 6:  # Sunday
            return today - timedelta(days=2)
        # If today is Saturday, last trading day is Friday
        elif today.weekday() == 5:  # Saturday
            return today - timedelta(days=1)
        else:
            # Tuesday-Friday, last trading day is yesterday
            return today - timedelta(days=1)
    
    def _validate_price_data(self, ticker: str, price: float, reference_price: Optional[float] = None) -> bool:
        """
        Validate price data for sanity checks.
        
        Args:
            ticker: Stock ticker symbol
            price: Price to validate
            reference_price: Reference price for change validation
            
        Returns:
            True if price data is valid
        """
        # Check price range
        if not (self.min_price <= price <= self.max_price):
            logger.warning(f"Price {price} for {ticker} outside valid range ({self.min_price}-{self.max_price})")
            return False
        
        # Check for reasonable price changes if reference price provided
        if reference_price and reference_price > 0:
            change_percent = abs(price - reference_price) / reference_price * 100
            if change_percent > self.max_price_change_percent:
                logger.warning(f"Price change {change_percent:.1f}% for {ticker} exceeds threshold ({self.max_price_change_percent}%)")
                return False
        
        return True
    
    def _get_cached_price(self, ticker: str) -> Optional[PriceData]:
        """
        Get cached price data if available and not expired.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Cached price data or None
        """
        with self.cache_lock:
            if ticker in self.price_cache:
                price_data, cache_time = self.price_cache[ticker]
                if time.time() - cache_time < self.cache_ttl:
                    logger.debug(f"Using cached price data for {ticker}")
                    return price_data
                else:
                    # Remove expired cache entry
                    del self.price_cache[ticker]
        
        return None
    
    def _cache_price_data(self, ticker: str, price_data: PriceData) -> None:
        """
        Cache price data.
        
        Args:
            ticker: Stock ticker symbol
            price_data: Price data to cache
        """
        with self.cache_lock:
            self.price_cache[ticker] = (price_data, time.time())
    
    def get_current_price(self, ticker: str, use_cache: bool = True) -> Optional[float]:
        """
        Get current price for a ticker.
        
        Args:
            ticker: Stock ticker symbol
            use_cache: Whether to use cached data
            
        Returns:
            Current price or None if unavailable
        """
        if use_cache:
            cached_data = self._get_cached_price(ticker)
            if cached_data:
                return cached_data.current_price
        
        try:
            start_time = time.time()
            stock = yf.Ticker(ticker)
            
            # Try to get real-time price first
            try:
                info = stock.info
                current_price = info.get('currentPrice') or info.get('regularMarketPrice')
                
                if current_price and self._validate_price_data(ticker, current_price):
                    request_time = time.time() - start_time
                    metrics_collector.record_execution_time("yfinance_current_price", request_time)
                    logger.debug(f"Got current price for {ticker}: ${current_price:.2f}")
                    return float(current_price)
            except Exception as e:
                logger.debug(f"Failed to get current price from info for {ticker}: {e}")
            
            # Fallback to historical data (most recent)
            try:
                hist = stock.history(period="1d", interval="1m")
                if not hist.empty:
                    latest_price = hist['Close'].iloc[-1]
                    if self._validate_price_data(ticker, latest_price):
                        request_time = time.time() - start_time
                        metrics_collector.record_execution_time("yfinance_hist_price", request_time)
                        logger.debug(f"Got latest price from history for {ticker}: ${latest_price:.2f}")
                        return float(latest_price)
            except Exception as e:
                logger.debug(f"Failed to get latest price from history for {ticker}: {e}")
            
            logger.warning(f"Could not get current price for {ticker}")
            return None
        
        except Exception as e:
            logger.error(f"Error getting current price for {ticker}: {e}")
            return None
    
    def get_price_data(self, ticker: str, use_cache: bool = True) -> Optional[PriceData]:
        """
        Get comprehensive price data for a ticker.
        
        Args:
            ticker: Stock ticker symbol
            use_cache: Whether to use cached data
            
        Returns:
            Price data or None if unavailable
        """
        if use_cache:
            cached_data = self._get_cached_price(ticker)
            if cached_data:
                return cached_data
        
        try:
            start_time = time.time()
            stock = yf.Ticker(ticker)
            
            # Get basic info
            info = stock.info
            current_price = info.get('currentPrice') or info.get('regularMarketPrice')
            
            if not current_price:
                logger.warning(f"No current price available for {ticker}")
                return None
            
            # Get today's OHLC data
            hist = stock.history(period="2d")  # Get 2 days to ensure we have today's data
            
            if hist.empty:
                logger.warning(f"No historical data available for {ticker}")
                return None
            
            # Use the most recent day's data
            latest_day = hist.iloc[-1]
            
            price_data = PriceData(
                ticker=ticker,
                current_price=float(current_price),
                open_price=float(latest_day['Open']),
                high_price=float(latest_day['High']),
                low_price=float(latest_day['Low']),
                volume=int(latest_day['Volume']),
                timestamp=datetime.now(),
                market_cap=info.get('marketCap'),
                pe_ratio=info.get('trailingPE')
            )
            
            # Validate price data
            if not self._validate_price_data(ticker, price_data.current_price):
                logger.warning(f"Price data validation failed for {ticker}")
                return None
            
            # Cache the data
            self._cache_price_data(ticker, price_data)
            
            request_time = time.time() - start_time
            metrics_collector.record_execution_time("yfinance_price_data", request_time)
            
            logger.debug(f"Retrieved price data for {ticker} in {request_time:.2f}s")
            return price_data
        
        except Exception as e:
            logger.error(f"Error getting price data for {ticker}: {e}")
            return None
    
    def get_historical_prices(self, ticker: str, start_date: date, end_date: Optional[date] = None) -> Optional[pd.DataFrame]:
        """
        Get historical price data for a ticker.
        
        Args:
            ticker: Stock ticker symbol
            start_date: Start date for historical data
            end_date: End date for historical data (default: today)
            
        Returns:
            DataFrame with historical prices or None if unavailable
        """
        if end_date is None:
            end_date = date.today()
        
        try:
            start_time = time.time()
            stock = yf.Ticker(ticker)
            
            hist = stock.history(
                start=start_date,
                end=end_date + timedelta(days=1),  # yfinance end date is exclusive
                auto_adjust=True,  # Adjust for splits and dividends
                prepost=False  # Don't include pre/post market data
            )
            
            if hist.empty:
                logger.warning(f"No historical data available for {ticker} from {start_date} to {end_date}")
                return None
            
            request_time = time.time() - start_time
            metrics_collector.record_execution_time("yfinance_historical", request_time)
            
            logger.debug(f"Retrieved {len(hist)} days of historical data for {ticker}")
            return hist
        
        except Exception as e:
            logger.error(f"Error getting historical prices for {ticker}: {e}")
            return None
    
    def calculate_return(self, ticker: str, reference_date: Optional[date] = None, 
                        reference_price: Optional[float] = None) -> Optional[ReturnData]:
        """
        Calculate return for a ticker against a reference point.
        
        Args:
            ticker: Stock ticker symbol
            reference_date: Date for reference price (if reference_price not provided)
            reference_price: Specific reference price to use
            
        Returns:
            Return data or None if calculation fails
        """
        current_price = self.get_current_price(ticker)
        if not current_price:
            logger.error(f"Cannot calculate return for {ticker}: no current price")
            return None
        
        # Get reference price
        if reference_price is None:
            if reference_date is None:
                reference_date = self._get_last_trading_day()
            
            # Get historical data for reference date
            hist = self.get_historical_prices(ticker, reference_date, reference_date)
            if hist is None or hist.empty:
                logger.error(f"Cannot calculate return for {ticker}: no reference price for {reference_date}")
                return None
            
            reference_price = float(hist['Close'].iloc[0])
        
        if reference_price <= 0:
            logger.error(f"Invalid reference price for {ticker}: {reference_price}")
            return None
        
        # Calculate return
        return_amount = current_price - reference_price
        return_percent = (return_amount / reference_price) * 100
        
        period_type = "custom"
        if reference_date:
            if reference_date == self._get_last_trading_day():
                period_type = "1d"
            elif reference_date == date.today():
                period_type = "since_open"
        
        return ReturnData(
            ticker=ticker,
            current_price=current_price,
            reference_price=reference_price,
            return_amount=return_amount,
            return_percent=return_percent,
            period_type=period_type,
            calculation_time=datetime.now()
        )
    
    def calculate_since_open_return(self, ticker: str) -> Optional[ReturnData]:
        """
        Calculate return since market open today.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Return data or None if calculation fails
        """
        price_data = self.get_price_data(ticker)
        if not price_data:
            return None
        
        return_amount = price_data.current_price - price_data.open_price
        return_percent = (return_amount / price_data.open_price) * 100 if price_data.open_price > 0 else 0
        
        return ReturnData(
            ticker=ticker,
            current_price=price_data.current_price,
            reference_price=price_data.open_price,
            return_amount=return_amount,
            return_percent=return_percent,
            period_type="since_open",
            calculation_time=datetime.now()
        )
    
    def calculate_daily_return(self, ticker: str) -> Optional[ReturnData]:
        """
        Calculate 1-day return (current price vs previous close).
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Return data or None if calculation fails
        """
        return self.calculate_return(ticker, reference_date=self._get_last_trading_day())
    
    def get_batch_prices(self, tickers: List[str], use_cache: bool = True) -> Dict[str, Optional[float]]:
        """
        Get current prices for multiple tickers.
        
        Args:
            tickers: List of stock ticker symbols
            use_cache: Whether to use cached data
            
        Returns:
            Dictionary mapping ticker to current price (None if unavailable)
        """
        results = {}
        
        # Check cache first if enabled
        uncached_tickers = []
        if use_cache:
            for ticker in tickers:
                cached_data = self._get_cached_price(ticker)
                if cached_data:
                    results[ticker] = cached_data.current_price
                else:
                    uncached_tickers.append(ticker)
        else:
            uncached_tickers = tickers
        
        # Fetch uncached tickers
        if uncached_tickers:
            try:
                start_time = time.time()
                
                # Use yfinance's batch download for efficiency
                data = yf.download(uncached_tickers, period="1d", interval="1m", group_by='ticker', progress=False)
                
                for ticker in uncached_tickers:
                    try:
                        if len(uncached_tickers) == 1:
                            ticker_data = data
                        else:
                            ticker_data = data[ticker] if ticker in data.columns.levels[0] else pd.DataFrame()
                        
                        if not ticker_data.empty:
                            latest_price = float(ticker_data['Close'].iloc[-1])
                            if self._validate_price_data(ticker, latest_price):
                                results[ticker] = latest_price
                            else:
                                results[ticker] = None
                        else:
                            results[ticker] = None
                    except Exception as e:
                        logger.warning(f"Failed to process batch data for {ticker}: {e}")
                        results[ticker] = None
                
                request_time = time.time() - start_time
                metrics_collector.record_execution_time("yfinance_batch_prices", request_time)
                logger.info(f"Retrieved batch prices for {len(uncached_tickers)} tickers in {request_time:.2f}s")
            
            except Exception as e:
                logger.error(f"Batch price fetch failed: {e}")
                # Fallback to individual requests
                for ticker in uncached_tickers:
                    results[ticker] = self.get_current_price(ticker, use_cache=False)
        
        successful_fetches = sum(1 for price in results.values() if price is not None)
        logger.info(f"Batch price results: {successful_fetches}/{len(tickers)} successful")
        
        return results
    
    def validate_ticker(self, ticker: str) -> bool:
        """
        Validate that a ticker symbol exists and has data.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            True if ticker is valid
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Check if we got valid info
            if not info or info.get('regularMarketPrice') is None:
                # Fallback: try to get some historical data
                hist = stock.history(period="1d")
                return not hist.empty
            
            return True
        
        except Exception as e:
            logger.debug(f"Ticker validation failed for {ticker}: {e}")
            return False
    
    def is_market_holiday(self, target_date: date) -> bool:
        """
        Check if a date is a market holiday (basic implementation).
        
        Args:
            target_date: Date to check
            
        Returns:
            True if it's likely a market holiday
        """
        # This is a simplified implementation
        # In production, you'd want to use a proper market calendar
        
        # Weekend check
        if target_date.weekday() >= 5:  # Saturday or Sunday
            return True
        
        # Common holidays (simplified - doesn't account for observed dates)
        year = target_date.year
        holidays = [
            date(year, 1, 1),   # New Year's Day
            date(year, 7, 4),   # Independence Day
            date(year, 12, 25), # Christmas Day
        ]
        
        return target_date in holidays
    
    def get_market_status(self) -> Dict[str, Any]:
        """
        Get current market status information.
        
        Returns:
            Dictionary with market status information
        """
        now = datetime.now(self.market_tz)
        is_open = self._is_market_open()
        is_weekend = now.weekday() >= 5
        is_holiday = self.is_market_holiday(now.date())
        
        # Calculate next market open/close
        if is_open:
            next_close = now.replace(hour=self.market_close[0], minute=self.market_close[1], second=0, microsecond=0)
            if next_close <= now:
                next_close += timedelta(days=1)
            next_event = "close"
            next_event_time = next_close
        else:
            next_open = now.replace(hour=self.market_open[0], minute=self.market_open[1], second=0, microsecond=0)
            if next_open <= now or is_weekend:
                # Move to next weekday
                days_to_add = 1
                while (now + timedelta(days=days_to_add)).weekday() >= 5:
                    days_to_add += 1
                next_open = (now + timedelta(days=days_to_add)).replace(
                    hour=self.market_open[0], minute=self.market_open[1], second=0, microsecond=0
                )
            next_event = "open"
            next_event_time = next_open
        
        return {
            'is_open': is_open,
            'is_weekend': is_weekend,
            'is_holiday': is_holiday,
            'current_time': now.isoformat(),
            'market_timezone': str(self.market_tz),
            'next_event': next_event,
            'next_event_time': next_event_time.isoformat(),
            'cache_stats': self.get_cache_stats()
        }
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring."""
        with self.cache_lock:
            return {
                'price_cache_size': len(self.price_cache),
                'info_cache_size': len(self.info_cache),
                'cache_ttl_seconds': self.cache_ttl
            }
    
    def clear_cache(self) -> None:
        """Clear all cached data."""
        with self.cache_lock:
            self.price_cache.clear()
            self.info_cache.clear()
            logger.info("Market data cache cleared")