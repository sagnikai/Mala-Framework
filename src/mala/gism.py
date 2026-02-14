"""
Global Industrial Semantic Model (GISM)
Section 4.5: Ontological Mapping and Linguistic Isolation

Static JSON lookup table containing 420 validated concept mappings
curated by plant engineers. Maps local shop-floor jargon to standard
industrial terminology.
"""

import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class GISM:
    """
    Global Industrial Semantic Model.
    Implements φ: L_local → L_standard mapping function.
    
    In production, this would load from a JSON file with 420 entries.
    For prototype, we implement a representative subset.
    """
    
    def __init__(self):
        # Representative subset of the 420-entry ontology
        self.mappings = {
            # Temperature and thermal terms
            "TMP": "temperature",
            "TEMP": "temperature",
            "FURN": "furnace",
            "FURNACE": "furnace",
            "OVERHEAT": "over_temperature_alarm",
            
            # Chemical composition
            "MN": "manganese",
            "Mn": "manganese",
            "VAR": "variance",
            "VARIANCE": "variance",
            "Var-Low": "variance_below_threshold",
            "Var-High": "variance_above_threshold",
            
            # Production units
            "H-402": "Heat_402",
            "HEAT": "heat_identifier",
            "LOT": "batch_lot",
            "BATCH": "batch_identifier",
            
            # Mill and routing
            "RM_B": "Rolling_Mill_B",
            "RM-B": "Rolling_Mill_B",
            "Mill B": "Rolling_Mill_B",
            "Mill A": "Rolling_Mill_A",
            "D0WN": "system_down",
            "DOWN": "system_down",
            
            # Logistics
            "YARD": "storage_yard",
            "Q3": "yard_quadrant_3",
            "TRK": "truck",
            "TRUCK": "truck",
            "ETA": "estimated_time_arrival",
            
            # Status indicators
            "ACTIVE": "operational_status_active",
            "ALARM": "alarm_status",
            "NONE": "no_alarm",
            "WARNING": "warning_level_alarm",
            
            # Actions
            "REROUTE": "production_reroute",
            "HOLD": "production_hold",
            "DISPATCH": "logistics_dispatch",
        }
        
        self.coverage_stats = {
            "total_entries": 420,
            "implemented_subset": len(self.mappings),
            "coverage_rate": 0.85  # 85% coverage per Section 5.8
        }
    
    def translate(self, local_term: str) -> Optional[str]:
        """
        Translate local jargon to standard term.
        Returns None if term not found in ontology.
        """
        # Try exact match first
        if local_term in self.mappings:
            logger.debug(f"GISM: {local_term} -> {self.mappings[local_term]}")
            return self.mappings[local_term]
        
        # Try case-insensitive match
        for key, value in self.mappings.items():
            if key.lower() == local_term.lower():
                logger.debug(f"GISM (case-insensitive): {local_term} -> {value}")
                return value
        
        logger.warning(f"GISM: No mapping found for '{local_term}' - fallback required")
        return None
    
    def translate_with_fallback(self, local_term: str, llm_fallback_fn=None) -> tuple[str, bool]:
        """
        Translate with LLM fallback for unmapped terms.
        Returns: (translated_term, required_fallback)
        
        Per Section 5.8: "If an unmapped local term is encountered, the system
        falls back to a few-shot LLM prompt to infer the likely standard term
        and flags the inferred translation for mandatory Judge review."
        """
        standard_term = self.translate(local_term)
        
        if standard_term is not None:
            return standard_term, False
        
        # Fallback to LLM inference
        if llm_fallback_fn is not None:
            inferred_term = llm_fallback_fn(local_term)
            logger.warning(
                f"GISM: LLM fallback inference for '{local_term}' -> '{inferred_term}' "
                f"(FLAGGED FOR JUDGE REVIEW)"
            )
            return inferred_term, True
        
        # No fallback available
        logger.error(f"GISM: Cannot translate '{local_term}' - no fallback available")
        return local_term, True
    
    def get_coverage_stats(self) -> Dict:
        """Return GISM coverage statistics."""
        return self.coverage_stats
    
    def add_mapping(self, local_term: str, standard_term: str):
        """
        Add a new validated mapping to GISM.
        In production, this would update the persistent JSON store.
        """
        self.mappings[local_term] = standard_term
        self.coverage_stats["implemented_subset"] = len(self.mappings)
        logger.info(f"GISM: Added mapping {local_term} -> {standard_term}")
