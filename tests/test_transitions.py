#!/usr/bin/env python3
"""
Unit tests for screensaver transition behavior.

Covers:
- supports_live_transition() contract
- _last_tick initialization and updates
- Frame player restoration after transition (including on exception)
- _warmed_up state when warm-up fails
- auto_teardown=False skips teardown
- warm_up_ticks=0 captures to_frame from _setup()
"""

import copy
import unittest
import sys
import os
from unittest.mock import MagicMock, patch, call

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pifi.config import Config
from pifi.led.ledframeplayer import LedFramePlayer
from pifi.screensaver.screensaver import Screensaver, FrameCapture
from pifi.screensaver.transitionplayer import TransitionPlayer


# --- Stub screensavers with controllable behavior ---

def _render_frame(screensaver, value=128):
    """Helper: render a solid-color frame to the screensaver's frame player."""
    w = Config.get_or_throw('leds.display_width')
    h = Config.get_or_throw('leds.display_height')
    screensaver._led_frame_player.play_frame(
        np.full([h, w, 3], value, dtype=np.uint8)
    )


class _StubScreensaver(Screensaver):
    """Basic stub that renders a frame each tick."""

    def _tick(self, tick):
        _render_frame(self)

    @classmethod
    def get_id(cls):
        return 'stub'

    @classmethod
    def get_name(cls):
        return 'Stub'

    @classmethod
    def get_description(cls):
        return 'Test stub'


class _FailingTickScreensaver(Screensaver):
    """Stub whose _tick() returns False after a set number of ticks."""

    def __init__(self, led_frame_player=None, fail_after=0):
        super().__init__(led_frame_player)
        self._fail_after = fail_after

    def _tick(self, tick):
        if tick >= self._fail_after:
            return False
        _render_frame(self)

    @classmethod
    def get_id(cls):
        return 'failing_tick'

    @classmethod
    def get_name(cls):
        return 'FailingTick'

    @classmethod
    def get_description(cls):
        return 'Fails after N ticks'


class _ExplodingTickScreensaver(Screensaver):
    """Stub whose _tick() raises an exception after a set number of ticks."""

    def __init__(self, led_frame_player=None, explode_after=0):
        super().__init__(led_frame_player)
        self._explode_after = explode_after

    def _tick(self, tick):
        if tick >= self._explode_after:
            raise RuntimeError("boom")
        _render_frame(self)

    @classmethod
    def get_id(cls):
        return 'exploding_tick'

    @classmethod
    def get_name(cls):
        return 'ExplodingTick'

    @classmethod
    def get_description(cls):
        return 'Raises after N ticks'


class _RenderingSetupScreensaver(Screensaver):
    """Stub that renders a frame during _setup()."""

    def _setup(self):
        frame = np.full([self._height, self._width, 3], 42, dtype=np.uint8)
        self._led_frame_player.play_frame(frame)

    def __init__(self, led_frame_player=None):
        super().__init__(led_frame_player)
        self._width = Config.get_or_throw('leds.display_width')
        self._height = Config.get_or_throw('leds.display_height')

    def _tick(self, tick):
        pass

    @classmethod
    def get_id(cls):
        return 'rendering_setup'

    @classmethod
    def get_name(cls):
        return 'RenderingSetup'

    @classmethod
    def get_description(cls):
        return 'Renders during _setup()'


BASE_CONFIG = {
    'leds': {
        'driver': 'apa102',
        'display_width': 4,
        'display_height': 4,
    },
    'screensavers': {
        'transitions': {
            'enabled': True,
            'duration': 0.1,
            'tick_sleep': 0.01,
            'warm_up_ticks': 3,
        },
    },
}


def setUpModule():
    LedFramePlayer.__init__ = lambda self: None
    LedFramePlayer.play_frame = MagicMock()
    LedFramePlayer.fade_to_frame = MagicMock()
    LedFramePlayer.get_current_frame = MagicMock(return_value=np.zeros([4, 4, 3], np.uint8))


class TestSupportsLiveTransition(unittest.TestCase):
    """Test the supports_live_transition() class method."""

    def setUp(self):
        Config._Config__is_loaded = True
        Config._Config__config = copy.deepcopy(BASE_CONFIG)

    def test_default_is_true(self):
        self.assertTrue(_StubScreensaver.supports_live_transition())

    def test_video_screensaver_returns_false(self):
        from pifi.screensaver.videoscreensaver import VideoScreensaver
        self.assertFalse(VideoScreensaver.supports_live_transition())

    def test_regular_screensavers_return_true(self):
        from pifi.screensaver.screensavermanager import ScreensaverManager
        from pifi.screensaver.videoscreensaver import VideoScreensaver
        for sid, cls in ScreensaverManager.SCREENSAVER_CLASSES.items():
            with self.subTest(screensaver=sid):
                if cls is VideoScreensaver:
                    self.assertFalse(cls.supports_live_transition())
                else:
                    self.assertTrue(cls.supports_live_transition())


class TestLastTick(unittest.TestCase):
    """Test _last_tick initialization and updates."""

    def setUp(self):
        Config._Config__is_loaded = True
        Config._Config__config = copy.deepcopy(BASE_CONFIG)

    def test_initialized_to_zero(self):
        ss = _StubScreensaver(led_frame_player=None)
        self.assertEqual(ss._last_tick, 0)

    def test_updated_after_play(self):
        ss = _FailingTickScreensaver(led_frame_player=None, fail_after=5)
        ss.play()
        self.assertEqual(ss._last_tick, 5)


