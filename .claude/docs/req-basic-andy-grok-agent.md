# Andy (Grok) Agent - Technical Requirements Specification

## Executive Summary

The Andy (Grok) Agent is a **technical indicator-driven trading agent** that operates independently from congressional trading data. It implements a RSI-based day trading strategy on SPY with automatic position management and intraday scheduling.

**Key Differentiators from Existing System:**
- Operates on technical analysis (RSI) vs congressional copy-trading
- Requires intraday scheduling (9:30 AM, 3:55 PM) vs daily 9:30 PM execution
- Implements algorithmic position sizing (1% equity) vs fixed dollar amounts
- Manages short positions vs buy-only congressional trades

---

## 1. CORE STRATEGY REQUIREMENTS

### Trading Logic
```
Market Open (9:30 AM ET):
1. Fetch last 14 hours of SPY closing prices (1-hour intervals)
2. Calculate 14-period RSI
3. Execute decision:
   - RSI < 30 (oversold) → BUY 1% of account equity in SPY
   - RSI > 70 (overbought) → SHORT 1% of account equity in SPY  
   - 30 ≤ RSI ≤ 70 → No action (stay flat)

Intraday (9:31 AM - 3:54 PM ET):
- Hold position, no additional trades

Market Close (3:55 PM ET):  
- Close ALL positions (sell longs, cover shorts)
- Always end day flat (zero overnight risk)
```

### Position Sizing
- **Size**: 1% of total account equity per trade
- **Calculation**: `trade_amount = account_equity * 0.01`
- **Minimum**: $100 per trade (fallback if 1% < $100)
- **Maximum**: No upper limit (risk management via 1% sizing)

### Risk Management
- **Overnight Risk**: None (always close by 3:55 PM)
- **Maximum Exposure**: 1% of account at any time
- **Stop Losses**: Not required (intraday mean reversion strategy)
- **Position Limits**: One position max (long OR short, never both)

---

## 2. TECHNICAL IMPLEMENTATION PLAN

### 2.1 Agent Architecture Decision

**Agent Type**: New `TechnicalAgent` class (extends `BaseAgent`)

**Rationale**: 
- Existing `IndividualAgent`/`CommitteeAgent` are designed for congressional data processing
- Technical analysis requires different data sources and decision logic  
- Need custom scheduling vs daily 9:30 PM execution
- RSI calculation and position management logic is unique

### 2.2 RSI Calculation Implementation

**Approach**: Custom RSI implementation using pandas/numpy
```python
def calculate_rsi(prices: List[float], period: int = 14) -> float:
    """Calculate RSI using standard formula"""
    # Implementation using: RSI = 100 - (100 / (1 + RS))
    # Where RS = Average Gain / Average Loss over period
```

**Data Source**: 
- Primary: yfinance 1-hour intervals for SPY
- Fallback: Alpaca market data if yfinance fails
- Cache: 5-minute cache for price data

### 2.3 Intraday Scheduling Solution  

**Challenge**: Current system only supports daily 9:30 PM scheduling

**Solution**: Extend `DailyRunner` with intraday capabilities
```python
class IntradayScheduler:
    """Handles market-hours scheduling for technical agents"""
    def schedule_market_open_execution()    # 9:30 AM ET
    def schedule_market_close_execution()   # 3:55 PM ET  
    def is_market_hours()                  # Trading hours validation
```

**Integration**: TechnicalAgent registers with IntradayScheduler instead of daily workflow

### 2.4 Database Schema Extensions

**New Tables**:
```sql
-- Technical indicator calculations
CREATE TABLE technical_indicators (
    id INTEGER PRIMARY KEY,
    agent_id TEXT,
    indicator_type TEXT,  -- 'RSI'
    ticker TEXT,          -- 'SPY'
    value REAL,           -- RSI value
    calculation_time TIMESTAMP,
    data_points TEXT      -- JSON of price data used
);

-- Intraday positions tracking
CREATE TABLE intraday_positions (
    id INTEGER PRIMARY KEY,
    agent_id TEXT,
    ticker TEXT,
    side TEXT,            -- 'long', 'short'  
    entry_time TIMESTAMP,
    exit_time TIMESTAMP,
    entry_price REAL,
    exit_price REAL,
    quantity REAL,
    pnl REAL
);
```

---

## 3. DETAILED COMPONENT SPECIFICATIONS

### 3.1 TechnicalAgent Class

