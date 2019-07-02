import sqlite3
from process import Process

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

class DB:
    __conn = None

    def __init__(self):
        self.__conn = sqlite3.connect('/home/pi/lightness/lightness.db')
        self.__conn.row_factory = dict_factory
        # self.__construct()

    def enqueue(self, url, is_color):
        self.__execute("""INSERT INTO videos (url, is_color, status)
                          VALUES(
                            '""" + url + """',
                            """ + (('1') if is_color else '0') + """,
                            '""" + Process.STATUS_QUEUED + """'
                          )""")

    def getVideos(self):
        return self.__fetch("SELECT * FROM videos")

    def getCurrentVideo(self):
        return self.__fetchSingle("SELECT * FROM videos WHERE is_current")

    def getNextVideo(self):
        return self.__fetchSingle("SELECT * FROM videos WHERE NOT(is_current) and status='" + Process.STATUS_QUEUED + "' order by id asc")

    def setCurrentVideo(self, video_id, pid):
        self.__execute("""UPDATE videos set
                            is_current=1,
                            pid='""" + str(pid) + """',
                            status='""" + Process.STATUS_LOADING + """'
                            WHERE id=""" + str(video_id))

    def setVideoStatus(self, video_id, status):
        self.__execute("UPDATE videos set status='" + status + "' WHERE id=" + str(video_id))

    def endVideo(self, video_id):
        self.__execute("UPDATE videos set status='" + Process.STATUS_DONE + "', is_current=0 WHERE id=" + str(video_id))

    def setVideoSignal(self, video_id, signal):
        self.__execute("UPDATE videos set signal='" + signal + "' WHERE id=" + str(video_id))

    def __execute(self, sql):
        c = self.__conn.cursor()
        c.execute(sql)
        self.__conn.commit()

    def __fetch(self, sql):
        c = self.__conn.cursor()
        c.execute(sql)
        return c.fetchall()

    def __fetchSingle(self, sql):
        rows = self.__fetch(sql)
        if (len(rows) > 0):
            return rows[0]

        return None

    def __construct(self):
        self.__execute("DROP TABLE IF EXISTS videos")
        self.__execute(""" CREATE TABLE videos (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        create_date DATETIME  DEFAULT CURRENT_TIMESTAMP,
                        pid INTEGER,
                        is_current BOOLEAN DEFAULT 0,
                        url TEXT,
                        is_color BOOLEAN,
                        status VARCHAR(255),
                        signal VARCHAR(255)
                      )""")
