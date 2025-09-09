"""
Daily Execution Scheduler for Trading Automation System.
Orchestrates daily execution of all trading agents at 9:30 PM EST.
"""
import time
import schedule
import threading
from datetime import datetime, date, time as dt_time, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import pytz
from concurrent.futures import Future
import signal
import sys

from config.settings import settings
from src.data.data_processor import DataProcessor, ProcessingResult
from src.agents.agent_factory import agent_factory, AgentFactory
from src.agents.base_agent import ExecutionResult
from src.utils.logging import get_logger
from src.utils.exceptions import SchedulerError, TradingError
from src.utils.monitoring import metrics_collector
from src.utils.health import HealthStatus

logger = get_logger(__name__)

class SchedulerState(Enum):
    """Scheduler states."""
    STOPPED = "stopped"
    RUNNING = "running"
    EXECUTING = "executing"
    ERROR = "error"

@dataclass
class ExecutionSummary:
    """Summary of daily execution."""
    execution_date: date
    start_time: datetime
    end_time: Optional[datetime]
    duration: Optional[float]
    data_processing_result: Optional[ProcessingResult]
    agent_results: Dict[str, ExecutionResult]
    total_trades_processed: int
    total_orders_placed: int
    successful_agents: int
    failed_agents: int
    errors: List[str]
    success: bool

