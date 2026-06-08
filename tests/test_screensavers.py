#!/usr/bin/env python3
"""
Tests covering every screensaver.

Two layers:
1. Interface/metadata contract — inheritance, the data returned by
   ScreensaverManager.get_all_screensavers(), and config-key hygiene in
   default_config.json.
2. End-to-end exercise — every screensaver is constructed and verified to call
   super().__init__(); every one that doesn't need external resources is then
   ticked 100 times via render_tick() and its output frame validated.

render_tick() captures frames into a BlackHoleFramePlayer instead of touching
LED hardware. We inject a BlackHoleFramePlayer at construction so no real
LedFramePlayer is ever built (it would initialize LED drivers and fail off-Pi)
— this matches how ScreensaverManager builds screensavers in production, which
always passes in a frame player rather than relying on the None default.
"""

import os
import subprocess
import sys
import unittest

import numpy as np
import pyjson5

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pifi.config import Config
from pifi.directoryutils import DirectoryUtils
from pifi.led.blackholeframeplayer import BlackHoleFramePlayer
from pifi.screensaver.screensaver import Screensaver
from pifi.screensaver.screensavermanager import ScreensaverManager
from pifi.screensaver.videoscreensaver import VideoScreensaver


def setUpModule():
    # Load the real default_config.json (tracked, and the source of every
    # per-screensaver default) straight into the Config singleton. We set the
    # private state directly rather than going through Config.load_config_if_not_loaded()
    # because config.json is gitignored (absent in CI) and because other test
    # modules leave a partial mock Config in the global singleton — seizing
    # control here keeps this suite deterministic regardless of run order.
    default_config_path = DirectoryUtils().root_dir + '/default_config.json'
    with open(default_config_path) as f:
        Config._load_for_test(pyjson5.decode(f.read()))

    # default_config.json ships display dimensions of 0 (real values come from
    # config.json on a device); set real ones so frames aren't empty.
    Config.set('leds.display_width', 32)
    Config.set('leds.display_height', 16)
    Config.set('screensavers.tick_sleep', 0)   # no sleep between ticks
    Config.set('screensavers.timeout', 0)      # unlimited


def tearDownModule():
    # Undo the singleton mutation from setUpModule so any test module that runs
    # after this one starts from a clean, unloaded Config rather than inheriting
    # our screensaver config. Reset all four mutable class attributes back to
    # their declared defaults (see Config in pifi/config.py).
    Config._reset_for_test()


# Screensavers that need external resources (video files, network, audio
# sources) to *tick*. They are still constructed and interface-checked; only
# the 100-tick render loop is skipped for them.
SKIP_TICK = {
    'video_screensaver', 'nyc_subway', 'wfmu',
    'sonos_karaoke', 'airplay_karaoke',
}


