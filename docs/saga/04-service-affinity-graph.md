# SAGA 服務優化（Service Affinity Graph-based Approach）—名詞消歧用

本頁的 **SAGA** 指的是雲端原生環境中，基於「服務親和力圖」的微服務部署最佳化方法（Service Affinity Graph-based Approach）。[1]

---

## 1) 一句話定義

SAGA（此處）把微服務之間的互動（資料交換量、延遲敏感度、隱私/合規需求等）建模成圖（Graph），再用分群（Clustering）把關聯性高的服務放得更近（例如同區域/同節點/同叢集），以降低延遲與成本並滿足限制條件。[1]

---

## 2) 核心機制（概念層）

- **Affinity Graph**：節點=服務，邊=服務間互動強度/需求（可加權）
- **Objective**：延遲、成本、跨區流量、資料主權/隱私約束等（常為多目標）
- **Clustering / Placement**：輸出服務分組與部署位置（例如以圖分割/社群偵測/啟發式搜尋）[1]

---

## 3) 與本 repo 的關係（目前狀態）

本 repo 目前以單機或單叢集部署為主（Docker Compose 編排），尚未看見基於 affinity graph 的自動化 placement/成本最佳化模組。  
因此本頁主要用於名詞消歧，而非描述 repo 既有功能。[1]

---

## Sources

- [1] 使用者提供的四域 SAGA 定義與回應原則（對話提示詞，2026-01-23）

