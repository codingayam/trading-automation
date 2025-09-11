"""
Tests for trading agents and related functionality.
"""
import pytest
from datetime import datetime, date
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any

from src.agents.base_agent import BaseAgent, AgentState, TradeDecision, AgentPerformance, ExecutionResult
from src.agents.individual_agent import IndividualAgent
from src.agents.committee_agent import CommitteeAgent
from src.agents.agent_factory import AgentFactory
from src.data.quiver_client import CongressionalTrade
from src.utils.exceptions import ValidationError, TradingError

class TestBaseAgent:
    """Test BaseAgent abstract functionality."""
    
    def create_mock_agent(self, agent_id: str = "test_agent") -> BaseAgent:
        """Create a mock agent for testing."""
        class MockAgent(BaseAgent):
            def _matches_tracked_politicians(self, trade: CongressionalTrade) -> bool:
                return trade.politician == "Test Politician"
        
        config = {
            'id': agent_id,
            'name': 'Test Agent',
            'type': 'individual',
            'politicians': ['Test Politician'],
            'enabled': True,
            'parameters': {
                'minimum_trade_value': 50000,
                'position_size_type': 'fixed',
                'position_size_value': 100,
                'match_threshold': 0.85
            }
        }
        
        return MockAgent(agent_id, config)
    
    def create_mock_congressional_trade(self, politician: str = "Test Politician", 
                                      ticker: str = "AAPL", amount: float = 75000) -> CongressionalTrade:
        """Create a mock congressional trade."""
        return CongressionalTrade(
            politician=politician,
            ticker=ticker,
            transaction_date=date.today(),
            trade_type="Purchase",
            amount_range="$50,001 - $100,000",
            amount_min=amount,
            amount_max=amount,
            last_modified=date.today(),
            raw_data={}
        )
    
    @patch('src.agents.base_agent.DatabaseManager')
    @patch('src.agents.base_agent.AlpacaClient')
    @patch('src.agents.base_agent.QuiverClient')
    @patch('src.agents.base_agent.MarketDataService')
    def test_agent_initialization(self, mock_market_data, mock_quiver, mock_alpaca, mock_db):
        """Test agent initialization."""
        agent = self.create_mock_agent()
        
        assert agent.agent_id == "test_agent"
        assert agent.state == AgentState.INITIALIZED
        assert len(agent.politicians) == 1
        assert agent.politicians[0] == "Test Politician"
        assert agent.minimum_trade_value == 50000
        assert agent.position_size_value == 100
        assert agent.match_threshold == 0.85
    
    def test_config_validation(self):
        """Test configuration validation."""
        # Missing required fields
        with pytest.raises(ValidationError):
            class MockAgent(BaseAgent):
                def _matches_tracked_politicians(self, trade: CongressionalTrade) -> bool:
                    return True
            config = {'id': 'test'}
            MockAgent('test', config)
        
        # Empty politicians list
        with pytest.raises(ValidationError):
            class MockAgent(BaseAgent):
                def _matches_tracked_politicians(self, trade: CongressionalTrade) -> bool:
                    return True
            config = {
                'id': 'test',
                'name': 'Test',
                'type': 'individual',
                'politicians': []
            }
            MockAgent('test', config)
        
        # Invalid parameter values
        with pytest.raises(ValidationError):
            class MockAgent(BaseAgent):
                def _matches_tracked_politicians(self, trade: CongressionalTrade) -> bool:
                    return True
            config = {
                'id': 'test',
                'name': 'Test', 
                'type': 'individual',
                'politicians': ['Test'],
                'parameters': {
                    'match_threshold': 1.5  # Invalid threshold
                }
            }
            MockAgent('test', config)
    
    @patch('src.agents.base_agent.DatabaseManager')
    @patch('src.agents.base_agent.AlpacaClient')
    @patch('src.agents.base_agent.QuiverClient')
    @patch('src.agents.base_agent.MarketDataService')
    def test_copy_trading_strategy(self, mock_market_data, mock_quiver, mock_alpaca, mock_db):
        """Test copy trading strategy logic."""
        agent = self.create_mock_agent()
        
        # Test matching purchase trade
        trade = self.create_mock_congressional_trade()
        decision = agent._apply_copy_trading_strategy(trade)
        
        assert decision is not None
        assert decision.ticker == "AAPL"
        assert decision.side == "buy"
        assert decision.amount >= 100  # Minimum amount
        assert "Test Politician" in decision.reason
        
        # Test non-matching trade (sale)
        trade.trade_type = "Sale"
        decision = agent._apply_copy_trading_strategy(trade)
        assert decision is None
        
        # Test trade below minimum value
        trade.trade_type = "Purchase"
        trade.amount_max = 10000  # Below 50k minimum
        decision = agent._apply_copy_trading_strategy(trade)
        assert decision is None
    
    @patch('src.agents.base_agent.DatabaseManager')
    @patch('src.agents.base_agent.AlpacaClient')
    @patch('src.agents.base_agent.QuiverClient')  
    @patch('src.agents.base_agent.MarketDataService')
    def test_trade_size_calculation(self, mock_market_data, mock_quiver, mock_alpaca, mock_db):
        """Test trade size calculation."""
        agent = self.create_mock_agent()
        trade = self.create_mock_congressional_trade()
        
        # Fixed size type
        size = agent._calculate_trade_size(trade)
        assert size == 100  # Fixed amount from config
        
        # Percentage size type
        agent.position_size_type = 'percentage'
        agent.position_size_value = 1.0  # 1% of trade
        size = agent._calculate_trade_size(trade)
        assert size == 750  # 1% of 75000
        
        # Dynamic size type (should fallback to minimum)
        agent.position_size_type = 'dynamic'
        size = agent._calculate_trade_size(trade)
        assert size >= 100
    
    @patch('src.agents.base_agent.DatabaseManager')
    @patch('src.agents.base_agent.AlpacaClient')
    @patch('src.agents.base_agent.QuiverClient')
    @patch('src.agents.base_agent.MarketDataService')
    def test_process_trades(self, mock_market_data, mock_quiver, mock_alpaca, mock_db):
        """Test trade processing."""
        agent = self.create_mock_agent()
        
        trades = [
            self.create_mock_congressional_trade("Test Politician", "AAPL", 75000),
            self.create_mock_congressional_trade("Other Politician", "TSLA", 80000),
            self.create_mock_congressional_trade("Test Politician", "MSFT", 25000)  # Below minimum
        ]
        
        decisions = agent.process_trades(trades)
        
        # Should only process matching politician's trades above minimum
        assert len(decisions) == 1
        assert decisions[0].ticker == "AAPL"
        assert agent.state == AgentState.PROCESSING