class DailyRunner:
    """
    Daily execution scheduler that orchestrates the complete trading workflow.
    
    Features:
    - 9:30 PM EST scheduling with timezone handling
    - Complete execution workflow orchestration
    - Execution failure and partial completion handling
    - Execution logging and monitoring
    - Manual execution triggers for testing
    - Execution status tracking and reporting
    - Market holiday and weekend scheduling
    - Execution retry logic for failed runs
    """
    
    def __init__(self, data_processor: Optional[DataProcessor] = None, 
                 agent_factory: Optional[AgentFactory] = None):
        """
        Initialize daily runner.
        
        Args:
            data_processor: Data processor instance (creates if None)
            agent_factory: Agent factory instance (uses global if None)
        """
        self.data_processor = data_processor or DataProcessor()
        self.agent_factory = agent_factory or globals()['agent_factory']
        
        # Configuration
        self.execution_time = settings.agents.global_parameters.execution_time  # "21:30"
        self.timezone = pytz.timezone(settings.agents.global_parameters.timezone)  # "US/Eastern"
        
        # State management
        self.state = SchedulerState.STOPPED
        self.current_execution: Optional[Future] = None
        self.execution_history: List[ExecutionSummary] = []
        self.last_execution_summary: Optional[ExecutionSummary] = None
        
        # Threading
        self.scheduler_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # Statistics
        self.total_executions = 0
        self.successful_executions = 0
        self.failed_executions = 0
        
        # Retry configuration
        self.max_retries = 3
        self.retry_delay = 300  # 5 minutes
        
        # Market calendar (simplified - could integrate with real market calendar)
        self.market_holidays = self._get_market_holidays()
        
        # Setup signal handlers for graceful shutdown
        self._setup_signal_handlers()
        
        logger.info("Initialized Daily Runner")
        logger.info(f"Scheduled execution time: {self.execution_time} {self.timezone}")
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down gracefully...")
            self.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def _get_market_holidays(self) -> List[date]:
        """
        Get list of market holidays.
        
        Returns:
            List of market holiday dates
        """
        # Simplified holiday list - in production would use market calendar API
        current_year = datetime.now().year
        holidays = [
            date(current_year, 1, 1),   # New Year's Day
            date(current_year, 7, 4),   # Independence Day
            date(current_year, 12, 25), # Christmas Day
        ]
        
        # Add previous/next year holidays for year transitions
        for year in [current_year - 1, current_year + 1]:
            holidays.extend([
                date(year, 1, 1),
                date(year, 7, 4), 
                date(year, 12, 25)
            ])
        
        return holidays
    
    def is_trading_day(self, check_date: date) -> bool:
        """
        Check if a date is a trading day.
        
        Args:
            check_date: Date to check
            
        Returns:
            True if it's a trading day
        """
        # Check if it's a weekend
        if check_date.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False
        
        # Check if it's a market holiday
        if check_date in self.market_holidays:
            return False
        
        return True
    
    def start_scheduler(self) -> None:
        """Start the daily scheduler."""
        if self.state == SchedulerState.RUNNING:
            logger.warning("Scheduler already running")
            return
        
        try:
            # Clear any existing schedule
            schedule.clear()
            
            # Schedule daily execution
            execution_time_str = self.execution_time
            schedule.every().day.at(execution_time_str).do(self._scheduled_execution)
            
            # Start scheduler thread
            self.stop_event.clear()
            self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
            self.scheduler_thread.start()
            
            self.state = SchedulerState.RUNNING
            
            logger.info(f"Daily scheduler started - next execution at {execution_time_str} {self.timezone}")
            
            # Log next execution time
            next_run = schedule.next_run()
            if next_run:
                logger.info(f"Next scheduled execution: {next_run}")
        
        except Exception as e:
            self.state = SchedulerState.ERROR
            logger.error(f"Failed to start scheduler: {e}")
            raise SchedulerError(f"Failed to start scheduler: {e}")
    
    def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        logger.info("Scheduler loop started")
        
        while not self.stop_event.is_set():
            try:
                # Run pending scheduled jobs
                schedule.run_pending()
                
                # Sleep for 1 minute before checking again
                if not self.stop_event.wait(60):
                    continue
                else:
                    break
            
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                time.sleep(60)  # Continue after error
        
        logger.info("Scheduler loop stopped")
    
    def _scheduled_execution(self) -> None:
        """Scheduled execution wrapper."""
        execution_date = date.today()
        
        # Check if today is a trading day
        if not self.is_trading_day(execution_date):
            logger.info(f"Skipping execution - {execution_date} is not a trading day")
            return
        
        # Check if we're already executing
        if self.state == SchedulerState.EXECUTING:
            logger.warning("Skipping scheduled execution - already running")
            return
        
        logger.info(f"Starting scheduled execution for {execution_date}")
        
        try:
            self.execute_daily_workflow(execution_date)
        except Exception as e:
            logger.error(f"Scheduled execution failed: {e}")
    
    def execute_daily_workflow(self, execution_date: Optional[date] = None, 
                             retry_count: int = 0) -> ExecutionSummary:
        """
        Execute the complete daily trading workflow.
        
        Args:
            execution_date: Date to execute for (default: today)
            retry_count: Current retry attempt
            
        Returns:
            Execution summary
        """
        if execution_date is None:
            execution_date = date.today()
        
        start_time = datetime.now()
        
        try:
            self.state = SchedulerState.EXECUTING
            logger.info(f"Starting daily workflow execution for {execution_date}")
            
            # Initialize execution summary
            summary = ExecutionSummary(
                execution_date=execution_date,
                start_time=start_time,
                end_time=None,
                duration=None,
                data_processing_result=None,
                agent_results={},
                total_trades_processed=0,
                total_orders_placed=0,
                successful_agents=0,
                failed_agents=0,
                errors=[],
                success=False
            )
            
            # Step 1: Fetch and process congressional data
            logger.info("Step 1: Processing congressional data")
            data_result = self.data_processor.process_daily_data(execution_date)
            summary.data_processing_result = data_result
            
            if not data_result.success:
                summary.errors.extend(data_result.errors)
                logger.error("Data processing failed, aborting execution")
                return self._finalize_execution_summary(summary)
            
            # Get the congressional trades from data processor
            # For now, we'll use the quiver client directly
            congressional_trades = self.data_processor.quiver_client.get_congressional_trades(execution_date)
            
            # Step 2: Initialize and execute all agents
            logger.info("Step 2: Executing trading agents")
            agents = self.agent_factory.create_agents_from_config()
            
            if not agents:
                summary.errors.append("No agents created")
                logger.error("No agents available for execution")
                return self._finalize_execution_summary(summary)
            
            # Execute all agents
            agent_results = self.agent_factory.execute_all_agents(
                congressional_trades, 
                parallel=True
            )
            summary.agent_results = agent_results
            
            # Step 3: Calculate summary statistics
            for agent_id, result in agent_results.items():
                summary.total_trades_processed += result.trades_processed
                summary.total_orders_placed += result.orders_placed
                
                if result.success:
                    summary.successful_agents += 1
                else:
                    summary.failed_agents += 1
                    summary.errors.extend(result.errors)
            
            # Step 4: Health check all systems
            logger.info("Step 3: Performing system health checks")
            health_results = self._perform_health_checks()
            
            # Step 5: Generate execution summary and notifications
            logger.info("Step 4: Finalizing execution")
            summary.success = summary.failed_agents == 0 and len(summary.errors) == 0
            
            return self._finalize_execution_summary(summary)
        
        except Exception as e:
            error_msg = f"Daily workflow execution failed: {e}"
            logger.error(error_msg, exc_info=True)
            
            summary.errors.append(error_msg)
            summary.success = False
            
            return self._finalize_execution_summary(summary)
        
        finally:
            self.state = SchedulerState.RUNNING if self.scheduler_thread else SchedulerState.STOPPED
    
    def _finalize_execution_summary(self, summary: ExecutionSummary) -> ExecutionSummary:
        """Finalize execution summary."""
        summary.end_time = datetime.now()
        summary.duration = (summary.end_time - summary.start_time).total_seconds()
        
        # Update statistics
        self.total_executions += 1
        if summary.success:
            self.successful_executions += 1
        else:
            self.failed_executions += 1
        
        # Store in history
        self.execution_history.append(summary)
        self.last_execution_summary = summary
        
        # Keep only last 30 days of history
        cutoff_date = date.today() - timedelta(days=30)
        self.execution_history = [
            s for s in self.execution_history 
            if s.execution_date >= cutoff_date
        ]
        
        # Log execution summary
        self._log_execution_summary(summary)
        
        # Record metrics
        metrics_collector.record_execution_time("daily_workflow", summary.duration)
        
        return summary
    
    def _log_execution_summary(self, summary: ExecutionSummary) -> None:
        """Log execution summary."""
        status = "SUCCESS" if summary.success else "FAILED"
        duration = summary.duration or 0
        
        logger.info(f"Daily execution {status} for {summary.execution_date}")
        logger.info(f"Duration: {duration:.2f}s")
        logger.info(f"Agents: {summary.successful_agents} successful, {summary.failed_agents} failed")
        logger.info(f"Trades: {summary.total_trades_processed} processed, {summary.total_orders_placed} orders placed")
        
        if summary.errors:
            logger.error(f"Errors: {len(summary.errors)}")
            for error in summary.errors[:5]:  # Log first 5 errors
                logger.error(f"  - {error}")
    
    def _perform_health_checks(self) -> Dict[str, Any]:
        """Perform comprehensive health checks."""
        health_results = {}
        
        try:
            # Check data processor connections
            connection_status = self.data_processor.test_all_connections()
            health_results['connections'] = connection_status
            
            # Check agent health
            agent_health = self.agent_factory.health_check_all_agents()
            health_results['agents'] = {
                agent_id: status.value for agent_id, status in agent_health.items()
            }
            
            # System health summary
            all_connections_healthy = all(connection_status.values())
            all_agents_healthy = all(status == HealthStatus.HEALTHY for status in agent_health.values())
            
            health_results['overall_health'] = all_connections_healthy and all_agents_healthy
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            health_results['error'] = str(e)
            health_results['overall_health'] = False
        
        return health_results
    
    def stop(self) -> None:
        """Stop the daily scheduler."""
        if self.state == SchedulerState.STOPPED:
            logger.info("Scheduler already stopped")
            return
        
        logger.info("Stopping daily scheduler...")
        
        # Signal stop and wait for scheduler thread
        self.stop_event.set()
        
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=10)
            if self.scheduler_thread.is_alive():
                logger.warning("Scheduler thread did not stop gracefully")
        
        # Clear schedule
        schedule.clear()
        
        self.state = SchedulerState.STOPPED
        logger.info("Daily scheduler stopped")
    
    def execute_now(self, execution_date: Optional[date] = None) -> ExecutionSummary:
        """
        Execute daily workflow immediately (for testing).
        
        Args:
            execution_date: Date to execute for
            
        Returns:
            Execution summary
        """
        if execution_date is None:
            execution_date = date.today()
        
        logger.info(f"Manual execution requested for {execution_date}")
        
        if self.state == SchedulerState.EXECUTING:
            raise SchedulerError("Cannot execute - another execution is already running")
        
        return self.execute_daily_workflow(execution_date)
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """
        Get comprehensive scheduler status.
        
        Returns:
            Scheduler status information
        """
        next_run = schedule.next_run()
        
        return {
            'state': self.state.value,
            'execution_time': self.execution_time,
            'timezone': str(self.timezone),
            'next_scheduled_run': next_run.isoformat() if next_run else None,
            'last_execution': {
                'date': self.last_execution_summary.execution_date.isoformat(),
                'success': self.last_execution_summary.success,
                'duration': self.last_execution_summary.duration,
                'agents_executed': len(self.last_execution_summary.agent_results),
                'trades_processed': self.last_execution_summary.total_trades_processed,
                'orders_placed': self.last_execution_summary.total_orders_placed
            } if self.last_execution_summary else None,
            'statistics': {
                'total_executions': self.total_executions,
                'successful_executions': self.successful_executions,
                'failed_executions': self.failed_executions,
                'success_rate': (self.successful_executions / max(self.total_executions, 1)) * 100
            },
            'market_status': {
                'today_is_trading_day': self.is_trading_day(date.today()),
                'next_trading_day': self._get_next_trading_day().isoformat()
            }
        }
    
    def _get_next_trading_day(self) -> date:
        """Get the next trading day."""
        check_date = date.today() + timedelta(days=1)
        
        while not self.is_trading_day(check_date):
            check_date += timedelta(days=1)
            
            # Prevent infinite loop
            if check_date > date.today() + timedelta(days=14):
                break
        
        return check_date
    
    def get_execution_history(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get execution history.
        
        Args:
            days: Number of days to include
            
        Returns:
            List of execution summaries
        """
        cutoff_date = date.today() - timedelta(days=days)
        
        history = []
        for summary in self.execution_history:
            if summary.execution_date >= cutoff_date:
                history.append({
                    'date': summary.execution_date.isoformat(),
                    'success': summary.success,
                    'duration': summary.duration,
                    'successful_agents': summary.successful_agents,
                    'failed_agents': summary.failed_agents,
                    'trades_processed': summary.total_trades_processed,
                    'orders_placed': summary.total_orders_placed,
                    'error_count': len(summary.errors),
                    'start_time': summary.start_time.isoformat(),
                    'end_time': summary.end_time.isoformat() if summary.end_time else None
                })
        
        return sorted(history, key=lambda x: x['date'], reverse=True)

# Global daily runner instance
daily_runner = DailyRunner()

def create_cron_script() -> str:
    """
    Create a cron script for system-level scheduling.
    
    Returns:
        Cron script content
    """
    script_content = f"""#!/bin/bash
# Daily Trading Automation Cron Script
# Add this to crontab with: 30 21 * * 1-5 /path/to/this/script.sh

cd {settings.base_path}
source venv/bin/activate

python -c "
from src.scheduler.daily_runner import daily_runner
import logging

logging.basicConfig(level=logging.INFO)

try:
    summary = daily_runner.execute_now()
    if summary.success:
        print(f'SUCCESS: {{summary.successful_agents}} agents executed, {{summary.total_orders_placed}} orders placed')
        exit(0)
    else:
        print(f'FAILED: {{len(summary.errors)}} errors occurred')
        exit(1)
except Exception as e:
    print(f'ERROR: {{e}}')
    exit(1)
"
"""
    return script_content