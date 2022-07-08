from PIL import Image
from rgbmatrix import RGBMatrix, RGBMatrixOptions

from pifi.config import Config
from pifi.led.drivers.driverbase import DriverBase

class DriverRgbMatrix(DriverBase):

    def __init__(self, clear_screen=True):
        options = RGBMatrixOptions()
        options.rows = Config.get_or_throw('leds.display_height')
        options.cols = Config.get_or_throw('leds.display_width')
        options.chain_length = 1
        options.parallel = 1
        options.hardware_mapping = 'adafruit-hat'
        options.drop_privileges = False

        self.__matrix = RGBMatrix(options = options)
        self.__pixels = self.__matrix.CreateFrameCanvas()
        if clear_screen:
            self.clear_screen()

    def display_frame(self, frame):
        img = Image.fromarray(frame, mode='RGB')
        self.__pixels.SetImage(img)
        self.__pixels = self.__matrix.SwapOnVSync(self.__pixels)

    def clear_screen(self):
        self.__pixels.Clear()
        self.__matrix.Clear()

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
        return False
