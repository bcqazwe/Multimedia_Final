# 橫向卷軸戰機射擊遊戲 - 規格說明 (spec)

語言: zh-tw

## 一、專案簡介
此文件列出在 Windows + Python 平台上，使用 OpenCV/NumPy 為主要渲染手段的「橫向卷軸戰機射擊遊戲」需求與最低可行功能（MVP）。目標風格為像素美術（可直接以陣列渲染），並以效能與簡潔實作為優先。本次更新將玩法收斂為單一敵人 Boss 戰，且不需要音訊。

## 二、目標平台與技術棧
- 平台: Windows（Python）
- 必要套件: `opencv-python`, `numpy`
- 選用套件: `numba`（效能優化）

## 三、最小可行產品（MVP）功能清單
以下為遊戲啟動可接受的最低功能集：

1. 基本畫面與解析度
   - 內部畫布解析度：320x640，以整數倍放大顯示保留像素感。
   - 固定 FPS：60（或可在設定中修改）。

2. 玩家（Player）
   - 左右上下移動（四向或上下與上下微調）。
   - 射擊（單按鍵發射連續子彈）。
   - 生命值（HP）與死亡條件。

3. 敵人（Boss）
   - 單一主要敵人 Boss，具備多階段血量或多段攻擊模式。
   - Boss 能被子彈擊中並扣血，並在生命歸零時結束關卡。

4. 子彈與碰撞
   - 玩家與敵人的子彈（多個同時存在）。
   - 碰撞偵測：先用 AABB 過濾，必要時以 alpha mask 做像素級精準檢測。

5. 關卡 / 波次
   - 自動橫向捲動場景（或玩家帶動捲動），關卡圍繞單一 Boss 戰展開。
   - 可加入 Boss 前置演出或簡單場景變化，但不需要多波小怪。

6. UI 與 HUD
   - 顯示分數、生命/能量、武器等級與當前道具圖示。
   - 暫停畫面（Pause）與重新開始（Restart）。

7. 資產與資源管理
   - 使用 sprite sheet（等格子）並將其切片為 NumPy 陣列緩存。
   - 支援 PNG alpha（保留透明通道）。

## 四、詳細需求

### 4.1 輸入
- 鍵盤支援基本方向與射擊鍵。
- 支援按住按鍵連續移動與連發。
- 若需要控制器支援，後續可再整合其他輸入庫；MVP 不強制。

### 4.2 物件模型
- `Entity` 基類（位置、速度、sprite index、hitbox、hp、active flag）。
- 使用 `@dataclass` 定義資料結構以利序列化/測試。

### 4.3 渲染管線
- 內部 canvas（NumPy uint8）做所有圖層合成。
- 使用向量化 mask（boolean arrays）做 alpha 貼合（避免 per-pixel Python loop）。
- 後處理（可選）：bloom、motion blur、CRT scanlines，使用 OpenCV 運算（GaussianBlur, addWeighted）。

### 4.4 碰撞
- 先大範圍 AABB 向量化過濾（批次計算）。
- 若需精準碰撞，使用 sprite 的 alpha boolean mask 做 bitwise AND 檢查。

### 4.5 效能目標
- 目標在典型桌面機（非高階 GPU）能維持 60 FPS，若無法達成則優先降低粒子數、特效或降低內部解析度。

## 五、資產規格（像素風）
- Sprite 格子大小：建議 16x16、24x24 或 32x32。
- Sprite sheet 排列：固定格線（rows x cols）每格同尺寸。
- 檔案格式：PNG（8-bit + alpha）。
- 色盤建議：若要復古風可限制至 16 或 32 色；若要簡單快速可任意 24-bit 色。

## 六、接受準則（Acceptance Criteria）
遊戲在驗收時需滿足：

- 能在 Windows 上啟動主視窗並以 320x640 內部解析度正確放大顯示。
- 玩家可移動並射擊，子彈可擊中敵人並造成得分或死亡反饋。
- 關卡以單一 Boss 戰構成，Boss 具有可見的攻擊模式與血量階段，且效能在典型桌面 CPU 下保持可玩（>=30 FPS；理想 60 FPS）。
- HUD 顯示生命與分數，並可暫停遊戲。

## 七、Spike 任務（建議排序）
1. Spike 1 — 基礎渲染：載入 sprite sheet、切片、在內部 canvas 上貼上單一移動精靈並放大顯示（驗證 nearest-neighbor 放大）。
2. Spike 2 — 碰撞效能：建立大量子彈與敵人，使用向量化 AABB 批次碰撞，觀察 FPS。
3. Spike 3 — 後處理效果：實作簡單 bloom 與 motion blur，量測效能影響與視覺效果。

## 八、風險與替代方案
- 風險：大量粒子與特效在 Python + OpenCV 上會成為 CPU 瓶頸。
  - 替代：減少粒子數、降低內部解析度、或在需要時使用 `numba` 或 GPU 加速模組。
- 風險：單一 Boss 戰若攻擊模式太少，會顯得內容不足。
   - 替代：為 Boss 加入多階段與可視化弱點，提升節奏與變化。

## 九、交付物
- `spec.md`（本檔）
- 建議後續產出：`tasks.md`（Spike 與實作任務）、`design.md`（高階系統設計與資料流）、最小 prototype 程式碼。

----
註：本規格為 MVP 指南，若同意我可以把 `tasks.md` 與 `design.md` 草稿一起建立。若要我開始實作 Spike，也請回覆同意退出探索模式。
