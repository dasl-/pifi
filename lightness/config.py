import os
import json
from lightness.logger import Logger
from lightness.directoryutils import DirectoryUtils

class Config:

    __server_config = None
    __video_settings = None

    __CONFIG_FILENAME = 'config.json'
    __logger = None

    def __init__(self):
        self.__logger = Logger().set_namespace(self.__class__.__name__)
        self.__video_settings = {}
        self.__server_config = {}
        self.__maybe_load_config()

    def get_server_config(self, key, default=None):
        if key in self.__server_config:
            return self.__server_config[key]

        return default

    def get_video_settings(self):
        return self.__video_settings

    def __maybe_load_config(self):
        config_path = DirectoryUtils().root_dir + '/' + self.__CONFIG_FILENAME
        if not os.path.exists(config_path):
            self.__logger.info("No config file found at: {}".format(config_path))
            return

        self.__logger.info("Found config file at: {}".format(config_path))
        with open(config_path) as config_json:
            data = json.load(config_json)
            if 'server_config' in data:
                self.__server_config = data['server_config']
            if 'video_settings' in data:
                self.__video_settings = data['video_settings']
