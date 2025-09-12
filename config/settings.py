"""
Configuration management for trading automation system.
Handles environment variables, agent definitions, and environment-specific settings.
"""
import os
import json
from pathlib import Path
from typing import Dict, Any, List
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base project directory
PROJECT_ROOT = Path(__file__).parent.parent.absolute()

@dataclass
class DatabaseConfig:
    """Database configuration settings."""
    path: str
    backup_enabled: bool
    backup_retention_days: int
    
    @property
    def full_path(self) -> str:
        """Get absolute database path."""
        if os.path.isabs(self.path):
            return self.path
        return str(PROJECT_ROOT / self.path)

@dataclass
class APIConfig:
    """API configuration settings."""
    quiver_api_key: str
    alpaca_api_key: str
    alpaca_secret_key: str
    alpaca_paper_trading: bool
    alpaca_base_url: str
    rate_limit_per_minute: int
    timeout_seconds: int
    retry_max_attempts: int
    retry_backoff_factor: float

@dataclass
class TradingConfig:
    """Trading configuration settings."""
    minimum_amount: float
    size_type: str
    politician_match_threshold: float
    minimum_congress_trade_value: float

@dataclass
class SchedulingConfig:
    """Scheduling configuration settings."""
    daily_execution_time: str
    timezone: str
    market_hours_start: str
    market_hours_end: str

@dataclass
class DashboardConfig:
    """Dashboard configuration settings."""
    host: str
    port: int
    debug: bool

@dataclass
class LoggingConfig:
    """Logging configuration settings."""
    level: str
    retention_days: int
    path: str
    
    @property
    def full_path(self) -> str:
        """Get absolute log path."""
        if os.path.isabs(self.path):
            return self.path
        return str(PROJECT_ROOT / self.path)

