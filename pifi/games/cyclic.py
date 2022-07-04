import numpy as np
import random
import time
import hashlib
from pifi.config import Config
from pifi.logger import Logger
from pifi.led.ledframeplayer import LedFramePlayer
from pifi.datastructure.limitedsizedict import LimitedSizeDict
from pifi.games.gamecolorhelper import GameColorHelper
import pifi.games.palette

class Cyclic:

    __COLOR_CHANGE_FREQ = 0.05
    __MAX_STATE_REPETITIONS_FOR_GAME_OVER = 10
    __TIMEOUT = 60

    palettes = vars(pifi.games.palette)

    def __init__(self):
        self.__logger = Logger().set_namespace(self.__class__.__name__)
        self.__video_player = LedFramePlayer()
        self.__game_color_helper = GameColorHelper()
        self.__board = None
        self.n = 16

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

        time.sleep(Config.get('game_of_life.tick_sleep', 0.07))

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
        if time.time() - self.__started > self.__TIMEOUT:
            return True
        if self.__prev_board_state_counts[self.__get_board_hash()] > self.__MAX_STATE_REPETITIONS_FOR_GAME_OVER:
            self.__logger.info(("Game over detected. Current board state has repeated at least {} times."
                    .format(self.__MAX_STATE_REPETITIONS_FOR_GAME_OVER)))
            return True
        return False

    def __reset(self):
        self.__logger.info("Starting new game.")
        self.__started = time.time()
        self.__num_ticks = 0
        self.__game_color_helper.reset()
        self.__game_color_mode = GameColorHelper.determine_game_color_mode(Config.get('game_of_life.game_color_mode'))
        self.__prev_board_state_counts = LimitedSizeDict(capacity = Config.get('game_of_life.game_over_detection_lookback', 16))
        self.palette = np.array(random.choice(list(self.palettes.values())))
        self.__seed()
        
    # See https://lhoupert.fr/test-jbook/book-jupyterbook.html#the-game-of-life
    def __seed(self):
        # Create the board with an extra edge cell on all sides to simplify the
        # neighborhood calculation and avoid edge checks.
        shape = [Config.get_or_throw('leds.display_height') + 2, Config.get_or_throw('leds.display_width') + 2]
        self.__board = np.random.randint(0,self.n,shape)

        self.__show_board()

    def __show_board(self):
        frame = self.__board_to_frame()

        if Config.get('game_of_life.fade', False):
            self.__video_player.fade_to_frame(frame)
        else:
            self.__video_player.play_frame(frame)

    def __board_to_frame(self):
        #frame = np.zeros([self.__settings.display_height, self.__settings.display_width, 3], np.uint8)

        board_shape = self.__board.shape + (3,)
        foo = self.palette[self.__board.ravel()].reshape(board_shape)
        return foo[1:-1,1:-1]

    def __tick_internal(self):
        self.__update_board()
        self.__show_board()

    # See https://lhoupert.fr/test-jbook/book-jupyterbook.html#the-game-of-life
    def __update_board(self):
        b = self.__board
        # n is an array of the count of the live neighbors in the board.
        # We stop counting at the edge of the board by summing up partial
        # boards that don't include the 2 edge cells.
        slices = [((0,-2), (0,-2)), 
                  ((0,-2), (1,-1)),
                  ((0,-2), (2,None)),
                  ((1,-1), (0,-2)),
                  ((1,-1), (2,None)),
                  ((2,None), (0,-2)),
                  ((2,None), (1,-1)),
                  ((2,None), (2,None))]

        succ = None
        bpad = b[1:-1,1:-1]
        for indices in slices:
            s = tuple(slice(*x) for x in indices)
            if succ is None:
                succ = (b[s] == ((bpad + 1) % self.n))
            else:
                succ |= (b[s] == ((bpad + 1) % self.n))

        b[1:-1,1:-1][succ] = ((bpad[succ] + 1) % self.n)

        self.__board = b
