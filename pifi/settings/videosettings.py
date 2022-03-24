from pifi.config import Config
from pifi.settings.ledsettings import LedSettings

class VideoSettings(LedSettings):

    # should_play_audio: boolean
    # should_save_video: boolean - saving the video allows us to avoid youtube-dl network calls to download the video
    #   if it's played again.
    # should_predownload_video: boolean - force the video to fully download before playing
    def __init__(
        self, color_mode = None, display_width = None, display_height = None,
        brightness = None, flip_x = False, flip_y = False,
        should_play_audio = True, should_save_video = False,
        should_predownload_video = False,
    ):
        super().__init__(
            color_mode, display_width, display_height, brightness, flip_x, flip_y
        )
        self.should_play_audio = should_play_audio
        self.should_save_video = should_save_video
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

    def get_values_from_config(self):
        return Config().get_video_settings()
