"""
SAGA Runner - Facade for the OuterLoop multi-turn engine.
"""
from __future__ import annotations

import ast
import logging
import uuid
import json
from pathlib import Path
from typing import AsyncIterator, Dict, Any, Optional

from .config import SagaConfig
from .outer_loop import OuterLoop, LoopState, IterationResult, FinalReport, HumanReviewRequest
from .mode_controller import ModeController, OperationMode
from .termination import TerminationChecker, TerminationConfig
from .modules.advanced_analyzer import AdvancedAnalyzer
from .modules.advanced_planner import AdvancedPlanner
from .modules.advanced_implementer import AdvancedImplementer
from .modules.advanced_optimizer import AdvancedOptimizer
from .search.generators import LLMGenerator, EvoGenerator
from .adapters.sglang_adapter import SGLangAdapter
from .adapters.groq_adapter import GroqAdapter
from .trace.sqlite import TraceDB

logger = logging.getLogger(__name__)


_SYMBOLIC_REGRESSION_KEYWORDS = {"符號回歸", "多項式", "擬合", "x²", "equation", "formula"}


def _infer_task_type(*, text: str, keywords: list[str]) -> str:
    if any(k in _SYMBOLIC_REGRESSION_KEYWORDS for k in keywords):
        return "symbolic_regression"
    # Heuristic: looks like a python literal list of (x, y) pairs
    s = (text or "").strip()
    if s.startswith("[") and ("(" in s and "," in s and ")" in s):
        return "symbolic_regression"
    return ""


def _try_parse_dataset(text: str) -> list[tuple[float, float]]:
    s = (text or "").strip()
    if not s:
        return []
    # Allow extra prompt text around the literal list, e.g. "....: [(x,y), ...]"
    start = s.find("[")
    end = s.rfind("]")
    if start != -1 and end != -1 and end > start:
        s = s[start : end + 1]
    try:
        obj = ast.literal_eval(s)
    except Exception:
        return []
    if not isinstance(obj, (list, tuple)):
        return []
    out: list[tuple[float, float]] = []
    for item in obj:
        if isinstance(item, (list, tuple)) and len(item) == 2:
            try:
                out.append((float(item[0]), float(item[1])))
            except Exception:
                continue
    return out


