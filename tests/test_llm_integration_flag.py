from saga.config import SagaConfig


def test_config_has_llm_flag():
    cfg = SagaConfig()
    assert hasattr(cfg, "use_llm_modules")
