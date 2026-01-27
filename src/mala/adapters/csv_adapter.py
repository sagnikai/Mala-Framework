"""
CSV Archive Adapter
Reads flat CSV quality files from legacy Windows XP workstations.
"""

import logging
import csv
from typing import Dict, List, Optional
from io import StringIO
from .base import BaseAdapter

logger = logging.getLogger(__name__)


class CSVArchiveAdapter(BaseAdapter):
    """
    Adapter for reading CSV archives from legacy systems.
    Simulates reading from flat files on Windows XP workstations.
    """
    
    def __init__(self, simulate_data: Optional[Dict[str, str]] = None):
        """
        Args:
            simulate_data: Dict mapping target names to CSV content strings
        """
        self.simulate_data = simulate_data or self._get_default_simulated_data()
    
    def scrape(self, target: str) -> str:
        """
        Extract CSV data from target archive.
        Returns raw CSV string.
        """
        if target in self.simulate_data:
            logger.info(f"CSVAdapter: Reading archive '{target}'")
            return self.simulate_data[target]
        
        logger.warning(f"CSVAdapter: Target '{target}' not found")
        return ""
    
    def scrape_as_dict(self, target: str) -> List[Dict[str, str]]:
        """
        Extract and parse CSV data as list of dictionaries.
        More convenient for downstream processing.
        """
        raw_csv = self.scrape(target)
        if not raw_csv:
            return []
        
        reader = csv.DictReader(StringIO(raw_csv))
        records = list(reader)
        logger.info(f"CSVAdapter: Parsed {len(records)} records from '{target}'")
        return records
    
    def _get_default_simulated_data(self) -> Dict[str, str]:
        """
        Simulated CSV archives for prototype.
        In production, these would be read from actual file paths.
        """
        return {
            "QUALITY_LOG_2026": """heat_id,batch_lot,mn_variance,cr_content,timestamp
H-402,7A,0.06,17.2,2026-04-27T09:45:00Z
H-401,6B,0.04,17.5,2026-04-27T08:30:00Z
H-403,8C,0.08,17.1,2026-04-27T10:15:00Z
H-381,5D,0.05,17.3,2026-04-20T14:20:00Z""",
            
            "INVENTORY_SNAPSHOT": """heat_id,location,quantity_tons,grade,status
H-402,YARD_Q3,45.2,CR-17,AVAILABLE
H-401,YARD_Q1,38.7,CR-18,ALLOCATED
H-403,YARD_Q3,52.1,CR-17,AVAILABLE
H-404,MILL_A,12.5,CR-16,IN_PROCESS""",
            
            "DISPATCH_LOG": """truck_id,eta_minutes,destination,load_capacity,status
TRK17,18,MILL_A,50.0,EN_ROUTE
TRK18,45,MILL_B,50.0,SCHEDULED
TRK19,120,EXTERNAL,60.0,SCHEDULED"""
        }
