from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List


def write_graph(path: Path, nodes: List[Dict[str, object]], edges: List[Dict[str, object]]) -> None:
    """Write graph JSON with nodes and edges."""
    payload = {"nodes": nodes, "edges": edges}
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_mermaid(path: Path, edges: List[Dict[str, object]]) -> None:
    """Write mermaid flow graph from edge list."""
    lines = ["graph TD"]
    for e in edges:
        lines.append(f'{e["from"]} --> {e["to"]}')
    Path(path).write_text("\n".join(lines), encoding="utf-8")
