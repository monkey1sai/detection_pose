from saga.modules.llm import LLMAnalyzer


class DummyClient:
    def call(self, prompt: str):
        return {"choices": [{"message": {"content": "{\"issues\": [], \"summary\": \"ok\"}"}}]}


def test_llm_analyzer_returns_dict():
    a = LLMAnalyzer(DummyClient())
    out = a.run({"text": "x", "keywords": []})
    assert isinstance(out, dict)
