"""
SQL-92 Legacy ERP Adapter
Connects to 1990s-era ERP systems via SQL-92 interface.
"""

import logging
from typing import Dict, List, Optional, Any
from .base import BaseAdapter

logger = logging.getLogger(__name__)


class SQL92Adapter(BaseAdapter):
    """
    Adapter for legacy SQL-92 ERP databases.
    In production, would use actual database drivers (e.g., pyodbc, psycopg2).
    For prototype, simulates query results.
    """
    
    def __init__(self, connection_string: Optional[str] = None):
        """
        Args:
            connection_string: Database connection string (unused in simulation)
        """
        self.connection_string = connection_string
        self.simulated_tables = self._initialize_simulated_db()
    
    def scrape(self, target: str) -> str:
        """
        Execute SQL query and return results as formatted string.
        Target should be a SQL query.
        """
        try:
            results = self.execute_query(target)
            return self._format_results(results)
        except Exception as e:
            logger.error(f"SQL92Adapter: Query failed: {e}")
            return f"ERROR: {str(e)}"
    
    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """
        Execute SQL query and return results as list of dictionaries.
        
        Args:
            query: SQL-92 compliant query string
        
        Returns:
            List of row dictionaries
        """
        query_upper = query.upper().strip()
        
        # Simple query parser for prototype
        if "SELECT" not in query_upper:
            raise ValueError("Only SELECT queries supported in prototype")
        
        # Extract table name
        if "FROM" not in query_upper:
            raise ValueError("Query must contain FROM clause")
        
        # Parse table name more robustly
        from_idx = query_upper.index("FROM")
        after_from_part = query[from_idx + 4:].strip()  # Skip "FROM"
        
        # Extract table name (first word after FROM)
        table_name = after_from_part.split()[0].strip().rstrip(";").upper()
        
        # Remove any WHERE clause from table name
        if " " in table_name:
            table_name = table_name.split()[0]
        
        if table_name not in self.simulated_tables:
            raise ValueError(f"Table '{table_name}' not found")
        
        # Return all rows (simplified - no WHERE clause parsing)
        results = self.simulated_tables[table_name]
        logger.info(f"SQL92Adapter: Query returned {len(results)} rows from {table_name}")
        return results
    
    def _format_results(self, results: List[Dict[str, Any]]) -> str:
        """Format query results as ASCII table string."""
        if not results:
            return "No results"
        
        # Get column names
        columns = list(results[0].keys())
        
        # Calculate column widths
        widths = {col: len(col) for col in columns}
        for row in results:
            for col in columns:
                widths[col] = max(widths[col], len(str(row[col])))
        
        # Build table
        lines = []
        
        # Header
        header = " | ".join(col.ljust(widths[col]) for col in columns)
        lines.append(header)
        lines.append("-" * len(header))
        
        # Rows
        for row in results:
            line = " | ".join(str(row[col]).ljust(widths[col]) for col in columns)
            lines.append(line)
        
        return "\n".join(lines)
    
    def _initialize_simulated_db(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Initialize simulated database tables.
        Represents 1990s-era ERP schema.
        """
        return {
            "PRODUCTION_ORDERS": [
                {
                    "order_id": "PO-2026-0427-001",
                    "heat_id": "H-402",
                    "batch_lot": "7A",
                    "grade": "CR-17",
                    "quantity_tons": 45.2,
                    "mill_assigned": "MILL_B",
                    "status": "IN_PROGRESS",
                    "priority": 1,
                    "start_time": "2026-04-27T09:00:00Z"
                },
                {
                    "order_id": "PO-2026-0427-002",
                    "heat_id": "H-403",
                    "batch_lot": "8C",
                    "grade": "CR-17",
                    "quantity_tons": 52.1,
                    "mill_assigned": "MILL_A",
                    "status": "SCHEDULED",
                    "priority": 2,
                    "start_time": "2026-04-27T16:00:00Z"
                }
            ],
            
            "EQUIPMENT_STATUS": [
                {
                    "equipment_id": "MILL_A",
                    "equipment_type": "ROLLING_MILL",
                    "status": "OPERATIONAL",
                    "capacity_tons_per_hour": 8.5,
                    "current_load_pct": 65.0,
                    "last_maintenance": "2026-04-20T08:00:00Z",
                    "next_maintenance": "2026-05-20T08:00:00Z"
                },
                {
                    "equipment_id": "MILL_B",
                    "equipment_type": "ROLLING_MILL",
                    "status": "DOWN",
                    "capacity_tons_per_hour": 9.0,
                    "current_load_pct": 0.0,
                    "fault_code": "HYD_FAIL_001",
                    "fault_time": "2026-04-27T14:12:00Z",
                    "estimated_repair_hours": 5.0
                },
                {
                    "equipment_id": "FURNACE_1",
                    "equipment_type": "REHEAT_FURNACE",
                    "status": "OPERATIONAL",
                    "temperature_celsius": 1548.0,
                    "temperature_setpoint": 1545.0,
                    "max_temperature": 1550.0
                }
            ],
            
            "INVENTORY": [
                {
                    "heat_id": "H-402",
                    "location": "YARD_Q3",
                    "quantity_tons": 45.2,
                    "grade": "CR-17",
                    "mn_content": 1.05,
                    "cr_content": 17.2,
                    "status": "AVAILABLE",
                    "last_updated": "2026-04-27T09:45:00Z"
                },
                {
                    "heat_id": "H-403",
                    "location": "YARD_Q3",
                    "quantity_tons": 52.1,
                    "grade": "CR-17",
                    "mn_content": 1.08,
                    "cr_content": 17.1,
                    "status": "AVAILABLE",
                    "last_updated": "2026-04-27T10:15:00Z"
                },
                {
                    "heat_id": "H-401",
                    "location": "YARD_Q1",
                    "quantity_tons": 38.7,
                    "grade": "CR-18",
                    "mn_content": 0.95,
                    "cr_content": 17.5,
                    "status": "ALLOCATED",
                    "last_updated": "2026-04-27T08:30:00Z"
                }
            ],
            
            "YARD_CAPACITY": [
                {
                    "quadrant": "Q1",
                    "capacity_tons": 500.0,
                    "current_load_tons": 385.0,
                    "occupancy_pct": 77.0,
                    "status": "NORMAL"
                },
                {
                    "quadrant": "Q2",
                    "capacity_tons": 500.0,
                    "current_load_tons": 420.0,
                    "occupancy_pct": 84.0,
                    "status": "HIGH"
                },
                {
                    "quadrant": "Q3",
                    "capacity_tons": 500.0,
                    "current_load_tons": 410.0,
                    "occupancy_pct": 82.0,
                    "status": "MEDIUM"
                },
                {
                    "quadrant": "Q4",
                    "capacity_tons": 500.0,
                    "current_load_tons": 360.0,
                    "occupancy_pct": 72.0,
                    "status": "NORMAL"
                }
            ]
        }
