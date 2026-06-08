import numpy as np
import random
import math

from pifi.screensaver.colorutils import hsv_to_rgb_uint8_frame
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

        self.__time = 0.0

    def _setup(self):
        self.__time = 0.0
        self.__hue_base = random.random()
        self.__speed = random.uniform(0.008, 0.015)

        # Pre-compute coordinate grid
        y = np.arange(self._height, dtype=np.float64)
        x = np.arange(self._width, dtype=np.float64)
        self.__gx, self.__gy = np.meshgrid(x, y)

        # 2-3 pattern layers, each with:
        # - center offset from display center
        # - rotation speed
        # - frequency (ring spacing)
        # - drift speed and angle
        self.__num_layers = random.choice([2, 3])
        self.__layers = []
        cx, cy = self._width / 2, self._height / 2

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

    def _tick(self):
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

        frame = hsv_to_rgb_uint8_frame(hue, sat, val)
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
