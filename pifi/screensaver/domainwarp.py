import numpy as np
import random

from pifi.config import Config
from pifi.screensaver.screensaver import Screensaver


class DomainWarp(Screensaver):
    """
    Domain warping — layered noise distortion.

    Uses one noise field to warp the coordinates of another, creating
    flowing organic structures that look like smoke, marble, or alien
    terrain. Continuously evolves by advancing a time parameter.
    """

    def __init__(self, led_frame_player=None):
        super().__init__(led_frame_player)

        self.__width = Config.get_or_throw('leds.display_width')
        self.__height = Config.get_or_throw('leds.display_height')
        self.__time = 0.0

    def _setup(self):
        self.__time = 0.0
        self.__hue_base = random.random()

        # Pre-compute coordinate grids (normalized 0-1)
        y = np.linspace(0, 1, self.__height, dtype=np.float64)
        x = np.linspace(0, 1, self.__width, dtype=np.float64)
        self.__gx, self.__gy = np.meshgrid(x, y)

        # Random parameters for variety
        self.__warp_strength = random.uniform(0.3, 0.6)
        self.__speed = random.uniform(0.008, 0.015)
        self.__num_octaves = random.choice([3, 4, 5])

        # Random phase offsets for each noise layer
        self.__phases = [random.uniform(0, 100) for _ in range(8)]

    def _tick(self):
        self.__time += self.__speed

        t = self.__time
        gx, gy = self.__gx, self.__gy
        s = self.__warp_strength
        p = self.__phases

        # Layer 1: base warp
        wx = gx + s * self.__fbm(gx + p[0], gy + p[1], t)
        wy = gy + s * self.__fbm(gx + p[2], gy + p[3], t + 3.7)

        # Layer 2: warp the warp
        wx2 = gx + s * self.__fbm(wx + p[4], wy + p[5], t + 7.3)
        wy2 = gy + s * self.__fbm(wx + p[6], wy + p[7], t + 11.1)

        # Final pattern value
        pattern = self.__fbm(wx2, wy2, t + 5.0)

        # Map to color using the pattern value and warp displacement
        displacement = np.sqrt((wx2 - gx) ** 2 + (wy2 - gy) ** 2)
        displacement /= max(displacement.max(), 0.001)

        hue = (self.__hue_base + pattern * 0.3 + displacement * 0.2) % 1.0
        sat = 0.5 + displacement * 0.4
        val = np.clip(0.2 + (pattern + 1) * 0.3 + displacement * 0.4, 0, 1)

        frame = _hsv_to_rgb_vec(hue, sat, val)
        self._led_frame_player.play_frame(frame)

    def __fbm(self, x, y, t):
        """Fractal Brownian motion — sum of sine-based noise at multiple octaves."""
        result = np.zeros_like(x)
        amp = 1.0
        freq = 2.0

        for i in range(self.__num_octaves):
            # Use sines at different angles/frequencies for pseudo-noise
            result += amp * (
                np.sin(x * freq * 3.17 + t * 1.3 + i * 1.7) *
                np.cos(y * freq * 2.83 + t * 0.9 + i * 2.3) +
                np.sin((x + y) * freq * 1.93 + t * 1.1 + i * 3.1) * 0.5
            )
            amp *= 0.5
            freq *= 2.0

        return result / 2.5  # Normalize roughly to -1..1

    @classmethod
    def get_id(cls) -> str:
        return 'domainwarp'

    @classmethod
    def get_name(cls) -> str:
        return 'Domain Warp'

    @classmethod
    def get_description(cls) -> str:
        return 'Flowing organic noise distortion'


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
