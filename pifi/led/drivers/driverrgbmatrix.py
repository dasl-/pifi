import gc
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

        # Performance tuning - reduce flickering from timing issues
        options.gpio_slowdown = Config.get('rgbmatrix.gpio_slowdown', 4)
        options.pwm_bits = Config.get('rgbmatrix.pwm_bits', 11)
        options.pwm_lsb_nanoseconds = Config.get('rgbmatrix.pwm_lsb_nanoseconds', 130)
        options.limit_refresh_rate_hz = Config.get('rgbmatrix.limit_refresh_rate_hz', 0)
        options.disable_hardware_pulsing = Config.get('rgbmatrix.disable_hardware_pulsing', False)

        self.__matrix = RGBMatrix(options = options)
        self.__pixels = self.__matrix.CreateFrameCanvas()

        # Pre-allocate image buffer to avoid per-frame allocations that trigger GC
        self.__width = options.cols
        self.__height = options.rows
        self.__img_buffer = Image.new('RGB', (self.__width, self.__height))

        if clear_screen:
            self.clear_screen()

    def display_frame(self, frame):
        # Disable GC during the critical display section to prevent timing jitter
        gc_was_enabled = gc.isenabled()
        gc.disable()

        try:
            # Reuse pre-allocated image buffer instead of creating new Image each frame
            # frombuffer with 'raw' mode avoids a data copy
            self.__img_buffer = Image.frombuffer(
                'RGB',
                (self.__width, self.__height),
                frame.astype('uint8').tobytes(),
                'raw',
                'RGB',
                0,
                1
            )
            self.__pixels.SetImage(self.__img_buffer)
            self.__pixels = self.__matrix.SwapOnVSync(self.__pixels)
        finally:
            if gc_was_enabled:
                gc.enable()

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
