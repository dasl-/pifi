from abc import ABC, abstractmethod

# Driver implementations should inherit from this abstract base class
class DriverBase(ABC):

    @abstractmethod
    def __init__(self, clear_screen=True):
        pass

    @abstractmethod
    def display_frame(self, frame):
        pass

    @abstractmethod
    def clear_screen(self):
        pass

    # For some drivers, only one instance of the driver can exist at a time because all of them
    # would send competing signals to the LEDs. The screensaver, video playback, etc processes
    # that the Queue launches might have their own instance of the driver as well as the
    # Queue process itself, which could cause problems.
    #
    # Thus, for some drivers (like the RGB Matrix driver), when the Queue needs to perform
    # operations like clearing the screen, it creates a short lived instance to avoid the
    # problems with multiple long lived driver instances. This approach does not work for other
    # drivers (like the APA102 driver).
    #
    # See: https://github.com/hzeller/rpi-rgb-led-matrix/issues/640
    #      https://github.com/dasl-/pifi/pull/32
    #      https://github.com/dasl-/pifi/issues/33
    def can_multiple_driver_instances_coexist(self):
        return True
