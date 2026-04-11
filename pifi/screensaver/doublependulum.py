import numpy as np
import random
import math

from pifi.config import Config
from pifi.logger import Logger
from pifi.screensaver.screensaver import Screensaver


class DoublePendulum(Screensaver):
    """
    Double pendulum — chaotic system traced as a glowing line.

    Simulates two connected pendulums. The tip of the second arm
    traces a path that never repeats, fading over time into a
    beautiful chaotic trail.
    """

    def __init__(self, led_frame_player=None):
        super().__init__(led_frame_player)

        self.__width = Config.get_or_throw('leds.display_width')
        self.__height = Config.get_or_throw('leds.display_height')

    def _setup(self):
        self.__time = 0.0
        self.__hue_base = random.random()

        # Canvas for trail (float for smooth fading)
        self.__canvas = np.zeros((self.__height, self.__width, 3), dtype=np.float64)

        # Pendulum parameters — scale to use most of the screen.
        # Total arm length is constrained by horizontal half-width,
        # then the pivot is placed so the fully extended pendulum
        # just touches the bottom of the screen.
        bob_radius = 2  # must match the radius used in __draw_arms
        max_reach = (self.__width / 2 - 1 - bob_radius) * 0.85
        self.__l1 = max_reach * random.uniform(0.45, 0.55)
        self.__l2 = max_reach - self.__l1
        self.__m1 = random.uniform(0.8, 1.2)
        self.__m2 = random.uniform(0.8, 1.2)
        self.__g = 9.81

        # Initial angles — start high for chaotic motion
        self.__theta1 = random.uniform(1.5, 3.0) * random.choice([-1, 1])
        self.__theta2 = random.uniform(1.0, 2.5) * random.choice([-1, 1])
        self.__omega1 = random.uniform(-0.5, 0.5)
        self.__omega2 = random.uniform(-0.5, 0.5)

        # Center point (pivot) — placed so fully extended pendulum
        # reaches the bottom row of the screen.
        self.__cx = self.__width / 2
        self.__cy = self.__height - 1 - bob_radius - (self.__l1 + self.__l2)

        # Previous tip position for line drawing
        self.__prev_x = None
        self.__prev_y = None

        # Steps per tick (smaller dt = more accurate)
        self.__steps_per_tick = 8
        self.__dt = 0.01

        # Trail fade rate
        self.__fade = 0.985

    def _tick(self, tick):
        self.__time += self.__dt * self.__steps_per_tick

        # Fade trail
        self.__canvas *= self.__fade

        # Simulate multiple physics steps per frame
        for _ in range(self.__steps_per_tick):
            self.__step()

            # Get tip position
            x2, y2 = self.__tip_position()

            # Draw line from previous position
            if self.__prev_x is not None:
                self.__draw_line(self.__prev_x, self.__prev_y, x2, y2)

            self.__prev_x = x2
            self.__prev_y = y2

        # Draw arms onto a temporary copy so they don't ghost into the trail
        display = self.__canvas.copy()
        self.__draw_arms(display)

        frame = (np.clip(display, 0, 1) * 255).astype(np.uint8)
        self._led_frame_player.play_frame(frame)

    def __step(self):
        """RK4 integration of double pendulum equations."""
        state = np.array([self.__theta1, self.__omega1, self.__theta2, self.__omega2])

        k1 = self.__derivs(state)
        k2 = self.__derivs(state + 0.5 * self.__dt * k1)
        k3 = self.__derivs(state + 0.5 * self.__dt * k2)
        k4 = self.__derivs(state + self.__dt * k3)

        state += self.__dt / 6.0 * (k1 + 2 * k2 + 2 * k3 + k4)

        self.__theta1 = state[0]
        self.__omega1 = state[1]
        self.__theta2 = state[2]
        self.__omega2 = state[3]

    def __derivs(self, state):
        """Compute derivatives for the double pendulum system."""
        t1, w1, t2, w2 = state
        m1, m2 = self.__m1, self.__m2
        l1, l2 = self.__l1, self.__l2
        g = self.__g

        delta = t1 - t2
        sin_d = math.sin(delta)
        cos_d = math.cos(delta)

        denom1 = (m1 + m2) * l1 - m2 * l1 * cos_d * cos_d
        denom2 = (l2 / l1) * denom1

        a1 = (-m2 * l1 * w1 * w1 * sin_d * cos_d +
              m2 * g * math.sin(t2) * cos_d -
              m2 * l2 * w2 * w2 * sin_d -
              (m1 + m2) * g * math.sin(t1)) / denom1

        a2 = (m2 * l2 * w2 * w2 * sin_d * cos_d +
              (m1 + m2) * g * math.sin(t1) * cos_d +
              (m1 + m2) * l1 * w1 * w1 * sin_d -
              (m1 + m2) * g * math.sin(t2)) / denom2

        return np.array([w1, a1, w2, a2])

    def __tip_position(self):
        """Get the (x, y) position of the second pendulum's tip."""
        x1 = self.__cx + self.__l1 * math.sin(self.__theta1)
        y1 = self.__cy + self.__l1 * math.cos(self.__theta1)
        x2 = x1 + self.__l2 * math.sin(self.__theta2)
        y2 = y1 + self.__l2 * math.cos(self.__theta2)
        return x2, y2

    def __draw_line(self, x1, y1, x2, y2):
        """Draw a line between two points with anti-aliasing."""
        # Bresenham-ish with sub-pixel blending
        dist = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        steps = max(1, int(dist * 2))

        # Trail color — hue shifts slowly over time
        hue = (self.__hue_base + self.__time * 0.02) % 1.0
        r, g, b = _hsv_to_rgb_scalar(hue, 0.8, 1.0)

        for s in range(steps + 1):
            t = s / steps if steps > 0 else 0
            px = x1 + (x2 - x1) * t
            py = y1 + (y2 - y1) * t

            ix = int(round(px))
            iy = int(round(py))

            if 0 <= ix < self.__width and 0 <= iy < self.__height:
                self.__canvas[iy, ix, 0] = min(1.0, self.__canvas[iy, ix, 0] + r * 0.4)
                self.__canvas[iy, ix, 1] = min(1.0, self.__canvas[iy, ix, 1] + g * 0.4)
                self.__canvas[iy, ix, 2] = min(1.0, self.__canvas[iy, ix, 2] + b * 0.4)

    def __draw_arms(self, canvas):
        """Draw the pendulum arms and bobs clearly on top of the trail."""
        x1 = self.__cx + self.__l1 * math.sin(self.__theta1)
        y1 = self.__cy + self.__l1 * math.cos(self.__theta1)
        x2 = x1 + self.__l2 * math.sin(self.__theta2)
        y2 = y1 + self.__l2 * math.cos(self.__theta2)

        arm_color = np.array([0.45, 0.45, 0.55])

        # Draw arms as visible lines
        for ax1, ay1, ax2, ay2 in [(self.__cx, self.__cy, x1, y1), (x1, y1, x2, y2)]:
            dist = math.sqrt((ax2 - ax1) ** 2 + (ay2 - ay1) ** 2)
            steps = max(1, int(dist * 3))
            for s in range(steps + 1):
                t = s / steps if steps > 0 else 0
                px = ax1 + (ax2 - ax1) * t
                py = ay1 + (ay2 - ay1) * t
                ix, iy = int(round(px)), int(round(py))
                if 0 <= ix < self.__width and 0 <= iy < self.__height:
                    canvas[iy, ix] = np.maximum(canvas[iy, ix], arm_color)

        # Draw bobs as bright discs — pivot, joint, and tip
        hue = (self.__hue_base + self.__time * 0.02) % 1.0
        tip_r, tip_g, tip_b = _hsv_to_rgb_scalar(hue, 0.7, 1.0)
        bobs = [
            (self.__cx, self.__cy, 1, np.array([0.5, 0.5, 0.6])),     # pivot — small, dim
            (x1, y1, 2, np.array([0.8, 0.8, 0.9])),                    # joint — medium
            (x2, y2, 2, np.array([tip_r, tip_g, tip_b])),              # tip — bright, colored
        ]
        for bx, by, radius, color in bobs:
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    if dx * dx + dy * dy <= radius * radius:
                        ix = int(round(bx)) + dx
                        iy = int(round(by)) + dy
                        if 0 <= ix < self.__width and 0 <= iy < self.__height:
                            canvas[iy, ix] = np.maximum(canvas[iy, ix], color)

    @classmethod
    def get_id(cls) -> str:
        return 'double_pendulum'

    @classmethod
    def get_name(cls) -> str:
        return 'Double Pendulum'

    @classmethod
    def get_description(cls) -> str:
        return 'Chaotic pendulum trail'


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
