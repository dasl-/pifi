import numpy as np
import random
import math

from pifi.config import Config
from pifi.screensaver.screensaver import Screensaver


class Moire(Screensaver):
    """
    Moire interference patterns.

    Overlays 2-3 slowly rotating/drifting sets of concentric circles
    or line gratings. The interference between the patterns creates
    mesmerizing flowing shapes from trivially simple math.
    """

    def __init__(self, led_frame_player=None):
        super().__init__(led_frame_player)

        self.__width = Config.get_or_throw('leds.display_width')
        self.__height = Config.get_or_throw('leds.display_height')
        self.__time = 0.0

    def _setup(self):
        self.__time = 0.0
        self.__hue_base = random.random()
        self.__speed = random.uniform(0.008, 0.015)

        # Pre-compute coordinate grid
        y = np.arange(self.__height, dtype=np.float64)
        x = np.arange(self.__width, dtype=np.float64)
        self.__gx, self.__gy = np.meshgrid(x, y)

        # 2-3 pattern layers, each with:
        # - center offset from display center
        # - rotation speed
        # - frequency (ring spacing)
        # - drift speed and angle
        self.__num_layers = random.choice([2, 3])
        self.__layers = []
        cx, cy = self.__width / 2, self.__height / 2

        for i in range(self.__num_layers):
            layer = {
                'cx': cx + random.uniform(-2, 2),
                'cy': cy + random.uniform(-2, 2),
                'freq': random.uniform(0.8, 1.8),
                'rot_speed': random.uniform(-0.3, 0.3),
                'drift_angle': random.uniform(0, 2 * math.pi),
                'drift_speed': random.uniform(0.3, 0.8),
                'phase': random.uniform(0, 2 * math.pi),
            }
            # Ensure at least some rotation difference between layers
            if i > 0:
                layer['rot_speed'] = self.__layers[0]['rot_speed'] + random.uniform(0.15, 0.4) * random.choice([-1, 1])
            self.__layers.append(layer)

    def _tick(self, tick):
        self.__time += self.__speed

        t = self.__time
        gx, gy = self.__gx, self.__gy

        # Accumulate interference from all layers
        combined = np.zeros_like(gx)

        for layer in self.__layers:
            # Drifting center
            lcx = layer['cx'] + math.cos(layer['drift_angle'] + t * 2) * layer['drift_speed'] * 3
            lcy = layer['cy'] + math.sin(layer['drift_angle'] + t * 2) * layer['drift_speed'] * 3

            dx = gx - lcx
            dy = gy - lcy

            # Rotate
            angle = t * layer['rot_speed']
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)
            rx = dx * cos_a - dy * sin_a
            ry = dx * sin_a + dy * cos_a

            # Concentric rings (distance from center)
            dist = np.sqrt(rx ** 2 + ry ** 2)
            combined += np.sin(dist * layer['freq'] * 2 + layer['phase'] + t * 0.5)

        # Normalize to 0-1
        combined = (combined / self.__num_layers + 1) / 2

        # Map to color — use the interference value for hue variation
        hue = (self.__hue_base + combined * 0.4 + t * 0.02) % 1.0
        sat = 0.6 + combined * 0.3
        val = np.clip(combined * 0.85 + 0.1, 0, 1)

        frame = _hsv_to_rgb_vec(hue, sat, val)
        self._led_frame_player.play_frame(frame)

    @classmethod
    def get_id(cls) -> str:
        return 'moire'

    @classmethod
    def get_name(cls) -> str:
        return 'Moire'

    @classmethod
    def get_description(cls) -> str:
        return 'Rotating interference patterns'


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
