# WD 即時語音 AI Gateway — WebSocket API（v1）

本文件定義 Browser Client ↔ WD Gateway TTS 的 **對外凍結 API v1**，可直接提供給前端、客戶與合作夥伴。

> 目標：
> - Browser 端可直接實作
> - 行為可預期、錯誤可處理
> - 不保證逐字音訊（以 chunk/flush 為單位）

---

## 1. Endpoint

- WebSocket：`ws(s)://<host>:9000/tts`
- 健康檢查（HTTP）：`http://<host>:9000/healthz`

---

## 2. 相容性原則（v1）

- `type` 欄位為必填字串。
- Client **必須忽略**未知欄位（forward compatible）。
- Server 可能在訊息中新增欄位，但不會移除既有欄位或改變既有欄位語意（v1 範圍內）。

---

## 3. 狀態機（State Machine）

單一 WebSocket 連線對應單一 session 流程：

1. `WAIT_START`：連線建立後等待 `start`
2. `STREAMING`：接收 `text_delta`、回傳 `audio_chunk`
3. `FLUSHING`：收到 `text_end` 後，flush pending units，直到送出 `tts_end`
4. `ENDED`：送出 `tts_end` 或 `error` 後，server 會關閉連線

非法狀態行為：server 會送 `error` 並關閉連線。

---

## 4. Client → Server 訊息

### 4.1 `start`（必須第一個送）

```json
{
  "type": "start",
  "session_id": "uuid",
  "audio_format": "pcm16_wav",
  "sample_rate": 16000,
  "channels": 1
}
```

- `session_id`：必填字串（建議 UUIDv4）
- `audio_format`：必填字串（建議 `pcm16_wav`）
- `sample_rate`：必填整數（例如 `16000`）
- `channels`：必填整數（`1` 或 `2`）

### 4.2 `text_delta`（逐字/逐段輸入）

```json
{
  "type": "text_delta",
  "session_id": "uuid",
  "seq": 12,
  "text": "今"
}
```

- `seq`：必填整數，client 自行遞增（用於錯誤回報與除錯）
- `text`：必填非空字串（可逐字、也可一次送多字）

### 4.3 `text_end`（本輪輸入結束）

```json
{
  "type": "text_end",
  "session_id": "uuid",
  "seq": 99
}
```

### 4.4 `cancel`（中止本次 TTS）

```json
{
  "type": "cancel",
  "session_id": "uuid",
  "seq": 100
}
```

### 4.5 `resume`（斷線重連續傳）

```json
{
  "type": "resume",
  "session_id": "uuid",
  "last_unit_index_received": 123
}
```

- `last_unit_index_received`：client 已接收的最後 unit index（用於 server 重新推送快取窗內的 `audio_chunk`）

---

## 5. Server → Client 訊息

### 5.1 `start_ack`（接受 start 並回傳音訊規格）

```json
{
  "type": "start_ack",
  "session_id": "uuid",
  "audio_format": "pcm16_wav",
  "sample_rate": 16000,
  "channels": 1,
  "ttl_s": 120.0,
  "wav_header_base64": "..."
}
```

- `wav_header_base64`：僅在 `audio_format=pcm16_wav` 時提供，方便 client 組 WAV 檔/播放器初始化
- 注意：後續 `audio_chunk.audio_base64` 仍是 **raw PCM16**（不是含 header 的 WAV）

### 5.2 `audio_chunk`（串流音訊片段）

```json
{
  "type": "audio_chunk",
  "session_id": "uuid",
  "seq": 12,
  "chunk_seq": 3,
  "unit_index_start": 24,
  "unit_index_end": 47,
  "units_text": "今天天氣不錯，",
  "audio_format": "pcm16_wav",
  "sample_rate": 16000,
  "channels": 1,
  "audio_base64": "..."
}
```

- `chunk_seq`：server 端 chunk 連號（單一 session 內遞增）
- `unit_index_start/end`：此音訊 chunk 對應的輸入 unit 索引區間（用於除錯/續傳）
- `units_text`：此 chunk 對應的文字片段（用於除錯/比對）

### 5.3 `tts_end`（自然結束）

```json
{
  "type": "tts_end",
  "session_id": "uuid",
  "seq": 99,
  "cancelled": false
}
```

server 送出 `tts_end` 後會主動 close WebSocket。

### 5.4 `error`（錯誤）

```json
{
  "type": "error",
  "session_id": "uuid",
  "seq": 12,
  "code": "backpressure",
  "message": "client 讀取過慢，已觸發背壓保護"
}
```

server 送出 `error` 後會主動 close WebSocket。

---

## 6. Error Codes（v1 凍結）

| code | 說明 | 建議 client 行為 |
|---|---|---|
| `bad_request` | 協定/欄位錯誤、狀態錯誤 | 修正後重連 |
| `backpressure` | client 接收/播放過慢，觸發背壓保護 | 降低輸入速率、縮短播放緩衝或提示使用者後重試 |
| `resume_not_available` | 快取窗外或無可續傳內容 | 重新開始新的 session |
| `internal_error` | server 未預期錯誤 | 稍後重試、回報 log |

---

## 7. Flush 規則（不保證逐字）

Gateway 會先累積文字，再以 chunk/flush 的粒度產生 `audio_chunk`：

- 符合下列任一條件會 flush：
  - 累積 unit 數達到上限（預設 24）
  - 遇到標點：`，。！？；：,.!?;\n`
  - 收到 `text_end`（會 flush 剩餘 pending units）

因此 client **不應假設**每個 `text_delta` 都會立即對應一個 `audio_chunk`。

