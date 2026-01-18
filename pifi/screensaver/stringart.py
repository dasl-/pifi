"""
String Art screensaver.

Lines drawn between points on a circle create beautiful
curved envelope patterns through straight lines alone.
"""

import math
import numpy as np
import time

from pifi.config import Config
from pifi.led.ledframeplayer import LedFramePlayer
from pifi.logger import Logger
from pifi.screensaver.screensaver import Screensaver


class StringArt(Screensaver):
    """Animated string art patterns with evolving parameters."""

    def __init__(self, led_frame_player=None):
        super().__init__(led_frame_player)
        self.__logger = Logger().set_namespace(self.__class__.__name__)

        if led_frame_player is None:
            led_frame_player = LedFramePlayer()
        self.__led_frame_player = led_frame_player

        self.__width = Config.get('leds.display_width')
        self.__height = Config.get('leds.display_height')

        # Config
        self.__num_points = Config.get('stringart.num_points', 64)
        self.__num_strings = Config.get('stringart.num_strings', 32)
        self.__multiplier_speed = Config.get('stringart.multiplier_speed', 0.02)
        self.__rotation_speed = Config.get('stringart.rotation_speed', 0.01)
        self.__fade = Config.get('stringart.fade', 0.15)
        self.__line_brightness = Config.get('stringart.line_brightness', 0.4)
        self.__tick_sleep = Config.get('stringart.tick_sleep', 0.03)
        self.__max_ticks = Config.get('stringart.max_ticks', 10000)

        # Canvas buffer
        self.__canvas = np.zeros((self.__height, self.__width, 3), dtype=np.float32)

        # Animation state
        self.__multiplier = 2.0  # Connection multiplier (creates different patterns)
        self.__rotation = 0.0
        self.__hue = 0.0
        self.__tick = 0

    def __init_pattern(self):
        """Initialize the pattern."""
        self.__multiplier = 2.0
        self.__rotation = 0.0
        self.__hue = np.random.random()
        self.__canvas.fill(0)
        self.__tick = 0

    def __get_circle_point(self, index, radius, center_x, center_y):
        """Get a point on the circle."""
        angle = (index / self.__num_points) * 2 * math.pi + self.__rotation
        x = center_x + math.cos(angle) * radius
        y = center_y + math.sin(angle) * radius
        return x, y

    def __hsv_to_rgb(self, h, s, v):
        """Convert HSV to RGB."""
        if s == 0:
            return v, v, v

        h = h % 1.0
        i = int(h * 6)
        f = h * 6 - i
        p = v * (1 - s)
        q = v * (1 - s * f)
        t = v * (1 - s * (1 - f))

        if i == 0:
            return v, t, p
        elif i == 1:
            return q, v, p
        elif i == 2:
            return p, v, t
        elif i == 3:
            return p, q, v
        elif i == 4:
            return t, p, v
        else:
            return v, p, q

    def __draw_line(self, x0, y0, x1, y1, r, g, b):
        """Draw a line using Bresenham's algorithm with additive blending."""
        # Convert to integers first
        x0, y0 = int(x0), int(y0)
        x1, y1 = int(x1), int(y1)

        # Clip to bounds
        x0 = max(0, min(self.__width - 1, x0))
        y0 = max(0, min(self.__height - 1, y0))
        x1 = max(0, min(self.__width - 1, x1))
        y1 = max(0, min(self.__height - 1, y1))

        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy

        x, y = x0, y0

        for _ in range(max(dx, dy) + 1):  # Safeguard against infinite loop
            if 0 <= x < self.__width and 0 <= y < self.__height:
                self.__canvas[y, x, 0] = min(1.0, self.__canvas[y, x, 0] + r * self.__line_brightness)
                self.__canvas[y, x, 1] = min(1.0, self.__canvas[y, x, 1] + g * self.__line_brightness)
                self.__canvas[y, x, 2] = min(1.0, self.__canvas[y, x, 2] + b * self.__line_brightness)

            if x == x1 and y == y1:
                break

            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy

    def __update(self):
        """Update and draw the string art pattern."""
        # Fade existing canvas
        self.__canvas *= (1.0 - self.__fade)

        # Calculate circle parameters
        center_x = self.__width / 2
        center_y = self.__height / 2
        radius = min(self.__width, self.__height) / 2 - 1

        # Draw strings
        for i in range(self.__num_strings):
            # Starting point index (evenly distributed)
            start_idx = (i * self.__num_points) / self.__num_strings

            # Ending point is determined by the multiplier
            end_idx = (start_idx * self.__multiplier) % self.__num_points

            # Get actual coordinates
            x0, y0 = self.__get_circle_point(start_idx, radius, center_x, center_y)
            x1, y1 = self.__get_circle_point(end_idx, radius, center_x, center_y)

            # Color based on position with hue shift
            line_hue = (self.__hue + i / self.__num_strings * 0.3) % 1.0
            r, g, b = self.__hsv_to_rgb(line_hue, 0.8, 1.0)

            self.__draw_line(x0, y0, x1, y1, r, g, b)

        # Animate
        self.__multiplier += self.__multiplier_speed
        if self.__multiplier > 10:
            self.__multiplier = 2.0

        self.__rotation += self.__rotation_speed
        self.__hue = (self.__hue + 0.001) % 1.0
        self.__tick += 1

    def play(self):
        """Run the screensaver."""
        self.__logger.info("Starting String Art screensaver")
        self.__init_pattern()

        for tick in range(self.__max_ticks):
            self.__update()

            # Convert to uint8 frame
            frame = (np.clip(self.__canvas, 0, 1) * 255).astype(np.uint8)

            self.__led_frame_player.play_frame(frame)
            time.sleep(self.__tick_sleep)

        self.__logger.info("String Art screensaver ended")

    @classmethod
    def get_id(cls) -> str:
        return 'stringart'

    @classmethod
    def get_name(cls) -> str:
        return 'String Art'

    @classmethod
    def get_description(cls) -> str:
        return 'Curved envelopes from lines'
