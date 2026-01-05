請把我們剛凍結的 WS API v1、責任邊界、部署形態，整理成對外文件：
- docs/API.md：WebSocket message schema、state machine、error codes、flush 規則（不保證逐字）
- docs/DEPLOY.md：docker-compose / env vars / ports / nginx ws upgrade 範例
- docs/OPERATE.md：如何壓測（baseline/mixed）、如何判讀指標、常見故障排查

限制：
- 只允許新增/更新文件，不修改任何 .py
- 文件以「可直接給前端/維運/客戶」為目標，中文撰寫
- 請附一個最小驗收 checklist
