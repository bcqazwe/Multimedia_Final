import random
import os

import cv2
import numpy as np
from boss_attacks import BossAttackA, BossAttackC


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def imread_unicode(path, flags=cv2.IMREAD_COLOR):
	data = np.fromfile(path, dtype=np.uint8)
	if data.size == 0:
		return None
	return cv2.imdecode(data, flags)


class BossController:
	def __init__(self, display_w, display_h, image_path='boss_ship_2.png', width=None, move_speed=4):
		self.display_w = display_w
		self.display_h = display_h
		self.move_speed = move_speed
		self.last_target_change = 0
		self.scale_factor = max(1, int(round(min(self.display_w / 320.0, self.display_h / 640.0))))
		if not os.path.isabs(image_path):
			image_path = os.path.join(BASE_DIR, 'image', image_path)

		self.boss_img = imread_unicode(image_path, cv2.IMREAD_UNCHANGED)
		if self.boss_img is None:
			self.boss_img = np.zeros((96, 128, 4), dtype=np.uint8)
			self.boss_img[:, :, :3] = (0, 180, 255)
			self.boss_img[:, :, 3] = 255
		elif self.boss_img.shape[2] == 3:
			alpha = np.full((self.boss_img.shape[0], self.boss_img.shape[1], 1), 255, dtype=np.uint8)
			self.boss_img = np.concatenate([self.boss_img, alpha], axis=2)

		if width is None:
			width = max(140, self.display_w // 4) * self.scale_factor

		scale = width / self.boss_img.shape[1]
		height = max(1, int(self.boss_img.shape[0] * scale))
		self.boss_img = cv2.resize(self.boss_img, (width, height), interpolation=cv2.INTER_NEAREST)
		self.boss_rgb = self.boss_img[:, :, :3]
		self.boss_mask = self.boss_img[:, :, 3:] / 255.0

		self.boss_w = self.boss_img.shape[1]
		self.boss_h = self.boss_img.shape[0]
		self.x = max((self.display_w - self.boss_w) // 2, 0)
		self.boss_y = max(int(self.display_h * 0.09), 8)
		self.y = self.boss_y
		self.target_x = self.x
		self.next_target_change_ms = 0
		self.attackA = BossAttackA(display_w, display_h)
		self.attackC = BossAttackC(display_w, display_h)

	def get_rect(self):
		return self.x, self.y, self.boss_w, self.boss_h

	def reset(self):
		self.x = max((self.display_w - self.boss_w) // 2, 0)
		self.y = self.boss_y
		self.target_x = self.x
		self.next_target_change_ms = 0
		self.attackA.reset()
		self.attackC.reset()

	def update(self, now_ms):
		if now_ms >= self.next_target_change_ms:
			self.target_x = random.randint(0, max(self.display_w - self.boss_w, 0))
			self.next_target_change_ms = now_ms + random.randint(700, 1400)

		if self.x < self.target_x:
			self.x = min(self.x + self.move_speed, self.target_x)
		elif self.x > self.target_x:
			self.x = max(self.x - self.move_speed, self.target_x)

		# attack update handled externally with phase/player info

	def draw(self, frame):
		frame = self.draw_body(frame)
		frame = self.draw_attacks(frame)
		return frame

	def draw_body(self, frame):
		return self._overlay_cached_image(frame, self.boss_rgb, self.boss_mask, self.x, self.y)

	def draw_attacks(self, frame):
		frame = self.attackA.draw(frame)
		frame = self.attackC.draw(frame)
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

		# use OpenCV operations for faster C-level blending
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