import os
import errno
import sys
import ast
import subprocess
import time
import json
import shlex
import socket
from pifi.playlist import Playlist
from pifi.logger import Logger
from pifi.settings.ledsettings import LedSettings
from pifi.settings.videosettings import VideoSettings
from pifi.settings.gameoflifesettings import GameOfLifeSettings
from pifi.videoplayer import VideoPlayer
from pifi.videoprocessor import VideoProcessor
from pifi.config import Config
from pifi.games.gameoflife import GameOfLife
from pifi.games.gamecolorhelper import GameColorHelper
from pifi.volumecontroller import VolumeController
from pifi.games.snake import Snake
from pifi.settings.snakesettings import SnakeSettings

# The Queue is responsible for playing the next video in the Playlist
class Queue:

    UNIX_SOCKET_PATH = '/tmp/snake_socket'

    __playlist = None
    __config = None
    __logger = None
    __should_play_game_of_life = None

    def __init__(self):
        self.__playlist = Playlist()
        self.__config = Config()
        self.__should_play_game_of_life = self.__config.get_queue_config('should_play_game_of_life', True)
        self.__logger = Logger().set_namespace(self.__class__.__name__)

        self.__setup_unix_socket()

        # house keeping
        self.__clear_screen()
        (VolumeController()).set_vol_pct(50)
        self.__playlist.clean_up_state()

    def run(self):
        if self.__should_play_game_of_life:
            game_of_life = GameOfLife(self.__get_game_of_life_settings())
            has_reset_game_since_last_video = True

        while True:
            next_item = self.__playlist.get_next_playlist_item()
            if next_item:
                if next_item["type"] == Playlist.TYPE_VIDEO or next_item["type"] == Playlist.TYPE_GAME:
                    self.__play_playlist_item(next_item)
                    if self.__should_play_game_of_life:
                        has_reset_game_since_last_video = False
                else:
                    raise Exception("Invalid playlist_item type: {}".format(next_item["type"]))
            elif self.__should_play_game_of_life:
                if has_reset_game_since_last_video:
                    force_reset = False
                else:
                    force_reset = True
                    has_reset_game_since_last_video = True
                game_of_life.tick(should_loop = True, force_reset = force_reset)
            else:
                time.sleep(0.050)

    def __play_playlist_item(self, playlist_item):
        if not self.__playlist.set_current_video(playlist_item["playlist_video_id"]):
            # Someone deleted the item from the queue in between getting the item and starting it.
            return

        exception_to_raise = None
        if playlist_item["type"] == Playlist.TYPE_VIDEO:
            video_settings = self.__get_video_settings(playlist_item)
            video_player = VideoPlayer(video_settings)
            video_processor = VideoProcessor(video_settings, playlist_item['playlist_video_id'])
            video_processor.process_and_play(url = playlist_item["url"], video_player = video_player)
        elif playlist_item["type"] == Playlist.TYPE_GAME:
            if playlist_item["title"] == Snake.GAME_TITLE:
                snake_settings = SnakeSettings(
                    # display_width = args.display_width, display_height = args.display_height,
                    # brightness = args.brightness, flip_x = args.flip_x, flip_y = args.flip_y, log_level = None,
                    # tick_sleep = args.tick_sleep, game_color_mode = args.game_color_mode,
                    tick_sleep = 0.2, should_check_playlist = True,
                )
                snake = Snake(snake_settings, self.__unix_socket)
                snake.newGame(playlist_video_id = playlist_item["playlist_video_id"])
            else:
                exception_to_raise = Exception("Invalid game title: {}".format(playlist_item["title"]))
        else:
            exception_to_raise = Exception("Invalid playlist_item type: {}".format(playlist_item["type"]))

        self.__playlist.end_video(playlist_item["playlist_video_id"])
        if exception_to_raise is not None:
            raise exception_to_raise

    def __clear_screen(self):
        # VIdeoPlayer.__init__() method will clear the screen
        VideoPlayer(self.__get_video_settings())

    def __get_led_settings(self, settings_type = None):
        settings_types = ['video', 'game_of_life',]
        if not settings_type in settings_types:
            raise Exception("Invalid settings_type: {}".format(settings_type))
        if settings_type == 'video':
            config = self.__config.get_video_settings()
        else:
            config = self.__config.get_game_of_life_settings()

        if 'display_width' in config:
            display_width = config['display_width']
        else:
            display_width = LedSettings.DEFAULT_DISPLAY_WIDTH

        if 'display_height' in config:
            display_height = config['display_height']
        else:
            display_height = LedSettings.DEFAULT_DISPLAY_HEIGHT

        if 'brightness' in config:
            brightness = config['brightness']
        else:
            brightness = LedSettings.DEFAULT_BRIGHTNESS

        if 'flip_x' in config:
            flip_x = config['flip_x']
        else:
            flip_x = False

        if 'flip_y' in config:
            flip_y = config['flip_y']
        else:
            flip_y = False

        if 'log_level' in config:
            log_level = config['log_level']
        else:
            log_level = LedSettings.LOG_LEVEL_NORMAL

        return display_width, display_height, brightness, flip_x, flip_y, log_level

    def __get_video_settings(self, video_record = None):
        display_width, display_height, brightness, flip_x, flip_y, log_level = self.__get_led_settings('video')
        config = self.__config.get_video_settings()

        if 'color_mode' in config:
            color_mode = config['color_mode']
        else:
            color_mode = VideoSettings.COLOR_MODE_COLOR
            if video_record:
                color_modes = [
                    VideoSettings.COLOR_MODE_COLOR,
                    VideoSettings.COLOR_MODE_BW,
                    VideoSettings.COLOR_MODE_R,
                    VideoSettings.COLOR_MODE_G,
                    VideoSettings.COLOR_MODE_B,
                    VideoSettings.COLOR_MODE_INVERT_COLOR,
                    VideoSettings.COLOR_MODE_INVERT_BW
                ]
                if video_record["color_mode"] in color_modes:
                    color_mode = video_record["color_mode"]

        if 'should_play_audio' in config:
            should_play_audio = config['should_play_audio']
        else:
            should_play_audio = True

        if 'should_save_video' in config:
            should_save_video = config['should_save_video']
        else:
            should_save_video = False

        if 'should_predownload_video' in config:
            should_predownload_video = config['should_predownload_video']
        else:
            should_predownload_video = False

        return VideoSettings(
            color_mode = color_mode, display_width = display_width, display_height = display_height,
            should_play_audio = should_play_audio, brightness = brightness,
            flip_x = flip_x, flip_y = flip_y, should_save_video = should_save_video,
            log_level = log_level, should_check_playlist = True, should_predownload_video = should_predownload_video
        )

    def __get_game_of_life_settings(self):
        display_width, display_height, brightness, flip_x, flip_y, log_level = self.__get_led_settings('game_of_life')
        config = self.__config.get_game_of_life_settings()

        if 'seed_liveness_probability' in config:
            seed_liveness_probability = config['seed_liveness_probability']
        else:
            seed_liveness_probability = GameOfLifeSettings.DEFAULT_SEED_LIVENESS_PROBABILITY

        if 'tick_sleep' in config:
            tick_sleep = config['tick_sleep']
        else:
            tick_sleep = GameOfLifeSettings.DEFAULT_TICK_SLEEP

        if 'game_over_detection_lookback' in config:
            game_over_detection_lookback = config['game_over_detection_lookback']
        else:
            game_over_detection_lookback = GameOfLifeSettings.DEFAULT_GAME_OVER_DETECTION_LOOKBACK

        if 'game_color_mode' in config:
            game_color_mode = config['game_color_mode']
        else:
            game_color_mode = GameColorHelper.GAME_COLOR_MODE_RANDOM

        if 'fade' in config:
            fade = config['fade']
        else:
            fade = GameOfLifeSettings.DEFAULT_FADE

        if 'invert' in config:
            invert = config['invert']
        else:
            invert = GameOfLifeSettings.DEFAULT_INVERT


        return GameOfLifeSettings(
            display_width = display_width, display_height = display_height,
            brightness = brightness, flip_x = flip_x, flip_y = flip_y, log_level = log_level,
            seed_liveness_probability = seed_liveness_probability, tick_sleep = tick_sleep,
            game_over_detection_lookback = game_over_detection_lookback, game_color_mode = game_color_mode,
            fade = fade, invert = invert
        )

    def __setup_unix_socket(self):
        self.__unix_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        try:
            os.remove(self.UNIX_SOCKET_PATH)
        except OSError as e: # this would be "except OSError, e:" before Python 2.6
            if e.errno != errno.ENOENT: # errno.ENOENT = no such file or directory
                raise # re-raise exception if a different error occurred
        self.__unix_socket.bind(self.UNIX_SOCKET_PATH)
