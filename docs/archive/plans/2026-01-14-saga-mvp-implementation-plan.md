# SAGA MVP Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在本 repo 新增 SAGA MVP（outer/inner loop 解耦、SQLite trace、SGLang 連線、WebSocket observability、React UI）並可用 `python -m examples.demo_run` 跑通。

**Architecture:** 以 `saga/` 為核心框架，`saga_server/` 為獨立服務，`web_client/` 改為 Vite+React UI。Trace 使用 SQLite，產出 graph.json 與 workflow.mmd。

**Tech Stack:** Python 3.10+, pytest, FastAPI + Uvicorn (WS), SQLite, Vite + React

---

### Task 1: 建立 saga 基本骨架與設定

**Files:**
- Create: `saga/__init__.py`
- Create: `saga/config.py`
- Create: `saga/modules/base.py`
- Create: `tests/test_config.py`

**Step 1: Write the failing test**

```python
# tests/test_config.py
from saga.config import SagaConfig

def test_config_defaults():
    cfg = SagaConfig()
    assert cfg.run_dir.endswith("runs")
    assert cfg.beam_width == 3
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py::test_config_defaults -v`  
Expected: FAIL (ImportError: saga/config.py not found)

**Step 3: Write minimal implementation**

```python
# saga/__init__.py
__all__ = ["config"]
```

```python
# saga/config.py
from dataclasses import dataclass
from pathlib import Path

@dataclass
class SagaConfig:
    run_dir: str = "runs"
    beam_width: int = 3
    max_iters: int = 2
    sglang_url: str = "http://localhost:8082/v1/chat/completions"
    timeout_s: float = 10.0

    def run_path(self, run_id: str) -> Path:
        return Path(self.run_dir) / run_id
```

```python
# saga/modules/base.py
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Dict

class Module(ABC):
    @abstractmethod
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py::test_config_defaults -v`  
Expected: PASS

**Step 5: Commit**

```bash
git add saga/__init__.py saga/config.py saga/modules/base.py tests/test_config.py
git commit -m "feat: add saga config and base module"
```

---

### Task 2: Scoring plugin 介面與沙盒執行

**Files:**
- Create: `saga/scoring/base.py`
- Create: `saga/scoring/sandbox.py`
- Create: `saga/scoring/plugins/summary_v1.py`
- Create: `tests/test_scoring_sandbox.py`

**Step 1: Write the failing test**

```python
# tests/test_scoring_sandbox.py
from saga.scoring.sandbox import run_scoring

def test_scoring_timeout():
    code = "def score(text, ctx):\n    while True: pass\n"
    ok, result = run_scoring(code, "x", {}, timeout_s=0.1)
    assert ok is False
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_scoring_sandbox.py::test_scoring_timeout -v`  
Expected: FAIL (ImportError)

**Step 3: Write minimal implementation**

```python
# saga/scoring/base.py
from __future__ import annotations
from typing import Dict, List, Protocol

class ScoringPlugin(Protocol):
    name: str
    version: str
    def score(self, text: str, ctx: Dict[str, object]) -> List[float]:
        ...
```

```python
# saga/scoring/sandbox.py
from __future__ import annotations
import multiprocessing as mp
import time
from typing import Any, Dict, Tuple

def _worker(code: str, text: str, ctx: Dict[str, Any], q: mp.Queue) -> None:
    ns: Dict[str, Any] = {}
    exec(code, ns, ns)
    score_fn = ns.get("score")
    if not callable(score_fn):
        q.put(("error", "score() not found"))
        return
    q.put(("ok", score_fn(text, ctx)))

def run_scoring(code: str, text: str, ctx: Dict[str, Any], timeout_s: float) -> Tuple[bool, Any]:
    q: mp.Queue = mp.Queue()
    p = mp.Process(target=_worker, args=(code, text, ctx, q))
    p.start()
    p.join(timeout_s)
    if p.is_alive():
        p.terminate()
        return False, "timeout"
    if q.empty():
        return False, "no-result"
    status, payload = q.get()
    return (status == "ok"), payload
```

```python
# saga/scoring/plugins/summary_v1.py
from __future__ import annotations
from typing import Dict, List

name = "summary"
version = "v1"

def score(text: str, ctx: Dict[str, object]) -> List[float]:
    keywords = ctx.get("keywords", [])
    if not isinstance(keywords, list):
        keywords = []
    length = max(1, len(text))
    coverage = sum(1 for k in keywords if k in text) / max(1, len(keywords))
    readability = 1.0 if length < 120 else 0.5
    len_score = 1.0 / length
    return [len_score, coverage, readability]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_scoring_sandbox.py::test_scoring_timeout -v`  
