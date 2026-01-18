from abc import ABC, abstractmethod

class Screensaver(ABC):
    """Abstract base class for all screensavers."""

    def __init__(self, led_frame_player=None):
        """Standard constructor. Subclasses should call super().__init__()"""
        pass

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
