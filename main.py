#!/usr/bin/env python3
"""
Main entry point for the Trading Automation System.
Provides command-line interface for running the system.
"""
import argparse
import sys
import time
from datetime import date, datetime
from typing import Optional

from config.settings import settings
from src.scheduler.daily_runner import daily_runner
from src.scheduler.intraday_scheduler import intraday_scheduler
from src.agents.agent_factory import agent_factory
from src.agents.andy_grok_agent import AndyGrokAgent
from src.data.data_processor import DataProcessor
from src.utils.logging import get_logger
from src.utils.health import health_server

logger = get_logger(__name__)

def run_scheduler():
    """Start the daily scheduler."""
    logger.info("Starting trading automation scheduler...")
    
    try:
        # Start health server
        health_server.start()
        logger.info("Health server started on port 8080")
        
        # Start daily scheduler
        daily_runner.start_scheduler()
        logger.info("Daily scheduler started successfully")
        
        # Keep the main thread alive
        try:
            while True:
                time.sleep(60)
                
                # Check scheduler health
                status = daily_runner.get_scheduler_status()
                if status['state'] == 'error':
                    logger.error("Scheduler is in error state")
                    break
        
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        
        finally:
            # Graceful shutdown
            logger.info("Shutting down scheduler...")
            daily_runner.stop()
            health_server.stop()
            logger.info("Scheduler stopped")
    
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")
        sys.exit(1)

def run_once(execution_date: Optional[str] = None):
    """Run the daily workflow once."""
    target_date = date.today()
    
    if execution_date:
        try:
            target_date = datetime.strptime(execution_date, '%Y-%m-%d').date()
        except ValueError:
            logger.error(f"Invalid date format: {execution_date}. Use YYYY-MM-DD")
            sys.exit(1)
    
    logger.info(f"Running daily workflow for {target_date}")
    
    try:
        summary = daily_runner.execute_now(target_date)
        
        # Print summary
        print(f"\n{'='*60}")
        print(f"EXECUTION SUMMARY - {target_date}")
        print(f"{'='*60}")
        print(f"Status: {'SUCCESS' if summary.success else 'FAILED'}")
        print(f"Duration: {summary.duration:.2f} seconds")
        print(f"Agents executed: {summary.successful_agents} successful, {summary.failed_agents} failed")
        print(f"Trades processed: {summary.total_trades_processed}")
        print(f"Orders placed: {summary.total_orders_placed}")
        
        if summary.errors:
            print(f"\nErrors ({len(summary.errors)}):")
            for error in summary.errors[:10]:  # Show first 10 errors
                print(f"  - {error}")
        
        print(f"{'='*60}\n")
        
        # Exit with appropriate code
        sys.exit(0 if summary.success else 1)
    
    except Exception as e:
        logger.error(f"Execution failed: {e}")
        print(f"ERROR: {e}")
        sys.exit(1)

def test_connections():
    """Test all API connections."""
    logger.info("Testing API connections...")
    
    try:
        data_processor = DataProcessor()
        results = data_processor.test_all_connections()
        
        print(f"\n{'='*40}")
        print("CONNECTION TEST RESULTS")
        print(f"{'='*40}")
        
        all_good = True
        for service, status in results.items():
            status_text = "✓ OK" if status else "✗ FAILED"
            print(f"{service:<15}: {status_text}")
            if not status:
                all_good = False
        
        print(f"{'='*40}")
        print(f"Overall: {'✓ ALL CONNECTIONS OK' if all_good else '✗ SOME CONNECTIONS FAILED'}")
        print(f"{'='*40}\n")
        
        sys.exit(0 if all_good else 1)
    
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        print(f"ERROR: {e}")
        sys.exit(1)

