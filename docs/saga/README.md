# SAGA 知識庫（Disambiguation + Repo Mapping）

本資料夾的目標是：當有人提到「SAGA」時，先判斷是在指哪一種 **SAGA**（四個領域），再進入對應文件。

> 注意：本知識庫目前屬「LLM 生成 + 自我批判修正」的內部文件；尚未有外部權威文獻來源導入時，請將文中結論視為**可操作的工作假設**，並優先以 repo 內原始碼/既有設計稿作為驗證依據。

---

## 0) 你現在講的「SAGA」是哪一種？

### A. Saga 設計模式（分散式事務 / 最終一致性）
**關鍵字訊號**
- 微服務、分散式事務、2PC、ACID、最終一致性、補償事務（Compensating Transaction）
- Orchestration / Choreography、Kafka/RabbitMQ、Temporal/Camunda/Dapr Workflow

➡️ 請看：`docs/saga/02-saga-design-pattern.md`

### B. SAGA 智能體（Scientific Autonomous Goal‑evolving Agent / 科學發現）
**關鍵字訊號**
- outer loop / inner loop、目標演化、Analyzer/Planner/Implementer/Optimizer
- scoring proxy、Beam Search、trace/replay、符號回歸、候選生成、約束/權重動態調整

➡️ 請看：`docs/saga/01-agentic-saga.md`

### C. SAGA 安全架構（治理 Agentic Systems）
**關鍵字訊號**
- Provider/Registry、一次性密鑰（OTK）、Access Control Token、Contact Policy
- 使用者對 agent lifecycle 的完全控制、跨 agent 通訊政策

➡️ 請看：`docs/saga/03-saga-security-architecture.md`

### D. SAGA 服務優化（Service Affinity Graph-based Approach / 雲端部署）
**關鍵字訊號**
- Service Affinity、圖論分群（clustering）、延遲/成本/隱私、微服務部署最佳化

➡️ 請看：`docs/saga/04-service-affinity-graph.md`

---

## 回應原則（使用本知識庫時）

1. 當被問及「SAGA」但未指定領域：請先用本頁的 A/B/C/D 做**簡要概述**，再詢問對方關注哪個方向。
2. 引用請以文件內的 Sources 編號為準（例如 `[1]`、`[2]`），避免把無來源內容寫成既定事實。
3. 若涉及 AI 代理：請區分「科學發現/雙層循環的 SAGA 智能體」與「治理型 SAGA 安全架構」。

---

## 1) 本 repo 的「SAGA」指的是哪一種？

就目前 repo 的程式結構與文件設計，本 repo 的 **SAGA** 主要指 **B：SAGA 智能體（outer/inner loop 的目標演化 + 候選搜尋）**，並提供：
- `saga/`：核心框架（Runner / OuterLoop / Modules / Search / Scoring / Trace）
- `saga_server/`：WebSocket Observability + 控制（pause/stop 等）
- `web_client/`：前端 UI（走同網域反代）

而 repo 裡也出現：
- `orchestrator/`：Web client ↔ SGLang ↔ ws_gateway_tts 的串流協調器（注意：這裡的 orchestrator **不是**「Saga 設計模式」的分散式事務協調器）。

---

## 2) 文件索引

- `docs/saga/01-agentic-saga.md`：本 repo SAGA（outer/inner loop）架構、資料流、模組責任分工、常見失敗模式與 guardrails
- `docs/saga/02-saga-design-pattern.md`：微服務分散式事務的 Saga pattern（用於名詞消歧，避免混用）
- `docs/saga/03-saga-security-architecture.md`：治理 Agentic Systems 的 SAGA 安全架構（用於名詞消歧）
- `docs/saga/04-service-affinity-graph.md`：雲端微服務部署優化的 SAGA（用於名詞消歧）
- `docs/saga/05-generation-self-critique.md`：LLM 生成知識庫的「自我批判修正」流程與提示詞

---

## 3) Sources（本知識庫目前可引用的內部來源）

- [1] 使用者提供的四域 SAGA 定義與回應原則（對話提示詞，2026-01-23）
- [2] `docs/plans/2026-01-14-saga-mvp-design.md`
- [3] `saga/SYSTEM_PROMPT.md`
- [4] `saga/QUICK_REFERENCE.md`
- [5] `saga/runner.py`、`saga/outer_loop.py`、`saga/search/beam.py`、`saga/scoring/sandbox.py`
