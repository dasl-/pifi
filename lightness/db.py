import sqlite3
from lightness.logger import Logger
from lightness.directoryutils import DirectoryUtils
from lightness.videorecord import VideoRecord

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

class DB:

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
    #   * is `is_current` necessary when we have `status`? One or the other.
    #   * when we play a new video, make sure we set old vidos status / is_current fields to not playing
    #   * remove `signal`, replace with `is_skipped` and `is_deleted`
    def construct(self):
        self.__cursor.execute("DROP TABLE IF EXISTS videos")
        self.__cursor.execute("""
            CREATE TABLE videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                create_date DATETIME  DEFAULT CURRENT_TIMESTAMP,
                is_current BOOLEAN DEFAULT 0,
                url TEXT,
                thumbnail TEXT,
                title TEXT,
                color_mode VARCHAR(20),
                status VARCHAR(255),
                signal VARCHAR(255)
            )"""
        )

    def enqueue(self, url, color_mode, thumbnail, title):
        self.__cursor.execute("INSERT INTO videos (url, color_mode, thumbnail, title, status) VALUES(?, ?, ?, ?, ?)",
                          [url, color_mode, thumbnail, title, VideoRecord.STATUS_QUEUED])

    def skip(self):
        self.__cursor.execute("UPDATE videos set signal = ? WHERE is_current", [VideoRecord.SIGNAL_KILL])

    def clear(self):
        self.__cursor.execute("UPDATE videos set status = ? WHERE status = ?", [VideoRecord.STATUS_SKIP, VideoRecord.STATUS_QUEUED])
        self.skip()

    def get_current_video(self):
        self.__cursor.execute("SELECT * FROM videos WHERE is_current LIMIT 1")
        return self.__cursor.fetchone()

    def get_next_video(self):
        self.__cursor.execute(
            "SELECT * FROM videos WHERE NOT(is_current) and status=? order by id asc LIMIT 1",
            [VideoRecord.STATUS_QUEUED]
        )
        return self.__cursor.fetchone()

    def get_queue(self):
        self.__cursor.execute("SELECT * FROM videos WHERE is_current OR status=? order by id asc", [VideoRecord.STATUS_QUEUED])
        return self.__cursor.fetchall()

    def set_current_video(self, video_id):
        self.__cursor.execute(
            "UPDATE videos set is_current=1, status=? WHERE id=?",
            [VideoRecord.STATUS_LOADING, str(video_id)]
        )

    def end_video(self, video_id):
        self.__cursor.execute("UPDATE videos set status=?, is_current=0 WHERE id=?", [VideoRecord.STATUS_DONE, str(video_id)])
