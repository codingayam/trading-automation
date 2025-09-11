"""
Intraday Scheduler for Technical Agents.
Handles market-hours scheduling for technical trading agents that need to execute during trading hours.
"""
import asyncio
import threading
import time
from datetime import datetime, time as dt_time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import pytz
import schedule

from config.settings import settings
from src.agents.technical_agent import TechnicalAgent
from src.agents.andy_grok_agent import AndyGrokAgent
from src.utils.logging import get_logger
from src.utils.exceptions import TradingError, ValidationError
from src.utils.monitoring import metrics_collector
from src.utils.health import HealthStatus

logger = get_logger(__name__)

class ScheduleType(Enum):
    """Types of intraday schedules."""
    MARKET_OPEN = "market_open"      # Execute at market open
    MARKET_CLOSE = "market_close"    # Execute before market close
    PERIODIC = "periodic"            # Execute at regular intervals
    CUSTOM = "custom"                # Custom time-based execution

@dataclass
class IntradayTask:
    """Intraday task definition."""
    task_id: str
    agent: TechnicalAgent
    schedule_type: ScheduleType
    execution_time: str  # Time in HH:MM format
    callback: Callable
    enabled: bool = True
    last_execution: Optional[datetime] = None
    execution_count: int = 0
    error_count: int = 0

@dataclass
class SchedulerStats:
    """Scheduler statistics."""
    active_tasks: int
    total_executions: int
    successful_executions: int
    failed_executions: int
    last_execution_time: Optional[datetime]
    scheduler_uptime: float

