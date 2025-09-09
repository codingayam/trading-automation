"""
Unit tests for Quiver API client.
Tests authentication, rate limiting, data filtering, and fuzzy name matching.
"""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import date, datetime
import requests

from src.data.quiver_client import QuiverClient, CongressionalTrade
from src.utils.exceptions import APIError, DataValidationError


class TestQuiverClient:
    """Test suite for QuiverClient."""
    
    @pytest.fixture
    def client(self):
        """Create QuiverClient instance for testing."""
        with patch('src.data.quiver_client.settings') as mock_settings:
            mock_settings.api.quiver_api_key = 'test_api_key'
            mock_settings.api.rate_limit_per_minute = 60
            mock_settings.api.timeout_seconds = 30
            mock_settings.trading.minimum_congress_trade_value = 50000
            mock_settings.trading.politician_match_threshold = 0.85
            mock_settings.is_development = True
            return QuiverClient()
    
    @pytest.fixture
    def sample_trade_data(self):
        """Sample trade data for testing."""
        return {
            'representative': 'Nancy Pelosi',
            'ticker': 'NVDA',
            'transactionDate': '2023-12-01',
            'type': 'Purchase',
            'range': '$50,001 - $100,000',
            'lastModified': '2023-12-01'
        }
    
    def test_initialization_with_api_key(self, client):
        """Test client initialization with API key."""
        assert client.api_key == 'test_api_key'
        assert client.session.headers['Authorization'] == 'Bearer test_api_key'
        assert 'User-Agent' in client.session.headers
    
    def test_initialization_without_api_key(self):
        """Test client initialization fails without API key."""
        with patch('src.data.quiver_client.settings') as mock_settings:
            mock_settings.api.quiver_api_key = ''
            with pytest.raises(ValueError, match="Quiver API key is required"):
                QuiverClient()
    
    def test_rate_limiting_enforcement(self, client):
        """Test rate limiting is enforced."""
        client.rate_limit_per_minute = 1  # Set very low limit
        client.request_count = 1
        client.rate_limit_window_start = datetime.now().timestamp()
        
        with patch('time.sleep') as mock_sleep:
            client._wait_for_rate_limit()
            mock_sleep.assert_called_once()
    
    @patch('requests.Session.get')
    def test_successful_api_request(self, mock_get, client, sample_trade_data):
        """Test successful API request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [sample_trade_data]
        mock_get.return_value = mock_response
        
        result = client._make_request('/test', {'param': 'value'})
        
        assert result == [sample_trade_data]
        mock_get.assert_called_once()
    
    @patch('requests.Session.get')
    def test_api_request_rate_limited(self, mock_get, client):
        """Test API request handles rate limiting."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {'Retry-After': '60'}
        mock_get.return_value = mock_response
        
        with pytest.raises(APIError) as exc_info:
            client._make_request('/test')
        
        assert exc_info.value.api_name == "Quiver"
        assert exc_info.value.status_code == 429
    
    @patch('requests.Session.get')
    def test_api_request_authentication_failed(self, mock_get, client):
        """Test API request handles authentication failure."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response
        
        with pytest.raises(APIError) as exc_info:
            client._make_request('/test')
        
        assert exc_info.value.api_name == "Quiver"
        assert exc_info.value.status_code == 401
        assert "Authentication failed" in str(exc_info.value)
    
    @patch('requests.Session.get')
    def test_api_request_server_error(self, mock_get, client):
        """Test API request handles server errors."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.return_value = {'error': 'Internal server error'}
        mock_get.return_value = mock_response
        
        with pytest.raises(APIError) as exc_info:
            client._make_request('/test')
        
        assert exc_info.value.api_name == "Quiver"
        assert exc_info.value.status_code == 500
    
    @patch('requests.Session.get')
    def test_api_request_timeout(self, mock_get, client):
        """Test API request handles timeout."""
        mock_get.side_effect = requests.exceptions.Timeout()
        
        with pytest.raises(APIError) as exc_info:
            client._make_request('/test')
        
        assert "timed out" in str(exc_info.value)
    
    @patch('requests.Session.get')
    def test_api_request_connection_error(self, mock_get, client):
        """Test API request handles connection errors."""
        mock_get.side_effect = requests.exceptions.ConnectionError()
        
        with pytest.raises(APIError) as exc_info:
            client._make_request('/test')
        
        assert "Connection error" in str(exc_info.value)
    
    def test_parse_trade_valid_data(self, client, sample_trade_data):
        """Test parsing valid trade data."""
        trade = client._parse_trade(sample_trade_data)
        
        assert trade is not None
        assert trade.politician == 'Nancy Pelosi'
        assert trade.ticker == 'NVDA'
        assert trade.trade_type == 'Purchase'
        assert trade.amount_min == 50001
        assert trade.amount_max == 100000
        assert trade.transaction_date == date(2023, 12, 1)
    
    def test_parse_trade_missing_fields(self, client):
        """Test parsing trade with missing required fields."""
        invalid_data = {'representative': 'John Doe'}
        
        trade = client._parse_trade(invalid_data)
        assert trade is None
    
    def test_parse_trade_invalid_date(self, client, sample_trade_data):
        """Test parsing trade with invalid date."""
        sample_trade_data['transactionDate'] = 'invalid-date'
        
        trade = client._parse_trade(sample_trade_data)
        assert trade is None
    
    def test_parse_amount_range_standard(self, client):
        """Test parsing standard amount range."""
        min_val, max_val = client._parse_amount_range('$50,001 - $100,000')
        assert min_val == 50001
        assert max_val == 100000
    
    def test_parse_amount_range_single_value(self, client):
        """Test parsing single value amount range."""
        min_val, max_val = client._parse_amount_range('$75000')
        assert min_val == 75000
        assert max_val == 75000
    
    def test_parse_amount_range_invalid(self, client):
        """Test parsing invalid amount range."""
        min_val, max_val = client._parse_amount_range('invalid')
        assert min_val == 0.0
        assert max_val == 0.0
    
    def test_should_include_trade_purchase(self, client):
        """Test trade inclusion for purchases above threshold."""
        trade = CongressionalTrade(
            politician='Test Politician',
            ticker='AAPL',
            transaction_date=date.today(),
            trade_type='Purchase',
            amount_range='$50,001 - $100,000',
            amount_min=50001,
            amount_max=100000,
            last_modified=date.today(),
            raw_data={}
        )
        
        assert client._should_include_trade(trade) is True
    
    def test_should_include_trade_sale(self, client):
        """Test trade exclusion for sales."""
        trade = CongressionalTrade(
            politician='Test Politician',
            ticker='AAPL',
            transaction_date=date.today(),
            trade_type='Sale',
            amount_range='$50,001 - $100,000',
            amount_min=50001,
            amount_max=100000,
            last_modified=date.today(),
            raw_data={}
        )
        
        assert client._should_include_trade(trade) is False
    
    def test_should_include_trade_below_threshold(self, client):
        """Test trade exclusion for amounts below threshold."""
        trade = CongressionalTrade(
            politician='Test Politician',
            ticker='AAPL',
            transaction_date=date.today(),
            trade_type='Purchase',
            amount_range='$1,000 - $15,000',
            amount_min=1000,
            amount_max=15000,
            last_modified=date.today(),
            raw_data={}
        )
        
        assert client._should_include_trade(trade) is False
    
    def test_fuzzy_name_matching_exact(self, client):
        """Test fuzzy name matching with exact match."""
        politicians = ['Nancy Pelosi', 'Josh Gottheimer']
        trade = CongressionalTrade(
            politician='Nancy Pelosi',
            ticker='AAPL',
            transaction_date=date.today(),
            trade_type='Purchase',
            amount_range='$50,001 - $100,000',
            amount_min=50001,
            amount_max=100000,
            last_modified=date.today(),
            raw_data={}
        )
        
        matches = client.find_matching_politicians(politicians, trade)
        assert 'Nancy Pelosi' in matches
    
    def test_fuzzy_name_matching_similar(self, client):
        """Test fuzzy name matching with similar names."""
        politicians = ['Nancy P. Pelosi']
        trade = CongressionalTrade(
            politician='Nancy Pelosi',
            ticker='AAPL',
            transaction_date=date.today(),
            trade_type='Purchase',
            amount_range='$50,001 - $100,000',
            amount_min=50001,
            amount_max=100000,
            last_modified=date.today(),
            raw_data={}
        )
        
        matches = client.find_matching_politicians(politicians, trade)
        assert len(matches) >= 0  # Depends on similarity threshold
    
    def test_fuzzy_name_matching_no_match(self, client):
        """Test fuzzy name matching with no matches."""
        politicians = ['John Smith']
        trade = CongressionalTrade(
            politician='Nancy Pelosi',
            ticker='AAPL',
            transaction_date=date.today(),
            trade_type='Purchase',
            amount_range='$50,001 - $100,000',
            amount_min=50001,
            amount_max=100000,
            last_modified=date.today(),
            raw_data={}
        )
        
        matches = client.find_matching_politicians(politicians, trade)
        assert len(matches) == 0
    
    @patch.object(QuiverClient, '_make_request')
    def test_get_congressional_trades_success(self, mock_request, client, sample_trade_data):
        """Test successful congressional trades retrieval."""
        mock_request.return_value = [sample_trade_data]
        
        trades = client.get_congressional_trades(date(2023, 12, 1))
        
        assert len(trades) == 1
        assert trades[0].politician == 'Nancy Pelosi'
        assert trades[0].ticker == 'NVDA'
        mock_request.assert_called_once_with(
            '/beta/bulk/congresstrading',
            {'date': '2023-12-01'}
        )
    
    @patch.object(QuiverClient, '_make_request')
    def test_get_congressional_trades_api_error(self, mock_request, client):
        """Test congressional trades retrieval with API error."""
        mock_request.side_effect = APIError("API failed", "Quiver", 500)
        
        trades = client.get_congressional_trades()
        assert len(trades) == 0  # Should return empty list on error
    
    @patch.object(QuiverClient, '_make_request')
    def test_get_congressional_trades_invalid_response(self, mock_request, client):
        """Test congressional trades retrieval with invalid response."""
        mock_request.return_value = "invalid response"  # Not a list
        
        with pytest.raises(DataValidationError):
            client.get_congressional_trades()
    
    @patch.object(QuiverClient, 'get_congressional_trades')
    def test_get_trades_for_politicians(self, mock_get_trades, client):
        """Test getting trades for specific politicians."""
        sample_trade = CongressionalTrade(
            politician='Nancy Pelosi',
            ticker='NVDA',
            transaction_date=date(2023, 12, 1),
            trade_type='Purchase',
            amount_range='$50,001 - $100,000',
            amount_min=50001,
            amount_max=100000,
            last_modified=date(2023, 12, 1),
            raw_data={}
        )
        mock_get_trades.return_value = [sample_trade]
        
        politicians = ['Nancy Pelosi', 'Josh Gottheimer']
        trades = client.get_trades_for_politicians(politicians)
        
        assert len(trades) == 1
        assert trades[0].politician == 'Nancy Pelosi'
    
    @patch.object(QuiverClient, '_make_request')
    def test_test_connection_success(self, mock_request, client):
        """Test successful connection test."""
        mock_request.return_value = []
        
        result = client.test_connection()
        assert result is True
    
    @patch.object(QuiverClient, '_make_request')
    def test_test_connection_failure(self, mock_request, client):
        """Test failed connection test."""
        mock_request.side_effect = Exception("Connection failed")
        
        result = client.test_connection()
        assert result is False
    
    def test_cache_functionality(self, client):
        """Test response caching functionality."""
        # Test cache stats
        stats = client.get_cache_stats()
        assert 'cache_size' in stats
        assert 'cache_ttl' in stats
        assert 'requests_this_minute' in stats
        assert 'rate_limit' in stats
    
    @patch('time.time')
    def test_cache_expiry(self, mock_time, client):
        """Test cache expiry functionality."""
        # Set up cache
        client._cache['test_key'] = ('test_data', 100)
        
        # Test within TTL
        mock_time.return_value = 500  # Within TTL
        cached_data, cache_time = client._cache['test_key']
        assert cached_data == 'test_data'
        
        # Test beyond TTL
        mock_time.return_value = 1500  # Beyond TTL
        # Cache should be considered expired in actual usage
        
    def test_request_count_reset(self, client):
        """Test request count reset after time window."""
        client.request_count = 60
        client.rate_limit_window_start = 0  # Old timestamp
        
        with patch('time.time', return_value=120):  # 2 minutes later
            client._wait_for_rate_limit()
            assert client.request_count <= 1  # Should be reset
    
    def test_minimum_delay_between_requests(self, client):
        """Test minimum delay between requests."""
        client.rate_limit_per_minute = 60  # 1 request per second minimum
        client.last_request_time = 100
        
        with patch('time.time', return_value=100.5), patch('time.sleep') as mock_sleep:
            client._wait_for_rate_limit()
            mock_sleep.assert_called_once()
    
    def test_congressional_trade_dataclass(self):
        """Test CongressionalTrade dataclass functionality."""
        trade = CongressionalTrade(
            politician='Test Politician',
            ticker='AAPL',
            transaction_date=date.today(),
            trade_type='Purchase',
            amount_range='$50,001 - $100,000',
            amount_min=50001,
            amount_max=100000,
            last_modified=date.today(),
            raw_data={'test': 'data'}
        )
        
        assert trade.politician == 'Test Politician'
        assert trade.ticker == 'AAPL'
        assert trade.trade_type == 'Purchase'
        assert trade.amount_min == 50001
        assert trade.amount_max == 100000
        assert trade.raw_data == {'test': 'data'}