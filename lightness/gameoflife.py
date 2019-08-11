import numpy as np
import random
import time
from lightness.logger import Logger
from lightness.videoplayer import VideoPlayer
from lightness.datastructure.appendonlycircularbuffer import AppendOnlyCircularBuffer

class GameOfLife:

    __GAME_OVER_DETECTION_LOOKBACK = 10
    __TICK_DURATION = 0.500 # seconds

    # GameOfLifeSettings
    __settings = None

    __board = None

    # AppendOnlyCircularBuffer
    __last_num_live = None

    def __init__(self, settings):
        self.__logger = Logger().set_namespace(self.__class__.__name__)
        self.__settings = settings
        self.__video_player = VideoPlayer(self.__settings)

    def play(self):
        self.__reset()
        while True:
            time.sleep(self.__TICK_DURATION)
            self.tick()
            if self.__is_game_over():
                break;

    def play_loop(self):
        while True:
            self.play()

    def __is_game_over(self):
        if not self.__last_num_live.is_full():
            return False

        last_num_live = None
        for i in range(0, len(self.__last_num_live)):
            if last_num_live == None:
                last_num_live = self.__last_num_live[i]
            else:
                if last_num_live != self.__last_num_live[i]:
                    return False

        self.__logger.info("Game over detected.")
        return True

    def __reset(self):
        self.__logger.info("Starting new game.")
        self.__last_num_live = AppendOnlyCircularBuffer(self.__GAME_OVER_DETECTION_LOOKBACK)
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
        self.__video_player.play_frame(frame)

    def __board_to_frame(self):
        frame = np.zeros([self.__settings.display_height, self.__settings.display_width, 3], np.uint8)
        rgb = [255, 255, 255]
        for x in range(self.__settings.display_width):
            for y in range(self.__settings.display_height):
                if self.__board[y,x] == 1:
                    frame[y, x] = rgb
        return frame

    def tick(self):
        new_board = np.zeros([self.__settings.display_height, self.__settings.display_width], np.uint8)
        num_live = 0

        # no method calls in the main loop (performance reasons)
        for x in range(self.__settings.display_width):
            for y in range(self.__settings.display_height):
                # calculate num live neighbors
                num_live_neighbors = 0
                if x > 0:
                    if self.__board[y, x - 1] == 1:
                        num_live_neighbors += 1
                    if y > 0:
                        if self.__board[y - 1, x - 1] == 1:
                            num_live_neighbors += 1
                    if (y + 1) < self.__settings.display_height:
                        if self.__board[y + 1, x - 1] == 1:
                            num_live_neighbors += 1
                if (x + 1) < self.__settings.display_width:
                    if self.__board[y, x + 1] == 1:
                        num_live_neighbors += 1
                    if y > 0:
                        if self.__board[y - 1, x + 1] == 1:
                            num_live_neighbors += 1
                    if (y + 1) < self.__settings.display_height:
                        if self.__board[y + 1, x + 1] == 1:
                            num_live_neighbors += 1
                if y > 0:
                    if self.__board[y - 1, x] == 1:
                        num_live_neighbors += 1
                if (y + 1) < self.__settings.display_height:
                    if self.__board[y + 1, x] == 1:
                        num_live_neighbors += 1

                # 1. Any live cell with fewer than two live neighbours dies, as if by underpopulation.
                if self.__board[y, x] == 1 and num_live_neighbors < 2:
                    new_board[y, x] = 0

                # 2. Any live cell with two or three live neighbours lives on to the next generation.
                elif self.__board[y, x] == 1 and (num_live_neighbors == 2 or num_live_neighbors == 3):
                    new_board[y, x] = 1
                    num_live += 1

                # 3. Any live cell with more than three live neighbours dies, as if by overpopulation.
                elif self.__board[y, x] == 1 and num_live_neighbors > 3:
                    new_board[y, x] = 0

                # 4. Any dead cell with exactly three live neighbours becomes a live cell, as if by reproduction.
                elif self.__board[y, x] == 0 and num_live_neighbors == 3:
                    new_board[y, x] = 1
                    num_live += 1

        self.__last_num_live.append(num_live)
        self.__board = new_board
        self.__show_board()
