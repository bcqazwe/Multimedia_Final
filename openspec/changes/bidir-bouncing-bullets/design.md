# Design: Bidir Bouncing Bullets

## Overview
在 `BossAttackA` 中保留既有攻擊手段（straight / cross / homing / bidir_bounce），但改成每個 phase 都會經過同一組攻擊池。phase 不再決定「有哪些招式存在」，只決定每個招式的速度、角度、傷害與反彈強度。子彈遇到左右邊界時進行水平反射（`vx = -vx * loss_factor`），每次反彈遞增 `bounces` 計數直到達 `max_bounces` 再回收。

## Data model
每顆 bullet 已有欄位 `x, y, vx, vy, img`。新增欄位：
- `bounces` (int): 已反彈次數，初始 0
- `max_bounces` (int): 該彈可反彈最大次數（可由 phase 決定）
- `loss_factor` (float): 每次反彈速度衰減係數（預設 0.96）

使用池化 `_pool`（現有實作）管理物件重用。

## Behaviour rules
- 邊界檢查只對左右邊界觸發水平反射；超出上下邊界則視為結束並回收。
- 反彈時只反轉 `vx`，`vy` 保持不變（視需要可同時變化）。
- 若反彈次數 >= `max_bounces`，下一次超出邊界時即回收。
- 為避免穿幀漏判，當速度過大時採用連續位置檢查：若下一位置超出邊界，將位置 clamp 到邊界並計入一次反彈。
- 同一招式的單次發射顆數固定，phase 僅調整速度、角度與傷害，不因 phase 增加總顆數。

## Integration points
- `boss_attacks.py`: 讓 `BossAttackA` 的招式輪替在所有 phase 中都包含同一組 attacks，並把 phase 參數映射到每個招式的 speed/angle/damage 表。
- `BossAttackA.update`: 在更新子彈位置後插入邊界檢查/反彈邏輯與回收判斷，調整 culling 條件以允許尚未達 `max_bounces` 的彈保留。
- `main.py`（選用）：新增 debug overlay 顯示目前 `len(attackA.bullets)`，以及 `dual_attack_mode`（已有）配合測試。

## Parameters (suggested defaults)
Phase 1:
- speed: 12
- angle: wider
- damage: low
- interval_scale: 0.95
- max_bounces: 1

Phase 2:
- speed: 18
- angle: medium
- damage: medium
- interval_scale: 0.80
- max_bounces: 2

Phase 3:
- speed: 26
- angle: narrow / closer to horizontal
- damage: high
- interval_scale: 0.65
- max_bounces: 3

## Safety and performance
- 上限池化容量與 bullets 數量限制（例如 1024）以防爆量。
- 每次反彈減速（loss_factor）以確保彈在有限時間內被回收。
- 建議在開發階段使用簡化圖形（方塊）以加速渲染測試。

## Testing notes
- 單元測試：模擬子彈位置更新與反彈次數，驗證不會超過 `max_bounces`。
- 整合測試：在 `dual_attack_mode` 下啟動，量測最大 bullets 與 FPS。
- 平衡測試：確認每個 phase 都會輪到所有攻擊手段，但沒有因 phase 升高而增加單次顆數。

