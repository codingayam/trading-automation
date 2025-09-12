#!/usr/bin/env python3
"""
Railway-specific runner that starts both dashboard and scheduler in one process.
This avoids supervisord complexity and Railway deployment issues.
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
        """Start the scheduler in a separate thread (optional)"""
        def run_scheduler():
            try:
                # Only start scheduler if all required env vars are present
                required_vars = ['ALPACA_API_KEY', 'ALPACA_SECRET_KEY', 'QUIVER_API_KEY']
                missing_vars = [var for var in required_vars if not os.getenv(var)]
                
                if missing_vars:
                    logger.warning(f"Scheduler disabled - missing env vars: {missing_vars}")
                    return
                    
                logger.info("Starting trading scheduler...")
                
                # Import and run scheduler
                from main import main as run_main
                sys.argv = ['main.py', 'start']
                run_main()
                
            except Exception as e:
                logger.error(f"Scheduler failed: {e}")
                # Don't shutdown on scheduler failure - dashboard can still work
                
        # Only start scheduler thread if environment variables are available
        if os.getenv('ALPACA_API_KEY') and os.getenv('QUIVER_API_KEY'):
            self.scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
            self.scheduler_thread.start()
            logger.info("Scheduler thread started")
        else:
            logger.info("Scheduler not started - missing API credentials")
        
    def run(self):
        """Main run method"""
        logger.info("Starting Railway Trading Automation System")
        
        # Set up signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        try:
            # Start dashboard (required)
            self.start_dashboard()
            
            # Start scheduler (optional)
            self.start_scheduler()
            
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