"""
Agent Factory and Registration System.
Provides dynamic agent creation, registration, and lifecycle management.
"""
import time
from typing import Dict, List, Any, Optional, Type, Union
from datetime import datetime
from enum import Enum
from dataclasses import dataclass
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from config.settings import settings
from src.agents.base_agent import BaseAgent, AgentState, ExecutionResult
from src.agents.individual_agent import IndividualAgent, JoshGottheimerAgent, SheldonWhitehouseAgent, NancyPelosiAgent, DanMeuserAgent
from src.agents.committee_agent import CommitteeAgent, TransportationCommitteeAgent
from src.data.quiver_client import CongressionalTrade
from src.utils.logging import get_logger
from src.utils.exceptions import TradingError, ValidationError
from src.utils.monitoring import metrics_collector
from src.utils.health import HealthStatus

logger = get_logger(__name__)

class AgentType(Enum):
    """Available agent types."""
    INDIVIDUAL = "individual"
    COMMITTEE = "committee"

@dataclass
class AgentRegistration:
    """Agent registration information."""
    agent_id: str
    agent_class: Type[BaseAgent]
    config: Dict[str, Any]
    enabled: bool
    created_at: datetime
    last_health_check: Optional[datetime] = None
    health_status: str = "unknown"

@dataclass
class FactoryStats:
    """Factory statistics."""
    total_agents_created: int
    active_agents: int
    failed_agents: int
    total_executions: int
    last_execution_time: Optional[datetime]

