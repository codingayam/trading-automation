#!/usr/bin/env python3
"""
Dashboard Integration Testing Script
Tests the complete dashboard functionality including API endpoints, 
data processing, error handling, and frontend integration.
"""
import sys
import os
import json
import time
import asyncio
from datetime import datetime, date
from typing import Dict, Any, List
import unittest
from unittest.mock import Mock, patch

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config.settings import settings
from src.data.database import DatabaseManager, initialize_database
from src.data.market_data_service import MarketDataService
from src.dashboard.api import create_app
from src.utils.logging import get_logger

logger = get_logger(__name__)

class DashboardIntegrationTest:
    """Integration test suite for the dashboard system."""
    
    def __init__(self):
        self.app = None
        self.client = None
        self.db = None
        self.market_data = None
        self.test_results = []
        
    def setup(self):
        """Set up test environment."""
        logger.info("Setting up dashboard integration tests...")
        
        # Initialize database
        self.db = DatabaseManager()
        
        # Initialize market data service
        self.market_data = MarketDataService()
        
        # Create Flask test client
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        
        # Insert test data
        self.create_test_data()
        
        logger.info("Test setup completed")
    
    def create_test_data(self):
        """Create test data for dashboard testing."""
        logger.info("Creating test data...")
        
        # Test agent positions
        test_positions = [
            {
                'agent_id': 'josh_gottheimer',
                'ticker': 'AAPL',
                'quantity': 100.0,
                'avg_cost': 150.0,
                'current_price': 160.0,
                'market_value': 16000.0,
                'unrealized_pnl': 1000.0
            },
            {
                'agent_id': 'josh_gottheimer',
                'ticker': 'MSFT',
                'quantity': 50.0,
                'avg_cost': 300.0,
                'current_price': 320.0,
                'market_value': 16000.0,
                'unrealized_pnl': 1000.0
            },
            {
                'agent_id': 'nancy_pelosi',
                'ticker': 'TSLA',
                'quantity': 25.0,
                'avg_cost': 800.0,
                'current_price': 850.0,
                'market_value': 21250.0,
                'unrealized_pnl': 1250.0
            }
        ]
        
        for position in test_positions:
            try:
                self.db.insert_position(position)
            except Exception as e:
                logger.warning(f"Error inserting test position: {e}")
        
        # Test performance data
        test_performance = [
            {
                'agent_id': 'josh_gottheimer',
                'date': date.today(),
                'total_value': 32000.0,
                'daily_return_pct': 2.5,
                'total_return_pct': 15.0
            },
            {
                'agent_id': 'nancy_pelosi',
                'date': date.today(),
                'total_value': 21250.0,
                'daily_return_pct': 1.8,
                'total_return_pct': 8.5
            }
        ]
        
        for perf in test_performance:
            try:
                self.db.insert_daily_performance(perf)
            except Exception as e:
                logger.warning(f"Error inserting test performance: {e}")
        
        logger.info("Test data created successfully")
    
    def run_all_tests(self):
        """Run all dashboard integration tests."""
        logger.info("Starting dashboard integration tests...")
        
        tests = [
            self.test_health_endpoint,
            self.test_system_status_endpoint,
            self.test_agents_overview_endpoint,
            self.test_agent_detail_endpoint,
            self.test_agent_positions_endpoint,
            self.test_agent_performance_endpoint,
            self.test_dashboard_ui_routes,
            self.test_error_handling,
            self.test_data_formatting,
            self.test_cache_functionality,
            self.test_concurrent_requests,
            self.test_frontend_integration
        ]
        
        passed = 0
        total = len(tests)
        
        for test in tests:
            try:
                logger.info(f"Running test: {test.__name__}")
                result = test()
                if result:
                    passed += 1
                    logger.info(f"✓ {test.__name__} PASSED")
                else:
                    logger.error(f"✗ {test.__name__} FAILED")
            except Exception as e:
                logger.error(f"✗ {test.__name__} ERROR: {e}")
        
        logger.info(f"Tests completed: {passed}/{total} passed")
        return passed == total
    
    def test_health_endpoint(self) -> bool:
        """Test health check endpoint."""
        try:
            response = self.client.get('/api/health')
            
            if response.status_code != 200:
                logger.error(f"Health check failed with status {response.status_code}")
                return False
            
            data = response.get_json()
            
            required_fields = ['status', 'timestamp', 'components', 'system_info']
            for field in required_fields:
                if field not in data:
                    logger.error(f"Health response missing field: {field}")
                    return False
            
            return True
        except Exception as e:
            logger.error(f"Health endpoint test error: {e}")
            return False
    
    def test_system_status_endpoint(self) -> bool:
        """Test system status endpoint."""
        try:
            response = self.client.get('/api/system/status')
            
            if response.status_code != 200:
                logger.error(f"System status failed with status {response.status_code}")
                return False
            
            data = response.get_json()
            
            required_fields = ['system_status', 'timestamp', 'market']
            for field in required_fields:
                if field not in data:
                    logger.error(f"System status response missing field: {field}")
                    return False
            
            return True
        except Exception as e:
            logger.error(f"System status endpoint test error: {e}")
            return False
    
    def test_agents_overview_endpoint(self) -> bool:
        """Test agents overview endpoint."""
        try:
            response = self.client.get('/api/agents')
            
            if response.status_code != 200:
                logger.error(f"Agents overview failed with status {response.status_code}")
                return False
            
            data = response.get_json()
            
            if 'agents' not in data:
                logger.error("Agents response missing 'agents' field")
                return False
            
            agents = data['agents']
            if not isinstance(agents, list):
                logger.error("Agents field is not a list")
                return False
            
            # Check agent data structure
            if agents:
                agent = agents[0]
                required_fields = ['agent_id', 'name', 'type', 'total_value']
                for field in required_fields:
                    if field not in agent:
                        logger.error(f"Agent data missing field: {field}")
                        return False
            
            return True
        except Exception as e:
            logger.error(f"Agents overview endpoint test error: {e}")
            return False
    
    def test_agent_detail_endpoint(self) -> bool:
        """Test individual agent detail endpoint."""
        try:
            # Test with valid agent
            response = self.client.get('/api/agents/josh_gottheimer')
            
            if response.status_code != 200:
                logger.error(f"Agent detail failed with status {response.status_code}")
                return False
            
            data = response.get_json()
            
            if 'agent' not in data:
                logger.error("Agent detail response missing 'agent' field")
                return False
            
            agent = data['agent']
            required_fields = ['agent_id', 'name', 'positions', 'total_value']
            for field in required_fields:
                if field not in agent:
                    logger.error(f"Agent detail missing field: {field}")
                    return False
            
            # Test with invalid agent (should return 404)
            response = self.client.get('/api/agents/nonexistent_agent')
            if response.status_code != 404:
                logger.error(f"Expected 404 for invalid agent, got {response.status_code}")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Agent detail endpoint test error: {e}")
            return False
    
    def test_agent_positions_endpoint(self) -> bool:
        """Test agent positions endpoint."""
        try:
            response = self.client.get('/api/agents/josh_gottheimer/positions')
            
            if response.status_code != 200:
                logger.error(f"Agent positions failed with status {response.status_code}")
                return False
            
            data = response.get_json()
            
            required_fields = ['agent_id', 'positions', 'position_count']
            for field in required_fields:
                if field not in data:
                    logger.error(f"Positions response missing field: {field}")
                    return False
            
            return True
        except Exception as e:
            logger.error(f"Agent positions endpoint test error: {e}")
            return False
    
    def test_agent_performance_endpoint(self) -> bool:
        """Test agent performance endpoint."""
        try:
            response = self.client.get('/api/agents/josh_gottheimer/performance')
            
            if response.status_code != 200:
                logger.error(f"Agent performance failed with status {response.status_code}")
                return False
            
            data = response.get_json()
            
            required_fields = ['agent_id', 'performance_history']
            for field in required_fields:
                if field not in data:
                    logger.error(f"Performance response missing field: {field}")
                    return False
            
            # Test with days parameter
            response = self.client.get('/api/agents/josh_gottheimer/performance?days=7')
            if response.status_code != 200:
                logger.error("Performance endpoint failed with days parameter")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Agent performance endpoint test error: {e}")
            return False
    
    def test_dashboard_ui_routes(self) -> bool:
        """Test dashboard UI routes."""
        try:
            # Test overview page
            response = self.client.get('/')
            if response.status_code != 200:
                logger.error(f"Dashboard overview page failed with status {response.status_code}")
                return False
            
            # Test agent detail page
            response = self.client.get('/agent/josh_gottheimer')
            if response.status_code != 200:
                logger.error(f"Agent detail page failed with status {response.status_code}")
                return False
            
            # Test invalid agent page (should return 404)
            response = self.client.get('/agent/nonexistent_agent')
            if response.status_code != 404:
                logger.error(f"Expected 404 for invalid agent page, got {response.status_code}")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Dashboard UI routes test error: {e}")
            return False
    
    def test_error_handling(self) -> bool:
        """Test error handling and edge cases."""
        try:
            # Test invalid endpoint
            response = self.client.get('/api/invalid_endpoint')
            if response.status_code != 404:
                logger.error(f"Expected 404 for invalid endpoint, got {response.status_code}")
                return False
            
            # Test malformed requests
            response = self.client.post('/api/agents')  # Should not accept POST
            if response.status_code not in [405, 404]:
                logger.error(f"Expected 405/404 for invalid method, got {response.status_code}")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Error handling test error: {e}")
            return False
    
    def test_data_formatting(self) -> bool:
        """Test data formatting and calculations."""
        try:
            response = self.client.get('/api/agents')
            
            if response.status_code != 200:
                return False
            
            data = response.get_json()
            agents = data.get('agents', [])
            
            for agent in agents:
                # Check that formatted fields exist
                formatted_fields = ['total_value_formatted', 'daily_return_formatted', 'total_return_formatted']
                for field in formatted_fields:
                    if field not in agent:
                        logger.error(f"Agent missing formatted field: {field}")
                        return False
                
                # Check formatting
                total_value_formatted = agent.get('total_value_formatted', '')
                if not total_value_formatted.startswith('$'):
                    logger.error("Total value formatting should start with $")
                    return False
                
                daily_return_formatted = agent.get('daily_return_formatted', '')
                if daily_return_formatted and not daily_return_formatted.endswith('%'):
                    logger.error("Return formatting should end with %")
                    return False
            
            return True
        except Exception as e:
            logger.error(f"Data formatting test error: {e}")
            return False
    
    def test_cache_functionality(self) -> bool:
        """Test API caching functionality."""
        try:
            # Make first request
            start_time = time.time()
            response1 = self.client.get('/api/agents')
            first_request_time = time.time() - start_time
            
            if response1.status_code != 200:
                return False
            
            # Make second request (should be cached)
            start_time = time.time()
            response2 = self.client.get('/api/agents')
            second_request_time = time.time() - start_time
            
            if response2.status_code != 200:
                return False
            
            # Second request should be faster (cached)
            if second_request_time >= first_request_time:
                logger.warning("Second request not faster - caching may not be working")
            
            # Data should be the same
            if response1.get_json() != response2.get_json():
                logger.error("Cached response differs from original")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Cache functionality test error: {e}")
            return False
    
    def test_concurrent_requests(self) -> bool:
        """Test handling of concurrent requests."""
        try:
            import threading
            import queue
            
            results = queue.Queue()
            threads = []
            
            def make_request():
                try:
                    response = self.client.get('/api/agents')
                    results.put(response.status_code)
                except Exception as e:
                    results.put(str(e))
            
            # Create 5 concurrent requests
            for i in range(5):
                thread = threading.Thread(target=make_request)
                threads.append(thread)
                thread.start()
            
            # Wait for all threads to complete
            for thread in threads:
                thread.join(timeout=10)
            
            # Check results
            success_count = 0
            while not results.empty():
                result = results.get()
                if result == 200:
                    success_count += 1
            
            if success_count < 3:  # At least 3 out of 5 should succeed
                logger.error(f"Only {success_count}/5 concurrent requests succeeded")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Concurrent requests test error: {e}")
            return False
    
    def test_frontend_integration(self) -> bool:
        """Test frontend integration points."""
        try:
            # Check that CSS and JS files are accessible
            response = self.client.get('/static/css/dashboard.css')
            if response.status_code != 200:
                logger.error("CSS file not accessible")
                return False
            
            response = self.client.get('/static/js/overview.js')
            if response.status_code != 200:
                logger.error("Overview JS file not accessible")
                return False
            
            response = self.client.get('/static/js/agent_detail.js')
            if response.status_code != 200:
                logger.error("Agent detail JS file not accessible")
                return False
            
            # Check that HTML templates render properly
            response = self.client.get('/')
            if response.status_code != 200:
                return False
            
            html_content = response.get_data(as_text=True)
            
            # Check for key HTML elements
            required_elements = [
                'agents-table',
                'loading-container', 
                'error-container',
                'market-status'
            ]
            
            for element in required_elements:
                if element not in html_content:
                    logger.error(f"Required HTML element not found: {element}")
                    return False
            
            return True
        except Exception as e:
            logger.error(f"Frontend integration test error: {e}")
            return False
    
    def cleanup(self):
        """Clean up test environment."""
        logger.info("Cleaning up test environment...")
        
        try:
            # Clear test data
            self.db.execute_modify("DELETE FROM agent_positions WHERE agent_id IN ('josh_gottheimer', 'nancy_pelosi')")
            self.db.execute_modify("DELETE FROM daily_performance WHERE agent_id IN ('josh_gottheimer', 'nancy_pelosi')")
            
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
        
        logger.info("Cleanup completed")

def main():
    """Run dashboard integration tests."""
    print("=" * 60)
    print("DASHBOARD INTEGRATION TESTING")
    print("=" * 60)
    
    # Initialize database first
    if not initialize_database():
        print("❌ Database initialization failed")
        return False
    
    tester = DashboardIntegrationTest()
    
    try:
        tester.setup()
        success = tester.run_all_tests()
        
        if success:
            print("\n✅ All dashboard integration tests passed!")
            print("Dashboard is ready for production use.")
        else:
            print("\n❌ Some dashboard integration tests failed.")
            print("Please check the logs and fix issues before deployment.")
        
        return success
        
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        print(f"\n❌ Test execution failed: {e}")
        return False
    
    finally:
        tester.cleanup()

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)