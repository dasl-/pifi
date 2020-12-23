import json
import traceback

from pifi.config import Config
from pifi.settings.ledsettings import LedSettings
from pifi.games.gamecolorhelper import GameColorHelper

class SnakeSettings(LedSettings):

    DEFAULT_DIFFICULTY = 7
    DEFAULT_NUM_PLAYERS = 1

    game_color_mode = None
    difficulty = None
    num_players = None

    def __init__(
        self, display_width = None, display_height = None,
        brightness = None, flip_x = False, flip_y = False, log_level = None,
        game_color_mode = None, difficulty = None, num_players = None
    ):
        super().__init__(
            color_mode = self.COLOR_MODE_COLOR, display_width = display_width, display_height = display_height,
            brightness = brightness, flip_x = flip_x, flip_y = flip_y, log_level = log_level
        )

        self.__set_difficulty(difficulty)
        self.__set_num_players(num_players)
        GameColorHelper().set_game_color_mode(self, game_color_mode)

    def from_config(self):
        super().from_config()
        # config = self.get_values_from_config()
        return self

    def from_playlist_item_in_queue(self, snake_record):
        snake_record_settings = {}
        try:
            snake_record_settings = json.loads(snake_record['settings'])
        except Exception as e:
            self._logger.error('Caught exception: {}'.format(traceback.format_exc()))
            return self

        try:
            self.__set_difficulty(int(snake_record_settings['difficulty']))
        except Exception as e:
            self._logger.error('Caught exception: {}'.format(traceback.format_exc()))
        try:
            self.__set_num_players(int(snake_record_settings['num_players']))
        except Exception as e:
            self._logger.error('Caught exception: {}'.format(traceback.format_exc()))

        return self.from_config()

    def get_values_from_config(self):
        return Config().get_snake_settings()

    def __set_difficulty(self, difficulty):
        if difficulty == None or difficulty < 0 or difficulty > 9:
            difficulty = self.DEFAULT_DIFFICULTY
        self.difficulty = difficulty

    def __set_num_players(self, num_players):
        if num_players == None or num_players < 1:
            num_players = self.DEFAULT_NUM_PLAYERS
        if num_players > 4:
            num_players = 4
        self.num_players = num_players
