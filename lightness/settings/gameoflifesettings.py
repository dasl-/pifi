from lightness.settings.ledsettings import LedSettings

class GameOfLifeSettings(LedSettings):

    DEFAULT_SEED_LIVENESS_PROBABILITY = 1/3
    DEFAULT_TICK_SLEEP = 0
    DEFAULT_GAME_OVER_DETECTION_LOOKBACK = 10

    GAME_COLOR_MODE_RANDOM = 'random'
    GAME_COLOR_MODE_RED = 'red'
    GAME_COLOR_MODE_GREEN = 'green'
    GAME_COLOR_MODE_BLUE = 'blue'
    GAME_COLOR_MODE_BW = 'bw'
    GAME_COLOR_MODE_RAINBOW = 'rainbow'

    # Lists all modes except GAME_COLOR_MODE_RANDOM
    GAME_COLOR_MODES = [
        GAME_COLOR_MODE_RED, GAME_COLOR_MODE_GREEN, GAME_COLOR_MODE_BLUE,
        GAME_COLOR_MODE_BW, GAME_COLOR_MODE_RAINBOW
    ]

    seed_liveness_probability = None
    tick_sleep = None # seconds
    game_over_detection_lookback = None
    game_color_mode = None

    def __init__(
        self, display_width = None, display_height = None,
        brightness = None, flip_x = False, flip_y = False, log_level = None,
        seed_liveness_probability = None, tick_sleep = None,
        game_over_detection_lookback = None, game_color_mode = None,
    ):
        super().__init__(
            color_mode = self.COLOR_MODE_COLOR, display_width = display_width, display_height = display_height,
            brightness = brightness, flip_x = flip_x, flip_y = flip_y, log_level = log_level
        )

        if seed_liveness_probability == None:
            seed_liveness_probability = self.DEFAULT_SEED_LIVENESS_PROBABILITY
        self.seed_liveness_probability = seed_liveness_probability

        if tick_sleep == None:
            tick_sleep = self.DEFAULT_TICK_SLEEP
        self.tick_sleep = tick_sleep

        if game_over_detection_lookback == None:
            game_over_detection_lookback = self.DEFAULT_GAME_OVER_DETECTION_LOOKBACK
        self.game_over_detection_lookback = game_over_detection_lookback

        if game_color_mode == None:
            game_color_mode = self.GAME_COLOR_MODE_RANDOM
        self.__set_game_color_mode(game_color_mode)

    def __set_game_color_mode(self, game_color_mode):
        game_color_mode = game_color_mode.lower()
        if game_color_mode in self.GAME_COLOR_MODES or game_color_mode == self.GAME_COLOR_MODE_RANDOM:
            self.game_color_mode = game_color_mode
        else:
            raise Exception("Unknown game_color_mode: {}".format(game_color_mode))
