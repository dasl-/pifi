import math
import numpy as np
import time
import random

from pifi.config import Config
from pifi.logger import Logger
from pifi.led.ledframeplayer import LedFramePlayer
from pifi.screensaver.screensaver import Screensaver


class Aurora(Screensaver):
    """
    Aurora borealis (northern lights) screensaver.

    Simulates the flowing, curtain-like appearance of the aurora with:
    - Vertical ribbon structures that undulate horizontally
    - Green core with pink/magenta edges
    - Shimmer and brightness variations
    - Multiple layered curtains with depth
    - Optional background stars
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

        # Curtains: each has properties defining its behavior
        self.__curtains = []

        # Background stars (x, y, brightness, twinkle_phase)
        self.__stars = []

        # Time accumulator
        self.__time = 0.0

        # Activity level (for bursts)
        self.__activity = 1.0
        self.__target_activity = 1.0

    def play(self):
        self.__logger.info("Starting Aurora screensaver")
        self.__reset()

        max_ticks = Config.get('aurora.max_ticks', 3000)
        tick = 0

        while tick < max_ticks:
            self.__tick()
            time.sleep(self.__get_tick_sleep())
            tick += 1

        self.__logger.info("Aurora screensaver ended")

    def __reset(self):
        self.__time = 0.0
        self.__activity = 1.0
        self.__target_activity = 1.0

        # Create curtains
        num_curtains = Config.get('aurora.num_curtains', 4)
        self.__curtains = []

        for i in range(num_curtains):
            self.__curtains.append(self.__create_curtain(i, num_curtains))

        # Create background stars
        if Config.get('aurora.show_stars', True):
            num_stars = Config.get('aurora.num_stars', 15)
            self.__stars = []
            for _ in range(num_stars):
                self.__stars.append({
                    'x': random.randint(0, self.__width - 1),
                    'y': random.randint(0, self.__height // 2),  # Stars in upper half
                    'brightness': random.uniform(0.3, 1.0),
                    'twinkle_speed': random.uniform(0.05, 0.15),
                    'twinkle_phase': random.uniform(0, 2 * math.pi),
                })

    def __create_curtain(self, index, total):
        """Create a curtain with randomized properties."""
        return {
            # Base horizontal position (0-1 range, will be scaled to width)
            'base_x': random.uniform(0.1, 0.9),

            # Horizontal drift speed
            'drift_speed': random.uniform(-0.002, 0.002),

            # Wave properties for undulation
            'wave_freq': random.uniform(0.3, 0.8),  # Vertical frequency
            'wave_amp': random.uniform(0.05, 0.15),  # Horizontal amplitude
            'wave_speed': random.uniform(0.5, 1.5),  # Animation speed

            # Secondary wave for more organic movement
            'wave2_freq': random.uniform(0.5, 1.2),
            'wave2_amp': random.uniform(0.02, 0.08),
            'wave2_speed': random.uniform(0.3, 0.8),

            # Curtain width (how spread out it is)
            'width': random.uniform(0.08, 0.2),

            # Intensity/opacity of this curtain
            'intensity': random.uniform(0.5, 1.0),

            # Depth (affects parallax and brightness)
            'depth': index / max(1, total - 1),  # 0 = front, 1 = back

            # Color temperature shift
            'color_temp': random.uniform(-0.2, 0.2),

            # Shimmer properties
            'shimmer_speed': random.uniform(2.0, 5.0),
        }

    def __tick(self):
        time_speed = Config.get('aurora.time_speed', 1.0)
        self.__time += 0.05 * time_speed

        # Occasionally change activity level (bursts)
        if random.random() < 0.005:
            self.__target_activity = random.uniform(0.5, 2.0)

        # Smooth activity transitions
        self.__activity += (self.__target_activity - self.__activity) * 0.02

        # Update curtain drift
        for curtain in self.__curtains:
            curtain['base_x'] += curtain['drift_speed']

            # Wrap around or bounce
            if curtain['base_x'] < -0.2:
                curtain['base_x'] = 1.2
            elif curtain['base_x'] > 1.2:
                curtain['base_x'] = -0.2

        self.__render()

    def __render(self):
        frame = np.zeros([self.__height, self.__width, 3], dtype=np.float32)

        # Draw background stars first
        if Config.get('aurora.show_stars', True):
            for star in self.__stars:
                # Twinkle
                twinkle = 0.5 + 0.5 * math.sin(self.__time * star['twinkle_speed'] * 10 + star['twinkle_phase'])
                brightness = star['brightness'] * twinkle * 0.6

                x, y = star['x'], star['y']
                if 0 <= x < self.__width and 0 <= y < self.__height:
                    # Dim white/blue for stars
                    frame[y, x, 0] = brightness * 200
                    frame[y, x, 1] = brightness * 200
                    frame[y, x, 2] = brightness * 255

        # Draw curtains (back to front for proper layering)
        sorted_curtains = sorted(self.__curtains, key=lambda c: -c['depth'])

        for curtain in sorted_curtains:
            self.__draw_curtain(frame, curtain)

        # Convert to uint8
        frame = np.clip(frame, 0, 255).astype(np.uint8)
        self.__led_frame_player.play_frame(frame)

    def __draw_curtain(self, frame, curtain):
        """Draw a single aurora curtain onto the frame."""
        base_x = curtain['base_x'] * self.__width
        width = curtain['width'] * self.__width
        intensity = curtain['intensity'] * self.__activity

        # Depth affects brightness (farther = dimmer)
        depth_factor = 0.4 + 0.6 * (1 - curtain['depth'])

        for y in range(self.__height):
            # Normalized y position (0 = top, 1 = bottom)
            y_norm = y / max(1, self.__height - 1)

            # Vertical brightness gradient (brighter at bottom, representing horizon)
            # Aurora is typically brighter lower in the sky
            vert_brightness = 0.2 + 0.8 * (y_norm ** 0.7)

            # Calculate horizontal position with undulation
            wave1 = math.sin(y_norm * curtain['wave_freq'] * 10 + self.__time * curtain['wave_speed'])
            wave2 = math.sin(y_norm * curtain['wave2_freq'] * 15 + self.__time * curtain['wave2_speed'] + 1.5)

            x_offset = (wave1 * curtain['wave_amp'] + wave2 * curtain['wave2_amp']) * self.__width
            center_x = base_x + x_offset

            # Shimmer effect (rapid brightness fluctuation)
            shimmer = 0.7 + 0.3 * math.sin(
                y * 0.5 + self.__time * curtain['shimmer_speed'] + curtain['base_x'] * 20
            )

            # Draw the curtain width at this y level
            for x in range(self.__width):
                # Distance from curtain center
                dist = abs(x - center_x)

                if dist < width * 2:
                    # Gaussian-ish falloff from center
                    falloff = math.exp(-(dist * dist) / (2 * width * width))

                    # Combined brightness
                    brightness = falloff * vert_brightness * intensity * depth_factor * shimmer

                    if brightness > 0.01:
                        # Aurora color: green core, pink/magenta at edges
                        # Core detection based on distance from center
                        core_factor = falloff  # 1 at center, 0 at edges

                        # Base green color
                        r = 0.0
                        g = 1.0
                        b = 0.0

                        # Blend toward pink/magenta at edges
                        edge_blend = 1 - core_factor
                        r += edge_blend * 0.8  # Add red for pink
                        g -= edge_blend * 0.3  # Reduce green slightly
                        b += edge_blend * 0.6  # Add blue for magenta tint

                        # Color temperature variation
                        temp = curtain['color_temp']
                        if temp > 0:
                            # Warmer (more pink)
                            r += temp * 0.3
                        else:
                            # Cooler (more blue-green)
                            b -= temp * 0.3

                        # Height-based color shift (more pink/purple at top)
                        height_color = 1 - y_norm
                        r += height_color * 0.2
                        b += height_color * 0.3

                        # Apply brightness and add to frame (additive blending)
                        frame[y, x, 0] = min(255, frame[y, x, 0] + r * brightness * 255)
                        frame[y, x, 1] = min(255, frame[y, x, 1] + g * brightness * 255)
                        frame[y, x, 2] = min(255, frame[y, x, 2] + b * brightness * 255)

    def __get_tick_sleep(self):
        return Config.get('aurora.tick_sleep', 0.04)

    @classmethod
    def get_id(cls) -> str:
        return 'aurora'

    @classmethod
    def get_name(cls) -> str:
        return 'Aurora Borealis'

    @classmethod
    def get_description(cls) -> str:
        return 'Northern lights with curtains'
