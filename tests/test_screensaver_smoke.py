#!/usr/bin/env python3
"""
Smoke test for every screensaver.

Ticks each screensaver 100 times via render_tick() (which captures frames into
a BlackHoleFramePlayer instead of touching LED hardware) and asserts it advances
without raising and produces a well-formed final frame. This is the safety net
for the HSV-to-RGB consolidation refactor — see hsv-refactor-plan.md.
"""

import os
import sys
import unittest

import numpy as np
import pyjson5

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pifi.config import Config
from pifi.directoryutils import DirectoryUtils
from pifi.led.blackholeframeplayer import BlackHoleFramePlayer
from pifi.screensaver.screensavermanager import ScreensaverManager


def setUpModule():
    # Load the real default_config.json (tracked, and the source of every
    # per-screensaver default) straight into the Config singleton. We set the
    # private state directly rather than going through Config.load_config_if_not_loaded()
    # because config.json is gitignored (absent in CI) and because other test
    # modules leave a partial mock Config in the global singleton — seizing
    # control here keeps this suite deterministic regardless of run order.
    default_config_path = DirectoryUtils().root_dir + '/default_config.json'
    with open(default_config_path) as f:
        Config._Config__config = pyjson5.decode(f.read())  # pyright: ignore[reportAttributeAccessIssue]
    Config._Config__is_loaded = True  # pyright: ignore[reportAttributeAccessIssue]

    # default_config.json ships display dimensions of 0 (real values come from
    # config.json on a device); set real ones so frames aren't empty.
    Config.set('leds.display_width', 32)
    Config.set('leds.display_height', 16)
    Config.set('screensavers.tick_sleep', 0)   # no sleep between ticks
    Config.set('screensavers.timeout', 0)      # unlimited


def tearDownModule():
    # Undo the singleton mutation from setUpModule so any test module that runs
    # after this one starts from a clean, unloaded Config (its initial state)
    # rather than inheriting our screensaver config.
    Config._Config__config = {}  # pyright: ignore[reportAttributeAccessIssue]
    Config._Config__is_loaded = False  # pyright: ignore[reportAttributeAccessIssue]


class TestScreensaverSmoke(unittest.TestCase):

    # Need external resources (video files, network, audio sources).
    SKIP = {
        'video_screensaver', 'nyc_subway', 'wfmu',
        'sonos_karaoke', 'airplay_karaoke',
    }

    def test_each_screensaver_runs_100_ticks(self):
        """Every screensaver advances 100 ticks without raising and produces a
        well-formed final frame."""
        for screensaver_id, cls in ScreensaverManager.SCREENSAVER_CLASSES.items():
            if screensaver_id in self.SKIP:
                continue
            with self.subTest(screensaver=screensaver_id):
                # Pass a BlackHoleFramePlayer at construction so we never
                # instantiate the real LedFramePlayer (which initializes LED
                # hardware drivers and fails off-Pi). render_tick() swaps in its
                # own BlackHoleFramePlayer during the tick regardless; the one we
                # pass just keeps __init__ off the hardware path. It's sufficient
                # because screensavers only ever call play_frame/fade_to_frame.
                ss = cls(led_frame_player=BlackHoleFramePlayer())
                try:
                    last_frame = None
                    for _ in range(100):
                        frame, alive = ss.render_tick()
                        if frame is not None:
                            last_frame = frame
                        if not alive:
                            break
                    if last_frame is None:
                        self.fail(f"{screensaver_id} produced no frame")
                    h = Config.get_or_throw('leds.display_height')
                    w = Config.get_or_throw('leds.display_width')
                    # Integer dtype (not necessarily uint8 — cyclic_automaton
                    # emits int64). A float frame would mean a screensaver forgot
                    # to scale/cast, which is exactly the kind of HSV regression
                    # this guards against.
                    self.assertTrue(
                        np.issubdtype(last_frame.dtype, np.integer),
                        f"{screensaver_id} emitted non-integer frame dtype {last_frame.dtype}",
                    )
                    # Allow either (H, W, 3) RGB or (H, W) monochrome.
                    self.assertIn(last_frame.shape, [(h, w, 3), (h, w)])
                finally:
                    ss.teardown()


if __name__ == '__main__':
    unittest.main()
