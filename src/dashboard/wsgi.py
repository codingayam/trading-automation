"""
WSGI entry point for production deployment.
This file is used by WSGI servers like Gunicorn or uWSGI.
"""
import sys
import os
from pathlib import Path

# Add src to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.settings import settings
from src.data.database import initialize_database
from src.dashboard.api import create_app
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Initialize database on startup
logger.info("Initializing database for WSGI application...")
if not initialize_database():
    logger.error("Database initialization failed")
    raise RuntimeError("Database initialization failed")

# Create application
application = create_app()

# Configure for production
application.config.update(
    SECRET_KEY=os.getenv('FLASK_SECRET_KEY', 'production-secret-key-change-me'),
    DEBUG=False,
    TESTING=False
)

logger.info("WSGI application initialized successfully")

if __name__ == "__main__":
    # For testing WSGI directly
    application.run()