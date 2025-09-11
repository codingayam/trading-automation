#!/usr/bin/env python3
"""
Railway Dashboard Server
Simple entry point for running the dashboard on Railway with PORT environment variable.
"""
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.dashboard.api import create_app
from src.data.database import initialize_database
from src.utils.logging import get_logger

logger = get_logger(__name__)

def main():
    """Run the dashboard for Railway deployment."""
    try:
        # Initialize database
        logger.info("Initializing database for Railway deployment...")
        if not initialize_database():
            logger.error("Database initialization failed")
            sys.exit(1)
        
        # Create Flask app
        app = create_app()
        
        # Get port from Railway environment
        port = int(os.environ.get('PORT', 5000))
        
        logger.info(f"Starting dashboard on port {port}")
        
        # Run the app
        app.run(
            host='0.0.0.0',
            port=port,
            debug=False,
            threaded=True
        )
        
    except Exception as e:
        logger.error(f"Failed to start dashboard: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()