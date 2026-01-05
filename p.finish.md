我要完成「Web client → LLM（SGLang）→ streaming 每個 delta 立即送到 WS Gateway TTS 產音 → web client 播放」的端到端產品流程。

你必須嚴格遵守 repo 既有的 ws_gateway_tts 協定與欄位，不可自創 schema。

========================
現況（你需要讀 repo 內實作再動手）
========================
1) ws_gateway_tts 的 WebSocket 端點是 GET /tts（aiohttp），訊息格式在 protocol.py / server.py
- Client -> Server:
  - start: { "type":"start", "session_id":str, "audio_format":str, "sample_rate":int, "channels":int }
  - text_delta: { "type":"text_delta", "session_id":str, "seq":int, "text":str }
  - text_end: { "type":"text_end", "session_id":str, "seq":int }
  - cancel: { "type":"cancel", "session_id":str, "seq":int }
  - resume: { "type":"resume", "session_id":str, "last_unit_index_received":int }
- Server -> Client:
  - start_ack: { "type":"start_ack", "session_id", "audio_format", "sample_rate", "channels", "ttl_s", "wav_header_base64"?(only if audio_format=="pcm16_wav") }
  - audio_chunk: { "type":"audio_chunk", "session_id", "seq", "chunk_seq", "unit_index_start", "unit_index_end", "units_text", "audio_format", "sample_rate", "channels", "audio_base64" }
  - tts_end: { "type":"tts_end", "session_id", "seq", "cancelled":bool }
  - error: { "type":"error", "session_id", "seq", "code", "message" }
2) ws_gateway_tts 的 flush 規則在 session.py：
- 累積到 max_pending_units（預設 24）或遇到標點 PUNCTUATION（"，。！？；：,.!?;\n"）才會 synthesize 產生 audio_chunk
- 收到 text_end 會 flush 最後一段，然後送 tts_end
3) benchmark_final.py 已示範如何呼叫 SGLang /v1/chat/completions 並 stream=True 解析 data: 行，取得 delta.content 與可能的 delta.tool_calls（function arguments）。

========================
目標（產品行為）
========================
A) Web client 送「使用者問題」給一個新服務（Orchestrator / Bridge），這個服務持有 SGLang API Key（前端不能拿 key）
B) Orchestrator 以 streaming 呼叫 SGLang：
- 每收到一個 delta.content（文字增量）就：
  1) 立刻把 delta.content 串流回傳給 web client（顯示文字）
  2) 同時把 delta.content 送到 ws_gateway_tts 的 WS（以 text_delta）讓它產音
C) web client 一邊顯示 LLM streaming 文本，一邊播放 ws_gateway_tts 回來的 audio_chunk（audio_base64 + start_ack 的 wav_header_base64）
D) tool_calls：
- Orchestrator 需要能「累積」delta.tool_calls 的 function.arguments（照 benchmark_final.py 的方式）
- 但是：不要把 tool_calls 內容做 TTS（只對 delta.content 做 TTS）
- tool_calls 的執行（真的去呼叫工具）這版先不做；只要正確解析並在 debug log 顯示即可

========================
你要實作的內容（可交付 + 可驗收）
========================
1) 新增 Orchestrator（建議 Python aiohttp 或 FastAPI；需支援串流回傳）
- 提供端點：
  - POST /chat（SSE 回傳）或 GET/WS /chat（WebSocket 回傳），擇一你最穩的方式
- 輸入：{ "prompt": "...", "session_id": "uuid", "audio_format":"pcm16_wav", "sample_rate":16000, "channels":1 }
- Orchestrator 內部做兩條連線：
  (a) 到 SGLang：streaming chat completions（沿用 benchmark_final.py 的解析法）
  (b) 到 ws_gateway_tts：WebSocket 連線 /tts，先送 start，再送 text_delta/text_end
- Orchestrator 必須維持 seq（int）單調遞增，並帶入每次 text_delta/text_end 的 seq 欄位（ws_gateway_tts 會用 state.seq）
- delta -> TTS 的送法（為了降低 flush 長尾與避免每字一包造成 WS 壓力）：
  - 實作一個可調的 buffering：
    - TTS_FLUSH_MIN_CHARS（預設 12）
    - TTS_FLUSH_ON_PUNCT（預設 True；遇到 "，。！？；：,.!?;\n" 立刻 flush）
  - Orchestrator 收到 delta.content 後先進 buffer，達到條件就用單次 text_delta 送出 buffer 並清空
  - LLM 結束後：若 buffer 還有字，先送最後一個 text_delta，再送 text_end
2) 更新 web client（你目前的 index.html）
- 不要再直接把文字送去 /tts 當作 TTS input
- 改成：
  - 呼叫 Orchestrator 的 /chat，取得 LLM streaming 文本（顯示在畫面）
  - 同時仍然由 Orchestrator 去驅動 ws_gateway_tts 產音（web client 仍然需要接收/播放 audio_chunk 的話，你可以有兩種方案，二選一）：

方案 1（最簡單、推薦）：
- web client 只連 Orchestrator 一條串流（/chat），Orchestrator 直接把 audio_chunk 也轉送給 web client（同一條 SSE/WS 通道帶兩種事件：llm_delta 與 audio_chunk）
- 這樣 web client 不需要自己再開一條到 /tts 的 WS，也不需要處理 Authorization header 限制

方案 2（保留現狀但較麻煩）：
- web client 維持直接連 /tts 播音，但「文字輸入」改走 Orchestrator
- 這會需要 web client 與 Orchestrator 同步 session_id/seq，較容易出錯（除非你做嚴格協調）

=> 請優先做方案 1，確保能穩定商業化（前端只連一條、key 不外洩）。

3) README / 操作方式
- 如何啟動：
  - ws_gateway_tts（WS_TTS_ENGINE=dummy 即可）
  - sglang server（沿用你既有設定）
  - orchestrator（環境變數：SGLANG_BASE_URL、SGLANG_API_KEY、WS_TTS_URL）
- 如何手動驗收：
  - 打開 web client
  - 輸入一句問題（例如「用三點告訴我如何壓測 WebSocket 服務」）
  - 看到文字逐段出現（streaming），同時持續播放語音
  - 最後正常結束（收到 tts_end / 連線關閉）

========================
限制（非常重要）
========================
- 不可改動 ws_gateway_tts 的 message schema 欄位名稱（type/session_id/seq/audio_base64/wav_header_base64…）
- 不可改動 ws_gateway_tts 的 flush 規則（max_pending_units=24 與 punctuation 判定仍維持）
- 你可以新增檔案（orchestrator/ 目錄、web_client/ 更新）
- 專案以「可商業部署」為導向：前端不持有任何 SGLang key；Orchestrator 負責安全邊界

請先：
1) 讀 protocol.py、server.py、session.py、benchmark_final.py
2) 提出你要新增的檔案清單與最小改動點
3) 再開始產出程式碼與 README
