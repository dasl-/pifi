import sqlite3
import threading
import time

from pifi.directoryutils import DirectoryUtils
from pifi.logger import Logger
import pifi.playlist
import pifi.games.scores
import pifi.settings.settingsdb

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


thread_local = threading.local()

class Database:

    __DB_PATH = DirectoryUtils().root_dir + '/pifi.db'

    # Zero indexed schema_version (first version is v0).
    __SCHEMA_VERSION = 2

    # instance vars
    __logger = None

    def __init__(self):
        self.__logger = Logger().set_namespace(self.__class__.__name__)

    @staticmethod
    def database_date_to_unix_time(database_date):
        return time.mktime(time.strptime(database_date, '%Y-%m-%d  %H:%M:%S'))

    # returns False on error
    @staticmethod
    def video_duration_to_unix_time(video_duration):
        # video durations are of the form HH:MM:SS, may have leading zeroes, etc
        parts = video_duration.split(':')
        num_parts = len(parts)
        if num_parts == 1: # just seconds
            try:
                return int(parts[0])
            except Exception:
                return False
        if num_parts == 2: # minutes and seconds
            try:
                return int(parts[0]) * 60 + int(parts[1])
            except Exception:
                return False
        if num_parts == 3: # hours, minutes, and seconds
            try:
                return int(parts[0]) * 60 * 60 + int(parts[1]) * 60 + int(parts[2])
            except Exception:
                return False
        return False

    # Schema change how-to:
    # 1) Update all DB classes with 'virgin' sql (i.e. Playlist().construct(), Scores.construct())
    # 2) Increment self.__SCHEMA_VERSION
    # 3) Implement self.__update_schema_to_vN for the incremented SCHEMA_VERSION, call this method in
    #   the below for loop.
    # 4) Run ./install/install.sh
    def construct(self):
        self.get_cursor().execute("BEGIN TRANSACTION")
        try:
            self.get_cursor().execute("SELECT version FROM pifi_schema_version")
            current_schema_version = int(self.get_cursor().fetchone()['version'])
        except Exception as e:
            current_schema_version = -1

        self.__logger.info("current_schema_version: {}".format(current_schema_version))

        if current_schema_version == -1:
            # construct from scratch
            self.__logger.info("Constructing database schema from scratch...")
            self.__construct_pifi_schema_version()
            pifi.playlist.Playlist().construct()
            pifi.games.scores.Scores().construct()
            pifi.settings.settingsdb.SettingsDb().construct()
        elif current_schema_version < self.__SCHEMA_VERSION:
            self.__logger.info(
                "Database schema is outdated. Updating from version {} to {}."
                    .format(current_schema_version, self.__SCHEMA_VERSION)
            )
            for i in range(current_schema_version + 1, self.__SCHEMA_VERSION + 1):
                self.__logger.info(
                    "Running database schema change to update from version {} to {}.".format(i - 1, i)
                )
                if i == 1:
                    self.__update_schema_to_v1()
                elif i == 2:
                    self.__update_schema_to_v2()
                else:
                    msg = "No update schema method defined for version: {}.".format(i)
                    self.__logger.error(msg)
                    raise Exception(msg)
                self.get_cursor().execute("UPDATE pifi_schema_version set version = ?", [i])
        elif current_schema_version == self.__SCHEMA_VERSION:
            self.__logger.info("Database schema is already up to date!")
            return
        else:
            msg = ("Database schema is newer than should be possible. This should never happen. " +
                "current_schema_version: {}. Tried to update to version: {}."
                .format(current_schema_version, self.__SCHEMA_VERSION))
            self.__logger.error(msg)
            raise Exception(msg)

        self.get_cursor().execute("COMMIT")
        self.__logger.info("Database schema constructed successfully.")

    def get_cursor(self):
        cursor = getattr(thread_local, 'database_cursor', None)
        if cursor is None:
            # `isolation_level = None` specifies autocommit mode.
            conn = sqlite3.connect(self.__DB_PATH, isolation_level = None)
            conn.row_factory = dict_factory
            cursor = conn.cursor()
            thread_local.database_cursor = cursor
        return cursor

    def __construct_pifi_schema_version(self):
        self.get_cursor().execute("DROP TABLE IF EXISTS pifi_schema_version")
        self.get_cursor().execute("CREATE TABLE pifi_schema_version (version INTEGER)")
        self.get_cursor().execute(
            "INSERT INTO pifi_schema_version (version) VALUES(?)",
            [self.__SCHEMA_VERSION]
        )

    # Updates schema from v0 to v1.
    def __update_schema_to_v1(self):
        pifi.settings.settingsdb.SettingsDb().construct()

    # Updates schema from v1 to v2.
    def __update_schema_to_v2(self):
        # Adding the update_date column. Trying to set the column's default value to CURRENT_TIMESTAMP results in:
        #   sqlite3.OperationalError: Cannot add a column with non-constant default
        # Thus, just blow the table away and re-create it.
        pifi.settings.settingsdb.SettingsDb().construct()
