import datetime
import pytz

class Logger:

    # Settings
    __namespace = ""

    def __init__(self):
        pass

    def set_namespace(self, namespace):
        self.__namespace = namespace
        return self

    def debug(self, msg):
        msg = self.__format_msg(level = 'debug', msg = msg)
        print(msg)

    def info(self, msg):
        msg = self.__format_msg(level = 'info', msg = msg)
        print(msg)

    def warning(self, msg):
        msg = self.__format_msg(level = 'warning', msg = msg)
        print(msg)

    def error(self, msg):
        msg = self.__format_msg(level = 'error', msg = msg)
        print(msg)

    def __format_msg(self, level, msg):
        return (datetime.datetime.now(pytz.timezone('UTC')).isoformat() +
            " [" + level + "] [" + self.__namespace + "] " + msg)
