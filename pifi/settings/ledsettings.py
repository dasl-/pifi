from pifi.logger import Logger

class LedSettings:

    COLOR_MODE_COLOR = 'color'
    COLOR_MODE_BW = 'bw' # black and white
    COLOR_MODE_R = 'red'
    COLOR_MODE_G = 'green'
    COLOR_MODE_B = 'blue'
    COLOR_MODE_INVERT_COLOR = 'inv_color'
    COLOR_MODE_INVERT_BW = 'inv_bw'

    DRIVER_APA102 = 'apa102'
    DRIVER_RGBMATRIX = 'rgbmatrix'

    COLOR_MODES = [
        COLOR_MODE_COLOR,
        COLOR_MODE_BW,
        COLOR_MODE_R,
        COLOR_MODE_G,
        COLOR_MODE_B,
        COLOR_MODE_INVERT_COLOR,
        COLOR_MODE_INVERT_BW,
    ]

    DEFAULT_DISPLAY_WIDTH = 28
    DEFAULT_DISPLAY_HEIGHT = 18

    DEFAULT_BRIGHTNESS = 3

    # color_mode: one of the COLOR_MODE_* constants
    # display_width: int - Number of pixels / units
    # display_height: int - Number of pixels / units
    # brightness: int - Global brightness value, max of 31
    # flip_x: boolean - swap left to right, depending on wiring
    # flip_y: boolean - swap top to bottom, depending on wiring
    # driver: one of the DRIVER_ constants
    def __init__(
        self, color_mode = None, display_width = None, display_height = None,
        brightness = None, flip_x = False, flip_y = False, driver = None
    ):
        # logger: used in child class(es)
        self._logger = Logger().set_namespace(self.__class__.__name__)

        if color_mode is None:
            color_mode = self.COLOR_MODE_COLOR
        self.set_color_mode(color_mode)

        if display_width is None:
            display_width = self.DEFAULT_DISPLAY_WIDTH
        self.display_width = display_width

        if display_height is None:
            display_height = self.DEFAULT_DISPLAY_HEIGHT
        self.display_height = display_height

        if brightness is None:
            brightness = self.DEFAULT_BRIGHTNESS
        self.brightness = brightness

        self.flip_x = flip_x
        self.flip_y = flip_y

        self.driver = driver

    def from_config(self):
        config = self.get_values_from_config()

        if 'display_width' in config:
            self.display_width = config['display_width']
        if 'display_height' in config:
            self.display_height = config['display_height']
        if 'brightness' in config:
            self.brightness = config['brightness']
        if 'flip_x' in config:
            self.flip_x = config['flip_x']
        if 'flip_y' in config:
            self.flip_y = config['flip_y']
        if 'driver' in config:
            self.driver = config['driver']

        return self

    def get_values_from_config(self):
        raise NotImplementedError("implement in child class")

    def set_color_mode(self, color_mode):
        color_mode = color_mode.lower()
        if color_mode in self.COLOR_MODES:
            self.color_mode = color_mode
        else:
            self.color_mode = self.COLOR_MODE_COLOR

    def is_color_mode_rgb(self):
        return self.color_mode in [self.COLOR_MODE_COLOR, self.COLOR_MODE_INVERT_COLOR]
