# MVP Automated Day Trading System Requirements

## Executive Summary

This document defines the requirements for a Minimum Viable Product (MVP) automated day trading system that follows congressional trading activities and replicates trades through the Alpaca API. The system consists of 5 specific trading agents, data processing infrastructure, and dashboard visualization components.

## Core Business Problem

The system addresses the need to automatically track and replicate congressional trading activities, leveraging the hypothesis that following certain politicians' trading patterns may yield profitable returns. The MVP focuses on essential functionality to validate this approach with minimal complexity.

## User Personas

- **Primary User**: Individual trader who wants to follow congressional trading patterns
- **Secondary User**: Portfolio manager monitoring multiple algorithmic strategies

## MVP Scope Definition

### In Scope for MVP
- 5 predefined trading agents (Transportation Committee, Josh Gottheimer, Sheldon Whitehouse, Nancy Pelosi, Dan Meuser)
- Daily data fetching and processing (9:30 PM EST)
- Basic dashboard with two levels (overview and individual holdings)
- GTC order placement through Alpaca API
- Trade tracking and storage
- Simple "copy trade" strategy (buy what they buy)

### Out of Scope for MVP
- Complex trading strategies beyond copying trades
- Real-time data processing
- Advanced portfolio optimization
- User-defined custom agents
- Advanced risk management features
- Mobile application
- Multi-user support
- Advanced analytics and reporting

## Functional Requirements

### 1. Trading Agent System

#### 1.1 Agent Definition
**Requirement**: Each trading agent must follow a specific congressional member or committee
**Acceptance Criteria**:
- System supports exactly 5 predefined agents:
  1. Transportation & Infrastructure Committee Agent (this follows every member listed under /inputs/committee-transportation-infra.md)
  2. Josh Gottheimer Agent  
  3. Sheldon Whitehouse Agent
  4. Nancy Pelosi Agent
  5. Dan Meuser Agent
- Each agent has a unique identifier and name
- Each agent tracks specific politicians using fuzzy name matching (85% similarity threshold)
- Each agent maintains separate portfolio tracking

#### 1.2 Trading Strategy Logic
**Requirement**: All agents implement "copy trading" strategy - buy what the politician(s) buy
**Acceptance Criteria**:
- When a politician makes a purchase > $50,000, agent places corresponding buy order
- Agent ignores sales transactions for MVP
- Trade size calculation: Use minimum viable amount (e.g., 1 share or $100 minimum)
- No position sizing optimization in MVP
- Only processes "Purchase" transactions, ignores "Sale" transactions

#### 1.3 Agent Execution Workflow
**Requirement**: Each agent executes trades based on daily data processing
**Acceptance Criteria**:
- Agents run once daily at 9:30 PM EST
- Process only trades with last_modified date = current date
- Place GTC orders through Alpaca API
- Log all trade decisions and executions
- Handle API failures gracefully with retry logic (3 attempts)

### 2. Data Integration System

#### 2.1 Quiver API Integration
**Requirement**: Fetch congressional trading data daily using existing congressional_filter.py logic
**Acceptance Criteria**:
- Use Quiver API `/beta/bulk/congresstrading` endpoint with date parameter
- Apply existing fuzzy name matching for politician identification
- Filter for transactions > $50,000 minimum value
- Handle rate limiting with exponential backoff
- Store raw API responses for audit trail
- Process date-filtered results (last_modified = execution date)

#### 2.2 Alpaca API Integration
**Requirement**: Execute trades and fetch position data using Alpaca Trading API
**Acceptance Criteria**:
- Use paper trading environment for MVP (paper=True)
- Implement market order placement with GTC time-in-force
- Fetch current positions for portfolio calculations
- Fetch market data for return calculations
- Handle API authentication and error responses
- Support order status monitoring

#### 2.3 yfinance Integration
**Requirement**: Supplement market data for return calculations where needed
**Acceptance Criteria**:
- Fetch current prices for return calculations
- Get historical prices for "since open" return calculations
- Handle ticker symbol validation
- Implement caching to minimize API calls

### 3. Database System

