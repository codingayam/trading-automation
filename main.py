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
from src.agents.agent_factory import agent_factory
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

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Trading Automation System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py scheduler                    # Start the daily scheduler
  python main.py run-once                     # Run daily workflow once for today
  python main.py run-once --date 2024-01-15  # Run for specific date
  python main.py test-connections             # Test all API connections
  python main.py status                       # Show system status
  python main.py list-agents                  # List configured agents
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Scheduler command
    subparsers.add_parser('scheduler', help='Start the daily scheduler')
    
    # Run once command
    run_parser = subparsers.add_parser('run-once', help='Run daily workflow once')
    run_parser.add_argument('--date', help='Date to run for (YYYY-MM-DD)', default=None)
    
    # Test connections command
    subparsers.add_parser('test-connections', help='Test all API connections')
    
    # Status command
    subparsers.add_parser('status', help='Show system status')
    
    # List agents command
    subparsers.add_parser('list-agents', help='List configured agents')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Initialize logging
    logger.info(f"Starting Trading Automation System - Command: {args.command}")
    
    try:
        if args.command == 'scheduler':
            run_scheduler()
        elif args.command == 'run-once':
            run_once(args.date)
        elif args.command == 'test-connections':
            test_connections()
        elif args.command == 'status':
            show_status()
        elif args.command == 'list-agents':
            list_agents()
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