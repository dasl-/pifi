"""
Pendulum Waves screensaver.

A row of pendulums with slightly different periods create
mesmerizing wave patterns as they go in and out of sync.
"""

import math
import numpy as np
import time

from pifi.config import Config
from pifi.led.ledframeplayer import LedFramePlayer
from pifi.logger import Logger


class PendulumWaves:
    """Pendulums creating wave patterns through phase differences."""

    def __init__(self, led_frame_player=None):
        self.__logger = Logger().set_namespace(self.__class__.__name__)

        if led_frame_player is None:
            led_frame_player = LedFramePlayer()
        self.__led_frame_player = led_frame_player

        self.__width = Config.get('leds.display_width')
        self.__height = Config.get('leds.display_height')

        # Config
        self.__num_pendulums = Config.get('pendulumwaves.num_pendulums', 0)  # 0 = auto
        self.__base_period = Config.get('pendulumwaves.base_period', 60.0)  # frames for longest pendulum
        self.__cycle_time = Config.get('pendulumwaves.cycle_time', 600)  # frames for full pattern cycle
        self.__bob_size = Config.get('pendulumwaves.bob_size', 1.5)
        self.__trail_fade = Config.get('pendulumwaves.trail_fade', 0.85)
        self.__color_mode = Config.get('pendulumwaves.color_mode', 'rainbow')  # rainbow, gradient, white
        self.__tick_sleep = Config.get('pendulumwaves.tick_sleep', 0.03)
        self.__max_ticks = Config.get('pendulumwaves.max_ticks', 10000)

        # Auto-calculate pendulum count if not specified
        if self.__num_pendulums <= 0:
            self.__num_pendulums = self.__width

        # Canvas buffer
        self.__canvas = np.zeros((self.__height, self.__width, 3), dtype=np.float32)

        self.__tick = 0

    def __init_pendulums(self):
        """Initialize pendulum parameters."""
        # Each pendulum completes one more oscillation than the previous
        # in the cycle_time. This creates the wave effect.
        #
        # Longest pendulum: completes N oscillations in cycle_time
        # Each subsequent: completes N+1, N+2, etc.

        # Base oscillations for the longest pendulum
        base_oscillations = self.__cycle_time / self.__base_period

        self.__periods = []
        for i in range(self.__num_pendulums):
            # Each pendulum completes i more oscillations in cycle_time
            oscillations = base_oscillations + i
            period = self.__cycle_time / oscillations
            self.__periods.append(period)

        self.__canvas.fill(0)
        self.__tick = 0

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

    def __get_pendulum_color(self, index):
        """Get color for a pendulum based on its index."""
        if self.__color_mode == 'white':
            return (1.0, 1.0, 1.0)
        elif self.__color_mode == 'gradient':
            # Blue to red gradient
            t = index / max(1, self.__num_pendulums - 1)
            return (t, 0.2, 1.0 - t)
        else:  # rainbow
            hue = index / self.__num_pendulums
            return self.__hsv_to_rgb(hue, 0.9, 1.0)

    def __draw_bob(self, cx, cy, r, g, b, size):
        """Draw a glowing pendulum bob."""
        radius = int(size) + 1

        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                px = int(cx + dx)
                py = int(cy + dy)

                # Skip out of bounds
                if px < 0 or px >= self.__width or py < 0 or py >= self.__height:
                    continue

                # Distance from center
                dist = math.sqrt((cx - px) ** 2 + (cy - py) ** 2)

                if dist < size:
                    # Soft falloff
                    intensity = 1.0 - (dist / size)
                    intensity = intensity ** 0.5

                    # Additive blending
                    self.__canvas[py, px, 0] = min(1.0, self.__canvas[py, px, 0] + r * intensity)
                    self.__canvas[py, px, 1] = min(1.0, self.__canvas[py, px, 1] + g * intensity)
                    self.__canvas[py, px, 2] = min(1.0, self.__canvas[py, px, 2] + b * intensity)

    def __update(self):
        """Update pendulum positions and draw."""
        # Fade trails
        self.__canvas *= self.__trail_fade

        # Calculate spacing
        spacing = self.__width / self.__num_pendulums
        margin = spacing / 2

        # Draw each pendulum
        for i in range(self.__num_pendulums):
            # X position (evenly spaced)
            x = margin + i * spacing

            # Y position based on sinusoidal motion
            # Phase is determined by time and period
            phase = (self.__tick / self.__periods[i]) * 2 * math.pi
            y_normalized = math.sin(phase)

            # Map to screen coordinates
            # Pendulum swings in the middle portion of the screen
            amplitude = (self.__height - 2) / 2
            center_y = self.__height / 2
            y = center_y + y_normalized * amplitude * 0.8

            # Get color and draw
            r, g, b = self.__get_pendulum_color(i)
            self.__draw_bob(x, y, r, g, b, self.__bob_size)

        self.__tick += 1

    def play(self):
        """Run the screensaver."""
        self.__logger.info("Starting Pendulum Waves screensaver")
        self.__init_pendulums()

        for tick in range(self.__max_ticks):
            self.__update()

            # Convert to uint8 frame
            frame = (np.clip(self.__canvas, 0, 1) * 255).astype(np.uint8)

            self.__led_frame_player.play_frame(frame)
            time.sleep(self.__tick_sleep)

        self.__logger.info("Pendulum Waves screensaver ended")
