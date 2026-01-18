import numpy as np
import time
import random
import math

from pifi.config import Config
from pifi.logger import Logger
from pifi.led.ledframeplayer import LedFramePlayer
from pifi.screensaver.screensaver import Screensaver


class InkInWater(Screensaver):
    """
    Ink drops diffusing in water.

    Drops of colored ink fall and slowly spread outward,
    creating beautiful blending patterns as colors mix.
    """

    def __init__(self, led_frame_player=None):
        self.__logger = Logger().set_namespace(self.__class__.__name__)

        if led_frame_player is None:
            self.__led_frame_player = LedFramePlayer()
        else:
            self.__led_frame_player = led_frame_player

        self.__width = Config.get_or_throw('leds.display_width')
        self.__height = Config.get_or_throw('leds.display_height')

        # RGB buffer for diffusion
        self.__buffer = None
        self.__time = 0

    def play(self):
        self.__logger.info("Starting Ink in Water screensaver")
        self.__reset()

        max_ticks = Config.get('inkinwater.max_ticks', 2500)
        tick = 0

        while tick < max_ticks:
            self.__tick()
            time.sleep(self.__get_tick_sleep())
            tick += 1

        self.__logger.info("Ink in Water screensaver ended")

    def __reset(self):
        self.__time = 0
        self.__buffer = np.zeros((self.__height, self.__width, 3), dtype=np.float32)

        # Add several initial drops for immediate visual interest
        for _ in range(6):
            self.__add_drop()

    def __add_drop(self):
        """Add a new ink drop at a random location."""
        x = random.randint(3, self.__width - 4)
        y = random.randint(3, self.__height - 4)

        # Random vibrant color
        hue = random.random()
        color = self.__hsv_to_rgb(hue, 0.9, 1.0)

        # Add ink as a larger blob for more visual impact
        radius = random.uniform(1.5, 3.0)
        intensity = random.uniform(200, 255)

        for dy in range(-3, 4):
            for dx in range(-3, 4):
                nx, ny = x + dx, y + dy
                if 0 <= nx < self.__width and 0 <= ny < self.__height:
                    dist = math.sqrt(dx * dx + dy * dy)
                    if dist < radius:
                        falloff = 1.0 - (dist / radius)
                        falloff = falloff ** 0.5  # Softer falloff
                        self.__buffer[ny, nx, 0] += color[0] * falloff * intensity / 255
                        self.__buffer[ny, nx, 1] += color[1] * falloff * intensity / 255
                        self.__buffer[ny, nx, 2] += color[2] * falloff * intensity / 255

    def __tick(self):
        # Add new drops more frequently for more activity
        drop_chance = Config.get('inkinwater.drop_chance', 0.06)
        if random.random() < drop_chance:
            self.__add_drop()

        # Add subtle flow/movement to make it more dynamic
        self.__apply_flow()

        # Diffuse the ink
        self.__diffuse()

        # Very slow fade to prevent eternal buildup
        fade = Config.get('inkinwater.fade', 0.997)
        self.__buffer *= fade

        self.__render()
        self.__time += 1

    def __apply_flow(self):
        """Apply subtle upward flow like ink rising in water."""
        flow_strength = Config.get('inkinwater.flow_strength', 0.03)
        if flow_strength <= 0:
            return

        # Shift buffer slightly upward with wrapping
        shifted = np.roll(self.__buffer, -1, axis=0)
        # Blend original with shifted version for subtle movement
        self.__buffer = self.__buffer * (1 - flow_strength) + shifted * flow_strength

    def __diffuse(self):
        """Simple diffusion - each pixel shares with neighbors."""
        diffusion_rate = Config.get('inkinwater.diffusion_rate', 0.15)

        # Pad for edge handling
        padded = np.pad(self.__buffer, ((1, 1), (1, 1), (0, 0)), mode='edge')

        # Average of neighbors
        neighbors = (
            padded[:-2, 1:-1] +  # up
            padded[2:, 1:-1] +   # down
            padded[1:-1, :-2] +  # left
            padded[1:-1, 2:]     # right
        ) / 4.0

        # Blend current with neighbors
        self.__buffer = self.__buffer * (1 - diffusion_rate) + neighbors * diffusion_rate

    def __render(self):
        # Clamp and convert to uint8
        frame = np.clip(self.__buffer * 255, 0, 255).astype(np.uint8)
        self.__led_frame_player.play_frame(frame)

    def __hsv_to_rgb(self, h, s, v):
        if s == 0.0:
            return [v, v, v]

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

        return [r, g, b]

    def __get_tick_sleep(self):
        return Config.get('inkinwater.tick_sleep', 0.04)

    @classmethod
    def get_id(cls) -> str:
        return 'inkinwater'

    @classmethod
    def get_name(cls) -> str:
        return 'Ink in Water'

    @classmethod
    def get_description(cls) -> str:
        return 'Diffusing color blooms'