class TestAutoTeardown(unittest.TestCase):
    """Test auto_teardown parameter of play()."""

    def setUp(self):
        Config._Config__is_loaded = True
        Config._Config__config = copy.deepcopy(BASE_CONFIG)

    def test_auto_teardown_true_calls_teardown(self):
        ss = _FailingTickScreensaver(led_frame_player=None, fail_after=0)
        ss._teardown = MagicMock()
        ss.play(auto_teardown=True)
        ss._teardown.assert_called_once()

    def test_auto_teardown_false_skips_teardown(self):
        ss = _FailingTickScreensaver(led_frame_player=None, fail_after=0)
        ss._teardown = MagicMock()
        ss.play(auto_teardown=False)
        ss._teardown.assert_not_called()


class TestFramePlayerRestoration(unittest.TestCase):
    """Test that frame players are restored after transition, even on exception."""

    def setUp(self):
        Config._Config__is_loaded = True
        Config._Config__config = copy.deepcopy(BASE_CONFIG)

    def _make_player(self):
        player = MagicMock()
        player.get_current_frame.return_value = np.zeros([4, 4, 3], np.uint8)
        return player

    def test_restored_after_normal_transition(self):
        player = self._make_player()
        tp = TransitionPlayer(player)

        from_ss = _StubScreensaver(led_frame_player=None)
        to_ss = _StubScreensaver(led_frame_player=None)

        tp.play_transition(from_screensaver=from_ss, to_screensaver=to_ss)

        # Both should have the real player restored
        self.assertIs(from_ss._led_frame_player, player)
        self.assertIs(to_ss._led_frame_player, player)

    def test_restored_after_exception_in_warmup(self):
        """If to_screensaver raises during warm-up, frame players are still restored."""
        player = self._make_player()
        tp = TransitionPlayer(player)

        from_ss = _StubScreensaver(led_frame_player=None)

        # Explodes on tick 0 — during warm-up phase
        to_ss = _ExplodingTickScreensaver(led_frame_player=None, explode_after=0)

        with self.assertRaises(RuntimeError):
            tp.play_transition(from_screensaver=from_ss, to_screensaver=to_ss)

        self.assertIs(from_ss._led_frame_player, player)
        self.assertIs(to_ss._led_frame_player, player)

    def test_restored_after_exception_in_blend(self):
        """If to_screensaver raises during blend, frame players are still restored."""
        player = self._make_player()
        tp = TransitionPlayer(player)

        from_ss = _StubScreensaver(led_frame_player=None)

        # Survives warm-up (3 ticks) but explodes during blend
        to_ss = _ExplodingTickScreensaver(led_frame_player=None, explode_after=5)

        with self.assertRaises(RuntimeError):
            tp.play_transition(from_screensaver=from_ss, to_screensaver=to_ss)

        self.assertIs(from_ss._led_frame_player, player)
        self.assertIs(to_ss._led_frame_player, player)


class TestWarmedUpState(unittest.TestCase):
    """Test that _warmed_up reflects whether warm-up actually succeeded."""

    def setUp(self):
        Config._Config__is_loaded = True
        Config._Config__config = copy.deepcopy(BASE_CONFIG)

    def _make_player(self):
        player = MagicMock()
        player.get_current_frame.return_value = np.zeros([4, 4, 3], np.uint8)
        return player

    def test_warmed_up_true_after_successful_warmup(self):
        player = self._make_player()
        tp = TransitionPlayer(player)

        from_ss = _StubScreensaver(led_frame_player=None)
        to_ss = _StubScreensaver(led_frame_player=None)
        self.assertFalse(to_ss._warmed_up)

        tp.play_transition(from_screensaver=from_ss, to_screensaver=to_ss)
        self.assertTrue(to_ss._warmed_up)

    def test_warmed_up_false_when_tick_returns_false_during_warmup(self):
        """If _tick() returns False during warm-up, _warmed_up stays False."""
        player = self._make_player()
        tp = TransitionPlayer(player)

        from_ss = _StubScreensaver(led_frame_player=None)

        # Fails immediately during warm-up
        to_ss = _FailingTickScreensaver(led_frame_player=None, fail_after=0)

        tp.play_transition(from_screensaver=from_ss, to_screensaver=to_ss)
        self.assertFalse(to_ss._warmed_up)


class TestWarmUpTicksZero(unittest.TestCase):
    """Test that warm_up_ticks=0 still captures to_frame from _setup()."""

    def setUp(self):
        config = copy.deepcopy(BASE_CONFIG)
        config['screensavers']['transitions']['warm_up_ticks'] = 0
        Config._Config__is_loaded = True
        Config._Config__config = config

    def _make_player(self):
        player = MagicMock()
        player.get_current_frame.return_value = np.zeros([4, 4, 3], np.uint8)
        return player

    def test_setup_frame_used_in_blend(self):
        """When warm_up_ticks=0, the frame rendered by _setup() should be
        used as to_frame in the blend, not a black frame."""
        player = self._make_player()
        tp = TransitionPlayer(player)

        to_ss = _RenderingSetupScreensaver(led_frame_player=None)

        # Run transition with only to_screensaver (from_frame will be black)
        tp.play_transition(to_screensaver=to_ss)

        # Check that play_frame was called with non-zero blended frames.
        # _RenderingSetupScreensaver renders value 42 in _setup(), so the
        # blended frames should contain non-zero values (progress > 0).
        frames_played = [
            c.args[0] for c in player.play_frame.call_args_list
        ]
        # The last frame (progress=1.0) should be entirely the to_frame
        last_frame = frames_played[-1]
        np.testing.assert_array_equal(
            last_frame,
            np.full([4, 4, 3], 42, dtype=np.uint8),
        )


if __name__ == '__main__':
    unittest.main()
