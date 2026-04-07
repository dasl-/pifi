import numpy as np
import random
import math

from pifi.config import Config
from pifi.screensaver.screensaver import Screensaver


class NoiseGradient(Screensaver):
    """
    Noise gradient drift — James Turrell-inspired ambient light.

    A smooth gradient that very slowly rotates, shifts hue, and gets
    subtly perturbed by noise. Almost nothing happening — but on a
    physical LED matrix the color depth and glow make it meditative
    and beautiful.
    """

    def __init__(self, led_frame_player=None):
        super().__init__(led_frame_player)

        self.__width = Config.get_or_throw('leds.display_width')
        self.__height = Config.get_or_throw('leds.display_height')
        self.__time = 0.0

    def _setup(self):
        self.__time = 0.0

        # Pre-compute coordinate grids (normalized 0-1)
        y = np.linspace(0, 1, self.__height, dtype=np.float64)
        x = np.linspace(0, 1, self.__width, dtype=np.float64)
        self.__gx, self.__gy = np.meshgrid(x, y)

        # Starting hue and gradient angle
        self.__hue = random.random()
        self.__hue_speed = random.uniform(0.0005, 0.0015)
        self.__angle = random.uniform(0, 2 * math.pi)
        self.__angle_speed = random.uniform(0.001, 0.003)

        # Gradient hue range — how much hue shifts across the gradient
        self.__hue_range = random.uniform(0.08, 0.2)

        # Noise parameters for subtle perturbation
        self.__noise_phases = [random.uniform(0, 100) for _ in range(6)]
        self.__noise_strength = random.uniform(0.01, 0.03)

        # Brightness breathing
        self.__breath_speed = random.uniform(0.3, 0.6)
        self.__base_val = random.uniform(0.45, 0.65)

    def _tick(self, tick):
        self.__time += 0.015
        t = self.__time

        # Slowly rotate gradient angle
        self.__angle += self.__angle_speed
        angle = self.__angle

        # Gradient direction
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)

        # Project coordinates onto gradient axis (0-1)
        gx = self.__gx - 0.5
        gy = self.__gy - 0.5
        projection = (gx * cos_a + gy * sin_a + 0.5)
        projection = np.clip(projection, 0, 1)

        # Slowly shift base hue
        self.__hue = (self.__hue + self.__hue_speed) % 1.0

        # Hue varies along gradient
        hue = (self.__hue + projection * self.__hue_range) % 1.0

        # Subtle noise perturbation
        p = self.__noise_phases
        noise = (
            np.sin(self.__gx * 5 + t * 0.7 + p[0]) *
            np.cos(self.__gy * 4 + t * 0.5 + p[1]) *
            self.__noise_strength +
            np.sin((self.__gx + self.__gy) * 3 + t * 0.3 + p[2]) *
            self.__noise_strength * 0.5
        )

        hue = (hue + noise) % 1.0

        # Saturation — high but with subtle variation
        sat = 0.6 + 0.15 * np.sin(projection * 3 + t * 0.4 + p[3])

        # Value — gentle breathing with gradient variation
        breath = self.__base_val + 0.08 * math.sin(t * self.__breath_speed)
        val = breath + projection * 0.15 + noise * 2
        val = np.clip(val, 0.2, 0.85)

        frame = _hsv_to_rgb_vec(hue, sat, val)
        self._led_frame_player.play_frame(frame)

    @classmethod
    def get_id(cls) -> str:
        return 'noise_gradient'

    @classmethod
    def get_name(cls) -> str:
        return 'Noise Gradient'

    @classmethod
    def get_description(cls) -> str:
        return 'Ambient drifting color light'


def _hsv_to_rgb_vec(h, s, v):
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
