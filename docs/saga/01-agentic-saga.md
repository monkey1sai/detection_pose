# SAGA 智能體（Scientific Autonomous Goal‑evolving Agent）—本 repo 實作視角

本頁描述的 **SAGA** 指的是「outer loop 目標演化 + inner loop 候選搜尋」的智能體架構（本 repo 主要採用的定義）。[1][2][3][4][5]

---

## 1) 一句話定義

SAGA（此處）是一個**多輪迭代的目標演化系統**：外循環（Outer Loop）負責「反思/調整目標與約束」，內循環（Inner Loop）在固定目標代理（scoring proxy）下「搜尋並評分候選」，並透過觀測與（可選）人審降低 reward hacking / false optimum 風險。[1][2][3][4]

---

## 2) 架構：Outer Loop vs Inner Loop（嚴格解耦）

### Outer Loop（目標演化）
責任：診斷目前候選的缺陷 → 調整策略/權重/約束 → 產生/更新 scoring proxy → 驅動下一輪 inner loop。  
本 repo 的典型序列：
1. Analyzer（分析）  
2. Planner（規劃）  
3. Implementer（實作 scoring code）  
4. Optimizer（呼叫 inner loop）  
5. Termination（判斷是否停止）[2][3][4][5]

### Inner Loop（候選搜尋）
責任：在「固定 scoring proxy」下，搜尋/生成/篩選候選（例如 Beam Search / Evo/LLM 生成 + 排序）。  
原則：inner loop **不做策略調整**，只做「搜尋」。[2][5]

> 你提到的「SAGA 內循環和外循環是有上下文學習的進而自我優化」：在本 repo 的落點通常是  
> - Outer loop：把「歷史表現」變成新的約束/權重（等同對目標函數做 in-context 的自我修正）  
> - Inner loop：把 keywords / 先前候選 / 分析回饋作為生成器的上下文（提升候選質量/多樣性）[1][4][5]

---

## 3) 本 repo 元件與責任分工（Mapping）

### 入口與主控
- `saga/runner.py`：`SagaRunner` 組裝所有元件並啟動 `OuterLoop.run()`，同時建立 `runs/<run_id>/trace.db`（TraceDB）。[5]
- `saga/outer_loop.py`：`OuterLoop` 維護 `LoopState`，並以事件串流形式產出 `IterationResult` / `FinalReport` / `HumanReviewRequest` / `LogEvent`。[5]

### 四大模組（Outer Loop 核心）
- Analyzer：產出 `AnalysisReport`（分數分佈、達成率、pareto、趨勢、瓶頸、建議約束）。[4][5]
- Planner：根據分析調整 `weights` 與新增 `constraints`（探索/開發/平衡策略）。[4][5]
- Implementer：把 plan/constraints 具體化為 scoring code（可視為「目標函數代理」）。[4][5]
- Optimizer：把 scoring code 套進 inner loop，對候選做搜尋/評分/排序，回傳 top‑k。 [4][5]

### Mode / 人審控制
- `saga/mode_controller.py`：控制不同操作模式（co‑pilot / semi‑pilot / autopilot）在 analyze/plan/implement 等階段是否需要人類審核。這是「自我優化」的重要安全閥。 [4][5]

### Observability + UI
- `saga_server/app.py`：WebSocket `/ws/run` 只是 observability 與控制層（UI 不介入決策），並提供 `/healthz` 與 `/runs` 靜態檔案（run artifacts）。[2]
- `web_client/`：Vite + React UI，展示 run 狀態、日誌、控制等。[2]

---

## 4) 關鍵資料結構（你在 debug/擴充時最常碰到）

- `LoopState`：跨迭代的狀態快照（candidates/scores/constraints/weights/score_history…）。[4][5]
- `AnalysisReport`：分析產物（瓶頸、趨勢、Pareto 等），通常是 Planner 的主要輸入。 [4][5]
- `IterationResult`：單輪結果（best_candidate/best_score/analysis_report）。[4][5]
- `FinalReport`：終止後總結（原因、演化曲線、最佳候選）。[5]

---

## 5) 內建 guardrails（避免 reward hacking / false optimum）

### False optimum：把「資料本身」當候選
在某些任務（例如符號回歸）中，若把原始資料/題目文本直接放進 candidates，scorer 可能會「拿資料比資料」造成假性滿分。  
本 repo 在 seeding 初始 candidates 時已特別避免這類情況（見 `SagaRunner` 的註解）。[5]

### Scoring proxy 的安全性
若 scoring code 由 LLM 產生，務必：
- 做 schema/解析/驗證（避免格式漂移）
- 在 sandbox/timeout 下執行（避免無限迴圈/危險操作）：本 repo 的 scoring sandbox 以**獨立 process**執行，並限制 `__builtins__`（無 `open` / 無 `__import__`），以降低 I/O 與 import 風險
- 把「不可違反約束」做成硬規則（不是只寫在 prompt）[2][4][5]

### Inner loop 的排序語義（避免誤解）
本 repo 的 inner loop「選擇器（Selector）」預設採 `ParetoSelector`：對每個候選先取得 score vector，然後以「加總」或「加權加總（weights 維度一致時）」排序取 top‑k；若 weights 維度不一致則退回純加總。另有 `BeamSelector` 會包裝 `beam_search()`，但目前不是預設路徑。[5]

---

## 6) 自我優化（學習）在這裡到底是什麼？

就本 repo 的語境，「學習」通常不是指參數微調，而是：
- **外循環**：用上一輪的分析與歷史軌跡，更新「目標權重/閾值/約束」→ 改變下一輪的搜索壓力方向。  
- **內循環**：用 keywords、候選摘要、瓶頸回饋當作生成器的上下文 → 產生更符合目標的候選。  
這是一種「in-context 的自我修正」，而不是模型權重更新。[1][4][5]

---

## 7) 自我批判修正：建議的文件/知識生成方式

請參考：`docs/saga/05-generation-self-critique.md`（把「生成 → 自我批判 → 修正」變成可重複流程）。[1]

---

## Sources

- [1] 使用者提供的四域 SAGA 定義與回應原則（對話提示詞，2026-01-23）
- [2] `docs/plans/2026-01-14-saga-mvp-design.md`
- [3] `saga/SYSTEM_PROMPT.md`
- [4] `saga/QUICK_REFERENCE.md`
- [5] `saga/runner.py`、`saga/outer_loop.py`、`saga/mode_controller.py`
