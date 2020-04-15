from pifi.settings.ledsettings import LedSettings

class VideoSettings(LedSettings):

    # Boolean
    should_play_audio = None

    # Boolean - saving the video allows us to avoid youtube-dl network calls to download the video if it's played again.
    should_save_video = None

    # If True, the videoprocessor will periodically check the DB to see if it should skip playing the current video
    should_check_playlist = None

    # Boolean - force the video to fully download before playing
    should_predownload_video = None

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
