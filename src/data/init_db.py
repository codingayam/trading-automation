#!/usr/bin/env python3
"""
Database initialization script for trading automation system.
Creates database schema, indexes, and sample data for development/testing.
"""
import sys
from pathlib import Path
from datetime import datetime, date, timedelta
import random

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.data.database import initialize_database, insert_trade, update_position, update_daily_performance
from src.utils.logging import get_logger
from config.settings import settings

logger = get_logger('database_init')

def create_sample_data():
    """Create sample data for development and testing."""
    logger.info("Creating sample data for development")
    
    # Sample agent configurations
    agents = [
        'transportation_committee',
        'josh_gottheimer', 
        'sheldon_whitehouse',
        'nancy_pelosi',
        'dan_meuser'
    ]
    
    # Sample tickers 
    tickers = ['AAPL', 'TSLA', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'NFLX']
    
    # Create sample trades for the last 30 days
    end_date = date.today()
    start_date = end_date - timedelta(days=30)
    
    trade_id_counter = 1
    
    for agent_id in agents:
        logger.info(f"Creating sample data for agent: {agent_id}")
        
        # Create some historical trades
        current_date = start_date
        positions = {}
        
        while current_date <= end_date:
            # Random chance of trades on any given day
            if random.random() < 0.3:  # 30% chance of trade per day
                ticker = random.choice(tickers)
                quantity = random.randint(1, 10)
                price = round(random.uniform(50, 500), 2)
                
                # Insert trade
                trade_data = {
                    'trade_date': current_date,
                    'execution_date': datetime.combine(current_date, datetime.min.time().replace(hour=21, minute=30)),
                    'order_type': 'market',
                    'quantity': quantity,
                    'price': price,
                    'order_status': 'filled',
                    'alpaca_order_id': f'test_order_{trade_id_counter}',
                    'source_politician': agent_id.replace('_', ' ').title(),
                    'source_trade_date': current_date - timedelta(days=1)
                }
                
                insert_trade(agent_id, ticker, trade_data)
                trade_id_counter += 1
                
                # Update position tracking
                if ticker in positions:
                    positions[ticker]['quantity'] += quantity
                    # Weighted average cost
                    total_cost = positions[ticker]['avg_cost'] * positions[ticker]['quantity'] + price * quantity
                    positions[ticker]['quantity'] += quantity
                    positions[ticker]['avg_cost'] = total_cost / positions[ticker]['quantity']
                else:
                    positions[ticker] = {
                        'quantity': quantity,
                        'avg_cost': price
                    }
            
            current_date += timedelta(days=1)
        
        # Create current positions
        for ticker, position in positions.items():
            if position['quantity'] > 0:
                # Simulate current price with some variation
                current_price = round(position['avg_cost'] * random.uniform(0.8, 1.3), 2)
                market_value = position['quantity'] * current_price
                unrealized_pnl = market_value - (position['quantity'] * position['avg_cost'])
                
                position_data = {
                    'quantity': position['quantity'],
                    'avg_cost': position['avg_cost'],
                    'current_price': current_price,
                    'market_value': market_value,
                    'unrealized_pnl': unrealized_pnl
                }
                
                update_position(agent_id, ticker, position_data)
        
        # Create performance history
        current_date = start_date
        previous_value = 10000  # Starting portfolio value
        
        while current_date <= end_date:
            # Simulate daily performance
            daily_change = random.uniform(-0.05, 0.05)  # -5% to +5% daily change
            current_value = previous_value * (1 + daily_change)
            
            total_return_pct = ((current_value - 10000) / 10000) * 100
            daily_return_pct = daily_change * 100
            
            performance_data = {
                'total_value': round(current_value, 2),
                'daily_return_pct': round(daily_return_pct, 4),
                'total_return_pct': round(total_return_pct, 4)
            }
            
            update_daily_performance(agent_id, current_date, performance_data)
            
            previous_value = current_value
            current_date += timedelta(days=1)

def verify_database():
    """Verify database was created correctly."""
    from src.data.database import db
    
    logger.info("Verifying database initialization")
    
    try:
        # Check if tables exist
        tables = db.execute_query("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """)
        
        table_names = [row['name'] for row in tables]
        expected_tables = ['trades', 'agent_positions', 'daily_performance']
        
        for table in expected_tables:
            if table in table_names:
                logger.info(f"Table '{table}' exists")
            else:
                logger.error(f"Table '{table}' missing")
                return False
        
        # Check if indexes exist
        indexes = db.execute_query("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND name LIKE 'idx_%'
            ORDER BY name
        """)
        
        index_count = len(indexes)
        logger.info(f"Found {index_count} indexes")
        
        # Check sample data
        agents = db.execute_query("SELECT DISTINCT agent_id FROM trades")
        logger.info(f"Found {len(agents)} agents with trade data")
        
        positions = db.execute_query("SELECT COUNT(*) as count FROM agent_positions")
        logger.info(f"Found {positions[0]['count']} positions")
        
        performance = db.execute_query("SELECT COUNT(*) as count FROM daily_performance") 
        logger.info(f"Found {performance[0]['count']} performance records")
        
        logger.info("Database verification completed successfully")
        return True
        
    except Exception as e:
        logger.error("Database verification failed", exception=e)
        return False

def main():
    """Main initialization function."""
    logger.info("Starting database initialization")
    
    try:
        # Initialize database schema
        if not initialize_database():
            logger.error("Failed to initialize database schema")
            return False
        
        # Create sample data for development
        if settings.is_development:
            create_sample_data()
        
        # Verify database
        if not verify_database():
            logger.error("Database verification failed")
            return False
        
        logger.info("Database initialization completed successfully")
        return True
        
    except Exception as e:
        logger.error("Database initialization failed", exception=e)
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)