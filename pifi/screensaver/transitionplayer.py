import random
import time

import numpy as np

from pifi.config import Config
from pifi.logger import Logger


# Transition effect functions.
# Each takes (from_frame, to_frame, progress, width, height) where progress is 0.0 to 1.0.
# Returns a blended [height, width, 3] uint8 numpy array.

def crossfade(from_frame, to_frame, progress, width, height):
    return (from_frame * (1 - progress) + to_frame * progress).astype(np.uint8)


def wipe_left(from_frame, to_frame, progress, width, height):
    result = from_frame.copy()
    boundary = int(progress * width)
    result[:, :boundary] = to_frame[:, :boundary]
    return result


def wipe_right(from_frame, to_frame, progress, width, height):
    result = from_frame.copy()
    boundary = width - int(progress * width)
    result[:, boundary:] = to_frame[:, boundary:]
    return result


def wipe_down(from_frame, to_frame, progress, width, height):
    result = from_frame.copy()
    boundary = int(progress * height)
    result[:boundary, :] = to_frame[:boundary, :]
    return result


def wipe_up(from_frame, to_frame, progress, width, height):
    result = from_frame.copy()
    boundary = height - int(progress * height)
    result[boundary:, :] = to_frame[boundary:, :]
    return result


def push_left(from_frame, to_frame, progress, width, height):
    result = np.zeros_like(from_frame)
    offset = int(progress * width)
    if offset < width:
        result[:, :width - offset] = from_frame[:, offset:]
    if offset > 0:
        result[:, width - offset:] = to_frame[:, :offset]
    return result


def push_right(from_frame, to_frame, progress, width, height):
    result = np.zeros_like(from_frame)
    offset = int(progress * width)
    if offset < width:
        result[:, offset:] = from_frame[:, :width - offset]
    if offset > 0:
        result[:, :offset] = to_frame[:, width - offset:]
    return result


def push_down(from_frame, to_frame, progress, width, height):
    result = np.zeros_like(from_frame)
    offset = int(progress * height)
    if offset < height:
        result[offset:, :] = from_frame[:height - offset, :]
    if offset > 0:
        result[:offset, :] = to_frame[height - offset:, :]
    return result


def push_up(from_frame, to_frame, progress, width, height):
    result = np.zeros_like(from_frame)
    offset = int(progress * height)
    if offset < height:
        result[:height - offset, :] = from_frame[offset:, :]
    if offset > 0:
        result[height - offset:, :] = to_frame[:offset, :]
    return result


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
    wipe_left,
    wipe_right,
    wipe_down,
    wipe_up,
    push_left,
    push_right,
    push_down,
    push_up,
]


