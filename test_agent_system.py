#!/usr/bin/env python3
"""
Test script for the agent system.
Used to verify that all components work together correctly.
"""
import os
from dotenv import load_dotenv
from datetime import date, datetime

# Load environment variables from .env file
load_dotenv()

# Set the required API keys from .env
os.environ['QUIVER_API_KEY'] = os.getenv('token', '')
os.environ['ALPACA_API_KEY'] = os.getenv('ALPACA_API_KEY_ID', '')
os.environ['ALPACA_SECRET_KEY'] = os.getenv('ALPACA_API_SECRET_KEY', '')
from src.agents.agent_factory import agent_factory
from src.data.quiver_client import CongressionalTrade
from src.utils.logging import get_logger

logger = get_logger(__name__)

def create_mock_congressional_trades():
    """Create mock congressional trades for testing."""
    trades = [
        CongressionalTrade(
            politician="Josh Gottheimer",
            ticker="AAPL",
            transaction_date=date.today(),
            trade_type="Purchase",
            amount_range="$50,001 - $100,000",
            amount_min=50001,
            amount_max=100000,
            last_modified=date.today(),
            raw_data={}
        ),
        CongressionalTrade(
            politician="Nancy Pelosi",
            ticker="TSLA", 
            transaction_date=date.today(),
            trade_type="Purchase",
            amount_range="$50,001 - $100,000",
            amount_min=50001,
            amount_max=100000,
            last_modified=date.today(),
            raw_data={}
        ),
        CongressionalTrade(
            politician="Peter DeFazio",  # Transportation Committee member
            ticker="MSFT",
            transaction_date=date.today(),
            trade_type="Purchase",
            amount_range="$50,001 - $100,000",
            amount_min=50001,
            amount_max=100000,
            last_modified=date.today(),
            raw_data={}
        ),
        CongressionalTrade(
            politician="Random Politician",  # Should not match any agent
            ticker="GOOGL",
            transaction_date=date.today(),
            trade_type="Purchase",
            amount_range="$50,001 - $100,000",
            amount_min=50001,
            amount_max=100000,
            last_modified=date.today(),
            raw_data={}
        )
    ]
    return trades

def test_agent_creation():
    """Test agent creation from configuration."""
    logger.info("Testing agent creation...")
    
    # Create agents from configuration
    agents = agent_factory.create_agents_from_config()
    
    print(f"Created {len(agents)} agents:")
    for agent in agents:
        print(f"  - {agent.agent_id}: {agent.config['name']}")
        print(f"    Type: {agent.config['type']}")
        print(f"    Politicians: {', '.join(agent.politicians)}")
    
    return agents

def test_trade_processing(agents):
    """Test trade processing by agents."""
    logger.info("Testing trade processing...")
    
    # Create mock trades
    mock_trades = create_mock_congressional_trades()
    
    print(f"\nProcessing {len(mock_trades)} mock congressional trades:")
    for trade in mock_trades:
        print(f"  - {trade.politician}: {trade.ticker} ${trade.amount_max:,.0f} ({trade.trade_type})")
    
    print("\nAgent processing results:")
    
    for agent in agents:
        logger.info(f"Processing trades for agent: {agent.agent_id}")
        
        try:
            # Process trades
            trade_decisions = agent.process_trades(mock_trades)
            
            print(f"\n{agent.agent_id} ({agent.config['name']}):")
            if trade_decisions:
                for decision in trade_decisions:
                    print(f"  ✓ Decision: {decision.side.upper()} {decision.ticker} ${decision.amount:.2f}")
                    print(f"    Reason: {decision.reason}")
            else:
                print(f"  - No matching trades found")
        
        except Exception as e:
            print(f"  ✗ Error: {e}")
            logger.error(f"Agent {agent.agent_id} processing failed: {e}")

def test_factory_operations():
    """Test factory operations."""
    logger.info("Testing factory operations...")
    
    print(f"\n{'='*50}")
    print("FACTORY STATUS")
    print(f"{'='*50}")
    
    status = agent_factory.get_factory_status()
    
    print(f"Registered agents: {status['registered_agents']}")
    print(f"Active agents: {status['active_agents']}")
    print(f"Enabled agents: {status['enabled_agents']}")
    print(f"Available types: {', '.join(status['available_types'])}")
    
    stats = status['statistics']
    print(f"Total created: {stats['total_created']}")
    print(f"Failed agents: {stats['failed_agents']}")
    
    print(f"\nAgent details:")
    for agent_id, info in status['agents'].items():
        status_icon = "✓" if info['active'] and info['enabled'] else "✗"
        print(f"  {status_icon} {agent_id}")
        print(f"    Type: {info['type']}")
        print(f"    Created: {info['created_at']}")
        print(f"    Health: {info['health_status']}")

def test_health_checks():
    """Test agent health checks."""
    logger.info("Testing health checks...")
    
    print(f"\n{'='*50}")
    print("HEALTH CHECK RESULTS")
    print(f"{'='*50}")
    
    health_results = agent_factory.health_check_all_agents()
    
    for agent_id, health_status in health_results.items():
        status_icon = "✓" if health_status.value == "healthy" else "⚠" if health_status.value == "degraded" else "✗"
        print(f"  {status_icon} {agent_id}: {health_status.value.upper()}")

def main():
    """Main test function."""
    print(f"{'='*60}")
    print("TRADING AGENT SYSTEM TEST")
    print(f"{'='*60}")
    
    try:
        # Test 1: Agent creation
        agents = test_agent_creation()
        
        if not agents:
            print("ERROR: No agents created!")
            return
        
        # Test 2: Trade processing
        test_trade_processing(agents)
        
        # Test 3: Factory operations
        test_factory_operations()
        
        # Test 4: Health checks
        test_health_checks()
        
        print(f"\n{'='*60}")
        print("ALL TESTS COMPLETED")
        print(f"{'='*60}")
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        print(f"ERROR: {e}")

if __name__ == '__main__':
    main()