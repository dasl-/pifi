import os
import json
from pifi.logger import Logger
from pifi.directoryutils import DirectoryUtils

class Config:

    CONFIG_PATH = DirectoryUtils().root_dir + '/config.json'

    def __init__(self):
        self.__logger = Logger().set_namespace(self.__class__.__name__)
        self.__server_config = {}
        self.__queue_config = {}
        self.__video_settings = {}
        self.__game_of_life_settings = {}
        self.__snake_settings = {}
        self.__maybe_load_config()

    def get_server_config(self, key, default=None):
        if key in self.__server_config:
            return self.__server_config[key]

        return default

    def get_queue_config(self, key, default=None):
        if key in self.__queue_config:
            return self.__queue_config[key]

        return default

    def get_video_settings(self):
        return self.__video_settings

    def get_game_of_life_settings(self):
        return self.__game_of_life_settings

    def get_snake_settings(self):
        return self.__snake_settings

    def __maybe_load_config(self):
        if not os.path.exists(self.CONFIG_PATH):
            self.__logger.info("No config file found at: {}".format(self.CONFIG_PATH))
            return

        self.__logger.info("Found config file at: {}".format(self.CONFIG_PATH))
        with open(self.CONFIG_PATH) as config_json:
            data = json.load(config_json)
            if 'server_config' in data:
                self.__server_config = data['server_config']
                self.__logger.info("Found server config: {}".format(self.__server_config))
            if 'queue_config' in data:
                self.__queue_config = data['queue_config']
                self.__logger.info("Found queue config: {}".format(self.__queue_config))

            led_settings = {}
            if 'led_settings' in data:
                led_settings = data['led_settings']
                self.__logger.info("Found LED settings: {}".format(led_settings))
                self.__video_settings = led_settings
                self.__game_of_life_settings = led_settings
                self.__snake_settings = led_settings

            if 'video_settings' in data:
                self.__video_settings = {**led_settings, **data['video_settings']}
                self.__logger.info("Found video settings: {}".format(self.__video_settings))
            if 'game_of_life_settings' in data:
                self.__game_of_life_settings = {**led_settings, **data['game_of_life_settings']}
                self.__logger.info("Found game of life settings: {}".format(self.__game_of_life_settings))
            if 'snake_settings' in data:
                self.__snake_settings = {**led_settings, **data['snake_settings']}
                self.__logger.info("Found snake settings: {}".format(self.__game_of_life_settings))
