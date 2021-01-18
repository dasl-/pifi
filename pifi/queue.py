import time
import traceback
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
from pifi.games.unixsockethelper import UnixSocketHelper
from pifi.volumecontroller import VolumeController
from pifi.games.snake import Snake
from pifi.settings.snakesettings import SnakeSettings

# The Queue is responsible for playing the next video in the Playlist
class Queue:

    UNIX_SOCKET_PATH = '/tmp/queue_unix_socket'

    __playlist = None
    __config = None
    __logger = None
    __should_play_game_of_life = None
    __unix_socket = None

    def __init__(self):
        self.__playlist = Playlist()
        self.__config = Config()
        self.__should_play_game_of_life = self.__config.get_queue_config('should_play_game_of_life', True)
        self.__logger = Logger().set_namespace(self.__class__.__name__)
        self.__unix_socket = UnixSocketHelper().create_server_unix_socket(self.UNIX_SOCKET_PATH)

        # house keeping
        self.__clear_screen()
        (VolumeController()).set_vol_pct(50)
        self.__playlist.clean_up_state()

    def run(self):
        if self.__should_play_game_of_life:
            game_of_life = GameOfLife(GameOfLifeSettings().from_config())
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
                status2 = Playlist.STATUS2_PLAYING
                if snake_settings.num_players > 1:
                    status2 = Playlist.STATUS2_WAITING_FOR_PLAYERS
                if not self.__playlist.set_current_video(playlist_item["playlist_video_id"], status2):
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

        self.__playlist.end_video(playlist_item["playlist_video_id"])
        if exception_to_raise is not None:
            raise exception_to_raise

    def __clear_screen(self):
        # VideoPlayer.__init__() method will clear the screen
        VideoPlayer(VideoSettings().from_playlist_item_in_queue())
