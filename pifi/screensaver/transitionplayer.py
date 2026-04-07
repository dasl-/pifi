import random
import time

import numpy as np

from pifi.config import Config
from pifi.logger import Logger
from pifi.screensaver.screensaver import FrameCapture


# Transition effect functions.
# Each takes (from_frame, to_frame, progress, width, height) where progress is 0.0 to 1.0.
# Returns a blended [height, width, 3] uint8 numpy array.

def _ease(t):
    """Smoothstep ease-in-out: 3t² - 2t³"""
    return t * t * (3 - 2 * t)


def crossfade(from_frame, to_frame, progress, width, height):
    return (from_frame * (1 - progress) + to_frame * progress).astype(np.uint8)


def _make_wipe(width, height):
    """Factory that picks a random wipe direction."""
    direction = random.choice(['left', 'right', 'up', 'down'])

    def wipe(from_frame, to_frame, progress, width, height):
        result = from_frame.copy()
        p = _ease(progress)
        if direction == 'left':
            boundary = int(p * width)
            result[:, :boundary] = to_frame[:, :boundary]
        elif direction == 'right':
            boundary = width - int(p * width)
            result[:, boundary:] = to_frame[:, boundary:]
        elif direction == 'down':
            boundary = int(p * height)
            result[:boundary, :] = to_frame[:boundary, :]
        else:
            boundary = height - int(p * height)
            result[boundary:, :] = to_frame[boundary:, :]
        return result

    wipe.__name__ = f'wipe_{direction}'
    return wipe


def _make_push(width, height):
    """Factory that picks a random push direction."""
    direction = random.choice(['left', 'right', 'up', 'down'])

    def push(from_frame, to_frame, progress, width, height):
        result = np.zeros_like(from_frame)
        p = _ease(progress)
        if direction == 'left':
            offset = int(p * width)
            if offset < width:
                result[:, :width - offset] = from_frame[:, offset:]
            if offset > 0:
                result[:, width - offset:] = to_frame[:, :offset]
        elif direction == 'right':
            offset = int(p * width)
            if offset < width:
                result[:, offset:] = from_frame[:, :width - offset]
            if offset > 0:
                result[:, :offset] = to_frame[:, width - offset:]
        elif direction == 'down':
            offset = int(p * height)
            if offset < height:
                result[offset:, :] = from_frame[:height - offset, :]
            if offset > 0:
                result[:offset, :] = to_frame[height - offset:, :]
        else:
            offset = int(p * height)
            if offset < height:
                result[:height - offset, :] = from_frame[offset:, :]
            if offset > 0:
                result[height - offset:, :] = to_frame[:offset, :]
        return result

    push.__name__ = f'push_{direction}'
    return push


def _make_wave(width, height):
    """Factory for wavy dream/ripple transition.

    The from_frame gets increasingly distorted by sine-wave displacement
    while the to_frame crossfades in over the distortion.
    """
    # Pre-compute base coordinate grids
    ys_grid, xs_grid = np.mgrid[0:height, 0:width]
    # Random wave parameters for variety
    freq_x = random.uniform(1.5, 3.0)
    freq_y = random.uniform(1.5, 3.0)
    phase_x = random.uniform(0, 2 * np.pi)
    phase_y = random.uniform(0, 2 * np.pi)

    def wave(from_frame, to_frame, progress, width, height):
        # Distortion amplitude ramps up then back down (peaks around 0.4)
        amp = progress * (1 - progress) * 4
        max_shift = max(width, height) * 0.3
        shift = amp * max_shift

        # Apply sine displacement to both axes
        dx = (np.sin(ys_grid * freq_y / height * 2 * np.pi + phase_y + progress * 6) * shift).astype(int)
        dy = (np.sin(xs_grid * freq_x / width * 2 * np.pi + phase_x + progress * 6) * shift).astype(int)

        src_x = np.clip(xs_grid + dx, 0, width - 1)
        src_y = np.clip(ys_grid + dy, 0, height - 1)

        warped_from = from_frame[src_y, src_x]

        # Crossfade from warped source to clean destination
        blend = _ease(progress)
        return (warped_from * (1 - blend) + to_frame * blend).astype(np.uint8)

    wave.__name__ = 'wave'
    return wave


