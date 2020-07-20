import sqlite3

from pifi.directoryutils import DirectoryUtils
from pifi.logger import Logger
import pifi.playlist
import pifi.games.highscores

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

class Database:

    __DB_PATH = DirectoryUtils().root_dir + '/pifi.db'

    # Zero indexed schema_version (first version is v0).
    __SCHEMA_VERSION = 1

    # static vars
    __static_conn = None
    __static_cursor = None

    # instance vars
    __cursor = None
    __logger = None

    def __init__(self):
        # Ensure we only ever have one database conn because it holds locks.
        # Having multiple database conns could lead to deadlocks.
        if Database.__static_conn == None:
            # `isolation_level = None` specifies autocommit mode
            Database.__static_conn = sqlite3.connect(self.__DB_PATH, isolation_level = None)
            Database.__static_conn.row_factory = dict_factory
            Database.__static_cursor = Database.__static_conn.cursor()

        self.__cursor = Database.__static_cursor
        self.__logger = Logger().set_namespace(self.__class__.__name__)


    # Schema change how-to:
    # 1) Update all DB classes with 'virgin' sql (i.e. Playlist().construct(), HighScores.construct())
    # 2) Increment self.__SCHEMA_VERSION
    # 3) Implement self.__update_schema_to_vN for the incremented SCHEMA_VERSION, call this method in
    #   the below for loop.
    # 4) Run ./install/install.sh
    def construct(self):
        self.__cursor.execute("BEGIN TRANSACTION")
        try:
            self.__cursor.execute("SELECT version FROM pifi_schema_version")
            current_schema_version = int(self.__cursor.fetchone()['version'])
        except Exception as e:
            current_schema_version = -1

        self.__logger.info("current_schema_version: {}".format(current_schema_version))

        if current_schema_version == -1:
            # construct from scratch
            self.__logger.info("Constructing database schema from scratch...")
            self.__construct_pifi_schema_version()
            pifi.playlist.Playlist().construct()
            pifi.games.highscores.HighScores().construct()
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
                else:
                    msg = "No update schema method defined for version: {}.".format(i)
                    self.__logger.error(msg)
                    raise Exception(msg)
                self.__cursor.execute("UPDATE pifi_schema_version set version = ?", [i])
        elif current_schema_version == self.__SCHEMA_VERSION:
            self.__logger.info("Database schema is already up to date!")
            return
        else:
            msg = ("Database schema is newer than should be possible. This should never happen. " +
                "current_schema_version: {}. Tried to update to version: {}."
                .format(current_schema_version, self.__SCHEMA_VERSION))
            self.__logger.error(msg)
            raise Exception(msg)

        self.__cursor.execute("COMMIT")
        self.__logger.info("Database schema constructed successfully.")

    def get_cursor(self):
        return Database.__static_cursor;

    def __construct_pifi_schema_version(self):
        self.__cursor.execute("DROP TABLE IF EXISTS pifi_schema_version")
        self.__cursor.execute("CREATE TABLE pifi_schema_version (version INTEGER)")
        self.__cursor.execute(
            "INSERT INTO pifi_schema_version (version) VALUES(?)",
            [self.__SCHEMA_VERSION]
        )

    # Updates schema from v0 to v1.
    # Changes the PKs from autoincrement to non-autoincrement for slight perf boost: https://www.sqlite.org/autoinc.html
    # (autoincrement is not usually necessary).
    # TODO: hack the next schema change to use v1 -- this wasnt really a compatible schema change anyway bc removing AUTOINCREMENT
    # the sqlite_sequence DB hangs around anyway
    def __update_schema_to_v1(self):
        # change PK for playlist_videos
        self.__cursor.execute("""
            CREATE TEMPORARY TABLE playlist_videos_backup (
                playlist_video_id INTEGER PRIMARY KEY,
                type VARCHAR(20) DEFAULT 'TYPE_VIDEO',
                create_date DATETIME  DEFAULT CURRENT_TIMESTAMP,
                url TEXT,
                thumbnail TEXT,
                title TEXT,
                duration VARCHAR(20),
                color_mode VARCHAR(20),
                status VARCHAR(20),
                is_skip_requested INTEGER DEFAULT 0,
                settings TEXT DEFAULT ''
            )"""
        )
        self.__cursor.execute("INSERT INTO playlist_videos_backup SELECT * FROM playlist_videos")
        self.__cursor.execute("DROP TABLE playlist_videos")
        self.__cursor.execute("""
            CREATE TABLE playlist_videos (
                playlist_video_id INTEGER PRIMARY KEY,
                type VARCHAR(20) DEFAULT 'TYPE_VIDEO',
                create_date DATETIME  DEFAULT CURRENT_TIMESTAMP,
                url TEXT,
                thumbnail TEXT,
                title TEXT,
                duration VARCHAR(20),
                color_mode VARCHAR(20),
                status VARCHAR(20),
                is_skip_requested INTEGER DEFAULT 0,
                settings TEXT DEFAULT ''
            )"""
        )
        self.__cursor.execute("INSERT INTO playlist_videos SELECT * FROM playlist_videos_backup")
        self.__cursor.execute("DROP TABLE playlist_videos_backup")

        # change PK for high_scores
        self.__cursor.execute("""
            CREATE TEMPORARY TABLE high_scores_backup (
                score_id INTEGER PRIMARY KEY,
                score INTEGER,
                initials VARCHAR(100) DEFAULT '',
                create_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                game_type VARCHAR(100)
            )"""
        )
        self.__cursor.execute("INSERT INTO high_scores_backup SELECT * FROM high_scores")
        self.__cursor.execute("DROP TABLE high_scores")
        self.__cursor.execute("""
            CREATE TABLE high_scores (
                score_id INTEGER PRIMARY KEY,
                score INTEGER,
                initials VARCHAR(100) DEFAULT '',
                create_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                game_type VARCHAR(100)
            )"""
        )
        self.__cursor.execute("INSERT INTO high_scores SELECT * FROM high_scores_backup")
        self.__cursor.execute("DROP TABLE high_scores_backup")