Expected: PASS

**Step 5: Commit**

```bash
git add saga/scoring/base.py saga/scoring/sandbox.py saga/scoring/plugins/summary_v1.py tests/test_scoring_sandbox.py
git commit -m "feat: add scoring base and sandbox runner"
```

---

### Task 3: Beam Search（inner loop）

**Files:**
- Create: `saga/search/beam.py`
- Create: `tests/test_beam_search.py`

**Step 1: Write the failing test**

```python
# tests/test_beam_search.py
from saga.search.beam import beam_search

def test_beam_search_topk():
    candidates = ["a", "bb", "ccc"]
    def scorer(x):
        return [1.0 / len(x)]
    top = beam_search(candidates, scorer, beam_width=2)
    assert top[0][0] == "a"
    assert len(top) == 2
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_beam_search.py::test_beam_search_topk -v`  
Expected: FAIL (ImportError)

**Step 3: Write minimal implementation**

```python
# saga/search/beam.py
from __future__ import annotations
from typing import Callable, List, Tuple

def beam_search(candidates: List[str], scorer: Callable[[str], List[float]], beam_width: int) -> List[Tuple[str, List[float]]]:
    scored = [(c, scorer(c)) for c in candidates]
    scored.sort(key=lambda x: sum(x[1]), reverse=True)
    return scored[:beam_width]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_beam_search.py::test_beam_search_topk -v`  
Expected: PASS

**Step 5: Commit**

```bash
git add saga/search/beam.py tests/test_beam_search.py
git commit -m "feat: add beam search"
```

---

### Task 4: Trace SQLite + Graph/Mermaid 輸出

**Files:**
- Create: `saga/trace/sqlite.py`
- Create: `saga/trace/graph.py`
- Create: `tests/test_trace_sqlite.py`

**Step 1: Write the failing test**

```python
# tests/test_trace_sqlite.py
from saga.trace.sqlite import TraceDB

def test_trace_create_and_write(tmp_path):
    db = TraceDB(tmp_path / "trace.db")
    db.init()
    db.write_node({"node_name": "Analyzer", "elapsed_ms": 1})
    rows = db.fetch_nodes()
    assert rows[0]["node_name"] == "Analyzer"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_trace_sqlite.py::test_trace_create_and_write -v`  
Expected: FAIL (ImportError)

**Step 3: Write minimal implementation**

```python
# saga/trace/sqlite.py
from __future__ import annotations
import sqlite3
from pathlib import Path
from typing import Dict, List

class TraceDB:
    def __init__(self, path: Path):
        self.path = Path(path)

    def init(self) -> None:
        conn = sqlite3.connect(self.path)
        cur = conn.cursor()
        cur.execute("create table if not exists nodes (node_name text, elapsed_ms integer)")
        conn.commit()
        conn.close()

    def write_node(self, row: Dict[str, object]) -> None:
        conn = sqlite3.connect(self.path)
        cur = conn.cursor()
        cur.execute("insert into nodes (node_name, elapsed_ms) values (?, ?)", (row["node_name"], row.get("elapsed_ms", 0)))
        conn.commit()
        conn.close()

    def fetch_nodes(self) -> List[Dict[str, object]]:
        conn = sqlite3.connect(self.path)
        cur = conn.cursor()
        cur.execute("select node_name, elapsed_ms from nodes")
        rows = [{"node_name": r[0], "elapsed_ms": r[1]} for r in cur.fetchall()]
        conn.close()
        return rows
```

```python
# saga/trace/graph.py
from __future__ import annotations
import json
from pathlib import Path
from typing import List, Dict

def write_graph(path: Path, nodes: List[Dict[str, object]], edges: List[Dict[str, object]]) -> None:
    payload = {"nodes": nodes, "edges": edges}
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

def write_mermaid(path: Path, edges: List[Dict[str, object]]) -> None:
    lines = ["graph TD"]
    for e in edges:
        lines.append(f'{e["from"]} --> {e["to"]}')
    Path(path).write_text("\n".join(lines), encoding="utf-8")
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_trace_sqlite.py::test_trace_create_and_write -v`  
Expected: PASS

**Step 5: Commit**