def show_status():
    """Show system status."""
    logger.info("Getting system status...")
    
    try:
        # Get scheduler status
        scheduler_status = daily_runner.get_scheduler_status()
        
        # Get factory status
        factory_status = agent_factory.get_factory_status()
        
        print(f"\n{'='*60}")
        print("TRADING AUTOMATION SYSTEM STATUS")
        print(f"{'='*60}")
        
        # Scheduler info
        print(f"Scheduler State: {scheduler_status['state'].upper()}")
        print(f"Execution Time: {scheduler_status['execution_time']} {scheduler_status['timezone']}")
        print(f"Next Run: {scheduler_status['next_scheduled_run'] or 'Not scheduled'}")
        
        if scheduler_status['last_execution']:
            last_exec = scheduler_status['last_execution']
            print(f"Last Execution: {last_exec['date']} ({'SUCCESS' if last_exec['success'] else 'FAILED'})")
            print(f"  Duration: {last_exec['duration']:.1f}s")
            print(f"  Agents: {last_exec['agents_executed']}")
            print(f"  Trades: {last_exec['trades_processed']}")
            print(f"  Orders: {last_exec['orders_placed']}")
        
        # Market info
        market_status = scheduler_status['market_status']
        print(f"Today is trading day: {'Yes' if market_status['today_is_trading_day'] else 'No'}")
        print(f"Next trading day: {market_status['next_trading_day']}")
        
        print()
        
        # Agent info
        print(f"Registered Agents: {factory_status['registered_agents']}")
        print(f"Active Agents: {factory_status['active_agents']}")
        print(f"Enabled Agents: {factory_status['enabled_agents']}")
        
        print("\nAgent Details:")
        for agent_id, agent_info in factory_status['agents'].items():
            status_icon = "✓" if agent_info['active'] and agent_info['enabled'] else "✗"
            print(f"  {status_icon} {agent_id} ({agent_info['type']}) - {agent_info['health_status']}")
        
        # Statistics
        stats = scheduler_status['statistics']
        print(f"\nExecution Statistics:")
        print(f"  Total executions: {stats['total_executions']}")
        print(f"  Success rate: {stats['success_rate']:.1f}%")
        
        print(f"{'='*60}\n")
    
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        print(f"ERROR: {e}")
        sys.exit(1)

def run_intraday_scheduler():
    """Start the intraday scheduler for technical agents."""
    logger.info("Starting intraday scheduler for technical trading agents...")
    
    try:
        # Create and register technical agents
        agents = agent_factory.create_agents_from_config()
        
        # Filter technical agents
        technical_agents = [agent for agent in agents if isinstance(agent, AndyGrokAgent)]
        
        if not technical_agents:
            logger.warning("No technical agents found in configuration")
            print("No technical agents configured. Please add technical agents to config/agents.json")
            sys.exit(1)
        
        # Add technical agents to intraday scheduler
        for agent in technical_agents:
            intraday_scheduler.add_technical_agent(agent)
            logger.info(f"Added technical agent {agent.agent_id} to intraday scheduler")
        
        # Start health server
        health_server.start()
        logger.info("Health server started on port 8080")
        
        # Start intraday scheduler
        intraday_scheduler.start()
        logger.info(f"Intraday scheduler started with {len(technical_agents)} technical agents")
        
        print(f"\n🚀 Intraday scheduler started successfully!")
        print(f"Technical agents: {', '.join([agent.agent_id for agent in technical_agents])}")
        print(f"Health server: http://localhost:8080")
        print(f"Press Ctrl+C to stop...\n")
        
        # Keep the main thread alive
        try:
            while True:
                time.sleep(60)
                
                # Check scheduler health
                status = intraday_scheduler.get_status()
                if not status['running']:
                    logger.error("Intraday scheduler stopped running")
                    break
        
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        
        finally:
            # Graceful shutdown
            logger.info("Shutting down intraday scheduler...")
            intraday_scheduler.stop()
            health_server.stop()
            logger.info("Intraday scheduler stopped")
    
    except Exception as e:
        logger.error(f"Intraday scheduler failed: {e}", exc_info=True)
        print(f"ERROR: {e}")
        sys.exit(1)

def run_andy_grok_once():
    """Run Andy Grok agent once for testing."""
    logger.info("Running Andy Grok agent once...")
    
    try:
        # Create Andy Grok agent from config
        agents = agent_factory.create_agents_from_config()
        andy_grok_agents = [agent for agent in agents if isinstance(agent, AndyGrokAgent)]
        
        if not andy_grok_agents:
            logger.error("No Andy Grok agent found in configuration")
            print("Andy Grok agent not found. Please check config/agents.json")
            sys.exit(1)
        
        agent = andy_grok_agents[0]
        
        print(f"\n🤖 Running {agent.agent_id} ({agent.config.get('name', 'Unknown')})...")
        print(f"Target ticker: {agent.target_ticker}")
        print(f"RSI thresholds: oversold < {agent.rsi_oversold_threshold}, overbought > {agent.rsi_overbought_threshold}")
        
        # Execute intraday workflow
        start_time = datetime.now()
        result = agent.execute_intraday_workflow()
        duration = (datetime.now() - start_time).total_seconds()
        
        print(f"\n📊 Execution Results:")
        print(f"Success: {'✓' if result.success else '✗'}")
        print(f"Duration: {duration:.2f}s")
        print(f"Trades processed: {result.trades_processed}")
        print(f"Orders placed: {result.orders_placed}")
        
        if result.errors:
            print(f"Errors: {len(result.errors)}")
            for error in result.errors:
                print(f"  - {error}")
        
        # Show strategy status
        status = agent.get_strategy_status()
        print(f"\n📈 Strategy Status:")
        print(f"Account equity: ${status['account_equity']:.2f}")
        print(f"Daily trades: {status['daily_trade_count']}")
        print(f"Last RSI: {status['last_rsi_value']:.2f}" if status['last_rsi_value'] else "Last RSI: Not calculated")
        print(f"Market open: {'Yes' if status['market_status']['is_open'] else 'No'}")
        print(f"Should close positions: {'Yes' if status['market_status']['should_close_positions'] else 'No'}")
        
        sys.exit(0 if result.success else 1)
    
    except Exception as e:
        logger.error(f"Andy Grok execution failed: {e}", exc_info=True)
        print(f"ERROR: {e}")
        sys.exit(1)

