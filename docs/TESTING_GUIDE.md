# Testing Guide - Trading Automation System

## Overview

This guide covers the comprehensive testing strategy for the Trading Automation System, including unit tests, integration tests, performance tests, and deployment validation.

## Table of Contents

- [Testing Framework](#testing-framework)
- [Test Structure](#test-structure)
- [Running Tests](#running-tests)
- [Test Categories](#test-categories)
- [Performance Testing](#performance-testing)
- [Integration Testing](#integration-testing)
- [CI/CD Pipeline](#cicd-pipeline)
- [Best Practices](#best-practices)

## Testing Framework

The system uses **pytest** as the primary testing framework with the following key extensions:

```bash
# Core testing dependencies
pytest==7.4.0
pytest-cov==4.1.0        # Coverage reporting
pytest-mock==3.11.1      # Mocking utilities
pytest-asyncio==0.21.1   # Async testing
pytest-xdist==3.3.1      # Parallel test execution
pytest-timeout==2.1.0    # Test timeout handling
```

## Test Structure

```
tests/
├── conftest.py                 # Global test fixtures
├── unit/                       # Unit tests
│   ├── test_agents.py
│   ├── test_data_clients.py
│   └── test_database.py
├── integration/               # Integration tests
│   ├── conftest.py
│   ├── test_end_to_end_workflow.py
│   └── test_api_integration.py
├── performance/               # Performance tests
│   └── test_performance.py
└── fixtures/                  # Test data fixtures
    ├── sample_trades.json
    └── mock_responses.json
```

## Running Tests

### Basic Test Execution

```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=src --cov-report=html

# Run specific test categories
python -m pytest -m unit          # Unit tests only
python -m pytest -m integration   # Integration tests only
python -m pytest -m performance   # Performance tests only

# Run specific test file
python -m pytest tests/test_agents.py

# Run with parallel execution
python -m pytest -n auto
```

### Test Configuration

The testing behavior is configured in `pytest.ini`:

```ini
[tool:pytest]
testpaths = tests
addopts = 
    --verbose
    --tb=short
    --strict-markers
    --disable-warnings
    --cov=src
    --cov-report=html:htmlcov
    --cov-report=term-missing
    --cov-fail-under=85
markers =
    integration: Integration tests
    performance: Performance tests
    api: Tests requiring API access
    unit: Unit tests
```

## Test Categories

### Unit Tests

Unit tests focus on individual components in isolation:

- **Agent Logic**: Test trading decision algorithms
- **Data Processing**: Test data validation and transformation
- **API Clients**: Test external API integrations with mocks
- **Database Operations**: Test CRUD operations and queries

```python
# Example unit test
def test_agent_decision_making(mock_trade_data):
    agent = IndividualAgent(test_config)
    decision = agent._apply_copy_trading_strategy(mock_trade_data)
    assert decision.ticker == "AAPL"
    assert decision.side == "buy"
```

### Integration Tests

Integration tests validate component interactions:

- **End-to-End Workflow**: Complete data flow from APIs to database
- **Database Integration**: Multi-component database operations
- **API Integration**: Real API calls (using test/staging environments)

```python
@pytest.mark.integration
def test_complete_daily_workflow(test_db, sample_trades):
    runner = DailyRunner(test_db)
    results = runner.execute_daily_run()
    assert results['status'] == 'success'
```

### Performance Tests

Performance tests ensure system meets requirements:

- **Response Time**: API endpoints < 1 second
- **Dashboard Load**: Page loads < 3 seconds
- **Agent Execution**: Complete processing < 30 minutes
- **Resource Usage**: Memory and CPU limits

```python
@pytest.mark.performance
def test_dashboard_load_time():
    start_time = time.time()
    response = client.get('/')
    load_time = time.time() - start_time
    assert load_time < 3.0
```

## Performance Testing

### Load Testing Setup

```bash
# Install load testing dependencies
pip install locust memory-profiler

# Run load tests
locust -f tests/performance/locustfile.py --host=http://localhost:8000
```

### Performance Benchmarks

| Component | Metric | Requirement | Test Method |
|-----------|--------|-------------|-------------|
| Dashboard | Page Load | < 3 seconds | Automated browser test |
| API Endpoints | Response Time | < 1 second | HTTP request timing |
| Agent Processing | Execution Time | < 30 minutes | Simulated trade processing |
| Database Queries | Query Time | < 500ms | SQL execution timing |

### Memory Profiling

```python
from memory_profiler import memory_usage

def process_large_dataset():
    # Process data
    pass

mem_usage = memory_usage(process_large_dataset)
peak_memory = max(mem_usage)
assert peak_memory < 1024  # < 1GB limit
```

## Integration Testing

### Test Environment Setup

Integration tests require test environment configuration:

```bash
# Set test environment variables
export ENVIRONMENT=test
export DATABASE_PATH=/tmp/test_trading.db
export ALPACA_PAPER=true
export LOG_LEVEL=DEBUG
```

### API Testing

Integration tests validate external API interactions:

```python
@pytest.mark.api
def test_alpaca_connection():
    client = AlpacaClient()
    account_info = client.get_account_info()
    assert account_info is not None
    assert 'buying_power' in account_info
```

### Database Testing

```python
def test_database_persistence(test_db):
    # Test data persistence across operations
    agent_data = create_test_agent_data()
    test_db.save_agent(agent_data)
    
    retrieved = test_db.get_agent(agent_data['id'])
    assert retrieved == agent_data
```

## CI/CD Pipeline

### GitHub Actions Workflow

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      
      - name: Run unit tests
        run: pytest -m "not integration and not performance"
      
      - name: Run integration tests
        run: pytest -m integration
        env:
          ALPACA_PAPER: true
      
      - name: Generate coverage report
        run: pytest --cov=src --cov-report=xml
      
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v1
```

### Pre-commit Hooks

```bash
# Install pre-commit hooks
pip install pre-commit
pre-commit install

# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 22.3.0
    hooks:
      - id: black
  
  - repo: https://github.com/pycqa/flake8
    rev: 4.0.1
    hooks:
      - id: flake8
  
  - repo: local
    hooks:
      - id: pytest-fast
        name: pytest-fast
        entry: pytest -m "not slow"
        language: system
        pass_filenames: false
```

## Best Practices

### Test Design

1. **Isolation**: Tests should be independent and not rely on external state
2. **Repeatability**: Tests should produce consistent results
3. **Speed**: Unit tests should run quickly (< 1 second each)
4. **Coverage**: Aim for >85% code coverage
5. **Clarity**: Test names should clearly describe what is being tested

### Mock Usage

```python
from unittest.mock import patch, MagicMock

@patch('src.data.alpaca_client.TradingClient')
def test_order_placement(mock_trading_client):
    mock_client = MagicMock()
    mock_trading_client.return_value = mock_client
    mock_client.submit_order.return_value = {'id': 'test_order'}
    
    client = AlpacaClient()
    result = client.place_market_order('AAPL', 'buy', 100)
    assert result['id'] == 'test_order'
```

### Fixture Management

```python
@pytest.fixture(scope="session")
def test_database():
    """Create test database for session."""
    db = create_test_db()
    yield db
    cleanup_test_db(db)

@pytest.fixture
def sample_trade():
    """Create sample trade data."""
    return CongressionalTrade(
        politician="Test Politician",
        ticker="AAPL",
        trade_type="Purchase",
        amount_min=50000,
        amount_max=100000
    )
```

### Error Testing

```python
def test_api_error_handling():
    with patch('requests.get') as mock_get:
        mock_get.side_effect = requests.RequestException("API Error")
        
        client = QuiverClient()
        with pytest.raises(APIError):
            client.get_congressional_trades()
```

### Async Testing

```python
@pytest.mark.asyncio
async def test_async_operation():
    result = await async_function()
    assert result is not None
```

## Test Data Management

### Fixtures and Sample Data

- Store test data in `tests/fixtures/`
- Use JSON files for complex data structures
- Create factory functions for generating test objects
- Keep test data minimal but representative

### Database Testing

```python
@pytest.fixture
def test_db():
    """Create temporary test database."""
    with tempfile.NamedTemporaryFile(suffix='.db') as tmp_file:
        test_db_path = tmp_file.name
        db = DatabaseManager(test_db_path)
        db.initialize_database()
        yield db
        db.close()
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure PYTHONPATH includes src directory
2. **Database Conflicts**: Use separate test databases
3. **API Rate Limits**: Use mocks for external APIs in unit tests
4. **Timeout Issues**: Increase timeout for slow operations

### Debugging Tests

```bash
# Run tests with debugging
python -m pytest --pdb                    # Drop into debugger on failure
python -m pytest -s                       # Don't capture stdout
python -m pytest --lf                     # Run last failed tests only
python -m pytest -x                       # Stop on first failure
```

## Coverage Reporting

```bash
# Generate coverage report
python -m pytest --cov=src --cov-report=html --cov-report=term

# View HTML coverage report
open htmlcov/index.html
```

### Coverage Requirements

- **Overall**: >85% code coverage
- **Critical Components**: >95% coverage (agents, trading logic)
- **Exception Handling**: All error paths tested
- **API Integrations**: Mock-based coverage for external calls