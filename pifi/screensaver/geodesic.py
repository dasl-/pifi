"""
Geodesic screensaver.

A slowly tumbling wireframe polyhedron that morphs between different
geometric forms: icosahedron, dodecahedron, cube, octahedron, snub cube,
and geodesic sphere. Inspired by Buckminster Fuller.
"""

import math
import numpy as np
import random

from pifi.config import Config
from pifi.screensaver.screensaver import Screensaver


# ---------------------------------------------------------------------------
# Polyhedra definitions — vertices on the unit sphere
# ---------------------------------------------------------------------------

_PHI = (1.0 + math.sqrt(5.0)) / 2.0


def _normalize_rows(arr):
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return arr / norms


def _edges_from_faces(faces, num_verts):
    edge_set = set()
    for f in faces:
        for i in range(len(f)):
            a, b = f[i], f[(i + 1) % len(f)]
            edge_set.add((min(a, b), max(a, b)))
    return np.array(sorted(edge_set), dtype=np.int32)


def _build_icosahedron():
    verts = _normalize_rows(np.array([
        [-1, _PHI, 0], [1, _PHI, 0], [-1, -_PHI, 0], [1, -_PHI, 0],
        [0, -1, _PHI], [0, 1, _PHI], [0, -1, -_PHI], [0, 1, -_PHI],
        [_PHI, 0, -1], [_PHI, 0, 1], [-_PHI, 0, -1], [-_PHI, 0, 1],
    ], dtype=np.float64))
    faces = [
        (0,11,5),(0,5,1),(0,1,7),(0,7,10),(0,10,11),
        (1,5,9),(5,11,4),(11,10,2),(10,7,6),(7,1,8),
        (3,9,4),(3,4,2),(3,2,6),(3,6,8),(3,8,9),
        (4,9,5),(2,4,11),(6,2,10),(8,6,7),(9,8,1),
    ]
    edges = _edges_from_faces(faces, len(verts))
    return verts, edges


def _build_dodecahedron():
    # Vertices of a dodecahedron from cube + golden ratio rectangles
    p = _PHI
    ip = 1.0 / _PHI
    raw = []
    for s1 in [-1, 1]:
        for s2 in [-1, 1]:
            for s3 in [-1, 1]:
                raw.append([s1, s2, s3])
    for s1 in [-1, 1]:
        for s2 in [-1, 1]:
            raw.append([0, s1 * ip, s2 * p])
            raw.append([s1 * ip, s2 * p, 0])
            raw.append([s2 * p, 0, s1 * ip])
    verts = _normalize_rows(np.array(raw, dtype=np.float64))
    # Build edges by connecting nearest neighbors (each vertex has 3)
    edges = _edges_by_distance(verts, 3)
    return verts, edges


def _build_cube():
    raw = []
    for s1 in [-1, 1]:
        for s2 in [-1, 1]:
            for s3 in [-1, 1]:
                raw.append([s1, s2, s3])
    verts = _normalize_rows(np.array(raw, dtype=np.float64))
    edges = _edges_by_distance(verts, 3)
    return verts, edges


def _build_octahedron():
    verts = np.array([
        [1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1],
    ], dtype=np.float64)
    edges = _edges_by_distance(verts, 4)
    return verts, edges


def _build_cuboctahedron():
    raw = []
    for s1 in [-1, 1]:
        for s2 in [-1, 1]:
            raw.append([s1, s2, 0])
            raw.append([s1, 0, s2])
            raw.append([0, s1, s2])
    verts = _normalize_rows(np.array(raw, dtype=np.float64))
    edges = _edges_by_distance(verts, 4)
    return verts, edges


