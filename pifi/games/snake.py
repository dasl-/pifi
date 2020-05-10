import numpy as np
import random
import time
import math
import hashlib
import pprint
import sqlite3
import os
import collections
from pifi.logger import Logger
from pifi.playlist import Playlist
from pifi.videoplayer import VideoPlayer
from pifi.settings.gameoflifesettings import GameOfLifeSettings
from pifi.datastructure.limitedsizedict import LimitedSizeDict
from pifi.games.gamecolorhelper import GameColorHelper
from pifi.directoryutils import DirectoryUtils

class Snake:

    UP = 1
    DOWN = 2
    LEFT = 3
    RIGHT = 4

    GAME_TITLE = "snake"

    DB_PATH = DirectoryUtils().root_dir + "/snake.db"

    __SNAKE_STARTING_LENGTH = 4

    __SNAKE_COLOR_CHANGE_FREQ = 0.05

    __APPLE_COLOR_CHANGE_FREQ = 0.2

    # SnakeSettings
    __settings = None

    __game_color_helper = None

    __num_ticks = None

    __game_color_mode = None

    # doubly linked list representing all the coordinate pairs in the snake
    __snake = None

    # set datastructure representing all the coordinate pairs in the snake
    __snake_set = None

    __direction = None

    __apple = None

    __pp = None

    __db_cursor = None

    __playlist = None

    __playlist_video_id = None

    def __init__(self, settings):
        self.__logger = Logger().set_namespace(self.__class__.__name__)
        self.__settings = settings
        self.__game_color_helper = GameColorHelper()
        self.__video_player = VideoPlayer(self.__settings)
        self.__logger.info("Doing init with SnakeSettings: {}".format(vars(self.__settings)))
        self.__pp = pprint.PrettyPrinter(indent=4)
        self.__playlist = Playlist()

        db_conn = sqlite3.connect(self.DB_PATH, isolation_level = None)
        self.__db_cursor = db_conn.cursor()

    def newGame(self, playlist_video_id = None):
        self.__reset()
        self.__show_board()
        self.__playlist_video_id = playlist_video_id

        while True:
            time.sleep(self.__settings.tick_sleep)
            """
            CREATE TABLE snake_moves(move INTEGER, move_id INTEGER PRIMARY KEY AUTOINCREMENT, is_deleted INTEGER default 0);
            CREATE TABLE sqlite_sequence(name,seq);
            CREATE INDEX is_deleted_move_id_idx ON snake_moves (is_deleted, move_id);
            """
            self.__db_cursor.execute("SELECT move, move_id FROM snake_moves WHERE is_deleted = 0 ORDER BY move_id ASC LIMIT 1")
            move = self.__db_cursor.fetchone()
            if move is not None:
                self.__db_cursor.execute("UPDATE snake_moves SET is_deleted = 1 WHERE move_id = " + str(move[1]))
                new_direction = move[0]
                if (
                    (self.__direction == self.UP or self.__direction == self.DOWN) and
                    (new_direction == self.UP or new_direction == self.DOWN)
                ):
                    pass
                elif (
                    (self.__direction == self.LEFT or self.__direction == self.RIGHT) and
                    (new_direction == self.LEFT or new_direction == self.RIGHT)
                ):
                    pass
                else:
                    self.__direction = new_direction
            self.__tick()
            if self.__is_game_over() or self.__maybe_skip_game():
                self.__clear_board()
                break

    def __tick(self):
        self.__num_ticks += 1
        old_head_y, old_head_x = self.__snake[0]

        if self.__direction == self.UP:
            new_head = ((old_head_y - 1) % self.__settings.display_height, old_head_x)
        elif self.__direction == self.DOWN:
            new_head = ((old_head_y + 1) % self.__settings.display_height, old_head_x)
        elif self.__direction == self.LEFT:
            new_head = (old_head_y, (old_head_x - 1) % self.__settings.display_width)
        elif self.__direction == self.RIGHT:
            new_head = (old_head_y, (old_head_x + 1) % self.__settings.display_width)

        if new_head == self.__apple:
            self.__place_apple()
        else:
            old_tail = self.__snake[-1]
            del self.__snake[-1]
            self.__snake_set.remove(old_tail)

        self.__snake.insert(0, new_head)
        self.__snake_set.add(new_head)

        self.__show_board()

    def __place_apple(self):
        # TODO: make better
        while True:
            x = random.randint(0, self.__settings.display_width - 1)
            y = random.randint(0, self.__settings.display_height - 1)
            if (y, x) not in self.__snake_set:
                break
        self.__apple = (y, x)

    def __is_game_over(self):
        return len(self.__snake_set) < len(self.__snake)

    def __show_board(self):
        frame = np.zeros([self.__settings.display_height, self.__settings.display_width, 3], np.uint8)
        snake_rgb = self.__game_color_helper.get_rgb(self.__game_color_mode, self.__SNAKE_COLOR_CHANGE_FREQ, self.__num_ticks)
        apple_rgb = self.__game_color_helper.get_rgb(GameColorHelper.GAME_COLOR_MODE_RAINBOW, self.__APPLE_COLOR_CHANGE_FREQ, self.__num_ticks)

        for (y, x) in self.__snake:
            frame[y, x] = snake_rgb

        if self.__apple is not None:
            frame[self.__apple[0], self.__apple[1]] = apple_rgb

        self.__video_player.play_frame(frame)

    def __reset(self):
        self.__direction = self.RIGHT
        self.__num_ticks = 0
        self.__game_color_helper.reset()
        self.__game_color_mode = self.__game_color_helper.determine_game_color_mode(self.__settings)
        height_midpoint = int(round(self.__settings.display_height / 2, 1))
        width_midpoint = int(round(self.__settings.display_width / 2, 1))
        self.__reset_datastructures()

        for x in range(self.__SNAKE_STARTING_LENGTH):
            coordinate = (height_midpoint, width_midpoint - x)
            self.__snake.append(coordinate)
            self.__snake_set.add(coordinate)

        self.__place_apple()
        self.__db_cursor.execute("DELETE FROM snake_moves")

    def __reset_datastructures(self):
        self.__snake = collections.deque()
        self.__apple = None
        self.__snake_set = set()

    def __clear_board(self):
        self.__reset_datastructures()
        self.__show_board()

    def __maybe_skip_game(self):
        if not self.__settings.should_check_playlist:
            return False

        if self.__playlist.should_skip_video_id(self.__playlist_video_id):
            return True
        return False;
