from pifi.settings.ledsettings import LedSettings
from pifi.games.gamecolorhelper import GameColorHelper

class SnakeSettings(LedSettings):

    DEFAULT_TICK_SLEEP = 0.5

    tick_sleep = None # seconds
    game_color_mode = None

    def __init__(
        self, display_width = None, display_height = None,
        brightness = None, flip_x = False, flip_y = False, log_level = None,
        tick_sleep = None, game_color_mode = None,
    ):
        super().__init__(
            color_mode = self.COLOR_MODE_COLOR, display_width = display_width, display_height = display_height,
            brightness = brightness, flip_x = flip_x, flip_y = flip_y, log_level = log_level
        )

        if tick_sleep == None:
            tick_sleep = self.DEFAULT_TICK_SLEEP
        self.tick_sleep = tick_sleep

        game_color_helper = GameColorHelper()
        game_color_helper.set_game_color_mode(self, game_color_mode)
