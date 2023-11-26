from abc import ABC, abstractmethod
import hashlib
import time

from pifi.logger import Logger
from pifi.led.ledframeplayer import LedFramePlayer
from pifi.datastructure.limitedsizedict import LimitedSizeDict

# Base class for cellular automaton games
class CellularAutomaton(ABC):

    _DEFAULT_MAX_GAME_LENGTH_SECONDS = 0 # unlimited
    _DEFAULT_MAX_STATE_REPETITIONS_FOR_GAME_OVER = 10

    def __init__(self, led_frame_player = None):
        self._logger = Logger().set_namespace(self.__class__.__name__)
        self._board = None
        if led_frame_player is None:
            self.__led_frame_player = LedFramePlayer()
        else:
            self.__led_frame_player = led_frame_player

    def play(self, should_loop = False):
        if should_loop:
            while True:
                self.tick(should_loop = should_loop)
        else:
            self.__reset()
            while True:
                if not self.tick():
                    break

    # return False when the game is over, True otherwise.
    def tick(self, should_loop = False, force_reset = False):
        is_game_in_progress = True
        if self._board is None or force_reset:
            # start the game
            self.__reset()
        else:
            self.__tick_internal()

        self.__do_tick_bookkeeping()

        if self.__is_game_over():
            if should_loop:
                self.__reset()
                self.__do_tick_bookkeeping()
                is_game_in_progress = True
            else:
                is_game_in_progress = False

        time.sleep(self._get_tick_sleep_seconds())

        return is_game_in_progress

    def __tick_internal(self):
        self._update_board()
        self.__show_board()

    def __do_tick_bookkeeping(self):
        self._num_ticks += 1
        board_hash = self.__get_board_hash()
        if board_hash in self.__prev_board_state_counts:
            self.__prev_board_state_counts[board_hash] += 1
        else:
            self.__prev_board_state_counts[board_hash] = 1

    def __show_board(self):
        frame = self._board_to_frame()

        if self._should_fade_to_frame():
            self.__led_frame_player.fade_to_frame(frame)
        else:
            self.__led_frame_player.play_frame(frame)

    def __get_board_hash(self):
        return hashlib.md5(self._board).hexdigest()

    def __is_game_over(self):
        if self._get_max_game_length_seconds() > 0 and (time.time() - self.__start_time) > self._get_max_game_length_seconds():
            self._logger.info("Game over due to timeout expiration.")
            return True

        if self.__prev_board_state_counts[self.__get_board_hash()] > self._get_max_state_repetitions_for_game_over():
            self._logger.info("Game over detected. Current board state has repeated at least " +
                f"{self._get_max_state_repetitions_for_game_over()} times.")
            return True
        return False

    def __reset(self):
        self._logger.info("Starting new game.")
        self.__start_time = time.time()
        self._num_ticks = 0
        self.__prev_board_state_counts = LimitedSizeDict(capacity = self._get_game_over_detection_lookback_amount())

        self._reset_hook()

        self.__seed()

    def __seed(self):
        self._seed_hook()
        self.__show_board()

    @abstractmethod
    def _reset_hook(self):
        pass

    @abstractmethod
    def _seed_hook(self):
        pass

    @abstractmethod
    def _board_to_frame(self):
        pass

    @abstractmethod
    def _update_board(self):
        pass

    @abstractmethod
    def _get_tick_sleep_seconds(self):
        pass

    @abstractmethod
    def _get_game_over_detection_lookback_amount(self):
        pass

    @abstractmethod
    def _should_fade_to_frame(self):
        pass

    def _get_max_state_repetitions_for_game_over(self):
        return self._DEFAULT_MAX_STATE_REPETITIONS_FOR_GAME_OVER

    # 0 means unlimited
    def _get_max_game_length_seconds(self):
        return self._DEFAULT_MAX_GAME_LENGTH_SECONDS
