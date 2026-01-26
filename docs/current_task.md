# 🚧 Current Task: SAGA 符號回歸調優與修復

**Last Updated**: 2026-01-26  
**Worker**: Antigravity Agent (Brainstorming Session)

## 🎯 Objective
讓 SAGA 在使用本地 **Qwen 2.5 7B (Q4_K_M)** 模型時，能正確找到符號回歸問題的解 `y = x^2 + 3x - 2`。

## ⚠️ Known Issues (Resolved)
1. **LLM 調用失敗 (Timeout)**：
   - 症狀：UI 日誌顯示 `SGLang API call failed: timed out`。
   - 原因：Adapter 寫死 60s timeout，無法處理複雜生成。
   - 解決：新增 `SGLANG_TIMEOUT` 環境變數（預設 300s），並修復 `saga_cli.py` 載入 `.env` 問題。

2. **API 認證錯誤 (401)**：
   - 症狀：`saga_cli.py` 執行 benchmark 顯示 401 Unauthorized。
   - 原因：CLI 腳本未載入 `.env`，導致 `SGLANG_API_KEY` 遺失。
   - 解決：引入 `python-dotenv` 並在腳本開頭載入。

3. **搜索策略失效**：
   - 症狀：SAGA 提早收斂於錯誤公式。
   - 原因：初始種子太少，迭代次數不足。
   - 解決：擴增初始種子，開啟激進搜索模式。

## 📋 Execution Plan & Progress
- [x] **Infrastructure Fixes**:
    - [x] Increase SGLang timeout (300s) & make configurable.
    - [x] Restore `saga_cli.py` and fix environment loading.
    - [x] Add benchmark script `scripts/benchmark_sglang.py`.
- [x] **Search Strategy Tuning**:
    - [x] Increase `inner_iterations` (15) & `batch_size` (20).
    - [x] Expand initial seed candidates.
- [x] **LLM Logging**:
    - [x] Add `get_last_interaction()` to `LLMGenerator`.
    - [x] Emit `llm` type `LogEvent`.
- [x] **Visualization**:
    - [x] Implement graph generation in `OuterLoop`.

## 🧠 Context & Thoughts
- SGLang 服務已穩定（Latency ~3s for complex prompt），且 CLI 可正常執行。
- 專案現在可以透過 `uv run saga_cli.py run` 進行端到端優化測試。

## 📝 Handoff Note
- **Next Steps**:
    1. 觀察 LLM 生成的公式是否優於寫死的種子。
    2. 考慮將「最優解簡化」步驟加入流程（SymPy）。