class IntradayScheduler:
    """
    Intraday scheduler for technical trading agents.
    
    Features:
    - Market hours awareness with Eastern timezone
    - Multiple schedule types (market open, close, periodic)
    - Agent-specific task management
    - Error handling and retry logic
    - Health monitoring and status tracking
    - Thread-safe execution
    - Graceful shutdown handling
    """
    
    def __init__(self):
        """Initialize intraday scheduler."""
        self.tasks: Dict[str, IntradayTask] = {}
        self.running = False
        self.scheduler_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # Market timezone
        self.market_tz = pytz.timezone('US/Eastern')
        
        # Scheduler statistics
        self.stats = SchedulerStats(
            active_tasks=0,
            total_executions=0,
            successful_executions=0,
            failed_executions=0,
            last_execution_time=None,
            scheduler_uptime=0.0
        )
        
        self.start_time = datetime.now()
        
        logger.info("Initialized Intraday Scheduler")
    
    def add_technical_agent(self, agent: TechnicalAgent, schedule_config: Dict[str, Any] = None) -> None:
        """
        Add a technical agent with intraday scheduling.
        
        Args:
            agent: Technical agent to schedule
            schedule_config: Custom schedule configuration
        """
        if not isinstance(agent, TechnicalAgent):
            raise ValidationError("Agent must be a TechnicalAgent instance")
        
        default_config = {
            'market_open_enabled': True,
            'market_close_enabled': True,
            'market_open_time': '09:30',
            'market_close_time': '15:55'
        }
        
        config = {**default_config, **(schedule_config or {})}
        
        # Add market open task
        if config['market_open_enabled']:
            open_task_id = f"{agent.agent_id}_market_open"
            self.add_task(
                task_id=open_task_id,
                agent=agent,
                schedule_type=ScheduleType.MARKET_OPEN,
                execution_time=config['market_open_time'],
                callback=self._execute_morning_workflow
            )
        
        # Add market close task  
        if config['market_close_enabled']:
            close_task_id = f"{agent.agent_id}_market_close"
            self.add_task(
                task_id=close_task_id,
                agent=agent,
                schedule_type=ScheduleType.MARKET_CLOSE,
                execution_time=config['market_close_time'],
                callback=self._execute_closing_workflow
            )
        
        logger.info(f"Added technical agent {agent.agent_id} to intraday scheduler")
    
    def add_task(self, task_id: str, agent: TechnicalAgent, schedule_type: ScheduleType,
                 execution_time: str, callback: Callable, enabled: bool = True) -> None:
        """
        Add an intraday task.
        
        Args:
            task_id: Unique task identifier
            agent: Technical agent for this task
            schedule_type: Type of schedule
            execution_time: Execution time in HH:MM format
            callback: Function to execute
            enabled: Whether task is enabled
        """
        # Validate execution time format
        try:
            datetime.strptime(execution_time, '%H:%M')
        except ValueError:
            raise ValidationError(f"Invalid execution time format: {execution_time}. Use HH:MM")
        
        task = IntradayTask(
            task_id=task_id,
            agent=agent,
            schedule_type=schedule_type,
            execution_time=execution_time,
            callback=callback,
            enabled=enabled
        )
        
        self.tasks[task_id] = task
        logger.info(f"Added intraday task: {task_id} at {execution_time}")
        
        # Update scheduler if running
        if self.running:
            self._schedule_task(task)
    
    def remove_task(self, task_id: str) -> bool:
        """
        Remove an intraday task.
        
        Args:
            task_id: Task identifier to remove
            
        Returns:
            True if task was removed
        """
        if task_id in self.tasks:
            del self.tasks[task_id]
            logger.info(f"Removed intraday task: {task_id}")
            return True
        return False
    
    def enable_task(self, task_id: str) -> bool:
        """Enable a task."""
        if task_id in self.tasks:
            self.tasks[task_id].enabled = True
            logger.info(f"Enabled intraday task: {task_id}")
            return True
        return False
    
    def disable_task(self, task_id: str) -> bool:
        """Disable a task."""
        if task_id in self.tasks:
            self.tasks[task_id].enabled = False
            logger.info(f"Disabled intraday task: {task_id}")
            return True
        return False
    
    def _schedule_task(self, task: IntradayTask) -> None:
        """Schedule a single task with the Python schedule library."""
        if not task.enabled:
            return
        
        execution_time = task.execution_time
        
        def job():
            if task.enabled and not self.stop_event.is_set():
                self._execute_task(task)
        
        # Schedule task for weekdays only (Monday=0, Friday=4)
        schedule.every().monday.at(execution_time).do(job)
        schedule.every().tuesday.at(execution_time).do(job)
        schedule.every().wednesday.at(execution_time).do(job)
        schedule.every().thursday.at(execution_time).do(job)
        schedule.every().friday.at(execution_time).do(job)
        
        logger.debug(f"Scheduled task {task.task_id} for weekdays at {execution_time}")
    
    def _execute_task(self, task: IntradayTask) -> None:
        """Execute a single intraday task."""
        try:
            logger.info(f"Executing intraday task: {task.task_id}")
            
            start_time = time.time()
            
            # Check if market is open for market-related tasks
            if task.schedule_type in [ScheduleType.MARKET_OPEN, ScheduleType.MARKET_CLOSE]:
                if not self._is_market_day():
                    logger.info(f"Skipping task {task.task_id} - not a market day")
                    return
            
            # Execute the callback
            result = task.callback(task.agent)
            
            execution_time = time.time() - start_time
            
            # Update task statistics
            task.last_execution = datetime.now()
            task.execution_count += 1
            
            # Update scheduler statistics
            self.stats.total_executions += 1
            self.stats.last_execution_time = datetime.now()
            
            if result:
                self.stats.successful_executions += 1
                logger.info(f"Task {task.task_id} completed successfully in {execution_time:.2f}s")
            else:
                self.stats.failed_executions += 1
                task.error_count += 1
                logger.error(f"Task {task.task_id} failed")
            
            metrics_collector.record_execution_time(f"intraday_task_{task.task_id}", execution_time)
        
        except Exception as e:
            task.error_count += 1
            self.stats.failed_executions += 1
            logger.error(f"Task execution failed for {task.task_id}: {e}")
    
    def _execute_morning_workflow(self, agent: TechnicalAgent) -> bool:
        """Execute morning trading workflow for technical agent."""
        try:
            if isinstance(agent, AndyGrokAgent):
                decisions = agent.execute_morning_analysis()
                
                # Execute any generated trade decisions
                successful_trades = 0
                for decision in decisions:
                    try:
                        if agent.execute_intraday_workflow().success:
                            successful_trades += 1
                    except Exception as e:
                        logger.error(f"Failed to execute morning trade: {e}")
                
                logger.info(f"Morning workflow completed for {agent.agent_id}: {successful_trades}/{len(decisions)} trades executed")
                return len(decisions) == 0 or successful_trades > 0
            else:
                # Generic technical agent workflow
                result = agent.execute_intraday_workflow()
                return result.success
        
        except Exception as e:
            logger.error(f"Morning workflow failed for {agent.agent_id}: {e}")
            return False
    
    def _execute_closing_workflow(self, agent: TechnicalAgent) -> bool:
        """Execute closing workflow for technical agent."""
        try:
            if isinstance(agent, AndyGrokAgent):
                decisions = agent.execute_closing_workflow()
                
                # Execute any position closing decisions
                successful_closes = 0
                for decision in decisions:
                    try:
                        # Convert technical decision to base trade decision and execute
                        from src.agents.base_agent import TradeDecision
                        base_decision = TradeDecision(
                            ticker=decision.ticker,
                            side=decision.side,
                            amount=decision.amount,
                            reason=decision.reason,
                            source_trade=decision.source_trade,
                            timestamp=decision.timestamp,
                            confidence=decision.confidence
                        )
                        
                        if agent.execute_trade(base_decision):
                            successful_closes += 1
                    except Exception as e:
                        logger.error(f"Failed to execute closing trade: {e}")
                
                logger.info(f"Closing workflow completed for {agent.agent_id}: {successful_closes}/{len(decisions)} positions closed")
                return len(decisions) == 0 or successful_closes > 0
            else:
                # Generic technical agent workflow
                result = agent.execute_intraday_workflow()
                return result.success
        
        except Exception as e:
            logger.error(f"Closing workflow failed for {agent.agent_id}: {e}")
            return False
    
    def _is_market_day(self) -> bool:
        """Check if today is a market day (weekday, not holiday)."""
        now = datetime.now(self.market_tz)
        
        # Check if weekday
        if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False
        
        # Basic holiday check (could be expanded)
        # This is a simplified implementation
        today = now.date()
        year = today.year
        
        # Common market holidays
        holidays = [
            (1, 1),   # New Year's Day
            (7, 4),   # Independence Day
            (12, 25), # Christmas Day
        ]
        
        return (today.month, today.day) not in holidays
    
    def start(self) -> None:
        """Start the intraday scheduler."""
        if self.running:
            logger.warning("Intraday scheduler is already running")
            return
        
        self.running = True
        self.stop_event.clear()
        
        # Schedule all tasks
        for task in self.tasks.values():
            self._schedule_task(task)
        
        # Start scheduler thread
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        
        self.stats.active_tasks = len([t for t in self.tasks.values() if t.enabled])
        
        logger.info(f"Started intraday scheduler with {self.stats.active_tasks} active tasks")
    
    def stop(self) -> None:
        """Stop the intraday scheduler."""
        if not self.running:
            return
        
        logger.info("Stopping intraday scheduler...")
        
        self.running = False
        self.stop_event.set()
        
        # Clear all scheduled jobs
        schedule.clear()
        
        # Wait for scheduler thread to finish
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5.0)
        
        logger.info("Intraday scheduler stopped")
    
    def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        logger.info("Intraday scheduler loop started")
        
        while self.running and not self.stop_event.is_set():
            try:
                # Run pending scheduled jobs
                schedule.run_pending()
                
                # Update uptime
                self.stats.scheduler_uptime = (datetime.now() - self.start_time).total_seconds()
                
                # Sleep for 1 second before next check
                time.sleep(1)
            
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                time.sleep(5)  # Wait longer on error
        
        logger.info("Intraday scheduler loop ended")
    
    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status and statistics."""
        return {
            'running': self.running,
            'total_tasks': len(self.tasks),
            'active_tasks': len([t for t in self.tasks.values() if t.enabled]),
            'statistics': {
                'total_executions': self.stats.total_executions,
                'successful_executions': self.stats.successful_executions,
                'failed_executions': self.stats.failed_executions,
                'success_rate': (self.stats.successful_executions / max(self.stats.total_executions, 1)) * 100,
                'last_execution_time': self.stats.last_execution_time.isoformat() if self.stats.last_execution_time else None,
                'uptime_seconds': self.stats.scheduler_uptime
            },
            'tasks': {
                task_id: {
                    'agent_id': task.agent.agent_id,
                    'schedule_type': task.schedule_type.value,
                    'execution_time': task.execution_time,
                    'enabled': task.enabled,
                    'execution_count': task.execution_count,
                    'error_count': task.error_count,
                    'last_execution': task.last_execution.isoformat() if task.last_execution else None
                }
                for task_id, task in self.tasks.items()
            },
            'market_status': {
                'is_market_day': self._is_market_day(),
                'timezone': str(self.market_tz)
            }
        }
    
    def health_check(self) -> HealthStatus:
        """Perform health check on the scheduler."""
        try:
            if not self.running:
                return HealthStatus.DISABLED
            
            # Check if scheduler thread is alive
            if not self.scheduler_thread or not self.scheduler_thread.is_alive():
                return HealthStatus.UNHEALTHY
            
            # Check for excessive failures
            total_executions = self.stats.total_executions
            if total_executions > 10:
                failure_rate = (self.stats.failed_executions / total_executions) * 100
                if failure_rate > 50:  # More than 50% failure rate
                    return HealthStatus.DEGRADED
            
            # Check if any tasks have high error counts
            for task in self.tasks.values():
                if task.execution_count > 5 and task.error_count > task.execution_count * 0.6:
                    return HealthStatus.DEGRADED
            
            return HealthStatus.HEALTHY
        
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return HealthStatus.UNHEALTHY

# Global scheduler instance
intraday_scheduler = IntradayScheduler()

def start_intraday_scheduler():
    """Start the global intraday scheduler."""
    intraday_scheduler.start()

def stop_intraday_scheduler():
    """Stop the global intraday scheduler."""
    intraday_scheduler.stop()

def add_andy_grok_agent_to_scheduler(agent: AndyGrokAgent):
    """Convenience function to add Andy Grok agent to scheduler."""
    intraday_scheduler.add_technical_agent(agent)