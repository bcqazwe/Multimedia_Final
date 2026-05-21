# Design: side-scroller-prototype

## 目標
提供一份針對 `specs/side_scroller_shooter/spec.md` 的具體實作設計，說明系統模組、資料結構、渲染與碰撞流程，以及開發時的效能考量與資源佈局。本次設計鎖定單一 Boss 戰，並移除音訊相關模組。

## 高階架構
- `main.py`：遊戲啟動與主迴圈（init、主循環、清理）。
- `resources.py`：資源載入與快取（sprite sheet 切片）。
- `entities.py`：`Entity` 系列類別（`Player`、`Enemy`、`Bullet`、`Particle`）。
- `scene.py`：關卡/波次管理（spawn rules、scrolling）。
- `render.py`：渲染相關函式（blit、alpha 合成、後處理）。
- `input_.py`：輸入處理（鍵盤）。
- `utils.py`：共用工具（AABB 計算、時間步處理、物件池）。

## 資料結構（範例）
使用 `@dataclass`：

```py
@dataclass
class Entity:
    id: int
    x: int
    y: int
    vx: float
    vy: float
    sprite_index: int
    width: int
    height: int
    hp: int
    active: bool
    mask: Optional[np.ndarray]  # boolean alpha mask

```

## 渲染流程
1. 清空內部 canvas（320x640, uint8）。
2. 繪製背景層（parallax layers）；若層不動則預先合成。
3. 按深度排序批次繪製實體：
   - 對每個實體取得 sprite frame（NumPy array）與預計算 mask。
   - 使用 mask 向量化一次性寫入 canvas 的 slice。
4. 後處理（選用）：bloom、motion blur、CRT effect。
5. 放大到視窗解析度並透過 `cv2.imshow()` 顯示。

## 碰撞檢測
- 批次向量化 AABB 檢查：把所有子彈/敵人的 boxes 以 NumPy 陣列處理過濾。
- 精準碰撞：對於過濾後的候選 pair 使用 `mask1 & mask2` 檢查是否有相交像素。

## 資源佈局
- `assets/sprites/`：sprite sheets (PNG)
- 設計預設解析度與 scale 設定檔（config.py 或 json）

## Boss 戰設計
- Boss 作為單一主要目標，透過血量階段、攻擊模式切換與攻擊前搖，提供完整關卡節奏。
- 遊戲流程可為：進場演出 → 第一階段 → 第二階段 → 結束畫面。
- 建議至少 2~3 種攻擊模式，避免內容過於單一。

## 性能優化策略
- 優先使用 NumPy 向量化與 slice 操作，避免 Python per-pixel loops。
- 使用物件池管理 Bullet/Particle。
- 若必要，用 `numba.njit` 加速批次碰撞或運動更新函式。
- 在可行情況下盡量將靜態圖層預先合成。

## 測試與驗證
- Spike 測試：渲染 1 個 Boss、玩家與少量子彈並量測 FPS。
- 單元測試：資源載入、AABB 計算、mask 合成等可測邏輯。
