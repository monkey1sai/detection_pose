from saga.modules.advanced_optimizer import AdvancedOptimizer


def test_batch_evaluate_returns_scoring_output():
    optimizer = AdvancedOptimizer(config={"timeout": 1.0})
    code = "def score(text, ctx): return [0.1, 0.2, 0.3]"

    scores = optimizer._batch_evaluate(["hello"], code, {})

    assert scores == [[0.1, 0.2, 0.3]]
