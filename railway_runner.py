#!/usr/bin/env python3
"""
Railway-specific runner that serves the dashboard (always) and optionally starts
the intraday scheduler when explicitly enabled via environment variable.
"""

import os
import sys
import time
import signal
import threading
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import settings
from src.data.database import initialize_database
from src.dashboard.api import create_app
from src.utils.logging import get_logger

logger = get_logger(__name__)

class RailwayRunner:
    def __init__(self):
        self.dashboard_thread = None
        self.scheduler_thread = None
        self.shutdown_event = threading.Event()
        
    def start_dashboard(self):
        """Start the dashboard in a separate thread"""
        def run_dashboard():
            try:
                # Use Railway's PORT environment variable
                port = int(os.getenv('PORT', '5000'))
                
                logger.info(f"Starting dashboard on port {port}")
                
                # Initialize database
                initialize_database()
                
                # Create Flask app
                app = create_app()
                
                # Run dashboard
                app.run(
                    host='0.0.0.0',
                    port=port,
                    debug=False,
                    use_reloader=False
                )
            except Exception as e:
                logger.error(f"Dashboard failed: {e}")
                self.shutdown_event.set()
                
        self.dashboard_thread = threading.Thread(target=run_dashboard, daemon=True)
        self.dashboard_thread.start()
        logger.info("Dashboard thread started")
        
    def start_scheduler(self):
        """Start the scheduler in a separate NON-DAEMON thread to keep process alive"""
        def run_scheduler():
            try:
                # Only start scheduler if all required env vars are present
                required_vars = ['ALPACA_API_KEY', 'ALPACA_SECRET_KEY', 'QUIVER_API_KEY']
                missing_vars = [var for var in required_vars if not os.getenv(var)]
                
                if missing_vars:
                    logger.warning(f"Scheduler disabled - missing env vars: {missing_vars}")
                    return
                    
                logger.info("Starting trading scheduler...")
                
                # Force logs to STDOUT for Railway visibility
                import logging
                logging.basicConfig(
                    level=logging.INFO,
                    format="%(asctime)s %(levelname)s [%(process)d:%(threadName)s] %(name)s: %(message)s",
                    handlers=[logging.StreamHandler(sys.stdout)],
                    force=True
                )
                
                # Add startup breadcrumbs
                import tzlocal
                from datetime import datetime
                logger.info(f"Process PID={os.getpid()} tz={tzlocal.get_localzone_name()} now_local={datetime.now().astimezone()}")
                
                # Import and run scheduler - but keep the thread alive!
                from src.scheduler.intraday_scheduler import IntradayScheduler
                from src.agents.agent_factory import AgentFactory
                from src.data.database import initialize_database
                
                # Initialize components
                initialize_database()
                agent_factory = AgentFactory()
                agents = agent_factory.create_all_agents()
                scheduler = IntradayScheduler()
                
                # Add all agents to scheduler
                for agent in agents:
                    if hasattr(agent, 'agent_type') and agent.agent_type == 'technical':
                        scheduler.add_technical_agent(agent)
                    else:
                        scheduler.add_congressional_agent(agent)
                
                logger.info(f"Tasks loaded: {list(scheduler.tasks.keys())}")
                logger.info(f"Current ET time: {datetime.now(scheduler.market_tz)}")
                
                # Start scheduler and keep running (non-daemon behavior)
                scheduler.start()
                
                # CRITICAL: Run catch-up reconciliation immediately for late starts
                logger.info("Running startup reconciliation for missed executions...")
                missed_count = 0
                for task in scheduler.tasks.values():
                    if task.enabled and scheduler._should_fire_now(task):
                        logger.info(f"Catch-up firing task: {task.task_id}")
                        scheduler._execute_task(task)
                        missed_count += 1
                logger.info(f"Startup reconciliation complete: {missed_count} tasks fired")
                
                # Keep this thread alive with a heartbeat loop
                import time
                while not self.shutdown_event.is_set():
                    time.sleep(60)
                    if int(time.time()) % 300 == 0:  # Every 5 minutes
                        logger.info(f"Scheduler heartbeat: {len(scheduler.tasks)} tasks active")
                
            except Exception as e:
                logger.exception(f"Scheduler failed with exception: {e}")
                self.shutdown_event.set()
                
        # Only start scheduler thread if environment variables are available  
        if os.getenv('ALPACA_API_KEY') and os.getenv('QUIVER_API_KEY'):
            # NON-DAEMON thread so process stays alive!
            self.scheduler_thread = threading.Thread(target=run_scheduler, daemon=False, name="TradingScheduler")
            self.scheduler_thread.start()
            logger.info("NON-DAEMON scheduler thread started - process will stay alive")
        else:
            logger.info("Scheduler not started - missing API credentials")
        
    def run(self):
        """Main run method"""
        logger.info("Starting Railway Trading Automation System v2.0 - Fixed Process Lifecycle")
        
        # Debug environment variables
        api_keys_status = {
            'QUIVER_API_KEY': 'SET' if os.getenv('QUIVER_API_KEY') else 'MISSING',
            'ALPACA_API_KEY': 'SET' if os.getenv('ALPACA_API_KEY') else 'MISSING', 
            'ALPACA_SECRET_KEY': 'SET' if os.getenv('ALPACA_SECRET_KEY') else 'MISSING',
            'PORT': os.getenv('PORT', 'NOT_SET')
        }
        logger.info(f"Environment variables status: {api_keys_status}")
        
        # Set up signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        try:
            # Start dashboard (required)
            self.start_dashboard()

            # Start scheduler only when explicitly enabled (e.g. intraday agents)
            enable_intraday = os.getenv('ENABLE_INTRADAY_WORKER', 'false').lower() == 'true'
            if enable_intraday:
                self.start_scheduler()
            else:
                logger.info("Intraday scheduler disabled (ENABLE_INTRADAY_WORKER!=true). Use Railway Cron for daily runs.")
            
            # Wait for shutdown signal or dashboard failure
            while not self.shutdown_event.is_set():
                time.sleep(1)
                
                # Check if dashboard thread is still alive
                if self.dashboard_thread and not self.dashboard_thread.is_alive():
                    logger.error("Dashboard thread died")
                    break
                    
        except KeyboardInterrupt:
            logger.info("Shutdown requested")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
        finally:
            self._cleanup()
            
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.shutdown_event.set()
        
    def _cleanup(self):
        """Clean up resources"""
        logger.info("Cleaning up...")
        self.shutdown_event.set()

if __name__ == '__main__':
    runner = RailwayRunner()
    runner.run()
