import numpy as np
import random

from pifi.config import Config
from pifi.games.gamecolorhelper import GameColorHelper
from pifi.screensaver.cellularautomata.cellularautomaton import CellularAutomaton

class GameOfLife(CellularAutomaton):

    __COLOR_CHANGE_FREQ = 0.05

    # Normal game of life
    __VARIANT_NORMAL = 'normal'

    # https://cs.stanford.edu/people/eroberts/courses/soco/projects/2008-09/modeling-natural-systems/gameOfLife2.html
    __VARIANT_IMMIGRATION = 'immigration'
    VARIANTS = (__VARIANT_NORMAL, __VARIANT_IMMIGRATION,)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.__game_color_helper = GameColorHelper()

    def _get_tick_sleep_seconds(self):
        return Config.get('game_of_life.tick_sleep')

    def _get_game_over_detection_lookback_amount(self):
        return Config.get('game_of_life.game_over_detection_lookback')

    def _should_fade_to_frame(self):
        return Config.get('game_of_life.fade')

    def _reset_hook(self):
        self.__game_color_helper.reset()
        self.__game_color_mode = GameColorHelper.determine_game_color_mode(Config.get('game_of_life.game_color_mode'))

        variant = Config.get('game_of_life.variant')
        if variant in self.VARIANTS:
            self.__variant = variant
        else:
            self.__variant = random.choice(self.VARIANTS)

    # See https://lhoupert.fr/test-jbook/book-jupyterbook.html#the-game-of-life
    def _seed_hook(self):
        # Create the board with an extra edge cell on all sides to simplify the
        # neighborhood calculation and avoid edge checks.
        shape = [Config.get_or_throw('leds.display_height') + 2, Config.get_or_throw('leds.display_width') + 2]
        self._board = np.zeros(shape, np.uint8)
        probability = Config.get('game_of_life.seed_liveness_probability')
        if self.__variant == self.__VARIANT_IMMIGRATION:
            seed = np.random.random_sample([x - 2 for x in shape]) < (probability / 2)
            seed2 = np.random.random_sample([x - 2 for x in shape]) < (probability / 2)
            self._board[1:-1, 1:-1][seed] = 1
            self._board[1:-1, 1:-1][seed2] = 2
        else: # __VARIANT_NORMAL
            seed = np.random.random_sample([x - 2 for x in shape]) < probability
            self._board[1:-1, 1:-1][seed] = 1

    def _board_to_frame(self):
        frame = np.zeros([Config.get_or_throw('leds.display_height'), Config.get_or_throw('leds.display_width'), 3], np.uint8)
        rgb = self.__game_color_helper.get_rgb(self.__game_color_mode, self.__COLOR_CHANGE_FREQ, self._num_ticks)
        frame[(self._board[1:-1, 1:-1] == 1)] = rgb

        if self.__variant == self.__VARIANT_IMMIGRATION:
            rgb2 = self.__game_color_helper.get_rgb2(self.__game_color_mode, self.__COLOR_CHANGE_FREQ, self._num_ticks)
            frame[(self._board[1:-1, 1:-1] == 2)] = rgb2

        return frame

    def _update_board(self):
        if self.__variant == self.__VARIANT_IMMIGRATION:
            self.__update_board_immigration()
        else: # __VARIANT_NORMAL
            self.__update_board_normal()

    # See https://lhoupert.fr/test-jbook/book-jupyterbook.html#the-game-of-life
    def __update_board_normal(self):
        b = self._board

        # n is an array of the count of the live neighbors in the board.
        # We stop counting at the edge of the board by summing up partial
        # boards that don't include the 2 edge cells.
        n = (b[ :-2, :-2] + b[ :-2,1:-1] + b[ :-2,2:] +
             b[1:-1, :-2]                + b[1:-1,2:] +
             b[2:  , :-2] + b[2:  ,1:-1] + b[2:  ,2:])

        # 1. Any live cell with two or three live neighbours lives on to the next generation.
        survivors = ((n==2) | (n==3)) & (b[1:-1,1:-1]==1)

        # 2. Any dead cell with exactly three live neighbours becomes a live cell, as if by reproduction.
        new_cells = (n==3) & (b[1:-1,1:-1]==0)

        # 3. All other cells die (over or underpopulation).
        new_board = np.zeros(b.shape, np.uint8)
        new_board[1:-1,1:-1][new_cells | survivors] = 1

        self._board = new_board

    def __update_board_immigration(self):
        b = self._board

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

        n = None
        ones = None
        twos = None
        for indices in slices:
            s = tuple(slice(*x) for x in indices)
            if n is None:
                n = (b[s] > 0).astype(int)
                ones = (b[s] == 1).astype(int)
                twos = (b[s] == 2).astype(int)
            else:
                n += (b[s] > 0).astype(int)
                ones += (b[s] == 1).astype(int)
                twos += (b[s] == 2).astype(int)

        # 1. Any live cell with two or three live neighbours lives on to the next generation.
        survivors = ((n==2) | (n==3)) & (b[1:-1,1:-1]>0)

        # 2. Any dead cell with exactly three live neighbours becomes a live cell, as if by reproduction.
        new_cells = (n==3) & (b[1:-1,1:-1]==0)

        # 3. All other cells die (over or underpopulation).
        new_board = np.zeros(b.shape, np.uint8)
        new_board[1:-1,1:-1][survivors] = b[1:-1,1:-1][survivors]
        new_board[1:-1,1:-1][new_cells & (ones > twos)] = 1
        new_board[1:-1,1:-1][new_cells & (twos > ones)] = 2

        self._board = new_board

    @classmethod
    def get_id(cls) -> str:
        return 'game_of_life'

    @classmethod
    def get_name(cls) -> str:
        return 'Game of Life'

    @classmethod
    def get_description(cls) -> str:
        return "Conway's Game of Life"
