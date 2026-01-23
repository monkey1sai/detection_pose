"""
Advanced Planner module for SAGA dynamic constraint addition.

Generates optimization plans based on Analyzer feedback:
- Dynamic objective weight adjustment
- New constraint suggestion based on analysis
- Strategy selection for different iteration phases
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class OptimizationPlan:
    """Generated optimization plan for current iteration."""
    weights: List[float]
    new_constraints: List[str]
    strategy: str  # "exploration", "exploitation", "balance"
    focus_objectives: List[str]
    weight_adjustments: Dict[str, float]  # objective -> adjustment delta


class AdvancedPlanner:
    """Advanced planner with dynamic constraint and weight adjustment.
    
    Uses analysis feedback to:
    1. Adjust objective weights based on bottlenecks
    2. Suggest new constraints for improved search
    3. Select appropriate optimization strategy
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize planner with configuration.
        
        Args:
            config: Configuration including weight bounds, adjustment rates, etc.
        """
        self.config = config or {}
        self.weight_bounds = self.config.get("weight_bounds", (0.1, 0.8))
        self.adjustment_rate = self.config.get("adjustment_rate", 0.1)
        self.exploration_threshold = self.config.get("exploration_threshold", 3)
        
        self._iteration_history: List[Dict] = []
        
        logger.info(f"[AdvancedPlanner] Initialized with config: {self.config}")
    
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate optimization plan based on analysis feedback.
        
        Args:
            state: Contains analysis results, constraints, iteration info
            
        Returns:
            Dictionary with weights, new_constraints, and strategy
        """
        logger.info("[AdvancedPlanner] Generating optimization plan...")
        
        analysis = state.get("analysis", {})
        current_constraints = state.get("constraints", [])
        iteration = state.get("iteration", 0)
        current_weights = state.get("weights", [0.33, 0.34, 0.33])
        task = (state.get("task", "") or "").strip().lower()
        keywords = state.get("keywords", []) or []
        
        # Determine strategy based on iteration and trends
        strategy = self._determine_strategy(analysis, iteration)
        
        # Adjust weights based on bottleneck and achievement rates
        new_weights, adjustments = self._adjust_weights(
            current_weights, 
            analysis,
            strategy
        )
        
        # Generate new constraints
        new_constraints = self._generate_constraints(
            analysis, 
            current_constraints,
            strategy
        )
        
        # Identify focus objectives
        focus_objectives = self._identify_focus(analysis)
        
        # Record for history
        self._iteration_history.append({
            "iteration": iteration,
            "strategy": strategy,
            "weights": new_weights,
            "new_constraints": new_constraints
        })
        
        result = {
            "weights": new_weights,
            "new_constraints": new_constraints,
            "strategy": strategy,
            "focus_objectives": focus_objectives,
            "weight_adjustments": adjustments,
        }

        # Task-specific objectives (used by Implementer to generate appropriate scoring proxy)
        if task == "symbolic_regression" or any(k in ["符號回歸", "多項式", "擬合", "x²", "equation", "formula"] for k in keywords):
            result["objectives"] = ["regression_fit", "expression_validity", "simplicity"]
        
        logger.info(
            f"[AdvancedPlanner] Plan generated: strategy={strategy}, "
            f"weights={new_weights}, new_constraints={len(new_constraints)}"
        )
        
        return result
    
    def _determine_strategy(
        self, analysis: Dict[str, Any], iteration: int
    ) -> str:
        """Determine optimization strategy for current iteration."""
        improvement = analysis.get("improvement_trend", 0)
        pareto_count = analysis.get("pareto_count", 0)
        
        # Early iterations: explore
        if iteration <= self.exploration_threshold:
            logger.debug(f"[AdvancedPlanner] Strategy: exploration (early iteration {iteration})")
            return "exploration"
        
        # If improvement is stagnating: more exploration
        if -0.01 < improvement < 0.01:
            logger.debug(f"[AdvancedPlanner] Strategy: exploration (stagnant improvement)")
            return "exploration"
        
        # If good progress: exploit current direction
        if improvement > 0.05:
            logger.debug(f"[AdvancedPlanner] Strategy: exploitation (good progress)")
            return "exploitation"
        
        # Default: balanced approach
        logger.debug(f"[AdvancedPlanner] Strategy: balance")
        return "balance"
    
    def _adjust_weights(
        self, 
        current_weights: List[float],
        analysis: Dict[str, Any],
        strategy: str
    ) -> tuple[List[float], Dict[str, float]]:
        """Adjust objective weights based on analysis."""
        weights = current_weights.copy()
        adjustments = {}
        
        bottleneck = analysis.get("bottleneck", "")
        goal_achievement = analysis.get("goal_achievement", {})
        
        # Find bottleneck index
        bottleneck_idx = None
        for i, (goal, rate) in enumerate(goal_achievement.items()):
            if goal == bottleneck:
                bottleneck_idx = i
                break
        
        if bottleneck_idx is not None and bottleneck_idx < len(weights):
            # Increase weight for bottleneck
            increase = self.adjustment_rate
            if strategy == "exploration":
                increase *= 1.5  # More aggressive in exploration
            elif strategy == "exploitation":
                increase *= 0.5  # Conservative in exploitation
            
            old_weight = weights[bottleneck_idx]
            weights[bottleneck_idx] = min(
                weights[bottleneck_idx] + increase,
                self.weight_bounds[1]
            )
            adjustments[bottleneck] = weights[bottleneck_idx] - old_weight
            
            # Reduce other weights proportionally
            reduction = (weights[bottleneck_idx] - old_weight) / (len(weights) - 1)
            for i in range(len(weights)):
                if i != bottleneck_idx:
                    old_w = weights[i]
                    weights[i] = max(weights[i] - reduction, self.weight_bounds[0])
                    adjustments[f"goal_{i}"] = weights[i] - old_w
        
        # Normalize to sum to 1
        total = sum(weights)
        if total > 0:
            weights = [w / total for w in weights]
        
        return weights, adjustments
    
    def _generate_constraints(
        self,
        analysis: Dict[str, Any],
        current_constraints: List[str],
        strategy: str
    ) -> List[str]:
        """Generate new constraints based on analysis."""
        new_constraints = []
        
        # Use suggestions from analyzer
        suggested = analysis.get("suggested_constraints", [])
        for suggestion in suggested:
            if suggestion not in current_constraints:
                new_constraints.append(suggestion)
        
        # Add strategy-specific constraints
        bottleneck = analysis.get("bottleneck", "")
        goal_achievement = analysis.get("goal_achievement", {})
        
        if bottleneck and bottleneck != "unknown":
            achievement = goal_achievement.get(bottleneck, 0)
            if achievement < 0.3:
                constraint = f"Priority: {bottleneck} (critical: {achievement:.0%})"
                if constraint not in current_constraints:
                    new_constraints.append(constraint)
        
        # For exploration: add diversity constraint
        if strategy == "exploration":
            diversity_constraint = "Maintain solution diversity"
            if diversity_constraint not in current_constraints:
                new_constraints.append(diversity_constraint)
        
        logger.info(f"[AdvancedPlanner] Generated {len(new_constraints)} new constraints")
        return new_constraints
    
    def _identify_focus(self, analysis: Dict[str, Any]) -> List[str]:
        """Identify objectives to focus on."""
        focus = []
        
        bottleneck = analysis.get("bottleneck", "")
        if bottleneck and bottleneck != "unknown":
            focus.append(bottleneck)
        
        # Add low-achievement goals
        goal_achievement = analysis.get("goal_achievement", {})
        for goal, rate in goal_achievement.items():
            if rate < 0.5 and goal not in focus:
                focus.append(goal)
        
        return focus
    
    def get_history(self) -> List[Dict]:
        """Get planning history for analysis."""
        return self._iteration_history.copy()
