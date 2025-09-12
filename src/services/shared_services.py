"""
Shared Services Singleton for API Clients.
Provides shared instances of API clients to prevent duplication and resource waste.
"""
from typing import Optional
import threading

from src.data.database import DatabaseManager
from src.data.alpaca_client import AlpacaClient
from src.data.quiver_client import QuiverClient
from src.data.market_data_service import MarketDataService
from src.utils.logging import get_logger

logger = get_logger(__name__)

class SharedServices:
    """
    Singleton class providing shared instances of API clients and services.
    
    This ensures that all agents share the same client instances rather than
    creating duplicate connections and using excess resources.
    """
    
    _instance: Optional['SharedServices'] = None
    _lock = threading.RLock()
    
    def __new__(cls) -> 'SharedServices':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize shared services only once."""
        if self._initialized:
            return
            
        with self._lock:
            if self._initialized:
                return
                
            logger.info("Initializing shared services singleton")
            
            # Initialize all shared services
            self._db = DatabaseManager()
            self._alpaca_client = AlpacaClient()
            self._quiver_client = QuiverClient()
            self._market_data_service = MarketDataService()
            
            self._initialized = True
            logger.info("Shared services initialized successfully")
    
    @property
    def db(self) -> DatabaseManager:
        """Get shared database manager."""
        return self._db
    
    @property
    def alpaca_client(self) -> AlpacaClient:
        """Get shared Alpaca client."""
        return self._alpaca_client
    
    @property
    def quiver_client(self) -> QuiverClient:
        """Get shared Quiver client."""
        return self._quiver_client
    
    @property
    def market_data_service(self) -> MarketDataService:
        """Get shared market data service."""
        return self._market_data_service
    
    def health_check(self) -> bool:
        """Check health of all shared services."""
        try:
            # Basic connectivity checks
            self._db.get_connection()  # Test database connection
            # Could add more health checks here for other services
            return True
        except Exception as e:
            logger.error(f"Shared services health check failed: {e}")
            return False

# Global singleton instance
shared_services = SharedServices()