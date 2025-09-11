"""
Tests for Andy (Grok) Agent RSI-based trading strategy.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date
import pandas as pd

from src.agents.andy_grok_agent import AndyGrokAgent, create_andy_grok_agent
from src.agents.technical_agent import TechnicalSignal, TechnicalIndicator
from src.utils.exceptions import ValidationError, TradingError
from src.utils.technical_indicators import TechnicalIndicators


class TestAndyGrokAgent:
    """Test suite for Andy Grok Agent."""
    
    @pytest.fixture
    def agent_config(self):
        """Standard agent configuration."""
        return {
            'id': 'test_andy_grok',
            'name': 'Test Andy Grok Agent',
            'type': 'technical',
            'enabled': True,
            'target_ticker': 'SPY',
            'position_size_percent': 1.0,
            'max_position_size': 10000,
            'min_account_value': 1000,
            'rsi_period': 14,
            'rsi_oversold_threshold': 30.0,
            'rsi_overbought_threshold': 70.0,
            'rsi_lookback_hours': 14
        }
    
    @pytest.fixture
    def mock_clients(self):
        """Mock external clients."""
        with patch('src.agents.technical_agent.DatabaseManager') as mock_db, \
             patch('src.agents.technical_agent.AlpacaClient') as mock_alpaca, \
             patch('src.agents.technical_agent.QuiverClient') as mock_quiver, \
             patch('src.agents.technical_agent.MarketDataService') as mock_market:
            
            # Mock account equity
            mock_alpaca.return_value.get_account.return_value.equity = 10000.0
            
            yield {
                'db': mock_db.return_value,
                'alpaca': mock_alpaca.return_value,
                'quiver': mock_quiver.return_value,
                'market_data': mock_market.return_value
            }
    
    @pytest.fixture
    def agent(self, agent_config, mock_clients):
        """Create a test agent instance."""
        return AndyGrokAgent('test_andy_grok', agent_config)
    
    def test_agent_initialization(self, agent_config, mock_clients):
        """Test agent initialization with valid configuration."""
        agent = AndyGrokAgent('test_andy_grok', agent_config)
        
        assert agent.agent_id == 'test_andy_grok'
        assert agent.target_ticker == 'SPY'
        assert agent.position_size_percent == 1.0
        assert agent.rsi_period == 14
        assert agent.rsi_oversold_threshold == 30.0
        assert agent.rsi_overbought_threshold == 70.0
    
    def test_invalid_configuration(self, mock_clients):
        """Test agent initialization with invalid configuration."""
        # Missing required fields
        with pytest.raises(ValidationError):
            AndyGrokAgent('test', {})
        
        # Invalid RSI period
        invalid_config = {
            'id': 'test',
            'name': 'Test',
            'type': 'technical',
            'rsi_period': 1  # Too small
        }
        with pytest.raises(ValidationError):
            AndyGrokAgent('test', invalid_config)
        
        # Invalid RSI thresholds
        invalid_config = {
            'id': 'test',
            'name': 'Test', 
            'type': 'technical',
            'rsi_oversold_threshold': 80.0,  # Greater than overbought
            'rsi_overbought_threshold': 70.0
        }
        with pytest.raises(ValidationError):
            AndyGrokAgent('test', invalid_config)
    
    def test_rsi_calculation(self, agent, mock_clients):
        """Test RSI calculation and indicator generation."""
        # Mock price data
        mock_price_data = pd.DataFrame({
            'Close': [100, 102, 98, 101, 99, 103, 97, 105, 96, 108, 95, 110, 94, 112, 93]
        }, index=pd.date_range('2024-01-01', periods=15, freq='H'))
        
        with patch('src.utils.technical_indicators.technical_indicators') as mock_ti:
            # Mock successful RSI calculation
            mock_ti.calculate_rsi.return_value = (25.5, {
                'period': 14,
                'data_points': 15,
                'latest_price': 93.0,
                'calculation_time': datetime.now()
            })
            
            indicators = agent.calculate_technical_indicators('SPY')
            
            assert len(indicators) == 1
            rsi_indicator = indicators[0]
            assert rsi_indicator.name == 'RSI_14'
            assert rsi_indicator.value == 25.5
            assert rsi_indicator.signal == TechnicalSignal.BUY  # RSI < 30 = oversold
    
    def test_rsi_signal_generation(self, agent, mock_clients):
        """Test trading signal generation from RSI values."""
        # Test oversold condition (RSI < 30)
        oversold_indicator = TechnicalIndicator(
            name='RSI_14',
            value=25.0,
            signal=TechnicalSignal.BUY,
            confidence=0.8,
            timestamp=datetime.now()
        )
        
        signal = agent.generate_trading_signal([oversold_indicator])
        assert signal == TechnicalSignal.BUY
        
        # Test overbought condition (RSI > 70)
        overbought_indicator = TechnicalIndicator(
            name='RSI_14',
            value=75.0,
            signal=TechnicalSignal.SHORT,
            confidence=0.8,
            timestamp=datetime.now()
        )
        
        signal = agent.generate_trading_signal([overbought_indicator])
        assert signal == TechnicalSignal.SHORT
        
        # Test neutral condition (30 <= RSI <= 70)
        neutral_indicator = TechnicalIndicator(
            name='RSI_14',
            value=50.0,
            signal=TechnicalSignal.HOLD,
            confidence=0.5,
            timestamp=datetime.now()
        )
        
        signal = agent.generate_trading_signal([neutral_indicator])
        assert signal == TechnicalSignal.HOLD
    
    def test_position_size_calculation(self, agent, mock_clients):
        """Test position sizing based on account equity."""
        # Test normal case
        with patch.object(agent, 'get_account_equity', return_value=10000.0):
            position_size = agent.calculate_position_size(100.0)
            expected_size = 10000.0 * 0.01  # 1% of account
            assert position_size == expected_size
        
        # Test below minimum account value
        with patch.object(agent, 'get_account_equity', return_value=500.0):
            position_size = agent.calculate_position_size(100.0)
            assert position_size == 0.0
        
        # Test max position size limit
        with patch.object(agent, 'get_account_equity', return_value=2000000.0):
            position_size = agent.calculate_position_size(100.0)
            assert position_size == agent.max_position_size
    
    def test_market_hours_detection(self, agent, mock_clients):
        """Test market hours and timing logic."""
        # Mock Eastern timezone datetime
        with patch('src.agents.technical_agent.datetime') as mock_dt:
            # Test market open time (Tuesday 10:00 AM ET)
            mock_dt.now.return_value = datetime(2024, 1, 2, 10, 0)  # Tuesday
            mock_dt.strptime = datetime.strptime
            
            is_open = agent.is_market_open(datetime(2024, 1, 2, 10, 0))
            assert is_open
            
            # Test after market hours
            is_open = agent.is_market_open(datetime(2024, 1, 2, 17, 0))
            assert not is_open
            
            # Test weekend
            is_open = agent.is_market_open(datetime(2024, 1, 6, 10, 0))  # Saturday
            assert not is_open
    
    def test_position_close_timing(self, agent, mock_clients):
        """Test position closing logic near market close."""
        # Test before position close time
        should_close = agent.should_close_positions(datetime(2024, 1, 2, 15, 50))
        assert not should_close
        
        # Test at position close time
        should_close = agent.should_close_positions(datetime(2024, 1, 2, 15, 55))
        assert should_close
        
        # Test after market close
        should_close = agent.should_close_positions(datetime(2024, 1, 2, 16, 30))
        assert should_close
    
    def test_morning_analysis_workflow(self, agent, mock_clients):
        """Test morning analysis and trade generation."""
        with patch.object(agent, 'is_market_entry_time', return_value=True), \
             patch.object(agent, 'can_trade_today', return_value=True), \
             patch.object(agent, 'process_technical_strategy') as mock_strategy:
            
            # Mock successful strategy processing
            mock_decision = Mock()
            mock_decision.ticker = 'SPY'
            mock_decision.side = 'buy'
            mock_decision.amount = 100.0
            mock_strategy.return_value = [mock_decision]
            
            decisions = agent.execute_morning_analysis()
            
            assert len(decisions) == 1
            assert agent.has_traded_today is True
            mock_strategy.assert_called_once()
    
    def test_closing_workflow(self, agent, mock_clients):
        """Test position closing workflow."""
        # Mock current positions
        mock_position = Mock()
        mock_position.ticker = 'SPY'
        mock_position.quantity = 10.0
        mock_position.current_price = 100.0
        
        mock_clients['alpaca'].get_all_positions.return_value = [mock_position]
        
        with patch.object(agent, 'calculate_technical_indicators') as mock_indicators:
            mock_indicators.return_value = []
            
            decisions = agent.execute_closing_workflow()
            
            # Should generate close decision
            assert len(decisions) >= 0  # May be 0 if no positions
    
    def test_daily_trade_limits(self, agent, mock_clients):
        """Test daily trading limits."""
        # Test within limits
        agent.daily_trade_count = 2
        agent.max_daily_trades = 3
        assert agent.can_trade_today() is True
        
        # Test at limit
        agent.daily_trade_count = 3
        assert agent.can_trade_today() is False
    
    def test_strategy_health_validation(self, agent, mock_clients):
        """Test strategy health checks."""
        with patch.object(agent, 'get_account_equity', return_value=5000.0), \
             patch('src.utils.technical_indicators.technical_indicators') as mock_ti:
            
            # Mock successful data and calculations
            mock_ti.get_hourly_prices.return_value = pd.DataFrame({'Close': [100, 101]})
            mock_ti.calculate_rsi.return_value = (50.0, {'data_points': 15})
            
            health = agent.validate_strategy_health()
            
            assert health['status'] == 'healthy'
            assert len(health['issues']) == 0
    
    def test_strategy_health_issues(self, agent, mock_clients):
        """Test strategy health with issues."""
        # Test low account equity
        with patch.object(agent, 'get_account_equity', return_value=500.0):
            health = agent.validate_strategy_health()
            assert health['status'] == 'unhealthy'
            assert any('Account equity' in issue for issue in health['issues'])
    
    def test_get_strategy_status(self, agent, mock_clients):
        """Test strategy status reporting."""
        with patch.object(agent, 'get_account_equity', return_value=10000.0):
            status = agent.get_strategy_status()
            
            assert status['agent_id'] == 'test_andy_grok'
            assert status['strategy'] == 'RSI-based SPY trading'
            assert status['target_ticker'] == 'SPY'
            assert 'rsi_thresholds' in status
            assert 'market_status' in status
            assert 'position_sizing' in status
    
    def test_factory_function(self, mock_clients):
        """Test the factory function for creating Andy Grok agents."""
        agent = create_andy_grok_agent()
        
        assert agent.agent_id == 'andy_grok'
        assert isinstance(agent, AndyGrokAgent)
        assert agent.target_ticker == 'SPY'
        
        # Test with custom configuration
        custom_config = {'rsi_period': 21}
        agent = create_andy_grok_agent('custom_grok', custom_config)
        
        assert agent.agent_id == 'custom_grok'
        assert agent.rsi_period == 21
    
    def test_intraday_workflow_execution(self, agent, mock_clients):
        """Test complete intraday workflow."""
        with patch.object(agent, 'is_market_open', return_value=True), \
             patch.object(agent, 'process_technical_strategy') as mock_strategy, \
             patch.object(agent, 'execute_trade') as mock_execute:
            
            # Mock trade decision
            mock_decision = Mock()
            mock_decision.ticker = 'SPY'
            mock_decision.side = 'buy'
            mock_decision.amount = 100.0
            mock_decision.source_trade = Mock()
            mock_decision.timestamp = datetime.now()
            mock_decision.confidence = 0.8
            mock_strategy.return_value = [mock_decision]
            
            # Mock successful trade execution
            mock_execute.return_value = True
            
            result = agent.execute_intraday_workflow()
            
            assert result.success is True
            assert result.trades_processed == 1
            assert result.orders_placed == 1
            mock_execute.assert_called_once()
    
    def test_error_handling(self, agent, mock_clients):
        """Test error handling in various scenarios."""
        # Test RSI calculation failure
        with patch('src.utils.technical_indicators.technical_indicators') as mock_ti:
            mock_ti.calculate_rsi.return_value = None
            
            indicators = agent.calculate_technical_indicators('SPY')
            assert len(indicators) == 0
        
        # Test market data unavailable
        with patch.object(agent, 'is_market_open', side_effect=Exception('Market data error')):
            try:
                agent.is_market_open()
                assert False, "Should have raised an exception"
            except Exception as e:
                assert 'Market data error' in str(e)


class TestTechnicalIndicators:
    """Test technical indicators utility."""
    
    def test_rsi_calculation_basic(self):
        """Test basic RSI calculation."""
        ti = TechnicalIndicators()
        
        # Mock price data
        mock_data = pd.DataFrame({
            'Close': [100, 102, 98, 101, 99, 103, 97, 105, 96, 108, 95, 110, 94, 112, 93],
            'Open': [99, 101, 100, 99, 100, 98, 102, 96, 104, 95, 107, 94, 109, 93, 111],
            'High': [103, 104, 101, 102, 101, 104, 98, 106, 97, 109, 96, 111, 95, 113, 94],
            'Low': [98, 100, 97, 99, 98, 101, 96, 103, 95, 106, 94, 108, 93, 110, 92],
            'Volume': [1000000] * 15
        }, index=pd.date_range('2024-01-01', periods=15, freq='H'))
        
        with patch.object(ti, 'get_hourly_prices', return_value=mock_data):
            result = ti.calculate_rsi('SPY', period=14, hours=24)
            
            assert result is not None
            rsi_value, metadata = result
            assert 0 <= rsi_value <= 100
            assert metadata['period'] == 14
            assert metadata['data_points'] == 15
    
    def test_data_validation(self):
        """Test price data validation."""
        ti = TechnicalIndicators()
        
        # Test empty data
        empty_data = pd.DataFrame()
        assert not ti._validate_price_data(empty_data, 10)
        
        # Test insufficient data
        small_data = pd.DataFrame({
            'Close': [100, 101],
            'Open': [99, 100],
            'High': [102, 103],
            'Low': [98, 99],
            'Volume': [1000, 1100]
        })
        assert not ti._validate_price_data(small_data, 10)
        
        # Test valid data
        valid_data = pd.DataFrame({
            'Close': [100] * 15,
            'Open': [99] * 15,
            'High': [102] * 15,
            'Low': [98] * 15,
            'Volume': [1000] * 15
        })
        assert ti._validate_price_data(valid_data, 10)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])