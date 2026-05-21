import ctypes


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
