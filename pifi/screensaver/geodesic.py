"""
Geodesic screensaver.

A slowly tumbling wireframe geodesic sphere inspired by Buckminster Fuller.
Glowing vertices and depth-shaded edges rotate against black, leaving a
faint afterglow trail.
"""

import math
import numpy as np
import random

from pifi.config import Config
from pifi.screensaver.screensaver import Screensaver


# ---------------------------------------------------------------------------
# Icosahedron geometry
# ---------------------------------------------------------------------------

# Golden ratio
_PHI = (1.0 + math.sqrt(5.0)) / 2.0

# 12 vertices of a unit icosahedron (edge length ~1.05)
_ICO_VERTICES = np.array([
    [-1,  _PHI,  0],
    [ 1,  _PHI,  0],
    [-1, -_PHI,  0],
    [ 1, -_PHI,  0],
    [ 0, -1,  _PHI],
    [ 0,  1,  _PHI],
    [ 0, -1, -_PHI],
    [ 0,  1, -_PHI],
    [ _PHI,  0, -1],
    [ _PHI,  0,  1],
    [-_PHI,  0, -1],
    [-_PHI,  0,  1],
], dtype=np.float64)

# 20 triangular faces (vertex indices, CCW winding)
_ICO_FACES = [
    (0, 11, 5),  (0, 5, 1),   (0, 1, 7),   (0, 7, 10),  (0, 10, 11),
    (1, 5, 9),   (5, 11, 4),  (11, 10, 2),  (10, 7, 6),  (7, 1, 8),
    (3, 9, 4),   (3, 4, 2),   (3, 2, 6),    (3, 6, 8),   (3, 8, 9),
    (4, 9, 5),   (2, 4, 11),  (6, 2, 10),   (8, 6, 7),   (9, 8, 1),
]


def _normalize_rows(arr):
    """Normalize each row of an (N, 3) array to unit length."""
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return arr / norms


def _build_icosahedron():
    """Return (vertices, edges, faces) for a unit icosahedron."""
    verts = _normalize_rows(_ICO_VERTICES.copy())
    edge_set = set()
    for f in _ICO_FACES:
        for i in range(3):
            a, b = f[i], f[(i + 1) % 3]
            edge_set.add((min(a, b), max(a, b)))
    edges = np.array(sorted(edge_set), dtype=np.int32)
    faces = np.array(_ICO_FACES, dtype=np.int32)
    return verts, edges, faces


def _subdivide(verts, faces):
    """Subdivide each triangle into 4, projecting new vertices onto the unit sphere.

    Returns (new_verts, new_edges, new_faces).
    """
    midpoint_cache = {}
    new_faces = []

    def _get_midpoint(a, b):
        key = (min(a, b), max(a, b))
        if key in midpoint_cache:
            return midpoint_cache[key]
        mid = (verts[a] + verts[b]) / 2.0
        mid /= np.linalg.norm(mid)  # project onto unit sphere
        idx = len(verts_list)
        verts_list.append(mid)
        midpoint_cache[key] = idx
        return idx

    verts_list = list(verts)

    for f in faces:
        a, b, c = int(f[0]), int(f[1]), int(f[2])
        ab = _get_midpoint(a, b)
        bc = _get_midpoint(b, c)
        ca = _get_midpoint(c, a)
        new_faces.append((a, ab, ca))
        new_faces.append((b, bc, ab))
        new_faces.append((c, ca, bc))
        new_faces.append((ab, bc, ca))

    new_verts = np.array(verts_list, dtype=np.float64)
    edge_set = set()
    for f in new_faces:
        for i in range(3):
            a, b = f[i], f[(i + 1) % 3]
            edge_set.add((min(a, b), max(a, b)))
    new_edges = np.array(sorted(edge_set), dtype=np.int32)
    new_faces_arr = np.array(new_faces, dtype=np.int32)
    return new_verts, new_edges, new_faces_arr


# ---------------------------------------------------------------------------
# Rotation helpers
# ---------------------------------------------------------------------------

def _rot_y(angle):
    """3x3 rotation matrix around the Y axis."""
    c, s = math.cos(angle), math.sin(angle)
    return np.array([
        [ c, 0, s],
        [ 0, 1, 0],
        [-s, 0, c],
    ], dtype=np.float64)


