## Why

目前專案沒有統一的音效層，若要在階段轉場時播放 `sfx/phase3_warning.mp3`，直接把播放邏輯散落在 `main.py` 或 `ui_screens.py` 會讓戰鬥流程和音效耦合。建立獨立的 `audio.py` 並使用 `pygame`，可以把音效載入、播放與未來擴充集中管理，同時保留現有渲染與更新流程的簡潔性。

## What Changes

- 新增一個獨立的 `audio.py`，作為音效播放與管理入口。
- 使用 `pygame.mixer` 播放 `mp3` 音效，先支援階段 2→3 的警告提示音。
- 在階段轉場觸發點統一呼叫音效層，避免把播放邏輯散落在主迴圈。
- 保留現有 OpenCV 渲染與戰鬥更新架構，不把音效播放混入畫面繪製流程。
- **BREAKING**: 音效播放不再依賴臨時的 inline 播放程式碼，改由集中式音效管理器處理。

## Capabilities

### New Capabilities
- `audio-playback-manager`: 提供集中式音效載入與播放能力，支援以 `pygame` 播放 `mp3` 提示音，並可由遊戲轉場事件觸發。

### Modified Capabilities
- 

## Impact

- 影響新增的 `audio.py` 模組設計與其公開 API。
- 影響 `main.py` 的事件觸發點，尤其是 2→3 phase crossing 的音效呼叫。
- 影響專案依賴，需加入 `pygame`。
- 不影響現有視覺轉場規格，但會讓轉場事件同時支援音效提示。
