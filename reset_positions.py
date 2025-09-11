#!/usr/bin/env python3
"""
Reset all agent positions to 0 for fresh start on Railway deployment.
This script clears all position data while preserving historical trade records.
"""
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.data.database import DatabaseManager
from src.utils.logging import get_logger

logger = get_logger(__name__)

def reset_all_positions():
    """Reset all agent positions to 0."""
    db = DatabaseManager()
    
    try:
        with db.transaction() as conn:
            cursor = conn.cursor()
            
            # Clear all positions
            cursor.execute("DELETE FROM agent_positions")
            positions_deleted = cursor.rowcount
            
            # Reset daily performance for fresh start
            cursor.execute("DELETE FROM daily_performance")
            performance_deleted = cursor.rowcount
            
            # Keep trade history but optionally clear it too
            # Uncomment the next lines if you want to clear trade history as well
            # cursor.execute("DELETE FROM trades")
            # trades_deleted = cursor.rowcount
            
            logger.info(f"Reset complete: {positions_deleted} positions, {performance_deleted} performance records deleted")
            print(f"✅ Successfully reset:")
            print(f"   - {positions_deleted} agent positions cleared")
            print(f"   - {performance_deleted} performance records cleared")
            print(f"   - Trade history preserved")
            print(f"\n🚀 System ready for fresh start on Railway!")
            
            return True
            
    except Exception as e:
        logger.error(f"Failed to reset positions: {e}")
        print(f"❌ Failed to reset positions: {e}")
        return False

def main():
    """Main entry point."""
    print("=" * 60)
    print("TRADING AUTOMATION - POSITION RESET")
    print("=" * 60)
    print("This will reset all agent positions to 0 for a fresh start.")
    print("Trade history will be preserved.")
    print("=" * 60)
    
    # Confirm action
    response = input("Are you sure you want to reset all positions? (y/N): ")
    if response.lower() != 'y':
        print("❌ Reset cancelled")
        return False
    
    print("\n🔄 Resetting positions...")
    success = reset_all_positions()
    
    if success:
        print("\n✅ Position reset completed successfully!")
        print("You can now deploy to Railway with a clean slate.")
    else:
        print("\n❌ Position reset failed!")
        return False
    
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)