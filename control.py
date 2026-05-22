import ctypes
import os

import cv2
import numpy as np


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def asset_path(filename):
	return os.path.join(BASE_DIR, 'image', filename)


def imread_unicode(path, flags=cv2.IMREAD_COLOR):
	data = np.fromfile(path, dtype=np.uint8)
	if data.size == 0:
		return None
	return cv2.imdecode(data, flags)


class ShipController:
	def __init__(self, display_w, display_h, ship_w, ship_h, speed=8):
		self.display_w = display_w
		self.display_h = display_h
		self.ship_w = ship_w
		self.ship_h = ship_h
		self.speed = speed

		self.x = (self.display_w - self.ship_w) // 2
		self.y = self.display_h // 2 + 200

	def move_left(self):
		self.x = max(self.x - self.speed, 0)

	def move_right(self):
		self.x = min(self.x + self.speed, self.display_w - self.ship_w)

	def move_up(self):
		self.y = max(self.y - self.speed, 0)

	def move_down(self):
		self.y = min(self.y + self.speed, self.display_h - self.ship_h)

	def set_position(self, x, y):
		self.x = max(0, min(int(x), self.display_w - self.ship_w))
		self.y = max(0, min(int(y), self.display_h - self.ship_h))

	def is_key_pressed(self, virtual_key_code):
		return ctypes.windll.user32.GetAsyncKeyState(virtual_key_code) & 0x8000 != 0

	def update(self):
		if self.is_key_pressed(0x41) or self.is_key_pressed(0x25):
			self.move_left()
		if self.is_key_pressed(0x44) or self.is_key_pressed(0x27):
			self.move_right()
		if self.is_key_pressed(0x57) or self.is_key_pressed(0x26):
			self.move_up()
		if self.is_key_pressed(0x53) or self.is_key_pressed(0x28):
			self.move_down()

	def reset(self):
		self.x = (self.display_w - self.ship_w) // 2
		self.y = self.display_h // 2 + 200


class BulletController:
	def __init__(self, bullet_img, display_w, display_h, ship_controller, fire_interval=180, speed=16, max_bullets=6):
		self.display_w = display_w
		self.display_h = display_h
		self.ship_controller = ship_controller
		self.fire_interval = fire_interval
		self.speed = speed
		self.max_bullets = max(max_bullets, 12)
		self.shot_count = 1
		self.shot_spacing = 12
		self.last_fire_time = 0
		self.bullets = []

		if bullet_img is None:
			bullet_img = imread_unicode(asset_path('player_bullet_stage1.png'), cv2.IMREAD_UNCHANGED)
		if bullet_img is None:
			bullet_img = np.zeros((16, 8, 4), dtype=np.uint8)
			bullet_img[:, :, :3] = 255
			bullet_img[:, :, 3] = 255

		self.bullet_img = bullet_img

	def is_key_pressed(self, virtual_key_code):
		return ctypes.windll.user32.GetAsyncKeyState(virtual_key_code) & 0x8000 != 0

	def can_fire(self, now_ms):
		return (now_ms - self.last_fire_time) >= self.fire_interval and len(self.bullets) + self.shot_count <= self.max_bullets

	def _get_shot_offsets(self):
		if self.shot_count <= 1:
			return [0]

		start_offset = -((self.shot_count - 1) * self.shot_spacing) // 2
		return [start_offset + index * self.shot_spacing for index in range(self.shot_count)]

	def fire(self, now_ms):
		if not self.can_fire(now_ms):
			return

		bullet_h, bullet_w = self.bullet_img.shape[:2]
		y = self.ship_controller.y - bullet_h + 8
		center_x = self.ship_controller.x + (self.ship_controller.ship_w - bullet_w) // 2

		for offset_x in self._get_shot_offsets():
			self.bullets.append({"x": center_x + offset_x, "y": y})
		self.last_fire_time = now_ms

	def update(self, now_ms):
		self.fire(now_ms)

		for bullet in self.bullets:
			bullet["y"] -= self.speed

		self.bullets = [bullet for bullet in self.bullets if bullet["y"] + self.bullet_img.shape[0] > 0]

	def draw(self, frame):
		for bullet in self.bullets:
			frame = self._overlay_image(frame, self.bullet_img, bullet["x"], bullet["y"])
		return frame

	def _overlay_image(self, background, overlay, x, y):
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