```python
class TechnicalAgent(BaseAgent):
    """
    Technical indicator-driven trading agent.
    
    Key Methods:
    - calculate_rsi(ticker, hours_back=14) -> float
    - get_account_equity() -> float  
    - execute_market_open_strategy() -> TradeDecision
    - execute_market_close_strategy() -> List[TradeDecision]
    - _schedule_intraday_execution() -> None
    """
```

**Configuration Parameters**:
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
    "minimum_trade_amount": 100,
    "market_open_time": "09:30",
    "market_close_time": "15:55"
  }
}
```

### 3.2 RSI Calculation Service

```python  
class RSICalculator:
    """
    Handles RSI calculations with data validation.
    
    Features:
    - Fetches hourly price data from yfinance
    - Validates data completeness (requires 14+ data points)
    - Caches calculations for 5 minutes
    - Error handling for missing/invalid data
    """
    
    def get_spy_hourly_data(hours_back: int) -> List[float]
    def calculate_rsi(prices: List[float], period: int) -> float
    def validate_price_data(prices: List[float]) -> bool
```

### 3.3 Position Management Extensions

**Account Equity Calculation**:
- Query Alpaca account endpoint: `GET /v2/account`
- Use `equity` field for position sizing
- Cache for 5 minutes to avoid API limits

**Short Position Support**: 
- Extend existing `AlpacaClient.place_market_order()` 
- Add `side='sell'` for short positions
- Handle margin requirements validation

**Position Closure Logic**:
- Query all open positions at 3:55 PM
- Generate opposite trades to close each position
- Execute with `time_in_force='IOC'` for immediate execution

---

## 4. INTEGRATION WITH EXISTING SYSTEM

### 4.1 Agent Factory Extensions

```python
# In agent_factory.py
def create_technical_agents(config: List[Dict]) -> List[TechnicalAgent]:
    """Create technical agents from configuration"""

def register_intraday_agent(agent: TechnicalAgent):
    """Register agent for intraday scheduling"""
