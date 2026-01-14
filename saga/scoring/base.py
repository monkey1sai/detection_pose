from __future__ import annotations

from typing import Dict, List, Protocol


class ScoringPlugin(Protocol):
    """Protocol for scoring plugins."""
    name: str
    version: str

    def score(self, text: str, ctx: Dict[str, object]) -> List[float]:
        """Return a score vector for text given context."""
        ...
