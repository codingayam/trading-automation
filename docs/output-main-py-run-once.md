2025-09-12 14:50:14,488 - monitoring - INFO - Default health checks registered
2025-09-12 14:50:15,160 - health - INFO - External dependency health checks registered
2025-09-12 14:50:15,162 - src.agents.agent_factory - INFO - Initialized Agent Factory
2025-09-12 14:50:15,162 - src.data.quiver_client - INFO - Initialized Quiver client with rate limit: 60/min
2025-09-12 14:50:15,162 - src.data.alpaca_client - INFO - Initialized Alpaca client in paper trading mode
2025-09-12 14:50:15,178 - src.data.market_data_service - INFO - Initialized Market Data Service with 15-minute cache
2025-09-12 14:50:15,178 - src.data.data_processor - INFO - Initialized Data Processing Engine
2025-09-12 14:50:15,178 - src.scheduler.daily_runner - INFO - Initialized Daily Runner
2025-09-12 14:50:15,178 - src.scheduler.daily_runner - INFO - Scheduled execution time: 21:30 US/Eastern
2025-09-12 14:50:15,179 - src.scheduler.intraday_scheduler - INFO - Initialized Intraday Scheduler
2025-09-12 14:50:15,181 - __main__ - INFO - Starting Trading Automation System - Command: run-once
2025-09-12 14:50:15,181 - __main__ - INFO - Running daily workflow for 2025-09-12
2025-09-12 14:50:15,181 - src.scheduler.daily_runner - INFO - Manual execution requested for 2025-09-12
2025-09-12 14:50:15,181 - src.scheduler.daily_runner - INFO - Starting daily workflow execution for 2025-09-12
2025-09-12 14:50:15,181 - src.scheduler.daily_runner - INFO - Step 1: Processing congressional data
2025-09-12 14:50:15,181 - src.data.data_processor - INFO - Starting daily data processing for 2025-09-12
2025-09-12 14:50:15,185 - database - INFO - Database backup created
2025-09-12 14:50:15,186 - src.data.data_processor - INFO - Data backup created successfully
2025-09-12 14:50:15,186 - src.data.data_processor - INFO - Step 1: Fetching congressional trades
2025-09-12 14:50:15,186 - src.data.quiver_client - INFO - Fetching congressional trades for 2025-09-12
2025-09-12 14:50:15,806 - monitoring - INFO - Performance metric quiver_api_request_execution_time: 0.6201720237731934
2025-09-12 14:50:15,806 - src.data.quiver_client - INFO - Quiver API request completed in 0.62s, status: 200
2025-09-12 14:50:15,807 - src.data.quiver_client - INFO - Received 0 raw congressional trades
2025-09-12 14:50:15,807 - monitoring - INFO - Performance metric quiver_trades_processing_execution_time: 0.6211230754852295
2025-09-12 14:50:15,807 - src.data.quiver_client - INFO - Processed 0 congressional trades after filtering
2025-09-12 14:50:15,807 - src.data.data_processor - INFO - Fetched 0 congressional trades for 2025-09-12
2025-09-12 14:50:15,807 - src.data.data_processor - INFO - Step 2: Processing trades for agents
2025-09-12 14:50:15,807 - src.data.data_processor - INFO - No congressional trades to process
2025-09-12 14:50:15,807 - src.data.data_processor - INFO - Step 3: Synchronizing portfolios
2025-09-12 14:50:16,789 - monitoring - INFO - Performance metric alpaca_get_all_positions_execution_time: 0.9816648960113525
2025-09-12 14:50:16,790 - src.data.alpaca_client - INFO - Retrieved 13 positions
2025-09-12 14:50:16,791 - src.data.data_processor - INFO - Updated 0 positions for agent transportation_committee
2025-09-12 14:50:16,791 - src.data.data_processor - INFO - Updated 0 positions for agent josh_gottheimer
2025-09-12 14:50:16,791 - src.data.data_processor - INFO - Updated 0 positions for agent sheldon_whitehouse
2025-09-12 14:50:16,791 - src.data.data_processor - INFO - Updated 0 positions for agent nancy_pelosi
2025-09-12 14:50:16,791 - src.data.data_processor - INFO - Updated 0 positions for agent dan_meuser
2025-09-12 14:50:16,791 - src.data.data_processor - INFO - Updated 0 positions for agent andy_grok
2025-09-12 14:50:16,792 - src.data.data_processor - INFO - Step 4: Updating performance metrics
2025-09-12 14:50:16,792 - src.data.data_processor - INFO - Updated performance metrics for agent transportation_committee: $0.00 (+0.00%)
2025-09-12 14:50:16,792 - src.data.data_processor - INFO - Updated performance metrics for agent josh_gottheimer: $0.00 (+0.00%)
2025-09-12 14:50:16,793 - src.data.data_processor - INFO - Updated performance metrics for agent sheldon_whitehouse: $0.00 (+0.00%)
2025-09-12 14:50:16,793 - src.data.data_processor - INFO - Updated performance metrics for agent nancy_pelosi: $0.00 (+0.00%)
2025-09-12 14:50:16,793 - src.data.data_processor - INFO - Updated performance metrics for agent dan_meuser: $0.00 (+0.00%)
2025-09-12 14:50:16,793 - src.data.data_processor - INFO - Updated performance metrics for agent andy_grok: $0.00 (+0.00%)
2025-09-12 14:50:16,794 - src.data.data_processor - INFO - Step 5: Validating and reconciling data
2025-09-12 14:50:17,028 - monitoring - INFO - Performance metric alpaca_get_account_execution_time: 0.2339611053466797
2025-09-12 14:50:17,028 - src.data.alpaca_client - INFO - Account info: buying_power=$183451.89, portfolio_value=$99696.06
2025-09-12 14:50:17,028 - src.data.alpaca_client - INFO - Alpaca API connection test successful, account: PA3JY395399D
2025-09-12 14:50:17,028 - src.data.quiver_client - INFO - Quiver API connection test successful
2025-09-12 14:50:17,265 - monitoring - INFO - Performance metric alpaca_get_all_positions_execution_time: 0.23613309860229492
2025-09-12 14:50:17,265 - src.data.alpaca_client - INFO - Retrieved 13 positions
2025-09-12 14:50:17,266 - src.data.data_processor - INFO - Daily data processing completed successfully in 2.08s
2025-09-12 14:50:17,266 - monitoring - INFO - Performance metric daily_processing_execution_time: 2.0849220752716064
2025-09-12 14:50:17,266 - src.data.quiver_client - INFO - Fetching congressional trades for 2025-09-12
2025-09-12 14:50:17,266 - src.data.quiver_client - INFO - Received 0 raw congressional trades
2025-09-12 14:50:17,266 - monitoring - INFO - Performance metric quiver_trades_processing_execution_time: 0.00014209747314453125
2025-09-12 14:50:17,266 - src.data.quiver_client - INFO - Processed 0 congressional trades after filtering
2025-09-12 14:50:17,266 - src.scheduler.daily_runner - INFO - Step 2: Executing trading agents
2025-09-12 14:50:17,266 - src.agents.agent_factory - INFO - Creating 6 agents from configuration
2025-09-12 14:50:17,267 - src.data.alpaca_client - INFO - Initialized Alpaca client in paper trading mode
2025-09-12 14:50:17,267 - src.data.quiver_client - INFO - Initialized Quiver client with rate limit: 60/min
2025-09-12 14:50:17,267 - src.data.market_data_service - INFO - Initialized Market Data Service with 15-minute cache
2025-09-12 14:50:17,267 - src.agents.base_agent - INFO - Initialized agent transportation_committee tracking 10 politicians
2025-09-12 14:50:17,267 - src.agents.committee_agent - INFO - Initialized committee agent transportation_committee tracking 10 politicians
2025-09-12 14:50:17,268 - src.agents.agent_factory - INFO - Created agent: transportation_committee (TransportationCommitteeAgent)
2025-09-12 14:50:17,268 - src.data.alpaca_client - INFO - Initialized Alpaca client in paper trading mode
2025-09-12 14:50:17,268 - src.data.quiver_client - INFO - Initialized Quiver client with rate limit: 60/min
2025-09-12 14:50:17,268 - src.data.market_data_service - INFO - Initialized Market Data Service with 15-minute cache
2025-09-12 14:50:17,268 - src.agents.base_agent - INFO - Initialized agent josh_gottheimer tracking 1 politicians
2025-09-12 14:50:17,268 - src.agents.individual_agent - INFO - Initialized individual agent josh_gottheimer tracking: Josh Gottheimer
2025-09-12 14:50:17,268 - src.agents.agent_factory - INFO - Created agent: josh_gottheimer (JoshGottheimerAgent)
2025-09-12 14:50:17,269 - src.data.alpaca_client - INFO - Initialized Alpaca client in paper trading mode
2025-09-12 14:50:17,269 - src.data.quiver_client - INFO - Initialized Quiver client with rate limit: 60/min
2025-09-12 14:50:17,269 - src.data.market_data_service - INFO - Initialized Market Data Service with 15-minute cache
2025-09-12 14:50:17,269 - src.agents.base_agent - INFO - Initialized agent sheldon_whitehouse tracking 1 politicians
2025-09-12 14:50:17,269 - src.agents.individual_agent - INFO - Initialized individual agent sheldon_whitehouse tracking: Sheldon Whitehouse
2025-09-12 14:50:17,269 - src.agents.agent_factory - INFO - Created agent: sheldon_whitehouse (SheldonWhitehouseAgent)
2025-09-12 14:50:17,269 - src.data.alpaca_client - INFO - Initialized Alpaca client in paper trading mode
2025-09-12 14:50:17,269 - src.data.quiver_client - INFO - Initialized Quiver client with rate limit: 60/min
2025-09-12 14:50:17,269 - src.data.market_data_service - INFO - Initialized Market Data Service with 15-minute cache
2025-09-12 14:50:17,269 - src.agents.base_agent - INFO - Initialized agent nancy_pelosi tracking 1 politicians
2025-09-12 14:50:17,270 - src.agents.individual_agent - INFO - Initialized individual agent nancy_pelosi tracking: Nancy Pelosi
2025-09-12 14:50:17,270 - src.agents.agent_factory - INFO - Created agent: nancy_pelosi (NancyPelosiAgent)
2025-09-12 14:50:17,270 - src.data.alpaca_client - INFO - Initialized Alpaca client in paper trading mode
2025-09-12 14:50:17,270 - src.data.quiver_client - INFO - Initialized Quiver client with rate limit: 60/min
2025-09-12 14:50:17,270 - src.data.market_data_service - INFO - Initialized Market Data Service with 15-minute cache
2025-09-12 14:50:17,270 - src.agents.base_agent - INFO - Initialized agent dan_meuser tracking 1 politicians
2025-09-12 14:50:17,270 - src.agents.individual_agent - INFO - Initialized individual agent dan_meuser tracking: Dan Meuser
2025-09-12 14:50:17,270 - src.agents.agent_factory - INFO - Created agent: dan_meuser (DanMeuserAgent)
2025-09-12 14:50:17,271 - src.data.alpaca_client - INFO - Initialized Alpaca client in paper trading mode
2025-09-12 14:50:17,272 - src.data.quiver_client - INFO - Initialized Quiver client with rate limit: 60/min
2025-09-12 14:50:17,272 - src.data.market_data_service - INFO - Initialized Market Data Service with 15-minute cache
2025-09-12 14:50:17,272 - src.agents.base_agent - INFO - Initialized agent andy_grok tracking 0 politicians
2025-09-12 14:50:17,272 - src.agents.technical_agent - INFO - Initialized technical agent andy_grok for ticker SPY
2025-09-12 14:50:17,272 - src.agents.andy_grok_agent - INFO - Initialized Andy Grok Agent andy_grok - RSI strategy for SPY
2025-09-12 14:50:17,272 - src.agents.andy_grok_agent - INFO - RSI thresholds: oversold < 30.0, overbought > 70.0
2025-09-12 14:50:17,272 - src.agents.agent_factory - INFO - Created agent: andy_grok (AndyGrokAgent)
2025-09-12 14:50:17,272 - src.agents.agent_factory - INFO - Successfully created 6 agents
2025-09-12 14:50:17,272 - src.agents.agent_factory - INFO - Executing 6 agents in parallel
2025-09-12 14:50:17,273 - src.agents.base_agent - INFO - Starting daily workflow for agent transportation_committee
2025-09-12 14:50:17,273 - src.agents.base_agent - INFO - Starting daily workflow for agent josh_gottheimer
2025-09-12 14:50:17,273 - src.agents.base_agent - INFO - Agent transportation_committee processing 0 congressional trades
2025-09-12 14:50:17,274 - src.agents.base_agent - INFO - Starting daily workflow for agent sheldon_whitehouse
2025-09-12 14:50:17,274 - src.agents.base_agent - INFO - Agent josh_gottheimer processing 0 congressional trades
2025-09-12 14:50:17,274 - src.agents.base_agent - INFO - Starting daily workflow for agent nancy_pelosi
2025-09-12 14:50:17,274 - monitoring - INFO - Performance metric agent_transportation_committee_processing_execution_time: 1.1920928955078125e-06
2025-09-12 14:50:17,274 - src.agents.base_agent - INFO - Starting daily workflow for agent dan_meuser
2025-09-12 14:50:17,274 - src.agents.base_agent - INFO - Agent sheldon_whitehouse processing 0 congressional trades
2025-09-12 14:50:17,274 - monitoring - INFO - Performance metric agent_josh_gottheimer_processing_execution_time: 0.0
2025-09-12 14:50:17,275 - src.agents.base_agent - INFO - Agent nancy_pelosi processing 0 congressional trades
2025-09-12 14:50:17,275 - monitoring - INFO - Performance metric agent_nancy_pelosi_processing_execution_time: 0.0
2025-09-12 14:50:17,275 - src.agents.base_agent - INFO - Agent dan_meuser processing 0 congressional trades
2025-09-12 14:50:17,275 - monitoring - INFO - Performance metric agent_sheldon_whitehouse_processing_execution_time: 9.5367431640625e-07
2025-09-12 14:50:17,275 - src.agents.base_agent - INFO - Agent josh_gottheimer generated 0 trade decisions in 0.00s
2025-09-12 14:50:17,276 - src.agents.base_agent - INFO - Agent nancy_pelosi generated 0 trade decisions in 0.00s
2025-09-12 14:50:17,275 - src.agents.base_agent - INFO - Agent transportation_committee generated 0 trade decisions in 0.00s
2025-09-12 14:50:17,276 - monitoring - INFO - Performance metric agent_dan_meuser_processing_execution_time: 9.5367431640625e-07
2025-09-12 14:50:17,276 - src.agents.base_agent - INFO - Agent sheldon_whitehouse generated 0 trade decisions in 0.00s
2025-09-12 14:50:17,276 - src.agents.base_agent - INFO - Updating positions for agent josh_gottheimer
2025-09-12 14:50:17,276 - src.agents.base_agent - INFO - Updating positions for agent nancy_pelosi
2025-09-12 14:50:17,276 - src.agents.base_agent - INFO - Updating positions for agent transportation_committee
2025-09-12 14:50:17,277 - src.agents.base_agent - INFO - Agent dan_meuser generated 0 trade decisions in 0.00s
2025-09-12 14:50:17,277 - src.agents.base_agent - INFO - Updating positions for agent sheldon_whitehouse
2025-09-12 14:50:17,277 - src.agents.base_agent - INFO - Updating positions for agent dan_meuser
2025-09-12 14:50:18,441 - monitoring - INFO - Performance metric alpaca_get_all_positions_execution_time: 1.1630990505218506
2025-09-12 14:50:18,442 - src.data.alpaca_client - INFO - Retrieved 13 positions
2025-09-12 14:50:18,442 - monitoring - INFO - Performance metric alpaca_get_all_positions_execution_time: 1.158778190612793
2025-09-12 14:50:18,443 - monitoring - INFO - Performance metric alpaca_get_all_positions_execution_time: 1.1628806591033936
2025-09-12 14:50:18,443 - monitoring - INFO - Performance metric alpaca_get_all_positions_execution_time: 1.163599967956543
2025-09-12 14:50:18,443 - src.data.alpaca_client - INFO - Retrieved 13 positions
2025-09-12 14:50:18,445 - monitoring - INFO - Performance metric alpaca_get_all_positions_execution_time: 1.1653790473937988
2025-09-12 14:50:18,445 - src.data.alpaca_client - INFO - Retrieved 13 positions
2025-09-12 14:50:18,446 - src.data.alpaca_client - INFO - Retrieved 13 positions
2025-09-12 14:50:18,445 - src.data.alpaca_client - INFO - Retrieved 13 positions
2025-09-12 14:50:18,445 - src.agents.base_agent - INFO - Updated 0 positions for agent josh_gottheimer
2025-09-12 14:50:18,446 - src.agents.base_agent - INFO - Performance for agent josh_gottheimer: $0.00 (+0.00%)
2025-09-12 14:50:18,446 - src.agents.base_agent - INFO - Daily workflow completed for agent josh_gottheimer: 0/0 trades executed
2025-09-12 14:50:18,446 - monitoring - INFO - Performance metric agent_josh_gottheimer_daily_workflow_execution_time: 1.1727521419525146
2025-09-12 14:50:18,446 - src.agents.base_agent - INFO - Starting daily workflow for agent andy_grok
2025-09-12 14:50:18,446 - src.agents.technical_agent - INFO - Technical agent andy_grok ignoring congressional trades, using technical strategy
2025-09-12 14:50:18,446 - src.agents.technical_agent - INFO - Technical agent andy_grok processing strategy for SPY
2025-09-12 14:50:18,446 - src.agents.agent_factory - INFO - Agent josh_gottheimer completed successfully
2025-09-12 14:50:18,447 - src.agents.base_agent - INFO - Updated 0 positions for agent transportation_committee
2025-09-12 14:50:18,447 - src.agents.base_agent - INFO - Performance for agent transportation_committee: $0.00 (+0.00%)
2025-09-12 14:50:18,447 - src.agents.base_agent - INFO - Daily workflow completed for agent transportation_committee: 0/0 trades executed
2025-09-12 14:50:18,448 - monitoring - INFO - Performance metric agent_transportation_committee_daily_workflow_execution_time: 1.1745860576629639
2025-09-12 14:50:18,448 - src.agents.agent_factory - INFO - Agent transportation_committee completed successfully
2025-09-12 14:50:18,449 - src.agents.base_agent - INFO - Updated 0 positions for agent sheldon_whitehouse
2025-09-12 14:50:18,450 - src.agents.base_agent - INFO - Performance for agent sheldon_whitehouse: $0.00 (+0.00%)
2025-09-12 14:50:18,450 - src.agents.base_agent - INFO - Daily workflow completed for agent sheldon_whitehouse: 0/0 trades executed
2025-09-12 14:50:18,450 - monitoring - INFO - Performance metric agent_sheldon_whitehouse_daily_workflow_execution_time: 1.1762340068817139
2025-09-12 14:50:18,450 - src.agents.agent_factory - INFO - Agent sheldon_whitehouse completed successfully
2025-09-12 14:50:18,456 - src.agents.base_agent - INFO - Updated 0 positions for agent nancy_pelosi
2025-09-12 14:50:18,456 - src.agents.base_agent - INFO - Performance for agent nancy_pelosi: $0.00 (+0.00%)
2025-09-12 14:50:18,456 - src.agents.base_agent - INFO - Daily workflow completed for agent nancy_pelosi: 0/0 trades executed
2025-09-12 14:50:18,456 - monitoring - INFO - Performance metric agent_nancy_pelosi_daily_workflow_execution_time: 1.182337760925293
2025-09-12 14:50:18,456 - src.agents.agent_factory - INFO - Agent nancy_pelosi completed successfully
2025-09-12 14:50:18,468 - src.agents.base_agent - INFO - Updated 0 positions for agent dan_meuser
2025-09-12 14:50:18,469 - src.agents.base_agent - INFO - Performance for agent dan_meuser: $0.00 (+0.00%)
2025-09-12 14:50:18,469 - src.agents.base_agent - INFO - Daily workflow completed for agent dan_meuser: 0/0 trades executed
2025-09-12 14:50:18,469 - monitoring - INFO - Performance metric agent_dan_meuser_daily_workflow_execution_time: 1.1945829391479492
2025-09-12 14:50:18,469 - src.agents.agent_factory - INFO - Agent dan_meuser completed successfully
2025-09-12 14:50:19,564 - monitoring - INFO - Performance metric alpaca_get_account_execution_time: 1.1176578998565674
2025-09-12 14:50:19,565 - src.data.alpaca_client - INFO - Account info: buying_power=$183451.89, portfolio_value=$99696.06
2025-09-12 14:50:19,988 - src.utils.technical_indicators - WARNING - Data is stale: latest data from 2025-09-11 15:30:00-04:00
2025-09-12 14:50:19,989 - src.agents.andy_grok_agent - INFO - RSI calculated: 77.70 → short (confidence: 0.51)
2025-09-12 14:50:19,989 - src.agents.andy_grok_agent - INFO - Generated signal: short from RSI 77.70
2025-09-12 14:50:20,138 - monitoring - INFO - Performance metric yfinance_current_price_execution_time: 0.1481800079345703
2025-09-12 14:50:20,139 - src.agents.technical_agent - INFO - Technical agent andy_grok generated 1 trade decisions
2025-09-12 14:50:20,139 - src.agents.base_agent - INFO - Executing trade: SPY sell $996.96
2025-09-12 14:50:21,288 - monitoring - INFO - Performance metric yfinance_current_price_execution_time: 0.10511994361877441
2025-09-12 14:50:21,289 - src.agents.base_agent - INFO - Converting short order to 1 shares ($657.63)
2025-09-12 14:50:21,611 - src.data.alpaca_client - INFO - Placing market order: sell 1 shares of SPY
2025-09-12 14:50:21,919 - monitoring - INFO - Performance metric alpaca_submit_order_execution_time: 0.3066859245300293
2025-09-12 14:50:21,920 - src.data.alpaca_client - INFO - Order placed successfully: 62f066b5-65dc-4d85-acd0-6e5112f58a68
2025-09-12 14:50:21,920 - monitoring - INFO - Performance metric order_placement_success_execution_time: 1
2025-09-12 14:50:21,921 - database - INFO - Trade record inserted
2025-09-12 14:50:21,922 - src.agents.base_agent - INFO - Successfully executed trade: SPY - Order ID: 62f066b5-65dc-4d85-acd0-6e5112f58a68
2025-09-12 14:50:21,922 - src.agents.base_agent - INFO - Updating positions for agent andy_grok
2025-09-12 14:50:22,161 - monitoring - INFO - Performance metric alpaca_get_all_positions_execution_time: 0.23900508880615234
2025-09-12 14:50:22,162 - src.data.alpaca_client - INFO - Retrieved 13 positions
2025-09-12 14:50:22,162 - src.agents.base_agent - INFO - Updated 0 positions for agent andy_grok
2025-09-12 14:50:22,162 - src.agents.base_agent - INFO - Performance for agent andy_grok: $0.00 (+0.00%)
2025-09-12 14:50:22,162 - src.agents.base_agent - INFO - Daily workflow completed for agent andy_grok: 1/1 trades executed
2025-09-12 14:50:22,163 - monitoring - INFO - Performance metric agent_andy_grok_daily_workflow_execution_time: 3.716317892074585
2025-09-12 14:50:22,163 - src.agents.agent_factory - INFO - Agent andy_grok completed successfully
2025-09-12 14:50:22,165 - src.agents.agent_factory - INFO - Agent execution completed in 4.89s: 6/6 agents successful, 1 trades processed, 1 orders placed
2025-09-12 14:50:22,165 - monitoring - INFO - Performance metric all_agents_execution_execution_time: 4.8926239013671875
2025-09-12 14:50:22,165 - src.scheduler.daily_runner - INFO - Step 3: Performing system health checks
2025-09-12 14:50:22,166 - src.data.quiver_client - INFO - Quiver API connection test successful
2025-09-12 14:50:22,431 - monitoring - INFO - Performance metric alpaca_get_account_execution_time: 0.26465392112731934
2025-09-12 14:50:22,431 - src.data.alpaca_client - INFO - Account info: buying_power=$182774.45, portfolio_value=$99696.06
2025-09-12 14:50:22,431 - src.data.alpaca_client - INFO - Alpaca API connection test successful, account: PA3JY395399D
2025-09-12 14:50:22,645 - monitoring - INFO - Performance metric yfinance_current_price_execution_time: 0.21413779258728027
2025-09-12 14:50:22,647 - src.scheduler.daily_runner - INFO - Step 4: Finalizing execution
2025-09-12 14:50:22,647 - src.scheduler.daily_runner - INFO - Daily execution SUCCESS for 2025-09-12
2025-09-12 14:50:22,647 - src.scheduler.daily_runner - INFO - Duration: 7.47s
2025-09-12 14:50:22,648 - src.scheduler.daily_runner - INFO - Agents: 6 successful, 0 failed
2025-09-12 14:50:22,648 - src.scheduler.daily_runner - INFO - Trades: 1 processed, 1 orders placed
2025-09-12 14:50:22,648 - monitoring - INFO - Performance metric daily_workflow_execution_time: 7.466199

============================================================
EXECUTION SUMMARY - 2025-09-12
============================================================
Status: SUCCESS
Duration: 7.47 seconds
Agents executed: 6 successful, 0 failed
Trades processed: 1
Orders placed: 1
============================================================