import numpy as np
import random
import math

from pifi.config import Config
from pifi.screensaver.screensaver import Screensaver


class Misprint(Screensaver):
    """
    Misregistered geometry — off-register risograph printing.

    Bold graphic shapes rendered in 2-3 color passes with slight
    misalignment that slowly drifts. The off-register look is the
    most iconic risograph quality — handmade imperfection in
    mechanical reproduction.
    """

    PALETTES = [
        [(0.95, 0.25, 0.4), (0.15, 0.35, 0.9)],
        [(0.95, 0.5, 0.1), (0.2, 0.6, 0.7)],
        [(0.9, 0.2, 0.25), (0.15, 0.3, 0.85), (0.95, 0.85, 0.15)],
        [(0.95, 0.3, 0.55), (0.15, 0.7, 0.4)],
        [(1.0, 0.3, 0.5), (0.2, 0.3, 0.9), (0.1, 0.8, 0.4)],
    ]

    def __init__(self, led_frame_player=None):
        super().__init__(led_frame_player)

        self.__width = Config.get_or_throw('leds.display_width')
        self.__height = Config.get_or_throw('leds.display_height')
        self.__time = 0.0

    def _setup(self):
        self.__time = 0.0

        self.__colors = random.choice(self.PALETTES)
        self.__num_passes = len(self.__colors)

        # Pre-compute coordinates
        cy, cx = self.__height / 2, self.__width / 2
        y = np.arange(self.__height, dtype=np.float64) - cy
        x = np.arange(self.__width, dtype=np.float64) - cx
        self.__gx, self.__gy = np.meshgrid(x, y)
        self.__dist = np.sqrt(self.__gx ** 2 + self.__gy ** 2)
        self.__angle = np.arctan2(self.__gy, self.__gx)

        # Pick a composition — the shapes that will be "printed"
        self.__composition = random.choice([
            'circles',
            'bars',
            'grid',
            'arcs',
            'blocks',
        ])

        # Per-pass registration offset drift parameters
        self.__offsets = []
        for i in range(self.__num_passes):  # pyright: ignore[reportUnusedVariable]
            self.__offsets.append({
                'dx_phase': random.uniform(0, 2 * math.pi),
                'dy_phase': random.uniform(0, 2 * math.pi),
                'dx_speed': random.uniform(0.3, 0.7),
                'dy_speed': random.uniform(0.3, 0.7),
                'max_drift': random.uniform(1.5, 3.0),
            })

        # Composition movement
        self.__comp_rot_speed = random.uniform(-0.1, 0.1)
        self.__comp_drift = random.uniform(0.3, 0.6)

        # Pre-compute block sizes for the 'blocks' composition so
        # __render_composition stays deterministic across ticks.
        self.__block_sizes = [
            (random.uniform(0.2, 0.35), random.uniform(0.15, 0.25))
            for _ in range(3)
        ]

    def _tick(self):
        self.__time += 0.012
        t = self.__time

        frame = np.zeros((self.__height, self.__width, 3), dtype=np.float64)

        for i in range(self.__num_passes):
            color = np.array(self.__colors[i])
            off = self.__offsets[i]

            # Misregistration offset — slowly drifting
            dx = math.sin(t * off['dx_speed'] + off['dx_phase']) * off['max_drift']
            dy = math.cos(t * off['dy_speed'] + off['dy_phase']) * off['max_drift']

            # Shifted coordinates for this color pass
            sx = self.__gx - dx
            sy = self.__gy - dy

            # Slight rotation per pass
            rot = t * self.__comp_rot_speed + i * 0.02
            cos_r = math.cos(rot)
            sin_r = math.sin(rot)
            rx = sx * cos_r - sy * sin_r
            ry = sx * sin_r + sy * cos_r

            # Generate the composition shape
            mask = self.__render_composition(rx, ry, t)

            # Additive mixing
            frame[:, :, 0] += mask * color[0] * 0.7
            frame[:, :, 1] += mask * color[1] * 0.7
            frame[:, :, 2] += mask * color[2] * 0.7

        frame = (np.clip(frame, 0, 1) * 255).astype(np.uint8)
        self._led_frame_player.play_frame(frame)

    def __render_composition(self, gx, gy, t):
        """Render the composition shapes as a 0-1 mask."""
        w, h = self.__width, self.__height
        scale = min(w, h)

        if self.__composition == 'circles':
            # Concentric circles with gaps
            dist = np.sqrt(gx ** 2 + gy ** 2)
            v = np.sin(dist / scale * 15 + t * 0.5)
            return np.where(v > 0.1, 0.9, 0.0)

        elif self.__composition == 'bars':
            # Thick horizontal bars
            v = np.sin(gy / scale * 8 + t * 0.3)
            return np.where(v > 0, 0.9, 0.0)

        elif self.__composition == 'grid':
            # Grid of rounded squares
            cell = scale * 0.3
            cx = np.mod(gx + t * 2, cell) - cell / 2
            cy = np.mod(gy + t * 1.5, cell) - cell / 2
            d = np.maximum(np.abs(cx), np.abs(cy))
            return np.where(d < cell * 0.3, 0.9, 0.0)

        elif self.__composition == 'arcs':
            # Circular arcs / pie slices
            dist = np.sqrt(gx ** 2 + gy ** 2)
            angle = np.arctan2(gy, gx)
            ring = np.sin(dist / scale * 10)
            pie = np.sin(angle * 3 + t * 0.4)
            return np.where((ring > 0) & (pie > 0) & (dist < scale * 0.45), 0.9, 0.0)

        else:  # blocks
            # Large overlapping rectangles
            mask = np.zeros_like(gx)
            for j, (bw_frac, bh_frac) in enumerate(self.__block_sizes):
                bx = math.sin(t * 0.3 + j * 2.1) * scale * 0.2
                by = math.cos(t * 0.25 + j * 1.7) * scale * 0.15
                bw = scale * bw_frac
                bh = scale * bh_frac
                in_block = (np.abs(gx - bx) < bw) & (np.abs(gy - by) < bh)
                mask[in_block] = 0.9
            return mask

    @classmethod
    def get_id(cls) -> str:
        return 'misprint'

    @classmethod
    def get_name(cls) -> str:
        return 'Misprint'

    @classmethod
    def get_description(cls) -> str:
        return 'Off-register risograph geometry'
