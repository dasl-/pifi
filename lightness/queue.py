import os
import sys
import ast
import subprocess
import time
import json
import shlex
from lightness.playlist import Playlist
from lightness.logger import Logger
from lightness.settings.ledsettings import LedSettings
from lightness.settings.videosettings import VideoSettings
from lightness.settings.gameoflifesettings import GameOfLifeSettings
from lightness.videoplayer import VideoPlayer
from lightness.videoprocessor import VideoProcessor
from lightness.config import Config
from lightness.gameoflife import GameOfLife

# The Queue is responsible for playing the next video in the Playlist
class Queue:

    __playlist = None
    __config = None
    __logger = None
    __should_play_game_of_life = None

    def __init__(self):
        self.__playlist = Playlist()
        self.__config = Config()
        self.__should_play_game_of_life = self.__config.get_queue_config('should_play_game_of_life', True)
        self.__logger = Logger().set_namespace(self.__class__.__name__)
        self.__clear_screen()
        self.__playlist.clean_up_state()

    def run(self):
        if self.__should_play_game_of_life:
            game_of_life = GameOfLife(self.__get_game_of_life_settings())
            has_reset_game_since_last_video = True

        while True:
            next_video = self.__playlist.get_next_video()
            if next_video:
                self.__play_video(next_video)
                if self.__should_play_game_of_life:
                    has_reset_game_since_last_video = False
            elif self.__should_play_game_of_life:
                if has_reset_game_since_last_video:
                    force_reset = False
                else:
                    force_reset = True
                    has_reset_game_since_last_video = True
                game_of_life.tick(should_loop = True, force_reset = force_reset)
            else:
                time.sleep(0.050)

    def __play_video(self, video_record):
        if not self.__playlist.set_current_video(video_record["playlist_video_id"]):
            # Someone deleted the video from the queue in between getting the video and starting it.
            return

        video_settings = self.__get_video_settings(video_record)
        video_player = VideoPlayer(video_settings)
        video_processor = VideoProcessor(video_settings, video_record['playlist_video_id'])
        video_processor.process_and_play(url = video_record["url"], video_player = video_player)

        self.__playlist.end_video(video_record["playlist_video_id"])

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
            game_color_mode = GameOfLifeSettings.GAME_COLOR_MODE_RANDOM

        return GameOfLifeSettings(
            display_width = display_width, display_height = display_height,
            brightness = brightness, flip_x = flip_x, flip_y = flip_y, log_level = log_level,
            seed_liveness_probability = seed_liveness_probability, tick_sleep = tick_sleep,
            game_over_detection_lookback = game_over_detection_lookback, game_color_mode = game_color_mode,
        )
