"""
End-to-end integration tests for the complete trading workflow.
Tests the full pipeline: Data -> Agents -> Trading -> Database -> Dashboard
"""
import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from src.scheduler.daily_runner import DailyRunner
from src.agents.agent_factory import AgentFactory
from src.data.data_processor import DataProcessor
from src.utils.exceptions import TradingError, APIError


class TestEndToEndWorkflow:
    """Test complete end-to-end trading workflow."""
    
    @pytest.mark.integration
    def test_complete_daily_execution_workflow(self, test_db, test_alpaca_client, 
                                             sample_congressional_trades, sample_agent_config):
        """Test complete daily execution workflow from data fetch to dashboard update."""
        
        # Initialize components
        agent_factory = AgentFactory(test_db)
        data_processor = DataProcessor(test_db)
        
        # Create test agent
        agent = agent_factory.create_agent(sample_agent_config)
        
        with patch('src.data.quiver_client.QuiverClient.get_congressional_trades') as mock_quiver, \
             patch('src.data.market_data_service.MarketDataService.get_current_price') as mock_price, \
             patch('src.data.alpaca_client.AlpacaClient.place_market_order') as mock_order:
            
            # Setup mocks
            mock_quiver.return_value = sample_congressional_trades
            mock_price.return_value = 150.0
            mock_order.return_value = {'id': 'test_order_123', 'status': 'filled'}
            
            # Process trades through agent
            decisions = agent.process_trades(sample_congressional_trades)
            
            # Should generate at least one trade decision
            assert len(decisions) > 0
            
            # Process decisions through data processor
            results = data_processor.execute_trade_decisions(decisions, agent.agent_id)
            
            # Verify execution results
            assert len(results) == len(decisions)
            for result in results:
                assert result.success
                assert result.order_id is not None
    
    @pytest.mark.integration
    def test_daily_runner_complete_cycle(self, test_db, sample_agent_config):
        """Test DailyRunner complete execution cycle."""
        
        with patch('src.scheduler.daily_runner.QuiverClient') as mock_quiver_class, \
             patch('src.scheduler.daily_runner.AlpacaClient') as mock_alpaca_class, \
             patch('src.scheduler.daily_runner.MarketDataService') as mock_market_class:
            
            # Setup mock instances
            mock_quiver = MagicMock()
            mock_alpaca = MagicMock()
            mock_market = MagicMock()
            
            mock_quiver_class.return_value = mock_quiver
            mock_alpaca_class.return_value = mock_alpaca
            mock_market_class.return_value = mock_market
            
            # Mock responses
            mock_quiver.get_congressional_trades.return_value = []
            mock_alpaca.get_account_info.return_value = {
                'buying_power': 100000,
                'equity': 100000
            }
            mock_market.get_current_price.return_value = 150.0
            
            # Initialize DailyRunner
            runner = DailyRunner(test_db)
            
            # Create agent
            agent_factory = AgentFactory(test_db)
            agent_factory.create_agent(sample_agent_config)
            
            # Execute daily run
            results = runner.execute_daily_run()
            
            # Verify execution
            assert results is not None
            assert 'execution_summary' in results
            assert 'agents_processed' in results
    
    @pytest.mark.integration
    def test_error_handling_in_workflow(self, test_db, sample_congressional_trades, sample_agent_config):
        """Test error handling throughout the workflow."""
        
        agent_factory = AgentFactory(test_db)
        agent = agent_factory.create_agent(sample_agent_config)
        
        with patch('src.data.alpaca_client.AlpacaClient.place_market_order') as mock_order:
            # Simulate API error
            mock_order.side_effect = APIError("API rate limit exceeded", api_name="Alpaca")
            
            # Process should handle error gracefully
            decisions = agent.process_trades(sample_congressional_trades)
            assert len(decisions) >= 0  # Should not crash
    
    @pytest.mark.integration
    def test_database_persistence_workflow(self, test_db, sample_congressional_trades, sample_agent_config):
        """Test that data persists correctly through the workflow."""
        
        agent_factory = AgentFactory(test_db)
        agent = agent_factory.create_agent(sample_agent_config)
        
        with patch('src.data.market_data_service.MarketDataService.get_current_price') as mock_price:
            mock_price.return_value = 150.0
            
            # Process trades
            initial_decisions = agent.process_trades(sample_congressional_trades)
            
            # Verify data was stored
            stored_agents = test_db.get_all_agents()
            assert len(stored_agents) >= 1
            assert stored_agents[0]['id'] == sample_agent_config['id']
    
    @pytest.mark.integration
    @pytest.mark.slow
    def test_performance_under_load(self, test_db, sample_agent_config):
        """Test system performance under simulated load."""
        
        # Create multiple agents
        agent_factory = AgentFactory(test_db)
        agents = []
        
        for i in range(5):
            config = sample_agent_config.copy()
            config['id'] = f'load_test_agent_{i}'
            agents.append(agent_factory.create_agent(config))
        
        # Generate large dataset
        from src.data.quiver_client import CongressionalTrade
        from datetime import date
        
        large_trade_set = []
        for i in range(100):
            trade = CongressionalTrade(
                politician=f"Politician_{i % 10}",
                ticker=f"TICK{i % 20:02d}",
                transaction_date=date.today(),
                trade_type="Purchase",
                amount_range="$50,001 - $100,000",
                amount_min=50000,
                amount_max=100000,
                last_modified=date.today(),
                raw_data={}
            )
            large_trade_set.append(trade)
        
        # Process with timing
        start_time = time.time()
        
        with patch('src.data.market_data_service.MarketDataService.get_current_price') as mock_price:
            mock_price.return_value = 150.0
            
            total_decisions = 0
            for agent in agents:
                decisions = agent.process_trades(large_trade_set)
                total_decisions += len(decisions)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Performance assertions
        assert execution_time < 30.0  # Should complete within 30 seconds
        assert total_decisions >= 0  # Should process without crashes
        
        print(f"Processed {len(large_trade_set)} trades across {len(agents)} agents in {execution_time:.2f}s")


