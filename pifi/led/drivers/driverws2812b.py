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
            brightness=Config.get('leds.brightness'), # 0 - 255
            strip_type=rpi_ws281x.WS2811_STRIP_GRB,
            gamma=None
        )

        self.__pixels.begin()

        if clear_screen:
            self.clear_screen()

    def display_frame(self, frame):
        # TODO: vectorize this shit
        frame = frame.tolist()
        for x in range(self.__display_width):
            for y in range(self.__display_height):
                r, g, b = frame[y][x]
                pixel_index = x * self.__display_height + y
                # TODO: this could also maybe be vectorized? e.g. use setPixelColor instead of setPixelColorRGB
                # https://github.com/rpi-ws281x/rpi-ws281x-python/blob/29a99c00ac3eefebf01480d7cb3e6c355f40ce0c/library/rpi_ws281x/rpi_ws281x.py#L140-L149
                self.__pixels.setPixelColorRGB(pixel_index, r, g, b)

        # We're done! Tell the underlying driver to send data to the LEDs.
        self.__pixels.show()

    def clear_screen(self):
        shape = [self.__display_height, self.__display_width, 3]
        self.display_frame(np.zeros(shape, np.uint8))
