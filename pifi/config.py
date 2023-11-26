import os
import pyjson5
from pifi.logger import Logger
from pifi.directoryutils import DirectoryUtils

class Config:

    CONFIG_PATH = DirectoryUtils().root_dir + '/config.json'
    __DEFAULT_CONFIG_PATH = DirectoryUtils().root_dir + '/default_config.json'

    __is_loaded = False
    __config = {}
    __logger = Logger().set_namespace('Config')
    __PATH_SEP = '.'

    # Get a key from config using dot notation: "foo.bar.baz"
    @staticmethod
    def get(key, default = None):
        return Config.__get(key, should_throw = False, default = default)

    @staticmethod
    def get_or_throw(key):
        return Config.__get(key, should_throw = True, default = None)

    @staticmethod
    def set(key, value):
        Config.load_config_if_not_loaded()

        new_config = Config.__set_nested(key.split(Config.__PATH_SEP), value, Config.__config)
        Config.__config = new_config

    @staticmethod
    def load_config_if_not_loaded(should_set_log_level = True):
        if Config.__is_loaded:
            return

        if not os.path.exists(Config.__DEFAULT_CONFIG_PATH):
            raise Exception(f"No default config file found at: {Config.__DEFAULT_CONFIG_PATH}.")

        if not os.path.exists(Config.CONFIG_PATH):
            raise Exception(f"No config file found at: {Config.CONFIG_PATH}.")

        Config.__logger.info(f"Found config file at: {Config.CONFIG_PATH}")
        with open(Config.__DEFAULT_CONFIG_PATH) as default_config_json, open(Config.CONFIG_PATH) as config_json:
            default_config = pyjson5.decode(default_config_json.read())
            config = pyjson5.decode(config_json.read())
            Config.__merge_dicts(default_config, config)
            Config.__config = default_config

            if 'log_level' in Config.__config and should_set_log_level:
                Logger.set_level(Config.__config['log_level'])

        Config.__is_loaded = True

    @staticmethod
    def __get(key, should_throw = False, default = None):
        Config.load_config_if_not_loaded()

        config = Config.__config
        for key in key.split(Config.__PATH_SEP):
            if key in config:
                config = config[key]
            else:
                if should_throw:
                    raise KeyError(f"{key}")
                else:
                    return default
        return config

    """
    keys: list of string keys
    value: any value
    my_dict: a dict in which to set the nested list of keys to the given value

    returns: a dict identical to my_dict, except with the nested dict element identified
        by the list of keys set to the given value

    Ex:
        >>> __set_nested(['foo'], 1, {})
        {'foo': 1}

        >>> __set_nested(['foo', 'bar'], 1, {})
        {'foo': {'bar': 1}}

        >>> __set_nested(['foo'], 1, {'foo': 2})
        {'foo': 1}

        >>> __set_nested(['foo', 'bar'], 1, {'foo': {'baz': 2}})
        {'foo': {'baz': 2, 'bar': 1}}
    """
    @staticmethod
    def __set_nested(keys, value, my_dict):
        if len(keys) > 1:
            key = keys[0]
            if key in my_dict:
                if isinstance(my_dict[key], dict):
                    new_config = my_dict[key]
                else:
                    new_config = {}
            else:
                new_config = {}
            return {**my_dict, **{key: Config.__set_nested(keys[1:], value, new_config)}}
        elif len(keys) == 1:
            my_dict[keys[0]] = value
            return my_dict
        else:
            raise Exception("No keys were given.")

    """
    Recursively merge two dicts. The dict d1 will be modified in-place.

    Example:
    d1 = {'a': {'b': {'c': 1, 'd': 2}, 'e': 3}, 'aa': {'bb': {'cc': 11}}}
    d2 = {'a': {'b': {'d': 666, 'f': 666}}, 'aa': {'bb': 666}, 'aaa': 666}
    Config.__merge_dicts(d1, d2)

    The contents of d1 will now be:
    {'a': {'b': {'c': 1, 'd': 666, 'f': 666}, 'e': 3}, 'aa': {'bb': 666}, 'aaa': 666}
    """
    @staticmethod
    def __merge_dicts(d1, d2):
        for k, v in d2.items():
            if (k in d1 and isinstance(d1[k], dict) and isinstance(d2[k], dict)):
                Config.__dict_merge(d1[k], d2[k])
            else:
                d1[k] = d2[k]
