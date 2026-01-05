請提供可上線的部署包裝：
1) docker-compose.yml：包含 gateway +（可選）sglang + nginx
2) nginx config：支援 websocket upgrade、TLS（可先用自簽）、/healthz 導流
3) 環境變數範本 .env.example：port、engine、api key、limits
4) DEPLOY.md 補上：如何在單機/雲機器上啟動、如何滾動更新（最小版）

限制：
- 不改 WS API v1
- docker 化以「最少 moving parts」為優先
