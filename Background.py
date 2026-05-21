import cv2
import numpy as np
import os


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def imread_unicode(path, flags=cv2.IMREAD_COLOR):
    data = np.fromfile(path, dtype=np.uint8)
    if data.size == 0:
        return None
    return cv2.imdecode(data, flags)


class BackgroundScroller:
    def __init__(self, image_path='image/Background.jpg', window_w=320, window_h=640, scroll_speed=2):
        self.window_w = window_w
        self.window_h = window_h
        self.scroll_speed = scroll_speed

        if not os.path.isabs(image_path):
            image_path = os.path.join(BASE_DIR, image_path)

        self.raw_map = imread_unicode(image_path)
        if self.raw_map is None:
            self.raw_map = np.zeros((1000, 380, 3), dtype=np.uint8)

        self.map_img = self.raw_map
        self.scrolling_map = np.vstack([self.map_img, self.map_img])
        self.map_h = self.map_img.shape[0]
        self.current_y = self.map_h
        self.center_x = max((self.map_img.shape[1] - self.window_w) // 2, 0)

    def get_frame(self):
        return self.scrolling_map[self.current_y:self.current_y + self.window_h, self.center_x:self.center_x + self.window_w].copy()

    def update(self):
        self.current_y -= self.scroll_speed
        if self.current_y <= 0:
            self.current_y = self.map_h

    def get_display_frame(self):
        frame = self.get_frame()
        return cv2.resize(frame, (self.window_w * 2, self.window_h * 2), interpolation=cv2.INTER_NEAREST)


if __name__ == '__main__':
    background = BackgroundScroller()

    while True:
        cv2.imshow('Space Shooter Background', background.get_display_frame())
        background.update()

        if cv2.waitKey(16) & 0xFF == ord('q'):
            break

    cv2.destroyAllWindows()