class TestIndividualAgent:
    """Test IndividualAgent functionality."""
    
    @patch('src.agents.base_agent.DatabaseManager')
    @patch('src.agents.base_agent.AlpacaClient')
    @patch('src.agents.base_agent.QuiverClient')
    @patch('src.agents.base_agent.MarketDataService')
    def test_individual_agent_creation(self, mock_market_data, mock_quiver, mock_alpaca, mock_db):
        """Test individual agent creation."""
        config = {
            'id': 'josh_gottheimer',
            'name': 'Josh Gottheimer Agent',
            'type': 'individual',
            'politicians': ['Josh Gottheimer'],
            'enabled': True,
            'parameters': {
                'minimum_trade_value': 50000,
                'position_size_type': 'fixed',
                'position_size_value': 100,
                'match_threshold': 0.85
            }
        }
        
        agent = IndividualAgent('josh_gottheimer', config)
        assert agent.agent_id == 'josh_gottheimer'
        assert agent.target_politician == 'Josh Gottheimer'
    
    def test_invalid_individual_agent_config(self):
        """Test invalid individual agent configurations."""
        # Wrong type
        with pytest.raises(ValueError):
            config = {
                'type': 'committee',
                'politicians': ['Josh Gottheimer']
            }
            IndividualAgent('test', config)
        
        # Multiple politicians
        with pytest.raises(ValueError):
            config = {
                'type': 'individual',
                'politicians': ['Josh Gottheimer', 'Nancy Pelosi']
            }
            IndividualAgent('test', config)
    
    @patch('src.agents.base_agent.DatabaseManager')
    @patch('src.agents.base_agent.AlpacaClient')
    @patch('src.agents.base_agent.QuiverClient')
    @patch('src.agents.base_agent.MarketDataService')
    def test_politician_name_matching(self, mock_market_data, mock_quiver, mock_alpaca, mock_db):
        """Test politician name fuzzy matching."""
        config = {
            'id': 'josh_gottheimer',
            'name': 'Josh Gottheimer Agent',
            'type': 'individual',
            'politicians': ['Josh Gottheimer'],
            'enabled': True,
            'parameters': {'match_threshold': 0.85}
        }
        
        agent = IndividualAgent('josh_gottheimer', config)
        
        # Test exact match
        trade = CongressionalTrade(
            politician="Josh Gottheimer",
            ticker="AAPL",
            transaction_date=date.today(),
            transaction_type="Purchase",
            amount=75000,
            filing_date=date.today()
        )
        assert agent._matches_tracked_politicians(trade)
        
        # Test fuzzy match
        trade.politician = "Joshua Gottheimer"  # Full name variant
        assert agent._matches_tracked_politicians(trade)
        
        # Test with titles
        trade.politician = "Rep. Josh Gottheimer"
        assert agent._matches_tracked_politicians(trade)
        
        # Test no match
        trade.politician = "Nancy Pelosi"
        assert not agent._matches_tracked_politicians(trade)

