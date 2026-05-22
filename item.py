import os
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


def ensure_rgba(image, fallback_shape=(32, 32, 4)):
	if image is None:
		fallback = np.zeros(fallback_shape, dtype=np.uint8)
		fallback[:, :, :3] = 255
		fallback[:, :, 3] = 255
		return fallback

	if image.ndim == 2:
		return cv2.cvtColor(image, cv2.COLOR_GRAY2BGRA)

	if image.shape[2] == 4:
		return image

	alpha_channel = np.full((image.shape[0], image.shape[1], 1), 255, dtype=np.uint8)
	return np.concatenate((image, alpha_channel), axis=2)


class ItemController:
	def __init__(self, display_w, display_h, spawn_interval_ms=10000, heal_weight=0.35):
		self.display_w = display_w
		self.display_h = display_h
		self.spawn_interval_ms = spawn_interval_ms
		self.heal_weight = heal_weight
		self.item_max_size = 70
		self.last_spawn_time = int(time.time() * 1000)
		self.items = []

		heal_image = ensure_rgba(imread_unicode(asset_path('heal.png')))
		upgrade_image = ensure_rgba(imread_unicode(asset_path('upgrade.png')))
		self.item_images = {
			'heal': self._resize_to_box(heal_image),
			'upgrade': self._resize_to_box(upgrade_image),
		}

	def reset(self, now_ms=None):
		self.items.clear()
		self.last_spawn_time = int(time.time() * 1000) if now_ms is None else now_ms

	def _random_velocity(self):
		velocity_choices = [-4, -3, -2, 2, 3, 4]
		velocity_x = random.choice(velocity_choices)
		velocity_y = random.choice(velocity_choices)
		return velocity_x, velocity_y

	def _resize_to_box(self, image):
		image_h, image_w = image.shape[:2]
		scale = min(self.item_max_size / image_w, self.item_max_size / image_h, 1.0)
		if scale >= 1.0:
			return image

		resized_w = max(1, int(image_w * scale))
		resized_h = max(1, int(image_h * scale))
		return cv2.resize(image, (resized_w, resized_h), interpolation=cv2.INTER_AREA)

	def _spawn_item(self):
		item_kind = random.choices(['heal', 'upgrade'], weights=[self.heal_weight, 1.0 - self.heal_weight], k=1)[0]
		item_image = self.item_images[item_kind]
		item_h, item_w = item_image.shape[:2]
		max_x = max(0, self.display_w - item_w)
		max_y = max(0, (self.display_h // 2) - item_h)
		start_x = random.randint(0, max_x)
		start_y = random.randint(0, max_y)
		velocity_x, velocity_y = self._random_velocity()

		self.items.append({
			'kind': item_kind,
			'image': item_image,
			'x': start_x,
			'y': start_y,
			'vx': velocity_x,
			'vy': velocity_y,
		})

	def update(self, now_ms):
		if now_ms - self.last_spawn_time >= self.spawn_interval_ms:
			self._spawn_item()
			self.last_spawn_time = now_ms

		for item in self.items:
			item['x'] += item['vx']
			item['y'] += item['vy']

			item_h, item_w = item['image'].shape[:2]

			if item['x'] <= 0:
				item['x'] = 0
				item['vx'] *= -1
			elif item['x'] + item_w >= self.display_w:
				item['x'] = self.display_w - item_w
				item['vx'] *= -1

			if item['y'] <= 0:
				item['y'] = 0
				item['vy'] *= -1
			elif item['y'] + item_h >= self.display_h:
				item['y'] = self.display_h - item_h
				item['vy'] *= -1

	def draw(self, frame):
		for item in self.items:
			frame = self._overlay_image(frame, item['image'], item['x'], item['y'])
		return frame

	def collect_player_items(self, player_rect):
		remaining_items = []
		collected_kinds = []

		for item in self.items:
			item_h, item_w = item['image'].shape[:2]
			item_rect = (item['x'], item['y'], item['x'] + item_w, item['y'] + item_h)
			hit_player = not (
				item_rect[2] < player_rect[0]
				or item_rect[0] > player_rect[2]
				or item_rect[3] < player_rect[1]
				or item_rect[1] > player_rect[3]
			)

			if hit_player:
				collected_kinds.append(item['kind'])
			else:
				remaining_items.append(item)

		self.items = remaining_items
		return collected_kinds

	def _overlay_image(self, background, overlay, pos_x, pos_y):
		overlay_h, overlay_w = overlay.shape[:2]
		if pos_x >= background.shape[1] or pos_y >= background.shape[0] or pos_x + overlay_w <= 0 or pos_y + overlay_h <= 0:
			return background

		overlay_img = overlay[:, :, :3]
		overlay_mask = overlay[:, :, 3:] / 255.0

		x1 = max(pos_x, 0)
		y1 = max(pos_y, 0)
		x2 = min(pos_x + overlay_w, background.shape[1])
		y2 = min(pos_y + overlay_h, background.shape[0])

		overlay_x1 = x1 - pos_x
		overlay_y1 = y1 - pos_y
		overlay_x2 = overlay_x1 + (x2 - x1)
		overlay_y2 = overlay_y1 + (y2 - y1)

		region = background[y1:y2, x1:x2]
		overlay_region = overlay_img[overlay_y1:overlay_y2, overlay_x1:overlay_x2]
		mask_region = overlay_mask[overlay_y1:overlay_y2, overlay_x1:overlay_x2]

		background[y1:y2, x1:x2] = (1.0 - mask_region) * region + mask_region * overlay_region
		return background
