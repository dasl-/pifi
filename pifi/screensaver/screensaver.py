import time
from abc import ABC, abstractmethod

from pifi.config import Config
from pifi.led.ledframeplayer import LedFramePlayer
from pifi.logger import Logger


class FrameCapture:
    """Lightweight stand-in for LedFramePlayer that captures frames without displaying.

    Used during screensaver warm-up to build visual state without sending
    frames to the LED hardware.
    """

    def __init__(self):
        self.__current_frame = None

    def play_frame(self, frame):
        self.__current_frame = frame.copy()

    def get_current_frame(self):
        if self.__current_frame is None:
            return None
        return self.__current_frame.copy()

    def fade_to_frame(self, frame):
        """During warm-up, skip the fade animation and just capture the target frame."""
        self.__current_frame = frame.copy()


class Screensaver(ABC):
    """Abstract base class for all screensavers.

    Provides a template play() method that runs a tick loop with timeout
    enforcement. Subclasses implement _tick(), and optionally override
    _setup() / _teardown().

    The tick loop exits when any of these occur:
    - The timeout is exceeded (per-screensaver or global)
    - _tick() returns False (for subclass-specific stop conditions)
    """

    _screensaver_logger = Logger().set_namespace('Screensaver')

    def __init__(self, led_frame_player=None):
        """
        Standard constructor signature for all screensavers.

        Args:
            led_frame_player: Optional LedFramePlayer instance. If None, a new
                            instance is created. Stored as self._led_frame_player.

        Note: Subclasses must call super().__init__(led_frame_player) as the first
              line of their __init__ method.
        """
        # Flag to verify subclasses call super().__init__()
        self._screensaver_base_init_called = True

        if led_frame_player is None:
            led_frame_player = LedFramePlayer()
        self._led_frame_player = led_frame_player

        # Per-screensaver config overrides global defaults. A per-screensaver
        # value of None (null in JSON) falls back to the global value — this is
        # how the API reverts per-screensaver overrides.
        # e.g. screensavers.configs.boids.tick_sleep overrides screensavers.tick_sleep
        sid = self.get_id()

        self._tick_sleep = Config.get(f'screensavers.configs.{sid}.tick_sleep')
        if self._tick_sleep is None:
            self._tick_sleep = Config.get('screensavers.tick_sleep')
        if self._tick_sleep is None:
            self._tick_sleep = 0

        # For timeout, null means unlimited at the global level (0 also means
        # unlimited). At the per-screensaver level, null falls back to global.
        self._timeout = Config.get(f'screensavers.configs.{sid}.timeout')
        if self._timeout is None:
            self._timeout = Config.get('screensavers.timeout')
        if self._timeout is None:
            self._timeout = 0

        self._warmed_up = False
        self._warm_up_ticks = 0
        self._last_tick = 0

    def _is_past_timeout(self):
        """Check if the screensaver timeout has been exceeded.

        A timeout of 0 or None means unlimited (never times out).
        """
        if not self._timeout:
            return False
        return (time.time() - self._start_time) > self._timeout

    def play(self, auto_teardown=True) -> None:
        """Run the screensaver tick loop.

        If the screensaver was warmed up by a transition, skips _setup()
        and continues from where warm-up left off. Otherwise starts fresh.
        Timeout always counts from when play() is called, not from warm-up.

        Args:
            auto_teardown: If True (default), _teardown() is called when the
                loop ends. Set to False to keep the screensaver alive for
                live transitions — the caller must call _teardown() manually.
        """
        self._screensaver_logger.info(f"Starting {self.get_name()} screensaver")
        self._start_time = time.time()
        if not self._warmed_up:
            self._setup()
            start_tick = 0
        else:
            start_tick = self._warm_up_ticks

        try:
            tick = start_tick
            while not self._is_past_timeout():
                if self._tick(tick) is False:
                    break
                time.sleep(self._tick_sleep)
                tick += 1
            self._last_tick = tick
        except Exception:
            self._teardown()
            raise
        if auto_teardown:
            self._teardown()
        self._screensaver_logger.info(f"{self.get_name()} screensaver ended")

    def set_led_frame_player(self, led_frame_player):
        """Replace the LED frame player (e.g. with a FrameCapture during transitions)."""
        self._led_frame_player = led_frame_player

    def _setup(self):
        """Called once before the tick loop. Override for initialization."""
        pass

    def _teardown(self):
        """Called after the tick loop (in finally block). Override for cleanup."""
        pass

    @abstractmethod
    def _tick(self, tick) -> None:
        """Called each iteration of the tick loop.

        Return False to stop the loop early. Any other return value
        (including None) continues the loop.
        """
        pass

    @classmethod
    @abstractmethod
    def get_id(cls) -> str:
        """Return unique identifier (e.g., 'boids')"""
        pass

    @classmethod
    @abstractmethod
    def get_name(cls) -> str:
        """Return display name (e.g., 'Boids')"""
        pass

    @classmethod
    @abstractmethod
    def get_description(cls) -> str:
        """Return brief description"""
        pass

    @classmethod
    def supports_live_transition(cls) -> bool:
        """Whether this screensaver can participate in live transitions.

        Screensavers that block in _tick() or require the full LedFramePlayer
        API (beyond play_frame/fade_to_frame) should return False.
        """
        return True