def show_intraday_status():
    """Show intraday scheduler status."""
    logger.info("Getting intraday scheduler status...")
    
    try:
        status = intraday_scheduler.get_status()
        
        print(f"\n{'='*60}")
        print("INTRADAY SCHEDULER STATUS")
        print(f"{'='*60}")
        
        # Scheduler info
        print(f"Running: {'Yes' if status['running'] else 'No'}")
        print(f"Total tasks: {status['total_tasks']}")
        print(f"Active tasks: {status['active_tasks']}")
        
        # Statistics
        stats = status['statistics']
        print(f"\nExecution Statistics:")
        print(f"  Total executions: {stats['total_executions']}")
        print(f"  Successful: {stats['successful_executions']}")
        print(f"  Failed: {stats['failed_executions']}")
        print(f"  Success rate: {stats['success_rate']:.1f}%")
        print(f"  Uptime: {stats['uptime_seconds']:.0f}s")
        
        if stats['last_execution_time']:
            print(f"  Last execution: {stats['last_execution_time']}")
        
        # Task details
        print(f"\nTasks:")
        for task_id, task_info in status['tasks'].items():
            status_icon = "✓" if task_info['enabled'] else "✗"
            print(f"  {status_icon} {task_id} ({task_info['schedule_type']}) at {task_info['execution_time']}")
            print(f"    Agent: {task_info['agent_id']}")
            print(f"    Executions: {task_info['execution_count']}, Errors: {task_info['error_count']}")
            if task_info['last_execution']:
                print(f"    Last run: {task_info['last_execution']}")
        
        # Market status
        market = status['market_status']
        print(f"\nMarket Status:")
        print(f"  Is market day: {'Yes' if market['is_market_day'] else 'No'}")
        print(f"  Timezone: {market['timezone']}")
        if 'current_time_et' in market:
            print(f"  Current ET time: {market['current_time_et']}")
        
        # Timezone fix status
        if 'timezone_fix' in status:
            tz_fix = status['timezone_fix']
            print(f"\nTimezone Fix:")
            print(f"  Enabled: {'Yes' if tz_fix['enabled'] else 'No'}")
            print(f"  Description: {tz_fix['description']}")
            print(f"  Execution window: {tz_fix['execution_window_minutes']} minutes")
            if tz_fix['last_execution_dates']:
                print(f"  Last executions: {dict(tz_fix['last_execution_dates'])}")
        
        print(f"{'='*60}\n")
    
    except Exception as e:
        logger.error(f"Intraday status check failed: {e}")
        print(f"ERROR: {e}")
        sys.exit(1)

def list_agents():
    """List all configured agents."""
    logger.info("Listing agents...")
    
    try:
        enabled_agents = settings.get_enabled_agents()
        
        print(f"\n{'='*80}")
        print("CONFIGURED TRADING AGENTS")
        print(f"{'='*80}")
        
        if not enabled_agents:
            print("No agents configured.")
            return
        
        for agent in enabled_agents:
            print(f"\nAgent ID: {agent['id']}")
            print(f"Name: {agent['name']}")
            print(f"Type: {agent['type']}")
            print(f"Politicians: {', '.join(agent['politicians'])}")
            print(f"Enabled: {'Yes' if agent.get('enabled', True) else 'No'}")
            
            params = agent.get('parameters', {})
            if params:
                print(f"Parameters:")
                for key, value in params.items():
                    print(f"  {key}: {value}")
        
        print(f"\nTotal agents: {len(enabled_agents)}")
        print(f"{'='*80}\n")
    
    except Exception as e:
        logger.error(f"Failed to list agents: {e}")
        print(f"ERROR: {e}")
        sys.exit(1)

