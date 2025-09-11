"""
Andy (Grok) Agent Implementation.
RSI-based intraday trading agent that trades SPY based on oversold/overbought conditions.
"""
from datetime import datetime, time
from typing import Dict, List, Any, Optional
import pytz

from src.agents.technical_agent import (
    TechnicalAgent, TechnicalSignal, TechnicalIndicator, 
    TechnicalTradeDecision, AgentState
)
from src.utils.technical_indicators import technical_indicators
from src.utils.logging import get_logger
from src.utils.exceptions import TradingError, ValidationError

logger = get_logger(__name__)

class AndyGrokAgent(TechnicalAgent):
    """
    Andy (Grok) Agent - RSI-based SPY trading strategy.
    
    Trading Strategy:
    1. At market open (9:30 AM ET):
       - Look at last 14 hours of SPY price closes
       - Calculate RSI (Relative Strength Index)
       - If RSI < 30 (oversold) → buy 1% of account equity
       - If RSI > 70 (overbought) → short 1% of account equity
       - Otherwise → do nothing, stay flat
    
    2. During the day:
       - Hold position (no intraday trades)
    
    3. Before market close (3:55 PM ET):
       - Close any open position (sell if long, buy back if short)
       - Always go flat before market closes (no overnight risk)
    
    Features:
    - Automatic position closure before market close
    - RSI-based entry signals with configurable thresholds
    - Risk management with position sizing limits
    - Market hours awareness
    - Comprehensive logging and monitoring
    """
    
    def __init__(self, agent_id: str, config: dict):
        """
        Initialize Andy Grok Agent.
        
        Args:
            agent_id: Unique agent identifier
            config: Agent configuration dictionary
        """
        # Set default configuration for Andy Grok strategy
        default_config = {
            'target_ticker': 'SPY',
            'position_size_percent': 1.0,  # 1% of account equity
            'max_position_size': 10000,    # Max $10k position
            'min_account_value': 1000,     # Require $1k minimum
            'max_daily_trades': 3,         # Limit to 3 trades per day
            'market_open_time': '09:30',
            'market_close_time': '16:00', 
            'position_close_time': '15:55'  # Close positions 5 min before market close
        }
        
        # Merge with provided config
        merged_config = {**default_config, **config}
        
        # RSI strategy parameters - initialize before super()
        self.rsi_period = merged_config.get('rsi_period', 14)
        self.rsi_oversold_threshold = merged_config.get('rsi_oversold_threshold', 30.0)
        self.rsi_overbought_threshold = merged_config.get('rsi_overbought_threshold', 70.0)
        self.rsi_lookback_hours = merged_config.get('rsi_lookback_hours', 14)
        
        super().__init__(agent_id, merged_config)
        
        # Trading state
        self.has_traded_today = False
        self.last_signal = TechnicalSignal.HOLD
        self.last_rsi_value = None
        
        logger.info(f"Initialized Andy Grok Agent {agent_id} - RSI strategy for {self.target_ticker}")
        logger.info(f"RSI thresholds: oversold < {self.rsi_oversold_threshold}, overbought > {self.rsi_overbought_threshold}")
    
    def _validate_config(self) -> None:
        """Validate Andy Grok agent configuration."""
        super()._validate_config()
        
        # Validate RSI parameters
        if self.rsi_period < 2 or self.rsi_period > 50:
            raise ValidationError("RSI period must be between 2 and 50")
        
        if not (0 < self.rsi_oversold_threshold < self.rsi_overbought_threshold < 100):
            raise ValidationError("RSI thresholds must satisfy: 0 < oversold < overbought < 100")
        
        if self.rsi_lookback_hours < self.rsi_period:
            raise ValidationError(f"RSI lookback hours ({self.rsi_lookback_hours}) must be >= RSI period ({self.rsi_period})")
    
    def calculate_technical_indicators(self, ticker: str) -> List[TechnicalIndicator]:
        """
        Calculate RSI indicator for the ticker.
        
        Args:
            ticker: Stock ticker symbol (should be SPY)
            
        Returns:
            List containing RSI technical indicator
        """
        try:
            logger.debug(f"Calculating RSI for {ticker} with {self.rsi_lookback_hours}h lookback, period={self.rsi_period}")
            
            # Calculate RSI using the technical indicators utility
            rsi_result = technical_indicators.calculate_rsi(
                ticker=ticker,
                period=self.rsi_period,
                hours=self.rsi_lookback_hours
            )
            
            if rsi_result is None:
                logger.error(f"Failed to calculate RSI for {ticker}")
                return []
            
            rsi_value, metadata = rsi_result
            self.last_rsi_value = rsi_value
            
            # Determine signal from RSI
            if rsi_value < self.rsi_oversold_threshold:
                signal = TechnicalSignal.BUY
                confidence = min(1.0, (self.rsi_oversold_threshold - rsi_value) / self.rsi_oversold_threshold * 2)
            elif rsi_value > self.rsi_overbought_threshold:
                signal = TechnicalSignal.SHORT
                confidence = min(1.0, (rsi_value - self.rsi_overbought_threshold) / (100 - self.rsi_overbought_threshold) * 2)
            else:
                signal = TechnicalSignal.HOLD
                confidence = 0.5
            
            # Create technical indicator
            rsi_indicator = TechnicalIndicator(
                name=f"RSI_{self.rsi_period}",
                value=rsi_value,
                signal=signal,
                confidence=confidence,
                timestamp=datetime.now(),
                metadata={
                    **metadata,
                    'oversold_threshold': self.rsi_oversold_threshold,
                    'overbought_threshold': self.rsi_overbought_threshold,
                    'lookback_hours': self.rsi_lookback_hours
                }
            )
            
            logger.info(f"RSI calculated: {rsi_value:.2f} → {signal.value} (confidence: {confidence:.2f})")
            return [rsi_indicator]
        
        except Exception as e:
            logger.error(f"Technical indicator calculation failed: {e}")
            return []
    
    def generate_trading_signal(self, indicators: List[TechnicalIndicator]) -> TechnicalSignal:
        """
        Generate trading signal from RSI indicator.
        
        Args:
            indicators: List of technical indicators (should contain RSI)
            
        Returns:
            Trading signal based on RSI analysis
        """
        try:
            if not indicators:
                logger.warning("No indicators provided for signal generation")
                return TechnicalSignal.HOLD
            
            # Get RSI indicator
            rsi_indicator = next((ind for ind in indicators if ind.name.startswith('RSI')), None)
            if not rsi_indicator:
                logger.error("RSI indicator not found")
                return TechnicalSignal.HOLD
            
            # Check if we should close positions first
            if self.should_close_positions():
                logger.info("Market close time - generating close signal")
                return TechnicalSignal.CLOSE
            
            # Check if we already traded today
            if self.has_traded_today and not self._should_allow_additional_trade(rsi_indicator):
                logger.info("Already traded today, holding position")
                return TechnicalSignal.HOLD
            
            # Generate signal based on RSI
            signal = rsi_indicator.signal
            rsi_value = rsi_indicator.value
            
            logger.info(f"Generated signal: {signal.value} from RSI {rsi_value:.2f}")
            self.last_signal = signal
            
            return signal
        
        except Exception as e:
            logger.error(f"Signal generation failed: {e}")
            return TechnicalSignal.HOLD
    
    def _should_allow_additional_trade(self, rsi_indicator: TechnicalIndicator) -> bool:
        """
        Check if we should allow additional trades today.
        Currently conservative - only one entry trade per day.
        
        Args:
            rsi_indicator: RSI indicator
            
        Returns:
            True if additional trade should be allowed
        """
        # For Andy Grok strategy, we typically only want one entry per day
        # Additional trades only for position management (closing)
        if rsi_indicator.signal == TechnicalSignal.CLOSE:
            return True
        
        # Don't allow multiple entry trades per day
        return False
    
    def is_market_entry_time(self) -> bool:
        """
        Check if it's the right time for market entry (near market open).
        
        Returns:
            True if within entry window
        """
        try:
            now = datetime.now(self.market_timezone)
            
            # Check if it's a trading day
            if now.weekday() >= 5:  # Weekend
                return False
            
            # Market entry window: 9:30 AM - 10:30 AM ET (1 hour after open)
            market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
            entry_window_end = now.replace(hour=10, minute=30, second=0, microsecond=0)
            
            return market_open <= now <= entry_window_end
        
        except Exception as e:
            logger.error(f"Failed to check market entry time: {e}")
            return False
    
    def execute_morning_analysis(self) -> List[TechnicalTradeDecision]:
        """
        Execute morning RSI analysis and generate entry signals.
        This should be called at market open (9:30 AM ET).
        
        Returns:
            List of trade decisions for morning entry
        """
        try:
            logger.info(f"Executing morning RSI analysis for {self.target_ticker}")
            
            # Reset daily state
            today = datetime.now().date()
            if self.last_trade_date != today:
                self.has_traded_today = False
                self.daily_trade_count = 0
                self.last_trade_date = today
            
            # Check if we should trade
            if not self.is_market_entry_time():
                logger.info("Not in market entry time window")
                return []
            
            if self.has_traded_today:
                logger.info("Already traded today")
                return []
            
            # Process technical strategy
            decisions = self.process_technical_strategy()
            
            if decisions:
                self.has_traded_today = True
                logger.info(f"Generated {len(decisions)} morning entry decisions")
            
            return decisions
        
        except Exception as e:
            logger.error(f"Morning analysis failed: {e}")
            return []
    
    def execute_closing_workflow(self) -> List[TechnicalTradeDecision]:
        """
        Execute position closing workflow before market close.
        This should be called at position close time (3:55 PM ET).
        
        Returns:
            List of trade decisions for position closing
        """
        try:
            logger.info(f"Executing closing workflow for {self.target_ticker}")
            
            # Calculate current indicators for logging
            indicators = self.calculate_technical_indicators(self.target_ticker)
            
            # Generate close decisions
            close_decisions = self._generate_position_close_decisions(indicators)
            
            if close_decisions:
                logger.info(f"Generated {len(close_decisions)} position close decisions")
            else:
                logger.info("No positions to close")
            
            return close_decisions
        
        except Exception as e:
            logger.error(f"Closing workflow failed: {e}")
            return []
    
    def get_strategy_status(self) -> Dict[str, Any]:
        """
        Get current strategy status and metrics.
        
        Returns:
            Dictionary with strategy status information
        """
        try:
            return {
                'agent_id': self.agent_id,
                'strategy': 'RSI-based SPY trading',
                'target_ticker': self.target_ticker,
                'has_traded_today': self.has_traded_today,
                'daily_trade_count': self.daily_trade_count,
                'last_signal': self.last_signal.value if self.last_signal else None,
                'last_rsi_value': self.last_rsi_value,
                'rsi_thresholds': {
                    'oversold': self.rsi_oversold_threshold,
                    'overbought': self.rsi_overbought_threshold
                },
                'market_status': {
                    'is_open': self.is_market_open(),
                    'should_close_positions': self.should_close_positions(),
                    'is_entry_time': self.is_market_entry_time()
                },
                'position_sizing': {
                    'percent_of_equity': self.position_size_percent,
                    'max_position_size': self.max_position_size
                },
                'account_equity': self.get_account_equity(),
                'state': self.state.value,
                'last_execution': self.last_execution_time.isoformat() if self.last_execution_time else None
            }
        
        except Exception as e:
            logger.error(f"Failed to get strategy status: {e}")
            return {'error': str(e)}
    
    def validate_strategy_health(self) -> Dict[str, Any]:
        """
        Validate the health of the RSI strategy.
        
        Returns:
            Health check results
        """
        try:
            health_issues = []
            warnings = []
            
            # Check account equity
            equity = self.get_account_equity()
            if equity < self.min_account_value:
                health_issues.append(f"Account equity ${equity:.2f} below minimum ${self.min_account_value}")
            
            # Check market data availability
            test_data = technical_indicators.get_hourly_prices(self.target_ticker, 2)
            if test_data is None or test_data.empty:
                health_issues.append(f"Cannot fetch market data for {self.target_ticker}")
            
            # Check RSI calculation
            try:
                rsi_result = technical_indicators.calculate_rsi(self.target_ticker, self.rsi_period, self.rsi_lookback_hours)
                if rsi_result is None:
                    health_issues.append("RSI calculation failed")
                else:
                    rsi_value, metadata = rsi_result
                    if metadata['data_points'] < self.rsi_period:
                        warnings.append(f"Limited data for RSI: {metadata['data_points']} < {self.rsi_period}")
            except Exception as e:
                health_issues.append(f"RSI calculation error: {e}")
            
            # Check daily trade limits
            if self.daily_trade_count >= self.max_daily_trades:
                warnings.append(f"Daily trade limit reached: {self.daily_trade_count}/{self.max_daily_trades}")
            
            health_status = "healthy" if not health_issues else "unhealthy"
            if warnings and health_status == "healthy":
                health_status = "degraded"
            
            return {
                'status': health_status,
                'issues': health_issues,
                'warnings': warnings,
                'checks_performed': {
                    'account_equity': equity,
                    'market_data_available': test_data is not None,
                    'rsi_calculation': rsi_result is not None,
                    'daily_trades': f"{self.daily_trade_count}/{self.max_daily_trades}"
                },
                'timestamp': datetime.now().isoformat()
            }
        
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

# Factory function for creating Andy Grok agents
def create_andy_grok_agent(agent_id: str = "andy_grok", custom_config: Dict[str, Any] = None) -> AndyGrokAgent:
    """
    Create an Andy Grok Agent with default configuration.
    
    Args:
        agent_id: Agent identifier
        custom_config: Custom configuration overrides
        
    Returns:
        Configured Andy Grok Agent
    """
    default_config = {
        'id': agent_id,
        'name': 'Andy (Grok) Agent',
        'type': 'technical',
        'enabled': True,
        'target_ticker': 'SPY',
        'position_size_percent': 1.0,
        'rsi_period': 14,
        'rsi_oversold_threshold': 30.0,
        'rsi_overbought_threshold': 70.0,
        'rsi_lookback_hours': 14
    }
    
    if custom_config:
        default_config.update(custom_config)
    
    return AndyGrokAgent(agent_id, default_config)