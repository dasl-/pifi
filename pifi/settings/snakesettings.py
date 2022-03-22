import json
import traceback

from pifi.config import Config
from pifi.settings.ledsettings import LedSettings
from pifi.games.gamecolorhelper import GameColorHelper

class SnakeSettings(LedSettings):

    DEFAULT_DIFFICULTY = 7
    DEFAULT_NUM_PLAYERS = 1
    DEFAULT_APPLE_COUNT = 15

    def __init__(
        self, display_width = None, display_height = None,
        brightness = None, flip_x = False, flip_y = False, log_level = None,
        game_color_mode = None, difficulty = None, num_players = None, apple_count = None
    ):
        super().__init__(
            color_mode = self.COLOR_MODE_COLOR, display_width = display_width, display_height = display_height,
            brightness = brightness, flip_x = flip_x, flip_y = flip_y, log_level = log_level
        )

        self.__set_difficulty(difficulty)
        self.__set_num_players(num_players)
        self.__set_apple_count(apple_count)
        GameColorHelper().set_game_color_mode(self, game_color_mode)

    def from_config(self):
        super().from_config()
        # config = self.get_values_from_config()
        return self

    def from_playlist_item_in_queue(self, snake_record):
        snake_record_settings = {}
        try:
            snake_record_settings = json.loads(snake_record['settings'])
        except Exception:
            self._logger.error('Caught exception: {}'.format(traceback.format_exc()))
            return self

        try:
            self.__set_difficulty(int(snake_record_settings['difficulty']))
        except Exception:
            self._logger.error('Caught exception: {}'.format(traceback.format_exc()))
        try:
            self.__set_num_players(int(snake_record_settings['num_players']))
        except Exception:
            self._logger.error('Caught exception: {}'.format(traceback.format_exc()))
        try:
            self.__set_apple_count(int(snake_record_settings['apple_count']))
        except Exception:
            self._logger.error('Caught exception: {}'.format(traceback.format_exc()))

        return self.from_config()

    def get_values_from_config(self):
        return Config().get_snake_settings()

    def __set_difficulty(self, difficulty):
        if difficulty is None or difficulty < 0 or difficulty > 9:
            difficulty = self.DEFAULT_DIFFICULTY
        self.difficulty = difficulty

    def __set_num_players(self, num_players):
        if num_players is None or num_players < 1:
            num_players = self.DEFAULT_NUM_PLAYERS
        if num_players > 4:
            num_players = 4
        self.num_players = num_players

    def __set_apple_count(self, apple_count):
        if apple_count is None or apple_count < 1:
            apple_count = self.DEFAULT_APPLE_COUNT
        if apple_count > 999:
            apple_count = 999
        self.apple_count = apple_count
