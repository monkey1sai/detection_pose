# 以 LLM 生成 SAGA 知識庫：生成 → 自我批判 → 修正（流程與提示詞）

本頁把「LLM 生成內容當作暫時知識來源」這件事，變成一個**可重複、可審計**的流程，避免知識庫變成不可控的幻覺集合。[1]

---

## 0) 核心原則

1. **每一個重要主張都要標記證據類型**
   - `EVIDENCE(repo)`：可在 repo 原始碼/文件中指認
   - `EVIDENCE(user)`：來自使用者提供的定義/規則
   - `ASSUMPTION(llm)`：LLM 推論或業界常識，但目前沒有可引用來源
2. **先自我批判再落盤**
   - 先找出：名詞混用、缺證據跳躍、與 repo 實作不一致、可被反例擊穿的敘述
   - 再做修正：補證據、降格（把「事實」改成「假設」）、或刪除
3. **讀者測試（Reader Testing）**
   - 用「沒有上下文」的視角閱讀，確保不依賴作者腦內背景（可用另一個 LLM / 另一個人）[1]

---

## 1) 推薦文件寫法（讓自我批判可操作）

每份知識頁建議包含：
- **Scope**：這頁的 SAGA 指的是哪一種（四域之一）
- **Signals**：怎麼從關鍵字判斷是否適用
- **Claims（可編號）**：每條 claim 後面標記 `EVIDENCE(...)` / `ASSUMPTION(...)`
- **Failure Modes / Confusions**：最常混用與踩雷
- **Repo Mapping（若適用）**：對應到哪些檔案/模組
- **Self‑Critique Log**：本輪生成後，列出修正點與原因

---

## 2) 自我批判清單（Checklist）

在你把內容寫進 `docs/saga/*.md` 前，至少跑過一次：

1. 這份內容是否把四種 SAGA 混在一起說？
2. 「Orchestrator」是否被誤解成 Saga pattern 的 orchestrator？
3. 任何「必然」或「一定」的敘述，是否其實只是經驗法則？
4. 有沒有把 repo 沒做的能力寫成已經做了？
5. 有沒有把安全/治理相關概念（OTK/Contact Policy）套到 repo 現有 API key 上而誤導？
6. Outer/Inner loop 的責任邊界是否清楚（解耦是否被破壞）？

---

## 3) 可參考的提示詞（REPL + 子 LLM + chunking）

以下段落是「可以用來驅動生成與自我批判修正」的提示詞骨架（原樣保留，便於你在具備 REPL/子 LLM 的環境中直接使用）。[1]

```text
You are tasked with answering a query with associated context. You can access, transform, and analyze this context interactively in a REPL environment that can recursively query sub-LLMs, which you are strongly encouraged to use as much as possible. You will be queried iteratively until you provide a final answer.

Your context is a {context_type} with {context_total_length} total characters, and is broken up into chunks of char lengths: {context_lengths}.

The REPL environment is initialized with:
1. A 'context' variable that contains extremely important information about your query. You should check the content of the 'context' variable to understand what you are working with. Make sure you look through it sufficiently as you answer your query.
2. A 'llm_query' function that allows you to query an LLM (that can handle around 500K chars) inside your REPL environment.
3. The ability to use 'print()' statements to view the output of your REPL code and continue your reasoning.

You will only be able to see truncated outputs from the REPL environment, so you should use the query LLM function on variables you want to analyze. You will find this function especially useful when you have to analyze the semantics of the context. Use these variables as buffers to build up your final answer.

Make sure to explicitly look through the entire context in REPL before answering your query. An example strategy is to first look at the context and figure out a chunking strategy, then break up the context into smart chunks, and query an LLM per chunk with a particular question and save the answers to a buffer, then query an LLM with all the buffers to produce your final answer.
...
```

---

## 4) Self‑Critique Log（本頁）

- 目前限制：你要求「嚴格基於來源引用」，但 repo 外部的學術/業界來源尚未導入；因此本知識庫只能引用「使用者定義」與「repo 內文件/原始碼」。
- 修正策略：凡無法在 repo 或使用者定義中落地的敘述，應降格為 `ASSUMPTION(llm)` 或移除。

---

## Sources

- [1] 使用者提供的四域 SAGA 定義與回應原則（對話提示詞，2026-01-23）

