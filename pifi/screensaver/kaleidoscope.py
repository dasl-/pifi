import numpy as np
import random

from pifi.screensaver.colorutils import hsv_to_rgb_uint8_frame
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

        self.__time = 0.0

    def _setup(self):
        self.__time = 0.0
        self.__hue_base = random.random()
        self.__speed = random.uniform(0.01, 0.02)

        # Number of symmetry axes
        self.__num_axes = random.choice([3, 4, 5, 6, 8])

        # Pre-compute polar coordinates from center
        cy, cx = self._height / 2, self._width / 2
        y = np.arange(self._height, dtype=np.float64) - cy
        x = np.arange(self._width, dtype=np.float64) - cx
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

        frame = hsv_to_rgb_uint8_frame(hue, sat, val)
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
