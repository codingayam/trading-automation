"""
Integration test configuration and fixtures.
"""
import os
import pytest
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from config.settings import settings
from src.data.database import DatabaseManager
from src.data.alpaca_client import AlpacaClient
from src.data.quiver_client import QuiverClient
from src.data.market_data_service import MarketDataService


@pytest.fixture(scope="session")
def test_db():
    """Create a temporary test database."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
        test_db_path = tmp_file.name
    
    # Create test database
    os.environ['DATABASE_PATH'] = test_db_path
    db_manager = DatabaseManager()
    db_manager.initialize_database()
    
    yield db_manager
    
    # Cleanup
    db_manager.close()
    if os.path.exists(test_db_path):
        os.unlink(test_db_path)


@pytest.fixture(scope="session")
def test_alpaca_client():
    """Create Alpaca client for testing (paper trading)."""
    # Ensure we're using paper trading
    original_paper = os.environ.get('ALPACA_PAPER')
    os.environ['ALPACA_PAPER'] = 'true'
    
    client = AlpacaClient()
    yield client
    
    # Restore original setting
    if original_paper is not None:
        os.environ['ALPACA_PAPER'] = original_paper


@pytest.fixture(scope="session") 
def test_quiver_client():
    """Create Quiver client for testing."""
    return QuiverClient()


@pytest.fixture(scope="session")
def test_market_data_service():
    """Create market data service for testing."""
    return MarketDataService()


@pytest.fixture
def sample_congressional_trades():
    """Generate sample congressional trade data."""
    from src.data.quiver_client import CongressionalTrade
    from datetime import date
    
    trades = [
        CongressionalTrade(
            politician="Nancy Pelosi",
            ticker="AAPL",
            transaction_date=date.today() - timedelta(days=1),
            trade_type="Purchase",
            amount_range="$50,001 - $100,000",
            amount_min=50000,
            amount_max=100000,
            last_modified=date.today(),
            raw_data={}
        ),
        CongressionalTrade(
            politician="Paul Pelosi",
            ticker="TSLA", 
            transaction_date=date.today() - timedelta(days=2),
            trade_type="Sale",
            amount_range="$100,001 - $250,000",
            amount_min=100000,
            amount_max=250000,
            last_modified=date.today(),
            raw_data={}
        ),
        CongressionalTrade(
            politician="Katherine Clark",
            ticker="MSFT",
            transaction_date=date.today() - timedelta(days=3),
            trade_type="Purchase",
            amount_range="$15,001 - $50,000",
            amount_min=15000,
            amount_max=50000,
            last_modified=date.today(),
            raw_data={}
        )
    ]
    return trades


@pytest.fixture
def sample_agent_config():
    """Sample agent configuration for testing."""
    return {
        'id': 'test_integration_agent',
        'name': 'Integration Test Agent',
        'type': 'individual',
        'politicians': ['Nancy Pelosi', 'Paul Pelosi'],
        'enabled': True,
        'parameters': {
            'minimum_trade_value': 50000,
            'position_size_type': 'fixed',
            'position_size_value': 1000,
            'match_threshold': 0.85
        }
    }


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Setup test environment variables."""
    original_env = os.environ.copy()
    
    # Set test environment
    os.environ['ENVIRONMENT'] = 'test'
    os.environ['LOG_LEVEL'] = 'DEBUG'
    
    yield
    
    # Restore environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def mock_market_data():
    """Mock market data for testing."""
    return {
        'AAPL': 150.0,
        'TSLA': 250.0,
        'MSFT': 300.0,
        'NVDA': 400.0,
        'GOOGL': 2500.0
    }