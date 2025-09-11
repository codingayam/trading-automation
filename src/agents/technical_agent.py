"""
Technical Agent Framework for Algorithm-Based Trading.
Base class for trading agents that use technical analysis and algorithms rather than copying congressional trades.
"""
import time
from abc import abstractmethod
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import pytz

from src.agents.base_agent import BaseAgent, AgentState, TradeDecision, ExecutionResult, AgentPerformance
from src.data.quiver_client import CongressionalTrade
from src.data.market_data_service import MarketDataService
from src.utils.logging import get_logger
from src.utils.exceptions import TradingError, APIError, ValidationError
from src.utils.monitoring import metrics_collector
from src.utils.retry import retry_on_exception, TRADING_RETRY_CONFIG

logger = get_logger(__name__)

class TechnicalSignal(Enum):
    """Technical analysis signals."""
    BUY = "buy"
    SELL = "sell"
    SHORT = "short"
    COVER = "cover"  # Cover short position
    HOLD = "hold"
    CLOSE = "close"  # Close any position

@dataclass
class TechnicalIndicator:
    """Technical indicator result."""
    name: str
    value: float
    signal: TechnicalSignal
    confidence: float
    timestamp: datetime
    metadata: Dict[str, Any] = None

@dataclass
class MarketPosition:
    """Current market position."""
    ticker: str
    side: str  # 'long' or 'short'
    quantity: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    entry_time: datetime
    market_value: float

@dataclass
class TechnicalTradeDecision(TradeDecision):
    """Extended trade decision for technical agents."""
    technical_indicators: List[TechnicalIndicator] = None
    position_type: str = 'entry'  # 'entry', 'exit', 'adjustment'
    risk_level: str = 'medium'  # 'low', 'medium', 'high'
    
    def __post_init__(self):
        """Post-initialization to set defaults."""
        if self.technical_indicators is None:
            self.technical_indicators = []

