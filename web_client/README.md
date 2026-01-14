# SAGA Web Client

## 開發模式

```powershell
cd web_client
npm install
npm run dev
```

預設 WebSocket：`ws://localhost:9100/ws/run`

## Mermaid 視覺化

Run 完成後會自動讀取 `/runs/<run_id>/workflow.mmd` 並用 mermaid 渲染 SVG。

## Build

```powershell
npm run build
```

Build 產物在 `web_client/dist/`。
