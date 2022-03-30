class APA102Driver():
    # LED Settings
    __MOSI_PIN = 10
    __SCLK_PIN = 11
    __LED_ORDER = 'rbg'

    def __init__(self, led_settings, clear_screen=False):
        from apa102_pi.driver import apa102

        self.__led_settings = led_settings
        # Add 8 because otherwise the last 8 LEDs don't powered correctly. Weird driver glitch?
        self.__pixels = apa102.APA102(
            num_led=(led_settings.display_width * led_settings.display_height + 8),
            mosi=self.__MOSI_PIN,
            sclk=self.__SCLK_PIN,
            order=self.__LED_ORDER
        )
        self.__pixels.set_global_brightness(led_settings.brightness)
        if clear_screen:
            self.clear_screen()

        # Look up the order in which to write each color value to the LED strip.
        # It's 1-indexed, so subtract by 1.
        self.__color_order = [x-1 for x in apa102.RGB_MAP[self.__LED_ORDER]]

        # Calculate the LED start "frame": 3 1 bits followed by 5 brightness bits. See
        # set_pixel in the apa102 implementation for this calculation.
        self.__ledstart = (led_settings.brightness & 0b00011111) | self.__pixels.LED_START

    # CAUTION:
    # This method has been heavily optimized. The program spends the bulk of its execution time in this loop.
    # If making any changes, profile your code first to see if there are regressions, i.e.:
    #
    #   python3 -m cProfile -s cumtime video --url https://www.youtube.com/watch?v=AxuvUAjHYWQ --color-mode color
    def display_frame(self, frame):
        width, height = self.__led_settings.display_width, self.__led_settings.display_height
        # Each row is zig-zagged, so every other row needs to be flipped
        # horizontally.
        #
        # Additionally, each RGB tuple needs to be re-ordered to match the order
        # that's expected by the LED strip, which is defined in
        # self.__color_order.
        #
        # This terse statement tells numpy to do all of the above. Starting
        # at row 1, with stride 2, set each column to itself with stride -1,
        # which reverses the column.
        # And, in the 3rd dimension, set each array via the desired index
        # ordering.
        frame[1::2,:,:] = frame[1::2,::-1,self.color_order]

        # Now, populate the LEDs array by flattening the array, interposing
        # each RGB triple with the "LED start frame".
        self.__pixels.leds = np.insert(frame.flat, range(0, frame.size, 3), self.__ledstart)

        # We're done! Tell the underlying driver to send data to the LEDs.
        self.__pixels.show()

    def clear_screen(self):
        self.__pixels.clear_strip()

class RGBMatrixDriver():
    def __init__(self, led_settings, clear_screen=False):
        from rgbmatrix import RGBMatrix, RGBMatrixOptions
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
        from PIL import Image
        img = Image.fromarray(frame, mode='RGB')
        self.__pixels.SetImage(img)
        self.__pixels = self.__matrix.SwapOnVSync(self.__pixels)

    def clear_screen(self):
        self.__pixels.Clear()
        self.__matrix.Clear()
