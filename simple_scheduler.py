#!/usr/bin/env python3
"""
Ultra-simple scheduler for Railway that just stays running.
"""
import sys
import time
import os
import traceback
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

def main():
    """Simple scheduler that just runs and logs status."""
    print("🚀 Simple Railway Scheduler Starting")
    print("=" * 50)
    
    # Check environment variables
    required_vars = ['ALPACA_API_KEY', 'ALPACA_SECRET_KEY', 'QUIVER_API_KEY', 'ALPACA_PAPER']
    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        print(f"❌ Missing environment variables: {missing}")
        print("Scheduler cannot start without API credentials.")
        # Don't exit immediately, wait and retry
        time.sleep(60)
        return main()  # Retry
    
    print("✅ All environment variables configured")
    
    try:
        # Import what we need
        from src.utils.logging import get_logger
        from config.settings import settings
        
        logger = get_logger(__name__)
        print("✅ Basic imports successful")
        
        print(f"🕐 Execution time: {settings.scheduling.daily_execution_time}")
        print(f"🌍 Timezone: {settings.scheduling.timezone}")
        
        # Just run a simple loop that stays alive
        counter = 0
        while True:
            counter += 1
            current_time = time.strftime("%H:%M:%S")
            
            if counter % 60 == 0:  # Log every 60 iterations (60 minutes)
                print(f"⏰ Scheduler alive at {current_time} (iteration {counter})")
                logger.info(f"Scheduler heartbeat: {counter} iterations")
            
            # Check if it's time to execute (9:30 PM = 21:30)
            if current_time.startswith("21:30"):
                print(f"🎯 Execution time reached: {current_time}")
                logger.info("Daily execution time reached")
                # TODO: Add actual trading logic here later
                print("📊 Trading workflow would execute here")
                # Sleep for 2 minutes to avoid re-triggering
                time.sleep(120)
            
            # Sleep for 1 minute
            time.sleep(60)
            
    except KeyboardInterrupt:
        print("✅ Scheduler stopped by interrupt")
        return 0
    except Exception as e:
        print(f"❌ Scheduler error: {e}")
        traceback.print_exc()
        print("⏱️ Retrying in 60 seconds...")
        time.sleep(60)
        return 1

if __name__ == '__main__':
    sys.exit(main())