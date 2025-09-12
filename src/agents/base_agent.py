"""
Base Agent Framework for Trading Automation System.
Provides abstract interface and common functionality for all trading agents.
"""
import time
from abc import ABC, abstractmethod
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from config.settings import settings
from src.data.database import DatabaseManager
from src.data.alpaca_client import AlpacaClient
from src.data.quiver_client import QuiverClient, CongressionalTrade
from src.data.market_data_service import MarketDataService
from src.utils.logging import get_logger
from src.utils.exceptions import TradingError, APIError, ValidationError
from src.utils.monitoring import metrics_collector
from src.utils.retry import retry_on_exception, TRADING_RETRY_CONFIG

logger = get_logger(__name__)

class AgentState(Enum):
    """Agent execution states."""
    INITIALIZED = "initialized"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"
    DISABLED = "disabled"

@dataclass
class TradeDecision:
    """Represents a trade decision made by an agent."""
    ticker: str
    side: str  # 'buy' or 'sell'
    amount: float  # Dollar amount
    reason: str
    source_trade: CongressionalTrade
    timestamp: datetime
    confidence: float = 1.0

@dataclass
class AgentPerformance:
    """Agent performance metrics."""
    agent_id: str
    total_value: float
    daily_return_pct: float
    total_return_pct: float
    position_count: int
    trades_today: int
    last_updated: datetime

@dataclass
class ExecutionResult:
    """Result of agent execution."""
    success: bool
    trades_processed: int
    orders_placed: int
    errors: List[str]
    execution_time: float
    timestamp: datetime

