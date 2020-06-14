from pifi.settings.ledsettings import LedSettings
from pifi.games.gamecolorhelper import GameColorHelper

class SnakeSettings(LedSettings):

    DEFAULT_DIFFICULTY = 7

    game_color_mode = None
    difficulty = None

    # If True, the videoprocessor will periodically check the DB to see if it should skip playing the current video
    should_check_playlist = None

    def __init__(
        self, display_width = None, display_height = None,
        brightness = None, flip_x = False, flip_y = False, log_level = None,
        game_color_mode = None, should_check_playlist = False, difficulty = None
    ):
        super().__init__(
            color_mode = self.COLOR_MODE_COLOR, display_width = display_width, display_height = display_height,
            brightness = brightness, flip_x = flip_x, flip_y = flip_y, log_level = log_level
        )

        if difficulty == None:
            difficulty = self.DEFAULT_DIFFICULTY
        self.difficulty = difficulty

        game_color_helper = GameColorHelper()
        game_color_helper.set_game_color_mode(self, game_color_mode)

        self.should_check_playlist = should_check_playlist
