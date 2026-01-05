請做一個官方 Web Client reference（最小可用，不追求 UI）：
- 可設定 gateway URL、api key
- 一鍵 connect/disconnect
- 一個文字輸入框（逐字/逐段送 text_delta）
- 播放 audio_chunk（處理 wav_header_base64 或直接播放 wav）
- 顯示 debug：session_id、chunk_seq、unit_index 範圍、TTFA、errors

限制：
- 不需要框架也可以（純 HTML/JS 最佳）
- 必須完全遵守 WS API v1（不要自創協定）
- 請附 README：如何本機跑、如何連到 docker 部署
