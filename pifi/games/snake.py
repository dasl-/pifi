import numpy as np
import random
import time
import math
import hashlib
import pprint
import sqlite3
import os
from pifi.logger import Logger
from pifi.videoplayer import VideoPlayer
from pifi.settings.gameoflifesettings import GameOfLifeSettings
from pifi.datastructure.limitedsizedict import LimitedSizeDict
from pifi.games.gamecolorhelper import GameColorHelper
from pifi.directoryutils import DirectoryUtils

class Snake:

    LOCK_FILE = '/tmp/snake.file'

    UP = 1
    DOWN = 2
    LEFT = 3
    RIGHT = 4

    DB_PATH = DirectoryUtils().root_dir + "/snake.db"

    __SNAKE_STARTING_LENGTH = 4

    __COLOR_CHANGE_FREQ = 0.05

    # SnakeSettings
    __settings = None

    __game_color_helper = None

    __board = None

    __num_ticks = None

    __game_color_mode = None

    __snake = None

    __direction = None

    __apple = None

    __pp = None

    __db_cursor = None

    def __init__(self, settings):
        self.__logger = Logger().set_namespace(self.__class__.__name__)
        self.__settings = settings
        self.__game_color_helper = GameColorHelper()
        self.__video_player = VideoPlayer(self.__settings)
        self.__logger.info("Doing init with GameOfLifeSettings: {}".format(vars(self.__settings)))
        self.__pp = pprint.PrettyPrinter(indent=4)

        db_conn = sqlite3.connect(self.DB_PATH, isolation_level = None)
        self.__db_cursor = db_conn.cursor()

    def newGameRequested(self):
        return os.path.exists(self.LOCK_FILE)

    def newGame(self):
        self.__reset()
        self.__show_board()

        while True:
            time.sleep(self.__settings.tick_sleep)
            self.__db_cursor.execute("SELECT move FROM snake_moves ORDER BY move_id DESC LIMIT 1")
            move = self.__db_cursor.fetchone()
            if move is not None:
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
            if self.__is_game_over():
                break

    def __tick(self):
        self.__num_ticks += 1
        snake_head = self.__snake[0]

        if self.__direction == self.UP:
            new_head = [(snake_head[0] - 1) % self.__settings.display_height, snake_head[1]]
        elif self.__direction == self.DOWN:
            new_head = [(snake_head[0] + 1) % self.__settings.display_height, snake_head[1]]
        elif self.__direction == self.LEFT:
            new_head = [snake_head[0], (snake_head[1] - 1) % self.__settings.display_width]
        elif self.__direction == self.RIGHT:
            new_head = [snake_head[0], (snake_head[1] + 1) % self.__settings.display_width]



        self.__snake.insert(0, new_head)
        if new_head == self.__apple:
            self.__place_apple()
        else:
            del self.__snake[-1]

        self.__show_board()

    def __place_apple(self):
        # TODO: make better
        while True:
            x = random.randint(0, self.__settings.display_width - 1)
            y = random.randint(0, self.__settings.display_height - 1)
            if [y, x] not in self.__snake:
                break
        self.__apple = [y, x]

    def __is_game_over(self):
        snake_head = self.__snake[0]
        for pair in self.__snake[1:]:
            if pair == snake_head:
                self.__snake = []
                self.__apple = None
                self.__show_board()
                os.remove(self.LOCK_FILE)
                return True

        return False

    def __show_board(self):
        self.__snake_to_board()
        frame = self.__board_to_frame()
        self.__video_player.play_frame(frame)

    def __snake_to_board(self):
        self.__board = np.zeros([self.__settings.display_height, self.__settings.display_width], np.uint8)
        for pair in self.__snake:
            self.__board[pair[0], pair[1]] = 1

        if self.__apple is not None:
            self.__board[self.__apple[0], self.__apple[1]] = 1

    def __board_to_frame(self):
        frame = np.zeros([self.__settings.display_height, self.__settings.display_width, 3], np.uint8)
        rgb = self.__game_color_helper.get_rgb(self.__game_color_mode, self.__COLOR_CHANGE_FREQ, self.__num_ticks)
        on = 1

        # todo: just iterate thru the snake bc its faster. get rid of the board instance variable??
        for x in range(self.__settings.display_width):
            for y in range(self.__settings.display_height):
                if self.__board[y,x] == on:
                    frame[y, x] = rgb

        return frame

    def __reset(self):
        self.__direction = self.RIGHT
        self.__num_ticks = 0
        self.__game_color_helper.reset()
        self.__game_color_mode = self.__game_color_helper.determine_game_color_mode(self.__settings)
        self.__board = np.zeros([self.__settings.display_height, self.__settings.display_width], np.uint8)
        height_midpoint = int(round(self.__settings.display_height / 2, 1))
        width_midpoint = int(round(self.__settings.display_width / 2, 1))
        self.__snake = []

        for x in range(self.__SNAKE_STARTING_LENGTH):
            self.__snake.append([height_midpoint, width_midpoint - x])

        self.__place_apple()
        self.__db_cursor.execute("DELETE FROM snake_moves")
