import math
import numpy as np
import time
import random

from pifi.config import Config
from pifi.logger import Logger
from pifi.led.ledframeplayer import LedFramePlayer
from pifi.screensaver.screensaver import Screensaver


class LavaLamp(Screensaver):
    """
    Classic lava lamp simulation.

    Warm blobs rise from the bottom, cool at the top, and sink back down.
    Uses metaball rendering for smooth, blobby shapes.
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

        self.__blobs = []
        self.__time = 0

    def play(self):
        self.__logger.info("Starting Lava Lamp screensaver")
        self.__reset()

        max_ticks = Config.get('lavalamp.max_ticks', 3000)
        tick = 0

        while tick < max_ticks:
            self.__tick()
            time.sleep(self.__get_tick_sleep())
            tick += 1

        self.__logger.info("Lava Lamp screensaver ended")

    def __reset(self):
        self.__time = 0

        # Create blobs - more blobs for more activity
        num_blobs = Config.get('lavalamp.num_blobs', 10)
        self.__blobs = []

        for i in range(num_blobs):
            # Start some at top (cold) and some at bottom (hot) for immediate motion
            if i % 2 == 0:
                y = random.uniform(0, self.__height * 0.3)
                heat = random.uniform(0.2, 0.4)
            else:
                y = random.uniform(self.__height * 0.7, self.__height)
                heat = random.uniform(0.7, 0.9)

            self.__blobs.append({
                'x': random.uniform(1, self.__width - 1),
                'y': y,
                'vx': random.uniform(-0.1, 0.1),
                'vy': 0,
                'radius': random.uniform(1.5, 3.5),
                'heat': heat,
            })

        # Color palette - warm colors like real lava lamp
        self.__base_hue = random.choice([0.0, 0.05, 0.08, 0.55, 0.75])  # Red, orange, yellow, blue, purple

    def __tick(self):
        self.__update_blobs()
        self.__render()
        self.__time += 1

    def __update_blobs(self):
        heat_rate = Config.get('lavalamp.heat_rate', 0.03)
        cool_rate = Config.get('lavalamp.cool_rate', 0.02)
        buoyancy = Config.get('lavalamp.buoyancy', 0.08)
        damping = 0.96

        for blob in self.__blobs:
            # Heat from bottom, cool from top
            # Temperature gradient based on y position
            ambient_temp = 1.0 - (blob['y'] / self.__height)

            if blob['heat'] < ambient_temp:
                blob['heat'] += heat_rate
            else:
                blob['heat'] -= cool_rate

            blob['heat'] = max(0.1, min(1.0, blob['heat']))

            # Buoyancy force based on heat differential
            # Hot blobs rise, cool blobs sink
            target_y = (1.0 - blob['heat']) * self.__height
            blob['vy'] += (target_y - blob['y']) * buoyancy * 0.15

            # Add wobble motion using sine waves for organic movement
            wobble = math.sin(self.__time * 0.05 + blob['x']) * 0.02
            blob['vx'] += wobble

            # More horizontal drift
            blob['vx'] += random.uniform(-0.02, 0.02)

            # Apply velocity with damping
            blob['vx'] *= damping
            blob['vy'] *= damping

            blob['x'] += blob['vx']
            blob['y'] += blob['vy']

            # Bounce off walls
            if blob['x'] < blob['radius']:
                blob['x'] = blob['radius']
                blob['vx'] *= -0.5
            elif blob['x'] > self.__width - blob['radius']:
                blob['x'] = self.__width - blob['radius']
                blob['vx'] *= -0.5

            # Contain vertically
            if blob['y'] < 0:
                blob['y'] = 0
                blob['vy'] *= -0.3
            elif blob['y'] > self.__height - 1:
                blob['y'] = self.__height - 1
                blob['vy'] *= -0.3

    def __render(self):
        frame = np.zeros((self.__height, self.__width, 3), dtype=np.uint8)

        # For each pixel, calculate metaball field value
        for y in range(self.__height):
            for x in range(self.__width):
                field = 0
                avg_heat = 0
                total_influence = 0

                for blob in self.__blobs:
                    dx = x - blob['x']
                    dy = y - blob['y']
                    dist_sq = dx * dx + dy * dy + 0.1
                    r_sq = blob['radius'] * blob['radius']

                    # Inverse square falloff for metaball effect
                    influence = r_sq / dist_sq
                    field += influence
                    avg_heat += blob['heat'] * influence
                    total_influence += influence

                if total_influence > 0:
                    avg_heat /= total_influence

                # Threshold for blob surface
                threshold = 1.0
                if field > threshold:
                    # Inside a blob
                    # Color based on heat: hot = bright, cool = darker
                    saturation = 0.8
                    value = 0.4 + avg_heat * 0.6

                    # Slight hue shift with heat
                    hue = (self.__base_hue + avg_heat * 0.1) % 1.0

                    color = self.__hsv_to_rgb(hue, saturation, value)
                    frame[y, x] = color
                elif field > threshold * 0.7:
                    # Glow around blobs
                    glow = (field - threshold * 0.7) / (threshold * 0.3)
                    hue = self.__base_hue
                    color = self.__hsv_to_rgb(hue, 0.9, glow * 0.3)
                    frame[y, x] = color

        self.__led_frame_player.play_frame(frame)

    def __hsv_to_rgb(self, h, s, v):
        if s == 0.0:
            val = int(v * 255)
            return [val, val, val]

        i = int(h * 6.0)
        f = (h * 6.0) - i
        p = v * (1.0 - s)
        q = v * (1.0 - s * f)
        t = v * (1.0 - s * (1.0 - f))
        i = i % 6

        if i == 0:
            r, g, b = v, t, p
        elif i == 1:
            r, g, b = q, v, p
        elif i == 2:
            r, g, b = p, v, t
        elif i == 3:
            r, g, b = p, q, v
        elif i == 4:
            r, g, b = t, p, v
        else:
            r, g, b = v, p, q

        return [int(r * 255), int(g * 255), int(b * 255)]

    def __get_tick_sleep(self):
        return Config.get('lavalamp.tick_sleep', 0.05)

    @classmethod
    def get_id(cls) -> str:
        return 'lavalamp'

    @classmethod
    def get_name(cls) -> str:
        return 'Lava Lamp'

    @classmethod
    def get_description(cls) -> str:
        return 'Rising and falling blobs'
