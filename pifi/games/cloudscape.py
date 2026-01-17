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


class Cloudscape:
    """Layered clouds drifting across a gradient sky."""

    def __init__(self, led_frame_player=None):
        self.__logger = Logger().set_namespace(self.__class__.__name__)

        if led_frame_player is None:
            led_frame_player = LedFramePlayer()
        self.__led_frame_player = led_frame_player

        self.__width = Config.get('leds.display_width')
        self.__height = Config.get('leds.display_height')

        # Config
        self.__num_layers = Config.get('cloudscape.num_layers', 3)
        self.__drift_speed = Config.get('cloudscape.drift_speed', 0.3)
        self.__sky_mode = Config.get('cloudscape.sky_mode', 'sunset')  # sunset, day, night, dawn
        self.__cloud_density = Config.get('cloudscape.cloud_density', 0.5)
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
        if mode == 'sunset':
            return [
                (25, 25, 60),      # Deep blue (top)
                (80, 50, 80),      # Purple
                (180, 80, 50),     # Orange
                (255, 150, 80),    # Light orange (horizon)
            ]
        elif mode == 'dawn':
            return [
                (20, 30, 60),      # Dark blue
                (60, 50, 80),      # Dusty purple
                (150, 100, 120),   # Pink
                (255, 180, 140),   # Soft peach
            ]
        elif mode == 'day':
            return [
                (30, 80, 180),     # Deep sky blue
                (80, 150, 220),    # Sky blue
                (150, 200, 240),   # Light blue
                (200, 230, 255),   # Horizon haze
            ]
        elif mode == 'night':
            return [
                (5, 5, 20),        # Near black
                (10, 15, 40),      # Dark blue
                (20, 30, 60),      # Night blue
                (30, 40, 70),      # Horizon glow
            ]
        else:  # Default sunset
            return self.__get_sky_colors('sunset')

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

    def __get_cloud_color(self, layer, density):
        """Get cloud color based on layer depth and sky mode."""
        # Deeper layers are darker/more distant
        layer_brightness = 0.6 + 0.4 * (layer / max(1, self.__num_layers - 1))

        if self.__sky_mode == 'sunset':
            # Warm tinted clouds
            base = np.array([255, 220, 200], dtype=np.float32)
        elif self.__sky_mode == 'dawn':
            # Pink/peach clouds
            base = np.array([255, 200, 180], dtype=np.float32)
        elif self.__sky_mode == 'day':
            # White fluffy clouds
            base = np.array([255, 255, 255], dtype=np.float32)
        elif self.__sky_mode == 'night':
            # Dark grey clouds
            base = np.array([60, 70, 90], dtype=np.float32)
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
            layer_speed = 0.3 + layer_depth * 0.7  # Back = slow, front = fast
            layer_scale = 0.08 + layer_depth * 0.04  # Back = larger clouds
            layer_alpha = 0.4 + layer_depth * 0.4  # Back = more transparent

            # Calculate cloud noise with drift
            drift_x = self.__time * self.__drift_speed * layer_speed
            noise_x = (self.__x_grid + drift_x) * layer_scale
            noise_y = self.__y_grid * layer_scale * 1.5 + layer * 100  # Offset each layer

            # Generate cloud density using fractal noise
            cloud_noise = self.__fbm(noise_x, noise_y, octaves=4)

            # Map noise to cloud density (threshold and smooth)
            threshold = 0.5 - self.__cloud_density * 0.4
            cloud_mask = (cloud_noise - threshold) / (1 - threshold)
            cloud_mask = np.clip(cloud_mask, 0, 1)

            # Soften cloud edges
            cloud_mask = cloud_mask * cloud_mask * (3 - 2 * cloud_mask)

            # Add vertical falloff (more clouds near horizon for depth)
            y_factor = self.__y_grid / self.__height
            # Clouds more prominent in middle/lower portion
            vertical_weight = np.sin(y_factor * np.pi * 0.8) ** 0.5
            cloud_mask = cloud_mask * vertical_weight

            # Get cloud color for this layer
            cloud_color = self.__get_cloud_color(layer, cloud_mask)

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
