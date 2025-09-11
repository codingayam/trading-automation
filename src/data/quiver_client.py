"""
Quiver API client for fetching congressional trading data.
Handles authentication, rate limiting, data filtering, and fuzzy name matching.
"""
import time
import json
import requests
from datetime import datetime, date
from typing import Dict, List, Any, Optional
from difflib import SequenceMatcher
from dataclasses import dataclass

from config.settings import settings
from src.utils.logging import get_logger
from src.utils.exceptions import APIError, ValidationError
from src.utils.retry import retry_on_exception, API_RETRY_CONFIG
from src.utils.monitoring import metrics_collector

logger = get_logger(__name__)

@dataclass
class CongressionalTrade:
    """Data structure for a congressional trade."""
    politician: str
    ticker: str
    transaction_date: date
    trade_type: str  # "Purchase" or "Sale"
    amount_range: str
    amount_min: float
    amount_max: float
    last_modified: date
    raw_data: Dict[str, Any]

class QuiverClient:
    """
    Quiver API client for congressional trading data.
    
    Features:
    - Authentication and rate limiting
    - Date parameter filtering
    - Transaction filtering (>$50,000 minimum value)
    - Fuzzy name matching with configurable similarity threshold
    - Exponential backoff for rate limit handling
    - Request/response logging with timing metrics
    - Response caching for development/testing
    """
    
    BASE_URL = "https://api.quiverquant.com"
    CONGRESS_ENDPOINT = "/beta/bulk/congresstrading"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Quiver client.
        
        Args:
            api_key: Quiver API key. If None, uses settings configuration.
        """
        self.api_key = api_key or settings.api.quiver_api_key
        if not self.api_key:
            raise ValueError("Quiver API key is required")
        
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'User-Agent': 'TradingAutomation/1.0',
            'Accept': 'application/json'
        })
        
        # Rate limiting
        self.rate_limit_per_minute = settings.api.rate_limit_per_minute
        self.last_request_time = 0
        self.request_count = 0
        self.rate_limit_window_start = time.time()
        
        # Configuration
        self.timeout = settings.api.timeout_seconds
        self.min_trade_value = settings.trading.minimum_congress_trade_value
        self.match_threshold = settings.trading.politician_match_threshold
        
        # Caching for development
        self._cache = {}
        self._cache_ttl = 900  # 15 minutes
        
        logger.info(f"Initialized Quiver client with rate limit: {self.rate_limit_per_minute}/min")
    
    def _wait_for_rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        current_time = time.time()
        
        # Reset counter if window has passed
        if current_time - self.rate_limit_window_start >= 60:
            self.request_count = 0
            self.rate_limit_window_start = current_time
        
        # If we've hit the rate limit, wait
        if self.request_count >= self.rate_limit_per_minute:
            wait_time = 60 - (current_time - self.rate_limit_window_start)
            if wait_time > 0:
                logger.warning(f"Rate limit reached, waiting {wait_time:.1f} seconds")
                time.sleep(wait_time)
                self.request_count = 0
                self.rate_limit_window_start = time.time()
        
        # Minimum delay between requests
        min_delay = 60 / self.rate_limit_per_minute
        time_since_last = current_time - self.last_request_time
        if time_since_last < min_delay:
            delay = min_delay - time_since_last
            time.sleep(delay)
        
        self.last_request_time = time.time()
        self.request_count += 1
    
    @retry_on_exception(API_RETRY_CONFIG)
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Make authenticated request to Quiver API.
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            
        Returns:
            JSON response data
            
        Raises:
            APIError: For API failures or authentication issues
        """
        url = f"{self.BASE_URL}{endpoint}"
        cache_key = f"{endpoint}_{json.dumps(params or {}, sort_keys=True)}"
        
        # Check cache first (development only)
        if settings.is_development and cache_key in self._cache:
            cached_data, cache_time = self._cache[cache_key]
            if time.time() - cache_time < self._cache_ttl:
                logger.debug(f"Using cached response for {endpoint}")
                return cached_data
        
        self._wait_for_rate_limit()
        
        start_time = time.time()
        try:
            logger.debug(f"Making request to {url} with params: {params}")
            
            response = self.session.get(
                url,
                params=params,
                timeout=self.timeout
            )
            
            request_time = time.time() - start_time
            metrics_collector.record_execution_time("quiver_api_request", request_time)
            
            logger.info(f"Quiver API request completed in {request_time:.2f}s, status: {response.status_code}")
            
            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 60))
                logger.warning(f"Rate limited by Quiver API, retrying after {retry_after}s")
                time.sleep(retry_after)
                raise APIError(
                    "Rate limited by Quiver API",
                    api_name="Quiver",
                    status_code=429,
                    retry_after=retry_after
                )
            
            # Handle authentication errors
            if response.status_code == 401:
                raise APIError(
                    "Authentication failed - check Quiver API key",
                    api_name="Quiver",
                    status_code=401
                )
            
            # Handle other errors
            if response.status_code != 200:
                error_msg = f"Quiver API request failed: {response.status_code}"
                try:
                    error_detail = response.json().get('error', 'Unknown error')
                    error_msg += f" - {error_detail}"
                except:
                    error_msg += f" - {response.text[:200]}"
                
                raise APIError(
                    error_msg,
                    api_name="Quiver",
                    status_code=response.status_code
                )
            
            # Parse response
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                raise APIError(
                    f"Invalid JSON response from Quiver API: {e}",
                    api_name="Quiver",
                    status_code=response.status_code
                )
            
            # Cache response (development only)
            if settings.is_development:
                self._cache[cache_key] = (data, time.time())
            
            return data
        
        except requests.exceptions.Timeout:
            raise APIError(
                f"Quiver API request timed out after {self.timeout}s",
                api_name="Quiver",
                status_code=None
            )
        except requests.exceptions.ConnectionError as e:
            raise APIError(
                f"Connection error to Quiver API: {e}",
                api_name="Quiver", 
                status_code=None
            )
        except requests.exceptions.RequestException as e:
            raise APIError(
                f"Request error to Quiver API: {e}",
                api_name="Quiver",
                status_code=None
            )
    
    def get_congressional_trades(self, target_date: Optional[date] = None) -> List[CongressionalTrade]:
        """
        Fetch congressional trading data for a specific date.
        
        Args:
            target_date: Date to fetch trades for. If None, uses current date.
            
        Returns:
            List of congressional trades matching filters
            
        Raises:
            APIError: For API failures
            ValidationError: For data validation issues
        """
        if target_date is None:
            target_date = date.today()
        
        logger.info(f"Fetching congressional trades for {target_date}")
        
        params = {
            'date': target_date.strftime('%Y%m%d')
        }
        
        try:
            start_time = time.time()
            raw_data = self._make_request(self.CONGRESS_ENDPOINT, params)
            
            # Validate response structure
            if not isinstance(raw_data, list):
                raise ValidationError(
                    f"Expected list response from Quiver API, got {type(raw_data)}"
                )
            
            logger.info(f"Received {len(raw_data)} raw congressional trades")
            
            # Parse and filter trades
            trades = []
            for trade_data in raw_data:
                try:
                    trade = self._parse_trade(trade_data)
                    if trade and self._should_include_trade(trade):
                        trades.append(trade)
                except Exception as e:
                    logger.warning(f"Failed to parse trade data: {e}, data: {trade_data}")
                    continue
            
            processing_time = time.time() - start_time
            metrics_collector.record_execution_time("quiver_trades_processing", processing_time)
            
            logger.info(f"Processed {len(trades)} congressional trades after filtering")
            return trades
        
        except APIError:
            raise
        except Exception as e:
            raise ValidationError(f"Error processing congressional trades: {e}")
    
    def _parse_trade(self, trade_data: Dict[str, Any]) -> Optional[CongressionalTrade]:
        """
        Parse raw trade data into CongressionalTrade object.
        
        Args:
            trade_data: Raw trade data from API
            
        Returns:
            CongressionalTrade object or None if parsing fails
        """
        try:
            # Extract required fields
            politician = trade_data.get('representative', '').strip()
            ticker = trade_data.get('ticker', '').strip().upper()
            transaction_date_str = trade_data.get('transactionDate', '')
            trade_type = trade_data.get('type', '').strip()
            amount_range = trade_data.get('range', '')
            
            # Validate required fields
            if not all([politician, ticker, transaction_date_str, trade_type]):
                logger.warning(f"Missing required fields in trade data: {trade_data}")
                return None
            
            # Parse transaction date
            try:
                transaction_date = datetime.strptime(transaction_date_str, '%Y-%m-%d').date()
            except ValueError:
                logger.warning(f"Invalid transaction date format: {transaction_date_str}")
                return None
            
            # Parse last modified date
            last_modified_str = trade_data.get('lastModified', transaction_date_str)
            try:
                last_modified = datetime.strptime(last_modified_str, '%Y-%m-%d').date()
            except ValueError:
                last_modified = transaction_date
            
            # Parse amount range
            amount_min, amount_max = self._parse_amount_range(amount_range)
            
            return CongressionalTrade(
                politician=politician,
                ticker=ticker,
                transaction_date=transaction_date,
                trade_type=trade_type,
                amount_range=amount_range,
                amount_min=amount_min,
                amount_max=amount_max,
                last_modified=last_modified,
                raw_data=trade_data
            )
        
        except Exception as e:
            logger.error(f"Error parsing trade data: {e}, data: {trade_data}")
            return None
    
    def _parse_amount_range(self, amount_range: str) -> tuple[float, float]:
        """
        Parse amount range string into min/max values.
        
        Args:
            amount_range: Amount range string (e.g., "$50,001 - $100,000")
            
        Returns:
            Tuple of (min_amount, max_amount)
        """
        if not amount_range:
            return 0.0, 0.0
        
        try:
            # Remove currency symbols and whitespace
            clean_range = amount_range.replace('$', '').replace(',', '').strip()
            
            # Handle different formats
            if ' - ' in clean_range:
                parts = clean_range.split(' - ')
                min_val = float(parts[0])
                max_val = float(parts[1])
            elif '-' in clean_range:
                parts = clean_range.split('-')
                min_val = float(parts[0])
                max_val = float(parts[1])
            else:
                # Single value
                val = float(clean_range)
                min_val = max_val = val
            
            return min_val, max_val
        
        except (ValueError, IndexError):
            logger.warning(f"Could not parse amount range: {amount_range}")
            return 0.0, 0.0
    
    def _should_include_trade(self, trade: CongressionalTrade) -> bool:
        """
        Determine if trade should be included based on filters.
        
        Args:
            trade: Congressional trade to evaluate
            
        Returns:
            True if trade should be included
        """
        # Only include purchases
        if trade.trade_type.lower() != 'purchase':
            return False
        
        # Check minimum trade value
        if trade.amount_min < self.min_trade_value:
            return False
        
        return True
    
    def find_matching_politicians(self, target_politicians: List[str], trade: CongressionalTrade) -> List[str]:
        """
        Find politicians that match the trade using fuzzy matching.
        
        Args:
            target_politicians: List of politician names to match against
            trade: Congressional trade to match
            
        Returns:
            List of matching politician names
        """
        matches = []
        
        for politician in target_politicians:
            similarity = SequenceMatcher(None, politician.lower(), trade.politician.lower()).ratio()
            
            if similarity >= self.match_threshold:
                matches.append(politician)
                logger.debug(f"Politician match: '{politician}' ~ '{trade.politician}' ({similarity:.2f})")
        
        return matches
    
    def get_trades_for_politicians(self, politicians: List[str], target_date: Optional[date] = None) -> List[CongressionalTrade]:
        """
        Get congressional trades for specific politicians.
        
        Args:
            politicians: List of politician names to match
            target_date: Date to fetch trades for
            
        Returns:
            List of matching congressional trades
        """
        all_trades = self.get_congressional_trades(target_date)
        
        matching_trades = []
        for trade in all_trades:
            if self.find_matching_politicians(politicians, trade):
                matching_trades.append(trade)
        
        logger.info(f"Found {len(matching_trades)} trades matching {len(politicians)} politicians")
        return matching_trades
    
    def test_connection(self) -> bool:
        """
        Test connection to Quiver API.
        
        Returns:
            True if connection is successful
        """
        try:
            # Make a simple request to test authentication
            self._make_request(self.CONGRESS_ENDPOINT, {
                'date': date.today().strftime('%Y%m%d')
            })
            logger.info("Quiver API connection test successful")
            return True
        except Exception as e:
            logger.error(f"Quiver API connection test failed: {e}")
            return False
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring."""
        return {
            'cache_size': len(self._cache),
            'cache_ttl': self._cache_ttl,
            'requests_this_minute': self.request_count,
            'rate_limit': self.rate_limit_per_minute
        }