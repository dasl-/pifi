#!/usr/bin/env python3
"""Unit tests for pifi.screensaver.colorutils."""

import colorsys
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pifi.screensaver.colorutils import hsv_to_rgb, hsv_to_rgb_bytes


def _grid():
    """A grid of (h, s, v) triples spanning [0, 1)."""
    for h in np.linspace(0.0, 0.999, 23):
        for s in np.linspace(0.0, 1.0, 11):
            for v in np.linspace(0.0, 1.0, 11):
                yield float(h), float(s), float(v)


class TestColorUtils(unittest.TestCase):

    def test_scalar_parity_with_colorsys(self):
        """hsv_to_rgb matches colorsys.hsv_to_rgb across a grid of h in [0,1)."""
        for h, s, v in _grid():
            expected = colorsys.hsv_to_rgb(h, s, v)
            r, g, b = hsv_to_rgb(h, s, v)
            np.testing.assert_allclose(
                [float(r), float(g), float(b)], expected, atol=1e-9,
                err_msg=f"mismatch at h={h}, s={s}, v={v}",
            )

    def test_scalar_returns_values_in_unit_range(self):
        for h, s, v in _grid():
            r, g, b = hsv_to_rgb(h, s, v)
            for c in (r, g, b):
                self.assertGreaterEqual(float(c), 0.0)
                self.assertLessEqual(float(c), 1.0)

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


if __name__ == '__main__':
    unittest.main()
