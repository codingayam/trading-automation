#!/usr/bin/env python3
"""
Initialize agents for Railway deployment.
Load agent configurations into the database so they appear on the dashboard.
"""
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.agents.agent_factory import agent_factory
from src.data.database import initialize_database
from src.utils.logging import get_logger

logger = get_logger(__name__)

def main():
    """Initialize agents in the database."""
    try:
        print("🔧 Initializing Trading Automation Agents")
        print("=" * 50)
        
        # Initialize database
        logger.info("Initializing database...")
        if not initialize_database():
            logger.error("Database initialization failed")
            print("❌ Database initialization failed")
            return False
        
        print("✅ Database initialized")
        
        # Create and register agents
        logger.info("Creating and registering agents...")
        agents = agent_factory.create_agents_from_config()
        
        print(f"✅ {len(agents)} agents loaded:")
        for agent in agents:
            agent_type = getattr(agent, 'type', 'unknown')
            politicians = getattr(agent, 'politicians', [])
            print(f"   - {agent.agent_id} ({agent_type})")
            if politicians:
                print(f"     Politicians: {', '.join(politicians[:3])}{'...' if len(politicians) > 3 else ''}")
        
        # Get factory status
        status = agent_factory.get_factory_status()
        print(f"\n📊 Agent Factory Status:")
        print(f"   - Registered: {status['registered_agents']}")
        print(f"   - Active: {status['active_agents']}")
        print(f"   - Enabled: {status['enabled_agents']}")
        
        print(f"\n🎉 Agents initialized successfully!")
        print(f"🌐 Your dashboard should now show {len(agents)} agents")
        print(f"📱 Refresh your dashboard at: https://trading-automation-production.up.railway.app/")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize agents: {e}")
        print(f"❌ Error: {e}")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)