import logging
from typing import Dict, List, Tuple, Optional
from ..models import SafetyConstraint, CMDPState, CMDPAction, TemperatureBin, YardOccupancyBin, ManganeseVarianceBin

logger = logging.getLogger(__name__)

# CMDP policy table is initialized once at startup and cached
# Policy compliance: proposed action must match pi*(s) from Table 2


class CriticAgent:
    """
    CMDP hard-veto safety filter - Section 3.3.
    Implements the solved policy π* from Table 2 of the paper.
    Checks every proposed plan against:
    1. The CMDP state-action policy table
    2. All registered SafetyConstraints (cost functions C_i)
    
    Blocks any action that violates κ_i thresholds.
    """
    
    def __init__(self, safety_ledger: List[SafetyConstraint]):
        self.safety_ledger = safety_ledger
        self.policy_table = self._initialize_policy_table()
    
    def validate_proposal(self, plan: Dict) -> Tuple[bool, str]:
        """
        Validate proposed plan against CMDP policy and safety constraints.
        
        Returns:
            (is_safe, message): True if plan is safe, False otherwise
        """
        # Step 1: Check hard safety constraints (cost functions)
        constraint_check, constraint_msg = self._check_constraints(plan)
        if not constraint_check:
            return False, constraint_msg
        
        # Step 2: Check CMDP policy compliance
        policy_check, policy_msg = self._check_policy(plan)
        if not policy_check:
            return False, policy_msg
        
        return True, "SAFE"
    
    def _check_constraints(self, plan: Dict) -> Tuple[bool, str]:
        """
        Check all SafetyConstraints (implements C_i cost functions).
        Per Equations 3-5, κ_i = 0 means hard constraint.
        """
        for constraint in self.safety_ledger:
            if constraint.key in plan:
                value = plan[constraint.key]
                cost = constraint.cost(value)
                
                if cost > constraint.kappa:
                    msg = (
                        f"CONSTRAINT VIOLATION: {constraint.key} "
                        f"({value}{constraint.unit}) > {constraint.max_val}{constraint.unit}. "
                        f"Cost C={cost:.2f} exceeds kappa={constraint.kappa}"
                    )
                    logger.error(msg)
                    return False, msg
        
        return True, "All constraints satisfied"
    
    def _check_policy(self, plan: Dict) -> Tuple[bool, str]:
        """
        Check if proposed action matches solved CMDP policy π*(s).
        Implements Table 2 from Section 3.3.
        """
        # Extract state variables from plan
        temperature = plan.get("temperature", 1545.0)
        yard_pct = plan.get("yard_pct", 75.0)
        mn_variance = plan.get("mn_variance", 0.04)
        
        # Discretize into CMDP state
        state = CMDPState.from_observations(temperature, yard_pct, mn_variance)
        
        # Get proposed action
        action_str = plan.get("action", "")
        try:
            proposed_action = self._parse_action(action_str)
        except ValueError as e:
            return False, f"Invalid action: {e}"
        
        # Look up policy
        policy_action = self.policy_table.get(state)
        
        if policy_action is None:
            logger.warning(f"No policy defined for state {state}")
            # Conservative: escalate to Judge if no policy
            if proposed_action != CMDPAction.ESCALATE_JUDGE:
                return False, f"No policy for state {state}, must escalate to Judge"
            return True, "Escalation to Judge (no policy)"
        
        # Check if proposed action matches policy
        if proposed_action != policy_action:
            msg = (
                f"POLICY VIOLATION: State {state} requires action {policy_action.value}, "
                f"but plan proposes {proposed_action.value}"
            )
            logger.error(msg)
            return False, msg
        
        logger.info(f"Policy check passed: {state} -> {proposed_action.value}")
        return True, f"Policy compliant: {proposed_action.value}"
    
    def _parse_action(self, action_str: str) -> CMDPAction:
        """Parse action string to CMDPAction enum."""
        action_map = {
            "immediate_reroute": CMDPAction.IMMEDIATE_REROUTE,
            "hold_dispatch_reroute": CMDPAction.HOLD_DISPATCH_REROUTE,
            "hold_only": CMDPAction.HOLD_ONLY,
            "escalate_judge": CMDPAction.ESCALATE_JUDGE,
            "a1": CMDPAction.IMMEDIATE_REROUTE,
            "a2": CMDPAction.HOLD_DISPATCH_REROUTE,
            "a3": CMDPAction.HOLD_ONLY,
            "a4": CMDPAction.ESCALATE_JUDGE,
        }
        
        action_lower = action_str.lower().strip()
        if action_lower in action_map:
            return action_map[action_lower]
        
        raise ValueError(f"Unknown action: {action_str}")
    
    def _initialize_policy_table(self) -> Dict[CMDPState, CMDPAction]:
        """
        Initialize solved CMDP policy π* from Table 2 (Section 3.3).
        Maps 27 states to optimal actions under κ_2 = 0 (hard yard constraint).
        
        Policy rules:
        - T=crit, any Y, any M -> escalate Judge
        - T=warn, Y=high, M=elev -> escalate Judge
        - T=safe, Y=low, M=nom -> immediate reroute
        - T=safe, Y=med, M=nom -> hold+dispatch+reroute
        - T=safe, Y=high, M=nom -> hold only
        - etc.
        """
        policy = {}
        
        # Critical temperature: always escalate
        for y_bin in YardOccupancyBin:
            for m_bin in ManganeseVarianceBin:
                state = CMDPState(TemperatureBin.CRIT, y_bin, m_bin)
                policy[state] = CMDPAction.ESCALATE_JUDGE
        
        # Warning temperature
        for y_bin in YardOccupancyBin:
            for m_bin in ManganeseVarianceBin:
                state = CMDPState(TemperatureBin.WARN, y_bin, m_bin)
                # High yard + elevated Mn -> escalate
                if y_bin == YardOccupancyBin.HIGH and m_bin == ManganeseVarianceBin.ELEV:
                    policy[state] = CMDPAction.ESCALATE_JUDGE
                # High yard -> hold only
                elif y_bin == YardOccupancyBin.HIGH:
                    policy[state] = CMDPAction.HOLD_ONLY
                # Medium yard -> hold+dispatch+reroute
                elif y_bin == YardOccupancyBin.MED:
                    policy[state] = CMDPAction.HOLD_DISPATCH_REROUTE
                # Low yard -> immediate reroute
                else:
                    policy[state] = CMDPAction.IMMEDIATE_REROUTE
        
        # Safe temperature
        for y_bin in YardOccupancyBin:
            for m_bin in ManganeseVarianceBin:
                state = CMDPState(TemperatureBin.SAFE, y_bin, m_bin)
                # Over Mn variance -> escalate
                if m_bin == ManganeseVarianceBin.OVER:
                    policy[state] = CMDPAction.ESCALATE_JUDGE
                # High yard -> hold only
                elif y_bin == YardOccupancyBin.HIGH:
                    policy[state] = CMDPAction.HOLD_ONLY
                # Medium yard -> hold+dispatch+reroute
                elif y_bin == YardOccupancyBin.MED:
                    policy[state] = CMDPAction.HOLD_DISPATCH_REROUTE
                # Low yard -> immediate reroute
                else:
                    policy[state] = CMDPAction.IMMEDIATE_REROUTE
        
        logger.info(f"Initialized CMDP policy table with {len(policy)} state-action mappings")
        return policy
    
    def get_recommended_action(self, temperature: float, yard_pct: float, 
                              mn_variance: float) -> CMDPAction:
        """
        Get recommended action for given state observations.
        Useful for Planner to query before proposing.
        """
        state = CMDPState.from_observations(temperature, yard_pct, mn_variance)
        return self.policy_table.get(state, CMDPAction.ESCALATE_JUDGE)
