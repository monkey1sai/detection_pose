# SAGA 安全架構（Security Architecture for Governing Agentic Systems）—名詞消歧用

本頁的 **SAGA** 指的是「治理 agentic systems 的安全架構」這個領域用語，而非本 repo 的「SAGA 智能體」框架。[1]

---

## 1) 一句話定義

SAGA（此處）是一種用於管理 AI 代理系統的安全架構，核心目標是讓使用者對 agent 的生命週期、互動與跨 agent 通訊擁有可驗證、可撤銷、可政策化的控制。[1]

---

## 2) 核心元件（概念層）

- **Provider / Registry**：維護使用者與代理的註冊表（身份、能力、連線資訊）。
- **存取控制**：用一次性密鑰（OTK）與存取控制權杖（Access Control Token）管理代理間通訊。
- **政策執行（Contact Policy）**：使用者可定義哪些 agent 可以主動聯繫、哪些只能被動回應、哪些完全禁止。[1]

---

## 3) 與本 repo 的關係（目前狀態）

本 repo 目前有 API key（例如 `SGLANG_API_KEY`）與服務分層（例如前端不直接持有 SGLang key，而是經由後端），這可視為「安全邊界」的雛形；  
但它不等同於上述 SAGA 安全架構（OTK/Registry/Contact Policy 等）的一整套治理模型。[1]

---

## 4) 若未來要把「治理型 SAGA」導入本 repo，通常會需要新增

- agent identity / capability registry（可稽核）
- per‑agent / per‑tool 的細粒度 token 與短期憑證（OTK/ACT）
- 明確的 contact policy（誰可主動對誰發起互動）
- 事件審計（audit log）與策略評估點（policy enforcement points）[1]

---

## Sources

- [1] 使用者提供的四域 SAGA 定義與回應原則（對話提示詞，2026-01-23）

