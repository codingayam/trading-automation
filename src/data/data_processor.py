"""
Data Processing Engine for orchestrating all API integrations.
Coordinates data fetching, validation, processing, and storage across all APIs.
"""
import time
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

from config.settings import settings
from src.data.database import DatabaseManager
from src.data.quiver_client import QuiverClient, CongressionalTrade
from src.data.alpaca_client import AlpacaClient, PositionInfo
from src.data.market_data_service import MarketDataService
from src.utils.logging import get_logger
from src.utils.exceptions import DataProcessingError, APIError, ValidationError
from src.utils.monitoring import metrics_collector
from src.utils.calculations import calculate_position_metrics, calculate_portfolio_metrics

logger = get_logger(__name__)

@dataclass
class ProcessingResult:
    """Result of data processing operation."""
    success: bool
    processed_trades: int
    errors: List[str]
    execution_time: float
    timestamp: datetime

@dataclass
class PortfolioSnapshot:
    """Portfolio snapshot data."""
    agent_id: str
    timestamp: datetime
    total_value: float
    position_count: int
    positions: List[Dict[str, Any]]
    performance_metrics: Dict[str, Any]

class DataProcessor:
    """
    Unified data processing engine that orchestrates all API integrations.
    
    Features:
    - Data fetching workflow (scheduled or manual trigger)
    - Data validation and consistency checks across APIs
    - Transaction processing pipeline (fetch → filter → validate → store)
    - Portfolio synchronization between Alpaca and database
    - Performance metrics calculation and storage
    - Data reconciliation procedures
    - Partial failure scenario handling
    - Comprehensive logging for all data operations
    - Database transaction management for atomic operations
    - Data backup and recovery procedures
    """
    
    def __init__(self):
        """Initialize Data Processing Engine."""
        # Initialize API clients
        self.settings = settings
        self.quiver_client = QuiverClient()
        self.alpaca_client = AlpacaClient()
        self.market_data_service = MarketDataService()
        self.db = DatabaseManager()
        
        # Configuration
        self.max_concurrent_requests = 5
        self.processing_timeout = 300  # 5 minutes
        self.backup_enabled = self.settings.database.backup_enabled
        
        # State tracking
        self.last_processing_time = None
        self.processing_stats = {
            'total_runs': 0,
            'successful_runs': 0,
            'failed_runs': 0,
            'total_trades_processed': 0,
            'avg_processing_time': 0.0
        }
        
        logger.info("Initialized Data Processing Engine")
    
    def process_daily_data(self, target_date: Optional[date] = None) -> ProcessingResult:
        """
        Execute the complete daily data processing workflow.
        
        Args:
            target_date: Date to process data for (default: today)
            
        Returns:
            Processing result with status and metrics
        """
        if target_date is None:
            target_date = date.today()
        
        start_time = time.time()
        logger.info(f"Starting daily data processing for {target_date}")
        
        try:
            with self.db.transaction():
                # Create backup if enabled
                if self.backup_enabled:
                    self._create_data_backup()
                
                # Step 1: Fetch congressional trades
                logger.info("Step 1: Fetching congressional trades")
                congressional_trades = self._fetch_congressional_trades(target_date)
                
                # Step 2: Agent execution handled by dedicated agent workflows
                logger.info("Step 2: Skipping legacy direct trade execution (handled by agent workflows)")
                processed_trades = 0

                # Step 3: Synchronize portfolios
                logger.info("Step 3: Synchronizing portfolios")
                self._synchronize_portfolios()
                
                # Step 4: Update performance metrics
                logger.info("Step 4: Updating performance metrics")
                self._update_performance_metrics(target_date)
                
                # Step 5: Data validation and reconciliation
                logger.info("Step 5: Validating and reconciling data")
                validation_results = self._validate_data_consistency()
                
                execution_time = time.time() - start_time
                
                # Update processing statistics
                self._update_processing_stats(True, execution_time, processed_trades)
                
                result = ProcessingResult(
                    success=True,
                    processed_trades=processed_trades,
                    errors=validation_results.get('warnings', []),
                    execution_time=execution_time,
                    timestamp=datetime.now()
                )
                
                logger.info(f"Daily data processing completed successfully in {execution_time:.2f}s")
                metrics_collector.record_execution_time("daily_processing", execution_time)
                
                return result
        
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Daily data processing failed: {e}"
            logger.error(error_msg, exception=e)
            
            self._update_processing_stats(False, execution_time, 0)
            
            return ProcessingResult(
                success=False,
                processed_trades=0,
                errors=[error_msg],
                execution_time=execution_time,
                timestamp=datetime.now()
            )
    
    def _fetch_congressional_trades(self, target_date: date) -> List[CongressionalTrade]:
        """
        Fetch congressional trades for the target date.
        
        Args:
            target_date: Date to fetch trades for
            
        Returns:
            List of congressional trades
        """
        try:
            trades = self.quiver_client.get_congressional_trades(target_date)
            logger.info(f"Fetched {len(trades)} congressional trades for {target_date}")
            return trades
        
        except APIError as e:
            logger.error(f"Failed to fetch congressional trades: {e}")
            # Continue processing with empty list rather than failing completely
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching congressional trades: {e}")
            return []
    
    def _process_agent_trades(self, congressional_trades: List[CongressionalTrade], target_date: date) -> int:
        """
        Process congressional trades for all enabled agents.
        
        Args:
            congressional_trades: List of congressional trades
            target_date: Date being processed
            
        Returns:
            Total number of trades processed
        """
        if not congressional_trades:
            logger.info("No congressional trades to process")
            return 0
        
        enabled_agents = self.settings.get_enabled_agents()
        total_processed = 0
        
        for agent_config in enabled_agents:
            try:
                agent_id = agent_config['id']
                politicians = agent_config['politicians']
                
                logger.info(f"Processing trades for agent: {agent_id}")
                
                # Find matching trades for this agent
                matching_trades = []
                for trade in congressional_trades:
                    if self.quiver_client.find_matching_politicians(politicians, trade):
                        matching_trades.append(trade)
                
                if matching_trades:
                    processed = self._process_agent_specific_trades(agent_id, matching_trades, target_date)
                    total_processed += processed
                    logger.info(f"Processed {processed} trades for agent {agent_id}")
                else:
                    logger.info(f"No matching trades found for agent {agent_id}")
            
            except Exception as e:
                logger.error(f"Error processing trades for agent {agent_config.get('id', 'unknown')}: {e}")
                # Continue processing other agents
                continue
        
        return total_processed
    
    def _process_agent_specific_trades(self, agent_id: str, trades: List[CongressionalTrade], target_date: date) -> int:
        """
        Process trades for a specific agent.
        
        Args:
            agent_id: Agent identifier
            trades: List of trades to process
            target_date: Date being processed
            
        Returns:
            Number of trades processed
        """
        processed_count = 0
        
        for trade in trades:
            try:
                # Check if we've already processed this trade
                if self._is_trade_already_processed(agent_id, trade, target_date):
                    logger.debug(f"Trade already processed: {agent_id} - {trade.ticker}")
                    continue
                
                # Validate ticker with Alpaca
                if not self.alpaca_client.validate_ticker(trade.ticker):
                    logger.warning(f"Invalid ticker {trade.ticker} for agent {agent_id}")
                    continue
                
                # Calculate trade size
                trade_amount = self._calculate_trade_amount(trade)
                if trade_amount < self.settings.trading.minimum_amount:
                    logger.info(f"Trade amount ${trade_amount} below minimum for {trade.ticker}")
                    continue
                
                # Place order through Alpaca
                order_info = self.alpaca_client.place_market_order(
                    ticker=trade.ticker,
                    side='buy',  # MVP only processes purchases
                    notional=trade_amount,
                    time_in_force='gtc'
                )
                
                if order_info:
                    # Store trade in database
                    self._store_trade_record(agent_id, trade, order_info, target_date)
                    processed_count += 1
                    logger.info(f"Successfully processed trade: {agent_id} - {trade.ticker}")
                else:
                    logger.error(f"Failed to place order for {agent_id} - {trade.ticker}")
            
            except Exception as e:
                logger.error(f"Error processing individual trade for {agent_id}: {e}")
                continue
        
        return processed_count
    
    def _calculate_trade_amount(self, trade: CongressionalTrade) -> float:
        """
        Calculate the amount to trade based on the congressional trade.
        
        Args:
            trade: Congressional trade information
            
        Returns:
            Amount in dollars to trade
        """
        # For MVP, use minimum viable amount or fixed percentage of trade
        min_amount = self.settings.trading.minimum_amount
        
        # Could implement more sophisticated sizing later
        # For now, just use the minimum amount
        return max(min_amount, 100.0)
    
    def _is_trade_already_processed(self, agent_id: str, trade: CongressionalTrade, target_date: date) -> bool:
        """
        Check if a trade has already been processed.
        
        Args:
            agent_id: Agent identifier
            trade: Congressional trade
            target_date: Processing date
            
        Returns:
            True if trade already processed
        """
        try:
            # Check database for existing trade record
            query = """
            SELECT COUNT(*) FROM trades 
            WHERE agent_id = ? AND ticker = ? AND source_trade_date = ? AND trade_date = ?
            """
            params = (agent_id, trade.ticker, trade.transaction_date, target_date)
            
            result = self.db.execute_query(query, params)
            return result[0][0] > 0 if result else False
        
        except Exception as e:
            logger.error(f"Error checking if trade already processed: {e}")
            return False
    
    def _store_trade_record(self, agent_id: str, congressional_trade: CongressionalTrade, 
                           order_info: Any, target_date: date) -> None:
        """
        Store trade record in database.
        
        Args:
            agent_id: Agent identifier
            congressional_trade: Original congressional trade
            order_info: Alpaca order information
            target_date: Processing date
        """
        try:
            trade_data = {
                'agent_id': agent_id,
                'ticker': congressional_trade.ticker,
                'trade_date': target_date,
                'execution_date': datetime.now(),
                'order_type': 'market',
                'quantity': order_info.quantity,
                'price': order_info.filled_avg_price,
                'order_status': order_info.status,
                'alpaca_order_id': order_info.order_id,
                'source_politician': congressional_trade.politician,
                'source_trade_date': congressional_trade.transaction_date
            }
            
            self.db.insert_trade(trade_data)
            logger.debug(f"Stored trade record: {agent_id} - {congressional_trade.ticker}")
        
        except Exception as e:
            logger.error(f"Error storing trade record: {e}")
            raise
    
    def _synchronize_portfolios(self) -> None:
        """Synchronize portfolios between Alpaca and database."""
        try:
            # Get all positions from Alpaca
            alpaca_positions = self.alpaca_client.get_all_positions()
            
            # Get enabled agents
            enabled_agents = self.settings.get_enabled_agents()
            
            # For each agent, reconcile positions
            for agent_config in enabled_agents:
                agent_id = agent_config['id']
                self._reconcile_agent_positions(agent_id, alpaca_positions)
        
        except Exception as e:
            logger.error(f"Error synchronizing portfolios: {e}")
            raise
    
    def _reconcile_agent_positions(self, agent_id: str, alpaca_positions: List[PositionInfo]) -> None:
        """
        Reconcile positions for a specific agent.
        
        Args:
            agent_id: Agent identifier
            alpaca_positions: List of Alpaca positions
        """
        try:
            # Get agent's trades from database to determine allocation
            agent_trades = self._get_agent_trades(agent_id)
            
            # Calculate agent's share of each position
            agent_positions = self._allocate_positions_to_agent(agent_id, agent_trades, alpaca_positions)
            
            # Update database with current positions
            self._update_agent_positions(agent_id, agent_positions)
        
        except Exception as e:
            logger.error(f"Error reconciling positions for agent {agent_id}: {e}")
    
    def _get_agent_trades(self, agent_id: str) -> List[Dict[str, Any]]:
        """
        Get all trades for an agent from database.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            List of trade records
        """
        query = """
        SELECT ticker, SUM(quantity) as total_quantity, AVG(price) as avg_price
        FROM trades 
        WHERE agent_id = ? AND order_status IN ('filled', 'partially_filled')
        GROUP BY ticker
        """
        
        result = self.db.execute_query(query, (agent_id,))
        
        trades = []
        for row in result:
            trades.append({
                'ticker': row[0],
                'total_quantity': row[1],
                'avg_price': row[2]
            })
        
        return trades
    
    def _allocate_positions_to_agent(self, agent_id: str, agent_trades: List[Dict[str, Any]], 
                                   alpaca_positions: List[PositionInfo]) -> List[Dict[str, Any]]:
        """
        Allocate Alpaca positions to specific agent based on trade history.
        
        Args:
            agent_id: Agent identifier
            agent_trades: Agent's trade history
            alpaca_positions: Current Alpaca positions
            
        Returns:
            List of agent positions
        """
        agent_positions = []
        
        for trade in agent_trades:
            ticker = trade['ticker']
            agent_quantity = trade['total_quantity']
            
            # Find corresponding Alpaca position
            alpaca_position = next((pos for pos in alpaca_positions if pos.ticker == ticker), None)
            
            if alpaca_position and agent_quantity > 0:
                # For MVP, assume agent owns all shares of tickers they traded
                # In production, would need more sophisticated allocation
                agent_positions.append({
                    'ticker': ticker,
                    'quantity': agent_quantity,
                    'avg_cost': trade['avg_price'],
                    'current_price': alpaca_position.current_price,
                    'market_value': agent_quantity * alpaca_position.current_price,
                    'unrealized_pnl': (alpaca_position.current_price - trade['avg_price']) * agent_quantity,
                    'last_updated': datetime.now()
                })
        
        return agent_positions
    
    def _update_agent_positions(self, agent_id: str, positions: List[Dict[str, Any]]) -> None:
        """
        Update agent positions in database.
        
        Args:
            agent_id: Agent identifier
            positions: List of position data
        """
        try:
            # Clear existing positions for agent
            self.db.execute_query("DELETE FROM agent_positions WHERE agent_id = ?", (agent_id,))
            
            # Insert new positions
            for position in positions:
                position_data = {
                    'agent_id': agent_id,
                    **position
                }
                self.db.insert_position(position_data)
            
            logger.info(f"Updated {len(positions)} positions for agent {agent_id}")
        
        except Exception as e:
            logger.error(f"Error updating positions for agent {agent_id}: {e}")
            raise
    
    def _update_performance_metrics(self, target_date: date) -> None:
        """
        Update daily performance metrics for all agents.
        
        Args:
            target_date: Date to calculate performance for
        """
        try:
            enabled_agents = self.settings.get_enabled_agents()
            
            for agent_config in enabled_agents:
                agent_id = agent_config['id']
                
                # Get current portfolio value
                current_value = self._calculate_agent_portfolio_value(agent_id)
                
                # Get previous day's value for return calculation
                previous_value = self._get_previous_portfolio_value(agent_id, target_date)
                
                # Calculate returns
                daily_return_pct = 0.0
                if previous_value and previous_value > 0:
                    daily_return_pct = ((current_value - previous_value) / previous_value) * 100
                
                # Calculate total return (since inception)
                inception_value = self._get_inception_portfolio_value(agent_id)
                total_return_pct = 0.0
                if inception_value and inception_value > 0:
                    total_return_pct = ((current_value - inception_value) / inception_value) * 100
                
                # Store performance snapshot
                performance_data = {
                    'agent_id': agent_id,
                    'date': target_date,
                    'total_value': current_value,
                    'daily_return_pct': daily_return_pct,
                    'total_return_pct': total_return_pct
                }
                
                self.db.insert_daily_performance(performance_data)
                
                logger.info(f"Updated performance metrics for agent {agent_id}: ${current_value:.2f} ({daily_return_pct:+.2f}%)")
        
        except Exception as e:
            logger.error(f"Error updating performance metrics: {e}")
            raise
    
    def _calculate_agent_portfolio_value(self, agent_id: str) -> float:
        """
        Calculate current portfolio value for an agent.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Current portfolio value
        """
        query = "SELECT SUM(market_value) FROM agent_positions WHERE agent_id = ?"
        result = self.db.execute_query(query, (agent_id,))
        return float(result[0][0] or 0.0) if result else 0.0
    
    def _get_previous_portfolio_value(self, agent_id: str, current_date: date) -> Optional[float]:
        """
        Get previous trading day's portfolio value for an agent.
        
        Args:
            agent_id: Agent identifier
            current_date: Current date
            
        Returns:
            Previous portfolio value or None
        """
        # Get last trading day
        previous_date = current_date - timedelta(days=1)
        while previous_date.weekday() >= 5:  # Skip weekends
            previous_date -= timedelta(days=1)
        
        query = "SELECT total_value FROM daily_performance WHERE agent_id = ? AND date = ?"
        result = self.db.execute_query(query, (agent_id, previous_date))
        
        return float(result[0][0]) if result else None
    
    def _get_inception_portfolio_value(self, agent_id: str) -> Optional[float]:
        """
        Get inception portfolio value (total invested) for an agent.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Inception portfolio value or None
        """
        query = "SELECT SUM(quantity * price) FROM trades WHERE agent_id = ? AND order_status IN ('filled', 'partially_filled')"
        result = self.db.execute_query(query, (agent_id,))
        
        return float(result[0][0]) if result and result[0][0] else None
    
    def _validate_data_consistency(self) -> Dict[str, Any]:
        """
        Validate data consistency across APIs and database.
        
        Returns:
            Dictionary with validation results
        """
        validation_results = {
            'errors': [],
            'warnings': [],
            'checks_performed': 0,
            'checks_passed': 0
        }
        
        try:
            # Check 1: Verify Alpaca connection
            validation_results['checks_performed'] += 1
            if self.alpaca_client.test_connection():
                validation_results['checks_passed'] += 1
            else:
                validation_results['errors'].append("Alpaca API connection failed")
            
            # Check 2: Verify Quiver connection
            validation_results['checks_performed'] += 1
            if self.quiver_client.test_connection():
                validation_results['checks_passed'] += 1
            else:
                validation_results['warnings'].append("Quiver API connection issues")
            
            # Check 3: Database integrity
            validation_results['checks_performed'] += 1
            db_check = self._validate_database_integrity()
            if db_check['success']:
                validation_results['checks_passed'] += 1
            else:
                validation_results['errors'].extend(db_check['errors'])
            
            # Check 4: Portfolio reconciliation
            validation_results['checks_performed'] += 1
            portfolio_check = self._validate_portfolio_consistency()
            if portfolio_check['success']:
                validation_results['checks_passed'] += 1
            else:
                validation_results['warnings'].extend(portfolio_check['warnings'])
            
        except Exception as e:
            validation_results['errors'].append(f"Validation process failed: {e}")
        
        return validation_results
    
    def _validate_database_integrity(self) -> Dict[str, Any]:
        """Validate database integrity."""
        try:
            # Check for orphaned records
            orphaned_positions = self.db.execute_query("""
                SELECT agent_id, COUNT(*) 
                FROM agent_positions 
                WHERE agent_id NOT IN (SELECT DISTINCT agent_id FROM trades)
                GROUP BY agent_id
            """)
            
            if orphaned_positions:
                return {
                    'success': False,
                    'errors': [f"Found orphaned positions for agents: {[row[0] for row in orphaned_positions]}"]
                }
            
            return {'success': True, 'errors': []}
        
        except Exception as e:
            return {'success': False, 'errors': [f"Database integrity check failed: {e}"]}
    
    def _validate_portfolio_consistency(self) -> Dict[str, Any]:
        """Validate portfolio consistency between Alpaca and database."""
        try:
            warnings = []
            
            # Compare total positions
            alpaca_positions = self.alpaca_client.get_all_positions()
            db_total_positions = len(self.db.execute_query("SELECT DISTINCT ticker FROM agent_positions"))
            
            if len(alpaca_positions) != db_total_positions:
                warnings.append(f"Position count mismatch: Alpaca={len(alpaca_positions)}, DB={db_total_positions}")
            
            return {'success': True, 'warnings': warnings}
        
        except Exception as e:
            return {'success': False, 'warnings': [f"Portfolio consistency check failed: {e}"]}
    
    def _create_data_backup(self) -> None:
        """Create data backup before processing."""
        try:
            if hasattr(self.db, 'create_backup'):
                self.db.create_backup()
                logger.info("Data backup created successfully")
        except Exception as e:
            logger.warning(f"Failed to create data backup: {e}")
    
    def _update_processing_stats(self, success: bool, execution_time: float, trades_processed: int) -> None:
        """Update processing statistics."""
        self.processing_stats['total_runs'] += 1
        
        if success:
            self.processing_stats['successful_runs'] += 1
        else:
            self.processing_stats['failed_runs'] += 1
        
        self.processing_stats['total_trades_processed'] += trades_processed
        
        # Update average processing time
        current_avg = self.processing_stats['avg_processing_time']
        total_runs = self.processing_stats['total_runs']
        self.processing_stats['avg_processing_time'] = (current_avg * (total_runs - 1) + execution_time) / total_runs
        
        self.last_processing_time = datetime.now()
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        return {
            **self.processing_stats,
            'last_processing_time': self.last_processing_time.isoformat() if self.last_processing_time else None,
            'success_rate': self.processing_stats['successful_runs'] / max(self.processing_stats['total_runs'], 1) * 100
        }
    
    def get_portfolio_snapshots(self, agent_ids: Optional[List[str]] = None) -> List[PortfolioSnapshot]:
        """
        Get current portfolio snapshots for agents.
        
        Args:
            agent_ids: List of agent IDs to get snapshots for (None for all)
            
        Returns:
            List of portfolio snapshots
        """
        if agent_ids is None:
            agent_ids = [agent['id'] for agent in self.settings.get_enabled_agents()]
        
        snapshots = []
        
        for agent_id in agent_ids:
            try:
                # Get positions
                positions_query = "SELECT * FROM agent_positions WHERE agent_id = ?"
                position_rows = self.db.execute_query(positions_query, (agent_id,))
                
                positions = []
                total_value = 0.0
                
                for row in position_rows:
                    position_data = {
                        'ticker': row[2],  # Assuming column order from schema
                        'quantity': row[3],
                        'avg_cost': row[4],
                        'current_price': row[5],
                        'market_value': row[6],
                        'unrealized_pnl': row[7]
                    }
                    positions.append(position_data)
                    total_value += position_data['market_value']
                
                # Get latest performance metrics
                perf_query = """
                    SELECT daily_return_pct, total_return_pct 
                    FROM daily_performance 
                    WHERE agent_id = ? 
                    ORDER BY date DESC 
                    LIMIT 1
                """
                perf_result = self.db.execute_query(perf_query, (agent_id,))
                
                performance_metrics = {}
                if perf_result:
                    performance_metrics = {
                        'daily_return_pct': perf_result[0][0],
                        'total_return_pct': perf_result[0][1]
                    }
                
                snapshot = PortfolioSnapshot(
                    agent_id=agent_id,
                    timestamp=datetime.now(),
                    total_value=total_value,
                    position_count=len(positions),
                    positions=positions,
                    performance_metrics=performance_metrics
                )
                
                snapshots.append(snapshot)
            
            except Exception as e:
                logger.error(f"Error getting portfolio snapshot for agent {agent_id}: {e}")
        
        return snapshots
    
    def test_all_connections(self) -> Dict[str, bool]:
        """
        Test connections to all external APIs.
        
        Returns:
            Dictionary with connection test results
        """
        results = {}
        
        try:
            results['quiver'] = self.quiver_client.test_connection()
        except Exception as e:
            logger.error(f"Quiver connection test failed: {e}")
            results['quiver'] = False
        
        try:
            results['alpaca'] = self.alpaca_client.test_connection()
        except Exception as e:
            logger.error(f"Alpaca connection test failed: {e}")
            results['alpaca'] = False
        
        try:
            # Test market data service with a simple ticker
            price = self.market_data_service.get_current_price('AAPL')
            results['yfinance'] = price is not None
        except Exception as e:
            logger.error(f"yfinance connection test failed: {e}")
            results['yfinance'] = False
        
        try:
            # Test database connection
            self.db.execute_query("SELECT 1")
            results['database'] = True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            results['database'] = False
        
        return results
