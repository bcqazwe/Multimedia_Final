## Context

目前主迴圈在 RUNNING 狀態下每幀同時更新 Boss 移動、Boss 攻擊、玩家攻擊、道具與碰撞。Phase 由 Boss HP 即時計算，尚未有專屬的 2->3 轉場鎖定機制，因此切換瞬間攻擊會連續發生，缺少節奏斷點與視覺辨識。此次變更需在不破壞既有 WIN/FAIL 與主選單流程前提下，加入短時演出狀態。

## Goals / Non-Goals

**Goals:**
- 在 Phase 2 進入 Phase 3 時觸發一次性轉場狀態。
- 轉場期間凍結 Boss 與玩家攻擊更新，並清空現存彈幕。
- 轉場期間呈現 glitch 視效（水平切片錯位、RGB 分離、抖動）。
- 轉場結束後恢復正常流程並進入 Phase 3。

**Non-Goals:**
- 不變更 Boss 攻擊家族內容與數值平衡策略。
- 不引入新第三方套件或音效系統。
- 不重構整個渲染管線為多執行緒/事件系統。

## Decisions

1. 新增過渡狀態而非直接在 RUNNING 內插 if
- 決策: 新增明確 transition state（例如 PHASE_GLITCH），以狀態機承接 2->3 演出。
- 理由: 可讀性高、測試邊界清楚，且可避免分散在多處 update 路徑。
- 替代方案: 在 RUNNING 各段更新前加旗標判斷。缺點是易遺漏，後續維護成本高。

2. 以 phase crossing（prev_phase=2, current_phase=3）做單次觸發
- 決策: 用前後 phase 比較觸發，並設置 transition_active 鎖避免重入。
- 理由: 直接對應 HP 門檻跨越語意，避免每幀重複觸發。
- 替代方案: 以 HP <= 門檻直接觸發。缺點是若無鎖會重複進入。

3. 轉場採清空彈幕策略
- 決策: 轉場開始時清空玩家彈幕與 Boss 攻擊彈幕/危險區。
- 理由: 與「狂暴演出後再開戰」節奏一致，並降低不公平死亡。
- 替代方案: 保留彈幕。優點是壓力連續，缺點是演出可讀性差且死亡歸因不清。

4. Glitch 實作採 NumPy + OpenCV 的後處理疊加
- 決策: 在已完成的 base frame 上施加後處理，不改動各 Entity draw 邏輯。
- 理由: 侵入性低，易於開關與調整參數。
- 替代方案: 在每個 sprite 繪製階段做通道錯位。缺點是耦合高且成本大。

5. 強度採時間曲線控制
- 決策: transition 期間依 elapsed/total 計算強度，前中後段有可預期變化。
- 理由: 比固定亂數更具演出節奏，可避免整段過噪。
- 替代方案: 固定強度。缺點是視覺疲勞，結束點突兀。

## Risks / Trade-offs

- [Risk] 每幀切片與通道位移造成 CPU 壓力上升 -> Mitigation: 限制切片數、限制位移像素、只在短時轉場啟用。
- [Risk] 暫停更新後恢復時攻擊計時器跳拍 -> Mitigation: 轉場結束時重置攻擊器為 idle 或補償 timer。
- [Risk] 清空彈幕使高手玩家覺得壓力被重置 -> Mitigation: 縮短轉場時長並提升 phase3 開場前 1-2 秒節奏。
- [Risk] dual attack mode 下可能遺漏某攻擊容器 -> Mitigation: 以統一 clear_attacks 入口清理 attackA/attackC 所有可傷害結構。

## Migration Plan

- 變更屬本地遊戲邏輯，無資料庫 migration。
- 部署步驟: 更新程式後直接啟動遊戲測試 phase crossing。
- 回滾策略: 關閉 transition state 分支並回到原 RUNNING 流程。

## Open Questions

- 轉場總時長是否固定（如 800ms）或依難度動態調整。
- 轉場期間是否允許玩家移動（目前偏向停火且可移動/不可移動需定案）。
- 轉場結束是否需要 200~300ms 的 phase3 safety grace window。
