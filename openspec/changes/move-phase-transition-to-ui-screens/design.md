## Context

目前專案已把開始畫面與失敗畫面互動邏輯拆到 ui_screens，但 phase 2->3 狂暴轉場若繼續由 main 管理，會讓主迴圈承擔過多狀態判斷與渲染分支。此變更目標是在不改變戰鬥規則（停火、清彈幕、glitch）的前提下，將轉場生命週期集中在 ui_screens，維持主流程清晰。

## Goals / Non-Goals

**Goals:**
- 將 phase 轉場控制流程（進入、更新、渲染、結束）統一封裝在 ui_screens。
- main 僅做狀態與 frame 委派，減少條件分支與轉場細節耦合。
- 保留既有停火/清彈幕/恢復 phase3 的行為語意。

**Non-Goals:**
- 不變更 Boss 攻擊家族、彈速或難度參數。
- 不新增外部套件。
- 不重寫整個遊戲狀態機架構。

## Decisions

1. 以 ui_screens 提供 transition orchestration API
- 決策: 由 ui_screens 提供一組轉場入口，例如 begin/update/draw/is_active。
- 理由: 轉場屬畫面導向流程，集中於 UI 模組可降低 main 膨脹。
- 替代方案: main 內直接維護 transition 細節。缺點是邏輯分散且難測。

2. main 僅保留 phase crossing 偵測與單次委派
- 決策: main 只負責偵測 phase 2->3 crossing，觸發 ui_screens 的 begin。
- 理由: phase crossing 與戰鬥資料在 main 最容易取得，但轉場細節不應留在 main。
- 替代方案: ui_screens 自己讀取所有 combat 狀態判定 crossing。缺點是 UI 模組耦合戰鬥資料過深。

3. 停火與清彈幕在 begin 階段一次完成
- 決策: 轉場開始時由 ui_screens 觸發統一清理流程，並在 active 期間阻斷攻擊更新。
- 理由: 一次性處理可避免多幀重複清理或漏清容器。
- 替代方案: 每幀判斷是否要清理。缺點是成本高且容易出現狀態競態。

4. Glitch 後處理維持 NumPy/OpenCV 算法但移至 ui_screens
- 決策: 水平切片、RGB split、抖動演算維持既有策略，僅改變模組歸屬。
- 理由: 達到責任重分配而不引入新行為風險。
- 替代方案: 新建獨立特效模組。優點是更純粹，缺點是當前專案規模下會增加切分成本。

## Risks / Trade-offs

- [Risk] ui_screens 介面擴大，隱含對 game 物件欄位依賴增加 -> Mitigation: 用明確 helper 函數封裝所需欄位，減少散落存取。
- [Risk] main 與 ui_screens 轉場狀態重複定義 -> Mitigation: 以單一狀態來源（game.state + transition flags）並集中更新。
- [Risk] 委派邊界不清造成重複渲染 -> Mitigation: 定義 frame 選擇優先順序，transition 分支優先於 RUNNING 一般分支。

## Migration Plan

- 不涉及資料遷移。
- 以小步重構方式導入：先建立 ui_screens API，再把 main 分支逐步改為委派。
- 若出現回歸問題，可暫時回切為 main 內聯轉場分支。

## Open Questions

- begin 時是否同時凍結玩家移動，或僅停火不鎖位移。
- glitch 強度參數是否暴露為可調整常數供平衡測試。
