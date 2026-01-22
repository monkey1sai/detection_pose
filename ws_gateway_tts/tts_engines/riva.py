from __future__ import annotations

from .base import AudioSpec


class RivaTtsEngine:
    """
    NVIDIA Riva TTS adapter（預留）。

    說明：
    - Riva Python client 套件需另外安裝（通常為 nvidia-riva-client 或對應 SDK）。
    - 本專案先提供 DummyTtsEngine 讓 WS Gateway 可在未安裝 Riva 時先完成開發與測試。
    """

    def __init__(self, *, server: str):
        self.server = server

    async def synthesize_pcm16(self, text: str, *, spec: AudioSpec) -> bytes:
        raise RuntimeError(
            "尚未安裝/整合 Riva client。請先使用 DummyTtsEngine，或補上 Riva gRPC 串流實作。"
        )

