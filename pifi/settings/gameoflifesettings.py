from pifi.config import Config
from pifi.settings.ledsettings import LedSettings
from pifi.games.gamecolorhelper import GameColorHelper

class GameOfLifeSettings(LedSettings):

    DEFAULT_SEED_LIVENESS_PROBABILITY = 1 / 3
    DEFAULT_TICK_SLEEP = 0.07
    DEFAULT_GAME_OVER_DETECTION_LOOKBACK = 16
    DEFAULT_FADE = False
    DEFAULT_INVERT = False

    # tick_sleep: in seconds
    def __init__(
        self, display_width = None, display_height = None,
        brightness = None, flip_x = False, flip_y = False,
        seed_liveness_probability = None, tick_sleep = None,
        game_over_detection_lookback = None, game_color_mode = None,
        fade = None, invert = None
    ):
        super().__init__(
            color_mode = self.COLOR_MODE_COLOR, display_width = display_width, display_height = display_height,
            brightness = brightness, flip_x = flip_x, flip_y = flip_y
        )

        if seed_liveness_probability is None:
            seed_liveness_probability = self.DEFAULT_SEED_LIVENESS_PROBABILITY
        self.seed_liveness_probability = seed_liveness_probability

        if tick_sleep is None:
            tick_sleep = self.DEFAULT_TICK_SLEEP
        self.tick_sleep = tick_sleep

        if game_over_detection_lookback is None:
            game_over_detection_lookback = self.DEFAULT_GAME_OVER_DETECTION_LOOKBACK
        self.game_over_detection_lookback = game_over_detection_lookback

        GameColorHelper().set_game_color_mode(self, game_color_mode)

        if fade is None:
            fade = self.DEFAULT_FADE
        self.fade = fade

        if invert is None:
            invert = self.DEFAULT_INVERT
        self.invert = invert

    def from_config(self):
        super().from_config()
        config = self.get_values_from_config()

        if 'seed_liveness_probability' in config:
            self.seed_liveness_probability = config['seed_liveness_probability']
        if 'tick_sleep' in config:
            self.tick_sleep = config['tick_sleep']
        if 'game_over_detection_lookback' in config:
            self.game_over_detection_lookback = config['game_over_detection_lookback']
        if 'game_color_mode' in config:
            GameColorHelper().set_game_color_mode(self, config['game_color_mode'])
        if 'fade' in config:
            self.fade = config['fade']
        if 'invert' in config:
            self.invert = config['invert']

        return self

    def get_values_from_config(self):
        return Config().get_game_of_life_settings()
