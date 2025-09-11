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
        
        # Store agents in database for dashboard
        logger.info("Storing agent data in database...")
        from src.data.database import DatabaseManager
        db = DatabaseManager()
        
        with db.transaction() as conn:
            cursor = conn.cursor()
            
            # Create agents table if not exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agents (
                    id VARCHAR(50) PRIMARY KEY,
                    name VARCHAR(200) NOT NULL,
                    type VARCHAR(50) NOT NULL,
                    description TEXT,
                    politicians TEXT,
                    enabled BOOLEAN DEFAULT TRUE,
                    parameters TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Insert agent data
            for agent in agents:
                politicians_str = ', '.join(getattr(agent, 'politicians', []))
                agent_type = getattr(agent, 'type', 'unknown')
                config = agent_factory.agent_configs.get(agent.agent_id, {})
                
                cursor.execute("""
                    INSERT OR REPLACE INTO agents 
                    (id, name, type, description, politicians, enabled, parameters)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    agent.agent_id,
                    config.get('name', agent.agent_id),
                    agent_type,
                    config.get('description', ''),
                    politicians_str,
                    config.get('enabled', True),
                    str(config.get('parameters', {}))
                ))
            
        print(f"✅ Agent data stored in database")
        
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