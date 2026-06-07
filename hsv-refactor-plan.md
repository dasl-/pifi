# HSV-to-RGB Refactor Plan

## Context

~30 screensaver files each define their own private HSV-to-RGB conversion
function. They implement the same algorithm but vary in:
- Return type (list vs tuple vs numpy array)
- Output range (floats 0–1 vs bytes 0–255)
- Whether they apply `h % 1.0` first
- Scalar vs vectorized over numpy arrays

Goal: consolidate to one shared utility so the algorithm lives in one place.

## Design

**New file: `pifi/screensaver/colorutils.py`**

```python
def hsv_to_rgb(h, s, v):
    """Convert HSV to RGB. Works on Python floats or numpy arrays.
    Returns a 3-tuple (r, g, b) of floats in [0, 1] (or arrays of same)."""
```

- Uses `np.asarray(h)` + `np.select` for the 6-case hue branch (the same
  approach already used in `waveinterference.py:__hsv_array_to_rgb`).
- Vectorized for array inputs; works correctly for scalar inputs too
  (returns 0-d arrays, which behave like floats for our call patterns).
- Returns floats in [0, 1] — matches `colorsys.hsv_to_rgb` semantics.

## Inventory

The categorization here is by **what the caller does with the return value**,
not by what the local helper currently returns. Group membership controls the
post-refactor migration pattern.

### Vectorized callers (8) — return uint8 `(H, W, 3)` frame today

| File | Current symbol |
| --- | --- |
| `pifi/screensaver/moire.py` | module-level `_hsv_to_rgb_vec` |
| `pifi/screensaver/kaleidoscope.py` | module-level `_hsv_to_rgb_vec` |
| `pifi/screensaver/pixelsort.py` | module-level `_hsv_to_rgb_vec` |
| `pifi/screensaver/colorfield.py` | module-level `_hsv_to_rgb_vec` |
| `pifi/screensaver/noisegradient.py` | module-level `_hsv_to_rgb_vec` |
| `pifi/screensaver/domainwarp.py` | module-level `_hsv_to_rgb_vec` |
| `pifi/screensaver/waveinterference.py` | instance method `__hsv_array_to_rgb` |
| `pifi/screensaver/lenia.py` | static method `__hsv_to_rgb_vec` |

Migration pattern:
```python
r, g, b = hsv_to_rgb(hue, sat, val)
frame = (np.stack([r, g, b], axis=-1) * 255).astype(np.uint8)
```

### Group A — byte-using scalar callers (10)

The caller assigns into a uint8 frame, additively blends into a buffer in
0–255 range, or otherwise needs values 0–255. Scale at the call site.

`cosmicdream.py`, `lorenz.py`, `lavalamp.py`, `matrixrain.py`, `mandelbrot.py`,
`meltingclock.py`, `shadebobs.py`, `dvdbounce.py`, `unknownpleasures.py`,
`flowfield.py`

Migration:
```python
r, g, b = hsv_to_rgb(...)
rgb = [int(r * 255), int(g * 255), int(b * 255)]
```

For float-buffer callers (`shadebobs`, `flowfield` — buffers are float32 in
0–255 range) the `int()` is unnecessary:
```python
rgb = [r * 255, g * 255, b * 255]
```

### Group B — float-using scalar callers (5)

The caller blends into a float canvas in 0–1 range. No scaling needed.

| File | Caller pattern |
| --- | --- |
| `pifi/screensaver/phyllotaxis.py` | `self.__canvas[iy, ix, c] += r_c` (canvas is float64 0–1) |
| `pifi/screensaver/geodesic.py` | `intensity * base_color[c]` into float canvas 0–1 |
| `pifi/screensaver/selfhealingsquares.py` | local helper already returns floats; caller scales `(int(r*255), …)` |
| `pifi/screensaver/pendulumwaves.py` | uses tuple unpack; caller can adapt |
| `pifi/screensaver/perlinworms.py` | uses tuple unpack |
| `pifi/screensaver/stringart.py` | uses tuple unpack |

Migration: drop the local helper, import the shared one. Caller code
unchanged (still `r, g, b = hsv_to_rgb(...)`).

### Group C — float-rescaling callers (2)

Currently get bytes from the local helper, then divide by 255 to convert to
floats. After refactor, the divide goes away.

