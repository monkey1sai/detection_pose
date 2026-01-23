# 🚧 Current Task: 修正「符號回歸」輸出無關文字

**Last Updated**: 2026-01-23  
**Worker**: Codex Agent

## 🎯 Objective
在符號回歸情境下，避免 SAGA 產出「優化/改進…」等無關字串，改為以可解析/可評分的數學表達式作為候選，並以 dataset 擬合品質作為主要目標代理（scoring proxy）。

## 📋 Execution Plan & Progress
- [x] **Root Cause**: 確認 inner loop generator 對「公式候選」仍會注入中文詞，且 scoring proxy 未使用 dataset 做擬合評分
- [x] **Generator Fix**: `EvoGenerator._mutate()` 對疑似公式候選改用數學式突變（不注入 CJK）
- [x] **Scoring Fix**: `AdvancedImplementer` 新增 sandbox-safe 的 symbolic regression scorer（不依賴 import/eval）
- [x] **Data Plumbing**: `SagaRunner` 解析 dataset，`OuterLoop` 將 dataset/keywords/task 傳入 `Optimizer.optimize(..., context)`
- [x] **Tests**: 新增單元測試覆蓋（真公式分數高、中文垃圾候選被拒、突變不注入 CJK）
- [x] **UI Defaults**: 將符號回歸的測試參數設為 Web UI 預設，並新增 inner loop 參數欄位（inner_iterations / batch_size / scoring_timeout_s）

## 🧠 Context & Thoughts
- UI 的「符號回歸」通常把資料點以字串形式送入 `text`（例如 `[(x,y), ...]`）；原先 scoring 未拿到 dataset 上下文時，優化會朝「字串型目標」（長度/關鍵字）收斂，導致看似「收斂」但與任務無關。
- sandbox 目前預設禁止 import/eval；因此符號回歸若仰賴 `eval` 會直接失效，需改用可控的 AST 評估（由 sandbox worker 注入 `ast`）。
- Web UI 原先只提供 outer loop 終止條件與 weights/thresholds，未能調整 inner loop 搜尋力度；目前已把測試參數變成模板預設，並在 UI 暴露 inner loop 參數。

## 📝 Handoff Note
若還要更接近理想的 symbolic regression（更快找到 `x**2 + 3*x - 2`）：
1) Planner/Implementer 加入「泛化」維度（自動 split train/test）。  
2) generator 增加「係數/常數」的系統性探索（減少純隨機突變）。  
3) 加一個 end-to-end 測試（固定 random seed，驗證 best_candidate 的 MSE 門檻）。
