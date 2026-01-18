import math
import numpy as np
import time
import random

from pifi.config import Config
from pifi.logger import Logger
from pifi.led.ledframeplayer import LedFramePlayer
from pifi.screensaver.screensaver import Screensaver


class Mandelbrot(Screensaver):
    """
    Mandelbrot set zoom screensaver.

    Continuously zooms into interesting regions of the Mandelbrot set,
    using smooth coloring based on escape time algorithm.
    """

    # Interesting zoom targets near the boundary (where detail lives)
    ZOOM_TARGETS = [
        # Seahorse valley
        (-0.743643887037151, 0.131825904205330),
        # Elephant valley
        (0.281717921930775, 0.5771052841488505),
        # Double spiral
        (-0.7436438870371587, 0.1318259043091895),
        # Mini Mandelbrot
        (-1.7497591451303665, 0.0),
        # Antenna region
        (-0.1592107937, 1.0342884833),
        # Spiral arm
        (-0.749, 0.1),
        # Triple spiral
        (-0.0452407411, 0.9868162204),
        # Feather
        (-0.8, 0.156),
    ]

    def __init__(self, led_frame_player=None):
        self.__logger = Logger().set_namespace(self.__class__.__name__)

        if led_frame_player is None:
            self.__led_frame_player = LedFramePlayer()
        else:
            self.__led_frame_player = led_frame_player

        self.__width = Config.get_or_throw('leds.display_width')
        self.__height = Config.get_or_throw('leds.display_height')

        # Current view parameters
        self.__center_x = -0.5
        self.__center_y = 0.0
        self.__zoom = 1.0

        # Target for this zoom session
        self.__target_x = 0.0
        self.__target_y = 0.0

        # Color palette
        self.__palette = None

        # Track consecutive black frames for reset detection
        self.__black_frame_count = 0

    def play(self):
        self.__logger.info("Starting Mandelbrot screensaver")
        self.__reset()

        max_ticks = Config.get('mandelbrot.max_ticks', 1500)
        tick = 0

        while tick < max_ticks:
            self.__tick()
            time.sleep(self.__get_tick_sleep())
            tick += 1

        self.__logger.info("Mandelbrot screensaver ended")

    def __reset(self):
        # Start with full view of the set
        self.__center_x = -0.5
        self.__center_y = 0.0
        self.__zoom = 1.0

        # Pick a random interesting target to zoom into
        target = random.choice(self.ZOOM_TARGETS)
        self.__target_x = target[0]
        self.__target_y = target[1]

        # Generate a random color palette
        self.__palette = self.__generate_palette()

        # Reset black frame counter
        self.__black_frame_count = 0

        self.__logger.info(f"Zoom target: ({self.__target_x}, {self.__target_y})")

    def __generate_palette(self):
        """Generate a vibrant color palette for the fractal."""
        palette_size = 256
        palette = np.zeros((palette_size, 3), dtype=np.uint8)

        # Random hue offset for variety
        hue_offset = random.random()

        for i in range(palette_size):
            # Cycle through hues with varying saturation/value
            t = i / palette_size
            hue = (t * 3 + hue_offset) % 1.0  # Multiple color cycles
            sat = 0.7 + 0.3 * math.sin(t * math.pi * 4)
            val = 0.5 + 0.5 * math.sin(t * math.pi * 2)

            palette[i] = self.__hsv_to_rgb(hue, sat, val)

        return palette

    def __tick(self):
        # Smoothly move center towards target
        lerp_factor = Config.get('mandelbrot.lerp_factor', 0.02)
        self.__center_x += (self.__target_x - self.__center_x) * lerp_factor
        self.__center_y += (self.__target_y - self.__center_y) * lerp_factor

        # Exponential zoom
        zoom_speed = Config.get('mandelbrot.zoom_speed', 1.02)
        self.__zoom *= zoom_speed

        black_ratio = self.__render()

        # If frame is all black, we've zoomed into the set interior
        if black_ratio == 1.0:
            self.__black_frame_count += 1
            if self.__black_frame_count >= 5:
                self.__logger.info("Zoomed into black region, picking new target")
                self.__reset()
        else:
            self.__black_frame_count = 0

    def __render(self):
        max_iter = Config.get('mandelbrot.max_iterations', 50)

        # Calculate view bounds
        aspect = self.__width / self.__height
        view_height = 3.0 / self.__zoom
        view_width = view_height * aspect

        x_min = self.__center_x - view_width / 2
        x_max = self.__center_x + view_width / 2
        y_min = self.__center_y - view_height / 2
        y_max = self.__center_y + view_height / 2

        # Create coordinate grids using float32 for speed
        x = np.linspace(x_min, x_max, self.__width, dtype=np.float32)
        y = np.linspace(y_min, y_max, self.__height, dtype=np.float32)
        X, Y = np.meshgrid(x, y)
        C = X + 1j * Y

        # Mandelbrot iteration - fully vectorized
        Z = np.zeros_like(C)
        M = np.zeros(C.shape, dtype=np.float32)  # Iteration count

        for i in range(max_iter):
            mask = np.abs(Z) <= 2
            if not np.any(mask):
                break
            Z[mask] = Z[mask] * Z[mask] + C[mask]
            # Record iteration for newly escaped points
            newly_escaped = (np.abs(Z) > 2) & (M == 0)
            M[newly_escaped] = i + 1

        # Points still inside get 0 (black)
        # M already has 0 for points that never escaped

        # Vectorized color mapping (no Python loops!)
        M_normalized = (M * 4) % 256  # Scale for more color variation
        idx = M_normalized.astype(np.int32)
        idx = np.clip(idx, 0, 255)

        # Direct palette lookup - fully vectorized
        frame = self.__palette[idx].copy()

        # Set interior points to black
        interior_mask = (M == 0)
        frame[interior_mask] = 0

        self.__led_frame_player.play_frame(frame)

        # Return ratio of black (interior) pixels
        total_pixels = self.__width * self.__height
        black_pixels = np.sum(interior_mask)
        return black_pixels / total_pixels

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
        return Config.get('mandelbrot.tick_sleep', 0.05)

    @classmethod
    def get_id(cls) -> str:
        return 'mandelbrot'

    @classmethod
    def get_name(cls) -> str:
        return 'Mandelbrot'

    @classmethod
    def get_description(cls) -> str:
        return 'Mandelbrot set zoom'
