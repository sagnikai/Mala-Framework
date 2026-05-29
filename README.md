# MALA: Multi-Agent Legacy Architecture

**A Framework for Multi-Agent AI Integration in Legacy Industrial Systems**

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.19954858.svg)](https://doi.org/10.5281/zenodo.19954858)

## Data Availability

The archival version of this paper and the framework source code are deposited at Zenodo: [10.5281/zenodo.19954858](https://doi.org/10.5281/zenodo.19954858). The underlying 50-cycle Rolling Mill B disruption archive is proprietary plant data and cannot be redistributed; the replay protocol and all evaluation scripts are included in this repository.

## Overview

MALA connects multi-agent AI to legacy industrial systems without requiring API modernization. It treats legacy software interfaces---terminal screens, CSV archives, and scanned PDF documents---as a queryable operational surface, supporting autonomous decision-making under formally verified safety constraints.

## Abstract

The **Multi-Agent Legacy Architecture (MALA)** framework addresses the problem of connecting agentic AI to legacy industrial systems that expose no modern APIs. Rather than treating legacy software---terminal interfaces, CSV archives, and scanned PDF files---as a static data store, MALA reads them as a live operational surface and supports autonomous decision-making through a Constrained Markov Decision Process (CMDP) safety filter.

A 50-cycle retrospective replay study at a 50-year-old European steel site produced the following results: a **26.6× reduction in decision-support latency** (from 320 to 12 minutes), a **98% task success rate**, an **88% reduction in human correction ratio**, and **zero safety violations** under supervised replay conditions. The framework combines Recursive Context Enrichment (RCE), CMDP-based safety filtering, confidence-gated autonomy thresholds, and Human-on-the-Loop (HotL) escalation in one auditable workflow.

## Citation

If you use MALA in your research, please cite the foundational paper:

```bibtex
@misc{mukherjee2026mala,
  title={Multi-Agent Legacy Architecture (MALA): A Framework for Multi-Agent AI Integration in Legacy Industrial Systems},
  author={Mukherjee, Sagnik},
  year={2026},
  note={Preprint, Zenodo},
  doi={10.5281/zenodo.19954858},
  url={https://doi.org/10.5281/zenodo.19954858}
}
```

## System Architecture

MALA uses a three-tier architecture that separates ingestion, planning, and human oversight, as shown in Figure 1 of the paper.

### Tier 1: Ingestion Layer ("The Bridge")

The Ingestion Layer reads legacy data sources of mixed types and converts them into a unified knowledge set *K*. Modality-specific adapters translate raw legacy outputs---terminal screen text, CSV records, and scanned PDF documents---into normalized JSON-LD objects. The Recursive Context Enrichment (RCE) procedure calls these adapters in a loop until the confidence score *ρ(K)* reaches the high-confidence threshold *θ_high* or the maximum recursion depth *d_max* is reached.

### Tier 2: Orchestration Layer ("The Brain")

The Orchestration Layer holds the three agents that form the MALA decision pipeline:

- **Gatherer**: Issues tool calls to the Tier 1 adapters and assembles the enriched knowledge set *K*.
- **Planner**: Reads *K* and proposes a ranked set of candidate corrective actions *A*.
- **Critic**: Checks each candidate action against the CMDP safety policy *π\**, applying Lagrangian safety filters. Any action that violates a hard constraint (*κᵢ = 0*) is removed from the feasible action set.

The `MALACore` orchestrator runs these three agents in a fixed sequential pipeline, applies confidence-gated autonomy thresholds, and manages transitions between autonomous execution and Human-on-the-Loop escalation.

### Tier 3: Human Interface Layer ("The Dashboard")

The Human Interface Layer runs the Human-on-the-Loop (HotL) escalation protocol. When the confidence score *ρ* falls below the low-confidence threshold *θ_low*, or when a safety constraint is violated, the system escalates to a human Judge. The Judge receives a justification log containing the knowledge set, the proposed action, and the Critic's constraint evaluation, which supports an informed approval or override decision. All escalation events are logged for later review.

## Repository Structure

```
Mala-Framework/
├── README.md                        # This document
├── LICENSE                          # MIT License
├── requirements.txt                 # Python dependencies
├── Academic Paper/
│   └── main-revised.tex             # LaTeX source of the foundational paper
├── src/
│   └── mala/
│       ├── __init__.py              # Public API surface
│       ├── core.py                  # MALACore orchestrator
│       ├── models.py                # Data models (FreshnessScore, CMDPState, etc.)
│       ├── cdp.py                   # Contextual Data Polishing module
│       ├── gism.py                  # Global Industrial Semantic Model
│       ├── agents/                  # Gatherer, Planner, Critic agents
│       └── adapters/                # Legacy I/O adapters (OCR, CSV, PDF, SQL)
├── examples/
│   ├── run_prototype.py             # Minimal single-scenario prototype
│   └── run_comprehensive_demo.py    # Full 50-cycle evaluation demo
└── tests/
    ├── test_mala.py                 # Unit test suite (equations, agents, workflows)
    └── run_tests.py                 # Standalone test runner (no pytest required)
```

## Installation

MALA has no required external dependencies — the core framework runs entirely on the Python standard library, which keeps it reproducible in air-gapped and compute-constrained research environments. Optional dependencies for live LLM calls and production-grade OCR/PDF/SQL adapters are listed in `requirements.txt`.

```bash
# Clone the repository
git clone https://github.com/sagnikai/Mala-Framework.git
cd Mala-Framework

# (Optional) Install optional dependencies for additional adapter functionality
pip install -r requirements.txt
```

> **Python version**: 3.8 or higher is required.

## Usage

### Minimal Example

```python
import sys
sys.path.insert(0, "src")  # Ensure the package is on the path

from mala import MALACore

# 1. Instantiate the orchestrator with default thresholds
mala = MALACore(
    theta_low=0.40,
    theta_high=0.80
)

# 2. Execute a disruption-recovery workflow
result = mala.execute_workflow(
    task="Re-route production schedule following Rolling Mill B failure"
)

# 3. Inspect the result
print(f"Status    : {result['status']}")
print(f"Confidence: {result['confidence']:.3f}")

if result['status'] == 'SUCCESS':
    print(f"Action    : {result['action']['action']}")
elif result['status'] == 'HOTL_TRIGGERED':
    print(f"Escalation: {result['reason']}")
    print(f"Justification Log:\n{result['justification_log_formatted']}")
```

### Running the Comprehensive Demo

```bash
python examples/run_comprehensive_demo.py
```

### Running the Unit Test Suite

```bash
python tests/run_tests.py
```

## Primary Components

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

With κᵢ = 0 (hard constraints), any action that drives a variable into its violation bin receives an infinite penalty and is removed from π*.

### 3. Global Industrial Semantic Model (GISM)

The GISM is an ontological mapping function φ: L_local → L_standard with 420 validated concept mappings. Example mappings:

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
1. **Unit normalization**: Convert metric, imperial, and local units to a plant-wide standard
2. **Temporal reconciliation**: Reconstruct the true state when timestamps disagree across systems
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

> **Note**: Full statistical results including 95% Wilson confidence intervals for all binary outcomes are reported in Table II of the paper (DOI: [10.5281/zenodo.19954858](https://doi.org/10.5281/zenodo.19954858)).

**Summary**:
- **26.6× latency reduction** compared to the manual baseline
- **88 percentage-point reduction** in human correction ratio
- **Zero safety violations** across all 50 cycles with Critic enforcement
- **6 Judge escalations** (12% HCR) concentrated in high-uncertainty cycles

## Limitations

1. **Terminal UI Stability**: Depends on stable OCR output; UI changes require adapter retraining
2. **GISM Coverage**: 85% coverage of observed terms; 15% trigger LLM fallback with Judge review
3. **Recursion Depth**: d_max = 3 limits queries requiring more than 3 cross-system lookups
4. **Compute Overhead**: 3--5× cost vs. a single LLM call (~$0.30--$0.40 per cycle at GPT-4 pricing)
5. **Evaluation Mode**: Replay/shadow protocol, not autonomous live actuation

## Next Steps

1. Test small language models (SLMs) on local factory hardware for offline reasoning
2. Define cross-firm agent protocols that preserve data sovereignty
3. Build self-healing adapters that relearn UI changes after legacy software updates
4. Extend the adapter set to mount offline-archived records on demand
5. Replicate the 50-cycle study on additional disruption classes and industrial sites

## AI Use Disclosure

The final draft of this paper, the repository content, and all associated scripts were produced from my own knowledge, findings, and research. 
Generative AI tools (self-hosted Ollama infrastructure running open-weight models including Gemma and OSS variants) were used solely for initial brainstorming, placeholder content during early drafting stages, and minor proofreading assistance. No AI-generated text appears in the final manuscript. All intellectual contributions, analysis, and conclusions are the author's own. This disclosure is made in accordance with IEEE policy on the use of artificial intelligence in scholarly publications.

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

<!-- Last updated: May 2026 -->
