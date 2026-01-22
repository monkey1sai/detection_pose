from __future__ import annotations

import argparse
import asyncio
import json
import os
from typing import Any, Dict, List, Optional

import websockets


def _parse_keywords(values: Optional[List[str]]) -> List[str]:
    if not values:
        return []
    out: List[str] = []
    for v in values:
        parts = [p.strip() for p in v.split(",")]
        out.extend([p for p in parts if p])
    return out


def _parse_json_or_empty(s: Optional[str]) -> Dict[str, Any]:
    if not s:
        return {}
    return json.loads(s)


async def _ainput(prompt: str) -> str:
    return await asyncio.to_thread(input, prompt)


async def run() -> int:
    parser = argparse.ArgumentParser(
        description="Connect to saga_server WebSocket (/ws/run) and print event stream."
    )
    parser.add_argument(
        "--url",
        default=os.getenv("SAGA_WS_URL", "ws://localhost:9200/ws/run"),
        help="WebSocket URL (default: ws://localhost:9200/ws/run; or env SAGA_WS_URL).",
    )
    parser.add_argument(
        "--text",
        default="Find a simple symbolic regression hypothesis for y = x^2 + 1.",
        help="Problem statement text.",
    )
    parser.add_argument(
        "--keywords",
        action="append",
        help="Keywords (repeatable). Also supports comma-separated values.",
    )
    parser.add_argument(
        "--mode",
        default="semi-pilot",
        choices=["co-pilot", "semi-pilot", "autopilot"],
        help="SAGA operation mode.",
    )
    parser.add_argument("--run-id", default=None, help="Optional run_id to reuse.")
    parser.add_argument(
        "--config",
        default=None,
        help="Optional JSON string for config overrides (e.g. '{\"max_iters\":2}').",
    )
    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="Auto-approve when server asks for human review.",
    )
    args = parser.parse_args()

    payload = {
        "text": args.text,
        "keywords": _parse_keywords(args.keywords),
        "mode": args.mode,
        "run_id": args.run_id,
        "config": _parse_json_or_empty(args.config),
    }

    # Disable client keepalive pings: the server can be CPU/LLM bound and may not respond in time.
    async with websockets.connect(
        args.url,
        max_size=64 * 1024 * 1024,
        ping_interval=None,
        close_timeout=3,
    ) as ws:
        await ws.send(json.dumps(payload, ensure_ascii=False))
        print(f"[client] sent payload: {json.dumps(payload, ensure_ascii=False)}")

        while True:
            try:
                raw = await ws.recv()
            except websockets.exceptions.ConnectionClosed as e:
                print(f"[client] connection closed: code={e.code} reason={e.reason!r}")
                return 1
            try:
                msg = json.loads(raw)
            except Exception:
                print(f"[server] {raw}")
                continue

            msg_type = msg.get("type")
            print(f"[server] {json.dumps(msg, ensure_ascii=False)}")

            if msg_type == "need_review":
                if args.auto_approve:
                    await ws.send(json.dumps({"type": "approve"}))
                    print("[client] auto approve sent")
                else:
                    ans = (await _ainput("Review needed. Type 'approve' or 'cancel': ")).strip().lower()
                    if ans not in {"approve", "cancel"}:
                        ans = "approve"
                    await ws.send(json.dumps({"type": ans}))
                    print(f"[client] {ans} sent")

            if msg_type == "run_finished":
                return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
