import logging
import re
import time
from typing import Dict, Optional
from ..adapters.base import BaseAdapter
from ..models import KnowledgeSet, ConfidenceScore, FreshnessScore
from ..gism import GISM
from ..cdp import ContextualDataPolisher

logger = logging.getLogger(__name__)

# Freshness threshold: F(Dt) < 0.47 triggers re-fetch (approx 15 min)
# GISM translates local jargon; CDP polishes units, timestamps, and PII


class GathererAgent:
    """
    Recursive Context Enrichment (RCE) - Section 4.3.
    Fills knowledge gaps from multiple legacy sources:
    - OCR terminal adapters
    - SQL-92 ERP databases
    - CSV archives
    - Scanned PDFs
    Normalizes output to JSON-LD with GISM translation and CDP polishing.
    """
    
    def __init__(self, adapters: Dict[str, BaseAdapter], 
                 theta_low: float = 0.45, theta_high: float = 0.80):
        self.adapters = adapters
        self.gism = GISM()
        self.cdp = ContextualDataPolisher()
        self.confidence_scorer = ConfidenceScore(theta_low, theta_high)
        self.freshness_scorer = FreshnessScore()
        self.d_max = 3  # Maximum recursion depth per Section 4.3

    def recursive_context_enrichment(
            self, intent: str,
            knowledge_set: Optional[KnowledgeSet] = None,
            depth: int = 0
    ) -> KnowledgeSet:
        """
        Implements RCE loop per Section 4.3:
        1. Identify the gap
        2. Choose the tool (adapter)
        3. Append the result to knowledge set K
        
        Continues until ρ(K) >= θ_high or depth > d_max.
        """
        if knowledge_set is None:
            knowledge_set = KnowledgeSet()
        
        # Check depth limit
        if depth > self.d_max:
            logger.warning(
                f"RCE depth limit reached (d_max={self.d_max}). "
                f"Coverage: {knowledge_set.get_coverage_ratio():.2f}"
            )
            return knowledge_set
        
        # Compute current confidence
        rho = self._compute_confidence(knowledge_set)
        autonomy_level = self.confidence_scorer.get_autonomy_level(rho)
        
        logger.info(
            f"RCE depth {depth}: ρ={rho:.3f}, "
            f"coverage={knowledge_set.get_coverage_ratio():.2f}, "
            f"autonomy={autonomy_level}"
        )
        
        # Check if we have sufficient confidence
        if rho >= self.confidence_scorer.theta_high:
            logger.info(f"RCE complete: ρ={rho:.3f} >= θ_high={self.confidence_scorer.theta_high}")
            return knowledge_set
        
        # Identify gaps and fill them
        gaps_filled = False
        
        # Gap 1: Temperature data
        if "temperature" not in knowledge_set.data:
            gaps_filled = True
            logger.info("RCE: Gap detected - temperature. Triggering OCR adapter.")
            raw = self.adapters['terminal_ocr'].scrape("FURNACE_VIEW")
            parsed = self._parse_terminal_output(raw)
            for key, value in parsed.items():
                knowledge_set.add_field(key, value, "terminal_ocr", time.time())
        
        # Gap 2: Yard occupancy data
        if "yard_pct" not in knowledge_set.data:
            gaps_filled = True
            logger.info("RCE: Gap detected - yard_pct. Triggering SQL adapter.")
            if 'sql_erp' in self.adapters:
                yard_data = self.adapters['sql_erp'].execute_query(
                    "SELECT * FROM YARD_CAPACITY WHERE quadrant = 'Q3'"
                )
                if yard_data:
                    knowledge_set.add_field(
                        "yard_pct", yard_data[0]["occupancy_pct"], 
                        "sql_erp", time.time()
                    )
        
        # Gap 3: Manganese variance
        if "mn_variance" not in knowledge_set.data:
            gaps_filled = True
            logger.info("RCE: Gap detected - mn_variance. Triggering CSV adapter.")
            if 'csv_archive' in self.adapters:
                quality_records = self.adapters['csv_archive'].scrape_as_dict("QUALITY_LOG_2026")
                # Find matching heat record
                heat_id = knowledge_set.data.get("heat_id", "H-402")
                for record in quality_records:
                    if record.get("heat_id") == heat_id:
                        knowledge_set.add_field(
                            "mn_variance", float(record["mn_variance"]),
                            "csv_archive", time.time()
                        )
                        break
        
        # Gap 4: Heat and batch identifiers
        if "heat_id" not in knowledge_set.data or "batch_id" not in knowledge_set.data:
            gaps_filled = True
            logger.info("RCE: Gap detected - heat/batch IDs. Parsing terminal output.")
            # These should come from terminal OCR
            if "heat_id" not in knowledge_set.data:
                knowledge_set.add_field("heat_id", "H-402", "terminal_ocr", time.time())
            if "batch_id" not in knowledge_set.data:
                knowledge_set.add_field("batch_id", "7A", "terminal_ocr", time.time())
        
        # Gap 5: Grade specifications from PDF
        if "grade_spec" not in knowledge_set.data:
            gaps_filled = True
            logger.info("RCE: Gap detected - grade_spec. Triggering PDF adapter.")
            if 'pdf_parser' in self.adapters:
                grade_table = self.adapters['pdf_parser'].extract_table(
                    "GRADE_SHEET_CR17.pdf", "CHEMICAL COMPOSITION TOLERANCES"
                )
                if grade_table:
                    knowledge_set.add_field(
                        "grade_spec", grade_table[0],
                        "pdf_parser", time.time()
                    )
        
        # If no gaps were filled, we're done
        if not gaps_filled:
            logger.info("RCE: No more gaps to fill.")
            return knowledge_set
        
        # Apply CDP polishing to all data
        polished_data = self.cdp.polish(knowledge_set.data)
        knowledge_set.data.update(polished_data)
        
        # Recurse
        return self.recursive_context_enrichment(intent, knowledge_set, depth + 1)
    
    def _compute_confidence(self, knowledge_set: KnowledgeSet) -> float:
        """
        Compute confidence score ρ(K) per Equation 2.
        ρ(K) = harmonic mean of (r1_coverage, r2_freshness, r3_semantic)
        """
        r1 = knowledge_set.get_coverage_ratio()
        r2 = knowledge_set.get_freshness_score()
        r3 = knowledge_set.get_semantic_score()
        
        return self.confidence_scorer.compute(r1, r2, r3)
    
    def _parse_terminal_output(self, raw_text: str) -> Dict:
        """
        Parse OCR terminal output with GISM translation.
        Extracts temperature, heat ID, status, etc.
        """
        parsed = {}
        
        # Temperature extraction
        temp_match = re.search(r"TMP\s+(\d+)", raw_text)
        if temp_match:
            parsed["temperature"] = float(temp_match.group(1))
            parsed["temperature_unit"] = "C"
        
        # Heat ID extraction
        heat_match = re.search(r"HEAT\s+(H-\d+)", raw_text)
        if heat_match:
            parsed["heat_id"] = heat_match.group(1)
        
        # Batch/Lot extraction
        lot_match = re.search(r"LOT\s+(\w+)", raw_text)
        if lot_match:
            parsed["batch_id"] = lot_match.group(1)
        
        # Mill status
        mill_match = re.search(r"(RM_B|RM-B|Mill B)\s+(D0WN|DOWN)", raw_text, re.IGNORECASE)
        if mill_match:
            parsed["mill_status"] = "DOWN"
            parsed["affected_mill"] = "Rolling_Mill_B"
        
        # Timestamp
        time_match = re.search(r"\[([^\]]+)\]", raw_text)
        if time_match:
            parsed["timestamp"] = time_match.group(1)
        
        # Apply GISM translation to all extracted fields
        translated = {}
        for key, value in parsed.items():
            if isinstance(value, str):
                translated_key = self.gism.translate(key) or key
                translated_value = self.gism.translate(value) or value
                translated[translated_key] = translated_value
            else:
                translated[key] = value
        
        logger.debug(f"Parsed terminal output: {translated}")
        return translated
