import time
from abc import ABC, abstractmethod

from pifi.config import Config
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
            led_frame_player: Optional LedFramePlayer instance. If None, subclasses
                            typically create their own instance.

        Note: Subclasses must call super().__init__(led_frame_player) as the first
              line of their __init__ method.
        """
        # Flag to verify subclasses call super().__init__()
        self._screensaver_base_init_called = True
        self._start_time = time.time()

        # Per-screensaver config overrides global defaults. To revert a
        # per-screensaver override, remove the key (set to null via the API)
        # so it falls back to the global value.
        # e.g. screensavers.configs.boids.tick_sleep overrides screensavers.tick_sleep
        sid = self.get_id()
        self._tick_sleep = Config.get(
            f'screensavers.configs.{sid}.tick_sleep',
            Config.get('screensavers.tick_sleep', 0.05)
        )
        self._timeout = Config.get(
            f'screensavers.configs.{sid}.timeout',
            Config.get('screensavers.timeout', 120)
        )

    def _is_past_timeout(self):
        """Check if the screensaver timeout has been exceeded.

        A timeout of 0 or None means unlimited (never times out).
        """
        if not self._timeout:
            return False
        return (time.time() - self._start_time) > self._timeout

    def play(self) -> None:
        """Run the screensaver tick loop.

        Calls _setup(), then runs _tick() in a loop until timeout or
        _tick() returns False. Calls _teardown() in a finally block
        to ensure cleanup.
        """
        self._screensaver_logger.info(f"Starting {self.get_name()} screensaver")
        self._setup()
        try:
            tick = 0
            while not self._is_past_timeout():
                if self._tick(tick) is False:
                    break
                time.sleep(self._tick_sleep)
                tick += 1
        finally:
            self._teardown()
        self._screensaver_logger.info(f"{self.get_name()} screensaver ended")

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
