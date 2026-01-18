import math
import numpy as np
import time

from pifi.config import Config
from pifi.logger import Logger
from pifi.led.ledframeplayer import LedFramePlayer
from pifi.screensaver.screensaver import Screensaver


class CosmicDream(Screensaver):
    """
    A hypnotic, psychedelic screensaver that layers multiple visual dimensions:

    - Plasma waves: Classic demoscene sine interference patterns
    - Flow field particles: Organic noise-driven motion with trails
    - Breathing geometry: Pulsing sacred geometry shapes
    - Color cycling: Multiple hue rotations at different speeds
    - Depth layers: Parallax effect with different time scales

    The result is a mesmerizing, ever-evolving visual that never repeats.
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

        # Pre-compute coordinate grids for plasma
        self.__x_grid, self.__y_grid = np.meshgrid(
            np.arange(self.__width),
            np.arange(self.__height)
        )
        self.__x_norm = self.__x_grid / max(self.__width, 1)
        self.__y_norm = self.__y_grid / max(self.__height, 1)

        # Particle system state
        self.__particles = None
        self.__particle_trails = None

        # Noise field (simplex-like via sine combinations)
        self.__noise_offsets = None

        # Time tracking for animations
        self.__start_time = None
        self.__frame_count = 0

    def play(self):
        self.__logger.info("Starting CosmicDream screensaver")
        self.__reset()

        max_ticks = Config.get('cosmicdream.max_ticks', 3000)
        tick = 0

        while tick < max_ticks:
            self.__tick()
            time.sleep(self.__get_tick_sleep())
            tick += 1

        self.__logger.info("CosmicDream screensaver ended")

    def __reset(self):
        self.__start_time = time.time()
        self.__frame_count = 0

        # Initialize particles for flow field
        num_particles = Config.get('cosmicdream.num_particles', 20)
        self.__particles = np.random.rand(num_particles, 2)
        self.__particles[:, 0] *= self.__width
        self.__particles[:, 1] *= self.__height

        # Trail buffer: stores previous positions for motion blur
        trail_length = Config.get('cosmicdream.trail_length', 8)
        self.__particle_trails = np.zeros((num_particles, trail_length, 2))
        for i in range(trail_length):
            self.__particle_trails[:, i, :] = self.__particles

        # Random offsets for multi-octave noise
        self.__noise_offsets = np.random.rand(6) * 1000

    def __tick(self):
        t = time.time() - self.__start_time
        self.__frame_count += 1

        # Create the layered frame
        frame = self.__render_plasma_layer(t)
        frame = self.__blend_geometry_layer(frame, t)
        frame = self.__blend_particle_layer(frame, t)

        # Apply global color cycling / hue shift
        frame = self.__apply_color_cycle(frame, t)

        self.__led_frame_player.play_frame(frame)

    def __render_plasma_layer(self, t):
        """
        Classic plasma effect using interference of sine waves.
        Multiple frequencies create organic, flowing patterns.
        """
        frame = np.zeros((self.__height, self.__width, 3), dtype=np.float32)

        # Time-varying frequencies for morphing effect
        freq1 = 3.0 + math.sin(t * 0.3) * 1.5
        freq2 = 4.0 + math.cos(t * 0.23) * 1.2
        freq3 = 2.5 + math.sin(t * 0.17) * 0.8

        # Multiple plasma waves with different phases
        plasma1 = np.sin(self.__x_norm * freq1 * math.pi + t * 0.7)
        plasma2 = np.sin(self.__y_norm * freq2 * math.pi + t * 0.5)
        plasma3 = np.sin((self.__x_norm + self.__y_norm) * freq3 * math.pi + t * 0.9)

        # Radial wave from center
        cx, cy = self.__width / 2, self.__height / 2
        dist = np.sqrt((self.__x_grid - cx)**2 + (self.__y_grid - cy)**2)
        max_dist = math.sqrt(cx**2 + cy**2)
        plasma4 = np.sin(dist / max_dist * 6 * math.pi - t * 1.2)

        # Combine plasmas
        combined = (plasma1 + plasma2 + plasma3 + plasma4) / 4.0

        # Map to hue (0-1 range)
        hue = (combined + 1) / 2  # normalize to 0-1

        # Add slow hue drift
        hue = (hue + t * 0.05) % 1.0

        # Convert to RGB with high saturation
        frame = self.__hue_array_to_rgb(hue, saturation=0.9, value=0.4)

        return frame

    def __blend_geometry_layer(self, frame, t):
        """
        Breathing sacred geometry - pulsing circles, rotating polygons.
        Creates a hypnotic focal point.
        """
        cx, cy = self.__width / 2, self.__height / 2

        # Breathing radius
        base_radius = min(self.__width, self.__height) * 0.35
        breath = math.sin(t * 0.8) * 0.3 + 1.0  # 0.7 to 1.3
        radius = base_radius * breath

        # Multiple concentric rings at different phases
        for ring in range(3):
            ring_breath = math.sin(t * 0.8 + ring * math.pi / 3) * 0.3 + 1.0
            ring_radius = base_radius * (0.4 + ring * 0.25) * ring_breath

            # Ring hue shifts over time
            ring_hue = (t * 0.1 + ring * 0.33) % 1.0

            # Draw ring pixels
            for angle_step in range(36):
                angle = angle_step * math.pi * 2 / 36 + t * (0.3 + ring * 0.1)
                px = int(cx + math.cos(angle) * ring_radius)
                py = int(cy + math.sin(angle) * ring_radius)

                if 0 <= px < self.__width and 0 <= py < self.__height:
                    ring_color = self.__hsv_to_rgb(ring_hue, 1.0, 1.0)
                    # Additive blend
                    for c in range(3):
                        frame[py, px, c] = min(255, frame[py, px, c] + ring_color[c] * 0.7)

        # Central pulsing dot
        pulse_intensity = (math.sin(t * 2.0) + 1) / 2
        center_hue = (t * 0.15) % 1.0
        center_color = self.__hsv_to_rgb(center_hue, 0.8, pulse_intensity)

        for dy in range(-1, 2):
            for dx in range(-1, 2):
                px, py = int(cx) + dx, int(cy) + dy
                if 0 <= px < self.__width and 0 <= py < self.__height:
                    dist = math.sqrt(dx*dx + dy*dy)
                    falloff = max(0, 1 - dist / 1.5)
                    for c in range(3):
                        frame[py, px, c] = min(255, frame[py, px, c] + center_color[c] * falloff)

        return frame

    def __blend_particle_layer(self, frame, t):
        """
        Flow field particles with trails.
        Particles follow a noise-based vector field, leaving fading trails.
        """
        num_particles = len(self.__particles)
        trail_length = self.__particle_trails.shape[1]

        # Update particle positions using noise-based flow field
        for i in range(num_particles):
            px, py = self.__particles[i]

            # Compute flow angle from pseudo-noise (layered sines)
            noise_val = self.__sample_flow_noise(px, py, t)
            angle = noise_val * math.pi * 2

            # Move particle
            speed = Config.get('cosmicdream.particle_speed', 0.5)
            self.__particles[i, 0] += math.cos(angle) * speed
            self.__particles[i, 1] += math.sin(angle) * speed

            # Wrap around edges
            self.__particles[i, 0] %= self.__width
            self.__particles[i, 1] %= self.__height

        # Shift trail buffer and add new position
        self.__particle_trails[:, 1:, :] = self.__particle_trails[:, :-1, :]
        self.__particle_trails[:, 0, :] = self.__particles

        # Render trails with fading
        for i in range(num_particles):
            # Particle hue based on position and time
            base_hue = (self.__particles[i, 0] / self.__width + t * 0.05) % 1.0

            for trail_idx in range(trail_length):
                tx, ty = self.__particle_trails[i, trail_idx]
                px, py = int(tx) % self.__width, int(ty) % self.__height

                # Fade based on trail position (newer = brighter)
                fade = 1.0 - (trail_idx / trail_length)
                fade = fade ** 0.5  # sqrt for slower falloff

                # Slight hue shift along trail
                hue = (base_hue + trail_idx * 0.02) % 1.0
                color = self.__hsv_to_rgb(hue, 1.0, fade)

                # Additive blend
                for c in range(3):
                    frame[py, px, c] = min(255, frame[py, px, c] + color[c] * 0.8)

        return frame

    def __sample_flow_noise(self, x, y, t):
        """
        Pseudo-noise function using layered sines.
        Creates organic, flowing patterns without requiring a noise library.
        """
        # Normalize coordinates
        nx = x / self.__width * 4
        ny = y / self.__height * 4

        # Multiple octaves of sine waves at different frequencies
        o = self.__noise_offsets
        noise = 0
        noise += math.sin(nx * 1.0 + o[0] + t * 0.3) * 0.5
        noise += math.sin(ny * 1.2 + o[1] + t * 0.25) * 0.5
        noise += math.sin((nx + ny) * 0.7 + o[2] + t * 0.2) * 0.3
        noise += math.sin((nx - ny) * 0.9 + o[3] - t * 0.15) * 0.3
        noise += math.sin(nx * 2.1 + ny * 1.8 + o[4] + t * 0.4) * 0.2
        noise += math.sin(math.sqrt(nx*nx + ny*ny) * 1.5 + o[5] + t * 0.35) * 0.2

        # Normalize to 0-1
        return (noise / 2.0 + 0.5) % 1.0

    def __apply_color_cycle(self, frame, t):
        """
        Global color transformation - shifts all hues for psychedelic effect.
        Also applies subtle pulsing to overall brightness.
        """
        # Breathing brightness
        breath = math.sin(t * 0.5) * 0.15 + 1.0  # 0.85 to 1.15

        # Apply to frame
        frame = frame * breath

        # Subtle color rotation using matrix transformation
        # This rotates the RGB cube slightly over time
        angle = t * 0.1
        cos_a, sin_a = math.cos(angle), math.sin(angle)

        # Simple hue rotation approximation
        r = frame[:, :, 0]
        g = frame[:, :, 1]
        b = frame[:, :, 2]

        # Rotate in RG plane slightly
        new_r = r * cos_a - g * sin_a * 0.3
        new_g = r * sin_a * 0.3 + g * cos_a

        frame[:, :, 0] = np.clip(new_r, 0, 255)
        frame[:, :, 1] = np.clip(new_g, 0, 255)

        return frame.astype(np.uint8)

    def __hue_array_to_rgb(self, hue_array, saturation=1.0, value=1.0):
        """
        Convert a 2D array of hue values to RGB frame.
        """
        h = hue_array
        s = saturation
        v = value

        i = (h * 6.0).astype(int)
        f = (h * 6.0) - i
        p = v * (1.0 - s)
        q = v * (1.0 - s * f)
        t = v * (1.0 - s * (1.0 - f))

        i = i % 6

        # Create RGB arrays
        r = np.zeros_like(h)
        g = np.zeros_like(h)
        b = np.zeros_like(h)

        mask0 = i == 0
        mask1 = i == 1
        mask2 = i == 2
        mask3 = i == 3
        mask4 = i == 4
        mask5 = i == 5

        r[mask0], g[mask0], b[mask0] = v, t[mask0], p
        r[mask1], g[mask1], b[mask1] = q[mask1], v, p
        r[mask2], g[mask2], b[mask2] = p, v, t[mask2]
        r[mask3], g[mask3], b[mask3] = p, q[mask3], v
        r[mask4], g[mask4], b[mask4] = t[mask4], p, v
        r[mask5], g[mask5], b[mask5] = v, p, q[mask5]

        frame = np.zeros((self.__height, self.__width, 3), dtype=np.float32)
        frame[:, :, 0] = r * 255
        frame[:, :, 1] = g * 255
        frame[:, :, 2] = b * 255

        return frame

    def __hsv_to_rgb(self, h, s, v):
        """Convert single HSV value to RGB list."""
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
        return Config.get('cosmicdream.tick_sleep', 0.03)

    @classmethod
    def get_id(cls) -> str:
        return 'cosmic_dream'

    @classmethod
    def get_name(cls) -> str:
        return 'Cosmic Dream'

    @classmethod
    def get_description(cls) -> str:
        return 'Psychedelic plasma waves, particles, and geometry'
