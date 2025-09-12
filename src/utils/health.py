"""
Health check endpoints and utilities for trading automation system.
Provides HTTP endpoints for monitoring system health and status.
"""
from flask import Flask, jsonify, request
from typing import Dict, Any
from enum import Enum
import threading
import time

class HealthStatus(Enum):
    """Health status enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    DISABLED = "disabled"

from src.utils.monitoring import health_checker, metrics_collector, system_monitor
from src.utils.logging import get_logger

logger = get_logger('health')

def create_health_app() -> Flask:
    """Create Flask app for health check endpoints."""
    app = Flask(__name__)
    
    @app.route('/health', methods=['GET'])
    def health_check():
        """Get overall system health status."""
        try:
            health_status = health_checker.get_system_health()
            
            # Set HTTP status code based on health
            status_code = 200
            if health_status['status'] == 'unhealthy':
                status_code = 503
            elif health_status['status'] == 'warning':
                status_code = 200  # Still OK, but with warnings
            
            return jsonify(health_status), status_code
            
        except Exception as e:
            logger.error("Health check endpoint failed", exception=e)
            return jsonify({
                'status': 'unhealthy',
                'message': f'Health check failed: {str(e)}',
                'timestamp': time.time()
            }), 503
    
    @app.route('/health/<component>', methods=['GET'])
    def component_health(component: str):
        """Get health status for specific component."""
        try:
            result = health_checker.run_check(component)
            
            status_code = 200
            if result.status == 'unhealthy':
                status_code = 503
            
            return jsonify({
                'component': result.component,
                'status': result.status,
                'message': result.message,
                'timestamp': result.timestamp.isoformat(),
                'response_time': result.response_time,
                'details': result.details
            }), status_code
            
        except Exception as e:
            logger.error(f"Component health check failed for {component}", exception=e)
            return jsonify({
                'component': component,
                'status': 'unhealthy',
                'message': f'Health check failed: {str(e)}',
                'timestamp': time.time()
            }), 503
    
    @app.route('/metrics', methods=['GET'])
    def metrics():
        """Get performance metrics summary."""
        try:
            # Get query parameters
            metric_name = request.args.get('metric')
            hours = int(request.args.get('hours', 24))
            
            if metric_name:
                # Get specific metric
                from datetime import datetime, timedelta
                since = datetime.now() - timedelta(hours=hours)
                summary = metrics_collector.get_metric_summary(metric_name, since)
                return jsonify({
                    'metric': metric_name,
                    'summary': summary,
                    'hours': hours
                })
            else:
                # Get all metrics
                summaries = metrics_collector.get_all_metrics_summary()
                return jsonify({
                    'metrics': summaries,
                    'timestamp': time.time()
                })
                
        except Exception as e:
            logger.error("Metrics endpoint failed", exception=e)
            return jsonify({
                'error': f'Metrics collection failed: {str(e)}',
                'timestamp': time.time()
            }), 500
    
    @app.route('/system', methods=['GET'])
    def system_stats():
        """Get system resource statistics."""
        try:
            stats = system_monitor.get_system_stats()
            return jsonify(stats)
            
        except Exception as e:
            logger.error("System stats endpoint failed", exception=e)
            return jsonify({
                'error': f'System stats collection failed: {str(e)}',
                'timestamp': time.time()
            }), 500
    
    @app.route('/ping', methods=['GET'])
    def ping():
        """Simple ping endpoint for basic availability check."""
        return jsonify({
            'status': 'ok',
            'message': 'Trading automation system is running',
            'timestamp': time.time()
        })
    
    return app

class HealthServer:
    """HTTP server for health check endpoints."""
    
    def __init__(self, host: str = '0.0.0.0', port: int = 8080):
        self.host = host
        self.port = port
        self.app = create_health_app()
        self.server_thread = None
        self.running = False
    
    def start(self):
        """Start the health check server in a background thread."""
        if self.running:
            logger.warning("Health server is already running")
            return
        
        def run_server():
            try:
                logger.info(f"Starting health server on {self.host}:{self.port}")
                self.app.run(
                    host=self.host,
                    port=self.port,
                    debug=False,
                    use_reloader=False,
                    threaded=True
                )
            except Exception as e:
                logger.error("Health server failed to start", exception=e)
        
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        self.running = True
        
        logger.info(f"Health server started on {self.host}:{self.port}")
    
    def stop(self):
        """Stop the health check server."""
        if not self.running:
            return
        
        self.running = False
        logger.info("Health server stopped")

def check_external_dependencies() -> Dict[str, Any]:
    """Check external service dependencies."""
    results = {}
    
    # Check Quiver API connectivity
    try:
        from config.settings import settings
        import requests
        
        # Skip if API key is not configured
        if not settings.api.quiver_api_key:
            results['quiver_api'] = {
                'status': 'warning',
                'message': 'Quiver API key not configured'
            }
        else:
            # Simple connectivity test (without making actual API calls)
            response = requests.get(
                'https://api.quiverquant.com',
                timeout=10,
                headers={'Authorization': f'Bearer {settings.api.quiver_api_key}'}
            )
            
            if response.status_code == 401:  # Unauthorized is expected without proper endpoint
                results['quiver_api'] = {
                    'status': 'healthy',
                    'message': 'API is accessible (authentication endpoint responded)',
                    'response_time': response.elapsed.total_seconds()
                }
            else:
                results['quiver_api'] = {
                    'status': 'warning',
                    'message': f'Unexpected response code: {response.status_code}',
                    'response_time': response.elapsed.total_seconds()
                }
            
    except requests.exceptions.RequestException as e:
        results['quiver_api'] = {
            'status': 'unhealthy',
            'message': f'Connection failed: {str(e)}'
        }
    except Exception as e:
        results['quiver_api'] = {
            'status': 'unhealthy',
            'message': f'Health check failed: {str(e)}'
        }
    
    # Check Alpaca API connectivity
    try:
        from alpaca.trading.client import TradingClient
        from alpaca.common.exceptions import APIError
        
        # Skip if API keys are not configured
        if not settings.api.alpaca_api_key or not settings.api.alpaca_secret_key:
            results['alpaca_api'] = {
                'status': 'warning',
                'message': 'Alpaca API keys not configured'
            }
        else:
            trading_client = TradingClient(
                api_key=settings.api.alpaca_api_key,
                secret_key=settings.api.alpaca_secret_key,
                paper=settings.api.alpaca_paper_trading
            )
            
            start_time = time.time()
            account = trading_client.get_account()
            response_time = time.time() - start_time
            
            results['alpaca_api'] = {
                'status': 'healthy',
                'message': f'API accessible, account status: {account.status}',
                'response_time': response_time,
                'details': {
                    'account_status': account.status,
                    'paper_trading': settings.api.alpaca_paper_trading
                }
            }
        
    except APIError as e:
        results['alpaca_api'] = {
            'status': 'unhealthy',
            'message': f'Alpaca API error: {str(e)}'
        }
    except Exception as e:
        results['alpaca_api'] = {
            'status': 'unhealthy',
            'message': f'Connection failed: {str(e)}'
        }
    
    return results

def register_external_dependency_checks():
    """Register health checks for external dependencies."""
    
    def external_dependencies_check():
        """Health check for external service dependencies."""
        dependency_results = check_external_dependencies()
        
        # Determine overall status
        statuses = [result['status'] for result in dependency_results.values()]
        
        if all(status == 'healthy' for status in statuses):
            overall_status = 'healthy'
            message = 'All external dependencies are healthy'
        elif any(status == 'unhealthy' for status in statuses):
            overall_status = 'unhealthy'
            unhealthy_services = [name for name, result in dependency_results.items() 
                                if result['status'] == 'unhealthy']
            message = f'Unhealthy external services: {", ".join(unhealthy_services)}'
        else:
            overall_status = 'warning'
            message = 'Some external services have warnings'
        
        from src.utils.monitoring import HealthCheck
        return HealthCheck(
            component='external_dependencies',
            status=overall_status,
            message=message,
            timestamp=time.time(),
            details=dependency_results
        )
    
    health_checker.register_check('external_dependencies', external_dependencies_check)
    logger.info("External dependency health checks registered")

# Initialize external dependency checks
register_external_dependency_checks()

# Global health server instance
health_server = HealthServer()