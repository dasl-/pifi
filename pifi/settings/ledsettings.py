from pifi.config import Config
from pifi.logger import Logger

class LedSettings:

    COLOR_MODE_COLOR = 'color'
    COLOR_MODE_BW = 'bw' # black and white
    COLOR_MODE_R = 'red'
    COLOR_MODE_G = 'green'
    COLOR_MODE_B = 'blue'
    COLOR_MODE_INVERT_COLOR = 'inv_color'
    COLOR_MODE_INVERT_BW = 'inv_bw'

    COLOR_MODES = [
        COLOR_MODE_COLOR,
        COLOR_MODE_BW,
        COLOR_MODE_R,
        COLOR_MODE_G,
        COLOR_MODE_B,
        COLOR_MODE_INVERT_COLOR,
        COLOR_MODE_INVERT_BW,
    ]

    LOG_LEVEL_NORMAL = 'normal'
    LOG_LEVEL_VERBOSE = 'verbose'

    DEFAULT_DISPLAY_WIDTH = 28
    DEFAULT_DISPLAY_HEIGHT = 18

    DEFAULT_BRIGHTNESS = 3

    # One of the COLOR_MODE_* constants
    color_mode = None

    # Int - Number of pixels / units
    display_width = None

    # Int - Number of pixels / units
    display_height = None

    # Int - Global brightness value, max of 31
    brightness = None

    # Boolean - swap left to right, depending on wiring
    flip_x = None

    # Boolean - swap top to bottom, depending on wiring
    flip_y = None

    log_level = None

    # used in child class(es)
    _logger = None

    def __init__(
        self, color_mode = None, display_width = None, display_height = None,
        brightness = None, flip_x = False, flip_y = False, log_level = None,
    ):
        self._logger = Logger().set_namespace(self.__class__.__name__)

        if color_mode == None:
            color_mode = self.COLOR_MODE_COLOR
        self.set_color_mode(color_mode)

        if display_width == None:
            display_width = self.DEFAULT_DISPLAY_WIDTH
        self.display_width = display_width

        if display_height == None:
            display_height = self.DEFAULT_DISPLAY_HEIGHT
        self.display_height = display_height

        if brightness == None:
            brightness = self.DEFAULT_BRIGHTNESS
        self.brightness = brightness

        self.flip_x = flip_x
        self.flip_y = flip_y

        if log_level == None:
            log_level = self.LOG_LEVEL_NORMAL
        self.log_level = log_level

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
        if 'log_level' in config:
            self.log_level = config['log_level']

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
        return self.color_mode in [self.COLOR_MODE_COLOR, self.COLOR_MODE_INVERT_COLOR];
