from saga.trace.graph import write_graph, write_mermaid


def test_graph_files(tmp_path):
    write_graph(tmp_path / "graph.json", [{"id": "A"}], [{"from": "A", "to": "B"}])
    write_mermaid(tmp_path / "workflow.mmd", [{"from": "A", "to": "B"}])
    assert (tmp_path / "graph.json").exists()
    assert (tmp_path / "workflow.mmd").exists()
