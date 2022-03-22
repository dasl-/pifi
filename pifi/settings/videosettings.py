from pifi.config import Config
from pifi.settings.ledsettings import LedSettings

class VideoSettings(LedSettings):

    # should_play_audio: boolean
    # should_save_video: boolean - saving the video allows us to avoid youtube-dl network calls to download the video
    #   if it's played again.
    # should_check_playlist: boolean - if True, the videoprocessor will periodically check the DB to see if it should
    #   skip playing the current video.
    # should_predownload_video: boolean - force the video to fully download before playing
    def __init__(
        self, color_mode = None, display_width = None, display_height = None,
        brightness = None, flip_x = False, flip_y = False, log_level = None,
        should_play_audio = True, should_save_video = False, should_check_playlist = False,
        should_predownload_video = False,
    ):
        super().__init__(
            color_mode, display_width, display_height, brightness, flip_x, flip_y, log_level
        )
        self.should_play_audio = should_play_audio
        self.should_save_video = should_save_video
        self.should_check_playlist = should_check_playlist
        self.should_predownload_video = should_predownload_video

    def from_config(self):
        super().from_config()

        config = self.get_values_from_config()
        if 'color_mode' in config:
            self.set_color_mode(config['color_mode'])
        if 'should_play_audio' in config:
            self.should_play_audio = config['should_play_audio']
        if 'should_save_video' in config:
            self.should_save_video = config['should_save_video']
        if 'should_predownload_video' in config:
            self.should_predownload_video = config['should_predownload_video']

        return self

    def from_playlist_item_in_queue(self, video_record = None):
        self.should_check_playlist = True
        if video_record:
            self.set_color_mode(video_record["color_mode"])
        return self.from_config()

    def get_values_from_config(self):
        return Config().get_video_settings()
