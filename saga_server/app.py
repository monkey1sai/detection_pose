from __future__ import annotations

"""SAGA server providing WebSocket observability and artifacts."""

from pathlib import Path

from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles

from saga.config import SagaConfig
from saga.runner import SagaRunner

app = FastAPI()
cfg = SagaConfig()
runner = SagaRunner(cfg)

Path(cfg.run_dir).mkdir(parents=True, exist_ok=True)
app.mount("/runs", StaticFiles(directory=cfg.run_dir), name="runs")


@app.get("/healthz")
def healthz():
    """Health check endpoint."""
    return {"ok": True}


@app.websocket("/ws/run")
async def ws_run(ws: WebSocket):
    await ws.accept()
    data = await ws.receive_json()
    text = data.get("text", "")
    keywords = data.get("keywords", [])
    run_id = data.get("run_id") or ""
    await ws.send_json({"type": "run_started", "run_id": run_id or "pending"})
    await ws.send_json({"type": "node_started", "node": "Analyzer"})
    result = runner.run_once(text, keywords, run_id=run_id or None)
    await ws.send_json(
        {"type": "run_finished", "run_id": result["run_id"], "best_candidate": result["best_candidate"]}
    )
    await ws.close()
