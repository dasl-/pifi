import sqlite3

from pifi.directoryutils import DirectoryUtils
from pifi.logger import Logger

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

class Database:

    __DB_PATH = DirectoryUtils().root_dir + '/pifi.db'

    __conn = None
    __cursor = None
    __logger = None

    def __init__(self):
        # `isolation_level = None` specifies autocommit mode
        self.__conn = sqlite3.connect(self.__DB_PATH, isolation_level = None)
        self.__conn.row_factory = dict_factory
        self.__cursor = self.__conn.cursor()
        self.__logger = Logger().set_namespace(self.__class__.__name__)

    def get_cursor(self):
        return self.__cursor;