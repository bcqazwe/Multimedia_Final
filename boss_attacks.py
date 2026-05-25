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
        self.ui_scale = max(1, int(round(min(self.display_w / 320.0, self.display_h / 640.0))))
        self.pixel_scale = self.ui_scale / 2.0

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
        self.straight_img = cv2.resize(
            straight,
            (max(1, int(round(14 * self.ui_scale))), max(1, int(round(26 * self.ui_scale)))),
            interpolation=cv2.INTER_AREA,
        )
        self.dot_img = cv2.resize(
            dot,
            (max(1, int(round(12 * self.ui_scale))), max(1, int(round(12 * self.ui_scale)))),
            interpolation=cv2.INTER_AREA,
        )
        self.straight_rgb = self.straight_img[:, :, :3]
        self.straight_mask = self.straight_img[:, :, 3:] / 255.0
        self.dot_rgb = self.dot_img[:, :, :3]
        self.dot_mask = self.dot_img[:, :, 3:] / 255.0

        self.bullets = []
        # bullet object pool
        self._pool = []
        for _ in range(256):
            self._pool.append({'x': 0.0, 'y': 0.0, 'vx': 0.0, 'vy': 0.0, 'img': self.dot_img})

        # State machine for attack sequence
        self.state = 'idle'  # idle, windup, attack, cooldown
        self.state_enter_ms = 0
        self.current_attack = None
        self.attack_index = 0
        self.attack_fired = False

        # attack order is shared by all phases; phase only changes parameters
        self.attack_order = ['straight', 'cross', 'homing', 'bidir_bounce']
        self.phase_sequences = {
            1: list(self.attack_order),
            2: list(self.attack_order),
            3: list(self.attack_order),
        }

        # phase tuning only affects speed/angle/duration feel, not which attacks exist
        self.phase_profiles = {
            1: {'speed_scale': 0.90, 'angle_scale': 1.15, 'damage_scale': 1.00},
            2: {'speed_scale': 1.00, 'angle_scale': 1.00, 'damage_scale': 1.20},
            3: {'speed_scale': 1.15, 'angle_scale': 0.82, 'damage_scale': 1.45},
        }

        # per-attack configuration
        self.attack_configs = {
            'straight': {'windup': 450, 'duration': 300, 'cooldown': 1100, 'interval': 120},
            'cross': {'windup': 400, 'duration': 780, 'cooldown': 360, 'interval': 100},
            'homing': {'windup': 200, 'duration': 560, 'cooldown': 260, 'interval': 90},
            # bidir_bounce: shoots left and right; bullets reflect on side boundaries
            # two lateral lanes keep firing for 3 seconds so the pressure window feels sustained
            'bidir_bounce': {'windup': 300, 'duration': 3000, 'cooldown': 400, 'interval': 110, 'max_bounces': 2, 'loss_factor': 0.96},
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
        profile = self.phase_profiles.get(phase, self.phase_profiles[1])

        # state transitions
        if self.state == 'idle':
            # start next attack
            self.current_attack = seq[self.attack_index % len(seq)]
            self.state = 'windup'
            self.state_enter_ms = now_ms
            self.last_spawn = now_ms
            self.attack_fired = False
            # debug
            #print(f"BossAttackA: enter windup {self.current_attack} phase={phase} time={now_ms}")
            return

        config = self.attack_configs.get(self.current_attack, self.attack_configs['straight'])
        elapsed = now_ms - self.state_enter_ms

        if self.state == 'windup':
            if elapsed >= config['windup']:
                self.state = 'attack'
                self.state_enter_ms = now_ms
                self.last_spawn = now_ms
                #print(f"BossAttackA: start attack {self.current_attack} phase={phase} time={now_ms}")

        elif self.state == 'attack':
            # spawn at configured interval (may use phase to scale intensity)
            # slightly increase attack frequency (interval scale < 1 -> faster)
            phase_interval_scale = {1: 0.95, 2: 0.80, 3: 0.65}
            spawn_interval = max(28, int(config['interval'] * phase_interval_scale.get(phase, 1.0)))
            should_spawn = now_ms - self.last_spawn >= spawn_interval
            if should_spawn:
                # spawn according to attack type
                if self.current_attack == 'straight':
                    self._spawn_straight(boss_x, boss_y, boss_w, boss_h, phase, profile)
                elif self.current_attack == 'cross':
                    self._spawn_cross_fan(boss_x, boss_y, boss_w, boss_h, phase, profile)
                elif self.current_attack == 'homing':
                    self._spawn_homing(boss_cx, boss_cy, player_pos, phase, profile)
                elif self.current_attack == 'bidir_bounce':
                    self._spawn_bidir_bounce(boss_x, boss_y, boss_w, boss_h, phase, profile)
                self.last_spawn = now_ms
                self.attack_fired = True

            if elapsed >= config['duration']:
                self.state = 'cooldown'
                self.state_enter_ms = now_ms
                #print(f"BossAttackA: enter cooldown {self.current_attack} phase={phase} time={now_ms}")

        elif self.state == 'cooldown':
            if elapsed >= config['cooldown']:
                # advance to next attack
                self.attack_index += 1
                self.current_attack = None
                self.state = 'idle'
                self.state_enter_ms = now_ms
                self.attack_fired = False
                #print(f"BossAttackA: cooldown end, next index={self.attack_index} time={now_ms}")

        # update bullets positions
        for b in self.bullets:
            b['x'] += b['vx']
            b['y'] += b['vy']

        # cull off-screen early; handle horizontal reflection if bullet still allowed to bounce
        margin = max(24, int(round(12 * self.ui_scale)))
        keep = []
        for b in self.bullets:
            bw = b.get('img').shape[1] if b.get('img') is not None else 8
            bh = b.get('img').shape[0] if b.get('img') is not None else 8

            # horizontal boundary reflection
            bx = b['x']
            by = b['y']
            bounces = b.get('bounces', 0)
            max_bounces = b.get('max_bounces', 0)
            loss = b.get('loss_factor', 0.96)

            reflected = False
            # left side
            if bx < 0:
                if bounces < max_bounces:
                    # clamp and reflect
                    b['x'] = 0.0
                    b['vx'] = -b['vx'] * loss
                    b['bounces'] = bounces + 1
                    reflected = True
                else:
                    # no more bounces, let it be culled below
                    pass

            # right side
            if bx + bw > self.display_w:
                if bounces < max_bounces:
                    b['x'] = float(max(0, self.display_w - bw))
                    b['vx'] = -b['vx'] * loss
                    b['bounces'] = bounces + 1
                    reflected = True
                else:
                    pass

            # if reflected or still within extended margin, keep; else recycle
            if reflected or (-margin < b['x'] < self.display_w + margin and -margin < b['y'] < self.display_h + margin):
                keep.append(b)
            else:
                if len(self._pool) < 1024:
                    self._pool.append({'x': 0.0, 'y': 0.0, 'vx': 0.0, 'vy': 0.0, 'img': b.get('img', self.dot_img)})
        self.bullets = keep

    def _spawn_bidir_bounce(self, boss_x, boss_y, boss_w, boss_h, phase, profile=None):
        # spawn one left lane and one right lane; repeated spawns over time form two long lines
        profile = profile or self.phase_profiles.get(phase, self.phase_profiles[1])
        speed = {1: 12, 2: 18, 3: 26}.get(phase, 12) * profile['speed_scale'] * self.pixel_scale
        max_bounces = {1: 1, 2: 2, 3: 3}.get(phase, 1)
        loss = {1: 0.98, 2: 0.96, 3: 0.94}.get(phase, 0.96)
        vertical_scale = {1: 0.55, 2: 0.40, 3: 0.25}.get(phase, 0.55) * profile['angle_scale']
        x = boss_x + (boss_w - self.dot_img.shape[1]) // 2
        y = boss_y + boss_h

        # left-going lane
        vx_l = -abs(speed * 0.75)
        vy_l = speed * vertical_scale
        if self._pool:
            b = self._pool.pop()
            b['x'] = float(x)
            b['y'] = float(y)
            b['vx'] = float(vx_l)
            b['vy'] = float(vy_l)
            b['img'] = self.dot_img
            b['bounces'] = 0
            b['max_bounces'] = max_bounces
            b['loss_factor'] = loss
            self.bullets.append(b)
        else:
            self.bullets.append({'x': float(x), 'y': float(y), 'vx': float(vx_l), 'vy': float(vy_l), 'img': self.dot_img, 'bounces': 0, 'max_bounces': max_bounces, 'loss_factor': loss})

        # right-going lane
        vx_r = abs(speed * 0.75)
        vy_r = speed * vertical_scale
        if self._pool:
            b = self._pool.pop()
            b['x'] = float(x)
            b['y'] = float(y)
            b['vx'] = float(vx_r)
            b['vy'] = float(vy_r)
            b['img'] = self.dot_img
            b['bounces'] = 0
            b['max_bounces'] = max_bounces
            b['loss_factor'] = loss
            self.bullets.append(b)
        else:
            self.bullets.append({'x': float(x), 'y': float(y), 'vx': float(vx_r), 'vy': float(vy_r), 'img': self.dot_img, 'bounces': 0, 'max_bounces': max_bounces, 'loss_factor': loss})

    def draw(self, frame):
        for b in self.bullets:
            img = b.get('img')
            if img is None:
                continue
            if img is self.straight_img:
                frame = self._overlay_cached_image(frame, self.straight_rgb, self.straight_mask, int(b['x']), int(b['y']))
            else:
                frame = self._overlay_cached_image(frame, self.dot_rgb, self.dot_mask, int(b['x']), int(b['y']))
        return frame

    def _overlay_cached_image(self, background, overlay_img, overlay_mask, x, y):
        h, w = overlay_mask.shape[:2]
        if x >= background.shape[1] or y >= background.shape[0] or x + w <= 0 or y + h <= 0:
            return background

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

        overlay_f = overlay_roi.astype('float32')
        roi_f = roi.astype('float32')
        mask_f = mask_roi.astype('float32')
        # ensure mask has same number of channels as overlay
        if mask_f.ndim == 2:
            mask_f = mask_f[:, :, None]
        if mask_f.shape[2] != overlay_f.shape[2]:
            mask_f = np.repeat(mask_f, overlay_f.shape[2], axis=2)
        inv_mask_f = 1.0 - mask_f

        fg = cv2.multiply(overlay_f, mask_f)
        bg = cv2.multiply(roi_f, inv_mask_f)
        res = cv2.add(fg, bg)
        background[y1:y2, x1:x2] = res.astype('uint8')
        return background

    def _spawn_straight(self, boss_x, boss_y, boss_w, boss_h, phase, profile=None):
        # spawn N bullets across boss width, shoot down
        profile = profile or self.phase_profiles.get(phase, self.phase_profiles[1])
        counts = {1: 4, 2: 7, 3: 9}
        n = counts.get(phase, 3)
        spacing = max(28, boss_w // max(1, n - 1))
        # increased speeds (approx 1.5x) while keeping spawn counts unchanged
        speed = {1: 12, 2: 16, 3: 21}.get(phase, 12) * profile['speed_scale'] * self.pixel_scale
        for i in range(n):
            x = boss_x + (boss_w - self.straight_img.shape[1]) // 2 + int((i - (n - 1) / 2) * spacing)
            y = boss_y + boss_h
            if self._pool:
                b = self._pool.pop()
                b['x'] = float(x)
                b['y'] = float(y)
                b['vx'] = 0.0
                b['vy'] = float(speed)
                b['img'] = self.straight_img
                self.bullets.append(b)
            else:
                self.bullets.append({'x': float(x), 'y': float(y), 'vx': 0.0, 'vy': float(speed), 'img': self.straight_img})

    def _spawn_cross_fan(self, boss_x, boss_y, boss_w, boss_h, phase, profile=None):
        # spawn two opposite fans from left and right
        profile = profile or self.phase_profiles.get(phase, self.phase_profiles[1])
        per_fan = {1: 7, 2: 10, 3: 12}[phase]
        # increased speeds for fan bullets
        speed = {1: 12, 2: 16, 3: 21}[phase] * profile['speed_scale'] * self.pixel_scale
        fan_spread = math.radians(92) * profile['angle_scale']
        fan_bias = math.radians(18) * profile['angle_scale']
        for side in (-1, 1):
            cx = boss_x + (0 if side < 0 else boss_w)
            cy = boss_y + boss_h
            for i in range(per_fan):
                t = i / max(1, per_fan - 1)
                angle = (-fan_spread / 2) + t * fan_spread + fan_bias
                # flip angle for right side
                if side > 0:
                    angle = math.pi - angle
                vx = math.cos(angle) * speed
                vy = math.sin(angle) * speed
                if self._pool:
                    b = self._pool.pop()
                    b['x'] = float(cx)
                    b['y'] = float(cy)
                    b['vx'] = float(vx)
                    b['vy'] = float(vy)
                    b['img'] = self.dot_img
                    self.bullets.append(b)
                else:
                    self.bullets.append({'x': float(cx), 'y': float(cy), 'vx': float(vx), 'vy': float(vy), 'img': self.dot_img})

    def _spawn_homing(self, boss_cx, boss_cy, player_pos, phase, profile=None):
        # spawn fast small dots that head toward player_pos
        profile = profile or self.phase_profiles.get(phase, self.phase_profiles[1])
        if player_pos is None:
            # fallback: shoot downward with increased speed
            vy = {1: 19, 2: 24, 3: 28}.get(phase, 19) * profile['speed_scale'] * self.pixel_scale
            vx = 0
            self.bullets.append({'x': boss_cx, 'y': boss_cy, 'vx': vx, 'vy': vy, 'img': self.dot_img})
            return

        px, py = player_pos
        dx = px - boss_cx
        dy = py - boss_cy
        dist = math.hypot(dx, dy) or 1.0
        # increased homing speeds
        speed = {1: 19, 2: 24, 3: 28}.get(phase, 19) * profile['speed_scale'] * self.pixel_scale
        vx = dx / dist * speed
        vy = dy / dist * speed
        # spawn a small burst
        for off in (-40, -20, 0, 20, 40):
            self.bullets.append({'x': boss_cx + off, 'y': boss_cy, 'vx': vx, 'vy': vy, 'img': self.dot_img})


class BossAttackC:
    """垂直導彈攻擊：5 秒前搖、紅線預警、lockdown 警示、rocket 下降。"""

    def __init__(self, display_w, display_h):
        self.display_w = display_w
        self.display_h = display_h
        self.ui_scale = max(1, int(round(min(self.display_w / 320.0, self.display_h / 640.0))))
        self.pixel_scale = self.ui_scale / 2.0

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

        self.warning_img = cv2.resize(
            lockdown,
            (max(1, int(round(45 * self.ui_scale))), max(1, int(round(45 * self.ui_scale)))),
            interpolation=cv2.INTER_AREA,
        )
        self.rocket_img = cv2.resize(
            rocket,
            (max(1, int(round(23 * self.ui_scale))), max(1, int(round(46 * self.ui_scale)))),
            interpolation=cv2.INTER_AREA,
        )
        self.warning_rgb = self.warning_img[:, :, :3]
        self.warning_mask = self.warning_img[:, :, 3:] / 255.0
        self.rocket_rgb = self.rocket_img[:, :, :3]
        self.rocket_mask = self.rocket_img[:, :, 3:] / 255.0

        self.damage_zones = []
        self.warning_line_x = None
        self.warning_icon = None
        self.active_rocket = None

        self.state = 'idle'  # idle, windup, attack, cooldown
        self.state_enter_ms = 0
        self.current_attack = None
        self.attack_index = 0

        self.phase_sequences = {
            1: ['vertical_missile'],
            2: ['vertical_missile'],
            3: ['vertical_missile'],
        }

        self.attack_configs = {
            'vertical_missile': {'speed': 36},
        }

        # phase timing (ms): phase 2/3 follow requested harder pacing.
        # phase 1 keeps original feel (5s telegraph + long cooldown).
        self.phase_timing = {
            # phase timings in milliseconds
            # phase1: 1s windup, 3s cooldown
            1: {'windup': 1000, 'cooldown': 3000},
            # phase2: 500ms windup, 1s cooldown
            2: {'windup': 500, 'cooldown': 1000},
            # phase3: 300ms windup, 500ms cooldown
            3: {'windup': 300, 'cooldown': 500},
        }

    def reset(self):
        self.damage_zones = []
        self.warning_line_x = None
        self.warning_icon = None
        self.active_rocket = None
        self.state = 'idle'
        self.state_enter_ms = 0
        self.current_attack = None
        self.attack_index = 0

    def update(self, now_ms, boss_rect, phase=1, player_pos=None):
        seq = self.phase_sequences.get(phase, ['vertical_missile'])
        config = self.attack_configs.get('vertical_missile')
        timing = self.phase_timing.get(phase, self.phase_timing[1])

        if self.state == 'idle':
            self.current_attack = seq[self.attack_index % len(seq)]
            self.state = 'windup'
            self.state_enter_ms = now_ms
            self.damage_zones = []
            self.active_rocket = None
            self.warning_line_x = self._pick_telegraph_x(boss_rect, player_pos)
            self.warning_icon = self._build_warning_icon(self.warning_line_x)
            #print(f"BossAttackC: enter windup {self.current_attack} phase={phase} time={now_ms}")
            return

        elapsed = now_ms - self.state_enter_ms

        if self.state == 'windup':
            if elapsed >= timing['windup']:
                self.state = 'attack'
                self.state_enter_ms = now_ms

                rocket_w = self.rocket_img.shape[1]
                rocket_h = self.rocket_img.shape[0]
                rocket_x = max(0, min(self.warning_line_x - rocket_w // 2, self.display_w - rocket_w))
                speed = float(config['speed'] + phase * 4) * self.pixel_scale
                self.active_rocket = {
                    'x': float(rocket_x),
                    'y': float(-rocket_h),
                    'vx': 0.0,
                    'vy': speed,
                    'img': self.rocket_img,
                }
                self.warning_line_x = None
                self.warning_icon = None
                self.damage_zones = [self._rocket_to_zone(self.active_rocket)]
                #print(f"BossAttackC: start attack {self.current_attack} phase={phase} time={now_ms}")

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
                    #print(f"BossAttackC: rocket finished, enter cooldown phase={phase} time={now_ms}")

        elif self.state == 'cooldown':
            if elapsed >= timing['cooldown']:
                self.attack_index += 1
                self.current_attack = None
                self.state = 'idle'
                self.state_enter_ms = now_ms
                self.warning_line_x = None
                self.warning_icon = None
                self.active_rocket = None
                self.damage_zones = []
                #print(f"BossAttackC: cooldown end next index={self.attack_index} time={now_ms}")

    def draw(self, frame):
        if self.warning_line_x is not None:
            line_x = int(self.warning_line_x)
            cv2.line(frame, (line_x, 0), (line_x, self.display_h - 1), (0, 0, 255), 4)

        if self.warning_icon is not None:
            frame = self._overlay_cached_image(frame, self.warning_rgb, self.warning_mask, int(self.warning_icon['x']), int(self.warning_icon['y']))

        if self.active_rocket is not None:
            frame = self._overlay_cached_image(frame, self.rocket_rgb, self.rocket_mask, int(self.active_rocket['x']), int(self.active_rocket['y']))

        return frame

    def _overlay_cached_image(self, background, overlay_img, overlay_mask, x, y):
        h, w = overlay_mask.shape[:2]
        if x >= background.shape[1] or y >= background.shape[0] or x + w <= 0 or y + h <= 0:
            return background

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

        overlay_f = overlay_roi.astype('float32')
        roi_f = roi.astype('float32')
        mask_f = mask_roi.astype('float32')
        # ensure mask has same number of channels as overlay
        if mask_f.ndim == 2:
            mask_f = mask_f[:, :, None]
        if mask_f.shape[2] != overlay_f.shape[2]:
            mask_f = np.repeat(mask_f, overlay_f.shape[2], axis=2)
        inv_mask_f = 1.0 - mask_f

        fg = cv2.multiply(overlay_f, mask_f)
        bg = cv2.multiply(roi_f, inv_mask_f)
        res = cv2.add(fg, bg)
        background[y1:y2, x1:x2] = res.astype('uint8')
        return background

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
