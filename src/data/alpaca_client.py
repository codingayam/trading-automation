"""
Alpaca Trading API client for trade execution and portfolio management.
Handles paper trading, order placement, position tracking, and market data.
"""
import time
from decimal import Decimal
from datetime import datetime, date
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum

from alpaca.trading import TradingClient, OrderRequest, MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce, OrderStatus, OrderType
from alpaca.trading.models import Position, Order, TradeAccount
from alpaca.data import StockHistoricalDataClient
from alpaca.data.requests import StockLatestQuoteRequest
from alpaca.common.exceptions import APIError as AlpacaAPIError

from config.settings import settings
from src.utils.logging import get_logger
from src.utils.exceptions import APIError, TradingError, ValidationError
from src.utils.retry import retry_on_exception, API_RETRY_CONFIG
from src.utils.monitoring import metrics_collector

logger = get_logger(__name__)

class OrderStatusEnum(Enum):
    """Order status enumeration."""
    NEW = "new"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    DONE_FOR_DAY = "done_for_day"
    CANCELED = "canceled"
    EXPIRED = "expired"
    REPLACED = "replaced"
    PENDING_CANCEL = "pending_cancel"
    PENDING_REPLACE = "pending_replace"
    ACCEPTED = "accepted"
    PENDING_NEW = "pending_new"
    ACCEPTED_FOR_BIDDING = "accepted_for_bidding"
    STOPPED = "stopped"
    REJECTED = "rejected"
    SUSPENDED = "suspended"

@dataclass
class TradeOrder:
    """Trade order data structure."""
    ticker: str
    side: str  # "buy" or "sell"
    quantity: Union[int, float]
    order_type: str
    time_in_force: str
    amount: Optional[float] = None  # For notional orders

@dataclass
class PositionInfo:
    """Position information data structure."""
    ticker: str
    quantity: float
    market_value: float
    cost_basis: float
    unrealized_pnl: float
    unrealized_pnl_percent: float
    current_price: float
    last_updated: datetime

@dataclass
class OrderInfo:
    """Order information data structure."""
    order_id: str
    ticker: str
    side: str
    quantity: float
    filled_quantity: float
    order_type: str
    status: str
    submitted_at: datetime
    filled_at: Optional[datetime]
    filled_avg_price: Optional[float]
    time_in_force: str

