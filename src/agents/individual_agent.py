"""
Individual Politician Agent Implementation.
Tracks trades by specific individual politicians using fuzzy name matching.
"""
from typing import Dict, List, Any, Optional
from difflib import SequenceMatcher

from src.agents.base_agent import BaseAgent
from src.data.quiver_client import CongressionalTrade
from src.utils.logging import get_logger

logger = get_logger(__name__)

class IndividualAgent(BaseAgent):
    """
    Agent that tracks trades by individual politicians.
    
    Features:
    - Fuzzy name matching with configurable threshold
    - Single politician tracking per agent
    - Politician-specific logging and identification
    - Individual performance tracking
    """
    
    def __init__(self, agent_id: str, config: dict):
        """
        Initialize individual politician agent.
        
        Args:
            agent_id: Unique agent identifier
            config: Agent configuration from agents.json
        """
        super().__init__(agent_id, config)
        
        # Validate that this is an individual agent
        if config.get('type') != 'individual':
            raise ValueError(f"IndividualAgent requires type='individual', got '{config.get('type')}'")
        
        if len(self.politicians) != 1:
            raise ValueError(f"IndividualAgent must track exactly one politician, got {len(self.politicians)}")
        
        self.target_politician = self.politicians[0]
        
        logger.info(f"Initialized individual agent {agent_id} tracking: {self.target_politician}")
    
    def _matches_tracked_politicians(self, trade: CongressionalTrade) -> bool:
        """
        Check if a trade matches the tracked politician using fuzzy matching.
        
        Args:
            trade: Congressional trade to check
            
        Returns:
            True if trade matches the tracked politician
        """
        if not trade.politician:
            return False
        
        # Normalize names for comparison
        trade_politician = self._normalize_politician_name(trade.politician)
        target_politician = self._normalize_politician_name(self.target_politician)
        
        # Calculate similarity using sequence matcher
        similarity = self._calculate_name_similarity(trade_politician, target_politician)
        
        is_match = similarity >= self.match_threshold
        
        if is_match:
            logger.info(f"Politician match found: '{trade.politician}' matches '{self.target_politician}' (similarity: {similarity:.3f})")
        else:
            logger.debug(f"No match: '{trade.politician}' vs '{self.target_politician}' (similarity: {similarity:.3f})")
        
        return is_match
    
    def _normalize_politician_name(self, name: str) -> str:
        """
        Normalize politician name for comparison.
        
        Args:
            name: Original politician name
            
        Returns:
            Normalized name for comparison
        """
        if not name:
            return ""
        
        # Convert to lowercase and remove extra whitespace
        normalized = name.lower().strip()
        
        # Remove common title prefixes
        titles = ['rep.', 'sen.', 'representative', 'senator', 'mr.', 'mrs.', 'ms.', 'dr.']
        for title in titles:
            if normalized.startswith(title + ' '):
                normalized = normalized[len(title) + 1:]
                break
        
        # Remove suffixes like Jr., Sr., III, etc.
        suffixes = [' jr.', ' sr.', ' jr', ' sr', ' iii', ' ii', ' iv']
        for suffix in suffixes:
            if normalized.endswith(suffix):
                normalized = normalized[:-len(suffix)]
                break
        
        # Handle common nickname patterns
        # Example: "Josh Gottheimer" should match "Joshua Gottheimer"
        name_mappings = {
            'josh': 'joshua',
            'bob': 'robert',
            'bill': 'william',
            'mike': 'michael',
            'dave': 'david',
            'steve': 'steven',
            'tom': 'thomas',
            'dan': 'daniel',
            'jim': 'james',
            'joe': 'joseph'
        }
        
        # Split name and check for nickname mappings
        parts = normalized.split()
        if parts:
            first_name = parts[0]
            if first_name in name_mappings:
                parts[0] = name_mappings[first_name]
            elif first_name in name_mappings.values():
                # Also check reverse mapping
                reverse_mapping = {v: k for k, v in name_mappings.items()}
                if first_name in reverse_mapping:
                    # Keep both forms for comparison
                    pass
        
        return ' '.join(parts).strip()
    
    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """
        Calculate similarity between two politician names.
        
        Args:
            name1: First name to compare
            name2: Second name to compare
            
        Returns:
            Similarity ratio between 0.0 and 1.0
        """
        if not name1 or not name2:
            return 0.0
        
        # Use SequenceMatcher for basic similarity
        basic_similarity = SequenceMatcher(None, name1, name2).ratio()
        
        # Also check word-level similarity for names with different word orders
        words1 = set(name1.split())
        words2 = set(name2.split())
        
        if words1 and words2:
            # Calculate Jaccard similarity for word sets
            intersection = words1.intersection(words2)
            union = words1.union(words2)
            word_similarity = len(intersection) / len(union) if union else 0.0
            
            # Take the higher of the two similarities
            return max(basic_similarity, word_similarity)
        
        return basic_similarity
    
    def get_politician_info(self) -> Dict[str, Any]:
        """
        Get information about the tracked politician.
        
        Returns:
            Dictionary with politician information
        """
        return {
            'politician_name': self.target_politician,
            'normalized_name': self._normalize_politician_name(self.target_politician),
            'match_threshold': self.match_threshold,
            'agent_type': 'individual'
        }
    
    def get_matching_trades_stats(self, trades: List[CongressionalTrade]) -> Dict[str, Any]:
        """
        Get statistics about matching trades.
        
        Args:
            trades: List of congressional trades to analyze
            
        Returns:
            Statistics about matching trades
        """
        matching_trades = [trade for trade in trades if self._matches_tracked_politicians(trade)]
        
        total_amount = sum(trade.amount for trade in matching_trades)
        purchase_count = sum(1 for trade in matching_trades if trade.transaction_type.lower() == 'purchase')
        sale_count = sum(1 for trade in matching_trades if trade.transaction_type.lower() == 'sale')
        
        unique_tickers = set(trade.ticker for trade in matching_trades)
        
        return {
            'total_trades': len(matching_trades),
            'purchase_count': purchase_count,
            'sale_count': sale_count,
            'total_amount': total_amount,
            'unique_tickers': len(unique_tickers),
            'tickers': list(unique_tickers),
            'politician': self.target_politician
        }

