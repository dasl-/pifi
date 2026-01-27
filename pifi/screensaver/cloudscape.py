"""
Cloudscape screensaver.

Dreamy drifting clouds over a gradient sky.
Multiple cloud layers create depth with parallax motion.

Optimized for low-power devices with buffer reuse and caching.
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
        self.__sky_mode = Config.get('cloudscape.sky_mode', 'pastel')
        self.__cloud_density = Config.get('cloudscape.cloud_density', 0.7)
        self.__cloud_scale = Config.get('cloudscape.cloud_scale', 0.04)
        self.__sky_shift_speed = Config.get('cloudscape.sky_shift_speed', 0.001)
        self.__tick_sleep = Config.get('cloudscape.tick_sleep', 0.05)
        self.__max_ticks = Config.get('cloudscape.max_ticks', 10000)

        # Pre-compute coordinate grids (reused every frame)
        self.__x_grid, self.__y_grid = np.meshgrid(
            np.arange(self.__width, dtype=np.float32),
            np.arange(self.__height, dtype=np.float32)
        )

        # Pre-allocate all buffers to avoid per-frame allocations
        self.__frame = np.zeros((self.__height, self.__width, 3), dtype=np.float32)
        self.__sky_gradient = np.zeros((self.__height, self.__width, 3), dtype=np.float32)
        self.__cloud_buffer = np.zeros((self.__height, self.__width), dtype=np.float32)
        self.__alpha_buffer = np.zeros((self.__height, self.__width, 3), dtype=np.float32)
        self.__output_frame = np.zeros((self.__height, self.__width, 3), dtype=np.uint8)

        # Noise buffers (reused in fbm)
        self.__noise_buffer = np.zeros((self.__height, self.__width), dtype=np.float32)
        self.__noise_x = np.zeros((self.__height, self.__width), dtype=np.float32)
        self.__noise_y = np.zeros((self.__height, self.__width), dtype=np.float32)

        # Perlin noise permutation table
        self.__perm = None

        # Pre-compute y-factor for vertical cloud distribution
        self.__y_factor = self.__y_grid / self.__height
        self.__vertical_weight = 0.6 + 0.4 * np.sin(self.__y_factor * np.pi * 0.9)

        # Sky gradient cache (updated less frequently)
        self.__sky_cache_tick = -1
        self.__sky_update_interval = 30  # Update sky every N frames

        self.__time = 0.0

    def __generate_permutation(self):
        """Generate permutation table for Perlin noise."""
        p = np.arange(256, dtype=np.int32)
        np.random.shuffle(p)
        return np.concatenate([p, p])

    def __noise2d_fast(self, x, y, out):
        """Fast 2D Perlin noise with output buffer reuse."""
        # Find unit square
        xi = np.floor(x).astype(np.int32) & 255
        yi = np.floor(y).astype(np.int32) & 255

        # Relative position in square
        xf = x - np.floor(x)
        yf = y - np.floor(y)

        # Fade curves (in-place where possible)
        u = xf * xf * xf * (xf * (xf * 6 - 15) + 10)
        v = yf * yf * yf * (yf * (yf * 6 - 15) + 10)

        # Hash corners
        perm = self.__perm
        aa = perm[perm[xi] + yi]
        ab = perm[perm[xi] + yi + 1]
        ba = perm[perm[xi + 1] + yi]
        bb = perm[perm[xi + 1] + yi + 1]

        # Simplified gradient computation (avoiding np.where calls)
        def grad_dot(h, px, py):
            # Use bottom 2 bits to pick gradient direction
            g = h & 3
            # Compute all variants and select
            signs_x = np.where(g & 1, -1.0, 1.0)
            signs_y = np.where(g & 2, -1.0, 1.0)
            return signs_x * px + signs_y * py

        # Gradient dot products
        g_aa = grad_dot(aa, xf, yf)
        g_ba = grad_dot(ba, xf - 1, yf)
        g_ab = grad_dot(ab, xf, yf - 1)
        g_bb = grad_dot(bb, xf - 1, yf - 1)

        # Bilinear interpolation
        x1 = g_aa + u * (g_ba - g_aa)
        x2 = g_ab + u * (g_bb - g_ab)
        np.add(x1, v * (x2 - x1), out=out)

    def __fbm_fast(self, x, y, out, octaves=3):
        """Fast Fractal Brownian Motion with buffer reuse."""
        out.fill(0)
        amplitude = 1.0
        frequency = 1.0
        max_value = 0.0

        for _ in range(octaves):
            # Reuse noise buffer
            np.multiply(x, frequency, out=self.__noise_x)
            np.multiply(y, frequency, out=self.__noise_y)
            self.__noise2d_fast(self.__noise_x, self.__noise_y, self.__noise_buffer)

            # Accumulate (in-place)
            out += self.__noise_buffer * amplitude

            max_value += amplitude
            amplitude *= 0.5
            frequency *= 2.0

        out /= max_value

    def __get_sky_colors(self, mode):
        """Get gradient colors for sky mode."""
        colors = {
            'pastel': [(120, 180, 255), (150, 200, 255), (180, 220, 255), (210, 235, 255)],
            'day': [(80, 140, 220), (120, 180, 240), (160, 210, 250), (200, 230, 255)],
            'sunset': [(25, 25, 60), (80, 50, 80), (180, 80, 50), (255, 150, 80)],
            'dawn': [(100, 140, 180), (140, 160, 190), (180, 180, 200), (220, 200, 210)],
            'night': [(15, 20, 40), (25, 35, 60), (40, 55, 80), (55, 70, 95)],
        }
        return colors.get(mode, colors['pastel'])

    def __compute_sky_gradient(self):
        """Compute sky gradient (vectorized, no Python loops)."""
        colors = np.array(self.__get_sky_colors(self.__sky_mode), dtype=np.float32)
        num_colors = len(colors)

        # Normalized y positions (0 = top, 1 = bottom)
        t = self.__y_grid[:, 0:1] / max(1, self.__height - 1)

        # Find color segment indices
        segment = t * (num_colors - 1)
        idx = np.clip(segment.astype(np.int32), 0, num_colors - 2)
        frac = segment - idx

        # Smooth interpolation
        frac = frac * frac * (3 - 2 * frac)

        # Gather colors and interpolate
        c1 = colors[idx.flatten()]
        c2 = colors[(idx + 1).flatten()]

        # Interpolate RGB
        gradient_flat = c1 + (c2 - c1) * frac.flatten()[:, np.newaxis]

        # Reshape and broadcast to full width
        self.__sky_gradient[:] = gradient_flat.reshape(self.__height, 1, 3)

    def __get_cloud_color(self, layer):
        """Get cloud color based on layer depth and sky mode."""
        layer_brightness = 0.85 + 0.15 * (layer / max(1, self.__num_layers - 1))

        cloud_colors = {
            'pastel': (255, 255, 255),
            'day': (255, 255, 255),
            'sunset': (255, 230, 210),
            'dawn': (240, 230, 245),
            'night': (100, 110, 130),
        }
        base = np.array(cloud_colors.get(self.__sky_mode, (255, 255, 255)), dtype=np.float32)
        return base * layer_brightness

    def __render(self, tick):
        """Render the cloudscape with optimized buffer reuse."""
        # Update sky gradient less frequently (it changes slowly)
        if tick - self.__sky_cache_tick >= self.__sky_update_interval:
            self.__compute_sky_gradient()
            self.__sky_cache_tick = tick

        # Start with cached sky gradient
        np.copyto(self.__frame, self.__sky_gradient)

        # Render each cloud layer (back to front)
        threshold_base = 0.3 - self.__cloud_density * 0.35
        threshold_range = 0.6 - threshold_base

        for layer in range(self.__num_layers):
            # Layer properties
            layer_depth = layer / max(1, self.__num_layers - 1)
            layer_speed = 0.4 + layer_depth * 0.6
            layer_scale = self.__cloud_scale * (0.8 + layer_depth * 0.4)
            layer_alpha = 0.7 + layer_depth * 0.3

            # Calculate noise coordinates (reuse grid)
            drift_x = self.__time * self.__drift_speed * layer_speed
            noise_x = (self.__x_grid + drift_x) * layer_scale
            noise_y = self.__y_grid * layer_scale * 1.2 + layer * 100

            # Generate cloud density (reuse buffer)
            self.__fbm_fast(noise_x, noise_y, self.__cloud_buffer, octaves=2)

            # Map noise to cloud density (in-place operations)
            cloud_mask = self.__cloud_buffer
            np.subtract(cloud_mask, threshold_base, out=cloud_mask)
            np.divide(cloud_mask, threshold_range, out=cloud_mask)
            np.clip(cloud_mask, 0, 1, out=cloud_mask)

            # Sharper edges for cartoon look
            np.multiply(cloud_mask, cloud_mask, out=cloud_mask)

            # Apply vertical weight
            np.multiply(cloud_mask, self.__vertical_weight, out=cloud_mask)

            # Get cloud color
            cloud_color = self.__get_cloud_color(layer)

            # Blend clouds onto frame (minimize temp arrays)
            alpha = cloud_mask * layer_alpha
            for c in range(3):
                self.__frame[:, :, c] *= (1 - alpha)
                self.__frame[:, :, c] += cloud_color[c] * alpha

        # Convert to uint8 output
        np.clip(self.__frame, 0, 255, out=self.__frame)
        np.copyto(self.__output_frame, self.__frame.astype(np.uint8))
        self.__led_frame_player.play_frame(self.__output_frame)

    def play(self):
        """Run the screensaver."""
        self.__logger.info("Starting Cloudscape screensaver")

        # Initialize
        self.__perm = self.__generate_permutation()
        self.__time = 0.0
        self.__sky_cache_tick = -1

        for tick in range(self.__max_ticks):
            self.__time += 1
            self.__render(tick)
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
