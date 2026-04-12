import numpy as np
import random
import math

from pifi.config import Config
from pifi.screensaver.screensaver import Screensaver


class SelfHealingSquares(Screensaver):
    """
    Healing Grid — after the optical illusion by Ryota Kanai.

    A connected grid of thin lines on a dark background. The center
    is perfectly regular; toward the edges, intersections are
    progressively displaced. The distortion breathes over time so the
    grid continuously breaks apart and heals back.
    """

    def __init__(self, led_frame_player=None):
        super().__init__(led_frame_player)

        self.__width = Config.get_or_throw('leds.display_width')
        self.__height = Config.get_or_throw('leds.display_height')

    def _setup(self):
        self.__time = 0.0

        # Grid spacing
        self.__spacing = max(3, min(self.__width, self.__height) // 8)

        # Number of grid nodes (one extra on each side for edge coverage)
        self.__cols = int(self.__width / self.__spacing) + 3
        self.__rows = int(self.__height / self.__spacing) + 3

        # Starting offset so grid is centered
        self.__ox = (self.__width - (self.__cols - 1) * self.__spacing) / 2.0
        self.__oy = (self.__height - (self.__rows - 1) * self.__spacing) / 2.0

        # Center of the display
        self.__cx = self.__width / 2.0
        self.__cy = self.__height / 2.0

        # Maximum distance from center (for normalizing distortion)
        self.__max_dist = math.sqrt(self.__cx ** 2 + self.__cy ** 2)

        # Per-node random displacement directions (seeded once)
        self.__rand_dx = np.random.uniform(-1, 1, (self.__rows, self.__cols))
        self.__rand_dy = np.random.uniform(-1, 1, (self.__rows, self.__cols))

        # Base hue
        self.__hue = random.random()

        # Frame buffer
        self.__frame = np.zeros((self.__height, self.__width, 3), dtype=np.uint8)

    def _tick(self, tick):
        self.__time += 0.015

        self.__frame[:] = 0

        # Distortion intensity oscillates smoothly
        distortion = (math.sin(self.__time * 0.7) * 0.5 + 0.5)
        distortion *= 0.3 + 0.7 * (math.sin(self.__time * 0.23) * 0.5 + 0.5)

        spacing = self.__spacing

        # Hue drifts slowly
        self.__hue = (self.__hue + 0.001) % 1.0

        # Compute distorted positions for all grid nodes
        positions = np.empty((self.__rows, self.__cols, 2))
        for row in range(self.__rows):
            for col in range(self.__cols):
                gx = self.__ox + col * spacing
                gy = self.__oy + row * spacing

                # Distance from center, normalized 0..1
                dx = gx - self.__cx
                dy = gy - self.__cy
                dist = min(1.0, math.sqrt(dx * dx + dy * dy) / self.__max_dist)

                # Distortion scales with distance squared
                d = dist * dist * distortion

                positions[row, col, 0] = gx + self.__rand_dx[row, col] * d * spacing * 0.6
                positions[row, col, 1] = gy + self.__rand_dy[row, col] * d * spacing * 0.6

        # Draw lines between neighboring nodes
        for row in range(self.__rows):
            for col in range(self.__cols):
                x1, y1 = positions[row, col]

                # Distance of this node from center for coloring
                dist = min(1.0, math.sqrt((x1 - self.__cx) ** 2 + (y1 - self.__cy) ** 2) / self.__max_dist)
                brightness = 0.5 + 0.5 * (1.0 - dist * 0.4)
                hue = (self.__hue + dist * 0.12) % 1.0
                r, g, b = _hsv_to_rgb(hue, 0.55, brightness)
                color = (int(r * 255), int(g * 255), int(b * 255))

                # Right neighbor
                if col + 1 < self.__cols:
                    x2, y2 = positions[row, col + 1]
                    self.__draw_line(x1, y1, x2, y2, color)

                # Down neighbor
                if row + 1 < self.__rows:
                    x2, y2 = positions[row + 1, col]
                    self.__draw_line(x1, y1, x2, y2, color)

        self._led_frame_player.play_frame(self.__frame)

    def __draw_line(self, x1, y1, x2, y2, color):
        """Draw a 1-pixel-wide line between two points."""
        dx = x2 - x1
        dy = y2 - y1
        steps = max(1, int(max(abs(dx), abs(dy)) * 1.5))

        for s in range(steps + 1):
            t = s / steps
            px = int(round(x1 + dx * t))
            py = int(round(y1 + dy * t))
            if 0 <= px < self.__width and 0 <= py < self.__height:
                self.__frame[py, px] = color

    @classmethod
    def get_id(cls) -> str:
        return 'self_healing_squares'

    @classmethod
    def get_name(cls) -> str:
        return 'Healing Grid'

    @classmethod
    def get_description(cls) -> str:
        return 'Kanai healing grid illusion'


def _hsv_to_rgb(h, s, v):
    h = h % 1.0
    i = int(h * 6)
    f = h * 6 - i
    p = v * (1 - s)
    q = v * (1 - s * f)
    t = v * (1 - s * (1 - f))
    i = i % 6
    if i == 0: return v, t, p
    elif i == 1: return q, v, p
    elif i == 2: return p, v, t
    elif i == 3: return p, q, v
    elif i == 4: return t, p, v
    else: return v, p, q
