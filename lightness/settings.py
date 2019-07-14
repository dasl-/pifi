class Settings:

    COLOR_MODE_COLOR = 'color'
    COLOR_MODE_BW = 'bw' # black and white
    COLOR_MODE_R = 'r'
    COLOR_MODE_G = 'g'
    COLOR_MODE_B = 'b'

    LOG_LEVEL_NORMAL = 'normal'
    LOG_LEVEL_VERBOSE = 'verbose'

    LOG_FILE_TERMINAL = 'terminal'

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
    should_play_audio = False

    # Boolean - saving the video allows us to avoid youtube-dl network calls to download the video if it's played again.
    should_save_video = False

    log_level = None

    log_file = None

    def __init__(self, args):
        self.__set_color_mode(args.color_mode)
        self.display_width = args.display_width
        self.display_height = args.display_height
        self.should_play_audio = args.should_play_audio
        self.brightness = args.brightness
        self.flip_x = args.flip_x
        self.flip_y = args.flip_y
        self.should_save_video = args.should_save_video
        self.log_level = args.log_level
        self.log_file = args.log_file

    def __set_color_mode(self, color_mode):
        color_mode = color_mode.lower()
        if color_mode in [self.COLOR_MODE_COLOR, self.COLOR_MODE_BW, self.COLOR_MODE_R, self.COLOR_MODE_G, self.COLOR_MODE_B]:
            self.color_mode = color_mode
        else:
            raise Exception("Unknown color_mode: {}".format(color_mode))
