import os
import pyjson5
from pifi.logger import Logger
from pifi.directoryutils import DirectoryUtils

class ConfigLoader:

    CONFIG_PATH = DirectoryUtils().root_dir + '/config.json'

    __is_loaded = False

    __server_config = {}
    __led_settings = {}
    __video_settings = {}
    __game_of_life_settings = {}
    __snake_settings = {}

    def __init__(self, should_set_log_level = True):
        self.__logger = Logger().set_namespace(self.__class__.__name__)
        self.__load_config_if_not_loaded(should_set_log_level)

    def get_server_config(self, key, default=None):
        if key in ConfigLoader.__server_config:
            return ConfigLoader.__server_config[key]

        return default

    def get_led_settings(self):
        return ConfigLoader.__led_settings

    def get_video_settings(self):
        return ConfigLoader.__video_settings

    def get_game_of_life_settings(self):
        return ConfigLoader.__game_of_life_settings

    def get_snake_settings(self):
        return ConfigLoader.__snake_settings

    def __load_config_if_not_loaded(self, should_set_log_level):
        if ConfigLoader.__is_loaded:
            return

        if not os.path.exists(self.CONFIG_PATH):
            raise Exception(f"No config file found at: {self.CONFIG_PATH}.")

        self.__logger.info(f"Found config file at: {self.CONFIG_PATH}")
        with open(self.CONFIG_PATH) as config_json:
            data = pyjson5.decode(config_json.read())
            if 'log_level' in data and should_set_log_level:
                Logger.set_level(data['log_level'])
            if 'server_config' in data:
                ConfigLoader.__server_config = data['server_config']
                self.__logger.info(f"Found server config: {ConfigLoader.__server_config}")
            if 'led_settings' in data:
                ConfigLoader.__led_settings = data['led_settings']
                self.__logger.info(f"Found LED settings: {ConfigLoader.__led_settings}")
            if 'video_settings' in data:
                ConfigLoader.__video_settings = data['video_settings']
                self.__logger.info(f"Found video settings: {ConfigLoader.__video_settings}")
            if 'game_of_life_settings' in data:
                ConfigLoader.__game_of_life_settings = data['game_of_life_settings']
                self.__logger.info(f"Found game of life settings: {ConfigLoader.__game_of_life_settings}")
            if 'snake_settings' in data:
                ConfigLoader.__snake_settings = data['snake_settings']
                self.__logger.info(f"Found snake settings: {ConfigLoader.__game_of_life_settings}")

        ConfigLoader.__is_loaded = True
