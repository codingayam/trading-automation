"""
Dashboard API endpoints using Flask.
Provides REST API endpoints for dashboard data including agent performance,
positions, and system health information.
"""
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional
import time
import logging
from functools import wraps

from config.settings import settings
from src.data.database import DatabaseManager, get_agent_positions, get_agent_performance_history, get_all_agent_summaries
from src.data.market_data_service import MarketDataService
from src.data.alpaca_client import AlpacaClient
from src.utils.logging import get_logger
from src.utils.calculations import calculate_position_metrics, format_currency, format_percentage
from src.utils.exceptions import APIError, ValidationError
from src.utils.monitoring import metrics_collector
from src.utils.health import health_checker

logger = get_logger(__name__)

# Initialize services
db = DatabaseManager()
market_data = MarketDataService()
alpaca_client = AlpacaClient()

app = Flask(__name__, 
            template_folder='templates',
            static_folder='static')

# Configure CORS for frontend integration
CORS(app, origins=['*'])  # Configure based on your frontend domain in production

# Disable Flask's default logging to avoid conflicts
logging.getLogger('werkzeug').setLevel(logging.WARNING)


def calculate_agent_lifetime_return(agent_id: str, current_unrealized_pnl: float) -> float:
    """Calculate agent's lifetime total return including realized profits."""
    try:
        # Get all trades for the agent
        query = """
        SELECT 
            ticker,
            SUM(CASE WHEN quantity > 0 THEN quantity * price ELSE 0 END) as total_invested,
            SUM(CASE WHEN quantity < 0 THEN ABS(quantity) * price ELSE 0 END) as total_proceeds,
            SUM(quantity * price) as net_cash_flow
        FROM trades 
        WHERE agent_id = ? AND order_status IN ('filled', 'partially_filled')
        GROUP BY ticker
        """
        
        rows = db.execute_query(query, (agent_id,))
        
        total_invested = 0.0
        total_realized_pnl = 0.0
        
        for row in rows:
            ticker_invested = float(row[1] or 0)  # Money spent on buys
            ticker_proceeds = float(row[2] or 0)  # Money received from sells
            net_cash_flow = float(row[3] or 0)   # Net cash flow for the ticker
            
            # For closed positions (net_cash_flow close to 0), calculate realized P&L
            if abs(net_cash_flow) < 1.0:  # Position is essentially closed
                realized_pnl = ticker_proceeds - ticker_invested
                total_realized_pnl += realized_pnl
            else:
                # For open positions, only count the invested amount
                if ticker_invested > 0:
                    total_invested += ticker_invested
        
        # Calculate overall lifetime return
        # Total P&L = Realized P&L (from closed positions) + Unrealized P&L (from open positions)
        total_lifetime_pnl = total_realized_pnl + current_unrealized_pnl
        
        if total_invested > 0:
            return (total_lifetime_pnl / total_invested) * 100
        else:
            return 0.0
            
    except Exception as e:
        logger.warning(f"Could not calculate lifetime return for agent {agent_id}: {e}")
        return 0.0


# Cache for performance optimization (15-minute refresh)
cache_ttl = 900  # 15 minutes
api_cache = {}


def cache_response(ttl_seconds: int = 900):
    """Decorator to cache API responses."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Create cache key from function name and args
            cache_key = f"{f.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
            
            current_time = time.time()
            
            # Check if we have cached data
            if cache_key in api_cache:
                data, cache_time = api_cache[cache_key]
                if current_time - cache_time < ttl_seconds:
                    logger.debug(f"Returning cached response for {f.__name__}")
                    return data
                else:
                    # Remove expired cache entry
                    del api_cache[cache_key]
            
            # Generate fresh response
            result = f(*args, **kwargs)
            api_cache[cache_key] = (result, current_time)
            
            return result
        return wrapper
    return decorator


def handle_api_errors(f):
    """Decorator to handle API errors and return proper HTTP responses."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            start_time = time.time()
            result = f(*args, **kwargs)
            
            # Record API response time
            response_time = time.time() - start_time
            metrics_collector.record_execution_time(f"api_{f.__name__}", response_time)
            
            return result
        except APIError as e:
            logger.error(f"API error in {f.__name__}: {e}")
            return jsonify({'error': str(e), 'code': 'API_ERROR'}), 500
        except ValidationError as e:
            logger.error(f"Validation error in {f.__name__}: {e}")
            return jsonify({'error': str(e), 'code': 'VALIDATION_ERROR'}), 400
        except Exception as e:
            logger.error(f"Unexpected error in {f.__name__}: {e}")
            return jsonify({'error': 'Internal server error', 'code': 'INTERNAL_ERROR'}), 500
    return wrapper


