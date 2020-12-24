import sqlite3
from pifi.logger import Logger
import pifi.database

class Playlist:

    STATUS_QUEUED = 'STATUS_QUEUED'
    STATUS_DELETED = 'STATUS_DELETED' # No longer in the queue
    STATUS_PLAYING = 'STATUS_PLAYING'
    STATUS_DONE = 'STATUS_DONE'

    # A sub-status of STATUS_PLAYING
    STATUS2_WAITING_FOR_PLAYERS = 'STATUS2_WAITING_FOR_PLAYERS'
    STATUS2_PLAYING = 'STATUS2_PLAYING'

    """
    The Playlist DB holds a queue of playlist items to play. These items can be either videos or games, such as snake.
    When a game is requested, we insert a new row in the playlist DB. This gets an autoincremented playlist_video_id,
    and playlist_video_id is what we use to order the playlist queue. Thus, if we didn't do anything special, the
    game would only start when the current queue of playlist items had been exhausted.

    The behavior we actually want though is to skip the current video (if there is one) and immediately start playing
    the requested game. Thus, we actually order the queue by a combination of `type` and `playlist_video_id`. Rows in the
    DB with a `game` type (i.e. snake) get precedence in the queue.
    """
    TYPE_VIDEO = 'TYPE_VIDEO'
    TYPE_GAME = 'TYPE_GAME'

    __cursor = None
    __logger = None

    def __init__(self):
        self.__cursor = pifi.database.Database().get_cursor()
        self.__logger = Logger().set_namespace(self.__class__.__name__)

    def construct(self):
        self.__cursor.execute("DROP TABLE IF EXISTS playlist_videos")
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

        self.__cursor.execute("DROP INDEX IF EXISTS status_idx")
        self.__cursor.execute("CREATE INDEX status_type_idx ON playlist_videos (status, type ASC, playlist_video_id ASC)")

    def enqueue(self, url, color_mode, thumbnail, title, duration, video_type, settings):
        self.__cursor.execute(
            "INSERT INTO playlist_videos " +
                "(type, url, color_mode, thumbnail, title, duration, status, settings) " +
                "VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
            [video_type, url, color_mode, thumbnail, title, duration, self.STATUS_QUEUED, settings]
        )
        return self.__cursor.lastrowid

    # Passing the id of the video to skip ensures our skips are "atomic". That is, we can ensure we skip the
    # video that the user intended to skip.
    def skip(self, playlist_video_id):
        self.__cursor.execute(
            "UPDATE playlist_videos set is_skip_requested = 1 WHERE status = ? AND playlist_video_id = ?",
            [self.STATUS_PLAYING, playlist_video_id]
        )
        return self.__cursor.rowcount >= 1

    def remove(self, playlist_video_id):
        self.__cursor.execute(
            "UPDATE playlist_videos set status = ? WHERE playlist_video_id = ? AND status = ?",
            [self.STATUS_DELETED, playlist_video_id, self.STATUS_QUEUED]
        )
        return self.__cursor.rowcount >= 1

    def clear(self):
        self.__cursor.execute("UPDATE playlist_videos set status = ? WHERE status = ?",
            [self.STATUS_DELETED, self.STATUS_QUEUED]
        )
        self.__cursor.execute(
            "UPDATE playlist_videos set is_skip_requested = 1 WHERE status = ?",
            [self.STATUS_PLAYING]
        )

    def get_current_video(self):
        self.__cursor.execute("SELECT * FROM playlist_videos WHERE status = ? LIMIT 1", [self.STATUS_PLAYING])
        return self.__cursor.fetchone()

    def get_next_playlist_item(self):
        self.__cursor.execute(
            "SELECT * FROM playlist_videos WHERE status = ? order by type asc, playlist_video_id asc LIMIT 1",
            [self.STATUS_QUEUED]
        )
        return self.__cursor.fetchone()

    def get_queue(self):
        self.__cursor.execute(
            "SELECT * FROM playlist_videos WHERE status IN (?, ?) order by type asc, playlist_video_id asc",
            [self.STATUS_PLAYING, self.STATUS_QUEUED]
        )
        return self.__cursor.fetchall()

    # Atomically set the requested video to "playing" status. This may fail if in a scenario like:
    #   1) Next video in the queue is retrieved
    #   2) Someone deletes the video from the queue
    #   3) We attempt to set the video to "playing" status
    def set_current_video(self, playlist_video_id, status2 = None):
        if status2:
            # HACK: using color_mode to store the status2 sub-status until we figure out if this is the best schema design
            self.__cursor.execute(
                "UPDATE playlist_videos set status = ?, color_mode = ? WHERE status = ? AND playlist_video_id = ?",
                [self.STATUS_PLAYING, status2, self.STATUS_QUEUED, playlist_video_id]
            )
        else:
            self.__cursor.execute(
                "UPDATE playlist_videos set status = ? WHERE status = ? AND playlist_video_id = ?",
                [self.STATUS_PLAYING, self.STATUS_QUEUED, playlist_video_id]
            )
        if self.__cursor.rowcount == 1:
            return True
        return False

    def set_all_players_ready(self, playlist_video_id):
        # HACK: using color_mode to store the status2 sub-status until we figure out if this is the best schema design
        self.__cursor.execute(
            "UPDATE playlist_videos set color_mode = ? WHERE status = ? AND playlist_video_id = ?",
            [self.STATUS2_PLAYING, self.STATUS_PLAYING, playlist_video_id]
        )
        if self.__cursor.rowcount == 1:
            return True
        return False

    def end_video(self, playlist_video_id):
        self.__cursor.execute(
            "UPDATE playlist_videos set status=? WHERE playlist_video_id=?",
            [self.STATUS_DONE, playlist_video_id]
        )

    # Clean up any weird state we may have in the DB as a result of unclean shutdowns, etc:
    # set any existing 'playing' videos to 'done'.
    def clean_up_state(self):
        self.__cursor.execute(
            "UPDATE playlist_videos set status = ? WHERE status = ?",
            [self.STATUS_DONE, self.STATUS_PLAYING]
        )

    def should_skip_video_id(self, playlist_video_id):
        current_video = self.get_current_video()
        if current_video and current_video['playlist_video_id'] != playlist_video_id:
            self.__logger.warning(
                "Database and current process disagree about which playlist item is currently playing. " +
                "Database says playlist_video_id: {}, whereas current process says playlist_video_id: {}."
                    .format(current_video['playlist_video_id'], playlist_video_id)
            )
            return False

        if current_video and current_video["is_skip_requested"]:
            self.__logger.info("Skipping current playlist item as requested.")
            return True

        return False