class TestScreensaverInterface(unittest.TestCase):
    """Interface contract and metadata for all screensavers."""

    def test_all_screensavers_inherit_from_screensaver(self):
        """Verify all screensavers inherit from Screensaver ABC."""
        for screensaver_id, cls in ScreensaverManager.SCREENSAVER_CLASSES.items():
            with self.subTest(screensaver=screensaver_id):
                self.assertTrue(
                    issubclass(cls, Screensaver),
                    f"{screensaver_id} ({cls.__name__}) does not inherit from Screensaver"
                )

    def test_get_all_screensavers_returns_valid_data(self):
        """Verify ScreensaverManager.get_all_screensavers() returns valid data."""
        all_screensavers = ScreensaverManager.get_all_screensavers()

        # Should return a list
        self.assertIsInstance(all_screensavers, list)

        # Should have at least 23 screensavers (all the non-video ones)
        self.assertGreaterEqual(len(all_screensavers), 23)

        # Each entry should have required fields
        for ss in all_screensavers:
            with self.subTest(screensaver=ss.get('id', 'unknown')):
                self.assertIn('id', ss)
                self.assertIn('name', ss)
                self.assertIn('description', ss)

                self.assertIsInstance(ss['id'], str)
                self.assertIsInstance(ss['name'], str)
                self.assertIsInstance(ss['description'], str)

                self.assertGreater(len(ss['id']), 0)
                self.assertGreater(len(ss['name']), 0)
                self.assertGreater(len(ss['description']), 0)

    def test_no_duplicate_ids(self):
        """Verify there are no duplicate screensaver IDs."""
        all_screensavers = ScreensaverManager.get_all_screensavers()
        ids = [ss['id'] for ss in all_screensavers]
        unique_ids = set(ids)
        self.assertEqual(
            len(ids), len(unique_ids),
            f"Duplicate IDs found: {[id for id in ids if ids.count(id) > 1]}"
        )

    def test_config_keys_match_screensaver_ids(self):
        """Verify screensavers.configs keys in default_config.json match screensaver IDs.

        The settings API keys configs by screensaver ID, so if default_config.json
        uses 'airplaykaraoke' but get_id() returns 'airplay_karaoke', overrides
        saved via the UI will be silently ignored.
        """
        default_config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'default_config.json'
        )
        with open(default_config_path) as f:
            default_config = pyjson5.decode(f.read())

        config_keys = set(default_config.get('screensavers', {}).get('configs', {}).keys())
        screensaver_ids = set(ScreensaverManager.SCREENSAVER_CLASSES.keys())

        # Every config key should correspond to a real screensaver class
        for key in config_keys:
            with self.subTest(config_key=key):
                self.assertIn(
                    key, screensaver_ids,
                    f"Config key '{key}' in screensavers.configs has no matching screensaver class."
                )

        # Every screensaver class should have a config key
        for screensaver_id in screensaver_ids:
            with self.subTest(screensaver=screensaver_id):
                self.assertIn(
                    screensaver_id, config_keys,
                    f"Screensaver '{screensaver_id}' has no matching key in screensavers.configs."
                )

    def test_config_keys_in_alphabetical_order(self):
        """Screensavers.configs keys should be sorted alphabetically.

        Keeping a deterministic order makes diffs cleaner and makes a key
        easy to find when scanning default_config.json by hand.
        """
        default_config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'default_config.json'
        )
        with open(default_config_path) as f:
            default_config = pyjson5.decode(f.read())

        keys = list(default_config.get('screensavers', {}).get('configs', {}).keys())
        self.assertEqual(
            keys, sorted(keys),
            f"screensavers.configs keys are not in alphabetical order. Expected: {sorted(keys)}"
        )


class TestScreensaverRendering(unittest.TestCase):
    """Construct, interface-check, and render every screensaver.

    One pass over all screensavers, constructing each exactly once: every one is
    interface-checked (is a Screensaver with play(), called super().__init__());
    those that don't need external resources are then ticked 100 times and their
    output frame validated. The external-resource screensavers (SKIP_TICK) are
    still constructed and interface-checked — only their render loop is skipped.
    """

    def test_each_screensaver_constructs_and_renders(self):
        h = Config.get_or_throw('leds.display_height')
        w = Config.get_or_throw('leds.display_width')
        for screensaver_id, cls in ScreensaverManager.SCREENSAVER_CLASSES.items():
            with self.subTest(screensaver=screensaver_id):
                # Inject a BlackHoleFramePlayer so __init__ never builds a real
                # LedFramePlayer (which would touch hardware). render_tick() swaps
                # in its own BlackHoleFramePlayer during the tick regardless;
                # screensavers only ever call play_frame/fade_to_frame.
                ss = cls(led_frame_player=BlackHoleFramePlayer())

                # Interface contract (all screensavers, including SKIP_TICK ones).
                self.assertIsInstance(
                    ss, Screensaver, f"{screensaver_id} instance is not a Screensaver")
                self.assertTrue(
                    hasattr(ss, 'play'), f"{screensaver_id} instance missing play method")
                # __screensaver_base_init_called is set only by Screensaver.__init__,
                # so its presence proves the subclass called super().__init__().
                self.assertTrue(
                    getattr(ss, '_Screensaver__screensaver_base_init_called', False),
                    f"{screensaver_id} does not call super().__init__()")

                # Ticking needs external resources for these; construction above
                # is enough to cover them.
                if screensaver_id in SKIP_TICK:
                    continue

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


