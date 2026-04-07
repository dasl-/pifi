import numpy as np
import random
import math

from pifi.config import Config
from pifi.screensaver.screensaver import Screensaver


class Ikeda(Screensaver):
    """
    Ryoji Ikeda-inspired data-driven minimalism.

    Rapid horizontal scan lines, binary flicker, stark monochrome
    with occasional bursts of color. Visualizes abstract data streams
    as high-contrast light patterns.
    """

    def __init__(self, led_frame_player=None):
        super().__init__(led_frame_player)

        self.__width = Config.get_or_throw('leds.display_width')
        self.__height = Config.get_or_throw('leds.display_height')
        self.__time = 0

    def _setup(self):
        self.__time = 0
        self.__canvas = np.zeros((self.__height, self.__width, 3), dtype=np.uint8)

        # Mode duration counters
        self.__mode = self.__pick_mode()
        self.__mode_ticks = 0
        self.__mode_duration = random.randint(30, 120)

        # Accent color for rare bursts
        self.__accent_hue = random.random()

    def _tick(self, tick):
        self.__time = tick
        self.__mode_ticks += 1

        # Switch modes periodically
        if self.__mode_ticks >= self.__mode_duration:
            self.__mode = self.__pick_mode()
            self.__mode_ticks = 0
            self.__mode_duration = random.randint(30, 120)

        mode = self.__mode
        if mode == 'scanlines':
            self.__render_scanlines()
        elif mode == 'binary':
            self.__render_binary()
        elif mode == 'bars':
            self.__render_bars()
        elif mode == 'burst':
            self.__render_burst()
        elif mode == 'rain':
            self.__render_data_rain()

    def __pick_mode(self):
        # Weighted: mostly stark modes, occasional color burst
        return random.choices(
            ['scanlines', 'binary', 'bars', 'rain', 'burst'],
            weights=[3, 3, 2, 2, 1],
        )[0]

    def __render_scanlines(self):
        """Horizontal scan lines sweeping across."""
        frame = np.zeros((self.__height, self.__width, 3), dtype=np.uint8)
        t = self.__mode_ticks

        # Moving bright scanline
        scan_y = t % (self.__height * 2)
        if scan_y >= self.__height:
            scan_y = self.__height * 2 - scan_y - 1

        # Bright scanline with falloff
        for y in range(self.__height):
            dist = abs(y - scan_y)
            if dist == 0:
                brightness = 255
            elif dist == 1:
                brightness = 120
            elif dist == 2:
                brightness = 40
            else:
                # Dim static on other lines
                brightness = random.randint(0, 8)
            frame[y, :] = brightness

        # Random flicker columns
        num_flicker = random.randint(0, self.__width // 4)
        for _ in range(num_flicker):
            x = random.randint(0, self.__width - 1)
            frame[:, x] = np.random.randint(0, 30, (self.__height, 3), dtype=np.uint8)

        self._led_frame_player.play_frame(frame)

    def __render_binary(self):
        """Binary on/off pixels — rapid data visualization."""
        # Mostly black with clusters of white
        density = 0.1 + 0.15 * math.sin(self.__mode_ticks * 0.15)
        bits = (np.random.random((self.__height, self.__width)) < density).astype(np.uint8)

        # Add horizontal structure — some rows are dense, some empty
        row_mask = np.random.random(self.__height) < 0.6
        bits[~row_mask] = 0

        frame = np.stack([bits * 255] * 3, axis=-1).astype(np.uint8)

        # Occasional single-color tint
        if random.random() < 0.15:
            tint = np.array([0, 0, 0], dtype=np.uint8)
            tint[random.randint(0, 2)] = 255
            frame = bits[:, :, np.newaxis] * tint[np.newaxis, np.newaxis, :]

        self._led_frame_player.play_frame(frame)

    def __render_bars(self):
        """Vertical bars of varying width and brightness."""
        frame = np.zeros((self.__height, self.__width, 3), dtype=np.uint8)
        t = self.__mode_ticks

        x = 0
        while x < self.__width:
            bar_w = random.randint(1, max(1, self.__width // 8))
            brightness = random.choice([0, 0, 0, 40, 120, 200, 255])
            x_hi = min(x + bar_w, self.__width)

            # Bars shift over time
            if brightness > 0:
                # Slight vertical variation
                for col in range(x, x_hi):
                    v = max(0, brightness + random.randint(-30, 30))
                    frame[:, col] = v
            x = x_hi

        # Horizontal cutoff — only part of the frame lit
        cutoff = int(self.__height * (0.3 + 0.7 * abs(math.sin(t * 0.08))))
        frame[cutoff:] = 0

        self._led_frame_player.play_frame(frame)

    def __render_burst(self):
        """Rare color burst — sudden flash of the accent color."""
        t = self.__mode_ticks
        frame = np.zeros((self.__height, self.__width, 3), dtype=np.uint8)

        # Intensity peaks then fades
        progress = t / max(1, self.__mode_duration)
        intensity = math.exp(-((progress - 0.2) ** 2) / 0.02) * 255

        if intensity > 5:
            # Convert accent hue to RGB
            h = self.__accent_hue
            r, g, b = _hsv_to_rgb_scalar(h, 0.9, intensity / 255)
            color = np.array([int(r * 255), int(g * 255), int(b * 255)], dtype=np.uint8)

            # Horizontal bands
            for y in range(self.__height):
                if random.random() < 0.7:
                    frame[y] = color

        self._led_frame_player.play_frame(frame)

    def __render_data_rain(self):
        """Vertical streams of data — columns of flickering brightness."""
        frame = np.zeros((self.__height, self.__width, 3), dtype=np.uint8)

        # Each column has a random activity level
        for x in range(self.__width):
            if random.random() < 0.4:
                # Active column
                col_brightness = random.randint(80, 255)
                for y in range(self.__height):
                    if random.random() < 0.5:
                        v = random.randint(col_brightness // 3, col_brightness)
                        frame[y, x] = v
            else:
                # Sparse column
                num_dots = random.randint(0, 2)
                for _ in range(num_dots):
                    y = random.randint(0, self.__height - 1)
                    frame[y, x] = random.randint(20, 60)

        self._led_frame_player.play_frame(frame)

    @classmethod
    def get_id(cls) -> str:
        return 'ikeda'

    @classmethod
    def get_name(cls) -> str:
        return 'Ikeda'

    @classmethod
    def get_description(cls) -> str:
        return 'Data-driven minimalist light'


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