def _build_snub_cube():
    """Approximate snub cube vertices on the unit sphere."""
    # Tribonacci constant
    t = 1.8393  # real root of t^3 - t^2 - t - 1 = 0
    raw = []
    evens = [(1, 1, 1), (1, -1, -1), (-1, 1, -1), (-1, -1, 1)]
    for (s1, s2, s3) in evens:
        # Even permutations of (1, 1/t, t)
        raw.append([s1 * 1, s2 * (1/t), s3 * t])
        raw.append([s1 * (1/t), s2 * t, s3 * 1])
        raw.append([s1 * t, s2 * 1, s3 * (1/t)])
    odds = [(1, 1, -1), (1, -1, 1), (-1, 1, 1), (-1, -1, -1)]
    for (s1, s2, s3) in odds:
        raw.append([s1 * 1, s2 * (1/t), s3 * t])
        raw.append([s1 * (1/t), s2 * t, s3 * 1])
        raw.append([s1 * t, s2 * 1, s3 * (1/t)])
    verts = _normalize_rows(np.array(raw, dtype=np.float64))
    # Remove duplicate vertices (within tolerance)
    verts = _deduplicate_verts(verts)
    edges = _edges_by_distance(verts, 5)
    return verts, edges


def _build_geodesic():
    """Build a 1x subdivided icosahedron (geodesic sphere)."""
    base_v, base_e = _build_icosahedron()
    faces = [
        (0,11,5),(0,5,1),(0,1,7),(0,7,10),(0,10,11),
        (1,5,9),(5,11,4),(11,10,2),(10,7,6),(7,1,8),
        (3,9,4),(3,4,2),(3,2,6),(3,6,8),(3,8,9),
        (4,9,5),(2,4,11),(6,2,10),(8,6,7),(9,8,1),
    ]
    # Subdivide
    midpoint_cache = {}
    new_faces = []
    verts_list = list(base_v)

    def get_mid(a, b):
        key = (min(a, b), max(a, b))
        if key in midpoint_cache:
            return midpoint_cache[key]
        mid = (verts_list[a] + verts_list[b]) / 2.0
        mid /= np.linalg.norm(mid)
        idx = len(verts_list)
        verts_list.append(mid)
        midpoint_cache[key] = idx
        return idx

    for f in faces:
        a, b, c = f
        ab = get_mid(a, b)
        bc = get_mid(b, c)
        ca = get_mid(c, a)
        new_faces.append((a, ab, ca))
        new_faces.append((b, bc, ab))
        new_faces.append((c, ca, bc))
        new_faces.append((ab, bc, ca))

    verts = np.array(verts_list, dtype=np.float64)
    edges = _edges_from_faces(new_faces, len(verts))
    return verts, edges


def _deduplicate_verts(verts, tol=0.01):
    unique = [verts[0]]
    for v in verts[1:]:
        dists = np.linalg.norm(np.array(unique) - v, axis=1)
        if np.all(dists > tol):
            unique.append(v)
    return np.array(unique, dtype=np.float64)


def _edges_by_distance(verts, k):
    """Build edges by connecting each vertex to its k nearest neighbors."""
    n = len(verts)
    dists = np.zeros((n, n))
    for i in range(n):
        dists[i] = np.linalg.norm(verts - verts[i], axis=1)
    edge_set = set()
    for i in range(n):
        sorted_idx = np.argsort(dists[i])
        for j in sorted_idx[1:k+1]:
            edge_set.add((min(i, int(j)), max(i, int(j))))
    return np.array(sorted(edge_set), dtype=np.int32)


# All available shapes
_SHAPES = {
    'icosahedron': _build_icosahedron,
    'dodecahedron': _build_dodecahedron,
    'cube': _build_cube,
    'octahedron': _build_octahedron,
    'cuboctahedron': _build_cuboctahedron,
    'snub_cube': _build_snub_cube,
    'geodesic': _build_geodesic,
}


# ---------------------------------------------------------------------------
# Rotation helpers
# ---------------------------------------------------------------------------

def _rot_y(angle):
    c, s = math.cos(angle), math.sin(angle)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], dtype=np.float64)


def _rot_axis(axis, angle):
    axis = axis / np.linalg.norm(axis)
    c, s = math.cos(angle), math.sin(angle)
    t = 1.0 - c
    x, y, z = axis
    return np.array([
        [t*x*x+c, t*x*y-s*z, t*x*z+s*y],
        [t*x*y+s*z, t*y*y+c, t*y*z-s*x],
        [t*x*z-s*y, t*y*z+s*x, t*z*z+c],
    ], dtype=np.float64)