| File | Current call site | After refactor |
| --- | --- | --- |
| `pifi/screensaver/boids.py` | `np.array(rgb, dtype=np.float64) / 255.0` | `np.array(hsv_to_rgb(...), dtype=np.float64)` |
| `pifi/screensaver/metaballs.py` | `contribution * (rgb[c] / 255.0)` | `contribution * rgb[c]` (with `r, g, b = hsv_to_rgb(...)`) |

### Group D — module-level helpers already (3)

Already define a top-level `_hsv_to_rgb*` and import-style call. Just swap to
the shared import.

`opart.py` (`_hsv_to_rgb_scalar`), `doublependulum.py` (`_hsv_to_rgb_scalar`),
`spirograph.py` (`_hsv_to_rgb`)

### Group E — `inkinwater.py` (1)

Local helper returns float list `[v, v, v]`; caller assigns the list directly
to a float canvas. Drop local, import shared, change caller to:
```python
r, g, b = hsv_to_rgb(...)
color = [r, g, b]
```

## Open question

Group A's `[int(r * 255), int(g * 255), int(b * 255)]` boilerplate appears in
10 files. Worth a `hsv_to_rgb_bytes(h, s, v) -> (int, int, int)` helper in
`colorutils.py`, or keep the call sites explicit?

## Required new test

`test_screensaver_interface` only validates metadata and constructors — no
existing test ticks the real screensavers. A 30-file color refactor cannot
ride on that coverage. Add **before** starting the migration:

`tests/test_screensaver_smoke.py`:
```python
def test_each_screensaver_runs_100_ticks(self):
    """Smoke test: every screensaver advances 100 ticks without raising
    and produces a well-formed final frame."""
    Config.set('screensavers.tick_sleep', 0)   # no sleep between ticks
    Config.set('screensavers.timeout', 0)      # unlimited

    SKIP = {
        # Need external resources (video files, network, audio sources)
        'video_screensaver', 'nyc_subway', 'wfmu',
        'sonos_karaoke', 'airplay_karaoke',
    }

    for screensaver_id, cls in ScreensaverManager.SCREENSAVER_CLASSES.items():
        if screensaver_id in SKIP:
            continue
        with self.subTest(screensaver=screensaver_id):
            ss = cls()  # uses default LedFramePlayer; render_tick captures into BlackHoleFramePlayer
            try:
                last_frame = None
                for _ in range(100):
                    frame, alive = ss.render_tick()
                    if frame is not None:
                        last_frame = frame
                    if not alive:
                        break
                self.assertIsNotNone(last_frame, f"{screensaver_id} produced no frame")
                h = Config.get_or_throw('leds.display_height')
                w = Config.get_or_throw('leds.display_width')
                self.assertEqual(last_frame.dtype, np.uint8)
                # Allow either (H, W, 3) RGB or (H, W) monochrome
                self.assertIn(last_frame.shape, [(h, w, 3), (h, w)])
            finally:
                ss.teardown()
```

`render_tick()` already exists on `Screensaver`, calls `setup()` (idempotent),
swaps the LED frame player for a `BlackHoleFramePlayer` that captures the
frame, and increments `__last_tick`. So we get tick + frame capture for free.

Setting `tick_sleep=0` makes the suite finish in seconds for cheap
screensavers; expect ~minutes total wall time across the heavyweights
(`lenia`, `geodesic`, `purkinje`). If too slow, reduce to 30 ticks — still
catches NaN propagation, shape mismatches, and exceptions, just less coverage
of the steady state.

## Steps

1. Add `tests/test_screensaver_smoke.py` (above) and verify it passes on
   the current branch *before* any HSV changes.
2. Create `pifi/screensaver/colorutils.py` with `hsv_to_rgb()`.
3. Add `tests/test_colorutils.py` verifying parity against `colorsys.hsv_to_rgb`
   on a grid of (h, s, v) values, plus array-input correctness.
4. Migrate vectorized callers one file at a time (8 files). Run smoke test
   after each.
5. Migrate Group A byte-using callers (10 files). Smoke test after each batch.
6. Migrate Groups B, C, D, E (10 files). Smoke test after each.

## Critical files

- `pifi/screensaver/colorutils.py` (new)
- `tests/test_colorutils.py` (new)
- `tests/test_screensaver_smoke.py` (new — required before migration)
- All 31 files listed in the inventory above

## Verification

- `pytest tests/` — all 68 existing tests must still pass.
- The new smoke test must pass before AND after each migration step.
- Optional manual: `python utils/screensaver_preview.py --all --duration 5` to
  eyeball every screensaver in the terminal renderer for color regressions.