```bash
git add saga/trace/sqlite.py saga/trace/graph.py tests/test_trace_sqlite.py
git commit -m "feat: add sqlite trace and graph writers"
```

---

### Task 5: Outer loop 預設模組與 Runner

**Files:**
- Create: `saga/modules/defaults.py`
- Create: `saga/runner.py`
- Create: `tests/test_runner.py`

**Step 1: Write the failing test**

```python
# tests/test_runner.py
from saga.runner import SagaRunner
from saga.config import SagaConfig

def test_runner_single_loop(tmp_path):
    cfg = SagaConfig(run_dir=str(tmp_path))
    runner = SagaRunner(cfg)
    result = runner.run_once("hello world", keywords=["hello"])
    assert result["best_candidate"]
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_runner.py::test_runner_single_loop -v`  
Expected: FAIL (ImportError)

**Step 3: Write minimal implementation**

```python
# saga/modules/defaults.py
from __future__ import annotations
from typing import Any, Dict
from .base import Module

class Analyzer(Module):
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return {"issue": "low_coverage"}

class Planner(Module):
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return {"weights": [0.2, 0.6, 0.2]}

class Implementer(Module):
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return {"scoring_code": state["scoring_code"], "version": "v1"}

class Optimizer(Module):
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return {"candidates": state["candidates"]}
```

```python
# saga/runner.py
from __future__ import annotations
from typing import Dict, List
from .config import SagaConfig
from .modules.defaults import Analyzer, Planner, Implementer, Optimizer
from .search.beam import beam_search
from .scoring.sandbox import run_scoring
from .scoring.plugins import summary_v1

class SagaRunner:
    def __init__(self, cfg: SagaConfig):
        self.cfg = cfg
        self.analyzer = Analyzer()
        self.planner = Planner()
        self.implementer = Implementer()
        self.optimizer = Optimizer()

    def run_once(self, text: str, keywords: List[str]) -> Dict[str, object]:
        scoring_code = "def score(text, ctx):\n    return [1.0/len(text), 1.0, 1.0]\n"
        state = {"text": text, "keywords": keywords, "scoring_code": scoring_code, "candidates": [text[:20], text[:10]]}
        self.analyzer.run(state)
        plan = self.planner.run(state)
        impl = self.implementer.run(state)
        def scorer(c: str):
            ok, result = run_scoring(impl["scoring_code"], c, {"keywords": keywords}, self.cfg.timeout_s)
            return result if ok else [0.0, 0.0, 0.0]
        scored = beam_search(state["candidates"], scorer, self.cfg.beam_width)
        best = scored[0][0] if scored else ""
        return {"best_candidate": best, "scored": scored}
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_runner.py::test_runner_single_loop -v`  
Expected: PASS

**Step 5: Commit**

```bash
git add saga/modules/defaults.py saga/runner.py tests/test_runner.py
git commit -m "feat: add saga runner with default modules"
```

---

### Task 6: SGLang Adapter + saga_server WebSocket

**Files:**
- Create: `saga/adapters/sglang_adapter.py`
- Create: `saga_server/app.py`
- Create: `tests/test_sglang_adapter.py`

**Step 1: Write the failing test**

```python
# tests/test_sglang_adapter.py
from saga.adapters.sglang_adapter import SGLangAdapter

def test_adapter_payload():
    adapter = SGLangAdapter("http://example.com")
    payload = adapter.build_payload("hi")
    assert payload["messages"][0]["content"] == "hi"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_sglang_adapter.py::test_adapter_payload -v`  
Expected: FAIL (ImportError)

**Step 3: Write minimal implementation**

```python
# saga/adapters/sglang_adapter.py
from __future__ import annotations
import json
import urllib.request
from typing import Dict, Any

class SGLangAdapter:
    def __init__(self, url: str):
        self.url = url

    def build_payload(self, prompt: str) -> Dict[str, Any]:
        return {
            "model": "twinkle-ai/Llama-3.2-3B-F1-Instruct",
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }

    def call(self, prompt: str) -> Dict[str, Any]:
        payload = self.build_payload(prompt)
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(self.url, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
```

