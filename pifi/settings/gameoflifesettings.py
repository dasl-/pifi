from pifi.settings.ledsettings import LedSettings
from pifi.games.gamecolorhelper import GameColorHelper

class GameOfLifeSettings(LedSettings):

    DEFAULT_SEED_LIVENESS_PROBABILITY = 1/3
    DEFAULT_TICK_SLEEP = 0
    DEFAULT_GAME_OVER_DETECTION_LOOKBACK = 16
    DEFAULT_FADE = False
    DEFAULT_INVERT = False

    seed_liveness_probability = None
    tick_sleep = None # seconds
    game_over_detection_lookback = None
    game_color_mode = None
    fade = None
    invert = None

    def __init__(
        self, display_width = None, display_height = None,
        brightness = None, flip_x = False, flip_y = False, log_level = None,
        seed_liveness_probability = None, tick_sleep = None,
        game_over_detection_lookback = None, game_color_mode = None,
        fade = None, invert = None
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

        game_color_helper = GameColorHelper()
        game_color_helper.set_game_color_mode(self, game_color_mode)

        self.fade = fade
        self.invert = invert