class AlpacaClient:
    """
    Alpaca Trading API client for paper trading and portfolio management.
    
    Features:
    - Paper trading configuration (paper=True)
    - Market order placement with GTC time-in-force
    - Order status monitoring and tracking
    - Position fetching for portfolio calculations
    - Account information and buying power checks
    - Market data fetching for current prices
    - Ticker symbol validation before order placement
    - Order retry logic for failed executions (3 attempts max)
    - Batch operations for multiple orders
    - Position reconciliation with database
    - Trade execution logging with complete audit trail
    """
    
    def __init__(self, api_key: Optional[str] = None, secret_key: Optional[str] = None, paper: Optional[bool] = None):
        """
        Initialize Alpaca client.
        
        Args:
            api_key: Alpaca API key. If None, uses settings configuration.
            secret_key: Alpaca secret key. If None, uses settings configuration.
            paper: Paper trading mode. If None, uses settings configuration.
        """
        self.api_key = api_key or settings.api.alpaca_api_key
        self.secret_key = secret_key or settings.api.alpaca_secret_key
        self.paper = paper if paper is not None else settings.api.alpaca_paper_trading
        
        if not self.api_key or not self.secret_key:
            raise ValueError("Alpaca API key and secret key are required")
        
        # Initialize trading client
        self.trading_client = TradingClient(
            api_key=self.api_key,
            secret_key=self.secret_key,
            paper=self.paper
        )
        
        # Initialize data client for market data
        self.data_client = StockHistoricalDataClient(
            api_key=self.api_key,
            secret_key=self.secret_key
        )
        
        # Configuration
        self.max_retries = settings.api.retry_max_attempts
        self.timeout = settings.api.timeout_seconds
        self.min_trade_amount = settings.trading.minimum_amount
        
        # Account info cache
        self._account_info = None
        self._account_info_cache_time = 0
        self._account_info_cache_ttl = 60  # 1 minute
        
        logger.info(f"Initialized Alpaca client in {'paper' if self.paper else 'live'} trading mode")
    
    @retry_on_exception(API_RETRY_CONFIG)
    def _make_trading_request(self, operation: str, *args, **kwargs) -> Any:
        """
        Make trading request with error handling and retry logic.
        
        Args:
            operation: Name of the trading client method to call
            *args: Arguments to pass to the method
            **kwargs: Keyword arguments to pass to the method
            
        Returns:
            Result of the trading operation
            
        Raises:
            APIError: For API failures
        """
        start_time = time.time()
        try:
            method = getattr(self.trading_client, operation)
            result = method(*args, **kwargs)
            
            request_time = time.time() - start_time
            metrics_collector.record_execution_time(f"alpaca_{operation}", request_time)
            
            logger.debug(f"Alpaca {operation} completed in {request_time:.2f}s")
            return result
        
        except AlpacaAPIError as e:
            error_msg = f"Alpaca API error in {operation}: {e}"
            logger.error(error_msg)
            
            # Map Alpaca status codes to our error handling
            status_code = getattr(e, 'status_code', None)
            raise APIError(
                error_msg,
                api_name="Alpaca",
                status_code=status_code
            )
        except Exception as e:
            error_msg = f"Unexpected error in Alpaca {operation}: {e}"
            logger.error(error_msg)
            raise APIError(error_msg, api_name="Alpaca")
    
    def get_account_info(self, use_cache: bool = True) -> TradeAccount:
        """
        Get account information including buying power.
        
        Args:
            use_cache: Whether to use cached account info
            
        Returns:
            Account information
        """
        current_time = time.time()
        
        if (use_cache and self._account_info and 
            current_time - self._account_info_cache_time < self._account_info_cache_ttl):
            return self._account_info
        
        account = self._make_trading_request('get_account')
        
        self._account_info = account
        self._account_info_cache_time = current_time
        
        logger.info(f"Account info: buying_power=${account.buying_power}, portfolio_value=${account.portfolio_value}")
        return account
    
    def validate_ticker(self, ticker: str) -> bool:
        """
        Validate ticker symbol before order placement.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            True if ticker is valid and tradeable
        """
        try:
            # Try to get latest quote to validate ticker
            request = StockLatestQuoteRequest(symbol_or_symbols=[ticker])
            response = self.data_client.get_stock_latest_quote(request)
            
            if ticker in response:
                logger.debug(f"Ticker {ticker} validated successfully")
                return True
            else:
                logger.warning(f"Ticker {ticker} not found in market data")
                return False
        
        except Exception as e:
            logger.warning(f"Failed to validate ticker {ticker}: {e}")
            return False
    
    def get_current_price(self, ticker: str) -> Optional[float]:
        """
        Get current market price for a ticker.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Current price or None if unavailable
        """
        try:
            request = StockLatestQuoteRequest(symbol_or_symbols=[ticker])
            response = self.data_client.get_stock_latest_quote(request)
            
            if ticker in response:
                quote = response[ticker]
                # Use mid price (average of bid and ask)
                price = (float(quote.bid_price) + float(quote.ask_price)) / 2
                logger.debug(f"Current price for {ticker}: ${price:.2f}")
                return price
            
            return None
        
        except Exception as e:
            logger.warning(f"Failed to get current price for {ticker}: {e}")
            return None
    
    def calculate_order_quantity(self, ticker: str, amount: float) -> Optional[int]:
        """
        Calculate order quantity based on dollar amount and current price.
        
        Args:
            ticker: Stock ticker symbol
            amount: Dollar amount to invest
            
        Returns:
            Number of shares to buy or None if calculation fails
        """
        current_price = self.get_current_price(ticker)
        if not current_price or current_price <= 0:
            logger.error(f"Cannot calculate quantity for {ticker}: invalid price")
            return None
        
        quantity = int(amount / current_price)
        
        if quantity <= 0:
            logger.warning(f"Calculated quantity is 0 for {ticker} with amount ${amount} and price ${current_price}")
            return None
        
        logger.info(f"Calculated quantity for {ticker}: {quantity} shares (${amount} / ${current_price:.2f})")
        return quantity
    
    def place_market_order(self, ticker: str, side: str, quantity: Optional[int] = None, 
                          notional: Optional[float] = None, 
                          time_in_force: str = "gtc") -> Optional[OrderInfo]:
        """
        Place a market order.
        
        Args:
            ticker: Stock ticker symbol
            side: "buy" or "sell"
            quantity: Number of shares (if None, uses notional)
            notional: Dollar amount (if None, uses quantity)
            time_in_force: Order time in force ("gtc", "day", "ioc", "fok")
            
        Returns:
            Order information or None if order fails
            
        Raises:
            ValidationError: For invalid parameters
            TradingError: For trading-related failures
        """
        # Validate parameters
        if not ticker:
            raise ValidationError("Ticker symbol is required")
        
        if side.lower() not in ['buy', 'sell']:
            raise ValidationError("Side must be 'buy' or 'sell'")
        
        if not quantity and not notional:
            raise ValidationError("Either quantity or notional amount is required")
        
        if quantity and quantity <= 0:
            raise ValidationError("Quantity must be positive")
        
        if notional and notional <= 0:
            raise ValidationError("Notional amount must be positive")
        
        # Validate ticker
        if not self.validate_ticker(ticker):
            raise ValidationError(f"Invalid or non-tradeable ticker: {ticker}")
        
        # Check buying power for buy orders
        if side.lower() == 'buy':
            account = self.get_account_info()
            buying_power = float(account.buying_power)
            
            order_value = notional or (quantity * (self.get_current_price(ticker) or 0))
            if order_value > buying_power:
                raise TradingError(f"Insufficient buying power: ${buying_power:.2f} < ${order_value:.2f}")
        
        # Convert time_in_force
        tif_map = {
            'gtc': TimeInForce.GTC,
            'day': TimeInForce.DAY,
            'ioc': TimeInForce.IOC,
            'fok': TimeInForce.FOK
        }
        
        if time_in_force.lower() not in tif_map:
            raise ValidationError(f"Invalid time_in_force: {time_in_force}")
        
        tif = tif_map[time_in_force.lower()]
        order_side = OrderSide.BUY if side.lower() == 'buy' else OrderSide.SELL
        
        # Create order request
        if quantity:
            order_request = MarketOrderRequest(
                symbol=ticker,
                qty=quantity,
                side=order_side,
                time_in_force=tif
            )
            order_description = f"{side} {quantity} shares of {ticker}"
        else:
            order_request = MarketOrderRequest(
                symbol=ticker,
                notional=notional,
                side=order_side,
                time_in_force=tif
            )
            order_description = f"{side} ${notional} of {ticker}"
        
        logger.info(f"Placing market order: {order_description}")
        
        try:
            # Place order with retry logic
            for attempt in range(self.max_retries):
                try:
                    order = self._make_trading_request('submit_order', order_request)
                    
                    order_info = OrderInfo(
                        order_id=str(order.id),
                        ticker=ticker,
                        side=side.lower(),
                        quantity=float(order.qty) if order.qty else 0,
                        filled_quantity=float(order.filled_qty) if order.filled_qty else 0,
                        order_type='market',
                        status=order.status.value,
                        submitted_at=order.submitted_at,
                        filled_at=order.filled_at,
                        filled_avg_price=float(order.filled_avg_price) if order.filled_avg_price else None,
                        time_in_force=time_in_force.lower()
                    )
                    
                    logger.info(f"Order placed successfully: {order_info.order_id}")
                    metrics_collector.record_execution_time("order_placement_success", 1)
                    
                    return order_info
                
                except APIError as e:
                    if attempt == self.max_retries - 1:
                        raise TradingError(f"Failed to place order after {self.max_retries} attempts: {e}")
                    
                    wait_time = (attempt + 1) * 2  # Exponential backoff
                    logger.warning(f"Order placement attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
                    time.sleep(wait_time)
                
                except Exception as e:
                    if attempt == self.max_retries - 1:
                        raise TradingError(f"Unexpected error placing order: {e}")
                    
                    wait_time = (attempt + 1) * 2
                    logger.warning(f"Unexpected error on attempt {attempt + 1}, retrying in {wait_time}s: {e}")
                    time.sleep(wait_time)
        
        except Exception as e:
            metrics_collector.record_execution_time("order_placement_failure", 1)
            raise TradingError(f"Failed to place market order: {e}")
    
    def get_order_status(self, order_id: str) -> Optional[OrderInfo]:
        """
        Get order status by order ID.
        
        Args:
            order_id: Alpaca order ID
            
        Returns:
            Order information or None if not found
        """
        try:
            order = self._make_trading_request('get_order_by_id', order_id)
            
            return OrderInfo(
                order_id=str(order.id),
                ticker=order.symbol,
                side=order.side.value.lower(),
                quantity=float(order.qty) if order.qty else 0,
                filled_quantity=float(order.filled_qty) if order.filled_qty else 0,
                order_type=order.order_type.value.lower(),
                status=order.status.value,
                submitted_at=order.submitted_at,
                filled_at=order.filled_at,
                filled_avg_price=float(order.filled_avg_price) if order.filled_avg_price else None,
                time_in_force=order.time_in_force.value.lower()
            )
        
        except Exception as e:
            logger.error(f"Failed to get order status for {order_id}: {e}")
            return None
    
    def get_all_positions(self) -> List[PositionInfo]:
        """
        Get all current positions.
        
        Returns:
            List of position information
        """
        try:
            positions = self._make_trading_request('get_all_positions')
            
            position_info = []
            for position in positions:
                pos_info = PositionInfo(
                    ticker=position.symbol,
                    quantity=float(position.qty),
                    market_value=float(position.market_value),
                    cost_basis=float(position.cost_basis),
                    unrealized_pnl=float(position.unrealized_pl),
                    unrealized_pnl_percent=float(position.unrealized_plpc),
                    current_price=float(position.current_price),
                    last_updated=datetime.now()
                )
                position_info.append(pos_info)
            
            logger.info(f"Retrieved {len(position_info)} positions")
            return position_info
        
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            return []
    
    def get_position(self, ticker: str) -> Optional[PositionInfo]:
        """
        Get position for specific ticker.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Position information or None if no position
        """
        try:
            position = self._make_trading_request('get_open_position', ticker)
            
            return PositionInfo(
                ticker=position.symbol,
                quantity=float(position.qty),
                market_value=float(position.market_value),
                cost_basis=float(position.cost_basis),
                unrealized_pnl=float(position.unrealized_pl),
                unrealized_pnl_percent=float(position.unrealized_plpc),
                current_price=float(position.current_price),
                last_updated=datetime.now()
            )
        
        except Exception as e:
            logger.debug(f"No position found for {ticker}: {e}")
            return None
    
    def place_batch_orders(self, orders: List[TradeOrder]) -> List[Optional[OrderInfo]]:
        """
        Place multiple orders in sequence.
        
        Args:
            orders: List of trade orders
            
        Returns:
            List of order information (None for failed orders)
        """
        results = []
        
        for order in orders:
            try:
                if order.amount:
                    # Calculate quantity from notional amount
                    quantity = self.calculate_order_quantity(order.ticker, order.amount)
                    if not quantity:
                        logger.error(f"Could not calculate quantity for {order.ticker}")
                        results.append(None)
                        continue
                else:
                    quantity = int(order.quantity)
                
                order_info = self.place_market_order(
                    ticker=order.ticker,
                    side=order.side,
                    quantity=quantity,
                    time_in_force=order.time_in_force
                )
                
                results.append(order_info)
                
                # Small delay between orders to avoid rate limiting
                time.sleep(0.5)
            
            except Exception as e:
                logger.error(f"Failed to place order for {order.ticker}: {e}")
                results.append(None)
        
        successful_orders = sum(1 for result in results if result is not None)
        logger.info(f"Batch order results: {successful_orders}/{len(orders)} successful")
        
        return results
    
    def close_position(self, ticker: str, percentage: float = 100.0) -> Optional[OrderInfo]:
        """
        Close position (sell shares).
        
        Args:
            ticker: Stock ticker symbol
            percentage: Percentage of position to close (default 100%)
            
        Returns:
            Order information or None if failed
        """
        position = self.get_position(ticker)
        if not position:
            logger.warning(f"No position to close for {ticker}")
            return None
        
        if position.quantity <= 0:
            logger.warning(f"No shares to sell for {ticker}")
            return None
        
        quantity_to_sell = int(position.quantity * (percentage / 100.0))
        
        if quantity_to_sell <= 0:
            logger.warning(f"Calculated 0 shares to sell for {ticker}")
            return None
        
        logger.info(f"Closing {percentage}% of {ticker} position: {quantity_to_sell} shares")
        
        return self.place_market_order(
            ticker=ticker,
            side='sell',
            quantity=quantity_to_sell
        )
    
    def test_connection(self) -> bool:
        """
        Test connection to Alpaca API.
        
        Returns:
            True if connection is successful
        """
        try:
            account = self.get_account_info(use_cache=False)
            logger.info(f"Alpaca API connection test successful, account: {account.account_number}")
            return True
        except Exception as e:
            logger.error(f"Alpaca API connection test failed: {e}")
            return False
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """
        Get portfolio summary information.
        
        Returns:
            Dictionary with portfolio metrics
        """
        try:
            account = self.get_account_info(use_cache=False)
            positions = self.get_all_positions()
            
            total_market_value = sum(pos.market_value for pos in positions)
            total_unrealized_pnl = sum(pos.unrealized_pnl for pos in positions)
            
            return {
                'account_value': float(account.portfolio_value),
                'buying_power': float(account.buying_power),
                'cash': float(account.cash),
                'total_positions': len(positions),
                'total_market_value': total_market_value,
                'total_unrealized_pnl': total_unrealized_pnl,
                'day_trade_count': int(account.daytrade_count) if account.daytrade_count else 0,
                'is_paper_account': self.paper
            }
        
        except Exception as e:
            logger.error(f"Failed to get portfolio summary: {e}")
            return {}
    
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an open order.
        
        Args:
            order_id: Alpaca order ID
            
        Returns:
            True if cancellation was successful
        """
        try:
            self._make_trading_request('cancel_order_by_id', order_id)
            logger.info(f"Order {order_id} cancelled successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return False