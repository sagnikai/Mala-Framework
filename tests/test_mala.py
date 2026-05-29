import pytest
import math
import time
from src.mala import (
    MALACore,
    GathererAgent,
    PlannerAgent,
    CriticAgent,
    SafetyConstraint,
    CMDPState,
    CMDPAction,
    TemperatureBin,
    YardOccupancyBin,
    ManganeseVarianceBin,
    FreshnessScore,
    ConfidenceScore,
    KnowledgeSet,
    JustificationLog,
    GISM,
    ContextualDataPolisher,
    TerminalOCRAdapter,
    CSVArchiveAdapter,
    PDFParserAdapter,
    SQL92Adapter
)

# -------------------------------------------------------------------------
# 1. Freshness Score Tests (Equation 1)
# -------------------------------------------------------------------------
def test_freshness_score():
    scorer = FreshnessScore(lambda_decay=0.05)
    
    # Delta t = 0 min -> Freshness = e^0 = 1.0
    assert pytest.approx(scorer.compute(0.0), abs=1e-5) == 1.0
    
    # Delta t = 15 min -> Freshness = e^(-0.05 * 15) = e^(-0.75) ≈ 0.47237
    assert pytest.approx(scorer.compute(15.0), abs=1e-4) == 0.4724
    
    # Delta t = 30 min -> Freshness = e^(-0.05 * 30) = e^(-1.5) ≈ 0.22313
    assert pytest.approx(scorer.compute(30.0), abs=1e-4) == 0.2231
    
    # Check needs_refresh: threshold is 0.47 (approx 15 min)
    # 14 minutes is under threshold -> needs_refresh = False (freshness approx 0.4966)
    assert not scorer.needs_refresh(14.0)
    # 16 minutes is over threshold -> needs_refresh = True (freshness approx 0.4493)
    assert scorer.needs_refresh(16.0)


# -------------------------------------------------------------------------
# 2. Confidence Score Tests (Equation 2)
# -------------------------------------------------------------------------
def test_confidence_score():
    scorer = ConfidenceScore(theta_low=0.45, theta_high=0.80)
    
    # If any score is <= 0, return 0.0
    assert scorer.compute(0.0, 1.0, 1.0) == 0.0
    assert scorer.compute(1.0, -0.5, 1.0) == 0.0
    
    # Case from demo/paper: r1 = 1.0 (coverage), r2 = 1.0 (freshness), r3 = 0.85 (semantic)
    # ρ(K) = (1/3 * (1/1.0 + 1/1.0 + 1/0.85))^-1
    #       = 3 / (1 + 1 + 1.17647) = 3 / 3.17647 ≈ 0.94444
    rho = scorer.compute(1.0, 1.0, 0.85)
    assert pytest.approx(rho, abs=1e-4) == 0.9444
    
    # Autonomy level mappings
    assert scorer.get_autonomy_level(0.95) == "silent"      # >= theta_high (0.80)
    assert scorer.get_autonomy_level(0.80) == "silent"      # >= theta_high (0.80)
    assert scorer.get_autonomy_level(0.60) == "approval"    # theta_low <= rho < theta_high
    assert scorer.get_autonomy_level(0.45) == "approval"    # theta_low <= rho < theta_high
    assert scorer.get_autonomy_level(0.30) == "pause"       # < theta_low


# -------------------------------------------------------------------------
# 3. CMDP State Discretization Tests (Section 3.3.1)
# -------------------------------------------------------------------------
def test_cmdp_state_discretization():
    # Bin limits:
    # T: safe (<=1545), warn (1545-1550), crit (>1550)
    # Y: low (<=78), med (78-83), high (>83)
    # M: nom (<=0.04), elev (0.04-0.08), over (>0.08)
    
    state1 = CMDPState.from_observations(1540.0, 75.0, 0.03)
    assert state1.temp_bin == TemperatureBin.SAFE
    assert state1.yard_bin == YardOccupancyBin.LOW
    assert state1.mn_bin == ManganeseVarianceBin.NOM
    
    state2 = CMDPState.from_observations(1548.0, 80.0, 0.06)
    assert state2.temp_bin == TemperatureBin.WARN
    assert state2.yard_bin == YardOccupancyBin.MED
    assert state2.mn_bin == ManganeseVarianceBin.ELEV
    
    state3 = CMDPState.from_observations(1555.0, 85.0, 0.09)
    assert state3.temp_bin == TemperatureBin.CRIT
    assert state3.yard_bin == YardOccupancyBin.HIGH
    assert state3.mn_bin == ManganeseVarianceBin.OVER
    
    # Equality and hashing
    state1_duplicate = CMDPState(TemperatureBin.SAFE, YardOccupancyBin.LOW, ManganeseVarianceBin.NOM)
    assert state1 == state1_duplicate
    assert hash(state1) == hash(state1_duplicate)
    assert state1 != state2


