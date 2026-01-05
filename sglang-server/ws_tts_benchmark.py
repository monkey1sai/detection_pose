import argparse
import asyncio
import base64
import json
import os
import random
import statistics
import sys
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import aiohttp

# Force UTF-8 output for Windows console
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


DEFAULT_TEXT = (
    "今天天氣不錯，我想測試即時語音合成。"
    "請把這段文字逐字轉成語音，並透過 WebSocket 以串流方式傳輸。"
    "如果我中途取消或斷線重連，也要能正確停止與續傳。"
)


def now_s() -> float:
    return time.perf_counter()


def percentile(sorted_values: List[float], p: float) -> float:
    if not sorted_values:
        return 0.0
    if p <= 0:
        return sorted_values[0]
    if p >= 100:
        return sorted_values[-1]
    idx = (len(sorted_values) - 1) * (p / 100.0)
    lo = int(idx)
    hi = min(lo + 1, len(sorted_values) - 1)
    frac = idx - lo
    return sorted_values[lo] * (1 - frac) + sorted_values[hi] * frac


@dataclass
class SessionConfig:
    url: str
    cps: float
    duration_s: float
    audio_format: str
    sample_rate: int
    channels: int
    cache_window_s: float
    scenario: str
    disconnect_percent: float
    cancel_percent: float
    backpressure_percent: float
    backpressure_pause_s: float
    reconnect_delay_s: float


@dataclass
class SessionMetrics:
    session_id: str
    sent_units: int = 0
    received_units: int = 0
    mismatched_units: int = 0
    missing_units: int = 0
    duplicate_units: int = 0
    errors: List[str] = field(default_factory=list)
    ttfa_s: Optional[float] = None
    unit_latencies_s: List[float] = field(default_factory=list)

    _start_s: float = field(default_factory=now_s)
    _send_time_by_unit: Dict[int, float] = field(default_factory=dict)
    _recv_time_by_unit: Dict[int, float] = field(default_factory=dict)


def load_text(text_file: Optional[str]) -> str:
    if not text_file:
        return DEFAULT_TEXT
    with open(text_file, "r", encoding="utf-8") as f:
        return f.read().strip()


def iter_units(text: str) -> List[str]:
    return list(text)


def json_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


async def ws_send_json(ws: aiohttp.ClientWebSocketResponse, payload: Dict[str, Any]) -> None:
    await ws.send_str(json_dumps(payload))


