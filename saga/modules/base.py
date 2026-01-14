from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class Module(ABC):
    """Base class for outer-loop modules."""
    @abstractmethod
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Run the module and return state updates."""
        raise NotImplementedError
