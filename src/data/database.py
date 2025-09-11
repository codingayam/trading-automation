"""
Database connection management and schema initialization for trading automation system.
Provides connection pooling, transaction management, and database utilities.
"""
import sqlite3
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple, Union
from contextlib import contextmanager
from datetime import datetime, date
import json
import shutil

from config.settings import settings
from src.utils.logging import get_logger

logger = get_logger('database')

class DatabaseManager:
    """
    Database manager with connection pooling, transaction management, and utilities.
    """
    
    _instance = None
    _lock = threading.Lock()
    _local = threading.local()
    
    def __new__(cls):
        """Singleton pattern to ensure single database manager instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.db_path = settings.database.full_path
            self.backup_enabled = settings.database.backup_enabled
            self.backup_retention_days = settings.database.backup_retention_days
            self.initialized = True
            
            # Ensure database directory exists
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            
            logger.info(
                "Database manager initialized",
                db_path=self.db_path,
                backup_enabled=self.backup_enabled
            )
    
    def get_connection(self) -> sqlite3.Connection:
        """Get database connection with proper configuration."""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self._local.connection = sqlite3.connect(
                self.db_path,
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
                check_same_thread=False,
                timeout=30.0
            )
            
            # Enable foreign key constraints
            self._local.connection.execute("PRAGMA foreign_keys = ON")
            
            # Set row factory for dictionary-like access
            self._local.connection.row_factory = sqlite3.Row
            
            # Configure WAL mode for better concurrency
            self._local.connection.execute("PRAGMA journal_mode = WAL")
            
            # Configure synchronous mode for performance
            self._local.connection.execute("PRAGMA synchronous = NORMAL")
        
        return self._local.connection
    
    @contextmanager
    def get_cursor(self):
        """Context manager for database cursor with automatic cleanup."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
        finally:
            cursor.close()
    
    @contextmanager
    def transaction(self):
        """Context manager for database transactions with automatic rollback on error."""
        conn = self.get_connection()
        try:
            yield conn
            conn.commit()
            logger.debug("Database transaction committed")
        except Exception as e:
            conn.rollback()
            logger.error("Database transaction rolled back", exception=e)
            raise
    
    def execute_query(self, query: str, params: Optional[Tuple] = None) -> List[sqlite3.Row]:
        """Execute SELECT query and return results."""
        with self.get_cursor() as cursor:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.fetchall()
    
    def execute_single(self, query: str, params: Optional[Tuple] = None) -> Optional[sqlite3.Row]:
        """Execute SELECT query and return single result."""
        with self.get_cursor() as cursor:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.fetchone()
    
    def execute_modify(self, query: str, params: Optional[Tuple] = None) -> int:
        """Execute INSERT/UPDATE/DELETE query and return affected rows."""
        with self.transaction() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            affected_rows = cursor.rowcount
            cursor.close()
            return affected_rows
    
    def execute_many(self, query: str, params_list: List[Tuple]) -> int:
        """Execute multiple queries with different parameters."""
        with self.transaction() as conn:
            cursor = conn.cursor()
            cursor.executemany(query, params_list)
            affected_rows = cursor.rowcount
            cursor.close()
            return affected_rows
    
    def backup_database(self) -> Optional[str]:
        """Create database backup if enabled."""
        if not self.backup_enabled:
            return None
        
        try:
            backup_dir = Path(self.db_path).parent / 'backups'
            backup_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = backup_dir / f'trading_automation_{timestamp}.db'
            
            shutil.copy2(self.db_path, backup_path)
            
            # Clean up old backups
            self._cleanup_old_backups(backup_dir)
            
            logger.info(
                "Database backup created",
                backup_path=str(backup_path)
            )
            return str(backup_path)
            
        except Exception as e:
            logger.error("Database backup failed", exception=e)
            return None
    
    def create_backup(self) -> Optional[str]:
        """Alias for backup_database method."""
        return self.backup_database()
    
    def insert_trade(self, trade_data: Dict[str, Any]) -> int:
        """Insert a new trade record."""
        query = """
        INSERT INTO trades (
            agent_id, ticker, trade_date, execution_date, order_type,
            quantity, price, order_status, alpaca_order_id,
            source_politician, source_trade_date
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        params = (
            trade_data.get('agent_id'),
            trade_data.get('ticker'),
            trade_data.get('trade_date', date.today()),
            trade_data.get('execution_date', datetime.now()),
            trade_data.get('order_type', 'market'),
            trade_data.get('quantity'),
            trade_data.get('price'),
            trade_data.get('order_status', 'pending'),
            trade_data.get('alpaca_order_id'),
            trade_data.get('source_politician'),
            trade_data.get('source_trade_date')
        )
        
        self.execute_modify(query, params)
        
        # Get the inserted trade ID
        result = self.execute_single("SELECT last_insert_rowid() as id")
        trade_id = result['id'] if result else None
        
        logger.info(
            "Trade record inserted",
            trade_id=trade_id,
            agent_id=trade_data.get('agent_id'),
            ticker=trade_data.get('ticker'),
            quantity=trade_data.get('quantity')
        )
        
        return trade_id
    
    def insert_position(self, position_data: Dict[str, Any]):
        """Insert or update agent position."""
        query = """
        INSERT INTO agent_positions (
            agent_id, ticker, quantity, avg_cost, current_price, market_value, unrealized_pnl
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(agent_id, ticker) DO UPDATE SET
            quantity = excluded.quantity,
            avg_cost = excluded.avg_cost,
            current_price = excluded.current_price,
            market_value = excluded.market_value,
            unrealized_pnl = excluded.unrealized_pnl,
            last_updated = CURRENT_TIMESTAMP
        """
        
        params = (
            position_data.get('agent_id'),
            position_data.get('ticker'),
            position_data.get('quantity'),
            position_data.get('avg_cost'),
            position_data.get('current_price'),
            position_data.get('market_value'),
            position_data.get('unrealized_pnl')
        )
        
        self.execute_modify(query, params)
        
        logger.debug(
            "Position updated",
            agent_id=position_data.get('agent_id'),
            ticker=position_data.get('ticker'),
            quantity=position_data.get('quantity'),
            market_value=position_data.get('market_value')
        )
    
    def insert_daily_performance(self, performance_data: Dict[str, Any]):
        """Insert or update daily performance record."""
        query = """
        INSERT INTO daily_performance (
            agent_id, date, total_value, daily_return_pct, total_return_pct
        ) VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(agent_id, date) DO UPDATE SET
            total_value = excluded.total_value,
            daily_return_pct = excluded.daily_return_pct,
            total_return_pct = excluded.total_return_pct,
            created_at = CURRENT_TIMESTAMP
        """
        
        params = (
            performance_data.get('agent_id'),
            performance_data.get('date'),
            performance_data.get('total_value'),
            performance_data.get('daily_return_pct'),
            performance_data.get('total_return_pct')
        )
        
        self.execute_modify(query, params)
        
        logger.debug(
            "Daily performance updated",
            agent_id=performance_data.get('agent_id'),
            date=str(performance_data.get('date')),
            total_value=performance_data.get('total_value')
        )
    
    def _cleanup_old_backups(self, backup_dir: Path):
        """Remove old backup files based on retention policy."""
        try:
            backup_files = list(backup_dir.glob('trading_automation_*.db'))
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # Keep only the specified number of backups
            files_to_remove = backup_files[self.backup_retention_days:]
            
            for file_path in files_to_remove:
                file_path.unlink()
                logger.debug(f"Removed old backup: {file_path}")
                
        except Exception as e:
            logger.warning("Failed to cleanup old backups", exception=e)

# Database schema definition
DATABASE_SCHEMA = """
-- Trades table: Store all trade executions with complete audit trail
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id VARCHAR(50) NOT NULL,
    ticker VARCHAR(10) NOT NULL,
    trade_date DATE NOT NULL,
    execution_date TIMESTAMP NOT NULL,
    order_type VARCHAR(20) NOT NULL,
    quantity DECIMAL(10,4) NOT NULL,
    price DECIMAL(10,2),
    order_status VARCHAR(20) NOT NULL,
    alpaca_order_id VARCHAR(50),
    source_politician VARCHAR(100),
    source_trade_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Agent positions table: Track current positions and performance for each agent
CREATE TABLE IF NOT EXISTS agent_positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id VARCHAR(50) NOT NULL,
    ticker VARCHAR(10) NOT NULL,
    quantity DECIMAL(10,4) NOT NULL,
    avg_cost DECIMAL(10,2) NOT NULL,
    current_price DECIMAL(10,2),
    market_value DECIMAL(12,2),
    unrealized_pnl DECIMAL(12,2),
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(agent_id, ticker)
);

