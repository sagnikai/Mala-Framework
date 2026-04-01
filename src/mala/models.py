import math
import time
from typing import Dict, Tuple, Optional
from enum import Enum


class TemperatureBin(Enum):
    """Furnace temperature discretization per Section 3.3 (CMDP State Space)."""
    SAFE = "safe"  # <= 1545°C
    WARN = "warn"  # 1545-1550°C
    CRIT = "crit"  # > 1550°C


class YardOccupancyBin(Enum):
    """Yard occupancy discretization per Section 3.3."""
    LOW = "low"    # <= 78%
    MED = "med"    # 78-83%
    HIGH = "high"  # > 83%


class ManganeseVarianceBin(Enum):
    """Manganese variance discretization per Section 3.3."""
    NOM = "nom"    # <= 0.04
    ELEV = "elev"  # 0.04-0.08
    OVER = "over"  # > 0.08


class CMDPState:
    """
    Represents the 27-state CMDP state space (Section 3.3).
    State s = (T, Y, M) where:
    - T ∈ {safe, warn, crit}
    - Y ∈ {low, med, high}
    - M ∈ {nom, elev, over}
    """
    def __init__(self, temp_bin: TemperatureBin, yard_bin: YardOccupancyBin, mn_bin: ManganeseVarianceBin):
        self.temp_bin = temp_bin
        self.yard_bin = yard_bin
        self.mn_bin = mn_bin
    
    def __repr__(self):
        return f"CMDPState(T={self.temp_bin.value}, Y={self.yard_bin.value}, M={self.mn_bin.value})"
    
    def __eq__(self, other):
        if not isinstance(other, CMDPState):
            return False
        return (self.temp_bin == other.temp_bin and 
                self.yard_bin == other.yard_bin and 
                self.mn_bin == other.mn_bin)
    
    def __hash__(self):
        return hash((self.temp_bin, self.yard_bin, self.mn_bin))
    
    @staticmethod
    def from_observations(temperature: float, yard_pct: float, mn_variance: float) -> 'CMDPState':
        """Discretize continuous observations into CMDP state bins."""
        # Temperature binning
        if temperature <= 1545:
            temp_bin = TemperatureBin.SAFE
        elif temperature <= 1550:
            temp_bin = TemperatureBin.WARN
        else:
            temp_bin = TemperatureBin.CRIT
        
        # Yard occupancy binning
        if yard_pct <= 78:
            yard_bin = YardOccupancyBin.LOW
        elif yard_pct <= 83:
            yard_bin = YardOccupancyBin.MED
        else:
            yard_bin = YardOccupancyBin.HIGH
        
        # Manganese variance binning
        if mn_variance <= 0.04:
            mn_bin = ManganeseVarianceBin.NOM
        elif mn_variance <= 0.08:
            mn_bin = ManganeseVarianceBin.ELEV
        else:
            mn_bin = ManganeseVarianceBin.OVER
        
        return CMDPState(temp_bin, yard_bin, mn_bin)


class CMDPAction(Enum):
    """
    Action set A = {a1, a2, a3, a4} per Section 3.3.`n    Maps to: immediate_reroute, hold_dispatch_reroute, hold_only, escalate_judge.
    """
    IMMEDIATE_REROUTE = "a1"           # Immediate reroute
    HOLD_DISPATCH_REROUTE = "a2"       # Hold, dispatch, then reroute
    HOLD_ONLY = "a3"                   # Hold only
    ESCALATE_JUDGE = "a4"              # Escalate to Judge


class SafetyConstraint:
    """Single CMDP hard-bound constraint.
    Maps one process variable to its maximum
    admissible value (e.g., 1550 deg-C limit).
    Implements cost functions C_i(s,a) per Equations 3-5.
    """
    def __init__(self, key: str, max_val: float, unit: str, kappa: float = 0.0):
        self.key = key
        self.max_val = max_val
        self.unit = unit
        self.kappa = kappa  # Constraint threshold (default 0 = hard constraint)

    def check(self, value: float) -> bool:
        """Returns True if constraint is satisfied."""
        return value <= self.max_val
    
    def cost(self, value: float) -> float:
        """
        Compute constraint cost C_i(s,a) as indicator function.
        Returns 1.0 if violated, 0.0 otherwise.
        """
        return 1.0 if value > self.max_val else 0.0


