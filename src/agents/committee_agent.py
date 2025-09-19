"""
Committee Agent Implementation.
Tracks trades by multiple politicians who are members of a committee.
"""
from typing import Dict, List, Any, Optional, Set
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path
import json

from src.agents.base_agent import BaseAgent
from src.data.quiver_client import CongressionalTrade
from src.utils.logging import get_logger
from config.settings import PROJECT_ROOT

logger = get_logger(__name__)

class CommitteeAgent(BaseAgent):
    """
    Agent that tracks trades by committee members.
    
    Features:
    - Multiple politician tracking with fuzzy matching
    - Committee member list management
    - Committee-specific performance aggregation
    - Handles multiple politicians in single trade decisions
    """
    
    def __init__(self, agent_id: str, config: dict):
        """
        Initialize committee agent.
        
        Args:
            agent_id: Unique agent identifier
            config: Agent configuration from agents.json
        """
        super().__init__(agent_id, config)
        
        # Validate that this is a committee agent
        if config.get('type') != 'committee':
            raise ValueError(f"CommitteeAgent requires type='committee', got '{config.get('type')}'")
        
        if len(self.politicians) < 2:
            raise ValueError(f"CommitteeAgent must track at least 2 politicians, got {len(self.politicians)}")
        
        # Normalize politician names for faster matching
        self.normalized_politicians = {
            self._normalize_politician_name(politician): politician 
            for politician in self.politicians
        }
        
        self.committee_name = config.get('name', 'Unknown Committee')
        
        logger.info(f"Initialized committee agent {agent_id} tracking {len(self.politicians)} politicians")
        logger.debug(f"Committee members: {', '.join(self.politicians)}")
    
    def _matches_tracked_politicians(self, trade: CongressionalTrade) -> bool:
        """
        Check if a trade matches any of the tracked committee members.
        
        Args:
            trade: Congressional trade to check
            
        Returns:
            True if trade matches any committee member
        """
        if not trade.politician:
            return False
        
        # Normalize the trade politician name
        trade_politician = self._normalize_politician_name(trade.politician)
        
        # Check against all committee members
        for normalized_member, original_member in self.normalized_politicians.items():
            similarity = self._calculate_name_similarity(trade_politician, normalized_member)
            
            if similarity >= self.match_threshold:
                logger.info(f"Committee match found: '{trade.politician}' matches member '{original_member}' (similarity: {similarity:.3f})")
                return True
        
        logger.debug(f"No committee match for: '{trade.politician}'")
        return False
    
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
            'joe': 'joseph',
            'pete': 'peter',
            'rick': 'richard',
            'tony': 'anthony',
            'sam': 'samuel'
        }
        
        # Split name and check for nickname mappings
        parts = normalized.split()
        if parts:
            first_name = parts[0]
            if first_name in name_mappings:
                parts[0] = name_mappings[first_name]
        
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
    
    def find_matching_member(self, trade: CongressionalTrade) -> Optional[str]:
        """
        Find which committee member matches a trade.
        
        Args:
            trade: Congressional trade
            
        Returns:
            Name of matching committee member or None
        """
        if not trade.politician:
            return None
        
        trade_politician = self._normalize_politician_name(trade.politician)
        best_match = None
        best_similarity = 0.0
        
        for normalized_member, original_member in self.normalized_politicians.items():
            similarity = self._calculate_name_similarity(trade_politician, normalized_member)
            
            if similarity >= self.match_threshold and similarity > best_similarity:
                best_match = original_member
                best_similarity = similarity
        
        return best_match
    
    def get_committee_info(self) -> Dict[str, Any]:
        """
        Get information about the committee.
        
        Returns:
            Dictionary with committee information
        """
        return {
            'committee_name': self.committee_name,
            'member_count': len(self.politicians),
            'members': self.politicians,
            'normalized_members': list(self.normalized_politicians.keys()),
            'match_threshold': self.match_threshold,
            'agent_type': 'committee'
        }
    
    def get_member_trade_stats(self, trades: List[CongressionalTrade]) -> Dict[str, Dict[str, Any]]:
        """
        Get trade statistics broken down by committee member.
        
        Args:
            trades: List of congressional trades to analyze
            
        Returns:
            Dictionary with stats per member
        """
        member_stats = {}
        
        # Initialize stats for all members
        for member in self.politicians:
            member_stats[member] = {
                'trades': 0,
                'purchases': 0,
                'sales': 0,
                'total_amount': 0.0,
                'unique_tickers': set(),
                'matching_trades': []
            }
        
        # Process each trade
        for trade in trades:
            matching_member = self.find_matching_member(trade)
            if matching_member:
                stats = member_stats[matching_member]
                stats['trades'] += 1
                stats['total_amount'] += trade.amount
                stats['unique_tickers'].add(trade.ticker)
                stats['matching_trades'].append(trade)
                
                if trade.transaction_type.lower() == 'purchase':
                    stats['purchases'] += 1
                elif trade.transaction_type.lower() == 'sale':
                    stats['sales'] += 1
        
        # Convert sets to lists for JSON serialization
        for member in member_stats:
            member_stats[member]['unique_tickers'] = list(member_stats[member]['unique_tickers'])
            member_stats[member]['ticker_count'] = len(member_stats[member]['unique_tickers'])
        
        return member_stats
    
    def get_committee_aggregate_stats(self, trades: List[CongressionalTrade]) -> Dict[str, Any]:
        """
        Get aggregate statistics for the entire committee.
        
        Args:
            trades: List of congressional trades to analyze
            
        Returns:
            Aggregate committee statistics
        """
        matching_trades = [trade for trade in trades if self._matches_tracked_politicians(trade)]
        
        total_amount = sum(trade.amount for trade in matching_trades)
        purchase_count = sum(1 for trade in matching_trades if trade.transaction_type.lower() == 'purchase')
        sale_count = sum(1 for trade in matching_trades if trade.transaction_type.lower() == 'sale')
        
        unique_tickers = set(trade.ticker for trade in matching_trades)
        
        # Count active members (members with trades)
        active_members = set()
        for trade in matching_trades:
            member = self.find_matching_member(trade)
            if member:
                active_members.add(member)
        
        return {
            'committee_name': self.committee_name,
            'total_members': len(self.politicians),
            'active_members': len(active_members),
            'total_trades': len(matching_trades),
            'purchase_count': purchase_count,
            'sale_count': sale_count,
            'total_amount': total_amount,
            'unique_tickers': len(unique_tickers),
            'tickers': list(unique_tickers),
            'active_member_names': list(active_members)
        }