class AgentFactory:
    """
    Factory for creating and managing trading agents.
    
    Features:
    - Dynamic agent creation from configuration
    - Agent registration and discovery system
    - Agent lifecycle management (start, stop, status)
    - Health checks and status monitoring
    - Configuration validation and error handling
    - Agent metrics collection and reporting
    - Support for adding new agents without code changes
    """
    
    def __init__(self):
        """Initialize the agent factory."""
        self._registered_agents: Dict[str, AgentRegistration] = {}
        self._active_agents: Dict[str, BaseAgent] = {}
        self._agent_types: Dict[str, Type[BaseAgent]] = {}
        self._lock = threading.RLock()
        
        # Factory statistics
        self.stats = FactoryStats(
            total_agents_created=0,
            active_agents=0,
            failed_agents=0,
            total_executions=0,
            last_execution_time=None
        )
        
        # Register built-in agent types
        self._register_built_in_types()
        
        logger.info("Initialized Agent Factory")
    
    def _register_built_in_types(self) -> None:
        """Register built-in agent types."""
        self._agent_types.update({
            'individual': IndividualAgent,
            'committee': CommitteeAgent,
            'josh_gottheimer': JoshGottheimerAgent,
            'sheldon_whitehouse': SheldonWhitehouseAgent,
            'nancy_pelosi': NancyPelosiAgent,
            'dan_meuser': DanMeuserAgent,
            'transportation_committee': TransportationCommitteeAgent
        })
        
        logger.debug(f"Registered {len(self._agent_types)} built-in agent types")
    
    def register_agent_type(self, type_name: str, agent_class: Type[BaseAgent]) -> None:
        """
        Register a new agent type.
        
        Args:
            type_name: Name of the agent type
            agent_class: Agent class implementation
        """
        if not issubclass(agent_class, BaseAgent):
            raise ValueError(f"Agent class must inherit from BaseAgent")
        
        with self._lock:
            self._agent_types[type_name] = agent_class
            logger.info(f"Registered agent type: {type_name}")
    
    def create_agent(self, agent_config: Dict[str, Any]) -> Optional[BaseAgent]:
        """
        Create an agent from configuration.
        
        Args:
            agent_config: Agent configuration dictionary
            
        Returns:
            Created agent instance or None if creation failed
        """
        agent_id = agent_config.get('id')
        if not agent_id:
            logger.error("Agent configuration missing 'id' field")
            return None
        
        try:
            # Validate configuration
            self._validate_agent_config(agent_config)
            
            # Determine agent type
            agent_type = agent_config.get('type', 'individual')
            
            # Use specific agent class if available, otherwise use generic class
            if agent_id in self._agent_types:
                agent_class = self._agent_types[agent_id]
            elif agent_type in self._agent_types:
                agent_class = self._agent_types[agent_type]
            else:
                logger.error(f"Unknown agent type: {agent_type}")
                return None
            
            # Create agent instance
            with self._lock:
                agent = agent_class(agent_id, agent_config)
                
                # Register the agent
                registration = AgentRegistration(
                    agent_id=agent_id,
                    agent_class=agent_class,
                    config=agent_config,
                    enabled=agent_config.get('enabled', True),
                    created_at=datetime.now()
                )
                
                self._registered_agents[agent_id] = registration
                
                if registration.enabled:
                    self._active_agents[agent_id] = agent
                    self.stats.active_agents += 1
                
                self.stats.total_agents_created += 1
                
                logger.info(f"Created agent: {agent_id} ({agent_class.__name__})")
                return agent
        
        except Exception as e:
            logger.error(f"Failed to create agent {agent_id}: {e}")
            self.stats.failed_agents += 1
            return None
    
    def _validate_agent_config(self, config: Dict[str, Any]) -> None:
        """
        Validate agent configuration.
        
        Args:
            config: Agent configuration to validate
        """
        required_fields = ['id', 'name', 'type', 'politicians']
        
        for field in required_fields:
            if field not in config:
                raise ValidationError(f"Missing required field: {field}")
        
        if not config['politicians']:
            raise ValidationError("Agent must track at least one politician")
        
        # Validate agent type
        valid_types = ['individual', 'committee']
        if config['type'] not in valid_types:
            raise ValidationError(f"Invalid agent type: {config['type']}")
        
        # Validate parameters
        parameters = config.get('parameters', {})
        if parameters:
            self._validate_agent_parameters(parameters)
    
    def _validate_agent_parameters(self, parameters: Dict[str, Any]) -> None:
        """Validate agent parameters."""
        numeric_validations = {
            'minimum_trade_value': (1000, 1000000),
            'position_size_value': (1, 10000),
            'match_threshold': (0.1, 1.0)
        }
        
        for param, (min_val, max_val) in numeric_validations.items():
            if param in parameters:
                value = parameters[param]
                if not isinstance(value, (int, float)) or not (min_val <= value <= max_val):
                    raise ValidationError(f"Parameter {param} must be between {min_val} and {max_val}")
    
    def create_agents_from_config(self) -> List[BaseAgent]:
        """
        Create all enabled agents from configuration.
        
        Returns:
            List of created agents
        """
        agents = []
        enabled_configs = settings.get_enabled_agents()
        
        logger.info(f"Creating {len(enabled_configs)} agents from configuration")
        
        for config in enabled_configs:
            agent = self.create_agent(config)
            if agent:
                agents.append(agent)
        
        logger.info(f"Successfully created {len(agents)} agents")
        return agents
    
    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """
        Get an active agent by ID.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Agent instance or None if not found
        """
        with self._lock:
            return self._active_agents.get(agent_id)
    
    def get_all_agents(self) -> List[BaseAgent]:
        """
        Get all active agents.
        
        Returns:
            List of active agents
        """
        with self._lock:
            return list(self._active_agents.values())
    
    def get_agent_registration(self, agent_id: str) -> Optional[AgentRegistration]:
        """
        Get agent registration information.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Agent registration or None if not found
        """
        with self._lock:
            return self._registered_agents.get(agent_id)
    
    def enable_agent(self, agent_id: str) -> bool:
        """
        Enable an agent.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            True if agent was enabled successfully
        """
        with self._lock:
            registration = self._registered_agents.get(agent_id)
            if not registration:
                logger.error(f"Agent {agent_id} not registered")
                return False
            
            if registration.enabled:
                logger.info(f"Agent {agent_id} already enabled")
                return True
            
            try:
                # Create agent instance if not already active
                if agent_id not in self._active_agents:
                    agent = registration.agent_class(agent_id, registration.config)
                    self._active_agents[agent_id] = agent
                    self.stats.active_agents += 1
                
                # Update registration
                registration.enabled = True
                
                # Enable the agent instance
                agent = self._active_agents[agent_id]
                agent.enable()
                
                logger.info(f"Enabled agent: {agent_id}")
                return True
            
            except Exception as e:
                logger.error(f"Failed to enable agent {agent_id}: {e}")
                return False
    
    def disable_agent(self, agent_id: str, reason: str = None) -> bool:
        """
        Disable an agent.
        
        Args:
            agent_id: Agent identifier
            reason: Reason for disabling
            
        Returns:
            True if agent was disabled successfully
        """
        with self._lock:
            registration = self._registered_agents.get(agent_id)
            if not registration:
                logger.error(f"Agent {agent_id} not registered")
                return False
            
            try:
                # Disable the agent instance
                if agent_id in self._active_agents:
                    agent = self._active_agents[agent_id]
                    agent.disable(reason)
                    
                    # Remove from active agents
                    del self._active_agents[agent_id]
                    self.stats.active_agents -= 1
                
                # Update registration
                registration.enabled = False
                
                logger.info(f"Disabled agent: {agent_id}" + (f" - {reason}" if reason else ""))
                return True
            
            except Exception as e:
                logger.error(f"Failed to disable agent {agent_id}: {e}")
                return False
    
    def remove_agent(self, agent_id: str) -> bool:
        """
        Remove an agent completely.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            True if agent was removed successfully
        """
        with self._lock:
            if agent_id not in self._registered_agents:
                logger.error(f"Agent {agent_id} not registered")
                return False
            
            try:
                # Disable first if active
                if agent_id in self._active_agents:
                    self.disable_agent(agent_id, "Agent removed")
                
                # Remove registration
                del self._registered_agents[agent_id]
                
                logger.info(f"Removed agent: {agent_id}")
                return True
            
            except Exception as e:
                logger.error(f"Failed to remove agent {agent_id}: {e}")
                return False
    
    def execute_all_agents(self, congressional_trades: List[CongressionalTrade], parallel: bool = True) -> Dict[str, ExecutionResult]:
        """
        Execute all active agents.
        
        Args:
            congressional_trades: List of congressional trades to process
            parallel: Whether to execute agents in parallel
            
        Returns:
            Dictionary of execution results by agent ID
        """
        start_time = time.time()
        logger.info(f"Executing {len(self._active_agents)} agents {'in parallel' if parallel else 'sequentially'}")
        
        results = {}
        
        if parallel and len(self._active_agents) > 1:
            results = self._execute_agents_parallel(congressional_trades)
        else:
            results = self._execute_agents_sequential(congressional_trades)
        
        execution_time = time.time() - start_time
        
        # Update statistics
        self.stats.total_executions += 1
        self.stats.last_execution_time = datetime.now()
        
        # Log summary
        successful_agents = sum(1 for result in results.values() if result.success)
        total_trades = sum(result.trades_processed for result in results.values())
        total_orders = sum(result.orders_placed for result in results.values())
        
        logger.info(f"Agent execution completed in {execution_time:.2f}s: {successful_agents}/{len(results)} agents successful, {total_trades} trades processed, {total_orders} orders placed")
        
        metrics_collector.record_execution_time("all_agents_execution", execution_time)
        
        return results
    
    def _execute_agents_parallel(self, congressional_trades: List[CongressionalTrade]) -> Dict[str, ExecutionResult]:
        """Execute agents in parallel."""
        results = {}
        max_workers = min(len(self._active_agents), 5)  # Limit concurrent agents
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all agent executions
            future_to_agent = {}
            
            with self._lock:
                agents_to_execute = list(self._active_agents.items())
            
            for agent_id, agent in agents_to_execute:
                if agent.is_enabled():
                    future = executor.submit(agent.execute_daily_workflow, congressional_trades)
                    future_to_agent[future] = agent_id
                else:
                    logger.info(f"Skipping disabled agent: {agent_id}")
            
            # Collect results as they complete
            for future in as_completed(future_to_agent):
                agent_id = future_to_agent[future]
                try:
                    result = future.result()
                    results[agent_id] = result
                    
                    if result.success:
                        logger.info(f"Agent {agent_id} completed successfully")
                    else:
                        logger.error(f"Agent {agent_id} failed: {'; '.join(result.errors)}")
                
                except Exception as e:
                    logger.error(f"Agent {agent_id} execution failed: {e}")
                    results[agent_id] = ExecutionResult(
                        success=False,
                        trades_processed=0,
                        orders_placed=0,
                        errors=[f"Execution failed: {e}"],
                        execution_time=0.0,
                        timestamp=datetime.now()
                    )
        
        return results
    
    def _execute_agents_sequential(self, congressional_trades: List[CongressionalTrade]) -> Dict[str, ExecutionResult]:
        """Execute agents sequentially."""
        results = {}
        
        with self._lock:
            agents_to_execute = list(self._active_agents.items())
        
        for agent_id, agent in agents_to_execute:
            if not agent.is_enabled():
                logger.info(f"Skipping disabled agent: {agent_id}")
                continue
            
            try:
                logger.info(f"Executing agent: {agent_id}")
                result = agent.execute_daily_workflow(congressional_trades)
                results[agent_id] = result
                
                if result.success:
                    logger.info(f"Agent {agent_id} completed successfully")
                else:
                    logger.error(f"Agent {agent_id} failed: {'; '.join(result.errors)}")
            
            except Exception as e:
                logger.error(f"Agent {agent_id} execution failed: {e}")
                results[agent_id] = ExecutionResult(
                    success=False,
                    trades_processed=0,
                    orders_placed=0,
                    errors=[f"Execution failed: {e}"],
                    execution_time=0.0,
                    timestamp=datetime.now()
                )
        
        return results
    
    def health_check_all_agents(self) -> Dict[str, HealthStatus]:
        """
        Perform health checks on all registered agents.
        
        Returns:
            Health status for each agent
        """
        health_results = {}
        
        with self._lock:
            for agent_id, registration in self._registered_agents.items():
                try:
                    if agent_id in self._active_agents:
                        agent = self._active_agents[agent_id]
                        
                        # Basic health checks
                        is_enabled = agent.is_enabled()
                        state = agent.state
                        
                        if is_enabled and state in [AgentState.INITIALIZED, AgentState.COMPLETED]:
                            health_status = HealthStatus.HEALTHY
                        elif state == AgentState.ERROR:
                            health_status = HealthStatus.UNHEALTHY
                        elif not is_enabled:
                            health_status = HealthStatus.DISABLED
                        else:
                            health_status = HealthStatus.DEGRADED
                        
                        health_results[agent_id] = health_status
                    else:
                        health_results[agent_id] = HealthStatus.DISABLED if not registration.enabled else HealthStatus.UNHEALTHY
                    
                    # Update registration with health check time
                    registration.last_health_check = datetime.now()
                    registration.health_status = health_results[agent_id].value
                
                except Exception as e:
                    logger.error(f"Health check failed for agent {agent_id}: {e}")
                    health_results[agent_id] = HealthStatus.UNHEALTHY
        
        return health_results
    
    def get_factory_status(self) -> Dict[str, Any]:
        """
        Get comprehensive factory status.
        
        Returns:
            Factory status information
        """
        with self._lock:
            registered_count = len(self._registered_agents)
            active_count = len(self._active_agents)
            enabled_count = sum(1 for reg in self._registered_agents.values() if reg.enabled)
        
        return {
            'registered_agents': registered_count,
            'active_agents': active_count,
            'enabled_agents': enabled_count,
            'available_types': list(self._agent_types.keys()),
            'statistics': {
                'total_created': self.stats.total_agents_created,
                'total_executions': self.stats.total_executions,
                'last_execution': self.stats.last_execution_time.isoformat() if self.stats.last_execution_time else None,
                'failed_agents': self.stats.failed_agents
            },
            'agents': {
                agent_id: {
                    'enabled': reg.enabled,
                    'type': reg.config.get('type'),
                    'created_at': reg.created_at.isoformat(),
                    'last_health_check': reg.last_health_check.isoformat() if reg.last_health_check else None,
                    'health_status': reg.health_status,
                    'active': agent_id in self._active_agents
                }
                for agent_id, reg in self._registered_agents.items()
            }
        }

# Global factory instance
agent_factory = AgentFactory()