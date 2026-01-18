"""
Perlin Worms screensaver.

Organic worms that slither through a Perlin noise field,
leaving glowing trails that fade over time.
"""

import math
import numpy as np
import time

from pifi.config import Config
from pifi.led.ledframeplayer import LedFramePlayer
from pifi.logger import Logger


class PerlinWorms:
    """Worms following Perlin noise gradients with glowing trails."""

    def __init__(self, led_frame_player=None):
        self.__logger = Logger().set_namespace(self.__class__.__name__)

        if led_frame_player is None:
            led_frame_player = LedFramePlayer()
        self.__led_frame_player = led_frame_player

        self.__width = Config.get('leds.display_width')
        self.__height = Config.get('leds.display_height')

        # Config
        self.__num_worms = Config.get('perlinworms.num_worms', 8)
        self.__worm_length = Config.get('perlinworms.worm_length', 12)
        self.__speed = Config.get('perlinworms.speed', 0.8)
        self.__noise_scale = Config.get('perlinworms.noise_scale', 0.1)
        self.__time_speed = Config.get('perlinworms.time_speed', 0.02)
        self.__fade = Config.get('perlinworms.fade', 0.92)
        self.__glow_size = Config.get('perlinworms.glow_size', 1.5)
        self.__tick_sleep = Config.get('perlinworms.tick_sleep', 0.03)
        self.__max_ticks = Config.get('perlinworms.max_ticks', 10000)

        # Initialize Perlin noise
        self.__perm = self.__generate_permutation()

        # Worm state: each worm has a list of (x, y) positions (head first)
        self.__worms = []
        self.__worm_hues = []

        # Canvas buffer (float for smooth accumulation)
        self.__canvas = np.zeros((self.__height, self.__width, 3), dtype=np.float32)

        self.__time = 0.0

    def __generate_permutation(self):
        """Generate permutation table for Perlin noise."""
        p = np.arange(256, dtype=np.int32)
        np.random.shuffle(p)
        return np.concatenate([p, p])

    def __noise2d(self, x, y):
        """2D Perlin noise."""
        # Find unit square
        xi = int(np.floor(x)) & 255
        yi = int(np.floor(y)) & 255

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

        # Gradient dot products
        def grad(h, x, y):
            h = h & 3
            if h == 0:
                return x + y
            elif h == 1:
                return -x + y
            elif h == 2:
                return x - y
            else:
                return -x - y

        x1 = self.__lerp(grad(aa, xf, yf), grad(ba, xf - 1, yf), u)
        x2 = self.__lerp(grad(ab, xf, yf - 1), grad(bb, xf - 1, yf - 1), u)

        return self.__lerp(x1, x2, v)

    def __lerp(self, a, b, t):
        return a + t * (b - a)

    def __init_worms(self):
        """Initialize worms at random positions."""
        self.__worms = []
        self.__worm_hues = []

        for i in range(self.__num_worms):
            # Start at random position
            x = np.random.uniform(0, self.__width)
            y = np.random.uniform(0, self.__height)

            # Initialize with single position (will grow)
            self.__worms.append([(x, y)])

            # Assign a hue to each worm
            self.__worm_hues.append(i / self.__num_worms)

        self.__canvas.fill(0)
        self.__time = 0.0

    def __get_flow_angle(self, x, y):
        """Get flow direction from noise field."""
        # Use time-varying noise for dynamic field
        noise_val = self.__noise2d(
            x * self.__noise_scale + self.__time * 0.5,
            y * self.__noise_scale + self.__time * 0.3
        )
        return noise_val * math.pi * 2

    def __update_worms(self):
        """Update worm positions following the flow field."""
        for i, worm in enumerate(self.__worms):
            # Get head position
            hx, hy = worm[0]

            # Get flow direction
            angle = self.__get_flow_angle(hx, hy)

            # Move head
            new_x = hx + math.cos(angle) * self.__speed
            new_y = hy + math.sin(angle) * self.__speed

            # Wrap around edges
            new_x = new_x % self.__width
            new_y = new_y % self.__height

            # Add new head position
            worm.insert(0, (new_x, new_y))

            # Trim tail if too long
            while len(worm) > self.__worm_length:
                worm.pop()

    def __hsv_to_rgb(self, h, s, v):
        """Convert HSV to RGB."""
        if s == 0:
            return v, v, v

        h = h % 1.0
        i = int(h * 6)
        f = h * 6 - i
        p = v * (1 - s)
        q = v * (1 - s * f)
        t = v * (1 - s * (1 - f))

        if i == 0:
            return v, t, p
        elif i == 1:
            return q, v, p
        elif i == 2:
            return p, v, t
        elif i == 3:
            return p, q, v
        elif i == 4:
            return t, p, v
        else:
            return v, p, q

    def __draw_worms(self):
        """Draw worms with glowing effect."""
        # Fade existing canvas
        self.__canvas *= self.__fade

        # Draw each worm
        for worm_idx, worm in enumerate(self.__worms):
            hue = self.__worm_hues[worm_idx]
            # Slowly shift hue over time
            hue = (hue + self.__time * 0.01) % 1.0

            for seg_idx, (x, y) in enumerate(worm):
                # Brightness fades towards tail
                brightness = 1.0 - (seg_idx / len(worm))
                brightness = brightness ** 0.5  # Softer falloff

                # Get color
                r, g, b = self.__hsv_to_rgb(hue, 0.8, brightness)

                # Draw with glow
                self.__draw_glow(x, y, r, g, b)

    def __draw_glow(self, cx, cy, r, g, b):
        """Draw a glowing point with soft falloff."""
        radius = int(self.__glow_size) + 1

        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                px = int(cx + dx) % self.__width
                py = int(cy + dy) % self.__height

                # Distance from center
                dist = math.sqrt((cx - int(cx) - dx) ** 2 + (cy - int(cy) - dy) ** 2)

                if dist < self.__glow_size:
                    # Gaussian-ish falloff
                    intensity = math.exp(-dist * dist / (self.__glow_size * 0.5))

                    # Additive blending
                    self.__canvas[py, px, 0] = min(1.0, self.__canvas[py, px, 0] + r * intensity * 0.3)
                    self.__canvas[py, px, 1] = min(1.0, self.__canvas[py, px, 1] + g * intensity * 0.3)
                    self.__canvas[py, px, 2] = min(1.0, self.__canvas[py, px, 2] + b * intensity * 0.3)

    def play(self):
        """Run the screensaver."""
        self.__logger.info("Starting Perlin Worms screensaver")
        self.__init_worms()

        for tick in range(self.__max_ticks):
            # Update time
            self.__time += self.__time_speed

            # Update worm positions
            self.__update_worms()

            # Draw worms
            self.__draw_worms()

            # Convert to uint8 frame
            frame = (np.clip(self.__canvas, 0, 1) * 255).astype(np.uint8)

            self.__led_frame_player.play_frame(frame)
            time.sleep(self.__tick_sleep)

        self.__logger.info("Perlin Worms screensaver ended")
