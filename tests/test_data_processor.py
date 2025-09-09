"""
Unit tests for Data Processing Engine.
Tests orchestration of API integrations, data processing workflows, and error handling.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date, timedelta

from src.data.data_processor import DataProcessor, ProcessingResult, PortfolioSnapshot
from src.data.quiver_client import CongressionalTrade
from src.data.alpaca_client import PositionInfo, OrderInfo
from src.utils.exceptions import DataProcessingError, APIError


class TestDataProcessor:
    """Test suite for DataProcessor."""
    
    @pytest.fixture
    def processor(self):
        """Create DataProcessor instance for testing."""
        with patch('src.data.data_processor.QuiverClient'), \
             patch('src.data.data_processor.AlpacaClient'), \
             patch('src.data.data_processor.MarketDataService'), \
             patch('src.data.data_processor.DatabaseManager'), \
             patch('src.data.data_processor.settings') as mock_settings:
            
            mock_settings.database.backup_enabled = True
            mock_settings.get_enabled_agents.return_value = [
                {'id': 'test_agent', 'politicians': ['Test Politician'], 'enabled': True}
            ]
            mock_settings.trading.minimum_amount = 100.0
            
            return DataProcessor()
    
    @pytest.fixture
    def sample_congressional_trade(self):
        """Sample congressional trade for testing."""
        return CongressionalTrade(
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
    
    @pytest.fixture
    def sample_position(self):
        """Sample Alpaca position for testing."""
        return PositionInfo(
            ticker='AAPL',
            quantity=100.0,
            market_value=15000.00,
            cost_basis=14000.00,
            unrealized_pnl=1000.00,
            unrealized_pnl_percent=7.14,
            current_price=150.00,
            last_updated=datetime.now()
        )
    
    @pytest.fixture
    def sample_order(self):
        """Sample order info for testing."""
        return OrderInfo(
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
    
    def test_initialization(self, processor):
        """Test processor initialization."""
        assert processor.max_concurrent_requests == 5
        assert processor.processing_timeout == 300
        assert processor.processing_stats['total_runs'] == 0
        assert processor.processing_stats['successful_runs'] == 0
    
    def test_process_daily_data_success(self, processor, sample_congressional_trade, sample_order):
        """Test successful daily data processing."""
        target_date = date.today()
        
        # Mock all the sub-processes
        processor._create_data_backup = Mock()
        processor._fetch_congressional_trades = Mock(return_value=[sample_congressional_trade])
        processor._process_agent_trades = Mock(return_value=1)
        processor._synchronize_portfolios = Mock()
        processor._update_performance_metrics = Mock()
        processor._validate_data_consistency = Mock(return_value={'warnings': []})
        processor._update_processing_stats = Mock()
        
        # Mock database transaction
        processor.db.transaction = Mock()
        processor.db.transaction.return_value.__enter__ = Mock()
        processor.db.transaction.return_value.__exit__ = Mock(return_value=None)
        
        result = processor.process_daily_data(target_date)
        
        assert result.success is True
        assert result.processed_trades == 1
        assert len(result.errors) == 0
        
        # Verify all steps were called
        processor._create_data_backup.assert_called_once()
        processor._fetch_congressional_trades.assert_called_once_with(target_date)
        processor._process_agent_trades.assert_called_once()
        processor._synchronize_portfolios.assert_called_once()
        processor._update_performance_metrics.assert_called_once()
        processor._validate_data_consistency.assert_called_once()
    
    def test_process_daily_data_with_error(self, processor):
        """Test daily data processing with error."""
        target_date = date.today()
        
        # Mock database transaction
        processor.db.transaction = Mock()
        processor.db.transaction.return_value.__enter__ = Mock(side_effect=Exception("Database error"))
        processor.db.transaction.return_value.__exit__ = Mock(return_value=None)
        
        processor._update_processing_stats = Mock()
        
        result = processor.process_daily_data(target_date)
        
        assert result.success is False
        assert result.processed_trades == 0
        assert len(result.errors) == 1
        assert "Database error" in result.errors[0]
    
    def test_fetch_congressional_trades_success(self, processor, sample_congressional_trade):
        """Test successful congressional trades fetching."""
        processor.quiver_client.get_congressional_trades = Mock(return_value=[sample_congressional_trade])
        
        trades = processor._fetch_congressional_trades(date.today())
        
        assert len(trades) == 1
        assert trades[0] == sample_congressional_trade
    
    def test_fetch_congressional_trades_api_error(self, processor):
        """Test congressional trades fetching with API error."""
        processor.quiver_client.get_congressional_trades = Mock(side_effect=APIError("API failed", "Quiver", 500))
        
        trades = processor._fetch_congressional_trades(date.today())
        
        assert len(trades) == 0  # Should return empty list on error
    
    def test_process_agent_trades_success(self, processor, sample_congressional_trade):
        """Test successful agent trades processing."""
        processor.quiver_client.find_matching_politicians = Mock(return_value=['Test Politician'])
        processor._process_agent_specific_trades = Mock(return_value=1)
        
        trades = [sample_congressional_trade]
        result = processor._process_agent_trades(trades, date.today())
        
        assert result == 1
    
    def test_process_agent_trades_no_trades(self, processor):
        """Test agent trades processing with no trades."""
        result = processor._process_agent_trades([], date.today())
        
        assert result == 0
    
    def test_process_agent_trades_no_matching_trades(self, processor, sample_congressional_trade):
        """Test agent trades processing with no matching trades."""
        processor.quiver_client.find_matching_politicians = Mock(return_value=[])
        
        trades = [sample_congressional_trade]
        result = processor._process_agent_trades(trades, date.today())
        
        assert result == 0
    
    def test_process_agent_trades_with_error(self, processor, sample_congressional_trade):
        """Test agent trades processing with error in one agent."""
        processor.quiver_client.find_matching_politicians = Mock(side_effect=Exception("Processing error"))
        
        trades = [sample_congressional_trade]
        result = processor._process_agent_trades(trades, date.today())
        
        assert result == 0  # Should continue despite error
    
    def test_process_agent_specific_trades_success(self, processor, sample_congressional_trade, sample_order):
        """Test successful processing of trades for specific agent."""
        processor._is_trade_already_processed = Mock(return_value=False)
        processor.alpaca_client.validate_ticker = Mock(return_value=True)
        processor._calculate_trade_amount = Mock(return_value=150.0)
        processor.alpaca_client.place_market_order = Mock(return_value=sample_order)
        processor._store_trade_record = Mock()
        
        result = processor._process_agent_specific_trades('test_agent', [sample_congressional_trade], date.today())
        
        assert result == 1
        processor._store_trade_record.assert_called_once()
    
    def test_process_agent_specific_trades_already_processed(self, processor, sample_congressional_trade):
        """Test processing of already processed trades."""
        processor._is_trade_already_processed = Mock(return_value=True)
        
        result = processor._process_agent_specific_trades('test_agent', [sample_congressional_trade], date.today())
        
        assert result == 0
    
    def test_process_agent_specific_trades_invalid_ticker(self, processor, sample_congressional_trade):
        """Test processing with invalid ticker."""
        processor._is_trade_already_processed = Mock(return_value=False)
        processor.alpaca_client.validate_ticker = Mock(return_value=False)
        
        result = processor._process_agent_specific_trades('test_agent', [sample_congressional_trade], date.today())
        
        assert result == 0
    
    def test_process_agent_specific_trades_below_minimum(self, processor, sample_congressional_trade):
        """Test processing with trade amount below minimum."""
        processor._is_trade_already_processed = Mock(return_value=False)
        processor.alpaca_client.validate_ticker = Mock(return_value=True)
        processor._calculate_trade_amount = Mock(return_value=50.0)  # Below minimum
        
        result = processor._process_agent_specific_trades('test_agent', [sample_congressional_trade], date.today())
        
        assert result == 0
    
    def test_process_agent_specific_trades_order_failure(self, processor, sample_congressional_trade):
        """Test processing with order placement failure."""
        processor._is_trade_already_processed = Mock(return_value=False)
        processor.alpaca_client.validate_ticker = Mock(return_value=True)
        processor._calculate_trade_amount = Mock(return_value=150.0)
        processor.alpaca_client.place_market_order = Mock(return_value=None)  # Order failed
        
        result = processor._process_agent_specific_trades('test_agent', [sample_congressional_trade], date.today())
        
        assert result == 0
    
    def test_calculate_trade_amount(self, processor, sample_congressional_trade):
        """Test trade amount calculation."""
        amount = processor._calculate_trade_amount(sample_congressional_trade)
        
        assert amount >= 100.0  # Should be at least minimum amount
    
    def test_is_trade_already_processed_true(self, processor, sample_congressional_trade):
        """Test checking if trade is already processed (true case)."""
        processor.db.execute_query = Mock(return_value=[(1,)])  # Count > 0
        
        result = processor._is_trade_already_processed('test_agent', sample_congressional_trade, date.today())
        
        assert result is True
    
    def test_is_trade_already_processed_false(self, processor, sample_congressional_trade):
        """Test checking if trade is already processed (false case)."""
        processor.db.execute_query = Mock(return_value=[(0,)])  # Count = 0
        
        result = processor._is_trade_already_processed('test_agent', sample_congressional_trade, date.today())
        
        assert result is False
    
    def test_is_trade_already_processed_error(self, processor, sample_congressional_trade):
        """Test checking if trade is already processed with database error."""
        processor.db.execute_query = Mock(side_effect=Exception("Database error"))
        
        result = processor._is_trade_already_processed('test_agent', sample_congressional_trade, date.today())
        
        assert result is False  # Default to False on error
    
    def test_store_trade_record_success(self, processor, sample_congressional_trade, sample_order):
        """Test successful trade record storage."""
        processor.db.insert_trade = Mock()
        
        processor._store_trade_record('test_agent', sample_congressional_trade, sample_order, date.today())
        
        processor.db.insert_trade.assert_called_once()
        
        # Verify the trade data structure
        call_args = processor.db.insert_trade.call_args[0][0]
        assert call_args['agent_id'] == 'test_agent'
        assert call_args['ticker'] == 'AAPL'
        assert call_args['alpaca_order_id'] == 'order123'
    
    def test_store_trade_record_error(self, processor, sample_congressional_trade, sample_order):
        """Test trade record storage with database error."""
        processor.db.insert_trade = Mock(side_effect=Exception("Database error"))
        
        with pytest.raises(Exception, match="Database error"):
            processor._store_trade_record('test_agent', sample_congressional_trade, sample_order, date.today())
    
    def test_synchronize_portfolios_success(self, processor, sample_position):
        """Test successful portfolio synchronization."""
        processor.alpaca_client.get_all_positions = Mock(return_value=[sample_position])
        processor._reconcile_agent_positions = Mock()
        
        processor._synchronize_portfolios()
        
        processor._reconcile_agent_positions.assert_called_once_with('test_agent', [sample_position])
    
    def test_synchronize_portfolios_error(self, processor):
        """Test portfolio synchronization with error."""
        processor.alpaca_client.get_all_positions = Mock(side_effect=Exception("API error"))
        
        with pytest.raises(Exception, match="API error"):
            processor._synchronize_portfolios()
    
    def test_reconcile_agent_positions_success(self, processor, sample_position):
        """Test successful agent position reconciliation."""
        processor._get_agent_trades = Mock(return_value=[
            {'ticker': 'AAPL', 'total_quantity': 10.0, 'avg_price': 140.0}
        ])
        processor._allocate_positions_to_agent = Mock(return_value=[
            {'ticker': 'AAPL', 'quantity': 10.0, 'market_value': 1500.0}
        ])
        processor._update_agent_positions = Mock()
        
        processor._reconcile_agent_positions('test_agent', [sample_position])
        
        processor._update_agent_positions.assert_called_once()
    
    def test_get_agent_trades_success(self, processor):
        """Test successful agent trades retrieval."""
        processor.db.execute_query = Mock(return_value=[
            ('AAPL', 10.0, 140.0),
            ('GOOGL', 5.0, 2800.0)
        ])
        
        trades = processor._get_agent_trades('test_agent')
        
        assert len(trades) == 2
        assert trades[0]['ticker'] == 'AAPL'
        assert trades[0]['total_quantity'] == 10.0
        assert trades[0]['avg_price'] == 140.0
    
    def test_allocate_positions_to_agent_success(self, processor, sample_position):
        """Test successful position allocation to agent."""
        agent_trades = [{'ticker': 'AAPL', 'total_quantity': 10.0, 'avg_price': 140.0}]
        
        positions = processor._allocate_positions_to_agent('test_agent', agent_trades, [sample_position])
        
        assert len(positions) == 1
        assert positions[0]['ticker'] == 'AAPL'
        assert positions[0]['quantity'] == 10.0
        assert positions[0]['current_price'] == 150.00
    
    def test_allocate_positions_to_agent_no_matching(self, processor, sample_position):
        """Test position allocation with no matching trades."""
        agent_trades = [{'ticker': 'GOOGL', 'total_quantity': 5.0, 'avg_price': 2800.0}]
        
        positions = processor._allocate_positions_to_agent('test_agent', agent_trades, [sample_position])
        
        assert len(positions) == 0  # No matching positions
    
    def test_update_agent_positions_success(self, processor):
        """Test successful agent positions update."""
        processor.db.execute_query = Mock()
        processor.db.insert_position = Mock()
        
        positions = [
            {'ticker': 'AAPL', 'quantity': 10.0, 'market_value': 1500.0}
        ]
        
        processor._update_agent_positions('test_agent', positions)
        
        # Should clear existing positions and insert new ones
        processor.db.execute_query.assert_called_once()
        processor.db.insert_position.assert_called_once()
    
    def test_update_agent_positions_error(self, processor):
        """Test agent positions update with error."""
        processor.db.execute_query = Mock(side_effect=Exception("Database error"))
        
        with pytest.raises(Exception, match="Database error"):
            processor._update_agent_positions('test_agent', [])
    
    def test_update_performance_metrics_success(self, processor):
        """Test successful performance metrics update."""
        processor._calculate_agent_portfolio_value = Mock(return_value=10000.0)
        processor._get_previous_portfolio_value = Mock(return_value=9500.0)
        processor._get_inception_portfolio_value = Mock(return_value=9000.0)
        processor.db.insert_daily_performance = Mock()
        
        processor._update_performance_metrics(date.today())
        
        processor.db.insert_daily_performance.assert_called_once()
        
        # Verify performance calculation
        call_args = processor.db.insert_daily_performance.call_args[0][0]
        assert call_args['agent_id'] == 'test_agent'
        assert call_args['total_value'] == 10000.0
        assert call_args['daily_return_pct'] == pytest.approx(5.26, abs=0.01)  # (10000-9500)/9500*100
        assert call_args['total_return_pct'] == pytest.approx(11.11, abs=0.01)  # (10000-9000)/9000*100
    
    def test_calculate_agent_portfolio_value_success(self, processor):
        """Test successful agent portfolio value calculation."""
        processor.db.execute_query = Mock(return_value=[(15000.0,)])
        
        value = processor._calculate_agent_portfolio_value('test_agent')
        
        assert value == 15000.0
    
    def test_calculate_agent_portfolio_value_no_data(self, processor):
        """Test agent portfolio value calculation with no data."""
        processor.db.execute_query = Mock(return_value=[])
        
        value = processor._calculate_agent_portfolio_value('test_agent')
        
        assert value == 0.0
    
    def test_get_previous_portfolio_value_success(self, processor):
        """Test successful previous portfolio value retrieval."""
        processor.db.execute_query = Mock(return_value=[(9500.0,)])
        
        value = processor._get_previous_portfolio_value('test_agent', date.today())
        
        assert value == 9500.0
    
    def test_get_previous_portfolio_value_no_data(self, processor):
        """Test previous portfolio value retrieval with no data."""
        processor.db.execute_query = Mock(return_value=[])
        
        value = processor._get_previous_portfolio_value('test_agent', date.today())
        
        assert value is None
    
    def test_get_inception_portfolio_value_success(self, processor):
        """Test successful inception portfolio value retrieval."""
        processor.db.execute_query = Mock(return_value=[(9000.0,)])
        
        value = processor._get_inception_portfolio_value('test_agent')
        
        assert value == 9000.0
    
    def test_get_inception_portfolio_value_no_data(self, processor):
        """Test inception portfolio value retrieval with no data."""
        processor.db.execute_query = Mock(return_value=[(None,)])
        
        value = processor._get_inception_portfolio_value('test_agent')
        
        assert value is None
    
    def test_validate_data_consistency_success(self, processor):
        """Test successful data consistency validation."""
        processor.alpaca_client.test_connection = Mock(return_value=True)
        processor.quiver_client.test_connection = Mock(return_value=True)
        processor._validate_database_integrity = Mock(return_value={'success': True, 'errors': []})
        processor._validate_portfolio_consistency = Mock(return_value={'success': True, 'warnings': []})
        
        result = processor._validate_data_consistency()
        
        assert result['checks_performed'] == 4
        assert result['checks_passed'] == 4
        assert len(result['errors']) == 0
    
    def test_validate_data_consistency_with_failures(self, processor):
        """Test data consistency validation with failures."""
        processor.alpaca_client.test_connection = Mock(return_value=False)
        processor.quiver_client.test_connection = Mock(return_value=False)
        processor._validate_database_integrity = Mock(return_value={'success': False, 'errors': ['DB error']})
        processor._validate_portfolio_consistency = Mock(return_value={'success': False, 'warnings': ['Portfolio mismatch']})
        
        result = processor._validate_data_consistency()
        
        assert result['checks_performed'] == 4
        assert result['checks_passed'] == 0
        assert len(result['errors']) == 2  # Alpaca + DB errors
        assert len(result['warnings']) == 2  # Quiver + portfolio warnings
    
    def test_validate_database_integrity_success(self, processor):
        """Test successful database integrity validation."""
        processor.db.execute_query = Mock(return_value=[])  # No orphaned records
        
        result = processor._validate_database_integrity()
        
        assert result['success'] is True
        assert len(result['errors']) == 0
    
    def test_validate_database_integrity_orphaned_records(self, processor):
        """Test database integrity validation with orphaned records."""
        processor.db.execute_query = Mock(return_value=[('agent1', 5), ('agent2', 3)])
        
        result = processor._validate_database_integrity()
        
        assert result['success'] is False
        assert len(result['errors']) == 1
        assert 'orphaned positions' in result['errors'][0]
    
    def test_validate_portfolio_consistency_success(self, processor, sample_position):
        """Test successful portfolio consistency validation."""
        processor.alpaca_client.get_all_positions = Mock(return_value=[sample_position])
        processor.db.execute_query = Mock(return_value=[('AAPL',)])  # 1 distinct ticker
        
        result = processor._validate_portfolio_consistency()
        
        assert result['success'] is True
        assert len(result['warnings']) == 0
    
    def test_validate_portfolio_consistency_mismatch(self, processor, sample_position):
        """Test portfolio consistency validation with mismatch."""
        processor.alpaca_client.get_all_positions = Mock(return_value=[sample_position])
        processor.db.execute_query = Mock(return_value=[('AAPL',), ('GOOGL',)])  # 2 distinct tickers
        
        result = processor._validate_portfolio_consistency()
        
        assert result['success'] is True
        assert len(result['warnings']) == 1
        assert 'Position count mismatch' in result['warnings'][0]
    
    def test_update_processing_stats(self, processor):
        """Test processing statistics update."""
        processor._update_processing_stats(True, 120.5, 5)
        
        stats = processor.processing_stats
        assert stats['total_runs'] == 1
        assert stats['successful_runs'] == 1
        assert stats['failed_runs'] == 0
        assert stats['total_trades_processed'] == 5
        assert stats['avg_processing_time'] == 120.5
    
    def test_get_processing_stats(self, processor):
        """Test processing statistics retrieval."""
        processor.processing_stats['total_runs'] = 10
        processor.processing_stats['successful_runs'] = 8
        processor.last_processing_time = datetime.now()
        
        stats = processor.get_processing_stats()
        
        assert stats['total_runs'] == 10
        assert stats['success_rate'] == 80.0
        assert 'last_processing_time' in stats
    
    def test_get_portfolio_snapshots_success(self, processor):
        """Test successful portfolio snapshots retrieval."""
        processor.db.execute_query = Mock(side_effect=[
            [('id', 'test_agent', 'AAPL', 10.0, 140.0, 150.0, 1500.0, 100.0)],  # Positions
            [(5.0, 10.0)]  # Performance
        ])
        
        snapshots = processor.get_portfolio_snapshots(['test_agent'])
        
        assert len(snapshots) == 1
        assert snapshots[0].agent_id == 'test_agent'
        assert snapshots[0].total_value == 1500.0
        assert snapshots[0].position_count == 1
        assert len(snapshots[0].positions) == 1
    
    def test_get_portfolio_snapshots_error(self, processor):
        """Test portfolio snapshots retrieval with error."""
        processor.db.execute_query = Mock(side_effect=Exception("Database error"))
        
        snapshots = processor.get_portfolio_snapshots(['test_agent'])
        
        assert len(snapshots) == 0  # Should handle error gracefully
    
    def test_test_all_connections_success(self, processor):
        """Test successful connection testing for all APIs."""
        processor.quiver_client.test_connection = Mock(return_value=True)
        processor.alpaca_client.test_connection = Mock(return_value=True)
        processor.market_data_service.get_current_price = Mock(return_value=150.0)
        processor.db.execute_query = Mock(return_value=[(1,)])
        
        results = processor.test_all_connections()
        
        assert results['quiver'] is True
        assert results['alpaca'] is True
        assert results['yfinance'] is True
        assert results['database'] is True
    
    def test_test_all_connections_failures(self, processor):
        """Test connection testing with failures."""
        processor.quiver_client.test_connection = Mock(side_effect=Exception("Quiver error"))
        processor.alpaca_client.test_connection = Mock(side_effect=Exception("Alpaca error"))
        processor.market_data_service.get_current_price = Mock(return_value=None)
        processor.db.execute_query = Mock(side_effect=Exception("Database error"))
        
        results = processor.test_all_connections()
        
        assert results['quiver'] is False
        assert results['alpaca'] is False
        assert results['yfinance'] is False
        assert results['database'] is False
    
    def test_processing_result_dataclass(self):
        """Test ProcessingResult dataclass functionality."""
        result = ProcessingResult(
            success=True,
            processed_trades=5,
            errors=[],
            execution_time=120.5,
            timestamp=datetime.now()
        )
        
        assert result.success is True
        assert result.processed_trades == 5
        assert len(result.errors) == 0
        assert result.execution_time == 120.5
    
    def test_portfolio_snapshot_dataclass(self):
        """Test PortfolioSnapshot dataclass functionality."""
        snapshot = PortfolioSnapshot(
            agent_id='test_agent',
            timestamp=datetime.now(),
            total_value=10000.0,
            position_count=3,
            positions=[{'ticker': 'AAPL', 'quantity': 10}],
            performance_metrics={'daily_return': 5.0}
        )
        
        assert snapshot.agent_id == 'test_agent'
        assert snapshot.total_value == 10000.0
        assert snapshot.position_count == 3
        assert len(snapshot.positions) == 1
        assert 'daily_return' in snapshot.performance_metrics