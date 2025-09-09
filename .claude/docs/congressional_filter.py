#!/usr/bin/env python3
"""
Congressional Trading Filter System

This script filters congressional trading data based on the following criteria:
1. Date-based filtering (last_modified equals current execution date)
2. Transaction value filtering (Purchase/Sale > $50,000)
3. Committee member filtering (Transportation & Infrastructure Committee)
4. Top performer filtering (Top-performing politicians)

Requirements implemented according to requirements-congressional-trading-filter.md
"""

import os
import json
import sqlite3
import logging
import re
import sys
import argparse
from datetime import datetime, timezone, timedelta
from difflib import SequenceMatcher
from typing import Dict, List, Tuple, Optional, Any
import time
import http.client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class FuzzyNameMatcher:
    """Implements fuzzy name matching with 85% minimum similarity threshold"""
    
    MINIMUM_SIMILARITY = 0.85
    
    # Common nickname mappings for better matching
    NICKNAME_MAP = {
        'david': ['dave', 'david'],
        'dave': ['dave', 'david'],
        'robert': ['bob', 'bobby', 'rob', 'robert'],
        'bob': ['bob', 'bobby', 'rob', 'robert'],
        'james': ['jim', 'jimmy', 'james'],
        'jim': ['jim', 'jimmy', 'james'],
        'william': ['bill', 'billy', 'will', 'william'],
        'bill': ['bill', 'billy', 'will', 'william'],
        'richard': ['rick', 'dick', 'richard'],
        'rick': ['rick', 'dick', 'richard'],
        'thomas': ['tom', 'tommy', 'thomas'],
        'tom': ['tom', 'tommy', 'thomas'],
        'michael': ['mike', 'mickey', 'michael'],
        'mike': ['mike', 'mickey', 'michael'],
        'christopher': ['chris', 'christopher'],
        'chris': ['chris', 'christopher'],
        'daniel': ['dan', 'danny', 'daniel'],
        'dan': ['dan', 'danny', 'daniel'],
        'matthew': ['matt', 'matthew'],
        'matt': ['matt', 'matthew'],
        'anthony': ['tony', 'anthony'],
        'tony': ['tony', 'anthony'],
        'joseph': ['joe', 'joey', 'joseph'],
        'joe': ['joe', 'joey', 'joseph'],
        'steven': ['steve', 'steven'],
        'steve': ['steve', 'steven'],
        'kenneth': ['ken', 'kenny', 'kenneth'],
        'ken': ['ken', 'kenny', 'kenneth'],
        'benjamin': ['ben', 'benny', 'benjamin'],
        'ben': ['ben', 'benny', 'benjamin'],
        'edward': ['ed', 'eddie', 'edward'],
        'ed': ['ed', 'eddie', 'edward']
    }
    
    @staticmethod
    def normalize_name(name: str) -> str:
        """Normalize name by converting to lowercase and removing punctuation"""
        if not name:
            return ""
        
        # Convert to lowercase
        normalized = name.lower()
        
        # Remove common punctuation and extra whitespace
        normalized = re.sub(r'[.,\'""-]', '', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized
    
    @staticmethod
    def parse_name_formats(name: str) -> List[str]:
        """
        Parse different name formats and return variations
        Handles 'Last, First' vs 'First Last' formats
        Example: 'Whitehouse, Sheldon' → ['whitehouse sheldon', 'sheldon whitehouse']
        """
        if not name:
            return []
        
        normalized = FuzzyNameMatcher.normalize_name(name)
        variations = [normalized]
        
        # Check if name contains comma (Last, First format)
        if ',' in normalized:
            parts = [part.strip() for part in normalized.split(',')]
            if len(parts) == 2 and parts[0] and parts[1]:
                # Convert "Last, First" to "First Last"
                first_last_format = f"{parts[1]} {parts[0]}"
                variations.append(first_last_format)
        else:
            # Check if it's "First Last" format and create "Last, First"
            words = normalized.split()
            if len(words) >= 2:
                # Assume last word is surname for basic cases
                last_name = words[-1]
                first_names = ' '.join(words[:-1])
                last_first_format = f"{last_name}, {first_names}"
                variations.append(last_first_format)
        
        return variations
    
    @staticmethod
    def generate_nickname_variations(base_name: str, original_name: str) -> List[str]:
        """
        Generate nickname and other variations for a base name
        """
        variations = [base_name]
        
        # Extract nicknames from quotes (existing logic) - use original_name for quote detection
        nickname_pattern = r'"([^"]+)"'
        nicknames = re.findall(nickname_pattern, original_name.lower())
        
        if nicknames:
            base_without_quotes = re.sub(r'\s*"[^"]+"\s*', ' ', original_name.lower())
            base_without_quotes = FuzzyNameMatcher.normalize_name(base_without_quotes)
            variations.append(base_without_quotes)
            
            for nickname in nicknames:
                nickname_normalized = FuzzyNameMatcher.normalize_name(nickname)
                parts = base_without_quotes.split()
                if len(parts) >= 2:
                    nickname_variation = nickname_normalized + ' ' + ' '.join(parts[1:])
                    variations.append(nickname_variation)
        
        # Handle common nickname mappings
        parts = base_name.split()
        if parts:
            first_name = parts[0]
            if first_name in FuzzyNameMatcher.NICKNAME_MAP:
                nickname_alternatives = FuzzyNameMatcher.NICKNAME_MAP[first_name]
                for alt_name in nickname_alternatives:
                    if alt_name != first_name:  # Don't duplicate the original
                        if len(parts) > 1:
                            alt_variation = alt_name + ' ' + ' '.join(parts[1:])
                            variations.append(alt_variation)
                        else:
                            variations.append(alt_name)
        
        # Remove middle initials/names to create shorter variations
        if len(parts) >= 3:
            # Create variation without middle names/initials
            first_last = parts[0] + ' ' + parts[-1]
            variations.append(first_last)
            
            # Also create nickname versions without middle names
            if parts[0] in FuzzyNameMatcher.NICKNAME_MAP:
                for alt_name in FuzzyNameMatcher.NICKNAME_MAP[parts[0]]:
                    if alt_name != parts[0]:
                        alt_first_last = alt_name + ' ' + parts[-1]
                        variations.append(alt_first_last)
        
        # Remove suffixes (Jr., Sr., III, etc.)
        suffix_pattern = r'\b(?:jr\.?|sr\.?|iii|iv|v)\b'
        additional_variations = []
        for variation in variations:
            without_suffix = re.sub(suffix_pattern, '', variation, flags=re.IGNORECASE)
            without_suffix = re.sub(r'\s+', ' ', without_suffix).strip()
            if without_suffix != variation and without_suffix:
                additional_variations.append(without_suffix)
        variations.extend(additional_variations)
        
        return variations
    
    @staticmethod
    def extract_name_variations(name: str) -> List[str]:
        """
        Extract name variations including nicknames, suffixes, and common name mappings
        Example: 'David J. Taylor' → ['david j taylor', 'dave taylor', 'david taylor']
        Example: 'Whitehouse, Sheldon' → ['whitehouse sheldon', 'sheldon whitehouse']
        """
        variations = []
        
        # Start with format variations (handles Last,First vs First Last)
        format_variations = FuzzyNameMatcher.parse_name_formats(name)
        variations.extend(format_variations)
        
        # Use the first format variation as the base for further processing
        normalized = format_variations[0] if format_variations else FuzzyNameMatcher.normalize_name(name)
        
        # Apply nickname and variation logic to each format variation
        all_format_variations = []
        for base_variation in format_variations:
            all_format_variations.extend(FuzzyNameMatcher.generate_nickname_variations(base_variation, name))
        
        variations.extend(all_format_variations)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_variations = []
        for variation in variations:
            if variation not in seen and variation:
                seen.add(variation)
                unique_variations.append(variation)
        
        return unique_variations
    
    @staticmethod
    def calculate_similarity(name1: str, name2: str) -> float:
        """Calculate similarity score between two names using SequenceMatcher"""
        if not name1 or not name2:
            return 0.0
        
        return SequenceMatcher(None, name1, name2).ratio()
    
    @classmethod
    def normalize_district(cls, district: str) -> str:
        """
        Normalize district format for comparison
        Examples: ' OH02' → 'OH-2', 'OH-2' → 'OH-2', 'MD06' → 'MD-6'
        """
        if not district:
            return ""
        
        # Remove leading/trailing spaces
        district = district.strip()
        
        # Handle format like ' OH02' or 'OH02'
        if len(district) >= 4 and district[-2:].isdigit():
            state = district[:-2].strip()
            num = district[-2:].lstrip('0') or '0'  # Remove leading zeros, but keep '0' if it's '00'
            return f"{state}-{num}"
        
        # Handle format like 'OH-2' (already normalized)
        if '-' in district:
            return district
        
        return district
    
    @classmethod
    def districts_match(cls, district1: str, district2: str) -> bool:
        """
        Check if two districts represent the same district
        """
        norm1 = cls.normalize_district(district1)
        norm2 = cls.normalize_district(district2)
        return norm1 and norm2 and norm1.upper() == norm2.upper()
    
    @classmethod
    def fuzzy_match(cls, target_name: str, candidate_names: List[str], target_district: str = None, candidate_districts: List[str] = None) -> Tuple[Optional[str], float]:
        """
        Find the best fuzzy match for target_name in candidate_names
        Optionally use district information for additional validation
        Returns: (matched_name, similarity_score) or (None, 0.0)
        """
        target_variations = cls.extract_name_variations(target_name)
        best_match = None
        best_score = 0.0
        best_candidate = None
        
        for i, candidate in enumerate(candidate_names):
            candidate_variations = cls.extract_name_variations(candidate)
            candidate_district = candidate_districts[i] if candidate_districts and i < len(candidate_districts) else None
            
            # Calculate name similarity
            max_name_score = 0.0
            for target_var in target_variations:
                for candidate_var in candidate_variations:
                    score = cls.calculate_similarity(target_var, candidate_var)
                    max_name_score = max(max_name_score, score)
            
            # If we have district information, use it for additional validation
            final_score = max_name_score
            if target_district and candidate_district:
                districts_match = cls.districts_match(target_district, candidate_district)
                if districts_match:
                    # Boost score for district match
                    final_score = min(1.0, max_name_score + 0.1)
                elif max_name_score >= 0.95:  # Very high name similarity
                    # Don't penalize too much for district mismatch if names are very similar
                    pass
                else:
                    # Penalize for district mismatch
                    final_score = max_name_score * 0.8
            
            if final_score > best_score:
                best_score = final_score
                best_match = candidate
                best_candidate = candidate
        
        if best_score >= cls.MINIMUM_SIMILARITY:
            return best_match, best_score
        
        return None, 0.0


class ValueRangeParser:
    """Parses Trade_Size_USD range values to extract minimum dollar amounts"""
    
    @staticmethod
    def extract_min_value(trade_size_str: str) -> Optional[float]:
        """
        Extract minimum value from trade size string
        Examples:
        - "$50,001 - $100,000" → 50001.0
        - "$75,000" → 75000.0
        - "$250,000 - " → 250000.0
        - Invalid format → None
        """
        if not trade_size_str:
            return None
        
        # Remove currency symbols and spaces
        clean_str = trade_size_str.replace('$', '').replace(',', '').strip()
        
        # Handle range format: "50001 - 100000" or "250000 - "
        if ' - ' in clean_str or ' -' in clean_str:
            # Handle both "250000 - " and "250000 -"
            parts = clean_str.replace(' -', ' - ').split(' - ')
            try:
                first_part = parts[0].strip()
                return float(first_part) if first_part else None
            except (ValueError, IndexError):
                return None
        else:
            # Single value: "75000"
            try:
                return float(clean_str)
            except ValueError:
                return None


class DatabaseManager:
    """Manages SQLite database operations for filtered trades"""
    
    def __init__(self, db_path: str = "data/congressional_trades_filtered.db"):
        self.db_path = db_path
        self.ensure_data_directory()
        self.init_database()
    
    def ensure_data_directory(self):
        """Create data directory if it doesn't exist"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    def init_database(self):
        """Initialize database with required schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS filtered_trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    execution_date DATE NOT NULL,
                    original_record_json TEXT NOT NULL,
                    categories_matched TEXT NOT NULL,
                    filter_match_reasons TEXT NOT NULL,
                    ticker VARCHAR(10),
                    trade_date DATE,
                    transaction_type VARCHAR(20),
                    trade_size_min DECIMAL(15,2),
                    representative_name VARCHAR(255),
                    party CHAR(1),
                    chamber VARCHAR(10),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("CREATE INDEX IF NOT EXISTS idx_execution_date ON filtered_trades(execution_date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ticker ON filtered_trades(ticker)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_representative ON filtered_trades(representative_name)")
    
    def insert_filtered_trades(self, execution_date: str, filtered_records: List[Dict]):
        """Insert filtered trade records into database"""
        with sqlite3.connect(self.db_path) as conn:
            for record in filtered_records:
                original_record = record['original_record']
                categories = json.dumps(record['categories_matched'])
                reasons = json.dumps(record.get('filter_match_reason', []))
                
                conn.execute("""
                    INSERT INTO filtered_trades (
                        execution_date, original_record_json, categories_matched,
                        filter_match_reasons, ticker, trade_date, transaction_type,
                        trade_size_min, representative_name, party, chamber
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    execution_date,
                    json.dumps(original_record),
                    categories,
                    reasons,
                    original_record.get('Ticker'),
                    original_record.get('Traded'),
                    original_record.get('Transaction'),
                    ValueRangeParser.extract_min_value(original_record.get('Trade_Size_USD', '')),
                    original_record.get('Name'),
                    original_record.get('Party'),
                    original_record.get('Chamber')
                ))


class CongressionalDataFetcher:
    """Handles fetching congressional trading data from Quiver API"""
    
    def __init__(self):
        self.token = os.getenv('token')
        if not self.token:
            raise ValueError("Token not found in .env file")
        
        self.headers = {
            'Accept': "application/json",
            'Authorization': f"Bearer {self.token}"
        }
    
    def fetch_daily_data(self, date_str: str = None, max_retries: int = 3) -> List[Dict]:
        """
        Fetch congressional trading data for specified date with retry logic
        Returns list of trade records
        """
        if not date_str:
            # Use current date in GMT-4 timezone
            et_timezone = timezone(timedelta(hours=-4))
            date_str = datetime.now(et_timezone).strftime("%Y%m%d")
        
        for attempt in range(max_retries):
            try:
                conn = http.client.HTTPSConnection("api.quiverquant.com")
                
                # Use V2 API with date parameter
                endpoint = f"/beta/bulk/congresstrading?date={date_str}&version=V2"
                conn.request("GET", endpoint, headers=self.headers)
                
                res = conn.getresponse()
                data = res.read()
                
                if res.status == 200:
                    json_data = json.loads(data.decode("utf-8"))
                    
                    # Save raw data to outputs folder
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"outputs/congress_trading_data_{timestamp}.json"
                    os.makedirs("outputs", exist_ok=True)
                    
                    with open(filename, 'w') as f:
                        json.dump(json_data, f, indent=2)
                    
                    logging.info(f"Raw data saved to {filename} - {len(json_data)} records retrieved")
                    return json_data
                
                elif res.status == 429:  # Rate limited
                    wait_time = 2 ** attempt  # Exponential backoff
                    logging.warning(f"Rate limited, waiting {wait_time}s before retry {attempt + 1}/{max_retries}")
                    time.sleep(wait_time)
                    continue
                
                elif res.status == 401:
                    logging.error("Unauthorized - check API token")
                    sys.exit(1)
                
                else:
                    logging.warning(f"HTTP {res.status}: {data.decode('utf-8')}")
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        logging.info(f"Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                
            except Exception as e:
                logging.error(f"Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                else:
                    logging.error("All retry attempts failed")
                    sys.exit(1)
            finally:
                try:
                    conn.close()
                except:
                    pass
        
        logging.error("Failed to fetch data after all retries")
        sys.exit(1)


class CongressionalTradeFilter:
    """Main filtering logic for congressional trading data"""
    
    def __init__(self):
        self.setup_logging()
        self.db_manager = DatabaseManager()
        self.data_fetcher = CongressionalDataFetcher()
        self.committee_names = []
        self.committee_districts = []
        self.top_politician_names = []
        
        # Load input files
        self.load_input_files()
    
    def setup_logging(self):
        """Setup daily logging with rotation"""
        os.makedirs("logs", exist_ok=True)
        
        today = datetime.now().strftime('%Y%m%d')
        log_filename = f"logs/congressional_filter_{today}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler(log_filename),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        # Log cleanup - keep last 30 days
        self.cleanup_old_logs()
    
    def cleanup_old_logs(self):
        """Remove log files older than 30 days"""
        try:
            log_dir = "logs"
            cutoff_date = datetime.now() - timedelta(days=30)
            
            for filename in os.listdir(log_dir):
                if filename.startswith("congressional_filter_") and filename.endswith(".log"):
                    filepath = os.path.join(log_dir, filename)
                    file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                    if file_time < cutoff_date:
                        os.remove(filepath)
                        logging.info(f"Removed old log file: {filename}")
        except Exception as e:
            logging.warning(f"Error cleaning up old logs: {e}")
    
    def load_input_files(self):
        """Load committee members and top politicians from input files"""
        try:
            # Load committee members
            committee_file = "inputs/committee-transportation-infra.json"
            if os.path.exists(committee_file):
                with open(committee_file, 'r') as f:
                    committee_data = json.load(f)
                
                self.committee_names = []
                self.committee_districts = []
                for member in committee_data.get('republicans', []):
                    self.committee_names.append(member['name'])
                    self.committee_districts.append(member.get('district', ''))
                for member in committee_data.get('democrats', []):
                    self.committee_names.append(member['name'])
                    self.committee_districts.append(member.get('district', ''))
                
                logging.info(f"Loaded {len(self.committee_names)} committee members")
            else:
                logging.warning(f"Committee file not found: {committee_file}")
            
            # Load top performing politicians
            politicians_file = "inputs/top-performing-politicians.md"
            if os.path.exists(politicians_file):
                with open(politicians_file, 'r') as f:
                    content = f.read().strip()
                
                # Parse comma-separated quoted names
                self.top_politician_names = [name.strip().strip('"') for name in content.split(',')]
                logging.info(f"Loaded {len(self.top_politician_names)} top performing politicians")
            else:
                logging.warning(f"Top politicians file not found: {politicians_file}")
        
        except Exception as e:
            logging.error(f"Error loading input files: {e}")
    
    def filter_by_date(self, trades: List[Dict], target_date: str) -> List[Dict]:
        """Filter trades by last_modified date"""
        filtered = []
        for trade in trades:
            last_modified = trade.get('last_modified', '')
            
            
            if isinstance(last_modified, str) and last_modified.startswith(target_date):
                filtered.append(trade)
        
        logging.info(f"Date filtering: {len(filtered)} records match {target_date}")
        return filtered
    
    def categorize_trades(self, trades: List[Dict]) -> Dict[str, List[Dict]]:
        """Apply all filtering criteria and categorize trades"""
        categorized = {
            "high_value_purchases": [],
            "high_value_sales": [],
            "committee_members": [],
            "top_performers": []
        }
        
        matcher = FuzzyNameMatcher()
        
        for trade in trades:
            categories_matched = []
            match_reasons = []
            
            # Parse trade value
            trade_size_str = trade.get('Trade_Size_USD', '')
            min_value = ValueRangeParser.extract_min_value(trade_size_str)
            transaction_type = trade.get('Transaction', '')
            trader_name = trade.get('Name', '')
            
            # Filter 1 & 2: High value purchases/sales
            if min_value and min_value > 50000:
                if transaction_type == 'Purchase':
                    categories_matched.append("high_value_purchases")
                    match_reasons.append(f"Purchase > $50,000 ({trade_size_str})")
                elif transaction_type == 'Sale':
                    categories_matched.append("high_value_sales")
                    match_reasons.append(f"Sale > $50,000 ({trade_size_str})")
            
            # Filter 3: Committee member trades
            if self.committee_names:
                trader_district = trade.get('District', '')
                matched_committee, similarity = matcher.fuzzy_match(
                    trader_name, 
                    self.committee_names, 
                    trader_district, 
                    self.committee_districts
                )
                
                
                if matched_committee:
                    categories_matched.append("committee_members")
                    match_reasons.append(f"Committee member: {matched_committee} (similarity: {similarity:.2f})")
            
            # Filter 4: Top performer trades
            if self.top_politician_names:
                matched_politician, similarity = matcher.fuzzy_match(trader_name, self.top_politician_names)
                if matched_politician:
                    categories_matched.append("top_performers")
                    match_reasons.append(f"Top performer: {matched_politician} (similarity: {similarity:.2f})")
            
            # Add to appropriate categories
            if categories_matched:
                record = {
                    "original_record": trade,
                    "filter_match_reason": "; ".join(match_reasons),
                    "categories_matched": categories_matched
                }
                
                for category in categories_matched:
                    categorized[category].append(record)
        
        # Log statistics
        for category, records in categorized.items():
            logging.info(f"{category}: {len(records)} records")
        
        return categorized
    
    def generate_output(self, categorized_trades: Dict, execution_date: str, total_processed: int) -> str:
        """Generate output JSON file with metadata"""
        output = {
            "metadata": {
                "execution_date": execution_date,
                "execution_time": datetime.now().strftime("%H:%M:%S GMT-4"),
                "total_records_processed": total_processed,
                "total_filtered_records": sum(len(records) for records in categorized_trades.values()),
                "filters_applied": ["high_value_purchases", "high_value_sales", "committee_members", "top_performers"]
            }
        }
        
        # Add categorized data
        output.update(categorized_trades)
        
        # Generate filename
        date_formatted = execution_date.replace('-', '')
        output_filename = f"outputs/{date_formatted}-trades.json"
        
        os.makedirs("outputs", exist_ok=True)
        with open(output_filename, 'w') as f:
            json.dump(output, f, indent=2)
        
        logging.info(f"Filtered trades saved to {output_filename}")
        return output_filename
    
    def run_daily_filter(self, date_str: str = None) -> Optional[str]:
        """Execute the complete daily filtering process"""
        start_time = datetime.now()
        logging.info("Starting congressional trading filter process")
        
        try:
            # Determine target date
            if date_str:
                target_date = date_str
                fetch_date = date_str.replace('-', '')
            else:
                et_timezone = timezone(timedelta(hours=-4))
                current_date = datetime.now(et_timezone)
                target_date = current_date.strftime("%Y-%m-%d")
                fetch_date = current_date.strftime("%Y%m%d")
            
            logging.info(f"Processing trades for date: {target_date}")
            
            # Fetch raw data
            raw_trades = self.data_fetcher.fetch_daily_data(fetch_date)
            logging.info(f"Retrieved {len(raw_trades)} raw trade records")
            
            # Filter by date
            date_filtered = self.filter_by_date(raw_trades, target_date)
            
            if not date_filtered:
                logging.info("No trades found for target date")
                # Still generate empty output file
                empty_output = {category: [] for category in ["high_value_purchases", "high_value_sales", "committee_members", "top_performers"]}
                output_file = self.generate_output(empty_output, target_date, len(raw_trades))
                return output_file
            
            # Apply filtering and categorization
            categorized = self.categorize_trades(date_filtered)
            
            # Generate output file
            output_file = self.generate_output(categorized, target_date, len(raw_trades))
            
            # Save to database
            all_filtered_records = []
            for category_records in categorized.values():
                all_filtered_records.extend(category_records)
            
            if all_filtered_records:
                self.db_manager.insert_filtered_trades(target_date, all_filtered_records)
                logging.info(f"Saved {len(all_filtered_records)} records to database")
            
            # Log execution summary
            duration = datetime.now() - start_time
            logging.info(f"Filter process completed in {duration.total_seconds():.2f} seconds")
            logging.info(f"Output file: {output_file}")
            
            return output_file
            
        except Exception as e:
            logging.error(f"Filter process failed: {e}", exc_info=True)
            sys.exit(2)


def main():
    """Main entry point with command line interface"""
    parser = argparse.ArgumentParser(
        description="Congressional Trading Filter System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 congressional_filter.py              # Process today's date
  python3 congressional_filter.py --date 2024-12-15  # Process specific date
  python3 congressional_filter.py --enable-trading   # Process today's date and execute automated trades
  python3 congressional_filter.py --date 2024-12-15 --enable-trading  # Process specific date with trading
        """
    )
    
    parser.add_argument(
        '--date',
        type=str,
        help='Date to process in YYYY-MM-DD format (default: today GMT-4)'
    )
    
    parser.add_argument(
        '--enable-trading',
        action='store_true',
        default=False,
        help='Enable automated trading of filtered trades via Alpaca API'
    )
    
    args = parser.parse_args()
    
    # Validate date format if provided
    if args.date:
        try:
            datetime.strptime(args.date, '%Y-%m-%d')
        except ValueError:
            print("Error: Date must be in YYYY-MM-DD format")
            sys.exit(1)
    
    # Run the filter
    try:
        filter_system = CongressionalTradeFilter()
        output_file = filter_system.run_daily_filter(args.date)
        
        # Execute automated trading if enabled
        if args.enable_trading and output_file:
            logging.info("Automated trading enabled - executing trades...")
            try:
                from congressional_automated_trader import CongressionalAutomatedTrader
                trader = CongressionalAutomatedTrader()
                trading_summary = trader.process_filtered_trades(output_file)
                
                # Log trading results
                summary_stats = trading_summary['summary']
                logging.info(f"Trading completed: {summary_stats['successful']}/{summary_stats['total_attempted']} trades successful")
                logging.info(f"Total trading amount: ${summary_stats['total_dollar_amount']:.2f}")
                
                if summary_stats['failed'] > 0:
                    logging.warning(f"Trading failures: {summary_stats['failed']} trades failed")
                    
            except ImportError as e:
                logging.error(f"Failed to import trading module: {e}")
            except Exception as e:
                logging.error(f"Automated trading failed: {e}", exc_info=True)
        
        sys.exit(0)
    except KeyboardInterrupt:
        logging.info("Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(3)


if __name__ == "__main__":
    main()