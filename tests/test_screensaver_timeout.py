#!/usr/bin/env python3
"""
Unit tests for Screensaver timeout and tick_sleep resolution.

Verifies the config resolution chain:
  per-screensaver -> global -> hardcoded default

And the timeout semantics:
  positive number = timeout after N seconds
  0 or None      = unlimited (no timeout)
  Per-screensaver None = fall back to global
"""

import copy
import time
import unittest
import sys
import os
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pifi.config import Config
from pifi.led.ledframeplayer import LedFramePlayer
from pifi.screensaver.screensaver import Screensaver


# Concrete subclass for testing
class _StubScreensaver(Screensaver):
    def _tick(self, tick):
        pass

    @classmethod
    def get_id(cls):
        return 'stub'

    @classmethod
    def get_name(cls):
        return 'Stub'

    @classmethod
    def get_description(cls):
        return 'Test stub'


def setUpModule():
    # Mock LedFramePlayer to avoid hardware initialization
    LedFramePlayer.__init__ = lambda self: None
    LedFramePlayer.play_frame = MagicMock()


class TestTimeoutResolution(unittest.TestCase):
    """Test the timeout config resolution chain."""

    def setUp(self):
        Config._Config__is_loaded = True

    def _make(self, config):
        Config._Config__config = copy.deepcopy(config)
        return _StubScreensaver(led_frame_player=None)

    def test_default_timeout_is_120(self):
        """When timeout is set to 120 in config (as in default_config.json), it's used."""
        ss = self._make({'screensavers': {'timeout': 120}})
        self.assertEqual(ss._timeout, 120)

    def test_timeout_absent_means_unlimited(self):
        """When timeout key is absent from config entirely, it's unlimited."""
        ss = self._make({'screensavers': {}})
        self.assertEqual(ss._timeout, 0)

    def test_global_timeout_overrides_default(self):
        """Global screensavers.timeout overrides the hardcoded default."""
        ss = self._make({'screensavers': {'timeout': 60}})
        self.assertEqual(ss._timeout, 60)

    def test_per_screensaver_timeout_overrides_global(self):
        """Per-screensaver timeout overrides the global timeout."""
        ss = self._make({
            'screensavers': {
                'timeout': 60,
                'configs': {'stub': {'timeout': 30}},
            }
        })
        self.assertEqual(ss._timeout, 30)

    def test_no_per_screensaver_timeout_falls_back_to_global(self):
        """When per-screensaver timeout is absent, global timeout is used."""
        ss = self._make({
            'screensavers': {
                'timeout': 90,
                'configs': {'stub': {'tick_sleep': 0.01}},
            }
        })
        self.assertEqual(ss._timeout, 90)

    def test_timeout_zero_means_unlimited(self):
        """Timeout of 0 means unlimited — _is_past_timeout always returns False."""
        ss = self._make({'screensavers': {'timeout': 0}})
        self.assertEqual(ss._timeout, 0)
        ss._start_time = time.time() - 99999
        self.assertFalse(ss._is_past_timeout())

    def test_global_timeout_none_means_unlimited(self):
        """Global timeout of None means unlimited (same as 0)."""
        ss = self._make({'screensavers': {'timeout': None}})
        self.assertEqual(ss._timeout, 0)
        ss._start_time = time.time() - 99999
        self.assertFalse(ss._is_past_timeout())

    def test_per_screensaver_timeout_null_falls_back_to_global(self):
        """Per-screensaver timeout of null falls back to global timeout."""
        ss = self._make({
            'screensavers': {
                'timeout': 60,
                'configs': {'stub': {'timeout': None}},
            }
        })
        self.assertEqual(ss._timeout, 60)

    def test_per_screensaver_timeout_zero_means_unlimited(self):
        """Per-screensaver timeout of 0 means unlimited, not fallback."""
        ss = self._make({
            'screensavers': {
                'timeout': 60,
                'configs': {'stub': {'timeout': 0}},
            }
        })
        self.assertEqual(ss._timeout, 0)
        ss._start_time = time.time() - 99999
        self.assertFalse(ss._is_past_timeout())

    def test_positive_timeout_expires(self):
        """A positive timeout causes _is_past_timeout to return True after elapsed time."""
        ss = self._make({'screensavers': {'timeout': 10}})
        ss._start_time = time.time() - 11
        self.assertTrue(ss._is_past_timeout())

    def test_positive_timeout_not_expired(self):
        """A positive timeout returns False before the time elapses."""
        ss = self._make({'screensavers': {'timeout': 10}})
        ss._start_time = time.time()
        self.assertFalse(ss._is_past_timeout())


class TestTickSleepResolution(unittest.TestCase):
    """Test the tick_sleep config resolution chain."""

    def setUp(self):
        Config._Config__is_loaded = True

    def _make(self, config):
        Config._Config__config = copy.deepcopy(config)
        return _StubScreensaver(led_frame_player=None)

    def test_default_tick_sleep(self):
        """When tick_sleep is set to 0.05 in config (as in default_config.json), it's used."""
        ss = self._make({'screensavers': {'tick_sleep': 0.05}})
        self.assertEqual(ss.tick_sleep(), 0.05)

    def test_tick_sleep_absent_means_zero(self):
        """When tick_sleep key is absent from config entirely, it's 0."""
        ss = self._make({'screensavers': {}})
        self.assertEqual(ss.tick_sleep(), 0)

    def test_global_tick_sleep_overrides_default(self):
        """Global screensavers.tick_sleep overrides the hardcoded default."""
        ss = self._make({'screensavers': {'tick_sleep': 0.1}})
        self.assertEqual(ss.tick_sleep(), 0.1)

    def test_per_screensaver_tick_sleep_overrides_global(self):
        """Per-screensaver tick_sleep overrides the global tick_sleep."""
        ss = self._make({
            'screensavers': {
                'tick_sleep': 0.1,
                'configs': {'stub': {'tick_sleep': 0.02}},
            }
        })
        self.assertEqual(ss.tick_sleep(), 0.02)

    def test_no_per_screensaver_tick_sleep_falls_back_to_global(self):
        """When per-screensaver tick_sleep is absent, global is used."""
        ss = self._make({
            'screensavers': {
                'tick_sleep': 0.08,
                'configs': {'stub': {'timeout': 60}},
            }
        })
        self.assertEqual(ss.tick_sleep(), 0.08)

    def test_per_screensaver_tick_sleep_null_falls_back_to_global(self):
        """Per-screensaver tick_sleep of null falls back to global tick_sleep."""
        ss = self._make({
            'screensavers': {
                'tick_sleep': 0.08,
                'configs': {'stub': {'tick_sleep': None}},
            }
        })
        self.assertEqual(ss.tick_sleep(), 0.08)

    def test_global_tick_sleep_none_means_zero(self):
        """Global tick_sleep of None means 0 (no sleep between ticks)."""
        ss = self._make({'screensavers': {'tick_sleep': None}})
        self.assertEqual(ss.tick_sleep(), 0)


if __name__ == '__main__':
    unittest.main()
