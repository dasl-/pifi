import math
import time
from driver import apa102

#local libraries
import gamma

class VideoPlayer:
    video_settings = None

    gamma_controller = None
    pixels = None

    #LED Settings
    MOSI_PIN = 10
    SCLK_PIN = 11
    LED_ORDER = 'rbg'

    def __init__(self, video_settings):
        self.video_settings = video_settings
        self.gamma_controller = gamma.Gamma(video_settings)
        self.setupPixels()

    def setupPixels(self):
        # Add 8 because otherwise the last 8 LEDs don't powered correctly. Weird driver glitch?
        self.pixels = apa102.APA102(
            num_led=(self.video_settings.display_width * self.video_settings.display_height + 8),
            global_brightness=self.video_settings.brightness,
            mosi=self.MOSI_PIN,
            sclk=self.SCLK_PIN,
            order=self.LED_ORDER
        )
        self.pixels.clear_strip()
        return self.pixels

    def setFramePixelsColor(self, avg_color_frame):
        for x in range(self.video_settings.display_width):
            for y in range(self.video_settings.display_height):
                r, g, b = self.gamma_controller.getScaledRGBOutputForColorFrame(avg_color_frame, x, y)
                color = self.pixels.combine_color(r, b, g)
                self.setPixel(x, y, color)

    def setFramePixelsBlackAndWhite(self, avg_color_frame):
        gamma_index = self.gamma_controller.setGammaIndexForFrame(avg_color_frame)

        for x in range(self.video_settings.display_width):
            for y in range(self.video_settings.display_height):
                r, g, b = self.gamma_controller.getScaledRGBOutputForBlackAndWhiteFrame(avg_color_frame, x, y)
                color = self.pixels.combine_color(r, b, g)
                self.setPixel(x, y, color)

    def setPixel(self, x, y, color):
        # each row is zig-zagged, so every other row needs to be flippe horizontally
        if (y % 2 == 0):
            pixel_index = (y * self.video_settings.display_width) + (self.video_settings.display_width - x - 1)
        else:
            pixel_index = (y * self.video_settings.display_width) + x

        self.pixels.set_pixel_rgb(pixel_index, color)

    def playVideo(self, avg_color_frames, fps):
        start_time = time.time()
        frame_length = (1/fps)
        last_frame = None

        while (True):
            try:
                cur_frame = math.ceil((time.time() - start_time) / frame_length)
                if (cur_frame >= len(avg_color_frames)):
                    break

                if cur_frame != last_frame:
                    self.playFrame(avg_color_frames[cur_frame])
                    last_frame = cur_frame

            except KeyboardInterrupt:
                pause_time = time.time()

                while (True):
                    in_key = input("type ' ' to unpause...")

                    if in_key == ' ':
                        # unpause
                        start_time = start_time + (time.time() - pause_time)
                        break
                    else:
                        # wait for next key pres
                        continue

    def playFrame(self, avg_color_frame):
        if self.video_settings.is_color:
            self.setFramePixelsColor(avg_color_frame)
        else:
            self.setFramePixelsBlackAndWhite(avg_color_frame)

        self.pixels.show()
