import sqlite3
from lightness.process import Process
from lightness.logger import Logger
from lightness.directoryutils import DirectoryUtils

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

class DB:
    __conn = None
    __logger = None

    def __init__(self):
        self.__conn = sqlite3.connect(DirectoryUtils().root_dir + '/lightness.db', check_same_thread=False)
        self.__conn.row_factory = dict_factory
        self.__logger = Logger().set_namespace(self.__class__.__name__)

    def construct(self):
        self.__construct()

    def enqueue(self, url, is_color, thumbnail, title):
        self.__execute("INSERT INTO videos (url, is_color, thumbnail, title, status) VALUES(?, ?, ?, ?, ?)",
                          [url, (('1') if is_color else '0'), thumbnail, title, Process.STATUS_QUEUED])

    def skip(self):
        self.__execute("UPDATE videos set signal = ? WHERE is_current", [Process.SIGNAL_KILL])

    def clear(self):
        self.__execute("UPDATE videos set status = ? WHERE status = ?", [Process.STATUS_SKIP, Process.STATUS_QUEUED])
        self.skip()

    def getVideos(self):
        return self.__fetch("SELECT * FROM videos")

    def getCurrentVideo(self):
        return self.__fetchSingle("SELECT * FROM videos WHERE is_current")

    def getNextVideo(self):
        return self.__fetchSingle("SELECT * FROM videos WHERE NOT(is_current) and status=? order by id asc", [Process.STATUS_QUEUED])

    def getQueue(self):
        return self.__fetch("SELECT * FROM videos WHERE is_current OR status=? order by id asc", [Process.STATUS_QUEUED])

    def setCurrentVideo(self, video_id, pid):
        self.__execute("UPDATE videos set is_current=1, pid=?, status=? WHERE id=?",
                          [str(pid), Process.STATUS_LOADING, str(video_id)])

    def setVideoStatus(self, video_id, status):
        self.__execute("UPDATE videos set status=? WHERE id=?", [status, str(video_id)])

    def endVideo(self, video_id):
        self.__execute("UPDATE videos set status=?, is_current=0 WHERE id=?", [Process.STATUS_DONE, str(video_id)])

    def setVideoSignal(self, video_id, signal):
        self.__execute("UPDATE videos set signal=? WHERE id=?", [signal, str(video_id)])

    def __execute(self, sql, params=[]):
        c = self.__conn.cursor()
        c.execute(sql, params)
        self.__conn.commit()

    def __fetch(self, sql, params=[]):
        c = self.__conn.cursor()
        c.execute(sql, params)
        return c.fetchall()

    def __fetchSingle(self, sql, params=[]):
        rows = self.__fetch(sql, params)
        if (len(rows) > 0):
            return rows[0]

        return None

    def __construct(self):
        self.__execute("DROP TABLE IF EXISTS videos")
        self.__execute("""CREATE TABLE videos (
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
