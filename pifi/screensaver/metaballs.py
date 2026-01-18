import math
import numpy as np
import time
import random

from pifi.config import Config
from pifi.logger import Logger
from pifi.led.ledframeplayer import LedFramePlayer
from pifi.screensaver.screensaver import Screensaver


class Metaballs(Screensaver):
    """
    Metaballs (blobby) screensaver.

    Simulates organic blob-like shapes that merge and separate smoothly.
    Uses an implicit surface technique where the "energy" from multiple
    point sources creates smooth, flowing shapes.
    """

    def __init__(self, led_frame_player=None):
        self.__logger = Logger().set_namespace(self.__class__.__name__)

        if led_frame_player is None:
            self.__led_frame_player = LedFramePlayer()
        else:
            self.__led_frame_player = led_frame_player

        self.__width = Config.get_or_throw('leds.display_width')
        self.__height = Config.get_or_throw('leds.display_height')

        # Metaballs: each is [x, y, radius, vx, vy, hue]
        self.__balls = []
        self.__time = 0.0

        # Precompute coordinate grids
        x = np.arange(self.__width)
        y = np.arange(self.__height)
        self.__grid_x, self.__grid_y = np.meshgrid(x, y)

    def play(self):
        self.__logger.info("Starting Metaballs screensaver")
        self.__reset()

        max_ticks = Config.get('metaballs.max_ticks', 2000)
        tick = 0

        while tick < max_ticks:
            self.__tick()
            time.sleep(self.__get_tick_sleep())
            tick += 1

        self.__logger.info("Metaballs screensaver ended")

    def __reset(self):
        num_balls = Config.get('metaballs.num_balls', 5)
        self.__balls = []

        for i in range(num_balls):
            self.__balls.append(self.__create_ball(i, num_balls))

        self.__time = 0.0

    def __create_ball(self, index, total):
        """Create a metaball with random properties."""
        x = random.uniform(0, self.__width)
        y = random.uniform(0, self.__height)

        # Radius affects the "strength" of the metaball
        min_radius = min(self.__width, self.__height) * 0.15
        max_radius = min(self.__width, self.__height) * 0.35
        radius = random.uniform(min_radius, max_radius)

        # Random velocity
        speed = Config.get('metaballs.speed', 0.5)
        angle = random.uniform(0, 2 * math.pi)
        vx = math.cos(angle) * speed
        vy = math.sin(angle) * speed

        # Evenly distributed hues
        hue = (index / total + random.uniform(-0.1, 0.1)) % 1.0

        return [x, y, radius, vx, vy, hue]

    def __tick(self):
        self.__update_balls()
        self.__render()
        self.__time += 0.1

    def __update_balls(self):
        """Update ball positions with smooth movement."""
        for ball in self.__balls:
            # Add some sinusoidal wobble for organic movement
            wobble_x = math.sin(self.__time * 0.5 + ball[5] * 10) * 0.2
            wobble_y = math.cos(self.__time * 0.7 + ball[5] * 10) * 0.2

            ball[0] += ball[3] + wobble_x
            ball[1] += ball[4] + wobble_y

            # Bounce off edges with some padding
            padding = ball[2] * 0.3
            if ball[0] < padding or ball[0] >= self.__width - padding:
                ball[3] *= -1
                ball[0] = max(padding, min(self.__width - padding - 1, ball[0]))
            if ball[1] < padding or ball[1] >= self.__height - padding:
                ball[4] *= -1
                ball[1] = max(padding, min(self.__height - padding - 1, ball[1]))

    def __render(self):
        # Calculate metaball field
        # For each pixel, sum the contribution from each ball
        # Contribution = radius^2 / distance^2 (inverse square falloff)

        field = np.zeros((self.__height, self.__width), dtype=np.float64)
        color_field = np.zeros((self.__height, self.__width, 3), dtype=np.float64)

        for ball in self.__balls:
            bx, by, radius, _, _, hue = ball

            # Distance from this ball to each pixel
            dx = self.__grid_x - bx
            dy = self.__grid_y - by
            dist_sq = dx * dx + dy * dy

            # Avoid division by zero
            dist_sq = np.maximum(dist_sq, 0.1)

            # Metaball contribution (inverse square)
            contribution = (radius * radius) / dist_sq
            field += contribution

            # Weighted color contribution
            rgb = self.__hsv_to_rgb(hue, 0.8, 1.0)
            for c in range(3):
                color_field[:, :, c] += contribution * rgb[c]

        # Threshold the field to create blob shapes
        threshold = Config.get('metaballs.threshold', 1.0)

        # Normalize colors by field strength
        field_safe = np.maximum(field, 0.001)
        for c in range(3):
            color_field[:, :, c] /= field_safe

        # Apply threshold with smooth falloff
        # Values above threshold are fully lit, below fade out
        intensity = np.clip((field - threshold * 0.5) / (threshold * 0.5), 0, 1)

        # Create frame
        frame = np.zeros([self.__height, self.__width, 3], np.uint8)

        for c in range(3):
            frame[:, :, c] = (color_field[:, :, c] * intensity * 255).astype(np.uint8)

        # Add glow effect at the edges
        glow = Config.get('metaballs.glow', True)
        if glow:
            edge_intensity = np.clip((field - threshold * 0.3) / (threshold * 0.3), 0, 1)
            edge_intensity = edge_intensity * (1 - intensity) * 0.5
            for c in range(3):
                glow_add = (color_field[:, :, c] * edge_intensity * 128).astype(np.uint8)
                frame[:, :, c] = np.minimum(255, frame[:, :, c].astype(np.int16) + glow_add).astype(np.uint8)

        self.__led_frame_player.play_frame(frame)

    def __hsv_to_rgb(self, h, s, v):
        """Convert HSV color to RGB."""
        if s == 0.0:
            return [int(v * 255)] * 3

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
        return Config.get('metaballs.tick_sleep', 0.04)

    @classmethod
    def get_id(cls) -> str:
        return 'metaballs'

    @classmethod
    def get_name(cls) -> str:
        return 'Metaballs'

    @classmethod
    def get_description(cls) -> str:
        return 'Blobby merging shapes'
