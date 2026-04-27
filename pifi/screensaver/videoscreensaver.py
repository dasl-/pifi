import os
import random
from pifi.config import Config
from pifi.directoryutils import DirectoryUtils
from pifi.video.videoprocessor import VideoProcessor
from pifi.screensaver.screensaver import Screensaver

class VideoScreensaver(Screensaver):

    __DATA_DIRECTORY = 'data/screensavers'

    def __init__(self, led_frame_player=None):
        super().__init__(led_frame_player)
        # Get video list from config instead of constructor parameter
        self.video_list = Config.get("screensavers.configs.video_screensaver.saved_videos", [])

    def __getScreensaverPath(self):
        save_dir = DirectoryUtils().root_dir + '/' + self.__DATA_DIRECTORY  # pyright: ignore[reportOptionalOperand]
        os.makedirs(save_dir, exist_ok=True)
        return save_dir

    def _tick(self):  # pyright: ignore[reportIncompatibleMethodOverride]
        if not self.video_list:
            return False

        # Note: process_and_play() is a blocking call that plays the entire video.
        # The base class timeout check only runs between ticks, so timeout is
        # effectively governed by video length, not the configured timeout.
        url = self.__getScreensaverPath() + '/' + random.choice(self.video_list)
        VideoProcessor(
            url = url,
            clear_screen = True,
            show_loading_screen = False,
            led_frame_player = self._led_frame_player
        ).process_and_play()

    @classmethod
    def get_id(cls) -> str:
        return 'video_screensaver'

    @classmethod
    def get_name(cls) -> str:
        return 'Video Screensaver'

    @classmethod
    def get_description(cls) -> str:
        return 'Plays saved video files from the data/screensavers directory.'

    def supports_live_transition(self) -> bool:
        return False
