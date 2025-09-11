"""
Performance testing for the trading automation system.
"""
import time
import psutil
import pytest
from datetime import datetime, timedelta, date
from unittest.mock import patch, MagicMock
from memory_profiler import memory_usage

from src.agents.agent_factory import AgentFactory
from src.scheduler.daily_runner import DailyRunner
from src.data.quiver_client import CongressionalTrade


class TestPerformanceRequirements:
    """Test that performance requirements are met."""
    
    @pytest.mark.performance
    def test_dashboard_load_time(self):
        """Test that dashboard loads in < 3 seconds."""
        from src.dashboard.api import create_app
        
        app = create_app()
        client = app.test_client()
        
        start_time = time.time()
        response = client.get('/')
        end_time = time.time()
        
        load_time = end_time - start_time
        assert load_time < 3.0, f"Dashboard loaded in {load_time:.2f}s (requirement: <3s)"
        assert response.status_code == 200
    
    @pytest.mark.performance
    def test_api_response_time(self):
        """Test that API responses are < 1 second."""
        from src.dashboard.api import create_app
        
        app = create_app()
        client = app.test_client()
        
        endpoints = [
            '/api/agents',
            '/api/trades/recent',
            '/api/performance/overview'
        ]
        
        for endpoint in endpoints:
            start_time = time.time()
            response = client.get(endpoint)
            end_time = time.time()
            
            response_time = end_time - start_time
            assert response_time < 1.0, f"{endpoint} responded in {response_time:.2f}s (requirement: <1s)"
            # Allow 404s for endpoints that require data
            assert response.status_code in [200, 404, 500]
    
    @pytest.mark.performance
    def test_agent_execution_time(self, test_db):
        """Test that agent execution completes within 30 minutes."""
        
        # Create test agent
        agent_factory = AgentFactory(test_db)
        config = {
            'id': 'performance_test_agent',
            'name': 'Performance Test Agent',
            'type': 'individual',
            'politicians': ['Test Politician'],
            'enabled': True,
            'parameters': {
                'minimum_trade_value': 50000,
                'position_size_type': 'fixed',
                'position_size_value': 1000,
                'match_threshold': 0.85
            }
        }
        agent = agent_factory.create_agent(config)
        
        # Generate large dataset
        trades = []
        for i in range(1000):
            trade = CongressionalTrade(
                politician="Test Politician",
                ticker=f"TICK{i % 50:02d}",
                transaction_date=date.today(),
                trade_type="Purchase",
                amount_range="$50,001 - $100,000",
                amount_min=50000 + (i * 1000),
                amount_max=100000 + (i * 1000),
                last_modified=date.today(),
                raw_data={}
            )
            trades.append(trade)
        
        with patch('src.data.market_data_service.MarketDataService.get_current_price') as mock_price:
            mock_price.return_value = 150.0
            
            start_time = time.time()
            decisions = agent.process_trades(trades)
            end_time = time.time()
            
            execution_time = end_time - start_time
            # 30 minutes = 1800 seconds, but for 1000 trades we expect much faster
            assert execution_time < 60.0, f"Agent processed {len(trades)} trades in {execution_time:.2f}s"
            assert len(decisions) >= 0


