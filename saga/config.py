"""Configuration for SAGA runs."""

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SagaConfig:
    """Runtime config for SAGA components."""
    run_dir: str = "runs"
    beam_width: int = 3
    max_iters: int = 2
    sglang_url: str = "http://localhost:8082/v1/chat/completions"
    timeout_s: float = 10.0
    sglang_api_key: str = ""
    use_sglang: bool = False
    use_llm_modules: bool = False

    def run_path(self, run_id: str) -> Path:
        """Return run output directory for the given run_id."""
        return Path(self.run_dir) / run_id

    @classmethod
    def from_file(cls, path: str) -> "SagaConfig":
        """Load config from a JSON file."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(**data)
