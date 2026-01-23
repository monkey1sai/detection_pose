import random
import re

from saga.modules.advanced_implementer import AdvancedImplementer
from saga.scoring.sandbox import run_scoring
from saga.search.generators import EvoGenerator


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


def test_symbolic_regression_scorer_scores_true_formula_high():
    impl = AdvancedImplementer()
    scoring_code = impl.run({"task": "symbolic_regression", "plan": {}, "constraints": []})["scoring_code"]

    ok, scores = run_scoring(scoring_code, "x**2 + 3*x - 2", {"dataset": DATASET}, timeout_s=1.0)
    assert ok is True
    assert isinstance(scores, list)
    assert scores[0] > 0.95  # fit_score
    assert scores[1] == 1.0  # validity_score
    assert scores[2] > 0.0   # simplicity_score


def test_symbolic_regression_scorer_rejects_non_math_text():
    impl = AdvancedImplementer()
    scoring_code = impl.run({"task": "symbolic_regression", "plan": {}, "constraints": []})["scoring_code"]

    ok, scores = run_scoring(scoring_code, "優化優化增強", {"dataset": DATASET}, timeout_s=1.0)
    assert ok is True
    assert scores == [0.0, 0.0, 0.0]


def test_evo_generator_mutate_expression_does_not_inject_cjk():
    random.seed(0)
    gen = EvoGenerator(mutation_rate=1.0, crossover_rate=0.0)
    mutated = gen._mutate("x**2 + 3*x - 2")
    assert re.search(r"[\u4e00-\u9fff]", mutated) is None

