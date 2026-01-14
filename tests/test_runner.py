from saga.runner import SagaRunner
from saga.config import SagaConfig


def test_runner_single_loop(tmp_path):
    cfg = SagaConfig(run_dir=str(tmp_path))
    runner = SagaRunner(cfg)
    result = runner.run_once("hello world", keywords=["hello"])
    assert result["best_candidate"]
