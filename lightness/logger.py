import datetime
import pytz
import sys

class Logger:

    # Settings
    __namespace = None
    __info_log_file = None
    __err_log_file = None

    def __init__(self):
        self.__namespace = ""
        self.__info_log_file = sys.stdout
        self.__err_log_file = sys.stderr

    def set_namespace(self, namespace):
        self.__namespace = namespace
        return self

    def set_log_files(self, info_log_file, err_log_file):
        self.__info_log_file = open(info_log_file, 'a')
        self.__err_log_file = open(err_log_file, 'a')
        return self

    def debug(self, msg):
        msg = self.__format_msg(level = 'debug', msg = msg)
        print(msg, file = self.__info_log_file, flush = True)

    def info(self, msg):
        msg = self.__format_msg(level = 'info', msg = msg)
        print(msg, file = self.__info_log_file, flush = True)

    def warning(self, msg):
        msg = self.__format_msg(level = 'warning', msg = msg)
        print(msg, file = self.__err_log_file, flush = True)

    def error(self, msg):
        msg = self.__format_msg(level = 'error', msg = msg)
        print(msg, file = self.__err_log_file, flush = True)

    def __format_msg(self, level, msg):
        return (datetime.datetime.now(pytz.timezone('UTC')).isoformat() +
            " [" + level + "] [" + self.__namespace + "] " + msg)
