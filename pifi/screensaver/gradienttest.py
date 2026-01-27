"""
Gradient Test screensaver.

Minimal CPU load screensaver for debugging display flicker.
Tests whether flicker is caused by colors/PWM rather than CPU load.
"""

import numpy as np
import time

from pifi.config import Config
from pifi.led.ledframeplayer import LedFramePlayer
from pifi.logger import Logger
from pifi.screensaver.screensaver import Screensaver


class GradientTest(Screensaver):
    """Static gradient for flicker debugging."""

    def __init__(self, led_frame_player=None):
        super().__init__(led_frame_player)
        self.__logger = Logger().set_namespace(self.__class__.__name__)

        if led_frame_player is None:
            led_frame_player = LedFramePlayer()
        self.__led_frame_player = led_frame_player

        self.__width = Config.get('leds.display_width')
        self.__height = Config.get('leds.display_height')

        # Config
        self.__mode = Config.get('gradienttest.mode', 'pastel_sky')
        self.__tick_sleep = Config.get('gradienttest.tick_sleep', 0.1)
        self.__max_ticks = Config.get('gradienttest.max_ticks', 3000)

        # Pre-generate the static frame ONCE
        self.__frame = self.__generate_frame()

    def __generate_frame(self):
        """Generate a static test frame based on mode."""
        frame = np.zeros((self.__height, self.__width, 3), dtype=np.uint8)

        if self.__mode == 'pastel_sky':
            # Cloudscape-like pastel gradient
            for y in range(self.__height):
                t = y / max(1, self.__height - 1)
                # Interpolate from soft blue to pale blue
                r = int(120 + t * 90)   # 120 -> 210
                g = int(180 + t * 55)   # 180 -> 235
                b = 255                  # constant
                frame[y, :] = [r, g, b]

        elif self.__mode == 'white':
            # Full white - maximum power draw
            frame[:, :] = [255, 255, 255]

        elif self.__mode == 'half_white':
            # 50% white - tests mid-brightness
            frame[:, :] = [128, 128, 128]

        elif self.__mode == 'dim_white':
            # Very dim white
            frame[:, :] = [32, 32, 32]

        elif self.__mode == 'red':
            # Full red only
            frame[:, :] = [255, 0, 0]

        elif self.__mode == 'green':
            # Full green only
            frame[:, :] = [0, 255, 0]

        elif self.__mode == 'blue':
            # Full blue only
            frame[:, :] = [0, 0, 255]

        elif self.__mode == 'horizontal_gradient':
            # Left to right gradient
            for x in range(self.__width):
                t = x / max(1, self.__width - 1)
                v = int(t * 255)
                frame[:, x] = [v, v, v]

        elif self.__mode == 'vertical_gradient':
            # Top to bottom gradient
            for y in range(self.__height):
                t = y / max(1, self.__height - 1)
                v = int(t * 255)
                frame[y, :] = [v, v, v]

        elif self.__mode == 'checkerboard':
            # Alternating pixels - stress test for PWM
            for y in range(self.__height):
                for x in range(self.__width):
                    if (x + y) % 2 == 0:
                        frame[y, x] = [255, 255, 255]
                    else:
                        frame[y, x] = [0, 0, 0]

        elif self.__mode == 'stripes':
            # Horizontal stripes - tests row addressing
            for y in range(self.__height):
                if y % 2 == 0:
                    frame[y, :] = [255, 255, 255]
                else:
                    frame[y, :] = [0, 0, 0]

        elif self.__mode == 'color_bars':
            # Vertical color bars
            bar_width = self.__width // 8
            colors = [
                [255, 255, 255],  # white
                [255, 255, 0],    # yellow
                [0, 255, 255],    # cyan
                [0, 255, 0],      # green
                [255, 0, 255],    # magenta
                [255, 0, 0],      # red
                [0, 0, 255],      # blue
                [0, 0, 0],        # black
            ]
            for i, color in enumerate(colors):
                x_start = i * bar_width
                x_end = min((i + 1) * bar_width, self.__width)
                frame[:, x_start:x_end] = color

        else:
            # Default: pastel sky
            return self.__generate_frame_mode('pastel_sky')

        return frame

    def __generate_frame_mode(self, mode):
        """Helper to generate frame for a specific mode."""
        old_mode = self.__mode
        self.__mode = mode
        frame = self.__generate_frame()
        self.__mode = old_mode
        return frame

    def play(self):
        """Run the screensaver - just display the same frame repeatedly."""
        self.__logger.info(f"Starting GradientTest screensaver (mode={self.__mode})")

        # Display the pre-generated static frame
        # This loop does almost NO CPU work - just sleep and display
        for tick in range(self.__max_ticks):
            self.__led_frame_player.play_frame(self.__frame)
            time.sleep(self.__tick_sleep)

        self.__logger.info("GradientTest screensaver ended")

    @classmethod
    def get_id(cls) -> str:
        return 'gradient_test'

    @classmethod
    def get_name(cls) -> str:
        return 'Gradient Test'

    @classmethod
    def get_description(cls) -> str:
        return 'Static gradient for flicker debugging'
