import React, { useMemo, useRef, useState } from "react";
import MermaidView from "./components/MermaidView.jsx";

const defaultWsUrl = (() => {
  if (typeof window === "undefined") return "ws://localhost:9200/ws/run";
  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  return `${proto}://${window.location.host}/ws/run`;
})();

export default function App() {
  const [wsUrl, setWsUrl] = useState(defaultWsUrl);
  const [text, setText] = useState("這是一段測試文字");
  const [keywords, setKeywords] = useState("測試");
  const [events, setEvents] = useState([]);
  const [runId, setRunId] = useState("");
  const [graphJson, setGraphJson] = useState("");
  const [mermaid, setMermaid] = useState("");
  const wsRef = useRef(null);

  const keywordList = useMemo(
    () =>
      keywords
        .split(",")
        .map((k) => k.trim())
        .filter(Boolean),
    [keywords],
  );

  const appendEvent = (evt) => {
    setEvents((prev) => [...prev, evt]);
  };

  const fetchArtifacts = async (rid) => {
    if (!rid) return;
    try {
      const g = await fetch(`/runs/${rid}/graph.json`);
      if (g.ok) setGraphJson(await g.text());
      const m = await fetch(`/runs/${rid}/workflow.mmd`);
      if (m.ok) setMermaid(await m.text());
    } catch (err) {
      appendEvent({ type: "ui_error", message: String(err) });
    }
  };

  const startRun = () => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setEvents([]);
    setGraphJson("");
    setMermaid("");
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;
    ws.onopen = () => {
      ws.send(
        JSON.stringify({
          type: "start_run",
          text,
          keywords: keywordList,
        }),
      );
    };
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        appendEvent(msg);
        if (msg.run_id) {
          setRunId(msg.run_id);
        }
        if (msg.type === "run_finished" && msg.run_id) {
          fetchArtifacts(msg.run_id);
        }
      } catch {
        appendEvent({ type: "raw", message: ev.data });
      }
    };
    ws.onclose = () => {
      appendEvent({ type: "ws_closed" });
    };
    ws.onerror = () => {
      appendEvent({ type: "ws_error" });
    };
  };

  return (
    <div className="page">
      <header className="hero">
        <div className="brand">SAGA MVP</div>
        <div className="subtitle">Observability channel + replay artifacts</div>
      </header>

      <section className="grid">
        <div className="panel">
          <h2>Run Controls</h2>
          <label>
            WebSocket URL
            <input value={wsUrl} onChange={(e) => setWsUrl(e.target.value)} />
          </label>
          <label>
            Text
            <textarea value={text} onChange={(e) => setText(e.target.value)} />
          </label>
          <label>
            Keywords (comma-separated)
            <input value={keywords} onChange={(e) => setKeywords(e.target.value)} />
          </label>
          <button className="primary" onClick={startRun}>
            Start Run
          </button>
          <div className="meta">Run ID: {runId || "-"}</div>
        </div>

        <div className="panel">
          <h2>Events</h2>
          <pre>{events.map((e) => JSON.stringify(e)).join("\n")}</pre>
        </div>

        <div className="panel">
          <h2>Graph JSON</h2>
          <pre>{graphJson || "(waiting)"}</pre>
        </div>

        <div className="panel">
          <h2>Mermaid</h2>
          <MermaidView code={mermaid} />
        </div>
      </section>
    </div>
  );
}
