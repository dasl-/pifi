import numpy as np
import random

from pifi.config import Config
from pifi.screensaver.screensaver import Screensaver


class Escher(Screensaver):
    """
    Escher — interlocking tessellation with metamorphosis.

    Domain-warped checkerboard creates interlocking shapes that
    tile the plane without gaps, inspired by M.C. Escher's
    Regular Division of the Plane woodcuts. Boundaries undulate
    and morph while color waves propagate across the grid.
    """

    PALETTES = [
        # Figure/ground pairs (Escher used strong contrast)
        [(0.08, 0.10, 0.18), (0.72, 0.65, 0.50)],  # Ink / parchment
        [(0.12, 0.18, 0.42), (0.80, 0.60, 0.20)],  # Deep blue / gold
        [(0.05, 0.28, 0.32), (0.80, 0.35, 0.25)],  # Teal / coral
        [(0.10, 0.30, 0.12), (0.50, 0.18, 0.50)],  # Forest / plum
        [(0.60, 0.22, 0.10), (0.12, 0.22, 0.48)],  # Rust / cobalt
    ]

    def __init__(self, led_frame_player=None):
        super().__init__(led_frame_player)
        self.__width = Config.get_or_throw('leds.display_width')
        self.__height = Config.get_or_throw('leds.display_height')

    def _setup(self):
        self.__time = 0.0
        w, h = self.__width, self.__height

        # Tile size
        self.__tile_size = max(3.0, min(w, h) / random.uniform(2.5, 4.5))
        ts = self.__tile_size

        # Warp: 2 harmonics for complex interlocking boundaries
        self.__warp_amp = ts * random.uniform(0.15, 0.30)
        self.__freq_y = random.uniform(0.7, 1.3) * 2 * np.pi / ts
        self.__freq_x = random.uniform(0.7, 1.3) * 2 * np.pi / ts
        self.__freq2_y = self.__freq_y * random.uniform(1.8, 2.5)
        self.__freq2_x = self.__freq_x * random.uniform(1.8, 2.5)
        self.__amp2_ratio = random.uniform(0.2, 0.4)

        # Pixel grids
        gy, gx = np.mgrid[0:h, 0:w].astype(np.float64)
        self.__px = gx
        self.__py = gy

        # Colors
        pair = random.choice(self.PALETTES)
        self.__color_a = np.array(pair[0])
        self.__color_b = np.array(pair[1])

        # Animation
        self.__morph_speed = random.uniform(0.3, 0.6)
        self.__scroll_speed = random.uniform(0.04, 0.12)
        self.__scroll_angle = random.uniform(0, 2 * np.pi)

    def _tick(self):
        self.__time += 0.015
        t = self.__time
        ts = self.__tile_size

        # Animated warp phases
        phase_y = t * self.__morph_speed
        phase_x = t * self.__morph_speed * 0.7

        # Breathing amplitude
        amp = self.__warp_amp * (0.4 + 0.6 * (0.5 + 0.5 * np.sin(t * 0.25)))
        amp2 = amp * self.__amp2_ratio

        # Domain warp: sine distortion makes tile boundaries interlock
        warp_x = (amp * np.sin(self.__py * self.__freq_y + phase_y) +
                  amp2 * np.sin(self.__py * self.__freq2_y + phase_y * 1.7))
        warp_y = (amp * np.sin(self.__px * self.__freq_x + phase_x) +
                  amp2 * np.sin(self.__px * self.__freq2_x + phase_x * 1.3))

        # Slow scroll
        scroll_x = t * self.__scroll_speed * ts * np.cos(self.__scroll_angle)
        scroll_y = t * self.__scroll_speed * ts * np.sin(self.__scroll_angle)

        effective_x = self.__px - warp_x + scroll_x
        effective_y = self.__py - warp_y + scroll_y

        # Tile assignment (checkerboard in warped space)
        col = np.floor(effective_x / ts).astype(np.int32)
        row = np.floor(effective_y / ts).astype(np.int32)
        tile_type = (col + row) % 2

        # Position within tile (0–1)
        frac_x = (effective_x / ts) % 1.0
        frac_y = (effective_y / ts) % 1.0

        # Woodcut edge lines (dark boundary between tiles)
        edge = np.minimum(
            np.minimum(frac_x, 1.0 - frac_x),
            np.minimum(frac_y, 1.0 - frac_y)
        )
        edge_line = np.exp(-(edge ** 2) / 0.004) * 0.5

        # Subtle internal shading (brighter at tile center)
        center_dist = np.sqrt((frac_x - 0.5) ** 2 + (frac_y - 0.5) ** 2)
        shade = 0.82 + 0.18 * np.cos(center_dist * np.pi)

        # Color assignment
        is_a = (tile_type == 0)
        r = np.where(is_a, self.__color_a[0], self.__color_b[0])
        g = np.where(is_a, self.__color_a[1], self.__color_b[1])
        b = np.where(is_a, self.__color_a[2], self.__color_b[2])

        brightness = shade * (1.0 - edge_line)
        r *= brightness
        g *= brightness
        b *= brightness

        frame = np.stack([
            (np.clip(r, 0, 1) * 255).astype(np.uint8),
            (np.clip(g, 0, 1) * 255).astype(np.uint8),
            (np.clip(b, 0, 1) * 255).astype(np.uint8),
        ], axis=-1)

        self._led_frame_player.play_frame(frame)

    @classmethod
    def get_id(cls) -> str:
        return 'escher'

    @classmethod
    def get_name(cls) -> str:
        return 'Escher'

    @classmethod
    def get_description(cls) -> str:
        return 'Interlocking tessellation metamorphosis'
