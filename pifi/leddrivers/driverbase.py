from abc import ABC, abstractmethod

# Driver implementations should inherit from this abstract base class
class DriverBase(ABC):

    @abstractmethod
    def __init__(self, led_settings, clear_screen=True):
        pass

    @abstractmethod
    def display_frame(self, frame):
        pass

    @abstractmethod
    def clear_screen(self):
        pass
