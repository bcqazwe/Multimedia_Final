import cv2
import numpy as np

from Background import BackgroundScroller
from control import ShipController

class Game:
    def __init__(self):
        # 設定視窗解析度
        self.WINDOW_W, self.WINDOW_H = 320, 640
        self.DISPLAY_W, self.DISPLAY_H = self.WINDOW_W * 2, self.WINDOW_H * 2

        # 直接重用 Background.py 的背景捲動邏輯
        self.background = BackgroundScroller(
            image_path='Background.jpg',
            window_w=self.WINDOW_W,
            window_h=self.WINDOW_H,
            scroll_speed=2,
        )
        
        # 載入玩家船隻 (包含 Alpha channel)
        self.ship_img = cv2.imread('player_ship_2.png', cv2.IMREAD_UNCHANGED)
        if self.ship_img is None:
            self.ship_img = np.zeros((50, 50, 4), dtype=np.uint8)
        self.ship_display_img = cv2.resize(
            self.ship_img,
            (self.ship_img.shape[1] * 2, self.ship_img.shape[0] * 2),
            interpolation=cv2.INTER_NEAREST,
        )
        self.ship_controller = ShipController(
            self.DISPLAY_W,
            self.DISPLAY_H,
            self.ship_display_img.shape[1],
            self.ship_display_img.shape[0],
        )
            
        # 遊戲狀態
        self.state = "START_MENU"
        self.start_button_rect = [self.DISPLAY_W // 2 - 100, self.DISPLAY_H // 2 + 50, 200, 60] # x, y, w, h
        
    def overlay_image(self, background, overlay, x, y):
        """將具有透明度的圖片疊加到背景上"""
        h, w = overlay.shape[:2]
        if x >= background.shape[1] or y >= background.shape[0] or x + w <= 0 or y + h <= 0:
            return background

        overlay_img = overlay[:, :, :3]
        overlay_mask = overlay[:, :, 3:] / 255.0

        x1 = max(x, 0)
        y1 = max(y, 0)
        x2 = min(x + w, background.shape[1])
        y2 = min(y + h, background.shape[0])

        overlay_x1 = x1 - x
        overlay_y1 = y1 - y
        overlay_x2 = overlay_x1 + (x2 - x1)
        overlay_y2 = overlay_y1 + (y2 - y1)

        roi = background[y1:y2, x1:x2]
        overlay_roi = overlay_img[overlay_y1:overlay_y2, overlay_x1:overlay_x2]
        mask_roi = overlay_mask[overlay_y1:overlay_y2, overlay_x1:overlay_x2]

        background[y1:y2, x1:x2] = (1.0 - mask_roi) * roi + mask_roi * overlay_roi
        return background

    def draw_start_menu(self):
        # 1. 取得當前捲動背景畫面 (原解析度)
        frame = self.background.get_frame()
        
        # 放大顯示畫面
        display_frame = cv2.resize(frame, (self.DISPLAY_W, self.DISPLAY_H), interpolation=cv2.INTER_NEAREST)

        # 2. 顯示玩家船隻 (在中軸下方，直接畫在放大後的畫面上)
        self.overlay_image(display_frame, self.ship_display_img, self.ship_controller.x, self.ship_controller.y)
        
        # 3. 繪製標題
        title = "SPACE SHOOTER"
        font = cv2.FONT_HERSHEY_DUPLEX
        cv2.putText(display_frame, title, (self.DISPLAY_W // 2 - 250, 300), font, 2, (255, 255, 255), 3, cv2.LINE_AA)
        
        # 4. 繪製開始按鈕 (在放大後的畫面上繪製)
        bx, by, bw, bh = self.start_button_rect
        cv2.rectangle(display_frame, (bx, by), (bx + bw, by + bh), (200, 200, 200), -1)
        cv2.putText(display_frame, "START GAME", (bx + 20, by + 40), font, 1, (0, 0, 0), 2, cv2.LINE_AA)
        
        return display_frame

    def draw_game_frame(self):
        frame = self.background.get_frame()
        display_frame = cv2.resize(frame, (self.DISPLAY_W, self.DISPLAY_H), interpolation=cv2.INTER_NEAREST)

        self.overlay_image(display_frame, self.ship_display_img, self.ship_controller.x, self.ship_controller.y)

        cv2.putText(display_frame, "USE WASD / ARROWS", (120, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)
        return display_frame

    def handle_mouse(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            bx, by, bw, bh = self.start_button_rect
            if bx <= x <= bx + bw and by <= y <= by + bh:
                print("Game Starting...")
                self.state = "RUNNING"

    def run(self):
        cv2.namedWindow('Space Shooter')
        cv2.setMouseCallback('Space Shooter', self.handle_mouse)
        
        while True:
            if self.state == "START_MENU":
                frame = self.draw_start_menu()
            else:
                frame = self.draw_game_frame()
            
            cv2.imshow('Space Shooter', frame)
            
            # 更新背景捲動
            self.background.update()

            if self.state == "RUNNING":
                self.ship_controller.update()
                
            key = cv2.waitKey(16) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('m'):
                self.state = "START_MENU"
                self.ship_controller.reset()
                
        cv2.destroyAllWindows()

if __name__ == "__main__":
    game = Game()
    game.run()