def _make_pixelate(width, height):
    """Factory for pixelate transition.

    From_frame gets increasingly pixelated (mosaic), then at the midpoint
    switches to the to_frame and de-pixelates back to full resolution.
    """
    ys_grid, xs_grid = np.mgrid[0:height, 0:width]
    max_block = max(2, max(width, height) // 2)

    def pixelate(from_frame, to_frame, progress, width, height):
        if progress < 0.5:
            # First half: pixelate from_frame more and more
            t = progress * 2  # 0→1
            block = max(1, int(1 + _ease(t) * (max_block - 1)))
            src = from_frame
        else:
            # Second half: de-pixelate to_frame
            t = (1 - progress) * 2  # 1→0
            block = max(1, int(1 + _ease(t) * (max_block - 1)))
            src = to_frame

        # Quantize coordinates to block grid, then sample
        bx = (xs_grid // block) * block + block // 2
        by = (ys_grid // block) * block + block // 2
        bx = np.clip(bx, 0, width - 1)
        by = np.clip(by, 0, height - 1)
        return src[by, bx].astype(np.uint8)

    pixelate.__name__ = 'pixelate'
    return pixelate


def _make_melt(width, height):
    """Factory for melt/drip transition.

    Columns of the from_frame drip downward at randomized speeds,
    revealing the to_frame underneath.
    """
    # Each column gets a random delay and speed
    col_delay = np.random.uniform(0.0, 0.35, size=width)
    col_speed = np.random.uniform(0.8, 1.5, size=width)
    ys_grid = np.arange(height).reshape(-1, 1)

    def melt(from_frame, to_frame, progress, width, height):
        # Per-column drop amount: how far down the column has shifted
        t = np.clip((progress - col_delay) * col_speed / (1 - col_delay + 1e-6), 0, 1)
        drop = (_ease_vec(t) * height * 1.5).astype(int)  # overshoot so columns fully clear

        result = to_frame.copy()
        # For each column, shift from_frame pixels down by drop amount
        for x in range(width):
            d = drop[x]
            if d < height:
                # Pixels that haven't fallen off screen yet
                result[d:, x] = from_frame[:height - d, x]

        return result.astype(np.uint8)

    melt.__name__ = 'melt'
    return melt


def _ease_vec(t):
    """Vectorized smoothstep for numpy arrays."""
    return t * t * (3 - 2 * t)


def _make_zoom(width, height):
    """Factory for zoom transition.

    From_frame zooms in (expanding from center) while fading out,
    revealing the to_frame underneath.
    """
    ys_grid, xs_grid = np.mgrid[0:height, 0:width]
    cy, cx = height / 2, width / 2

    def zoom(from_frame, to_frame, progress, width, height):
        p = _ease(progress)
        # Scale factor: 1.0 → ~3.0 (zooming in)
        scale = 1.0 + p * 2.0

        # Map each output pixel back to source coordinates (inverse zoom from center)
        src_x = ((xs_grid - cx) / scale + cx).astype(int)
        src_y = ((ys_grid - cy) / scale + cy).astype(int)

        # Pixels that map outside the frame become transparent (show to_frame)
        in_bounds = (src_x >= 0) & (src_x < width) & (src_y >= 0) & (src_y < height)
        src_x_safe = np.clip(src_x, 0, width - 1)
        src_y_safe = np.clip(src_y, 0, height - 1)

        zoomed = from_frame[src_y_safe, src_x_safe]

        # Blend: zoomed from_frame fades out, to_frame shows through
        result = to_frame.copy()
        alpha = (1 - p) * in_bounds.astype(np.float32)
        result = (zoomed * alpha[..., np.newaxis] + to_frame * (1 - alpha[..., np.newaxis])).astype(np.uint8)
        return result

    zoom.__name__ = 'zoom'
    return zoom


def _make_dissolve(width, height):
    """Factory that pre-shuffles pixel order for dissolve effect."""
    total_pixels = width * height
    indices = np.arange(total_pixels)
    np.random.shuffle(indices)

    def dissolve(from_frame, to_frame, progress, width, height):
        result = from_frame.copy()
        num_switched = int(progress * total_pixels)
        switched = indices[:num_switched]
        ys, xs = np.divmod(switched, width)
        result[ys, xs] = to_frame[ys, xs]
        return result

    return dissolve


def _make_spiral(width, height):
    """Factory that pre-computes spiral order from center outward."""
    cy, cx = height / 2, width / 2
    coords = np.array([(y, x) for y in range(height) for x in range(width)])
    # Sort by angle, then by distance, to create a spiral pattern
    dy = coords[:, 0] - cy
    dx = coords[:, 1] - cx
    angles = np.arctan2(dy, dx)
    distances = np.sqrt(dy ** 2 + dx ** 2)
    max_dist = distances.max() if distances.max() > 0 else 1
    # Combine distance and angle to get spiral ordering:
    # each "ring" of distance completes a full angular sweep
    spiral_key = distances / max_dist + angles / (2 * np.pi * 3)
    order = np.argsort(spiral_key)

    def spiral(from_frame, to_frame, progress, width, height):
        result = from_frame.copy()
        total_pixels = width * height
        num_switched = int(progress * total_pixels)
        switched = order[:num_switched]
        ys = coords[switched, 0]
        xs = coords[switched, 1]
        result[ys, xs] = to_frame[ys, xs]
        return result

    return spiral


# Simple effects that don't need factories
SIMPLE_EFFECTS = [
    crossfade,
]


class TransitionPlayer:

    def __init__(self, led_frame_player):
        self.__led_frame_player = led_frame_player
        self.__logger = Logger().set_namespace(self.__class__.__name__)

    def play_transition(self, from_frame=None, to_frame=None,
                        from_screensaver=None, to_screensaver=None):
        width = Config.get_or_throw('leds.display_width')
        height = Config.get_or_throw('leds.display_height')
        duration = Config.get('screensavers.transitions.duration', 1.0)
        tick_sleep = Config.get('screensavers.transitions.tick_sleep', 0.03)
        warm_up_ticks = Config.get('screensavers.transitions.warm_up_ticks', 60)
        num_steps = max(1, int(duration / tick_sleep)) if tick_sleep > 0 else 1

        if from_frame is None:
            from_frame = self.__led_frame_player.get_current_frame()
        if from_frame is None:
            from_frame = np.zeros([height, width, 3], np.uint8)
        if from_frame.ndim == 2:
            from_frame = np.stack([from_frame] * 3, axis=-1)

        if to_frame is None:
            to_frame = np.zeros([height, width, 3], np.uint8)
        if to_frame.ndim == 2:
            to_frame = np.stack([to_frame] * 3, axis=-1)

        # Pick a random effect - include factory-generated effects
        effect = self.__pick_effect(width, height)

        self.__logger.info(f"Playing transition: {effect.__name__}")

        # Set up live ticking if screensaver objects are provided
        from_capture = None
        to_capture = None
        from_tick = 0
        to_tick = 0
        from_alive = from_screensaver is not None
        to_alive = to_screensaver is not None

        if from_alive:
            from_capture = FrameCapture()
            from_capture.play_frame(from_frame)
            from_tick = getattr(from_screensaver, '_last_tick', 0)
            from_screensaver._led_frame_player = from_capture

        if to_alive:
            to_capture = FrameCapture()
            to_screensaver._led_frame_player = to_capture
            # If not warmed up, run _setup() here (renders to capture, not
            # the real display). Warm-up ticks happen below while the
            # from_screensaver keeps playing on screen.
            if not to_screensaver._warmed_up:
                to_screensaver._setup()
                to_screensaver._warmed_up = True
            else:
                to_capture.play_frame(to_frame)
                warm_up_ticks = 0  # already warmed up

        # --- Warm-up phase ---
        # Keep the from_screensaver playing on screen at its natural rate
        # while building up the to_screensaver's state one tick per frame.
        # This finishes all warm-up BEFORE the transition blend starts.
        if to_alive and warm_up_ticks > 0:
            from_sleep = from_screensaver._tick_sleep if from_alive else tick_sleep

            while to_tick < warm_up_ticks and to_alive:
                step_start = time.time()

                # Keep from_screensaver animating on the real display
                if from_alive:
                    if from_screensaver._tick(from_tick) is not False:
                        from_tick += 1
                        self.__led_frame_player.play_frame(from_capture.get_current_frame())
                    else:
                        from_alive = False

                # One warm-up tick per frame to stay within CPU budget
                if to_screensaver._tick(to_tick) is not False:
                    to_tick += 1
                else:
                    to_alive = False

                remaining = from_sleep - (time.time() - step_start)
                if remaining > 0:
                    time.sleep(remaining)

            if to_alive:
                to_frame = to_capture.get_current_frame()

        # --- Transition blend ---
        # Both screensavers are now ready. The to_screensaver's tick rate
        # interpolates from the from_screensaver's rate to its own so the
        # tempo change is gradual rather than an abrupt shift.
        from_sleep = from_screensaver._tick_sleep if from_alive else tick_sleep
        to_sleep = to_screensaver._tick_sleep if to_alive else tick_sleep
        from_accum = from_sleep if from_alive else 0
        to_accum = from_sleep if to_alive else 0  # start at from's rhythm

        try:
            for step in range(1, num_steps + 1):
                step_start = time.time()
                progress = step / num_steps

                from_accum += tick_sleep
                to_accum += tick_sleep

                if from_alive and from_accum >= from_sleep:
                    from_accum -= from_sleep
                    if from_screensaver._tick(from_tick) is not False:
                        from_tick += 1
                        from_frame = from_capture.get_current_frame()
                    else:
                        from_alive = False

                # Interpolate tick rate: from_sleep at start → to_sleep at end
                effective_to_sleep = from_sleep + (to_sleep - from_sleep) * progress
                if to_alive and to_accum >= effective_to_sleep:
                    to_accum -= effective_to_sleep
                    if to_screensaver._tick(to_tick) is not False:
                        to_tick += 1
                        to_frame = to_capture.get_current_frame()
                    else:
                        to_alive = False

                from_float = from_frame.astype(np.float32)
                to_float = to_frame.astype(np.float32)
                blended = effect(from_float, to_float, progress, width, height)
                self.__led_frame_player.play_frame(blended.astype(np.uint8))

                remaining = tick_sleep - (time.time() - step_start)
                if remaining > 0:
                    time.sleep(remaining)
        finally:
            # Restore real frame player so play() works after transition
            if from_screensaver is not None:
                from_screensaver._led_frame_player = self.__led_frame_player
            if to_screensaver is not None:
                to_screensaver._led_frame_player = self.__led_frame_player
                to_screensaver._warm_up_ticks = to_tick

    def __pick_effect(self, width, height):
        # Build the full list including factory effects
        effects = list(SIMPLE_EFFECTS)
        effects.append(_make_wipe(width, height))
        effects.append(_make_push(width, height))
        effects.append(_make_wave(width, height))
        effects.append(_make_pixelate(width, height))
        effects.append(_make_melt(width, height))
        effects.append(_make_zoom(width, height))
        effects.append(_make_dissolve(width, height))
        effects.append(_make_spiral(width, height))
        return random.choice(effects)
