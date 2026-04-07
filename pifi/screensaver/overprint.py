import numpy as np
import random
import math

from pifi.config import Config
from pifi.screensaver.screensaver import Screensaver


class Overprint(Screensaver):
    """
    Risograph overprint — layered spot colors with additive mixing.

    2-3 layers of bold geometric shapes in limited spot colors. Where
    layers overlap, colors mix additively to create rich third colors.
    Shapes slowly drift and rotate, creating continuously evolving
    compositions.
    """

    # Classic riso color pairs/triples (as RGB floats)
    PALETTES = [
        # Pink + Blue
        [(0.95, 0.3, 0.5), (0.2, 0.4, 0.9)],
        # Orange + Teal
        [(0.95, 0.5, 0.15), (0.1, 0.7, 0.65)],
        # Red + Blue + Yellow
        [(0.9, 0.15, 0.2), (0.15, 0.3, 0.85), (0.95, 0.85, 0.15)],
        # Pink + Green
        [(0.95, 0.35, 0.55), (0.2, 0.75, 0.4)],
        # Coral + Purple
        [(0.95, 0.4, 0.35), (0.5, 0.25, 0.8)],
        # Yellow + Violet + Teal
        [(0.95, 0.8, 0.2), (0.6, 0.2, 0.7), (0.15, 0.65, 0.6)],
        # Fluorescent Pink + Blue + Green
        [(1.0, 0.2, 0.6), (0.2, 0.35, 0.95), (0.1, 0.85, 0.4)],
    ]

    def __init__(self, led_frame_player=None):
        super().__init__(led_frame_player)

        self.__width = Config.get_or_throw('leds.display_width')
        self.__height = Config.get_or_throw('leds.display_height')
        self.__time = 0.0

    def _setup(self):
        self.__time = 0.0

        # Pick a palette
        self.__colors = random.choice(self.PALETTES)
        self.__num_layers = len(self.__colors)

        # Pre-compute coordinate grids centered at origin
        cy, cx = self.__height / 2, self.__width / 2
        y = np.arange(self.__height, dtype=np.float64) - cy
        x = np.arange(self.__width, dtype=np.float64) - cx
        self.__gx, self.__gy = np.meshgrid(x, y)

        # Each layer gets random shape parameters
        self.__layers = []
        for i in range(self.__num_layers):
            layer = {
                'shape': random.choice(['circle', 'rect', 'blob', 'stripe']),
                'cx': random.uniform(-cx * 0.3, cx * 0.3),
                'cy': random.uniform(-cy * 0.3, cy * 0.3),
                'drift_angle': random.uniform(0, 2 * math.pi),
                'drift_speed': random.uniform(0.3, 0.8),
                'rot_speed': random.uniform(-0.2, 0.2),
                'size': random.uniform(0.4, 0.7) * min(self.__width, self.__height),
                'freq': random.uniform(0.8, 1.5),  # for stripe/blob
            }
            self.__layers.append(layer)

    def _tick(self, tick):
        self.__time += 0.012
        t = self.__time

        frame = np.zeros((self.__height, self.__width, 3), dtype=np.float64)

        for i, layer in enumerate(self.__layers):
            color = np.array(self.__colors[i])

            # Drifting center
            lcx = layer['cx'] + math.cos(layer['drift_angle'] + t * 0.5) * layer['drift_speed'] * 5
            lcy = layer['cy'] + math.sin(layer['drift_angle'] + t * 0.7) * layer['drift_speed'] * 4

            # Coordinates relative to layer center
            dx = self.__gx - lcx
            dy = self.__gy - lcy

            # Rotate
            angle = t * layer['rot_speed']
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)
            rx = dx * cos_a - dy * sin_a
            ry = dx * sin_a + dy * cos_a

            # Generate shape mask (0-1 with soft edges)
            size = layer['size'] * (0.9 + 0.1 * math.sin(t * 0.4 + i * 2))

            if layer['shape'] == 'circle':
                dist = np.sqrt(rx ** 2 + ry ** 2)
                mask = np.clip(1.0 - (dist - size * 0.4) / (size * 0.1), 0, 1)
            elif layer['shape'] == 'rect':
                # Soft-edged rectangle
                mx = np.clip(1.0 - (np.abs(rx) - size * 0.35) / (size * 0.08), 0, 1)
                my = np.clip(1.0 - (np.abs(ry) - size * 0.25) / (size * 0.08), 0, 1)
                mask = mx * my
            elif layer['shape'] == 'blob':
                # Organic blob — circle distorted by sine
                angle_field = np.arctan2(ry, rx)
                dist = np.sqrt(rx ** 2 + ry ** 2)
                wobble = size * 0.4 + size * 0.12 * np.sin(angle_field * layer['freq'] * 3 + t * 1.5)
                mask = np.clip(1.0 - (dist - wobble) / (size * 0.08), 0, 1)
            else:  # stripe
                # Thick stripes
                v = np.sin(rx * layer['freq'] * 0.3 + t * 0.8)
                mask = np.clip(v * 2, 0, 1)

            # Additive color mixing — this is the key riso quality
            frame[:, :, 0] += mask * color[0] * 0.7
            frame[:, :, 1] += mask * color[1] * 0.7
            frame[:, :, 2] += mask * color[2] * 0.7

        frame = (np.clip(frame, 0, 1) * 255).astype(np.uint8)
        self._led_frame_player.play_frame(frame)

    @classmethod
    def get_id(cls) -> str:
        return 'overprint'

    @classmethod
    def get_name(cls) -> str:
        return 'Overprint'

    @classmethod
    def get_description(cls) -> str:
        return 'Risograph spot color layers'
