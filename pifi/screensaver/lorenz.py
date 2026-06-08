import math
import numpy as np
import random

from pifi.config import Config
from pifi.screensaver.colorutils import hsv_to_rgb_bytes
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

        # Lorenz system state
        self.__x = 0.0
        self.__y = 0.0
        self.__z = 0.0

        # Trail of points
        self.__trail = []

        # Rotation angle for 3D projection
        self.__rotation = 0.0

    def _setup(self):
        self.__reset()

    def _tick(self):
        # Lorenz system parameters (classic values)
        sigma = Config.get('screensavers.configs.lorenz.sigma', 10.0)
        rho = Config.get('screensavers.configs.lorenz.rho', 28.0)
        beta = Config.get('screensavers.configs.lorenz.beta', 8.0 / 3.0)

        # Time step for integration
        dt = Config.get('screensavers.configs.lorenz.dt', 0.01)

        # Number of integration steps per frame
        steps_per_frame = Config.get('screensavers.configs.lorenz.steps_per_frame', 5)

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
        max_trail = Config.get('screensavers.configs.lorenz.trail_length', 800)
        if len(self.__trail) > max_trail:
            self.__trail = self.__trail[-max_trail:]

        # Slowly rotate view
        rotation_speed = Config.get('screensavers.configs.lorenz.rotation_speed', 0.005)
        self.__rotation += rotation_speed

        self.__render()

    def __reset(self):
        # Start near the attractor with small random offset
        self.__x = 1.0 + random.uniform(-0.1, 0.1)
        self.__y = 1.0 + random.uniform(-0.1, 0.1)
        self.__z = 1.0 + random.uniform(-0.1, 0.1)

        self.__trail = []
        self.__rotation = random.uniform(0, 2 * math.pi)

    def __render(self):
        frame = np.zeros([self._height, self._width, 3], np.uint8)

        if not self.__trail:
            self._led_frame_player.play_frame(frame)
            return

        # The Lorenz attractor typically spans roughly:
        # x: -20 to 20, y: -30 to 30, z: 0 to 50
        # Use fixed bounds for stable display
        x_range = 40
        y_range = 50
        z_min, z_max = 0, 50

        cx = self._width / 2
        cy = self._height / 2
        scale = min(self._width / x_range, self._height / y_range) * 0.9

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

            if 0 <= screen_x < self._width and 0 <= screen_y < self._height:
                # Color based on z-height (blue at bottom, red at top)
                z_norm = (z - z_min) / (z_max - z_min)
                z_norm = max(0, min(1, z_norm))

                # Hue: blue (0.6) to red (0.0)
                hue = 0.6 - z_norm * 0.6

                # Brightness based on trail position (newer = brighter)
                brightness = 0.3 + 0.7 * (i / len(self.__trail))

                rgb = hsv_to_rgb_bytes(hue, 0.9, brightness)

                # Additive blending
                current = frame[screen_y, screen_x].astype(np.int16)
                new_color = np.minimum(255, current + np.array(rgb, dtype=np.int16))
                frame[screen_y, screen_x] = new_color.astype(np.uint8)

        self._led_frame_player.play_frame(frame)

    @classmethod
    def get_id(cls) -> str:
        return 'lorenz'

    @classmethod
    def get_name(cls) -> str:
        return 'Lorenz Attractor'

    @classmethod
    def get_description(cls) -> str:
        return 'Lorenz attractor butterfly'
