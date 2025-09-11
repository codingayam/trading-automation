#!/usr/bin/env python3
"""
Simple Railway test to check what's actually failing.
"""
import sys
import os
import traceback
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

def main():
    """Test basic functionality that might be failing on Railway."""
    print("🔍 RAILWAY TEST - Basic Component Check")
    print("=" * 50)
    
    # Test 1: Environment variables
    print("1. Testing environment variables...")
    required_vars = ['ALPACA_API_KEY', 'ALPACA_SECRET_KEY', 'QUIVER_API_KEY', 'ALPACA_PAPER']
    for var in required_vars:
        if os.getenv(var):
            print(f"✅ {var}: configured")
        else:
            print(f"❌ {var}: missing")
    
    # Test 2: Basic imports
    print("\n2. Testing basic imports...")
    try:
        import sqlite3
        print("✅ sqlite3: available")
    except Exception as e:
        print(f"❌ sqlite3: {e}")
        
    try:
        from pathlib import Path
        print("✅ pathlib: available")
    except Exception as e:
        print(f"❌ pathlib: {e}")
    
    # Test 3: Settings loading
    print("\n3. Testing settings...")
    try:
        from config.settings import settings
        print(f"✅ settings: loaded")
        print(f"   - Database path: {settings.database.path}")
        print(f"   - Execution time: {settings.scheduling.daily_execution_time}")
    except Exception as e:
        print(f"❌ settings: {e}")
        traceback.print_exc()
        return 1
    
    # Test 4: Database
    print("\n4. Testing database...")
    try:
        from src.data.database import DatabaseManager
        db = DatabaseManager()
        print(f"✅ database: connected")
        print(f"   - Database path: {db.db_path}")
    except Exception as e:
        print(f"❌ database: {e}")
        traceback.print_exc()
        return 1
        
    # Test 5: Port binding (common Railway issue)
    print("\n5. Testing port availability...")
    port = os.getenv('PORT', '8080')
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('0.0.0.0', int(port)))
        sock.close()
        print(f"✅ port {port}: available")
    except Exception as e:
        print(f"❌ port {port}: {e}")
        
    # Test 6: Health server import
    print("\n6. Testing health server...")
    try:
        from src.utils.health import health_server
        print("✅ health_server: imported")
    except Exception as e:
        print(f"❌ health_server: {e}")
        traceback.print_exc()
        return 1
        
    print("\n" + "=" * 50)
    print("✅ Basic tests completed")
    return 0

if __name__ == '__main__':
    sys.exit(main())