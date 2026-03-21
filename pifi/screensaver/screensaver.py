import time
from abc import ABC, abstractmethod

from pifi.config import Config


class Screensaver(ABC):
    """Abstract base class for all screensavers."""

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

    def _is_past_screensaver_timeout(self):
        """Check if the screensaver timeout has been exceeded.

        Returns True if screensavers.screensaver_timeout is set (> 0) and the elapsed
        time since play started exceeds it. Returns False if screensaver_timeout is
        not set (None/0), deferring to per-screensaver max_ticks.
        """
        screensaver_timeout = Config.get('screensavers.screensaver_timeout', None)
        if not screensaver_timeout:
            return False
        return (time.time() - self._start_time) > screensaver_timeout

    @abstractmethod
    def play(self) -> None:
        """Play the screensaver until completion."""
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
