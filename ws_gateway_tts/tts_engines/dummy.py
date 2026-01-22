from __future__ import annotations

import math
from typing import Final

from .base import AudioSpec


class DummyTtsEngine:
    """
    產生可播放的簡單音訊（非真實 TTS），用於驗證 WS 協定 / cancel / resume / 壓測流程。
    """

    _AMP: Final[int] = 8000
    _FREQ_HZ: Final[float] = 440.0

    async def synthesize_pcm16(self, text: str, *, spec: AudioSpec) -> bytes:
        # 每個字給固定長度音訊，確保逐字對齊可驗證。
        ms_per_unit = 40
        total_ms = max(ms_per_unit, len(text) * ms_per_unit)
        total_samples = int(spec.sample_rate * (total_ms / 1000.0))

        pcm = bytearray()
        for i in range(total_samples):
            t = i / spec.sample_rate
            sample = int(self._AMP * math.sin(2.0 * math.pi * self._FREQ_HZ * t))
            pcm += int(sample).to_bytes(2, byteorder="little", signed=True)
            if spec.channels == 2:
                pcm += int(sample).to_bytes(2, byteorder="little", signed=True)
        return bytes(pcm)
