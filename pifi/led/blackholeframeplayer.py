from pifi.led.frameplayerbase import FramePlayerBase


class BlackHoleFramePlayer(FramePlayerBase):
    """Frame player that captures frames without displaying them.

    Used internally by Screensaver.render_tick() to intercept frames
    that a screensaver renders via self._led_frame_player, without
    sending them to LED hardware.
    """

    def __init__(self):
        self.__current_frame = None

    def play_frame(self, frame):
        self.__current_frame = frame.copy()

    def get_current_frame(self):
        if self.__current_frame is None:
            return None
        return self.__current_frame.copy()

    def fade_to_frame(self, frame):
        """Skip the fade animation and just capture the target frame."""
        self.__current_frame = frame.copy()