class BaseAgent(ABC):
    """
    Abstract base class for all trading agents.
    
    Provides common functionality:
    - Copy trading strategy implementation
    - Trade size calculation logic
    - Position management and portfolio tracking
    - Trade decision logging and audit trail
    - Performance metrics calculation
    - Database integration
    - Error handling with retry logic
    - Agent state management and persistence
    - Configuration validation
    """
    
    def __init__(self, agent_id: str, config: dict):
        """
        Initialize base agent.
        
        Args:
            agent_id: Unique identifier for the agent
            config: Agent configuration dictionary
        """
        self.agent_id = agent_id
        self.config = config
        self.state = AgentState.INITIALIZED
        
        # Validate configuration
        self._validate_config()
        
        # Get shared clients to prevent duplication
        from src.services.shared_services import shared_services
        self.db = shared_services.db
        self.alpaca_client = shared_services.alpaca_client
        self.quiver_client = shared_services.quiver_client
        self.market_data_service = shared_services.market_data_service
        
        # Agent parameters
        self.politicians = config.get('politicians', [])
        self.minimum_trade_value = config.get('parameters', {}).get('minimum_trade_value', 50000)
        self.position_size_type = config.get('parameters', {}).get('position_size_type', 'fixed')
        self.position_size_value = config.get('parameters', {}).get('position_size_value', 100)
        self.match_threshold = config.get('parameters', {}).get('match_threshold', 0.85)
        
        # State tracking
        self.last_execution_time = None
        self.execution_count = 0
        self.total_trades_processed = 0
        self.total_orders_placed = 0
        
        logger.info(f"Initialized agent {agent_id} tracking {len(self.politicians)} politicians")
    
    def _validate_config(self) -> None:
        """Validate agent configuration."""
        required_fields = ['id', 'name', 'type', 'politicians']
        
        for field in required_fields:
            if field not in self.config:
                raise ValidationError(f"Missing required configuration field: {field}")
        
        if not self.config['politicians']:
            raise ValidationError("Agent must track at least one politician")
        
        parameters = self.config.get('parameters', {})
        
        # Validate numeric parameters
        numeric_params = {
            'minimum_trade_value': (1000, 1000000),
            'position_size_value': (1, 10000),
            'match_threshold': (0.1, 1.0)
        }
        
        for param, (min_val, max_val) in numeric_params.items():
            value = parameters.get(param)
            if value is not None and not (min_val <= value <= max_val):
                raise ValidationError(f"Parameter {param} must be between {min_val} and {max_val}")
        
        # Validate position size type
        valid_size_types = ['fixed', 'percentage', 'dynamic']
        size_type = parameters.get('position_size_type', 'fixed')
        if size_type not in valid_size_types:
            raise ValidationError(f"Invalid position_size_type: {size_type}. Must be one of {valid_size_types}")
    
    def process_trades(self, congressional_data: List[CongressionalTrade]) -> List[TradeDecision]:
        """
        Process congressional trades and generate trade decisions.
        
        Args:
            congressional_data: List of congressional trades to process
            
        Returns:
            List of trade decisions to execute
        """
        try:
            self.state = AgentState.PROCESSING
            logger.info(f"Agent {self.agent_id} processing {len(congressional_data)} congressional trades")
            
            start_time = time.time()
            trade_decisions = []
            
            for trade in congressional_data:
                try:
                    # Check if this trade matches our politicians
                    if not self._matches_tracked_politicians(trade):
                        continue
                    
                    # Apply copy trading strategy
                    decision = self._apply_copy_trading_strategy(trade)
                    if decision:
                        trade_decisions.append(decision)
                        logger.info(f"Generated trade decision: {decision.ticker} {decision.side} ${decision.amount:.2f}")
                
                except Exception as e:
                    logger.error(f"Error processing individual trade: {e}")
                    continue
            
            execution_time = time.time() - start_time
            metrics_collector.record_execution_time(f"agent_{self.agent_id}_processing", execution_time)
            
            logger.info(f"Agent {self.agent_id} generated {len(trade_decisions)} trade decisions in {execution_time:.2f}s")
            return trade_decisions
        
        except Exception as e:
            self.state = AgentState.ERROR
            logger.error(f"Agent {self.agent_id} processing failed: {e}")
            raise TradingError(f"Trade processing failed: {e}", agent_id=self.agent_id)
    
    @abstractmethod
    def _matches_tracked_politicians(self, trade: CongressionalTrade) -> bool:
        """
        Check if a trade matches the politicians tracked by this agent.
        
        Args:
            trade: Congressional trade to check
            
        Returns:
            True if trade matches tracked politicians
        """
        pass
    
    def _apply_copy_trading_strategy(self, trade: CongressionalTrade) -> Optional[TradeDecision]:
        """
        Apply copy trading strategy to congressional trade.
        
        Args:
            trade: Congressional trade
            
        Returns:
            Trade decision or None if no action needed
        """
        # MVP: Only process purchases > minimum value
        if trade.trade_type.lower() != 'purchase':
            logger.debug(f"Ignoring non-purchase trade: {trade.trade_type}")
            return None
        
        if trade.amount_max < self.minimum_trade_value:
            logger.debug(f"Trade amount ${trade.amount_max} below minimum ${self.minimum_trade_value}")
            return None
        
        # Calculate trade size
        trade_amount = self._calculate_trade_size(trade)
        
        if trade_amount < settings.trading.minimum_amount:
            logger.debug(f"Calculated trade amount ${trade_amount} below system minimum")
            return None
        
        # Create trade decision
        decision = TradeDecision(
            ticker=trade.ticker,
            side='buy',  # MVP only does purchases
            amount=trade_amount,
            reason=f"Copy trade from {trade.politician} - ${trade.amount_max:,.0f} purchase",
            source_trade=trade,
            timestamp=datetime.now(),
            confidence=1.0  # MVP uses fixed confidence
        )
        
        return decision
    
    def _calculate_trade_size(self, trade: CongressionalTrade) -> float:
        """
        Calculate trade size based on agent configuration.
        
        Args:
            trade: Congressional trade
            
        Returns:
            Dollar amount to trade
        """
        if self.position_size_type == 'fixed':
            return max(self.position_size_value, 100.0)  # Minimum $100
        
        elif self.position_size_type == 'percentage':
            # Use percentage of congressional trade amount
            return max(trade.amount_max * (self.position_size_value / 100), 100.0)
        
        elif self.position_size_type == 'dynamic':
            # Dynamic sizing based on portfolio size (future enhancement)
            current_portfolio_value = self._get_current_portfolio_value()
            if current_portfolio_value > 0:
                target_percentage = 0.05  # 5% of portfolio
                return max(current_portfolio_value * target_percentage, 100.0)
            else:
                return 100.0
        
        else:
            logger.warning(f"Unknown position size type: {self.position_size_type}")
            return 100.0
    
    @retry_on_exception(TRADING_RETRY_CONFIG)
    def execute_trade(self, trade_decision: TradeDecision) -> bool:
        """
        Execute a trade decision through Alpaca API.
        
        Args:
            trade_decision: Trade decision to execute
            
        Returns:
            True if trade executed successfully
        """
        try:
            logger.info(f"Executing trade: {trade_decision.ticker} {trade_decision.side} ${trade_decision.amount:.2f}")
            
            # Validate ticker with Alpaca
            if not self.alpaca_client.validate_ticker(trade_decision.ticker):
                logger.error(f"Invalid ticker: {trade_decision.ticker}")
                return False
            
            # For short sells, convert to whole shares (fractional shorts not allowed)
            if trade_decision.side == 'sell' and 'short' in trade_decision.reason.lower():
                # Get current price and convert to shares
                current_price = self.market_data_service.get_current_price(trade_decision.ticker)
                if not current_price:
                    logger.error(f"Could not get current price for {trade_decision.ticker}")
                    return False
                
                # Calculate whole shares (round down to avoid insufficient funds)
                shares = int(trade_decision.amount / current_price)
                if shares <= 0:
                    logger.warning(f"Position size too small for whole shares: ${trade_decision.amount:.2f} / ${current_price:.2f} = {shares}")
                    return False
                
                logger.info(f"Converting short order to {shares} shares (${shares * current_price:.2f})")
                order_info = self.alpaca_client.place_market_order(
                    ticker=trade_decision.ticker,
                    side=trade_decision.side,
                    quantity=shares,
                    time_in_force='day'  # Short orders use DAY
                )
            else:
                # Regular buy orders can use fractional amounts
                time_in_force = 'day' if trade_decision.amount < 1000 else 'gtc'
                order_info = self.alpaca_client.place_market_order(
                    ticker=trade_decision.ticker,
                    side=trade_decision.side,
                    notional=trade_decision.amount,
                    time_in_force=time_in_force
                )
            
            
            if order_info:
                # Log trade execution
                self._log_trade_execution(trade_decision, order_info)
                self.total_orders_placed += 1
                
                logger.info(f"Successfully executed trade: {trade_decision.ticker} - Order ID: {order_info.order_id}")
                return True
            else:
                logger.error(f"Failed to place order for {trade_decision.ticker}")
                return False
        
        except Exception as e:
            logger.error(f"Trade execution failed for {trade_decision.ticker}: {e}")
            raise TradingError(f"Trade execution failed: {e}", agent_id=self.agent_id, ticker=trade_decision.ticker)
    
    def _log_trade_execution(self, trade_decision: TradeDecision, order_info: Any) -> None:
        """
        Log trade execution to database.
        
        Args:
            trade_decision: Original trade decision
            order_info: Alpaca order information
        """
        try:
            trade_data = {
                'agent_id': self.agent_id,
                'ticker': trade_decision.ticker,
                'trade_date': date.today(),
                'execution_date': datetime.now(),
                'order_type': 'market',
                'quantity': getattr(order_info, 'quantity', 0),
                'price': getattr(order_info, 'filled_avg_price', None),
                'order_status': getattr(order_info, 'status', 'unknown'),
                'alpaca_order_id': getattr(order_info, 'order_id', None),
                'source_politician': trade_decision.source_trade.politician,
                'source_trade_date': trade_decision.source_trade.transaction_date
            }
            
            self.db.insert_trade(trade_data)
            logger.debug(f"Logged trade execution: {trade_decision.ticker}")
        
        except Exception as e:
            logger.error(f"Failed to log trade execution: {e}")
    
    def update_positions(self) -> None:
        """Update agent positions from Alpaca data."""
        try:
            logger.info(f"Updating positions for agent {self.agent_id}")
            
            # Get agent's trades to determine ownership
            agent_trades = self._get_agent_trades()
            
            # Get current Alpaca positions
            alpaca_positions = self.alpaca_client.get_all_positions()
            
            # Calculate agent's positions
            agent_positions = self._calculate_agent_positions(agent_trades, alpaca_positions)
            
            # Update database
            self._update_agent_positions_in_db(agent_positions)
            
            logger.info(f"Updated {len(agent_positions)} positions for agent {self.agent_id}")
        
        except Exception as e:
            logger.error(f"Position update failed for agent {self.agent_id}: {e}")
            raise TradingError(f"Position update failed: {e}", agent_id=self.agent_id)
    
    def _get_agent_trades(self) -> List[Dict[str, Any]]:
        """Get agent's trade history from database."""
        query = """
        SELECT ticker, SUM(quantity) as total_quantity, AVG(price) as avg_price,
               SUM(quantity * price) as total_cost
        FROM trades 
        WHERE agent_id = ? AND order_status IN ('filled', 'partially_filled')
        GROUP BY ticker
        HAVING total_quantity != 0
        """
        
        result = self.db.execute_query(query, (self.agent_id,))
        
        trades = []
        for row in result:
            trades.append({
                'ticker': row[0],
                'total_quantity': float(row[1]),
                'avg_price': float(row[2]),
                'total_cost': float(row[3])
            })
        
        return trades
    
    def _calculate_agent_positions(self, agent_trades: List[Dict[str, Any]], alpaca_positions: List[Any]) -> List[Dict[str, Any]]:
        """Calculate current positions for this agent."""
        positions = []
        
        for trade in agent_trades:
            ticker = trade['ticker']
            agent_quantity = trade['total_quantity']
            agent_avg_cost = trade['avg_price']
            
            # Find current price from Alpaca positions
            alpaca_position = next((pos for pos in alpaca_positions if pos.ticker == ticker), None)
            
            if alpaca_position and agent_quantity != 0:
                current_price = float(alpaca_position.current_price)
                market_value = agent_quantity * current_price
                unrealized_pnl = (current_price - agent_avg_cost) * agent_quantity
                
                positions.append({
                    'ticker': ticker,
                    'quantity': agent_quantity,
                    'avg_cost': agent_avg_cost,
                    'current_price': current_price,
                    'market_value': market_value,
                    'unrealized_pnl': unrealized_pnl,
                    'last_updated': datetime.now()
                })
        
        return positions
    
    def _update_agent_positions_in_db(self, positions: List[Dict[str, Any]]) -> None:
        """Update agent positions in database."""
        try:
            # Clear existing positions
            self.db.execute_query("DELETE FROM agent_positions WHERE agent_id = ?", (self.agent_id,))
            
            # Insert new positions
            for position in positions:
                position_data = {
                    'agent_id': self.agent_id,
                    **position
                }
                self.db.insert_position(position_data)
        
        except Exception as e:
            logger.error(f"Failed to update positions in database: {e}")
            raise
    
    def calculate_performance(self) -> AgentPerformance:
        """
        Calculate current performance metrics for the agent.
        
        Returns:
            Agent performance metrics
        """
        try:
            # Get current portfolio value
            total_value = self._get_current_portfolio_value()
            
            # Get position count
            position_count = self._get_position_count()
            
            # Get daily return
            daily_return_pct = self._calculate_daily_return()
            
            # Get total return (since inception)
            total_return_pct = self._calculate_total_return()
            
            # Get trades today
            trades_today = self._get_trades_today()
            
            performance = AgentPerformance(
                agent_id=self.agent_id,
                total_value=total_value,
                daily_return_pct=daily_return_pct,
                total_return_pct=total_return_pct,
                position_count=position_count,
                trades_today=trades_today,
                last_updated=datetime.now()
            )
            
            logger.info(f"Performance for agent {self.agent_id}: ${total_value:.2f} ({total_return_pct:+.2f}%)")
            return performance
        
        except Exception as e:
            logger.error(f"Performance calculation failed for agent {self.agent_id}: {e}")
            raise TradingError(f"Performance calculation failed: {e}", agent_id=self.agent_id)
    
    def _get_current_portfolio_value(self) -> float:
        """Get current portfolio value using database positions with real-time prices."""
        try:
            # First update positions to ensure we have current prices
            self._update_positions_with_current_prices()
            
            # Then get total value from database
            query = "SELECT SUM(market_value) FROM agent_positions WHERE agent_id = ?"
            result = self.db.execute_query(query, (self.agent_id,))
            return float(result[0][0] or 0.0) if result else 0.0
            
        except Exception as e:
            logger.warning(f"Could not get current portfolio value: {e}")
            return 0.0
    
    def _update_positions_with_current_prices(self) -> None:
        """Update agent positions in database with current market prices."""
        try:
            # Get agent's current positions from database
            query = """
            SELECT ticker, quantity, avg_cost 
            FROM agent_positions 
            WHERE agent_id = ? AND quantity != 0
            """
            result = self.db.execute_query(query, (self.agent_id,))
            
            if not result:
                return
            
            # Get current Alpaca positions for price lookup
            alpaca_positions = self.alpaca_client.get_all_positions()
            alpaca_price_map = {pos.ticker: float(pos.current_price) for pos in alpaca_positions}
            
            # Update each position with current price
            for row in result:
                ticker, quantity, avg_cost = row[0], float(row[1]), float(row[2])
                
                if ticker in alpaca_price_map:
                    current_price = alpaca_price_map[ticker]
                    market_value = quantity * current_price
                    unrealized_pnl = (current_price - avg_cost) * quantity
                    
                    # Update position in database
                    update_query = """
                    UPDATE agent_positions 
                    SET current_price = ?, market_value = ?, unrealized_pnl = ?, last_updated = CURRENT_TIMESTAMP
                    WHERE agent_id = ? AND ticker = ?
                    """
                    self.db.execute_modify(update_query, (current_price, market_value, unrealized_pnl, self.agent_id, ticker))
            
        except Exception as e:
            logger.warning(f"Could not update positions with current prices: {e}")
    
    def _get_agent_tickers(self) -> List[str]:
        """Get list of tickers this agent has traded."""
        query = "SELECT DISTINCT ticker FROM trades WHERE agent_id = ?"
        result = self.db.execute_query(query, (self.agent_id,))
        return [row[0] for row in result] if result else []
    
    def _get_position_count(self) -> int:
        """Get number of positions from agent_positions table."""
        query = "SELECT COUNT(*) FROM agent_positions WHERE agent_id = ? AND quantity != 0"
        result = self.db.execute_query(query, (self.agent_id,))
        return int(result[0][0] or 0) if result else 0
    
    def _calculate_daily_return(self) -> float:
        """Calculate daily return percentage."""
        try:
            # Get yesterday's total value
            yesterday = date.today() - timedelta(days=1)
            query = "SELECT total_value FROM daily_performance WHERE agent_id = ? AND date = ?"
            result = self.db.execute_query(query, (self.agent_id, yesterday))
            
            if result and result[0][0]:
                yesterday_value = float(result[0][0])
                current_value = self._get_current_portfolio_value()
                
                if yesterday_value > 0:
                    return ((current_value - yesterday_value) / yesterday_value) * 100
            
            return 0.0
        
        except Exception as e:
            logger.warning(f"Could not calculate daily return: {e}")
            return 0.0
    
    def _calculate_total_return(self) -> float:
        """Calculate total return since inception."""
        try:
            # Get total invested amount
            query = "SELECT SUM(quantity * price) FROM trades WHERE agent_id = ? AND order_status IN ('filled', 'partially_filled')"
            result = self.db.execute_query(query, (self.agent_id,))
            
            if result and result[0][0]:
                total_invested = float(result[0][0])
                current_value = self._get_current_portfolio_value()
                
                if total_invested > 0:
                    return ((current_value - total_invested) / total_invested) * 100
            
            return 0.0
        
        except Exception as e:
            logger.warning(f"Could not calculate total return: {e}")
            return 0.0
    
    def _get_trades_today(self) -> int:
        """Get number of trades executed today."""
        query = "SELECT COUNT(*) FROM trades WHERE agent_id = ? AND DATE(execution_date) = DATE('now')"
        result = self.db.execute_query(query, (self.agent_id,))
        return int(result[0][0] or 0) if result else 0
    
    def execute_daily_workflow(self, congressional_trades: List[CongressionalTrade]) -> ExecutionResult:
        """
        Execute complete daily workflow for the agent.
        
        Args:
            congressional_trades: List of congressional trades to process
            
        Returns:
            Execution result with summary
        """
        try:
            start_time = time.time()
            logger.info(f"Starting daily workflow for agent {self.agent_id}")
            
            # Process trades to generate decisions
            trade_decisions = self.process_trades(congressional_trades)
            
            # Execute trade decisions
            successful_trades = 0
            errors = []
            
            for decision in trade_decisions:
                try:
                    if self.execute_trade(decision):
                        successful_trades += 1
                except Exception as e:
                    error_msg = f"Failed to execute trade {decision.ticker}: {e}"
                    errors.append(error_msg)
                    logger.error(error_msg)
            
            # Update positions
            try:
                self.update_positions()
            except Exception as e:
                error_msg = f"Failed to update positions: {e}"
                errors.append(error_msg)
                logger.error(error_msg)
            
            # Calculate and store performance
            try:
                performance = self.calculate_performance()
                self._store_daily_performance(performance)
            except Exception as e:
                error_msg = f"Failed to calculate performance: {e}"
                errors.append(error_msg)
                logger.error(error_msg)
            
            execution_time = time.time() - start_time
            
            # Update agent statistics
            self.execution_count += 1
            self.total_trades_processed += len(trade_decisions)
            self.last_execution_time = datetime.now()
            
            result = ExecutionResult(
                success=len(errors) == 0,
                trades_processed=len(trade_decisions),
                orders_placed=successful_trades,
                errors=errors,
                execution_time=execution_time,
                timestamp=datetime.now()
            )
            
            self.state = AgentState.COMPLETED if result.success else AgentState.ERROR
            
            logger.info(f"Daily workflow completed for agent {self.agent_id}: {successful_trades}/{len(trade_decisions)} trades executed")
            metrics_collector.record_execution_time(f"agent_{self.agent_id}_daily_workflow", execution_time)
            
            return result
        
        except Exception as e:
            self.state = AgentState.ERROR
            error_msg = f"Daily workflow failed for agent {self.agent_id}: {e}"
            logger.error(error_msg, exc_info=True)
            
            return ExecutionResult(
                success=False,
                trades_processed=0,
                orders_placed=0,
                errors=[error_msg],
                execution_time=time.time() - start_time,
                timestamp=datetime.now()
            )
    
    def _store_daily_performance(self, performance: AgentPerformance) -> None:
        """Store daily performance metrics in database."""
        try:
            performance_data = {
                'agent_id': self.agent_id,
                'date': date.today(),
                'total_value': performance.total_value,
                'daily_return_pct': performance.daily_return_pct,
                'total_return_pct': performance.total_return_pct
            }
            
            self.db.insert_daily_performance(performance_data)
        
        except Exception as e:
            logger.error(f"Failed to store daily performance: {e}")
    
    def get_agent_state(self) -> Dict[str, Any]:
        """
        Get current agent state and statistics.
        
        Returns:
            Dictionary with agent state information
        """
        return {
            'agent_id': self.agent_id,
            'name': self.config.get('name', ''),
            'type': self.config.get('type', ''),
            'state': self.state.value,
            'politicians_tracked': len(self.politicians),
            'last_execution_time': self.last_execution_time.isoformat() if self.last_execution_time else None,
            'execution_count': self.execution_count,
            'total_trades_processed': self.total_trades_processed,
            'total_orders_placed': self.total_orders_placed,
            'enabled': self.config.get('enabled', True)
        }
    
    def is_enabled(self) -> bool:
        """Check if agent is enabled."""
        return self.config.get('enabled', True) and self.state != AgentState.DISABLED
    
    def disable(self, reason: str = None) -> None:
        """
        Disable the agent.
        
        Args:
            reason: Reason for disabling
        """
        self.state = AgentState.DISABLED
        logger.info(f"Agent {self.agent_id} disabled" + (f": {reason}" if reason else ""))
    
    def enable(self) -> None:
        """Enable the agent."""
        self.state = AgentState.INITIALIZED
        logger.info(f"Agent {self.agent_id} enabled")