def run_all_schedulers():
    """Start all agents together during market hours."""
    logger.info("Starting all trading agents for market hours execution...")
    
    try:
        # Start health server
        health_server.start()
        logger.info("Health server started on port 8080")
        
        # Create and register ALL agents for market hours execution
        agents = agent_factory.create_agents_from_config()
        technical_agents = [agent for agent in agents if isinstance(agent, AndyGrokAgent)]
        congressional_agents = [agent for agent in agents if not isinstance(agent, AndyGrokAgent)]
        
        if not agents:
            logger.warning("No agents found in configuration")
            print("No agents configured. Please add agents to config/agents.json")
            sys.exit(1)
        
        # Add ALL agents to intraday scheduler for market hours execution
        for agent in agents:
            if isinstance(agent, AndyGrokAgent):
                # Technical agents get their full intraday workflow
                intraday_scheduler.add_technical_agent(agent)
                logger.info(f"Added technical agent {agent.agent_id} to market hours scheduler")
            else:
                # Congressional agents get morning-only execution
                intraday_scheduler.add_congressional_agent(agent)
                logger.info(f"Added congressional agent {agent.agent_id} to market hours scheduler")
        
        # Start market hours scheduler
        intraday_scheduler.start()
        logger.info(f"Market hours scheduler started with {len(agents)} total agents")
        
        print(f"\n🚀 All agents scheduled for market hours execution!")
        print(f"Congressional agents: {len(congressional_agents)} (execute at market open 9:30 AM ET)")
        if technical_agents:
            print(f"Technical agents: {len(technical_agents)} (full market hours - open & close)")
            print(f"  - {', '.join([agent.agent_id for agent in technical_agents])}")
        print(f"Total agents: {len(agents)}")
        print(f"Health server: http://localhost:8080")
        print(f"Press Ctrl+C to stop all schedulers...\n")
        
        # Keep the main thread alive
        try:
            while True:
                time.sleep(60)
                
                # Check scheduler health
                intraday_status = intraday_scheduler.get_status()
                if not intraday_status['running']:
                    logger.error("Market hours scheduler stopped running")
                    break
        
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        
        finally:
            # Graceful shutdown
            logger.info("Shutting down market hours scheduler...")
            intraday_scheduler.stop()
            health_server.stop()
            logger.info("All agents stopped")
    
    except Exception as e:
        logger.error(f"Failed to start schedulers: {e}", exc_info=True)
        print(f"ERROR: {e}")
        sys.exit(1)

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Trading Automation System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py start                        # Start ALL schedulers together (recommended)
  python main.py scheduler                    # Start congressional agents only
  python main.py intraday                     # Start technical agents only
  python main.py run-once                     # Run daily workflow once for today
  python main.py run-once --date 2024-01-15  # Run for specific date
  python main.py test-connections             # Test all API connections
  python main.py status                       # Show system status
  python main.py list-agents                  # List configured agents
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Start all schedulers command (recommended)
    subparsers.add_parser('start', help='Start ALL schedulers together (recommended)')
    
    # Individual scheduler commands
    subparsers.add_parser('scheduler', help='[DEPRECATED] Start congressional agents scheduler only (9:30 PM)')
    subparsers.add_parser('intraday', help='[DEPRECATED] Start technical agents scheduler only')
    
    # Run once command
    run_parser = subparsers.add_parser('run-once', help='Run daily workflow once')
    run_parser.add_argument('--date', help='Date to run for (YYYY-MM-DD)', default=None)
    
    # Test connections command
    subparsers.add_parser('test-connections', help='Test all API connections')
    
    # Status command
    subparsers.add_parser('status', help='Show system status')
    
    # List agents command
    subparsers.add_parser('list-agents', help='List configured agents')
    
    # Andy Grok run once command
    subparsers.add_parser('andy-grok-once', help='Run Andy Grok agent once for testing')
    
    # Intraday status command
    subparsers.add_parser('intraday-status', help='Show intraday scheduler status')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Initialize logging
    logger.info(f"Starting Trading Automation System - Command: {args.command}")
    
    try:
        if args.command == 'start':
            run_all_schedulers()
        elif args.command == 'scheduler':
            run_scheduler()
        elif args.command == 'intraday':
            run_intraday_scheduler()
        elif args.command == 'run-once':
            run_once(args.date)
        elif args.command == 'test-connections':
            test_connections()
        elif args.command == 'status':
            show_status()
        elif args.command == 'list-agents':
            list_agents()
        elif args.command == 'andy-grok-once':
            run_andy_grok_once()
        elif args.command == 'intraday-status':
            show_intraday_status()
        else:
            parser.print_help()
            sys.exit(1)
    
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()