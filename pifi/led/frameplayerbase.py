from abc import ABC, abstractmethod


class FramePlayerBase(ABC):
    """Abstract base class for frame players.

    Concrete implementations include LedFramePlayer (renders to LED hardware)
    and BlackHoleFramePlayer (captures frames without displaying).
    """

    @abstractmethod
    def play_frame(self, frame):
        pass

    @abstractmethod
    def get_current_frame(self):
        pass

    @abstractmethod
    def fade_to_frame(self, frame):
        pass
