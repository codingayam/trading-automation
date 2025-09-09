"""
Performance monitoring and metrics collection for trading automation system.
Provides execution time tracking, health checks, and system status monitoring.
"""
import time
import psutil
import threading
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict, deque

from src.utils.logging import get_logger

logger = get_logger('monitoring')

@dataclass
class PerformanceMetric:
    """Performance metric data structure."""
    name: str
    value: float
    unit: str
    timestamp: datetime
    tags: Dict[str, str]

@dataclass
class HealthCheck:
    """Health check result data structure."""
    component: str
    status: str  # 'healthy', 'warning', 'unhealthy'
    message: str
    timestamp: datetime
    response_time: Optional[float] = None
    details: Optional[Dict[str, Any]] = None

class MetricsCollector:
    """Collects and manages performance metrics."""
    
    def __init__(self):
        self.metrics = defaultdict(lambda: deque(maxlen=1000))  # Keep last 1000 metrics per name
        self.lock = threading.Lock()
    
    def record_metric(self, name: str, value: float, unit: str = "", 
                     tags: Optional[Dict[str, str]] = None):
        """Record a performance metric."""
        metric = PerformanceMetric(
            name=name,
            value=value,
            unit=unit,
            timestamp=datetime.now(),
            tags=tags or {}
        )
        
        with self.lock:
            self.metrics[name].append(metric)
        
        logger.performance_metric(name, value, **(tags or {}))
    
    def record_execution_time(self, operation: str, execution_time: float,
                            tags: Optional[Dict[str, str]] = None):
        """Record execution time for an operation."""
        self.record_metric(
            name=f"{operation}_execution_time",
            value=execution_time,
            unit="seconds",
            tags=tags
        )
    
    def record_api_response_time(self, api_name: str, endpoint: str, 
                               response_time: float, status_code: Optional[int] = None):
        """Record API response time."""
        tags = {
            'api': api_name,
            'endpoint': endpoint
        }
        if status_code:
            tags['status_code'] = str(status_code)
        
        self.record_metric(
            name="api_response_time",
            value=response_time,
            unit="seconds",
            tags=tags
        )
    
    def record_trade_execution(self, agent_id: str, ticker: str, 
                             execution_time: float, success: bool):
        """Record trade execution metrics."""
        tags = {
            'agent_id': agent_id,
            'ticker': ticker,
            'success': str(success)
        }
        
        self.record_metric(
            name="trade_execution_time",
            value=execution_time,
            unit="seconds",
            tags=tags
        )
        
        self.record_metric(
            name="trade_count",
            value=1,
            unit="count",
            tags=tags
        )
    
    def get_metrics(self, name: str, since: Optional[datetime] = None) -> List[PerformanceMetric]:
        """Get metrics by name, optionally filtered by time."""
        with self.lock:
            metrics = list(self.metrics.get(name, []))
        
        if since:
            metrics = [m for m in metrics if m.timestamp >= since]
        
        return metrics
    
    def get_metric_summary(self, name: str, since: Optional[datetime] = None) -> Dict[str, Any]:
        """Get summary statistics for a metric."""
        metrics = self.get_metrics(name, since)
        
        if not metrics:
            return {
                'count': 0,
                'min': None,
                'max': None,
                'avg': None,
                'latest': None
            }
        
        values = [m.value for m in metrics]
        
        return {
            'count': len(values),
            'min': min(values),
            'max': max(values),
            'avg': sum(values) / len(values),
            'latest': values[-1] if values else None,
            'unit': metrics[-1].unit if metrics else None
        }
    
    def get_all_metrics_summary(self) -> Dict[str, Dict[str, Any]]:
        """Get summary for all collected metrics."""
        summaries = {}
        
        with self.lock:
            for name in self.metrics.keys():
                summaries[name] = self.get_metric_summary(name)
        
        return summaries

