import datetime
import pytz
import sys

class Logger:

    __namespace = None

    def __init__(self):
        self.__namespace = ""

    def set_namespace(self, namespace):
        self.__namespace = namespace
        return self

    def debug(self, msg):
        msg = self.__format_msg(level = 'debug', msg = msg)
        print(msg, file = sys.stdout, flush = True)

    def info(self, msg):
        msg = self.__format_msg(level = 'info', msg = msg)
        print(msg, file = sys.stdout, flush = True)

    def warning(self, msg):
        msg = self.__format_msg(level = 'warning', msg = msg)
        print(msg, file = sys.stderr, flush = True)

    def error(self, msg):
        msg = self.__format_msg(level = 'error', msg = msg)
        print(msg, file = sys.stderr, flush = True)

    def __format_msg(self, level, msg):
        return (datetime.datetime.now(pytz.timezone('UTC')).isoformat() +
            " [" + level + "] [" + self.__namespace + "] " + msg)
