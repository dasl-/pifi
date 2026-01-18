import os
import random
from pifi.config import Config
from pifi.directoryutils import DirectoryUtils
from pifi.video.videoprocessor import VideoProcessor
from pifi.screensaver.screensaver import Screensaver

class VideoScreensaver(Screensaver):

    __DATA_DIRECTORY = 'data/screensavers'

    def __init__(self, led_frame_player=None):
        # Get video list from config instead of constructor parameter
        self.video_list = Config.get("screensavers.saved_videos", [])

    def __getScreensaverPath(self):
        save_dir = DirectoryUtils().root_dir + '/' + self.__DATA_DIRECTORY
        os.makedirs(save_dir, exist_ok=True)
        return save_dir

    def play(self):
        url = self.__getScreensaverPath() + '/' + random.choice(self.video_list)
        VideoProcessor(
            url = url,
            clear_screen = True,
            show_loading_screen = False
        ).process_and_play()

    @classmethod
    def get_id(cls) -> str:
        return 'video_screensaver'

    @classmethod
    def get_name(cls) -> str:
        return 'Video Screensaver'

    @classmethod
    def get_description(cls) -> str:
        return 'Saved video playback'
