import math
import numpy as np
import time

from pifi.config import Config
from pifi.logger import Logger
from pifi.led.ledframeplayer import LedFramePlayer
from pifi.screensaver.screensaver import Screensaver


class Boids(Screensaver):
    """
    Boids flocking simulation screensaver.

    Implements Craig Reynolds' flocking algorithm with three rules:
    1. Separation: Steer away from nearby boids to avoid crowding
    2. Alignment: Steer towards the average heading of nearby boids
    3. Cohesion: Steer towards the average position of nearby boids
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

        self.__positions = None
        self.__velocities = None

    def play(self):
        self.__logger.info("Starting Boids screensaver")
        self.__reset()

        max_ticks = Config.get('boids.max_ticks', 2000)
        tick = 0

        while tick < max_ticks:
            self.__tick()
            time.sleep(self.__get_tick_sleep())
            tick += 1

        self.__logger.info("Boids screensaver ended")

    def __reset(self):
        num_boids = Config.get('boids.num_boids', 15)

        # Initialize random positions across the display
        self.__positions = np.random.rand(num_boids, 2)
        self.__positions[:, 0] *= self.__width
        self.__positions[:, 1] *= self.__height

        # Initialize random velocities
        max_speed = self.__get_max_speed()
        angles = np.random.rand(num_boids) * 2 * math.pi
        speeds = np.random.rand(num_boids) * max_speed * 0.5 + max_speed * 0.5
        self.__velocities = np.column_stack([
            np.cos(angles) * speeds,
            np.sin(angles) * speeds
        ])

    def __tick(self):
        self.__update_velocities()
        self.__update_positions()
        self.__render()

    def __update_velocities(self):
        separation = self.__calculate_separation()
        alignment = self.__calculate_alignment()
        cohesion = self.__calculate_cohesion()

        sep_weight = Config.get('boids.separation_weight', 1.5)
        align_weight = Config.get('boids.alignment_weight', 1.0)
        coh_weight = Config.get('boids.cohesion_weight', 1.0)

        self.__velocities += (
            separation * sep_weight +
            alignment * align_weight +
            cohesion * coh_weight
        )

        # Clamp to max speed
        max_speed = self.__get_max_speed()
        speeds = np.linalg.norm(self.__velocities, axis=1, keepdims=True)
        speeds = np.maximum(speeds, 0.0001)  # Avoid division by zero
        scale = np.minimum(max_speed / speeds, 1.0)
        self.__velocities *= scale

    def __calculate_separation(self):
        """Steer away from nearby boids to avoid crowding."""
        num_boids = len(self.__positions)
        separation = np.zeros_like(self.__velocities)

        min_distance = Config.get('boids.min_distance', 2.0)

        for i in range(num_boids):
            diff = self.__positions[i] - self.__positions
            distances = np.linalg.norm(diff, axis=1)

            # Find boids that are too close (excluding self)
            mask = (distances > 0) & (distances < min_distance)

            if np.any(mask):
                # Steer away from close neighbors
                away = diff[mask] / distances[mask, np.newaxis]
                separation[i] = np.sum(away, axis=0)

        return separation * 0.1

    def __calculate_alignment(self):
        """Steer towards the average heading of nearby boids."""
        num_boids = len(self.__positions)
        alignment = np.zeros_like(self.__velocities)

        perception = self.__get_perception_radius()

        for i in range(num_boids):
            diff = self.__positions - self.__positions[i]
            distances = np.linalg.norm(diff, axis=1)

            # Find neighbors within perception radius (excluding self)
            mask = (distances > 0) & (distances < perception)

            if np.any(mask):
                # Average velocity of neighbors
                avg_velocity = np.mean(self.__velocities[mask], axis=0)
                alignment[i] = avg_velocity - self.__velocities[i]

        return alignment * 0.05

    def __calculate_cohesion(self):
        """Steer towards the average position of nearby boids."""
        num_boids = len(self.__positions)
        cohesion = np.zeros_like(self.__velocities)

        perception = self.__get_perception_radius()

        for i in range(num_boids):
            diff = self.__positions - self.__positions[i]
            distances = np.linalg.norm(diff, axis=1)

            # Find neighbors within perception radius (excluding self)
            mask = (distances > 0) & (distances < perception)

            if np.any(mask):
                # Steer towards center of mass of neighbors
                center = np.mean(self.__positions[mask], axis=0)
                cohesion[i] = center - self.__positions[i]

        return cohesion * 0.02

    def __update_positions(self):
        self.__positions += self.__velocities

        # Wrap around edges
        self.__positions[:, 0] = self.__positions[:, 0] % self.__width
        self.__positions[:, 1] = self.__positions[:, 1] % self.__height

    def __render(self):
        frame = np.zeros([self.__height, self.__width, 3], np.uint8)

        for i, pos in enumerate(self.__positions):
            x = int(pos[0]) % self.__width
            y = int(pos[1]) % self.__height

            # Color based on velocity direction (rainbow effect)
            vx, vy = self.__velocities[i]
            angle = math.atan2(vy, vx)
            hue = (angle + math.pi) / (2 * math.pi)  # Normalize to 0-1

            rgb = self.__hsv_to_rgb(hue, 1.0, 1.0)
            frame[y, x] = rgb

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
        return Config.get('boids.tick_sleep', 0.05)

    def __get_max_speed(self):
        return Config.get('boids.max_speed', 1.5)

    def __get_perception_radius(self):
        return Config.get('boids.perception_radius', 8.0)

    @classmethod
    def get_id(cls) -> str:
        return 'boids'

    @classmethod
    def get_name(cls) -> str:
        return 'Boids'

    @classmethod
    def get_description(cls) -> str:
        return 'Flocking simulation'
