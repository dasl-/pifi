import numpy as np
import random

from pifi.config import Config
from pifi.screensaver.screensaver import Screensaver


class Kaleidoscope(Screensaver):
    """
    Kaleidoscope — animated noise mirrored across multiple axes.

    Generates a pattern in polar coordinates and mirrors it across N
    symmetry axes from the center. The low resolution of LED matrices
    makes the symmetry read clearly.
    """

    def __init__(self, led_frame_player=None):
        super().__init__(led_frame_player)

        self.__width = Config.get_or_throw('leds.display_width')
        self.__height = Config.get_or_throw('leds.display_height')
        self.__time = 0.0

    def _setup(self):
        self.__time = 0.0
        self.__hue_base = random.random()
        self.__speed = random.uniform(0.01, 0.02)

        # Number of symmetry axes
        self.__num_axes = random.choice([3, 4, 5, 6, 8])

        # Pre-compute polar coordinates from center
        cy, cx = self.__height / 2, self.__width / 2
        y = np.arange(self.__height, dtype=np.float64) - cy
        x = np.arange(self.__width, dtype=np.float64) - cx
        gx, gy = np.meshgrid(x, y)

        self.__radius = np.sqrt(gx ** 2 + gy ** 2)
        max_r = max(self.__radius.max(), 1)
        self.__radius_norm = self.__radius / max_r

        # Fold angle into one segment, then mirror
        angle = np.arctan2(gy, gx)  # -pi to pi
        segment = 2 * np.pi / self.__num_axes
        # Fold into [0, segment) then mirror to create kaleidoscope
        folded = np.mod(angle, segment)
        self.__angle = np.where(folded > segment / 2, segment - folded, folded)

        # Random noise parameters
        self.__freqs = [random.uniform(2, 5) for _ in range(4)]
        self.__phases = [random.uniform(0, 10) for _ in range(6)]

    def _tick(self):
        self.__time += self.__speed

        t = self.__time
        a = self.__angle
        r = self.__radius_norm
        f = self.__freqs
        p = self.__phases

        # Generate pattern using folded angle and radius
        # Multiple sine layers for complexity
        v1 = np.sin(a * f[0] + r * f[1] * 6 + t * 3.0 + p[0])
        v2 = np.sin(r * f[2] * 8 - t * 2.0 + p[1]) * np.cos(a * f[3] + t * 1.5 + p[2])
        v3 = np.sin((a + r) * 5 + t * 2.5 + p[3]) * np.sin(r * 10 - t * 1.8 + p[4])

        pattern = (v1 + v2 + v3) / 3.0  # -1 to 1

        # Map to color
        hue = (self.__hue_base + pattern * 0.3 + r * 0.1 + t * 0.05) % 1.0
        sat = 0.6 + pattern * 0.2
        val = np.clip(0.1 + (pattern + 1) * 0.4 + (1 - r) * 0.15, 0, 1)

        frame = _hsv_to_rgb_vec(hue, sat, val)
        self._led_frame_player.play_frame(frame)

    @classmethod
    def get_id(cls) -> str:
        return 'kaleidoscope'

    @classmethod
    def get_name(cls) -> str:
        return 'Kaleidoscope'

    @classmethod
    def get_description(cls) -> str:
        return 'Mirrored animated patterns'


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