class TestCommitteeAgent:
    """Test CommitteeAgent functionality."""
    
    @patch('src.agents.base_agent.DatabaseManager')
    @patch('src.agents.base_agent.AlpacaClient')
    @patch('src.agents.base_agent.QuiverClient')
    @patch('src.agents.base_agent.MarketDataService')
    def test_committee_agent_creation(self, mock_market_data, mock_quiver, mock_alpaca, mock_db):
        """Test committee agent creation."""
        config = {
            'id': 'transportation_committee',
            'name': 'Transportation Committee Agent',
            'type': 'committee',
            'politicians': ['Peter DeFazio', 'Sam Graves', 'Rick Larsen'],
            'enabled': True,
            'parameters': {
                'minimum_trade_value': 50000,
                'match_threshold': 0.85
            }
        }
        
        agent = CommitteeAgent('transportation_committee', config)
        assert agent.agent_id == 'transportation_committee'
        assert len(agent.politicians) == 3
        assert len(agent.normalized_politicians) == 3
    
    def test_invalid_committee_agent_config(self):
        """Test invalid committee agent configurations."""
        # Wrong type
        with pytest.raises(ValueError):
            config = {
                'type': 'individual',
                'politicians': ['Peter DeFazio', 'Sam Graves']
            }
            CommitteeAgent('test', config)
        
        # Too few politicians
        with pytest.raises(ValueError):
            config = {
                'type': 'committee',
                'politicians': ['Peter DeFazio']  # Need at least 2
            }
            CommitteeAgent('test', config)
    
    @patch('src.agents.base_agent.DatabaseManager')
    @patch('src.agents.base_agent.AlpacaClient')
    @patch('src.agents.base_agent.QuiverClient')
    @patch('src.agents.base_agent.MarketDataService')
    def test_committee_member_matching(self, mock_market_data, mock_quiver, mock_alpaca, mock_db):
        """Test committee member matching."""
        config = {
            'id': 'transportation_committee',
            'name': 'Transportation Committee Agent',
            'type': 'committee',
            'politicians': ['Peter DeFazio', 'Sam Graves', 'Rick Larsen'],
            'enabled': True,
            'parameters': {'match_threshold': 0.85}
        }
        
        agent = CommitteeAgent('transportation_committee', config)
        
        # Test matching different members
        trade1 = CongressionalTrade(
            politician="Peter DeFazio",
            ticker="AAPL",
            transaction_date=date.today(),
            transaction_type="Purchase",
            amount=75000,
            filing_date=date.today()
        )
        assert agent._matches_tracked_politicians(trade1)
        assert agent.find_matching_member(trade1) == "Peter DeFazio"
        
        trade2 = CongressionalTrade(
            politician="Rep. Sam Graves",
            ticker="TSLA",
            transaction_date=date.today(),
            transaction_type="Purchase",
            amount=80000,
            filing_date=date.today()
        )
        assert agent._matches_tracked_politicians(trade2)
        assert agent.find_matching_member(trade2) == "Sam Graves"
        
        # Test non-member
        trade3 = CongressionalTrade(
            politician="Nancy Pelosi",
            ticker="MSFT",
            transaction_date=date.today(),
            transaction_type="Purchase",
            amount=90000,
            filing_date=date.today()
        )
        assert not agent._matches_tracked_politicians(trade3)
        assert agent.find_matching_member(trade3) is None

