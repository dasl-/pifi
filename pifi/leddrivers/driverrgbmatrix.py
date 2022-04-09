from PIL import Image
from rgbmatrix import RGBMatrix, RGBMatrixOptions

from pifi.leddrivers.driverbase import DriverBase

class DriverRgbMatrix(DriverBase):

    def __init__(self, led_settings, clear_screen=True):
        options = RGBMatrixOptions()
        options.rows = led_settings.display_height
        options.cols = led_settings.display_width
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
