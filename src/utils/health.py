"""
System health monitoring and reporting.
Provides a health check server and utilities for monitoring system components.
"""
import threading
import time
from datetime import datetime
from flask import Flask, jsonify
from typing import Dict, Any, Callable, Optional

from src.utils.logging import get_logger
from src.data.database import db as database_manager # Use the global instance
from src.data.alpaca_client import alpaca_client # Use the global instance
from src.scheduler.intraday_scheduler import intraday_scheduler # Import the scheduler

logger = get_logger(__name__)

class HealthChecker:
    """Manages and executes health checks for system components."""
    
    def __init__(self):
        self._checks: Dict[str, Callable[[], Dict[str, Any]]] = {}
        self.register_default_checks()

    def register_check(self, name: str, check_func: Callable[[], Dict[str, Any]]):
        """Register a new health check function."""
        self._checks[name] = check_func
        logger.debug(f"Registered health check: {name}")

    def register_default_checks(self):
        """Register default system health checks."""
        self.register_check("database", self._check_database)
        self.register_check("alpaca_api", self._check_alpaca)
        self.register_check("scheduler", self._check_scheduler) # Register the new scheduler check

    def _check_database(self) -> Dict[str, Any]:
        """Check database connection health."""
        try:
            is_connected = database_manager.is_connected()
            return {
                "status": "ok" if is_connected else "error",
                "details": "Database connection is responsive." if is_connected else "Database connection failed."
            }
        except Exception as e:
            return {"status": "error", "details": str(e)}

    def _check_alpaca(self) -> Dict[str, Any]:
        """Check Alpaca API connectivity."""
        try:
            if alpaca_client.is_account_ok():
                return {"status": "ok", "details": "Alpaca API is responsive."}
            else:
                return {"status": "error", "details": "Alpaca account status is not ACTIVE."}
        except Exception as e:
            return {"status": "error", "details": str(e)}

    def _check_scheduler(self) -> Dict[str, Any]:
        """Check the intraday scheduler status."""
        try:
            status = intraday_scheduler.get_status()
            is_running = status.get('running', False)
            return {
                "status": "ok" if is_running else "error",
                "details": {
                    "running": is_running,
                    "active_tasks": status.get('active_tasks', 0),
                    "total_executions": status.get('statistics', {}).get('total_executions', 0),
                    "last_execution": status.get('statistics', {}).get('last_execution_time', 'N/A'),
                    "current_time_et": status.get('market_status', {}).get('current_time_et', 'N/A')
                }
            }
        except Exception as e:
            return {"status": "error", "details": str(e)}

    def get_system_health(self) -> Dict[str, Any]:
        """Execute all registered checks and return an aggregated status."""
        results = {}
        overall_status = "ok"
        
        for name, check_func in self._checks.items():
            result = check_func()
            results[name] = result
            if result["status"] != "ok":
                overall_status = "error"
        
        return {
            "overall_status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "checks": results
        }

class HealthServer:
    """A simple Flask-based server to expose health checks via HTTP."""
    
    def __init__(self, checker: HealthChecker, host: str = '0.0.0.0', port: int = 8080):
        self.app = Flask(__name__)
        self.checker = checker
        self.host = host
        self.port = port
        self._thread: Optional[threading.Thread] = None

        @self.app.route('/health', methods=['GET'])
        def health():
            health_status = self.checker.get_system_health()
            status_code = 200 if health_status["overall_status"] == "ok" else 503
            return jsonify(health_status), status_code
            
        @self.app.route('/ping', methods=['GET'])
        def ping():
            return "pong", 200

    def start(self):
        """Start the health check server in a separate thread."""
        # Skip health server in Railway environment - dashboard handles health checks
        import os
        if os.getenv('RAILWAY_ENVIRONMENT_NAME') or os.getenv('PORT'):
            logger.info("Railway environment detected - skipping health server (dashboard handles health checks)")
            return
            
        if self._thread is not None and self._thread.is_alive():
            logger.warning("Health server is already running.")
            return

        def run_server():
            try:
                logger.info(f"Starting health server on {self.host}:{self.port}")
                # Use a production-grade server if available, otherwise Flask's dev server
                try:
                    from waitress import serve
                    serve(self.app, host=self.host, port=self.port)
                except ImportError:
                    logger.warning("waitress not found, using Flask's development server.")
                    self.app.run(host=self.host, port=self.port)
            except Exception as e:
                logger.error(f"Health server failed to start: {e}", exc_info=True)

        self._thread = threading.Thread(target=run_server, daemon=True)
        self._thread.start()
        
    def stop(self):
        """Stop the health check server."""
        import os
        if os.getenv('RAILWAY_ENVIRONMENT_NAME') or os.getenv('PORT'):
            logger.info("Railway environment - health server was not started")
            return
            
        # This is a bit tricky with daemon threads and servers.
        # For this app, we'll just let the daemon thread die with the main process.
        logger.info("Health server stopped")


# Global instances to be used across the application
health_checker = HealthChecker()
health_server = HealthServer(health_checker)