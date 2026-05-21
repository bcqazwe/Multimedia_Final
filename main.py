import cv2
import numpy as np
import time
import os

from Background import BackgroundScroller
from Boss import BossController
from Health import HealthMeter, draw_health_bar, draw_segmented_health_bar
from control import ShipController, BulletController


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def asset_path(filename):
    return os.path.join(BASE_DIR, 'image', filename)


def imread_unicode(path, flags=cv2.IMREAD_COLOR):
    data = np.fromfile(path, dtype=np.uint8)
    if data.size == 0:
        return None
    return cv2.imdecode(data, flags)

class Game:
    def __init__(self):
        # 設定視窗解析度
        self.WINDOW_W, self.WINDOW_H = 320, 640
        self.DISPLAY_W, self.DISPLAY_H = self.WINDOW_W * 2, self.WINDOW_H * 2

        # 直接重用 Background.py 的背景捲動邏輯
        self.background = BackgroundScroller(
            image_path=asset_path('Background.jpg'),
            window_w=self.WINDOW_W,
            window_h=self.WINDOW_H,
            scroll_speed=2,
        )
        
        # 載入玩家船隻 (包含 Alpha channel)
        self.ship_img = imread_unicode(asset_path('player_ship_2.png'), cv2.IMREAD_UNCHANGED)
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

        self.bullet_img = imread_unicode(asset_path('player_bullet_stage1.png'), cv2.IMREAD_UNCHANGED)
        self.bullet_controller = BulletController(
            self.bullet_img,
            self.DISPLAY_W,
            self.DISPLAY_H,
            self.ship_controller,
            fire_interval=180,
            speed=16,
            max_bullets=6,
        )

        self.boss_controller = BossController(self.DISPLAY_W, self.DISPLAY_H)
        self.boss_health = HealthMeter(3000)
        self.player_health = HealthMeter(100)
        self.last_player_hit_ms = 0
            
        # 遊戲狀態
        self.state = "START_MENU"
        self.start_button_rect = [self.DISPLAY_W // 2 - 100, self.DISPLAY_H // 2 + 50, 200, 60] # x, y, w, h
        self.menu_button_rect = [self.DISPLAY_W // 2 - 120, self.DISPLAY_H // 2 + 80, 240, 60]
        
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

        # 2. 顯示 boss 與玩家船隻
        display_frame = self.boss_controller.draw(display_frame)
        self.overlay_image(display_frame, self.ship_display_img, self.ship_controller.x, self.ship_controller.y)
        
        # 3. 繪製標題
        title = "SPACE SHOOTER"
        font = cv2.FONT_HERSHEY_DUPLEX
        cv2.putText(display_frame, title, (self.DISPLAY_W // 2 - 250, 300), font, 2, (255, 255, 255), 3, cv2.LINE_AA)

        #draw_segmented_health_bar(display_frame, self.boss_health.current_hp, self.boss_health.max_hp, 40, 20, 1000, 180, 24, (0, 0, 255), label="BOSS")
        #draw_health_bar(display_frame, self.player_health.current_hp, self.player_health.max_hp, 40, self.DISPLAY_H - 44, self.DISPLAY_W - 80, 24, (0, 255, 0), label="PLAYER")
        
        # 4. 繪製開始按鈕 (在放大後的畫面上繪製)
        bx, by, bw, bh = self.start_button_rect
        cv2.rectangle(display_frame, (bx, by), (bx + bw, by + bh), (200, 200, 200), -1)
        cv2.putText(display_frame, "START GAME", (bx + 20, by + 40), font, 1, (0, 0, 0), 2, cv2.LINE_AA)
        
        return display_frame

    def draw_win_screen(self):
        frame = self.background.get_frame()
        display_frame = cv2.resize(frame, (self.DISPLAY_W, self.DISPLAY_H), interpolation=cv2.INTER_NEAREST)

        dark_overlay = np.zeros_like(display_frame)
        display_frame = cv2.addWeighted(display_frame, 0.35, dark_overlay, 0.65, 0)

        font = cv2.FONT_HERSHEY_DUPLEX
        cv2.putText(display_frame, "YOU WIN", (self.DISPLAY_W // 2 - 170, self.DISPLAY_H // 2 - 50), font, 2.4, (255, 255, 255), 4, cv2.LINE_AA)
        cv2.putText(display_frame, "BOSS DEFEATED", (self.DISPLAY_W // 2 - 180, self.DISPLAY_H // 2), font, 1.2, (220, 220, 220), 2, cv2.LINE_AA)

        bx, by, bw, bh = self.menu_button_rect
        cv2.rectangle(display_frame, (bx, by), (bx + bw, by + bh), (210, 210, 210), -1)
        cv2.putText(display_frame, "MAIN MENU", (bx + 28, by + 40), font, 1, (0, 0, 0), 2, cv2.LINE_AA)

        return display_frame

    def draw_game_frame(self):
        frame = self.background.get_frame()
        display_frame = cv2.resize(frame, (self.DISPLAY_W, self.DISPLAY_H), interpolation=cv2.INTER_NEAREST)

        if not self.boss_health.is_empty():
            display_frame = self.boss_controller.draw(display_frame)
        display_frame = self.bullet_controller.draw(display_frame)
        self.overlay_image(display_frame, self.ship_display_img, self.ship_controller.x, self.ship_controller.y)

        draw_segmented_health_bar(display_frame, self.boss_health.current_hp, self.boss_health.max_hp, 40, 20, 1000, 180, 24, (0, 0, 255), label="BOSS")
        draw_health_bar(display_frame, self.player_health.current_hp, self.player_health.max_hp, 40, self.DISPLAY_H - 44, self.DISPLAY_W - 80, 24, (0, 255, 0), label="PLAYER")

        cv2.putText(display_frame, "USE WASD / ARROWS", (120, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)
        return display_frame

    def reset_match(self):
        self.boss_controller.reset()
        self.boss_health = HealthMeter(3000)
        self.player_health = HealthMeter(100)
        self.ship_controller.reset()
        self.bullet_controller.bullets.clear()
        self.bullet_controller.last_fire_time = 0
        self.last_player_hit_ms = 0

    def handle_combat(self, now_ms):
        if self.boss_health.is_empty() or self.player_health.is_empty():
            return

        boss_x, boss_y, boss_w, boss_h = self.boss_controller.get_rect()
        boss_rect = (boss_x, boss_y, boss_x + boss_w, boss_y + boss_h)

        remaining_bullets = []
        bullet_w = self.bullet_controller.bullet_img.shape[1]
        bullet_h = self.bullet_controller.bullet_img.shape[0]

        for bullet in self.bullet_controller.bullets:
            bullet_rect = (bullet["x"], bullet["y"], bullet["x"] + bullet_w, bullet["y"] + bullet_h)
            hit_boss = not (
                bullet_rect[2] < boss_rect[0]
                or bullet_rect[0] > boss_rect[2]
                or bullet_rect[3] < boss_rect[1]
                or bullet_rect[1] > boss_rect[3]
            )

            if hit_boss:
                self.boss_health.take_damage(5)
            else:
                remaining_bullets.append(bullet)

        self.bullet_controller.bullets = remaining_bullets

        ship_x = self.ship_controller.x
        ship_y = self.ship_controller.y
        ship_w = self.ship_controller.ship_w
        ship_h = self.ship_controller.ship_h
        ship_rect = (ship_x, ship_y, ship_x + ship_w, ship_y + ship_h)

        hit_player = not (
            ship_rect[2] < boss_rect[0]
            or ship_rect[0] > boss_rect[2]
            or ship_rect[3] < boss_rect[1]
            or ship_rect[1] > boss_rect[3]
        )

        if hit_player and now_ms - self.last_player_hit_ms >= 500:
            self.player_health.take_damage(10)
            self.last_player_hit_ms = now_ms

        if self.boss_health.is_empty():
            self.state = "WIN"

    def handle_mouse(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            if self.state == "START_MENU":
                bx, by, bw, bh = self.start_button_rect
                if bx <= x <= bx + bw and by <= y <= by + bh:
                    print("Game Starting...")
                    self.reset_match()
                    self.state = "RUNNING"
            elif self.state == "WIN":
                bx, by, bw, bh = self.menu_button_rect
                if bx <= x <= bx + bw and by <= y <= by + bh:
                    self.reset_match()
                    self.state = "START_MENU"

    def run(self):
        cv2.namedWindow('Space Shooter')
        cv2.setMouseCallback('Space Shooter', self.handle_mouse)
        
        while True:
            now_ms = int(time.time() * 1000)

            if self.state in ("START_MENU", "RUNNING"):
                self.boss_controller.update(now_ms)

            if self.state == "RUNNING":
                self.ship_controller.update()
                self.bullet_controller.update(now_ms)
                self.handle_combat(now_ms)

            if self.state == "START_MENU":
                frame = self.draw_start_menu()
            elif self.state == "WIN":
                frame = self.draw_win_screen()
            else:
                frame = self.draw_game_frame()
            
            cv2.imshow('Space Shooter', frame)
            
            # 更新背景捲動
            self.background.update()
                
            key = cv2.waitKey(16) & 0xFF
            if key == ord('q') or key == ord('Q'):
                break
            elif key == ord('m') or key == ord('M'):
                self.reset_match()
                self.state = "START_MENU"
                self.ship_controller.reset()
                self.bullet_controller.bullets.clear()
                self.bullet_controller.last_fire_time = 0
                
        cv2.destroyAllWindows()

if __name__ == "__main__":
    game = Game()
    game.run()
