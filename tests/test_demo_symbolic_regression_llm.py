from examples.demo_symbolic_regression import build_llm_stack
from saga.modules.llm import LLMAnalyzer, LLMPlanner, LLMImplementer
from saga.search.generators import LLMGenerator


def test_build_llm_stack_returns_llm_modules():
    client, analyzer, planner, implementer, generator = build_llm_stack(
        "http://example.com/v1/chat/completions", "test-key"
    )

    assert client.url == "http://example.com/v1/chat/completions"
    assert isinstance(analyzer, LLMAnalyzer)
    assert isinstance(planner, LLMPlanner)
    assert isinstance(implementer, LLMImplementer)
    assert isinstance(generator, LLMGenerator)
