import time
import traceback
import simpleaudio
from pifi.directoryutils import DirectoryUtils
from pifi.playlist import Playlist
from pifi.logger import Logger
from pifi.settings.videosettings import VideoSettings
from pifi.settings.gameoflifesettings import GameOfLifeSettings
from pifi.videoplayer import VideoPlayer
from pifi.videoprocessor import VideoProcessor
from pifi.config import Config
from pifi.games.gameoflife import GameOfLife
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
        self.__game_of_life = GameOfLife(GameOfLifeSettings().from_config())
        self.__is_game_of_life_enabled = None
        self.__last_settings_db_check_time = 0
        self.__last_screen_clear_while_screensaver_disabled_time = 0
        self.__logger = Logger().set_namespace(self.__class__.__name__)
        self.__unix_socket = UnixSocketHelper().create_server_unix_socket(self.UNIX_SOCKET_PATH)
        self.__video_player = VideoPlayer(VideoSettings().from_playlist_item_in_queue())

        # house keeping
        self.__clear_screen()
        (VolumeController()).set_vol_pct(50)
        self.__playlist.clean_up_state()

    def run(self):
        is_game_reset_needed = False
        while True:
            next_item = self.__playlist.get_next_playlist_item()
            if next_item:
                if next_item["type"] == Playlist.TYPE_VIDEO or next_item["type"] == Playlist.TYPE_GAME:
                    self.__play_playlist_item(next_item)
                    is_game_reset_needed = True
                else:
                    raise Exception("Invalid playlist_item type: {}".format(next_item["type"]))
            if not self.__maybe_play_game_of_life(is_game_reset_needed):
                # don't sleep if we're playing GoL (let GoL run as fast as possible).
                time.sleep(0.050)
            is_game_reset_needed = False

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

    """
    Starting a game causes the currently playing video to immediately be skipped. Playing a lot of games in quick
    succession could therefore cause the playlist queue to become depleted without the videos even having had a
    chance to play.

    Thus, when we are skipping a video, we check if a game is the next item in the queue. If so, we reenqueue the
    video so as not to deplete the queue when a lot of games are being played.
    """
    def __reenqueue_or_end_playlist_item(self, current_playlist_item, force_end):
        if force_end or current_playlist_item["type"] != Playlist.TYPE_VIDEO:
            pass
        else: # The current playlist item is a video
            next_playlist_item = self.__playlist.get_next_playlist_item()
            if next_playlist_item and next_playlist_item["type"] == Playlist.TYPE_GAME:
                # Check if the current playlist item was actually skipped -- need to reload it from the DB to get the
                # latest state.
                current_playlist_item = self.__playlist.get_playlist_item_by_id(current_playlist_item['playlist_video_id'])
                if current_playlist_item['is_skip_requested']:
                    self.__logger.debug("Re-enqueuing current video because it was skipped due " +
                        "to a game")
                    self.__playlist.reenqueue(current_playlist_item['playlist_video_id'])
                    return

        self.__playlist.end_video(current_playlist_item["playlist_video_id"])

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

    def __clear_screen(self):
        self.__video_player.clear_screen()