-- Daily performance table: Store daily performance metrics for historical tracking
CREATE TABLE IF NOT EXISTS daily_performance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id VARCHAR(50) NOT NULL,
    date DATE NOT NULL,
    total_value DECIMAL(12,2) NOT NULL,
    daily_return_pct DECIMAL(8,4),
    total_return_pct DECIMAL(8,4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(agent_id, date)
);

-- Create indexes for query optimization
CREATE INDEX IF NOT EXISTS idx_trades_agent_id ON trades(agent_id);
CREATE INDEX IF NOT EXISTS idx_trades_trade_date ON trades(trade_date);
CREATE INDEX IF NOT EXISTS idx_trades_ticker ON trades(ticker);
CREATE INDEX IF NOT EXISTS idx_trades_execution_date ON trades(execution_date);

CREATE INDEX IF NOT EXISTS idx_positions_agent_id ON agent_positions(agent_id);
CREATE INDEX IF NOT EXISTS idx_positions_ticker ON agent_positions(ticker);
CREATE INDEX IF NOT EXISTS idx_positions_agent_ticker ON agent_positions(agent_id, ticker);

CREATE INDEX IF NOT EXISTS idx_performance_agent_id ON daily_performance(agent_id);
CREATE INDEX IF NOT EXISTS idx_performance_date ON daily_performance(date);
CREATE INDEX IF NOT EXISTS idx_performance_agent_date ON daily_performance(agent_id, date);
"""

def initialize_database():
    """Initialize database with schema and sample data."""
    db = DatabaseManager()
    
    try:
        logger.info("Initializing database schema")
        
        # Execute schema creation
        with db.transaction() as conn:
            conn.executescript(DATABASE_SCHEMA)
        
        logger.info("Database schema initialized successfully")
        
        # Create backup after initialization
        db.backup_database()
        
        return True
        
    except Exception as e:
        logger.error("Database initialization failed", exception=e)
        return False

def insert_trade(agent_id: str, ticker: str, trade_data: Dict[str, Any]) -> int:
    """Insert a new trade record."""
    db = DatabaseManager()
    
    query = """
    INSERT INTO trades (
        agent_id, ticker, trade_date, execution_date, order_type,
        quantity, price, order_status, alpaca_order_id,
        source_politician, source_trade_date
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    params = (
        agent_id,
        ticker,
        trade_data.get('trade_date', date.today()),
        trade_data.get('execution_date', datetime.now()),
        trade_data.get('order_type', 'market'),
        trade_data.get('quantity'),
        trade_data.get('price'),
        trade_data.get('order_status', 'pending'),
        trade_data.get('alpaca_order_id'),
        trade_data.get('source_politician'),
        trade_data.get('source_trade_date')
    )
    
    db.execute_modify(query, params)
    
    # Get the inserted trade ID
    trade_id = db.execute_single("SELECT last_insert_rowid() as id").get('id')
    
    logger.info(
        "Trade record inserted",
        trade_id=trade_id,
        agent_id=agent_id,
        ticker=ticker,
        quantity=trade_data.get('quantity'),
        order_type=trade_data.get('order_type')
    )
    
    return trade_id

def update_position(agent_id: str, ticker: str, position_data: Dict[str, Any]):
    """Update or insert agent position."""
    db = DatabaseManager()
    
    query = """
    INSERT INTO agent_positions (
        agent_id, ticker, quantity, avg_cost, current_price, market_value, unrealized_pnl
    ) VALUES (?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(agent_id, ticker) DO UPDATE SET
        quantity = excluded.quantity,
        avg_cost = excluded.avg_cost,
        current_price = excluded.current_price,
        market_value = excluded.market_value,
        unrealized_pnl = excluded.unrealized_pnl,
        last_updated = CURRENT_TIMESTAMP
    """
    
    params = (
        agent_id,
        ticker,
        position_data.get('quantity'),
        position_data.get('avg_cost'),
        position_data.get('current_price'),
        position_data.get('market_value'),
        position_data.get('unrealized_pnl')
    )
    
    db.execute_modify(query, params)
    
    logger.debug(
        "Position updated",
        agent_id=agent_id,
        ticker=ticker,
        quantity=position_data.get('quantity'),
        market_value=position_data.get('market_value')
    )

def update_daily_performance(agent_id: str, date: date, performance_data: Dict[str, Any]):
    """Update or insert daily performance record."""
    db = DatabaseManager()
    
    query = """
    INSERT INTO daily_performance (
        agent_id, date, total_value, daily_return_pct, total_return_pct
    ) VALUES (?, ?, ?, ?, ?)
    ON CONFLICT(agent_id, date) DO UPDATE SET
        total_value = excluded.total_value,
        daily_return_pct = excluded.daily_return_pct,
        total_return_pct = excluded.total_return_pct,
        created_at = CURRENT_TIMESTAMP
    """
    
    params = (
        agent_id,
        date,
        performance_data.get('total_value'),
        performance_data.get('daily_return_pct'),
        performance_data.get('total_return_pct')
    )
    
    db.execute_modify(query, params)
    
    logger.debug(
        "Daily performance updated",
        agent_id=agent_id,
        date=str(date),
        total_value=performance_data.get('total_value')
    )

def get_agent_positions(agent_id: str) -> List[Dict[str, Any]]:
    """Get all positions for an agent."""
    db = DatabaseManager()
    
    query = """
    SELECT * FROM agent_positions 
    WHERE agent_id = ?
    ORDER BY market_value DESC
    """
    
    rows = db.execute_query(query, (agent_id,))
    return [dict(row) for row in rows]

def get_agent_performance_history(agent_id: str, days: int = 30) -> List[Dict[str, Any]]:
    """Get performance history for an agent."""
    db = DatabaseManager()
    
    query = """
    SELECT * FROM daily_performance 
    WHERE agent_id = ?
    ORDER BY date DESC
    LIMIT ?
    """
    
    rows = db.execute_query(query, (agent_id, days))
    return [dict(row) for row in rows]

def get_all_agent_summaries() -> List[Dict[str, Any]]:
    """Get summary data for all agents."""
    db = DatabaseManager()
    
    # Get all agents from daily_performance table (which includes agents with $0 positions)
    query = """
    SELECT 
        dp.agent_id,
        COALESCE(COUNT(ap.ticker), 0) as position_count,
        COALESCE(SUM(ap.market_value), 0.0) as total_value,
        dp.daily_return_pct,
        dp.total_return_pct
    FROM daily_performance dp
    LEFT JOIN agent_positions ap ON dp.agent_id = ap.agent_id AND ap.quantity != 0
    WHERE dp.date = (SELECT MAX(date) FROM daily_performance WHERE agent_id = dp.agent_id)
    GROUP BY dp.agent_id
    """
    
    rows = db.execute_query(query)
    summaries = []
    for row in rows:
        summaries.append({
            'agent_id': row[0],
            'position_count': row[1],
            'total_value': row[2],
            'daily_return_pct': row[3],
            'total_return_pct': row[4]
        })
    return summaries

# Global database instance
db = DatabaseManager()