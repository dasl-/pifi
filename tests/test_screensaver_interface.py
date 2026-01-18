#!/usr/bin/env python3
"""
Unit tests for the Screensaver interface.

Verifies that all screensavers:
1. Inherit from the Screensaver ABC
2. Implement required abstract methods (play, get_id, get_name, get_description)
3. Use the standard constructor signature
4. Return correct metadata types
"""

import unittest
import sys
import os
import subprocess
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pifi.screensaver.screensaver import Screensaver
from pifi.screensaver.screensavermanager import ScreensaverManager
from pifi.config import Config
from pifi.led.ledframeplayer import LedFramePlayer


def setUpModule():
    """Set up mock config for all tests."""
    # Mock the Config to avoid needing a real config file
    Config._Config__is_loaded = True
    Config._Config__config = {
        'leds': {
            'driver': 'apa102',
            'display_width': 32,
            'display_height': 16,
        },
        'screensavers': {
            'saved_videos': [],
        },
        # Add minimal config for each screensaver
        'boids': {'tick_sleep': 0.05, 'max_ticks': 100},
        'aurora': {'tick_sleep': 0.04, 'max_ticks': 100},
        'game_of_life': {
            'tick_sleep': 0.1,
            'game_over_detection_lookback': 100,
            'fade': False,
            'game_color_mode': 'color',
            'variant': 'normal',
            'seed_liveness_probability': 0.3,
        },
        'cyclic_automaton': {
            'tick_sleep': 0.1,
            'game_over_detection_lookback': 100,
            'fade': False,
        },
    }

    # Mock LedFramePlayer.__init__ to avoid hardware initialization
    original_init = LedFramePlayer.__init__

    def mock_init(self):
        # Just set the basic attributes without initializing hardware
        self.__led_driver = MagicMock()
        self.__gamma = MagicMock()

    LedFramePlayer.__init__ = mock_init
    LedFramePlayer.play_frame = MagicMock()
    LedFramePlayer.fade_to_frame = MagicMock()


