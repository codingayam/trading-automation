# Development Setup Guide

This guide will help you set up the trading automation system for development.

## Prerequisites

- Python 3.11 or higher
- Git
- Docker (optional, for containerized development)
- Virtual environment tool (venv, virtualenv, or conda)

## Quick Start

### 1. Clone and Setup Environment

```bash
# Clone the repository
git clone <repository-url>
cd trading-automation

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements-dev.txt
```

### 2. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your actual API keys
vim .env  # or use your preferred editor
```

Required environment variables:
- `QUIVER_API_KEY`: Your Quiver API key
- `ALPACA_API_KEY`: Your Alpaca API key  
- `ALPACA_SECRET_KEY`: Your Alpaca secret key

### 3. Initialize Database

```bash
# Initialize database with schema and sample data
python src/data/init_db.py
```

### 4. Install Pre-commit Hooks (Optional but Recommended)

```bash
# Install pre-commit hooks for code quality
pre-commit install
```

## Development Workflow

### Running the Application

#### Dashboard Development
```bash
# Run the dashboard server
python -m flask --app src.dashboard.app run --debug --port 5000

# Or using gunicorn for production-like testing
gunicorn --bind 0.0.0.0:5000 --reload src.dashboard.app:app
```

#### Health Check Server
```bash
# Run health check server
python -c "from src.utils.health import health_server; health_server.start(); import time; time.sleep(3600)"
```

#### Daily Scheduler (Testing)
```bash
# Run daily processing manually
python src/scheduler/daily_runner.py

# Test individual agents
python -c "
from config.settings import settings
from src.agents.base_agent import AgentFactory
agent = AgentFactory.create_agent('nancy_pelosi')
agent.process_daily()
"
```

### Running Tests

```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_database.py

# Run tests in parallel
pytest -n auto
```

### Code Quality Checks

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/

# Security scan
bandit -r src/

# Run all pre-commit hooks
pre-commit run --all-files
```

## Project Structure

```
trading-automation/
├── src/                          # Main application code
│   ├── agents/                   # Trading agent implementations
│   ├── data/                     # Database and API clients
│   ├── dashboard/                # Web dashboard
│   ├── scheduler/                # Daily execution scheduler
│   └── utils/                    # Utilities (logging, monitoring, etc.)
├── config/                       # Configuration files
├── data/                         # Database and data files
├── logs/                         # Application logs
├── tests/                        # Test files
├── requirements.txt              # Production dependencies
├── requirements-dev.txt          # Development dependencies
├── Dockerfile                    # Container configuration
├── docker-compose.yml            # Multi-container setup
└── .env.example                  # Environment variables template
```

## Development with Docker

### Build and Run
```bash
# Build the container
docker build -t trading-automation .

# Run with docker-compose
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Development Mode with Docker
```bash
# Override for development (with volume mounts)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

## Database Management

### Schema Updates
```bash
# Re-initialize database (WARNING: destroys existing data)
python src/data/init_db.py

# Backup database
cp data/trading_automation.db data/backup_$(date +%Y%m%d_%H%M%S).db
```

### Sample Data Generation
```bash
# Generate fresh sample data for development
python -c "
from src.data.init_db import create_sample_data
create_sample_data()
"
```

## API Testing

### Manual API Testing
```bash
# Test Quiver API
python -c "
from src.data.quiver_client import QuiverClient
client = QuiverClient()
data = client.get_congressional_trades(date='2023-01-01')
print(len(data), 'trades found')
"

# Test Alpaca API
python -c "
from src.data.alpaca_client import AlpacaClient
client = AlpacaClient()
account = client.get_account()
print('Account status:', account.status)
"
```

### Health Checks
```bash
# Check system health
curl http://localhost:8080/health

# Check specific component
curl http://localhost:8080/health/database

# Get metrics
curl http://localhost:8080/metrics

# System stats
curl http://localhost:8080/system
```

## Debugging

### Logging
- Application logs: `logs/trading_automation.log`
- Agent logs: `logs/agents.log`
- API logs: `logs/api.log`
- Trading logs: `logs/trading.log`

### Common Issues

1. **Database locked error**
   ```bash
   # Kill any running processes and restart
   pkill -f trading-automation
   python src/data/init_db.py
   ```

2. **API key issues**
   ```bash
   # Verify environment variables
   python -c "from config.settings import settings; print(settings.api.alpaca_api_key[:10])"
   ```

3. **Import errors**
   ```bash
   # Ensure project root is in Python path
   export PYTHONPATH="$PWD:$PYTHONPATH"
   ```

## Performance Profiling

### Memory Profiling
```bash
# Install memory profiler
pip install memory-profiler

# Profile memory usage
python -m memory_profiler src/scheduler/daily_runner.py
```

### CPU Profiling
```bash
# Install py-spy
pip install py-spy

# Profile running process
py-spy top --pid <pid>
py-spy record -o profile.svg --pid <pid>
```

## Contributing

1. Create feature branch: `git checkout -b feature/new-feature`
2. Make changes and write tests
3. Run code quality checks: `pre-commit run --all-files`
4. Run tests: `pytest`
5. Commit changes: `git commit -m "Add new feature"`
6. Push branch: `git push origin feature/new-feature`
7. Create pull request

## Environment Variables Reference

See `.env.example` for all available configuration options.

### Required
- `QUIVER_API_KEY`: Quiver API authentication token
- `ALPACA_API_KEY`: Alpaca trading API key
- `ALPACA_SECRET_KEY`: Alpaca trading API secret

### Optional
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `DATABASE_PATH`: Path to SQLite database file
- `DASHBOARD_PORT`: Port for web dashboard (default: 5000)

## Troubleshooting

### Common Error Messages

1. **"Configuration validation failed"**
   - Check all required environment variables are set in `.env`

2. **"Database initialization failed"**
   - Ensure `data/` directory exists and is writable
   - Check disk space

3. **"API call failed"**
   - Verify API keys are correct
   - Check network connectivity
   - Review rate limiting settings

For more help, check the logs in `logs/` directory or create an issue in the repository.