from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict, List


class TraceDB:
    """SQLite-backed trace store."""
    def __init__(self, path: Path):
        self.path = Path(path)

    def init(self) -> None:
        """Initialize schema for trace tables."""
        conn = sqlite3.connect(self.path)
        cur = conn.cursor()
        cur.execute(
            "create table if not exists nodes (node_name text, input_summary text, output_summary text, "
            "error text, goal_set_version text, elapsed_ms integer)"
        )
        cur.execute("create table if not exists edges (source text, target text)")
        cur.execute(
            "create table if not exists candidates (candidate_id text, text text, score_vector text, objective_weights text)"
        )
        conn.commit()
        conn.close()

    def write_node(self, row: Dict[str, object]) -> None:
        """Insert a node record."""
        conn = sqlite3.connect(self.path)
        cur = conn.cursor()
        cur.execute(
            "insert into nodes (node_name, input_summary, output_summary, error, goal_set_version, elapsed_ms) "
            "values (?, ?, ?, ?, ?, ?)",
            (
                row["node_name"],
                row.get("input_summary", ""),
                row.get("output_summary", ""),
                row.get("error", ""),
                row.get("goal_set_version", ""),
                row.get("elapsed_ms", 0),
            ),
        )
        conn.commit()
        conn.close()

    def fetch_nodes(self) -> List[Dict[str, object]]:
        """Fetch all node records."""
        conn = sqlite3.connect(self.path)
        cur = conn.cursor()
        cur.execute("select node_name, elapsed_ms from nodes")
        rows = [{"id": r[0], "node_name": r[0], "elapsed_ms": r[1]} for r in cur.fetchall()]
        conn.close()
        return rows

    def write_edge(self, source: str, target: str) -> None:
        """Insert an edge record."""
        conn = sqlite3.connect(self.path)
        cur = conn.cursor()
        cur.execute("insert into edges (source, target) values (?, ?)", (source, target))
        conn.commit()
        conn.close()

    def fetch_edges(self) -> List[Dict[str, object]]:
        """Fetch all edge records."""
        conn = sqlite3.connect(self.path)
        cur = conn.cursor()
        cur.execute("select source, target from edges")
        rows = [{"from": r[0], "to": r[1]} for r in cur.fetchall()]
        conn.close()
        return rows

    def write_candidate(self, candidate_id: str, text: str, score_vector: str, objective_weights: str) -> None:
        """Insert a candidate record."""
        conn = sqlite3.connect(self.path)
        cur = conn.cursor()
        cur.execute(
            "insert into candidates (candidate_id, text, score_vector, objective_weights) values (?, ?, ?, ?)",
            (candidate_id, text, score_vector, objective_weights),
        )
        conn.commit()
        conn.close()
