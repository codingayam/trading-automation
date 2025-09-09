#!/usr/bin/env python3
"""
Dashboard Development Server
Runs the Flask dashboard application for development and testing.
"""
import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config.settings import settings
from src.data.database import initialize_database
from src.dashboard.api import create_app
from src.utils.logging import get_logger

logger = get_logger(__name__)

def main():
    """Run the dashboard development server."""
    print("=" * 60)
    print("TRADING AUTOMATION DASHBOARD")
    print("=" * 60)
    
    # Initialize database
    logger.info("Initializing database...")
    if not initialize_database():
        logger.error("Database initialization failed")
        print("❌ Database initialization failed")
        return False
    
    print("✅ Database initialized")
    
    # Create Flask app
    app = create_app()
    
    print(f"\n🚀 Starting dashboard server...")
    print(f"   Host: {settings.dashboard.host}")
    print(f"   Port: {settings.dashboard.port}")
    print(f"   Debug: {settings.dashboard.debug}")
    print(f"   URL: http://{settings.dashboard.host}:{settings.dashboard.port}")
    print("\n📊 Available endpoints:")
    print("   GET  /                         - Overview dashboard")
    print("   GET  /agent/<agent_id>         - Individual agent dashboard")
    print("   GET  /api/health               - Health check")
    print("   GET  /api/system/status        - System status")
    print("   GET  /api/agents               - List all agents")
    print("   GET  /api/agents/<agent_id>    - Agent details")
    print("   GET  /api/agents/<agent_id>/positions - Agent positions")
    print("   GET  /api/agents/<agent_id>/performance - Agent performance")
    
    if settings.dashboard.debug:
        print("   POST /api/cache/clear         - Clear cache (development only)")
        print("   GET  /api/cache/stats         - Cache statistics")
    
    print(f"\n📝 Logs will be written to: {settings.logging.full_path}")
    print("\nPress Ctrl+C to stop the server")
    print("=" * 60)
    
    try:
        app.run(
            host=settings.dashboard.host,
            port=settings.dashboard.port,
            debug=settings.dashboard.debug,
            use_reloader=settings.dashboard.debug,
            threaded=True
        )
    except KeyboardInterrupt:
        print("\n\n👋 Dashboard server stopped")
        return True
    except Exception as e:
        logger.error(f"Failed to start dashboard server: {e}")
        print(f"\n❌ Failed to start dashboard server: {e}")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)