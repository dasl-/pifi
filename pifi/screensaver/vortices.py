import numpy as np

from pifi.config import Config
from pifi.screensaver.screensaver import Screensaver


class Vortices(Screensaver):
    """
    Descartes' Theory of Vortices.

    Packed circles of varying sizes fill the display, each containing
    concentric swirling rings — inspired by the Principia Philosophiae
    illustrations of cosmic vortices filling all of space. Dark gaps
    outline each vortex cell while matter spirals within.
    """

    TINTS = [
        (0.80, 0.55, 0.35),  # Warm amber/sepia
        (0.40, 0.55, 0.80),  # Cool blue
        (0.75, 0.70, 0.65),  # Neutral cream/parchment
        (0.55, 0.30, 0.20),  # Brown/umber
        (0.50, 0.65, 0.80),  # Pale blue
    ]

    def __init__(self, led_frame_player=None):
        super().__init__(led_frame_player)
        self.__width = Config.get_or_throw('leds.display_width')
        self.__height = Config.get_or_throw('leds.display_height')

    def _setup(self):
        self.__time = 0.0
        w, h = self.__width, self.__height

        circles = self.__pack_circles(w, h)
        n = len(circles)
        self.__num_circles = n

        cx = np.array([c[0] for c in circles])
        cy = np.array([c[1] for c in circles])
        radii = np.array([c[2] for c in circles])
        self.__cx = cx
        self.__cy = cy
        self.__radii = radii

        # Per-circle animation
        self.__rotation_speed = (
            np.random.uniform(0.4, 1.8, n) * np.random.choice([-1, 1], n)
        )
        self.__num_rings = np.clip(radii * 1.0, 2, 8)
        self.__spiral_factor = np.random.uniform(0.3, 1.2, n)

        # Per-circle color
        tint_idx = np.random.randint(0, len(self.TINTS), n)
        self.__tint = np.array([self.TINTS[i] for i in tint_idx])

        # Build pixel-to-circle maps
        gy, gx = np.mgrid[0:h, 0:w].astype(np.float64)
        px, py = gx.ravel(), gy.ravel()
        num_px = len(px)

        circle_map = np.full(num_px, -1, dtype=np.int32)
        norm_dist = np.zeros(num_px, dtype=np.float64)
        angle = np.zeros(num_px, dtype=np.float64)

        # Assign pixels to circles (largest placed first, gets priority)
        for i in range(n):
            dx = px - cx[i]
            dy = py - cy[i]
            dist = np.sqrt(dx ** 2 + dy ** 2)
            assign = (dist < radii[i]) & (circle_map == -1)
            circle_map[assign] = i
            norm_dist[assign] = dist[assign] / radii[i]
            angle[assign] = np.arctan2(dy[assign], dx[assign])

        self.__circle_map = circle_map.reshape(h, w)
        self.__norm_dist = norm_dist.reshape(h, w)
        self.__angle = angle.reshape(h, w)
        self.__in_circle = self.__circle_map >= 0

    def __pack_circles(self, w, h):
        """Greedy circle packing: largest-fitting-gap first."""
        circles = []
        min_radius = max(0.7, min(w, h) * 0.025)
        max_radius = min(w, h) * 0.38
        gap = 0.5
        num_attempts = 500
        max_circles = 120

        for _ in range(max_circles):
            cx = np.random.uniform(-1, w + 1, num_attempts)
            cy = np.random.uniform(-1, h + 1, num_attempts)

            if circles:
                existing = np.array(circles)
                dx = cx[:, np.newaxis] - existing[:, 0]
                dy = cy[:, np.newaxis] - existing[:, 1]
                edge_dist = np.sqrt(dx ** 2 + dy ** 2) - existing[:, 2]
                max_r = np.min(edge_dist, axis=1) - gap
            else:
                max_r = np.full(num_attempts, max_radius)

            max_r = np.minimum(max_r, max_radius)
            valid = max_r >= min_radius

            if not np.any(valid):
                break

            best = np.argmax(np.where(valid, max_r, -1))
            circles.append((cx[best], cy[best], max_r[best]))

        return circles

    def _tick(self, tick):
        self.__time += 0.02
        t = self.__time
        h, w = self.__height, self.__width

        if self.__num_circles == 0:
            self._led_frame_player.play_frame(np.zeros((h, w, 3), dtype=np.uint8))
            return

        # Safe index for array lookups (-1 clipped to 0, masked out later)
        cids = np.clip(self.__circle_map, 0, self.__num_circles - 1)
        nd = self.__norm_dist
        ang = self.__angle

        # Spiral ring pattern
        rings = self.__num_rings[cids]
        rot = (self.__rotation_speed * t)[cids]
        spf = self.__spiral_factor[cids]

        phase = nd * rings * 2 * np.pi - ang * spf + rot
        pattern = 0.5 + 0.4 * np.cos(phase)

        # Bright outline ring near edge
        outline = np.exp(-((nd - 0.85) ** 2) / 0.008) * 0.5

        # Center dot
        center = np.exp(-(nd ** 2) / 0.015) * 0.6

        brightness = pattern + outline + center

        # Apply per-circle tint
        tint = self.__tint[cids]
        r = tint[..., 0] * brightness
        g = tint[..., 1] * brightness
        b = tint[..., 2] * brightness

        mask = self.__in_circle
        frame = np.stack([
            np.where(mask, np.clip(r * 255, 0, 255), 0).astype(np.uint8),
            np.where(mask, np.clip(g * 255, 0, 255), 0).astype(np.uint8),
            np.where(mask, np.clip(b * 255, 0, 255), 0).astype(np.uint8),
        ], axis=-1)

        self._led_frame_player.play_frame(frame)

    @classmethod
    def get_id(cls) -> str:
        return 'vortices'

    @classmethod
    def get_name(cls) -> str:
        return 'Vortices'

    @classmethod
    def get_description(cls) -> str:
        return "Descartes' cosmic vortex theory"