def _rot_axis(axis, angle):
    """3x3 rotation matrix around an arbitrary unit axis (Rodrigues)."""
    axis = axis / np.linalg.norm(axis)
    c = math.cos(angle)
    s = math.sin(angle)
    t = 1.0 - c
    x, y, z = axis
    return np.array([
        [t * x * x + c,     t * x * y - s * z, t * x * z + s * y],
        [t * x * y + s * z, t * y * y + c,     t * y * z - s * x],
        [t * x * z - s * y, t * y * z + s * x, t * z * z + c    ],
    ], dtype=np.float64)


# ---------------------------------------------------------------------------
# Color helpers
# ---------------------------------------------------------------------------

def _hsv_to_rgb(h, s, v):
    """Convert HSV [0..1] to RGB tuple of floats [0..1]."""
    h = h % 1.0
    i = int(h * 6.0)
    f = h * 6.0 - i
    p = v * (1.0 - s)
    q = v * (1.0 - s * f)
    t = v * (1.0 - s * (1.0 - f))
    i = i % 6
    if i == 0:
        return v, t, p
    elif i == 1:
        return q, v, p
    elif i == 2:
        return p, v, t
    elif i == 3:
        return p, q, v
    elif i == 4:
        return t, p, v
    else:
        return v, p, q


# ---------------------------------------------------------------------------
# Screensaver
# ---------------------------------------------------------------------------

