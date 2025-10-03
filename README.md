# MALA: Multi-Agent Legacy Architecture

**A Framework for Multi-Agent AI Integration in Legacy Industrial Systems**

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.19954858.svg)](https://doi.org/10.5281/zenodo.19954858)

## Abstract

The **Multi-Agent Legacy Architecture (MALA)** framework addresses the critical challenge of integrating agentic artificial intelligence into legacy industrial environments that lack modern Application Programming Interfaces (APIs). By treating legacy software systems—including terminal interfaces, comma-separated value (CSV) archives, and scanned Portable Document Format (PDF) files—as a dynamic operational surface rather than a static data repository, MALA enables autonomous decision support while maintaining rigorous, deterministic safety guarantees through a Constrained Markov Decision Process (CMDP) formulation.

Empirical evaluation at a 50-year-old European steel manufacturing site demonstrated significant operational improvements: a **26.6× reduction in decision-support latency** (from 320 to 12 minutes), a **98% task success rate** across 50 disruption cycles, an **88% reduction in human correction ratio**, and **zero safety violations** under supervised replay conditions. The framework integrates Recursive Context Enrichment (RCE), CMDP-based safety filtering, confidence-gated autonomy thresholds, and Human-on-the-Loop (HotL) escalation into a single auditable workflow.

## Citation

If you use the MALA framework in your research, please cite the foundational paper:

```bibtex
@article{mukherjee2026mala,
  title={Multi-Agent Legacy Architecture (MALA): A Framework for Multi-Agent AI Integration in Legacy Industrial Systems},
  author={Mukherjee, Sagnik},
  year={2026},
  journal={Preprint},
  doi={10.5281/zenodo.19954858},
  url={https://doi.org/10.5281/zenodo.19954858}
}
```

## System Architecture

MALA implements a three-tier architecture that isolates ingestion, cognitive planning, and human oversight, as illustrated in Figure 1 of the paper.

### Tier 1: Ingestion Layer ("The Bridge")

The Ingestion Layer functions as the primary integration interface between legacy systems and the orchestration layer. It employs heterogeneous adapters to normalize unstructured and semi-structured data into a unified JSON-LD context representation:

- **OCR Terminal Adapter**: Extracts text from legacy terminal emulators via Optical Character Recognition
- **SQL-92 Connector**: Interfaces with 1990s-era Enterprise Resource Planning (ERP) databases
- **CSV Archive Parser**: Reads flat-file quality logs from legacy workstations
- **PDF Document Extractor**: Processes scanned metallurgical specifications and logistics schedules

### Tier 2: Orchestration Layer ("The Brain")

The Orchestration Layer implements a multi-agent cognitive architecture with three specialized roles:

#### Gatherer Agent: Recursive Context Enrichment (RCE)

Implements the RCE algorithm (Section 4.3) to dynamically traverse siloed legacy systems and reconstruct missing state information. The agent iterates until either:
- The confidence score ρ(K) exceeds the high threshold θ_high (Equation 2), or
- The recursion depth limit d_max = 3 is reached

**Confidence Score Computation** (Equation 2):
```
ρ(K) = (1/3 · Σ(r_j^-1))^-1
```
where:
- r₁: source-coverage ratio (fraction of required fields filled)
- r₂: freshness score F(Δt) = exp(-λΔt) with λ = 0.05 min⁻¹ (Equation 1)
- r₃: semantic-match score (embedding cosine similarity)

#### Planner Agent: LLM-Based Plan Generation

Synthesizes enriched context from the Gatherer into sequential operational plans. In the prototype implementation, the Planner queries the Critic for CMDP-recommended actions before proposing, implementing a "Critic-guided planning" pattern that reduces rejected proposals.

#### Critic Agent: CMDP Safety Filter

Operates as a deterministic safety verifier implementing the solved CMDP policy π* from Table 2 of the paper. The Critic enforces three hard constraints (κᵢ = 0):

**Cost Functions** (Equations 3-5):
- C₁(s,a): Furnace over-temperature indicator (T > 1550°C)
- C₂(s,a): Yard congestion indicator (Y > 85%)
- C₃(s,a): Manganese out-of-spec indicator (Mn variance > 0.08)

**State Space**: 27 discrete states s = (T, Y, M) where:
- T ∈ {safe, warn, crit}: Temperature bins (≤1545°C, 1545-1550°C, >1550°C)
- Y ∈ {low, med, high}: Yard occupancy bins (≤78%, 78-83%, >83%)
- M ∈ {nom, elev, over}: Manganese variance bins (≤0.04, 0.04-0.08, >0.08)

**Action Set**: A = {a₁, a₂, a₃, a₄}
- a₁: Immediate reroute
- a₂: Hold, dispatch, then reroute
- a₃: Hold only
- a₄: Escalate to Judge

The Critic vetoes any proposed action that does not match π*(s) for the observed state, ensuring that every executed plan satisfies all safety constraints.

### Tier 3: Interface Layer ("The Human Filter")

Implements the Human-on-the-Loop (HotL) paradigm with tiered verification rules keyed to confidence score ρ:

- **ρ ≥ θ_high (0.80)**: Silent autonomy—system proceeds and logs action for later review
- **θ_low (0.45) ≤ ρ < θ_high**: Explicit approval—Judge receives Justification Log and must approve
- **ρ < θ_low**: System pause—exposes missing evidence and requests guidance

The Judge verification function V(ŷ, K) receives:
- Complete Justification Log (source rows, translations, rule checks)
- Freshness Score for each evidence field
- Confidence Score ρ with sub-score breakdown
- Proposed action with CMDP state context
- Raw knowledge set K with source provenance

## Repository Structure

```
mala-framework/
├── src/
│   └── mala/                      # Core MALA implementation
│       ├── adapters/              # Legacy system integration adapters
│       │   ├── base.py           # Abstract adapter interface
│       │   ├── ocr.py            # Terminal OCR adapter
│       │   ├── csv_adapter.py    # CSV archive parser
│       │   ├── pdf_adapter.py    # PDF document extractor
│       │   └── sql_adapter.py    # SQL-92 ERP connector
│       ├── agents/                # Multi-agent orchestration
│       │   ├── gatherer.py       # RCE implementation
│       │   ├── planner.py        # LLM-based plan generation
│       │   └── critic.py         # CMDP safety filter
│       ├── models.py              # Core data structures (CMDP, constraints, scores)
│       ├── gism.py                # Global Industrial Semantic Model (420 entries)
│       ├── cdp.py                 # Contextual Data Polishing
│       └── core.py                # MALACore orchestrator
├── run_comprehensive_demo.py      # Full demonstration script
├── run_prototype.py               # Simple prototype demonstration
├── requirements.txt               # Python dependencies
├── README.md                      # This file
└── Academic Paper/
    └── main-revised.tex           # IEEE-format source paper
```

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Setup

1. Clone the repository:
```bash
git clone https://github.com/sagnikai/Mala-Framework.git
cd Mala-Framework
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Comprehensive Demonstration

Run the full demonstration showcasing all framework components:

```bash
python run_comprehensive_demo.py
```

This script demonstrates:
1. **Silent Autonomy**: High-confidence execution without human intervention
2. **Explicit Approval**: Medium-confidence escalation to Judge
3. **Safety Violation**: Critic veto of unsafe plan (temperature > 1550°C)
4. **System Pause**: Low-confidence pause with missing evidence exposure

### Programmatic Usage

```python
from src.mala import (
    MALACore, GathererAgent, PlannerAgent, CriticAgent,
    SafetyConstraint, TerminalOCRAdapter, CSVArchiveAdapter,
    PDFParserAdapter, SQL92Adapter
)

# 1. Define safety constraints (CMDP cost functions)
safety_ledger = [
    SafetyConstraint(key="temperature", max_val=1550.0, unit="C", kappa=0.0),
    SafetyConstraint(key="yard_pct", max_val=85.0, unit="%", kappa=0.0),
    SafetyConstraint(key="mn_variance", max_val=0.08, unit="", kappa=0.0)
]

# 2. Initialize legacy system adapters
adapters = {
    "terminal_ocr": TerminalOCRAdapter(),
    "sql_erp": SQL92Adapter(),
    "csv_archive": CSVArchiveAdapter(),
    "pdf_parser": PDFParserAdapter()
}

# 3. Instantiate agents
gatherer = GathererAgent(adapters=adapters, theta_low=0.45, theta_high=0.80)
critic = CriticAgent(safety_ledger=safety_ledger)
planner = PlannerAgent(critic_agent=critic)

# 4. Initialize MALA orchestrator
mala = MALACore(
    gatherer=gatherer,
    planner=planner,
    critic=critic,
    theta_low=0.45,
    theta_high=0.80
)

# 5. Execute workflow
result = mala.execute_workflow(
    task="Re-route production schedule following Rolling Mill B failure"
)

# 6. Inspect result
print(f"Status: {result['status']}")
print(f"Confidence ρ: {result['confidence']:.3f}")
if result['status'] == 'SUCCESS':
    print(f"Action: {result['action']['action']}")
elif result['status'] == 'HOTL_TRIGGERED':
    print(f"Escalation: {result['reason']}")
    print(f"Justification Log: {result['justification_log_formatted']}")
```

## Key Components

### 1. Recursive Context Enrichment (RCE)

**Algorithm** (Section 4.3):
```
1. Identify the gap: Determine which variable is missing
2. Choose the tool: Call appropriate adapter (OCR, SQL, CSV, PDF)
3. Append the result: Normalize to JSON-LD and add to knowledge set K
4. Repeat until ρ(K) ≥ θ_high or depth > d_max
```

### 2. CMDP Safety Filtering

**Lagrangian Formulation** (Equation 6):
```
min_{λ≥0} max_π E_π[Σ γ^t R_t] - Σ λᵢ(E_π[Σ γ^t C_{i,t}] - κᵢ)
```

With κᵢ = 0 (hard constraints), any action driving a variable into its violation bin acquires infinite penalty, removing it from π*.

### 3. Global Industrial Semantic Model (GISM)

Implements ontological mapping function φ: L_local → L_standard with 420 validated concept mappings. Example mappings:

| Local Term | Standard Term |
|------------|---------------|
| TMP | temperature |
| RM_B | Rolling_Mill_B |
| H-402 | Heat_402 |
| Var-Low | variance_below_threshold |
| D0WN | system_down |

Coverage: 85% of observed terms (Section 5.8). Unmapped terms trigger LLM-based fallback inference with mandatory Judge review.

### 4. Contextual Data Polishing (CDP)

Applies three cleaning rules (Section 4.6):
1. **Unit normalization**: Convert metric, imperial, and local units to plant-wide standard
2. **Temporal reconciliation**: Reconstruct true state when timestamps disagree across systems
3. **Sensitive-field stripping**: Remove personal data before optional remote model use

## Evaluation Results

From the 50-cycle retrospective replay study (Section 5):

| Metric | Manual Baseline | Fully Agentic | MALA |
|--------|----------------|---------------|------|
| Success Rate | 84% (42/50) | 72% (36/50) | **98% (49/50)** |
| Mean Latency | 320 min | 4 min | **12 min** |
| Median Latency | 305 min | 4 min | **10 min** |
| Safety Violations | 2 | 14 | **0** |
| Human Correction Ratio | 100% (50/50) | 0% (0/50) | **12% (6/50)** |

**Key Findings**:
- **26.6× latency reduction** compared to manual baseline
- **88 percentage-point reduction** in human correction ratio
- **Zero safety violations** across all 50 cycles with Critic enforcement
- **6 Judge escalations** (12% HCR) concentrated in high-uncertainty cycles

## Limitations

1. **Terminal UI Stability**: Depends on stable OCR output; UI changes require adapter retraining
2. **GISM Coverage**: 85% coverage of observed terms; 15% trigger LLM fallback with Judge review
3. **Recursion Depth**: d_max = 3 limits queries requiring >3 cross-system lookups
4. **Compute Overhead**: 3-5× cost vs. single LLM call (~$0.30-$0.40 per cycle at GPT-4 pricing)
5. **Evaluation Mode**: Replay/shadow protocol, not autonomous live actuation

## Future Work

1. Test small language models (SLMs) on local factory hardware for offline reasoning
2. Define cross-firm agent protocols preserving data sovereignty
3. Build self-healing adapters that relearn UI changes after legacy software updates
4. Extend adapter set to mount offline-archived records on demand
5. Replicate 50-cycle study on additional disruption classes and industrial sites

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Author

**Sagnik Mukherjee**  
Independent Researcher  
ORCID: [0009-0002-4111-6299](https://orcid.org/0009-0002-4111-6299)

## Acknowledgments

This work builds on prior research in:
- Constrained Policy Optimization (Achiam et al., 2017)
- Distributional Safety Critics (Yang et al., 2023)
- Legacy System Modernization (Comella-Dorda et al., 2000)
- Ontology-Based Interoperability (Fraga et al., 2020)
- Human-in-the-Loop Cyber-Physical Systems (Gil et al., 2019)

## References

For complete references, see the bibliography in `Academic Paper/main-revised.tex` or the published paper at DOI: [10.5281/zenodo.19954858](https://doi.org/10.5281/zenodo.19954858).

## Contact

For questions, issues, or collaboration inquiries, please open an issue on the GitHub repository or contact the author via ORCID.

---

**DOI**: [10.5281/zenodo.19954858](https://doi.org/10.5281/zenodo.19954858)  
**Repository**: [github.com/sagnikai/Mala-Framework](https://github.com/sagnikai/Mala-Framework)  
**Version**: 1.0.0  
**Last Updated**: May 2026