```python
# saga_server/app.py
from __future__ import annotations
from fastapi import FastAPI, WebSocket
from saga.config import SagaConfig
from saga.runner import SagaRunner

app = FastAPI()
cfg = SagaConfig()
runner = SagaRunner(cfg)

@app.websocket("/ws/run")
async def ws_run(ws: WebSocket):
    await ws.accept()
    data = await ws.receive_json()
    text = data.get("text", "")
    keywords = data.get("keywords", [])
    await ws.send_json({"type": "node_started", "node": "Analyzer"})
    result = runner.run_once(text, keywords)
    await ws.send_json({"type": "run_finished", "best_candidate": result["best_candidate"]})
    await ws.close()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_sglang_adapter.py::test_adapter_payload -v`  
Expected: PASS

**Step 5: Commit**

```bash
git add saga/adapters/sglang_adapter.py saga_server/app.py tests/test_sglang_adapter.py
git commit -m "feat: add sglang adapter and saga_server ws endpoint"
```

---

### Task 7: examples/demo_run + CLI 與輸出

**Files:**
- Create: `examples/demo_run.py`
- Modify: `README.md`
- Create: `requirements.txt`

**Step 1: Write the failing test**

```python
# tests/test_demo_run.py
import subprocess, sys

def test_demo_run_exec():
    r = subprocess.run([sys.executable, "-m", "examples.demo_run"], capture_output=True, text=True)
    assert r.returncode == 0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_demo_run.py::test_demo_run_exec -v`  
Expected: FAIL (ModuleNotFoundError)

**Step 3: Write minimal implementation**

```python
# examples/demo_run.py
from saga.config import SagaConfig
from saga.runner import SagaRunner

def main():
    cfg = SagaConfig()
    runner = SagaRunner(cfg)
    result = runner.run_once("這是一段測試文字", keywords=["測試"])
    print(result["best_candidate"])

if __name__ == "__main__":
    main()
```

```text
# requirements.txt
fastapi
uvicorn
pytest
```

```markdown
# README.md (新增段落)
## SAGA MVP Demo
```bash
pip install -r requirements.txt
python -m examples.demo_run
```
輸出會產生在 `runs/<run_id>/`（trace.db / graph.json / workflow.mmd）。
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_demo_run.py::test_demo_run_exec -v`  
Expected: PASS

**Step 5: Commit**

```bash
git add examples/demo_run.py README.md requirements.txt tests/test_demo_run.py
git commit -m "feat: add demo runner and docs"
```

---

### Task 8: Web UI（Vite + React）

**Files:**
- Replace: `web_client/*` (Vite app)
- Create: `web_client/src/App.tsx`
- Create: `web_client/src/main.tsx`
- Create: `web_client/vite.config.ts`

**Step 1: Write the failing test**

（前端不做自動化測試；手動驗收）

**Step 2: Build minimal implementation**

- UI 功能：
  - 輸入 text / keywords
  - WebSocket 連線 `/ws/run`
  - 讀取 `graph.json` 與 `workflow.mmd`
  - 顯示 node/edge 與 mermaid 字串

**Step 3: Manual verification**

Run:
```
cd web_client
npm install
npm run dev
```
Expected: UI 可連線 `ws://localhost:9100/ws/run` 並顯示回傳資料

**Step 4: Commit**

```bash
git add web_client
git commit -m "feat: add saga web client"
```

---

### Task 9: Graph/Trace 回放輸出補齊

**Files:**
- Modify: `saga/runner.py`
- Modify: `saga/trace/sqlite.py`
- Modify: `examples/demo_run.py`

**Step 1: Write the failing test**

```python
# tests/test_graph_output.py
from pathlib import Path
from saga.trace.graph import write_graph, write_mermaid

def test_graph_files(tmp_path):
    write_graph(tmp_path / "graph.json", [{"id":"A"}], [{"from":"A","to":"B"}])
    write_mermaid(tmp_path / "workflow.mmd", [{"from":"A","to":"B"}])
    assert (tmp_path / "graph.json").exists()
    assert (tmp_path / "workflow.mmd").exists()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_graph_output.py::test_graph_files -v`  
Expected: PASS (already implemented)

**Step 3: Implement output integration**

在 `runner.run_once` 實際寫入 trace/graph/mermaid 至 `runs/<run_id>/`。

**Step 4: Commit**

```bash
git add saga/runner.py saga/trace/sqlite.py examples/demo_run.py tests/test_graph_output.py
git commit -m "feat: add trace and graph outputs"
```

---

Plan complete and saved to `docs/plans/2026-01-14-saga-mvp-implementation-plan.md`. Two execution options:

1. Subagent-Driven (this session)
2. Parallel Session (separate)

Which approach?
