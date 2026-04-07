import numpy as np
import random
import math

from pifi.config import Config
from pifi.screensaver.screensaver import Screensaver


class Blueprint(Screensaver):
    """
    Blueprint — animated architectural/technical drawing.

    Construction lines, sweeping arcs, perspective grids, and
    dimension marks drawn progressively on a deep blue field.
    Each element appears to be plotted by an invisible drafting
    machine — precise, deliberate, mechanical.
    """

    # Deep navy background
    _BG = np.array([8, 18, 42], dtype=np.float64)
    # Primary line color (pale cyan-white)
    _PRIMARY = np.array([160, 200, 230], dtype=np.float64)
    # Accent color (amber/orange for dimensions)
    _ACCENT = np.array([220, 160, 60], dtype=np.float64)
    # Crosshair color
    _MARK = np.array([200, 80, 60], dtype=np.float64)

    def __init__(self, led_frame_player=None):
        super().__init__(led_frame_player)

        self.__width = Config.get_or_throw('leds.display_width')
        self.__height = Config.get_or_throw('leds.display_height')

    def _setup(self):
        self.__time = 0.0
        w, h = self.__width, self.__height

        # Pre-compute coordinates
        y = np.arange(h, dtype=np.float64)
        x = np.arange(w, dtype=np.float64)
        self.__gx, self.__gy = np.meshgrid(x, y)

        # Canvas (float for additive blending)
        self.__canvas = np.tile(self._BG, (h, w, 1)).astype(np.float64)

        # Persistent faint grid
        self.__grid_angle = random.uniform(-0.2, 0.2)
        self.__grid_spacing = random.uniform(3.0, 6.0)
        self.__grid_scroll_x = random.uniform(-0.3, 0.3)
        self.__grid_scroll_y = random.uniform(-0.2, 0.2)

        # Element pool
        self.__elements = []
        self.__max_elements = max(3, int(w * h / 150))
        self.__spawn_timer = 0.0
        self.__spawn_interval = random.uniform(0.3, 0.8)

    def _tick(self, tick):
        self.__time += 0.02
        t = self.__time
        w, h = self.__width, self.__height

        # Fade canvas toward background
        self.__canvas = self.__canvas * 0.97 + self._BG * 0.03

        # Draw faint background grid
        self.__draw_grid(t)

        # Spawn new elements
        self.__spawn_timer += 0.02
        if self.__spawn_timer >= self.__spawn_interval and len(self.__elements) < self.__max_elements:
            self.__spawn_timer = 0.0
            self.__spawn_element()

        # Update and draw elements
        alive = []
        for elem in self.__elements:
            elem['age'] += 0.02
            if elem['age'] < elem['lifetime']:
                self.__draw_element(elem, t)
                alive.append(elem)
        self.__elements = alive

        frame = np.clip(self.__canvas, 0, 255).astype(np.uint8)
        self._led_frame_player.play_frame(frame)

    def __draw_grid(self, t):
        """Faint rotating, scrolling graph-paper grid."""
        angle = self.__grid_angle + t * 0.01
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)

        rx = self.__gx * cos_a - self.__gy * sin_a + t * self.__grid_scroll_x * 10
        ry = self.__gx * sin_a + self.__gy * cos_a + t * self.__grid_scroll_y * 10

        spacing = self.__grid_spacing
        grid_x = np.abs(np.mod(rx, spacing) - spacing / 2)
        grid_y = np.abs(np.mod(ry, spacing) - spacing / 2)

        line_x = np.clip(1.0 - grid_x / 0.6, 0, 1)
        line_y = np.clip(1.0 - grid_y / 0.6, 0, 1)
        grid_mask = np.maximum(line_x, line_y)

        brightness = 12
        for c in range(3):
            self.__canvas[:, :, c] = np.maximum(
                self.__canvas[:, :, c],
                self._BG[c] + grid_mask * brightness
            )

    def __spawn_element(self):
        """Spawn a new drawing element."""
        w, h = self.__width, self.__height
        kind = random.choices(
            ['arc', 'line', 'perspective', 'dimension', 'crosshair', 'circle'],
            weights=[3, 2, 2, 2, 1, 2],
            k=1
        )[0]

        elem = {
            'kind': kind,
            'age': 0.0,
            'lifetime': random.uniform(2.0, 5.0),
            'draw_time': random.uniform(0.5, 1.5),
            'hold_time': random.uniform(1.0, 2.5),
        }

        if kind == 'arc':
            elem['cx'] = random.uniform(0, w)
            elem['cy'] = random.uniform(0, h)
            elem['radius'] = random.uniform(3, min(w, h) * 0.6)
            elem['start_angle'] = random.uniform(0, 2 * math.pi)
            elem['sweep'] = random.uniform(math.pi * 0.5, math.pi * 1.8)
            elem['color'] = self._PRIMARY

        elif kind == 'line':
            elem['x1'] = random.uniform(-w * 0.1, w * 1.1)
            elem['y1'] = random.uniform(-h * 0.1, h * 1.1)
            angle = random.uniform(0, 2 * math.pi)
            length = random.uniform(min(w, h) * 0.3, max(w, h) * 0.8)
            elem['x2'] = elem['x1'] + math.cos(angle) * length
            elem['y2'] = elem['y1'] + math.sin(angle) * length
            elem['color'] = self._PRIMARY

        elif kind == 'perspective':
            elem['vp_x'] = random.uniform(w * 0.2, w * 0.8)
            elem['vp_y'] = random.uniform(h * 0.2, h * 0.8)
            elem['num_lines'] = random.randint(4, 8)
            elem['color'] = self._PRIMARY * 0.7

        elif kind == 'dimension':
            horizontal = random.random() < 0.5
            if horizontal:
                y_pos = random.uniform(h * 0.1, h * 0.9)
                elem['x1'] = random.uniform(0, w * 0.3)
                elem['x2'] = random.uniform(w * 0.6, w)
                elem['y1'] = elem['y2'] = y_pos
            else:
                x_pos = random.uniform(w * 0.1, w * 0.9)
                elem['y1'] = random.uniform(0, h * 0.3)
                elem['y2'] = random.uniform(h * 0.6, h)
                elem['x1'] = elem['x2'] = x_pos
            elem['color'] = self._ACCENT

        elif kind == 'crosshair':
            elem['cx'] = random.uniform(w * 0.1, w * 0.9)
            elem['cy'] = random.uniform(h * 0.1, h * 0.9)
            elem['size'] = random.uniform(2, min(w, h) * 0.15)
            elem['color'] = self._MARK

        else:  # circle
            elem['cx'] = random.uniform(w * 0.15, w * 0.85)
            elem['cy'] = random.uniform(h * 0.15, h * 0.85)
            elem['radius'] = random.uniform(2, min(w, h) * 0.4)
            elem['sides'] = random.choice([0, 3, 4, 5, 6])
            elem['rot'] = random.uniform(0, 2 * math.pi)
            elem['color'] = self._PRIMARY

        self.__elements.append(elem)

    def __draw_element(self, elem, t):
        """Draw an element based on its age/lifecycle."""
        age = elem['age']
        draw_t = elem['draw_time']
        hold_t = elem['hold_time']
        lifetime = elem['lifetime']

        if age < draw_t:
            progress = age / draw_t
            alpha = 1.0
        elif age < draw_t + hold_t:
            progress = 1.0
            alpha = 1.0
        else:
            progress = 1.0
            fade_time = lifetime - draw_t - hold_t
            alpha = max(0, 1.0 - (age - draw_t - hold_t) / max(fade_time, 0.01))

        brightness = alpha * 0.8
        kind = elem['kind']

        if kind == 'arc':
            self.__render_arc(elem, progress, brightness)
        elif kind == 'line':
            self.__render_line(
                elem['x1'], elem['y1'], elem['x2'], elem['y2'],
                elem['color'], progress, brightness
            )
        elif kind == 'perspective':
            self.__render_perspective(elem, progress, brightness)
        elif kind == 'dimension':
            self.__render_dimension(elem, progress, brightness)
        elif kind == 'crosshair':
            self.__render_crosshair(elem, progress, brightness)
        else:
            self.__render_circle(elem, progress, brightness)

    def __render_arc(self, elem, progress, brightness):
        """Render a sweeping arc."""
        cx, cy = elem['cx'], elem['cy']
        r = elem['radius']
        start = elem['start_angle']
        sweep = elem['sweep'] * progress

        dist = np.sqrt((self.__gx - cx) ** 2 + (self.__gy - cy) ** 2)
        angle = np.arctan2(self.__gy - cy, self.__gx - cx)

        rel_angle = (angle - start) % (2 * math.pi)

        on_ring = np.clip(1.0 - np.abs(dist - r) / 0.8, 0, 1)
        in_sweep = rel_angle < sweep

        mask = on_ring * in_sweep * brightness
        color = elem['color']
        for c in range(3):
            self.__canvas[:, :, c] = np.maximum(
                self.__canvas[:, :, c],
                self._BG[c] + mask * color[c]
            )

    def __render_line(self, x1, y1, x2, y2, color, progress, brightness):
        """Render a line being drawn progressively."""
        ex = x1 + (x2 - x1) * progress
        ey = y1 + (y2 - y1) * progress

        dx = ex - x1
        dy = ey - y1
        len_sq = dx * dx + dy * dy
        if len_sq < 0.01:
            return

        t_param = np.clip(
            ((self.__gx - x1) * dx + (self.__gy - y1) * dy) / len_sq,
            0, 1
        )
        proj_x = x1 + t_param * dx
        proj_y = y1 + t_param * dy
        dist = np.sqrt((self.__gx - proj_x) ** 2 + (self.__gy - proj_y) ** 2)

        mask = np.clip(1.0 - dist / 0.8, 0, 1) * brightness
        for c in range(3):
            self.__canvas[:, :, c] = np.maximum(
                self.__canvas[:, :, c],
                self._BG[c] + mask * color[c]
            )

    def __render_perspective(self, elem, progress, brightness):
        """Render lines converging to a vanishing point."""
        vx, vy = elem['vp_x'], elem['vp_y']
        w, h = self.__width, self.__height
        n = elem['num_lines']
        color = elem['color']

        for i in range(n):
            angle = (i / n) * 2 * math.pi
            edge_x = vx + math.cos(angle) * max(w, h) * 1.5
            edge_y = vy + math.sin(angle) * max(w, h) * 1.5
            self.__render_line(vx, vy, edge_x, edge_y, color, progress, brightness * 0.5)

    def __render_dimension(self, elem, progress, brightness):
        """Render a dimension/measurement line with end caps."""
        x1, y1 = elem['x1'], elem['y1']
        x2, y2 = elem['x2'], elem['y2']
        color = elem['color']

        self.__render_line(x1, y1, x2, y2, color, progress, brightness)

        if progress > 0.3:
            cap_brightness = brightness * min(1, (progress - 0.3) / 0.3)
            if abs(y2 - y1) < 0.1:  # horizontal
                cap_len = min(2, self.__height * 0.15)
                self.__render_line(x1, y1 - cap_len, x1, y1 + cap_len, color, 1.0, cap_brightness)
                ex = x1 + (x2 - x1) * progress
                self.__render_line(ex, y2 - cap_len, ex, y2 + cap_len, color, 1.0, cap_brightness)
            else:  # vertical
                cap_len = min(2, self.__width * 0.15)
                self.__render_line(x1 - cap_len, y1, x1 + cap_len, y1, color, 1.0, cap_brightness)
                ey = y1 + (y2 - y1) * progress
                self.__render_line(x2 - cap_len, ey, x2 + cap_len, ey, color, 1.0, cap_brightness)

    def __render_crosshair(self, elem, progress, brightness):
        """Render a pulsing crosshair mark."""
        cx, cy = elem['cx'], elem['cy']
        size = elem['size'] * progress
        color = elem['color']

        self.__render_line(cx - size, cy, cx + size, cy, color, 1.0, brightness)
        self.__render_line(cx, cy - size, cx, cy + size, color, 1.0, brightness)

        if size > 1:
            dist = np.sqrt((self.__gx - cx) ** 2 + (self.__gy - cy) ** 2)
            ring = np.clip(1.0 - np.abs(dist - size * 0.6) / 0.7, 0, 1) * brightness * 0.6
            for c in range(3):
                self.__canvas[:, :, c] = np.maximum(
                    self.__canvas[:, :, c],
                    self._BG[c] + ring * color[c]
                )

    def __render_circle(self, elem, progress, brightness):
        """Render a circle or inscribed polygon being drawn."""
        cx, cy = elem['cx'], elem['cy']
        r = elem['radius']
        color = elem['color']

        if elem['sides'] == 0:
            dist = np.sqrt((self.__gx - cx) ** 2 + (self.__gy - cy) ** 2)
            angle = (np.arctan2(self.__gy - cy, self.__gx - cx) + math.pi) / (2 * math.pi)
            on_ring = np.clip(1.0 - np.abs(dist - r) / 0.8, 0, 1)
            in_progress = angle < progress
            mask = on_ring * in_progress * brightness
            for c in range(3):
                self.__canvas[:, :, c] = np.maximum(
                    self.__canvas[:, :, c],
                    self._BG[c] + mask * color[c]
                )
        else:
            sides = elem['sides']
            edges_to_draw = max(1, int(progress * sides))
            rot = elem['rot']
            for i in range(edges_to_draw):
                a1 = rot + i * 2 * math.pi / sides
                a2 = rot + (i + 1) * 2 * math.pi / sides
                vx1 = cx + r * math.cos(a1)
                vy1 = cy + r * math.sin(a1)
                vx2 = cx + r * math.cos(a2)
                vy2 = cy + r * math.sin(a2)

                edge_progress = 1.0
                if i == edges_to_draw - 1:
                    partial = progress * sides - int(progress * sides)
                    edge_progress = partial if partial > 0 else 1.0

                self.__render_line(vx1, vy1, vx2, vy2, color, edge_progress, brightness)

    @classmethod
    def get_id(cls) -> str:
        return 'blueprint'

    @classmethod
    def get_name(cls) -> str:
        return 'Blueprint'

    @classmethod
    def get_description(cls) -> str:
        return 'Animated technical drawings'
