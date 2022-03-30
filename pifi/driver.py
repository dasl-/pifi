from apa102_pi.driver import apa102
from rgbmatrix import RGBMatrix, RGBMatrixOptions
from PIL import Image

class APA102Driver():
    # LED Settings
    __MOSI_PIN = 10
    __SCLK_PIN = 11
    __LED_ORDER = 'rbg'

    def __init__(self, led_settings, clear_screen=False):
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

    # CAUTION:
    # This method has been heavily optimized. The program spends the bulk of its execution time in this loop.
    # If making any changes, profile your code first to see if there are regressions, i.e.:
    #
    #   python3 -m cProfile -s cumtime video --url https://www.youtube.com/watch?v=AxuvUAjHYWQ --color-mode color
    #
    # In the nested for loop, function calls are to be avoided. Inlining them is more performant.
    #
    # See: https://github.com/dasl-/pifi/commit/9640268084acb0c46b2624178f350017ab666d41
    def display_frame(self, frame):
        width, height = self.__led_settings.display_width, self.__led_settings.display_height
        for x in range(width):
            for y in range(height):
                # TODO(dasl): re-implement this logic using numpy vectorization
                # to improve performance.
                # each row is zig-zagged, so every other row needs to be flipped horizontally
                if (y % 2 == 0):
                    pixel_index = (y * width) + (width - x - 1)
                else:
                    pixel_index = (y * width) + x

                # order on the strip is RBG (refer to self.__LED_ORDER)
                self.__pixels.set_pixel(x, y, r, b, g)
        self.__pixels.show()

    def clear_screen(self):
        self.__pixels.clear_strip()

class RGBMatrixDriver():
    def __init__(self, led_settings, clear_screen=False):
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
