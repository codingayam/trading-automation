# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## System Overview

This is a **Congressional Trading Automation System** that monitors congressional stock trading data and automatically executes copy-trading strategies. The system fetches congressional trade data via Quiver API, processes it through configurable trading agents, and executes trades via Alpaca API (paper or live trading).

### Core Architecture

The system follows a modular architecture with clear separation of concerns:

```
Data Ingestion (Quiver API) → Trading Agents → Trade Execution (Alpaca API) → Web Dashboard
                    ↓
            SQLite Database ← Performance Tracking ← Scheduler (Daily 9:30 PM EST)
```

**Key Components:**
- `src/scheduler/daily_runner.py` - Main scheduler that runs daily at 9:30 PM EST
- `src/agents/` - Trading agent framework (individual politicians, committees)
- `src/data/` - API clients for external services (Alpaca, Quiver, market data)
- `src/dashboard/` - Flask web interface for monitoring and configuration
- `config/settings.py` - Centralized configuration management
- `main.py` - CLI entry point with multiple commands

## Common Development Commands

### Running the System

**Start the automated trading scheduler:**
```bash
python3 main.py scheduler  # Runs daily at 9:30 PM EST
```

**Run trading workflow once (for testing):**
```bash
python3 main.py run-once                     # Run for today
python3 main.py run-once --date 2024-01-15  # Run for specific date
```

**Other system commands:**
```bash
python3 main.py test-connections  # Test API connectivity
python3 main.py status           # Show system status
python3 main.py list-agents      # List configured agents
```

**Start the web dashboard:**
```bash
python3 src/dashboard/run_dashboard.py
# Access at http://localhost:5000
```

### Testing

**Run all tests:**
```bash
python3 -m pytest
```

**Run specific test categories:**
```bash
python3 -m pytest -m unit          # Unit tests only
python3 -m pytest -m integration   # Integration tests only
python3 -m pytest -m performance   # Performance tests only
```

**Run with coverage:**
```bash
python3 -m pytest --cov=src --cov-report=html
```

**Run specific test file:**
```bash
python3 -m pytest tests/test_agents.py -v
```

### Development Setup

