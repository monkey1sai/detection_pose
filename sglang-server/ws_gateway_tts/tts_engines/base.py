from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class AudioSpec:
    audio_format: str
    sample_rate: int
    channels: int


class TtsEngine(Protocol):
    async def synthesize_pcm16(self, text: str, *, spec: AudioSpec) -> bytes:
        """Return PCM16 (s16le) bytes for the given text."""

