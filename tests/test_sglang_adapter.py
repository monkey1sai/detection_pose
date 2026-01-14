from saga.adapters.sglang_adapter import SGLangAdapter


def test_adapter_payload():
    adapter = SGLangAdapter("http://example.com")
    payload = adapter.build_payload("hi")
    assert payload["messages"][0]["content"] == "hi"
