import numpy as np
import random
import math

from pifi.config import Config
from pifi.screensaver.screensaver import Screensaver


class PixelSort(Screensaver):
    """
    Pixel sorting — glitch art aesthetic.

    Generates an animated source pattern, then sorts runs of pixels
    by brightness within threshold bands. Creates streaky, waterfall-like
    distortion effects. The sort direction, threshold, and source pattern
    evolve over time.
    """

    def __init__(self, led_frame_player=None):
        super().__init__(led_frame_player)

        self.__width = Config.get_or_throw('leds.display_width')
        self.__height = Config.get_or_throw('leds.display_height')
        self.__time = 0.0

    def _setup(self):
        self.__time = 0.0
        self.__hue_base = random.random()
        self.__speed = random.uniform(0.01, 0.02)

        # Sort mode: which axis to sort along
        self.__sort_axis = random.choice(['horizontal', 'vertical'])

        # Pre-compute coordinate grids
        y = np.linspace(0, 1, self.__height, dtype=np.float64)
        x = np.linspace(0, 1, self.__width, dtype=np.float64)
        self.__gx, self.__gy = np.meshgrid(x, y)

        # Random source pattern parameters
        self.__pattern_freqs = [random.uniform(2, 6) for _ in range(4)]
        self.__pattern_phases = [random.uniform(0, 10) for _ in range(4)]

    def _tick(self):
        self.__time += self.__speed
        t = self.__time

        # Generate source pattern — flowing gradient with some structure
        gx, gy = self.__gx, self.__gy
        f = self.__pattern_freqs
        p = self.__pattern_phases

        pattern = (
            np.sin(gx * f[0] * 6 + t * 2.0 + p[0]) *
            np.cos(gy * f[1] * 4 + t * 1.5 + p[1]) +
            np.sin((gx + gy) * f[2] * 3 + t * 1.8 + p[2]) * 0.5 +
            np.sin(gy * f[3] * 8 + t * 0.7 + p[3]) * 0.3
        )
        # Normalize to 0-1
        pattern = (pattern - pattern.min()) / max(pattern.max() - pattern.min(), 0.001)

        # Color the source — hue from pattern, full saturation
        hue = (self.__hue_base + pattern * 0.4 + t * 0.03) % 1.0
        sat = 0.7 + pattern * 0.2
        val = 0.15 + pattern * 0.75

        frame = _hsv_to_rgb_vec(hue, sat, val)

        # Animated sort threshold — controls which pixels get sorted
        # Lower threshold = more sorting, higher = less
        lo = 0.15 + 0.15 * math.sin(t * 1.2)
        hi = 0.6 + 0.25 * math.sin(t * 0.8 + 1.5)

        # Sort pixel runs along the chosen axis
        brightness = pattern
        frame = self.__sort_frame(frame, brightness, lo, hi)

        self._led_frame_player.play_frame(frame)

    def __sort_frame(self, frame, brightness, lo, hi):
        """Sort runs of pixels where brightness falls within [lo, hi]."""
        result = frame.copy()

        if self.__sort_axis == 'horizontal':
            for y in range(self.__height):
                result[y] = self.__sort_row(frame[y], brightness[y], lo, hi)
        else:
            # Sort columns by transposing, sorting rows, transposing back
            for x in range(self.__width):
                result[:, x] = self.__sort_row(frame[:, x], brightness[:, x], lo, hi)

        return result

    def __sort_row(self, pixels, bright, lo, hi):
        """Sort contiguous runs of pixels where brightness is in [lo, hi]."""
        n = len(bright)
        result = pixels.copy()
        mask = (bright >= lo) & (bright <= hi)

        # Find contiguous runs of True in mask
        i = 0
        while i < n:
            if not mask[i]:
                i += 1
                continue
            # Start of a run
            j = i
            while j < n and mask[j]:
                j += 1
            # Sort this run by brightness (ascending = streaks flow dark→light)
            run_indices = np.argsort(bright[i:j])
            result[i:j] = pixels[i:j][run_indices]
            i = j

        return result

    @classmethod
    def get_id(cls) -> str:
        return 'pixelsort'

    @classmethod
    def get_name(cls) -> str:
        return 'Pixel Sort'

    @classmethod
    def get_description(cls) -> str:
        return 'Glitch art pixel sorting'


def _hsv_to_rgb_vec(h, s, v):
    """Vectorized HSV to RGB. Returns [H, W, 3] uint8."""
    i = (h * 6.0).astype(int) % 6
    f = h * 6.0 - np.floor(h * 6.0)
    p = v * (1.0 - s)
    q = v * (1.0 - s * f)
    t = v * (1.0 - s * (1.0 - f))

    r = np.zeros_like(h)
    g = np.zeros_like(h)
    bl = np.zeros_like(h)

    m0 = i == 0; r[m0] = v[m0]; g[m0] = t[m0]; bl[m0] = p[m0]
    m1 = i == 1; r[m1] = q[m1]; g[m1] = v[m1]; bl[m1] = p[m1]
    m2 = i == 2; r[m2] = p[m2]; g[m2] = v[m2]; bl[m2] = t[m2]
    m3 = i == 3; r[m3] = p[m3]; g[m3] = q[m3]; bl[m3] = v[m3]
    m4 = i == 4; r[m4] = t[m4]; g[m4] = p[m4]; bl[m4] = v[m4]
    m5 = i == 5; r[m5] = v[m5]; g[m5] = p[m5]; bl[m5] = q[m5]

    return np.stack([r * 255, g * 255, bl * 255], axis=-1).astype(np.uint8)