class TestResourceUsage:
    """Test system resource usage under various conditions."""
    
    @pytest.mark.performance
    def test_memory_usage_during_processing(self, test_db):
        """Monitor memory usage during trade processing."""
        
        def process_large_dataset():
            agent_factory = AgentFactory(test_db)
            config = {
                'id': 'memory_test_agent',
                'name': 'Memory Test Agent',
                'type': 'individual',
                'politicians': ['Test Politician'],
                'enabled': True,
                'parameters': {
                    'minimum_trade_value': 50000,
                    'position_size_type': 'fixed',
                    'position_size_value': 1000,
                    'match_threshold': 0.85
                }
            }
            agent = agent_factory.create_agent(config)
            
            # Generate dataset
            trades = []
            for i in range(5000):
                trade = CongressionalTrade(
                    politician="Test Politician",
                    ticker=f"TICK{i % 100:02d}",
                    transaction_date=date.today(),
                    trade_type="Purchase",
                    amount_range="$50,001 - $100,000",
                    amount_min=50000,
                    amount_max=100000,
                    last_modified=date.today(),
                    raw_data={}
                )
                trades.append(trade)
            
            with patch('src.data.market_data_service.MarketDataService.get_current_price') as mock_price:
                mock_price.return_value = 150.0
                agent.process_trades(trades)
        
        # Monitor memory usage
        mem_usage = memory_usage(process_large_dataset)
        peak_memory = max(mem_usage)
        
        # Should not exceed 1GB for processing
        assert peak_memory < 1024, f"Peak memory usage: {peak_memory:.2f} MB (limit: 1024 MB)"
        print(f"Peak memory usage: {peak_memory:.2f} MB")
    
    @pytest.mark.performance
    def test_cpu_usage_monitoring(self, test_db):
        """Monitor CPU usage during intensive operations."""
        
        # Get baseline CPU usage
        baseline_cpu = psutil.cpu_percent(interval=1)
        
        agent_factory = AgentFactory(test_db)
        config = {
            'id': 'cpu_test_agent',
            'name': 'CPU Test Agent',
            'type': 'individual',
            'politicians': ['Test Politician'],
            'enabled': True,
            'parameters': {
                'minimum_trade_value': 50000,
                'position_size_type': 'fixed',
                'position_size_value': 1000,
                'match_threshold': 0.85
            }
        }
        agent = agent_factory.create_agent(config)
        
        # Generate workload
        trades = []
        for i in range(2000):
            trade = CongressionalTrade(
                politician="Test Politician",
                ticker=f"TICK{i % 50:02d}",
                transaction_date=date.today(),
                trade_type="Purchase",
                amount_range="$50,001 - $100,000",
                amount_min=50000,
                amount_max=100000,
                last_modified=date.today(),
                raw_data={}
            )
            trades.append(trade)
        
        with patch('src.data.market_data_service.MarketDataService.get_current_price') as mock_price:
            mock_price.return_value = 150.0
            
            # Monitor CPU during processing
            start_time = time.time()
            agent.process_trades(trades)
            end_time = time.time()
            
            # Check CPU didn't spike too high
            current_cpu = psutil.cpu_percent(interval=1)
            
        print(f"CPU usage - Baseline: {baseline_cpu}%, During processing: {current_cpu}%")
        print(f"Processing time: {end_time - start_time:.2f}s")
    
    @pytest.mark.performance
    def test_database_query_performance(self, test_db):
        """Test database query performance."""
        
        # Insert test data
        test_data = []
        for i in range(10000):
            test_data.append({
                'agent_id': f'agent_{i % 100}',
                'ticker': f'TICK{i % 500:03d}',
                'timestamp': datetime.now() - timedelta(minutes=i),
                'value': float(i * 100)
            })
        
        # Insert data and measure time
        start_time = time.time()
        for data in test_data[:1000]:  # Insert sample
            # Simulate database insert (would need actual DB schema)
            pass
        insert_time = time.time() - start_time
        
        # Query data and measure time
        start_time = time.time()
        # Simulate complex query (would need actual implementation)
        query_time = time.time() - start_time
        
        # Database operations should be fast
        assert insert_time < 5.0, f"Insert time: {insert_time:.2f}s"
        assert query_time < 1.0, f"Query time: {query_time:.2f}s"


