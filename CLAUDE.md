# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## System Overview

This is a **Congressional Trading Automation System** with technical analysis capabilities that monitors congressional stock trading data and executes both copy-trading and technical trading strategies. The system fetches congressional trade data via Quiver API and market data for technical analysis, processes them through configurable trading agents, and executes trades via Alpaca API during market hours.

### Core Architecture

The system follows a modular architecture with clear separation of concerns:

```
Congressional Data (Quiver API) → Congressional Agents → Trade Execution (Alpaca API) ↘
                                                                                        ↓
                                                                               Web Dashboard
                                                                                        ↑
 Market Data (yfinance/Alpaca) → Technical Agents → Trade Execution (Alpaca API) ↗
                    ↓                      ↓
        Technical Indicators            SQLite Database ← Performance Tracking
                ↓                                    ↑
    Intraday Scheduler (market hours)    Congressional Scheduler (Daily 9:30 PM EST)
```

**Key Components:**
- `src/scheduler/intraday_scheduler.py` - Market hours scheduler for ALL agents (9:30 AM ET)
- `src/scheduler/daily_runner.py` - Legacy congressional scheduler (9:30 PM EST) - use `scheduler` command
- `src/agents/` - Trading agent framework (congressional, technical)
  - `andy_grok_agent.py` - RSI-based SPY day trading agent
  - `technical_agent.py` - Base class for technical analysis agents
  - `individual_agent.py` - Individual politician tracking
  - `committee_agent.py` - Committee/multiple politician tracking
- `src/data/` - API clients for external services (Alpaca, Quiver, market data)
- `src/dashboard/` - Flask web interface for monitoring and configuration
- `src/utils/technical_indicators.py` - RSI and other technical analysis tools
- `config/settings.py` - Centralized configuration management
- `main.py` - CLI entry point with multiple commands

## Common Development Commands

### Running the System

**Start ALL trading schedulers (recommended):**
```bash
python3 main.py start        # Runs ALL agents together in one process
```

**Start individual schedulers (advanced):**
```bash
python3 main.py scheduler    # Congressional agents only (9:30 PM EST)
python3 main.py intraday     # Technical agents only (market hours)
```

**Test individual agent types:**
```bash
# Congressional agents
python3 main.py run-once                     # Run congressional agents for today
python3 main.py run-once --date 2024-01-15  # Run for specific date

# Technical agents  
python3 main.py andy-grok-once              # Test Andy Grok agent once
```

