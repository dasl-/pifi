import numpy as np
import random
import math  # pyright: ignore[reportUnusedImport]

from pifi.config import Config
from pifi.screensaver.screensaver import Screensaver


class OpArt(Screensaver):
    """
    Op art — Bridget Riley-inspired optical illusion patterns.

    High-contrast geometric patterns (stripes, concentric shapes,
    chevrons) that slowly shift phase, creating the illusion of
    movement and depth. Mostly black and white with optional
    limited color palette.
    """

    def __init__(self, led_frame_player=None):
        super().__init__(led_frame_player)

        self.__width = Config.get_or_throw('leds.display_width')
        self.__height = Config.get_or_throw('leds.display_height')
        self.__time = 0.0

    def _setup(self):
        self.__time = 0.0
        self.__speed = random.uniform(0.008, 0.015)

        # Pre-compute coordinate grids
        cy, cx = self.__height / 2, self.__width / 2
        y = np.arange(self.__height, dtype=np.float64) - cy
        x = np.arange(self.__width, dtype=np.float64) - cx
        self.__gx, self.__gy = np.meshgrid(x, y)
        self.__dist = np.sqrt(self.__gx ** 2 + self.__gy ** 2)
        self.__angle = np.arctan2(self.__gy, self.__gx)

        # Pattern type
        self.__pattern = random.choice([
            'concentric',
            'stripes',
            'chevron',
            'radial',
            'diamonds',
            'warp',
        ])

        # Color mode
        self.__color_mode = random.choices(
            ['bw', 'tinted', 'duo'],
            weights=[4, 3, 2],
        )[0]

        if self.__color_mode == 'tinted':
            self.__tint_hue = random.random()
        elif self.__color_mode == 'duo':
            self.__hue_a = random.random()
            self.__hue_b = (self.__hue_a + random.uniform(0.3, 0.5)) % 1.0

        # Pattern parameters
        self.__freq = random.uniform(0.6, 1.5)
        self.__warp_strength = random.uniform(0.3, 0.8)
        self.__slices = random.choice([6, 8, 10, 12])

    def _tick(self):
        self.__time += self.__speed
        t = self.__time

        gx, gy = self.__gx, self.__gy
        dist = self.__dist
        angle = self.__angle
        freq = self.__freq

        # Generate the base pattern value (-1 to 1)
        if self.__pattern == 'concentric':
            # Expanding/contracting rings
            v = np.sin(dist * freq - t * 8)
            # Add subtle angular modulation for depth
            v += np.sin(angle * 3 + t * 2) * 0.15
        elif self.__pattern == 'stripes':
            # Wavy stripes
            warp = np.sin(gy * 0.3 + t * 3) * self.__warp_strength * 3
            v = np.sin((gx + warp) * freq + t * 4)
        elif self.__pattern == 'chevron':
            # V-shaped patterns
            v = np.sin((np.abs(gx) + gy * 0.7) * freq + t * 5)
        elif self.__pattern == 'radial':
            # Rotating pie slices
            v = np.sin(angle * self.__slices + dist * 0.3 - t * 6)
        elif self.__pattern == 'diamonds':
            # Rotated grid
            rot_x = gx * 0.7 + gy * 0.7
            rot_y = -gx * 0.7 + gy * 0.7
            v = np.sin(rot_x * freq + t * 3) * np.sin(rot_y * freq + t * 2)
        else:  # warp
            # Distorted grid
            wx = gx + np.sin(gy * 0.4 + t * 3) * self.__warp_strength * 4
            wy = gy + np.sin(gx * 0.4 + t * 2) * self.__warp_strength * 4
            v = np.sin(wx * freq) * np.cos(wy * freq)

        # Threshold to create sharp black/white (op art is high contrast)
        sharp = np.where(v > 0, 1.0, 0.0)

        # Apply color
        if self.__color_mode == 'bw':
            frame = np.stack([sharp * 255] * 3, axis=-1).astype(np.uint8)
        elif self.__color_mode == 'tinted':
            h = self.__tint_hue
            # White areas get the tint, black stays black
            r, g, b = _hsv_to_rgb_scalar(h, 0.6, 1.0)
            frame = np.stack([
                (sharp * r * 255).astype(np.uint8),
                (sharp * g * 255).astype(np.uint8),
                (sharp * b * 255).astype(np.uint8),
            ], axis=-1)
        else:  # duo
            r_a, g_a, b_a = _hsv_to_rgb_scalar(self.__hue_a, 0.7, 0.9)
            r_b, g_b, b_b = _hsv_to_rgb_scalar(self.__hue_b, 0.7, 0.9)
            frame = np.stack([
                (sharp * r_a * 255 + (1 - sharp) * r_b * 255).astype(np.uint8),
                (sharp * g_a * 255 + (1 - sharp) * g_b * 255).astype(np.uint8),
                (sharp * b_a * 255 + (1 - sharp) * b_b * 255).astype(np.uint8),
            ], axis=-1)

        self._led_frame_player.play_frame(frame)

    @classmethod
    def get_id(cls) -> str:
        return 'opart'

    @classmethod
    def get_name(cls) -> str:
        return 'Op Art'

    @classmethod
    def get_description(cls) -> str:
        return 'Optical illusion patterns'


def _hsv_to_rgb_scalar(h, s, v):
    h = h % 1.0
    i = int(h * 6)
    f = h * 6 - i
    p = v * (1 - s)
    q = v * (1 - s * f)
    t = v * (1 - s * (1 - f))
    i = i % 6
    if i == 0: return v, t, p
    elif i == 1: return q, v, p
    elif i == 2: return p, v, t
    elif i == 3: return p, q, v
    elif i == 4: return t, p, v
    else: return v, p, q
