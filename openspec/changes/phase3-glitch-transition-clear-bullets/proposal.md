## Why

目前二階段切到三階段時，Boss 與玩家攻擊會無縫延續，缺少「狂暴化」前的節奏斷點與視覺演出，導致階段切換辨識度不足。這次需要在 2->3 切換時加入短暫停火與強烈 glitch 轉場，讓玩家明確感知進入高壓第三階段。

## What Changes

- 在 Boss 由 Phase 2 進入 Phase 3 時，加入專屬轉場狀態（transition lock）。
- 轉場期間暫停 Boss 攻擊更新與玩家攻擊更新，並採用清空彈幕策略（玩家彈幕與 Boss 彈幕清空）。
- 轉場期間套用數位雜訊/畫面破圖風特效：水平切片錯位、RGB 通道分離、短暫抖動。
- 轉場結束後恢復正常渲染並進入 Phase 3 攻擊節奏。
- 保持現有 WIN/FAIL 流程與主選單流程不變。

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `side_scroller_shooter`: 新增 Phase 2->3 狂暴轉場需求，明確規範轉場期間停火、清空彈幕、glitch 視覺效果與恢復條件。

## Impact

- 影響遊戲主迴圈狀態切換與 phase 判定節點。
- 影響 Boss/玩家攻擊更新時序與彈幕生命週期管理。
- 影響渲染管線，需新增 transition 特效後處理步驟。
- 不新增外部依賴，維持 OpenCV/NumPy 技術棧。
