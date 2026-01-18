import numpy as np
import time
import random

from pifi.config import Config
from pifi.logger import Logger
from pifi.led.ledframeplayer import LedFramePlayer
from pifi.screensaver.screensaver import Screensaver


class ReactionDiffusion(Screensaver):
    """
    Gray-Scott reaction-diffusion simulation.

    Creates organic, coral-like patterns that slowly evolve.
    Two chemicals interact and diffuse, creating spots, stripes,
    and other biological-looking patterns.
    """

    def __init__(self, led_frame_player=None):
        self.__logger = Logger().set_namespace(self.__class__.__name__)

        if led_frame_player is None:
            self.__led_frame_player = LedFramePlayer()
        else:
            self.__led_frame_player = led_frame_player

        self.__width = Config.get_or_throw('leds.display_width')
        self.__height = Config.get_or_throw('leds.display_height')

        # Chemical concentrations
        self.__A = None  # Chemical A
        self.__B = None  # Chemical B

        self.__time = 0

    def play(self):
        self.__logger.info("Starting Reaction Diffusion screensaver")
        self.__reset()

        max_ticks = Config.get('reactiondiffusion.max_ticks', 2000)
        tick = 0

        while tick < max_ticks:
            self.__tick()
            time.sleep(self.__get_tick_sleep())
            tick += 1

        self.__logger.info("Reaction Diffusion screensaver ended")

    def __reset(self):
        self.__time = 0

        # Initialize with A=1 everywhere, B=0 with some seed points
        self.__A = np.ones((self.__height, self.__width), dtype=np.float32)
        self.__B = np.zeros((self.__height, self.__width), dtype=np.float32)

        # Seed some B in random spots - more seeds for faster start
        num_seeds = Config.get('reactiondiffusion.num_seeds', 8)
        for _ in range(num_seeds):
            cx = random.randint(2, self.__width - 3)
            cy = random.randint(2, self.__height - 3)
            radius = random.randint(1, 3)
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    if 0 <= cy + dy < self.__height and 0 <= cx + dx < self.__width:
                        self.__B[cy + dy, cx + dx] = 1.0

        # Pick random parameters that produce interesting patterns
        # Prefer more dynamic/chaotic patterns that keep evolving
        self.__params = random.choice([
            # Mitosis (cell division) - very dynamic
            {'f': 0.0367, 'k': 0.0649, 'dA': 1.0, 'dB': 0.5},
            # Coral growth - actively growing
            {'f': 0.0545, 'k': 0.062, 'dA': 1.0, 'dB': 0.5},
            # Pulsing solitons - constantly moving
            {'f': 0.03, 'k': 0.062, 'dA': 1.0, 'dB': 0.5},
            # Worms - wiggly moving patterns
            {'f': 0.038, 'k': 0.061, 'dA': 1.0, 'dB': 0.5},
            # Bubbling chaos
            {'f': 0.026, 'k': 0.051, 'dA': 1.0, 'dB': 0.5},
        ])

        # Color palette
        self.__hue = random.random()

        self.__logger.info(f"Reaction Diffusion params: f={self.__params['f']}, k={self.__params['k']}")

    def __tick(self):
        # Run multiple simulation steps per frame for faster evolution
        steps_per_frame = Config.get('reactiondiffusion.steps_per_frame', 10)
        for _ in range(steps_per_frame):
            self.__simulate_step()

        # Periodically inject new seeds to keep evolution going
        inject_interval = Config.get('reactiondiffusion.inject_interval', 100)
        if self.__time > 0 and self.__time % inject_interval == 0:
            self.__inject_seed()

        self.__render()
        self.__time += 1

    def __inject_seed(self):
        """Inject a new seed to keep the pattern evolving."""
        cx = random.randint(2, self.__width - 3)
        cy = random.randint(2, self.__height - 3)
        radius = random.randint(1, 2)
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                if 0 <= cy + dy < self.__height and 0 <= cx + dx < self.__width:
                    self.__B[cy + dy, cx + dx] = 1.0

    def __simulate_step(self):
        f = self.__params['f']  # Feed rate
        k = self.__params['k']  # Kill rate
        dA = self.__params['dA']  # Diffusion rate for A
        dB = self.__params['dB']  # Diffusion rate for B

        # Compute Laplacian using convolution
        # Simple 3x3 kernel: neighbors - 4*center
        laplacian_A = self.__laplacian(self.__A)
        laplacian_B = self.__laplacian(self.__B)

        # Reaction-diffusion equations
        AB2 = self.__A * self.__B * self.__B

        # Update concentrations
        self.__A += dA * laplacian_A - AB2 + f * (1 - self.__A)
        self.__B += dB * laplacian_B + AB2 - (k + f) * self.__B

        # Clamp values
        self.__A = np.clip(self.__A, 0, 1)
        self.__B = np.clip(self.__B, 0, 1)

    def __laplacian(self, grid):
        """Compute discrete Laplacian using convolution."""
        # Pad with wrap-around for continuous boundaries
        padded = np.pad(grid, 1, mode='wrap')

        # 5-point stencil Laplacian
        laplacian = (
            padded[:-2, 1:-1] +  # up
            padded[2:, 1:-1] +   # down
            padded[1:-1, :-2] +  # left
            padded[1:-1, 2:] -   # right
            4 * grid
        )

        return laplacian

    def __render(self):
        frame = np.zeros((self.__height, self.__width, 3), dtype=np.uint8)

        # Color based on B concentration
        # B=0 is background, B=1 is pattern
        for y in range(self.__height):
            for x in range(self.__width):
                b = self.__B[y, x]

                if b > 0.1:
                    # Pattern color
                    hue = (self.__hue + b * 0.2) % 1.0
                    sat = 0.7
                    val = 0.3 + b * 0.7
                    frame[y, x] = self.__hsv_to_rgb(hue, sat, val)
                else:
                    # Background - subtle glow based on A
                    a = self.__A[y, x]
                    val = (1 - a) * 0.15
                    frame[y, x] = self.__hsv_to_rgb(self.__hue, 0.3, val)

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
        return Config.get('reactiondiffusion.tick_sleep', 0.05)

    @classmethod
    def get_id(cls) -> str:
        return 'reactiondiffusion'

    @classmethod
    def get_name(cls) -> str:
        return 'Reaction Diffusion'

    @classmethod
    def get_description(cls) -> str:
        return 'Gray-Scott organic patterns'
