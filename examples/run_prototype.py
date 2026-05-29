"""
MALA Framework — Minimal Prototype
===================================
Mirrors the core implementation shown in Listing 1 of the paper:

    Multi-Agent Legacy Architecture (MALA):
    A Framework for Multi-Agent AI Integration in Legacy Industrial Systems
    DOI: 10.5281/zenodo.19954858

This script demonstrates the three-stage pipeline:
    Stage 1 — Recursive Context Enrichment (RCE)
    Stage 2 — LLM-based plan generation (stubbed)
    Stage 3 — CMDP Critic validation + HotL escalation
"""

import sys
import os
import io

# Ensure repository root is in sys.path so it runs seamlessly from anywhere
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
else:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import logging
from src.mala import (
    MALACore,
    GathererAgent,
    PlannerAgent,
    CriticAgent,
    SafetyConstraint,
    TerminalOCRAdapter,
    SQL92Adapter,
    CSVArchiveAdapter,
    PDFParserAdapter,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def main() -> None:
    print("=" * 60)
    print("  MALA Framework — Prototype Run")
    print("  DOI: 10.5281/zenodo.19954858")
    print("=" * 60)

    # ── Safety ledger (CMDP cost functions C1, C2, C3) ──────────────
    # Equations 3-5 in the paper; kappa=0 means hard constraint.
    safety_ledger = [
        SafetyConstraint(key="temperature", max_val=1550.0, unit="C",  kappa=0.0),
        SafetyConstraint(key="yard_pct",    max_val=85.0,   unit="%",  kappa=0.0),
        SafetyConstraint(key="mn_variance", max_val=0.08,   unit="",   kappa=0.0),
    ]

    # ── Ingestion adapters (Tier 1 — The Bridge) ─────────────────────
    adapters = {
        "terminal_ocr": TerminalOCRAdapter(simulate_unsafe=False),
        "sql_erp":       SQL92Adapter(),
        "csv_archive":   CSVArchiveAdapter(),
        "pdf_parser":    PDFParserAdapter(),
    }

    # ── Agents (Tier 2 — The Brain) ──────────────────────────────────
    gatherer = GathererAgent(adapters=adapters, theta_low=0.45, theta_high=0.80)
    critic   = CriticAgent(safety_ledger=safety_ledger)
    planner  = PlannerAgent(critic_agent=critic)   # Critic-guided planning

    # ── Orchestrator ─────────────────────────────────────────────────
    mala = MALACore(
        gatherer=gatherer,
        planner=planner,
        critic=critic,
        theta_low=0.45,
        theta_high=0.80,
    )

    # ── Execute workflow ─────────────────────────────────────────────
    task = "Re-route production schedule following Rolling Mill B failure"
    result = mala.execute_workflow(task)

    # ── Report ───────────────────────────────────────────────────────
    print(f"\nStatus    : {result['status']}")
    print(f"Confidence: ρ = {result.get('confidence', 0.0):.3f}")

    if result["status"] == "SUCCESS":
        action = result["action"]
        print(f"Action    : {action['action']}")
        print(f"Heat      : {action.get('heat_id', 'N/A')}  "
              f"Batch: {action.get('batch_id', 'N/A')}")
        print(f"Temp      : {action.get('temperature', 'N/A')} °C  "
              f"Yard: {action.get('yard_pct', 'N/A')} %  "
              f"Mn var: {action.get('mn_variance', 'N/A')}")
    elif result["status"] == "HOTL_TRIGGERED":
        print(f"Escalation: {result['reason']}")
    elif result["status"] == "SYSTEM_PAUSE":
        print(f"Pause     : {result['reason']}")

    print("\nSources used:")
    for entry in result.get("justification_log", []):
        if entry["stage"] == "RCE_COMPLETE":
            for src in entry["data"].get("sources", []):
                print(f"  • {src}")
            break

    print("\nPrototype run complete.")


if __name__ == "__main__":
    main()
