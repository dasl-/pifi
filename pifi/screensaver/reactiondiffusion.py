import numpy as np
import random

from pifi.config import Config
from pifi.logger import Logger
from pifi.screensaver.screensaver import Screensaver


class ReactionDiffusion(Screensaver):
    """
    Gray-Scott reaction-diffusion simulation.

    Creates organic, coral-like patterns that slowly evolve.
    Two chemicals interact and diffuse, creating spots, stripes,
    and other biological-looking patterns.
    """

    def __init__(self, led_frame_player=None):
        super().__init__(led_frame_player)
        self.__logger = Logger().set_namespace(self.__class__.__name__)

        self.__width = Config.get_or_throw('leds.display_width')
        self.__height = Config.get_or_throw('leds.display_height')

        # Chemical concentrations
        self.__A = None  # Chemical A
        self.__B = None  # Chemical B

    def _setup(self):
        self.__reset()

    def _tick(self):
        # Run multiple simulation steps per frame for faster evolution
        steps_per_frame = Config.get('screensavers.configs.reactiondiffusion.steps_per_frame', 5)
        for _ in range(steps_per_frame):
            self.__simulate_step()

        # Detect if pattern has settled into a fixed point and perturb it
        if self.__time > 0 and self.__time % 30 == 0:
            self.__check_and_perturb()

        self.__render()

    def __reset(self):
        self.__time = 0
        self.__prev_B_mean = None

        # Initialize with A=1 everywhere, B=0 with some seed points
        self.__A = np.ones((self.__height, self.__width), dtype=np.float32)
        self.__B = np.zeros((self.__height, self.__width), dtype=np.float32)

        # Seed some B in random spots
        num_seeds = Config.get('screensavers.configs.reactiondiffusion.num_seeds', 5)
        for _ in range(num_seeds):
            cx = random.randint(1, self.__width - 2)
            cy = random.randint(1, self.__height - 2)
            radius = random.randint(1, 2)
            y_lo = max(0, cy - radius)
            y_hi = min(self.__height, cy + radius + 1)
            x_lo = max(0, cx - radius)
            x_hi = min(self.__width, cx + radius + 1)
            self.__B[y_lo:y_hi, x_lo:x_hi] = 1.0

        # Parameters tuned for small grids — these stay dynamic longer.
        # Higher feed rates push more chemical A in, preventing B from
        # dying out. Slightly higher dB helps patterns spread across the
        # small grid before settling.
        self.__params = random.choice([
            # Mitosis — cells divide and keep splitting
            {'f': 0.037, 'k': 0.064, 'dA': 1.0, 'dB': 0.5},
            # Moving spots — solitons that wander
            {'f': 0.030, 'k': 0.060, 'dA': 1.0, 'dB': 0.5},
            # Worms — wiggly stripes
            {'f': 0.040, 'k': 0.060, 'dA': 1.0, 'dB': 0.5},
            # Chaos — constantly shifting
            {'f': 0.026, 'k': 0.052, 'dA': 1.0, 'dB': 0.5},
            # Waves — pulsing rings
            {'f': 0.014, 'k': 0.045, 'dA': 1.0, 'dB': 0.5},
        ])

        # Slowly rotating hue for color variation over time
        self.__hue_base = random.random()

        self.__logger.info(f"Reaction Diffusion params: f={self.__params['f']}, k={self.__params['k']}")

    def __check_and_perturb(self):
        """Detect stagnation and inject noise to keep things dynamic."""
        b_mean = float(self.__B.mean())
        if self.__prev_B_mean is not None:
            delta = abs(b_mean - self.__prev_B_mean)
            if delta < 0.0005:
                # System has settled — inject a band of noise to shake it up
                axis = random.choice(['h', 'v'])
                if axis == 'h':
                    y = random.randint(0, self.__height - 1)
                    thickness = random.randint(1, max(1, self.__height // 4))
                    y_lo = max(0, y - thickness // 2)
                    y_hi = min(self.__height, y_lo + thickness)
                    self.__B[y_lo:y_hi, :] = np.random.uniform(0.2, 1.0,
                        (y_hi - y_lo, self.__width)).astype(np.float32)
                else:
                    x = random.randint(0, self.__width - 1)
                    thickness = random.randint(1, max(1, self.__width // 4))
                    x_lo = max(0, x - thickness // 2)
                    x_hi = min(self.__width, x_lo + thickness)
                    self.__B[:, x_lo:x_hi] = np.random.uniform(0.2, 1.0,
                        (self.__height, x_hi - x_lo)).astype(np.float32)
        self.__prev_B_mean = b_mean

    def __simulate_step(self):
        f = self.__params['f']
        k = self.__params['k']
        dA = self.__params['dA']
        dB = self.__params['dB']

        laplacian_A = self.__laplacian(self.__A)
        laplacian_B = self.__laplacian(self.__B)

        AB2 = self.__A * self.__B * self.__B

        self.__A += dA * laplacian_A - AB2 + f * (1 - self.__A)
        self.__B += dB * laplacian_B + AB2 - (k + f) * self.__B

        np.clip(self.__A, 0, 1, out=self.__A)
        np.clip(self.__B, 0, 1, out=self.__B)

    def __laplacian(self, grid):
        """Compute discrete Laplacian with wrap-around boundaries."""
        # Use roll instead of pad+slice — avoids allocation on small grids
        return (
            np.roll(grid, -1, axis=0) +
            np.roll(grid, 1, axis=0) +
            np.roll(grid, -1, axis=1) +
            np.roll(grid, 1, axis=1) -
            4 * grid
        )

    def __render(self):
        b = self.__B
        hue = (self.__hue_base + self.__time * 0.002) % 1.0

        # Vectorized HSV→RGB: pattern pixels get hue-shifted color,
        # background gets a subtle glow.
        h = np.where(b > 0.1, (hue + b * 0.2) % 1.0, hue)
        s = np.where(b > 0.1, 0.7, 0.3)
        v = np.where(b > 0.1, 0.3 + b * 0.7, (1 - self.__A) * 0.15)

        frame = self.__hsv_to_rgb_vec(h, s, v)
        self._led_frame_player.play_frame(frame)

    @staticmethod
    def __hsv_to_rgb_vec(h, s, v):
        """Vectorized HSV to RGB conversion. Returns [H, W, 3] uint8 array."""
        i = (h * 6.0).astype(int) % 6
        f = (h * 6.0) - (h * 6.0).astype(int)
        p = v * (1.0 - s)
        q = v * (1.0 - s * f)
        t = v * (1.0 - s * (1.0 - f))

        r = np.zeros_like(h)
        g = np.zeros_like(h)
        bl = np.zeros_like(h)

        m0 = i == 0; r[m0] = v[m0]; g[m0] = t[m0]; bl[m0] = p[m0]
        m1 = i == 1; r[m1] = q[m1]; g[m1] = v[m1]; bl[m1] = p[m1]
        m2 = i == 2; r[m2] = p[m2]; g[m2] = v[m2]; bl[m2] = t[m2]
        m3 = i == 3; r[m3] = p[m3]; g[m3] = q[m3]; bl[m3] = v[m3]
        m4 = i == 4; r[m4] = t[m4]; g[m4] = p[m4]; bl[m4] = v[m4]
        m5 = i == 5; r[m5] = v[m5]; g[m5] = p[m5]; bl[m5] = q[m5]

        return np.stack([r * 255, g * 255, bl * 255], axis=-1).astype(np.uint8)

    @classmethod
    def get_id(cls) -> str:
        return 'reactiondiffusion'

    @classmethod
    def get_name(cls) -> str:
        return 'Reaction Diffusion'

    @classmethod
    def get_description(cls) -> str:
        return 'Gray-Scott organic patterns'
