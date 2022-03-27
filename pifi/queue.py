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
from pifi.config import Config
from pifi.games.unixsockethelper import UnixSocketHelper
from pifi.volumecontroller import VolumeController
from pifi.games.snake import Snake
from pifi.settings.settingsdb import SettingsDb
from pifi.settings.snakesettings import SnakeSettings

# The Queue is responsible for playing the next video in the Playlist
class Queue:

    UNIX_SOCKET_PATH = '/tmp/queue_unix_socket'

    def __init__(self):
        self.__playlist = Playlist()
        self.__settings_db = SettingsDb()
        self.__config = Config()
        self.__is_game_of_life_enabled = None
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
            self.__maybe_respond_to_settings_changes()
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
            time.sleep(0.050)

    def __play_playlist_item(self, playlist_item):
        log_uuid = Logger.make_uuid()
        Logger.set_uuid(log_uuid)

        cmd = None
        pass_fds = ()
        if playlist_item["type"] == Playlist.TYPE_VIDEO:
            if not self.__playlist.set_current_video(playlist_item["playlist_video_id"]):
                # Someone deleted the item from the queue in between getting the item and starting it.
                return
            cmd = (f"{DirectoryUtils().root_dir}/bin/play_video --url {shlex.quote(playlist_item['url'])} " +
                f"--color-mode {shlex.quote(playlist_item['color_mode'])}")
        elif playlist_item["type"] == Playlist.TYPE_GAME:
            if playlist_item["title"] == Snake.GAME_TITLE:
                snake_settings = SnakeSettings().from_playlist_item_in_queue(playlist_item)
                is_waiting_for_players = False
                if snake_settings.num_players > 1:
                    is_waiting_for_players = True
                if not self.__playlist.set_current_video(playlist_item["playlist_video_id"], is_waiting_for_players):
                    # Someone deleted the item from the queue in between getting the item and starting it.
                    return
                unix_socket_fd = self.__unix_socket.fileno()
                cmd = (f"{DirectoryUtils().root_dir}/bin/snake " +
                    f"--playlist-video-id {shlex.quote(str(playlist_item['playlist_video_id']))} " +
                    f"--server-unix-socket-fd {shlex.quote(str(unix_socket_fd))}")
                pass_fds = (unix_socket_fd,)
            else:
                self.__logger.error(f"Invalid game title: {playlist_item['title']}")
        else:
            self.__logger.error(f"Invalid playlist_item type: {playlist_item['type']}")

        if (cmd):
            self.__start_playback(cmd, log_uuid, pass_fds)
            self.__playlist_item = playlist_item
        else:
            Logger.set_uuid('')

    def __maybe_play_screensaver(self):
        if not self.__is_game_of_life_enabled:
            return
        log_uuid = 'SCREENSAVER__' + Logger.make_uuid()
        Logger.set_uuid(log_uuid)
        self.__logger.info("Starting game of life screensaver...")
        cmd = f"{DirectoryUtils().root_dir}/bin/game_of_life --loop"
        self.__start_playback(cmd, log_uuid)

    # Play something, whether it's a screensaver (game of life), a video, or a game (snake)
    def __start_playback(self, cmd, log_uuid, pass_fds = ()):
        cmd += f' --log-uuid {shlex.quote(log_uuid)}'
        self.__logger.debug(f"Starting playback with cmd: {cmd}.")
        # Using start_new_session = False here because it is not necessary to start a new session here (though
        # it should not hurt if we were to set it to True either)
        self.__playback_proc = subprocess.Popen(
            cmd, shell = True, executable = '/usr/bin/bash', start_new_session = False, pass_fds = pass_fds
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
        elif self.__is_screensaver_playing():
            should_skip = self.__playlist.get_next_playlist_item() is not None

        if should_skip:
            self.__stop_playback_if_playing(was_skipped = True)
            return True

        return False

    def __is_screensaver_playing(self):
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

        self.__clear_screen()

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

    def __maybe_respond_to_settings_changes(self):
        old_is_enabled = self.__is_game_of_life_enabled
        setting = self.__settings_db.get_row(SettingsDb.SCREENSAVER_SETTING)
        if (setting is None or setting['value'] == '1'):
            self.__is_game_of_life_enabled = True
        else:
            self.__is_game_of_life_enabled = False

        if old_is_enabled is not None and old_is_enabled != self.__is_game_of_life_enabled:
            should_play_sound = not self.__is_anything_playing or self.__is_screensaver_playing()
            if self.__is_game_of_life_enabled:
                if should_play_sound:
                    simpleaudio.WaveObject.from_wave_file(
                        DirectoryUtils().root_dir + "/assets/pifi/SFX_HEAL_UP.wav"
                    ).play()
            else:
                if should_play_sound:
                    simpleaudio.WaveObject.from_wave_file(
                        DirectoryUtils().root_dir + "/assets/pifi/SFX_TURN_OFF_PC.wav"
                    ).play()
                if self.__is_screensaver_playing():
                    self.__stop_playback_if_playing()

        if not self.__is_anything_playing:
            now = time.time()
            if (now - self.__last_screen_clear_while_screensaver_disabled_time) > 1:
                # Clear screen every second while screensaver is disabled
                # See: https://github.com/dasl-/pifi/issues/6
                self.__clear_screen()
                self.__last_screen_clear_while_screensaver_disabled_time = now

        return self.__is_game_of_life_enabled

    def __clear_screen(self):
        self.__video_player.clear_screen()
