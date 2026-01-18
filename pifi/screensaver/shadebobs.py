import math
import numpy as np
import time
import random

from pifi.config import Config
from pifi.logger import Logger
from pifi.led.ledframeplayer import LedFramePlayer
from pifi.screensaver.screensaver import Screensaver


class Shadebobs(Screensaver):
    """
    Classic demoscene shadebobs effect.

    Glowing circles move in Lissajous patterns, using additive blending
    with a fading trail to create beautiful flowing color patterns.
    """

    def __init__(self, led_frame_player=None):
        self.__logger = Logger().set_namespace(self.__class__.__name__)

        if led_frame_player is None:
            self.__led_frame_player = LedFramePlayer()
        else:
            self.__led_frame_player = led_frame_player

        self.__width = Config.get_or_throw('leds.display_width')
        self.__height = Config.get_or_throw('leds.display_height')

        # Frame buffer as float for smooth accumulation
        self.__buffer = None

        # Bob state
        self.__bobs = []
        self.__time = 0

    def play(self):
        self.__logger.info("Starting Shadebobs screensaver")
        self.__reset()

        max_ticks = Config.get('shadebobs.max_ticks', 2000)
        tick = 0

        while tick < max_ticks:
            self.__tick()
            time.sleep(self.__get_tick_sleep())
            tick += 1

        self.__logger.info("Shadebobs screensaver ended")

    def __reset(self):
        # Float buffer for smooth color accumulation
        self.__buffer = np.zeros((self.__height, self.__width, 3), dtype=np.float32)
        self.__time = 0

        # Create bobs with different Lissajous parameters
        num_bobs = Config.get('shadebobs.num_bobs', 5)
        self.__bobs = []

        for i in range(num_bobs):
            bob = {
                # Lissajous parameters - use ratios that create interesting patterns
                'freq_x': random.uniform(1, 4),
                'freq_y': random.uniform(1, 4),
                'phase_x': random.uniform(0, 2 * math.pi),
                'phase_y': random.uniform(0, 2 * math.pi),
                # Speed multiplier
                'speed': random.uniform(0.8, 1.5),
                # Color - spread hues evenly with some randomness
                'hue': (i / num_bobs + random.uniform(-0.1, 0.1)) % 1.0,
                'hue_speed': random.uniform(0.001, 0.005),
                # Glow radius
                'radius': random.uniform(1.5, 3.0),
                # Brightness
                'intensity': random.uniform(0.3, 0.5),
            }
            self.__bobs.append(bob)

        self.__logger.info(f"Created {num_bobs} shadebobs")

    def __tick(self):
        # Fade the buffer
        fade = Config.get('shadebobs.fade', 0.92)
        self.__buffer *= fade

        # Update and draw each bob
        for bob in self.__bobs:
            # Update hue
            bob['hue'] = (bob['hue'] + bob['hue_speed']) % 1.0

            # Calculate position using Lissajous curves
            t = self.__time * bob['speed'] * 0.05
            x = math.sin(bob['freq_x'] * t + bob['phase_x'])
            y = math.sin(bob['freq_y'] * t + bob['phase_y'])

            # Map from [-1, 1] to screen coordinates
            screen_x = (x + 1) / 2 * (self.__width - 1)
            screen_y = (y + 1) / 2 * (self.__height - 1)

            # Draw the bob with additive blending
            self.__draw_bob(screen_x, screen_y, bob)

        # Render to display
        self.__render()
        self.__time += 1

    def __draw_bob(self, cx, cy, bob):
        """Draw a glowing bob at the given position with additive blending."""
        radius = bob['radius']
        intensity = bob['intensity']
        color = self.__hsv_to_rgb(bob['hue'], 0.9, 1.0)

        # Calculate bounding box
        x_min = max(0, int(cx - radius - 1))
        x_max = min(self.__width, int(cx + radius + 2))
        y_min = max(0, int(cy - radius - 1))
        y_max = min(self.__height, int(cy + radius + 2))

        for y in range(y_min, y_max):
            for x in range(x_min, x_max):
                # Distance from center
                dx = x - cx
                dy = y - cy
                dist = math.sqrt(dx * dx + dy * dy)

                if dist < radius:
                    # Gaussian-ish falloff
                    falloff = 1.0 - (dist / radius)
                    falloff = falloff * falloff  # Squared for softer edges
                    brightness = intensity * falloff

                    # Additive blend
                    self.__buffer[y, x, 0] += color[0] * brightness
                    self.__buffer[y, x, 1] += color[1] * brightness
                    self.__buffer[y, x, 2] += color[2] * brightness

    def __render(self):
        """Convert float buffer to uint8 and display."""
        # Clamp to 255 and convert
        frame = np.clip(self.__buffer, 0, 255).astype(np.uint8)
        self.__led_frame_player.play_frame(frame)

    def __hsv_to_rgb(self, h, s, v):
        """Convert HSV to RGB, returns values in 0-255 range."""
        if s == 0.0:
            val = int(v * 255)
            return [val, val, val]

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

        return [r * 255, g * 255, b * 255]

    def __get_tick_sleep(self):
        return Config.get('shadebobs.tick_sleep', 0.03)

    @classmethod
    def get_id(cls) -> str:
        return 'shadebobs'

    @classmethod
    def get_name(cls) -> str:
        return 'Shadebobs'

    @classmethod
    def get_description(cls) -> str:
        return 'Glowing Lissajous trails'
