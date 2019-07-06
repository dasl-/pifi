import math
import time
from driver import apa102
from lightness.gamma import Gamma
from lightness.settings import Settings

class VideoPlayer:
    __video_settings = None

    __gamma_controller = None
    __pixels = None

    #LED Settings
    __MOSI_PIN = 10
    __SCLK_PIN = 11
    __LED_ORDER = 'rbg'

    def __init__(self, video_settings):
        self.__video_settings = video_settings
        self.__gamma_controller = Gamma(self.__video_settings)
        self.__setupPixels()

    def clearScreen(self):
        self.__pixels.clear_strip();

    def playFrame(self, avg_color_frame):
        self.__setFramePixels(avg_color_frame)
        self.__pixels.show()

    def __setupPixels(self):
        # Add 8 because otherwise the last 8 LEDs don't powered correctly. Weird driver glitch?
        self.__pixels = apa102.APA102(
            num_led=(self.__video_settings.display_width * self.__video_settings.display_height + 8),
            global_brightness=self.__video_settings.brightness,
            mosi=self.__MOSI_PIN,
            sclk=self.__SCLK_PIN,
            order=self.__LED_ORDER
        )
        self.__pixels.clear_strip()
        return self.__pixels

    def __setFramePixels(self, avg_color_frame):
        if not self.__video_settings.color_mode == Settings.COLOR_MODE_COLOR:
            self.__gamma_controller.setGammaIndexForMonochromeFrame(avg_color_frame)

        for x in range(self.__video_settings.display_width):
            for y in range(self.__video_settings.display_height):
                if self.__video_settings.color_mode == Settings.COLOR_MODE_COLOR:
                    r, g, b = self.__gamma_controller.getScaledRGBOutputForColorPixel(avg_color_frame[y, x])
                elif self.__video_settings.color_mode == Settings.COLOR_MODE_R:
                    r = self.__gamma_controller.getScaledOutputForBrightnessAndColor(avg_color_frame[y, x], 'r')
                    g, b = [0, 0]
                elif self.__video_settings.color_mode == Settings.COLOR_MODE_G:
                    g = self.__gamma_controller.getScaledOutputForBrightnessAndColor(avg_color_frame[y, x], 'g')
                    r, b = [0, 0]
                elif self.__video_settings.color_mode == Settings.COLOR_MODE_B:
                    b = self.__gamma_controller.getScaledOutputForBrightnessAndColor(avg_color_frame[y, x], 'b')
                    r, g = [0, 0]
                elif self.__video_settings.color_mode == Settings.COLOR_MODE_BW:
                    r, g, b = self.__gamma_controller.getScaledRGBOutputForBlackAndWhitePixel(avg_color_frame[y, x])
                else:
                    raise Exception('Unexpected color mode: {}'.format(self.__video_settings.color_mode))

                self.__setPixel(x, y, r, g, b)

    def __setPixel(self, x, y, r, g, b):
        if (self.__video_settings.flip_x):
            x = self.__video_settings.display_width - x - 1
        if (self.__video_settings.flip_y):
            y = self.__video_settings.display_height - y - 1

        # each row is zig-zagged, so every other row needs to be flipped horizontally
        if (y % 2 == 0):
            pixel_index = (y * self.__video_settings.display_width) + (self.__video_settings.display_width - x - 1)
        else:
            pixel_index = (y * self.__video_settings.display_width) + x

        # order on the strip is RBG (refer to self.__LED_ORDER)
        self.__pixels.set_pixel(pixel_index, r, b, g)
