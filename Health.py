import cv2


class HealthMeter:
	def __init__(self, max_hp, current_hp=None):
		self.max_hp = max(1, int(max_hp))
		self.current_hp = self.max_hp if current_hp is None else max(0, min(int(current_hp), self.max_hp))

	def take_damage(self, amount):
		self.current_hp = max(self.current_hp - int(amount), 0)

	def heal(self, amount):
		self.current_hp = min(self.current_hp + int(amount), self.max_hp)

	def ratio(self):
		return self.current_hp / self.max_hp if self.max_hp else 0.0

	def is_empty(self):
		return self.current_hp <= 0


def draw_health_bar(frame, current_hp, max_hp, x, y, width, height, fill_color, border_color=(255, 255, 255), label=None):
	max_hp = max(1, int(max_hp))
	current_hp = max(0, min(int(current_hp), max_hp))
	width = max(1, int(width))
	height = max(1, int(height))
	filled_width = int(width * (current_hp / max_hp))

	cv2.rectangle(frame, (x, y), (x + width, y + height), border_color, 2)
	cv2.rectangle(frame, (x + 2, y + 2), (x + 2 + max(filled_width - 4, 0), y + height - 2), fill_color, -1)

	if label:
		cv2.putText(frame, label, (x, max(y - 8, 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, border_color, 2, cv2.LINE_AA)

	return frame


def draw_segmented_health_bar(frame, current_hp, max_hp, x, y, segment_hp, segment_width, height, fill_color, border_color=(255, 255, 255), label=None, stage_text_color=(255, 255, 255)):
	max_hp = max(1, int(max_hp))
	current_hp = max(0, min(int(current_hp), max_hp))
	segment_hp = max(1, int(segment_hp))
	segment_width = max(1, int(segment_width))
	height = max(1, int(height))
	segment_count = (max_hp + segment_hp - 1) // segment_hp
	remaining_segments = (current_hp + segment_hp - 1) // segment_hp if current_hp > 0 else 0

	for index in range(segment_count):
		segment_x = x + index * segment_width
		segment_left = index * segment_hp
		segment_right = min(segment_left + segment_hp, max_hp)
		segment_current = max(0, min(current_hp - segment_left, segment_right - segment_left))
		fill_ratio = segment_current / max(1, segment_right - segment_left)
		filled_width = int(segment_width * fill_ratio)

		cv2.rectangle(frame, (segment_x, y), (segment_x + segment_width, y + height), border_color, 2)
		if filled_width > 0:
			cv2.rectangle(frame, (segment_x + 2, y + 2), (segment_x + 2 + max(filled_width - 4, 0), y + height - 2), fill_color, -1)

	if label:
		cv2.putText(frame, label, (x, max(y - 8, 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, border_color, 2, cv2.LINE_AA)

	stage_text = f"X{remaining_segments}"
	text_x = x + segment_count * segment_width + 16
	text_y = y + height - 4
	cv2.putText(frame, stage_text, (text_x, text_y), cv2.FONT_HERSHEY_DUPLEX, 0.9, stage_text_color, 2, cv2.LINE_AA)

	return frame
