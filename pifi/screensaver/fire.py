import numpy as np
import random

from pifi.config import Config
from pifi.screensaver.screensaver import Screensaver


class Fire(Screensaver):
    """
    Classic demoscene fire effect.

    Heat rises from the bottom, cools as it goes up, and is mapped
    through a black → deep red → orange → yellow → white palette.
    Simple, iconic, mesmerizing.
    """

    def __init__(self, led_frame_player=None):
        super().__init__(led_frame_player)

        self.__width = Config.get_or_throw('leds.display_width')
        self.__height = Config.get_or_throw('leds.display_height')

    def _setup(self):
        # Heat buffer — extra row at bottom for the heat source
        self.__heat = np.zeros((self.__height + 1, self.__width), dtype=np.float64)

        # Build the fire palette (256 entries)
        self.__palette = self.__build_palette()

        # Cooling rate — how quickly heat dissipates going up
        self.__cooling = random.uniform(0.3, 0.5)

        # Wind — slight horizontal bias
        self.__wind = random.uniform(-0.15, 0.15)

        # Persistent heat source that evolves smoothly
        self.__base_heat = np.random.uniform(0.4, 0.9, self.__width)

    def _tick(self):
        h, w = self.__height, self.__width
        heat = self.__heat

        # Smoothly evolve the persistent heat source rather than
        # regenerating it from scratch each frame.
        drift = np.random.uniform(-0.06, 0.06, w)
        self.__base_heat = np.clip(self.__base_heat + drift, 0.2, 1.0)

        # Occasionally shift a hot spot to a new location
        if random.random() < 0.08:
            cx = random.randint(0, w - 1)
            spread = random.randint(1, max(1, w // 8))
            x_lo = max(0, cx - spread)
            x_hi = min(w, cx + spread + 1)
            target = random.uniform(0.85, 1.0)
            self.__base_heat[x_lo:x_hi] += (target - self.__base_heat[x_lo:x_hi]) * 0.4

        heat[h, :] = self.__base_heat

        # Propagate heat upward with averaging and cooling
        for y in range(h - 1, -1, -1):
            below = heat[y + 1]
            below_left = np.roll(below, 1)
            below_right = np.roll(below, -1)

            # Wind bias
            if self.__wind > 0:
                avg = (below * (2 - self.__wind) + below_left * (1 + self.__wind) + below_right) / 4
            else:
                avg = (below * (2 + self.__wind) + below_left + below_right * (1 - self.__wind)) / 4

            # Cooling increases with height for shorter flames
            height_factor = 1.0 + (1 - y / h) * 2.0
            heat[y] = np.clip(avg - self.__cooling * height_factor / h, 0, 1)

        # Map heat to color via palette
        indices = (np.clip(heat[:h], 0, 1) * 255).astype(int)
        frame = self.__palette[indices]

        self._led_frame_player.play_frame(frame)

    def __build_palette(self):
        """Build a 256-entry fire palette: black → red → orange → yellow → white."""
        palette = np.zeros((256, 3), dtype=np.uint8)

        for i in range(256):
            t = i / 255.0

            if t < 0.33:
                # Black to dark red
                p = t / 0.33
                r = int(p * 180)
                g = 0
                b = 0
            elif t < 0.6:
                # Dark red to orange
                p = (t - 0.33) / 0.27
                r = 180 + int(p * 75)
                g = int(p * 120)
                b = 0
            elif t < 0.8:
                # Orange to yellow
                p = (t - 0.6) / 0.2
                r = 255
                g = 120 + int(p * 135)
                b = int(p * 30)
            else:
                # Yellow to white
                p = (t - 0.8) / 0.2
                r = 255
                g = 255
                b = 30 + int(p * 225)

            palette[i] = [min(255, r), min(255, g), min(255, b)]

        return palette

    @classmethod
    def get_id(cls) -> str:
        return 'fire'

    @classmethod
    def get_name(cls) -> str:
        return 'Fire'

    @classmethod
    def get_description(cls) -> str:
        return 'Classic demoscene fire'