class SagaRunner:
    """Orchestrates the SAGA system components."""
    
    def __init__(self, cfg: SagaConfig):
        self.cfg = cfg
        
        # Initialize Core Modules
        self.analyzer = AdvancedAnalyzer()
        self.planner = AdvancedPlanner()
        self.implementer = AdvancedImplementer()
        
        # Initialize Generator & Optimizer
        if cfg.use_groq:
            try:
                client = GroqAdapter(cfg.groq_api_key, cfg.groq_model)
                self.generator = LLMGenerator(client)
                logger.info(f"Initialized LLMGenerator with Groq (model={cfg.groq_model})")
            except Exception as e:
                logger.warning(f"Failed to init GroqAdapter: {e}, falling back to EvoGenerator")
                self.generator = EvoGenerator()
        elif cfg.use_llm_modules:
            try:
                client = SGLangAdapter(cfg.sglang_url, cfg.sglang_api_key)
                self.generator = LLMGenerator(client)
                logger.info("Initialized LLMGenerator with SGLang")
            except Exception as e:
                logger.warning(f"Failed to init SGLangAdapter: {e}, using EvoGenerator")
                self.generator = EvoGenerator()
        else:
            self.generator = EvoGenerator()
            
        self.optimizer = AdvancedOptimizer(generator=self.generator)
        
    async def run(
        self, 
        text: str, 
        keywords: list[str], 
        mode: str = "semi-pilot",
        run_id: Optional[str] = None,
        config_overrides: Optional[dict] = None
    ) -> AsyncIterator[Any]:
        """
        Execute the SAGA loop.
        
        Args:
            text: Input text/problem description
            keywords: Initial keywords
            mode: Operation mode (co-pilot, semi-pilot, autopilot)
            run_id: Optional run ID
            config_overrides: Scientist parameters (max_iters, weights, etc.)
            
        Yields:
            OuterLoop events (IterationResult, HumanReviewRequest, FinalReport)
        """
        run_id = run_id or uuid.uuid4().hex
        logger.info(f"Starting run {run_id} in {mode} mode")
        
        # Merge config
        overrides = config_overrides or {}
        term_config = TerminationConfig(
            max_iters=overrides.get("max_iters", 10),
            convergence_eps=overrides.get("convergence_eps", 0.001),
            convergence_patience=overrides.get("convergence_patience", 3),
            goal_thresholds=self._parse_floats(overrides.get("goal_thresholds", []))
        )
        
        # Initialize Controllers
        op_mode = OperationMode(mode) if mode in [m.value for m in OperationMode] else OperationMode.SEMI_PILOT
        mode_controller = ModeController(op_mode)
        terminator = TerminationChecker(term_config)
        
        # Initialize TraceDB
        run_dir = self.cfg.run_path(run_id)
        run_dir.mkdir(parents=True, exist_ok=True)
        trace_db = TraceDB(run_dir / "trace.db")
        trace_db.init()
        
        # Initial State
        weights = self._parse_floats(overrides.get("weights")) or [0.33, 0.34, 0.33]
        goal_thresholds = self._parse_floats(overrides.get("goal_thresholds")) or [0.7, 0.7, 0.7]

        task = _infer_task_type(text=text, keywords=keywords)
        dataset = _try_parse_dataset(text) if task == "symbolic_regression" else []
        if task:
            logger.info(f"Detected task={task} (dataset_points={len(dataset)})")

        # Optimizer defaults (can be overridden by UI)
        if task == "symbolic_regression":
            default_inner_iterations = 15
            default_batch_size = 20
            default_scoring_timeout_s = 1.0
        else:
            # Keep conservative defaults for generic text tasks
            default_inner_iterations = 2
            default_batch_size = 4
            default_scoring_timeout_s = 15.0

        try:
            inner_iterations = int(overrides.get("inner_iterations", default_inner_iterations))
        except Exception:
            inner_iterations = default_inner_iterations
        try:
            batch_size = int(overrides.get("batch_size", default_batch_size))
        except Exception:
            batch_size = default_batch_size

        scoring_timeout_s = overrides.get("scoring_timeout_s", None)
        if scoring_timeout_s is None:
            scoring_timeout_s = overrides.get("timeout", None)
        try:
            scoring_timeout_s = float(scoring_timeout_s) if scoring_timeout_s is not None else float(default_scoring_timeout_s)
        except Exception:
            scoring_timeout_s = float(default_scoring_timeout_s)

        inner_iterations = max(1, inner_iterations)
        batch_size = max(1, batch_size)
        scoring_timeout_s = max(0.1, scoring_timeout_s)
        
        # Enhanced seeding for symbolic regression
        # CRITICAL FIX: Do NOT include raw 'text' as candidate, because if it evaluates to the dataset itself,
        # the scorer might give it a perfect score (data matching data), creating a false optimum.
        initial_candidates = []
        if any(k in ["x²", "多項式", "擬合", "formula", "equation"] for k in keywords):
            # Expanded seed set covering more quadratic polynomial variations
            initial_candidates.extend([
                "x", "x**2", "x**2 + x", "x**2 - x", 
                "x**2 + 2*x", "x**2 + 3*x", "x**2 - 2*x",
                "x**2 + x - 1", "x**2 + x - 2", "x**2 + 2*x - 1", "x**2 + 2*x - 2",
                "x**2 + 3*x - 1", "x**2 + 3*x - 2", "x**2 + 3*x - 3",
                "2*x + 1", "3*x - 1", "x**2 - 1", "x**2 - 2",
            ])
        elif text and len(text) < 50: # Only include text if it's short (likely a formula hint), not a full dataset
            initial_candidates.append(text)
            
        state = LoopState(
            text=text,
            keywords=keywords,
            task=task,
            dataset=dataset,
            constraints=[], 
            candidates=initial_candidates,
            weights=weights,
            goal_thresholds=goal_thresholds
        )
        
        # Apply optimizer tuning (read by AdvancedOptimizer at runtime)
        self.optimizer.config.update({
            "inner_iterations": inner_iterations,
            "batch_size": batch_size,
            "timeout": scoring_timeout_s,
        })
        
        if hasattr(self.generator, "set_context"):
            self.generator.set_context(keywords)
            
        # Create Loop
        loop = OuterLoop(
            config=self.cfg,
            analyzer=self.analyzer,
            planner=self.planner,
            implementer=self.implementer,
            optimizer=self.optimizer,
            terminator=terminator,
            mode_controller=mode_controller
        )
        
        # Execute and Yield
        async for event in loop.run(state, run_id):
            # Log to TraceDB (Simplified for now, ideally OuterLoop does this via callbacks)
            if isinstance(event, IterationResult):
                self._log_iteration(trace_db, event)
            
            yield event

    def _log_iteration(self, db: TraceDB, result: IterationResult):
        """Log iteration details to trace DB."""
        # This maps the new complex objects to the simple TraceDB schema
        # For MVP, we basically dump the analysis report as a node
        try:
            db.write_node({
                "node_name": f"Iteration_{result.iteration}",
                "input_summary": f"best_score={result.best_score:.4f}",
                "output_summary": json.dumps({
                    "bottleneck": result.analysis_report.bottleneck,
                    "trend": result.analysis_report.improvement_trend
                }),
                "elapsed_ms": result.elapsed_ms
            })
        except Exception as e:
            logger.error(f"Failed to log trace: {e}")

    def _parse_floats(self, val: Any) -> Optional[list[float]]:
        if isinstance(val, list): return val
        if isinstance(val, str):
            try:
                return [float(x.strip()) for x in val.split(",") if x.strip()]
            except:
                pass
        return None
