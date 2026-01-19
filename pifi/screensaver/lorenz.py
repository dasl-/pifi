import math
import numpy as np
import time
import random

from pifi.config import Config
from pifi.logger import Logger
from pifi.led.ledframeplayer import LedFramePlayer
from pifi.screensaver.screensaver import Screensaver


class Lorenz(Screensaver):
    """
    Lorenz attractor screensaver.

    Visualizes the famous Lorenz system - a set of differential equations
    that produce beautiful chaotic "butterfly" patterns. The system is
    sensitive to initial conditions, creating endlessly varying trajectories.
    """

    def __init__(self, led_frame_player=None):
        super().__init__(led_frame_player)
        self.__logger = Logger().set_namespace(self.__class__.__name__)

        if led_frame_player is None:
            self.__led_frame_player = LedFramePlayer()
        else:
            self.__led_frame_player = led_frame_player

        self.__width = Config.get_or_throw('leds.display_width')
        self.__height = Config.get_or_throw('leds.display_height')

        # Lorenz system state
        self.__x = 0.0
        self.__y = 0.0
        self.__z = 0.0

        # Trail of points
        self.__trail = []

        # Rotation angle for 3D projection
        self.__rotation = 0.0

    def play(self):
        self.__logger.info("Starting Lorenz attractor screensaver")
        self.__reset()

        max_ticks = Config.get('lorenz.max_ticks', 3000)
        tick = 0

        while tick < max_ticks:
            self.__tick()
            time.sleep(self.__get_tick_sleep())
            tick += 1

        self.__logger.info("Lorenz attractor screensaver ended")

    def __reset(self):
        # Start near the attractor with small random offset
        self.__x = 1.0 + random.uniform(-0.1, 0.1)
        self.__y = 1.0 + random.uniform(-0.1, 0.1)
        self.__z = 1.0 + random.uniform(-0.1, 0.1)

        self.__trail = []
        self.__rotation = random.uniform(0, 2 * math.pi)

    def __tick(self):
        # Lorenz system parameters (classic values)
        sigma = Config.get('lorenz.sigma', 10.0)
        rho = Config.get('lorenz.rho', 28.0)
        beta = Config.get('lorenz.beta', 8.0 / 3.0)

        # Time step for integration
        dt = Config.get('lorenz.dt', 0.01)

        # Number of integration steps per frame
        steps_per_frame = Config.get('lorenz.steps_per_frame', 5)

        for _ in range(steps_per_frame):
            # Lorenz equations (Euler integration)
            dx = sigma * (self.__y - self.__x)
            dy = self.__x * (rho - self.__z) - self.__y
            dz = self.__x * self.__y - beta * self.__z

            self.__x += dx * dt
            self.__y += dy * dt
            self.__z += dz * dt

            # Store point with color based on z-height
            self.__trail.append((self.__x, self.__y, self.__z))

        # Limit trail length
        max_trail = Config.get('lorenz.trail_length', 800)
        if len(self.__trail) > max_trail:
            self.__trail = self.__trail[-max_trail:]

        # Slowly rotate view
        rotation_speed = Config.get('lorenz.rotation_speed', 0.005)
        self.__rotation += rotation_speed

        self.__render()

    def __render(self):
        frame = np.zeros([self.__height, self.__width, 3], np.uint8)

        if not self.__trail:
            self.__led_frame_player.play_frame(frame)
            return

        # Find bounds for scaling
        xs = [p[0] for p in self.__trail]
        ys = [p[1] for p in self.__trail]
        zs = [p[2] for p in self.__trail]

        # The Lorenz attractor typically spans roughly:
        # x: -20 to 20, y: -30 to 30, z: 0 to 50
        # Use fixed bounds for stable display
        x_range = 40
        y_range = 50
        z_min, z_max = 0, 50

        cx = self.__width / 2
        cy = self.__height / 2
        scale = min(self.__width / x_range, self.__height / y_range) * 0.9

        # Render trail with 3D rotation
        cos_r = math.cos(self.__rotation)
        sin_r = math.sin(self.__rotation)

        for i, (x, y, z) in enumerate(self.__trail):
            # Rotate around z-axis
            rx = x * cos_r - y * sin_r
            ry = x * sin_r + y * cos_r

            # Project to 2D (simple orthographic with slight z influence)
            screen_x = int(cx + rx * scale)
            screen_y = int(cy - (ry * 0.7 + (z - 25) * 0.3) * scale)

            if 0 <= screen_x < self.__width and 0 <= screen_y < self.__height:
                # Color based on z-height (blue at bottom, red at top)
                z_norm = (z - z_min) / (z_max - z_min)
                z_norm = max(0, min(1, z_norm))

                # Hue: blue (0.6) to red (0.0)
                hue = 0.6 - z_norm * 0.6

                # Brightness based on trail position (newer = brighter)
                brightness = 0.3 + 0.7 * (i / len(self.__trail))

                rgb = self.__hsv_to_rgb(hue, 0.9, brightness)

                # Additive blending
                current = frame[screen_y, screen_x].astype(np.int16)
                new_color = np.minimum(255, current + np.array(rgb, dtype=np.int16))
                frame[screen_y, screen_x] = new_color.astype(np.uint8)

        self.__led_frame_player.play_frame(frame)

    def __hsv_to_rgb(self, h, s, v):
        """Convert HSV color to RGB."""
        if s == 0.0:
            return [int(v * 255)] * 3

        h = h % 1.0
        i = int(h * 6.0)
        f = (h * 6.0) - i
        p = v * (1.0 - s)
        q = v * (1.0 - s * f)
        t = v * (1.0 - s * (1.0 - f))
        i = i % 6

        if i == 0:
            r, g, b = v, t, p
        elif i == 1:
            r, g, b = q, v, p
        elif i == 2:
            r, g, b = p, v, t
        elif i == 3:
            r, g, b = p, q, v
        elif i == 4:
            r, g, b = t, p, v
        else:
            r, g, b = v, p, q

        return [int(r * 255), int(g * 255), int(b * 255)]

    def __get_tick_sleep(self):
        return Config.get('lorenz.tick_sleep', 0.03)

    @classmethod
    def get_id(cls) -> str:
        return 'lorenz'

    @classmethod
    def get_name(cls) -> str:
        return 'Lorenz Attractor'

    @classmethod
    def get_description(cls) -> str:
        return 'Lorenz attractor butterfly'
