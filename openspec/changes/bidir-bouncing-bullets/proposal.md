# Change: bidir-bouncing-bullets

## What
新增 Boss 的「雙向發射且會在側邊反彈」彈幕攻擊（bidir bouncing bullets），並把此行為階段化：每個 phase 都會使用完整攻擊池，但單次發射顆數固定，差異只來自速度、角度與傷害的提升，使玩家安全走廊逐步縮小。

## Why
- 目前 AttackA 的直線/扇形/追蹤彈在後期仍然較容易閃避。
- 引入反彈行為能讓彈幕路徑延伸並填滿場域，增加空間壓迫感且符合使用者要求「階段越後面留給玩家的空家樂小」。
- 可用作效能壓力測試（與 dual_attack_mode 結合）以量化彈幕數量對 FPS 的影響。
 - 使用固定單次顆數可讓壓力來源更可控，避免 phase 升高時因子彈數暴增而失去可比較性。

## Scope
- 只改動 boss 的攻擊系統（`boss_attacks.py`）與最少量的整合程式碼（若需顯示統計則改 `main.py`）。
- 產出三個 artifact：proposal.md（本檔）、design.md、tasks.md。
- 不會變更玩家碰撞、關卡系統或資產檔案。

## Acceptance Criteria
- `openspec/changes/bidir-bouncing-bullets/` 包含 proposal.md、design.md、tasks.md
- 新增的彈幕能在左右邊界反彈（最大反彈次數可調）且不會導致無限增長或記憶體泄漏
- 每個 phase 都會輪到同一組攻擊手段；phase 不改變單次發射顆數，只改變速度、角度與傷害
- 依 phase 提供可調參數：`speed`, `angle`, `damage`, `max_bounces`, `interval_scale`
- 可用 `dual_attack_mode` 同時啟動大量攻擊以做壓力測試

