import numpy as np
import random
import math

from pifi.config import Config
from pifi.screensaver.screensaver import Screensaver


class ColorField(Screensaver):
    """
    Color field / Rothko-inspired screensaver.

    Slow, meditative rectangles of color that breathe and bleed
    into each other at their edges. Pure luminous slowness — the LED
    glow makes this feel like a Turrell light installation.
    """

    def __init__(self, led_frame_player=None):
        super().__init__(led_frame_player)

        self.__width = Config.get_or_throw('leds.display_width')
        self.__height = Config.get_or_throw('leds.display_height')
        self.__time = 0.0

    def _setup(self):
        self.__time = 0.0

        # 2-4 horizontal bands with distinct hues
        self.__num_bands = random.choice([2, 3, 3, 4])

        # Each band: base hue, target position (as fraction of height)
        self.__bands = []
        hue = random.random()
        for i in range(self.__num_bands):
            band = {
                'hue': hue,
                'hue_drift': random.uniform(-0.0008, 0.0008),
                'sat': random.uniform(0.5, 0.85),
                'val': random.uniform(0.4, 0.8),
                'val_drift': random.uniform(-0.0003, 0.0003),
            }
            self.__bands.append(band)
            # Next band: analogous or complementary shift
            hue = (hue + random.choice([
                random.uniform(0.05, 0.15),   # analogous
                random.uniform(0.3, 0.5),      # complementary-ish
            ])) % 1.0

        # Band boundaries — evenly spaced with slight variation
        spacing = 1.0 / self.__num_bands
        self.__boundaries = []
        for i in range(1, self.__num_bands):
            pos = i * spacing + random.uniform(-0.05, 0.05)
            self.__boundaries.append(pos)

        # Boundary drift speeds
        self.__boundary_drifts = [random.uniform(-0.0005, 0.0005) for _ in self.__boundaries]

        # Pre-compute y coordinates normalized to 0-1
        self.__y_norm = np.linspace(0, 1, self.__height, dtype=np.float64)

        # Breathing phase offsets per band
        self.__breath_phases = [random.uniform(0, 2 * math.pi) for _ in range(self.__num_bands)]

    def _tick(self):
        self.__time += 0.02
        t = self.__time

        # Update band colors (very slow drift)
        for band in self.__bands:
            band['hue'] = (band['hue'] + band['hue_drift']) % 1.0
            band['val'] = np.clip(band['val'] + band['val_drift'], 0.3, 0.9)
            # Reverse drift at boundaries
            if band['val'] <= 0.3 or band['val'] >= 0.9:
                band['val_drift'] *= -1

        # Update boundary positions (very slow movement)
        for i in range(len(self.__boundaries)):
            self.__boundaries[i] += self.__boundary_drifts[i]
            # Keep boundaries ordered and in range
            lo = 0.15 if i == 0 else self.__boundaries[i - 1] + 0.1
            hi = 0.85 if i == len(self.__boundaries) - 1 else self.__boundaries[i + 1] - 0.1 if i + 1 < len(self.__boundaries) else 0.85
            if self.__boundaries[i] < lo or self.__boundaries[i] > hi:
                self.__boundary_drifts[i] *= -1
                self.__boundaries[i] = np.clip(self.__boundaries[i], lo, hi)

        # Build per-pixel color
        y = self.__y_norm
        hue = np.zeros(self.__height, dtype=np.float64)
        sat = np.zeros(self.__height, dtype=np.float64)
        val = np.zeros(self.__height, dtype=np.float64)

        # For each pixel row, blend between adjacent bands
        boundaries = [0.0] + list(self.__boundaries) + [1.0]

        for row in range(self.__height):
            yp = y[row]

            # Find which two bands this pixel is between
            band_idx = 0
            for i, b in enumerate(self.__boundaries):
                if yp > b:
                    band_idx = i + 1

            # Blend zone width — how much the bands bleed into each other
            bleed = 0.08 + 0.03 * math.sin(t * 0.5)

            if band_idx > 0:
                boundary = self.__boundaries[band_idx - 1]
                dist_to_boundary = abs(yp - boundary)
                if dist_to_boundary < bleed:
                    # In the bleed zone — blend between bands
                    blend = 0.5 + 0.5 * math.cos(dist_to_boundary / bleed * math.pi)
                    if yp < boundary:
                        a, b_band = self.__bands[band_idx - 1], self.__bands[band_idx]
                    else:
                        a, b_band = self.__bands[band_idx], self.__bands[band_idx - 1]

                    hue[row] = _lerp_hue(a['hue'], b_band['hue'], blend)
                    sat[row] = a['sat'] * (1 - blend) + b_band['sat'] * blend
                    val[row] = a['val'] * (1 - blend) + b_band['val'] * blend
                    continue

            band = self.__bands[band_idx]

            # Gentle breathing
            breath = 1.0 + 0.06 * math.sin(t * 0.4 + self.__breath_phases[band_idx])

            hue[row] = band['hue']
            sat[row] = band['sat']
            val[row] = band['val'] * breath

        # Broadcast to full width (uniform horizontally with very subtle noise)
        hue_2d = np.tile(hue[:, np.newaxis], (1, self.__width))
        sat_2d = np.tile(sat[:, np.newaxis], (1, self.__width))
        val_2d = np.tile(val[:, np.newaxis], (1, self.__width))

        # Very subtle luminance noise for texture
        noise = np.random.uniform(-0.02, 0.02, (self.__height, self.__width))
        val_2d = np.clip(val_2d + noise, 0, 1)

        frame = _hsv_to_rgb_vec(hue_2d, sat_2d, val_2d)
        self._led_frame_player.play_frame(frame)

    @classmethod
    def get_id(cls) -> str:
        return 'colorfield'

    @classmethod
    def get_name(cls) -> str:
        return 'Color Field'

    @classmethod
    def get_description(cls) -> str:
        return 'Rothko-inspired luminous color bands'


def _lerp_hue(a, b, t):
    """Interpolate between two hues via the shortest path."""
    diff = b - a
    if abs(diff) > 0.5:
        if diff > 0:
            a += 1.0
        else:
            b += 1.0
    return (a + (b - a) * t) % 1.0


def _hsv_to_rgb_vec(h, s, v):
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
