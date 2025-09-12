admin@MacBook-Pro-2 trading-automation % python3 main.py start
2025-09-12 16:09:41,572 - system - INFO - Logging system initialized
2025-09-12 16:09:41,572 - database - INFO - Database manager initialized
/Users/admin/Library/Python/3.9/lib/python/site-packages/urllib3/__init__.py:35: NotOpenSSLWarning: urllib3 v2 only supports OpenSSL 1.1.1+, currently the 'ssl' module is compiled with 'LibreSSL 2.8.3'. See: https://github.com/urllib3/urllib3/issues/3020
  warnings.warn(
2025-09-12 16:09:41,633 - monitoring - INFO - Default health checks registered
2025-09-12 16:09:42,147 - health - INFO - External dependency health checks registered
2025-09-12 16:09:42,149 - src.agents.agent_factory - INFO - Initialized Agent Factory
2025-09-12 16:09:42,150 - src.data.quiver_client - INFO - Initialized Quiver client with rate limit: 60/min
2025-09-12 16:09:42,150 - src.data.alpaca_client - INFO - Initialized Alpaca client in paper trading mode
2025-09-12 16:09:42,165 - src.data.market_data_service - INFO - Initialized Market Data Service with 15-minute cache
2025-09-12 16:09:42,165 - src.data.data_processor - INFO - Initialized Data Processing Engine
2025-09-12 16:09:42,165 - src.scheduler.daily_runner - INFO - Initialized Daily Runner
2025-09-12 16:09:42,165 - src.scheduler.daily_runner - INFO - Scheduled execution time: 21:30 US/Eastern
2025-09-12 16:09:42,166 - src.scheduler.intraday_scheduler - INFO - Initialized Intraday Scheduler
2025-09-12 16:09:42,168 - __main__ - INFO - Starting Trading Automation System - Command: start
2025-09-12 16:09:42,168 - __main__ - INFO - Starting all trading agents for market hours execution...
2025-09-12 16:09:42,168 - health - INFO - Starting health server on 0.0.0.0:8080
2025-09-12 16:09:42,168 - health - INFO - Health server started on 0.0.0.0:8080
2025-09-12 16:09:42,168 - __main__ - INFO - Health server started on port 8080
2025-09-12 16:09:42,168 - src.agents.agent_factory - INFO - Creating 6 agents from configuration
2025-09-12 16:09:42,168 - src.data.alpaca_client - INFO - Initialized Alpaca client in paper trading mode
2025-09-12 16:09:42,168 - src.data.quiver_client - INFO - Initialized Quiver client with rate limit: 60/min
2025-09-12 16:09:42,168 - src.data.market_data_service - INFO - Initialized Market Data Service with 15-minute cache
2025-09-12 16:09:42,169 - src.agents.base_agent - INFO - Initialized agent transportation_committee tracking 10 politicians
2025-09-12 16:09:42,169 - src.agents.committee_agent - INFO - Initialized committee agent transportation_committee tracking 10 politicians
2025-09-12 16:09:42,169 - src.agents.agent_factory - INFO - Created agent: transportation_committee (TransportationCommitteeAgent)
2025-09-12 16:09:42,169 - src.data.alpaca_client - INFO - Initialized Alpaca client in paper trading mode
 * Serving Flask app 'src.utils.health' (lazy loading)
 * Environment: production
   WARNING: This is a development server. Do not use it in a production deployment.
   Use a production WSGI server instead.
 * Debug mode: off
2025-09-12 16:09:42,169 - src.data.quiver_client - INFO - Initialized Quiver client with rate limit: 60/min
2025-09-12 16:09:42,169 - src.data.market_data_service - INFO - Initialized Market Data Service with 15-minute cache
2025-09-12 16:09:42,169 - src.agents.base_agent - INFO - Initialized agent josh_gottheimer tracking 1 politicians
2025-09-12 16:09:42,170 - health - ERROR - Health server failed to start
Traceback (most recent call last):
  File "/Users/admin/github/trading-automation/src/utils/health.py", line 155, in run_server
    self.app.run(
  File "/Users/admin/Library/Python/3.9/lib/python/site-packages/flask/app.py", line 922, in run
    run_simple(t.cast(str, host), port, self, **options)
  File "/Users/admin/Library/Python/3.9/lib/python/site-packages/werkzeug/serving.py", line 1017, in run_simple
    inner()
  File "/Users/admin/Library/Python/3.9/lib/python/site-packages/werkzeug/serving.py", line 957, in inner
    srv = make_server(
  File "/Users/admin/Library/Python/3.9/lib/python/site-packages/werkzeug/serving.py", line 789, in make_server
    return ThreadedWSGIServer(
  File "/Users/admin/Library/Python/3.9/lib/python/site-packages/werkzeug/serving.py", line 693, in __init__
    super().__init__(server_address, handler)  # type: ignore
  File "/Applications/Xcode.app/Contents/Developer/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/socketserver.py", line 452, in __init__
    self.server_bind()
  File "/Applications/Xcode.app/Contents/Developer/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/http/server.py", line 138, in server_bind
    socketserver.TCPServer.server_bind(self)
  File "/Applications/Xcode.app/Contents/Developer/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/socketserver.py", line 466, in server_bind
    self.socket.bind(self.server_address)
OSError: [Errno 48] Address already in use
2025-09-12 16:09:42,170 - src.agents.individual_agent - INFO - Initialized individual agent josh_gottheimer tracking: Josh Gottheimer
2025-09-12 16:09:42,176 - src.agents.agent_factory - INFO - Created agent: josh_gottheimer (JoshGottheimerAgent)
2025-09-12 16:09:42,176 - src.data.alpaca_client - INFO - Initialized Alpaca client in paper trading mode
2025-09-12 16:09:42,176 - src.data.quiver_client - INFO - Initialized Quiver client with rate limit: 60/min
2025-09-12 16:09:42,176 - src.data.market_data_service - INFO - Initialized Market Data Service with 15-minute cache
2025-09-12 16:09:42,176 - src.agents.base_agent - INFO - Initialized agent sheldon_whitehouse tracking 1 politicians
2025-09-12 16:09:42,177 - src.agents.individual_agent - INFO - Initialized individual agent sheldon_whitehouse tracking: Sheldon Whitehouse
2025-09-12 16:09:42,177 - src.agents.agent_factory - INFO - Created agent: sheldon_whitehouse (SheldonWhitehouseAgent)
2025-09-12 16:09:42,177 - src.data.alpaca_client - INFO - Initialized Alpaca client in paper trading mode
2025-09-12 16:09:42,177 - src.data.quiver_client - INFO - Initialized Quiver client with rate limit: 60/min
2025-09-12 16:09:42,177 - src.data.market_data_service - INFO - Initialized Market Data Service with 15-minute cache
2025-09-12 16:09:42,177 - src.agents.base_agent - INFO - Initialized agent nancy_pelosi tracking 1 politicians
2025-09-12 16:09:42,177 - src.agents.individual_agent - INFO - Initialized individual agent nancy_pelosi tracking: Nancy Pelosi
2025-09-12 16:09:42,177 - src.agents.agent_factory - INFO - Created agent: nancy_pelosi (NancyPelosiAgent)
2025-09-12 16:09:42,177 - src.data.alpaca_client - INFO - Initialized Alpaca client in paper trading mode
2025-09-12 16:09:42,177 - src.data.quiver_client - INFO - Initialized Quiver client with rate limit: 60/min
2025-09-12 16:09:42,177 - src.data.market_data_service - INFO - Initialized Market Data Service with 15-minute cache
2025-09-12 16:09:42,177 - src.agents.base_agent - INFO - Initialized agent dan_meuser tracking 1 politicians
2025-09-12 16:09:42,177 - src.agents.individual_agent - INFO - Initialized individual agent dan_meuser tracking: Dan Meuser
2025-09-12 16:09:42,177 - src.agents.agent_factory - INFO - Created agent: dan_meuser (DanMeuserAgent)
2025-09-12 16:09:42,177 - src.data.alpaca_client - INFO - Initialized Alpaca client in paper trading mode
2025-09-12 16:09:42,177 - src.data.quiver_client - INFO - Initialized Quiver client with rate limit: 60/min
2025-09-12 16:09:42,177 - src.data.market_data_service - INFO - Initialized Market Data Service with 15-minute cache
2025-09-12 16:09:42,178 - src.agents.base_agent - INFO - Initialized agent andy_grok tracking 0 politicians
2025-09-12 16:09:42,178 - src.agents.technical_agent - INFO - Initialized technical agent andy_grok for ticker SPY
2025-09-12 16:09:42,178 - src.agents.andy_grok_agent - INFO - Initialized Andy Grok Agent andy_grok - RSI strategy for SPY
2025-09-12 16:09:42,178 - src.agents.andy_grok_agent - INFO - RSI thresholds: oversold < 30.0, overbought > 70.0
2025-09-12 16:09:42,178 - src.agents.agent_factory - INFO - Created agent: andy_grok (AndyGrokAgent)
2025-09-12 16:09:42,178 - src.agents.agent_factory - INFO - Successfully created 6 agents
2025-09-12 16:09:42,178 - src.scheduler.intraday_scheduler - INFO - Added intraday task: transportation_committee_market_open at 09:30
2025-09-12 16:09:42,178 - src.scheduler.intraday_scheduler - INFO - Added congressional agent transportation_committee to market hours scheduler
2025-09-12 16:09:42,178 - __main__ - INFO - Added congressional agent transportation_committee to market hours scheduler
2025-09-12 16:09:42,178 - src.scheduler.intraday_scheduler - INFO - Added intraday task: josh_gottheimer_market_open at 09:30
2025-09-12 16:09:42,178 - src.scheduler.intraday_scheduler - INFO - Added congressional agent josh_gottheimer to market hours scheduler
2025-09-12 16:09:42,178 - __main__ - INFO - Added congressional agent josh_gottheimer to market hours scheduler
2025-09-12 16:09:42,178 - src.scheduler.intraday_scheduler - INFO - Added intraday task: sheldon_whitehouse_market_open at 09:30
2025-09-12 16:09:42,178 - src.scheduler.intraday_scheduler - INFO - Added congressional agent sheldon_whitehouse to market hours scheduler
2025-09-12 16:09:42,178 - __main__ - INFO - Added congressional agent sheldon_whitehouse to market hours scheduler
2025-09-12 16:09:42,178 - src.scheduler.intraday_scheduler - INFO - Added intraday task: nancy_pelosi_market_open at 09:30
2025-09-12 16:09:42,178 - src.scheduler.intraday_scheduler - INFO - Added congressional agent nancy_pelosi to market hours scheduler
2025-09-12 16:09:42,178 - __main__ - INFO - Added congressional agent nancy_pelosi to market hours scheduler
2025-09-12 16:09:42,178 - src.scheduler.intraday_scheduler - INFO - Added intraday task: dan_meuser_market_open at 09:30
2025-09-12 16:09:42,178 - src.scheduler.intraday_scheduler - INFO - Added congressional agent dan_meuser to market hours scheduler
2025-09-12 16:09:42,178 - __main__ - INFO - Added congressional agent dan_meuser to market hours scheduler
2025-09-12 16:09:42,178 - src.scheduler.intraday_scheduler - INFO - Added intraday task: andy_grok_market_open at 09:30
2025-09-12 16:09:42,178 - src.scheduler.intraday_scheduler - INFO - Added intraday task: andy_grok_market_close at 15:55
2025-09-12 16:09:42,178 - src.scheduler.intraday_scheduler - INFO - Added technical agent andy_grok to intraday scheduler
2025-09-12 16:09:42,178 - __main__ - INFO - Added technical agent andy_grok to market hours scheduler
2025-09-12 16:09:42,179 - src.scheduler.intraday_scheduler - INFO - Intraday scheduler loop started
2025-09-12 16:09:42,179 - src.scheduler.intraday_scheduler - INFO - Started intraday scheduler with 7 active tasks
2025-09-12 16:09:42,179 - __main__ - INFO - Market hours scheduler started with 6 total agents

🚀 All agents scheduled for market hours execution!
Congressional agents: 5 (execute at market open 9:30 AM ET)
Technical agents: 1 (full market hours - open & close)
  - andy_grok
Total agents: 6
Health server: http://localhost:8080
Press Ctrl+C to stop all schedulers...