def get_real_time_agent_positions(agent_id: str) -> List[Dict[str, Any]]:
    """Get real-time positions for an agent from Alpaca."""
    try:
        # Get all current Alpaca positions
        alpaca_positions = alpaca_client.get_all_positions()
        
        # Get agent's trade history to determine which positions belong to this agent
        # For now, let's use a simpler approach - get positions for tickers the agent has traded
        agent_tickers_query = """
        SELECT DISTINCT ticker FROM trades WHERE agent_id = ?
        """
        agent_ticker_rows = db.execute_query(agent_tickers_query, (agent_id,))
        agent_tickers = [row[0] for row in agent_ticker_rows]
        
        # Filter Alpaca positions to only include agent's tickers
        agent_positions = []
        for position in alpaca_positions:
            if position.ticker in agent_tickers:
                # Calculate additional metrics
                quantity = float(position.quantity)
                market_value = float(position.market_value)
                cost_basis = float(position.cost_basis) if hasattr(position, 'cost_basis') else 0.0
                current_price = float(position.current_price)
                unrealized_pnl = float(position.unrealized_pnl) if hasattr(position, 'unrealized_pnl') else 0.0
                unrealized_pnl_percent = float(position.unrealized_pnl_percent) if hasattr(position, 'unrealized_pnl_percent') else 0.0
                
                # Calculate total P&L from cost basis
                total_pnl_dollars = market_value - cost_basis if cost_basis != 0 else unrealized_pnl
                total_pnl_percent = (total_pnl_dollars / abs(cost_basis)) if cost_basis != 0 else unrealized_pnl_percent
                
                # Determine side
                side = "Short" if quantity < 0 else "Long"
                
                # Convert to dictionary with new column format
                position_data = {
                    'agent_id': agent_id,
                    # New column format
                    'asset': position.ticker,
                    'qty': abs(quantity),  # Show absolute quantity
                    'side': side,
                    'market_value': market_value,
                    'todays_pnl_percent': unrealized_pnl_percent * 100,  # Convert to percentage
                    'todays_pnl_dollars': unrealized_pnl,
                    'total_pnl_percent': total_pnl_percent * 100,  # Convert to percentage
                    'total_pnl_dollars': total_pnl_dollars,
                    
                    # Keep legacy fields for compatibility
                    'ticker': position.ticker,
                    'quantity': quantity,
                    'current_price': current_price,
                    'unrealized_pnl': unrealized_pnl,
                    'cost_basis': cost_basis,
                    'last_updated': datetime.now().isoformat()
                }
                agent_positions.append(position_data)
        
        return agent_positions
        
    except Exception as e:
        logger.error(f"Error getting real-time positions for agent {agent_id}: {e}")
        # Fallback to database positions
        return get_agent_positions(agent_id)


@app.route('/api/health', methods=['GET'])
@handle_api_errors
def health_check():
    """System health check endpoint."""
    health_status = health_checker.get_system_health()
    
    return jsonify({
        'status': 'healthy' if health_status['overall_status'] else 'unhealthy',
        'timestamp': datetime.now().isoformat(),
        'components': health_status['components'],
        'system_info': health_status['system_info']
    })


@app.route('/api/system/status', methods=['GET'])
@handle_api_errors
@cache_response(ttl_seconds=60)  # 1-minute cache for system status
def system_status():
    """System status and last update time."""
    market_status = market_data.get_market_status()
    cache_stats = market_data.get_cache_stats()
    
    # Get latest trade execution timestamp
    latest_trade = db.execute_single(
        "SELECT MAX(execution_date) as last_execution FROM trades"
    )
    
    last_execution = None
    if latest_trade and latest_trade['last_execution']:
        last_execution = latest_trade['last_execution']
    
    # Get latest position update
    latest_position = db.execute_single(
        "SELECT MAX(last_updated) as last_update FROM agent_positions"
    )
    
    last_position_update = None
    if latest_position and latest_position['last_update']:
        last_position_update = latest_position['last_update']
    
    return jsonify({
        'system_status': 'operational',
        'timestamp': datetime.now().isoformat(),
        'market': market_status,
        'cache': cache_stats,
        'last_trade_execution': last_execution,
        'last_position_update': last_position_update,
        'api_cache_size': len(api_cache)
    })


