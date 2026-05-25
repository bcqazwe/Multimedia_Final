import cv2
import numpy as np
import os
import time
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont


def imread_unicode(path, flags=cv2.IMREAD_COLOR):
    try:
        data = np.fromfile(path, dtype=np.uint8)
        if data.size == 0:
            return None
        return cv2.imdecode(data, flags)
    except Exception:
        return None


PHASE_TRANSITION_STATE = "PHASE_GLITCH"
SOFT_PULSE_TRANSITION_STATE = "PHASE_PULSE"


@lru_cache(maxsize=8)
def _load_chinese_font(font_size):
    font_candidates = [
        r"C:\\Windows\\Fonts\\msjh.ttc",
        r"C:\\Windows\\Fonts\\msjhbd.ttc",
        r"C:\\Windows\\Fonts\\msyh.ttc",
        r"C:\\Windows\\Fonts\\simhei.ttf",
    ]

    for font_path in font_candidates:
        if os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, font_size)
            except Exception:
                continue

    return ImageFont.load_default()


def draw_chinese_text(frame, text, org, font_scale=1.0, color=(255, 255, 255), thickness=2, line_spacing=6):
    if frame is None:
        return frame

    bgr = frame.copy()
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    image = Image.fromarray(rgb)
    draw = ImageDraw.Draw(image)

    font_size = max(12, int(32 * float(font_scale)))
    font = _load_chinese_font(font_size)

    x, y = org
    text_lines = str(text).splitlines() or [""]
    rgb_color = (int(color[2]), int(color[1]), int(color[0]))

    for index, line in enumerate(text_lines):
        line_y = y + index * (font_size + line_spacing)
        draw.text((x, line_y), line, font=font, fill=rgb_color, stroke_width=max(0, int(thickness) - 1), stroke_fill=rgb_color)

    rendered = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    return rendered


def _ensure_battle_countdown_defaults(game):
    if not hasattr(game, "battle_countdown_duration_ms"):
        game.battle_countdown_duration_ms = 5000
    if not hasattr(game, "battle_countdown_active"):
        game.battle_countdown_active = False
    if not hasattr(game, "battle_countdown_started_ms"):
        game.battle_countdown_started_ms = 0


def start_battle_countdown(game, now_ms):
    _ensure_battle_countdown_defaults(game)
    game.reset_match()
    game.battle_countdown_active = True
    game.battle_countdown_started_ms = now_ms
    game.state = "PRE_BATTLE"


def update_battle_countdown(game, now_ms):
    _ensure_battle_countdown_defaults(game)
    if not game.battle_countdown_active:
        return

    elapsed = now_ms - game.battle_countdown_started_ms
    if elapsed >= game.battle_countdown_duration_ms:
        game.battle_countdown_active = False
        game.state = "RUNNING"


