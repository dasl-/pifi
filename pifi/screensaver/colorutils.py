import colorsys
from typing import Any

import numpy as np


def hsv_to_rgb(h, s, v) -> tuple[Any, Any, Any]:
    """Convert HSV to RGB, vectorized over numpy arrays (also works on scalars).

    h, s, v may be Python floats or numpy arrays. Returns a 3-tuple (r, g, b) of
    floats in [0, 1]; for array inputs the components are arrays of the same
    shape, for scalar inputs they are Python floats.

    Hue is wrapped into [0, 1) first, so the result matches colorsys.hsv_to_rgb
    for h in [0, 1) and wraps correctly for hue outside that range. Use this for
    array work and for callers that consume floats directly; use
    hsv_to_rgb_bytes() for scalar callers that need 0-255 ints.

    Two paths, chosen by input type:
    - Scalar inputs use a pure-Python colorsys call. The vectorized path is
      ~250x slower per call for scalars (measured on the Pi), and several callers
      convert one color at a time inside tight loops.
    - Array inputs use boolean masking rather than np.select. np.select evaluates
      every branch for every element and is ~1.5x slower than masking on the Pi's
      ARM CPU (even though it's faster on x86); the Pi is the target hardware.
    """
    if not (isinstance(h, np.ndarray) or isinstance(s, np.ndarray)
            or isinstance(v, np.ndarray)):
        return colorsys.hsv_to_rgb(h % 1.0, s, v)

    h = np.asarray(h, dtype=np.float64) % 1.0
    s = np.asarray(s, dtype=np.float64)
    v = np.asarray(v, dtype=np.float64)

    i = (h * 6.0).astype(np.int64)
    f = (h * 6.0) - i
    p = v * (1.0 - s)
    q = v * (1.0 - s * f)
    t = v * (1.0 - s * (1.0 - f))
    i = i % 6

    r = np.zeros_like(h)
    g = np.zeros_like(h)
    b = np.zeros_like(h)
    m = i == 0; r[m] = v[m]; g[m] = t[m]; b[m] = p[m]
    m = i == 1; r[m] = q[m]; g[m] = v[m]; b[m] = p[m]
    m = i == 2; r[m] = p[m]; g[m] = v[m]; b[m] = t[m]
    m = i == 3; r[m] = p[m]; g[m] = q[m]; b[m] = v[m]
    m = i == 4; r[m] = t[m]; g[m] = p[m]; b[m] = v[m]
    m = i == 5; r[m] = v[m]; g[m] = p[m]; b[m] = q[m]
    return r, g, b


def hsv_to_rgb_bytes(h, s, v) -> tuple[int, int, int]:
    """Scalar HSV to RGB as a 3-tuple (r, g, b) of Python ints in [0, 255].

    Pure-Python (colorsys) scalar path for the many call sites that assign into
    a uint8 frame or blend in 0-255 range. Hue is wrapped into [0, 1) to match
    hsv_to_rgb().
    """
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, s, v)
    return int(r * 255), int(g * 255), int(b * 255)
