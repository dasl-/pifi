import json

from pifi.configloader import ConfigLoader
from pifi.games.gamecolorhelper import GameColorHelper
from pifi.settings.ledsettings import LedSettings

class SnakeSettings(LedSettings):

    DEFAULT_DIFFICULTY = 7
    DEFAULT_NUM_PLAYERS = 1
    DEFAULT_APPLE_COUNT = 15

    # difficulty: snake difficulty setting
    # num_players: number of snake game players
    # apple_count: apple count for multiplayer snake game
    def __init__(
        self, display_width = None, display_height = None,
        brightness = None, flip_x = False, flip_y = False,
        game_color_mode = None, difficulty = None, num_players = None, apple_count = None
    ):
        super().__init__(
            color_mode = self.COLOR_MODE_COLOR, display_width = display_width, display_height = display_height,
            brightness = brightness, flip_x = flip_x, flip_y = flip_y,
        )

        self.__set_difficulty(difficulty)
        self.__set_num_players(num_players)
        self.__set_apple_count(apple_count)
        GameColorHelper().set_game_color_mode(self, game_color_mode)

    @classmethod
    def from_playlist_item_in_queue(cls, snake_record):
        settings = SnakeSettings.from_config()
        snake_record_settings = json.loads(snake_record['settings'])
        settings.__set_difficulty(int(snake_record_settings['difficulty']))
        settings.__set_num_players(int(snake_record_settings['num_players']))
        settings.__set_apple_count(int(snake_record_settings['apple_count']))
        return settings

    def get_values_from_config(self):
        return ConfigLoader().get_snake_settings()

    def populate_values_from_config(self):
        super().populate_values_from_config()

        config = self.get_values_from_config()
        if 'difficulty' in config:
            self.__set_difficulty(int(config['difficulty']))
        if 'num_players' in config:
            self.__set_num_players(int(config['num_players']))
        if 'apple_count' in config:
            self.__set_apple_count(int(config['apple_count']))

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
