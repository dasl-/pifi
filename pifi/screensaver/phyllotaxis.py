import numpy as np
import random
import math

from pifi.config import Config
from pifi.screensaver.screensaver import Screensaver


class Phyllotaxis(Screensaver):
    """
    Phyllotaxis spiral — golden ratio sunflower pattern.

    Points are placed at the golden angle with radii proportional to
    sqrt(index), creating the classic sunflower/pinecone spiral.
    Points grow outward, pulse in brightness, and slowly rotate.
    """

    GOLDEN_ANGLE = math.pi * (3 - math.sqrt(5))  # ~137.508 degrees

    def __init__(self, led_frame_player=None):
        super().__init__(led_frame_player)

        self.__width = Config.get_or_throw('leds.display_width')
        self.__height = Config.get_or_throw('leds.display_height')
        self.__time = 0.0

    def _setup(self):
        self.__time = 0.0
        self.__hue_base = random.random()
        self.__speed = random.uniform(0.015, 0.025)
        self.__rotation_speed = random.uniform(0.005, 0.015) * random.choice([-1, 1])

        self.__cx = self.__width / 2
        self.__cy = self.__height / 2
        self.__max_radius = min(self.__width, self.__height) / 2 * 0.95

        # How many dots fill the display nicely
        area = self.__width * self.__height
        self.__max_dots = int(area * 0.6)

        # Color scheme — controls how hue varies across the spiral
        self.__color_scheme = random.choice([
            'mono',       # single hue with brightness variation
            'duo',        # two complementary hues alternating by ring
            'gradient',   # smooth gradient from center to edge
            'rainbow',    # full spectrum across dots
        ])
        # Hue spread: how much hue range the scheme covers
        if self.__color_scheme == 'mono':
            self.__hue_spread = 0.0
        elif self.__color_scheme == 'duo':
            self.__hue_spread = 0.5  # complementary
        elif self.__color_scheme == 'gradient':
            self.__hue_spread = random.uniform(0.15, 0.35)
        else:  # rainbow
            self.__hue_spread = 1.0

        # Pre-allocate canvas
        self.__canvas = np.zeros((self.__height, self.__width, 3), dtype=np.float64)

    def _tick(self):
        self.__time += self.__speed

        self.__canvas *= 0.0  # clear each frame

        t = self.__time
        rotation = t * self.__rotation_speed * 2 * math.pi

        # Breathing effect — modulates brightness
        breath = 0.7 + 0.3 * math.sin(t * 1.5)

        # Slowly vary the angle multiplier for morphing spirals
        # Drift very slightly away from golden angle then back
        angle_wobble = math.sin(t * 0.3) * 0.003
        angle = self.GOLDEN_ANGLE + angle_wobble

        for i in range(self.__max_dots):
            # Spiral placement
            r = math.sqrt(i) * self.__max_radius / math.sqrt(self.__max_dots)
            theta = i * angle + rotation

            px = self.__cx + r * math.cos(theta)
            py = self.__cy + r * math.sin(theta)

            ix = int(round(px))
            iy = int(round(py))

            if 0 <= ix < self.__width and 0 <= iy < self.__height:
                norm_r = r / self.__max_radius

                # Color depends on scheme
                if self.__color_scheme == 'duo':
                    # Alternate hue by spiral arm (even/odd index)
                    hue = (self.__hue_base + (i % 2) * self.__hue_spread + t * 0.03) % 1.0
                elif self.__color_scheme == 'gradient':
                    # Hue shifts from center to edge
                    hue = (self.__hue_base + norm_r * self.__hue_spread + t * 0.03) % 1.0
                elif self.__color_scheme == 'rainbow':
                    hue = (self.__hue_base + i * 0.003 + t * 0.03) % 1.0
                else:  # mono
                    hue = (self.__hue_base + t * 0.03) % 1.0

                sat = 0.85 if self.__color_scheme == 'mono' else 0.75

                # Brightness: inner dots brighter, plus breathing
                val = (1.0 - norm_r * 0.5) * breath

                # Pulsing wave radiating outward
                pulse = 0.5 + 0.5 * math.sin(norm_r * 12 - t * 4)
                val *= 0.5 + 0.5 * pulse

                r_c, g_c, b_c = _hsv_to_rgb(hue, sat, val)
                # Additive — overlapping dots glow brighter
                self.__canvas[iy, ix, 0] = min(1.0, self.__canvas[iy, ix, 0] + r_c)
                self.__canvas[iy, ix, 1] = min(1.0, self.__canvas[iy, ix, 1] + g_c)
                self.__canvas[iy, ix, 2] = min(1.0, self.__canvas[iy, ix, 2] + b_c)

        frame = (np.clip(self.__canvas, 0, 1) * 255).astype(np.uint8)
        self._led_frame_player.play_frame(frame)

    @classmethod
    def get_id(cls) -> str:
        return 'phyllotaxis'

    @classmethod
    def get_name(cls) -> str:
        return 'Phyllotaxis'

    @classmethod
    def get_description(cls) -> str:
        return 'Golden ratio sunflower spirals'


def _hsv_to_rgb(h, s, v):
    """Scalar HSV to RGB, returns floats 0-1."""
    h = h % 1.0
    i = int(h * 6)
    f = h * 6 - i
    p = v * (1 - s)
    q = v * (1 - s * f)
    t = v * (1 - s * (1 - f))
    i = i % 6

    if i == 0:
        return v, t, p
    elif i == 1:
        return q, v, p
    elif i == 2:
        return p, v, t
    elif i == 3:
        return p, q, v
    elif i == 4:
        return t, p, v
    else:
        return v, p, q