class HealthChecker:
    """Performs health checks on system components."""
    
    def __init__(self):
        self.checks = {}
        self.results = defaultdict(lambda: deque(maxlen=100))  # Keep last 100 results per check
        self.lock = threading.Lock()
    
    def register_check(self, component: str, check_func: Callable[[], HealthCheck]):
        """Register a health check function."""
        self.checks[component] = check_func
        logger.debug(f"Registered health check for component: {component}")
    
    def run_check(self, component: str) -> HealthCheck:
        """Run health check for a specific component."""
        if component not in self.checks:
            return HealthCheck(
                component=component,
                status='unhealthy',
                message=f'No health check registered for {component}',
                timestamp=datetime.now()
            )
        
        start_time = time.time()
        
        try:
            result = self.checks[component]()
            result.response_time = time.time() - start_time
            
        except Exception as e:
            result = HealthCheck(
                component=component,
                status='unhealthy',
                message=f'Health check failed: {str(e)}',
                timestamp=datetime.now(),
                response_time=time.time() - start_time
            )
            
            logger.error(f"Health check failed for {component}", exception=e)
        
        # Store result
        with self.lock:
            self.results[component].append(result)
        
        return result
    
    def run_all_checks(self) -> Dict[str, HealthCheck]:
        """Run all registered health checks."""
        results = {}
        
        for component in self.checks.keys():
            results[component] = self.run_check(component)
        
        return results
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status."""
        results = self.run_all_checks()
        
        if not results:
            return {
                'status': 'unknown',
                'message': 'No health checks configured',
                'components': {},
                'timestamp': datetime.now().isoformat()
            }
        
        # Determine overall status
        statuses = [result.status for result in results.values()]
        
        if all(status == 'healthy' for status in statuses):
            overall_status = 'healthy'
        elif any(status == 'unhealthy' for status in statuses):
            overall_status = 'unhealthy'
        else:
            overall_status = 'warning'
        
        return {
            'status': overall_status,
            'message': f'System status: {overall_status}',
            'components': {name: asdict(result) for name, result in results.items()},
            'timestamp': datetime.now().isoformat()
        }
    
    def get_component_history(self, component: str, limit: int = 10) -> List[HealthCheck]:
        """Get health check history for a component."""
        with self.lock:
            results = list(self.results.get(component, []))
        
        return results[-limit:] if results else []

class SystemMonitor:
    """Monitors system resources and performance."""
    
    def __init__(self):
        self.process = psutil.Process()
        self.start_time = datetime.now()
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get current system statistics."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            process_memory = self.process.memory_info()
            
            # Disk usage for database directory
            from config.settings import settings
            db_path = settings.database.full_path
            disk_usage = psutil.disk_usage(str(db_path).rsplit('/', 1)[0])
            
            return {
                'cpu': {
                    'percent': cpu_percent,
                    'count': psutil.cpu_count()
                },
                'memory': {
                    'total': memory.total,
                    'available': memory.available,
                    'percent': memory.percent,
                    'process_rss': process_memory.rss,
                    'process_vms': process_memory.vms
                },
                'disk': {
                    'total': disk_usage.total,
                    'used': disk_usage.used,
                    'free': disk_usage.free,
                    'percent': (disk_usage.used / disk_usage.total) * 100
                },
                'uptime': (datetime.now() - self.start_time).total_seconds(),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error("Failed to collect system stats", exception=e)
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

# Global instances
metrics_collector = MetricsCollector()
health_checker = HealthChecker()
system_monitor = SystemMonitor()

def record_execution_time(operation: str, tags: Optional[Dict[str, str]] = None):
    """Decorator to record execution time for functions."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                final_tags = {'status': 'success'}
                if tags:
                    final_tags.update(tags)
                
                metrics_collector.record_execution_time(
                    operation or func.__name__,
                    execution_time,
                    final_tags
                )
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                
                final_tags = {'status': 'error', 'error_type': type(e).__name__}
                if tags:
                    final_tags.update(tags)
                
                metrics_collector.record_execution_time(
                    operation or func.__name__,
                    execution_time,
                    final_tags
                )
                
                raise
        
        return wrapper
    return decorator

def setup_default_health_checks():
    """Set up default health checks for system components."""
    
    def database_health_check() -> HealthCheck:
        """Check database connectivity and basic operation."""
        try:
            from src.data.database import db
            
            start_time = time.time()
            result = db.execute_single("SELECT 1 as test")
            response_time = time.time() - start_time
            
            if result and result.get('test') == 1:
                return HealthCheck(
                    component='database',
                    status='healthy',
                    message='Database is accessible and responding',
                    timestamp=datetime.now(),
                    response_time=response_time
                )
            else:
                return HealthCheck(
                    component='database',
                    status='unhealthy',
                    message='Database query returned unexpected result',
                    timestamp=datetime.now(),
                    response_time=response_time
                )
                
        except Exception as e:
            return HealthCheck(
                component='database',
                status='unhealthy',
                message=f'Database connection failed: {str(e)}',
                timestamp=datetime.now()
            )
    
    def system_resources_health_check() -> HealthCheck:
        """Check system resource usage."""
        try:
            stats = system_monitor.get_system_stats()
            
            # Check memory usage
            memory_percent = stats.get('memory', {}).get('percent', 0)
            disk_percent = stats.get('disk', {}).get('percent', 0)
            
            if memory_percent > 90 or disk_percent > 90:
                status = 'unhealthy'
                message = f'High resource usage: Memory {memory_percent}%, Disk {disk_percent}%'
            elif memory_percent > 80 or disk_percent > 80:
                status = 'warning'
                message = f'Moderate resource usage: Memory {memory_percent}%, Disk {disk_percent}%'
            else:
                status = 'healthy'
                message = f'Resource usage normal: Memory {memory_percent}%, Disk {disk_percent}%'
            
            return HealthCheck(
                component='system_resources',
                status=status,
                message=message,
                timestamp=datetime.now(),
                details=stats
            )
            
        except Exception as e:
            return HealthCheck(
                component='system_resources',
                status='unhealthy',
                message=f'Failed to check system resources: {str(e)}',
                timestamp=datetime.now()
            )
    
    # Register health checks
    health_checker.register_check('database', database_health_check)
    health_checker.register_check('system_resources', system_resources_health_check)
    
    logger.info("Default health checks registered")

# Initialize default health checks
setup_default_health_checks()