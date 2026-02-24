import logging
from typing import Dict, Optional
from ..models import KnowledgeSet, CMDPAction

logger = logging.getLogger(__name__)

# Critic-guided planning: Planner queries Critic before proposing action


class PlannerAgent:
    """
    LLM-based plan generation with CMDP-guided action selection.
    
    In production, this would query an LLM (e.g., GPT-4) with enriched context.
    For prototype, generates plans based on knowledge set and CMDP state.
    
    The Planner can optionally query the Critic for recommended actions
    before proposing, implementing a "Critic-guided planning" pattern.
    """
    
    def __init__(self, critic_agent=None):
        """
        Args:
            critic_agent: Optional CriticAgent for policy-guided planning
        """
        self.critic = critic_agent
    
    def generate_plan(self, knowledge_set: KnowledgeSet, task: str) -> Dict:
        """
        Generate action plan from enriched knowledge set.
        
        Args:
            knowledge_set: Enriched context from RCE
            task: Task description (e.g., "Re-route production after Mill B failure")
        
        Returns:
            Proposed action plan dictionary
        """
        logger.info(f"Planner evaluating context for task: {task}")
        
        # Extract state variables from knowledge set
        temperature = knowledge_set.data.get("temperature", 1545.0)
        yard_pct = knowledge_set.data.get("yard_pct", 75.0)
        mn_variance = knowledge_set.data.get("mn_variance", 0.04)
        heat_id = knowledge_set.data.get("heat_id", "UNKNOWN")
        batch_id = knowledge_set.data.get("batch_id", "UNKNOWN")
        
        # Query Critic for recommended action (if available)
        if self.critic is not None:
            recommended_action = self.critic.get_recommended_action(
                temperature, yard_pct, mn_variance
            )
            action_str = self._action_to_string(recommended_action)
            logger.info(f"Critic recommends action: {action_str}")
        else:
            # Fallback: simple heuristic
            action_str = self._heuristic_action(temperature, yard_pct, mn_variance)
            logger.info(f"Heuristic action (no Critic): {action_str}")
        
        # Construct proposal
        proposal = {
            "temperature": temperature,
            "mn_variance": mn_variance,
            "yard_pct": yard_pct,
            "action": action_str,
            "heat_id": heat_id,
            "batch_id": batch_id,
            "task": task,
            "confidence": knowledge_set.get_coverage_ratio(),
            "freshness": knowledge_set.get_freshness_score(),
        }
        
        logger.info(f"Generated plan: {action_str} for Heat {heat_id}, Batch {batch_id}")
        return proposal
    
    def _action_to_string(self, action: CMDPAction) -> str:
        """Convert CMDPAction enum to string."""
        action_map = {
            CMDPAction.IMMEDIATE_REROUTE: "immediate_reroute",
            CMDPAction.HOLD_DISPATCH_REROUTE: "hold_dispatch_reroute",
            CMDPAction.HOLD_ONLY: "hold_only",
            CMDPAction.ESCALATE_JUDGE: "escalate_judge",
        }
        return action_map.get(action, "escalate_judge")
    
    def _heuristic_action(self, temperature: float, yard_pct: float, 
                         mn_variance: float) -> str:
        """
        Simple heuristic for action selection when Critic is not available.
        Not used in production (Critic should always be present).
        """
        # Critical conditions -> escalate
        if temperature > 1550 or mn_variance > 0.08:
            return "escalate_judge"
        
        # High yard occupancy -> hold
        if yard_pct > 83:
            return "hold_only"
        
        # Medium yard -> hold+dispatch+reroute
        if yard_pct > 78:
            return "hold_dispatch_reroute"
        
        # Normal conditions -> immediate reroute
        return "immediate_reroute"