def safe_parse_json(data: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    try:
        parsed = json.loads(data)
        if isinstance(parsed, dict):
            return parsed, None
        return None, "JSON 不是物件"
    except Exception as e:
        return None, f"JSON 解析失敗: {e}"


def normalize_audio_bytes(message: Dict[str, Any]) -> Optional[bytes]:
    audio_b64 = message.get("audio_base64")
    if not audio_b64:
        return None
    if not isinstance(audio_b64, str):
        return None
    try:
        return base64.b64decode(audio_b64)
    except Exception:
        return None


class WsTtsSessionRunner:
    def __init__(self, cfg: SessionConfig, text: str, session_id: str):
        self.cfg = cfg
        self.text = text
        self.units = iter_units(text)
        self.session_id = session_id

        self.metrics = SessionMetrics(session_id=session_id)
        self._stop = asyncio.Event()
        self._pause_read = asyncio.Event()
        self._pause_read.clear()

        self._last_unit_index_received = -1
        self._seq = 1

    async def run(self) -> SessionMetrics:
        disconnect_enabled = random.random() < self.cfg.disconnect_percent
        cancel_enabled = random.random() < self.cfg.cancel_percent
        backpressure_enabled = random.random() < self.cfg.backpressure_percent

        cancel_at_s = None
        disconnect_at_s = None
        backpressure_at_s = None

        if cancel_enabled:
            cancel_at_s = random.uniform(self.cfg.duration_s * 0.2, self.cfg.duration_s * 0.8)
        if disconnect_enabled:
            disconnect_at_s = random.uniform(self.cfg.duration_s * 0.2, self.cfg.duration_s * 0.8)
        if backpressure_enabled:
            backpressure_at_s = random.uniform(self.cfg.duration_s * 0.2, self.cfg.duration_s * 0.8)

        start_s = now_s()
        try:
            async with aiohttp.ClientSession() as session:
                ws = await self._connect(session)
                receiver_task = asyncio.create_task(self._receiver_loop(ws))
                sender_task = asyncio.create_task(
                    self._sender_loop(
                        session=session,
                        ws=ws,
                        start_s=start_s,
                        cancel_at_s=cancel_at_s,
                        disconnect_at_s=disconnect_at_s,
                        backpressure_at_s=backpressure_at_s,
                    )
                )

                await asyncio.wait(
                    [receiver_task, sender_task],
                    return_when=asyncio.FIRST_EXCEPTION,
                )

                if sender_task.done() and sender_task.exception():
                    raise sender_task.exception()
                if receiver_task.done() and receiver_task.exception():
                    raise receiver_task.exception()
        except Exception as e:
            self.metrics.errors.append(str(e))
        finally:
            self._stop.set()
            self._finalize_metrics()
            return self.metrics

    async def _connect(self, session: aiohttp.ClientSession) -> aiohttp.ClientWebSocketResponse:
        ws = await session.ws_connect(self.cfg.url, heartbeat=30)
        await ws_send_json(
            ws,
            {
                "type": "start",
                "session_id": self.session_id,
                "audio_format": self.cfg.audio_format,
                "sample_rate": self.cfg.sample_rate,
                "channels": self.cfg.channels,
            },
        )
        return ws

    async def _send_text_delta(self, ws: aiohttp.ClientWebSocketResponse, text: str) -> None:
        await ws_send_json(
            ws,
            {
                "type": "text_delta",
                "session_id": self.session_id,
                "seq": self._seq,
                "text": text,
            },
        )

    async def _send_text_end(self, ws: aiohttp.ClientWebSocketResponse) -> None:
        await ws_send_json(
            ws,
            {
                "type": "text_end",
                "session_id": self.session_id,
                "seq": self._seq,
            },
        )

    async def _send_cancel(self, ws: aiohttp.ClientWebSocketResponse) -> None:
        await ws_send_json(
            ws,
            {
                "type": "cancel",
                "session_id": self.session_id,
                "seq": self._seq,
            },
        )

    async def _send_resume(self, ws: aiohttp.ClientWebSocketResponse) -> None:
        await ws_send_json(
            ws,
            {
                "type": "resume",
                "session_id": self.session_id,
                "last_unit_index_received": self._last_unit_index_received,
            },
        )

    async def _sender_loop(
        self,
        *,
        session: aiohttp.ClientSession,
        ws: aiohttp.ClientWebSocketResponse,
        start_s: float,
        cancel_at_s: Optional[float],
        disconnect_at_s: Optional[float],
        backpressure_at_s: Optional[float],
    ) -> None:
        unit_interval_s = 1.0 / self.cfg.cps if self.cfg.cps > 0 else 0.0
        next_send_s = start_s

        disconnected = False
        cancelled = False
        unit_index = 0

        while not self._stop.is_set():
            elapsed_s = now_s() - start_s
            if elapsed_s >= self.cfg.duration_s:
                # 結束前送出 text_end，讓 server flush pending units 並回 tts_end。
                try:
                    await self._send_text_end(ws)
                except Exception:
                    pass
                break

            if backpressure_at_s is not None and elapsed_s >= backpressure_at_s:
                backpressure_at_s = None
                self._pause_read.set()
                await asyncio.sleep(self.cfg.backpressure_pause_s)
                self._pause_read.clear()

            if cancel_at_s is not None and elapsed_s >= cancel_at_s and not cancelled:
                cancelled = True
                try:
                    await self._send_cancel(ws)
                except Exception:
                    pass
                break

            if disconnect_at_s is not None and elapsed_s >= disconnect_at_s and not disconnected:
                disconnected = True
                try:
                    await ws.close()
                except Exception:
                    pass
                await asyncio.sleep(self.cfg.reconnect_delay_s)
                ws = await self._connect(session)
                await self._send_resume(ws)

            if now_s() < next_send_s:
                await asyncio.sleep(min(0.05, max(0.0, next_send_s - now_s())))
                continue

            if unit_index >= len(self.units):
                try:
                    await self._send_text_end(ws)
                except Exception:
                    pass
                break

            unit = self.units[unit_index]
            self.metrics._send_time_by_unit[unit_index] = now_s()
            self.metrics.sent_units += 1
            await self._send_text_delta(ws, unit)

            unit_index += 1
            next_send_s += unit_interval_s
        # 讓 receiver_loop 接收 tts_end/error 後結束；避免過早停止導致缺漏。

    async def _receiver_loop(self, ws: aiohttp.ClientWebSocketResponse) -> None:
        while not self._stop.is_set():
            if self._pause_read.is_set():
                await asyncio.sleep(0.05)
                continue

            try:
                msg = await ws.receive(timeout=1.0)
            except asyncio.TimeoutError:
                continue
            if msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSING):
                await asyncio.sleep(0.05)
                continue
            if msg.type == aiohttp.WSMsgType.ERROR:
                self.metrics.errors.append(f"WebSocket ERROR: {ws.exception()}")
                break
            if msg.type != aiohttp.WSMsgType.TEXT:
                continue

            parsed, err = safe_parse_json(msg.data)
            if err:
                self.metrics.errors.append(err)
                continue

            message_type = parsed.get("type")
            if message_type == "audio_chunk":
                self._handle_audio_chunk(parsed)
            elif message_type == "tts_end":
                self._stop.set()
                break
            elif message_type == "error":
                code = parsed.get("code", "unknown")
                message = parsed.get("message", "")
                self.metrics.errors.append(f"{code}: {message}")
                self._stop.set()
                break

    def _handle_audio_chunk(self, message: Dict[str, Any]) -> None:
        if self.metrics.ttfa_s is None:
            self.metrics.ttfa_s = now_s() - self.metrics._start_s

        unit_start = message.get("unit_index_start")
        unit_end = message.get("unit_index_end")
        units_text = message.get("units_text")

        if not isinstance(unit_start, int) or not isinstance(unit_end, int) or unit_end < unit_start:
            self.metrics.errors.append("audio_chunk unit_index 範圍不合法")
            return
        if not isinstance(units_text, str):
            self.metrics.errors.append("audio_chunk units_text 不合法")
            return

        expected = "".join(self.units[unit_start : unit_end + 1])
        if units_text != expected:
            mismatch_len = max(len(expected), len(units_text))
            self.metrics.mismatched_units += mismatch_len

        for unit_index in range(unit_start, unit_end + 1):
            recv_t = now_s()
            if unit_index in self.metrics._recv_time_by_unit:
                self.metrics.duplicate_units += 1
                continue
            self.metrics._recv_time_by_unit[unit_index] = recv_t
            self.metrics.received_units += 1
            self._last_unit_index_received = max(self._last_unit_index_received, unit_index)

            sent_t = self.metrics._send_time_by_unit.get(unit_index)
            if sent_t is not None:
                self.metrics.unit_latencies_s.append(max(0.0, recv_t - sent_t))

        _ = normalize_audio_bytes(message)

    def _finalize_metrics(self) -> None:
        sent = self.metrics.sent_units
        received = len(self.metrics._recv_time_by_unit)
        if received < sent:
            self.metrics.missing_units = sent - received


