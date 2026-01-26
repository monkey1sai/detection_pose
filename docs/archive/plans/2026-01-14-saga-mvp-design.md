# SAGA MVP 設計稿（本地端）

## 0. 目標與範圍

建立可運行的 SAGA MVP，核心為「outer loop 目標演化」與「inner loop 候選搜尋」的**嚴格解耦**。系統具備：
- 模組化的 Analyzer / Planner / Implementer / Optimizer
- 內循環搜尋器（Beam Search）
- Scoring plugin 一等公民（版本化、可測試、可沙盒）
- 可觀測 trace（SQLite）
- 可視化輸出（graph.json + workflow.mmd）
- 可回放（behavioral replay）
- 以 SGLang 進行節點調用（本機服務）
- UI 以 `web_client/`（Vite + React）實作

## 1. 設計原則：outer loop / inner loop 嚴格解耦

**核心原則**：系統必須嚴格區分「目標演化（outer loop）」與「候選搜尋（inner loop）」。  
任何元件與資料流設計皆以此解耦為最高優先。

- **Outer loop**：Analyzer / Planner / Implementer / Optimizer  
  負責診斷目標、調整策略、產出 scoring proxy。
- **Inner loop**：Beam Search  
  在固定 scoring 下搜尋候選，不涉及策略調整。

## 2. 架構與模組

### 2.1 核心框架
- `saga/`：核心框架
- `saga/modules/`：四大模組介面 + 預設實作
- `saga/search/beam.py`：內循環搜尋器
- `saga/scoring/`：scoring plugin 介面與實作
- `saga/trace/`：SQLite trace logger
- `saga/adapters/sglang_adapter.py`：SGLang 封裝

### 2.2 服務與 UI
- `saga_server/`：獨立服務，負責 workflow 協調與 observability
- `web_client/`：可視化 UI（取代原功能）

## 3. 資料流與 replay

### 3.1 Trace（SQLite）
每次 run 產生 `run_id`，所有事件寫入 `runs/<run_id>/trace.db`。
至少包含下列表：
- `run_meta`
- `nodes`
- `edges`
- `candidates`
- `errors`
- `artifacts`

### 3.2 Node 記錄內容
每個 node 記錄：
- `node_name`
- `input_summary`
- `output_summary`
- `start_at`, `end_at`, `elapsed_ms`
- `error`（nullable）
- `goal_set_version`

### 3.3 Candidates 記錄內容
每個候選記錄：
- `candidate_id`
- `text`
- `score_vector`（JSON array）
- `objective_weights`

### 3.4 Replay（behavioral replay）
本系統的 replay **只保證行為可重播（behavioral replay）**：  
可在不重跑 LLM 的情況下重建節點圖與候選摘要。  
**不保證 LLM 內部隨機性可逆**，因此 replay 用於診斷與回顧，而非 bit‑level 重現。

## 4. Observability Channel（WebSocket）

`saga_server/` 提供 WebSocket `/ws/run` **僅作 observability**：
- 前端可訂閱 `node_started`, `node_finished`, `candidate_scored`, `run_finished`
- UI 不介入決策流程
- 決策僅由 server 與 SAGA 模組驅動

## 5. 可視化輸出

每次 run 產出：
- `runs/<run_id>/graph.json`（nodes/edges）
- `runs/<run_id>/workflow.mmd`（mermaid）

UI 以 `graph.json` 繪製 DAG，並顯示 `workflow.mmd` 文字預覽。

## 6. Toy Domain（MVP）

**文字摘要/改寫**：
- Input：原文 + 目標關鍵字集合
- Candidate：候選摘要
- Objectives：
  - `len_score`：越短越高
  - `keyword_coverage`：關鍵字覆蓋率
  - `readability`：簡化規則（平均句長/標點比例）

Outer loop 流程：
1. Analyzer：偵測缺陷
2. Planner：調整權重或策略
3. Implementer：更新 scoring plugin 版本
4. Optimizer：Beam Search 搜尋候選

## 7. Failure Case 與限制

**若 scoring function 無法形式化為可計算 proxy**，  
outer loop 的目標演化可能停滯或震盪。  
此為 MVP 已知限制，未來需引入人類回饋或更強的 reward modeling。

## 8. 測試與配置

- pytest 覆蓋：
  - scoring plugin
  - beam search
  - trace logger
  - graph/mermaid 生成
  - replay 讀取
- Config 透過 CLI/YAML 提供（`--beam-width`, `--max-iters`, `--weights`, `--timeout`, `--sglang-url`）。
- 所有模組需有 docstring + 型別註解。

