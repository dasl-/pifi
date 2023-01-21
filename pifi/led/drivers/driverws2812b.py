import rpi_ws281x
import numpy as np

from pifi.config import Config
from pifi.led.drivers.driverbase import DriverBase

class DriverWs2812b(DriverBase):

    def __init__(self, clear_screen=True):

        self.__display_width = Config.get_or_throw('leds.display_width')
        self.__display_height = Config.get_or_throw('leds.display_height')

        """
        View something of an API reference by doing:

        >>> import rpi_ws281x
        >>> dir(rpi_ws281x)
        ['Adafruit_NeoPixel', 'Color', 'PixelStrip', ...

        >>> help(rpi_ws281x.PixelStrip)
        ...

        Also: https://github.com/rpi-ws281x/rpi-ws281x-python/blob/29a99c00ac3eefebf01480d7cb3e6c355f40ce0c/library/rpi_ws281x/rpi_ws281x.py#L57
        """
        self.__pixels = rpi_ws281x.PixelStrip(
            num=self.__display_width * self.__display_height,
            pin=10, # SPI pin https://pinout.xyz/pinout/pin19_gpio10
            brightness=Config.get('leds.brightness', 3), # 0 - 255 
            strip_type=rpi_ws281x.WS2811_STRIP_RGB,
            gamma=None
        )

        self.__pixels.begin()

        if clear_screen:
            self.clear_screen()

    # CAUTION:
    # This method has been heavily optimized. The program spends the bulk of its execution time in this loop.
    # If making any changes, profile your code first to see if there are regressions, i.e.:
    #
    #   python3 -m cProfile -s cumtime video --url https://www.youtube.com/watch?v=AxuvUAjHYWQ --color-mode color
    #
    # Here are some graphs about the performance, generated like so:
    # https://gist.github.com/dasl-/d552c0abb38fca823e97fb3b49898f2d
    # https://docs.google.com/spreadsheets/d/1psa070FdMv2w8RPqzFuRVg1eqzTiLwlekClMsEG3qwE/edit#gid=716887181
    def display_frame(self, frame):
        # Each row is zig-zagged, so every other row needs to be flipped
        # horizontally.
        #
        # Starting at row 1, with stride 2, set each column to itself with
        # stride -1, which reverses the column.
        # frame[0::2, :, :] = frame[0::2, ::-1, :]

        # Additionally, each RGB tuple needs to be re-ordered to match the order
        # that's expected by the LED strip, which is defined in
        # self.__color_order.
        # frame = frame[:, :, self.__color_order]

        for x in range(self.__display_width):
            for y in range(self.__display_height):
                r, g, b = frame[y, x]
                self.__pixels.setPixelColorRGB(y * x, r, g, b)

        # We're done! Tell the underlying driver to send data to the LEDs.
        self.__pixels.show()

    def clear_screen(self):
        shape = [self.__display_height, self.__display_width, 3]
        self.display_frame(np.zeros(shape, np.uint8))
