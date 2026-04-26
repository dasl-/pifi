import numpy as np
import random
import math

from pifi.config import Config
from pifi.screensaver.screensaver import Screensaver


class Halftone(Screensaver):
    """
    Halftone drift — animated CMYK-style dot screen patterns.

    Each color channel is rendered as a halftone dot grid at a
    different screen angle. Dots slowly shift size and position,
    creating moiré interference between color separations. That
    "printed but alive" feeling.
    """

    def __init__(self, led_frame_player=None):
        super().__init__(led_frame_player)

        self.__width = Config.get_or_throw('leds.display_width')
        self.__height = Config.get_or_throw('leds.display_height')
        self.__time = 0.0

    def _setup(self):
        self.__time = 0.0

        # Pre-compute coordinate grids
        y = np.arange(self.__height, dtype=np.float64)
        x = np.arange(self.__width, dtype=np.float64)
        self.__gx, self.__gy = np.meshgrid(x, y)

        # Screen angles for each color channel (classic CMYK-ish angles)
        self.__angles = [
            random.uniform(0.1, 0.5),    # channel 1
            random.uniform(1.0, 1.4),    # channel 2
            random.uniform(1.8, 2.2),    # channel 3
        ]

        # Dot grid frequency (spacing)
        self.__freq = random.uniform(1.5, 2.5)

        # Color channels — riso-inspired spot colors
        palettes = [
            [(0.9, 0.15, 0.3), (0.1, 0.35, 0.85), (0.95, 0.8, 0.1)],  # red, blue, yellow
            [(0.95, 0.3, 0.5), (0.15, 0.7, 0.6), (0.9, 0.6, 0.1)],    # pink, teal, orange
            [(0.85, 0.2, 0.2), (0.2, 0.7, 0.3), (0.3, 0.2, 0.8)],     # red, green, purple
        ]
        self.__palette = random.choice(palettes)

        # Underlying pattern — slowly moving gradient that drives dot sizes
        self.__pattern_speed = random.uniform(0.005, 0.012)
        self.__pattern_phases = [random.uniform(0, 10) for _ in range(6)]

    def _tick(self):
        self.__time += self.__pattern_speed
        t = self.__time

        gx, gy = self.__gx, self.__gy
        p = self.__pattern_phases
        w, h = self.__width, self.__height

        frame = np.zeros((self.__height, self.__width, 3), dtype=np.float64)

        for ch in range(3):
            angle = self.__angles[ch] + t * 0.3
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)

            # Rotate grid for this channel's screen angle
            rx = gx * cos_a - gy * sin_a
            ry = gx * sin_a + gy * cos_a

            # Halftone dot pattern: distance to nearest grid point
            freq = self.__freq
            # Fractional position within each cell (0-1)
            cell_x = np.mod(rx * freq / max(w, h) * 6 + t * 2, 1.0) - 0.5
            cell_y = np.mod(ry * freq / max(w, h) * 6 + t * 1.5, 1.0) - 0.5
            cell_dist = np.sqrt(cell_x ** 2 + cell_y ** 2)

            # Underlying "image" that drives dot sizes — flowing gradients
            image_val = (
                np.sin(gx / w * 4 + t * 3 + p[ch * 2]) *
                np.cos(gy / h * 3 + t * 2 + p[ch * 2 + 1]) + 1
            ) / 2  # 0-1

            # Dot radius proportional to image value
            # Larger image_val = larger dot = more color
            dot_radius = image_val * 0.45

            # Sharp threshold: pixel is "on" if distance to cell center < dot radius
            dot_mask = np.where(cell_dist < dot_radius, 1.0, 0.0)

            # Apply color
            color = self.__palette[ch]
            frame[:, :, 0] += dot_mask * color[0] * 0.65
            frame[:, :, 1] += dot_mask * color[1] * 0.65
            frame[:, :, 2] += dot_mask * color[2] * 0.65

        frame = (np.clip(frame, 0, 1) * 255).astype(np.uint8)
        self._led_frame_player.play_frame(frame)

    @classmethod
    def get_id(cls) -> str:
        return 'halftone'

    @classmethod
    def get_name(cls) -> str:
        return 'Halftone'

    @classmethod
    def get_description(cls) -> str:
        return 'Animated dot screen patterns'
