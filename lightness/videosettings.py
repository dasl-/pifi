class VideoSettings:

    COLOR_MODE_COLOR = 'color'
    COLOR_MODE_BW = 'bw' # black and white
    COLOR_MODE_R = 'r'
    COLOR_MODE_G = 'g'
    COLOR_MODE_B = 'b'

    LOG_LEVEL_NORMAL = 'normal'
    LOG_LEVEL_VERBOSE = 'verbose'

    DEFAULT_DISPLAY_WIDTH = 28
    DEFAULT_DISPLAY_HEIGHT = 18

    DEFAULT_BRIGHTNESS = 3

    # One of the COLOR_MODE_* constants
    color_mode = COLOR_MODE_COLOR

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

    # Boolean
    should_play_audio = None

    # Boolean - saving the video allows us to avoid youtube-dl network calls to download the video if it's played again.
    should_save_video = None

    log_level = None

    # If True, the videoprocessor will periodically check the DB to see if it should abort playing the video
    should_check_abort_signals = None

    def __init__(
        self, color_mode = None, display_width = None, display_height = None,
        should_play_audio = True, brightness = None, flip_x = False, flip_y = False,
        should_save_video = False, log_level = None, should_check_abort_signals = False
    ):
        if color_mode == None:
            color_mode = self.COLOR_MODE_COLOR
        self.__set_color_mode(color_mode)

        if display_width == None:
            display_width = self.DEFAULT_DISPLAY_WIDTH
        self.display_width = display_width

        if display_height == None:
            display_height = self.DEFAULT_DISPLAY_HEIGHT
        self.display_height = display_height

        self.should_play_audio = should_play_audio

        if brightness == None:
            brightness = self.DEFAULT_BRIGHTNESS
        self.brightness = brightness

        self.flip_x = flip_x
        self.flip_y = flip_y
        self.should_save_video = should_save_video

        if log_level == None:
            log_level = self.LOG_LEVEL_NORMAL
        self.log_level = log_level

        self.should_check_abort_signals = should_check_abort_signals

    def __set_color_mode(self, color_mode):
        color_mode = color_mode.lower()
        if color_mode in [self.COLOR_MODE_COLOR, self.COLOR_MODE_BW, self.COLOR_MODE_R, self.COLOR_MODE_G, self.COLOR_MODE_B]:
            self.color_mode = color_mode
        else:
            raise Exception("Unknown color_mode: {}".format(color_mode))