def summarize(all_metrics: List[SessionMetrics], duration_s: float) -> str:
    sessions = len(all_metrics)
    errors = sum(1 for m in all_metrics if m.errors)
    sent_units = sum(m.sent_units for m in all_metrics)
    received_units = sum(m.received_units for m in all_metrics)
    missing_units = sum(m.missing_units for m in all_metrics)
    duplicate_units = sum(m.duplicate_units for m in all_metrics)
    mismatched_units = sum(m.mismatched_units for m in all_metrics)

    ttfa_values = sorted([m.ttfa_s for m in all_metrics if m.ttfa_s is not None])
    all_latencies = sorted([v for m in all_metrics for v in m.unit_latencies_s])

    lines = []
    lines.append("=" * 50)
    lines.append("WS TTS 壓測報告（逐字對齊 / cancel / resume）")
    lines.append("=" * 50)
    lines.append(f"Session 數: {sessions}")
    lines.append(f"測試時間: {duration_s:.1f}s")
    lines.append(f"總送出 units: {sent_units}")
    lines.append(f"總收到 units: {received_units}")
    lines.append(f"缺漏 units: {missing_units}")
    lines.append(f"重複 units: {duplicate_units}")
    lines.append(f"不一致 units(估算): {mismatched_units}")
    lines.append(f"錯誤 session: {errors}")
    if duration_s > 0:
        lines.append(f"輸入速率(估算): {sent_units / duration_s:.2f} units/s")
        lines.append(f"輸出速率(估算): {received_units / duration_s:.2f} units/s")

    if ttfa_values:
        lines.append("-" * 50)
        lines.append("TTFA（首段音訊延遲）")
        lines.append(f"  p50: {percentile(ttfa_values, 50) * 1000:.0f} ms")
        lines.append(f"  p95: {percentile(ttfa_values, 95) * 1000:.0f} ms")
        lines.append(f"  p99: {percentile(ttfa_values, 99) * 1000:.0f} ms")

    if all_latencies:
        lines.append("-" * 50)
        lines.append("UnitLatency（每字延遲）")
        lines.append(f"  p50: {percentile(all_latencies, 50) * 1000:.0f} ms")
        lines.append(f"  p95: {percentile(all_latencies, 95) * 1000:.0f} ms")
        lines.append(f"  p99: {percentile(all_latencies, 99) * 1000:.0f} ms")

    lines.append("=" * 50)
    return "\n".join(lines)


