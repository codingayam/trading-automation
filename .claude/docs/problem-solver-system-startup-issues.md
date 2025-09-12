# Triage Report: System Startup Issues

## Summary
- **Symptom:** Multiple component re-initializations during startup, health server port conflicts, excessive API client instantiation
- **Scope/Blast Radius:** System-wide startup sequence, affects all agent initialization
- **First Seen / Last Known Good:** Current execution logs show pattern, no historical baseline available
- **Environments Affected:** Local development environment (macOS)
- **Related Tickets/Deploys/Flags:** None specified

## Likely Components & Paths
- **Agent Factory** → Multiple instantiation of API clients for each agent creation
- **Health Server** → Port 8080 already in use conflict
- **API Client Management** → Lack of singleton pattern causing duplicate instances
- Candidate paths:
  - `/Users/admin/github/trading-automation/src/agents/agent_factory.py` - Agent creation logic
  - `/Users/admin/github/trading-automation/src/utils/health.py` - Health server startup
  - `/Users/admin/github/trading-automation/src/data/alpaca_client.py` - API client initialization
  - `/Users/admin/github/trading-automation/src/data/quiver_client.py` - API client initialization
  - `/Users/admin/github/trading-automation/src/data/market_data_service.py` - Market data service initialization

## Ranked Hypotheses

1) **Multiple API Client Instantiation Per Agent** — Confidence: 95
   - **Mechanism:** Agent factory creates new API clients (Alpaca, Quiver, MarketData) for each agent instead of reusing shared instances
   - **Evidence for:** Lines 22-24, 28-29, 34-35, 60-62, 66-68, 72-74, 78-80 show identical API client initialization for each agent
   - **Evidence against:** None - pattern is clearly visible in logs
   - **Quick validation:** Check if agent_factory.py creates new API client instances per agent
   - **Expected observation if true:** Each of 6 agents shows 3 API client initializations (18 total vs 3 expected)

2) **Health Server Port Already in Use** — Confidence: 90
   - **Mechanism:** Previous system execution left health server running on port 8080, new instance cannot bind
   - **Evidence for:** Lines 37-57 show clear OSError: [Errno 48] Address already in use on port 8080
   - **Evidence against:** System continues functioning normally after error
   - **Quick validation:** `lsof -i :8080` to check what process owns the port
   - **Expected observation if true:** Another process or zombie health server holding port 8080

3) **Missing Singleton Pattern for Shared Services** — Confidence: 85
   - **Mechanism:** Architecture lacks proper dependency injection/singleton pattern for shared services
   - **Evidence for:** Repeated initialization of identical services (market data, API clients) across agents
   - **Evidence against:** System completes startup successfully despite inefficiency
   - **Quick validation:** Review agent_factory.py and base_agent.py for service instantiation patterns
   - **Expected observation if true:** Each agent creates its own service instances instead of sharing

4) **Race Condition in Health Server Startup** — Confidence: 70
   - **Mechanism:** Health server tries to start twice simultaneously or previous instance cleanup failed
   - **Evidence for:** Health server error occurs during agent initialization phase
   - **Evidence against:** Only one health server start attempt visible in logs
   - **Quick validation:** Check for multiple health server initialization calls in main.py
   - **Expected observation if true:** Multiple health server start calls or cleanup failure

## High-Signal Checks (Do First)
- [ ] `lsof -i :8080` - Identify what process is using port 8080
- [ ] Count API client initializations: `grep -c "Initialized.*client" logs` (should be 3, currently ~18)
- [ ] Review agent_factory.py for API client instantiation pattern per agent
- [ ] Check if health server error prevents system functionality or is cosmetic
- [ ] Verify final system state: all 6 agents properly scheduled and ready

## Recent Changes (last 20 commits touching suspects)
- c35e8b5 — supervisord.conf — Fix Railway dashboard command
- 016b843 — (multiple files) — Complete codebase cleanup after unified market hours implementation  
- 85b64e1 — scheduler files — Create ultra-simple scheduler to isolate Railway deployment issues
- 954e283 — supervisord config — Fix supervisor configuration to handle scheduler exit codes
- ebd9bab — diagnostic files — Add Railway diagnostic test

## Data Gaps & Requests
- **Need:** Current process list to identify port 8080 owner: `ps aux | grep python` and `lsof -i :8080`
- **Need:** Agent factory source code to confirm API client instantiation pattern
- **Need:** Verification if system functions correctly despite health server error
- **Need:** Resource usage impact assessment of multiple API client instances

## Handoff to Debugger subagent
- **Start with:** `/Users/admin/github/trading-automation/src/agents/base_agent.py` lines 96-99
- **CONFIRMED Hypothesis #1:** Each agent creates its own API client instances via BaseAgent.__init__()
  - AlpacaClient(), QuiverClient(), MarketDataService() instantiated per agent (6x duplication)
  - Creates 18 API client instances instead of 3 shared ones
  - Process 80286 confirmed holding port 8080 from previous `main.py scheduler` execution
- **Impact assessment:** Likely causing rate limiting issues, excess memory usage, duplicate connection pools
- **Health server error:** Non-blocking - system successfully reaches operational state despite port conflict

## Root Cause Analysis CONFIRMED

**PRIMARY ISSUE:** `src/agents/base_agent.py` lines 96-99
```python
self.alpaca_client = AlpacaClient()        # Creates new instance per agent
self.quiver_client = QuiverClient()        # Creates new instance per agent  
self.market_data_service = MarketDataService()  # Creates new instance per agent
```

**SECONDARY ISSUE:** Health server port conflict due to previous process 80286 still running

## Assessment: System Functionality Status
✅ **SYSTEM IS OPERATIONAL** despite inefficiencies:
- All 6 agents properly created and scheduled (lines 110-117 in logs)
- Intraday scheduler started with 7 active tasks (line 107)
- System successfully reached "Press Ctrl+C to stop all schedulers..." state (line 116)
- Health server error is **cosmetic only** - does not block core functionality

**Classification:** Performance optimization needed, not critical system failure.