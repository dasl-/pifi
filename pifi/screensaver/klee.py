import numpy as np
import random

from pifi.config import Config
from pifi.screensaver.screensaver import Screensaver


class Klee(Screensaver):
    """
    Klee — Paul Klee pedagogical notebook color studies.

    Color theory exercises from Klee's Bauhaus teaching notes:
    diamond color mixing grids showing RYB primary-to-secondary
    progressions, radial color wheels, and systematic hue × value
    grids. Based on the Pädagogisches Skizzenbuch.
    """

    # 12-step RYB color wheel (Klee's Farbkreis)
    # Rot → Orange → Gelb → Grün → Blau → Violett
    WHEEL = np.array([
        [0.82, 0.18, 0.15],  # 0  Rot
        [0.87, 0.35, 0.12],  # 1  Rotorange
        [0.90, 0.50, 0.12],  # 2  Orange
        [0.92, 0.65, 0.18],  # 3  Gelborange
        [0.90, 0.80, 0.25],  # 4  Gelb
        [0.50, 0.70, 0.25],  # 5  Gelbgrün
        [0.20, 0.60, 0.30],  # 6  Grün
        [0.15, 0.45, 0.55],  # 7  Blaugrün
        [0.20, 0.30, 0.65],  # 8  Blau
        [0.35, 0.22, 0.62],  # 9  Blauviolett
        [0.50, 0.15, 0.55],  # 10 Violett
        [0.70, 0.15, 0.35],  # 11 Rotviolett
    ])

    # Three 5-step mixing progressions between primaries
    # Each row: indices into WHEEL for a primary → primary progression
    PROGRESSIONS = np.array([
        [0, 1, 2, 3, 4],    # Rot → Gelb (through orange)
        [4, 5, 6, 7, 8],    # Gelb → Blau (through green)
        [8, 9, 10, 11, 0],  # Blau → Rot (through violet)
    ])

    def __init__(self, led_frame_player=None):
        super().__init__(led_frame_player)
        self.__width = Config.get_or_throw('leds.display_width')
        self.__height = Config.get_or_throw('leds.display_height')

    def _setup(self):
        self.__time = 0.0
        w, h = self.__width, self.__height

        y = np.arange(h, dtype=np.float64)
        x = np.arange(w, dtype=np.float64)
        self.__gx, self.__gy = np.meshgrid(x, y)

        self.__mode = random.choice([
            'diamond_mixing',
            'color_wheel',
            'color_grid',
        ])

        if self.__mode == 'diamond_mixing':
            self.__setup_diamond()
        elif self.__mode == 'color_wheel':
            self.__setup_wheel()
        else:
            self.__setup_grid()

    def __setup_diamond(self):
        w, h = self.__width, self.__height
        self.__diamond_size = max(2.5, min(w, h) / random.uniform(3, 5))
        ds = self.__diamond_size
        # Rotated coordinates give a natural diamond tiling
        self.__u_base = (self.__gx + self.__gy) / ds
        self.__v_base = (self.__gx - self.__gy) / ds

    def __setup_wheel(self):
        w, h = self.__width, self.__height
        self.__cx = w / 2.0
        self.__cy = h / 2.0
        self.__radius = min(w, h) * 0.45
        self.__num_segments = random.choice([6, 12])
        dx = self.__gx - self.__cx
        dy = self.__gy - self.__cy
        self.__angle = np.arctan2(dy, dx)
        self.__dist = np.sqrt(dx ** 2 + dy ** 2)

    def __setup_grid(self):
        self.__grid_cols = random.randint(4, min(8, self.__width // 2))
        self.__grid_rows = random.randint(3, min(6, self.__height // 2))

    def _tick(self, tick):
        self.__time += 0.02
        t = self.__time

        if self.__mode == 'diamond_mixing':
            frame = self.__tick_diamond(t)
        elif self.__mode == 'color_wheel':
            frame = self.__tick_wheel(t)
        else:
            frame = self.__tick_grid(t)

        self._led_frame_player.play_frame(frame)

    def __tick_diamond(self, t):
        """Diamond grid with RYB mixing progressions (the Darstellung diagram)."""
        u = self.__u_base + t * 0.06
        v = self.__v_base + t * 0.04

        cell_u = np.floor(u).astype(np.int32)
        cell_v = np.floor(v).astype(np.int32)
        frac_u = u % 1.0
        frac_v = v % 1.0

        # Which progression (R→Y, Y→B, B→R) — rows cycle
        prog = (cell_v + int(t * 0.12)) % 3

        # Smooth color flow: mixing ratio animates as a wave across the grid
        # Each cell's position in the 5-step progression shifts over time
        flow = (cell_u * 1.0 + cell_v * 0.4 + t * 0.35) % 5.0
        step_low = np.floor(flow).astype(np.int32) % 5
        step_high = (step_low + 1) % 5
        mix = flow - np.floor(flow)
        # Cosine ease for smoother color transitions
        mix = 0.5 - 0.5 * np.cos(mix * np.pi)

        idx_low = self.PROGRESSIONS[prog, step_low]
        idx_high = self.PROGRESSIONS[prog, step_high]
        color = (self.WHEEL[idx_low] * (1 - mix[:, :, np.newaxis]) +
                 self.WHEEL[idx_high] * mix[:, :, np.newaxis])

        # Diamond border darkening
        edge_u = np.minimum(frac_u, 1.0 - frac_u)
        edge_v = np.minimum(frac_v, 1.0 - frac_v)
        edge = np.minimum(edge_u, edge_v)
        border = np.clip(edge / 0.12, 0, 1)

        # Flat fill — border handles cell separation, no spotlight
        brightness = (border * 0.85)[:, :, np.newaxis]
        frame = color * brightness

        return (np.clip(frame, 0, 1) * 255).astype(np.uint8)

    def __tick_wheel(self, t):
        """Radial color wheel with growing/shrinking segments (the Farbkreis)."""
        n = self.__num_segments

        # Slowly rotate
        angle = (self.__angle + t * 0.08) % (2 * np.pi)
        seg_float = angle / (2 * np.pi) * n
        segment = np.floor(seg_float).astype(np.int32) % n

        # Map segments to wheel colors
        if n == 12:
            color = self.WHEEL[segment]
        else:
            color = self.WHEEL[(segment * 2) % 12]

        # Per-segment animated radius — alternating long/short like the diagram
        seg_radii = np.zeros(n)
        for i in range(n):
            # Alternating base: even segments long, odd segments short
            alt = 0.3 * (1 if i % 2 == 0 else -1)
            # Animate: the alternation pattern slowly rotates around the wheel
            seg_radii[i] = self.__radius * (0.7 + alt * np.cos(t * 0.3 + i * 0.2))
        pixel_radius = seg_radii[segment]

        norm_dist = self.__dist / np.maximum(pixel_radius, 0.1)
        inside = norm_dist < 1.0

        # Flat color fill — no radial gradient, just the wheel color
        val = np.where(inside, 0.8, 0.0)

        # Segment border lines
        seg_frac = seg_float % 1.0
        seg_edge = np.minimum(seg_frac, 1.0 - seg_frac)
        seg_border = np.clip(seg_edge / 0.06, 0, 1)
        val *= seg_border

        frame = color * val[:, :, np.newaxis]

        return (np.clip(frame, 0, 1) * 255).astype(np.uint8)

    def __tick_grid(self, t):
        """Rectangular grid: hue progression × tonal value steps."""
        w, h = self.__width, self.__height
        cols, rows = self.__grid_cols, self.__grid_rows

        cell_w = w / cols
        cell_h = h / rows

        col_idx = np.clip((self.__gx / cell_w).astype(np.int32), 0, cols - 1)
        row_idx = np.clip((self.__gy / cell_h).astype(np.int32), 0, rows - 1)

        # Smooth hue scrolling: each cell's hue interpolates between wheel steps
        hue_pos = (col_idx.astype(np.float64) * (12.0 / cols) + t * 0.4) % 12.0
        hue_low = np.floor(hue_pos).astype(np.int32) % 12
        hue_high = (hue_low + 1) % 12
        hue_frac = hue_pos - np.floor(hue_pos)
        color = (self.WHEEL[hue_low] * (1 - hue_frac[:, :, np.newaxis]) +
                 self.WHEEL[hue_high] * hue_frac[:, :, np.newaxis])

        # Vertical: tonal value undulates as a traveling wave
        row_frac = row_idx.astype(np.float64) / max(rows - 1, 1)
        value = 0.35 + 0.55 * (0.5 + 0.5 * np.sin(row_frac * np.pi * 1.5 - t * 0.5))

        # Cell border darkening
        fx = np.mod(self.__gx, cell_w)
        fy = np.mod(self.__gy, cell_h)
        border = np.minimum(np.minimum(fx, cell_w - fx), np.minimum(fy, cell_h - fy))
        border_fade = np.clip(border / 1.0, 0, 1) ** 0.5

        # Flat fill — value controls tonal progression, no per-cell spotlighting
        brightness = (value * border_fade)[:, :, np.newaxis]
        frame = color * brightness

        return (np.clip(frame, 0, 1) * 255).astype(np.uint8)

    @classmethod
    def get_id(cls) -> str:
        return 'klee'

    @classmethod
    def get_name(cls) -> str:
        return 'Klee'

    @classmethod
    def get_description(cls) -> str:
        return 'Pedagogical notebook color studies'
