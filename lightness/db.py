import sqlite3
from lightness.process import Process
from lightness.logger import Logger
from lightness.directoryutils import DirectoryUtils

class DB:

    __conn = None
    __cursor = None
    __logger = None

    def __init__(self):
        # `isolation_level = None` specifies autocommit mode
        self.__conn = sqlite3.connect(DirectoryUtils().root_dir + '/lightness.db', isolation_level = None)
        self.__conn.row_factory = sqlite3.Row
        self.__cursor = self.__conn.cursor()
        self.__logger = Logger().set_namespace(self.__class__.__name__)

    # TODO:
    #   * indices
    #   * is `is_current` necessary when we have `status`? One or the other.
    #   * when we play a new video, make sure we set old vidos status / is_current fields to not playing
    #   * change `is_color` to `color_mode`
    #   * remove `pid`
    #   * remove `signal`, replace with `is_skipped` and `is_deleted`
    def construct(self):
        self.__cursor.execute("DROP TABLE IF EXISTS videos")
        self.__cursor.execute("""CREATE TABLE videos (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        create_date DATETIME  DEFAULT CURRENT_TIMESTAMP,
                        pid INTEGER,
                        is_current BOOLEAN DEFAULT 0,
                        url TEXT,
                        thumbnail TEXT,
                        title TEXT,
                        is_color BOOLEAN,
                        status VARCHAR(255),
                        signal VARCHAR(255)
                      )""")

    def enqueue(self, url, is_color, thumbnail, title):
        self.__cursor.execute("INSERT INTO videos (url, is_color, thumbnail, title, status) VALUES(?, ?, ?, ?, ?)",
                          [url, (('1') if is_color else '0'), thumbnail, title, Process.STATUS_QUEUED])

    def skip(self):
        self.__cursor.execute("UPDATE videos set signal = ? WHERE is_current", [Process.SIGNAL_KILL])

    def clear(self):
        self.__cursor.execute("UPDATE videos set status = ? WHERE status = ?", [Process.STATUS_SKIP, Process.STATUS_QUEUED])
        self.skip()

    def getVideos(self):
        self.__cursor.execute("SELECT * FROM videos")
        return self.__cursor.fetchall()

    def getCurrentVideo(self):
        self.__cursor.execute("SELECT * FROM videos WHERE is_current LIMIT 1")
        return self.__cursor.fetchone()

    def getNextVideo(self):
        self.__cursor.execute(
            "SELECT * FROM videos WHERE NOT(is_current) and status=? order by id asc LIMIT 1",
            [Process.STATUS_QUEUED]
        )
        return self.__cursor.fetchone()

    def getQueue(self):
        self.__cursor.execute("SELECT * FROM videos WHERE is_current OR status=? order by id asc", [Process.STATUS_QUEUED])
        return self.__cursor.fetchall()

    def setCurrentVideo(self, video_id, pid):
        self.__cursor.execute(
            "UPDATE videos set is_current=1, pid=?, status=? WHERE id=?",
            [str(pid), Process.STATUS_LOADING, str(video_id)]
        )

    def setVideoStatus(self, video_id, status):
        self.__cursor.execute("UPDATE videos set status=? WHERE id=?", [status, str(video_id)])

    def endVideo(self, video_id):
        self.__cursor.execute("UPDATE videos set status=?, is_current=0 WHERE id=?", [Process.STATUS_DONE, str(video_id)])

    def setVideoSignal(self, video_id, signal):
        self.__cursor.execute("UPDATE videos set signal=? WHERE id=?", [signal, str(video_id)])
