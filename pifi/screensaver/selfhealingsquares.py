import numpy as np
import random
import math

from pifi.config import Config
from pifi.screensaver.screensaver import Screensaver


class SelfHealingSquares(Screensaver):
    """
    Healing Grid — after the optical illusion by Ryota Kanai.

    A grid of plus/cross shapes on a dark background. The center is
    perfectly regular; toward the edges, the crosses are progressively
    shifted, rotated, and distorted. The distortion level slowly
    breathes — breaking and healing the grid over time.
    """

    def __init__(self, led_frame_player=None):
        super().__init__(led_frame_player)

        self.__width = Config.get_or_throw('leds.display_width')
        self.__height = Config.get_or_throw('leds.display_height')

    def _setup(self):
        self.__time = 0.0

        # Grid spacing — aim for roughly 4-pixel spacing between crosses
        self.__spacing = max(3, min(self.__width, self.__height) // 8)

        # Cross arm length and thickness
        self.__arm = max(1, self.__spacing // 3)
        self.__thickness = 1

        # Center of the display
        self.__cx = self.__width / 2.0
        self.__cy = self.__height / 2.0

        # Maximum distance from center (for normalizing distortion)
        self.__max_dist = math.sqrt(self.__cx ** 2 + self.__cy ** 2)

        # Per-cross random offsets for organic distortion (seeded once)
        cols = int(self.__width / self.__spacing) + 2
        rows = int(self.__height / self.__spacing) + 2
        self.__rand_dx = np.random.uniform(-1, 1, (rows, cols))
        self.__rand_dy = np.random.uniform(-1, 1, (rows, cols))
        self.__rand_rot = np.random.uniform(-1, 1, (rows, cols))

        # Base hue for the crosses
        self.__hue = random.random()

        # Frame buffer
        self.__frame = np.zeros((self.__height, self.__width, 3), dtype=np.uint8)

    def _tick(self, tick):
        self.__time += 0.015

        self.__frame[:] = 0

        # Distortion intensity oscillates smoothly
        distortion = (math.sin(self.__time * 0.7) * 0.5 + 0.5)
        # Add a slower secondary oscillation for variety
        distortion *= 0.3 + 0.7 * (math.sin(self.__time * 0.23) * 0.5 + 0.5)

        spacing = self.__spacing
        arm = self.__arm

        # Hue drifts slowly
        self.__hue = (self.__hue + 0.001) % 1.0

        row = 0
        gy = spacing // 2
        while gy < self.__height + spacing:
            col = 0
            gx = spacing // 2
            while gx < self.__width + spacing:
                # Distance from center, normalized 0..1
                dx = gx - self.__cx
                dy = gy - self.__cy
                dist = math.sqrt(dx * dx + dy * dy) / self.__max_dist
                dist = min(dist, 1.0)

                # Distortion scales with distance from center
                d = dist * dist * distortion

                # Per-cross random offsets, scaled by distortion
                ri = row % self.__rand_dx.shape[0]
                ci = col % self.__rand_dx.shape[1]
                offset_x = self.__rand_dx[ri, ci] * d * spacing * 0.5
                offset_y = self.__rand_dy[ri, ci] * d * spacing * 0.5
                rotation = self.__rand_rot[ri, ci] * d * 0.8

                cx = gx + offset_x
                cy = gy + offset_y

                # Color: slight hue variation per cross, brighter toward center
                brightness = 0.5 + 0.5 * (1.0 - dist * 0.5)
                hue = (self.__hue + dist * 0.15) % 1.0
                r, g, b = _hsv_to_rgb(hue, 0.6, brightness)
                color = (int(r * 255), int(g * 255), int(b * 255))

                self.__draw_cross(cx, cy, arm, rotation, color)

                gx += spacing
                col += 1
            gy += spacing
            row += 1

        self._led_frame_player.play_frame(self.__frame)

    def __draw_cross(self, cx, cy, arm, rotation, color):
        """Draw a plus/cross shape, optionally rotated."""
        cos_r = math.cos(rotation)
        sin_r = math.sin(rotation)

        # Two arms of the cross: horizontal and vertical
        for ax, ay in [(1, 0), (0, 1)]:
            # Rotate the arm direction
            dax = ax * cos_r - ay * sin_r
            day = ax * sin_r + ay * cos_r

            # Draw pixels along the arm in both directions
            steps = arm
            for s in range(-steps, steps + 1):
                px = int(round(cx + dax * s))
                py = int(round(cy + day * s))
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
