"""
Cloudscape screensaver.

Dreamy drifting clouds over a gradient sky.
Multiple cloud layers create depth with parallax motion.
"""

import numpy as np
import time

from pifi.config import Config
from pifi.led.ledframeplayer import LedFramePlayer
from pifi.logger import Logger
from pifi.screensaver.screensaver import Screensaver


class Cloudscape(Screensaver):
    """Layered clouds drifting across a gradient sky."""

    def __init__(self, led_frame_player=None):
        super().__init__(led_frame_player)
        self.__logger = Logger().set_namespace(self.__class__.__name__)

        if led_frame_player is None:
            led_frame_player = LedFramePlayer()
        self.__led_frame_player = led_frame_player

        self.__width = Config.get('leds.display_width')
        self.__height = Config.get('leds.display_height')

        # Config
        self.__num_layers = Config.get('cloudscape.num_layers', 3)
        self.__drift_speed = Config.get('cloudscape.drift_speed', 0.2)
        self.__sky_mode = Config.get('cloudscape.sky_mode', 'pastel')  # pastel, day, night, dawn, sunset
        self.__cloud_density = Config.get('cloudscape.cloud_density', 0.7)
        self.__cloud_scale = Config.get('cloudscape.cloud_scale', 0.04)  # Smaller = bigger clouds
        self.__sky_shift_speed = Config.get('cloudscape.sky_shift_speed', 0.001)
        self.__tick_sleep = Config.get('cloudscape.tick_sleep', 0.05)
        self.__max_ticks = Config.get('cloudscape.max_ticks', 10000)

        # Pre-compute coordinate grids
        self.__x_grid, self.__y_grid = np.meshgrid(
            np.arange(self.__width, dtype=np.float32),
            np.arange(self.__height, dtype=np.float32)
        )

        # Perlin noise permutation table
        self.__perm = None

        # Sky gradient (pre-computed each mode change)
        self.__sky_gradient = None

        self.__time = 0.0

    def __generate_permutation(self):
        """Generate permutation table for Perlin noise."""
        p = np.arange(256, dtype=np.int32)
        np.random.shuffle(p)
        return np.concatenate([p, p])

    def __noise2d_vectorized(self, x, y):
        """Vectorized 2D Perlin noise."""
        # Find unit square
        xi = np.floor(x).astype(np.int32) & 255
        yi = np.floor(y).astype(np.int32) & 255

        # Relative position in square
        xf = x - np.floor(x)
        yf = y - np.floor(y)

        # Fade curves
        u = xf * xf * xf * (xf * (xf * 6 - 15) + 10)
        v = yf * yf * yf * (yf * (yf * 6 - 15) + 10)

        # Hash corners
        aa = self.__perm[self.__perm[xi] + yi]
        ab = self.__perm[self.__perm[xi] + yi + 1]
        ba = self.__perm[self.__perm[xi + 1] + yi]
        bb = self.__perm[self.__perm[xi + 1] + yi + 1]

        # Simplified gradients (just use hash bits)
        def grad(h, x, y):
            # Use bottom 2 bits to pick gradient direction
            g = h & 3
            result = np.zeros_like(x)
            result = np.where(g == 0, x + y, result)
            result = np.where(g == 1, -x + y, result)
            result = np.where(g == 2, x - y, result)
            result = np.where(g == 3, -x - y, result)
            return result

        # Gradient dot products and interpolation
        x1 = grad(aa, xf, yf) * (1 - u) + grad(ba, xf - 1, yf) * u
        x2 = grad(ab, xf, yf - 1) * (1 - u) + grad(bb, xf - 1, yf - 1) * u

        return x1 * (1 - v) + x2 * v

    def __fbm(self, x, y, octaves=4):
        """Fractal Brownian Motion - layered noise for clouds."""
        value = np.zeros_like(x)
        amplitude = 1.0
        frequency = 1.0
        max_value = 0.0

        for _ in range(octaves):
            value += self.__noise2d_vectorized(x * frequency, y * frequency) * amplitude
            max_value += amplitude
            amplitude *= 0.5
            frequency *= 2.0

        return value / max_value

    def __get_sky_colors(self, mode):
        """Get gradient colors for sky mode."""
        if mode == 'pastel':
            # Soft, relaxing cartoon sky
            return [
                (120, 180, 255),   # Soft sky blue (top)
                (150, 200, 255),   # Light blue
                (180, 220, 255),   # Pale blue
                (210, 235, 255),   # Almost white blue (horizon)
            ]
        elif mode == 'day':
            return [
                (80, 140, 220),    # Sky blue (top)
                (120, 180, 240),   # Light sky blue
                (160, 210, 250),   # Pale blue
                (200, 230, 255),   # Horizon haze
            ]
        elif mode == 'sunset':
            return [
                (25, 25, 60),      # Deep blue (top)
                (80, 50, 80),      # Purple
                (180, 80, 50),     # Orange
                (255, 150, 80),    # Light orange (horizon)
            ]
        elif mode == 'dawn':
            return [
                (100, 140, 180),   # Soft blue
                (140, 160, 190),   # Dusty blue
                (180, 180, 200),   # Lavender
                (220, 200, 210),   # Soft pink
            ]
        elif mode == 'night':
            return [
                (15, 20, 40),      # Dark blue
                (25, 35, 60),      # Night blue
                (40, 55, 80),      # Lighter night
                (55, 70, 95),      # Horizon glow
            ]
        else:  # Default pastel
            return self.__get_sky_colors('pastel')

    def __compute_sky_gradient(self, time_offset=0):
        """Compute sky gradient with optional color shifting."""
        colors = self.__get_sky_colors(self.__sky_mode)

        # Create gradient based on y position
        gradient = np.zeros((self.__height, self.__width, 3), dtype=np.float32)

        for y in range(self.__height):
            # Normalized position (0 = top, 1 = bottom)
            t = y / max(1, self.__height - 1)

            # Find which color segment we're in
            segment = t * (len(colors) - 1)
            idx = int(segment)
            frac = segment - idx

            if idx >= len(colors) - 1:
                idx = len(colors) - 2
                frac = 1.0

            # Interpolate between colors
            c1 = colors[idx]
            c2 = colors[idx + 1]

            # Smooth interpolation
            frac = frac * frac * (3 - 2 * frac)

            r = c1[0] + (c2[0] - c1[0]) * frac
            g = c1[1] + (c2[1] - c1[1]) * frac
            b = c1[2] + (c2[2] - c1[2]) * frac

            # Slight horizontal variation for more organic feel
            variation = np.sin(np.arange(self.__width) * 0.2 + time_offset) * 5
            gradient[y, :, 0] = np.clip(r + variation, 0, 255)
            gradient[y, :, 1] = np.clip(g + variation * 0.5, 0, 255)
            gradient[y, :, 2] = np.clip(b + variation * 0.3, 0, 255)

        return gradient

    def __get_cloud_color(self, layer):
        """Get cloud color based on layer depth and sky mode."""
        # Deeper layers are slightly darker for depth
        layer_brightness = 0.85 + 0.15 * (layer / max(1, self.__num_layers - 1))

        if self.__sky_mode == 'pastel':
            # Bright white fluffy cartoon clouds
            base = np.array([255, 255, 255], dtype=np.float32)
        elif self.__sky_mode == 'day':
            # Pure white clouds
            base = np.array([255, 255, 255], dtype=np.float32)
        elif self.__sky_mode == 'sunset':
            # Warm tinted clouds
            base = np.array([255, 230, 210], dtype=np.float32)
        elif self.__sky_mode == 'dawn':
            # Soft lavender clouds
            base = np.array([240, 230, 245], dtype=np.float32)
        elif self.__sky_mode == 'night':
            # Silvery grey clouds
            base = np.array([100, 110, 130], dtype=np.float32)
        else:
            base = np.array([255, 255, 255], dtype=np.float32)

        return base * layer_brightness

    def __render(self):
        """Render the cloudscape."""
        # Start with sky gradient
        frame = self.__compute_sky_gradient(self.__time * self.__sky_shift_speed)

        # Render each cloud layer (back to front)
        for layer in range(self.__num_layers):
            # Layer properties - back layers move slower (parallax)
            layer_depth = layer / max(1, self.__num_layers - 1)  # 0 = back, 1 = front
            layer_speed = 0.4 + layer_depth * 0.6  # Back = slow, front = fast
            # Use cloud_scale config - smaller values = bigger clouds
            layer_scale = self.__cloud_scale * (0.8 + layer_depth * 0.4)
            layer_alpha = 0.7 + layer_depth * 0.3  # More opaque for cartoon look

            # Calculate cloud noise with drift
            drift_x = self.__time * self.__drift_speed * layer_speed
            noise_x = (self.__x_grid + drift_x) * layer_scale
            noise_y = self.__y_grid * layer_scale * 1.2 + layer * 100  # Offset each layer

            # Generate cloud density using fractal noise (fewer octaves = puffier)
            cloud_noise = self.__fbm(noise_x, noise_y, octaves=3)

            # Map noise to cloud density (lower threshold = more clouds)
            threshold = 0.3 - self.__cloud_density * 0.35
            cloud_mask = (cloud_noise - threshold) / (0.6 - threshold)
            cloud_mask = np.clip(cloud_mask, 0, 1)

            # Slightly sharper edges for cartoon look (steeper curve)
            cloud_mask = cloud_mask * cloud_mask

            # Spread clouds across more of the sky
            y_factor = self.__y_grid / self.__height
            # Clouds visible across most of the sky, slightly less at very top
            vertical_weight = 0.6 + 0.4 * np.sin(y_factor * np.pi * 0.9)
            cloud_mask = cloud_mask * vertical_weight

            # Get cloud color for this layer
            cloud_color = self.__get_cloud_color(layer)

            # Blend clouds onto frame
            alpha = cloud_mask[:, :, np.newaxis] * layer_alpha
            frame = frame * (1 - alpha) + cloud_color * alpha

        # Convert to uint8
        frame = np.clip(frame, 0, 255).astype(np.uint8)
        self.__led_frame_player.play_frame(frame)

    def play(self):
        """Run the screensaver."""
        self.__logger.info("Starting Cloudscape screensaver")

        # Initialize
        self.__perm = self.__generate_permutation()
        self.__time = 0.0

        for tick in range(self.__max_ticks):
            self.__time += 1
            self.__render()
            time.sleep(self.__tick_sleep)

        self.__logger.info("Cloudscape screensaver ended")

    @classmethod
    def get_id(cls) -> str:
        return 'cloudscape'

    @classmethod
    def get_name(cls) -> str:
        return 'Cloudscape'

    @classmethod
    def get_description(cls) -> str:
        return 'Drifting clouds over gradient sky'
