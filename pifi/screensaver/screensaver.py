import time
from abc import ABC, abstractmethod

from pifi.config import Config
from pifi.led.blackholeframeplayer import BlackHoleFramePlayer
from pifi.led.ledframeplayer import LedFramePlayer
from pifi.logger import Logger


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
        self.__screensaver_base_init_called = True

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
        self.__timeout = Config.get(f'screensavers.configs.{sid}.timeout')
        if self.__timeout is None:
            self.__timeout = Config.get('screensavers.timeout')
        if self.__timeout is None:
            self.__timeout = 0

        self.live_transition_warmed_up = False
        self.__last_tick = 0
        self.__black_hole_frame_player = BlackHoleFramePlayer()
        self.__is_set_up = False

    def get_tick_sleep(self):
        """Seconds to sleep between ticks (read-only, from config)."""
        return self._tick_sleep

    def get_last_tick(self):
        """The next tick number to execute (read-only).

        Updated by both play() and render_tick(). Starts at 0 for a fresh
        screensaver; after a transition warm-up it reflects how far the
        screensaver has already been ticked.
        """
        return self.__last_tick

    def _is_past_timeout(self):
        """Check if the screensaver timeout has been exceeded.

        A timeout of 0 or None means unlimited (never times out).
        """
        if not self.__timeout:
            return False
        return (time.time() - self.__start_time) > self.__timeout

    def setup(self):
        """Initialize the screensaver for ticking. Idempotent — safe to call
        multiple times, but only runs _setup() once."""
        if not self.__is_set_up:
            self._setup()
            self.__is_set_up = True

    def teardown(self):
        """Clean up resources after the screensaver finishes."""
        self._teardown()
        self.__is_set_up = False

    def render_tick(self):
        """Advance state by one tick, capturing the rendered frame without
        displaying it on the LED hardware.

        Calls setup() on first invocation (under the capture, so any frames
        rendered during _setup() are intercepted rather than displayed).

        Returns:
            (frame, alive) where frame is a numpy array (or None if nothing
            was rendered) and alive is True unless _tick() returned False.
        """
        real_player = self._led_frame_player
        self._led_frame_player = self.__black_hole_frame_player
        try:
            self.setup()
            alive = self._tick() is not False
            if alive:
                self.__last_tick += 1
            return self.__black_hole_frame_player.get_current_frame(), alive
        finally:
            self._led_frame_player = real_player

    def play(self, auto_teardown=True) -> None:
        """Run the screensaver tick loop.

        If the screensaver was warmed up by a transition, skips setup()
        and continues from where warm-up left off. Otherwise starts fresh.
        Timeout always counts from when play() is called, not from warm-up.

        Args:
            auto_teardown: If True (default), teardown() is called when the
                loop ends. Set to False to keep the screensaver alive for
                transitions — the caller must call teardown() manually.
        """
        self._screensaver_logger.info(f"Starting {self.get_name()} screensaver")
        self.__start_time = time.time()
        self.setup()

        try:
            while not self._is_past_timeout():
                if self._tick() is False:
                    break
                time.sleep(self.get_tick_sleep())
                self.__last_tick += 1
        except Exception:
            self.teardown()
            raise
        if auto_teardown:
            self.teardown()
        self._screensaver_logger.info(f"{self.get_name()} screensaver ended")

    def _setup(self):
        """Called once before the tick loop. Override for initialization."""
        pass

    def _teardown(self):
        """Called after the tick loop ends. Override for cleanup."""
        pass

    @abstractmethod
    def _tick(self) -> None:
        """Called each iteration of the tick loop.

        Return False to stop the loop early. Any other return value
        (including None) continues the loop. Use self.get_last_tick()
        to get the current tick number if needed.
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

    def supports_live_transition(self) -> bool:
        """Whether this screensaver can participate in live transitions.

        Live transitions animate both screensavers during the blend.
        Static transitions crossfade from the last displayed frame to black.

        Screensavers that block in _tick() or require the full LedFramePlayer
        API (beyond play_frame/fade_to_frame) should return False.
        """
        return True
