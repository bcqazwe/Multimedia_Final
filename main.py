import cv2
import numpy as np
import time
import os

from Background import BackgroundScroller
from Boss import BossController
from Health import HealthMeter, draw_health_bar, draw_segmented_health_bar
from item import ItemController
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
            max_bullets=40,
        )
        self.weapon_level = 1
        self._sync_weapon_level()
        self.item_controller = ItemController(self.DISPLAY_W, self.DISPLAY_H)

        self.boss_controller = BossController(self.DISPLAY_W, self.DISPLAY_H)
        # Boss has a large HP pool and is split evenly into three phases
        self.boss_health = HealthMeter(9999)
        self.player_health = HealthMeter(100)
        self.last_player_hit_ms = 0
        self.last_combat_check_ms = 0
        self.mouse_dragging = False
        self.drag_offset_x = 0
        self.drag_offset_y = 0
            
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
        # 使用背景快取的顯示尺寸畫面，避免每幀重新 resize
        display_frame = self.background.get_display_frame()

        # 2. 顯示 boss 與玩家船隻
        display_frame = self.boss_controller.draw_body(display_frame)
        self.overlay_image(display_frame, self.ship_display_img, self.ship_controller.x, self.ship_controller.y)
        display_frame = self.boss_controller.draw_attacks(display_frame)
        
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
        display_frame = self.background.get_display_frame()

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
        display_frame = self.background.get_display_frame()

        if not self.boss_health.is_empty():
            display_frame = self.boss_controller.draw_body(display_frame)
        display_frame = self.item_controller.draw(display_frame)
        display_frame = self.bullet_controller.draw(display_frame)
        self.overlay_image(display_frame, self.ship_display_img, self.ship_controller.x, self.ship_controller.y)
        if not self.boss_health.is_empty():
            display_frame = self.boss_controller.draw_attacks(display_frame)

        # show segmented bar with segments equal to one third of boss max HP
        segment_hp = max(1, self.boss_health.max_hp // 3)
        draw_segmented_health_bar(display_frame, self.boss_health.current_hp, self.boss_health.max_hp, 40, 20, segment_hp, 180, 24, (0, 0, 255), label="BOSS")
        draw_health_bar(display_frame, self.player_health.current_hp, self.player_health.max_hp, 40, self.DISPLAY_H - 44, self.DISPLAY_W - 80, 24, (0, 255, 0), label="PLAYER")
        return display_frame

    def reset_match(self):
        self.boss_controller.reset()
        self.boss_health = HealthMeter(9999)
        self.player_health = HealthMeter(100)
        self.ship_controller.reset()
        self.weapon_level = 1
        self._sync_weapon_level()
        self.bullet_controller.bullets.clear()
        self.bullet_controller.last_fire_time = 0
        self.item_controller.reset()
        self.last_player_hit_ms = 0
        self.last_combat_check_ms = 0
        self.mouse_dragging = False

    def _sync_weapon_level(self):
        level_to_shots = {1: 1, 2: 2, 3: 4}
        self.weapon_level = max(1, min(int(self.weapon_level), 3))
        self.bullet_controller.shot_count = level_to_shots[self.weapon_level]

    def upgrade_weapon(self):
        if self.weapon_level < 3:
            self.weapon_level += 1
            self._sync_weapon_level()

    def downgrade_weapon(self):
        if self.weapon_level > 1:
            self.weapon_level -= 1
            self._sync_weapon_level()

    def handle_items(self):
        ship_x = self.ship_controller.x
        ship_y = self.ship_controller.y
        ship_w = self.ship_controller.ship_w
        ship_h = self.ship_controller.ship_h
        ship_rect = (ship_x, ship_y, ship_x + ship_w, ship_y + ship_h)

        collected_kinds = self.item_controller.collect_player_items(ship_rect)

        for item_kind in collected_kinds:
            if item_kind == "upgrade":
                self.upgrade_weapon()
            elif item_kind == "heal":
                self.player_health.heal(20)

    def _get_ship_core_rect(self):
        ship_x = self.ship_controller.x
        ship_y = self.ship_controller.y
        ship_w = self.ship_controller.ship_w
        ship_h = self.ship_controller.ship_h

        core_w = max(10, int(ship_w * 0.28))
        core_h = max(10, int(ship_h * 0.28))
        core_x = ship_x + (ship_w - core_w) // 2
        core_y = ship_y + (ship_h - core_h) // 2
        return (core_x, core_y, core_x + core_w, core_y + core_h)

    def handle_combat(self, now_ms):
        if self.boss_health.is_empty() or self.player_health.is_empty():
            return

        combat_check_interval_ms = 32
        if now_ms - self.last_combat_check_ms < combat_check_interval_ms:
            return
        self.last_combat_check_ms = now_ms

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
            self.downgrade_weapon()
            self.last_player_hit_ms = now_ms

        ship_core_rect = self._get_ship_core_rect()

        if hasattr(self.boss_controller, 'attackA'):
            remaining_attack_a_bullets = []
            attack_a_hit_player = False
            core_left, core_top, core_right, core_bottom = ship_core_rect
            core_cx = (core_left + core_right) / 2.0
            core_cy = (core_top + core_bottom) / 2.0
            core_half_w = max(6, int((core_right - core_left) * 0.22))
            core_half_h = max(6, int((core_bottom - core_top) * 0.22))

            for bullet in self.boss_controller.attackA.bullets:
                bullet_w = bullet['img'].shape[1]
                bullet_h = bullet['img'].shape[0]
                bullet_cx = bullet['x'] + bullet_w / 2.0
                bullet_cy = bullet['y'] + bullet_h / 2.0
                hit_core = (
                    abs(bullet_cx - core_cx) <= core_half_w
                    and abs(bullet_cy - core_cy) <= core_half_h
                )

                if hit_core:
                    attack_a_hit_player = True
                else:
                    remaining_attack_a_bullets.append(bullet)

            self.boss_controller.attackA.bullets = remaining_attack_a_bullets

            if attack_a_hit_player and now_ms - self.last_player_hit_ms >= 500:
                self.player_health.take_damage(10)
                self.downgrade_weapon()
                self.last_player_hit_ms = now_ms

        if hasattr(self.boss_controller, 'attackC'):
            zone_hit_player = False
            core_left, core_top, core_right, core_bottom = ship_core_rect
            core_cx = (core_left + core_right) / 2.0
            core_cy = (core_top + core_bottom) / 2.0
            for zone in self.boss_controller.attackC.get_damage_zones():
                if isinstance(zone, dict):
                    zone_rect = (zone['x'], zone['y'], zone['x'] + zone['w'], zone['y'] + zone['h'])
                else:
                    zone_x, zone_y, zone_w, zone_h = zone
                    zone_rect = (zone_x, zone_y, zone_x + zone_w, zone_y + zone_h)
                hit_player = (
                    zone_rect[0] <= core_cx <= zone_rect[2]
                    and zone_rect[1] <= core_cy <= zone_rect[3]
                )
                if hit_player:
                    zone_hit_player = True
                    break

            if zone_hit_player and now_ms - self.last_player_hit_ms >= 500:
                self.player_health.take_damage(10)
                self.downgrade_weapon()
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
            elif self.state == "RUNNING":
                ship_rect = (self.ship_controller.x, self.ship_controller.y, self.ship_controller.ship_w, self.ship_controller.ship_h)
                self.mouse_dragging = True
                self.drag_offset_x = self.ship_controller.x - x
                self.drag_offset_y = self.ship_controller.y - y
        elif event == cv2.EVENT_LBUTTONUP:
            self.mouse_dragging = False
        elif event == cv2.EVENT_MOUSEMOVE and self.state == "RUNNING" and self.mouse_dragging:
            self.ship_controller.set_position(x + self.drag_offset_x, y + self.drag_offset_y)

    def update_input(self):
        if self.state != "RUNNING":
            return

        if not self.mouse_dragging:
            self.ship_controller.update()

    def run(self):
        cv2.namedWindow('Space Shooter')
        cv2.setMouseCallback('Space Shooter', self.handle_mouse)
        
        while True:
            now_ms = int(time.time() * 1000)

            if self.state in ("START_MENU", "RUNNING"):
                self.boss_controller.update(now_ms)
                boss_rect = self.boss_controller.get_rect()
                bhp = self.boss_health.current_hp
                max_hp = self.boss_health.max_hp
                # split boss HP into three equal phases
                third = max_hp / 3.0
                if bhp > 2 * third:
                    phase = 1
                elif bhp > third:
                    phase = 2
                else:
                    phase = 3

                player_center = (self.ship_controller.x + self.ship_controller.ship_w // 2, self.ship_controller.y + self.ship_controller.ship_h // 2)
                if hasattr(self.boss_controller, 'attackA'):
                    self.boss_controller.attackA.update(now_ms, boss_rect, phase=phase, player_pos=player_center)
                if hasattr(self.boss_controller, 'attackC'):
                    self.boss_controller.attackC.update(now_ms, boss_rect, phase=phase, player_pos=player_center)

            if self.state == "RUNNING":
                self.update_input()
                self.bullet_controller.update(now_ms)
                self.item_controller.update(now_ms)
                self.handle_items()
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
                self.item_controller.reset()
                self.mouse_dragging = False
                
        cv2.destroyAllWindows()

if __name__ == "__main__":
    game = Game()
    game.run()
