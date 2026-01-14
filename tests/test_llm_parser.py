from saga.llm.parser import parse_analyzer_output


def test_parse_analyzer_output():
    raw = '{"issues":["low_coverage"],"summary":"coverage low"}'
    data = parse_analyzer_output(raw)
    assert "issues" in data