def draw_battle_countdown_overlay(game, frame, now_ms):
    _ensure_battle_countdown_defaults(game)
    if frame is None or not game.battle_countdown_active:
        return frame

    elapsed = max(0, now_ms - game.battle_countdown_started_ms)
    remaining_ms = max(0, game.battle_countdown_duration_ms - elapsed)
    remaining_seconds = max(1, int(np.ceil(remaining_ms / 1000.0)))

    dark_overlay = np.zeros_like(frame)
    out = cv2.addWeighted(frame, 0.35, dark_overlay, 0.65, 0)

    text_x = game.DISPLAY_W // 2 - 150
    title_y = game.DISPLAY_H // 2 - 150
    subtitle_y = game.DISPLAY_H // 2 - 25
    countdown_y = game.DISPLAY_H // 2 + 55
    font = cv2.FONT_HERSHEY_DUPLEX

    out = draw_chinese_text(out, "你的目標是擊敗BOSS\n             祝好運", (text_x, title_y), font_scale=1.0, color=(255, 255, 255), thickness=2, line_spacing=10)
    cv2.putText(out, str(remaining_seconds), (game.DISPLAY_W // 2 - 40, countdown_y), font, 2.4, (255, 255, 255), 5, cv2.LINE_AA)

    return out


def _ensure_soft_pulse_defaults(game):
    if not hasattr(game, "phase1_to_2_transition_active"):
        game.phase1_to_2_transition_active = False
    if not hasattr(game, "phase1_to_2_transition_started_ms"):
        game.phase1_to_2_transition_started_ms = 0
    if not hasattr(game, "phase1_to_2_transition_ended_ms"):
        game.phase1_to_2_transition_ended_ms = 0
    if not hasattr(game, "phase1_to_2_transition_duration_ms"):
        game.phase1_to_2_transition_duration_ms = 5000


def get_soft_pulse_transition_duration_ms(game):
    _ensure_soft_pulse_defaults(game)
    return int(game.phase1_to_2_transition_duration_ms)


def is_soft_pulse_transition_active(game):
    return getattr(game, "phase1_to_2_transition_active", False)


def _clear_transition_combat_state(game, now_ms):
    game.bullet_controller.bullets.clear()
    game.bullet_controller.last_fire_time = now_ms

    if hasattr(game.boss_controller, "attackA"):
        game.boss_controller.attackA.bullets.clear()
        if hasattr(game.boss_controller.attackA, "state"):
            game.boss_controller.attackA.state = "idle"
        if hasattr(game.boss_controller.attackA, "state_enter_ms"):
            game.boss_controller.attackA.state_enter_ms = now_ms
        if hasattr(game.boss_controller.attackA, "current_attack"):
            game.boss_controller.attackA.current_attack = None
        if hasattr(game.boss_controller.attackA, "attack_fired"):
            game.boss_controller.attackA.attack_fired = False
        if hasattr(game.boss_controller.attackA, "last_spawn"):
            game.boss_controller.attackA.last_spawn = now_ms

    if hasattr(game.boss_controller, "attackC"):
        game.boss_controller.attackC.damage_zones = []
        game.boss_controller.attackC.active_rocket = None
        game.boss_controller.attackC.warning_line_x = None
        game.boss_controller.attackC.warning_icon = None
        if hasattr(game.boss_controller.attackC, "state"):
            game.boss_controller.attackC.state = "idle"
        if hasattr(game.boss_controller.attackC, "state_enter_ms"):
            game.boss_controller.attackC.state_enter_ms = now_ms
        if hasattr(game.boss_controller.attackC, "current_attack"):
            game.boss_controller.attackC.current_attack = None


def begin_soft_pulse_transition(game, now_ms):
    if is_soft_pulse_transition_active(game):
        return

    _ensure_soft_pulse_defaults(game)
    game.phase1_to_2_transition_active = True
    game.phase1_to_2_transition_started_ms = now_ms
    game.phase1_to_2_transition_ended_ms = 0
    game.state = SOFT_PULSE_TRANSITION_STATE

    duration_ms = get_soft_pulse_transition_duration_ms(game)
    if getattr(game, "score_last_tick_ms", 0):
        game.score_last_tick_ms += duration_ms
    if getattr(game, "multiplier_next_award_ms", 0):
        game.multiplier_next_award_ms += duration_ms

    _clear_transition_combat_state(game, now_ms)


def update_soft_pulse_transition(game, now_ms):
    if not is_soft_pulse_transition_active(game):
        return

    _ensure_soft_pulse_defaults(game)
    elapsed = now_ms - game.phase1_to_2_transition_started_ms
    if elapsed >= get_soft_pulse_transition_duration_ms(game):
        game.phase1_to_2_transition_active = False
        game.phase1_to_2_transition_ended_ms = now_ms
        game.state = "RUNNING"


def draw_soft_pulse_transition(game, now_ms):
    _ensure_soft_pulse_defaults(game)
    _ensure_soft_pulse_defaults(game)
    base_frame = game.draw_game_frame()
    if base_frame is None:
        return base_frame

    elapsed = max(0, now_ms - game.phase1_to_2_transition_started_ms)
    duration = max(1, get_soft_pulse_transition_duration_ms(game))
    progress = min(1.0, elapsed / duration)

    # Apply the existing soft-pulse visual effect as background
    pulse_frame = _apply_soft_pulse_effect(base_frame, progress)

    # Dim the scene and overlay a centered Chinese countdown (same style as PRE_BATTLE)
    dark_overlay = np.zeros_like(pulse_frame)
    out = cv2.addWeighted(pulse_frame, 0.35, dark_overlay, 0.65, 0)

    text_x = game.DISPLAY_W // 2 - 150
    title_y = game.DISPLAY_H // 2 - 150
    countdown_y = game.DISPLAY_H // 2 + 55
    font = cv2.FONT_HERSHEY_DUPLEX

    remaining_ms = max(0, duration - elapsed)
    remaining_seconds = max(1, int(np.ceil(remaining_ms / 1000.0)))

    out = draw_chinese_text(out, "BOSS進入2階段\n子彈速度與攻擊性提升", (text_x, title_y), font_scale=1.0, color=(255, 255, 255), thickness=2, line_spacing=10)
    cv2.putText(out, str(remaining_seconds), (game.DISPLAY_W // 2 - 40, countdown_y), font, 2.4, (255, 255, 255), 5, cv2.LINE_AA)

    return out


def _apply_soft_pulse_effect(frame, progress):
    if frame is None:
        return frame

    out = frame.copy()
    height, width = out.shape[:2]
    pulse = 0.5 - 0.5 * np.cos(np.pi * progress)

    tint_overlay = np.zeros_like(out)
    tint_overlay[:] = (18, 22, 32)
    out = cv2.addWeighted(out, 1.0, tint_overlay, 0.03 + 0.04 * pulse, 0)

    ring_overlay = np.zeros_like(out)
    center_x = width // 2
    center_y = height // 2
    max_radius = int(min(width, height) * 0.42)
    min_radius = int(min(width, height) * 0.28)
    radius = int(min_radius + (max_radius - min_radius) * pulse)
    ring_color = (255, 220, 170)
    border_thickness = max(2, int(6 + 4 * pulse))
    cv2.circle(ring_overlay, (center_x, center_y), radius, ring_color, border_thickness)
    cv2.rectangle(ring_overlay, (0, 0), (width - 1, height - 1), (220, 240, 255), max(2, int(4 + 2 * pulse)))
    out = cv2.addWeighted(out, 1.0, ring_overlay, 0.06 + 0.08 * pulse, 0)

    return out


def draw_start_menu(game):
    if game.menu_img is None:
        return np.zeros((game.DISPLAY_H, game.DISPLAY_W, 3), dtype=np.uint8)

    if game.menu_img.shape[1] != game.DISPLAY_W or game.menu_img.shape[0] != game.DISPLAY_H:
        return cv2.resize(game.menu_img, (game.DISPLAY_W, game.DISPLAY_H), interpolation=cv2.INTER_AREA)

    return game.menu_img.copy()


def _menu_click_to_image_space(game, x, y):
    if game.menu_img is None:
        return x, y

    menu_h, menu_w = game.menu_img.shape[:2]
    image_x = int(x * menu_w / game.DISPLAY_W)
    image_y = int(y * menu_h / game.DISPLAY_H)
    return image_x, image_y


def _fail_click_to_image_space(game, x, y):
    if game.fail_img is None:
        return x, y

    img_h, img_w = game.fail_img.shape[:2]
    image_x = int(x * img_w / game.DISPLAY_W)
    image_y = int(y * img_h / game.DISPLAY_H)
    return image_x, image_y


def _win_click_to_image_space(game, x, y):
    if game.win_img is None:
        return x, y

    img_h, img_w = game.win_img.shape[:2]
    image_x = int(x * img_w / game.DISPLAY_W)
    image_y = int(y * img_h / game.DISPLAY_H)
    return image_x, image_y


def _start_button_clicked(game, x, y):
    image_x, image_y = _menu_click_to_image_space(game, x, y)
    bx, by, bw, bh = game.start_button_rect
    return bx <= image_x <= bx + bw and by <= image_y <= by + bh


def _fail_restart_clicked(game, x, y):
    image_x, image_y = _fail_click_to_image_space(game, x, y)
    return 44 <= image_x <= 273 and 493 <= image_y <= 546


def _fail_menu_clicked(game, x, y):
    image_x, image_y = _fail_click_to_image_space(game, x, y)
    return 44 <= image_x <= 273 and 557 <= image_y <= 607


def _win_play_again_clicked(game, x, y):
    image_x, image_y = _win_click_to_image_space(game, x, y)
    return 50 <= image_x <= 267 and 420 <= image_y <= 468


def _win_menu_clicked(game, x, y):
    image_x, image_y = _win_click_to_image_space(game, x, y)
    return 50 <= image_x <= 267 and 491 <= image_y <= 539


def enter_fail_transition(game, now_ms):
    if game.state not in ("FAIL_FADE_OUT", "FAIL_FADE_IN", "FAIL"):
        game.state = "FAIL_FADE_OUT"
        game.fail_transition_stage = "FADE_OUT"
        game.fail_transition_started_ms = now_ms


def draw_fail_screen(game):
    if game.fail_img is None:
        return np.zeros((game.DISPLAY_H, game.DISPLAY_W, 3), dtype=np.uint8)

    if game.fail_img.shape[1] != game.DISPLAY_W or game.fail_img.shape[0] != game.DISPLAY_H:
        return cv2.resize(game.fail_img, (game.DISPLAY_W, game.DISPLAY_H), interpolation=cv2.INTER_AREA)

    return game.fail_img.copy()


def draw_win_screen(game):
    if game.win_img is None:
        return np.zeros((game.DISPLAY_H, game.DISPLAY_W, 3), dtype=np.uint8)

    if game.win_img.shape[1] != game.DISPLAY_W or game.win_img.shape[0] != game.DISPLAY_H:
        return cv2.resize(game.win_img, (game.DISPLAY_W, game.DISPLAY_H), interpolation=cv2.INTER_AREA)

    return game.win_img.copy()


def draw_fail_transition(game, now_ms):
    base_frame = game.draw_game_frame()
    elapsed = now_ms - game.fail_transition_started_ms

    if game.fail_transition_stage == "FADE_OUT":
        progress = min(max(elapsed / max(1, game.fail_transition_fade_out_ms), 0.0), 1.0)
        return cv2.addWeighted(base_frame, 1.0 - progress, np.zeros_like(base_frame), progress, 0)

    return draw_fail_screen(game)


def update_fail_transition(game, now_ms):
    if game.state == "FAIL_FADE_OUT":
        if now_ms - game.fail_transition_started_ms >= game.fail_transition_fade_out_ms:
            game.fail_transition_stage = None
            game.state = "FAIL"


def apply_player_hit_effect(game, frame, now_ms):
    if frame is None:
        return frame

    hit_start_ms = getattr(game, "last_player_hit_ms", 0)
    elapsed = now_ms - hit_start_ms
    duration_ms = 240
    if elapsed < 0 or elapsed > duration_ms:
        return frame

    progress = min(max(elapsed / max(1, duration_ms), 0.0), 1.0)
    intensity = 1.0 - progress

    out = frame.copy()
    height, width = out.shape[:2]

    shake = max(0, int(3 * intensity))
    offset_x = int(np.random.randint(-shake, shake + 1))
    offset_y = int(np.random.randint(-shake, shake + 1))
    if offset_x != 0 or offset_y != 0:
        out = np.roll(out, shift=(offset_y, offset_x), axis=(0, 1))

    border_overlay = np.zeros_like(out)
    border_color = (0, 0, 255)
    border_thickness = max(4, int(16 * intensity))
    cv2.rectangle(border_overlay, (0, 0), (width - 1, height - 1), border_color, border_thickness)
    cv2.addWeighted(out, 1.0, border_overlay, 0.18 + 0.22 * intensity, 0, out)

    return out


def begin_phase_transition(game, now_ms):
    if is_phase_transition_active(game):
        return

    _ensure_phase_transition_defaults(game)
    game.phase_transition_active = True
    game.phase_transition_started_ms = now_ms
    game.phase_transition_ended_ms = 0
    game.state = PHASE_TRANSITION_STATE

    # Clear active projectiles once at transition start.
    game.bullet_controller.bullets.clear()
    game.bullet_controller.last_fire_time = now_ms

    if hasattr(game.boss_controller, "attackA"):
        game.boss_controller.attackA.bullets.clear()
        if hasattr(game.boss_controller.attackA, "state"):
            game.boss_controller.attackA.state = "idle"
        if hasattr(game.boss_controller.attackA, "state_enter_ms"):
            game.boss_controller.attackA.state_enter_ms = now_ms
        if hasattr(game.boss_controller.attackA, "current_attack"):
            game.boss_controller.attackA.current_attack = None

    if hasattr(game.boss_controller, "attackC"):
        game.boss_controller.attackC.damage_zones = []
        game.boss_controller.attackC.active_rocket = None
        game.boss_controller.attackC.warning_line_x = None
        game.boss_controller.attackC.warning_icon = None
        if hasattr(game.boss_controller.attackC, "state"):
            game.boss_controller.attackC.state = "idle"
        if hasattr(game.boss_controller.attackC, "state_enter_ms"):
            game.boss_controller.attackC.state_enter_ms = now_ms
        if hasattr(game.boss_controller.attackC, "current_attack"):
            game.boss_controller.attackC.current_attack = None

    # Preload warning image for phase transition (top-most, not affected by glitch)
    _ensure_warning_phase_image(game)


def update_phase_transition(game, now_ms):
    if not is_phase_transition_active(game):
        return

    _ensure_phase_transition_defaults(game)
    elapsed = now_ms - game.phase_transition_started_ms
    if elapsed >= game.phase_transition_duration_ms:
        game.phase_transition_active = False
        game.phase_transition_ended_ms = now_ms
        game.state = "RUNNING"


def draw_phase_transition(game, now_ms):
    _ensure_phase_transition_defaults(game)
    base_frame = game.draw_game_frame()
    elapsed = max(0, now_ms - game.phase_transition_started_ms)
    duration = max(1, int(game.phase_transition_duration_ms))
    progress = min(1.0, elapsed / duration)
    intensity = np.power(np.sin(np.pi * progress), 0.8)
    out = _apply_glitch_effect(base_frame, intensity)

    # Overlay the warning image on top, with fade in/out over the same duration
    out = _overlay_warning_phase_image(game, out, now_ms, progress)
    return out


def _ensure_warning_phase_image(game):
    if hasattr(game, "warning_phase_img"):
        return

    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = ['warning_phase_1.png', 'warning_phase.png']
    loaded = None
    for name in candidates:
        img_path = os.path.join(base_dir, 'image', name)
        try:
            if os.path.exists(img_path):
                img = imread_unicode(img_path, cv2.IMREAD_UNCHANGED)
                if img is not None:
                    try:
                        img = cv2.resize(img, (game.DISPLAY_W, game.DISPLAY_H), interpolation=cv2.INTER_AREA)
                    except Exception:
                        pass
                    loaded = img
                    print(f"[ui_screens] loaded warning image: {name}, shape={getattr(img, 'shape', None)}")
                    break
                else:
                    print(f"[ui_screens] failed to imread_unicode: {img_path}")
            else:
                # file missing
                print(f"[ui_screens] warning image not found: {img_path}")
        except Exception as e:
            print(f"[ui_screens] error loading {img_path}: {e}")

    if loaded is None:
        print("[ui_screens] no warning image loaded from candidates")

    game.warning_phase_img = loaded


def _overlay_warning_phase_image(game, frame, now_ms, progress):
    """Overlay the warning image for the full transition duration without fades.

    This function no longer applies any time-varying fade; it simply composites
    the warning image on top each frame. If the warning image has an alpha
    channel, that alpha is respected. Otherwise the warning image will fully
    replace the frame content (assumes the image is intended as a full-screen
    overlay).
    """
    if frame is None:
        return frame
    warn = getattr(game, 'warning_phase_img', None)
    if warn is None:
        return frame

    out = frame.copy().astype(np.float32)

    # If warning image has alpha, composite using its alpha (no temporal envelope)
    if warn.shape[2] == 4:
        warn_rgb = warn[:, :, :3].astype(np.float32)
        warn_a = warn[:, :, 3].astype(np.float32) / 255.0
        warn_a = np.expand_dims(warn_a, axis=2)
        out = warn_a * warn_rgb + (1.0 - warn_a) * out
    else:
        # No alpha channel: overlay fully (replace) to avoid per-frame blending costs
        out = warn.astype(np.float32)

    out = np.clip(out, 0, 255).astype(np.uint8)
    return out


def is_phase_transition_active(game):
    return getattr(game, "phase_transition_active", False)


def _ensure_phase_transition_defaults(game):
    if not hasattr(game, "phase_transition_active"):
        game.phase_transition_active = False
    if not hasattr(game, "phase_transition_started_ms"):
        game.phase_transition_started_ms = 0
    if not hasattr(game, "phase_transition_ended_ms"):
        game.phase_transition_ended_ms = 0
    if not hasattr(game, "phase_transition_duration_ms"):
        game.phase_transition_duration_ms = 5000


def _apply_glitch_effect(frame, intensity):
    if intensity <= 0.001:
        return frame

    out = frame.copy()
    height, width = out.shape[:2]

    max_slices = 18
    slice_count = max(2, int(max_slices * intensity))
    max_shift = max(6, int(72 * intensity))
    for _ in range(slice_count):
        strip_h = np.random.randint(4, 22)
        y1 = np.random.randint(0, max(1, height - strip_h))
        y2 = min(height, y1 + strip_h)
        shift = int(np.random.randint(-max_shift, max_shift + 1))
        out[y1:y2, :] = np.roll(out[y1:y2, :], shift, axis=1)

    split = max(1, int(3 * intensity))
    jitter_x = int(np.random.randint(-split, split + 1))
    jitter_y = int(np.random.randint(-split, split + 1))
    b = np.roll(out[:, :, 0], shift=(0, -split + jitter_x), axis=(0, 1))
    g = np.roll(out[:, :, 1], shift=(jitter_y, 0), axis=(0, 1))
    r = np.roll(out[:, :, 2], shift=(0, split + jitter_x), axis=(0, 1))
    out = np.stack((b, g, r), axis=2)

    shake = max(1, int(3 * intensity))
    offset_x = int(np.random.randint(-shake, shake + 1))
    offset_y = int(np.random.randint(-shake, shake + 1))
    out = np.roll(out, shift=(offset_y, offset_x), axis=(0, 1))

    emp_blocks = max(2, int(8 * intensity))
    for _ in range(emp_blocks):
        block_w = np.random.randint(max(20, width // 18), max(40, width // 6))
        block_h = np.random.randint(max(8, height // 40), max(24, height // 12))
        bx = np.random.randint(0, max(1, width - block_w))
        by = np.random.randint(0, max(1, height - block_h))
        color = np.array([
            np.random.randint(80, 256),
            np.random.randint(80, 256),
            np.random.randint(80, 256),
        ], dtype=np.uint8)
        if np.random.rand() < 0.5:
            color = np.array([
                np.random.randint(180, 256),
                np.random.randint(0, 120),
                np.random.randint(180, 256),
            ], dtype=np.uint8)
        out[by:by + block_h, bx:bx + block_w] = color

    return out


def handle_mouse_event(game, event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        if game.state == "START_MENU":
            if _start_button_clicked(game, x, y):
                print("Game Starting...")
                start_battle_countdown(game, int(time.time() * 1000))
        elif game.state == "WIN":
            if _win_play_again_clicked(game, x, y):
                start_battle_countdown(game, int(time.time() * 1000))
            elif _win_menu_clicked(game, x, y):
                game.go_to_start_menu(reset_match=True)
        elif game.state == "FAIL":
            if _fail_restart_clicked(game, x, y):
                game.reset_match()
                game.state = "RUNNING"
            elif _fail_menu_clicked(game, x, y):
                game.go_to_start_menu(reset_match=True)
        elif game.state == "RUNNING":
            game.mouse_dragging = True
            game.drag_offset_x = game.ship_controller.x - x
            game.drag_offset_y = game.ship_controller.y - y
    elif event == cv2.EVENT_LBUTTONUP:
        game.mouse_dragging = False
    elif event == cv2.EVENT_MOUSEMOVE and game.state == "RUNNING" and game.mouse_dragging:
        game.ship_controller.set_position(x + game.drag_offset_x, y + game.drag_offset_y)