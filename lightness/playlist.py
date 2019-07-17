import sqlite3
from lightness.logger import Logger
from lightness.directoryutils import DirectoryUtils

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

class Playlist:

    STATUS_QUEUED = 'QUEUED'
    STATUS_DELETED = 'DELETED' # No longer in the queue
    STATUS_PLAYING = 'PLAYING'
    STATUS_DONE = 'DONE'

    __conn = None
    __cursor = None
    __logger = None

    def __init__(self):
        # `isolation_level = None` specifies autocommit mode
        self.__conn = sqlite3.connect(DirectoryUtils().root_dir + '/lightness.db', isolation_level = None)
        self.__conn.row_factory = dict_factory
        self.__cursor = self.__conn.cursor()
        self.__logger = Logger().set_namespace(self.__class__.__name__)

    # TODO:
    #   * indices
    #   * when we play a new video, make sure we set old vidos status / is_current fields to not playing
    #   * atomic skip
    #   * atomic get and play video
    def construct(self):
        self.__cursor.execute("DROP TABLE IF EXISTS playlist_videos")
        self.__cursor.execute("""
            CREATE TABLE playlist_videos (
                playlist_video_id INTEGER PRIMARY KEY AUTOINCREMENT,
                create_date DATETIME  DEFAULT CURRENT_TIMESTAMP,
                url TEXT,
                thumbnail TEXT,
                title TEXT,
                color_mode VARCHAR(20),
                status VARCHAR(20),
                is_skip_requested INTEGER DEFAULT 0
            )"""
        )

    def enqueue(self, url, color_mode, thumbnail, title):
        self.__cursor.execute("INSERT INTO playlist_videos (url, color_mode, thumbnail, title, status) VALUES(?, ?, ?, ?, ?)",
                          [url, color_mode, thumbnail, title, self.STATUS_QUEUED])

    def skip(self):
        self.__cursor.execute("UPDATE playlist_videos set is_skip_requested = 1 WHERE status = ?", [self.STATUS_PLAYING])

    def clear(self):
        self.__cursor.execute("UPDATE playlist_videos set status = ? WHERE status = ?",
            [self.STATUS_DELETED, self.STATUS_QUEUED]
        )
        self.skip()

    def get_current_video(self):
        self.__cursor.execute("SELECT * FROM playlist_videos WHERE status = ? LIMIT 1", [self.STATUS_PLAYING])
        return self.__cursor.fetchone()

    def get_next_video(self):
        self.__cursor.execute(
            "SELECT * FROM playlist_videos WHERE status= ? order by playlist_video_id asc LIMIT 1",
            [self.STATUS_QUEUED]
        )
        return self.__cursor.fetchone()

    def get_queue(self):
        self.__cursor.execute(
            "SELECT * FROM playlist_videos WHERE status IN (?, ?) order by playlist_video_id asc",
            [self.STATUS_PLAYING, self.STATUS_QUEUED]
        )
        return self.__cursor.fetchall()

    def set_current_video(self, playlist_video_id):
        self.__cursor.execute(
            "UPDATE playlist_videos set status=? WHERE playlist_video_id=?",
            [self.STATUS_PLAYING, str(playlist_video_id)]
        )

    def end_video(self, playlist_video_id):
        self.__cursor.execute(
            "UPDATE playlist_videos set status=? WHERE playlist_video_id=?",
            [self.STATUS_DONE, str(playlist_video_id)]
        )