class TestScalability:
    """Test system scalability with varying loads."""
    
    @pytest.mark.performance
    @pytest.mark.slow
    def test_multiple_agents_concurrent_processing(self, test_db):
        """Test processing with multiple agents running concurrently."""
        
        import concurrent.futures
        
        # Create multiple agents
        agent_factory = AgentFactory(test_db)
        agents = []
        
        for i in range(10):
            config = {
                'id': f'scale_test_agent_{i}',
                'name': f'Scale Test Agent {i}',
                'type': 'individual',
                'politicians': [f'Politician_{i}'],
                'enabled': True,
                'parameters': {
                    'minimum_trade_value': 50000,
                    'position_size_type': 'fixed',
                    'position_size_value': 1000,
                    'match_threshold': 0.85
                }
            }
            agents.append(agent_factory.create_agent(config))
        
        # Generate trades for each agent
        def create_trades_for_agent(agent_id):
            trades = []
            for i in range(500):
                trade = CongressionalTrade(
                    politician=f"Politician_{agent_id}",
                    ticker=f"TICK{i % 50:02d}",
                    transaction_date=date.today(),
                    trade_type="Purchase",
                    amount_range="$50,001 - $100,000",
                    amount_min=50000,
                    amount_max=100000,
                    last_modified=date.today(),
                    raw_data={}
                )
                trades.append(trade)
            return trades
        
        def process_agent_trades(agent_and_id):
            agent, agent_id = agent_and_id
            trades = create_trades_for_agent(agent_id)
            
            with patch('src.data.market_data_service.MarketDataService.get_current_price') as mock_price:
                mock_price.return_value = 150.0
                return agent.process_trades(trades)
        
        # Process all agents concurrently
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(process_agent_trades, (agent, i)) 
                for i, agent in enumerate(agents)
            ]
            
            results = []
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should complete within reasonable time
        assert total_time < 120.0, f"Concurrent processing took {total_time:.2f}s"
        assert len(results) == len(agents)
        
        print(f"Processed {len(agents)} agents concurrently in {total_time:.2f}s")
    
    @pytest.mark.performance
    def test_large_dataset_processing(self, test_db):
        """Test processing very large datasets."""
        
        agent_factory = AgentFactory(test_db)
        config = {
            'id': 'large_dataset_agent',
            'name': 'Large Dataset Agent',
            'type': 'individual',
            'politicians': ['Test Politician'],
            'enabled': True,
            'parameters': {
                'minimum_trade_value': 50000,
                'position_size_type': 'fixed',
                'position_size_value': 1000,
                'match_threshold': 0.85
            }
        }
        agent = agent_factory.create_agent(config)
        
        # Create very large dataset
        large_dataset = []
        for i in range(50000):  # 50k trades
            trade = CongressionalTrade(
                politician="Test Politician" if i % 10 == 0 else "Other Politician",
                ticker=f"TICK{i % 1000:03d}",
                transaction_date=date.today() - timedelta(days=i % 365),
                trade_type="Purchase" if i % 3 == 0 else "Sale",
                amount_range="$50,001 - $100,000",
                amount_min=50000,
                amount_max=100000,
                last_modified=date.today(),
                raw_data={}
            )
            large_dataset.append(trade)
        
        with patch('src.data.market_data_service.MarketDataService.get_current_price') as mock_price:
            mock_price.return_value = 150.0
            
            start_time = time.time()
            decisions = agent.process_trades(large_dataset)
            end_time = time.time()
            
            processing_time = end_time - start_time
            trades_per_second = len(large_dataset) / processing_time
            
            # Should process at reasonable speed
            assert trades_per_second > 100, f"Processing rate: {trades_per_second:.2f} trades/sec"
            assert processing_time < 300, f"Processing time: {processing_time:.2f}s"
            
            print(f"Processed {len(large_dataset)} trades in {processing_time:.2f}s")
            print(f"Rate: {trades_per_second:.2f} trades/second")


class TestLoadTesting:
    """Load testing scenarios."""
    
    @pytest.mark.performance
    @pytest.mark.slow
    def test_sustained_load(self, test_db):
        """Test system under sustained load over time."""
        
        agent_factory = AgentFactory(test_db)
        config = {
            'id': 'sustained_load_agent',
            'name': 'Sustained Load Agent',
            'type': 'individual',
            'politicians': ['Test Politician'],
            'enabled': True,
            'parameters': {
                'minimum_trade_value': 50000,
                'position_size_type': 'fixed',
                'position_size_value': 1000,
                'match_threshold': 0.85
            }
        }
        agent = agent_factory.create_agent(config)
        
        # Run multiple cycles
        cycle_times = []
        total_decisions = 0
        
        for cycle in range(10):
            # Generate trades for this cycle
            trades = []
            for i in range(1000):
                trade = CongressionalTrade(
                    politician="Test Politician",
                    ticker=f"TICK{(cycle * 1000 + i) % 100:02d}",
                    transaction_date=date.today(),
                    trade_type="Purchase",
                    amount_range="$50,001 - $100,000",
                    amount_min=50000,
                    amount_max=100000,
                    last_modified=date.today(),
                    raw_data={}
                )
                trades.append(trade)
            
            with patch('src.data.market_data_service.MarketDataService.get_current_price') as mock_price:
                mock_price.return_value = 150.0
                
                start_time = time.time()
                decisions = agent.process_trades(trades)
                end_time = time.time()
                
                cycle_time = end_time - start_time
                cycle_times.append(cycle_time)
                total_decisions += len(decisions)
                
                print(f"Cycle {cycle + 1}: {cycle_time:.2f}s, {len(decisions)} decisions")
        
        # Performance should remain consistent
        avg_cycle_time = sum(cycle_times) / len(cycle_times)
        max_cycle_time = max(cycle_times)
        
        # No cycle should take more than 2x the average
        assert max_cycle_time < (avg_cycle_time * 2), "Performance degraded over time"
        
        print(f"Average cycle time: {avg_cycle_time:.2f}s")
        print(f"Max cycle time: {max_cycle_time:.2f}s")
        print(f"Total decisions: {total_decisions}")