class TestScreensaverInterface(unittest.TestCase):
    """Test that all screensavers implement the Screensaver interface correctly."""

    def test_all_screensavers_inherit_from_screensaver(self):
        """Verify all screensavers inherit from Screensaver ABC."""
        for screensaver_id, cls in ScreensaverManager.SCREENSAVER_CLASSES.items():
            with self.subTest(screensaver=screensaver_id):
                self.assertTrue(
                    issubclass(cls, Screensaver),
                    f"{screensaver_id} ({cls.__name__}) does not inherit from Screensaver"
                )

    def test_all_screensavers_implement_get_id(self):
        """Verify all screensavers implement get_id() class method."""
        for screensaver_id, cls in ScreensaverManager.SCREENSAVER_CLASSES.items():
            with self.subTest(screensaver=screensaver_id):
                self.assertTrue(
                    hasattr(cls, 'get_id'),
                    f"{screensaver_id} missing get_id() method"
                )
                result = cls.get_id()
                self.assertIsInstance(
                    result, str,
                    f"{screensaver_id}.get_id() returned {type(result)}, expected str"
                )
                self.assertGreater(
                    len(result), 0,
                    f"{screensaver_id}.get_id() returned empty string"
                )

    def test_all_screensavers_implement_get_name(self):
        """Verify all screensavers implement get_name() class method."""
        for screensaver_id, cls in ScreensaverManager.SCREENSAVER_CLASSES.items():
            with self.subTest(screensaver=screensaver_id):
                self.assertTrue(
                    hasattr(cls, 'get_name'),
                    f"{screensaver_id} missing get_name() method"
                )
                result = cls.get_name()
                self.assertIsInstance(
                    result, str,
                    f"{screensaver_id}.get_name() returned {type(result)}, expected str"
                )
                self.assertGreater(
                    len(result), 0,
                    f"{screensaver_id}.get_name() returned empty string"
                )

    def test_all_screensavers_implement_get_description(self):
        """Verify all screensavers implement get_description() class method."""
        for screensaver_id, cls in ScreensaverManager.SCREENSAVER_CLASSES.items():
            with self.subTest(screensaver=screensaver_id):
                self.assertTrue(
                    hasattr(cls, 'get_description'),
                    f"{screensaver_id} missing get_description() method"
                )
                result = cls.get_description()
                self.assertIsInstance(
                    result, str,
                    f"{screensaver_id}.get_description() returned {type(result)}, expected str"
                )
                self.assertGreater(
                    len(result), 0,
                    f"{screensaver_id}.get_description() returned empty string"
                )

    def test_all_screensavers_have_play_method(self):
        """Verify all screensavers have a play() method."""
        for screensaver_id, cls in ScreensaverManager.SCREENSAVER_CLASSES.items():
            with self.subTest(screensaver=screensaver_id):
                self.assertTrue(
                    hasattr(cls, 'play'),
                    f"{screensaver_id} missing play() method"
                )

    def test_all_screensavers_use_standard_constructor(self):
        """Verify all screensavers can be instantiated with led_frame_player=None."""
        for screensaver_id, cls in ScreensaverManager.SCREENSAVER_CLASSES.items():
            with self.subTest(screensaver=screensaver_id):
                try:
                    instance = cls(led_frame_player=None)
                    self.assertIsInstance(
                        instance, Screensaver,
                        f"{screensaver_id} instance is not a Screensaver"
                    )
                    self.assertTrue(
                        hasattr(instance, 'play'),
                        f"{screensaver_id} instance missing play method"
                    )
                except TypeError as e:
                    self.fail(
                        f"{screensaver_id} failed to instantiate with led_frame_player=None: {e}"
                    )

    def test_metadata_consistency(self):
        """Verify get_id() matches the key in SCREENSAVER_CLASSES."""
        for screensaver_id, cls in ScreensaverManager.SCREENSAVER_CLASSES.items():
            with self.subTest(screensaver=screensaver_id):
                self.assertEqual(
                    cls.get_id(), screensaver_id,
                    f"{screensaver_id} class key does not match get_id() return value"
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

    def test_get_all_screensavers_is_sorted(self):
        """Verify get_all_screensavers() returns sorted results."""
        all_screensavers = ScreensaverManager.get_all_screensavers()
        ids = [ss['id'] for ss in all_screensavers]
        sorted_ids = sorted(ids)
        self.assertEqual(ids, sorted_ids, "Screensavers are not sorted by ID")

    def test_no_duplicate_ids(self):
        """Verify there are no duplicate screensaver IDs."""
        all_screensavers = ScreensaverManager.get_all_screensavers()
        ids = [ss['id'] for ss in all_screensavers]
        unique_ids = set(ids)
        self.assertEqual(
            len(ids), len(unique_ids),
            f"Duplicate IDs found: {[id for id in ids if ids.count(id) > 1]}"
        )

    def test_screensaver_count(self):
        """Verify we have exactly 24 screensavers (23 regular + 1 video)."""
        self.assertEqual(
            len(ScreensaverManager.SCREENSAVER_CLASSES), 24,
            "Expected exactly 24 screensavers in SCREENSAVER_CLASSES"
        )

    def test_all_screensavers_call_super_init(self):
        """Verify all screensaver subclasses call super().__init__() in their __init__ method."""
        for screensaver_id, cls in ScreensaverManager.SCREENSAVER_CLASSES.items():
            with self.subTest(screensaver=screensaver_id):
                # Instantiate the screensaver
                try:
                    instance = cls(led_frame_player=None)
                except Exception as e:
                    self.fail(f"{screensaver_id} failed to instantiate: {e}")

                # Check if the base class __init__ was called by verifying the flag
                self.assertTrue(
                    hasattr(instance, '_screensaver_base_init_called'),
                    f"{screensaver_id} does not call super().__init__() - "
                    f"missing _screensaver_base_init_called attribute"
                )
                self.assertTrue(
                    instance._screensaver_base_init_called,
                    f"{screensaver_id}._screensaver_base_init_called is not True"
                )


class TestSpecificScreensavers(unittest.TestCase):
    """Test specific screensaver implementations."""

    def test_video_screensaver_uses_config(self):
        """Verify VideoScreensaver gets video_list from Config, not constructor."""
        from pifi.screensaver.videoscreensaver import VideoScreensaver

        # Should be able to instantiate without passing video_list
        instance = VideoScreensaver(led_frame_player=None)
        self.assertTrue(hasattr(instance, 'video_list'))
        self.assertIsInstance(instance.video_list, list)

    def test_cellular_automaton_hierarchy(self):
        """Verify CellularAutomaton inherits from Screensaver."""
        from pifi.screensaver.cellularautomata.cellularautomaton import CellularAutomaton

        self.assertTrue(issubclass(CellularAutomaton, Screensaver))

    def test_game_of_life_metadata(self):
        """Verify GameOfLife has correct metadata."""
        from pifi.screensaver.cellularautomata.gameoflife import GameOfLife

        self.assertEqual(GameOfLife.get_id(), 'game_of_life')
        self.assertEqual(GameOfLife.get_name(), 'Game of Life')
        self.assertIn("Conway", GameOfLife.get_description())

    def test_cyclic_automaton_metadata(self):
        """Verify CyclicAutomaton has correct metadata."""
        from pifi.screensaver.cellularautomata.cyclicautomaton import CyclicAutomaton

        self.assertEqual(CyclicAutomaton.get_id(), 'cyclic_automaton')
        self.assertEqual(CyclicAutomaton.get_name(), 'Cyclic Automaton')
        self.assertIn("cyclic", CyclicAutomaton.get_description().lower())


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
