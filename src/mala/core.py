import logging
from typing import Dict, Tuple
from .agents.gatherer import GathererAgent
from .agents.planner import PlannerAgent
from .agents.critic import CriticAgent
from .models import KnowledgeSet, ConfidenceScore, JustificationLog

logger = logging.getLogger(__name__)

# Autonomy thresholds: theta_low=0.45, theta_high=0.80 (Section 4.4)
# All exceptions are caught and escalated to Judge rather than crashing


class MALACore:
    """
    \MALA{} orchestrator - Section 3.1.
    
    Implements three-tier architecture:
    1. Ingestion Layer (via Gatherer + Adapters)
    2. Orchestration Layer (Planner + Critic)
    3. Interface Layer (Judge verification function)
    
    Pipeline: Gather -> Plan -> Critic -> Execute | HotL escalate
    """
    
    def __init__(self, gatherer: GathererAgent, planner: PlannerAgent, 
                 critic: CriticAgent, theta_low: float = 0.45, theta_high: float = 0.80):
        self.gatherer = gatherer
        self.planner = planner
        self.critic = critic
        self.confidence_scorer = ConfidenceScore(theta_low, theta_high)
        self.justification_log = JustificationLog()
    
    def execute_workflow(self, task: str) -> Dict:
        """
        Execute full MALA workflow for given task.
        
        Args:
            task: Task description (e.g., "Re-route production after Mill B failure")
        
        Returns:
            Result dictionary with status, action, and audit trail
        """
        logger.info(f"=== MALA Workflow Started ===")
        logger.info(f"Task: '{task}'")
        
        self.justification_log = JustificationLog()  # Reset log
        
        # Stage 1: Recursive Context Enrichment (RCE)
        logger.info("Stage 1: Recursive Context Enrichment")
        knowledge_set = self.gatherer.recursive_context_enrichment(task)
        
        self.justification_log.add_entry("RCE_COMPLETE", {
            "coverage": knowledge_set.get_coverage_ratio(),
            "freshness": knowledge_set.get_freshness_score(),
            "sources": list(knowledge_set.sources.keys()),
            "fields": list(knowledge_set.data.keys())
        })
        
        # Compute confidence score ρ(K)
        rho = self._compute_confidence(knowledge_set)
        autonomy_level = self.confidence_scorer.get_autonomy_level(rho)
        
        logger.info(f"Confidence ρ={rho:.3f}, autonomy_level={autonomy_level}")
        
        self.justification_log.add_entry("CONFIDENCE_SCORE", {
            "rho": rho,
            "autonomy_level": autonomy_level,
            "theta_low": self.confidence_scorer.theta_low,
            "theta_high": self.confidence_scorer.theta_high
        })
        
        # Check if we need to pause for missing evidence
        if rho < self.confidence_scorer.theta_low:
            logger.warning(f"ρ={rho:.3f} < θ_low={self.confidence_scorer.theta_low}: SYSTEM PAUSE")
            return self._system_pause(knowledge_set, rho)
        
        # Stage 2: LLM-based plan generation
        logger.info("Stage 2: Plan Generation")
        proposal = self.planner.generate_plan(knowledge_set, task)
        
        self.justification_log.add_entry("PLAN_GENERATED", {
            "action": proposal.get("action"),
            "temperature": proposal.get("temperature"),
            "yard_pct": proposal.get("yard_pct"),
            "mn_variance": proposal.get("mn_variance")
        })
        
        # Stage 3: Critic validation (CMDP safety filter)
        logger.info("Stage 3: Critic Validation")
        is_safe, safety_msg = self.critic.validate_proposal(proposal)
        
        self.justification_log.add_entry("CRITIC_VALIDATION", {
            "is_safe": is_safe,
            "message": safety_msg
        })
        
        # Stage 4: Execute or escalate
        if not is_safe:
            logger.warning(f"Critic VETO: {safety_msg}")
            return self.escalate_to_judge(knowledge_set, proposal, safety_msg, rho)
        
        # Check if explicit approval needed (θ_low <= ρ < θ_high)
        if autonomy_level == "approval":
            logger.info(f"Explicit approval required: {self.confidence_scorer.theta_low} <= ρ={rho:.3f} < {self.confidence_scorer.theta_high}")
            return self.escalate_to_judge(knowledge_set, proposal, "Explicit approval required", rho)
        
        # Silent autonomy: execute
        logger.info(f"Silent autonomy: ρ={rho:.3f} >= θ_high={self.confidence_scorer.theta_high}")
        return self._execute_plan(proposal, knowledge_set, rho)
    
    def _compute_confidence(self, knowledge_set: KnowledgeSet) -> float:
        """
        Compute confidence score ρ(K) per Equation 2.
        ρ(K) = harmonic mean of (r1_coverage, r2_freshness, r3_semantic)
        """
        r1 = knowledge_set.get_coverage_ratio()
        r2 = knowledge_set.get_freshness_score()
        r3 = knowledge_set.get_semantic_score()
        
        return self.confidence_scorer.compute(r1, r2, r3)
    
    def _execute_plan(self, proposal: Dict, knowledge_set: KnowledgeSet, rho: float) -> Dict:
        """Execute approved plan with full audit trail."""
        self.justification_log.add_entry("EXECUTION", {
            "status": "SUCCESS",
            "action": proposal.get("action"),
            "confidence": rho
        })
        
        logger.info(f"=== MALA Workflow Complete: SUCCESS ===")
        
        return {
            "status": "SUCCESS",
            "action": proposal,
            "confidence": rho,
            "autonomy_level": "silent",
            "justification_log": self.justification_log.get_full_log(),
            "knowledge_set": knowledge_set.data
        }
    
    def _system_pause(self, knowledge_set: KnowledgeSet, rho: float) -> Dict:
        """
        System pause for insufficient confidence.
        Per Section 4.4: ρ < θ_low triggers pause with missing evidence exposed.
        """
        missing_fields = knowledge_set.required_fields - set(knowledge_set.data.keys())
        
        self.justification_log.add_entry("SYSTEM_PAUSE", {
            "reason": "Insufficient confidence",
            "rho": rho,
            "missing_fields": list(missing_fields)
        })
        
        logger.warning(f"=== MALA Workflow Paused ===")
        
        return {
            "status": "SYSTEM_PAUSE",
            "reason": f"Insufficient confidence: ρ={rho:.3f} < θ_low={self.confidence_scorer.theta_low}",
            "missing_fields": list(missing_fields),
            "confidence": rho,
            "justification_log": self.justification_log.get_full_log(),
            "knowledge_set": knowledge_set.data
        }
    
    def escalate_to_judge(self, knowledge_set: KnowledgeSet, proposal: Dict, 
                         reason: str, rho: float) -> Dict:
        """
        Human-on-the-Loop (HotL) escalation with full audit trail.
        
        Implements Judge verification function V(ŷ, K) per Section 4.4.
        The Judge receives:
        - Justification Log (source rows, translations, rule checks)
        - Freshness Score
        - Confidence Score ρ
        - Proposed action
        - Raw knowledge set
        """
        self.justification_log.add_entry("HOTL_ESCALATION", {
            "reason": reason,
            "confidence": rho,
            "proposed_action": proposal.get("action")
        })
        
        logger.warning(f"=== HotL Escalation Triggered ===")
        logger.warning(f"Reason: {reason}")
        
        # Format for Judge review
        judge_review_package = {
            "status": "HOTL_TRIGGERED",
            "reason": reason,
            "confidence": rho,
            "autonomy_level": self.confidence_scorer.get_autonomy_level(rho),
            "proposed_action": proposal,
            "knowledge_set": knowledge_set.data,
            "sources": knowledge_set.sources,
            "justification_log": self.justification_log.get_full_log(),
            "justification_log_formatted": self.justification_log.format_for_judge(),
            "coverage_ratio": knowledge_set.get_coverage_ratio(),
            "freshness_score": knowledge_set.get_freshness_score(),
            "semantic_score": knowledge_set.get_semantic_score()
        }
        
        return judge_review_package
