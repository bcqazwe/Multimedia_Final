import os
import math
import random
import time

import cv2
import numpy as np


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def asset_path(filename):
    return os.path.join(BASE_DIR, 'image', filename)


def imread_unicode(path, flags=cv2.IMREAD_UNCHANGED):
    data = np.fromfile(path, dtype=np.uint8)
    if data.size == 0:
        return None
    return cv2.imdecode(data, flags)


def _overlay_image(background, overlay, x, y):
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


class BossAttackA:
    """彈幕家族 A：直線掃射、交叉扇形、高速鎖定彈

    使用 boss_bullet_straight.png (直線) 與 boss_bullet_dot.png (dot)
    """

    def __init__(self, display_w, display_h):
        self.display_w = display_w
        self.display_h = display_h

        straight = imread_unicode(asset_path('boss_bullet_straight.png'))
        dot = imread_unicode(asset_path('boss_bullet_dot.png'))
        if straight is None:
            straight = np.zeros((8, 8, 4), dtype=np.uint8)
            straight[:, :, :3] = (200, 200, 50)
            straight[:, :, 3] = 255
        if dot is None:
            dot = np.zeros((6, 6, 4), dtype=np.uint8)
            dot[:, :, :3] = (255, 80, 80)
            dot[:, :, 3] = 255

        # Slightly larger sizes for better visibility
        self.straight_img = cv2.resize(straight, (28, 52), interpolation=cv2.INTER_AREA)
        self.dot_img = cv2.resize(dot, (18, 18), interpolation=cv2.INTER_AREA)

        self.bullets = []

        # State machine for attack sequence
        self.state = 'idle'  # idle, windup, attack, cooldown
        self.state_enter_ms = 0
        self.current_attack = None
        self.attack_index = 0
        self.attack_fired = False

        # default sequences per phase (lists of attack types)
        self.phase_sequences = {
            1: ['straight'],
            2: ['straight', 'cross'],
            3: ['cross', 'homing', 'straight'],
        }

        # per-attack configuration
        self.attack_configs = {
            'straight': {'windup': 450, 'duration': 260, 'cooldown': 1200, 'interval': 160},
            'cross': {'windup': 400, 'duration': 700, 'cooldown': 400, 'interval': 140},
            'homing': {'windup': 200, 'duration': 500, 'cooldown': 300, 'interval': 120},
        }

        # runtime timers for spawning during attack
        self.last_spawn = 0

    def reset(self):
        self.bullets = []
        self.state = 'idle'
        self.state_enter_ms = 0
        self.current_attack = None
        self.attack_index = 0
        self.attack_fired = False
        self.last_spawn = 0

    def update(self, now_ms, boss_rect, phase=1, player_pos=None):
        boss_x, boss_y, boss_w, boss_h = boss_rect
        boss_cx = boss_x + boss_w // 2
        boss_cy = boss_y + boss_h // 2

        seq = self.phase_sequences.get(phase, ['straight'])

        # state transitions
        if self.state == 'idle':
            # start next attack
            self.current_attack = seq[self.attack_index % len(seq)]
            self.state = 'windup'
            self.state_enter_ms = now_ms
            self.last_spawn = now_ms
            self.attack_fired = False
            # debug
            print(f"BossAttackA: enter windup {self.current_attack} phase={phase} time={now_ms}")
            return

        config = self.attack_configs.get(self.current_attack, self.attack_configs['straight'])
        elapsed = now_ms - self.state_enter_ms

        if self.state == 'windup':
            if elapsed >= config['windup']:
                self.state = 'attack'
                self.state_enter_ms = now_ms
                self.last_spawn = now_ms
                print(f"BossAttackA: start attack {self.current_attack} phase={phase} time={now_ms}")

        elif self.state == 'attack':
            # spawn at configured interval (may use phase to scale intensity)
            spawn_interval = max(40, int(config['interval'] / max(1, phase)))
            should_spawn = (phase == 1 and not self.attack_fired) or (phase > 1 and now_ms - self.last_spawn >= spawn_interval)
            if should_spawn:
                # spawn according to attack type
                if self.current_attack == 'straight':
                    self._spawn_straight(boss_x, boss_y, boss_w, boss_h, phase)
                elif self.current_attack == 'cross':
                    self._spawn_cross_fan(boss_x, boss_y, boss_w, boss_h, phase)
                elif self.current_attack == 'homing':
                    self._spawn_homing(boss_cx, boss_cy, player_pos, phase)
                self.last_spawn = now_ms
                self.attack_fired = True

            if elapsed >= config['duration']:
                self.state = 'cooldown'
                self.state_enter_ms = now_ms
                print(f"BossAttackA: enter cooldown {self.current_attack} phase={phase} time={now_ms}")

        elif self.state == 'cooldown':
            if elapsed >= config['cooldown']:
                # advance to next attack
                self.attack_index += 1
                self.current_attack = None
                self.state = 'idle'
                self.state_enter_ms = now_ms
                self.attack_fired = False
                print(f"BossAttackA: cooldown end, next index={self.attack_index} time={now_ms}")

        # update bullets positions
        for b in self.bullets:
            b['x'] += b['vx']
            b['y'] += b['vy']

        # cull off-screen
        self.bullets = [b for b in self.bullets if -64 < b['x'] < self.display_w + 64 and -64 < b['y'] < self.display_h + 64]

    def draw(self, frame):
        for b in self.bullets:
            img = b.get('img')
            if img is None:
                continue
            frame = _overlay_image(frame, img, int(b['x']), int(b['y']))
        return frame

    def _spawn_straight(self, boss_x, boss_y, boss_w, boss_h, phase):
        # spawn N bullets across boss width, shoot down
        counts = {1: 3, 2: 5, 3: 7}
        n = counts.get(phase, 3)
        spacing = max(28, boss_w // max(1, n - 1))
        speed = 3 + phase * 2
        for i in range(n):
            x = boss_x + (boss_w - self.straight_img.shape[1]) // 2 + int((i - (n - 1) / 2) * spacing)
            y = boss_y + boss_h
            self.bullets.append({'x': x, 'y': y, 'vx': 0, 'vy': speed, 'img': self.straight_img})

    def _spawn_cross_fan(self, boss_x, boss_y, boss_w, boss_h, phase):
        # spawn two opposite fans from left and right
        per_fan = {1: 5, 2: 7, 3: 9}[phase]
        speed = 4 + phase * 2
        fan_spread = math.radians(92)
        for side in (-1, 1):
            cx = boss_x + (0 if side < 0 else boss_w)
            cy = boss_y + boss_h
            for i in range(per_fan):
                t = i / max(1, per_fan - 1)
                angle = (-fan_spread/2) + t * fan_spread
                # flip angle for right side
                if side > 0:
                    angle = math.pi - angle
                vx = math.cos(angle) * speed
                vy = math.sin(angle) * speed
                self.bullets.append({'x': cx, 'y': cy, 'vx': vx, 'vy': vy, 'img': self.dot_img})

    def _spawn_homing(self, boss_cx, boss_cy, player_pos, phase):
        # spawn fast small dots that head toward player_pos
        if player_pos is None:
            # fallback: shoot downward
            vx, vy = 0, 8 + phase * 2
            print(f"BossAttackA: homing fallback spawn speed={vy}")
            self.bullets.append({'x': boss_cx, 'y': boss_cy, 'vx': vx, 'vy': vy, 'img': self.dot_img})
            return

        px, py = player_pos
        dx = px - boss_cx
        dy = py - boss_cy
        dist = math.hypot(dx, dy) or 1.0
        speed = 8 + phase * 3
        vx = dx / dist * speed
        vy = dy / dist * speed
        # spawn a small burst
        for off in (-28, 0, 28):
            self.bullets.append({'x': boss_cx + off, 'y': boss_cy, 'vx': vx, 'vy': vy, 'img': self.dot_img})


class BossAttackC:
    """垂直導彈攻擊：5 秒前搖、紅線預警、lockdown 警示、rocket 下降。"""

    def __init__(self, display_w, display_h):
        self.display_w = display_w
        self.display_h = display_h

        lockdown = imread_unicode(asset_path('lockdown.png'))
        if lockdown is None:
            lockdown = np.zeros((24, 24, 4), dtype=np.uint8)
            lockdown[:, :, :3] = (255, 40, 40)
            lockdown[:, :, 3] = 255

        rocket = imread_unicode(asset_path('rocket.png'))
        if rocket is None:
            rocket = np.zeros((40, 80, 4), dtype=np.uint8)
            rocket[:, :, :3] = (255, 170, 40)
            rocket[:, :, 3] = 255

        if lockdown.shape[2] == 3:
            alpha = np.full((lockdown.shape[0], lockdown.shape[1], 1), 255, dtype=np.uint8)
            lockdown = np.concatenate([lockdown, alpha], axis=2)
        if rocket.shape[2] == 3:
            alpha = np.full((rocket.shape[0], rocket.shape[1], 1), 255, dtype=np.uint8)
            rocket = np.concatenate([rocket, alpha], axis=2)

        self.warning_img = cv2.resize(lockdown, (90, 90), interpolation=cv2.INTER_AREA)
        self.rocket_img = cv2.resize(rocket, (46, 92), interpolation=cv2.INTER_AREA)

        self.damage_zones = []
        self.warning_line_x = None
        self.warning_icon = None
        self.active_rocket = None

        self.state = 'idle'  # idle, windup, attack, cooldown
        self.state_enter_ms = 0
        self.cycle_start_ms = 0
        self.current_attack = None
        self.attack_index = 0

        self.phase_sequences = {
            1: ['vertical_missile'],
            2: ['vertical_missile'],
            3: ['vertical_missile'],
        }

        self.attack_configs = {
            'vertical_missile': {'windup': 5000, 'cycle': 20000, 'speed': 30},
        }

    def reset(self):
        self.damage_zones = []
        self.warning_line_x = None
        self.warning_icon = None
        self.active_rocket = None
        self.state = 'idle'
        self.state_enter_ms = 0
        self.cycle_start_ms = 0
        self.current_attack = None
        self.attack_index = 0

    def update(self, now_ms, boss_rect, phase=1, player_pos=None):
        seq = self.phase_sequences.get(phase, ['vertical_missile'])
        config = self.attack_configs.get('vertical_missile')

        if self.state == 'idle':
            self.current_attack = seq[self.attack_index % len(seq)]
            self.state = 'windup'
            self.state_enter_ms = now_ms
            self.cycle_start_ms = now_ms
            self.damage_zones = []
            self.active_rocket = None
            self.warning_line_x = self._pick_telegraph_x(boss_rect, player_pos)
            self.warning_icon = self._build_warning_icon(self.warning_line_x)
            print(f"BossAttackC: enter windup {self.current_attack} phase={phase} time={now_ms}")
            return

        elapsed = now_ms - self.state_enter_ms
        cycle_elapsed = now_ms - self.cycle_start_ms

        if self.state == 'windup':
            if elapsed >= config['windup']:
                self.state = 'attack'
                self.state_enter_ms = now_ms

                rocket_w = self.rocket_img.shape[1]
                rocket_h = self.rocket_img.shape[0]
                rocket_x = max(0, min(self.warning_line_x - rocket_w // 2, self.display_w - rocket_w))
                self.active_rocket = {
                    'x': float(rocket_x),
                    'y': float(-rocket_h),
                    'vx': 0.0,
                    'vy': float(config['speed']),
                    'img': self.rocket_img,
                }
                self.warning_line_x = None
                self.warning_icon = None
                self.damage_zones = [self._rocket_to_zone(self.active_rocket)]
                print(f"BossAttackC: start attack {self.current_attack} phase={phase} time={now_ms}")

        elif self.state == 'attack':
            if self.active_rocket is not None:
                self.active_rocket['x'] += self.active_rocket['vx']
                self.active_rocket['y'] += self.active_rocket['vy']
                self.damage_zones = [self._rocket_to_zone(self.active_rocket)]

                if self.active_rocket['y'] > self.display_h:
                    self.active_rocket = None
                    self.damage_zones = []
                    self.state = 'cooldown'
                    self.state_enter_ms = now_ms
                    print(f"BossAttackC: rocket finished, enter cooldown phase={phase} time={now_ms}")

            if cycle_elapsed >= config['cycle']:
                self.active_rocket = None
                self.damage_zones = []
                self.state = 'cooldown'
                self.state_enter_ms = now_ms

        elif self.state == 'cooldown':
            if cycle_elapsed >= config['cycle']:
                self.attack_index += 1
                self.current_attack = None
                self.state = 'idle'
                self.state_enter_ms = now_ms
                self.warning_line_x = None
                self.warning_icon = None
                self.active_rocket = None
                self.damage_zones = []
                print(f"BossAttackC: cooldown end next index={self.attack_index} time={now_ms}")

    def draw(self, frame):
        if self.warning_line_x is not None:
            line_x = int(self.warning_line_x)
            cv2.line(frame, (line_x, 0), (line_x, self.display_h - 1), (0, 0, 255), 4)

        if self.warning_icon is not None:
            frame = _overlay_image(frame, self.warning_icon['img'], int(self.warning_icon['x']), int(self.warning_icon['y']))

        if self.active_rocket is not None:
            frame = _overlay_image(frame, self.active_rocket['img'], int(self.active_rocket['x']), int(self.active_rocket['y']))

        return frame

    def get_damage_zones(self):
        return list(self.damage_zones)

    def _pick_telegraph_x(self, boss_rect, player_pos):
        if player_pos is not None:
            return max(0, min(int(player_pos[0]), self.display_w - 1))

        boss_x, boss_y, boss_w, boss_h = boss_rect
        _ = boss_y, boss_h
        return max(0, min(int(boss_x + boss_w // 2), self.display_w - 1))

    def _build_warning_icon(self, line_x):
        img_w = self.warning_img.shape[1]
        img_h = self.warning_img.shape[0]
        warning_x = max(0, min(int(line_x - img_w // 2), self.display_w - img_w))
        warning_y = max(0, min(self.display_h // 4 - img_h // 2, self.display_h - img_h))
        return {'x': warning_x, 'y': warning_y, 'img': self.warning_img}

    def _rocket_to_zone(self, rocket):
        return {
            'x': int(rocket['x']),
            'y': int(rocket['y']),
            'w': int(rocket['img'].shape[1]),
            'h': int(rocket['img'].shape[0]),
        }
