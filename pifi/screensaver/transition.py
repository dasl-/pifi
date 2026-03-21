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

    def play_transition(self, from_frame=None, to_frame=None):
        width = Config.get_or_throw('leds.display_width')
        height = Config.get_or_throw('leds.display_height')
        duration = Config.get('screensavers.transitions.duration', 1.0)
        num_steps = Config.get('screensavers.transitions.num_steps', 30)

        if from_frame is None:
            from_frame = self.__led_frame_player.get_current_frame()
        if from_frame is None:
            from_frame = np.zeros([height, width, 3], np.uint8)

        if to_frame is None:
            to_frame = np.zeros([height, width, 3], np.uint8)

        # Convert to float32 for blending math
        from_float = from_frame.astype(np.float32)
        to_float = to_frame.astype(np.float32)

        # Pick a random effect - include factory-generated effects
        effect = self.__pick_effect(width, height)

        self.__logger.info(f"Playing transition: {effect.__name__}")

        sleep_time = duration / num_steps
        for step in range(1, num_steps + 1):
            progress = step / num_steps
            blended = effect(from_float, to_float, progress, width, height)
            self.__led_frame_player.play_frame(blended.astype(np.uint8))
            time.sleep(sleep_time)

    def __pick_effect(self, width, height):
        # Build the full list including factory effects
        effects = list(SIMPLE_EFFECTS)
        effects.append(_make_dissolve(width, height))
        effects.append(_make_spiral(width, height))
        return random.choice(effects)