**Install dependencies:**
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For development/testing
```

**Environment configuration:**
```bash
# Required API keys in .env file:
ALPACA_API_KEY=your_alpaca_key
ALPACA_SECRET_KEY=your_alpaca_secret
ALPACA_PAPER=true  # Always start with paper trading
QUIVER_API_KEY=your_quiver_key
```

## Agent System Architecture

The trading agent system is the core of the application and uses an abstract base class pattern:

### Agent Types
- **IndividualAgent** (`src/agents/individual_agent.py`) - Tracks specific politicians
- **CommitteeAgent** (`src/agents/committee_agent.py`) - Tracks multiple politicians (committees)

### Agent Configuration
Agents are configured in `config/agents.json` or via the settings system:
```json
{
  "id": "nancy_pelosi",
  "name": "Nancy Pelosi Tracker",
  "type": "individual",
  "politicians": ["Nancy Pelosi"],
  "parameters": {
    "minimum_trade_value": 50000,
    "position_size_type": "fixed",
    "position_size_value": 1000
  }
}
```

### Agent Lifecycle
1. **Daily Runner** (`src/scheduler/daily_runner.py`) triggers agents at 9:30 PM EST
2. **Agent Factory** (`src/agents/agent_factory.py`) creates and manages agent instances
3. **Base Agent** (`src/agents/base_agent.py`) defines the abstract interface
4. **Data Processor** (`src/data/data_processor.py`) handles trade execution

## Data Flow and External APIs

### API Clients
- **AlpacaClient** (`src/data/alpaca_client.py`) - Trade execution, account management
- **QuiverClient** (`src/data/quiver_client.py`) - Congressional trading data
- **MarketDataService** (`src/data/market_data_service.py`) - Real-time stock prices

### Database Schema
The system uses SQLite with tables managed through `src/data/database.py`:
- `agents` - Agent configurations and status
- `congressional_trades` - Raw congressional trading data
- `agent_trades` - Executed trades by agents
- `positions` - Current portfolio positions
- `performance_history` - Historical performance data

### Configuration System
Centralized configuration in `config/settings.py` loads from environment variables:
- Database paths and connection settings
- API credentials and endpoints
- Trading parameters and risk limits
- Scheduling and execution timing
- Logging and monitoring configuration

## Testing Strategy

The system has comprehensive testing with different categories:

### Test Structure
- `tests/unit/` - Unit tests for individual components
- `tests/integration/` - End-to-end workflow tests
- `tests/performance/` - Performance and load testing
- `tests/fixtures/` - Test data and mock objects

### Key Test Files
- `tests/test_agents.py` - Agent logic and decision-making
- `tests/integration/test_end_to_end_workflow.py` - Complete system workflows
- `tests/performance/test_performance.py` - Performance benchmarks
- `src/dashboard/test_dashboard.py` - Dashboard API testing

### Test Configuration
Test behavior is configured in `pytest.ini`:
- Coverage target: >85%
- Test markers for categorization
- Warning filters for external libraries

## Production Deployment

### Docker Deployment
```bash
docker-compose -f docker-compose.production.yml up -d
```

### Manual Deployment
```bash
sudo ./deployment/deploy.sh  # Automated deployment script
```

**Production services:**
- Main trading application with scheduler
- Flask dashboard with Gunicorn
- Nginx reverse proxy
- PostgreSQL database (production)
- Prometheus + Grafana monitoring

### Monitoring and Health Checks
- Health server runs on port 8080 when scheduler is active
- Prometheus metrics collection configured
- Grafana dashboards for system monitoring
- Comprehensive alerting rules in `deployment/prometheus/alerts.yml`

## Important Implementation Notes

### Exception Handling
The system uses a hierarchical exception system in `src/utils/exceptions.py`:
- `TradingSystemError` - Base exception
- `APIError`, `TradingError`, `ValidationError` - Specific error types
- All exceptions include structured logging and context

### Logging
Structured logging throughout the system via `src/utils/logging.py`:
- JSON format for production parsing
- Performance metrics collection
- Separate log files for different components

### Security Considerations
- All API keys stored as environment variables
- Paper trading enabled by default
- Input validation and sanitization
- Rate limiting and retry logic for external APIs

### Performance Requirements
The system must meet these benchmarks:
- Dashboard load time: <3 seconds
- API response time: <1 second
- Agent execution: <30 minutes total
- Database queries: <500ms average

## Common Troubleshooting

**Import errors with abstract classes:** Use concrete implementations or mock classes in tests, never instantiate `BaseAgent` directly.

**Configuration access errors:** Use the settings object structure (e.g., `settings.scheduling.daily_execution_time`, not `settings.agents.global_parameters`).

**API connection issues:** Always test with `python3 main.py test-connections` before running full system.

**Database schema issues:** The database auto-initializes on first run. Check `src/data/database.py` for schema definitions.

**Scheduler timing:** The system uses US/Eastern timezone by default. Execution time is configurable via `DAILY_EXECUTION_TIME` environment variable.

## how to run 101 guide ##
Typical Usage Pattern

  For daily use:
  1. python3 main.py scheduler ← This is the main one
  2. python3 src/dashboard/run_dashboard.py ← This shows you results

  For first-time setup:
  1. python3 main.py test-connections ← Make sure it works
  2. Then run the two main commands above

  For testing/development:
  - python3 main.py run-once ← Test without waiting until 9:30 PM

  ---
  🎯 The Two You Actually Need

  99% of the time, you only need these two commands:

  1. python3 main.py scheduler → Runs automated trading
  2. python3 src/dashboard/run_dashboard.py → Shows you what happened