def _hsv_to_rgb(h, s, v):
    h = h % 1.0
    i = int(h * 6.0)
    f = h * 6.0 - i
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


# ---------------------------------------------------------------------------
# Screensaver
# ---------------------------------------------------------------------------

class Geodesic(Screensaver):
    """Rotating wireframe polyhedron that morphs between geometric forms."""

    _MODE_WHITE = 0
    _MODE_CYAN = 1
    _MODE_HUE_SHIFT = 2

    def __init__(self, led_frame_player=None):
        super().__init__(led_frame_player)
        self.__width = Config.get_or_throw('leds.display_width')
        self.__height = Config.get_or_throw('leds.display_height')

    def _setup(self):
        # Build all shapes once
        self.__all_shapes = {}
        for name, builder in _SHAPES.items():
            v, e = builder()
            self.__all_shapes[name] = (v, e)

        self.__shape_names = list(_SHAPES.keys())

        # Pick initial shape
        self.__current_shape = random.choice(self.__shape_names)
        v, e = self.__all_shapes[self.__current_shape]
        self.__verts = v.copy()
        self.__edges = e.copy()
        self.__num_verts = len(v)
        self.__num_edges = len(e)

        # Morphing state
        self.__morph_progress = 1.0  # 1.0 = fully arrived
        self.__morph_from_verts = v.copy()
        self.__morph_from_edges = e.copy()
        self.__morph_to_verts = v.copy()
        self.__morph_to_edges = e.copy()
        self.__morph_timer = 0.0
        self.__morph_interval = random.uniform(6.0, 12.0)
        self.__morph_duration = random.uniform(2.0, 4.0)

        # Sphere radius in pixels
        self.__radius = min(self.__width, self.__height) * 0.38

        # Perspective camera
        self.__cam_dist = 4.0

        # Rotation
        self.__angle_y = random.uniform(0, 2 * math.pi)
        self.__angle_tilt = random.uniform(0, 2 * math.pi)
        self.__speed_y = random.uniform(0.008, 0.020) * random.choice([-1, 1])
        self.__speed_tilt = random.uniform(0.005, 0.015) * random.choice([-1, 1])

        tilt_elev = random.uniform(0.2, 0.6)
        self.__tilt_axis = np.array([
            math.cos(tilt_elev), math.sin(tilt_elev) * 0.3, 0
        ], dtype=np.float64)
        self.__tilt_axis /= np.linalg.norm(self.__tilt_axis)

        # Color
        self.__color_mode = random.choice([
            self._MODE_WHITE, self._MODE_CYAN, self._MODE_HUE_SHIFT
        ])
        self.__hue_base = random.random()
        self.__hue_speed = random.uniform(0.0008, 0.003)

        # Canvas
        self.__canvas = np.zeros((self.__height, self.__width, 3), dtype=np.float32)
        self.__decay = 0.82

        # Pixel grids
        ys = np.arange(self.__height, dtype=np.float32)
        xs = np.arange(self.__width, dtype=np.float32)
        self.__grid_x, self.__grid_y = np.meshgrid(xs, ys)

        min_dim = min(self.__width, self.__height)
        self.__line_half_width = max(0.6, min_dim / 50.0)
        self.__vertex_radius = max(1.0, min_dim / 30.0)

    def _tick(self, tick):
        self.__angle_y += self.__speed_y
        self.__angle_tilt += self.__speed_tilt

        # Morphing timer
        dt = 0.03
        self.__morph_timer += dt

        if self.__morph_progress >= 1.0 and self.__morph_timer >= self.__morph_interval:
            # Start morphing to a new shape
            self.__morph_timer = 0.0
            self.__morph_interval = random.uniform(6.0, 12.0)
            self.__morph_duration = random.uniform(2.0, 4.0)

            # Pick a different shape
            candidates = [s for s in self.__shape_names if s != self.__current_shape]
            next_shape = random.choice(candidates)

            self.__morph_from_verts = self.__verts.copy()
            self.__morph_from_edges = self.__edges.copy()

            # Build target: map current vertices to nearest target vertices
            target_v, target_e = self.__all_shapes[next_shape]
            self.__morph_to_verts, self.__morph_to_edges = self.__build_morph_target(
                self.__morph_from_verts, target_v, target_e
            )
            self.__morph_progress = 0.0
            self.__current_shape = next_shape

        # Interpolate morph
        if self.__morph_progress < 1.0:
            self.__morph_progress = min(1.0, self.__morph_progress + dt / self.__morph_duration)
            # Smoothstep easing
            p = self.__morph_progress
            t = p * p * (3 - 2 * p)

            # Interpolate vertex positions on the unit sphere
            interp = self.__morph_from_verts * (1 - t) + self.__morph_to_verts * t
            # Re-project onto unit sphere for smooth spherical interpolation
            self.__verts = _normalize_rows(interp)
            self.__num_verts = len(self.__verts)

            # Switch edges at halfway point
            if p >= 0.5:
                self.__edges = self.__morph_to_edges
            else:
                self.__edges = self.__morph_from_edges
            self.__num_edges = len(self.__edges)

        # Rotation
        rot = _rot_axis(self.__tilt_axis, self.__angle_tilt) @ _rot_y(self.__angle_y)
        rotated = (rot @ self.__verts.T).T

        # Perspective projection
        z_vals = rotated[:, 2]
        depth_factor = self.__cam_dist / (self.__cam_dist - z_vals)
        proj_x = rotated[:, 0] * depth_factor * self.__radius + self.__width / 2.0
        proj_y = rotated[:, 1] * depth_factor * self.__radius + self.__height / 2.0
        depth_brightness = 0.25 + 0.75 * (z_vals + 1) / 2.0

        base_color = self.__get_base_color(tick)

        # Decay canvas
        self.__canvas *= self.__decay

        # Render
        self.__render_edges(proj_x, proj_y, z_vals, depth_brightness, base_color)
        self.__render_vertices(proj_x, proj_y, depth_brightness, base_color)

        frame = (np.clip(self.__canvas, 0.0, 1.0) * 255).astype(np.uint8)
        self._led_frame_player.play_frame(frame)

    def __build_morph_target(self, from_verts, to_verts, to_edges):
        """Build a morph target with the same vertex count as from_verts.

        For each from_vertex, find the nearest to_vertex (on unit sphere).
        Multiple from_verts may map to the same to_vert, which is fine —
        they'll converge during the morph.
        """
        n_from = len(from_verts)
        n_to = len(to_verts)

        if n_from == n_to:
            # Same count — find optimal 1:1 mapping by greedy nearest
            target = np.zeros_like(from_verts)
            used = set()
            for i in range(n_from):
                dists = np.linalg.norm(to_verts - from_verts[i], axis=1)
                sorted_idx = np.argsort(dists)
                for j in sorted_idx:
                    if int(j) not in used:
                        target[i] = to_verts[j]
                        used.add(int(j))
                        break
            return target, to_edges

        if n_from > n_to:
            # More from_verts than to_verts — each from_vert goes to nearest to_vert
            target = np.zeros_like(from_verts)
            mapping = np.zeros(n_from, dtype=np.int32)
            for i in range(n_from):
                dists = np.linalg.norm(to_verts - from_verts[i], axis=1)
                nearest = int(np.argmin(dists))
                target[i] = to_verts[nearest]
                mapping[i] = nearest

            # Build edge list: remap to_edges through the mapping
            # Find which from_verts map to each to_vert
            remap = {}
            for i in range(n_from):
                to_idx = mapping[i]
                if to_idx not in remap:
                    remap[to_idx] = i  # first from_vert that maps here

            new_edges = set()
            for e in to_edges:
                a_to, b_to = int(e[0]), int(e[1])
                if a_to in remap and b_to in remap:
                    a_from = remap[a_to]
                    b_from = remap[b_to]
                    new_edges.add((min(a_from, b_from), max(a_from, b_from)))

            return target, np.array(sorted(new_edges), dtype=np.int32) if new_edges else to_edges

        else:
            # Fewer from_verts than to_verts — expand from_verts
            # Duplicate some from_verts to match to_vert count, then map 1:1
            target = to_verts.copy()
            # Build expanded from_verts
            expanded = np.zeros((n_to, 3), dtype=np.float64)
            for i in range(n_to):
                dists = np.linalg.norm(from_verts - to_verts[i], axis=1)
                nearest = int(np.argmin(dists))
                expanded[i] = from_verts[nearest]

            self.__morph_from_verts = expanded
            self.__verts = expanded.copy()
            self.__num_verts = n_to
            return target, to_edges

    def __get_base_color(self, tick):
        if self.__color_mode == self._MODE_WHITE:
            return (1.0, 1.0, 1.0)
        elif self.__color_mode == self._MODE_CYAN:
            return (0.3, 1.0, 1.0)
        else:
            hue = (self.__hue_base + tick * self.__hue_speed) % 1.0
            return _hsv_to_rgb(hue, 0.7, 1.0)

    def __render_edges(self, proj_x, proj_y, z_vals, depth_brightness, base_color):
        hw = self.__line_half_width
        gx, gy = self.__grid_x, self.__grid_y

        for ei in range(self.__num_edges):
            a, b = int(self.__edges[ei, 0]), int(self.__edges[ei, 1])
            if a >= self.__num_verts or b >= self.__num_verts:
                continue

            x0, y0 = proj_x[a], proj_y[a]
            x1, y1 = proj_x[b], proj_y[b]
            edge_bright = (depth_brightness[a] + depth_brightness[b]) * 0.5

            pad = hw + 1.5
            min_x = max(0, int(min(x0, x1) - pad))
            max_x = min(self.__width, int(max(x0, x1) + pad) + 1)
            min_y = max(0, int(min(y0, y1) - pad))
            max_y = min(self.__height, int(max(y0, y1) + pad) + 1)
            if max_x <= min_x or max_y <= min_y:
                continue

            sx = gx[min_y:max_y, min_x:max_x]
            sy = gy[min_y:max_y, min_x:max_x]

            dx_seg = x1 - x0
            dy_seg = y1 - y0
            seg_len_sq = dx_seg * dx_seg + dy_seg * dy_seg
            if seg_len_sq < 1e-6:
                continue

            t_p = np.clip(((sx - x0) * dx_seg + (sy - y0) * dy_seg) / seg_len_sq, 0, 1)
            cx = x0 + t_p * dx_seg
            cy = y0 + t_p * dy_seg
            dist = np.sqrt((sx - cx) ** 2 + (sy - cy) ** 2)

            intensity = np.clip(1.0 - (dist - hw * 0.5) / (hw * 0.5 + 0.5), 0, 1)
            intensity *= edge_bright * 0.7

            for c in range(3):
                self.__canvas[min_y:max_y, min_x:max_x, c] = np.maximum(
                    self.__canvas[min_y:max_y, min_x:max_x, c],
                    intensity * base_color[c]
                )

    def __render_vertices(self, proj_x, proj_y, depth_brightness, base_color):
        vr = self.__vertex_radius
        gx, gy = self.__grid_x, self.__grid_y

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
            intensity = np.clip(1.0 - dist / vr, 0, 1) * bright

            for c in range(3):
                self.__canvas[min_y:max_y, min_x:max_x, c] = np.maximum(
                    self.__canvas[min_y:max_y, min_x:max_x, c],
                    intensity * base_color[c]
                )

    @classmethod
    def get_id(cls) -> str:
        return 'geodesic'

    @classmethod
    def get_name(cls) -> str:
        return 'Geodesic'

    @classmethod
    def get_description(cls) -> str:
        return 'Morphing wireframe polyhedra'
