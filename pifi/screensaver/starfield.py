import math
import numpy as np
import time
import random

from pifi.config import Config
from pifi.logger import Logger
from pifi.led.ledframeplayer import LedFramePlayer
from pifi.screensaver.screensaver import Screensaver


class Starfield(Screensaver):
    """
    Classic 3D starfield screensaver.

    Simulates flying through a field of stars, with stars appearing
    from the center and streaking outward. Closer stars move faster
    and appear brighter.
    """

    def __init__(self, led_frame_player=None):
        self.__logger = Logger().set_namespace(self.__class__.__name__)

        if led_frame_player is None:
            self.__led_frame_player = LedFramePlayer()
        else:
            self.__led_frame_player = led_frame_player

        self.__width = Config.get_or_throw('leds.display_width')
        self.__height = Config.get_or_throw('leds.display_height')

        # Stars: each is [x, y, z] where z is depth (0 = closest, 1 = farthest)
        self.__stars = []

    def play(self):
        self.__logger.info("Starting Starfield screensaver")
        self.__reset()

        max_ticks = Config.get('starfield.max_ticks', 3000)
        tick = 0

        while tick < max_ticks:
            self.__tick()
            time.sleep(self.__get_tick_sleep())
            tick += 1

        self.__logger.info("Starfield screensaver ended")

    def __reset(self):
        num_stars = Config.get('starfield.num_stars', 80)
        self.__stars = []

        for _ in range(num_stars):
            self.__add_star(random_z=True)

    def __add_star(self, random_z=False):
        """Add a new star at a random position."""
        # Stars start in a circle around center, spread out in 3D
        # x, y are in normalized coordinates (-1 to 1)
        angle = random.uniform(0, 2 * math.pi)
        radius = random.uniform(0.1, 1.5)

        x = math.cos(angle) * radius
        y = math.sin(angle) * radius

        # z is depth: new stars start far away (z=1), move toward viewer (z=0)
        if random_z:
            z = random.uniform(0.1, 1.0)
        else:
            z = 1.0

        self.__stars.append([x, y, z])

    def __tick(self):
        speed = Config.get('starfield.speed', 0.02)

        # Move stars toward viewer (decrease z)
        new_stars = []
        for star in self.__stars:
            star[2] -= speed

            # If star passed the viewer, respawn it far away
            if star[2] <= 0.01:
                self.__add_star(random_z=False)
            else:
                new_stars.append(star)

        self.__stars = new_stars

        # Maintain star count
        num_stars = Config.get('starfield.num_stars', 80)
        while len(self.__stars) < num_stars:
            self.__add_star(random_z=False)

        self.__render()

    def __render(self):
        frame = np.zeros([self.__height, self.__width, 3], np.uint8)

        cx = self.__width / 2
        cy = self.__height / 2

        show_trails = Config.get('starfield.show_trails', True)
        trail_length = Config.get('starfield.trail_length', 3)

        for star in self.__stars:
            x, y, z = star

            # Perspective projection: closer stars (small z) spread out more
            # Avoid division by very small z
            z_safe = max(z, 0.01)
            screen_x = cx + (x / z_safe) * cx
            screen_y = cy + (y / z_safe) * cy

            # Brightness based on depth (closer = brighter)
            brightness = 1.0 - z_safe
            brightness = max(0, min(1, brightness))

            # Size/intensity based on depth
            intensity = int(brightness * 255)

            # Color: white with slight blue tint for distant stars
            if z > 0.7:
                # Distant stars: dimmer, slightly blue
                color = [int(intensity * 0.7), int(intensity * 0.8), intensity]
            elif z > 0.4:
                # Mid-distance: white
                color = [intensity, intensity, intensity]
            else:
                # Close stars: bright white, slightly warm
                color = [intensity, intensity, int(intensity * 0.95)]

            ix = int(screen_x)
            iy = int(screen_y)

            if 0 <= ix < self.__width and 0 <= iy < self.__height:
                # Draw the star
                frame[iy, ix] = np.maximum(frame[iy, ix], color)

                # Draw trail for close, fast-moving stars
                if show_trails and z < 0.5:
                    trail_brightness = brightness * 0.5
                    for t in range(1, trail_length + 1):
                        # Trail extends back toward center
                        trail_z = z + t * 0.05
                        if trail_z > 1:
                            break
                        trail_x = cx + (x / trail_z) * cx
                        trail_y = cy + (y / trail_z) * cy
                        tix = int(trail_x)
                        tiy = int(trail_y)

                        if 0 <= tix < self.__width and 0 <= tiy < self.__height:
                            trail_int = int(trail_brightness * 255 * (1 - t / (trail_length + 1)))
                            trail_color = [trail_int, trail_int, trail_int]
                            frame[tiy, tix] = np.maximum(frame[tiy, tix], trail_color)

        self.__led_frame_player.play_frame(frame)

    def __get_tick_sleep(self):
        return Config.get('starfield.tick_sleep', 0.03)

    @classmethod
    def get_id(cls) -> str:
        return 'starfield'

    @classmethod
    def get_name(cls) -> str:
        return 'Starfield'

    @classmethod
    def get_description(cls) -> str:
        return '3D flying through stars'
