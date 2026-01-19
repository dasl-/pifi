import numpy as np
import time
import random

from pifi.config import Config
from pifi.logger import Logger
from pifi.led.ledframeplayer import LedFramePlayer
from pifi.screensaver.screensaver import Screensaver


class DvdBounce(Screensaver):
    """
    DVD logo bounce screensaver.

    A rectangular logo bounces around the screen, changing color
    each time it hits an edge. The anticipation of hitting a corner
    perfectly is the best part!
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

        # Logo dimensions
        self.__logo_width = Config.get('dvd_bounce.logo_width', 8)
        self.__logo_height = Config.get('dvd_bounce.logo_height', 4)

        # Position (float for smooth movement)
        self.__x = 0.0
        self.__y = 0.0

        # Velocity
        self.__vx = 0.0
        self.__vy = 0.0

        # Current color
        self.__color = [255, 255, 255]

        # Corner hit counter (for fun!)
        self.__corner_hits = 0

    def play(self):
        self.__logger.info("Starting DVD Bounce screensaver")
        self.__reset()

        max_ticks = Config.get('dvd_bounce.max_ticks', 10000)
        tick = 0

        while tick < max_ticks:
            self.__tick()
            time.sleep(self.__get_tick_sleep())
            tick += 1

        self.__logger.info(f"DVD Bounce ended. Corner hits: {self.__corner_hits}")

    def __reset(self):
        """Initialize the bouncing logo."""
        # Start at a random position
        self.__x = random.uniform(0, self.__width - self.__logo_width)
        self.__y = random.uniform(0, self.__height - self.__logo_height)

        # Random initial velocity
        speed = Config.get('dvd_bounce.speed', 0.5)
        angle = random.uniform(0, 2 * np.pi)
        self.__vx = speed * np.cos(angle)
        self.__vy = speed * np.sin(angle)

        # Ensure we're actually moving
        if abs(self.__vx) < 0.1:
            self.__vx = 0.3 if self.__vx >= 0 else -0.3
        if abs(self.__vy) < 0.1:
            self.__vy = 0.3 if self.__vy >= 0 else -0.3

        # Random initial color
        self.__color = self.__random_color()
        self.__corner_hits = 0

    def __tick(self):
        """Update position and check for bounces."""
        # Update position
        self.__x += self.__vx
        self.__y += self.__vy

        # Check for bounces
        bounced_x = False
        bounced_y = False

        # Left/right edges
        if self.__x <= 0:
            self.__x = 0
            self.__vx = abs(self.__vx)
            bounced_x = True
        elif self.__x >= self.__width - self.__logo_width:
            self.__x = self.__width - self.__logo_width
            self.__vx = -abs(self.__vx)
            bounced_x = True

        # Top/bottom edges
        if self.__y <= 0:
            self.__y = 0
            self.__vy = abs(self.__vy)
            bounced_y = True
        elif self.__y >= self.__height - self.__logo_height:
            self.__y = self.__height - self.__logo_height
            self.__vy = -abs(self.__vy)
            bounced_y = True

        # Change color on bounce
        if bounced_x or bounced_y:
            self.__color = self.__random_color()

            # Check for corner hit!
            if bounced_x and bounced_y:
                self.__corner_hits += 1
                self.__logger.info(f"🎯 CORNER HIT! Total: {self.__corner_hits}")

        self.__render()

    def __random_color(self):
        """Generate a random bright color."""
        color_mode = Config.get('dvd_bounce.color_mode', 'random')

        if color_mode == 'random':
            # Random bright color
            colors = [
                [255, 0, 0],      # Red
                [0, 255, 0],      # Green
                [0, 0, 255],      # Blue
                [255, 255, 0],    # Yellow
                [255, 0, 255],    # Magenta
                [0, 255, 255],    # Cyan
                [255, 128, 0],    # Orange
                [128, 0, 255],    # Purple
                [255, 255, 255],  # White
            ]
            return random.choice(colors)
        elif color_mode == 'rainbow':
            # Rainbow hue cycling
            hue = random.random()
            return self.__hsv_to_rgb(hue, 1.0, 1.0)
        elif color_mode == 'pastel':
            # Pastel colors
            hue = random.random()
            return self.__hsv_to_rgb(hue, 0.5, 1.0)
        else:  # 'white'
            return [255, 255, 255]

    def __render(self):
        """Render the bouncing logo."""
        frame = np.zeros([self.__height, self.__width, 3], np.uint8)

        # Draw the logo as a filled rectangle
        x_start = int(self.__x)
        y_start = int(self.__y)
        x_end = min(x_start + self.__logo_width, self.__width)
        y_end = min(y_start + self.__logo_height, self.__height)

        # Fill the rectangle
        show_border = Config.get('dvd_bounce.show_border', True)

        if show_border:
            # Draw filled logo with border
            for y in range(y_start, y_end):
                for x in range(x_start, x_end):
                    # Border pixels
                    if (y == y_start or y == y_end - 1 or
                        x == x_start or x == x_end - 1):
                        frame[y, x] = self.__color
                    # Interior pixels (slightly dimmer)
                    else:
                        frame[y, x] = [c // 2 for c in self.__color]
        else:
            # Draw solid filled rectangle
            frame[y_start:y_end, x_start:x_end] = self.__color

        # Optional: Draw "DVD" text if logo is big enough
        show_text = Config.get('dvd_bounce.show_text', False)
        if show_text and self.__logo_width >= 5 and self.__logo_height >= 3:
            self.__draw_dvd_text(frame, x_start, y_start)

        self.__led_frame_player.play_frame(frame)

    def __draw_dvd_text(self, frame, x_offset, y_offset):
        """Draw simple 'DVD' text pattern in the logo."""
        # Simple 3x5 pixel patterns for D, V, D
        # Only draw if there's enough space
        if self.__logo_width < 5 or self.__logo_height < 3:
            return

        # Center the text vertically
        text_y = y_offset + (self.__logo_height - 3) // 2
        text_x = x_offset + 1

        # Simple patterns (3 pixels wide each, with gaps)
        # D pattern
        if text_x + 2 < x_offset + self.__logo_width and text_y + 2 < y_offset + self.__logo_height:
            frame[text_y:text_y+3, text_x] = [255, 255, 255]  # Left edge
            frame[text_y, text_x+1] = [255, 255, 255]         # Top
            frame[text_y+2, text_x+1] = [255, 255, 255]       # Bottom

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
        return Config.get('dvd_bounce.tick_sleep', 0.03)

    @classmethod
    def get_id(cls) -> str:
        return 'dvd_bounce'

    @classmethod
    def get_name(cls) -> str:
        return 'DVD Bounce'

    @classmethod
    def get_description(cls) -> str:
        return 'Classic DVD logo bounce with color changes'