class Geodesic(Screensaver):
    """Rotating wireframe geodesic sphere with glowing vertices and edges."""

    # Color mode constants
    _MODE_WHITE = 0
    _MODE_CYAN = 1
    _MODE_HUE_SHIFT = 2

    def __init__(self, led_frame_player=None):
        super().__init__(led_frame_player)

        self.__width = Config.get_or_throw('leds.display_width')
        self.__height = Config.get_or_throw('leds.display_height')

    def _setup(self):
        # Decide subdivision level based on display size
        min_dim = min(self.__width, self.__height)
        if min_dim >= 32:
            subdiv = random.choice([0, 1])
        else:
            subdiv = 0

        # Build geometry
        verts, edges, faces = _build_icosahedron()
        if subdiv >= 1:
            verts, edges, faces = _subdivide(verts, faces)

        self.__base_verts = verts     # (V, 3) unit sphere — reference shape
        self.__verts = verts.copy()   # working copy with deformations
        self.__edges = edges          # (E, 2) index pairs
        self.__faces = faces          # (F, 3) index triples
        self.__num_verts = len(verts)
        self.__num_edges = len(edges)

        # Vertex radius modulation — each vertex breathes at its own frequency
        self.__vert_freq = np.array([random.uniform(0.3, 1.2) for _ in range(len(verts))])
        self.__vert_phase = np.array([random.uniform(0, 2 * math.pi) for _ in range(len(verts))])
        self.__vert_amp = np.array([random.uniform(0.05, 0.2) for _ in range(len(verts))])
        # Target modulation params for smooth transitions
        self.__vert_target_freq = self.__vert_freq.copy()
        self.__vert_target_phase = self.__vert_phase.copy()
        self.__vert_target_amp = self.__vert_amp.copy()
        self.__morph_timer = 0.0
        self.__morph_interval = random.uniform(8.0, 15.0)

        # Sphere radius in pixels -- fill ~75% of the smaller display dimension
        self.__radius = min(self.__width, self.__height) * 0.38

        # Perspective camera distance (in sphere-radius units)
        self.__cam_dist = 4.0

        # Random initial rotation angles
        self.__angle_y = random.uniform(0, 2 * math.pi)
        self.__angle_tilt = random.uniform(0, 2 * math.pi)

        # Random rotation speeds (radians per tick) -- slow tumble
        self.__speed_y = random.uniform(0.008, 0.020) * random.choice([-1, 1])
        self.__speed_tilt = random.uniform(0.005, 0.015) * random.choice([-1, 1])

        # Tilt axis (fixed, slightly off from X)
        tilt_elevation = random.uniform(0.2, 0.6)
        self.__tilt_axis = np.array([
            math.cos(tilt_elevation), math.sin(tilt_elevation) * 0.3, 0
        ], dtype=np.float64)
        self.__tilt_axis /= np.linalg.norm(self.__tilt_axis)

        # Color mode
        self.__color_mode = random.choice([
            self._MODE_WHITE, self._MODE_CYAN, self._MODE_HUE_SHIFT
        ])
        self.__hue_base = random.random()
        self.__hue_speed = random.uniform(0.0008, 0.003)

        # Canvas for afterglow (float32 for smooth fading)
        self.__canvas = np.zeros((self.__height, self.__width, 3), dtype=np.float32)

        # Afterglow decay factor
        self.__decay = 0.82

        # Pre-compute pixel coordinate grids for vectorized distance computation
        ys = np.arange(self.__height, dtype=np.float32)
        xs = np.arange(self.__width, dtype=np.float32)
        self.__grid_x, self.__grid_y = np.meshgrid(xs, ys)  # (H, W) each

        # Line rendering thickness (half-width in pixels)
        self.__line_half_width = max(0.6, min_dim / 50.0)

        # Vertex glow radius
        self.__vertex_radius = max(1.0, min_dim / 30.0)

    def _tick(self, tick):
        # Update rotation angles
        self.__angle_y += self.__speed_y
        self.__angle_tilt += self.__speed_tilt

        # Morph modulation parameters over time
        self.__morph_timer += 1
        if self.__morph_timer > self.__morph_interval / 0.03:  # convert seconds to ticks
            self.__morph_timer = 0
            self.__morph_interval = random.uniform(8.0, 15.0)
            # Set new target modulation
            self.__vert_target_freq = np.array([random.uniform(0.3, 1.2) for _ in range(self.__num_verts)])
            self.__vert_target_phase = np.array([random.uniform(0, 2 * math.pi) for _ in range(self.__num_verts)])
            self.__vert_target_amp = np.array([random.uniform(0.05, 0.25) for _ in range(self.__num_verts)])

        # Smoothly interpolate modulation params toward targets
        lerp = 0.01
        self.__vert_freq += (self.__vert_target_freq - self.__vert_freq) * lerp
        self.__vert_phase += (self.__vert_target_phase - self.__vert_phase) * lerp
        self.__vert_amp += (self.__vert_target_amp - self.__vert_amp) * lerp

        # Apply vertex radius modulation — each vertex breathes independently
        t_sec = tick * 0.03  # approximate time in seconds
        modulation = 1.0 + self.__vert_amp * np.sin(t_sec * self.__vert_freq * 2 * math.pi + self.__vert_phase)
        # Scale each vertex's radius
        self.__verts = self.__base_verts * modulation[:, np.newaxis]

        # Build combined rotation matrix
        rot = _rot_axis(self.__tilt_axis, self.__angle_tilt) @ _rot_y(self.__angle_y)

        # Rotate all vertices: (V, 3)
        rotated = (rot @ self.__verts.T).T  # (V, 3)

        # Perspective projection
        # Camera looks down -Z; vertices are on the unit sphere centered at origin.
        # We place the camera at z = cam_dist (in radius units).
        cam_z = self.__cam_dist
        # Projected coords: x_proj = x / (cam_z - z), similarly y
        z_vals = rotated[:, 2]  # (V,)
        depth_factor = cam_z / (cam_z - z_vals)  # (V,) -- positive, >1 for closer

        proj_x = rotated[:, 0] * depth_factor * self.__radius + self.__width / 2.0
        proj_y = rotated[:, 1] * depth_factor * self.__radius + self.__height / 2.0

        # Depth-based brightness: map z from [-1, 1] to [0.25, 1.0]
        # z=1 is closest to camera, z=-1 is farthest
        depth_brightness = 0.25 + 0.75 * (z_vals + 1.0) / 2.0  # (V,)

        # Determine base color for this tick
        base_color = self.__get_base_color(tick)

        # Decay canvas (afterglow)
        self.__canvas *= self.__decay

        # -- Render edges --
        self.__render_edges(proj_x, proj_y, z_vals, depth_brightness, base_color)

        # -- Render vertices --
        self.__render_vertices(proj_x, proj_y, depth_brightness, base_color)

        # Output frame
        frame = (np.clip(self.__canvas, 0.0, 1.0) * 255).astype(np.uint8)
        self._led_frame_player.play_frame(frame)

    # -------------------------------------------------------------------
    # Color
    # -------------------------------------------------------------------

    def __get_base_color(self, tick):
        """Return (r, g, b) floats in [0, 1] for the current tick."""
        if self.__color_mode == self._MODE_WHITE:
            return (1.0, 1.0, 1.0)
        elif self.__color_mode == self._MODE_CYAN:
            return (0.3, 1.0, 1.0)
        else:
            hue = (self.__hue_base + tick * self.__hue_speed) % 1.0
            return _hsv_to_rgb(hue, 0.7, 1.0)

    # -------------------------------------------------------------------
    # Edge rendering (vectorized distance-to-segment per edge)
    # -------------------------------------------------------------------

    def __render_edges(self, proj_x, proj_y, z_vals, depth_brightness, base_color):
        hw = self.__line_half_width
        gx = self.__grid_x  # (H, W)
        gy = self.__grid_y  # (H, W)

        for ei in range(self.__num_edges):
            a, b = int(self.__edges[ei, 0]), int(self.__edges[ei, 1])

            x0, y0 = proj_x[a], proj_y[a]
            x1, y1 = proj_x[b], proj_y[b]

            # Edge average depth brightness
            edge_bright = (depth_brightness[a] + depth_brightness[b]) * 0.5

            # Bounding box (with padding) to limit computation
            pad = hw + 1.5
            min_x = max(0, int(min(x0, x1) - pad))
            max_x = min(self.__width, int(max(x0, x1) + pad) + 1)
            min_y = max(0, int(min(y0, y1) - pad))
            max_y = min(self.__height, int(max(y0, y1) + pad) + 1)

            if max_x <= min_x or max_y <= min_y:
                continue

            # Sub-grid for this edge
            sx = gx[min_y:max_y, min_x:max_x]  # (h, w)
            sy = gy[min_y:max_y, min_x:max_x]

            # Vector from segment start to end
            dx_seg = x1 - x0
            dy_seg = y1 - y0
            seg_len_sq = dx_seg * dx_seg + dy_seg * dy_seg

            if seg_len_sq < 1e-6:
                continue

            # Parameter t of closest point on segment for each pixel
            # t = dot(P - A, B - A) / |B - A|^2, clamped [0, 1]
            t = ((sx - x0) * dx_seg + (sy - y0) * dy_seg) / seg_len_sq
            t = np.clip(t, 0.0, 1.0)

            # Closest point on segment
            cx = x0 + t * dx_seg
            cy = y0 + t * dy_seg

            # Distance from pixel to closest point
            dist = np.sqrt((sx - cx) ** 2 + (sy - cy) ** 2)

            # Anti-aliased intensity: 1 inside half-width, smooth falloff outside
            intensity = np.clip(1.0 - (dist - hw * 0.5) / (hw * 0.5 + 0.5), 0.0, 1.0)
            intensity *= edge_bright * 0.7  # scale edge brightness

            # Apply color additively to the canvas sub-region
            for c in range(3):
                self.__canvas[min_y:max_y, min_x:max_x, c] = np.maximum(
                    self.__canvas[min_y:max_y, min_x:max_x, c],
                    intensity * base_color[c]
                )

    # -------------------------------------------------------------------
    # Vertex rendering
    # -------------------------------------------------------------------

    def __render_vertices(self, proj_x, proj_y, depth_brightness, base_color):
        vr = self.__vertex_radius
        gx = self.__grid_x
        gy = self.__grid_y

        for vi in range(self.__num_verts):
            vx, vy = proj_x[vi], proj_y[vi]
            bright = depth_brightness[vi]

            pad = vr + 1.0
            min_x = max(0, int(vx - pad))
            max_x = min(self.__width, int(vx + pad) + 1)
            min_y = max(0, int(vy - pad))
            max_y = min(self.__height, int(vy + pad) + 1)

            if max_x <= min_x or max_y <= min_y:
                continue

            sx = gx[min_y:max_y, min_x:max_x]
            sy = gy[min_y:max_y, min_x:max_x]

            dist = np.sqrt((sx - vx) ** 2 + (sy - vy) ** 2)
            intensity = np.clip(1.0 - dist / vr, 0.0, 1.0)
            intensity *= bright

            for c in range(3):
                self.__canvas[min_y:max_y, min_x:max_x, c] = np.maximum(
                    self.__canvas[min_y:max_y, min_x:max_x, c],
                    intensity * base_color[c]
                )

    # -------------------------------------------------------------------
    # Metadata
    # -------------------------------------------------------------------

    @classmethod
    def get_id(cls) -> str:
        return 'geodesic'

    @classmethod
    def get_name(cls) -> str:
        return 'Geodesic'

    @classmethod
    def get_description(cls) -> str:
        return 'Rotating wireframe geodesic sphere'