class FreshnessScore:
    """
    Implements Equation 1: F(Δt) = exp(-λ * Δt)
    where λ = 0.05 min^-1 and Δt is time since last refresh.
    """
    def __init__(self, lambda_decay: float = 0.05):
        self.lambda_decay = lambda_decay
        self.threshold = 0.47  # F < 0.47 triggers refresh (≈15 min)
    
    def compute(self, delta_t_minutes: float) -> float:
        """Compute freshness score for given staleness."""
        return math.exp(-self.lambda_decay * delta_t_minutes)
    
    def needs_refresh(self, delta_t_minutes: float) -> bool:
        """Check if data needs refresh based on threshold."""
        return self.compute(delta_t_minutes) < self.threshold


class ConfidenceScore:
    """
    Implements Equation 2: ρ(K) = harmonic mean of three sub-scores.
    ρ(K) = (1/3 * Σ(r_j^-1))^-1 where:
    - r1: source-coverage ratio
    - r2: freshness score
    - r3: semantic-match score
    """
    def __init__(self, theta_low: float = 0.45, theta_high: float = 0.80):
        self.theta_low = theta_low
        self.theta_high = theta_high
    
    def compute(self, r1_coverage: float, r2_freshness: float, r3_semantic: float) -> float:
        """
        Compute harmonic mean confidence score.
        All r_j must be in (0, 1].
        """
        if r1_coverage <= 0 or r2_freshness <= 0 or r3_semantic <= 0:
            return 0.0
        
        harmonic_sum = (1.0 / r1_coverage) + (1.0 / r2_freshness) + (1.0 / r3_semantic)
        return 3.0 / harmonic_sum
    
    def get_autonomy_level(self, rho: float) -> str:
        """
        Determine autonomy level based on confidence thresholds.
        Returns: 'silent', 'approval', or 'pause'
        """
        if rho >= self.theta_high:
            return "silent"  # Silent autonomy
        elif rho >= self.theta_low:
            return "approval"  # Explicit approval required
        else:
            return "pause"  # System pause


class KnowledgeSet:
    """
    Represents the enriched knowledge set K assembled by RCE.
    Tracks source coverage, timestamps, and semantic matches.
    """
    def __init__(self):
        self.data: Dict = {}
        self.sources: Dict[str, Dict] = {}  # source_name -> {timestamp, data}
        self.required_fields = {"temperature", "yard_pct", "mn_variance", "heat_id", "batch_id"}
        self.ingestion_times: Dict[str, float] = {}  # field -> timestamp
    
    def add_field(self, field: str, value, source: str, timestamp: Optional[float] = None):
        """Add a field to the knowledge set with provenance tracking."""
        self.data[field] = value
        if timestamp is None:
            timestamp = time.time()
        self.ingestion_times[field] = timestamp
        
        if source not in self.sources:
            self.sources[source] = {"timestamp": timestamp, "fields": []}
        self.sources[source]["fields"].append(field)
    
    def get_coverage_ratio(self) -> float:
        """Compute r1: fraction of required fields filled."""
        filled = len(self.required_fields.intersection(self.data.keys()))
        return filled / len(self.required_fields) if self.required_fields else 1.0
    
    def get_freshness_score(self, current_time: Optional[float] = None) -> float:
        """Compute r2: minimum freshness across all fields."""
        if not self.ingestion_times:
            return 0.0
        
        if current_time is None:
            current_time = time.time()
        
        freshness_calc = FreshnessScore()
        min_freshness = 1.0
        
        for field, ingest_time in self.ingestion_times.items():
            delta_minutes = (current_time - ingest_time) / 60.0
            freshness = freshness_calc.compute(delta_minutes)
            min_freshness = min(min_freshness, freshness)
        
        return min_freshness
    
    def get_semantic_score(self) -> float:
        """
        Compute r3: semantic match score.
        In production, this would use embedding similarity.
        For prototype, we return 0.85 if all required fields present.
        """
        coverage = self.get_coverage_ratio()
        return 0.85 if coverage >= 0.8 else coverage * 0.85


class JustificationLog:
    """
    Audit trail for Human-on-the-Loop review (Section 4.4).
    Records source rows, translations, rule checks, and decisions.
    """
    def __init__(self):
        self.entries = []
    
    def add_entry(self, stage: str, data: Dict):
        """Add a timestamped entry to the log."""
        entry = {
            "timestamp": time.time(),
            "stage": stage,
            "data": data
        }
        self.entries.append(entry)
    
    def get_full_log(self) -> list:
        """Return complete audit trail."""
        return self.entries
    
    def format_for_judge(self) -> str:
        """Format log for human review."""
        lines = ["=== JUSTIFICATION LOG ==="]
        for entry in self.entries:
            lines.append(f"\n[{entry['stage']}] at {entry['timestamp']}")
            lines.append(f"  {entry['data']}")
        return "\n".join(lines)
