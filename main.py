import cv2
import numpy as np
import time
import os

from Background import BackgroundScroller
from Boss import BossController
from Health import HealthMeter, draw_health_bar
from item import ItemController
from control import ShipController, BulletController


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def asset_path(filename):
    return os.path.join(BASE_DIR, 'image', filename)


def streaming_path(filename):
    return os.path.join(BASE_DIR, 'streaming', filename)


def imread_unicode(path, flags=cv2.IMREAD_COLOR):
    data = np.fromfile(path, dtype=np.uint8)
    if data.size == 0:
        return None
    return cv2.imdecode(data, flags)


def ensure_bgr(image):
    if image is None:
        return None
    if len(image.shape) == 2:
        return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    if image.shape[2] == 4:
        return cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
    return image

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
        self.start_button_rect = [71, 421, 177, 45] # x, y, w, h in menu image pixels
        self.menu_button_rect = [self.DISPLAY_W // 2 - 120, self.DISPLAY_H // 2 + 80, 240, 60]
        self.intro_video_path = streaming_path('warning_start.mp4')
        self.intro_played = False
        self.menu_img = imread_unicode(asset_path('menu.png'), cv2.IMREAD_UNCHANGED)
        self.menu_img = ensure_bgr(self.menu_img)
        self.fail_img = imread_unicode(asset_path('fail.jpg'), cv2.IMREAD_UNCHANGED)
        self.fail_img = ensure_bgr(self.fail_img)
        self.boss_phase_hp = 3333
        self.dual_attack_mode = False
        self.fail_transition_started_ms = 0
        self.fail_transition_stage = None
        self.fail_transition_fade_out_ms = 420
        self.score = 0
        self.score_last_tick_ms = 0
        self.last_damage_taken_ms = 0
        self.multiplier = 1
        self.multiplier_next_award_ms = 0
        
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
        if self.menu_img is None:
            return np.zeros((self.DISPLAY_H, self.DISPLAY_W, 3), dtype=np.uint8)

        if self.menu_img.shape[1] != self.DISPLAY_W or self.menu_img.shape[0] != self.DISPLAY_H:
            return cv2.resize(self.menu_img, (self.DISPLAY_W, self.DISPLAY_H), interpolation=cv2.INTER_AREA)

        return self.menu_img.copy()

    def _menu_click_to_image_space(self, x, y):
        if self.menu_img is None:
            return x, y

        menu_h, menu_w = self.menu_img.shape[:2]
        image_x = int(x * menu_w / self.DISPLAY_W)
        image_y = int(y * menu_h / self.DISPLAY_H)
        return image_x, image_y

    def _fail_click_to_image_space(self, x, y):
        """將顯示器座標 (display) 映射回 fail 圖片的座標空間"""
        if self.fail_img is None:
            return x, y

        img_h, img_w = self.fail_img.shape[:2]
        image_x = int(x * img_w / self.DISPLAY_W)
        image_y = int(y * img_h / self.DISPLAY_H)
        return image_x, image_y

    def _start_button_clicked(self, x, y):
        image_x, image_y = self._menu_click_to_image_space(x, y)
        bx, by, bw, bh = self.start_button_rect
        return bx <= image_x <= bx + bw and by <= image_y <= by + bh

    def _fail_restart_clicked(self, x, y):
        image_x, image_y = self._fail_click_to_image_space(x, y)
        return 44 <= image_x <= 273 and 493 <= image_y <= 546

    def _fail_menu_clicked(self, x, y):
        image_x, image_y = self._fail_click_to_image_space(x, y)
        return 44 <= image_x <= 273 and 557 <= image_y <= 607

    def _enter_fail_transition(self, now_ms):
        if self.state not in ("FAIL_FADE_OUT", "FAIL_FADE_IN", "FAIL"):
            self.state = "FAIL_FADE_OUT"
            self.fail_transition_stage = "FADE_OUT"
            self.fail_transition_started_ms = now_ms

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

    def draw_fail_screen(self):
        if self.fail_img is None:
            return np.zeros((self.DISPLAY_H, self.DISPLAY_W, 3), dtype=np.uint8)

        if self.fail_img.shape[1] != self.DISPLAY_W or self.fail_img.shape[0] != self.DISPLAY_H:
            return cv2.resize(self.fail_img, (self.DISPLAY_W, self.DISPLAY_H), interpolation=cv2.INTER_AREA)

        return self.fail_img.copy()

    def draw_fail_transition(self, now_ms):
        base_frame = self.draw_game_frame()
        elapsed = now_ms - self.fail_transition_started_ms

        if self.fail_transition_stage == "FADE_OUT":
            progress = min(max(elapsed / max(1, self.fail_transition_fade_out_ms), 0.0), 1.0)
            return cv2.addWeighted(base_frame, 1.0 - progress, np.zeros_like(base_frame), progress, 0)

        return self.draw_fail_screen()

    def play_intro_video(self):
        if self.intro_played or not os.path.exists(self.intro_video_path):
            self.intro_played = True
            self.state = "START_MENU"
            return

        capture = cv2.VideoCapture(self.intro_video_path)
        if not capture.isOpened():
            self.intro_played = True
            self.state = "START_MENU"
            return

        cv2.namedWindow('Space Shooter')
        cv2.setMouseCallback('Space Shooter', lambda *args: None)

        try:
            while True:
                success, frame = capture.read()
                if not success:
                    break

                frame = cv2.resize(frame, (self.DISPLAY_W, self.DISPLAY_H), interpolation=cv2.INTER_AREA)
                cv2.imshow('Space Shooter', frame)

                key = cv2.waitKey(30) & 0xFF
                if key == ord('q') or key == ord('Q'):
                    self.state = "START_MENU"
                    self.intro_played = True
                    return

            self.intro_played = True
            self.state = "START_MENU"
        finally:
            capture.release()

    def draw_game_frame(self):
        display_frame = self.background.get_display_frame()

        if not self.boss_health.is_empty():
            display_frame = self.boss_controller.draw_body(display_frame)
        display_frame = self.item_controller.draw(display_frame)
        display_frame = self.bullet_controller.draw(display_frame)
        self.overlay_image(display_frame, self.ship_display_img, self.ship_controller.x, self.ship_controller.y)
        if not self.boss_health.is_empty():
            display_frame = self.boss_controller.draw_attacks(display_frame)

        phase, phase_hp_current, phase_hp_max, remaining_bars = self._get_boss_phase_info()
        draw_health_bar(
            display_frame,
            phase_hp_current,
            phase_hp_max,
            40,
            20,
            self.DISPLAY_W - 80,
            24,
            (0, 0, 255),
            label=f"BOSS X{remaining_bars}",
        )
        draw_health_bar(display_frame, self.player_health.current_hp, self.player_health.max_hp, 40, self.DISPLAY_H - 44, self.DISPLAY_W - 80, 24, (0, 255, 0), label="PLAYER")

        cv2.putText(display_frame, f"score: {self.score}", (20, 70), cv2.FONT_HERSHEY_DUPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(display_frame, f"multiple Rate: x{self.multiplier}", (20, 102), cv2.FONT_HERSHEY_DUPLEX, 0.7, (255, 255, 0), 2, cv2.LINE_AA)

        if self.dual_attack_mode and hasattr(self.boss_controller, 'attackA'):
            bullet_count = len(self.boss_controller.attackA.bullets)
            cv2.putText(display_frame, f"A bullets: {bullet_count}", (20, self.DISPLAY_H - 70), cv2.FONT_HERSHEY_DUPLEX, 0.7, (255, 255, 0), 2, cv2.LINE_AA)

        return display_frame

    def _get_boss_phase_info(self):
        phase_hp = max(1, int(self.boss_phase_hp))
        bhp = max(0, int(self.boss_health.current_hp))

        if bhp > phase_hp * 2:
            phase = 1
        elif bhp > phase_hp:
            phase = 2
        else:
            phase = 3

        if bhp <= 0:
            phase_hp_current = 0
        else:
            phase_hp_current = ((bhp - 1) % phase_hp) + 1

        remaining_bars = min(3, (bhp + phase_hp - 1) // phase_hp)

        return phase, phase_hp_current, phase_hp, remaining_bars

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
        self.score = 0
        self.score_last_tick_ms = 0
        self.last_damage_taken_ms = 0
        self.multiplier = 1
        self.multiplier_next_award_ms = 0

    def _sync_weapon_level(self):
        level_to_shots = {1: 1, 2: 2, 3: 4}
        self.weapon_level = max(1, min(int(self.weapon_level), 3))
        self.bullet_controller.shot_count = level_to_shots[self.weapon_level]

    def upgrade_weapon(self):
        if self.weapon_level < 3:
            self.weapon_level += 1
            self._sync_weapon_level()

    def refill_player_health(self):
        self.player_health.current_hp = self.player_health.max_hp

    def cheat_upgrade_weapon(self):
        self.upgrade_weapon()

    def _reset_multiplier_on_damage(self, now_ms):
        self.last_damage_taken_ms = now_ms
        self.multiplier = 1
        self.multiplier_next_award_ms = now_ms + 10000

    def _update_score_over_time(self, now_ms):
        if self.state != "RUNNING" or self.player_health.is_empty():
            return

        if self.score_last_tick_ms == 0:
            self.score_last_tick_ms = now_ms

        if self.multiplier_next_award_ms == 0:
            self.multiplier_next_award_ms = now_ms + 10000

        elapsed_ms = now_ms - self.score_last_tick_ms
        if elapsed_ms >= 1000:
            gained_seconds = elapsed_ms // 1000
            self.score += int(gained_seconds * 10 * self.multiplier)
            self.score_last_tick_ms += gained_seconds * 1000

        while now_ms >= self.multiplier_next_award_ms:
            self.multiplier += 1
            self.multiplier_next_award_ms += 10000

    def _add_score_for_damage(self):
        self.score += int(50 * self.multiplier)

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
        if self.boss_health.is_empty():
            return

        if self.player_health.is_empty():
            self._enter_fail_transition(now_ms)
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
                self._add_score_for_damage()
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
            self._reset_multiplier_on_damage(now_ms)

        if self.player_health.is_empty():
            self.state = "FAIL"
            return

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
                self._reset_multiplier_on_damage(now_ms)

            if self.player_health.is_empty():
                self._enter_fail_transition(now_ms)
                return

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
                self.player_health.take_damage(self.player_health.current_hp)
                self.last_player_hit_ms = now_ms
                self._reset_multiplier_on_damage(now_ms)

            if self.player_health.is_empty():
                self._enter_fail_transition(now_ms)
                return

        if self.boss_health.is_empty():
            self.state = "WIN"

    def handle_mouse(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            if self.state == "START_MENU":
                if self._start_button_clicked(x, y):
                    print("Game Starting...")
                    self.reset_match()
                    self.state = "RUNNING"
            elif self.state == "WIN":
                bx, by, bw, bh = self.menu_button_rect
                if bx <= x <= bx + bw and by <= y <= by + bh:
                    self.reset_match()
                    self.state = "START_MENU"
            elif self.state == "FAIL":
                if self._fail_restart_clicked(x, y):
                    self.reset_match()
                    self.state = "RUNNING"
                elif self._fail_menu_clicked(x, y):
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

        self.play_intro_video()
        cv2.setMouseCallback('Space Shooter', self.handle_mouse)
        
        while True:
            now_ms = int(time.time() * 1000)

            if self.state in ("START_MENU", "RUNNING"):
                self.boss_controller.update(now_ms)
                boss_rect = self.boss_controller.get_rect()
                phase, _, _, _ = self._get_boss_phase_info()

                player_center = (self.ship_controller.x + self.ship_controller.ship_w // 2, self.ship_controller.y + self.ship_controller.ship_h // 2)
                if hasattr(self.boss_controller, 'attackA'):
                    self.boss_controller.attackA.update(now_ms, boss_rect, phase=phase, player_pos=player_center)
                if hasattr(self.boss_controller, 'attackC'):
                    self.boss_controller.attackC.update(now_ms, boss_rect, phase=phase, player_pos=player_center)

                if self.dual_attack_mode and self.state == "RUNNING":
                    if hasattr(self.boss_controller, 'attackA'):
                        self.boss_controller.attackA.update(now_ms, boss_rect, phase=phase, player_pos=player_center)
                    if hasattr(self.boss_controller, 'attackC'):
                        self.boss_controller.attackC.update(now_ms, boss_rect, phase=phase, player_pos=player_center)

            if self.state == "RUNNING":
                self.update_input()
                self._update_score_over_time(now_ms)
                self.bullet_controller.update(now_ms)
                self.item_controller.update(now_ms)
                self.handle_items()
                self.handle_combat(now_ms)
            elif self.state == "FAIL_FADE_OUT":
                if now_ms - self.fail_transition_started_ms >= self.fail_transition_fade_out_ms:
                    self.fail_transition_stage = None
                    self.state = "FAIL"

            if self.state == "START_MENU":
                frame = self.draw_start_menu()
            elif self.state == "WIN":
                frame = self.draw_win_screen()
            elif self.state == "FAIL_FADE_OUT":
                frame = self.draw_fail_transition(now_ms)
            elif self.state == "FAIL":
                frame = self.draw_fail_screen()
            else:
                frame = self.draw_game_frame()
            
            cv2.imshow('Space Shooter', frame)
            
            # 更新背景捲動
            self.background.update()
                
            key = cv2.waitKey(16) & 0xFF
            if key == ord('p') or key == ord('P'):
                self.refill_player_health()
            elif key == ord('o') or key == ord('O'):
                self.cheat_upgrade_weapon()
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
            elif key == ord('s') or key == ord('S'):
                if self.state == "START_MENU":
                    self.reset_match()
                    self.state = "RUNNING"
            elif key == ord('2'):
                self.dual_attack_mode = not self.dual_attack_mode
                print(f"Dual attack mode: {self.dual_attack_mode}")
                
        cv2.destroyAllWindows()

if __name__ == "__main__":
    game = Game()
    game.run()
