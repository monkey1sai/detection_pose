from __future__ import annotations

from typing import Callable, List, Tuple


def beam_search(
    candidates: List[str],
    scorer: Callable[[str], List[float]],
    beam_width: int,
) -> List[Tuple[str, List[float]]]:
    """Score candidates and return top-k by summed score."""
    scored = [(c, scorer(c)) for c in candidates]
    scored.sort(key=lambda x: sum(x[1]), reverse=True)
    return scored[:beam_width]
