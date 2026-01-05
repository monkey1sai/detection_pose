from __future__ import annotations

import asyncio
import base64
import json
import time
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional

from .tts_engines.base import AudioSpec, TtsEngine


def json_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


PUNCTUATION = set("，。！？；：,.!?;\n")


@dataclass
class CachedChunk:
    created_s: float
    chunk_seq: int
    unit_index_start: int
    unit_index_end: int
    units_text: str
    audio_format: str
    sample_rate: int
    channels: int
    audio_bytes: bytes

    def to_ws_message(self, *, session_id: str, seq: int) -> Dict[str, Any]:
        return {
            "type": "audio_chunk",
            "session_id": session_id,
            "seq": seq,
            "chunk_seq": self.chunk_seq,
            "unit_index_start": self.unit_index_start,
            "unit_index_end": self.unit_index_end,
            "units_text": self.units_text,
            "audio_format": self.audio_format,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "audio_base64": base64.b64encode(self.audio_bytes).decode("ascii"),
        }


@dataclass
class SessionState:
    session_id: str
    audio_spec: AudioSpec
    ttl_s: float = 120.0
    max_pending_units: int = 24
    max_send_queue: int = 200

    created_s: float = field(default_factory=lambda: time.monotonic())
    last_activity_s: float = field(default_factory=lambda: time.monotonic())

    seq: int = 1
    cancelled: bool = False
    finished: bool = False

    next_unit_index: int = 0
    _pending_units: List[str] = field(default_factory=list)
    _pending_start_index: Optional[int] = None

    chunk_seq: int = 0
    cache: List[CachedChunk] = field(default_factory=list)

    send_queue: "asyncio.Queue[Dict[str, Any]]" = field(init=False)
    cancel_event: asyncio.Event = field(default_factory=asyncio.Event)
    synth_task: Optional[asyncio.Task[None]] = None
    synth_done: asyncio.Event = field(default_factory=asyncio.Event)

    def __post_init__(self) -> None:
        # +1：保留一個位置給 terminal 訊息（error/tts_end），避免在慢 client 時無限制成長。
        self.send_queue = asyncio.Queue(maxsize=self.max_send_queue + 1)

    def touch(self) -> None:
        self.last_activity_s = time.monotonic()

    def is_expired(self) -> bool:
        return (time.monotonic() - self.last_activity_s) > self.ttl_s

    def enqueue_text_units(self, text: str) -> None:
        if not text:
            return
        for ch in list(text):
            if self._pending_start_index is None:
                self._pending_start_index = self.next_unit_index
            self._pending_units.append(ch)
            self.next_unit_index += 1

    def should_flush(self) -> bool:
        if not self._pending_units:
            return False
        if len(self._pending_units) >= self.max_pending_units:
            return True
        last = self._pending_units[-1]
        return last in PUNCTUATION

    def pop_pending_segment(self) -> Optional[Dict[str, Any]]:
        if not self._pending_units:
            return None
        start = self._pending_start_index
        if start is None:
            return None
        units = "".join(self._pending_units)
        end = start + len(self._pending_units) - 1
        self._pending_units = []
        self._pending_start_index = None
        return {"start": start, "end": end, "text": units}

    def cache_chunk(self, chunk: CachedChunk) -> None:
        self.cache.append(chunk)
        # Trim cache by TTL window (keep recent chunks)
        cutoff = time.monotonic() - self.ttl_s
        self.cache = [c for c in self.cache if c.created_s >= cutoff]


class SessionManager:
    def __init__(self, engine: TtsEngine):
        self.engine = engine
        self._sessions: Dict[str, SessionState] = {}
        self._lock = asyncio.Lock()

    async def get_or_create(self, session_id: str, audio_spec: AudioSpec) -> SessionState:
        async with self._lock:
            state = self._sessions.get(session_id)
            if state is not None:
                state.touch()
                return state
            state = SessionState(session_id=session_id, audio_spec=audio_spec)
            self._sessions[session_id] = state
            return state

    async def get(self, session_id: str) -> Optional[SessionState]:
        async with self._lock:
            return self._sessions.get(session_id)

    async def cleanup_loop(self, *, interval_s: float = 5.0) -> None:
        while True:
            await asyncio.sleep(interval_s)
            expired_states: List[SessionState] = []
            async with self._lock:
                expired = [sid for sid, s in self._sessions.items() if s.is_expired()]
                for sid in expired:
                    state = self._sessions.pop(sid, None)
                    if state is not None:
                        expired_states.append(state)
            for state in expired_states:
                try:
                    await self.cancel(state)
                except Exception:
                    pass

    async def start_synth_loop_if_needed(self, state: SessionState) -> None:
        if state.synth_task is not None and not state.synth_task.done():
            return
        state.synth_done.clear()
        state.synth_task = asyncio.create_task(self._synth_loop(state))

    async def cancel(self, state: SessionState) -> None:
        state.cancelled = True
        state.cancel_event.set()
        state.touch()
        if state.synth_task and not state.synth_task.done():
            state.synth_task.cancel()
            try:
                await state.synth_task
            except Exception:
                pass
        state.synth_done.set()

    async def finish(self, state: SessionState) -> None:
        state.finished = True
        state.touch()
        if state.synth_task:
            try:
                await state.synth_task
            except Exception:
                pass

    async def _synth_loop(self, state: SessionState) -> None:
        natural_end = False
        try:
            while not state.cancelled:
                if state.send_queue.qsize() >= state.max_send_queue:
                    try:
                        state.send_queue.put_nowait(
                            {
                                "type": "error",
                                "session_id": state.session_id,
                                "seq": state.seq,
                                "code": "backpressure",
                                "message": "client 讀取過慢，已觸發背壓保護",
                            }
                        )
                    except asyncio.QueueFull:
                        pass
                    state.cancelled = True
                    break

                if not state.should_flush():
                    if state.finished:
                        segment = state.pop_pending_segment()
                        if segment:
                            await self._synthesize_and_enqueue(state, segment)
                        natural_end = True
                        break
                    await asyncio.sleep(0.01)
                    continue

                segment = state.pop_pending_segment()
                if segment is None:
                    await asyncio.sleep(0.01)
                    continue
                await self._synthesize_and_enqueue(state, segment)
        finally:
            state.synth_done.set()
            if natural_end and not state.cancelled:
                try:
                    await state.send_queue.put(
                        {
                            "type": "tts_end",
                            "session_id": state.session_id,
                            "seq": state.seq,
                            "cancelled": False,
                        }
                    )
                except Exception:
                    pass

    async def _synthesize_and_enqueue(self, state: SessionState, segment: Dict[str, Any]) -> None:
        if state.cancelled:
            return
        text = segment["text"]
        unit_start = segment["start"]
        unit_end = segment["end"]

        pcm = await self.engine.synthesize_pcm16(text, spec=state.audio_spec)
        state.chunk_seq += 1
        chunk = CachedChunk(
            created_s=time.monotonic(),
            chunk_seq=state.chunk_seq,
            unit_index_start=unit_start,
            unit_index_end=unit_end,
            units_text=text,
            audio_format=state.audio_spec.audio_format,
            sample_rate=state.audio_spec.sample_rate,
            channels=state.audio_spec.channels,
            audio_bytes=pcm,
        )
        state.cache_chunk(chunk)
        await state.send_queue.put(chunk.to_ws_message(session_id=state.session_id, seq=state.seq))
