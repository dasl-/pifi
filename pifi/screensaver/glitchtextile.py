import numpy as np
import random
import math

from pifi.config import Config
from pifi.screensaver.screensaver import Screensaver


class GlitchTextile(Screensaver):
    """
    Glitch textile — generative weaving with digital corruption.

    Creates warp/weft grid patterns like a loom, then introduces
    glitches: dropped threads, color bleeding, shifted rows,
    and pattern corruption. References both digital error and
    physical craft.
    """

    def __init__(self, led_frame_player=None):
        super().__init__(led_frame_player)

        self.__width = Config.get_or_throw('leds.display_width')
        self.__height = Config.get_or_throw('leds.display_height')
        self.__time = 0

    def _setup(self):
        self.__time = 0

        # Base weave pattern parameters
        self.__weave_type = random.choice(['plain', 'twill', 'satin'])

        # Thread colors — 2-3 warp colors, 2-3 weft colors
        base_hue = random.random()
        self.__warp_hues = [
            (base_hue + random.uniform(-0.05, 0.05)) % 1.0
            for _ in range(random.randint(2, 3))
        ]
        self.__weft_hues = [
            (base_hue + random.uniform(0.15, 0.45)) % 1.0
            for _ in range(random.randint(2, 3))
        ]

        # Thread width in pixels
        self.__thread_w = random.choice([1, 2])

        # Glitch state
        self.__glitch_rows = set()
        self.__glitch_cols = set()
        self.__color_bleed = {}
        self.__shift_offset = {}

        # Pre-generate base pattern
        self.__base_pattern = self.__generate_weave()

    def __generate_weave(self):
        """Generate the base weave pattern as a boolean grid (True=warp on top)."""
        h, w = self.__height, self.__width
        tw = self.__thread_w
        pattern = np.zeros((h, w), dtype=bool)

        for y in range(h):
            for x in range(w):
                # Thread indices
                ty = y // tw
                tx = x // tw

                if self.__weave_type == 'plain':
                    pattern[y, x] = (ty + tx) % 2 == 0
                elif self.__weave_type == 'twill':
                    pattern[y, x] = (ty + tx) % 3 < 1
                else:  # satin
                    pattern[y, x] = (ty * 2 + tx) % 5 < 2

        return pattern

    def _tick(self, tick):
        self.__time = tick

        # Periodically update glitches
        if tick % 8 == 0:
            self.__update_glitches()

        self.__render()

    def __update_glitches(self):
        """Add, remove, and evolve glitch effects."""
        # Randomly drop/restore rows
        if random.random() < 0.3:
            if len(self.__glitch_rows) > self.__height // 4:
                self.__glitch_rows.discard(random.choice(list(self.__glitch_rows)))
            else:
                self.__glitch_rows.add(random.randint(0, self.__height - 1))

        # Randomly drop/restore columns
        if random.random() < 0.2:
            if len(self.__glitch_cols) > self.__width // 4:
                self.__glitch_cols.discard(random.choice(list(self.__glitch_cols)))
            else:
                self.__glitch_cols.add(random.randint(0, self.__width - 1))

        # Row shift glitches — displaced rows
        if random.random() < 0.25:
            y = random.randint(0, self.__height - 1)
            if y in self.__shift_offset:
                del self.__shift_offset[y]
            else:
                self.__shift_offset[y] = random.randint(-self.__width // 3, self.__width // 3)

        # Color bleed — wrong color in some regions
        if random.random() < 0.2:
            y = random.randint(0, self.__height - 1)
            if y in self.__color_bleed:
                del self.__color_bleed[y]
            else:
                self.__color_bleed[y] = random.uniform(0, 1)

    def __render(self):
        h, w = self.__height, self.__width
        frame = np.zeros((h, w, 3), dtype=np.uint8)
        t = self.__time

        for y in range(h):
            x_offset = self.__shift_offset.get(y, 0)
            bleed_hue = self.__color_bleed.get(y, None)
            is_dropped_row = y in self.__glitch_rows

            tw = self.__thread_w
            ty = y // tw

            for x in range(w):
                # Apply row shift
                sx = (x + x_offset) % w
                is_dropped_col = x in self.__glitch_cols

                # Dropped thread — dark gap
                if is_dropped_row or is_dropped_col:
                    # Show the "other" thread dimly, or gap
                    if random.random() < 0.3:
                        frame[y, x] = [8, 8, 8]
                    continue

                tx = sx // tw
                warp_on_top = self.__base_pattern[y, sx]

                if warp_on_top:
                    hue = self.__warp_hues[tx % len(self.__warp_hues)]
                    val = 0.6 + 0.15 * math.sin(ty * 0.5 + t * 0.05)
                else:
                    hue = self.__weft_hues[ty % len(self.__weft_hues)]
                    val = 0.5 + 0.15 * math.sin(tx * 0.5 + t * 0.07)

                # Apply color bleed
                if bleed_hue is not None:
                    hue = (hue + bleed_hue * 0.5) % 1.0
                    val *= 0.8

                r, g, b = _hsv_to_rgb_scalar(hue, 0.65, val)
                frame[y, x] = [int(r * 255), int(g * 255), int(b * 255)]

        self._led_frame_player.play_frame(frame)

    @classmethod
    def get_id(cls) -> str:
        return 'glitch_textile'

    @classmethod
    def get_name(cls) -> str:
        return 'Glitch Textile'

    @classmethod
    def get_description(cls) -> str:
        return 'Corrupted digital weaving'


def _hsv_to_rgb_scalar(h, s, v):
    h = h % 1.0
    i = int(h * 6)
    f = h * 6 - i
    p = v * (1 - s)
    q = v * (1 - s * f)
    t = v * (1 - s * (1 - f))
    i = i % 6
    if i == 0: return v, t, p
    elif i == 1: return q, v, p
    elif i == 2: return p, v, t
    elif i == 3: return p, q, v
    elif i == 4: return t, p, v
    else: return v, p, q
