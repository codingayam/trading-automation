#!/usr/bin/env python3
"""
Railway-specific scheduler entry point with better error handling.
"""
import sys
import os
import traceback
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

def check_environment():
    """Check if all required environment variables are available."""
    required_vars = {
        'ALPACA_API_KEY': 'Alpaca trading API key',
        'ALPACA_SECRET_KEY': 'Alpaca trading secret key', 
        'QUIVER_API_KEY': 'Quiver congressional data API key',
        'ALPACA_PAPER': 'Alpaca paper trading mode (true/false)'
    }
    
    missing = []
    for var, desc in required_vars.items():
        if not os.getenv(var):
            missing.append(f"{var} ({desc})")
    
    if missing:
        print("❌ SCHEDULER STARTUP FAILED")
        print("Missing required environment variables:")
        for var in missing:
            print(f"  - {var}")
        print("\nPlease configure these variables in Railway dashboard:")
        print("https://railway.app -> Project -> Variables")
        return False
    
    return True

def main():
    """Main scheduler entry point with error handling."""
    print("🚀 Railway Trading Automation Scheduler")
    print("=" * 50)
    
    try:
        # Check environment first
        if not check_environment():
            print("\n⏱️  Scheduler will retry in 60 seconds...")
            import time
            time.sleep(60)
            return 1
        
        print("✅ Environment variables configured")
        
        # Import and run the main scheduler
        from main import main as main_scheduler
        
        # Run scheduler command
        sys.argv = ['main.py', 'scheduler']
        return main_scheduler()
        
    except Exception as e:
        print(f"❌ Scheduler crashed: {e}")
        traceback.print_exc()
        print("\n⏱️  Retrying in 60 seconds...")
        import time
        time.sleep(60)
        return 1

if __name__ == '__main__':
    sys.exit(main())