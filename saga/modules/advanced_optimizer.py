"""
Advanced Optimizer module for SAGA inner loop optimization.

Implements the inner optimization loop:
- Generation -> Evaluation -> Selection cycle
- Pluggable generator strategies
- Batch evaluation in sandbox
- Pareto-aware selection
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from saga.search.generators import (
    AnalysisReport,
    CandidateGenerator,
    LLMGenerator,
    EvoGenerator,
    Selector,
    ParetoSelector,
)
from saga.scoring.sandbox import run_scoring

logger = logging.getLogger(__name__)


class AdvancedOptimizer:
    """Advanced optimizer with pluggable inner loop strategies.
    
    Implements the inner optimization loop:
    1. Generation: Create new candidates via LLM or evolution
    2. Evaluation: Score candidates in sandbox
    3. Selection: Choose best candidates via Pareto selection
    """
    
    def __init__(
        self,
        generator: Optional[CandidateGenerator] = None,
        selector: Optional[Selector] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """Initialize optimizer with generator and selector.
        
        Args:
            generator: Candidate generator (defaults to EvoGenerator)
            selector: Candidate selector (defaults to ParetoSelector)
            config: Configuration including inner loop iterations, batch size
        """
        self.generator = generator or EvoGenerator()
        self.selector = selector or ParetoSelector()
        self.config = config or {}
        
        self.inner_iterations = self.config.get("inner_iterations", 3)
        self.batch_size = self.config.get("batch_size", 10)
        self.timeout = self.config.get("timeout", 5.0)
        
        logger.info(
            f"[AdvancedOptimizer] Initialized: generator={self.generator.get_name()}, "
            f"inner_iterations={self.inner_iterations}, batch_size={self.batch_size}"
        )
    
    def optimize(
        self,
        candidates: List[str],
        scoring_code: str,
        weights: List[float],
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[str, List[float]]]:
        """Run inner loop optimization.
        
        Args:
            candidates: Initial candidate population
            scoring_code: Python code for scoring function
            weights: Objective weights for selection
            context: Additional context for scoring
            
        Returns:
            List of (candidate, score_vector) tuples, sorted by weighted score
        """
        logger.info(f"[AdvancedOptimizer] Starting optimization with {len(candidates)} candidates")
        
        context = context or {}
        population = candidates.copy()
        best_results: List[Tuple[str, List[float]]] = []
        
        # Create fake analysis report for generator
        feedback = AnalysisReport(
            score_distribution={},
            goal_achievement={},
            pareto_count=0,
            improvement_trend=0.0,
            bottleneck="unknown",
            suggested_constraints=[],
            iteration=0
        )
        
        for inner_iter in range(self.inner_iterations):
            logger.info(f"[AdvancedOptimizer] Inner iteration {inner_iter + 1}/{self.inner_iterations}")
            
            # Step 1: Generation
            new_candidates = self.generator.generate(
                population, feedback, self.batch_size
            )
            all_candidates = list(set(population + new_candidates))  # Deduplicate
            
            logger.debug(f"[AdvancedOptimizer] Generated {len(new_candidates)} new candidates, total={len(all_candidates)}")
            
            # Step 2: Evaluation
            scores = self._batch_evaluate(all_candidates, scoring_code, context)
            
            # Step 3: Selection
            selected = self.selector.select(
                all_candidates, scores, weights, self.batch_size
            )
            
            # Update population and feedback
            population = [c for c, _ in selected]
            best_results = selected
            
            # Update feedback for next iteration
            if scores:
                feedback = self._create_feedback(scores, inner_iter + 1)
            
            logger.info(
                f"[AdvancedOptimizer] Iteration {inner_iter + 1} complete: "
                f"selected={len(selected)}, best_score={self._weighted_score(best_results[0][1], weights) if best_results else 0:.4f}"
            )
        
        logger.info(f"[AdvancedOptimizer] Optimization complete: {len(best_results)} candidates selected")
        return best_results
    
    def _batch_evaluate(
        self,
        candidates: List[str],
        scoring_code: str,
        context: Dict[str, Any]
    ) -> List[List[float]]:
        """Evaluate all candidates using sandbox."""
        scores = []
        
        for candidate in candidates:
            try:
                ok, result = run_scoring(scoring_code, candidate, context, timeout_s=self.timeout)
                if ok and isinstance(result, list) and all(isinstance(x, (int, float)) for x in result):
                    scores.append(result)
                else:
                    logger.warning(f"[AdvancedOptimizer] Invalid score for candidate: {result}")
                    scores.append([0.0, 0.0, 0.0])  # Default score
            except Exception as e:
                logger.warning(f"[AdvancedOptimizer] Scoring failed for candidate: {e}")
                scores.append([0.0, 0.0, 0.0])
        
        return scores
    
    def _create_feedback(self, scores: List[List[float]], iteration: int) -> AnalysisReport:
        """Create feedback report from scores."""
        import statistics
        
        if not scores:
            return AnalysisReport(
                score_distribution={},
                goal_achievement={},
                pareto_count=0,
                improvement_trend=0.0,
                bottleneck="unknown",
                suggested_constraints=[],
                iteration=iteration
            )
        
        # Calculate score distribution
        num_dims = len(scores[0]) if scores[0] else 0
        distribution = {}
        for dim in range(num_dims):
            dim_scores = [s[dim] for s in scores if len(s) > dim]
            if dim_scores:
                distribution[f"dim_{dim}"] = {
                    "min": min(dim_scores),
                    "max": max(dim_scores),
                    "avg": statistics.mean(dim_scores),
                    "std": statistics.stdev(dim_scores) if len(dim_scores) > 1 else 0
                }
        
        # Find bottleneck (dimension with lowest average)
        bottleneck = "unknown"
        min_avg = 1.0
        for dim, stats in distribution.items():
            if stats["avg"] < min_avg:
                min_avg = stats["avg"]
                bottleneck = dim
        
        return AnalysisReport(
            score_distribution=distribution,
            goal_achievement={},
            pareto_count=len(scores) // 4,  # Rough estimate
            improvement_trend=0.0,
            bottleneck=bottleneck,
            suggested_constraints=[],
            iteration=iteration
        )
    
    def _weighted_score(self, score_vec: List[float], weights: List[float]) -> float:
        """Calculate weighted score."""
        if len(weights) == len(score_vec):
            return sum(w * s for w, s in zip(weights, score_vec))
        return sum(score_vec) / len(score_vec) if score_vec else 0.0
    
    def set_generator(self, generator: CandidateGenerator) -> None:
        """Switch to different generation strategy."""
        old_name = self.generator.get_name()
        self.generator = generator
        logger.info(f"[AdvancedOptimizer] Switched generator: {old_name} -> {generator.get_name()}")
    
    def set_selector(self, selector: Selector) -> None:
        """Switch to different selection strategy."""
        self.selector = selector
        logger.info(f"[AdvancedOptimizer] Switched selector")
