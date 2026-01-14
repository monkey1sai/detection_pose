from saga.trace.sqlite import TraceDB


def test_trace_create_and_write(tmp_path):
    db = TraceDB(tmp_path / "trace.db")
    db.init()
    db.write_node({"node_name": "Analyzer", "elapsed_ms": 1})
    rows = db.fetch_nodes()
    assert rows[0]["node_name"] == "Analyzer"
