# SAGA UI Mermaid Render Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在 `web_client` 內使用 mermaid NPM 套件即時渲染 workflow.mmd，於 `run_finished` 後自動顯示圖。

**Architecture:** 前端接收 `run_finished` 後拉取 `/runs/<run_id>/workflow.mmd`，用 mermaid 轉 SVG 並掛載到 UI 區塊；保留現有 events/graph.json 顯示流程。

**Tech Stack:** Vite + React, mermaid (NPM)

---

### Task 1: 新增 mermaid 依賴與基礎渲染元件

**Files:**
- Modify: `web_client/package.json`
- Create: `web_client/src/components/MermaidView.jsx`
- Test: (manual) `web_client` dev server render

**Step 1: Write the failing test**

（前端無自動化測試，改用手動驗收）

**Step 2: Build minimal implementation**

```json
// web_client/package.json (dependencies)
"mermaid": "^10.9.1"
```

```jsx
// web_client/src/components/MermaidView.jsx
import React, { useEffect, useRef } from "react";
import mermaid from "mermaid";

export default function MermaidView({ code }) {
  const ref = useRef(null);
  useEffect(() => {
    mermaid.initialize({ startOnLoad: false, theme: "dark" });
    if (!code) return;
    const id = `mermaid-${Date.now()}`;
    mermaid.render(id, code).then(({ svg }) => {
      if (ref.current) ref.current.innerHTML = svg;
    });
  }, [code]);
  return <div ref={ref} />;
}
```

**Step 3: Manual verification**

Run:
```
cd web_client
npm install
npm run dev
```
Expected: MermaidView 顯示 SVG（用固定字串測試）。

**Step 4: Commit**

```bash
git add web_client/package.json web_client/src/components/MermaidView.jsx
git commit -m "feat: add mermaid renderer"
```

---

### Task 2: App.jsx 接入 MermaidView 並改為即時渲染

**Files:**
- Modify: `web_client/src/App.jsx`

**Step 1: Write the failing test**

（前端無自動化測試，改用手動驗收）

**Step 2: Build minimal implementation**

- 在 `run_finished` 後 fetch `/runs/<run_id>/workflow.mmd`
- 將內容傳入 `MermaidView`
- 移除原本的 Mermaid 文字區塊（只顯示圖）

**Step 3: Manual verification**

Run:
```
npm run dev
```
Expected: Run 完成後顯示 Mermaid 圖。

**Step 4: Commit**

```bash
git add web_client/src/App.jsx
git commit -m "feat: render mermaid graph in ui"
```

---

### Task 3: README 更新

**Files:**
- Modify: `web_client/README.md`

**Step 1: Update docs**
- 說明 Mermaid 渲染依賴與使用方式

**Step 2: Commit**

```bash
git add web_client/README.md
git commit -m "docs: update web client mermaid usage"
```

---

Plan complete and saved to `docs/plans/2026-01-14-saga-ui-mermaid-render-plan.md`. Two execution options:

1. Subagent-Driven (this session)
2. Parallel Session (separate)

Which approach?
