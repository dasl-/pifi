import os
import random
from pifi.config import Config
from pifi.directoryutils import DirectoryUtils
from pifi.video.videoprocessor import VideoProcessor

class VideoScreensaver:

    __DATA_DIRECTORY = 'data/screensavers'

    def __init__(self):
        # Videos must be set in the Config to be playable
        saved_videos = Config.get("screensavers.saved_videos")
        self.video_name = None
        if saved_videos is not None:
            self.video_name = random.choice(saved_videos)

    def __getScreensaverPath(self):
        save_dir = DirectoryUtils().root_dir + '/' + self.__DATA_DIRECTORY
        os.makedirs(save_dir, exist_ok=True)
        return save_dir

    def play(self):
        if self.video_name is not None:
            url = self.__getScreensaverPath() + '/' + self.video_name
            VideoProcessor(
                url=url,
                clear_screen=True,
                yt_dlp_extractors="",
                show_loading_screen=False
            ).process_and_play()
