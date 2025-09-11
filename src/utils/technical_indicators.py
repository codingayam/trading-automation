"""
Technical Indicators Calculation Utilities.
Provides RSI and other technical analysis calculations with proper data validation.
"""
import pandas as pd
import numpy as np
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime, timedelta
import yfinance as yf

from src.utils.logging import get_logger
from src.utils.exceptions import ValidationError, APIError

logger = get_logger(__name__)

class TechnicalIndicators:
    """
    Technical indicators calculator with data validation and caching.
    
    Features:
    - RSI calculation with customizable periods
    - Data validation and quality checks
    - Caching to reduce API calls
    - Support for multiple data sources
    """
    
    def __init__(self, cache_duration_minutes: int = 5):
        """
        Initialize technical indicators calculator.
        
        Args:
            cache_duration_minutes: How long to cache price data
        """
        self.cache_duration = timedelta(minutes=cache_duration_minutes)
        self._price_cache: Dict[str, Dict[str, Any]] = {}
        
        logger.debug(f"Initialized TechnicalIndicators with {cache_duration_minutes}min cache")
    
    def get_hourly_prices(self, ticker: str, hours: int = 24) -> Optional[pd.DataFrame]:
        """
        Get hourly price data for the ticker.
        
        Args:
            ticker: Stock ticker symbol
            hours: Number of hours of data to fetch
            
        Returns:
            DataFrame with OHLCV data or None if failed
        """
        try:
            cache_key = f"{ticker}_{hours}h"
            now = datetime.now()
            
            # Check cache first
            if cache_key in self._price_cache:
                cache_entry = self._price_cache[cache_key]
                if now - cache_entry['timestamp'] < self.cache_duration:
                    logger.debug(f"Using cached data for {ticker}")
                    return cache_entry['data']
            
            # Fetch new data
            logger.debug(f"Fetching {hours}h of hourly data for {ticker}")
            
            # Calculate period for yfinance
            period = self._calculate_yfinance_period(hours)
            
            # Fetch data from yfinance
            stock = yf.Ticker(ticker)
            data = stock.history(period=period, interval='1h')
            
            if data.empty:
                logger.error(f"No data returned for {ticker}")
                return None
            
            # Validate data quality
            if not self._validate_price_data(data, hours):
                logger.error(f"Data validation failed for {ticker}")
                return None
            
            # Get the last N hours of data
            data = data.tail(hours)
            
            # Cache the result
            self._price_cache[cache_key] = {
                'data': data.copy(),
                'timestamp': now
            }
            
            logger.debug(f"Fetched {len(data)} hours of data for {ticker}")
            return data
        
        except Exception as e:
            logger.error(f"Failed to get hourly prices for {ticker}: {e}")
            return None
    
    def _calculate_yfinance_period(self, hours: int) -> str:
        """Calculate appropriate yfinance period for requested hours."""
        if hours <= 24:
            return "2d"  # Get 2 days to ensure we have enough data
        elif hours <= 168:  # 1 week
            return "1wk"
        elif hours <= 720:  # 1 month  
            return "1mo"
        else:
            return "3mo"
    
    def _validate_price_data(self, data: pd.DataFrame, min_hours: int) -> bool:
        """
        Validate price data quality.
        
        Args:
            data: Price data DataFrame
            min_hours: Minimum required hours of data
            
        Returns:
            True if data passes validation
        """
        try:
            # Check if we have enough data points
            if len(data) < max(min_hours * 0.7, 10):  # At least 70% of requested data or 10 points
                logger.warning(f"Insufficient data points: {len(data)} < {min_hours * 0.7}")
                return False
            
            # Check for required columns
            required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            if not all(col in data.columns for col in required_columns):
                logger.error("Missing required price columns")
                return False
            
            # Check for NaN values in Close prices
            if data['Close'].isna().sum() > len(data) * 0.1:  # More than 10% NaN
                logger.warning(f"Too many NaN values in Close prices: {data['Close'].isna().sum()}")
                return False
            
            # Check for reasonable price values
            close_prices = data['Close'].dropna()
            if close_prices.empty or (close_prices <= 0).any():
                logger.error("Invalid price values found")
                return False
            
            # Check data recency (should be within last few hours)
            latest_time = data.index.max()
            # Handle timezone-aware comparison properly
            current_time = pd.Timestamp.now()
            if latest_time.tz is not None:
                current_time = current_time.tz_localize('UTC').tz_convert(latest_time.tz)
            elif current_time.tz is not None:
                current_time = current_time.tz_localize(None)
                
            if current_time - latest_time > timedelta(hours=6):
                logger.warning(f"Data is stale: latest data from {latest_time}")
                # Don't fail validation, just warn
            
            return True
        
        except Exception as e:
            logger.error(f"Data validation error: {e}")
            return False
    
    def calculate_rsi(self, ticker: str, period: int = 14, hours: int = 24) -> Optional[Tuple[float, Dict[str, Any]]]:
        """
        Calculate RSI (Relative Strength Index) for the ticker.
        
        Args:
            ticker: Stock ticker symbol
            period: RSI period (default 14)
            hours: Hours of data to analyze (default 24)
            
        Returns:
            Tuple of (RSI value, metadata) or None if calculation failed
        """
        try:
            # Need extra data points for RSI calculation
            data_hours = max(hours, period * 3)  # At least 3x the period
            
            # Get price data
            data = self.get_hourly_prices(ticker, data_hours)
            if data is None or data.empty:
                logger.error(f"No price data available for RSI calculation: {ticker}")
                return None
            
            # Calculate RSI
            close_prices = data['Close'].dropna()
            
            if len(close_prices) < period + 1:
                logger.error(f"Insufficient data for RSI calculation: {len(close_prices)} < {period + 1}")
                return None
            
            # Calculate price changes
            delta = close_prices.diff()
            
            # Separate gains and losses
            gains = delta.where(delta > 0, 0.0)
            losses = -delta.where(delta < 0, 0.0)
            
            # Calculate average gains and losses using exponential moving average
            avg_gains = gains.ewm(span=period, adjust=False).mean()
            avg_losses = losses.ewm(span=period, adjust=False).mean()
            
            # Calculate RS and RSI
            rs = avg_gains / avg_losses.replace(0, np.inf)  # Avoid division by zero
            rsi = 100 - (100 / (1 + rs))
            
            # Get the latest RSI value
            latest_rsi = float(rsi.iloc[-1])
            
            # Create metadata
            metadata = {
                'period': period,
                'data_points': len(close_prices),
                'latest_price': float(close_prices.iloc[-1]),
                'price_change': float(delta.iloc[-1]) if not delta.empty else 0.0,
                'calculation_time': datetime.now(),
                'data_start': data.index.min(),
                'data_end': data.index.max(),
                'avg_gain': float(avg_gains.iloc[-1]),
                'avg_loss': float(avg_losses.iloc[-1]),
                'rs': float(rs.iloc[-1])
            }
            
            logger.debug(f"Calculated RSI for {ticker}: {latest_rsi:.2f} (period={period}, data_points={len(close_prices)})")
            return latest_rsi, metadata
        
        except Exception as e:
            logger.error(f"RSI calculation failed for {ticker}: {e}")
            return None
    
    def calculate_simple_moving_average(self, ticker: str, period: int = 20, hours: int = 48) -> Optional[Tuple[float, Dict[str, Any]]]:
        """
        Calculate Simple Moving Average (SMA).
        
        Args:
            ticker: Stock ticker symbol
            period: SMA period
            hours: Hours of data to analyze
            
        Returns:
            Tuple of (SMA value, metadata) or None if calculation failed
        """
        try:
            data = self.get_hourly_prices(ticker, max(hours, period * 2))
            if data is None or data.empty:
                return None
            
            close_prices = data['Close'].dropna()
            if len(close_prices) < period:
                logger.error(f"Insufficient data for SMA calculation: {len(close_prices)} < {period}")
                return None
            
            sma = close_prices.rolling(window=period).mean()
            latest_sma = float(sma.iloc[-1])
            
            metadata = {
                'period': period,
                'data_points': len(close_prices),
                'latest_price': float(close_prices.iloc[-1]),
                'calculation_time': datetime.now()
            }
            
            return latest_sma, metadata
        
        except Exception as e:
            logger.error(f"SMA calculation failed for {ticker}: {e}")
            return None
    
    def get_price_momentum(self, ticker: str, hours: int = 14) -> Optional[Dict[str, float]]:
        """
        Calculate price momentum over specified hours.
        
        Args:
            ticker: Stock ticker symbol
            hours: Hours to look back for momentum
            
        Returns:
            Dictionary with momentum metrics or None if calculation failed
        """
        try:
            data = self.get_hourly_prices(ticker, hours + 2)  # Extra buffer
            if data is None or data.empty:
                return None
            
            close_prices = data['Close'].dropna()
            if len(close_prices) < 2:
                return None
            
            current_price = float(close_prices.iloc[-1])
            past_price = float(close_prices.iloc[0])
            
            # Calculate various momentum metrics
            absolute_change = current_price - past_price
            percent_change = (absolute_change / past_price) * 100
            
            # Price velocity (average change per hour)
            velocity = absolute_change / len(close_prices)
            
            momentum = {
                'absolute_change': absolute_change,
                'percent_change': percent_change,
                'velocity': velocity,
                'current_price': current_price,
                'past_price': past_price,
                'hours_analyzed': hours
            }
            
            return momentum
        
        except Exception as e:
            logger.error(f"Momentum calculation failed for {ticker}: {e}")
            return None
    
    def clear_cache(self) -> None:
        """Clear the price data cache."""
        self._price_cache.clear()
        logger.debug("Cleared price data cache")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        now = datetime.now()
        active_entries = 0
        
        for entry in self._price_cache.values():
            if now - entry['timestamp'] < self.cache_duration:
                active_entries += 1
        
        return {
            'total_entries': len(self._price_cache),
            'active_entries': active_entries,
            'cache_duration_minutes': self.cache_duration.total_seconds() / 60
        }

# Global instance for easy import
technical_indicators = TechnicalIndicators()

# Utility functions for easy access
def calculate_rsi(ticker: str, period: int = 14, hours: int = 24) -> Optional[Tuple[float, Dict[str, Any]]]:
    """Calculate RSI for a ticker."""
    return technical_indicators.calculate_rsi(ticker, period, hours)

def get_hourly_prices(ticker: str, hours: int = 24) -> Optional[pd.DataFrame]:
    """Get hourly price data for a ticker."""
    return technical_indicators.get_hourly_prices(ticker, hours)

def clear_price_cache() -> None:
    """Clear the global price data cache."""
    technical_indicators.clear_cache()