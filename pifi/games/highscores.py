import sqlite3
from pifi.logger import Logger
import pifi.database

class HighScores:

    __HIGHSCORE_CUTOFF = 25

    __cursor = None
    __logger = None

    def __init__(self):
        self.__cursor = pifi.database.Database().get_cursor()
        self.__logger = Logger().set_namespace(self.__class__.__name__)

    def construct(self):
        self.__cursor.execute("DROP TABLE IF EXISTS high_scores")
        self.__cursor.execute("""
            CREATE TABLE high_scores (
                score_id INTEGER PRIMARY KEY,
                score INTEGER,
                initials VARCHAR(100) DEFAULT '',
                create_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                game_type VARCHAR(100)
            )"""
        )

    def insert_score(self, score, game_type):
        self.__cursor.execute(
            "INSERT INTO high_scores " +
                "(score, game_type) " +
                "VALUES(?, ?)",
            [score, game_type]
        )
        return self.__cursor.lastrowid

    # Note: should call this method on a score that has not yet been inserted into the DB, i.e.:
    #
    #   is_high_score = highscores.is_high_score(score, game_type)
    #   high_score_id = highscores.insert_score(score, game_type)
    #
    # Calling this method after inserting the score may result in miscounting.
    def is_high_score(self, score, game_type):
        self.__cursor.execute(
            "SELECT COUNT(*) as count FROM high_scores WHERE score > ? AND game_type = ?", [score, game_type]
        )
        if self.__cursor.fetchone()['count'] < self.__HIGHSCORE_CUTOFF:
            return True
        else:
            return False

    def get_high_scores(self, game_type):
        self.__cursor.execute(
            "SELECT * FROM high_scores WHERE game_type = ? ORDER BY score DESC, score_id DESC LIMIT ?",
            [game_type, self.__HIGHSCORE_CUTOFF]
        )
        return self.__cursor.fetchall()
