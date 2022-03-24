import os
import time
import traceback
import shlex
import signal
import simpleaudio
import subprocess

from pifi.directoryutils import DirectoryUtils
from pifi.playlist import Playlist
from pifi.logger import Logger
from pifi.settings.videosettings import VideoSettings
from pifi.videoplayer import VideoPlayer
from pifi.videoprocessor import VideoProcessor
from pifi.config import Config
from pifi.games.unixsockethelper import UnixSocketHelper
from pifi.volumecontroller import VolumeController
from pifi.games.snake import Snake
from pifi.settings.settingsdb import SettingsDb
from pifi.settings.snakesettings import SnakeSettings
from pifi.database import Database

# The Queue is responsible for playing the next video in the Playlist
class Queue:

    UNIX_SOCKET_PATH = '/tmp/queue_unix_socket'

    def __init__(self):
        self.__playlist = Playlist()
        self.__settings_db = SettingsDb()
        self.__config = Config()
        self.__is_game_of_life_enabled = True
        self.__last_settings_db_check_time = 0
        self.__last_screen_clear_while_screensaver_disabled_time = 0
        self.__logger = Logger().set_namespace(self.__class__.__name__)
        self.__unix_socket = UnixSocketHelper().create_server_unix_socket(self.UNIX_SOCKET_PATH)
        self.__video_player = VideoPlayer(VideoSettings().from_config())

        # True if game of life screensaver, a video, or a game (like snake) is playing
        self.__is_anything_playing = False
        self.__playback_proc = None
        self.__playlist_item = None

        # house keeping
        self.__clear_screen()
        (VolumeController()).set_vol_pct(50)
        self.__playlist.clean_up_state()

    def run(self):
        while True:
            if self.__is_anything_playing:
                self.__maybe_skip_playback()
                if self.__playback_proc and self.__playback_proc.poll() is not None:
                    self.__logger.info("Ending playback because playback proc is no longer running...")
                    self.__stop_playback_if_playing()
            else:
                next_item = self.__playlist.get_next_playlist_item()
                if next_item:
                    self.__play_playlist_item(next_item)
                else:
                    self.__maybe_play_screensaver()

            self.__maybe_respond_to_settings_changes()
            time.sleep(0.050)

    def __play_playlist_item(self, playlist_item):
        exception_to_raise = None
        if playlist_item["type"] == Playlist.TYPE_VIDEO:
            if not self.__playlist.set_current_video(playlist_item["playlist_video_id"]):
                # Someone deleted the item from the queue in between getting the item and starting it.
                return
            video_settings = VideoSettings().from_playlist_item_in_queue(playlist_item)
            video_player = VideoPlayer(video_settings)
            video_processor = VideoProcessor(video_settings, playlist_item['playlist_video_id'])
            video_processor.process_and_play(url = playlist_item["url"], video_player = video_player)
        elif playlist_item["type"] == Playlist.TYPE_GAME:
            if playlist_item["title"] == Snake.GAME_TITLE:
                snake_settings = SnakeSettings().from_playlist_item_in_queue(playlist_item)
                is_waiting_for_players = False
                if snake_settings.num_players > 1:
                    is_waiting_for_players = True
                if not self.__playlist.set_current_video(playlist_item["playlist_video_id"], is_waiting_for_players):
                    # Someone deleted the item from the queue in between getting the item and starting it.
                    return
                snake = Snake(snake_settings, self.__unix_socket, playlist_item)
                try:
                    snake.play_snake()
                except Exception:
                    self.__logger.error('Caught exception: {}'.format(traceback.format_exc()))

            else:
                exception_to_raise = Exception("Invalid game title: {}".format(playlist_item["title"]))
        else:
            exception_to_raise = Exception("Invalid playlist_item type: {}".format(playlist_item["type"]))

        self.__reenqueue_or_end_playlist_item(
            playlist_item, force_end = (exception_to_raise is not None)
        )
        if exception_to_raise is not None:
            raise exception_to_raise

    def __maybe_play_screensaver(self):
        if not self.__is_game_of_life_enabled:
            return
        log_uuid = 'SCREENSAVER__' + Logger.make_uuid()
        Logger.set_uuid(log_uuid)
        self.__logger.info("Starting game of life screensaver...")
        cmd = f"{DirectoryUtils().root_dir}/bin/game_of_life --loop"
        self.__start_playback(cmd, log_uuid)

    # Play something, whether it's a screensaver (game of life), a video, or a game (snake)
    # TODO: set color mode of videos via cli flag
    def __start_playback(self, cmd, log_uuid):
        cmd += f' --log-uuid {shlex.quote(log_uuid)}'

        # Using start_new_session = False here because it is not necessary to start a new session here (though
        # it should not hurt if we were to set it to True either)
        self.__playback_proc = subprocess.Popen(
            cmd, shell = True, executable = '/usr/bin/bash', start_new_session = False
        )
        self.__is_anything_playing = True

    def __maybe_skip_playback(self):
        if not self.__is_anything_playing:
            return

        should_skip = False
        if self.__playlist_item:
            try:
                # Might result in: `sqlite3.OperationalError: database is locked`, when DB is under load
                should_skip = self.__playlist.should_skip_video_id(self.__playlist_item['playlist_video_id'])
            except Exception as e:
                self.__logger.info(f"Caught exception: {e}.")
        elif self.__is_screensaver_in_progress():
            should_skip = self.__playlist.get_next_playlist_item() is not None

        if should_skip:
            self.__stop_playback_if_playing(was_skipped = True)
            return True

        return False

    def __is_screensaver_in_progress(self):
        return self.__is_anything_playing and self.__playlist_item is None

    def __stop_playback_if_playing(self, was_skipped = False):
        if not self.__is_anything_playing:
            return

        if self.__playback_proc:
            self.__logger.info("Killing playback proc (if it's still running)...")
            was_killed = True
            try:
                os.kill(self.__playback_proc.pid, signal.SIGTERM)
            except Exception:
                # might raise: `ProcessLookupError: [Errno 3] No such process`
                was_killed = False
            exit_status = self.__playback_proc.wait()
            if exit_status != 0:
                if was_killed and abs(exit_status) == signal.SIGTERM:
                    pass # We expect a specific non-zero exit code if the playback was killed.
                else:
                    self.__logger.error(f'Got non-zero exit_status for playback proc: {exit_status}')

        if self.__playlist_item:
            if self.__should_reenqueue_current_playlist_item(was_skipped):
                self.__playlist.reenqueue(self.__playlist_item["playlist_video_id"])
            else:
                self.__playlist.end_video(self.__playlist_item["playlist_video_id"])

        self.__logger.info("Ended playback.")
        Logger.set_uuid('')
        self.__playback_proc = None
        self.__playlist_item = None
        self.__is_anything_playing = False

    """
    Starting a game of snake causes the currently playing video to immediately be skipped. Playing a lot of snake
    games in quick succession could therefore cause the playlist queue to become depleted without the videos even
    having had a chance to play.

    Thus, when we are skipping a video, we check if a snake game is the next item in the queue. If so, we
    reenqueue the video so as not to deplete the queue when a lot of snake games are being played.
    """
    def __should_reenqueue_current_playlist_item(self, was_current_playlist_item_skipped):
        if self.__playlist_item["type"] != Playlist.TYPE_VIDEO:
            return False

        if not was_current_playlist_item_skipped:
            return False

        next_playlist_item = self.__playlist.get_next_playlist_item()
        if next_playlist_item and next_playlist_item["type"] == Playlist.TYPE_GAME:
            return True

        return False

    # returns boolean: __is_game_of_life_enabled
    def __maybe_play_game_of_life(self, is_game_reset_needed):
        # query settings DB no more than once per second. For perf reasons *shrug* (didn't actually measure how expensive it is)
        num_seconds_between_settings_db_queries = 1
        now = time.time()
        if (now - self.__last_settings_db_check_time) > num_seconds_between_settings_db_queries:
            old_is_enabled = self.__is_game_of_life_enabled
            setting = self.__settings_db.get_row(SettingsDb.SCREENSAVER_SETTING)
            if (setting is None or setting['value'] == '1'):
                self.__is_game_of_life_enabled = True
            else:
                self.__is_game_of_life_enabled = False
            seconds_since_setting_updated = 0
            if setting is not None:
                seconds_since_setting_updated = now - Database.database_date_to_unix_time(setting['update_date'])
            if old_is_enabled is not None and old_is_enabled != self.__is_game_of_life_enabled:
                # don't play the sound if they changed the value of the setting a while ago,
                # perhaps while a video was playing
                should_play_sound = seconds_since_setting_updated < (num_seconds_between_settings_db_queries + 2)
                if self.__is_game_of_life_enabled:
                    if should_play_sound:
                        simpleaudio.WaveObject.from_wave_file(
                            DirectoryUtils().root_dir + "/assets/pifi/SFX_HEAL_UP.wav"
                        ).play()
                    is_game_reset_needed = True
                else:
                    if should_play_sound:
                        simpleaudio.WaveObject.from_wave_file(
                            DirectoryUtils().root_dir + "/assets/pifi/SFX_TURN_OFF_PC.wav"
                        ).play()
                    self.__clear_screen()
            self.__last_settings_db_check_time = now

        if self.__is_game_of_life_enabled:
            self.__game_of_life.tick(should_loop = True, force_reset = is_game_reset_needed)
        else:
            if (now - self.__last_screen_clear_while_screensaver_disabled_time) > 1:
                # Clear screen every second while screensaver is disabled
                # See: https://github.com/dasl-/pifi/issues/6
                self.__clear_screen()
                self.__last_screen_clear_while_screensaver_disabled_time = now

        return self.__is_game_of_life_enabled

    def __maybe_respond_to_settings_changes(self):
        pass

    def __clear_screen(self):
        self.__video_player.clear_screen()
