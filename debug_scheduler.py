#!/usr/bin/env python3
"""
Debug scheduler startup to identify Railway deployment issues.
"""
import sys
import os
import traceback
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

def test_scheduler_startup():
    """Test scheduler startup components step by step."""
    print("🔍 DEBUG: Testing scheduler startup components...")
    
    try:
        print("Step 1: Testing basic imports...")
        from src.utils.logging import get_logger
        print("✅ Logging import successful")
        
        from config.settings import settings
        print("✅ Settings import successful")
        
        print("Step 2: Testing database connection...")
        from src.data.database import DatabaseManager
        db = DatabaseManager()
        print("✅ Database manager created")
        
        print("Step 3: Testing agent factory...")
        from src.agents.agent_factory import agent_factory
        print("✅ Agent factory import successful")
        
        print("Step 4: Testing scheduler import...")
        from src.scheduler.daily_runner import DailyRunner
        print("✅ Daily runner import successful")
        
        print("Step 5: Testing scheduler initialization...")
        runner = DailyRunner()
        print("✅ Daily runner created successfully")
        
        print("Step 6: Testing scheduler mode...")
        print(f"Execution time: {settings.scheduling.daily_execution_time}")
        print(f"Timezone: {settings.scheduling.timezone}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in scheduler startup: {e}")
        traceback.print_exc()
        return False

def test_environment_variables():
    """Check critical environment variables."""
    print("\n🔍 DEBUG: Checking environment variables...")
    
    required_vars = [
        'ALPACA_API_KEY',
        'ALPACA_SECRET_KEY', 
        'QUIVER_API_KEY',
        'ALPACA_PAPER'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
            print(f"❌ Missing: {var}")
        else:
            # Don't print actual values, just confirm they exist
            print(f"✅ Found: {var}")
    
    if missing_vars:
        print(f"\n❌ Missing environment variables: {missing_vars}")
        return False
    
    print("✅ All required environment variables present")
    return True

if __name__ == '__main__':
    print("🚀 Scheduler Debug Tool")
    print("=" * 50)
    
    # Test environment first
    env_ok = test_environment_variables()
    
    # Test scheduler components
    scheduler_ok = test_scheduler_startup()
    
    print("\n" + "=" * 50)
    if env_ok and scheduler_ok:
        print("✅ All tests passed - scheduler should work")
        
        # Try actually running scheduler command
        print("\n🔍 Testing actual scheduler command...")
        try:
            os.system("python3 main.py scheduler --help")
        except Exception as e:
            print(f"❌ Scheduler command failed: {e}")
    else:
        print("❌ Tests failed - scheduler will not work")
        if not env_ok:
            print("  - Fix environment variables")
        if not scheduler_ok:
            print("  - Fix scheduler startup issues")
    
    sys.exit(0 if (env_ok and scheduler_ok) else 1)