class TestAgentFactory:
    """Test AgentFactory functionality."""
    
    def test_factory_initialization(self):
        """Test factory initialization."""
        factory = AgentFactory()
        
        assert len(factory._agent_types) > 0
        assert 'individual' in factory._agent_types
        assert 'committee' in factory._agent_types
        assert factory.stats.total_agents_created == 0
    
    @patch('src.agents.base_agent.DatabaseManager')
    @patch('src.agents.base_agent.AlpacaClient')
    @patch('src.agents.base_agent.QuiverClient')
    @patch('src.agents.base_agent.MarketDataService')
    def test_agent_creation_from_config(self, mock_market_data, mock_quiver, mock_alpaca, mock_db):
        """Test agent creation from configuration."""
        factory = AgentFactory()
        
        config = {
            'id': 'test_agent',
            'name': 'Test Agent',
            'type': 'individual',
            'politicians': ['Test Politician'],
            'enabled': True,
            'parameters': {
                'minimum_trade_value': 50000,
                'position_size_type': 'fixed',
                'position_size_value': 100,
                'match_threshold': 0.85
            }
        }
        
        agent = factory.create_agent(config)
        
        assert agent is not None
        assert agent.agent_id == 'test_agent'
        assert factory.stats.total_agents_created == 1
        assert factory.stats.active_agents == 1
        assert 'test_agent' in factory._registered_agents
        assert 'test_agent' in factory._active_agents
    
    def test_invalid_agent_creation(self):
        """Test invalid agent creation."""
        factory = AgentFactory()
        
        # Missing ID
        config = {
            'name': 'Test Agent',
            'type': 'individual',
            'politicians': ['Test']
        }
        
        agent = factory.create_agent(config)
        assert agent is None
        assert factory.stats.failed_agents == 1
    
    @patch('src.agents.base_agent.DatabaseManager')
    @patch('src.agents.base_agent.AlpacaClient')
    @patch('src.agents.base_agent.QuiverClient')
    @patch('src.agents.base_agent.MarketDataService')
    def test_agent_lifecycle_management(self, mock_market_data, mock_quiver, mock_alpaca, mock_db):
        """Test agent enable/disable/remove."""
        factory = AgentFactory()
        
        config = {
            'id': 'test_agent',
            'name': 'Test Agent',
            'type': 'individual',
            'politicians': ['Test Politician'],
            'enabled': True,
            'parameters': {}
        }
        
        agent = factory.create_agent(config)
        assert agent is not None
        
        # Test disable
        success = factory.disable_agent('test_agent', 'Test disable')
        assert success
        assert factory.stats.active_agents == 0
        assert 'test_agent' not in factory._active_agents
        
        # Test enable
        success = factory.enable_agent('test_agent')
        assert success
        assert factory.stats.active_agents == 1
        assert 'test_agent' in factory._active_agents
        
        # Test remove
        success = factory.remove_agent('test_agent')
        assert success
        assert 'test_agent' not in factory._registered_agents
        assert 'test_agent' not in factory._active_agents
    
    def test_factory_status(self):
        """Test factory status reporting."""
        factory = AgentFactory()
        
        status = factory.get_factory_status()
        
        assert 'registered_agents' in status
        assert 'active_agents' in status
        assert 'available_types' in status
        assert 'statistics' in status
        assert 'agents' in status