class TestSpecificScreensavers(unittest.TestCase):
    """Behavior specific to individual screensaver implementations."""

    def test_video_screensaver_uses_config(self):
        """Verify VideoScreensaver gets video_list from Config, not constructor."""
        instance = VideoScreensaver(led_frame_player=BlackHoleFramePlayer())
        self.assertTrue(hasattr(instance, 'video_list'))
        self.assertIsInstance(instance.video_list, list)

    def test_video_screensaver_handles_empty_list(self):
        """Verify VideoScreensaver.play() handles empty video list gracefully."""
        instance = VideoScreensaver(led_frame_player=BlackHoleFramePlayer())

        # Should have empty list from config
        self.assertEqual(instance.video_list, [])

        # play() should return gracefully without error (empty list => _tick stops)
        try:
            instance.play()
        except Exception as e:
            self.fail(f"VideoScreensaver.play() raised exception with empty video_list: {e}")


class TestScreensaverPreviewIntegration(unittest.TestCase):
    """Integration tests for the screensaver_preview.py command-line tool."""

    def test_preview_list_command(self):
        """Verify screensaver_preview.py --list runs successfully and shows all screensavers."""
        result = subprocess.run(
            ['python3', 'utils/screensaver_preview.py', '--list'],
            capture_output=True,
            text=True,
            timeout=10
        )

        # Should exit successfully
        self.assertEqual(result.returncode, 0, f"Command failed with stderr: {result.stderr}")

        # Should have output
        self.assertGreater(len(result.stdout), 0, "No output from --list command")

        # Should contain header
        self.assertIn('Available screensavers:', result.stdout)

        # Should list all 24 screensavers (verify a few key ones)
        expected_screensavers = [
            'boids',
            'aurora',
            'game_of_life',
            'cosmic_dream',
            'starfield',
            'video_screensaver',
        ]

        for screensaver in expected_screensavers:
            self.assertIn(screensaver, result.stdout,
                         f"Expected screensaver '{screensaver}' not in list output")

        # Count lines (should have at least 24 screensaver lines + header)
        lines = result.stdout.strip().split('\n')
        # Filter out empty lines and the header
        screensaver_lines = [line for line in lines if line.strip() and not line.startswith('Available')]
        self.assertGreaterEqual(len(screensaver_lines), 24,
                               f"Expected at least 24 screensavers, found {len(screensaver_lines)}")

    def test_preview_unknown_screensaver(self):
        """Verify screensaver_preview.py fails gracefully with unknown screensaver."""
        result = subprocess.run(
            ['python3', 'utils/screensaver_preview.py', 'nonexistent_screensaver'],
            capture_output=True,
            text=True,
            timeout=10
        )

        # Should fail
        self.assertNotEqual(result.returncode, 0, "Expected non-zero exit code for unknown screensaver")

        # Should have error message
        output = result.stdout + result.stderr
        self.assertIn('Unknown screensaver', output)

    def test_preview_game_of_life(self):
        """Verify we can successfully preview game_of_life screensaver."""
        # Run the screensaver for a short time then kill it
        # This verifies the entire pipeline works: loading, instantiating, and running
        try:
            result = subprocess.run(
                ['python3', 'utils/screensaver_preview.py', 'game_of_life', '--width', '16', '--height', '16'],
                capture_output=True,
                text=True,
                timeout=2  # Let it run for 2 seconds then timeout
            )
            # If it completes within 2 seconds, that's also fine (shouldn't happen but acceptable)
            self.assertEqual(result.returncode, 0, f"Command failed with stderr: {result.stderr}")
        except subprocess.TimeoutExpired:
            # This is expected - the screensaver runs indefinitely
            # The fact that it timed out (rather than crashing) means it's working
            pass


if __name__ == '__main__':
    unittest.main()
