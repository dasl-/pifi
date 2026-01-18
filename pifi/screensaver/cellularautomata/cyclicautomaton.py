import numpy as np
import random

from pifi.config import Config
from pifi.screensaver.cellularautomata.palette import palettes
from pifi.screensaver.cellularautomata.cellularautomaton import CellularAutomaton

# https://en.wikipedia.org/wiki/Cyclic_cellular_automaton
class CyclicAutomaton(CellularAutomaton):

    def _get_tick_sleep_seconds(self):
        return Config.get('cyclic_automaton.tick_sleep')

    def _get_game_over_detection_lookback_amount(self):
        return Config.get('cyclic_automaton.game_over_detection_lookback')

    def _should_fade_to_frame(self):
        return Config.get('cyclic_automaton.fade')

    def _get_max_game_length_seconds(self):
        return 60

    def _reset_hook(self):
        self.__num_states = random.randint(5, 16)
        self.__palette = np.array(random.choice(palettes))

    def _seed_hook(self):
        # Create the board with an extra edge cell on all sides to simplify the
        # neighborhood calculation and avoid edge checks.
        shape = [Config.get_or_throw('leds.display_height') + 2, Config.get_or_throw('leds.display_width') + 2]
        self._board = np.random.randint(0, self.__num_states, shape)

    def _board_to_frame(self):
        board_shape = self._board.shape + (3,)
        foo = self.__palette[self._board.ravel()].reshape(board_shape)
        return foo[1:-1, 1:-1]

    def _update_board(self):
        b = self._board

        slices = [((0,-2), (0,-2)), 
                  ((0,-2), (1,-1)),
                  ((0,-2), (2,None)),
                  ((1,-1), (0,-2)),
                  ((1,-1), (2,None)),
                  ((2,None), (0,-2)),
                  ((2,None), (1,-1)),
                  ((2,None), (2,None))]

        succ = None
        bpad = b[1:-1, 1:-1]
        for indices in slices:
            s = tuple(slice(*x) for x in indices)
            if succ is None:
                succ = (b[s] == ((bpad + 1) % self.__num_states))
            else:
                succ |= (b[s] == ((bpad + 1) % self.__num_states))

        b[1:-1, 1:-1][succ] = ((bpad[succ] + 1) % self.__num_states)

        self._board = b
