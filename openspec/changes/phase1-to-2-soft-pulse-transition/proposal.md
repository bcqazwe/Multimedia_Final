## Why

目前 2→3 已經有較強烈的 glitch 轉場與清彈幕演出，但 1→2 仍缺少一致的節奏斷點。當 Boss 進入第二階段時，若能先以較輕量的過場停火、清彈幕並給出明確視覺提示，玩家會更容易讀懂階段切換，同時不會搶走 2→3 的戲劇性。

## What Changes

- 在階段 1 進入階段 2 時，新增一段 5 秒的輕量轉場。
- 轉場期間暫停玩家與 Boss 的動作更新，並清空螢幕上的子彈與危險判定。
- 轉場視覺採「軟性脈衝清場」風格，強度明顯低於 2→3 的 glitch 演出。
- 保留 2→3 現有的強轉場與故障風格，不與本次新轉場混用。

## Capabilities

### New Capabilities
- `phase1-to-2-soft-pulse-transition`: 定義階段 1→2 的輕量轉場行為，包括停火、清彈幕、5 秒持續時間與低強度視覺提示。

### Modified Capabilities
- 

## Impact

- 影響 `ui_screens.py` 的轉場管理與畫面疊加流程。
- 影響 `main.py` 或 Boss 更新流程中的 phase crossing 判斷與停火/清場委派。
- 影響 Boss 攻擊容器與玩家子彈容器在轉場期間的更新節奏。
- 不需要新增第三方套件；視覺效果應維持在現有 OpenCV / NumPy 管線內。
