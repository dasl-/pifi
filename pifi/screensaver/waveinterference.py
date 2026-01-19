import math
import numpy as np
import time
import random

from pifi.config import Config
from pifi.logger import Logger
from pifi.led.ledframeplayer import LedFramePlayer
from pifi.screensaver.screensaver import Screensaver


class WaveInterference(Screensaver):
    """
    Wave interference pattern screensaver.

    Simulates multiple point sources emitting circular waves that
    interfere with each other, creating mesmerizing ripple patterns.
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

        # Wave sources: each is [x, y, phase_offset, vx, vy]
        self.__sources = []
        self.__time = 0.0

        # Precompute coordinate grids for efficiency
        x = np.arange(self.__width)
        y = np.arange(self.__height)
        self.__grid_x, self.__grid_y = np.meshgrid(x, y)

        # Color palette
        self.__hue_offset = 0.0

    def play(self):
        self.__logger.info("Starting Wave Interference screensaver")
        self.__reset()

        max_ticks = Config.get('wave_interference.max_ticks', 2000)
        tick = 0

        while tick < max_ticks:
            self.__tick()
            time.sleep(self.__get_tick_sleep())
            tick += 1

        self.__logger.info("Wave Interference screensaver ended")

    def __reset(self):
        num_sources = Config.get('wave_interference.num_sources', 4)

        self.__sources = []
        for _ in range(num_sources):
            self.__add_random_source()

        self.__time = 0.0
        self.__hue_offset = random.random()

    def __add_random_source(self):
        """Add a new wave source at a random position with random velocity."""
        x = random.uniform(0, self.__width)
        y = random.uniform(0, self.__height)
        phase_offset = random.uniform(0, 2 * math.pi)

        # Slow drift velocity
        drift_speed = Config.get('wave_interference.drift_speed', 0.3)
        angle = random.uniform(0, 2 * math.pi)
        vx = math.cos(angle) * drift_speed
        vy = math.sin(angle) * drift_speed

        self.__sources.append([x, y, phase_offset, vx, vy])

    def __tick(self):
        self.__update_sources()
        self.__render()

        time_speed = Config.get('wave_interference.time_speed', 0.15)
        self.__time += time_speed

    def __update_sources(self):
        """Update source positions (drifting)."""
        for source in self.__sources:
            # Update position
            source[0] += source[3]  # x += vx
            source[1] += source[4]  # y += vy

            # Bounce off edges
            if source[0] < 0 or source[0] >= self.__width:
                source[3] *= -1
                source[0] = max(0, min(self.__width - 1, source[0]))
            if source[1] < 0 or source[1] >= self.__height:
                source[4] *= -1
                source[1] = max(0, min(self.__height - 1, source[1]))

    def __render(self):
        wave_frequency = Config.get('wave_interference.wave_frequency', 0.5)
        color_mode = Config.get('wave_interference.color_mode', 'rainbow')

        # Calculate combined wave amplitude at each pixel
        amplitude = np.zeros((self.__height, self.__width), dtype=np.float64)

        for source in self.__sources:
            sx, sy, phase_offset, _, _ = source

            # Distance from this source to each pixel
            dx = self.__grid_x - sx
            dy = self.__grid_y - sy
            distance = np.sqrt(dx * dx + dy * dy)

            # Wave contribution: sin(distance * frequency - time + phase)
            wave = np.sin(distance * wave_frequency - self.__time + phase_offset)
            amplitude += wave

        # Normalize amplitude to [-1, 1] range
        num_sources = len(self.__sources)
        amplitude = amplitude / num_sources

        # Convert to frame
        frame = np.zeros([self.__height, self.__width, 3], np.uint8)

        if color_mode == 'rainbow':
            # Map amplitude to hue, with time-based offset for color cycling
            hue = (amplitude + 1) / 2  # Map [-1, 1] to [0, 1]
            hue = (hue * 0.7 + self.__hue_offset + self.__time * 0.02) % 1.0

            # Saturation and value based on amplitude
            sat = np.ones_like(amplitude) * 0.9
            val = (amplitude + 1) / 2 * 0.8 + 0.2  # Map to [0.2, 1.0]

            frame = self.__hsv_array_to_rgb(hue, sat, val)

        elif color_mode == 'monochrome':
            # Simple grayscale based on amplitude
            brightness = ((amplitude + 1) / 2 * 255).astype(np.uint8)
            frame[:, :, 0] = brightness
            frame[:, :, 1] = brightness
            frame[:, :, 2] = brightness

        elif color_mode == 'plasma':
            # Two-color plasma effect
            t = (amplitude + 1) / 2
            # Interpolate between two colors
            r = (np.sin(t * math.pi + self.__time * 0.1) + 1) / 2
            g = (np.sin(t * math.pi + self.__time * 0.1 + 2.094) + 1) / 2
            b = (np.sin(t * math.pi + self.__time * 0.1 + 4.189) + 1) / 2

            frame[:, :, 0] = (r * 255).astype(np.uint8)
            frame[:, :, 1] = (g * 255).astype(np.uint8)
            frame[:, :, 2] = (b * 255).astype(np.uint8)

        else:  # 'classic' - blue ripples on dark background
            # Bright peaks, dark troughs
            brightness = np.maximum(0, amplitude)  # Only positive values
            frame[:, :, 0] = (brightness * 50).astype(np.uint8)   # R
            frame[:, :, 1] = (brightness * 150).astype(np.uint8)  # G
            frame[:, :, 2] = (brightness * 255).astype(np.uint8)  # B

        self.__led_frame_player.play_frame(frame)

    def __hsv_array_to_rgb(self, h, s, v):
        """Convert HSV arrays to RGB frame."""
        frame = np.zeros((self.__height, self.__width, 3), dtype=np.uint8)

        # Vectorized HSV to RGB conversion
        h = np.asarray(h)
        s = np.asarray(s)
        v = np.asarray(v)

        i = (h * 6.0).astype(int)
        f = (h * 6.0) - i
        p = v * (1.0 - s)
        q = v * (1.0 - s * f)
        t = v * (1.0 - s * (1.0 - f))
        i = i % 6

        # Build RGB based on hue sector
        conditions = [i == 0, i == 1, i == 2, i == 3, i == 4, i == 5]

        r = np.select(conditions, [v, q, p, p, t, v])
        g = np.select(conditions, [t, v, v, q, p, p])
        b = np.select(conditions, [p, p, t, v, v, q])

        frame[:, :, 0] = (r * 255).astype(np.uint8)
        frame[:, :, 1] = (g * 255).astype(np.uint8)
        frame[:, :, 2] = (b * 255).astype(np.uint8)

        return frame

    def __get_tick_sleep(self):
        return Config.get('wave_interference.tick_sleep', 0.03)

    @classmethod
    def get_id(cls) -> str:
        return 'wave_interference'

    @classmethod
    def get_name(cls) -> str:
        return 'Wave Interference'

    @classmethod
    def get_description(cls) -> str:
        return 'Ripple interference patterns'
