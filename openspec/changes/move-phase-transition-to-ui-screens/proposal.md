## Why

目前 phase 轉場控制邏輯若分散在主迴圈，會持續增加 main 的分支與狀態判斷負擔，降低可維護性。將轉場流程集中到 ui_screens 可讓 main 聚焦戰鬥更新，並使畫面演出責任單一化。

## What Changes

- 將 Phase 2->3 的狂暴轉場控制流程封裝到 ui_screens（包含進入、更新、繪製、結束）。
- main 僅保留最小委派呼叫，不在主迴圈內維護轉場細節。
- 轉場期間停火與清空彈幕策略維持不變（玩家彈幕與 Boss 彈幕/危險區清空）。
- glitch 視效處理管線由 ui_screens 管理，統一轉場渲染入口。

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `side_scroller_shooter`: 補充 phase 轉場模組化要求，規範轉場責任應集中於 UI/transition 模組而非主迴圈內聯流程。

## Impact

- 影響 main 與 ui_screens 的責任分工與呼叫邊界。
- 影響 phase 轉場狀態欄位管理與轉場更新時機。
- 不改變外部 API 與依賴；維持 OpenCV/NumPy。
