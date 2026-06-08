#!/usr/bin/env python3
"""Unit tests for pifi.screensaver.colorutils."""

import colorsys
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pifi.screensaver.colorutils import hsv_to_rgb, hsv_to_rgb_bytes, hsv_to_rgb_uint8_frame


def _grid():
    """A grid of (h, s, v) triples spanning [0, 1)."""
    for h in np.linspace(0.0, 0.999, 23):
        for s in np.linspace(0.0, 1.0, 11):
            for v in np.linspace(0.0, 1.0, 11):
                yield float(h), float(s), float(v)


class TestColorUtils(unittest.TestCase):

    def test_scalar_parity_with_colorsys(self):
        """The scalar path is a pure delegation to colorsys for h in [0,1), so it
        must match exactly (bit for bit), not merely approximately. (Range stays
        in [0,1] for free, since colorsys output does.)"""
        for h, s, v in _grid():
            self.assertEqual(
                hsv_to_rgb(h, s, v), colorsys.hsv_to_rgb(h, s, v),
                f"mismatch at h={h}, s={s}, v={v}",
            )

    def test_array_matches_scalar_elementwise(self):
        """Vectorized call over arrays matches per-element scalar calls."""
        rng = np.random.default_rng(0)
        h = rng.random((7, 5))
        s = rng.random((7, 5))
        v = rng.random((7, 5))
        r, g, b = hsv_to_rgb(h, s, v)
        self.assertEqual(r.shape, (7, 5))
        for iy in range(7):
            for ix in range(5):
                er, eg, eb = colorsys.hsv_to_rgb(h[iy, ix], s[iy, ix], v[iy, ix])
                np.testing.assert_allclose(
                    [r[iy, ix], g[iy, ix], b[iy, ix]], [er, eg, eb], atol=1e-9,
                )

    def test_hue_wraps_outside_unit_interval(self):
        """Hue outside [0,1) wraps the same as the fractional part."""
        for base in (0.1, 0.37, 0.83):
            for offset in (-2.0, -1.0, 1.0, 3.0):
                got = tuple(float(c) for c in hsv_to_rgb(base + offset, 0.8, 0.9))
                want = tuple(float(c) for c in hsv_to_rgb(base, 0.8, 0.9))
                np.testing.assert_allclose(got, want, atol=1e-9)

    def test_bytes_parity_with_colorsys(self):
        """hsv_to_rgb_bytes matches int(colorsys * 255) and stays in [0,255]."""
        for h, s, v in _grid():
            er, eg, eb = colorsys.hsv_to_rgb(h, s, v)
            expected = (int(er * 255), int(eg * 255), int(eb * 255))
            got = hsv_to_rgb_bytes(h, s, v)
            self.assertEqual(got, expected, f"mismatch at h={h}, s={s}, v={v}")
            for c in got:
                self.assertIsInstance(c, int)
                self.assertGreaterEqual(c, 0)
                self.assertLessEqual(c, 255)

    def test_uint8_frame_known_colors(self):
        """hsv_to_rgb_uint8_frame maps known HSV to the expected uint8 RGB and
        produces a uniform (H, W, 3) uint8 frame. Covers all six hue sectors
        (primaries + secondaries) plus white/gray/black."""
        cases = {
            (0.0, 1.0, 1.0): (255, 0, 0),      # red
            (1 / 6, 1.0, 1.0): (255, 255, 0),  # yellow
            (1 / 3, 1.0, 1.0): (0, 255, 0),    # green
            (0.5, 1.0, 1.0): (0, 255, 255),    # cyan
            (2 / 3, 1.0, 1.0): (0, 0, 255),    # blue
            (0.0, 0.0, 1.0): (255, 255, 255),  # white
            (0.0, 0.0, 0.5): (127, 127, 127),  # gray (int(0.5*255))
            (0.0, 0.0, 0.0): (0, 0, 0),        # black
        }
        for (h, s, v), expected in cases.items():
            frame = hsv_to_rgb_uint8_frame(
                np.full((2, 3), h), np.full((2, 3), s), np.full((2, 3), v))
            self.assertEqual(frame.dtype, np.uint8)
            self.assertEqual(frame.shape, (2, 3, 3))
            self.assertTrue(np.all(frame == frame[0, 0]), f"non-uniform at {(h, s, v)}")
            self.assertEqual(
                tuple(int(c) for c in frame[0, 0]), expected,
                f"mismatch at h={h}, s={s}, v={v}",
            )

    def test_uint8_frame_broadcasts_scalar_channels(self):
        """A scalar saturation/value paired with an array hue broadcasts instead
        of crashing — regression guard for the 0-d boolean-mask IndexError."""
        hue = np.linspace(0.0, 0.99, 6).reshape(2, 3)
        frame = hsv_to_rgb_uint8_frame(hue, 0.8, 1.0)
        self.assertEqual(frame.shape, (2, 3, 3))
        self.assertEqual(frame.dtype, np.uint8)
        # Broadcasting must match passing fully-expanded arrays.
        full = hsv_to_rgb_uint8_frame(
            hue, np.full_like(hue, 0.8), np.full_like(hue, 1.0))
        np.testing.assert_array_equal(frame, full)


if __name__ == '__main__':
    unittest.main()
