"""
Unit tests for Alpaca API client.
Tests trading operations, position management, and market data functionality.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date
from decimal import Decimal

from alpaca.trading.models import Position, Order, AccountConfiguration
from alpaca.trading.enums import OrderSide, TimeInForce, OrderStatus, OrderType
from alpaca.common.exceptions import APIError as AlpacaAPIError

from src.data.alpaca_client import AlpacaClient, TradeOrder, PositionInfo, OrderInfo
from src.utils.exceptions import APIError, TradingError, ValidationError


class TestAlpacaClient:
    """Test suite for AlpacaClient."""
    
    @pytest.fixture
    def client(self):
        """Create AlpacaClient instance for testing."""
        with patch('src.data.alpaca_client.settings') as mock_settings:
            mock_settings.api.alpaca_api_key = 'test_api_key'
            mock_settings.api.alpaca_secret_key = 'test_secret_key'
            mock_settings.api.alpaca_paper_trading = True
            mock_settings.api.retry_max_attempts = 3
            mock_settings.api.timeout_seconds = 30
            mock_settings.trading.minimum_amount = 100.0
            
            with patch('alpaca.trading.TradingClient'), \
                 patch('alpaca.data.StockHistoricalDataClient'):
                return AlpacaClient()
    
    @pytest.fixture
    def sample_account(self):
        """Sample account data for testing."""
        account = Mock(spec=Account)
        account.buying_power = 10000.00
        account.portfolio_value = 15000.00
        account.cash = 5000.00
        account.daytrade_count = 0
        account.account_number = 'TEST123456'
        return account
    
    @pytest.fixture
    def sample_position(self):
        """Sample position data for testing."""
        position = Mock(spec=Position)
        position.symbol = 'AAPL'
        position.qty = 100
        position.market_value = 15000.00
        position.cost_basis = 14000.00
        position.unrealized_pl = 1000.00
        position.unrealized_plpc = 0.0714  # 7.14%
        position.current_price = 150.00
        return position
    
    @pytest.fixture
    def sample_order(self):
        """Sample order data for testing."""
        order = Mock(spec=Order)
        order.id = 'order123'
        order.symbol = 'AAPL'
        order.qty = 10
        order.filled_qty = 10
        order.side = OrderSide.BUY
        order.order_type = OrderType.MARKET
        order.status = OrderStatus.FILLED
        order.submitted_at = datetime.now()
        order.filled_at = datetime.now()
        order.filled_avg_price = 150.00
        order.time_in_force = TimeInForce.GTC
        return order
    
    def test_initialization_with_credentials(self, client):
        """Test client initialization with credentials."""
        assert client.api_key == 'test_api_key'
        assert client.secret_key == 'test_secret_key'
        assert client.paper is True
        assert client.max_retries == 3
    
    def test_initialization_without_credentials(self):
        """Test client initialization fails without credentials."""
        with patch('src.data.alpaca_client.settings') as mock_settings:
            mock_settings.api.alpaca_api_key = ''
            mock_settings.api.alpaca_secret_key = ''
            mock_settings.api.alpaca_paper_trading = True
            
            with pytest.raises(ValueError, match="Alpaca API key and secret key are required"):
                AlpacaClient()
    
    def test_make_trading_request_success(self, client):
        """Test successful trading request."""
        mock_method = Mock(return_value='success')
        client.trading_client.test_method = mock_method
        
        result = client._make_trading_request('test_method', 'arg1', key='value')
        
        assert result == 'success'
        mock_method.assert_called_once_with('arg1', key='value')
    
    def test_make_trading_request_alpaca_error(self, client):
        """Test trading request with Alpaca API error."""
        mock_method = Mock(side_effect=AlpacaAPIError("API Error"))
        client.trading_client.test_method = mock_method
        
        with pytest.raises(APIError) as exc_info:
            client._make_trading_request('test_method')
        
        assert exc_info.value.api_name == "Alpaca"
    
    def test_make_trading_request_unexpected_error(self, client):
        """Test trading request with unexpected error."""
        mock_method = Mock(side_effect=Exception("Unexpected error"))
        client.trading_client.test_method = mock_method
        
        with pytest.raises(APIError) as exc_info:
            client._make_trading_request('test_method')
        
        assert "Unexpected error" in str(exc_info.value)
    
    def test_get_account_info_success(self, client, sample_account):
        """Test successful account info retrieval."""
        client.trading_client.get_account = Mock(return_value=sample_account)
        
        account = client.get_account_info(use_cache=False)
        
        assert account.buying_power == 10000.00
        assert account.portfolio_value == 15000.00
        client.trading_client.get_account.assert_called_once()
    
    def test_get_account_info_cached(self, client, sample_account):
        """Test cached account info retrieval."""
        client._account_info = sample_account
        client._account_info_cache_time = 999999999  # Far future
        
        account = client.get_account_info(use_cache=True)
        
        assert account == sample_account
    
    @patch('alpaca.data.StockHistoricalDataClient.get_stock_latest_quote')
    def test_validate_ticker_success(self, mock_get_quote, client):
        """Test successful ticker validation."""
        mock_response = {'AAPL': Mock(bid_price=149.50, ask_price=150.50)}
        mock_get_quote.return_value = mock_response
        
        result = client.validate_ticker('AAPL')
        
        assert result is True
    
    @patch('alpaca.data.StockHistoricalDataClient.get_stock_latest_quote')
    def test_validate_ticker_not_found(self, mock_get_quote, client):
        """Test ticker validation for non-existent ticker."""
        mock_get_quote.return_value = {}
        
        result = client.validate_ticker('INVALID')
        
        assert result is False
    
    @patch('alpaca.data.StockHistoricalDataClient.get_stock_latest_quote')
    def test_validate_ticker_error(self, mock_get_quote, client):
        """Test ticker validation with API error."""
        mock_get_quote.side_effect = Exception("API Error")
        
        result = client.validate_ticker('AAPL')
        
        assert result is False
    
    @patch('alpaca.data.StockHistoricalDataClient.get_stock_latest_quote')
    def test_get_current_price_success(self, mock_get_quote, client):
        """Test successful current price retrieval."""
        mock_quote = Mock(bid_price=149.50, ask_price=150.50)
        mock_response = {'AAPL': mock_quote}
        mock_get_quote.return_value = mock_response
        
        price = client.get_current_price('AAPL')
        
        assert price == 150.00  # Average of bid and ask
    
    @patch('alpaca.data.StockHistoricalDataClient.get_stock_latest_quote')
    def test_get_current_price_not_found(self, mock_get_quote, client):
        """Test current price retrieval for non-existent ticker."""
        mock_get_quote.return_value = {}
        
        price = client.get_current_price('INVALID')
        
        assert price is None
    
    def test_calculate_order_quantity_success(self, client):
        """Test successful order quantity calculation."""
        with patch.object(client, 'get_current_price', return_value=150.00):
            quantity = client.calculate_order_quantity('AAPL', 1500)
            
            assert quantity == 10  # 1500 / 150 = 10 shares
    
    def test_calculate_order_quantity_no_price(self, client):
        """Test order quantity calculation with no price available."""
        with patch.object(client, 'get_current_price', return_value=None):
            quantity = client.calculate_order_quantity('AAPL', 1500)
            
            assert quantity is None
    
    def test_calculate_order_quantity_zero_quantity(self, client):
        """Test order quantity calculation resulting in zero."""
        with patch.object(client, 'get_current_price', return_value=1000.00):
            quantity = client.calculate_order_quantity('AAPL', 50)  # Less than 1 share
            
            assert quantity is None
    
    def test_place_market_order_validation_errors(self, client):
        """Test market order placement validation errors."""
        # Test missing ticker
        with pytest.raises(ValidationError, match="Ticker symbol is required"):
            client.place_market_order('', 'buy', quantity=10)
        
        # Test invalid side
        with pytest.raises(ValidationError, match="Side must be 'buy' or 'sell'"):
            client.place_market_order('AAPL', 'hold', quantity=10)
        
        # Test missing quantity and notional
        with pytest.raises(ValidationError, match="Either quantity or notional amount is required"):
            client.place_market_order('AAPL', 'buy')
        
        # Test invalid quantity
        with pytest.raises(ValidationError, match="Quantity must be positive"):
            client.place_market_order('AAPL', 'buy', quantity=-10)
        
        # Test invalid notional
        with pytest.raises(ValidationError, match="Notional amount must be positive"):
            client.place_market_order('AAPL', 'buy', notional=-100)
    
    def test_place_market_order_invalid_ticker(self, client, sample_account):
        """Test market order placement with invalid ticker."""
        client.trading_client.get_account = Mock(return_value=sample_account)
        
        with patch.object(client, 'validate_ticker', return_value=False):
            with pytest.raises(ValidationError, match="Invalid or non-tradeable ticker"):
                client.place_market_order('INVALID', 'buy', quantity=10)
    
    def test_place_market_order_insufficient_buying_power(self, client, sample_account):
        """Test market order placement with insufficient buying power."""
        sample_account.buying_power = 100.00  # Low buying power
        client.trading_client.get_account = Mock(return_value=sample_account)
        
        with patch.object(client, 'validate_ticker', return_value=True), \
             patch.object(client, 'get_current_price', return_value=150.00):
            
            with pytest.raises(TradingError, match="Insufficient buying power"):
                client.place_market_order('AAPL', 'buy', quantity=100)  # $15,000 order
    
    def test_place_market_order_success_with_quantity(self, client, sample_account, sample_order):
        """Test successful market order placement with quantity."""
        client.trading_client.get_account = Mock(return_value=sample_account)
        client.trading_client.submit_order = Mock(return_value=sample_order)
        
        with patch.object(client, 'validate_ticker', return_value=True):
            order_info = client.place_market_order('AAPL', 'buy', quantity=10)
            
            assert order_info is not None
            assert order_info.ticker == 'AAPL'
            assert order_info.side == 'buy'
            assert order_info.quantity == 10
            assert order_info.status == 'filled'
    
    def test_place_market_order_success_with_notional(self, client, sample_account, sample_order):
        """Test successful market order placement with notional amount."""
        client.trading_client.get_account = Mock(return_value=sample_account)
        client.trading_client.submit_order = Mock(return_value=sample_order)
        
        with patch.object(client, 'validate_ticker', return_value=True):
            order_info = client.place_market_order('AAPL', 'buy', notional=1500)
            
            assert order_info is not None
            assert order_info.ticker == 'AAPL'
            assert order_info.side == 'buy'
    
    def test_place_market_order_retry_logic(self, client, sample_account):
        """Test market order placement retry logic."""
        client.trading_client.get_account = Mock(return_value=sample_account)
        client.trading_client.submit_order = Mock(side_effect=[
            APIError("Temporary error", "Alpaca", 500),
            APIError("Temporary error", "Alpaca", 500),
            sample_order  # Success on third attempt
        ])
        client.max_retries = 3
        
        with patch.object(client, 'validate_ticker', return_value=True), \
             patch('time.sleep'):
            order_info = client.place_market_order('AAPL', 'buy', quantity=10)
            
            assert order_info is not None
            assert client.trading_client.submit_order.call_count == 3
    
    def test_place_market_order_retry_exhausted(self, client, sample_account):
        """Test market order placement with retry attempts exhausted."""
        client.trading_client.get_account = Mock(return_value=sample_account)
        client.trading_client.submit_order = Mock(side_effect=APIError("Persistent error", "Alpaca", 500))
        client.max_retries = 2
        
        with patch.object(client, 'validate_ticker', return_value=True), \
             patch('time.sleep'):
            with pytest.raises(TradingError, match="Failed to place order after 2 attempts"):
                client.place_market_order('AAPL', 'buy', quantity=10)
    
    def test_get_order_status_success(self, client, sample_order):
        """Test successful order status retrieval."""
        client.trading_client.get_order_by_id = Mock(return_value=sample_order)
        
        order_info = client.get_order_status('order123')
        
        assert order_info is not None
        assert order_info.order_id == 'order123'
        assert order_info.ticker == 'AAPL'
        assert order_info.status == 'filled'
    
    def test_get_order_status_not_found(self, client):
        """Test order status retrieval for non-existent order."""
        client.trading_client.get_order_by_id = Mock(side_effect=Exception("Order not found"))
        
        order_info = client.get_order_status('invalid_order')
        
        assert order_info is None
    
    def test_get_all_positions_success(self, client, sample_position):
        """Test successful positions retrieval."""
        client.trading_client.get_all_positions = Mock(return_value=[sample_position])
        
        positions = client.get_all_positions()
        
        assert len(positions) == 1
        assert positions[0].ticker == 'AAPL'
        assert positions[0].quantity == 100
        assert positions[0].market_value == 15000.00
    
    def test_get_all_positions_empty(self, client):
        """Test positions retrieval with no positions."""
        client.trading_client.get_all_positions = Mock(return_value=[])
        
        positions = client.get_all_positions()
        
        assert len(positions) == 0
    
    def test_get_all_positions_error(self, client):
        """Test positions retrieval with error."""
        client.trading_client.get_all_positions = Mock(side_effect=Exception("API Error"))
        
        positions = client.get_all_positions()
        
        assert len(positions) == 0
    
    def test_get_position_success(self, client, sample_position):
        """Test successful individual position retrieval."""
        client.trading_client.get_open_position = Mock(return_value=sample_position)
        
        position = client.get_position('AAPL')
        
        assert position is not None
        assert position.ticker == 'AAPL'
        assert position.quantity == 100
    
    def test_get_position_not_found(self, client):
        """Test position retrieval for non-existent position."""
        client.trading_client.get_open_position = Mock(side_effect=Exception("Position not found"))
        
        position = client.get_position('INVALID')
        
        assert position is None
    
    def test_place_batch_orders_success(self, client, sample_account, sample_order):
        """Test successful batch order placement."""
        client.trading_client.get_account = Mock(return_value=sample_account)
        client.trading_client.submit_order = Mock(return_value=sample_order)
        
        orders = [
            TradeOrder('AAPL', 'buy', 10, 'market', 'gtc'),
            TradeOrder('GOOGL', 'buy', 5, 'market', 'gtc')
        ]
        
        with patch.object(client, 'validate_ticker', return_value=True), \
             patch('time.sleep'):
            results = client.place_batch_orders(orders)
            
            assert len(results) == 2
            assert all(result is not None for result in results)
    
    def test_place_batch_orders_with_failures(self, client, sample_account):
        """Test batch order placement with some failures."""
        client.trading_client.get_account = Mock(return_value=sample_account)
        
        orders = [
            TradeOrder('AAPL', 'buy', 10, 'market', 'gtc'),
            TradeOrder('INVALID', 'buy', 5, 'market', 'gtc')
        ]
        
        def validate_ticker_side_effect(ticker):
            return ticker != 'INVALID'
        
        with patch.object(client, 'validate_ticker', side_effect=validate_ticker_side_effect), \
             patch('time.sleep'):
            results = client.place_batch_orders(orders)
            
            assert len(results) == 2
            assert results[1] is None  # Invalid ticker should fail
    
    def test_close_position_success(self, client, sample_position, sample_order):
        """Test successful position closure."""
        client.trading_client.get_open_position = Mock(return_value=sample_position)
        client.trading_client.get_account = Mock(return_value=Mock(buying_power=10000))
        client.trading_client.submit_order = Mock(return_value=sample_order)
        
        with patch.object(client, 'validate_ticker', return_value=True):
            order_info = client.close_position('AAPL', percentage=50.0)
            
            assert order_info is not None
            # Should sell 50% of 100 shares = 50 shares
    
    def test_close_position_no_position(self, client):
        """Test position closure with no existing position."""
        client.trading_client.get_open_position = Mock(side_effect=Exception("No position"))
        
        order_info = client.close_position('AAPL')
        
        assert order_info is None
    
    def test_close_position_zero_quantity(self, client):
        """Test position closure with zero quantity."""
        zero_position = Mock(spec=Position)
        zero_position.symbol = 'AAPL'
        zero_position.qty = 0
        zero_position.market_value = 0.00
        zero_position.cost_basis = 0.00
        zero_position.unrealized_pl = 0.00
        zero_position.unrealized_plpc = 0.00
        zero_position.current_price = 150.00
        
        client.trading_client.get_open_position = Mock(return_value=zero_position)
        
        order_info = client.close_position('AAPL')
        
        assert order_info is None
    
    def test_test_connection_success(self, client, sample_account):
        """Test successful connection test."""
        client.trading_client.get_account = Mock(return_value=sample_account)
        
        result = client.test_connection()
        
        assert result is True
    
    def test_test_connection_failure(self, client):
        """Test failed connection test."""
        client.trading_client.get_account = Mock(side_effect=Exception("Connection failed"))
        
        result = client.test_connection()
        
        assert result is False
    
    def test_get_portfolio_summary_success(self, client, sample_account, sample_position):
        """Test successful portfolio summary retrieval."""
        client.trading_client.get_account = Mock(return_value=sample_account)
        client.trading_client.get_all_positions = Mock(return_value=[sample_position])
        
        summary = client.get_portfolio_summary()
        
        assert summary['account_value'] == 15000.00
        assert summary['buying_power'] == 10000.00
        assert summary['total_positions'] == 1
        assert summary['total_market_value'] == 15000.00
        assert summary['is_paper_account'] is True
    
    def test_get_portfolio_summary_error(self, client):
        """Test portfolio summary retrieval with error."""
        client.trading_client.get_account = Mock(side_effect=Exception("API Error"))
        
        summary = client.get_portfolio_summary()
        
        assert summary == {}
    
    def test_cancel_order_success(self, client):
        """Test successful order cancellation."""
        client.trading_client.cancel_order_by_id = Mock()
        
        result = client.cancel_order('order123')
        
        assert result is True
        client.trading_client.cancel_order_by_id.assert_called_once_with('order123')
    
    def test_cancel_order_failure(self, client):
        """Test failed order cancellation."""
        client.trading_client.cancel_order_by_id = Mock(side_effect=Exception("Cancel failed"))
        
        result = client.cancel_order('order123')
        
        assert result is False
    
    def test_position_info_dataclass(self):
        """Test PositionInfo dataclass functionality."""
        position = PositionInfo(
            ticker='AAPL',
            quantity=100.0,
            market_value=15000.00,
            cost_basis=14000.00,
            unrealized_pnl=1000.00,
            unrealized_pnl_percent=7.14,
            current_price=150.00,
            last_updated=datetime.now()
        )
        
        assert position.ticker == 'AAPL'
        assert position.quantity == 100.0
        assert position.market_value == 15000.00
        assert position.unrealized_pnl == 1000.00
    
    def test_order_info_dataclass(self):
        """Test OrderInfo dataclass functionality."""
        order = OrderInfo(
            order_id='order123',
            ticker='AAPL',
            side='buy',
            quantity=10.0,
            filled_quantity=10.0,
            order_type='market',
            status='filled',
            submitted_at=datetime.now(),
            filled_at=datetime.now(),
            filled_avg_price=150.00,
            time_in_force='gtc'
        )
        
        assert order.order_id == 'order123'
        assert order.ticker == 'AAPL'
        assert order.side == 'buy'
        assert order.quantity == 10.0
        assert order.status == 'filled'
    
    def test_trade_order_dataclass(self):
        """Test TradeOrder dataclass functionality."""
        order = TradeOrder(
            ticker='AAPL',
            side='buy',
            quantity=10,
            order_type='market',
            time_in_force='gtc',
            amount=1500.0
        )
        
        assert order.ticker == 'AAPL'
        assert order.side == 'buy'
        assert order.quantity == 10
        assert order.order_type == 'market'
        assert order.time_in_force == 'gtc'
        assert order.amount == 1500.0