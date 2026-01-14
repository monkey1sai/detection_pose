from saga.config import SagaConfig


def test_config_defaults():
    cfg = SagaConfig()
    assert cfg.run_dir.endswith("runs")
    assert cfg.beam_width == 3
