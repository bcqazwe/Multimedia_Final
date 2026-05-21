# Proposal: side-scroller-prototype

## 概要
建立一個橫向卷軸戰機射擊遊戲的變更提案，目標是以 Windows + Python 為平台，使用 OpenCV/NumPy 進行像素風渲染，先完成設計與任務規劃（不立即實作）。本次更新將原型收斂為單一 Boss 戰，並移除音訊需求。此變更會產出 `proposal.md`、`design.md`、`tasks.md` 三份文件，作為後續實作（Spike / prototype）的基礎。

## 為何要做這個變更
- 已有 `specs/side_scroller_shooter/spec.md` 描述 MVP 與技術限制，本變更將把規格落地為可執行的設計與任務清單，降低實作風險並列出優先級 Spike。
- 單一 Boss 戰更適合先驗證 OpenCV + NumPy 的渲染、碰撞與節奏控制，避免一開始就把範圍擴大到多敵人波次與音訊整合。

## 範圍 (scope)
- 包含：設計文件（`design.md`）、任務/排程（`tasks.md`）、提案說明（本檔）。
- 不包含：實際程式碼實作（Spike 實作會在另一次變更或 `/opsx:apply` 後進行）。
- 不包含：音訊系統與多敵人波次內容。

## 成果
- `design.md`：系統設計、模組化分工、資料結構、渲染/碰撞流程、資源 layout。
- `tasks.md`：分解的 Spike 與實作任務，含估時與優先順序。
