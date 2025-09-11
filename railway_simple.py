#!/usr/bin/env python3
"""
Simple Railway deployment - Dashboard only for now
This runs just the dashboard without the scheduler until PostgreSQL is configured.
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
    """Run just the dashboard for Railway deployment."""
    try:
        print("🚀 Starting Railway deployment (Dashboard only)")
        
        # Initialize database (SQLite for now)
        logger.info("Initializing database...")
        if not initialize_database():
            logger.error("Database initialization failed")
            print("❌ Database initialization failed")
            # Don't exit - try to continue with dashboard
        else:
            print("✅ Database initialized")
        
        # Create Flask app
        app = create_app()
        
        # Get port from Railway environment
        port = int(os.environ.get('PORT', 5000))
        
        print(f"🌐 Starting dashboard on port {port}")
        print(f"📊 Dashboard will be available at: https://your-app.up.railway.app")
        print(f"🔧 Next step: Add PostgreSQL database in Railway dashboard")
        
        # Run the app
        app.run(
            host='0.0.0.0',
            port=port,
            debug=False,
            threaded=True
        )
        
    except Exception as e:
        logger.error(f"Failed to start dashboard: {e}")
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()