# -------------------------------------------------------------------------
# 4. Contextual Data Polisher Tests (Section 4.6)
# -------------------------------------------------------------------------
def test_cdp_polishing():
    polisher = ContextualDataPolisher()
    
    # Test physical measurements detection and conversion
    assert polisher._is_measurement_field("furnace_temp", "1548C")
    assert polisher._is_measurement_field("yard_load", "79.0 %")
    # Reject identifiers even if they end in a letter
    assert not polisher._is_measurement_field("heat_id", "7A")
    assert not polisher._is_measurement_field("batch_id", "H-402")
    
    # Test unit conversions
    # Fahrenheit to Celsius
    val, unit = polisher._normalize_units("temp", "77 F")
    assert val == 25.0
    assert unit == "C"
    
    # PSI to bar
    val, unit = polisher._normalize_units("press", "100 psi")
    assert pytest.approx(val, abs=1e-4) == 6.89476
    assert unit == "bar"
    
    # Feet to meters
    val, unit = polisher._normalize_units("len", "10 ft")
    assert pytest.approx(val, abs=1e-4) == 3.048
    assert unit == "m"
    
    # Sensitive-field stripping
    raw_record = {
        "heat_id": "H-402",
        "operator_name": "John Doe",
        "ssn": "123-456-789",
        "temperature": "1548 C"
    }
    polished = polisher.polish(raw_record)
    assert polished["operator_name"] == "[REDACTED]"
    assert polished["ssn"] == "[REDACTED]"
    assert polished["temperature"] == 1548.0
    assert polished["temperature_unit"] == "C"
    
    # Temporal reconciliation
    conflicting_record = {
        "timestamp_erp": "2026-04-27T09:45:00Z",
        "timestamp_csv": "2026-04-27T10:15:00Z"
    }
    reconciled = polisher.polish(conflicting_record)
    assert reconciled["canonical_timestamp"] == "2026-04-27T10:15:00"
    assert reconciled["timestamp_source"] == "timestamp_csv"


# -------------------------------------------------------------------------
# 5. GISM Ontological Mapping Tests (Section 4.5)
# -------------------------------------------------------------------------
def test_gism_translation():
    gism = GISM()
    
    # Exact mappings
    assert gism.translate("TMP") == "temperature"
    assert gism.translate("RM_B") == "Rolling_Mill_B"
    assert gism.translate("D0WN") == "system_down"
    
    # Case-insensitive matching
    assert gism.translate("tmp") == "temperature"
    assert gism.translate("rm_b") == "Rolling_Mill_B"
    
    # LLM fallback
    mock_llm_fallback = lambda x: f"inferred_{x.lower()}"
    term, required_review = gism.translate_with_fallback("UNKNOWN_JARGON", mock_llm_fallback)
    assert term == "inferred_unknown_jargon"
    assert required_review is True
    
    # Normal translate returns None for unmapped terms
    assert gism.translate("UNKNOWN_JARGON") is None


# -------------------------------------------------------------------------
# 6. Critic Safety Tests (Section 3.3)
# -------------------------------------------------------------------------
def test_critic_safety():
    safety_ledger = [
        SafetyConstraint(key="temperature", max_val=1550.0, unit="C", kappa=0.0),
        SafetyConstraint(key="yard_pct", max_val=85.0, unit="%", kappa=0.0),
        SafetyConstraint(key="mn_variance", max_val=0.08, unit="", kappa=0.0)
    ]
    critic = CriticAgent(safety_ledger=safety_ledger)
    
    # Safe plan
    safe_plan = {
        "temperature": 1540.0,
        "yard_pct": 75.0,
        "mn_variance": 0.03,
        "action": "immediate_reroute"
    }
    is_safe, msg = critic.validate_proposal(safe_plan)
    assert is_safe
    assert msg == "SAFE"
    
    # Unsafe plan - constraint violation (furnace temperature over-temp)
    unsafe_plan1 = {
        "temperature": 1580.0,
        "yard_pct": 75.0,
        "mn_variance": 0.03,
        "action": "immediate_reroute"
    }
    is_safe, msg = critic.validate_proposal(unsafe_plan1)
    assert not is_safe
    assert "CONSTRAINT VIOLATION: temperature" in msg
    
    # Unsafe plan - policy violation (SAFE, MED, NOM) require hold_dispatch_reroute (a2)
    # Proposing immediate_reroute (a1) instead
    unsafe_plan2 = {
        "temperature": 1540.0,
        "yard_pct": 80.0,  # MED bin (78-83)
        "mn_variance": 0.03, # NOM bin
        "action": "immediate_reroute" # Policy is hold_dispatch_reroute
    }
    is_safe, msg = critic.validate_proposal(unsafe_plan2)
    assert not is_safe
    assert "POLICY VIOLATION" in msg