class Settings:
    """Main settings class that loads and validates all configuration."""
    
    def __init__(self):
        self.database = self._load_database_config()
        self.api = self._load_api_config()
        self.trading = self._load_trading_config()
        self.scheduling = self._load_scheduling_config()
        self.dashboard = self._load_dashboard_config()
        self.logging = self._load_logging_config()
        self.agents = self._load_agents_config()
        
        # Validate configuration
        self._validate_config()
    
    def _load_database_config(self) -> DatabaseConfig:
        """Load database configuration."""
        return DatabaseConfig(
            path=os.getenv('DATABASE_PATH', 'data/trading_automation.db'),
            backup_enabled=os.getenv('DATABASE_BACKUP_ENABLED', 'true').lower() == 'true',
            backup_retention_days=int(os.getenv('DATABASE_BACKUP_RETENTION_DAYS', '30'))
        )
    
    def _load_api_config(self) -> APIConfig:
        """Load API configuration."""
        return APIConfig(
            quiver_api_key=os.getenv('QUIVER_API_KEY', ''),
            alpaca_api_key=os.getenv('ALPACA_API_KEY', ''),
            alpaca_secret_key=os.getenv('ALPACA_SECRET_KEY', ''),
            alpaca_paper_trading=os.getenv('ALPACA_PAPER_TRADING', 'true').lower() == 'true',
            alpaca_base_url=os.getenv('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets'),
            rate_limit_per_minute=int(os.getenv('RATE_LIMIT_REQUESTS_PER_MINUTE', '60')),
            timeout_seconds=int(os.getenv('API_TIMEOUT_SECONDS', '30')),
            retry_max_attempts=int(os.getenv('RETRY_MAX_ATTEMPTS', '3')),
            retry_backoff_factor=float(os.getenv('RETRY_BACKOFF_FACTOR', '2.0'))
        )
    
    def _load_trading_config(self) -> TradingConfig:
        """Load trading configuration."""
        return TradingConfig(
            minimum_amount=float(os.getenv('TRADE_MINIMUM_AMOUNT', '100.0')),
            size_type=os.getenv('TRADE_SIZE_TYPE', 'fixed'),
            politician_match_threshold=float(os.getenv('POLITICIAN_MATCH_THRESHOLD', '0.85')),
            minimum_congress_trade_value=float(os.getenv('MINIMUM_CONGRESS_TRADE_VALUE', '50000'))
        )
    
    def _load_scheduling_config(self) -> SchedulingConfig:
        """Load scheduling configuration."""
        return SchedulingConfig(
            daily_execution_time=os.getenv('DAILY_EXECUTION_TIME', '21:30'),  # DEPRECATED: Use 'start' command for market hours execution
            timezone=os.getenv('TIMEZONE', 'US/Eastern'),
            market_hours_start=os.getenv('MARKET_HOURS_START', '09:30'),
            market_hours_end=os.getenv('MARKET_HOURS_END', '16:00')
        )
    
    def _load_dashboard_config(self) -> DashboardConfig:
        """Load dashboard configuration."""
        return DashboardConfig(
            host=os.getenv('DASHBOARD_HOST', '0.0.0.0'),
            port=int(os.getenv('DASHBOARD_PORT', '5000')),
            debug=os.getenv('DASHBOARD_DEBUG', 'false').lower() == 'true'
        )
    
    def _load_logging_config(self) -> LoggingConfig:
        """Load logging configuration."""
        return LoggingConfig(
            level=os.getenv('LOG_LEVEL', 'INFO'),
            retention_days=int(os.getenv('LOG_RETENTION_DAYS', '30')),
            path=os.getenv('LOG_PATH', 'logs')
        )
    
    def _load_agents_config(self) -> Dict[str, Any]:
        """Load agent definitions from config file."""
        agents_config_path = PROJECT_ROOT / 'config' / 'agents.json'
        
        if not agents_config_path.exists():
            # Return default configuration if file doesn't exist
            return self._get_default_agents_config()
        
        try:
            with open(agents_config_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            raise ValueError(f"Failed to load agents configuration: {e}")
    
    def _get_default_agents_config(self) -> Dict[str, Any]:
        """Get default agent configuration."""
        return {
            "agents": [
                {
                    "id": "transportation_committee",
                    "name": "Transportation & Infrastructure Committee Agent",
                    "type": "committee",
                    "politicians": [
                        "Peter DeFazio",
                        "Sam Graves", 
                        "Eleanor Holmes Norton",
                        "Rick Larsen",
                        "Garret Graves"
                    ],
                    "enabled": True
                },
                {
                    "id": "josh_gottheimer",
                    "name": "Josh Gottheimer Agent",
                    "type": "individual",
                    "politicians": ["Josh Gottheimer"],
                    "enabled": True
                },
                {
                    "id": "sheldon_whitehouse",
                    "name": "Sheldon Whitehouse Agent",
                    "type": "individual", 
                    "politicians": ["Sheldon Whitehouse"],
                    "enabled": True
                },
                {
                    "id": "nancy_pelosi",
                    "name": "Nancy Pelosi Agent",
                    "type": "individual",
                    "politicians": ["Nancy Pelosi"],
                    "enabled": True
                },
                {
                    "id": "dan_meuser",
                    "name": "Dan Meuser Agent", 
                    "type": "individual",
                    "politicians": ["Dan Meuser"],
                    "enabled": True
                }
            ]
        }
    
    def _validate_config(self) -> None:
        """Validate configuration settings."""
        errors = []
        
        # Validate required API keys
        if not self.api.quiver_api_key:
            errors.append("QUIVER_API_KEY is required")
        if not self.api.alpaca_api_key:
            errors.append("ALPACA_API_KEY is required")
        if not self.api.alpaca_secret_key:
            errors.append("ALPACA_SECRET_KEY is required")
        
        # Validate trading parameters
        if self.trading.minimum_amount <= 0:
            errors.append("TRADE_MINIMUM_AMOUNT must be positive")
        if not 0 < self.trading.politician_match_threshold <= 1:
            errors.append("POLITICIAN_MATCH_THRESHOLD must be between 0 and 1")
        
        # Validate agents configuration
        if not self.agents.get('agents'):
            errors.append("No agents configured")
        
        if errors:
            raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")
    
    def get_agent_by_id(self, agent_id: str) -> Dict[str, Any]:
        """Get agent configuration by ID."""
        for agent in self.agents['agents']:
            if agent['id'] == agent_id:
                return agent
        raise ValueError(f"Agent '{agent_id}' not found in configuration")
    
    def get_enabled_agents(self) -> List[Dict[str, Any]]:
        """Get list of enabled agents."""
        return [agent for agent in self.agents['agents'] if agent.get('enabled', True)]
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return os.getenv('ENVIRONMENT', 'development').lower() == 'development'
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return os.getenv('ENVIRONMENT', 'development').lower() == 'production'

# Global settings instance
settings = Settings()