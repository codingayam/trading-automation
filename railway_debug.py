#!/usr/bin/env python3
"""
Railway Debug Script
Check environment and dependencies before starting main services.
"""
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

def check_environment():
    """Check environment variables and system status."""
    print("🔍 Railway Environment Debug")
    print("=" * 50)
    
    # Check environment
    print(f"Environment: {os.environ.get('ENVIRONMENT', 'Not set')}")
    print(f"Port: {os.environ.get('PORT', 'Not set')}")
    print(f"Python version: {sys.version}")
    print(f"Working directory: {os.getcwd()}")
    
    # Check required environment variables
    required_vars = [
        'ALPACA_API_KEY',
        'ALPACA_SECRET_KEY',
        'QUIVER_API_KEY'
    ]
    
    print("\n📋 Environment Variables:")
    missing_vars = []
    for var in required_vars:
        value = os.environ.get(var)
        if value:
            print(f"✅ {var}: {'*' * (len(value) - 4) + value[-4:]}")
        else:
            print(f"❌ {var}: Not set")
            missing_vars.append(var)
    
    # Check optional variables
    optional_vars = [
        'DATABASE_URL',
        'LOG_LEVEL',
        'DAILY_EXECUTION_TIME'
    ]
    
    print("\n📋 Optional Variables:")
    for var in optional_vars:
        value = os.environ.get(var)
        if value:
            if 'DATABASE_URL' in var:
                print(f"✅ {var}: {value[:20]}...")
            else:
                print(f"✅ {var}: {value}")
        else:
            print(f"⚪ {var}: Not set (using default)")
    
    # Check if we can import our modules
    print("\n📦 Module Imports:")
    try:
        from config.settings import settings
        print("✅ Settings module imported")
        
        print(f"✅ Database path: {settings.database.full_path}")
        print(f"✅ Dashboard host: {settings.dashboard.host}:{settings.dashboard.port}")
        
    except Exception as e:
        print(f"❌ Settings import failed: {e}")
        return False
    
    try:
        from src.data.database import initialize_database
        print("✅ Database module imported")
        
        # Try to initialize database
        if initialize_database():
            print("✅ Database initialized successfully")
        else:
            print("❌ Database initialization failed")
            
    except Exception as e:
        print(f"❌ Database import/init failed: {e}")
        return False
    
    try:
        from src.dashboard.api import create_app
        app = create_app()
        print("✅ Dashboard app created successfully")
        
    except Exception as e:
        print(f"❌ Dashboard creation failed: {e}")
        return False
    
    # Check if we have missing required variables
    if missing_vars:
        print(f"\n❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("⚠️  Set these in Railway dashboard under Variables tab")
        return False
    
    print("\n✅ All checks passed! System should be able to start.")
    return True

def main():
    """Main diagnostic function."""
    try:
        if check_environment():
            print("\n🚀 Environment is ready for deployment!")
            
            # If all checks pass, try to start just the dashboard
            port = int(os.environ.get('PORT', 5000))
            print(f"\n🌐 Starting diagnostic dashboard on port {port}")
            
            from src.dashboard.api import create_app
            app = create_app()
            
            app.run(
                host='0.0.0.0',
                port=port,
                debug=False
            )
        else:
            print("\n❌ Environment issues detected. Fix these before deployment.")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()