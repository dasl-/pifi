import math
import numpy as np
import random

from pifi.config import Config
from pifi.logger import Logger
from pifi.screensaver.screensaver import Screensaver


class Spirograph(Screensaver):
    """
    Spirograph screensaver with visible gear mechanism.

    Supports multiple curve variants:
    - hypotrochoid: gear rolls inside the ring (classic Spirograph toy)
    - epitrochoid: gear rolls outside the ring
    - compound: two gears chained together (epicycle / guilloché)
    - star_ring: gear rolls inside a star-shaped ring
    """

    VARIANTS = ['hypotrochoid', 'epitrochoid', 'compound', 'star_ring']

    def __init__(self, led_frame_player=None):
        super().__init__(led_frame_player)
        self.__logger = Logger().set_namespace(self.__class__.__name__)

        self.__width = Config.get_or_throw('leds.display_width')
        self.__height = Config.get_or_throw('leds.display_height')

    def _setup(self):
        self.__time = 0.0
        self.__variant = random.choice(self.VARIANTS)

        self.__speed = random.uniform(0.04, 0.08)
        self.__hue_speed = random.uniform(0.001, 0.003)
        self.__cx = self.__width / 2.0
        self.__cy = self.__height / 2.0

        # Trail canvas (persistent, fading)
        self.__canvas = np.zeros((self.__height, self.__width, 3), dtype=np.float64)

        setup_fn, self.__compute_fn = {
            'hypotrochoid': (self.__setup_hypotrochoid, self.__compute_hypotrochoid),
            'epitrochoid': (self.__setup_epitrochoid, self.__compute_epitrochoid),
            'compound': (self.__setup_compound, self.__compute_compound),
            'star_ring': (self.__setup_star_ring, self.__compute_star_ring),
        }[self.__variant]
        setup_fn()

    def __setup_hypotrochoid(self):
        """Gear rolls inside the fixed ring — the classic Spirograph toy."""
        R = random.uniform(0.35, 0.5)
        r = random.uniform(0.08, 0.2)
        d = random.uniform(0.05, r * 1.3)

        # Ensure interesting ratio (avoid exact integer = boring polygon)
        if abs(R / r - round(R / r)) < 0.1:
            r *= 1.1

        # Hypotrochoid stays within R, but d > r creates loops outside (R-r)+d
        max_extent = max(R, (R - r) + d)
        self.__scale = min(self.__width, self.__height) / 2.0 * 0.92 / max_extent
        self.__R, self.__r, self.__d = R, r, d

        self.__logger.info(
            f"Spirograph hypotrochoid: R={R:.3f}, r={r:.3f}, d={d:.3f}")

    def __setup_epitrochoid(self):
        """Gear rolls outside the fixed ring."""
        R = random.uniform(0.3, 0.5)
        r = random.uniform(0.08, 0.25)
        d = random.uniform(0.05, 0.2)

        if abs(R / r - round(R / r)) < 0.1:
            r *= 1.1

        max_extent = R + r + d
        self.__scale = min(self.__width, self.__height) / 2.0 * 0.92 / max_extent
        self.__R, self.__r, self.__d = R, r, d  # pyright: ignore[reportConstantRedefinition]

        self.__logger.info(
            f"Spirograph epitrochoid: R={R:.3f}, r={r:.3f}, d={d:.3f}")

    def __setup_compound(self):
        """Two gears chained — arm1 rotates at f1, arm2 at f2, pen at tip."""
        a1 = random.uniform(0.2, 0.4)
        a2 = random.uniform(0.1, 0.25)

        # Use non-integer frequency ratios for interesting patterns
        nice_ratios = [3/7, 4/9, 5/8, 5/11, 7/11, 3/5, 7/13, 8/13, 5/13]
        ratio = random.choice(nice_ratios)
        if random.random() < 0.5:
            ratio = 1 / ratio
        f1 = 1.0
        f2 = f1 * ratio
        # Randomly reverse second arm direction
        if random.random() < 0.5:
            f2 = -f2

        max_extent = a1 + a2
        self.__scale = min(self.__width, self.__height) / 2.0 * 0.90 / max_extent
        self.__a1, self.__a2 = a1, a2
        self.__f1, self.__f2 = f1, f2

        self.__logger.info(
            f"Spirograph compound: a1={a1:.3f}, a2={a2:.3f}, " +
            f"f1={f1:.3f}, f2={f2:.3f}")

    def __setup_star_ring(self):
        """Gear rolls inside a star/polygon-shaped ring."""
        R = random.uniform(0.35, 0.5)
        r = random.uniform(0.06, 0.15)
        d = random.uniform(0.04, r * 1.2)
        n_points = random.choice([3, 4, 5, 6, 8])
        amplitude = random.uniform(0.1, 0.25)

        if abs(R / r - round(R / r)) < 0.1:
            r *= 1.1

        max_extent = R * (1 + amplitude)
        self.__scale = min(self.__width, self.__height) / 2.0 * 0.90 / max_extent
        self.__R, self.__r, self.__d = R, r, d  # pyright: ignore[reportConstantRedefinition]
        self.__n_points = n_points
        self.__amplitude = amplitude

        self.__logger.info(
            f"Spirograph star_ring: R={R:.3f}, r={r:.3f}, d={d:.3f}, " +
            f"n={n_points}, amp={amplitude:.3f}")

    # ------------------------------------------------------------------
    # Tick
    # ------------------------------------------------------------------

    def _tick(self):
        time_speed = Config.get('screensavers.configs.spirograph.time_speed', 1.0)
        self.__time += time_speed

        t = self.__time * self.__speed
        pen_x, pen_y, mech = self.__compute_fn(t)

        # Convert to screen coords and deposit on trail
        scale = self.__scale
        sx = self.__cx + pen_x * scale
        sy = self.__cy + pen_y * scale

        hue = (self.__time * self.__hue_speed) % 1.0
        color = _hsv_to_rgb(hue, 0.85, 1.0)

        ix, iy = int(round(sx)), int(round(sy))
        if 0 <= ix < self.__width and 0 <= iy < self.__height:
            self.__canvas[iy, ix] = np.minimum(
                1.0, self.__canvas[iy, ix] + np.array(color) * 0.5
            )

        self.__canvas *= 0.999

        display = self.__canvas.copy()
        self.__draw_mechanism(display, mech)

        frame = (np.clip(display, 0, 1) * 255).astype(np.uint8)
        self._led_frame_player.play_frame(frame)

    # ------------------------------------------------------------------
    # Curve math — each returns (pen_x, pen_y, mechanism_dict)
    # ------------------------------------------------------------------

    def __compute_hypotrochoid(self, t):
        R, r, d = self.__R, self.__r, self.__d
        ratio = (R - r) / r

        gear_x = (R - r) * math.cos(t)
        gear_y = (R - r) * math.sin(t)
        pen_x = gear_x + d * math.cos(ratio * t)
        pen_y = gear_y - d * math.sin(ratio * t)

        return pen_x, pen_y, {
            'type': 'ring_gear',
            'ring_cx': 0, 'ring_cy': 0, 'ring_R': R,
            'gear_x': gear_x, 'gear_y': gear_y, 'gear_r': r,
            'pen_x': pen_x, 'pen_y': pen_y,
        }

    def __compute_epitrochoid(self, t):
        R, r, d = self.__R, self.__r, self.__d
        ratio = (R + r) / r

        gear_x = (R + r) * math.cos(t)
        gear_y = (R + r) * math.sin(t)
        pen_x = gear_x - d * math.cos(ratio * t)
        pen_y = gear_y - d * math.sin(ratio * t)

        return pen_x, pen_y, {
            'type': 'ring_gear',
            'ring_cx': 0, 'ring_cy': 0, 'ring_R': R,
            'gear_x': gear_x, 'gear_y': gear_y, 'gear_r': r,
            'pen_x': pen_x, 'pen_y': pen_y,
        }

    def __compute_compound(self, t):
        a1, a2 = self.__a1, self.__a2
        f1, f2 = self.__f1, self.__f2

        arm1_x = a1 * math.cos(f1 * t)
        arm1_y = a1 * math.sin(f1 * t)
        pen_x = arm1_x + a2 * math.cos(f2 * t)
        pen_y = arm1_y + a2 * math.sin(f2 * t)

        return pen_x, pen_y, {
            'type': 'compound',
            'arm1_x': arm1_x, 'arm1_y': arm1_y,
            'arm1_r': a1, 'arm2_r': a2,
            'pen_x': pen_x, 'pen_y': pen_y,
        }

    def __compute_star_ring(self, t):
        R_base, r, d = self.__R, self.__r, self.__d
        n = self.__n_points
        amp = self.__amplitude

        # Modulated ring radius at gear's angular position
        R_eff = R_base * (1 + amp * math.cos(n * t))

        gear_x = (R_eff - r) * math.cos(t)
        gear_y = (R_eff - r) * math.sin(t)

        # Gear rotation with phase modulation from the non-circular ring
        ratio = (R_base - r) / r
        phase_mod = amp * R_base / r * math.sin(n * t) / n
        gear_angle = ratio * t + phase_mod

        pen_x = gear_x + d * math.cos(gear_angle)
        pen_y = gear_y - d * math.sin(gear_angle)

        return pen_x, pen_y, {
            'type': 'star_ring',
            'gear_x': gear_x, 'gear_y': gear_y, 'gear_r': r,
            'pen_x': pen_x, 'pen_y': pen_y,
            'ring_R_base': R_base, 'n_points': n, 'amplitude': amp,
        }

    # ------------------------------------------------------------------
    # Mechanism drawing
    # ------------------------------------------------------------------

    def __draw_mechanism(self, canvas, mech):
        scale = self.__scale
        cx, cy = self.__cx, self.__cy

        gear_color = np.array([0.15, 0.15, 0.2])
        ring_color = np.array([0.1, 0.1, 0.15])

        hue = (self.__time * self.__hue_speed) % 1.0
        pen_color = np.array(_hsv_to_rgb(hue, 0.7, 1.0))

        if mech['type'] == 'ring_gear':
            # Fixed ring
            self.__draw_circle(canvas, cx, cy, mech['ring_R'] * scale, ring_color)

            # Rolling gear
            gcx = cx + mech['gear_x'] * scale
            gcy = cy + mech['gear_y'] * scale
            self.__draw_circle(canvas, gcx, gcy, mech['gear_r'] * scale, gear_color)

            # Arm to pen
            px = cx + mech['pen_x'] * scale
            py = cy + mech['pen_y'] * scale
            self.__draw_line(canvas, gcx, gcy, px, py, gear_color * 1.5)

            # Pen dot
            self.__draw_dot(canvas, px, py, pen_color)

        elif mech['type'] == 'compound':
            # Orbit circles (faint guides)
            self.__draw_circle(canvas, cx, cy, mech['arm1_r'] * scale,
                               ring_color * 0.6)

            # Arm 1: center to first joint
            a1x = cx + mech['arm1_x'] * scale
            a1y = cy + mech['arm1_y'] * scale
            self.__draw_line(canvas, cx, cy, a1x, a1y, gear_color * 1.2)
            self.__draw_dot(canvas, a1x, a1y, gear_color * 2)

            # Arm 2: first joint to pen
            px = cx + mech['pen_x'] * scale
            py = cy + mech['pen_y'] * scale
            self.__draw_line(canvas, a1x, a1y, px, py, gear_color * 1.5)

            # Pen dot
            self.__draw_dot(canvas, px, py, pen_color)

        elif mech['type'] == 'star_ring':
            # Star-shaped ring
            R_base = mech['ring_R_base'] * scale
            n = mech['n_points']
            amp = mech['amplitude']
            circumference = max(16, int(2 * math.pi * R_base * 2.0))
            for i in range(circumference):
                angle = 2 * math.pi * i / circumference
                R_eff = R_base * (1 + amp * math.cos(n * angle))
                px = int(round(cx + R_eff * math.cos(angle)))
                py = int(round(cy + R_eff * math.sin(angle)))
                if 0 <= px < self.__width and 0 <= py < self.__height:
                    canvas[py, px] = np.maximum(canvas[py, px], ring_color)

            # Rolling gear
            gcx = cx + mech['gear_x'] * scale
            gcy = cy + mech['gear_y'] * scale
            self.__draw_circle(canvas, gcx, gcy, mech['gear_r'] * scale,
                               gear_color)

            # Arm to pen
            px = cx + mech['pen_x'] * scale
            py = cy + mech['pen_y'] * scale
            self.__draw_line(canvas, gcx, gcy, px, py, gear_color * 1.5)

            # Pen dot
            self.__draw_dot(canvas, px, py, pen_color)

    # ------------------------------------------------------------------
    # Drawing primitives
    # ------------------------------------------------------------------

    def __draw_dot(self, canvas, x, y, color):
        ix, iy = int(round(x)), int(round(y))
        if 0 <= ix < self.__width and 0 <= iy < self.__height:
            canvas[iy, ix] = np.maximum(canvas[iy, ix], color)

    def __draw_circle(self, canvas, cx, cy, radius, color):
        """Draw a 1-pixel circle outline."""
        circumference = max(8, int(2 * math.pi * radius * 1.5))
        for i in range(circumference):
            angle = 2 * math.pi * i / circumference
            px = int(round(cx + radius * math.cos(angle)))
            py = int(round(cy + radius * math.sin(angle)))
            if 0 <= px < self.__width and 0 <= py < self.__height:
                canvas[py, px] = np.maximum(canvas[py, px], color)

    def __draw_line(self, canvas, x1, y1, x2, y2, color):
        """Draw a 1-pixel line."""
        dx, dy = x2 - x1, y2 - y1
        steps = max(1, int(max(abs(dx), abs(dy)) * 1.5))
        for s in range(steps + 1):
            frac = s / steps
            px = int(round(x1 + dx * frac))
            py = int(round(y1 + dy * frac))
            if 0 <= px < self.__width and 0 <= py < self.__height:
                canvas[py, px] = np.maximum(canvas[py, px], color)

    @classmethod
    def get_id(cls) -> str:
        return 'spirograph'

    @classmethod
    def get_name(cls) -> str:
        return 'Spirograph'

    @classmethod
    def get_description(cls) -> str:
        return 'Gear-drawn geometric patterns'


def _hsv_to_rgb(h, s, v):
    h = h % 1.0
    i = int(h * 6)
    f = h * 6 - i
    p = v * (1 - s)
    q = v * (1 - s * f)
    t = v * (1 - s * (1 - f))
    i = i % 6
    if i == 0: return (v, t, p)
    elif i == 1: return (q, v, p)
    elif i == 2: return (p, v, t)
    elif i == 3: return (p, q, v)
    elif i == 4: return (t, p, v)
    else: return (v, p, q)