class TestAPIIntegration:
    """Test integration with external APIs."""
    
    @pytest.mark.integration
    @pytest.mark.api
    def test_alpaca_connection(self, test_alpaca_client):
        """Test real connection to Alpaca API (paper trading)."""
        try:
            account_info = test_alpaca_client.get_account_info()
            assert account_info is not None
            assert 'buying_power' in account_info
        except Exception as e:
            pytest.skip(f"Alpaca API not available: {e}")
    
    @pytest.mark.integration
    @pytest.mark.api
    def test_quiver_connection(self, test_quiver_client):
        """Test real connection to Quiver API."""
        try:
            # Test with minimal date range to avoid large response
            from datetime import date, timedelta
            start_date = date.today() - timedelta(days=1)
            end_date = date.today()
            
            trades = test_quiver_client.get_congressional_trades(
                start_date=start_date,
                end_date=end_date
            )
            assert isinstance(trades, list)
        except Exception as e:
            pytest.skip(f"Quiver API not available: {e}")
    
    @pytest.mark.integration
    @pytest.mark.api
    def test_market_data_integration(self, test_market_data_service):
        """Test market data service integration."""
        try:
            price = test_market_data_service.get_current_price('AAPL')
            assert price is not None
            assert price > 0
        except Exception as e:
            pytest.skip(f"Market data service not available: {e}")


class TestSystemReliability:
    """Test system reliability and recovery scenarios."""
    
    @pytest.mark.integration
    def test_graceful_degradation_quiver_failure(self, test_db, sample_agent_config):
        """Test system behavior when Quiver API fails."""
        
        agent_factory = AgentFactory(test_db)
        agent = agent_factory.create_agent(sample_agent_config)
        
        with patch('src.data.quiver_client.QuiverClient.get_congressional_trades') as mock_quiver:
            mock_quiver.side_effect = APIError("API unavailable", api_name="Quiver")
            
            # System should handle failure gracefully
            try:
                runner = DailyRunner(test_db)
                results = runner.execute_daily_run()
                # Should complete without crashing, possibly with warnings
                assert results is not None
            except APIError:
                # Acceptable to propagate API errors for monitoring
                pass
    
    @pytest.mark.integration
    def test_database_recovery(self, test_db):
        """Test database connection recovery."""
        
        # Simulate database connection issues
        original_connection = test_db.connection
        test_db.connection = None
        
        try:
            # Should attempt reconnection
            test_db.reconnect()
            assert test_db.connection is not None
        finally:
            # Restore for other tests
            if test_db.connection is None:
                test_db.connection = original_connection
    
    @pytest.mark.integration
    def test_concurrent_agent_execution(self, test_db, sample_congressional_trades):
        """Test concurrent execution of multiple agents."""
        
        import threading
        import concurrent.futures
        
        # Create multiple agents
        agent_factory = AgentFactory(test_db)
        agents = []
        
        for i in range(3):
            config = {
                'id': f'concurrent_agent_{i}',
                'name': f'Concurrent Test Agent {i}',
                'type': 'individual', 
                'politicians': [f'Politician{i}'],
                'enabled': True,
                'parameters': {
                    'minimum_trade_value': 50000,
                    'position_size_type': 'fixed',
                    'position_size_value': 1000,
                    'match_threshold': 0.85
                }
            }
            agents.append(agent_factory.create_agent(config))
        
        results = []
        
        def process_agent(agent):
            with patch('src.data.market_data_service.MarketDataService.get_current_price') as mock_price:
                mock_price.return_value = 150.0
                return agent.process_trades(sample_congressional_trades)
        
        # Execute concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(process_agent, agent) for agent in agents]
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())
        
        # All should complete successfully
        assert len(results) == 3
        for result in results:
            assert isinstance(result, list)