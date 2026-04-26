import numpy as np
import random
import math

from pifi.config import Config
from pifi.screensaver.screensaver import Screensaver


class HexGrid(Screensaver):
    """
    Hex grid — compound eye with color waves.

    A hexagonal tessellation where each cell pulses with color.
    Waves propagate across the grid as ripples, spirals, or
    sweeps, creating an organic, hypnotic pattern like looking
    into a dragonfly's compound eye.
    """

    PALETTES = [
        # Jewel tones
        [(0.6, 0.1, 0.3), (0.2, 0.1, 0.6), (0.1, 0.5, 0.5), (0.7, 0.5, 0.1)],
        # Dragonfly iridescent
        [(0.0, 0.4, 0.3), (0.1, 0.6, 0.5), (0.3, 0.2, 0.6), (0.0, 0.3, 0.7)],
        # Ember
        [(0.8, 0.2, 0.05), (0.9, 0.5, 0.05), (0.6, 0.05, 0.1), (0.95, 0.8, 0.2)],
        # Ocean
        [(0.0, 0.15, 0.4), (0.0, 0.3, 0.6), (0.1, 0.5, 0.5), (0.0, 0.2, 0.3)],
        # Aurora
        [(0.1, 0.7, 0.4), (0.1, 0.4, 0.7), (0.4, 0.1, 0.6), (0.2, 0.8, 0.6)],
    ]

    def __init__(self, led_frame_player=None):
        super().__init__(led_frame_player)

        self.__width = Config.get_or_throw('leds.display_width')
        self.__height = Config.get_or_throw('leds.display_height')

    def _setup(self):
        self.__time = 0.0
        w, h = self.__width, self.__height

        # Hex cell size (pixels per cell radius)
        self.__cell_size = max(2.0, min(w, h) / random.uniform(4, 8))
        cs = self.__cell_size

        # Pointy-top hex grid spacing
        col_spacing = cs * math.sqrt(3)
        row_spacing = cs * 1.5

        # Generate hex cell centers
        centers = []
        col_count = int(w / col_spacing) + 3
        row_count = int(h / row_spacing) + 3

        for row in range(row_count):
            for col in range(col_count):
                cx = col * col_spacing + (0.5 * col_spacing if row % 2 else 0)
                cy = row * row_spacing
                cx -= col_spacing
                cy -= row_spacing
                centers.append((cx, cy))

        self.__centers = np.array(centers)
        self.__num_cells = len(centers)

        # For each pixel, find nearest hex center (Voronoi assignment)
        y_coords = np.arange(h, dtype=np.float64)
        x_coords = np.arange(w, dtype=np.float64)
        gx, gy = np.meshgrid(x_coords, y_coords)

        px = gx.ravel()
        py = gy.ravel()

        self.__cell_map = np.zeros(h * w, dtype=np.int32)
        self.__cell_dist = np.zeros(h * w, dtype=np.float64)

        chunk_size = 1000
        for start in range(0, len(px), chunk_size):
            end = min(start + chunk_size, len(px))
            dx = self.__centers[:, 0][np.newaxis, :] - px[start:end, np.newaxis]
            dy = self.__centers[:, 1][np.newaxis, :] - py[start:end, np.newaxis]
            dists = dx ** 2 + dy ** 2
            nearest = np.argmin(dists, axis=1)
            self.__cell_map[start:end] = nearest
            self.__cell_dist[start:end] = np.sqrt(dists[np.arange(end - start), nearest])

        self.__cell_map = self.__cell_map.reshape(h, w)
        self.__cell_dist = self.__cell_dist.reshape(h, w)

        # Border darkening
        self.__border_brightness = 1.0 - np.clip(self.__cell_dist / (cs * 0.85), 0, 1) ** 3 * 0.6

        # Cell center positions for wave calculations
        self.__cell_cx = self.__centers[:, 0]
        self.__cell_cy = self.__centers[:, 1]

        # Wave mode
        self.__wave_mode = random.choice(['ripple', 'spiral', 'sweep', 'dual_ripple'])

        # Wave source points
        self.__wave_x = random.uniform(0, w)
        self.__wave_y = random.uniform(0, h)
        self.__wave_x2 = random.uniform(0, w)
        self.__wave_y2 = random.uniform(0, h)

        # Sweep direction
        self.__sweep_angle = random.uniform(0, 2 * math.pi)

        # Color palette
        palette = random.choice(self.PALETTES)
        self.__palette = np.array(palette)
        self.__palette_size = len(palette)

        # Animation speeds
        self.__wave_speed = random.uniform(1.5, 3.0)
        self.__color_drift = random.uniform(0.1, 0.3)

    def _tick(self):
        self.__time += 0.015
        t = self.__time
        w, h = self.__width, self.__height

        cx = self.__cell_cx
        cy = self.__cell_cy

        if self.__wave_mode == 'ripple':
            dist = np.sqrt((cx - self.__wave_x) ** 2 + (cy - self.__wave_y) ** 2)
            scale = max(w, h)
            wave = np.sin(dist / scale * 20 - t * self.__wave_speed)

        elif self.__wave_mode == 'spiral':
            dist = np.sqrt((cx - w / 2) ** 2 + (cy - h / 2) ** 2)
            angle = np.arctan2(cy - h / 2, cx - w / 2)
            scale = max(w, h)
            wave = np.sin(dist / scale * 15 + angle * 2 - t * self.__wave_speed)

        elif self.__wave_mode == 'sweep':
            proj = cx * math.cos(self.__sweep_angle) + cy * math.sin(self.__sweep_angle)
            scale = max(w, h)
            wave = np.sin(proj / scale * 12 - t * self.__wave_speed)
            proj2 = -cx * math.sin(self.__sweep_angle) + cy * math.cos(self.__sweep_angle)
            wave += 0.3 * np.sin(proj2 / scale * 8 - t * self.__wave_speed * 0.7)
            wave /= 1.3

        else:  # dual_ripple
            d1 = np.sqrt((cx - self.__wave_x) ** 2 + (cy - self.__wave_y) ** 2)
            d2 = np.sqrt((cx - self.__wave_x2) ** 2 + (cy - self.__wave_y2) ** 2)
            scale = max(w, h)
            wave = 0.5 * (
                np.sin(d1 / scale * 18 - t * self.__wave_speed) +
                np.sin(d2 / scale * 14 - t * self.__wave_speed * 0.8)
            )

        # Map wave to palette
        palette_pos = (wave * 0.5 + 0.5 + t * self.__color_drift) % 1.0
        palette_idx = palette_pos * (self.__palette_size - 1)

        idx_low = np.floor(palette_idx).astype(np.int32)
        idx_high = np.minimum(idx_low + 1, self.__palette_size - 1)
        frac = palette_idx - idx_low
        idx_low = np.clip(idx_low, 0, self.__palette_size - 1)

        cell_r = self.__palette[idx_low, 0] * (1 - frac) + self.__palette[idx_high, 0] * frac
        cell_g = self.__palette[idx_low, 1] * (1 - frac) + self.__palette[idx_high, 1] * frac
        cell_b = self.__palette[idx_low, 2] * (1 - frac) + self.__palette[idx_high, 2] * frac

        # Shimmer
        shimmer = 0.85 + 0.15 * np.sin(t * 3 + np.arange(self.__num_cells) * 0.7)
        cell_r *= shimmer
        cell_g *= shimmer
        cell_b *= shimmer

        # Scatter to pixels
        frame_r = cell_r[self.__cell_map] * self.__border_brightness
        frame_g = cell_g[self.__cell_map] * self.__border_brightness
        frame_b = cell_b[self.__cell_map] * self.__border_brightness

        frame = np.stack([
            (np.clip(frame_r, 0, 1) * 255).astype(np.uint8),
            (np.clip(frame_g, 0, 1) * 255).astype(np.uint8),
            (np.clip(frame_b, 0, 1) * 255).astype(np.uint8),
        ], axis=-1)

        self._led_frame_player.play_frame(frame)

    @classmethod
    def get_id(cls) -> str:
        return 'hex_grid'

    @classmethod
    def get_name(cls) -> str:
        return 'Hex Grid'

    @classmethod
    def get_description(cls) -> str:
        return 'Compound eye color waves'
