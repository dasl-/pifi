from apa102_pi.driver import apa102
import numpy as np

from pifi.config import Config
from pifi.led.drivers.driverbase import DriverBase

class DriverApa102(DriverBase):

    __MOSI_PIN = 10
    __SCLK_PIN = 11
    __LED_ORDER = 'rgb'

    def __init__(self, clear_screen=True):
        self.__pixels = apa102.APA102(
            num_led=(Config.get_or_throw('leds.display_width') * Config.get_or_throw('leds.display_height')),
            mosi=self.__MOSI_PIN,
            sclk=self.__SCLK_PIN,
            order=self.__LED_ORDER
        )

        brightness = Config.get('leds.brightness', 3)
        self.__pixels.set_global_brightness(brightness)
        if clear_screen:
            self.clear_screen()

        # Look up the order in which to write each color value to the LED strip.
        # It's 1-indexed, so subtract by 1.
        self.__color_order = [x - 1 for x in apa102.RGB_MAP[self.__LED_ORDER]]

        # Calculate the LED start "frame": 3 1 bits followed by 5 brightness bits. See
        # set_pixel in the apa102 implementation for this calculation.
        self.__ledstart = (brightness & 0b00011111) | self.__pixels.LED_START

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
        frame[0::2, :, :] = frame[0::2, ::-1, :]

        # Additionally, each RGB tuple needs to be re-ordered to match the order
        # that's expected by the LED strip, which is defined in
        # self.__color_order.
        frame = frame[:, :, self.__color_order]

        # Now, populate the LEDs array by flattening the array, interposing
        # each RGB triple with the "LED start frame".
        # See: https://github.com/dasl-/pifi/issues/26
        self.__pixels.leds = np.insert(frame.flat, range(0, frame.size, 3), self.__ledstart).tolist()

        # We're done! Tell the underlying driver to send data to the LEDs.
        self.__pixels.show()

    def clear_screen(self):
        self.__pixels.clear_strip()
