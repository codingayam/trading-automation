"""
Pytest configuration and shared fixtures for trading automation tests.
"""
import pytest
import os
import tempfile
import shutil
from unittest.mock import Mock, patch
from pathlib import Path


@pytest.fixture(scope='session')
def test_data_dir():
    """Create a temporary directory for test data."""
    temp_dir = tempfile.mkdtemp(prefix='trading_automation_test_')
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    mock_settings = Mock()
    
    # Database settings
    mock_settings.database.full_path = ':memory:'  # Use in-memory SQLite for tests
    mock_settings.database.backup_enabled = False
    mock_settings.database.backup_retention_days = 7
    
    # API settings
    mock_settings.api.quiver_api_key = 'test_quiver_key'
    mock_settings.api.alpaca_api_key = 'test_alpaca_key'
    mock_settings.api.alpaca_secret_key = 'test_alpaca_secret'
    mock_settings.api.alpaca_paper_trading = True
    mock_settings.api.alpaca_base_url = 'https://paper-api.alpaca.markets'
    mock_settings.api.rate_limit_per_minute = 60
    mock_settings.api.timeout_seconds = 30
    mock_settings.api.retry_max_attempts = 3
    mock_settings.api.retry_backoff_factor = 2.0
    
    # Trading settings
    mock_settings.trading.minimum_amount = 100.0
    mock_settings.trading.size_type = 'fixed'
    mock_settings.trading.politician_match_threshold = 0.85
    mock_settings.trading.minimum_congress_trade_value = 50000
    
    # Scheduling settings
    mock_settings.scheduling.daily_execution_time = '21:30'
    mock_settings.scheduling.timezone = 'US/Eastern'
    mock_settings.scheduling.market_hours_start = '09:30'
    mock_settings.scheduling.market_hours_end = '16:00'
    
    # Dashboard settings
    mock_settings.dashboard.host = '0.0.0.0'
    mock_settings.dashboard.port = 5000
    mock_settings.dashboard.debug = True
    
    # Logging settings
    mock_settings.logging.level = 'DEBUG'
    mock_settings.logging.retention_days = 7
    mock_settings.logging.full_path = '/tmp/test_logs'
    
    # Environment flags
    mock_settings.is_development = True
    mock_settings.is_production = False
    
    # Agent configuration
    mock_settings.agents = {
        'agents': [
            {
                'id': 'test_agent',
                'name': 'Test Agent',
                'type': 'individual',
                'politicians': ['Test Politician'],
                'enabled': True
            }
        ]
    }
    
    mock_settings.get_enabled_agents.return_value = mock_settings.agents['agents']
    mock_settings.get_agent_by_id.return_value = mock_settings.agents['agents'][0]
    
    return mock_settings


@pytest.fixture
def mock_database():
    """Mock database for testing."""
    mock_db = Mock()
    
    # Common database methods
    mock_db.execute_query.return_value = []
    mock_db.execute_single.return_value = None
    mock_db.execute_modify.return_value = 1
    mock_db.insert_trade.return_value = 1
    mock_db.insert_position.return_value = None
    mock_db.insert_daily_performance.return_value = None
    
    # Transaction context manager
    mock_db.transaction.return_value.__enter__ = Mock()
    mock_db.transaction.return_value.__exit__ = Mock(return_value=None)
    
    return mock_db


@pytest.fixture
def mock_quiver_client():
    """Mock Quiver API client for testing."""
    mock_client = Mock()
    mock_client.api_key = 'test_key'
    mock_client.test_connection.return_value = True
    mock_client.get_congressional_trades.return_value = []
    mock_client.find_matching_politicians.return_value = []
    return mock_client


@pytest.fixture
def mock_alpaca_client():
    """Mock Alpaca API client for testing."""
    mock_client = Mock()
    mock_client.api_key = 'test_key'
    mock_client.secret_key = 'test_secret'
    mock_client.paper = True
    mock_client.test_connection.return_value = True
    mock_client.get_account_info.return_value = Mock(
        buying_power=10000.0,
        portfolio_value=15000.0,
        cash=5000.0
    )
    mock_client.get_all_positions.return_value = []
    mock_client.validate_ticker.return_value = True
    mock_client.get_current_price.return_value = 150.0
    mock_client.place_market_order.return_value = Mock(
        order_id='test_order',
        status='filled'
    )
    return mock_client


@pytest.fixture
def mock_market_data_service():
    """Mock Market Data Service for testing."""
    mock_service = Mock()
    mock_service.get_current_price.return_value = 150.0
    mock_service.get_price_data.return_value = Mock(
        ticker='AAPL',
        current_price=150.0,
        open_price=148.0
    )
    mock_service.validate_ticker.return_value = True
    mock_service.test_connection.return_value = True
    return mock_service


@pytest.fixture(autouse=True)
def mock_logging():
    """Mock logging to prevent log output during tests."""
    with patch('src.utils.logging.get_logger') as mock_get_logger:
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        yield mock_logger


@pytest.fixture
def suppress_requests():
    """Suppress actual HTTP requests during tests."""
    with patch('requests.Session.get') as mock_get, \
         patch('requests.Session.post') as mock_post, \
         patch('yfinance.Ticker') as mock_ticker, \
         patch('alpaca.trading.TradingClient') as mock_trading, \
         patch('alpaca.data.StockHistoricalDataClient') as mock_data:
        
        # Default successful responses
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_get.return_value = mock_response
        mock_post.return_value = mock_response
        
        yield {
            'get': mock_get,
            'post': mock_post,
            'ticker': mock_ticker,
            'trading': mock_trading,
            'data': mock_data
        }


@pytest.fixture
def sample_env_vars():
    """Sample environment variables for testing."""
    return {
        'QUIVER_API_KEY': 'test_quiver_key',
        'ALPACA_API_KEY': 'test_alpaca_key',
        'ALPACA_SECRET_KEY': 'test_alpaca_secret',
        'ALPACA_PAPER_TRADING': 'true',
        'DATABASE_PATH': ':memory:',
        'LOG_LEVEL': 'DEBUG',
        'ENVIRONMENT': 'testing'
    }


@pytest.fixture
def with_env_vars(sample_env_vars):
    """Context manager for setting environment variables during test."""
    old_environ = dict(os.environ)
    os.environ.update(sample_env_vars)
    yield
    os.environ.clear()
    os.environ.update(old_environ)


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "external_api: mark test as requiring external API access"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on file/function names."""
    for item in items:
        # Add unit test marker for test files in unit directories or with test_ prefix
        if "unit" in str(item.fspath) or item.name.startswith("test_"):
            item.add_marker(pytest.mark.unit)
        
        # Add integration marker for integration test files
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        
        # Add slow marker for tests that might be slow
        if any(keyword in item.name.lower() for keyword in ["batch", "large", "performance"]):
            item.add_marker(pytest.mark.slow)
        
        # Add external_api marker for tests that use external APIs
        if any(keyword in str(item.fspath).lower() for keyword in ["quiver", "alpaca", "yfinance"]):
            item.add_marker(pytest.mark.external_api)