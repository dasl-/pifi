import datetime
import pytz
import sys
import random
import string

class Logger:

    # Log levels
    QUIET = 100
    ERROR = 40
    WARNING = 30
    INFO = 20
    DEBUG = 10
    ALL = 0
    __LOG_LEVELS = [QUIET, ERROR, WARNING, INFO, DEBUG, ALL]

    STR_TO_LEVEL = {
        "quiet": QUIET,
        "error": ERROR,
        "warning": WARNING,
        "info": INFO,
        "debug": DEBUG,
        "all": ALL,
    }

    __level = INFO

    __uuid = ''

    def __init__(self, dont_log_to_stdout = False):
        self.__namespace = ""
        self.__dont_log_to_stdout = dont_log_to_stdout

    def set_namespace(self, namespace):
        self.__namespace = namespace
        return self

    # A numeric level means to log everything at that level and above.
    # String levels are also accepted: see STR_TO_LEVEL.
    @staticmethod
    def set_level(level):
        if isinstance(level, str):
            level = level.lower()
            if level not in Logger.STR_TO_LEVEL:
                raise Exception(f"Invalid log level specified. Must be one of: {list(Logger.STR_TO_LEVEL.keys())}.")
            level = Logger.STR_TO_LEVEL[level]

        if level not in Logger.__LOG_LEVELS:
            raise Exception(f"Invalid log level specified. Must be one of: {Logger.__LOG_LEVELS}.")
        Logger.__level = level

    @staticmethod
    def get_level():
        return Logger.__level

    @staticmethod
    def make_uuid():
        return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(5))

    @staticmethod
    def set_uuid(uuid):
        Logger.__uuid = uuid

    @staticmethod
    def get_uuid():
        return Logger.__uuid

    def debug(self, msg):
        if Logger.__level > Logger.DEBUG:
            return

        msg = self.__format_msg(level = 'debug', msg = msg)
        if self.__dont_log_to_stdout:
            file = sys.stderr
        else:
            file = sys.stdout
        self.__print_msg(msg, file)

    def info(self, msg):
        if Logger.__level > Logger.INFO:
            return

        msg = self.__format_msg(level = 'info', msg = msg)
        if self.__dont_log_to_stdout:
            file = sys.stderr
        else:
            file = sys.stdout
        self.__print_msg(msg, file)

    def warning(self, msg):
        if Logger.__level > Logger.WARNING:
            return

        msg = self.__format_msg(level = 'warning', msg = msg)
        self.__print_msg(msg, sys.stderr)

    def error(self, msg):
        if Logger.__level > Logger.ERROR:
            return

        msg = self.__format_msg(level = 'error', msg = msg)
        self.__print_msg(msg, sys.stderr)

    def __format_msg(self, level, msg):
        return (datetime.datetime.now(pytz.timezone('UTC')).isoformat() +
            " [" + level + "] [" + self.__namespace + "] [" + Logger.__uuid + "] " + msg)

    def __print_msg(self, msg, file):
        # Note: we could omit `flush = True` in our print function. This would result in a lot fewer
        # `write` syscalls, at the expense of having to wait longer for logs to show up. But this makes
        # things harder to reason about. There might be delays in between calling print and the log line
        # actually being written to the file. And with separate log files (stdout vs stderr), each one
        # keeps a separate buffer, so error vs info logs will be out of order in the log file.
        #
        # Furthermore, other binaries we shell out to, like youtube-dl, don't buffer their writes, so
        # the output of those binaries will be out of order relative to our logs. Fwiw, omxplayer
        # flushes with every log when using its `--genlog` param.
        #
        # See docs:
        # https://docs.python.org/3/library/functions.html#print
        #
        # See strace analysis of with and without `flush = True`
        # https://gist.github.com/dasl-/796031c305ac26da76cdc2887d9fa817
        print(msg, file = file, flush = True)
