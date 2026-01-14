import React, { useEffect, useRef } from "react";
import mermaid from "mermaid";

export default function MermaidView({ code }) {
  const ref = useRef(null);

  useEffect(() => {
    mermaid.initialize({ startOnLoad: false, theme: "dark" });
    if (!code) {
      if (ref.current) ref.current.innerHTML = "";
      return;
    }
    const id = `mermaid-${Date.now()}`;
    mermaid
      .render(id, code)
      .then(({ svg }) => {
        if (ref.current) ref.current.innerHTML = svg;
      })
      .catch((err) => {
        if (ref.current) ref.current.textContent = `Mermaid render error: ${String(err)}`;
      });
  }, [code]);

  return <div ref={ref} className="mermaid-view" />;
}
