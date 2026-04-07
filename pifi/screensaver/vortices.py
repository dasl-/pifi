import numpy as np
import random

from pifi.config import Config
from pifi.screensaver.screensaver import Screensaver


class Vortices(Screensaver):
    """
    Descartes' Theory of Vortices.

    Irregular Voronoi cells with swirling spiral streamlines,
    inspired by the Principia Philosophiae illustrations of cosmic
    vortices filling all of space. Each cell is a whirlpool of
    matter with a bright center, rotating independently while
    packed edge-to-edge with its neighbors.
    """

    PALETTES = [
        # Antique manuscript — sepia, ochre, burnt umber
        [(0.55, 0.35, 0.15), (0.4, 0.22, 0.08), (0.7, 0.5, 0.25), (0.25, 0.12, 0.04)],
        # Cosmic ether — deep blues, violet, gold
        [(0.05, 0.08, 0.25), (0.15, 0.05, 0.35), (0.55, 0.45, 0.1), (0.08, 0.15, 0.4)],
        # Celestial — teal, silver, midnight
        [(0.08, 0.25, 0.35), (0.35, 0.45, 0.45), (0.04, 0.08, 0.18), (0.25, 0.5, 0.45)],
        # Solar — amber, crimson, deep orange
        [(0.7, 0.3, 0.05), (0.85, 0.15, 0.05), (0.3, 0.08, 0.03), (0.9, 0.55, 0.1)],
    ]

    def __init__(self, led_frame_player=None):
        super().__init__(led_frame_player)
        self.__width = Config.get_or_throw('leds.display_width')
        self.__height = Config.get_or_throw('leds.display_height')

    def _setup(self):
        self.__time = 0.0
        w, h = self.__width, self.__height

        # Generate irregular Voronoi cell centers
        avg_cell_size = max(3.0, min(w, h) / random.uniform(3.0, 5.5))
        num_cells = max(8, int(w * h / (avg_cell_size ** 2)))
        margin = avg_cell_size * 1.5

        centers_x = np.random.uniform(-margin, w + margin, num_cells)
        centers_y = np.random.uniform(-margin, h + margin, num_cells)

        # Lloyd relaxation for organic but even spacing
        for _ in range(4):
            gx_r, gy_r = np.meshgrid(
                np.linspace(-margin, w + margin, min(w * 2, 120)),
                np.linspace(-margin, h + margin, min(h * 2, 80))
            )
            px_r, py_r = gx_r.ravel(), gy_r.ravel()
            dx = centers_x[np.newaxis, :] - px_r[:, np.newaxis]
            dy = centers_y[np.newaxis, :] - py_r[:, np.newaxis]
            nearest_r = np.argmin(dx ** 2 + dy ** 2, axis=1)

            for ci in range(num_cells):
                mask = nearest_r == ci
                if np.any(mask):
                    centers_x[ci] = np.mean(px_r[mask])
                    centers_y[ci] = np.mean(py_r[mask])

        self.__centers_x = centers_x
        self.__centers_y = centers_y
        self.__num_cells = num_cells

        # Per-cell vortex properties
        self.__rotation_speed = (
            np.random.uniform(0.8, 2.5, num_cells)
            * np.random.choice([-1, 1], num_cells)
        )
        self.__num_arms = np.random.choice([2, 3], num_cells).astype(np.float64)
        self.__spiral_tightness = np.random.uniform(0.2, 0.6, num_cells)

        # Per-cell color phase
        self.__cell_phase = np.random.uniform(0, 1.0, num_cells)
        self.__phase_drift = (
            np.random.uniform(0.01, 0.04, num_cells)
            * np.random.choice([-1, 1], num_cells)
        )

        # Build Voronoi assignment for every pixel
        y_coords = np.arange(h, dtype=np.float64)
        x_coords = np.arange(w, dtype=np.float64)
        gx, gy = np.meshgrid(x_coords, y_coords)
        px, py = gx.ravel(), gy.ravel()
        num_px = len(px)

        cell_map = np.zeros(num_px, dtype=np.int32)
        cell_dist = np.zeros(num_px, dtype=np.float64)
        cell_angle = np.zeros(num_px, dtype=np.float64)

        chunk_size = 1000
        for start in range(0, num_px, chunk_size):
            end = min(start + chunk_size, num_px)
            dx = centers_x[np.newaxis, :] - px[start:end, np.newaxis]
            dy = centers_y[np.newaxis, :] - py[start:end, np.newaxis]
            dists_sq = dx ** 2 + dy ** 2
            nearest = np.argmin(dists_sq, axis=1)
            cell_map[start:end] = nearest

            pdx = px[start:end] - centers_x[nearest]
            pdy = py[start:end] - centers_y[nearest]
            cell_dist[start:end] = np.sqrt(pdx ** 2 + pdy ** 2)
            cell_angle[start:end] = np.arctan2(pdy, pdx)

        self.__cell_map = cell_map.reshape(h, w)
        self.__cell_dist = cell_dist.reshape(h, w)
        self.__cell_angle = cell_angle.reshape(h, w)

        # Compute cell radius (max distance) for normalization
        cell_radius = np.ones(num_cells, dtype=np.float64)
        flat_map = cell_map
        flat_dist = cell_dist
        for ci in range(num_cells):
            mask = flat_map == ci
            if np.any(mask):
                cell_radius[ci] = max(1.0, np.max(flat_dist[mask]))

        self.__norm_dist = self.__cell_dist / cell_radius[self.__cell_map]

        # Border darkening
        self.__border_dark = 1.0 - np.clip(self.__norm_dist, 0, 1) ** 2.5 * 0.55

        # Color palette
        palette = random.choice(self.PALETTES)
        self.__palette = np.array(palette)
        self.__palette_size = len(palette)

        # Global color drift
        self.__color_drift_speed = random.uniform(0.05, 0.15)

    def _tick(self, tick):
        self.__time += 0.02
        t = self.__time

        # Per-cell color from palette
        color_pos = (
            self.__cell_phase + t * self.__phase_drift + t * self.__color_drift_speed
        ) % 1.0
        palette_idx = color_pos * (self.__palette_size - 1)
        idx_low = np.clip(np.floor(palette_idx).astype(np.int32), 0, self.__palette_size - 1)
        idx_high = np.minimum(idx_low + 1, self.__palette_size - 1)
        frac = palette_idx - idx_low

        cell_r = self.__palette[idx_low, 0] * (1 - frac) + self.__palette[idx_high, 0] * frac
        cell_g = self.__palette[idx_low, 1] * (1 - frac) + self.__palette[idx_high, 1] * frac
        cell_b = self.__palette[idx_low, 2] * (1 - frac) + self.__palette[idx_high, 2] * frac

        # Spiral vortex pattern
        cell_ids = self.__cell_map
        rotation = (self.__rotation_speed * t)[cell_ids]
        arms = self.__num_arms[cell_ids]
        tightness = self.__spiral_tightness[cell_ids]

        phase = self.__cell_angle * arms + self.__cell_dist * tightness - rotation
        spiral = 0.5 + 0.5 * np.sin(phase)

        # Spiral is subtle at center (smooth core), strong at edge (visible streamlines)
        spiral_strength = np.clip(self.__norm_dist * 1.5, 0, 1)
        modulated = (1.0 - spiral_strength) + spiral_strength * spiral

        # Center glow — bright core at each vortex center
        center_glow = 1.0 + 0.3 * np.exp(-self.__norm_dist ** 2 * 5.0)

        brightness = modulated * center_glow * self.__border_dark

        frame_r = cell_r[cell_ids] * brightness
        frame_g = cell_g[cell_ids] * brightness
        frame_b = cell_b[cell_ids] * brightness

        frame = np.stack([
            (np.clip(frame_r, 0, 1) * 255).astype(np.uint8),
            (np.clip(frame_g, 0, 1) * 255).astype(np.uint8),
            (np.clip(frame_b, 0, 1) * 255).astype(np.uint8),
        ], axis=-1)

        self._led_frame_player.play_frame(frame)

    @classmethod
    def get_id(cls) -> str:
        return 'vortices'

    @classmethod
    def get_name(cls) -> str:
        return 'Vortices'

    @classmethod
    def get_description(cls) -> str:
        return "Descartes' cosmic vortex theory"
