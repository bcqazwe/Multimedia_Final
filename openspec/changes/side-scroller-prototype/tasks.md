# Tasks: side-scroller-prototype

## 優先順序與概覽
此清單以 Spike 為先、然後進入最小可玩原型（MVP）實作任務，最後為優化與整理。本次版本以單一 Boss 戰為核心，不包含音訊與多波小怪。

### Spike（高優先，短時）
1. Spike-A: 基礎渲染 (1 day)
   - 載入 sprite sheet，切片為 NumPy 陣列。
   - 在內部 canvas（320x640）上顯示單一可移動精靈並以 `INTER_NEAREST` 放大顯示。
   - 成果：截圖與 FPS 記錄。

2. Spike-B: 碰撞效能 (1 day)
   - 實作大量子彈與敵人的 AABB 批次檢測。
   - 測試與紀錄在不同數量下的 FPS。

3. Spike-C: 後處理測試 (0.5 day)
   - 實作簡單 bloom 與 motion blur，量測效能。

### MVP 實作任務（中優先）
4. Player 與控制 (1 day)
   - 實作玩家移動、射擊、生命系統、死亡回饋。

5. Boss 系統 (2 days)
   - 實作單一 Boss 的多階段血量、攻擊模式與前搖/後搖狀態。

6. 碰撞與子彈系統 (1 day)
   - 完成子彈池、AABB 過濾與精準檢測流程。

7. HUD 與 UI (0.5 day)
   - 顯示分數、生命、暫停/重試功能。

### 優化與整理（低優先）
8. 效能優化（as needed）
   - `numba` 加速熱點、預計算更多資源。

9. 測試與文件
   - 撰寫 README、執行方法、以及簡易測試腳本。

## 交付驗收
- 每個 Spike 需提交短報告（結果、FPS、問題點）。
- MVP 應達到基本接受準則（參見 `specs/side_scroller_shooter/spec.md`）。
