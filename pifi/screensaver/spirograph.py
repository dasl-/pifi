import math
import numpy as np
import random

from pifi.config import Config
from pifi.logger import Logger
from pifi.screensaver.screensaver import Screensaver


class Spirograph(Screensaver):
    """
    Spirograph screensaver with visible gear mechanism.

    Draws epitrochoid curves while showing the fixed ring, rolling
    gear, and arm. The pen traces a fading trail as the gear rolls.
    """

    def __init__(self, led_frame_player=None):
        super().__init__(led_frame_player)
        self.__logger = Logger().set_namespace(self.__class__.__name__)

        self.__width = Config.get_or_throw('leds.display_width')
        self.__height = Config.get_or_throw('leds.display_height')

    def _setup(self):
        self.__time = 0.0

        # Spirograph parameters
        R = random.uniform(0.3, 0.5)
        r = random.uniform(0.08, 0.25)
        d = random.uniform(0.05, 0.2)

        # Ensure interesting ratio (non-repeating patterns)
        ratio = R / r
        if abs(ratio - round(ratio)) < 0.1:
            r *= 1.1

        speed = random.uniform(0.02, 0.05)
        hue_speed = random.uniform(0.001, 0.003)

        # Scale so the full pattern fits on screen
        max_extent = R + r + d
        scale = min(self.__width, self.__height) / 2.0 * 0.92 / max_extent

        self.__R = R
        self.__r = r
        self.__d = d
        self.__speed = speed
        self.__hue_speed = hue_speed
        self.__scale = scale
        self.__ratio = (R + r) / r

        self.__cx = self.__width / 2.0
        self.__cy = self.__height / 2.0

        # Trail canvas (persistent, fading)
        self.__canvas = np.zeros((self.__height, self.__width, 3), dtype=np.float64)

        self.__logger.info(f"Spirograph params: R={R:.3f}, r={r:.3f}, d={d:.3f}")

    def _tick(self):
        time_speed = Config.get('screensavers.configs.spirograph.time_speed', 1.0)
        self.__time += time_speed

        t = self.__time * self.__speed
        R, r, d = self.__R, self.__r, self.__d
        ratio = self.__ratio
        scale = self.__scale

        # Rolling gear center
        gear_x = (R + r) * math.cos(t)
        gear_y = (R + r) * math.sin(t)

        # Pen point (epitrochoid)
        pen_x = gear_x - d * math.cos(ratio * t)
        pen_y = gear_y - d * math.sin(ratio * t)

        # Convert to screen coords
        sx = self.__cx + pen_x * scale
        sy = self.__cy + pen_y * scale

        # Deposit on trail canvas
        hue = (self.__time * self.__hue_speed) % 1.0
        color = _hsv_to_rgb(hue, 0.85, 1.0)

        ix, iy = int(round(sx)), int(round(sy))
        if 0 <= ix < self.__width and 0 <= iy < self.__height:
            self.__canvas[iy, ix] = np.minimum(
                1.0, self.__canvas[iy, ix] + np.array(color) * 0.5
            )

        # Fade trail
        self.__canvas *= 0.997

        # Build display: trail + gear mechanism
        display = self.__canvas.copy()
        self.__draw_mechanism(display, t, gear_x, gear_y, pen_x, pen_y)

        frame = (np.clip(display, 0, 1) * 255).astype(np.uint8)
        self._led_frame_player.play_frame(frame)

    def __draw_mechanism(self, canvas, t, gear_x, gear_y, pen_x, pen_y):
        """Draw the fixed ring, rolling gear, arm, and pen dot."""
        scale = self.__scale
        cx, cy = self.__cx, self.__cy
        R, r, d = self.__R, self.__r, self.__d

        gear_color = np.array([0.15, 0.15, 0.2])
        ring_color = np.array([0.1, 0.1, 0.15])

        # Fixed ring
        self.__draw_circle(canvas, cx, cy, R * scale, ring_color)

        # Rolling gear
        gcx = cx + gear_x * scale
        gcy = cy + gear_y * scale
        self.__draw_circle(canvas, gcx, gcy, r * scale, gear_color)

        # Arm from gear center to pen
        px = cx + pen_x * scale
        py = cy + pen_y * scale
        self.__draw_line(canvas, gcx, gcy, px, py, gear_color * 1.5)

        # Pen dot — bright
        hue = (self.__time * self.__hue_speed) % 1.0
        pen_color = np.array(_hsv_to_rgb(hue, 0.7, 1.0))
        ix, iy = int(round(px)), int(round(py))
        if 0 <= ix < self.__width and 0 <= iy < self.__height:
            canvas[iy, ix] = np.maximum(canvas[iy, ix], pen_color)

    def __draw_circle(self, canvas, cx, cy, radius, color):
        """Draw a 1-pixel circle outline."""
        circumference = max(8, int(2 * math.pi * radius * 1.5))
        for i in range(circumference):
            angle = 2 * math.pi * i / circumference
            px = int(round(cx + radius * math.cos(angle)))
            py = int(round(cy + radius * math.sin(angle)))
            if 0 <= px < self.__width and 0 <= py < self.__height:
                canvas[py, px] = np.maximum(canvas[py, px], color)

    def __draw_line(self, canvas, x1, y1, x2, y2, color):
        """Draw a 1-pixel line."""
        dx, dy = x2 - x1, y2 - y1
        steps = max(1, int(max(abs(dx), abs(dy)) * 1.5))
        for s in range(steps + 1):
            t = s / steps
            px = int(round(x1 + dx * t))
            py = int(round(y1 + dy * t))
            if 0 <= px < self.__width and 0 <= py < self.__height:
                canvas[py, px] = np.maximum(canvas[py, px], color)

    @classmethod
    def get_id(cls) -> str:
        return 'spirograph'

    @classmethod
    def get_name(cls) -> str:
        return 'Spirograph'

    @classmethod
    def get_description(cls) -> str:
        return 'Gear-drawn geometric patterns'


def _hsv_to_rgb(h, s, v):
    h = h % 1.0
    i = int(h * 6)
    f = h * 6 - i
    p = v * (1 - s)
    q = v * (1 - s * f)
    t = v * (1 - s * (1 - f))
    i = i % 6
    if i == 0: return (v, t, p)
    elif i == 1: return (q, v, p)
    elif i == 2: return (p, v, t)
    elif i == 3: return (p, q, v)
    elif i == 4: return (t, p, v)
    else: return (v, p, q)