class TransitionPlayer:

    def __init__(self, led_frame_player):
        self.__led_frame_player = led_frame_player
        self.__logger = Logger().set_namespace(self.__class__.__name__)

    def play_transition(self, from_screensaver=None, to_screensaver=None):
        """Play a transition between two screensavers.

        Both screensavers stay alive and animate during the transition.
        The to_screensaver is warmed up (setup + N ticks) while the
        from_screensaver keeps playing on the real display, then both
        frames are blended together for the visual transition.

        Can also be called with no screensavers for a static-frame
        transition (crossfade from the current display to black).
        """
        width = Config.get_or_throw('leds.display_width')
        height = Config.get_or_throw('leds.display_height')
        duration = Config.get('screensavers.transitions.duration', 1.0)
        tick_sleep = Config.get('screensavers.transitions.tick_sleep', 0.03)
        warm_up_ticks = Config.get('screensavers.transitions.warm_up_ticks', 60)
        num_steps = max(1, int(duration / tick_sleep)) if tick_sleep > 0 else 1

        from_frame = self.__led_frame_player.get_current_frame()
        if from_frame is None:
            from_frame = np.zeros([height, width, 3], np.uint8)
        # Monochrome video modes produce (H, W) frames. Expand to (H, W, 3)
        # so blending math works with consistent shapes.
        if from_frame.ndim == 2:
            from_frame = np.stack([from_frame] * 3, axis=-1)

        to_frame = np.zeros([height, width, 3], np.uint8)

        effect = self.__pick_effect(width, height)
        self.__logger.info(f"Playing transition: {effect.__name__}")

        from_tick = from_screensaver.get_last_tick() if from_screensaver else 0
        to_tick = 0
        from_alive = from_screensaver is not None
        to_alive = to_screensaver is not None

        if to_alive and to_screensaver.warmed_up:
            warm_up_ticks = 0

        # --- Warm-up phase ---
        to_frame, from_tick, to_tick, from_alive, to_alive = self.__run_warm_up(
            from_screensaver, to_screensaver,
            from_frame, from_tick, to_tick, from_alive, to_alive,
            warm_up_ticks, tick_sleep,
        )

        if to_alive:
            to_screensaver.warmed_up = True

        # --- Transition blend ---
        self.__run_blend(
            from_screensaver, to_screensaver,
            from_frame, to_frame, effect,
            from_tick, to_tick, from_alive, to_alive,
            num_steps, tick_sleep,
        )

        if to_screensaver is not None:
            to_screensaver.warm_up_ticks = to_tick

    def __run_warm_up(self, from_screensaver, to_screensaver,
                      from_frame, from_tick, to_tick, from_alive, to_alive,
                      warm_up_ticks, tick_sleep):
        """Warm up the to_screensaver while from_screensaver keeps playing.

        Returns (to_frame, from_tick, to_tick, from_alive, to_alive).
        """
        to_frame = np.zeros_like(from_frame)

        if not (to_alive and warm_up_ticks > 0):
            # No warm-up needed — grab initial frame if setup rendered one
            if to_alive:
                frame, _ = to_screensaver.render_tick(to_tick)
                if frame is not None:
                    to_frame = frame
                to_tick += 1
            return to_frame, from_tick, to_tick, from_alive, to_alive

        from_sleep = from_screensaver.get_tick_sleep() if from_alive else tick_sleep

        while to_tick < warm_up_ticks and to_alive:
            step_start = time.time()

            # Keep from_screensaver animating on the real display
            if from_alive:
                frame, alive = from_screensaver.render_tick(from_tick)
                if alive:
                    from_tick += 1
                    if frame is not None:
                        from_frame = frame
                        self.__led_frame_player.play_frame(frame)
                else:
                    from_alive = False

            # One warm-up tick per frame to stay within CPU budget
            frame, alive = to_screensaver.render_tick(to_tick)
            if alive:
                to_tick += 1
                if frame is not None:
                    to_frame = frame
            else:
                to_alive = False

            remaining = from_sleep - (time.time() - step_start)
            if remaining > 0:
                time.sleep(remaining)

        return to_frame, from_tick, to_tick, from_alive, to_alive

    def __run_blend(self, from_screensaver, to_screensaver,
                    from_frame, to_frame, effect,
                    from_tick, to_tick, from_alive, to_alive,
                    num_steps, tick_sleep):
        """Blend both screensavers together over num_steps."""
        from_sleep = from_screensaver.get_tick_sleep() if from_alive else tick_sleep
        to_sleep = to_screensaver.get_tick_sleep() if to_alive else tick_sleep
        # Prime accumulators so both screensavers tick on the first step,
        # maintaining continuity from the warm-up phase.
        from_accum = from_sleep if from_alive else 0
        to_accum = from_sleep if to_alive else 0  # start at from's rhythm

        for step in range(1, num_steps + 1):
            step_start = time.time()
            progress = step / num_steps

            from_accum += tick_sleep
            to_accum += tick_sleep

            if from_alive and from_accum >= from_sleep:
                from_accum -= from_sleep
                frame, alive = from_screensaver.render_tick(from_tick)
                if alive:
                    from_tick += 1
                    if frame is not None:
                        from_frame = frame
                else:
                    from_alive = False

            # Interpolate tick rate: from_sleep at start → to_sleep at end
            effective_to_sleep = from_sleep + (to_sleep - from_sleep) * progress
            if to_alive and to_accum >= effective_to_sleep:
                to_accum -= effective_to_sleep
                frame, alive = to_screensaver.render_tick(to_tick)
                if alive:
                    to_tick += 1
                    if frame is not None:
                        to_frame = frame
                else:
                    to_alive = False

            from_float = from_frame.astype(np.float32)
            to_float = to_frame.astype(np.float32)
            blended = effect(from_float, to_float, progress,
                             from_frame.shape[1], from_frame.shape[0])
            self.__led_frame_player.play_frame(blended.astype(np.uint8))

            remaining = tick_sleep - (time.time() - step_start)
            if remaining > 0:
                time.sleep(remaining)

    def __pick_effect(self, width, height):
        # Build the full list including factory effects
        effects = list(SIMPLE_EFFECTS)
        effects.append(_make_dissolve(width, height))
        effects.append(_make_spiral(width, height))
        return random.choice(effects)