# -------------------------------------------------------------------------
# 7. MALACore Workflow Execution Scenarios (Section 5)
# -------------------------------------------------------------------------
def test_mala_core_workflow_scenarios():
    safety_ledger = [
        SafetyConstraint(key="temperature", max_val=1550.0, unit="C", kappa=0.0),
        SafetyConstraint(key="yard_pct", max_val=85.0, unit="%", kappa=0.0),
        SafetyConstraint(key="mn_variance", max_val=0.08, unit="", kappa=0.0)
    ]
    
    # Scenario 1: Silent Autonomy
    adapters = {
        "terminal_ocr": TerminalOCRAdapter(simulate_unsafe=False),
        "sql_erp": SQL92Adapter(),
        "csv_archive": CSVArchiveAdapter(),
        "pdf_parser": PDFParserAdapter()
    }
    gatherer = GathererAgent(adapters=adapters, theta_low=0.45, theta_high=0.80)
    critic = CriticAgent(safety_ledger=safety_ledger)
    planner = PlannerAgent(critic_agent=critic)
    mala = MALACore(gatherer=gatherer, planner=planner, critic=critic, theta_low=0.45, theta_high=0.80)
    
    result = mala.execute_workflow("Re-route production schedule following Rolling Mill B failure")
    assert result["status"] == "SUCCESS"
    assert result["autonomy_level"] == "silent"
    assert result["action"]["action"] == "immediate_reroute"
    assert pytest.approx(result["confidence"], abs=1e-4) == 0.9444
    
    # Scenario 2: Explicit Approval (Medium confidence due to raised thresholds)
    gatherer2 = GathererAgent(adapters=adapters, theta_low=0.70, theta_high=0.95)
    mala2 = MALACore(gatherer=gatherer2, planner=planner, critic=critic, theta_low=0.70, theta_high=0.95)
    result2 = mala2.execute_workflow("Re-route production schedule following Rolling Mill B failure")
    assert result2["status"] == "HOTL_TRIGGERED"
    assert result2["reason"] == "Explicit approval required"
    assert result2["autonomy_level"] == "approval"
    
    # Scenario 3: Safety Violation / Critic Veto
    adapters_unsafe = {
        "terminal_ocr": TerminalOCRAdapter(simulate_unsafe=True), # triggers over-temp (1580C)
        "sql_erp": SQL92Adapter(),
        "csv_archive": CSVArchiveAdapter(),
        "pdf_parser": PDFParserAdapter()
    }
    gatherer3 = GathererAgent(adapters=adapters_unsafe, theta_low=0.45, theta_high=0.80)
    planner3 = PlannerAgent(critic_agent=critic)
    mala3 = MALACore(gatherer=gatherer3, planner=planner3, critic=critic, theta_low=0.45, theta_high=0.80)
    result3 = mala3.execute_workflow("Re-route production schedule following Rolling Mill B failure")
    assert result3["status"] == "HOTL_TRIGGERED"
    assert "CONSTRAINT VIOLATION: temperature" in result3["reason"]
    assert result3["proposed_action"]["action"] == "escalate_judge"
    
    # Scenario 4: System Pause (raised theta_low above current confidence)
    gatherer4 = GathererAgent(adapters=adapters, theta_low=0.95, theta_high=0.99)
    mala4 = MALACore(gatherer=gatherer4, planner=planner, critic=critic, theta_low=0.95, theta_high=0.99)
    result4 = mala4.execute_workflow("Re-route production schedule following Rolling Mill B failure")
    assert result4["status"] == "SYSTEM_PAUSE"
    assert "Insufficient confidence" in result4["reason"]
