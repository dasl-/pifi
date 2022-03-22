import numpy as np
import random
import time
import hashlib
from pifi.logger import Logger
from pifi.videoplayer import VideoPlayer
from pifi.datastructure.limitedsizedict import LimitedSizeDict
from pifi.games.gamecolorhelper import GameColorHelper

class GameOfLife:

    __COLOR_CHANGE_FREQ = 0.05
    __MAX_STATE_REPETITIONS_FOR_GAME_OVER = 10

    # settings: GameOfLifeSettings
    def __init__(self, settings):
        self.__logger = Logger().set_namespace(self.__class__.__name__)
        self.__settings = settings
        self.__video_player = VideoPlayer(self.__settings)
        self.__logger.info("Doing init with GameOfLifeSettings: {}".format(vars(self.__settings)))
        self.__game_color_helper = GameColorHelper()

    def play(self, should_loop = False):
        if should_loop:
            while True:
                self.tick(should_loop = should_loop)
        else:
            while True:
                if not self.tick():
                    break

    # return False when the game is over, True otherwise.
    def tick(self, should_loop = False, force_reset = False):
        if self.__board is None or force_reset:
            # start the game
            self.__reset()
            is_game_in_progress = True
        else:
            self.__tick_internal()
            is_game_in_progress = True

        self.__do_tick_bookkeeping()

        if self.__is_game_over():
            if should_loop:
                self.__reset()
                self.__do_tick_bookkeeping()
                is_game_in_progress = True
            else:
                is_game_in_progress = False

        time.sleep(self.__settings.tick_sleep)

        return is_game_in_progress

    def __do_tick_bookkeeping(self):
        self.__num_ticks += 1
        board_hash = self.__get_board_hash()
        if board_hash in self.__prev_board_state_counts:
            self.__prev_board_state_counts[board_hash] += 1
        else:
            self.__prev_board_state_counts[board_hash] = 1

    def __get_board_hash(self):
        return hashlib.md5(self.__board).hexdigest()

    def __is_game_over(self):
        if self.__prev_board_state_counts[self.__get_board_hash()] > self.__MAX_STATE_REPETITIONS_FOR_GAME_OVER:
            self.__logger.info(("Game over detected. Current board state has repeated at least {} times."
                    .format(self.__MAX_STATE_REPETITIONS_FOR_GAME_OVER)))
            return True
        return False

    def __reset(self):
        self.__logger.info("Starting new game.")
        self.__num_ticks = 0
        self.__game_color_helper.reset()
        self.__game_color_mode = self.__game_color_helper.determine_game_color_mode(self.__settings)
        self.__prev_board_state_counts = LimitedSizeDict(capacity = self.__settings.game_over_detection_lookback)
        self.__seed()

    def __seed(self):
        self.__board = np.zeros([self.__settings.display_height, self.__settings.display_width], np.uint8)
        for x in range(self.__settings.display_width):
            for y in range(self.__settings.display_height):
                if random.random() < self.__settings.seed_liveness_probability:
                    self.__board[y, x] = 1

        self.__show_board()

    def __show_board(self):
        frame = self.__board_to_frame()

        if self.__settings.fade:
            self.__video_player.fade_to_frame(frame)
        else:
            self.__video_player.play_frame(frame)

    def __board_to_frame(self):
        frame = np.zeros([self.__settings.display_height, self.__settings.display_width, 3], np.uint8)
        rgb = self.__game_color_helper.get_rgb(self.__game_color_mode, self.__COLOR_CHANGE_FREQ, self.__num_ticks)
        on = 0 if self.__settings.invert else 1

        for x in range(self.__settings.display_width):
            for y in range(self.__settings.display_height):
                if self.__board[y, x] == on:
                    frame[y, x] = rgb

        return frame

    # Takes ~127-155ms on a 28x18 LED array
    def __tick_internal(self):
        new_board = np.zeros([self.__settings.display_height, self.__settings.display_width], np.uint8)

        # no method calls in the main loop (performance reasons)
        for x in range(self.__settings.display_width):
            for y in range(self.__settings.display_height):
                # calculate num live neighbors
                num_live_neighbors = 0
                # left
                num_live_neighbors += (self.__board[y, x - 1] if x > 1 else 0)
                # left-up
                num_live_neighbors += (self.__board[y - 1, x - 1] if x > 1 and y > 1 else 0)
                # left-down
                num_live_neighbors += (self.__board[y + 1, x - 1] if x > 1 and y < (self.__settings.display_height - 1) else 0)
                # right
                num_live_neighbors += (self.__board[y, x + 1] if x < (self.__settings.display_width - 1) else 0)
                # right-up
                num_live_neighbors += (self.__board[y - 1, x + 1] if x < (self.__settings.display_width - 1) and y > 1 else 0)
                # right-down
                num_live_neighbors += (self.__board[y + 1, x + 1] if x < (self.__settings.display_width - 1) and y < (self.__settings.display_height - 1) else 0)
                # up
                num_live_neighbors += (self.__board[y - 1, x] if y > 1 else 0)
                # down
                num_live_neighbors += (self.__board[y + 1, x] if y < (self.__settings.display_height - 1) else 0)

                # 1. Any live cell with fewer than two live neighbours dies, as if by underpopulation.
                if self.__board[y, x] == 1 and num_live_neighbors < 2:
                    new_board[y, x] = 0

                # 2. Any live cell with two or three live neighbours lives on to the next generation.
                elif self.__board[y, x] == 1 and (num_live_neighbors == 2 or num_live_neighbors == 3):
                    new_board[y, x] = 1

                # 3. Any live cell with more than three live neighbours dies, as if by overpopulation.
                elif self.__board[y, x] == 1 and num_live_neighbors > 3:
                    new_board[y, x] = 0

                # 4. Any dead cell with exactly three live neighbours becomes a live cell, as if by reproduction.
                elif self.__board[y, x] == 0 and num_live_neighbors == 3:
                    new_board[y, x] = 1

        self.__board = new_board
        self.__show_board()