```

### 4.2 Scheduler Integration

**Current State**: Daily 9:30 PM execution only
**Required Changes**: 
- Add `IntradayScheduler` class parallel to `DailyRunner`
- Modify main.py to support: `python main.py start-intraday-scheduler`  
- Handle market holidays/weekends in intraday scheduling

### 4.3 Dashboard Integration

**New Dashboard Sections**:
- Intraday performance tracking
- RSI indicator visualization  
- Position timeline (entry/exit times)
- Technical agent status monitoring

---

## 5. RISK MANAGEMENT & VALIDATION

### 5.1 Data Validation Requirements

**RSI Data Quality**:
- Minimum 14 hourly data points required
- Price data must be from last 24 hours (exclude stale data)
- Validate price movements are realistic (< 10% hourly change)
- Fallback to "no trade" if data quality insufficient

**Account Equity Validation**:
- Minimum account value ($1,000) before allowing trades
- Maximum position size safety check (never > 5% of equity)
- Validate buying power available for shorts

### 5.2 Error Handling Scenarios

**Market Data Failures**:
- No RSI data available → Skip trade, log warning
- RSI calculation error → Skip trade, alert monitoring
- Stale price data → Skip trade, use previous day close as fallback

**Execution Failures**:
- Order rejection → Log error, retry once with smaller size
- Partial fills → Monitor and close remaining at market close
- Market close execution failure → Emergency market order, alert operations

### 5.3 Monitoring & Alerting

**Critical Alerts**:
- Failed to close positions before market close
- RSI calculation failures > 2 consecutive days
- Account equity drop > 5% in single day
- Unexpected overnight positions held

---

## 6. TESTING & VALIDATION PLAN

### 6.1 Unit Testing Requirements

**RSI Calculation Testing**:
```python
def test_rsi_calculation_accuracy()     # Compare vs known RSI values  
def test_rsi_edge_cases()              # Empty data, single data point
def test_rsi_data_validation()         # Invalid/stale price data
```

**Position Management Testing**:
```python
def test_position_sizing_calculation()  # 1% equity calculation
def test_account_equity_fetching()     # Alpaca API integration
def test_short_position_handling()     # Short order placement
def test_position_closure_logic()      # Market close execution
```

### 6.2 Integration Testing

**Market Hours Testing**:
- Validate 9:30 AM execution triggers correctly
- Validate 3:55 PM position closure works
- Test weekend/holiday scheduling behavior

**End-to-End Workflow**:
- Complete trading day simulation (9:30 AM → 3:55 PM)
- Multiple consecutive trading days
- Error recovery scenarios

### 6.3 Paper Trading Validation

**Duration**: 2 weeks minimum
**Success Criteria**:
- RSI calculations match external sources (TradingView)
- Positions properly close by 3:55 PM (100% success rate)  
- No overnight positions held
- Trade execution latency < 30 seconds from signal

---

## 7. DEPLOYMENT & CONFIGURATION

### 7.1 Agent Configuration

Add to `config/agents.json`:
```json
{
  "id": "andy_grok_agent",
  "name": "Andy (Grok) Technical Agent",
  "type": "technical", 
  "description": "RSI-based SPY day trading with intraday position management",
  "ticker": "SPY",
  "enabled": true,
  "parameters": {
    "rsi_period": 14,
    "rsi_oversold_threshold": 30,
    "rsi_overbought_threshold": 70, 
    "position_size_percent": 1.0,
    "minimum_trade_amount": 100,
    "market_open_time": "09:30",
    "market_close_time": "15:55",
    "timezone": "US/Eastern"
  }
}
```

### 7.2 Environment Variables

```bash
# Add to .env file
ENABLE_INTRADAY_TRADING=true
TECHNICAL_AGENT_ENABLED=true  
SPY_DATA_SOURCE=yfinance
INTRADAY_LOG_LEVEL=INFO
```

### 7.3 Command Line Interface

**New Commands**:
```bash
python main.py start-intraday-scheduler    # Start intraday agent scheduling
python main.py test-rsi-calculation       # Test RSI calculation on current data
python main.py simulate-andy-grok-agent   # Run agent simulation without trades
python main.py close-all-positions        # Emergency position closure
```

---

## 8. SUCCESS CRITERIA & METRICS

### 8.1 Functional Requirements

✅ **RSI Calculation Accuracy**: Values match TradingView within 0.1%
✅ **Intraday Execution**: Trades execute within 5 minutes of market open
✅ **Position Closure**: 100% of positions closed by 3:55 PM  
✅ **No Overnight Risk**: Zero positions held after 4:00 PM
✅ **Account Integration**: Position sizing reflects actual account equity

### 8.2 Performance Requirements  

✅ **Latency**: Market open signal → trade execution < 30 seconds
✅ **Reliability**: > 95% successful execution rate
✅ **Data Quality**: RSI calculated with complete 14-hour dataset > 90% of time
✅ **System Integration**: Agent runs alongside existing congressional agents without conflicts

### 8.3 Business Requirements

✅ **Risk Management**: Maximum 1% account exposure maintained
✅ **Compliance**: All trades properly logged and auditable  
✅ **Monitoring**: Real-time dashboard shows agent status and positions
✅ **Flexibility**: Strategy parameters configurable without code changes

---

## 9. IMPLEMENTATION PHASES

### Phase 1: Core Technical Agent (1-2 weeks)
- Create `TechnicalAgent` class extending `BaseAgent`
- Implement RSI calculation with yfinance data
- Build position sizing logic with account equity integration
- Unit tests for core functionality

### Phase 2: Intraday Scheduling (1 week)  
- Extend scheduler to support market hours execution
- Implement 9:30 AM and 3:55 PM trigger logic
- Market holiday and weekend handling
- Integration tests with existing daily scheduler

### Phase 3: Position Management (1 week)
- Short position support in Alpaca client
- Position closure logic for market close  
- Emergency position closure capabilities
- Error handling and retry logic

### Phase 4: Integration & Testing (1 week)
- Dashboard integration for technical agent monitoring
- End-to-end testing with paper trading
- Performance validation and optimization
- Documentation and deployment preparation

**Total Estimated Duration**: 4-5 weeks
**Risk Factors**: Market data API changes, Alpaca API limitations, intraday scheduling complexity

---

## 10. OPEN QUESTIONS & DECISIONS NEEDED

1. **Market Data Backup**: If yfinance fails, should we use Alpaca data or skip the trade?
2. **RSI Period Flexibility**: Should RSI period be configurable or fixed at 14?
3. **Multiple Technical Agents**: Design for one SPY agent or framework for multiple tickers?
4. **Scheduling Conflicts**: How to handle if daily (9:30 PM) and intraday (9:30 AM) agents conflict?
5. **Error Notification**: Should failed executions send email alerts or just log?
6. **Historical Performance**: Should we backtest the strategy before going live?

**Recommendation**: Start with single SPY agent, fixed 14-period RSI, yfinance primary with Alpaca fallback, and comprehensive logging without email alerts initially.

---

This specification provides a complete roadmap for implementing the Andy (Grok) Agent while maintaining integration with the existing congressional trading automation system. The agent will operate as a parallel trading strategy focused on technical analysis rather than copy-trading.