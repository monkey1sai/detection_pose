from saga.scoring.sandbox import run_scoring


def test_scoring_timeout():
    code = "def score(text, ctx):\n    while True: pass\n"
    ok, result = run_scoring(code, "x", {}, timeout_s=0.1)
    assert ok is False
