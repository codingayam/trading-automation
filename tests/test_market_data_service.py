"""
Unit tests for Market Data Service.
Tests price data fetching, caching, validation, and return calculations.
"""
import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date, timedelta
import pytz

from src.data.market_data_service import MarketDataService, PriceData, ReturnData
from src.utils.exceptions import APIError, DataValidationError


class TestMarketDataService:
    """Test suite for MarketDataService."""
    
    @pytest.fixture
    def service(self):
        """Create MarketDataService instance for testing."""
        return MarketDataService()
    
    @pytest.fixture
    def sample_price_data(self):
        """Sample price data for testing."""
        return PriceData(
            ticker='AAPL',
            current_price=150.00,
            open_price=148.00,
            high_price=152.00,
            low_price=147.50,
            volume=1000000,
            timestamp=datetime.now(),
            market_cap=2400000000000,
            pe_ratio=25.5
        )
    
    @pytest.fixture
    def sample_historical_data(self):
        """Sample historical data for testing."""
        dates = pd.date_range('2023-12-01', periods=5, freq='D')
        return pd.DataFrame({
            'Open': [148, 149, 150, 151, 152],
            'High': [149, 151, 152, 153, 154],
            'Low': [147, 148, 149, 150, 151],
            'Close': [148.5, 150.0, 151.5, 152.0, 153.0],
            'Volume': [1000000, 1100000, 1200000, 1300000, 1400000]
        }, index=dates)
    
    def test_initialization(self, service):
        """Test service initialization."""
        assert service.cache_ttl == 900  # 15 minutes
        assert service.market_tz.zone == 'US/Eastern'
        assert service.max_price_change_percent == 50.0
        assert service.min_price == 0.01
        assert service.max_price == 100000.0
    
    def test_is_market_open_weekday_hours(self, service):
        """Test market open detection during weekday trading hours."""
        # Mock a Tuesday at 2 PM Eastern
        eastern_time = datetime(2023, 12, 5, 14, 0, 0)  # Tuesday
        mock_now = service.market_tz.localize(eastern_time)
        
        with patch('src.data.market_data_service.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_now
            result = service._is_market_open()
            
            assert result is True
    
    def test_is_market_open_weekend(self, service):
        """Test market open detection during weekend."""
        # Mock a Saturday
        eastern_time = datetime(2023, 12, 9, 14, 0, 0)  # Saturday
        mock_now = service.market_tz.localize(eastern_time)
        
        with patch('src.data.market_data_service.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_now
            result = service._is_market_open()
            
            assert result is False
    
    def test_is_market_open_after_hours(self, service):
        """Test market open detection after trading hours."""
        # Mock a weekday at 6 PM Eastern (after market close)
        eastern_time = datetime(2023, 12, 5, 18, 0, 0)  # Tuesday
        mock_now = service.market_tz.localize(eastern_time)
        
        with patch('src.data.market_data_service.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_now
            result = service._is_market_open()
            
            assert result is False
    
    def test_get_last_trading_day_monday(self, service):
        """Test getting last trading day when today is Monday."""
        monday = date(2023, 12, 4)  # Monday
        
        with patch('src.data.market_data_service.date') as mock_date:
            mock_date.today.return_value = monday
            result = service._get_last_trading_day()
            
            # Last trading day should be Friday
            expected = date(2023, 12, 1)  # Friday
            assert result == expected
    
    def test_get_last_trading_day_tuesday(self, service):
        """Test getting last trading day when today is Tuesday."""
        tuesday = date(2023, 12, 5)  # Tuesday
        
        with patch('src.data.market_data_service.date') as mock_date:
            mock_date.today.return_value = tuesday
            result = service._get_last_trading_day()
            
            # Last trading day should be Monday
            expected = date(2023, 12, 4)  # Monday
            assert result == expected
    
    def test_get_last_trading_day_sunday(self, service):
        """Test getting last trading day when today is Sunday."""
        sunday = date(2023, 12, 10)  # Sunday
        
        with patch('src.data.market_data_service.date') as mock_date:
            mock_date.today.return_value = sunday
            result = service._get_last_trading_day()
            
            # Last trading day should be Friday
            expected = date(2023, 12, 8)  # Friday
            assert result == expected
    
    def test_validate_price_data_valid(self, service):
        """Test price data validation with valid data."""
        result = service._validate_price_data('AAPL', 150.00)
        assert result is True
    
    def test_validate_price_data_below_minimum(self, service):
        """Test price data validation with price below minimum."""
        result = service._validate_price_data('AAPL', 0.005)  # Below min_price
        assert result is False
    
    def test_validate_price_data_above_maximum(self, service):
        """Test price data validation with price above maximum."""
        result = service._validate_price_data('AAPL', 150000.00)  # Above max_price
        assert result is False
    
    def test_validate_price_data_large_change(self, service):
        """Test price data validation with large price change."""
        result = service._validate_price_data('AAPL', 300.00, reference_price=100.00)  # 200% change
        assert result is False
    
    def test_validate_price_data_acceptable_change(self, service):
        """Test price data validation with acceptable price change."""
        result = service._validate_price_data('AAPL', 130.00, reference_price=100.00)  # 30% change
        assert result is True
    
    def test_cache_functionality(self, service, sample_price_data):
        """Test price data caching functionality."""
        # Cache price data
        service._cache_price_data('AAPL', sample_price_data)
        
        # Retrieve from cache
        cached_data = service._get_cached_price('AAPL')
        
        assert cached_data is not None
        assert cached_data.ticker == 'AAPL'
        assert cached_data.current_price == 150.00
    
    def test_cache_expiry(self, service, sample_price_data):
        """Test cache expiry functionality."""
        # Cache price data
        service._cache_price_data('AAPL', sample_price_data)
        
        # Mock expired timestamp
        with patch('time.time', return_value=99999):  # Far in future
            cached_data = service._get_cached_price('AAPL')
            
            assert cached_data is None  # Should be expired and removed
    
    @patch('yfinance.Ticker')
    def test_get_current_price_success(self, mock_ticker, service):
        """Test successful current price retrieval."""
        mock_stock = Mock()
        mock_stock.info = {'currentPrice': 150.00}
        mock_ticker.return_value = mock_stock
        
        price = service.get_current_price('AAPL', use_cache=False)
        
        assert price == 150.00
        mock_ticker.assert_called_once_with('AAPL')
    
    @patch('yfinance.Ticker')
    def test_get_current_price_fallback_to_history(self, mock_ticker, service, sample_historical_data):
        """Test current price retrieval with fallback to historical data."""
        mock_stock = Mock()
        mock_stock.info = {}  # No current price
        mock_stock.history.return_value = sample_historical_data.tail(1)  # Last day only
        mock_ticker.return_value = mock_stock
        
        price = service.get_current_price('AAPL', use_cache=False)
        
        assert price == 153.0  # Latest close price
    
    @patch('yfinance.Ticker')
    def test_get_current_price_no_data(self, mock_ticker, service):
        """Test current price retrieval with no data available."""
        mock_stock = Mock()
        mock_stock.info = {}
        mock_stock.history.return_value = pd.DataFrame()  # Empty dataframe
        mock_ticker.return_value = mock_stock
        
        price = service.get_current_price('AAPL', use_cache=False)
        
        assert price is None
    
    @patch('yfinance.Ticker')
    def test_get_current_price_error(self, mock_ticker, service):
        """Test current price retrieval with error."""
        mock_ticker.side_effect = Exception("API Error")
        
        price = service.get_current_price('AAPL', use_cache=False)
        
        assert price is None
    
    def test_get_current_price_from_cache(self, service, sample_price_data):
        """Test current price retrieval from cache."""
        # Cache price data
        service._cache_price_data('AAPL', sample_price_data)
        
        price = service.get_current_price('AAPL', use_cache=True)
        
        assert price == 150.00
    
    @patch('yfinance.Ticker')
    def test_get_price_data_success(self, mock_ticker, service, sample_historical_data):
        """Test successful comprehensive price data retrieval."""
        mock_stock = Mock()
        mock_stock.info = {
            'currentPrice': 150.00,
            'marketCap': 2400000000000,
            'trailingPE': 25.5
        }
        mock_stock.history.return_value = sample_historical_data.tail(1)
        mock_ticker.return_value = mock_stock
        
        price_data = service.get_price_data('AAPL', use_cache=False)
        
        assert price_data is not None
        assert price_data.ticker == 'AAPL'
        assert price_data.current_price == 150.00
        assert price_data.open_price == 152.0  # From sample data
        assert price_data.market_cap == 2400000000000
        assert price_data.pe_ratio == 25.5
    
    @patch('yfinance.Ticker')
    def test_get_price_data_no_current_price(self, mock_ticker, service):
        """Test price data retrieval with no current price."""
        mock_stock = Mock()
        mock_stock.info = {}  # No current price
        mock_ticker.return_value = mock_stock
        
        price_data = service.get_price_data('AAPL', use_cache=False)
        
        assert price_data is None
    
    @patch('yfinance.Ticker')
    def test_get_price_data_validation_failure(self, mock_ticker, service, sample_historical_data):
        """Test price data retrieval with validation failure."""
        mock_stock = Mock()
        mock_stock.info = {'currentPrice': 500000.00}  # Price above maximum
        mock_stock.history.return_value = sample_historical_data.tail(1)
        mock_ticker.return_value = mock_stock
        
        price_data = service.get_price_data('AAPL', use_cache=False)
        
        assert price_data is None
    
    def test_get_price_data_from_cache(self, service, sample_price_data):
        """Test price data retrieval from cache."""
        # Cache price data
        service._cache_price_data('AAPL', sample_price_data)
        
        price_data = service.get_price_data('AAPL', use_cache=True)
        
        assert price_data == sample_price_data
    
    @patch('yfinance.Ticker')
    def test_get_historical_prices_success(self, mock_ticker, service, sample_historical_data):
        """Test successful historical prices retrieval."""
        mock_stock = Mock()
        mock_stock.history.return_value = sample_historical_data
        mock_ticker.return_value = mock_stock
        
        start_date = date(2023, 12, 1)
        end_date = date(2023, 12, 5)
        
        hist_data = service.get_historical_prices('AAPL', start_date, end_date)
        
        assert hist_data is not None
        assert len(hist_data) == 5
        assert 'Close' in hist_data.columns
        mock_stock.history.assert_called_once_with(
            start=start_date,
            end=date(2023, 12, 6),  # end_date + 1 day
            auto_adjust=True,
            prepost=False
        )
    
    @patch('yfinance.Ticker')
    def test_get_historical_prices_no_data(self, mock_ticker, service):
        """Test historical prices retrieval with no data."""
        mock_stock = Mock()
        mock_stock.history.return_value = pd.DataFrame()  # Empty dataframe
        mock_ticker.return_value = mock_stock
        
        hist_data = service.get_historical_prices('AAPL', date(2023, 12, 1))
        
        assert hist_data is None
    
    @patch('yfinance.Ticker')
    def test_get_historical_prices_error(self, mock_ticker, service):
        """Test historical prices retrieval with error."""
        mock_ticker.side_effect = Exception("API Error")
        
        hist_data = service.get_historical_prices('AAPL', date(2023, 12, 1))
        
        assert hist_data is None
    
    def test_calculate_return_with_reference_price(self, service):
        """Test return calculation with reference price."""
        with patch.object(service, 'get_current_price', return_value=150.00):
            return_data = service.calculate_return('AAPL', reference_price=100.00)
            
            assert return_data is not None
            assert return_data.ticker == 'AAPL'
            assert return_data.current_price == 150.00
            assert return_data.reference_price == 100.00
            assert return_data.return_amount == 50.00
            assert return_data.return_percent == 50.00
    
    def test_calculate_return_with_reference_date(self, service, sample_historical_data):
        """Test return calculation with reference date."""
        reference_date = date(2023, 12, 1)
        
        with patch.object(service, 'get_current_price', return_value=150.00), \
             patch.object(service, 'get_historical_prices', return_value=sample_historical_data.head(1)):
            
            return_data = service.calculate_return('AAPL', reference_date=reference_date)
            
            assert return_data is not None
            assert return_data.current_price == 150.00
            assert return_data.reference_price == 148.5  # Close price from sample data
    
    def test_calculate_return_no_current_price(self, service):
        """Test return calculation with no current price."""
        with patch.object(service, 'get_current_price', return_value=None):
            return_data = service.calculate_return('AAPL', reference_price=100.00)
            
            assert return_data is None
    
    def test_calculate_return_no_reference_price(self, service):
        """Test return calculation with no reference price available."""
        with patch.object(service, 'get_current_price', return_value=150.00), \
             patch.object(service, 'get_historical_prices', return_value=None):
            
            return_data = service.calculate_return('AAPL')
            
            assert return_data is None
    
    def test_calculate_return_invalid_reference_price(self, service):
        """Test return calculation with invalid reference price."""
        with patch.object(service, 'get_current_price', return_value=150.00):
            return_data = service.calculate_return('AAPL', reference_price=0.00)
            
            assert return_data is None
    
    def test_calculate_since_open_return_success(self, service, sample_price_data):
        """Test successful since-open return calculation."""
        with patch.object(service, 'get_price_data', return_value=sample_price_data):
            return_data = service.calculate_since_open_return('AAPL')
            
            assert return_data is not None
            assert return_data.ticker == 'AAPL'
            assert return_data.period_type == 'since_open'
            assert return_data.current_price == 150.00
            assert return_data.reference_price == 148.00
            assert return_data.return_amount == 2.00
    
    def test_calculate_since_open_return_no_data(self, service):
        """Test since-open return calculation with no price data."""
        with patch.object(service, 'get_price_data', return_value=None):
            return_data = service.calculate_since_open_return('AAPL')
            
            assert return_data is None
    
    def test_calculate_daily_return_success(self, service):
        """Test successful daily return calculation."""
        with patch.object(service, 'calculate_return') as mock_calculate:
            mock_calculate.return_value = Mock(period_type='1d')
            
            return_data = service.calculate_daily_return('AAPL')
            
            assert return_data.period_type == '1d'
            mock_calculate.assert_called_once()
    
    @patch('yfinance.download')
    def test_get_batch_prices_success(self, mock_download, service):
        """Test successful batch price retrieval."""
        # Mock batch download data
        mock_data = pd.DataFrame({
            ('AAPL', 'Close'): [150.0, 151.0],
            ('GOOGL', 'Close'): [2800.0, 2850.0]
        })
        mock_data.columns = pd.MultiIndex.from_tuples([('AAPL', 'Close'), ('GOOGL', 'Close')])
        mock_download.return_value = mock_data
        
        tickers = ['AAPL', 'GOOGL']
        prices = service.get_batch_prices(tickers, use_cache=False)
        
        assert len(prices) == 2
        assert prices['AAPL'] == 151.0  # Last close price
        assert prices['GOOGL'] == 2850.0
    
    @patch('yfinance.download')
    def test_get_batch_prices_fallback_to_individual(self, mock_download, service):
        """Test batch price retrieval with fallback to individual requests."""
        mock_download.side_effect = Exception("Batch download failed")
        
        with patch.object(service, 'get_current_price', side_effect=[150.0, 2800.0]):
            tickers = ['AAPL', 'GOOGL']
            prices = service.get_batch_prices(tickers, use_cache=False)
            
            assert len(prices) == 2
            assert prices['AAPL'] == 150.0
            assert prices['GOOGL'] == 2800.0
    
    def test_get_batch_prices_with_cache(self, service, sample_price_data):
        """Test batch price retrieval using cache."""
        # Cache one ticker
        service._cache_price_data('AAPL', sample_price_data)
        
        with patch.object(service, 'get_current_price', return_value=2800.0) as mock_get_price:
            tickers = ['AAPL', 'GOOGL']
            prices = service.get_batch_prices(tickers, use_cache=True)
            
            assert prices['AAPL'] == 150.0  # From cache
            # Only GOOGL should be fetched individually
            mock_get_price.assert_called_once_with('GOOGL', use_cache=False)
    
    @patch('yfinance.Ticker')
    def test_validate_ticker_success(self, mock_ticker, service):
        """Test successful ticker validation."""
        mock_stock = Mock()
        mock_stock.info = {'regularMarketPrice': 150.00}
        mock_ticker.return_value = mock_stock
        
        result = service.validate_ticker('AAPL')
        
        assert result is True
    
    @patch('yfinance.Ticker')
    def test_validate_ticker_fallback_to_history(self, mock_ticker, service, sample_historical_data):
        """Test ticker validation with fallback to historical data."""
        mock_stock = Mock()
        mock_stock.info = {}  # No market price
        mock_stock.history.return_value = sample_historical_data.head(1)  # Has data
        mock_ticker.return_value = mock_stock
        
        result = service.validate_ticker('AAPL')
        
        assert result is True
    
    @patch('yfinance.Ticker')
    def test_validate_ticker_no_data(self, mock_ticker, service):
        """Test ticker validation with no data."""
        mock_stock = Mock()
        mock_stock.info = {}
        mock_stock.history.return_value = pd.DataFrame()  # Empty
        mock_ticker.return_value = mock_stock
        
        result = service.validate_ticker('INVALID')
        
        assert result is False
    
    @patch('yfinance.Ticker')
    def test_validate_ticker_error(self, mock_ticker, service):
        """Test ticker validation with error."""
        mock_ticker.side_effect = Exception("Invalid ticker")
        
        result = service.validate_ticker('INVALID')
        
        assert result is False
    
    def test_is_market_holiday_weekend(self, service):
        """Test market holiday detection for weekends."""
        saturday = date(2023, 12, 9)  # Saturday
        sunday = date(2023, 12, 10)  # Sunday
        
        assert service.is_market_holiday(saturday) is True
        assert service.is_market_holiday(sunday) is True
    
    def test_is_market_holiday_new_year(self, service):
        """Test market holiday detection for New Year's Day."""
        new_year = date(2023, 1, 1)
        
        assert service.is_market_holiday(new_year) is True
    
    def test_is_market_holiday_regular_day(self, service):
        """Test market holiday detection for regular trading day."""
        regular_day = date(2023, 12, 5)  # Tuesday
        
        assert service.is_market_holiday(regular_day) is False
    
    def test_get_market_status_open(self, service):
        """Test market status when market is open."""
        with patch.object(service, '_is_market_open', return_value=True):
            status = service.get_market_status()
            
            assert status['is_open'] is True
            assert status['next_event'] == 'close'
            assert 'current_time' in status
            assert 'market_timezone' in status
    
    def test_get_market_status_closed(self, service):
        """Test market status when market is closed."""
        with patch.object(service, '_is_market_open', return_value=False):
            status = service.get_market_status()
            
            assert status['is_open'] is False
            assert status['next_event'] == 'open'
    
    def test_get_cache_stats(self, service, sample_price_data):
        """Test cache statistics retrieval."""
        # Add some data to cache
        service._cache_price_data('AAPL', sample_price_data)
        service._cache_price_data('GOOGL', sample_price_data)
        
        stats = service.get_cache_stats()
        
        assert stats['price_cache_size'] == 2
        assert stats['info_cache_size'] >= 0
        assert stats['cache_ttl_seconds'] == 900
    
    def test_clear_cache(self, service, sample_price_data):
        """Test cache clearing functionality."""
        # Add data to cache
        service._cache_price_data('AAPL', sample_price_data)
        
        # Verify data is cached
        assert len(service.price_cache) == 1
        
        # Clear cache
        service.clear_cache()
        
        # Verify cache is empty
        assert len(service.price_cache) == 0
        assert len(service.info_cache) == 0
    
    def test_price_data_dataclass(self):
        """Test PriceData dataclass functionality."""
        price_data = PriceData(
            ticker='AAPL',
            current_price=150.00,
            open_price=148.00,
            high_price=152.00,
            low_price=147.50,
            volume=1000000,
            timestamp=datetime.now(),
            market_cap=2400000000000,
            pe_ratio=25.5
        )
        
        assert price_data.ticker == 'AAPL'
        assert price_data.current_price == 150.00
        assert price_data.open_price == 148.00
        assert price_data.volume == 1000000
        assert price_data.market_cap == 2400000000000
    
    def test_return_data_dataclass(self):
        """Test ReturnData dataclass functionality."""
        return_data = ReturnData(
            ticker='AAPL',
            current_price=150.00,
            reference_price=100.00,
            return_amount=50.00,
            return_percent=50.00,
            period_type='1d',
            calculation_time=datetime.now()
        )
        
        assert return_data.ticker == 'AAPL'
        assert return_data.current_price == 150.00
        assert return_data.reference_price == 100.00
        assert return_data.return_amount == 50.00
        assert return_data.return_percent == 50.00
        assert return_data.period_type == '1d'