**Other system commands:**
```bash
python3 main.py test-connections     # Test API connectivity
python3 main.py status              # Show congressional scheduler status
python3 main.py intraday-status     # Show technical scheduler status
python3 main.py list-agents         # List all configured agents
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
- **TechnicalAgent** (`src/agents/technical_agent.py`) - Base class for technical indicator-driven agents
- **AndyGrokAgent** (`src/agents/andy_grok_agent.py`) - RSI-based SPY day trading agent

### Agent Configuration
Agents are configured in `config/agents.json` or via the settings system:

**Congressional Agents:**
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

**Technical Agents:**
```json
{
  "id": "andy_grok_agent",
  "name": "Andy (Grok) Technical Agent",
  "type": "technical",
  "ticker": "SPY",
  "parameters": {
    "rsi_period": 14,
    "rsi_oversold_threshold": 30,
    "rsi_overbought_threshold": 70,
    "position_size_percent": 1.0,
    "market_open_time": "09:30",
    "market_close_time": "15:55"
  }
}
```

### Agent Lifecycle

**Congressional Agents:**
1. **Daily Runner** (`src/scheduler/daily_runner.py`) triggers agents at 9:30 PM EST
2. **Agent Factory** (`src/agents/agent_factory.py`) creates and manages agent instances
3. **Base Agent** (`src/agents/base_agent.py`) defines the abstract interface
4. **Data Processor** (`src/data/data_processor.py`) handles trade execution

**Technical Agents (Andy Grok):**
1. **Intraday Scheduler** (`src/scheduler/intraday_scheduler.py`) handles market-hours execution
2. **Morning Analysis** (9:30 AM ET) - RSI calculation and entry decisions
3. **Position Management** - Hold positions during trading day
4. **Closing Workflow** (3:55 PM ET) - Close all positions before market close
5. **Technical Indicators** (`src/utils/technical_indicators.py`) - RSI and market data

## Data Flow and External APIs

### API Clients
- **AlpacaClient** (`src/data/alpaca_client.py`) - Trade execution, account management
- **QuiverClient** (`src/data/quiver_client.py`) - Congressional trading data
- **MarketDataService** (`src/data/market_data_service.py`) - Real-time stock prices
- **TechnicalIndicators** (`src/utils/technical_indicators.py`) - RSI calculation using yfinance data

### Database Schema

**All environments:** SQLite with tables managed through `src/data/database.py`
- **Development:** Local SQLite file
- **Railway:** SQLite with persistent file storage

**Tables:**
- `agents` - Agent configurations and status
- `congressional_trades` - Raw congressional trading data
- `agent_trades` - Executed trades by agents
- `positions` - Current portfolio positions
- `performance_history` - Historical performance data
- `technical_indicators` - RSI and other technical analysis data
- `intraday_positions` - Andy Grok agent position tracking

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
- `tests/test_andy_grok_agent.py` - Andy Grok agent specific tests

### Key Test Files
- `tests/test_agents.py` - Congressional agent logic and decision-making
- `tests/test_andy_grok_agent.py` - Technical agent RSI strategy testing
- `tests/integration/test_end_to_end_workflow.py` - Complete system workflows
- `tests/performance/test_performance.py` - Performance benchmarks
- `src/dashboard/test_dashboard.py` - Dashboard API testing

### Test Configuration
Test behavior is configured in `pytest.ini`:
- Coverage target: >85%
- Test markers for categorization
- Warning filters for external libraries

## Production Deployment

### Railway Deployment (Recommended)

**Quick Deploy:**
1. Go to [Railway Dashboard](https://railway.app/dashboard)
2. Click **"New Project"** → **"Deploy from GitHub repo"**
3. Connect your repository and select main branch
4. Set required environment variables (see Railway section below)
5. Database uses SQLite with persistent file storage
6. Railway auto-deploys using `Dockerfile.railway`

**What gets deployed:**
- All-in-one container with both scheduler and dashboard
- SQLite database (file-based, persistent storage)
- Health monitoring at `/health` endpoint
- Public URL for dashboard access
- Automatic SSL and domain management

**Cost: ~$5/month** for small portfolios

### Docker Deployment (Alternative)
```bash
docker-compose -f docker-compose.production.yml up -d
```

### Manual Deployment (Legacy)
```bash
sudo ./deployment/deploy.sh  # Automated deployment script
```

**Production services:**
- Main trading application with scheduler
- Flask dashboard with Gunicorn
- Nginx reverse proxy
- PostgreSQL database (legacy production only)
- Prometheus + Grafana monitoring

### Railway Environment Variables

**Required for Railway:**
```bash
ENVIRONMENT=production
ALPACA_API_KEY=your_alpaca_key_here
ALPACA_SECRET_KEY=your_alpaca_secret_here
ALPACA_PAPER=true
QUIVER_API_KEY=your_quiver_key_here
```

**Optional:**
```bash
LOG_LEVEL=INFO
DAILY_EXECUTION_TIME=21:30
DATABASE_PATH=data/trading_automation.db
```

**Auto-configured by Railway:**
- `PORT` - Application port

### Monitoring and Health Checks
- Health endpoint at `/health` for Railway monitoring
- Health server runs on port 8080 when scheduler is active (legacy)
- Railway provides built-in monitoring and alerts
- Prometheus metrics collection configured (legacy deployments)
- Grafana dashboards for system monitoring (legacy deployments)
- Comprehensive alerting rules in `deployment/prometheus/alerts.yml` (legacy)

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

**Scheduler timing:** All agents now execute during market hours (9:30 AM ET) by default when using the unified `start` command. The legacy congressional-only scheduler still uses 9:30 PM ET and is configurable via `DAILY_EXECUTION_TIME` environment variable.

**Railway deployment issues:** If the scheduler crashes on Railway, check that all required environment variables are set. Use Railway logs (`railway logs`) to debug startup issues. The health endpoint (`/health`) provides system status.

## how to run 101 guide ##

### Railway Deployment (Cloud)

**For production use:**
1. Deploy to Railway (see Railway section above)
2. Access dashboard at your Railway URL
3. System runs ALL agents automatically - no manual commands needed
4. Both congressional (9:30 PM) and technical (market hours) agents run together

### Local Development

**For all trading (recommended):**
1. `python3 main.py start` ← ALL agents together (congressional + technical)
2. `python3 src/dashboard/run_dashboard.py` ← View results

**For individual agent types (advanced):**
- `python3 main.py scheduler` ← Congressional agents only
- `python3 main.py intraday` ← Technical agents only

**First-time setup:**
1. `python3 main.py test-connections` ← Make sure APIs work
2. Then run the main commands above

**Testing/development:**
- `python3 main.py run-once` ← Test congressional agents only
- `python3 main.py andy-grok-once` ← Test technical agent only

---
🎯 **The Commands You Actually Need**

**Cloud (Railway) - Zero maintenance:**
- Deploy once → runs ALL agents automatically
- Dashboard at your Railway URL

**Local development:**
- `python3 main.py start` → ALL agents together (recommended)
- `python3 src/dashboard/run_dashboard.py` → See what happened

**Advanced (separate processes):**
- `python3 main.py scheduler` → Congressional agents only
- `python3 main.py intraday` → Technical agents only