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

        # Attractor parameters — start with known-good values that produce
        # interesting shapes
        presets = [
            {'a': -1.4, 'b': 1.6, 'c': 1.0, 'd': 0.7},
            {'a': 1.7, 'b': 1.7, 'c': 0.6, 'd': 1.2},
            {'a': -1.7, 'b': 1.3, 'c': -0.1, 'd': -1.2},
            {'a': 1.5, 'b': -1.8, 'c': 1.6, 'd': 0.9},
            {'a': -1.8, 'b': -2.0, 'c': -0.5, 'd': -0.9},
            {'a': 1.1, 'b': -1.3, 'c': 1.7, 'd': 0.5},
        ]
        self.__base_params = random.choice(presets)

        # Drift speeds for each parameter (slow sinusoidal)
        self.__drift_freq = {k: random.uniform(0.3, 0.8) for k in 'abcd'}
        self.__drift_phase = {k: random.uniform(0, 2 * math.pi) for k in 'abcd'}
        self.__drift_amp = {k: random.uniform(0.15, 0.3) for k in 'abcd'}

        # Current point
        self.__x = 0.1
        self.__y = 0.1

        # Track bounds for auto-fitting
        self.__x_min = self.__x_max = self.__x
        self.__y_min = self.__y_max = self.__y

        # More iterations = brighter, more filled display
        self.__iters_per_tick = max(500, self.__width * self.__height * 4)

    def _tick(self, tick):
        self.__time += 0.01

        t = self.__time

        # Slowly drift parameters around the preset
        a = self.__base_params['a'] + self.__drift_amp['a'] * math.sin(t * self.__drift_freq['a'] + self.__drift_phase['a'])
        b = self.__base_params['b'] + self.__drift_amp['b'] * math.sin(t * self.__drift_freq['b'] + self.__drift_phase['b'])
        c = self.__base_params['c'] + self.__drift_amp['c'] * math.sin(t * self.__drift_freq['c'] + self.__drift_phase['c'])
        d = self.__base_params['d'] + self.__drift_amp['d'] * math.sin(t * self.__drift_freq['d'] + self.__drift_phase['d'])

        # Fade existing density for trail effect
        self.__density *= 0.88

        # Vectorized iteration: compute all points from the last known state
        n = self.__iters_per_tick
        xs = np.empty(n)
        ys = np.empty(n)
        xs[0] = self.__x
        ys[0] = self.__y

        # The recurrence is sequential, but we can at least use numpy scalar ops
        for i in range(1, n):
            xs[i] = math.sin(a * ys[i - 1]) + c * math.cos(a * xs[i - 1])
            ys[i] = math.sin(b * xs[i - 1]) + d * math.cos(b * ys[i - 1])

        self.__x = xs[-1]
        self.__y = ys[-1]

        # Update running bounds with exponential smoothing
        cur_xmin, cur_xmax = xs.min(), xs.max()
        cur_ymin, cur_ymax = ys.min(), ys.max()
        alpha = 0.05
        self.__x_min += alpha * (cur_xmin - self.__x_min)
        self.__x_max += alpha * (cur_xmax - self.__x_max)
        self.__y_min += alpha * (cur_ymin - self.__y_min)
        self.__y_max += alpha * (cur_ymax - self.__y_max)

        # Map to pixel space using tracked bounds (auto-fit with padding)
        x_range = max(self.__x_max - self.__x_min, 0.1)
        y_range = max(self.__y_max - self.__y_min, 0.1)

        # Fit to display while preserving aspect ratio
        w, h = self.__width, self.__height
        scale = min((w - 2) / x_range, (h - 2) / y_range)
        cx = (self.__x_min + self.__x_max) / 2
        cy = (self.__y_min + self.__y_max) / 2

        px = ((xs - cx) * scale + w / 2).astype(int)
        py = ((ys - cy) * scale + h / 2).astype(int)

        # Accumulate hits into density buffer
        mask = (px >= 0) & (px < w) & (py >= 0) & (py < h)
        np.add.at(self.__density, (py[mask], px[mask]), 0.08)

        # Render with gamma curve for glow
        d = np.clip(self.__density, 0, 1)

        hue = (self.__hue_base + d * 0.35 + t * 0.03) % 1.0
        sat = np.where(d > 0.01, 0.55 + d * 0.4, 0.0)
        val = np.where(d > 0.01, d ** 0.5, 0.0)

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
