from __future__ import annotations

import json
import os
import urllib.request
from typing import Any, Dict


class SGLangAdapter:
    """HTTP adapter for SGLang chat completions."""

    def __init__(self, url: str, api_key: str = "", model: str | None = None):
        self.url = url
        self.api_key = api_key
        self.model = model or os.getenv("SGLANG_MODEL") or os.getenv("MODEL_NAME") or "twinkle-ai/Llama-3.2-3B-F1-Instruct"

    def build_payload(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Build request payload for SGLang."""
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }
        payload.update(kwargs)
        return payload

    def call(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Call SGLang API and return parsed JSON."""
        payload = self.build_payload(prompt, **kwargs)
        data = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        req = urllib.request.Request(self.url, data=data, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
