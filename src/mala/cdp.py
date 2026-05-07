"""
Contextual Data Polishing (CDP)
Section 4.6: Data cleaning and normalization for legacy records

Applies three cleaning rules before Planner uses a record:
1. Unit normalization
2. Temporal reconciliation
3. Sensitive-field stripping
"""

import logging
import re
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# CDP applies three rules: unit normalization, temporal reconciliation, sensitive-field stripping
# State space: 27 discrete states s=(T,Y,M) per Section 3.3
# CDP is stateless: each call to polish() is independent


class ContextualDataPolisher:
    """
    Implements CDP cleaning rules per Section 4.6.
    """
    
    def __init__(self):
        self.unit_conversions = {
            # Temperature conversions to Celsius
            "F": lambda x: (x - 32) * 5/9,
            "K": lambda x: x - 273.15,
            "C": lambda x: x,
            
            # Pressure conversions to bar
            "psi": lambda x: x * 0.0689476,
            "Pa": lambda x: x * 1e-5,
            "bar": lambda x: x,
            
            # Length conversions to meters
            "ft": lambda x: x * 0.3048,
            "in": lambda x: x * 0.0254,
            "m": lambda x: x,
        }
        
        self.sensitive_fields = {
            "employee_id", "worker_name", "operator_name",
            "ssn", "social_security", "personal_id",
            "phone", "email", "address"
        }
    
    def polish(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply all three CDP rules to raw legacy data.
        Returns cleaned and normalized data.
        """
        polished = {}
        
        for key, value in raw_data.items():
            # Rule 3: Strip sensitive fields
            if self._is_sensitive_field(key):
                logger.info(f"CDP: Stripping sensitive field '{key}'")
                polished[key] = "[REDACTED]"
                continue
            
            # Rule 1: Unit normalization
            if self._is_measurement_field(key, value):
                normalized_value, normalized_unit = self._normalize_units(key, value)
                polished[key] = normalized_value
                polished[f"{key}_unit"] = normalized_unit
                logger.debug(f"CDP: Normalized {key}: {value} -> {normalized_value} {normalized_unit}")
            else:
                polished[key] = value
        
        # Rule 2: Temporal reconciliation
        polished = self._reconcile_timestamps(polished)
        
        return polished
    
    def _is_sensitive_field(self, field_name: str) -> bool:
        """Check if field contains sensitive personal data."""
        field_lower = field_name.lower()
        return any(sensitive in field_lower for sensitive in self.sensitive_fields)
    
    # Fields that look like measurements but are identifiers — never normalize.
    _IDENTIFIER_FIELDS = {
        "heat_id", "batch_id", "batch_lot", "order_id", "truck_id",
        "equipment_id", "heat_identifier", "batch_identifier",
    }

    def _is_measurement_field(self, key: str, value: Any) -> bool:
        """
        Detect if a field is a physical measurement with units.

        Accepts patterns like ``"1548C"``, ``"79.0%"``, ``"1550 F"``.
        Explicitly rejects identifier fields (heat_id, batch_id, etc.)
        whose alphanumeric values (e.g. ``"7A"``) would otherwise
        match the numeric-plus-letter pattern.
        """
        if key.lower() in self._IDENTIFIER_FIELDS:
            return False

        if not isinstance(value, (str, int, float)):
            return False

        value_str = str(value)
        # Must start with a number; unit suffix must be a recognised
        # physical unit abbreviation, not an arbitrary letter.
        _KNOWN_UNITS = r"(?:C|F|K|bar|psi|Pa|ft|in|m|%)"
        return bool(re.match(rf'[\d.]+\s*{_KNOWN_UNITS}$', value_str.strip()))
    
    def _normalize_units(self, key: str, value: Any) -> tuple[float, str]:
        """
        Convert measurements to plant-wide standard units.
        Returns: (normalized_value, standard_unit)
        """
        value_str = str(value)
        
        # Extract numeric value and unit
        match = re.match(r'([\d.]+)\s*([A-Za-z%]+)', value_str)
        if not match:
            # No unit found, return as-is
            try:
                return float(value), "unknown"
            except (ValueError, TypeError):
                return value, "unknown"
        
        numeric_val = float(match.group(1))
        unit = match.group(2)
        
        # Temperature normalization
        if unit in ["C", "F", "K"]:
            if unit in self.unit_conversions:
                normalized = self.unit_conversions[unit](numeric_val)
                return normalized, "C"
        
        # Pressure normalization
        if unit in ["psi", "Pa", "bar"]:
            if unit in self.unit_conversions:
                normalized = self.unit_conversions[unit](numeric_val)
                return normalized, "bar"
        
        # Length normalization
        if unit in ["ft", "in", "m"]:
            if unit in self.unit_conversions:
                normalized = self.unit_conversions[unit](numeric_val)
                return normalized, "m"
        
        # Percentage - no conversion needed
        if unit == "%":
            return numeric_val, "%"
        
        # Unknown unit - return as-is with warning
        logger.warning(f"CDP: Unknown unit '{unit}' for field '{key}'")
        return numeric_val, unit
    
    def _reconcile_timestamps(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Reconstruct true state when timestamps disagree across systems.
        Uses most recent timestamp as authoritative.
        """
        timestamp_fields = [k for k in data.keys() if "timestamp" in k.lower() or "time" in k.lower()]
        
        if len(timestamp_fields) <= 1:
            return data  # No conflict possible
        
        # Parse all timestamps
        parsed_times = {}
        for field in timestamp_fields:
            try:
                parsed_times[field] = self._parse_timestamp(data[field])
            except Exception as e:
                logger.warning(f"CDP: Could not parse timestamp field '{field}': {e}")
        
        if parsed_times:
            # Use most recent timestamp as canonical
            canonical_field = max(parsed_times, key=parsed_times.get)
            canonical_time = parsed_times[canonical_field]
            
            data["canonical_timestamp"] = canonical_time.isoformat()
            data["timestamp_source"] = canonical_field
            
            logger.info(
                f"CDP: Reconciled {len(timestamp_fields)} timestamps, "
                f"using {canonical_field} as canonical"
            )
        
        return data
    
    def _parse_timestamp(self, timestamp_value: Any) -> datetime:
        """
        Parse various timestamp formats from legacy systems.
        Supports: ISO 8601, Unix epoch, common date formats.
        """
        if isinstance(timestamp_value, datetime):
            return timestamp_value
        
        if isinstance(timestamp_value, (int, float)):
            # Assume Unix epoch
            return datetime.fromtimestamp(timestamp_value)
        
        if isinstance(timestamp_value, str):
            # Try common formats
            formats = [
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%d %H:%M:%S",
                "%d/%m/%Y %H:%M:%S",
                "%m/%d/%Y %H:%M:%S",
                "%Y-%m-%d",
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(timestamp_value, fmt)
                except ValueError:
                    continue
        
        raise ValueError(f"Could not parse timestamp: {timestamp_value}")