#### 3.1 Trade Storage
**Requirement**: Store all trade executions with complete audit trail
**Acceptance Criteria**:
```sql
CREATE TABLE trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id VARCHAR(50) NOT NULL,
    ticker VARCHAR(10) NOT NULL,
    trade_date DATE NOT NULL,
    execution_date TIMESTAMP NOT NULL,
    order_type VARCHAR(20) NOT NULL,
    quantity DECIMAL(10,4) NOT NULL,
    price DECIMAL(10,2),
    order_status VARCHAR(20) NOT NULL,
    alpaca_order_id VARCHAR(50),
    source_politician VARCHAR(100),
    source_trade_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 3.2 Agent Portfolio Tracking
**Requirement**: Track current positions and performance for each agent
**Acceptance Criteria**:
```sql
CREATE TABLE agent_positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id VARCHAR(50) NOT NULL,
    ticker VARCHAR(10) NOT NULL,
    quantity DECIMAL(10,4) NOT NULL,
    avg_cost DECIMAL(10,2) NOT NULL,
    current_price DECIMAL(10,2),
    market_value DECIMAL(12,2),
    unrealized_pnl DECIMAL(12,2),
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(agent_id, ticker)
);
```

#### 3.3 Daily Performance Snapshots
**Requirement**: Store daily performance metrics for historical tracking
**Acceptance Criteria**:
```sql
CREATE TABLE daily_performance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id VARCHAR(50) NOT NULL,
    date DATE NOT NULL,
    total_value DECIMAL(12,2) NOT NULL,
    daily_return_pct DECIMAL(8,4),
    total_return_pct DECIMAL(8,4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(agent_id, date)
);
```

### 4. Dashboard System

#### 4.1 Overview Dashboard
**Requirement**: Display high-level performance metrics for all agents
**Acceptance Criteria**:
- Table with columns: Strategy Name, Return (1d) %, Return (Since Open) %
- Each row represents one trading agent
- Returns calculated as percentage changes
- Clicking on row navigates to individual agent view
- Auto-refresh every 60 seconds during market hours
- Display last update timestamp

#### 4.2 Individual Agent Dashboard
**Requirement**: Show detailed holdings for selected agent
**Acceptance Criteria**:
- Table with columns: Ticker, Amount ($), % of NAV, Return (1d), Return (Since Open)
- Amount = Quantity × Current Price
- % of NAV = Individual Position Value / Total Portfolio Value × 100
- Return (1d) = Current Price / Yesterday's Close Price - 1
- Return (Since Open) = Current Price / Average Cost - 1
- Display agent name and total portfolio value
- Back button to return to overview

#### 4.3 Dashboard Calculations
**Requirement**: All financial calculations must be accurate and real-time
**Acceptance Criteria**:
- Portfolio values updated from Alpaca positions API
- Price data from Alpaca or yfinance with < 15-minute delay
- Return calculations handle dividends and splits correctly
- Handle zero/negative positions gracefully
- Display monetary values in USD with 2 decimal places
- Display percentages with 2 decimal places

### 5. System Architecture

#### 5.1 Application Structure
**Requirement**: Modular Python application with clear separation of concerns
**Acceptance Criteria**:
```
trading_automation/
├── src/
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base_agent.py
│   │   ├── committee_agent.py
│   │   └── individual_agent.py
│   ├── data/
│   │   ├── __init__.py
│   │   ├── quiver_client.py
│   │   ├── alpaca_client.py
│   │   └── database.py
│   ├── dashboard/
│   │   ├── __init__.py
│   │   ├── app.py
│   │   └── templates/
│   └── scheduler/
│       ├── __init__.py
│       └── daily_runner.py
├── config/
├── data/
├── logs/
└── tests/
```

#### 5.2 Configuration Management
**Requirement**: Centralized configuration with environment-specific settings
**Acceptance Criteria**:
- Use environment variables for API keys and secrets
- Configuration file for agent definitions and parameters
- Separate configs for development/production environments
- Default values for non-sensitive settings

#### 5.3 Logging and Monitoring
**Requirement**: Comprehensive logging for debugging and audit purposes
**Acceptance Criteria**:
- Daily log files with rotation (keep 30 days)
- Structured logging with levels (DEBUG, INFO, WARNING, ERROR)
- Log all API calls, trade executions, and system events
- Performance metrics logging (execution times, API response times)
- Error tracking with stack traces

### 6. Execution Workflow

#### 6.1 Daily Processing Schedule
**Requirement**: Automated daily execution at 9:30 PM EST
**Acceptance Criteria**:
1. **9:30 PM EST**: Start daily processing
2. **Data Fetch**: Retrieve congressional trades from Quiver API for current date
3. **Trade Filtering**: Apply existing filtering logic (>$50k purchases, name matching)
4. **Trade Execution**: For each filtered trade:
   - Check if ticker is tradeable on Alpaca
   - Calculate appropriate position size
   - Place GTC market order
   - Record trade in database
5. **Portfolio Update**: Refresh all agent positions from Alpaca
6. **Performance Calculation**: Update daily performance metrics
7. **Completion**: Log summary and send notification (if configured)

#### 6.2 Error Handling and Recovery
**Requirement**: System must handle failures gracefully without data loss
**Acceptance Criteria**:
- Database transactions are atomic
- API failures trigger retry logic with exponential backoff
- Partial failures allow system to continue processing other agents
- Failed trades are logged with detailed error information
- System state can be recovered from logs and database

### 7. Performance and Quality Standards

#### 7.1 Response Time Requirements
**Requirement**: Dashboard and API responses must be performant
**Acceptance Criteria**:
- Dashboard loads in < 3 seconds
- API responses in < 1 second for standard queries
- Database queries optimized with appropriate indexes
- Position updates complete in < 30 seconds per agent

#### 7.2 Data Accuracy Requirements
**Requirement**: All financial calculations must be precise
**Acceptance Criteria**:
- Price data accuracy within market standards
- Portfolio calculations match Alpaca positions exactly
- Return calculations are mathematically correct
- No rounding errors in monetary calculations

#### 7.3 Reliability Requirements
**Requirement**: System must operate reliably for daily trading
**Acceptance Criteria**:
- 95% uptime during trading hours
- Graceful handling of market holidays
- Automatic recovery from temporary API outages
- Data backup and recovery procedures

## Technical Dependencies

### Required APIs and Services
- **Quiver API**: Congressional trading data (existing token required)
- **Alpaca API**: Trade execution and position management (paper trading account)
- **yfinance**: Supplementary market data (free)

### Technology Stack
- **Backend**: Python 3.9+
- **Database**: SQLite (MVP) / PostgreSQL (production)
- **Web Framework**: Flask or FastAPI for dashboard
- **Frontend**: Simple HTML/CSS/JavaScript (no complex framework)
- **Scheduling**: Python cron or system cron
- **Environment**: Linux/macOS compatible

### Python Package Dependencies
```
alpaca-py==0.8.0
yfinance==0.2.18
flask==2.3.0
python-dotenv==1.0.0
requests==2.31.0
sqlite3 (built-in)
```

## Risk Considerations

### Technical Risks
- **API Rate Limits**: Quiver and Alpaca APIs have usage limitations
- **Market Data Delays**: Price data may have delays affecting calculations
- **Order Execution Risk**: GTC orders may not fill in illiquid markets

### Business Risks
- **Regulatory Risk**: Congressional trading patterns may change due to legislation
- **Market Risk**: Following political trades does not guarantee profits
- **Execution Risk**: Time delays between congressional reporting and trade execution

## Success Metrics

### MVP Success Criteria
1. **Functional**: All 5 agents successfully execute trades daily
2. **Technical**: System runs for 30 consecutive days without critical failures
3. **Data**: Dashboard accurately displays portfolio performance
4. **Usability**: User can monitor all agents and individual positions

### Key Performance Indicators
- Daily processing success rate > 95%
- Trade execution latency < 2 hours from data availability
- Dashboard uptime > 98%
- Data accuracy verified through manual reconciliation

## Implementation Phases

### Phase 1: Core Infrastructure (Week 1-2)
- Database schema creation
- API client implementations
- Basic agent framework

### Phase 2: Trading Logic (Week 2-3)
- Agent implementations
- Trade execution workflow
- Error handling and logging

### Phase 3: Dashboard (Week 3-4)
- Web interface development
- Performance calculations
- User interface testing

### Phase 4: Integration and Testing (Week 4)
- End-to-end testing
- Performance optimization
- Documentation completion

## Open Questions and Assumptions

### Assumptions
- Congressional trading data is available daily through Quiver API
- Alpaca paper trading provides sufficient functionality for MVP
- Simple "copy trade" strategy is sufficient for initial validation
- Users will access dashboard through web browser only

### Questions Requiring Clarification
1. **Position Sizing**: Should all agents use the same dollar amount per trade or vary by agent?
2. **Duplicate Handling**: How to handle the same politician making multiple purchases of the same stock?
3. **Market Hours**: Should trades be placed immediately or wait for market open?
4. **Cleanup Logic**: When/how should old positions be closed?

## Acceptance Criteria Summary

The MVP is considered complete when:
1. All 5 trading agents are implemented and functional
2. Daily data processing runs automatically at 9:30 PM EST
3. Trades are successfully placed through Alpaca API with proper logging
4. Dashboard displays accurate portfolio information for all agents
5. System handles errors gracefully without data corruption
6. Complete audit trail exists for all trades and decisions
7. Documentation is complete and system can be operated by technical user

This MVP provides a foundation for validating the congressional trading strategy while maintaining simplicity and reducing development time to 4 weeks.