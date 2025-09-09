"""
Financial calculation utilities for trading automation system.
Provides portfolio calculations, return metrics, and performance analytics.
"""
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, date
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from src.utils.logging import get_logger

logger = get_logger(__name__)

@dataclass
class PortfolioMetrics:
    """Portfolio performance metrics."""
    total_value: float
    total_cost_basis: float
    total_unrealized_pnl: float
    total_unrealized_pnl_percent: float
    daily_return: float
    daily_return_percent: float
    position_count: int
    largest_position_value: float
    largest_position_ticker: str

@dataclass
class PositionMetrics:
    """Individual position metrics."""
    ticker: str
    quantity: float
    current_price: float
    market_value: float
    cost_basis: float
    avg_cost_per_share: float
    unrealized_pnl: float
    unrealized_pnl_percent: float
    weight_in_portfolio: float
    daily_return: float
    daily_return_percent: float
    since_open_return: float
    since_open_return_percent: float

def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    Safely divide two numbers, returning default if denominator is zero.
    
    Args:
        numerator: The numerator
        denominator: The denominator
        default: Default value if division by zero
        
    Returns:
        Division result or default
    """
    if denominator == 0:
        return default
    return numerator / denominator

def safe_percentage(value: float, total: float, default: float = 0.0) -> float:
    """
    Safely calculate percentage, handling zero total.
    
    Args:
        value: The value to calculate percentage for
        total: The total value
        default: Default value if total is zero
        
    Returns:
        Percentage (0-100) or default
    """
    if total == 0:
        return default
    return (value / total) * 100

def round_currency(amount: float, precision: int = 2) -> float:
    """
    Round currency amount to specified precision.
    
    Args:
        amount: Amount to round
        precision: Number of decimal places
        
    Returns:
        Rounded amount
    """
    if amount is None:
        return 0.0
    
    decimal_amount = Decimal(str(amount))
    rounded = decimal_amount.quantize(
        Decimal('0.' + '0' * precision),
        rounding=ROUND_HALF_UP
    )
    return float(rounded)

def calculate_return(current_value: float, reference_value: float) -> Tuple[float, float]:
    """
    Calculate return amount and percentage.
    
    Args:
        current_value: Current value
        reference_value: Reference value (cost basis, previous value, etc.)
        
    Returns:
        Tuple of (return_amount, return_percentage)
    """
    return_amount = current_value - reference_value
    return_percentage = safe_percentage(return_amount, abs(reference_value))
    
    return return_amount, return_percentage

def calculate_portfolio_weight(position_value: float, total_portfolio_value: float) -> float:
    """
    Calculate position weight in portfolio.
    
    Args:
        position_value: Market value of the position
        total_portfolio_value: Total portfolio market value
        
    Returns:
        Weight as percentage (0-100)
    """
    return safe_percentage(position_value, total_portfolio_value)

def calculate_position_metrics(
    ticker: str,
    quantity: float,
    avg_cost: float,
    current_price: float,
    previous_close: Optional[float] = None,
    open_price: Optional[float] = None,
    total_portfolio_value: Optional[float] = None
) -> PositionMetrics:
    """
    Calculate comprehensive position metrics.
    
    Args:
        ticker: Stock ticker symbol
        quantity: Number of shares
        avg_cost: Average cost per share
        current_price: Current market price
        previous_close: Previous day's closing price
        open_price: Today's opening price
        total_portfolio_value: Total portfolio value for weight calculation
        
    Returns:
        Position metrics
    """
    # Basic calculations
    market_value = quantity * current_price
    cost_basis = quantity * avg_cost
    unrealized_pnl = market_value - cost_basis
    unrealized_pnl_percent = safe_percentage(unrealized_pnl, abs(cost_basis))
    
    # Portfolio weight
    weight_in_portfolio = 0.0
    if total_portfolio_value:
        weight_in_portfolio = calculate_portfolio_weight(market_value, total_portfolio_value)
    
    # Daily return
    daily_return = 0.0
    daily_return_percent = 0.0
    if previous_close:
        daily_return = (current_price - previous_close) * quantity
        daily_return_percent = safe_percentage(current_price - previous_close, previous_close)
    
    # Since-open return
    since_open_return = 0.0
    since_open_return_percent = 0.0
    if open_price:
        since_open_return = (current_price - open_price) * quantity
        since_open_return_percent = safe_percentage(current_price - open_price, open_price)
    
    return PositionMetrics(
        ticker=ticker,
        quantity=quantity,
        current_price=current_price,
        market_value=round_currency(market_value),
        cost_basis=round_currency(cost_basis),
        avg_cost_per_share=round_currency(avg_cost),
        unrealized_pnl=round_currency(unrealized_pnl),
        unrealized_pnl_percent=round_currency(unrealized_pnl_percent),
        weight_in_portfolio=round_currency(weight_in_portfolio),
        daily_return=round_currency(daily_return),
        daily_return_percent=round_currency(daily_return_percent),
        since_open_return=round_currency(since_open_return),
        since_open_return_percent=round_currency(since_open_return_percent)
    )

def calculate_portfolio_metrics(
    positions: List[PositionMetrics],
    previous_portfolio_value: Optional[float] = None
) -> PortfolioMetrics:
    """
    Calculate comprehensive portfolio metrics.
    
    Args:
        positions: List of position metrics
        previous_portfolio_value: Previous portfolio value for daily return calculation
        
    Returns:
        Portfolio metrics
    """
    if not positions:
        return PortfolioMetrics(
            total_value=0.0,
            total_cost_basis=0.0,
            total_unrealized_pnl=0.0,
            total_unrealized_pnl_percent=0.0,
            daily_return=0.0,
            daily_return_percent=0.0,
            position_count=0,
            largest_position_value=0.0,
            largest_position_ticker=""
        )
    
    # Aggregate values
    total_value = sum(pos.market_value for pos in positions)
    total_cost_basis = sum(pos.cost_basis for pos in positions)
    total_unrealized_pnl = sum(pos.unrealized_pnl for pos in positions)
    total_daily_return = sum(pos.daily_return for pos in positions)
    
    # Calculate percentages
    total_unrealized_pnl_percent = safe_percentage(total_unrealized_pnl, abs(total_cost_basis))
    
    # Daily return percentage
    daily_return_percent = 0.0
    if previous_portfolio_value:
        daily_return_percent = safe_percentage(
            total_value - previous_portfolio_value,
            previous_portfolio_value
        )
    
    # Find largest position
    largest_position = max(positions, key=lambda p: p.market_value)
    
    return PortfolioMetrics(
        total_value=round_currency(total_value),
        total_cost_basis=round_currency(total_cost_basis),
        total_unrealized_pnl=round_currency(total_unrealized_pnl),
        total_unrealized_pnl_percent=round_currency(total_unrealized_pnl_percent),
        daily_return=round_currency(total_daily_return),
        daily_return_percent=round_currency(daily_return_percent),
        position_count=len(positions),
        largest_position_value=round_currency(largest_position.market_value),
        largest_position_ticker=largest_position.ticker
    )

def calculate_sharpe_ratio(
    returns: List[float],
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252
) -> Optional[float]:
    """
    Calculate Sharpe ratio for a series of returns.
    
    Args:
        returns: List of return percentages
        risk_free_rate: Annual risk-free rate (default 0%)
        periods_per_year: Number of periods per year (default 252 for daily)
        
    Returns:
        Sharpe ratio or None if insufficient data
    """
    if len(returns) < 2:
        return None
    
    import numpy as np
    
    returns_array = np.array(returns)
    
    # Convert to excess returns
    daily_risk_free = risk_free_rate / periods_per_year
    excess_returns = returns_array - daily_risk_free
    
    # Calculate Sharpe ratio
    mean_excess_return = np.mean(excess_returns)
    std_excess_return = np.std(excess_returns, ddof=1)
    
    if std_excess_return == 0:
        return None
    
    sharpe_ratio = (mean_excess_return / std_excess_return) * np.sqrt(periods_per_year)
    return round_currency(sharpe_ratio, 4)

def calculate_max_drawdown(values: List[float]) -> Tuple[float, float]:
    """
    Calculate maximum drawdown from a series of portfolio values.
    
    Args:
        values: List of portfolio values over time
        
    Returns:
        Tuple of (max_drawdown_amount, max_drawdown_percent)
    """
    if len(values) < 2:
        return 0.0, 0.0
    
    import numpy as np
    
    values_array = np.array(values)
    
    # Calculate running maximum
    running_max = np.maximum.accumulate(values_array)
    
    # Calculate drawdown
    drawdown = values_array - running_max
    
    # Find maximum drawdown
    max_drawdown_amount = np.min(drawdown)
    max_drawdown_percent = safe_percentage(max_drawdown_amount, np.max(running_max))
    
    return round_currency(max_drawdown_amount), round_currency(max_drawdown_percent)

def calculate_volatility(returns: List[float], periods_per_year: int = 252) -> Optional[float]:
    """
    Calculate annualized volatility from returns.
    
    Args:
        returns: List of return percentages
        periods_per_year: Number of periods per year (default 252 for daily)
        
    Returns:
        Annualized volatility percentage or None if insufficient data
    """
    if len(returns) < 2:
        return None
    
    import numpy as np
    
    returns_array = np.array(returns) / 100  # Convert percentages to decimals
    volatility = np.std(returns_array, ddof=1) * np.sqrt(periods_per_year) * 100
    
    return round_currency(volatility, 4)

def calculate_beta(asset_returns: List[float], market_returns: List[float]) -> Optional[float]:
    """
    Calculate beta relative to market returns.
    
    Args:
        asset_returns: List of asset return percentages
        market_returns: List of market return percentages
        
    Returns:
        Beta value or None if insufficient data
    """
    if len(asset_returns) != len(market_returns) or len(asset_returns) < 2:
        return None
    
    import numpy as np
    
    asset_array = np.array(asset_returns)
    market_array = np.array(market_returns)
    
    # Calculate covariance and variance
    covariance = np.cov(asset_array, market_array)[0, 1]
    market_variance = np.var(market_array, ddof=1)
    
    if market_variance == 0:
        return None
    
    beta = covariance / market_variance
    return round_currency(beta, 4)

def calculate_information_ratio(
    portfolio_returns: List[float],
    benchmark_returns: List[float]
) -> Optional[float]:
    """
    Calculate information ratio (active return / tracking error).
    
    Args:
        portfolio_returns: List of portfolio return percentages
        benchmark_returns: List of benchmark return percentages
        
    Returns:
        Information ratio or None if insufficient data
    """
    if len(portfolio_returns) != len(benchmark_returns) or len(portfolio_returns) < 2:
        return None
    
    import numpy as np
    
    portfolio_array = np.array(portfolio_returns)
    benchmark_array = np.array(benchmark_returns)
    
    # Calculate active returns
    active_returns = portfolio_array - benchmark_array
    
    # Calculate information ratio
    mean_active_return = np.mean(active_returns)
    tracking_error = np.std(active_returns, ddof=1)
    
    if tracking_error == 0:
        return None
    
    information_ratio = mean_active_return / tracking_error
    return round_currency(information_ratio, 4)

def format_currency(amount: float, symbol: str = "$") -> str:
    """
    Format currency amount for display.
    
    Args:
        amount: Amount to format
        symbol: Currency symbol
        
    Returns:
        Formatted currency string
    """
    if amount >= 0:
        return f"{symbol}{amount:,.2f}"
    else:
        return f"-{symbol}{abs(amount):,.2f}"

def format_percentage(percentage: float, precision: int = 2) -> str:
    """
    Format percentage for display.
    
    Args:
        percentage: Percentage value
        precision: Number of decimal places
        
    Returns:
        Formatted percentage string
    """
    if percentage >= 0:
        return f"+{percentage:.{precision}f}%"
    else:
        return f"{percentage:.{precision}f}%"

def calculate_compound_annual_growth_rate(
    beginning_value: float,
    ending_value: float,
    num_years: float
) -> Optional[float]:
    """
    Calculate compound annual growth rate (CAGR).
    
    Args:
        beginning_value: Starting value
        ending_value: Ending value
        num_years: Number of years
        
    Returns:
        CAGR percentage or None if invalid inputs
    """
    if beginning_value <= 0 or ending_value <= 0 or num_years <= 0:
        return None
    
    cagr = (pow(ending_value / beginning_value, 1 / num_years) - 1) * 100
    return round_currency(cagr, 4)