class TechnicalAgent(BaseAgent):
    """
    Abstract base class for technical analysis trading agents.
    
    Unlike BaseAgent which focuses on congressional trade copying, TechnicalAgent
    implements algorithm-based trading using technical indicators.
    
    Features:
    - Technical indicator calculation and analysis
    - Intraday trading with market hours awareness
    - Long and short position support
    - Risk management and position sizing
    - Market data integration
    - Performance tracking for technical strategies
    """
    
    def __init__(self, agent_id: str, config: dict):
        """
        Initialize technical agent.
        
        Args:
            agent_id: Unique identifier for the agent
            config: Agent configuration dictionary
        """
        # Initialize ALL technical agent parameters before calling super()
        self.target_ticker = config.get('target_ticker', 'SPY')
        self.position_size_percent = config.get('position_size_percent', 1.0)  # % of account equity
        self.max_position_size = config.get('max_position_size', 10000)  # Max dollar amount
        self.min_account_value = config.get('min_account_value', 1000)  # Minimum account value required
        
        # Risk management parameters
        self.max_daily_trades = config.get('max_daily_trades', 5)
        self.stop_loss_percent = config.get('stop_loss_percent', 0.05)  # 5% stop loss
        self.take_profit_percent = config.get('take_profit_percent', 0.10)  # 10% take profit
        
        # Market hours (Eastern Time)
        self.market_timezone = pytz.timezone('US/Eastern')
        self.market_open_time = config.get('market_open_time', '09:30')
        self.market_close_time = config.get('market_close_time', '16:00')
        self.position_close_time = config.get('position_close_time', '15:55')  # Close positions 5 min before market close
        
        # Initialize base agent but skip congressional trade validation
        super().__init__(agent_id, config)
        
        # State tracking for technical agents
        self.current_positions: Dict[str, MarketPosition] = {}
        self.daily_trade_count = 0
        self.last_trade_date = None
        
        logger.info(f"Initialized technical agent {agent_id} for ticker {self.target_ticker}")
    
    def _create_dummy_source_trade(self, ticker: str) -> CongressionalTrade:
        """Create a dummy congressional trade for technical analysis."""
        return CongressionalTrade(
            politician="Technical Analysis",
            ticker=ticker,
            transaction_date=date.today(),
            trade_type="technical_analysis",
            amount_range="$0",
            amount_min=0.0,
            amount_max=0.0,
            last_modified=date.today(),
            raw_data={"source": "technical_analysis"}
        )
    
    def _validate_config(self) -> None:
        """Validate technical agent configuration."""
        required_fields = ['id', 'name', 'type']
        
        for field in required_fields:
            if field not in self.config:
                raise ValidationError(f"Missing required configuration field: {field}")
        
        # Validate technical agent specific parameters
        if self.position_size_percent <= 0 or self.position_size_percent > 10:
            raise ValidationError("position_size_percent must be between 0 and 10")
        
        if self.min_account_value < 100:
            raise ValidationError("min_account_value must be at least $100")
        
        # Validate market hours format
        try:
            datetime.strptime(self.market_open_time, '%H:%M')
            datetime.strptime(self.market_close_time, '%H:%M')
            datetime.strptime(self.position_close_time, '%H:%M')
        except ValueError:
            raise ValidationError("Market times must be in HH:MM format")
    
    def is_market_open(self, check_time: Optional[datetime] = None) -> bool:
        """
        Check if the market is currently open.
        
        Args:
            check_time: Time to check (defaults to now)
            
        Returns:
            True if market is open
        """
        if check_time is None:
            check_time = datetime.now(self.market_timezone)
        elif check_time.tzinfo is None:
            check_time = self.market_timezone.localize(check_time)
        else:
            check_time = check_time.astimezone(self.market_timezone)
        
        # Check if it's a weekday
        if check_time.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False
        
        # Check market hours
        market_open = check_time.replace(
            hour=int(self.market_open_time.split(':')[0]),
            minute=int(self.market_open_time.split(':')[1]),
            second=0,
            microsecond=0
        )
        
        market_close = check_time.replace(
            hour=int(self.market_close_time.split(':')[0]),
            minute=int(self.market_close_time.split(':')[1]),
            second=0,
            microsecond=0
        )
        
        return market_open <= check_time <= market_close
    
    def should_close_positions(self, check_time: Optional[datetime] = None) -> bool:
        """
        Check if positions should be closed (near market close).
        
        Args:
            check_time: Time to check (defaults to now)
            
        Returns:
            True if positions should be closed
        """
        if check_time is None:
            check_time = datetime.now(self.market_timezone)
        elif check_time.tzinfo is None:
            check_time = self.market_timezone.localize(check_time)
        else:
            check_time = check_time.astimezone(self.market_timezone)
        
        # Check if it's a weekday
        if check_time.weekday() >= 5:
            return True  # Close positions on weekends
        
        position_close = check_time.replace(
            hour=int(self.position_close_time.split(':')[0]),
            minute=int(self.position_close_time.split(':')[1]),
            second=0,
            microsecond=0
        )
        
        return check_time >= position_close
    
    def get_account_equity(self) -> float:
        """
        Get current account equity.
        
        Returns:
            Account equity in dollars
        """
        try:
            account = self.alpaca_client.get_account_info()
            return float(account.equity) if account else 0.0
        except Exception as e:
            logger.error(f"Failed to get account equity: {e}")
            return 0.0
    
    def calculate_position_size(self, current_price: float) -> float:
        """
        Calculate position size based on account equity and configuration.
        
        Args:
            current_price: Current price of the ticker
            
        Returns:
            Dollar amount to trade
        """
        try:
            account_equity = self.get_account_equity()
            
            if account_equity < self.min_account_value:
                logger.warning(f"Account equity ${account_equity:.2f} below minimum ${self.min_account_value}")
                return 0.0
            
            # Calculate position size as percentage of equity
            position_size = account_equity * (self.position_size_percent / 100)
            
            # Apply maximum position size limit
            position_size = min(position_size, self.max_position_size)
            
            # Ensure minimum position size
            position_size = max(position_size, 100.0)
            
            # Round to 2 decimal places for Alpaca API requirements
            position_size = round(position_size, 2)
            
            logger.debug(f"Calculated position size: ${position_size:.2f} ({self.position_size_percent}% of ${account_equity:.2f})")
            return position_size
        
        except Exception as e:
            logger.error(f"Failed to calculate position size: {e}")
            return 100.0  # Default minimum
    
    def update_daily_trade_count(self) -> None:
        """Update daily trade count and reset if new day."""
        today = date.today()
        
        if self.last_trade_date != today:
            self.daily_trade_count = 0
            self.last_trade_date = today
    
    def can_trade_today(self) -> bool:
        """
        Check if agent can still trade today.
        
        Returns:
            True if within daily trade limit
        """
        self.update_daily_trade_count()
        return self.daily_trade_count < self.max_daily_trades
    
    @abstractmethod
    def calculate_technical_indicators(self, ticker: str) -> List[TechnicalIndicator]:
        """
        Calculate technical indicators for the given ticker.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            List of technical indicators with signals
        """
        pass
    
    @abstractmethod
    def generate_trading_signal(self, indicators: List[TechnicalIndicator]) -> TechnicalSignal:
        """
        Generate trading signal from technical indicators.
        
        Args:
            indicators: List of technical indicators
            
        Returns:
            Trading signal
        """
        pass
    
    def process_technical_strategy(self) -> List[TechnicalTradeDecision]:
        """
        Process technical strategy and generate trade decisions.
        
        Returns:
            List of trade decisions based on technical analysis
        """
        try:
            self.state = AgentState.PROCESSING
            logger.info(f"Technical agent {self.agent_id} processing strategy for {self.target_ticker}")
            
            # Check if we can trade today
            if not self.can_trade_today():
                logger.info(f"Daily trade limit reached: {self.daily_trade_count}/{self.max_daily_trades}")
                return []
            
            # Check account minimum
            account_equity = self.get_account_equity()
            if account_equity < self.min_account_value:
                logger.warning(f"Account equity ${account_equity:.2f} below minimum ${self.min_account_value}")
                return []
            
            trade_decisions = []
            
            # Calculate technical indicators
            indicators = self.calculate_technical_indicators(self.target_ticker)
            
            if not indicators:
                logger.warning(f"No technical indicators calculated for {self.target_ticker}")
                return []
            
            # Generate trading signal
            signal = self.generate_trading_signal(indicators)
            
            # Check if we should close positions first
            if self.should_close_positions():
                close_decisions = self._generate_position_close_decisions(indicators)
                trade_decisions.extend(close_decisions)
                return trade_decisions
            
            # Generate trade decision based on signal
            if signal != TechnicalSignal.HOLD:
                decision = self._create_trade_decision_from_signal(signal, indicators)
                if decision:
                    trade_decisions.append(decision)
            
            logger.info(f"Technical agent {self.agent_id} generated {len(trade_decisions)} trade decisions")
            return trade_decisions
        
        except Exception as e:
            self.state = AgentState.ERROR
            logger.error(f"Technical strategy processing failed: {e}")
            raise TradingError(f"Technical strategy failed: {e}", agent_id=self.agent_id)
    
    def _generate_position_close_decisions(self, indicators: List[TechnicalIndicator]) -> List[TechnicalTradeDecision]:
        """Generate decisions to close all positions."""
        decisions = []
        
        try:
            # Get current positions
            positions = self.alpaca_client.get_all_positions()
            
            for position in positions:
                if position.ticker == self.target_ticker and float(position.quantity) != 0:
                    quantity = float(position.quantity)
                    side = 'sell' if quantity > 0 else 'buy'  # Sell long, buy to cover short
                    amount = abs(quantity * float(position.current_price))
                    
                    decision = TechnicalTradeDecision(
                        ticker=self.target_ticker,
                        side=side,
                        amount=amount,
                        reason=f"Close position before market close - {side} {abs(quantity)} shares",
                        source_trade=self._create_dummy_source_trade(self.target_ticker),
                        timestamp=datetime.now(),
                        confidence=1.0,
                        technical_indicators=indicators,
                        position_type='exit',
                        risk_level='low'
                    )
                    decisions.append(decision)
                    
                    logger.info(f"Generated position close decision: {side} ${amount:.2f} of {self.target_ticker}")
        
        except Exception as e:
            logger.error(f"Failed to generate position close decisions: {e}")
        
        return decisions
    
    def _create_trade_decision_from_signal(self, signal: TechnicalSignal, indicators: List[TechnicalIndicator]) -> Optional[TechnicalTradeDecision]:
        """Create trade decision from technical signal."""
        try:
            # Get current price
            current_price = self.market_data_service.get_current_price(self.target_ticker)
            if not current_price:
                logger.error(f"Could not get current price for {self.target_ticker}")
                return None
            
            # Calculate position size
            position_size = self.calculate_position_size(current_price)
            if position_size <= 0:
                return None
            
            # Create decision based on signal
            if signal in [TechnicalSignal.BUY, TechnicalSignal.SHORT]:
                side = 'buy' if signal == TechnicalSignal.BUY else 'sell'  # sell for short
                reason = f"Technical {signal.value} signal - RSI analysis"
                
                decision = TechnicalTradeDecision(
                    ticker=self.target_ticker,
                    side=side,
                    amount=position_size,
                    reason=reason,
                    source_trade=self._create_dummy_source_trade(self.target_ticker),
                    timestamp=datetime.now(),
                    confidence=self._calculate_signal_confidence(indicators),
                    technical_indicators=indicators,
                    position_type='entry',
                    risk_level='medium'
                )
                
                return decision
        
        except Exception as e:
            logger.error(f"Failed to create trade decision from signal: {e}")
        
        return None
    
    def _calculate_signal_confidence(self, indicators: List[TechnicalIndicator]) -> float:
        """Calculate confidence score from indicators."""
        if not indicators:
            return 0.5
        
        # Average confidence from all indicators
        avg_confidence = sum(ind.confidence for ind in indicators) / len(indicators)
        return max(0.1, min(1.0, avg_confidence))
    
    # Override base agent methods for technical agents
    def process_trades(self, congressional_data: List[CongressionalTrade]) -> List[TradeDecision]:
        """
        Technical agents don't process congressional trades.
        Instead, call process_technical_strategy().
        """
        logger.info(f"Technical agent {self.agent_id} ignoring congressional trades, using technical strategy")
        technical_decisions = self.process_technical_strategy()
        
        # Convert technical decisions to base TradeDecision format
        trade_decisions = []
        for tech_decision in technical_decisions:
            trade_decisions.append(TradeDecision(
                ticker=tech_decision.ticker,
                side=tech_decision.side,
                amount=tech_decision.amount,
                reason=tech_decision.reason,
                source_trade=tech_decision.source_trade,
                timestamp=tech_decision.timestamp,
                confidence=tech_decision.confidence
            ))
        
        return trade_decisions
    
    def _matches_tracked_politicians(self, trade: CongressionalTrade) -> bool:
        """Technical agents don't track politicians."""
        return False
    
    def execute_intraday_workflow(self) -> ExecutionResult:
        """
        Execute intraday technical trading workflow.
        This is the main entry point for technical agents.
        
        Returns:
            Execution result
        """
        try:
            start_time = time.time()
            logger.info(f"Starting intraday workflow for technical agent {self.agent_id}")
            
            # Check if market is open
            if not self.is_market_open():
                logger.info("Market is closed, skipping intraday workflow")
                return ExecutionResult(
                    success=True,
                    trades_processed=0,
                    orders_placed=0,
                    errors=[],
                    execution_time=0.0,
                    timestamp=datetime.now()
                )
            
            # Process technical strategy (bypassing congressional trades)
            trade_decisions = self.process_technical_strategy()
            
            # Execute trade decisions
            successful_trades = 0
            errors = []
            
            for decision in trade_decisions:
                try:
                    # Convert back to base TradeDecision for execution
                    base_decision = TradeDecision(
                        ticker=decision.ticker,
                        side=decision.side,
                        amount=decision.amount,
                        reason=decision.reason,
                        source_trade=decision.source_trade,
                        timestamp=decision.timestamp,
                        confidence=decision.confidence
                    )
                    
                    if self.execute_trade(base_decision):
                        successful_trades += 1
                        self.daily_trade_count += 1
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
            
            execution_time = time.time() - start_time
            
            result = ExecutionResult(
                success=len(errors) == 0,
                trades_processed=len(trade_decisions),
                orders_placed=successful_trades,
                errors=errors,
                execution_time=execution_time,
                timestamp=datetime.now()
            )
            
            self.state = AgentState.COMPLETED if result.success else AgentState.ERROR
            
            logger.info(f"Intraday workflow completed: {successful_trades}/{len(trade_decisions)} trades executed")
            metrics_collector.record_execution_time(f"technical_agent_{self.agent_id}_intraday", execution_time)
            
            return result
        
        except Exception as e:
            self.state = AgentState.ERROR
            error_msg = f"Intraday workflow failed: {e}"
            logger.error(error_msg)
            
            return ExecutionResult(
                success=False,
                trades_processed=0,
                orders_placed=0,
                errors=[error_msg],
                execution_time=time.time() - start_time,
                timestamp=datetime.now()
            )