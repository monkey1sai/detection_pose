from saga.search.beam import beam_search


def test_beam_search_topk():
    candidates = ["a", "bb", "ccc"]

    def scorer(x):
        return [1.0 / len(x)]

    top = beam_search(candidates, scorer, beam_width=2)
    assert top[0][0] == "a"
    assert len(top) == 2
