from __future__ import annotations

from typing import Dict, List

"""Default scoring plugin for summary toy domain."""

name = "summary"
version = "v1"


def score(text: str, ctx: Dict[str, object]) -> List[float]:
    """Return [len_score, keyword_coverage, readability]."""
    keywords = ctx.get("keywords", [])
    if not isinstance(keywords, list):
        keywords = []
    length = max(1, len(text))
    coverage = sum(1 for k in keywords if k in text) / max(1, len(keywords))
    readability = 1.0 if length < 120 else 0.5
    len_score = 1.0 / length
    return [len_score, coverage, readability]