# Factory function to create committee agents
def create_committee_agents(agents_config: List[Dict[str, Any]]) -> List[CommitteeAgent]:
    """
    Create committee agents from configuration.
    
    Args:
        agents_config: List of agent configurations
        
    Returns:
        List of created committee agents
    """
    committee_agents = []
    
    for config in agents_config:
        if config.get('type') == 'committee' and config.get('enabled', True):
            try:
                agent = CommitteeAgent(config['id'], config)
                committee_agents.append(agent)
                logger.info(f"Created committee agent: {config['id']}")
            except Exception as e:
                logger.error(f"Failed to create committee agent {config.get('id', 'unknown')}: {e}")
    
    return committee_agents

# Specific committee agent implementation
class TransportationCommitteeAgent(CommitteeAgent):
    """Specialized agent for tracking Transportation & Infrastructure Committee trades."""
    
    def __init__(self, agent_id: str, config: dict):
        file_members = self._load_transportation_members()
        if file_members:
            config['politicians'] = file_members
        elif not config.get('politicians'):
            logger.warning(
                "Transportation committee file missing or empty; using default list from configuration"
            )
        super().__init__(agent_id, config)

    @staticmethod
    @lru_cache(maxsize=1)
    def _load_transportation_members() -> List[str]:
        """Load committee roster from JSON input file."""
        committee_path = Path(PROJECT_ROOT) / 'inputs' / 'committee-transportation-infra.json'

        if not committee_path.exists():
            logger.error("Transportation committee roster file not found at %s", committee_path)
            return []

        try:
            with committee_path.open('r', encoding='utf-8') as f:
                data = json.load(f)

            members: List[str] = []
            for caucus in ('republicans', 'democrats'):
                for entry in data.get(caucus, []):
                    name = entry.get('name')
                    if name:
                        members.append(name)

            if not members:
                logger.error("Transportation committee file (%s) contains no member names", committee_path)

            return members

        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Failed to load transportation committee roster: %s", exc)
            return []
