import sqlite3
from pifi.logger import Logger
import pifi.database

class Scores:

    __HIGHSCORE_CUTOFF = 10

    __cursor = None
    __logger = None

    def __init__(self):
        self.__cursor = pifi.database.Database().get_cursor()
        self.__logger = Logger().set_namespace(self.__class__.__name__)

    # TODO: indices
    def construct(self):
        self.__cursor.execute("DROP TABLE IF EXISTS scores")
        self.__cursor.execute("""
            CREATE TABLE scores (
                score_id INTEGER PRIMARY KEY,
                score INTEGER,
                initials VARCHAR(100) DEFAULT '',
                create_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                game_type VARCHAR(100)
            )"""
        )

    def insert_score(self, score, game_type):
        self.__cursor.execute(
            "INSERT INTO scores " +
                "(score, initials, game_type) " +
                "VALUES(?, ?, ?)",
            [score, "AAA", game_type]
        )
        return self.__cursor.lastrowid

    def is_high_score(self, score, game_type):
        self.__cursor.execute(
            "SELECT COUNT(*) as count FROM scores WHERE score > ? AND game_type = ?", [score, game_type]
        )
        if self.__cursor.fetchone()['count'] < self.__HIGHSCORE_CUTOFF:
            return True
        else:
            return False

    # Recent high scores win out over old high scores when there are ties.
    def get_high_scores(self, game_type):
        self.__cursor.execute(
            "SELECT * FROM scores WHERE game_type = ? ORDER BY score DESC, score_id DESC LIMIT ?",
            [game_type, self.__HIGHSCORE_CUTOFF]
        )
        return self.__cursor.fetchall()

    def update_initials(self, score_id, initials):
        self.__cursor.execute(
            "UPDATE scores set initials = ? WHERE score_id = ?",
            [initials, score_id]
        )
        return self.__cursor.rowcount >= 1

