import os
import json
from lightness.logger import Logger
from lightness.directoryutils import DirectoryUtils

class Config:

    __custom_server_args = None
    __custom_video_args = None

    __CONFIG_FILENAME = 'config.json'
    __logger = None

    def __init__(self):
        self.__logger = Logger().set_namespace(self.__class__.__name__)
        self.__maybe_load_custom_config()

    def getServerConfig(self, key, default=None):
        if self.__custom_server_args:
            if key in self.__custom_server_args:
                return self.__custom_server_args[key]

        return default

    def getCustomVideoArgs(self):
        if self.__custom_video_args:
            return self.__custom_video_args

        return []

    def __maybe_load_custom_config(self):
        config_path = DirectoryUtils().root_dir + '/' + self.__CONFIG_FILENAME
        if not os.path.exists(config_path):
            self.__logger.info("No custom config found at: {}".format(config_path))
            return

        self.__logger.info("Found custom config found at: {}".format(config_path))
        with open(config_path) as config_json:
            data = json.load(config_json)
            if 'custom_server_args' in data:
                self.__custom_server_args = data['custom_server_args']
            if 'custom_video_args' in data:
                self.__custom_video_args = data['custom_video_args']
