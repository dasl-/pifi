import numpy as np
import time
import random

from pifi.config import Config
from pifi.logger import Logger
from pifi.led.ledframeplayer import LedFramePlayer
from pifi.screensaver.screensaver import Screensaver


class MatrixRain(Screensaver):
    """
    Matrix digital rain screensaver.

    Simulates the iconic falling green characters from The Matrix.
    Characters fall in columns with varying speeds, with bright
    heads and fading trails.
    """

    # Characters to display (katakana-inspired, but we just use brightness levels)
    # On a small LED matrix, we show the effect rather than actual characters

    def __init__(self, led_frame_player=None):
        super().__init__(led_frame_player)
        self.__logger = Logger().set_namespace(self.__class__.__name__)

        if led_frame_player is None:
            self.__led_frame_player = LedFramePlayer()
        else:
            self.__led_frame_player = led_frame_player

        self.__width = Config.get_or_throw('leds.display_width')
        self.__height = Config.get_or_throw('leds.display_height')

        # Each column has: [y_position, speed, length, active]
        self.__drops = []

        # The frame buffer for trails (stores brightness values)
        self.__trail_buffer = None

    def play(self):
        self.__logger.info("Starting Matrix Rain screensaver")
        self.__reset()

        max_ticks = Config.get('matrix_rain.max_ticks', 3000)
        tick = 0

        while tick < max_ticks:
            self.__tick()
            time.sleep(self.__get_tick_sleep())
            tick += 1

        self.__logger.info("Matrix Rain screensaver ended")

    def __reset(self):
        self.__drops = []
        self.__trail_buffer = np.zeros((self.__height, self.__width), dtype=np.float32)

        # Initialize some drops
        for x in range(self.__width):
            if random.random() < 0.3:
                self.__add_drop(x)

    def __add_drop(self, x, from_top=True):
        """Add a new raindrop in column x."""
        min_speed = Config.get('matrix_rain.min_speed', 0.2)
        max_speed = Config.get('matrix_rain.max_speed', 0.8)
        min_length = Config.get('matrix_rain.min_length', 4)
        max_length = Config.get('matrix_rain.max_length', 12)

        speed = random.uniform(min_speed, max_speed)
        length = random.randint(min_length, min(max_length, self.__height))

        if from_top:
            y = random.uniform(-length, 0)
        else:
            y = random.uniform(-length, self.__height)

        self.__drops.append({
            'x': x,
            'y': y,
            'speed': speed,
            'length': length,
            'active': True
        })

    def __tick(self):
        fade_rate = Config.get('matrix_rain.fade_rate', 0.85)
        spawn_rate = Config.get('matrix_rain.spawn_rate', 0.08)

        # Fade existing trails
        self.__trail_buffer *= fade_rate

        # Update drops
        active_columns = set()
        new_drops = []

        for drop in self.__drops:
            drop['y'] += drop['speed']
            active_columns.add(drop['x'])

            # Check if drop is still visible
            head_y = int(drop['y'])
            tail_y = head_y - drop['length']

            if tail_y < self.__height:
                new_drops.append(drop)

                # Draw the drop head (brightest point)
                if 0 <= head_y < self.__height:
                    self.__trail_buffer[head_y, drop['x']] = 1.0

                # Draw trail with gradient
                for i in range(1, drop['length']):
                    trail_y = head_y - i
                    if 0 <= trail_y < self.__height:
                        # Brightness decreases along trail
                        brightness = 1.0 - (i / drop['length'])
                        brightness *= 0.7  # Trail is dimmer than head
                        self.__trail_buffer[trail_y, drop['x']] = max(
                            self.__trail_buffer[trail_y, drop['x']],
                            brightness
                        )

        self.__drops = new_drops

        # Spawn new drops in empty columns
        for x in range(self.__width):
            if x not in active_columns and random.random() < spawn_rate:
                self.__add_drop(x)

        self.__render()

    def __render(self):
        frame = np.zeros([self.__height, self.__width, 3], np.uint8)

        color_mode = Config.get('matrix_rain.color_mode', 'green')

        if color_mode == 'green':
            # Classic green matrix
            # Bright heads are white-green, trails are green
            for y in range(self.__height):
                for x in range(self.__width):
                    b = self.__trail_buffer[y, x]
                    if b > 0.01:
                        if b > 0.9:
                            # Bright head: white-green
                            frame[y, x] = [180, 255, 180]
                        elif b > 0.7:
                            # Near head: bright green
                            frame[y, x] = [0, int(b * 255), 0]
                        else:
                            # Trail: darker green
                            green = int(b * 200)
                            frame[y, x] = [0, green, int(green * 0.2)]

        elif color_mode == 'rainbow':
            # Rainbow variation - each column has a different hue
            for y in range(self.__height):
                for x in range(self.__width):
                    b = self.__trail_buffer[y, x]
                    if b > 0.01:
                        hue = (x / self.__width) % 1.0
                        if b > 0.9:
                            # Bright head
                            rgb = self.__hsv_to_rgb(hue, 0.3, 1.0)
                        else:
                            rgb = self.__hsv_to_rgb(hue, 0.9, b)
                        frame[y, x] = rgb

        elif color_mode == 'blue':
            # Blue/cyan variation
            for y in range(self.__height):
                for x in range(self.__width):
                    b = self.__trail_buffer[y, x]
                    if b > 0.01:
                        if b > 0.9:
                            frame[y, x] = [200, 255, 255]
                        elif b > 0.7:
                            frame[y, x] = [0, int(b * 200), int(b * 255)]
                        else:
                            blue = int(b * 200)
                            frame[y, x] = [0, int(blue * 0.4), blue]

        else:  # 'white'
            # Monochrome white
            for y in range(self.__height):
                for x in range(self.__width):
                    b = self.__trail_buffer[y, x]
                    if b > 0.01:
                        intensity = int(b * 255)
                        frame[y, x] = [intensity, intensity, intensity]

        self.__led_frame_player.play_frame(frame)

    def __hsv_to_rgb(self, h, s, v):
        """Convert HSV color to RGB."""
        if s == 0.0:
            return [int(v * 255)] * 3

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
        return Config.get('matrix_rain.tick_sleep', 0.05)

    @classmethod
    def get_id(cls) -> str:
        return 'matrix_rain'

    @classmethod
    def get_name(cls) -> str:
        return 'Matrix Rain'

    @classmethod
    def get_description(cls) -> str:
        return 'Falling green characters'