# Factory function to create individual agents from configuration
def create_individual_agents(agents_config: List[Dict[str, Any]]) -> List[IndividualAgent]:
    """
    Create individual agents from configuration.
    
    Args:
        agents_config: List of agent configurations
        
    Returns:
        List of created individual agents
    """
    individual_agents = []
    
    for config in agents_config:
        if config.get('type') == 'individual' and config.get('enabled', True):
            try:
                agent = IndividualAgent(config['id'], config)
                individual_agents.append(agent)
                logger.info(f"Created individual agent: {config['id']}")
            except Exception as e:
                logger.error(f"Failed to create individual agent {config.get('id', 'unknown')}: {e}")
    
    return individual_agents

# Specific agent implementations for each politician
class JoshGottheimerAgent(IndividualAgent):
    """Specialized agent for tracking Josh Gottheimer trades."""
    
    def __init__(self, agent_id: str, config: dict):
        # Ensure configuration is set up for Josh Gottheimer
        config['politicians'] = ['Josh Gottheimer']
        super().__init__(agent_id, config)

class SheldonWhitehouseAgent(IndividualAgent):
    """Specialized agent for tracking Sheldon Whitehouse trades."""
    
    def __init__(self, agent_id: str, config: dict):
        config['politicians'] = ['Sheldon Whitehouse']
        super().__init__(agent_id, config)

class NancyPelosiAgent(IndividualAgent):
    """Specialized agent for tracking Nancy Pelosi trades."""
    
    def __init__(self, agent_id: str, config: dict):
        config['politicians'] = ['Nancy Pelosi']
        super().__init__(agent_id, config)

class DanMeuserAgent(IndividualAgent):
    """Specialized agent for tracking Dan Meuser trades."""
    
    def __init__(self, agent_id: str, config: dict):
        config['politicians'] = ['Dan Meuser']
        super().__init__(agent_id, config)