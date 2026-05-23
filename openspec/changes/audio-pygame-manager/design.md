## Context

目前專案沒有獨立音效模組，音效播放若直接寫在 `main.py` 會讓 phase crossing、UI 與音訊混在一起。此次變更要新增 `audio.py`，把 `pygame.mixer` 的初始化、音效載入與單次播放集中處理，並在 phase 2->3 轉場時播放 `sfx/phase3_warning.mp3`。

約束條件：
- 仍以 Windows + Python 為主要執行環境。
- 不破壞現有 OpenCV 視覺主迴圈。
- 音效失敗不得導致遊戲崩潰或阻塞。

## Goals / Non-Goals

**Goals:**
- 提供一個可重用的 `audio.py` 音效管理層。
- 使用 `pygame` 播放 `mp3` 警告音。
- 在 phase 2->3 crossing 時只觸發一次音效。
- 保持主迴圈更新與畫面渲染不受音效播放影響。

**Non-Goals:**
- 不建立完整 BGM 系統。
- 不處理混音、音量滑桿或多通道優先權。
- 不重構整個遊戲事件系統。

## Decisions

1. 以 `pygame.mixer` 作為唯一播放後端
- 決策: 直接使用 `pygame.mixer` 播放 `mp3`，由 `audio.py` 封裝初始化與播放。
- 理由: 能直接支援 `mp3`，而且對短促警告音效的整合成本低。
- 替代方案: `winsound` 或 `simpleaudio`。缺點是主要支援 `wav`，需要轉檔。

2. 音效管理獨立成薄模組
- 決策: 新增 `audio.py`，由它統一負責載入、播放與簡單保護邏輯。
- 理由: 可以把音效依賴從 `main.py` 與 `ui_screens.py` 分離，避免遊戲流程與音訊 API 糾纏。
- 替代方案: 將播放邏輯直接寫在 `main.py`。缺點是未來音效擴充時會快速膨脹。

3. 轉場觸發採一次性事件
- 決策: phase 2->3 crossing 觸發時只播放一次 warning cue，並以內部旗標避免每幀重播。
- 理由: phase transition 是單次事件，不應在 active 期間重複啟動音效。
- 替代方案: 每幀檢查並重播。缺點是會產生刺耳重複播放與 CPU 浪費。

4. 音效失敗採降級不崩潰
- 決策: 若 mixer 初始化或音檔載入失敗，系統只記錄失敗並跳過播放。
- 理由: 遊戲核心是射擊與轉場，音效不可成為單點故障。
- 替代方案: 直接中止遊戲。這不符合可用性需求。

## Risks / Trade-offs

- [Risk] `pygame` 增加依賴與安裝成本 → Mitigation: 只在需要音效時引入，並把音效 API 封裝成薄層。
- [Risk] 音效初始化在某些 Windows 音訊設備上失敗 → Mitigation: 提供無音訊 fallback，不阻塞主迴圈。
- [Risk] 音效觸發點若寫得太散，容易重播 → Mitigation: 只在 phase crossing 的單一入口觸發。

## Migration Plan

- 新增 `audio.py`，實作 `pygame.mixer` 初始化與 cue 播放。
- 將 `main.py` 的 phase 2->3 crossing 改為呼叫音效管理器。
- 新增/更新依賴安裝說明，加入 `pygame`。
- 驗證無音效裝置時遊戲仍可啟動與渲染。
- 若回歸，關閉音效呼叫即可回退到原本無聲流程。

## Open Questions

- 是否只播放單一 warning cue，還是未來也要支援更多轉場/命中音效。
- 是否需要讓音效管理器先做 lazy init，避免啟動時就碰音訊裝置。
- `mp3` 是否要保留，或後續轉成 `wav` 以降低相容性風險。
