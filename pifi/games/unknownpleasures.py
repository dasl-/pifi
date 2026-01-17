"""
Unknown Pleasures screensaver.

Inspired by the iconic Joy Division album cover - stacked
waveforms that pulse and evolve, evoking pulsar radio signals.
"""

import math
import numpy as np
import time
import random

from pifi.config import Config
from pifi.led.ledframeplayer import LedFramePlayer
from pifi.logger import Logger


class UnknownPleasures:
    """Stacked waveform visualization inspired by pulsar data."""

    def __init__(self, led_frame_player=None):
        self.__logger = Logger().set_namespace(self.__class__.__name__)

        if led_frame_player is None:
            led_frame_player = LedFramePlayer()
        self.__led_frame_player = led_frame_player

        self.__width = Config.get('leds.display_width')
        self.__height = Config.get('leds.display_height')

        # Config
        self.__num_lines = Config.get('unknownpleasures.num_lines', 0)  # 0 = auto
        self.__wave_speed = Config.get('unknownpleasures.wave_speed', 0.05)
        self.__noise_scale = Config.get('unknownpleasures.noise_scale', 0.15)
        self.__amplitude = Config.get('unknownpleasures.amplitude', 0.4)
        self.__line_brightness = Config.get('unknownpleasures.line_brightness', 1.0)
        self.__fill_below = Config.get('unknownpleasures.fill_below', True)
        self.__color_mode = Config.get('unknownpleasures.color_mode', 'white')  # white, blue, rainbow
        self.__tick_sleep = Config.get('unknownpleasures.tick_sleep', 0.05)
        self.__max_ticks = Config.get('unknownpleasures.max_ticks', 10000)

        # Auto-calculate line count
        if self.__num_lines <= 0:
            self.__num_lines = max(6, self.__height // 2)

        # Perlin noise setup
        self.__perm = self.__generate_permutation()

        self.__time = 0.0

    def __generate_permutation(self):
        """Generate permutation table for Perlin noise."""
        p = np.arange(256, dtype=np.int32)
        np.random.shuffle(p)
        return np.concatenate([p, p])

    def __noise1d(self, x):
        """1D Perlin-like noise."""
        xi = int(np.floor(x)) & 255
        xf = x - np.floor(x)

        # Fade curve
        u = xf * xf * xf * (xf * (xf * 6 - 15) + 10)

        # Hash and gradient
        a = self.__perm[xi]
        b = self.__perm[xi + 1]

        # Gradient values
        ga = (a & 1) * 2 - 1  # -1 or 1
        gb = (b & 1) * 2 - 1

        # Interpolate
        return ga * xf * (1 - u) + gb * (xf - 1) * u

    def __get_wave_value(self, x, line_index, time_offset):
        """Get wave height at position x for a given line."""
        # Multiple octaves of noise for interesting patterns
        value = 0
        freq = 1.0
        amp = 1.0

        for _ in range(3):
            noise_x = x * self.__noise_scale * freq + time_offset + line_index * 10
            value += self.__noise1d(noise_x) * amp
            freq *= 2
            amp *= 0.5

        # Add some sine wave components for smoother peaks
        value += math.sin(x * 0.3 + time_offset * 2 + line_index) * 0.3
        value += math.sin(x * 0.7 - time_offset + line_index * 0.5) * 0.2

        return value * self.__amplitude

    def __hsv_to_rgb(self, h, s, v):
        """Convert HSV to RGB (0-255)."""
        if s == 0:
            val = int(v * 255)
            return (val, val, val)

        h = h % 1.0
        i = int(h * 6)
        f = h * 6 - i
        p = v * (1 - s)
        q = v * (1 - s * f)
        t = v * (1 - s * (1 - f))

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

        return (int(r * 255), int(g * 255), int(b * 255))

    def __get_line_color(self, line_index, brightness=1.0):
        """Get color for a line based on color mode."""
        b = self.__line_brightness * brightness

        if self.__color_mode == 'white':
            val = int(255 * b)
            return (val, val, val)
        elif self.__color_mode == 'blue':
            # Cool blue like some variations of the cover
            return (int(80 * b), int(120 * b), int(255 * b))
        elif self.__color_mode == 'rainbow':
            hue = line_index / self.__num_lines
            return self.__hsv_to_rgb(hue, 0.7, b)
        else:  # default white
            val = int(255 * b)
            return (val, val, val)

    def __render(self):
        """Render the waveforms."""
        frame = np.zeros((self.__height, self.__width, 3), dtype=np.uint8)

        # Calculate vertical spacing
        # Lines are drawn from back (top) to front (bottom) for proper occlusion
        line_spacing = self.__height / (self.__num_lines + 1)

        # Store wave heights for each line (for occlusion)
        wave_heights = []

        for line_idx in range(self.__num_lines):
            # Base Y position (center of this line's row)
            base_y = (line_idx + 1) * line_spacing

            # Calculate wave heights for this line
            heights = []
            for x in range(self.__width):
                wave = self.__get_wave_value(x, line_idx, self.__time)
                # Wave displaces upward (negative Y)
                y = base_y - wave * line_spacing * 1.5
                heights.append(y)

            wave_heights.append((line_idx, base_y, heights))

        # Draw from back to front (top to bottom) for occlusion
        for line_idx, base_y, heights in wave_heights:
            color = self.__get_line_color(line_idx)
            fill_color = tuple(c // 4 for c in color)  # Darker fill

            for x in range(self.__width):
                wave_y = heights[x]
                pixel_y = int(wave_y)

                if self.__fill_below:
                    # Fill from wave line down to base (creates solid mountain effect)
                    fill_end = int(base_y)
                    for y in range(max(0, pixel_y), min(self.__height, fill_end + 1)):
                        if y == pixel_y:
                            # Bright line at the top edge
                            frame[y, x] = color
                        else:
                            # Black fill below (occludes lines behind)
                            frame[y, x] = (0, 0, 0)
                else:
                    # Just draw the line
                    if 0 <= pixel_y < self.__height:
                        frame[pixel_y, x] = color

            # Draw the wave line on top
            for x in range(self.__width):
                pixel_y = int(heights[x])
                if 0 <= pixel_y < self.__height:
                    frame[pixel_y, x] = color

        self.__led_frame_player.play_frame(frame)

    def play(self):
        """Run the screensaver."""
        self.__logger.info("Starting Unknown Pleasures screensaver")

        # Re-seed for variety
        self.__perm = self.__generate_permutation()
        self.__time = 0.0

        for tick in range(self.__max_ticks):
            self.__time += self.__wave_speed
            self.__render()
            time.sleep(self.__tick_sleep)

        self.__logger.info("Unknown Pleasures screensaver ended")