@app.route('/api/agents', methods=['GET'])
@handle_api_errors
@cache_response(ttl_seconds=60)  # 1-minute cache for real-time data
def get_agents():
    """List all agents with performance summary."""
    try:
        # Get agent summaries from database
        agent_summaries = get_all_agent_summaries()
        
        # Enhance with agent configuration and current market data
        agents_data = []
        agent_configs = settings.get_enabled_agents()
        
        for summary in agent_summaries:
            agent_id = summary['agent_id']
            
            # Find matching agent configuration
            agent_config = next(
                (config for config in agent_configs if config['id'] == agent_id),
                None
            )
            
            if not agent_config:
                logger.warning(f"No configuration found for agent {agent_id}")
                continue
            
            # Calculate returns from real-time positions instead of stale database values
            positions = get_real_time_agent_positions(agent_id)
            
            # Calculate portfolio-level returns from position P&L
            total_portfolio_value = sum(pos.get('market_value', 0) or 0 for pos in positions)
            total_todays_pnl = sum(pos.get('todays_pnl_dollars', 0) or 0 for pos in positions)
            total_unrealized_pnl = sum(pos.get('total_pnl_dollars', 0) or 0 for pos in positions)
            
            # Calculate lifetime total return including realized profits
            lifetime_total_return_pct = calculate_agent_lifetime_return(agent_id, total_unrealized_pnl)
            
            # Calculate return percentages based on portfolio value
            daily_return_pct = 0.0
            
            if total_portfolio_value != 0:
                # Today's return = today's P&L / (portfolio value - today's P&L) * 100
                portfolio_value_yesterday = total_portfolio_value - total_todays_pnl
                if portfolio_value_yesterday != 0:
                    daily_return_pct = (total_todays_pnl / portfolio_value_yesterday) * 100
            
            agent_data = {
                'agent_id': agent_id,
                'name': agent_config['name'],
                'type': agent_config['type'],
                'description': agent_config.get('description', ''),
                'total_value': float(total_portfolio_value),
                'position_count': len([pos for pos in positions if pos.get('qty', 0) != 0]),
                'daily_return_pct': float(daily_return_pct),
                'total_return_pct': float(lifetime_total_return_pct),
                'daily_return_formatted': format_percentage(daily_return_pct),
                'total_return_formatted': format_percentage(lifetime_total_return_pct),
                'total_value_formatted': format_currency(total_portfolio_value),
                'enabled': agent_config.get('enabled', True)
            }
            
            agents_data.append(agent_data)
        
        # Sort by total value descending
        agents_data.sort(key=lambda x: x['total_value'], reverse=True)
        
        return jsonify({
            'agents': agents_data,
            'total_agents': len(agents_data),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting agents summary: {e}")
        raise APIError(f"Failed to retrieve agents data: {e}")


@app.route('/api/agents/<agent_id>', methods=['GET'])
@handle_api_errors
@cache_response(ttl_seconds=60)  # 1-minute cache for real-time data
def get_agent_detail(agent_id: str):
    """Detailed agent information."""
    try:
        # Get agent configuration
        agent_config = settings.get_agent_by_id(agent_id)
        
        # Get real-time agent positions
        positions = get_real_time_agent_positions(agent_id)
        
        # Get recent performance history
        performance_history = get_agent_performance_history(agent_id, days=30)
        
        # Calculate total portfolio value
        total_value = sum(pos.get('market_value', 0) or 0 for pos in positions)
        
        # Get current prices for all positions to calculate returns
        tickers = [pos['ticker'] for pos in positions if pos.get('quantity', 0) > 0]
        current_prices = {}
        
        if tickers:
            current_prices = market_data.get_batch_prices(tickers)
        
        # Use the same real-time position data as the positions endpoint
        position_details = []
        for pos in positions:
            if pos.get('quantity', 0) == 0:
                continue
            
            # Build position detail using new column format
            position_detail = {
                # New format columns
                'asset': pos.get('asset', pos.get('ticker')),
                'qty': pos.get('qty', abs(float(pos.get('quantity', 0)))),
                'side': pos.get('side', 'Long' if pos.get('quantity', 0) > 0 else 'Short'),
                'market_value': pos.get('market_value', 0),
                'todays_pnl_percent': pos.get('todays_pnl_percent', 0),
                'todays_pnl_dollars': pos.get('todays_pnl_dollars', 0),
                'total_pnl_percent': pos.get('total_pnl_percent', 0),
                'total_pnl_dollars': pos.get('total_pnl_dollars', 0),
                
                # Legacy format for compatibility
                'ticker': pos.get('ticker'),
                'quantity': pos.get('quantity', 0),
                'current_price': pos.get('current_price', 0),
                'unrealized_pnl': pos.get('unrealized_pnl', 0),
                'cost_basis': pos.get('cost_basis', 0)
            }
            
            # Add formatted display fields
            position_detail.update({
                'market_value_formatted': format_currency(position_detail['market_value']),
                'todays_pnl_dollars_formatted': format_currency(position_detail['todays_pnl_dollars']),
                'total_pnl_dollars_formatted': format_currency(position_detail['total_pnl_dollars']),
                'todays_pnl_percent_formatted': format_percentage(position_detail['todays_pnl_percent']),
                'total_pnl_percent_formatted': format_percentage(position_detail['total_pnl_percent'])
            })
            
            position_details.append(position_detail)
        
        # Sort positions by market value descending
        position_details.sort(key=lambda x: x['market_value'], reverse=True)
        
        # Calculate returns from real-time position data
        total_todays_pnl = sum(pos.get('todays_pnl_dollars', 0) or 0 for pos in positions)
        total_unrealized_pnl = sum(pos.get('total_pnl_dollars', 0) or 0 for pos in positions)
        
        # Calculate today's return
        daily_return_pct = 0.0
        if total_value != 0:
            portfolio_value_yesterday = total_value - total_todays_pnl
            if portfolio_value_yesterday != 0:
                daily_return_pct = (total_todays_pnl / portfolio_value_yesterday) * 100
        
        # Calculate lifetime total return including realized profits
        lifetime_total_return_pct = calculate_agent_lifetime_return(agent_id, total_unrealized_pnl)
        
        agent_detail = {
            'agent_id': agent_id,
            'name': agent_config['name'],
            'type': agent_config['type'],
            'description': agent_config.get('description', ''),
            'politicians': agent_config.get('politicians', []),
            'total_value': total_value,
            'total_value_formatted': format_currency(total_value),
            'position_count': len(position_details),
            'daily_return_pct': daily_return_pct,
            'total_return_pct': lifetime_total_return_pct,
            'daily_return_formatted': format_percentage(daily_return_pct),
            'total_return_formatted': format_percentage(lifetime_total_return_pct),
            'positions': position_details,
            'performance_history': performance_history[:7]  # Last 7 days
        }
        
        return jsonify({
            'agent': agent_detail,
            'timestamp': datetime.now().isoformat()
        })
        
    except ValueError as e:
        logger.error(f"Agent not found: {agent_id}")
        return jsonify({'error': f'Agent {agent_id} not found'}), 404
    except Exception as e:
        logger.error(f"Error getting agent detail for {agent_id}: {e}")
        raise APIError(f"Failed to retrieve agent details: {e}")


@app.route('/api/agents/<agent_id>/positions', methods=['GET'])
@handle_api_errors
@cache_response(ttl_seconds=30)  # 30-second cache for real-time positions
def get_agent_positions_api(agent_id: str):
    """Current positions for agent."""
    try:
        # Get real-time positions from Alpaca
        positions = get_real_time_agent_positions(agent_id)
        
        # Filter for active positions only
        active_positions = [pos for pos in positions if pos.get('quantity', 0) != 0]
        
        return jsonify({
            'agent_id': agent_id,
            'positions': active_positions,
            'position_count': len(active_positions),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting positions for agent {agent_id}: {e}")
        raise APIError(f"Failed to retrieve agent positions: {e}")


@app.route('/api/agents/<agent_id>/performance', methods=['GET'])
@handle_api_errors
@cache_response(ttl_seconds=600)  # 10-minute cache for performance history
def get_agent_performance(agent_id: str):
    """Performance history for agent."""
    try:
        # Get query parameters
        days = request.args.get('days', default=30, type=int)
        days = min(days, 365)  # Limit to 1 year max
        
        performance_history = get_agent_performance_history(agent_id, days)
        
        return jsonify({
            'agent_id': agent_id,
            'performance_history': performance_history,
            'days': days,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting performance for agent {agent_id}: {e}")
        raise APIError(f"Failed to retrieve agent performance: {e}")


# Dashboard UI Routes
@app.route('/', methods=['GET'])
def dashboard_overview():
    """Render overview dashboard."""
    return render_template('overview.html')


@app.route('/agent/<agent_id>', methods=['GET'])
def agent_detail_page(agent_id: str):
    """Render individual agent dashboard."""
    try:
        agent_config = settings.get_agent_by_id(agent_id)
        return render_template('agent_detail.html', 
                             agent_id=agent_id, 
                             agent_name=agent_config['name'])
    except ValueError:
        return render_template('error.html', 
                             error=f"Agent '{agent_id}' not found"), 404


# Utility endpoints for development
@app.route('/api/cache/clear', methods=['POST'])
@handle_api_errors
def clear_cache():
    """Clear API cache (development utility)."""
    if not settings.is_development:
        return jsonify({'error': 'Not available in production'}), 403
    
    api_cache.clear()
    market_data.clear_cache()
    
    return jsonify({
        'message': 'Cache cleared successfully',
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/cache/stats', methods=['GET'])
@handle_api_errors
def cache_stats():
    """Get cache statistics."""
    return jsonify({
        'api_cache_size': len(api_cache),
        'market_data_cache': market_data.get_cache_stats(),
        'timestamp': datetime.now().isoformat()
    })


# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500


def create_app(config_name='default'):
    """Application factory."""
    app.config['DEBUG'] = settings.dashboard.debug
    app.config['SECRET_KEY'] = 'dev-secret-key'  # Use proper secret in production
    
    return app


if __name__ == '__main__':
    app.run(
        host=settings.dashboard.host,
        port=settings.dashboard.port,
        debug=settings.dashboard.debug
    )