請把 WD Gateway TTS 加入最小可商業化的安全與限流：
1) Authorization: Bearer <API_KEY>（先用 env: GATEWAY_API_KEY）
2) per-key 限制：
   - max_conns_per_key（預設 10，可 env 配）
   - max_text_deltas_per_sec_per_key（預設例如 50，可 env 配）

限制：
- 不改 WS API v1 message schema
- 超過限制時：回 error(code=rate_limit 或 backpressure) 並關閉連線（按文件定義）
- 請補 docs/SECURITY.md：如何發 key、如何 rotation、如何在 nginx 傳遞 header
- 請提供 3 個驗收指令（curl/簡單腳本）來證明有效
