from saga.modules.advanced_optimizer import AdvancedOptimizer


def test_batch_evaluate_returns_scoring_output():
    optimizer = AdvancedOptimizer(config={"timeout": 1.0})
    code = "def score(text, ctx): return [0.1, 0.2, 0.3]"

    scores = optimizer._batch_evaluate(["hello"], code, {})

    assert scores == [[0.1, 0.2, 0.3]]


def test_optimizer_reloads_config_each_optimize_call():
    class CountingGenerator:
        def __init__(self):
            self.calls = 0

        def get_name(self) -> str:
            return "CountingGenerator"

        def generate(self, population, feedback, num_candidates=5):
            self.calls += 1
            return []

    gen = CountingGenerator()
    optimizer = AdvancedOptimizer(generator=gen, config={"inner_iterations": 1, "batch_size": 1, "timeout": 1.0})
    code = "def score(text, ctx): return [0.1, 0.2, 0.3]"

    optimizer.optimize(["x"], code, [0.33, 0.34, 0.33], {})
    assert gen.calls == 1

    optimizer.config["inner_iterations"] = 3
    optimizer.optimize(["x"], code, [0.33, 0.34, 0.33], {})
    assert gen.calls == 4
