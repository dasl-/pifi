import numpy as np
import random

from pifi.config import Config
from pifi.logger import Logger
from pifi.screensaver.screensaver import Screensaver


class Lenia(Screensaver):
    """
    Lenia — continuous cellular automaton.

    A generalization of Conway's Game of Life with continuous states,
    space, and time. Produces organic, lifelike creatures that move,
    grow, and interact. Uses ring-shaped convolution kernels and
    bell-curve growth functions.
    """

    def __init__(self, led_frame_player=None):
        super().__init__(led_frame_player)
        self.__logger = Logger().set_namespace(self.__class__.__name__)

        self.__width = Config.get_or_throw('leds.display_width')
        self.__height = Config.get_or_throw('leds.display_height')

    def _setup(self):
        self.__reset()

    def _tick(self):
        tick = self.get_last_tick()
        self.__step()

        # Check for extinction or stagnation
        if tick > 0 and tick % 40 == 0:
            self.__check_vitality()

        self.__render()

    def __reset(self):
        self.__grid = np.zeros((self.__height, self.__width), dtype=np.float64)
        self.__prev_mean = None
        self.__stagnant_count = 0

        # Pick a random creature preset — these are (R, mu, sigma, dt) combos
        # known to produce dynamic behavior. R is kernel radius.
        # Smaller R values work better on small grids.
        R_max = min(self.__width, self.__height) // 3
        self.__params = random.choice([
            # Orbium — classic glider, smooth and elegant
            {'R': min(7, R_max), 'mu': 0.15, 'sigma': 0.015, 'dt': 0.1, 'beta': [1]},
            # Geminium — splits and reforms
            {'R': min(6, R_max), 'mu': 0.14, 'sigma': 0.014, 'dt': 0.1, 'beta': [1]},
            # Smooth life-like — active, bubbly
            {'R': min(5, R_max), 'mu': 0.12, 'sigma': 0.018, 'dt': 0.15, 'beta': [1, 0.5]},
            # Active blobs — lots of motion
            {'R': min(6, R_max), 'mu': 0.13, 'sigma': 0.016, 'dt': 0.12, 'beta': [1]},
            # Pulsating rings
            {'R': min(8, R_max), 'mu': 0.17, 'sigma': 0.020, 'dt': 0.08, 'beta': [0.5, 1, 0.5]},
            # Worms — elongated moving structures
            {'R': min(5, R_max), 'mu': 0.10, 'sigma': 0.012, 'dt': 0.15, 'beta': [1, 0.7]},
        ])

        R = self.__params['R']
        beta = self.__params['beta']
        self.__dt = self.__params['dt']
        self.__mu = self.__params['mu']
        self.__sigma = self.__params['sigma']

        # Build the ring-shaped kernel in frequency domain for fast convolution.
        # The kernel is a series of concentric rings weighted by beta.
        self.__kernel_fft = self.__build_kernel_fft(R, beta)

        # Seed the grid with random blobs
        self.__seed_creatures(3)

        # Slowly rotating color palette
        self.__hue_base = random.random()

        self.__logger.info(
            f"Lenia params: R={R}, mu={self.__mu}, sigma={self.__sigma}, " +
            f"dt={self.__dt}, beta={beta}"
        )

    def __build_kernel_fft(self, R, beta):
        """Build ring kernel and return its FFT for convolution."""
        # Kernel is defined on the full grid with wrap-around
        # Create distance field from center
        cy, cx = self.__height // 2, self.__width // 2
        y = np.arange(self.__height) - cy
        x = np.arange(self.__width) - cx
        yy, xx = np.meshgrid(y, x, indexing='ij')
        dist = np.sqrt(xx ** 2 + yy ** 2)

        # Normalized distance (0 at center, 1 at radius R)
        r = dist / R

        # Multi-ring kernel: sum of bell curves at different radii
        num_rings = len(beta)
        kernel = np.zeros_like(dist)
        for i, b in enumerate(beta):
            # Ring center at (i + 0.5) / num_rings of the radius
            ring_center = (i + 0.5) / num_rings
            ring_width = 0.5 / num_rings
            kernel += b * np.exp(-((r - ring_center) / ring_width) ** 2 / 2)

        # Zero out beyond radius
        kernel[dist > R] = 0

        # Normalize
        total = kernel.sum()
        if total > 0:
            kernel /= total

        # FFT for fast convolution
        return np.fft.fft2(np.fft.fftshift(kernel))

    def __growth(self, potential):
        """Bell-curve growth function centered at mu with width sigma."""
        return 2 * np.exp(-((potential - self.__mu) ** 2) / (2 * self.__sigma ** 2)) - 1  # pyright: ignore[reportOperatorIssue]

    def __step(self):
        """One Lenia simulation step."""
        # Convolve grid with kernel using FFT
        grid_fft = np.fft.fft2(self.__grid)
        potential = np.real(np.fft.ifft2(grid_fft * self.__kernel_fft))

        # Apply growth function and update
        self.__grid = np.clip(self.__grid + self.__dt * self.__growth(potential), 0, 1)

    def __seed_creatures(self, num_creatures):
        """Place random blob creatures on the grid."""
        R = self.__params['R']
        for _ in range(num_creatures):
            cx = random.randint(R, self.__width - R - 1)  # pyright: ignore[reportArgumentType]
            cy = random.randint(R, self.__height - R - 1)  # pyright: ignore[reportArgumentType]
            # Random organic blob
            size = random.randint(max(2, R // 2), R)  # pyright: ignore[reportArgumentType, reportOperatorIssue]
            for dy in range(-size, size + 1):
                for dx in range(-size, size + 1):
                    dist = (dx ** 2 + dy ** 2) ** 0.5
                    if dist <= size:
                        ny = (cy + dy) % self.__height
                        nx = (cx + dx) % self.__width
                        # Smooth falloff from center
                        val = (1 - dist / size) * random.uniform(0.5, 1.0)
                        self.__grid[ny, nx] = max(self.__grid[ny, nx], val)

    def __check_vitality(self):
        """Re-seed if the grid has gone dead or stagnant."""
        # 0.05 is the activity threshold — Lenia values stay close to 0
        # outside live regions, so > 0.05 reliably picks out "alive" cells.
        alive = (self.__grid > 0.05).sum()
        total = self.__width * self.__height
        mean = float(self.__grid.mean())

        # Extinction: fewer than 2% of cells active means the pattern
        # has died out and won't recover on its own — re-seed.
        if alive < total * 0.02:
            self.__logger.info("Lenia: extinction detected, re-seeding")
            self.__seed_creatures(3)
            self.__stagnant_count = 0
            self.__prev_mean = None
            return

        # Check for stagnation (frozen pattern)
        if self.__prev_mean is not None:
            delta = abs(mean - self.__prev_mean)
            if delta < 0.0002:
                self.__stagnant_count += 1
            else:
                self.__stagnant_count = 0

            if self.__stagnant_count >= 3:
                self.__logger.info("Lenia: stagnation detected, adding perturbation")
                # Add a new creature to disrupt the static pattern
                self.__seed_creatures(2)
                self.__stagnant_count = 0

        self.__prev_mean = mean

    def __render(self):
        hue = (self.__hue_base + self.__grid * 0.3) % 1.0
        sat = np.where(self.__grid > 0.05, 0.75, 0.2)
        val = np.where(self.__grid > 0.05, 0.2 + self.__grid * 0.8, self.__grid * 0.1)

        frame = self.__hsv_to_rgb_vec(hue, sat, val)
        self._led_frame_player.play_frame(frame)

    @staticmethod
    def __hsv_to_rgb_vec(h, s, v):
        """Vectorized HSV to RGB. Returns [H, W, 3] uint8."""
        i = (h * 6.0).astype(int) % 6
        f = h * 6.0 - np.floor(h * 6.0)
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
        return 'lenia'

    @classmethod
    def get_name(cls) -> str:
        return 'Lenia'

    @classmethod
    def get_description(cls) -> str:
        return 'Continuous cellular automaton with lifelike creatures'
