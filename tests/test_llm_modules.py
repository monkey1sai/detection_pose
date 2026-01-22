from saga.modules.llm import LLMAnalyzer
from saga.outer_loop import LoopState


class DummyClient:
    def call(self, prompt: str):
        return {"choices": [{"message": {"content": "{\"issues\": [], \"summary\": \"ok\"}"}}]}


def test_llm_analyzer_returns_dict():
    a = LLMAnalyzer(DummyClient())
    out = a.run({"text": "x", "keywords": []})
    assert isinstance(out, dict)


def test_llm_analyzer_accepts_loop_state():
    a = LLMAnalyzer(DummyClient())
    state = LoopState(text="hello", keywords=["k1"])
    out = a.run(state)
    assert out["issues"] == []
