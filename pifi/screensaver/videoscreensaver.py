import os
import random
from pifi.config import Config
from pifi.directoryutils import DirectoryUtils
from pifi.video.videoprocessor import VideoProcessor

class VideoScreensaver:

    __DATA_DIRECTORY = 'data/screensavers'

    def __init__(self, video_list):
        self.video_list = video_list

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
