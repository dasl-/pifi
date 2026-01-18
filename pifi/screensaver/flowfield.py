import math
import numpy as np
import time
import random

from pifi.config import Config
from pifi.logger import Logger
from pifi.led.ledframeplayer import LedFramePlayer
from pifi.screensaver.screensaver import Screensaver


class FlowField(Screensaver):
    """
    Particles flowing through a Perlin noise vector field.

    Creates organic, wind-like movement as particles follow
    smoothly varying directional gradients.
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

        # Flow field and particles
        self.__particles = []
        self.__buffer = None
        self.__time = 0

        # Noise parameters
        self.__noise_scale = 0.15
        self.__noise_z = 0  # For animating the field

        # Precompute permutation table for Perlin noise
        self.__perm = list(range(256))
        random.shuffle(self.__perm)
        self.__perm += self.__perm  # Double it for overflow

    def play(self):
        self.__logger.info("Starting Flow Field screensaver")
        self.__reset()

        max_ticks = Config.get('flowfield.max_ticks', 2500)
        tick = 0

        while tick < max_ticks:
            self.__tick()
            time.sleep(self.__get_tick_sleep())
            tick += 1

        self.__logger.info("Flow Field screensaver ended")

    def __reset(self):
        self.__buffer = np.zeros((self.__height, self.__width, 3), dtype=np.float32)
        self.__time = 0
        self.__noise_z = random.random() * 100

        # Create particles
        num_particles = Config.get('flowfield.num_particles', 50)
        self.__particles = []
        for _ in range(num_particles):
            self.__particles.append(self.__create_particle())

        # Random color palette for this session
        self.__hue_base = random.random()
        self.__hue_range = random.uniform(0.1, 0.3)

    def __create_particle(self):
        return {
            'x': random.random() * self.__width,
            'y': random.random() * self.__height,
            'hue': random.random(),
        }

    def __tick(self):
        # Fade buffer
        fade = Config.get('flowfield.fade', 0.95)
        self.__buffer *= fade

        # Slowly evolve the flow field
        self.__noise_z += 0.002

        # Update and draw particles
        for particle in self.__particles:
            # Get flow direction from noise
            angle = self.__noise(
                particle['x'] * self.__noise_scale,
                particle['y'] * self.__noise_scale,
                self.__noise_z
            ) * math.pi * 4  # Map to full rotation

            # Move particle
            speed = Config.get('flowfield.speed', 0.5)
            particle['x'] += math.cos(angle) * speed
            particle['y'] += math.sin(angle) * speed

            # Wrap around edges
            if particle['x'] < 0:
                particle['x'] += self.__width
            elif particle['x'] >= self.__width:
                particle['x'] -= self.__width
            if particle['y'] < 0:
                particle['y'] += self.__height
            elif particle['y'] >= self.__height:
                particle['y'] -= self.__height

            # Draw particle
            ix = int(particle['x'])
            iy = int(particle['y'])
            if 0 <= ix < self.__width and 0 <= iy < self.__height:
                # Color based on particle's hue + global palette
                hue = (self.__hue_base + particle['hue'] * self.__hue_range) % 1.0
                color = self.__hsv_to_rgb(hue, 0.8, 1.0)

                # Additive blend
                self.__buffer[iy, ix, 0] += color[0] * 0.3
                self.__buffer[iy, ix, 1] += color[1] * 0.3
                self.__buffer[iy, ix, 2] += color[2] * 0.3

        self.__render()
        self.__time += 1

    def __render(self):
        frame = np.clip(self.__buffer, 0, 255).astype(np.uint8)
        self.__led_frame_player.play_frame(frame)

    def __noise(self, x, y, z):
        """Simple Perlin-like noise implementation."""
        # Integer coordinates
        xi = int(x) & 255
        yi = int(y) & 255
        zi = int(z) & 255

        # Fractional coordinates
        xf = x - int(x)
        yf = y - int(y)
        zf = z - int(z)

        # Fade curves
        u = self.__fade(xf)
        v = self.__fade(yf)
        w = self.__fade(zf)

        # Hash coordinates
        p = self.__perm
        aaa = p[p[p[xi] + yi] + zi]
        aba = p[p[p[xi] + yi + 1] + zi]
        aab = p[p[p[xi] + yi] + zi + 1]
        abb = p[p[p[xi] + yi + 1] + zi + 1]
        baa = p[p[p[xi + 1] + yi] + zi]
        bba = p[p[p[xi + 1] + yi + 1] + zi]
        bab = p[p[p[xi + 1] + yi] + zi + 1]
        bbb = p[p[p[xi + 1] + yi + 1] + zi + 1]

        # Gradient dot products and interpolation
        x1 = self.__lerp(self.__grad(aaa, xf, yf, zf), self.__grad(baa, xf - 1, yf, zf), u)
        x2 = self.__lerp(self.__grad(aba, xf, yf - 1, zf), self.__grad(bba, xf - 1, yf - 1, zf), u)
        y1 = self.__lerp(x1, x2, v)

        x1 = self.__lerp(self.__grad(aab, xf, yf, zf - 1), self.__grad(bab, xf - 1, yf, zf - 1), u)
        x2 = self.__lerp(self.__grad(abb, xf, yf - 1, zf - 1), self.__grad(bbb, xf - 1, yf - 1, zf - 1), u)
        y2 = self.__lerp(x1, x2, v)

        return (self.__lerp(y1, y2, w) + 1) / 2  # Normalize to 0-1

    def __fade(self, t):
        return t * t * t * (t * (t * 6 - 15) + 10)

    def __lerp(self, a, b, t):
        return a + t * (b - a)

    def __grad(self, hash, x, y, z):
        h = hash & 15
        u = x if h < 8 else y
        v = y if h < 4 else (x if h == 12 or h == 14 else z)
        return (u if (h & 1) == 0 else -u) + (v if (h & 2) == 0 else -v)

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

        return [r * 255, g * 255, b * 255]

    def __get_tick_sleep(self):
        return Config.get('flowfield.tick_sleep', 0.03)

    @classmethod
    def get_id(cls) -> str:
        return 'flowfield'

    @classmethod
    def get_name(cls) -> str:
        return 'Flow Field'

    @classmethod
    def get_description(cls) -> str:
        return 'Particles flowing through noise'
