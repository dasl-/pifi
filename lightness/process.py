import os
import sys
import ast
import signal
from lightness.directoryutils import DirectoryUtils

class Process:

    __PROCESS_FILE = 'process'

    __mode = None
    __file = None
    __write_contents = {}

    STATUS_QUEUED = 'QUEUED'
    STATUS_LOADING = 'LOADING'
    STATUS_PLAYING = 'PLAYING'
    STATUS_SKIP = 'SKIP'
    STATUS_DONE = 'DONE'

    SIGNAL_KILL = 'KILL'

    MODE_READ = 'r'
    MODE_WRITE = 'w+'

    def __init__(self, mode=MODE_READ):
        self.__DATA_DIRECTORY = DirectoryUtils().root_dir + '/data'
        self.__mode = mode

        if (mode == self.MODE_WRITE):
            self.__create_file()

    @staticmethod
    def clear_process():
        process = Process()
        old_pid = process.get_pid()
        if (old_pid != None):
            try:
                print("KILL PID " + str(old_pid))
                os.kill(old_pid, signal.SIGTERM)
            except OSError:
                print("invalid process")

        process = Process(Process.MODE_WRITE)

    def store_value(self, key, value):
        if (self.__mode == self.MODE_READ):
            raise ValueError('Unable to store value in MODE_READ')

        self.__write_contents[key] = value
        self.__write_contents_to_file()

    def get_value(self, key):
        self.__open_file()
        data = self.__file.read()
        parsed_data = ast.literal_eval(data)
        self.__file.close()

        if key in parsed_data:
            return parsed_data[key]

        return None

    def set_pid(self):
        self.store_value("pid", os.getpid())

    def get_pid(self):
        return self.get_value("pid")

    def set_status(self, value):
        self.store_value("status", value)

    def get_status(self):
        return self.get_value("status")

    def __write_contents_to_file(self):
        self.__open_file()
        self.__file.write(str(self.__write_contents))
        self.__file.close()

    def __create_file(self):
        self.store_value('pid', os.getpid())
        open(self.__get_file_path(), self.__mode).close()
        self.__write_contents_to_file()

    def __open_file(self):
        self.__file = open(self.__get_file_path(), self.__mode)

    def __get_file_path(self):
        return self.__DATA_DIRECTORY+ "/" + self.__PROCESS_FILE
