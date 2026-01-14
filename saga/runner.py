from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Dict, List

from .config import SagaConfig
from .adapters.sglang_adapter import SGLangAdapter
from .modules.defaults import Analyzer, Planner, Implementer, Optimizer
from .modules.llm import LLMAnalyzer, LLMPlanner, LLMImplementer
from .search.beam import beam_search
from .scoring.sandbox import run_scoring
from .trace.graph import write_graph, write_mermaid
from .trace.sqlite import TraceDB


class SagaRunner:
    """Run a single SAGA outer/inner loop cycle."""
    def __init__(self, cfg: SagaConfig):
        self.cfg = cfg
        if cfg.use_llm_modules:
            client = SGLangAdapter(cfg.sglang_url, cfg.sglang_api_key)
            self.analyzer = LLMAnalyzer(client)
            self.planner = LLMPlanner(client)
            self.implementer = LLMImplementer(client)
        else:
            self.analyzer = Analyzer()
            self.planner = Planner()
            self.implementer = Implementer()
        self.optimizer = Optimizer()

    def run_once(self, text: str, keywords: List[str], run_id: str | None = None) -> Dict[str, object]:
        """Execute one SAGA run and persist trace artifacts."""
        run_id = run_id or uuid.uuid4().hex
        run_dir = self.cfg.run_path(run_id)
        run_dir.mkdir(parents=True, exist_ok=True)
        db = TraceDB(run_dir / "trace.db")
        db.init()

        scoring_code = "def score(text, ctx):\n    return [1.0/len(text), 1.0, 1.0]\n"
        candidates = [text[:20], text[:10]]
        if self.cfg.use_sglang:
            adapter = SGLangAdapter(self.cfg.sglang_url, self.cfg.sglang_api_key)
            prompt = f"請將以下文字摘要成一句話：{text}"
            try:
                resp = adapter.call(prompt)
                msg = resp.get("choices", [{}])[0].get("message", {}).get("content", "")
                if isinstance(msg, str) and msg.strip():
                    candidates.insert(0, msg.strip())
            except Exception:
                pass

        state = {
            "text": text,
            "keywords": keywords,
            "scoring_code": scoring_code,
            "candidates": candidates,
        }
        goal_set_version = "v1"

        t0 = time.perf_counter()
        try:
            analyzer_out = self.analyzer.run(state)
        except Exception as exc:
            analyzer_out = {"issues": ["llm_error"], "summary": str(exc)}
        state["analysis"] = analyzer_out
        db.write_node(
            {
                "node_name": "Analyzer",
                "input_summary": f"text_len={len(text)} keywords={len(keywords)}",
                "output_summary": json.dumps(analyzer_out, ensure_ascii=False),
                "goal_set_version": goal_set_version,
                "elapsed_ms": int((time.perf_counter() - t0) * 1000),
            }
        )

        t1 = time.perf_counter()
        try:
            plan = self.planner.run(state)
        except Exception as exc:
            plan = {"weights": [0.2, 0.6, 0.2], "summary": f"fallback:{exc}"}
        state.update(plan)
        state["plan"] = plan
        db.write_node(
            {
                "node_name": "Planner",
                "input_summary": json.dumps(analyzer_out, ensure_ascii=False),
                "output_summary": json.dumps(plan, ensure_ascii=False),
                "goal_set_version": goal_set_version,
                "elapsed_ms": int((time.perf_counter() - t1) * 1000),
            }
        )

        t2 = time.perf_counter()
        try:
            impl = self.implementer.run(state)
        except Exception as exc:
            impl = {"scoring_code": scoring_code, "version": "v1", "summary": f"fallback:{exc}"}
        db.write_node(
            {
                "node_name": "Implementer",
                "input_summary": json.dumps(plan, ensure_ascii=False),
                "output_summary": f"scoring_version={impl.get('version', '')}",
                "goal_set_version": goal_set_version,
                "elapsed_ms": int((time.perf_counter() - t2) * 1000),
            }
        )

        def scorer(c: str):
            ok, result = run_scoring(impl["scoring_code"], c, {"keywords": keywords}, self.cfg.timeout_s)
            return result if ok else [0.0, 0.0, 0.0]

        t3 = time.perf_counter()
        scored = beam_search(state["candidates"], scorer, self.cfg.beam_width)
        db.write_node(
            {
                "node_name": "Optimizer",
                "input_summary": f"beam_width={self.cfg.beam_width}",
                "output_summary": f"candidates={len(scored)}",
                "goal_set_version": goal_set_version,
                "elapsed_ms": int((time.perf_counter() - t3) * 1000),
            }
        )
        best = scored[0][0] if scored else ""

        edges = [
            {"from": "Analyzer", "to": "Planner"},
            {"from": "Planner", "to": "Implementer"},
            {"from": "Implementer", "to": "Optimizer"},
        ]
        for e in edges:
            db.write_edge(e["from"], e["to"])

        for idx, (cand, score_vec) in enumerate(scored):
            db.write_candidate(
                f"cand_{idx}",
                cand,
                json.dumps(score_vec),
                json.dumps(plan.get("weights", [])),
            )

        write_graph(run_dir / "graph.json", db.fetch_nodes(), edges)
        write_mermaid(run_dir / "workflow.mmd", edges)

        return {"run_id": run_id, "best_candidate": best, "scored": scored}
