import math
import numpy as np
import time
import random

from pifi.config import Config
from pifi.logger import Logger
from pifi.led.ledframeplayer import LedFramePlayer
from pifi.screensaver.screensaver import Screensaver


class Spirograph(Screensaver):
    """
    Spirograph screensaver.

    Draws hypnotic geometric patterns using the mathematics of a spirograph
    (epitrochoid and hypotrochoid curves). Multiple rotating arms create
    intricate, ever-changing designs.
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

        # Drawing state
        self.__time = 0.0
        self.__trail = []  # List of (x, y, hue) points
        self.__params = {}

    def play(self):
        self.__logger.info("Starting Spirograph screensaver")
        self.__reset()

        max_ticks = Config.get('spirograph.max_ticks', 2000)
        tick = 0

        while tick < max_ticks:
            self.__tick()
            time.sleep(self.__get_tick_sleep())
            tick += 1

        self.__logger.info("Spirograph screensaver ended")

    def __reset(self):
        self.__time = 0.0
        self.__trail = []

        # Randomize spirograph parameters for variety
        # R = radius of fixed circle, r = radius of rolling circle, d = drawing point offset
        self.__params = {
            'R': random.uniform(0.3, 0.5),  # Outer radius (fraction of display)
            'r': random.uniform(0.08, 0.25),  # Inner radius
            'd': random.uniform(0.05, 0.2),   # Pen offset
            'speed1': random.uniform(0.02, 0.05),  # Primary rotation speed
            'speed2': random.uniform(0.03, 0.08),  # Secondary rotation speed
            'hue_speed': random.uniform(0.001, 0.003),  # Color cycling speed
        }

        # Ensure interesting ratio (non-repeating patterns)
        ratio = self.__params['R'] / self.__params['r']
        if abs(ratio - round(ratio)) < 0.1:
            self.__params['r'] *= 1.1

        self.__logger.info(f"Spirograph params: R={self.__params['R']:.3f}, r={self.__params['r']:.3f}")

    def __tick(self):
        time_speed = Config.get('spirograph.time_speed', 1.0)
        self.__time += time_speed

        # Calculate current point using epitrochoid formula
        R = self.__params['R']
        r = self.__params['r']
        d = self.__params['d']
        t = self.__time * self.__params['speed1']

        # Epitrochoid: point on a circle rolling around outside of fixed circle
        # x = (R + r) * cos(t) - d * cos((R + r) / r * t)
        # y = (R + r) * sin(t) - d * sin((R + r) / r * t)
        ratio = (R + r) / r

        x = (R + r) * math.cos(t) - d * math.cos(ratio * t)
        y = (R + r) * math.sin(t) - d * math.sin(ratio * t)

        # Add secondary rotation for more complexity
        t2 = self.__time * self.__params['speed2']
        x += 0.05 * math.cos(t2 * 3.7)
        y += 0.05 * math.sin(t2 * 2.3)

        # Convert to screen coordinates
        cx = self.__width / 2
        cy = self.__height / 2
        scale = min(self.__width, self.__height) * 0.8

        screen_x = cx + x * scale
        screen_y = cy + y * scale

        # Calculate hue based on time
        hue = (self.__time * self.__params['hue_speed']) % 1.0

        # Add to trail
        max_trail = Config.get('spirograph.trail_length', 500)
        self.__trail.append((screen_x, screen_y, hue))
        if len(self.__trail) > max_trail:
            self.__trail.pop(0)

        self.__render()

    def __render(self):
        frame = np.zeros([self.__height, self.__width, 3], np.uint8)
        fade_trail = Config.get('spirograph.fade_trail', True)

        for i, (x, y, hue) in enumerate(self.__trail):
            ix = int(x) % self.__width
            iy = int(y) % self.__height

            if 0 <= ix < self.__width and 0 <= iy < self.__height:
                # Fade older points if enabled
                if fade_trail:
                    brightness = (i + 1) / len(self.__trail)
                else:
                    brightness = 1.0

                rgb = self.__hsv_to_rgb(hue, 0.9, brightness)

                # Additive blending for overlapping points
                frame[iy, ix] = np.minimum(255, frame[iy, ix] + np.array(rgb, dtype=np.uint8))

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
        return Config.get('spirograph.tick_sleep', 0.02)

    @classmethod
    def get_id(cls) -> str:
        return 'spirograph'

    @classmethod
    def get_name(cls) -> str:
        return 'Spirograph'

    @classmethod
    def get_description(cls) -> str:
        return 'Rotating geometric patterns'
