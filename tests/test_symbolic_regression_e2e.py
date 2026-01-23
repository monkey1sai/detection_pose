import asyncio
import random
import re

from saga.config import SagaConfig
from saga.mode_controller import ModeController, OperationMode
from saga.modules.advanced_analyzer import AdvancedAnalyzer
from saga.modules.advanced_implementer import AdvancedImplementer
from saga.modules.advanced_optimizer import AdvancedOptimizer
from saga.modules.advanced_planner import AdvancedPlanner
from saga.outer_loop import FinalReport, LoopState, OuterLoop
from saga.search.generators import EvoGenerator
from saga.termination import TerminationChecker, TerminationConfig
from saga.scoring.sandbox import run_scoring


DATASET = [
    (-3, -2),
    (-2, -4),
    (-1, -4),
    (0, -2),
    (1, 2),
    (2, 8),
    (3, 16),
    (4, 26),
]


def _is_expression_like(s: str) -> bool:
    if re.search(r"[\u4e00-\u9fff]", s or ""):
        return False
    return bool(re.match(r"^[0-9xX\s\+\-\*\/\(\)\.\_]+$", s.strip()))


def test_symbolic_regression_outer_loop_produces_expression_candidate():
    async def run_once() -> FinalReport:
        random.seed(0)

        cfg = SagaConfig()
        analyzer = AdvancedAnalyzer(config={"goal_thresholds": {"goal_0": 0.8, "goal_1": 0.5, "goal_2": 0.2}})
        planner = AdvancedPlanner()
        implementer = AdvancedImplementer()
        optimizer = AdvancedOptimizer(
            generator=EvoGenerator(),
            config={"inner_iterations": 6, "batch_size": 10, "timeout": 1.0},
        )
        terminator = TerminationChecker(
            TerminationConfig(max_iters=2, convergence_eps=1e-6, convergence_patience=50)
        )
        mode = ModeController(OperationMode.AUTOPILOT)

        loop = OuterLoop(
            config=cfg,
            analyzer=analyzer,
            planner=planner,
            implementer=implementer,
            optimizer=optimizer,
            terminator=terminator,
            mode_controller=mode,
        )

        state = LoopState(
            text=str(DATASET),
            keywords=["符號回歸"],
            task="symbolic_regression",
            dataset=DATASET,
            candidates=["x", "x**2", "2*x+1", "x*x + x"],
            weights=[0.6, 0.2, 0.2],
            goal_thresholds=[0.8, 0.5, 0.2],
        )

        final: FinalReport | None = None
        async for ev in loop.run(state, run_id="sr_e2e"):
            if isinstance(ev, FinalReport):
                final = ev
        assert final is not None
        return final

    final = asyncio.run(run_once())
    assert _is_expression_like(final.best_candidate)

    # Verify the best candidate is actually scorable against the dataset.
    scoring_code = AdvancedImplementer().run({"task": "symbolic_regression", "plan": {}, "constraints": []})[
        "scoring_code"
    ]
    ok, scores = run_scoring(scoring_code, final.best_candidate, {"dataset": DATASET}, timeout_s=1.0)
    assert ok is True
    assert scores[1] == 1.0  # validity_score
    assert scores[0] >= 0.5  # fit_score (should be meaningfully correlated with data)

