import numpy as np
import random
import time
import math
import hashlib
import pprint
import sqlite3
import os
import collections
import select
import simpleaudio
from pifi.logger import Logger
from pifi.playlist import Playlist
from pifi.videoplayer import VideoPlayer
from pifi.settings.gameoflifesettings import GameOfLifeSettings
from pifi.datastructure.limitedsizedict import LimitedSizeDict
from pifi.games.gamecolorhelper import GameColorHelper
from pifi.games.scoredisplayer import ScoreDisplayer
from pifi.directoryutils import DirectoryUtils

class Snake:

    UP = 1
    DOWN = 2
    LEFT = 3
    RIGHT = 4

    GAME_TITLE = "snake"

    __GAME_OVER_REASON_SNAKE_STATE = 'game_over_reason_snake_state'
    __GAME_OVER_REASON_SKIP_REQUESTED = 'game_over_reason_skip_requested'
    __GAME_OVER_REASON_SOCKET_SIGNAL = 'game_over_reason_socket_signal'

    __SNAKE_STARTING_LENGTH = 4

    __SNAKE_COLOR_CHANGE_FREQ = 0.05

    __APPLE_COLOR_CHANGE_FREQ = 0.2

    __logger = None

    # SnakeSettings
    __settings = None

    __game_color_helper = None

    __num_ticks = None

    __game_color_mode = None

    # doubly linked list representing all the coordinate pairs in the snake
    __snake_linked_list = None

    # set datastructure representing all the coordinate pairs in the snake
    __snake_set = None

    __direction = None

    __apple = None

    __apple_sound = None

    __pp = None

    __playlist = None

    __playlist_video_id = None

    __unix_socket = None
    __unix_socket_address = None

    def __init__(self, settings, unix_socket):
        self.__logger = Logger().set_namespace(self.__class__.__name__)
        self.__settings = settings
        self.__game_color_helper = GameColorHelper()
        self.__video_player = VideoPlayer(self.__settings)
        self.__logger.info("Doing init with SnakeSettings: {}".format(vars(self.__settings)))
        self.__pp = pprint.PrettyPrinter(indent=4)
        self.__playlist = Playlist()
        self.__apple_sound = simpleaudio.WaveObject.from_wave_file(DirectoryUtils().root_dir + "/assets/snake/sfx_coin_double7.wav")

        self.__unix_socket = unix_socket

    def newGame(self, playlist_video_id = None):
        self.__reset()
        self.__show_board()
        self.__playlist_video_id = playlist_video_id

        while True:
            time.sleep(0.05)#self.__settings.tick_sleep)

            move = None
            is_ready_to_read, ignore1, ignore2 = select.select([self.__unix_socket], [], [], 0)
            if is_ready_to_read:
                move, self.__unix_socket_address = self.__unix_socket.recvfrom(4096)
                move = move.decode()
                if move == "game_over":
                    self.__end_game(self.__GAME_OVER_REASON_SOCKET_SIGNAL)
                    break
                move = int(move)

            if move is not None:
                new_direction = move
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
                self.__end_game(self.__GAME_OVER_REASON_SNAKE_STATE)
                break
            if self.__should_skip_game():
                self.__end_game(self.__GAME_OVER_REASON_SKIP_REQUESTED)
                break

    def __tick(self):
        self.__num_ticks += 1
        old_head_y, old_head_x = self.__snake_linked_list[0]

        if self.__direction == self.UP:
            new_head = ((old_head_y - 1) % self.__settings.display_height, old_head_x)
        elif self.__direction == self.DOWN:
            new_head = ((old_head_y + 1) % self.__settings.display_height, old_head_x)
        elif self.__direction == self.LEFT:
            new_head = (old_head_y, (old_head_x - 1) % self.__settings.display_width)
        elif self.__direction == self.RIGHT:
            new_head = (old_head_y, (old_head_x + 1) % self.__settings.display_width)

        self.__snake_linked_list.insert(0, new_head)
        self.__snake_set.add(new_head)

        if new_head == self.__apple:
            self.__eat_apple()
        else:
            old_tail = self.__snake_linked_list[-1]
            del self.__snake_linked_list[-1]
            self.__snake_set.remove(old_tail)

        self.__show_board()

    def __eat_apple(self):
        play_obj = self.__apple_sound.play()
        self.__place_apple()

    def __place_apple(self):
        # TODO: make better
        while True:
            x = random.randint(0, self.__settings.display_width - 1)
            y = random.randint(0, self.__settings.display_height - 1)
            if (y, x) not in self.__snake_set:
                break
        self.__apple = (y, x)

    def __is_game_over(self):
        return len(self.__snake_set) < len(self.__snake_linked_list)

    def __show_board(self):
        frame = np.zeros([self.__settings.display_height, self.__settings.display_width, 3], np.uint8)
        snake_rgb = self.__game_color_helper.get_rgb(self.__game_color_mode, self.__SNAKE_COLOR_CHANGE_FREQ, self.__num_ticks)
        apple_rgb = self.__game_color_helper.get_rgb(GameColorHelper.GAME_COLOR_MODE_RAINBOW, self.__APPLE_COLOR_CHANGE_FREQ, self.__num_ticks)

        for (y, x) in self.__snake_linked_list:
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
            self.__snake_linked_list.append(coordinate)
            self.__snake_set.add(coordinate)

        self.__place_apple()

    def __reset_datastructures(self):
        self.__snake_linked_list = collections.deque()
        self.__apple = None
        self.__snake_set = set()

    def __end_game(self, reason):
        self.__close_websocket()
        score = len(self.__snake_linked_list)
        if reason == self.__GAME_OVER_REASON_SNAKE_STATE:
            time.sleep(0.3)
            for x in range(1, 5): # bink board
                self.__clear_board()
                time.sleep(0.1)
                self.__show_board()
                time.sleep(0.1)

            score_displayer = ScoreDisplayer(self.__settings, self.__video_player, score)
            score_displayer.display_score()
            for i in range(1, 40):
                # if someone clicks "New Game" while the score is being displayed, immediately start a new game
                # instead of waiting for the score to stop being displayed
                time.sleep(0.2)
                if self.__should_skip_game():
                    break

        self.__clear_board()

        self.__logger.info("game over. score: {}. Reason: {}".format(score, reason))
        self.__reset_datastructures()

    def __clear_board(self):
        frame = np.zeros([self.__settings.display_height, self.__settings.display_width, 3], np.uint8)
        self.__video_player.play_frame(frame)

    def __close_websocket(self):
        try:
            sent = self.__unix_socket.sendto('close_websocket'.encode(), self.__unix_socket_address)
        except Exception as e:
            pass

    def __should_skip_game(self):
        if not self.__settings.should_check_playlist:
            return False

        if self.__playlist.should_skip_video_id(self.__playlist_video_id):
            return True
        return False;
