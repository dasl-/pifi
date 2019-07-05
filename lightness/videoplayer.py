import math
import time
from driver import apa102
from lightness.gamma import Gamma

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
        self.gamma_controller = Gamma(video_settings)
        self.setupPixels()

    def clearScreen(self):
        self.pixels.clear_strip();

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

    def __setFramePixels(self, avg_color_frame):
        if not self.video_settings.is_color:
            self.gamma_controller.setGammaIndexForFrame(avg_color_frame)

        for x in range(self.video_settings.display_width):
            for y in range(self.video_settings.display_height):
                if self.video_settings.is_color:
                    r, g, b = self.gamma_controller.getScaledRGBOutputForColorFrame(avg_color_frame, x, y)
                elif self.video_settings.red_mode:
                    r, g, b = self.gamma_controller.getScaledRGBOutputForBlackAndWhiteFrame(avg_color_frame, x, y)
                    g, b = [0, 0]
                elif self.video_settings.green_mode:
                    r, g, b = self.gamma_controller.getScaledRGBOutputForBlackAndWhiteFrame(avg_color_frame, x, y)
                    r, b = [0, 0]
                elif self.video_settings.blue_mode:
                    r, g, b = self.gamma_controller.getScaledRGBOutputForBlackAndWhiteFrame(avg_color_frame, x, y)
                    r, g = [0, 0]
                else:
                    r, g, b = self.gamma_controller.getScaledRGBOutputForBlackAndWhiteFrame(avg_color_frame, x, y)

                # order on the strip is RBG (refer to LED_ORDER)
                color = self.pixels.combine_color(r, b, g)
                self.setPixel(x, y, color)

    def setPixel(self, x, y, color):
        if (self.video_settings.flip_x):
            x = self.video_settings.display_width - x - 1
        if (self.video_settings.flip_y):
            y = self.video_settings.display_height - y - 1

        # each row is zig-zagged, so every other row needs to be flipped horizontally
        if (y % 2 == 0):
            pixel_index = (y * self.video_settings.display_width) + (self.video_settings.display_width - x - 1)
        else:
            pixel_index = (y * self.video_settings.display_width) + x

        self.pixels.set_pixel_rgb(pixel_index, color)

    def playFrame(self, avg_color_frame):
        self.__setFramePixels(avg_color_frame)
        self.pixels.show()
