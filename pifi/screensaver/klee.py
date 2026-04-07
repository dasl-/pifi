import numpy as np
import random
import math

from pifi.config import Config
from pifi.screensaver.screensaver import Screensaver


class Klee(Screensaver):
    """
    Klee — Paul Klee pedagogical notebook compositions.

    Structured geometric color studies that slowly animate:
    layered transparent rectangles, rhythmic grid progressions,
    checkerboard color studies, and geometric constructions.
    Warm earthy palettes with jewel-like accents.
    """

    # Klee-inspired palettes: earthy, warm, with vivid accents
    PALETTES = [
        # Tunisian watercolors
        [(0.85, 0.55, 0.25), (0.65, 0.25, 0.2), (0.3, 0.45, 0.5), (0.9, 0.8, 0.5), (0.45, 0.3, 0.25)],
        # Harmony of the Northern Flora
        [(0.55, 0.65, 0.35), (0.75, 0.5, 0.3), (0.35, 0.3, 0.5), (0.85, 0.75, 0.4), (0.5, 0.55, 0.4)],
        # Senecio / abstract portraits
        [(0.9, 0.6, 0.3), (0.7, 0.25, 0.2), (0.25, 0.35, 0.55), (0.95, 0.85, 0.6), (0.5, 0.2, 0.35)],
        # Castle and sun
        [(0.85, 0.45, 0.15), (0.65, 0.2, 0.15), (0.3, 0.25, 0.5), (0.95, 0.8, 0.35), (0.4, 0.35, 0.3)],
        # Ad Parnassum
        [(0.75, 0.6, 0.3), (0.55, 0.4, 0.25), (0.3, 0.5, 0.55), (0.85, 0.7, 0.45), (0.6, 0.35, 0.3)],
    ]

    def __init__(self, led_frame_player=None):
        super().__init__(led_frame_player)

        self.__width = Config.get_or_throw('leds.display_width')
        self.__height = Config.get_or_throw('leds.display_height')

    def _setup(self):
        self.__time = 0.0
        self.__palette = random.choice(self.PALETTES)
        self.__mode = random.choice([
            'color_grid',
            'layered_rects',
            'checkerboard',
            'geometric',
        ])

        w, h = self.__width, self.__height

        # Pre-compute coordinates
        y = np.arange(h, dtype=np.float64)
        x = np.arange(w, dtype=np.float64)
        self.__gx, self.__gy = np.meshgrid(x, y)

        if self.__mode == 'color_grid':
            self.__setup_color_grid()
        elif self.__mode == 'layered_rects':
            self.__setup_layered_rects()
        elif self.__mode == 'checkerboard':
            self.__setup_checkerboard()
        else:
            self.__setup_geometric()

    def __setup_color_grid(self):
        """Grid of cells with systematic color progressions."""
        w, h = self.__width, self.__height
        # Grid dimensions
        self.__grid_cols = random.randint(4, min(8, w // 2))
        self.__grid_rows = random.randint(3, min(6, h // 2))
        # Color progression axes
        self.__hue_axis = random.choice(['horizontal', 'vertical', 'diagonal'])
        self.__base_hue = random.uniform(0, 1)
        self.__hue_range = random.uniform(0.15, 0.4)
        self.__val_range = random.uniform(0.3, 0.6)

    def __setup_layered_rects(self):
        """Overlapping semi-transparent rectangles."""
        w, h = self.__width, self.__height
        self.__num_rects = random.randint(4, 7)
        self.__rects = []
        for i in range(self.__num_rects):
            rw = random.uniform(0.2, 0.6) * w
            rh = random.uniform(0.2, 0.6) * h
            self.__rects.append({
                'cx': random.uniform(0, w),
                'cy': random.uniform(0, h),
                'w': rw,
                'h': rh,
                'color': random.choice(self.__palette),
                'opacity': random.uniform(0.3, 0.6),
                'drift_x': random.uniform(-0.8, 0.8),
                'drift_y': random.uniform(-0.6, 0.6),
                'rot_speed': random.uniform(-0.15, 0.15),
                'phase': random.uniform(0, 2 * math.pi),
            })

    def __setup_checkerboard(self):
        """Checkerboard with color relationships between neighbors."""
        w, h = self.__width, self.__height
        self.__check_cols = random.randint(4, min(10, w))
        self.__check_rows = random.randint(3, min(7, h))
        self.__check_relationship = random.choice([
            'complementary', 'analogous', 'value_step',
        ])
        self.__base_colors = [random.choice(self.__palette) for _ in range(4)]

    def __setup_geometric(self):
        """Circles, triangles, and lines with Klee's color sensibility."""
        w, h = self.__width, self.__height
        self.__geo_elements = []
        num = random.randint(3, 6)
        for _ in range(num):
            shape = random.choice(['circle', 'triangle', 'line'])
            self.__geo_elements.append({
                'shape': shape,
                'cx': random.uniform(0, w),
                'cy': random.uniform(0, h),
                'size': random.uniform(0.15, 0.4) * min(w, h),
                'color': random.choice(self.__palette),
                'opacity': random.uniform(0.4, 0.7),
                'rot_speed': random.uniform(-0.4, 0.4),
                'breath_speed': random.uniform(1.0, 3.0),
                'drift_speed': random.uniform(0.3, 0.8),
                'phase': random.uniform(0, 2 * math.pi),
            })

    def _tick(self, tick):
        self.__time += 0.04
        t = self.__time

        if self.__mode == 'color_grid':
            frame = self.__tick_color_grid(t)
        elif self.__mode == 'layered_rects':
            frame = self.__tick_layered_rects(t)
        elif self.__mode == 'checkerboard':
            frame = self.__tick_checkerboard(t)
        else:
            frame = self.__tick_geometric(t)

        self._led_frame_player.play_frame(frame)

    def __tick_color_grid(self, t):
        """Render grid with evolving color progression."""
        w, h = self.__width, self.__height
        cols, rows = self.__grid_cols, self.__grid_rows
        canvas = np.zeros((h, w, 3), dtype=np.float64)

        cell_w = w / cols
        cell_h = h / rows

        # Cell indices for each pixel
        col_idx = np.clip((self.__gx / cell_w).astype(np.int32), 0, cols - 1)
        row_idx = np.clip((self.__gy / cell_h).astype(np.int32), 0, rows - 1)

        # Normalized position in grid
        col_frac = col_idx.astype(np.float64) / max(cols - 1, 1)
        row_frac = row_idx.astype(np.float64) / max(rows - 1, 1)

        # Color progression
        if self.__hue_axis == 'horizontal':
            prog = col_frac
        elif self.__hue_axis == 'vertical':
            prog = row_frac
        else:
            prog = (col_frac + row_frac) / 2

        # Progression axis itself rotates over time
        blend = 0.5 + 0.5 * math.sin(t * 0.15)
        if self.__hue_axis == 'horizontal':
            prog = col_frac * blend + row_frac * (1 - blend)
        elif self.__hue_axis == 'vertical':
            prog = row_frac * blend + col_frac * (1 - blend)
        else:
            diag = (col_frac + row_frac) / 2
            anti = (col_frac + 1 - row_frac) / 2
            prog = diag * blend + anti * (1 - blend)

        # Per-cell brightness wave traveling across the grid
        cell_wave = 0.7 + 0.3 * np.sin(
            col_idx * 1.2 + row_idx * 0.9 + t * 1.5
        )

        hue = (self.__base_hue + prog * self.__hue_range + t * 0.3) % 1.0
        sat = 0.45 + 0.25 * np.sin(row_frac * math.pi + t * 1.5)
        val = (0.35 + self.__val_range * (1 - row_frac) + 0.15 * np.sin(t * 1.0 + col_frac * 5)) * cell_wave

        # HSV to RGB vectorized
        canvas = self.__hsv_to_rgb(hue, sat, val)

        # Cell borders — darken pixels near cell edges
        fx = np.mod(self.__gx, cell_w)
        fy = np.mod(self.__gy, cell_h)
        border_x = np.minimum(fx, cell_w - fx)
        border_y = np.minimum(fy, cell_h - fy)
        border = np.minimum(border_x, border_y)
        border_fade = np.clip(border / 1.2, 0, 1) ** 0.5
        canvas *= border_fade[:, :, np.newaxis]

        return (np.clip(canvas, 0, 1) * 255).astype(np.uint8)

    def __tick_layered_rects(self, t):
        """Render drifting overlapping transparent rectangles."""
        w, h = self.__width, self.__height
        # Warm background that breathes
        bg_bright = 0.12 + 0.05 * math.sin(t * 0.3)
        bg = np.array(self.__palette[0]) * bg_bright
        canvas = np.full((h, w, 3), bg, dtype=np.float64)

        for rect in self.__rects:
            cx = rect['cx'] + math.sin(t * rect['drift_x'] + rect['phase']) * w * 0.3
            cy = rect['cy'] + math.cos(t * rect['drift_y'] + rect['phase'] * 0.7) * h * 0.25

            rw = rect['w'] * (1 + 0.2 * math.sin(t * 0.8 + rect['phase']))
            rh = rect['h'] * (1 + 0.2 * math.cos(t * 0.6 + rect['phase']))

            # Slight rotation of the rectangle
            rot = t * rect['rot_speed']
            cos_r = math.cos(rot)
            sin_r = math.sin(rot)
            dx = self.__gx - cx
            dy = self.__gy - cy
            rx = dx * cos_r + dy * sin_r
            ry = -dx * sin_r + dy * cos_r

            in_rect = (np.abs(rx) < rw / 2) & (np.abs(ry) < rh / 2)

            # Color slowly shifts through palette
            color_idx = (rect['phase'] / (2 * math.pi) * len(self.__palette) + t * 0.15) % len(self.__palette)
            ci = int(color_idx) % len(self.__palette)
            ci2 = (ci + 1) % len(self.__palette)
            cf = color_idx - int(color_idx)
            color = np.array(self.__palette[ci]) * (1 - cf) + np.array(self.__palette[ci2]) * cf

            opacity = rect['opacity'] * (0.7 + 0.3 * math.sin(t * 1.2 + rect['phase']))

            canvas[:, :, 0] += in_rect * color[0] * opacity
            canvas[:, :, 1] += in_rect * color[1] * opacity
            canvas[:, :, 2] += in_rect * color[2] * opacity

        return (np.clip(canvas, 0, 1) * 255).astype(np.uint8)

    def __tick_checkerboard(self, t):
        """Render checkerboard with shifting color relationships."""
        w, h = self.__width, self.__height
        cols, rows = self.__check_cols, self.__check_rows

        cell_w = w / cols
        cell_h = h / rows

        col_idx = np.clip((self.__gx / cell_w).astype(np.int32), 0, cols - 1)
        row_idx = np.clip((self.__gy / cell_h).astype(np.int32), 0, rows - 1)

        # Checker parity
        parity = (col_idx + row_idx) % 2

        canvas = np.zeros((h, w, 3), dtype=np.float64)

        # Generate two colors that shift over time
        base = np.array(self.__base_colors[0])
        alt = np.array(self.__base_colors[1])

        # Rotate through palette
        phase = t * 0.5
        idx1 = int(phase) % len(self.__palette)
        idx2 = (idx1 + 1) % len(self.__palette)
        frac = phase - int(phase)
        color_a = np.array(self.__palette[idx1]) * (1 - frac) + np.array(self.__palette[idx2]) * frac

        idx3 = (idx1 + 2) % len(self.__palette)
        idx4 = (idx3 + 1) % len(self.__palette)
        color_b = np.array(self.__palette[idx3]) * (1 - frac) + np.array(self.__palette[idx4]) * frac

        # Traveling brightness wave across the grid
        val_mod = 0.55 + 0.45 * np.sin(
            col_idx * 1.2 - row_idx * 0.8 + t * 2.0
        )

        for c in range(3):
            canvas[:, :, c] = np.where(
                parity == 0,
                color_a[c] * val_mod,
                color_b[c] * val_mod,
            )

        # Subtle cell borders
        fx = np.mod(self.__gx, cell_w)
        fy = np.mod(self.__gy, cell_h)
        border = np.minimum(np.minimum(fx, cell_w - fx), np.minimum(fy, cell_h - fy))
        border_fade = np.clip(border / 1.0, 0, 1)
        canvas *= border_fade[:, :, np.newaxis]

        return (np.clip(canvas, 0, 1) * 255).astype(np.uint8)

    def __tick_geometric(self, t):
        """Render geometric shapes with Klee colors."""
        w, h = self.__width, self.__height
        bg = np.array(self.__palette[-1]) * 0.1
        canvas = np.full((h, w, 3), bg, dtype=np.float64)

        for elem in self.__geo_elements:
            ds = elem['drift_speed']
            cx = elem['cx'] + math.sin(t * ds + elem['phase']) * w * 0.2
            cy = elem['cy'] + math.cos(t * ds * 0.8 + elem['phase'] * 1.3) * h * 0.2
            size = elem['size'] * (0.7 + 0.5 * math.sin(t * elem['breath_speed'] + elem['phase']))
            # Color drifts through palette over time
            color_idx = (elem['phase'] / (2 * math.pi) * len(self.__palette) + t * 0.2) % len(self.__palette)
            ci = int(color_idx) % len(self.__palette)
            ci2 = (ci + 1) % len(self.__palette)
            cf = color_idx - int(color_idx)
            color = np.array(self.__palette[ci]) * (1 - cf) + np.array(self.__palette[ci2]) * cf
            opacity = elem['opacity'] * (0.7 + 0.3 * math.sin(t * 0.8 + elem['phase']))

            if elem['shape'] == 'circle':
                dist = np.sqrt((self.__gx - cx) ** 2 + (self.__gy - cy) ** 2)
                # Filled circle with soft edge
                mask = np.clip(1.0 - (dist - size * 0.4) / max(size * 0.1, 0.5), 0, 1)
                canvas[:, :, 0] += mask * color[0] * opacity
                canvas[:, :, 1] += mask * color[1] * opacity
                canvas[:, :, 2] += mask * color[2] * opacity

            elif elem['shape'] == 'triangle':
                # Equilateral triangle, rotating
                rot = t * elem['rot_speed'] + elem['phase']
                # Three vertices
                angles = [rot, rot + 2 * math.pi / 3, rot + 4 * math.pi / 3]
                verts = [(cx + size * 0.5 * math.cos(a), cy + size * 0.5 * math.sin(a)) for a in angles]
                # Point-in-triangle test (vectorized with cross products)
                mask = self.__point_in_triangle(
                    self.__gx, self.__gy,
                    verts[0], verts[1], verts[2]
                )
                canvas[:, :, 0] += mask * color[0] * opacity
                canvas[:, :, 1] += mask * color[1] * opacity
                canvas[:, :, 2] += mask * color[2] * opacity

            else:  # line
                rot = t * elem['rot_speed'] * 2 + elem['phase']
                lx = math.cos(rot) * size * 0.5
                ly = math.sin(rot) * size * 0.5
                # Distance from point to line segment
                ax, ay = cx - lx, cy - ly
                bx, by = cx + lx, cy + ly
                dist = self.__dist_to_segment(self.__gx, self.__gy, ax, ay, bx, by)
                thickness = max(1.0, min(w, h) * 0.03)
                mask = np.clip(1.0 - dist / thickness, 0, 1)
                canvas[:, :, 0] += mask * color[0] * opacity * 0.8
                canvas[:, :, 1] += mask * color[1] * opacity * 0.8
                canvas[:, :, 2] += mask * color[2] * opacity * 0.8

        return (np.clip(canvas, 0, 1) * 255).astype(np.uint8)

    @staticmethod
    def __point_in_triangle(px, py, v0, v1, v2):
        """Vectorized point-in-triangle test using cross products."""
        def sign(x1, y1, x2, y2, x3, y3):
            return (x1 - x3) * (y2 - y3) - (x2 - x3) * (y1 - y3)

        d1 = sign(px, py, v0[0], v0[1], v1[0], v1[1])
        d2 = sign(px, py, v1[0], v1[1], v2[0], v2[1])
        d3 = sign(px, py, v2[0], v2[1], v0[0], v0[1])

        has_neg = (d1 < 0) | (d2 < 0) | (d3 < 0)
        has_pos = (d1 > 0) | (d2 > 0) | (d3 > 0)

        return (~(has_neg & has_pos)).astype(np.float64)

    @staticmethod
    def __dist_to_segment(px, py, ax, ay, bx, by):
        """Vectorized distance from points to line segment."""
        dx = bx - ax
        dy = by - ay
        len_sq = dx * dx + dy * dy
        if len_sq < 1e-10:
            return np.sqrt((px - ax) ** 2 + (py - ay) ** 2)
        t = np.clip(((px - ax) * dx + (py - ay) * dy) / len_sq, 0, 1)
        proj_x = ax + t * dx
        proj_y = ay + t * dy
        return np.sqrt((px - proj_x) ** 2 + (py - proj_y) ** 2)

    @staticmethod
    def __hsv_to_rgb(h, s, v):
        """Vectorized HSV to RGB conversion."""
        h = h % 1.0
        h6 = h * 6.0
        hi = h6.astype(np.int32) % 6
        f = h6 - np.floor(h6)
        p = v * (1 - s)
        q = v * (1 - s * f)
        t = v * (1 - s * (1 - f))

        r = np.zeros_like(h)
        g = np.zeros_like(h)
        b = np.zeros_like(h)

        for i in range(6):
            m = hi == i
            if i == 0:
                r[m] = v[m]; g[m] = t[m]; b[m] = p[m]
            elif i == 1:
                r[m] = q[m]; g[m] = v[m]; b[m] = p[m]
            elif i == 2:
                r[m] = p[m]; g[m] = v[m]; b[m] = t[m]
            elif i == 3:
                r[m] = p[m]; g[m] = q[m]; b[m] = v[m]
            elif i == 4:
                r[m] = t[m]; g[m] = p[m]; b[m] = v[m]
            else:
                r[m] = v[m]; g[m] = p[m]; b[m] = q[m]

        return np.stack([r, g, b], axis=-1)

    @classmethod
    def get_id(cls) -> str:
        return 'klee'

    @classmethod
    def get_name(cls) -> str:
        return 'Klee'

    @classmethod
    def get_description(cls) -> str:
        return 'Geometric color compositions'
