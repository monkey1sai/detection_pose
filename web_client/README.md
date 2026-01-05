# WD Gateway TTS — Web Client Reference（最小可用）

本資料夾提供一個「官方 reference」的純 HTML/JS Web client，用於：
- 設定 gateway URL / API key
- 一鍵 connect / disconnect
- 送出 `start`、`text_delta`、`text_end`、`cancel`
- 播放 `audio_chunk`（raw PCM16，依 `audio_format=pcm16_wav` 的 v1 定義）
- 顯示 debug：`session_id`、`chunk_seq`、`unit_index` 範圍、TTFA、errors

> 注意：Browser 原生 WebSocket **無法**自訂 `Authorization` header。此 reference 會把 API key 附加到 URL query：`?api_key=...`。若你的部署要求 `Authorization: Bearer ...`，請在 Nginx/Ingress 層把 query 轉成 header（或調整 Gateway 認證方式）。

---

## 1. 本機執行（最簡單）

### 1.1 啟動 Gateway（dummy）

在專案根目錄：

```powershell
cd sglang-server
$env:WS_TTS_ENGINE="dummy"
$env:WS_TTS_PORT="9000"
..\.venv\Scripts\python.exe -m ws_gateway_tts.server
```

### 1.2 啟動靜態網站

在專案根目錄：

```powershell
cd D:\._vscode2\detection_pose
cd .\web_client
..\.venv\Scripts\python.exe -m http.server 8000
```

打開瀏覽器：
- `http://localhost:8000/`

### 1.3 常見問題：瀏覽器顯示「Directory listing」

如果你看到的是 `.env`、`docker-compose.yml`、`nginx/` 之類的清單，代表你在錯的資料夾啟動了 `http.server`（通常是不小心在 `sglang-server/` 下面）。

- 先在命令列按 `Ctrl + C` 停掉 server
- 再確認目前資料夾並重新啟動：

```powershell
Get-Location
cd D:\._vscode2\detection_pose\web_client
..\.venv\Scripts\python.exe -m http.server 8000
```

> 補充：PowerShell 的 `;` 會「就算前面 `cd` 失敗也繼續跑下一個指令」，所以不建議用 `cd web_client; ...` 來寫成一行。

---

## 2. 操作方式

1. `Gateway URL`：例如 `ws://localhost:9000/tts`
2. `API Key`：可留空（會附加到 `?api_key=`）
3. `Connect + Start`：會建立 WS 並立即送 `start`
4. 在「輸入文字」貼上內容後按 `Send text_delta`
   - `逐段`：一次送整段（單一 `text_delta`）
   - `逐字`：每字一個 `text_delta`（用於逐字互動/除錯）
5. 按 `Send text_end`：讓 server flush pending units，最後送 `tts_end` 並關閉連線
6. `Send cancel`：中止並收到 `tts_end.cancelled=true`

---

## 3. 連到 Docker 部署

若你已把 Gateway 暴露為：
- `wss://<host>/tts`（Nginx WS upgrade）

則在頁面上設定：
- `Gateway URL`：`wss://<host>/tts`
- `API Key`：依部署需求填入

若部署使用 Nginx，請確認 WS upgrade 已開啟（參考 `docs/DEPLOY.md` 的 Nginx 範例）。
