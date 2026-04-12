#!/usr/bin/env python3
"""
Unit tests for screensaver transition behavior.

Covers:
- supports_live_transition() contract
- last_tick initialization and updates
- Frame player restoration after transition (including on exception)
- live_transition_warmed_up state when warm-up fails
- auto_teardown=False skips teardown
- warm_up_ticks=0 captures to_frame from _setup()
- render_tick() captures frames without displaying
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
from pifi.screensaver.screensaver import Screensaver
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
        _render_frame(self, value=42)

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
    """Test the supports_live_transition() method."""

    def setUp(self):
        Config._Config__is_loaded = True
        Config._Config__config = copy.deepcopy(BASE_CONFIG)

    def test_video_screensaver_returns_false(self):
        from pifi.screensaver.videoscreensaver import VideoScreensaver
        ss = VideoScreensaver(led_frame_player=None)
        self.assertFalse(ss.supports_live_transition())


class TestLastTick(unittest.TestCase):
    """Test last_tick initialization and updates."""

    def setUp(self):
        Config._Config__is_loaded = True
        Config._Config__config = copy.deepcopy(BASE_CONFIG)

    def test_updated_after_play(self):
        ss = _FailingTickScreensaver(led_frame_player=None, fail_after=5)
        ss.play()
        self.assertEqual(ss.get_last_tick(), 5)


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


class TestRenderTick(unittest.TestCase):
    """Test render_tick() captures frames without displaying."""

    def setUp(self):
        Config._Config__is_loaded = True
        Config._Config__config = copy.deepcopy(BASE_CONFIG)

    def test_returns_frame_and_alive(self):
        ss = _StubScreensaver(led_frame_player=None)
        frame, alive = ss.render_tick(0)
        self.assertTrue(alive)
        self.assertIsNotNone(frame)
        self.assertEqual(frame.shape, (4, 4, 3))

    def test_does_not_render_to_real_player(self):
        """render_tick() should not call play_frame on the real LedFramePlayer."""
        player = MagicMock()
        player.get_current_frame.return_value = np.zeros([4, 4, 3], np.uint8)

        ss = _StubScreensaver(led_frame_player=player)
        player.play_frame.reset_mock()

        frame, alive = ss.render_tick(0)
        player.play_frame.assert_not_called()

    def test_restores_frame_player_after_tick(self):
        player = MagicMock()
        ss = _StubScreensaver(led_frame_player=player)
        ss.render_tick(0)
        self.assertIs(ss._led_frame_player, player)

    def test_restores_frame_player_on_exception(self):
        player = MagicMock()
        ss = _ExplodingTickScreensaver(led_frame_player=player, explode_after=0)
        with self.assertRaises(RuntimeError):
            ss.render_tick(0)
        self.assertIs(ss._led_frame_player, player)

    def test_returns_false_alive_when_tick_stops(self):
        ss = _FailingTickScreensaver(led_frame_player=None, fail_after=0)
        frame, alive = ss.render_tick(0)
        self.assertFalse(alive)

    def test_calls_setup_on_first_invocation(self):
        ss = _RenderingSetupScreensaver(led_frame_player=None)
        self.assertFalse(ss._Screensaver__is_set_up)
        frame, alive = ss.render_tick(0)
        self.assertTrue(ss._Screensaver__is_set_up)

    def test_setup_frame_captured_not_displayed(self):
        """Frames rendered during _setup() should be captured, not sent to real display."""
        player = MagicMock()
        player.get_current_frame.return_value = np.zeros([4, 4, 3], np.uint8)

        ss = _RenderingSetupScreensaver(led_frame_player=player)
        player.play_frame.reset_mock()

        frame, alive = ss.render_tick(0)
        # The real player should NOT have received any frames
        player.play_frame.assert_not_called()
        # But we should have captured a frame
        self.assertIsNotNone(frame)


class TestTransitionFramePlayerIntegrity(unittest.TestCase):
    """Test that frame players are never corrupted by transitions."""

    def setUp(self):
        Config._Config__is_loaded = True
        Config._Config__config = copy.deepcopy(BASE_CONFIG)

    def _make_player(self):
        player = MagicMock()
        player.get_current_frame.return_value = np.zeros([4, 4, 3], np.uint8)
        return player

    def test_screensaver_player_unchanged_after_transition(self):
        """Both screensavers should still have their original _led_frame_player
        after the transition completes (render_tick restores per-call)."""
        player = self._make_player()
        tp = TransitionPlayer(player)

        from_ss = _StubScreensaver(led_frame_player=None)
        to_ss = _StubScreensaver(led_frame_player=None)
        from_original = from_ss._led_frame_player
        to_original = to_ss._led_frame_player

        tp.play_transition(from_screensaver=from_ss, to_screensaver=to_ss)

        self.assertIs(from_ss._led_frame_player, from_original)
        self.assertIs(to_ss._led_frame_player, to_original)

    def test_screensaver_player_intact_after_exception(self):
        player = self._make_player()
        tp = TransitionPlayer(player)

        from_ss = _StubScreensaver(led_frame_player=None)
        to_ss = _ExplodingTickScreensaver(led_frame_player=None, explode_after=0)
        from_original = from_ss._led_frame_player
        to_original = to_ss._led_frame_player

        with self.assertRaises(RuntimeError):
            tp.play_transition(from_screensaver=from_ss, to_screensaver=to_ss)

        self.assertIs(from_ss._led_frame_player, from_original)
        self.assertIs(to_ss._led_frame_player, to_original)


class TestWarmedUpState(unittest.TestCase):
    """Test that live_transition_warmed_up reflects whether warm-up actually succeeded."""

    def setUp(self):
        Config._Config__is_loaded = True
        Config._Config__config = copy.deepcopy(BASE_CONFIG)

    def _make_player(self):
        player = MagicMock()
        player.get_current_frame.return_value = np.zeros([4, 4, 3], np.uint8)
        return player

    def test_live_transition_warmed_up_true_after_successful_warmup(self):
        player = self._make_player()
        tp = TransitionPlayer(player)

        from_ss = _StubScreensaver(led_frame_player=None)
        to_ss = _StubScreensaver(led_frame_player=None)
        self.assertFalse(to_ss.live_transition_warmed_up)

        tp.play_transition(from_screensaver=from_ss, to_screensaver=to_ss)
        self.assertTrue(to_ss.live_transition_warmed_up)

    def test_live_transition_warmed_up_false_when_tick_returns_false_during_warmup(self):
        """If _tick() returns False during warm-up, live_transition_warmed_up stays False."""
        player = self._make_player()
        tp = TransitionPlayer(player)

        from_ss = _StubScreensaver(led_frame_player=None)

        # Fails immediately during warm-up
        to_ss = _FailingTickScreensaver(led_frame_player=None, fail_after=0)

        tp.play_transition(from_screensaver=from_ss, to_screensaver=to_ss)
        self.assertFalse(to_ss.live_transition_warmed_up)


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


class TestFromDiesDuringWarmup(unittest.TestCase):
    """Test that to_screensaver still warms up when from dies during warm-up."""

    def setUp(self):
        config = copy.deepcopy(BASE_CONFIG)
        config['screensavers']['transitions']['warm_up_ticks'] = 60
        Config._Config__is_loaded = True
        Config._Config__config = config

    def test_to_still_warms_up(self):
        """If from_screensaver dies during warm-up, warm-up ends early
        and jumps straight to the blend phase."""
        player = MagicMock()
        player.get_current_frame.return_value = np.zeros([4, 4, 3], np.uint8)
        tp = TransitionPlayer(player)

        from_ss = _FailingTickScreensaver(led_frame_player=None, fail_after=1)
        to_ss = _StubScreensaver(led_frame_player=None)

        tp.play_transition(from_screensaver=from_ss, to_screensaver=to_ss)

        self.assertTrue(to_ss.live_transition_warmed_up)
        # Warm-up should have ended early (from died after 1 tick), so
        # total ticks (warm-up + blend) should be far less than 60.
        self.assertLess(to_ss.live_transition_warm_up_ticks, 30)


class TestStaticTransition(unittest.TestCase):
    """Test static-frame transitions (no live screensavers)."""

    def setUp(self):
        Config._Config__is_loaded = True
        Config._Config__config = copy.deepcopy(BASE_CONFIG)

    def test_static_transition_runs(self):
        """play_transition() with no screensavers should crossfade to black."""
        player = MagicMock()
        player.get_current_frame.return_value = np.full([4, 4, 3], 200, np.uint8)
        tp = TransitionPlayer(player)

        tp.play_transition()

        # Should have called play_frame for each blend step
        self.assertGreater(player.play_frame.call_count, 0)

    def test_static_transition_ends_at_black(self):
        """The last frame of a static transition should be black."""
        player = MagicMock()
        player.get_current_frame.return_value = np.full([4, 4, 3], 200, np.uint8)
        tp = TransitionPlayer(player)

        tp.play_transition()

        last_frame = player.play_frame.call_args_list[-1].args[0]
        np.testing.assert_array_equal(
            last_frame,
            np.zeros([4, 4, 3], dtype=np.uint8),
        )

    def test_static_transition_from_none(self):
        """Static transition when get_current_frame returns None should not crash."""
        player = MagicMock()
        player.get_current_frame.return_value = None
        tp = TransitionPlayer(player)

        tp.play_transition()

        self.assertGreater(player.play_frame.call_count, 0)
        last_frame = player.play_frame.call_args_list[-1].args[0]
        np.testing.assert_array_equal(
            last_frame,
            np.zeros([4, 4, 3], dtype=np.uint8),
        )


if __name__ == '__main__':
    unittest.main()