async def run_benchmark(args: argparse.Namespace) -> int:
    text = load_text(args.text_file)
    if args.scenario == "baseline":
        args.disconnect_percent = 0.0
        args.cancel_percent = 0.0
        args.backpressure_percent = 0.0

    cfg = SessionConfig(
        url=args.url,
        cps=args.cps,
        duration_s=args.duration,
        audio_format=args.audio_format,
        sample_rate=args.sample_rate,
        channels=args.channels,
        cache_window_s=args.cache_window_s,
        scenario=args.scenario,
        disconnect_percent=args.disconnect_percent,
        cancel_percent=args.cancel_percent,
        backpressure_percent=args.backpressure_percent,
        backpressure_pause_s=args.backpressure_pause_s,
        reconnect_delay_s=args.reconnect_delay_s,
    )

    runners = []
    for _ in range(args.concurrency):
        session_id = str(uuid.uuid4())
        runners.append(WsTtsSessionRunner(cfg, text, session_id))

    start_s = now_s()
    results = await asyncio.gather(*[r.run() for r in runners])
    end_s = now_s()

    print(summarize(results, end_s - start_s), flush=True)

    if args.output_json:
        os.makedirs(os.path.dirname(args.output_json) or ".", exist_ok=True)
        payload = {
            "config": {
                "url": args.url,
                "concurrency": args.concurrency,
                "cps": args.cps,
                "duration": args.duration,
                "audio_format": args.audio_format,
                "sample_rate": args.sample_rate,
                "channels": args.channels,
                "disconnect_percent": args.disconnect_percent,
                "cancel_percent": args.cancel_percent,
                "backpressure_percent": args.backpressure_percent,
                "backpressure_pause_s": args.backpressure_pause_s,
                "reconnect_delay_s": args.reconnect_delay_s,
            },
            "summary": {
                "sessions": len(results),
                "errors": sum(1 for m in results if m.errors),
                "sent_units": sum(m.sent_units for m in results),
                "received_units": sum(m.received_units for m in results),
                "missing_units": sum(m.missing_units for m in results),
                "duplicate_units": sum(m.duplicate_units for m in results),
                "mismatched_units": sum(m.mismatched_units for m in results),
            },
            "sessions": [
                {
                    "session_id": m.session_id,
                    "sent_units": m.sent_units,
                    "received_units": m.received_units,
                    "missing_units": m.missing_units,
                    "duplicate_units": m.duplicate_units,
                    "mismatched_units": m.mismatched_units,
                    "ttfa_s": m.ttfa_s,
                    "unit_latency_ms_p50": percentile(sorted(m.unit_latencies_s), 50) * 1000
                    if m.unit_latencies_s
                    else None,
                    "unit_latency_ms_p95": percentile(sorted(m.unit_latencies_s), 95) * 1000
                    if m.unit_latencies_s
                    else None,
                    "errors": m.errors,
                }
                for m in results
            ],
        }
        with open(args.output_json, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="WebSocket 即時 TTS 壓力測試（逐字對齊 / cancel / resume）")
    parser.add_argument("--url", required=True, help="WebSocket URL，例如 ws://localhost:9000/tts")
    parser.add_argument("--concurrency", type=int, default=50, help="同時連線數")
    parser.add_argument("--cps", type=float, default=5.0, help="每秒送出字元數（逐字輸入）")
    parser.add_argument("--duration", type=float, default=600.0, help="測試秒數")
    parser.add_argument("--text-file", help="測試文字檔（UTF-8），未提供則用內建繁中範例")
    parser.add_argument("--audio-format", default="pcm16_wav", help="期望音訊格式（建議 pcm16_wav）")
    parser.add_argument("--sample-rate", type=int, default=16000, help="取樣率")
    parser.add_argument("--channels", type=int, default=1, help="聲道數")

    parser.add_argument("--scenario", default="mixed", choices=["baseline", "mixed"], help="測試情境")
    parser.add_argument("--disconnect-percent", type=float, default=0.10, help="斷線並 resume 的 session 比例")
    parser.add_argument("--cancel-percent", type=float, default=0.10, help="中途 cancel 的 session 比例")
    parser.add_argument("--backpressure-percent", type=float, default=0.10, help="模擬背壓（暫停讀取）的 session 比例")
    parser.add_argument("--backpressure-pause-s", type=float, default=5.0, help="背壓暫停讀取秒數")
    parser.add_argument("--reconnect-delay-s", type=float, default=5.0, help="斷線後重連等待秒數")
    parser.add_argument("--cache-window-s", type=float, default=120.0, help="resume 快取窗（用於測試設定/紀錄）")

    parser.add_argument("--output-json", help="輸出 JSON 報告檔路徑（例如 logs/ws_tts_report.json）")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    print("開始執行 WS TTS 壓測...", flush=True)
    print(f"URL: {args.url}", flush=True)
    print(f"concurrency={args.concurrency}, cps={args.cps}, duration={args.duration}s", flush=True)
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    return asyncio.run(run_benchmark(args))


if __name__ == "__main__":
    raise SystemExit(main())
