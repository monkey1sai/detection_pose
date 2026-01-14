from saga.llm.prompts import analyzer_prompt


def test_analyzer_prompt_contains_schema():
    p = analyzer_prompt("text", ["k1"])
    assert "issues" in p
