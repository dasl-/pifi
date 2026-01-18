"""
Unknown Pleasures screensaver.

Inspired by the iconic Joy Division album cover - stacked
waveforms that pulse and evolve, evoking pulsar radio signals.
"""

import numpy as np
import time

from pifi.config import Config
from pifi.led.ledframeplayer import LedFramePlayer
from pifi.logger import Logger
from pifi.screensaver.screensaver import Screensaver


class UnknownPleasures(Screensaver):
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
        self.__color_mode = Config.get('unknownpleasures.color_mode', 'white')
        self.__tick_sleep = Config.get('unknownpleasures.tick_sleep', 0.05)
        self.__max_ticks = Config.get('unknownpleasures.max_ticks', 10000)

        # Auto-calculate line count
        if self.__num_lines <= 0:
            self.__num_lines = max(6, self.__height // 2)

        # Pre-compute arrays for vectorized operations
        self.__x_coords = np.arange(self.__width, dtype=np.float32)
        self.__x_indices = np.arange(self.__width, dtype=np.int32)
        self.__y_grid = np.arange(self.__height, dtype=np.int32)[:, np.newaxis]

        # Perlin noise setup
        self.__perm = None

        # Pre-compute line colors
        self.__line_colors = None

        self.__time = 0.0

    def __init_colors(self):
        """Pre-compute colors for all lines."""
        self.__line_colors = np.zeros((self.__num_lines, 3), dtype=np.uint8)
        b = self.__line_brightness

        for i in range(self.__num_lines):
            if self.__color_mode == 'white':
                val = int(255 * b)
                self.__line_colors[i] = (val, val, val)
            elif self.__color_mode == 'blue':
                self.__line_colors[i] = (int(80 * b), int(120 * b), int(255 * b))
            elif self.__color_mode == 'rainbow':
                hue = i / self.__num_lines
                self.__line_colors[i] = self.__hsv_to_rgb(hue, 0.7, b)
            else:
                val = int(255 * b)
                self.__line_colors[i] = (val, val, val)

    def __generate_permutation(self):
        """Generate permutation table for Perlin noise."""
        p = np.arange(256, dtype=np.int32)
        np.random.shuffle(p)
        return np.concatenate([p, p])

    def __noise1d_vectorized(self, x_array):
        """Vectorized 1D Perlin-like noise."""
        xi = np.floor(x_array).astype(np.int32) & 255
        xf = x_array - np.floor(x_array)

        # Fade curve
        u = xf * xf * xf * (xf * (xf * 6 - 15) + 10)

        # Hash and gradient
        a = self.__perm[xi]
        b = self.__perm[xi + 1]

        # Gradient values (-1 or 1)
        ga = (a & 1) * 2 - 1
        gb = (b & 1) * 2 - 1

        # Interpolate
        return ga * xf * (1 - u) + gb * (xf - 1) * u

    def __get_wave_values(self, line_index, time_offset):
        """Get wave heights for all x positions (vectorized)."""
        x = self.__x_coords

        # Multiple octaves of noise
        value = np.zeros(self.__width, dtype=np.float32)
        freq = 1.0
        amp = 1.0

        for _ in range(3):
            noise_x = x * self.__noise_scale * freq + time_offset + line_index * 10
            value += self.__noise1d_vectorized(noise_x) * amp
            freq *= 2
            amp *= 0.5

        # Add sine wave components
        value += np.sin(x * 0.3 + time_offset * 2 + line_index) * 0.3
        value += np.sin(x * 0.7 - time_offset + line_index * 0.5) * 0.2

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

    def __render(self):
        """Render the waveforms."""
        frame = np.zeros((self.__height, self.__width, 3), dtype=np.uint8)

        line_spacing = self.__height / (self.__num_lines + 1)

        # Pre-compute all wave heights as a 2D array (num_lines x width)
        all_heights = np.zeros((self.__num_lines, self.__width), dtype=np.float32)
        all_base_y = np.zeros(self.__num_lines, dtype=np.float32)

        for line_idx in range(self.__num_lines):
            base_y = (line_idx + 1) * line_spacing
            wave_values = self.__get_wave_values(line_idx, self.__time)
            all_heights[line_idx] = base_y - wave_values * line_spacing * 1.5
            all_base_y[line_idx] = base_y

        # Draw from back to front (top to bottom) for occlusion
        for line_idx in range(self.__num_lines):
            pixel_heights = np.clip(all_heights[line_idx].astype(np.int32), 0, self.__height - 1)
            fill_end = min(int(all_base_y[line_idx]), self.__height - 1)
            color = self.__line_colors[line_idx]

            if self.__fill_below:
                # Vectorized: create mask where y > pixel_height and y <= fill_end
                mask = (self.__y_grid > pixel_heights) & (self.__y_grid <= fill_end)
                frame[mask] = 0  # Black fill

            # Draw the wave line using advanced indexing
            frame[pixel_heights, self.__x_indices] = color

        self.__led_frame_player.play_frame(frame)

    def play(self):
        """Run the screensaver."""
        self.__logger.info("Starting Unknown Pleasures screensaver")

        # Initialize
        self.__perm = self.__generate_permutation()
        self.__init_colors()
        self.__time = 0.0

        for tick in range(self.__max_ticks):
            self.__time += self.__wave_speed
            self.__render()
            time.sleep(self.__tick_sleep)

        self.__logger.info("Unknown Pleasures screensaver ended")

    @classmethod
    def get_id(cls) -> str:
        return 'unknownpleasures'

    @classmethod
    def get_name(cls) -> str:
        return 'Unknown Pleasures'

    @classmethod
    def get_description(cls) -> str:
        return 'Joy Division pulsar waves'
