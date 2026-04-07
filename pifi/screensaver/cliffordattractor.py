import numpy as np
import random
import math

from pifi.config import Config
from pifi.screensaver.screensaver import Screensaver


class CliffordAttractor(Screensaver):
    """
    Clifford strange attractor.

    Iterates the system:
        x' = sin(a*y) + c*cos(a*x)
        y' = sin(b*x) + d*cos(b*y)

    Points accumulate into a density buffer that glows with color.
    Parameters drift slowly for continuously morphing shapes.
    """

    def __init__(self, led_frame_player=None):
        super().__init__(led_frame_player)

        self.__width = Config.get_or_throw('leds.display_width')
        self.__height = Config.get_or_throw('leds.display_height')
        self.__time = 0.0

    def _setup(self):
        self.__time = 0.0
        self.__hue_base = random.random()

        # Density accumulation buffer
        self.__density = np.zeros((self.__height, self.__width), dtype=np.float64)

        # Attractor parameters — start with known-good values
        self.__base_params = {
            'a': random.uniform(-2.0, 2.0),
            'b': random.uniform(-2.0, 2.0),
            'c': random.uniform(-2.0, 2.0),
            'd': random.uniform(-2.0, 2.0),
        }

        # Drift speeds for each parameter
        self.__drift = {
            'a': random.uniform(-0.003, 0.003),
            'b': random.uniform(-0.003, 0.003),
            'c': random.uniform(-0.003, 0.003),
            'd': random.uniform(-0.003, 0.003),
        }

        # Current point
        self.__x = random.uniform(-0.1, 0.1)
        self.__y = random.uniform(-0.1, 0.1)

        # How many iterations per tick
        self.__iters_per_tick = max(100, self.__width * self.__height * 2)

    def _tick(self, tick):
        self.__time += 0.01

        # Slowly drift parameters
        a = self.__base_params['a'] + math.sin(self.__time * self.__drift['a'] * 100) * 0.5
        b = self.__base_params['b'] + math.sin(self.__time * self.__drift['b'] * 100 + 1.3) * 0.5
        c = self.__base_params['c'] + math.sin(self.__time * self.__drift['c'] * 100 + 2.7) * 0.5
        d = self.__base_params['d'] + math.sin(self.__time * self.__drift['d'] * 100 + 4.1) * 0.5

        # Fade existing density for trail effect
        self.__density *= 0.92

        # Iterate the attractor
        x, y = self.__x, self.__y
        w, h = self.__width, self.__height
        density = self.__density

        # Batch iterate using numpy for speed
        xs = np.empty(self.__iters_per_tick)
        ys = np.empty(self.__iters_per_tick)
        xs[0] = x
        ys[0] = y

        for i in range(1, self.__iters_per_tick):
            xs[i] = math.sin(a * ys[i - 1]) + c * math.cos(a * xs[i - 1])
            ys[i] = math.sin(b * xs[i - 1]) + d * math.cos(b * ys[i - 1])

        self.__x = xs[-1]
        self.__y = ys[-1]

        # Map attractor coordinates to pixel space
        # Attractor output is roughly in [-3, 3]
        scale = min(w, h) / 6
        px = ((xs + 3) * scale).astype(int) + (w - int(6 * scale)) // 2
        py = ((ys + 3) * scale).astype(int) + (h - int(6 * scale)) // 2

        # Accumulate hits into density buffer
        mask = (px >= 0) & (px < w) & (py >= 0) & (py < h)
        np.add.at(density, (py[mask], px[mask]), 0.15)

        # Normalize and render
        d = np.clip(density, 0, 1)

        hue = (self.__hue_base + d * 0.35 + self.__time * 0.05) % 1.0
        sat = np.where(d > 0.01, 0.6 + d * 0.3, 0.0)
        val = np.where(d > 0.01, d ** 0.6, 0.0)  # gamma for glow

        frame = _hsv_to_rgb_vec(hue, sat, val)
        self._led_frame_player.play_frame(frame)

    @classmethod
    def get_id(cls) -> str:
        return 'clifford_attractor'

    @classmethod
    def get_name(cls) -> str:
        return 'Clifford Attractor'

    @classmethod
    def get_description(cls) -> str:
        return 'Strange attractor wisps'


def _hsv_to_rgb_vec(h, s, v):
    """Vectorized HSV to RGB. Returns [H, W, 3] uint8."""
    i = (h * 6.0).astype(int) % 6
    f = h * 6.0 - np.floor(h * 6.0)
    p = v * (1.0 - s)
    q = v * (1.0 - s * f)
    t = v * (1.0 - s * (1.0 - f))

    r = np.zeros_like(h)
    g = np.zeros_like(h)
    bl = np.zeros_like(h)

    m0 = i == 0; r[m0] = v[m0]; g[m0] = t[m0]; bl[m0] = p[m0]
    m1 = i == 1; r[m1] = q[m1]; g[m1] = v[m1]; bl[m1] = p[m1]
    m2 = i == 2; r[m2] = p[m2]; g[m2] = v[m2]; bl[m2] = t[m2]
    m3 = i == 3; r[m3] = p[m3]; g[m3] = q[m3]; bl[m3] = v[m3]
    m4 = i == 4; r[m4] = t[m4]; g[m4] = p[m4]; bl[m4] = v[m4]
    m5 = i == 5; r[m5] = v[m5]; g[m5] = p[m5]; bl[m5] = q[m5]

    return np.stack([r * 255, g * 255, bl * 255], axis=-1).astype(np.uint8)
