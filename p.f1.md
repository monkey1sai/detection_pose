請在 WD Gateway TTS 增加產品部署必需的運維接口：
1) GET /healthz：回 200 + 基本狀態（engine、版本、啟動時間）
2) /metrics：Prometheus text format（至少）
   - active_connections
   - sessions_total
   - errors_total{code}
   - backpressure_total
   - ttfa_ms histogram 或 summary（若太重，先用 summary）

限制：
- 不更動 WebSocket API v1 協定與 message schema
- 不改 flush 行為與 max_pending_units 預設
- 只在 server 層加 endpoint 與 metrics 記錄點
- 請給最小 diff + 如何本機驗收 + 如何在 docker-compose 暴露
