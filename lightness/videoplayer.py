import numpy as np
import math
import time
from driver import apa102
from lightness.gamma import Gamma
from lightness.settings.ledsettings import LedSettings

class VideoPlayer:
    __led_settings = None

    __gamma_controller = None
    __pixels = None

    #LED Settings
    __MOSI_PIN = 10
    __SCLK_PIN = 11
    __LED_ORDER = 'rbg'

    # static gamma curve
    __scale_red_gamma_curve = None
    __scale_green_gamma_curve = None
    __scale_blue_gamma_curve = None

    # dynamic gamma curves
    __scale_red_gamma_curves = None
    __scale_green_gamma_curves = None
    __scale_blue_gamma_curves = None

    __current_frame = None

    __FADE_STEPS = 5

    def __init__(self, led_settings):
        self.__led_settings = led_settings
        self.__gamma_controller = Gamma(self.__led_settings)

        # Memoizing the specific gamma curve index for static gamma videos enables us to shave
        # 1 or 2 milliseconds off the loop per frame. See: self.__set_frame_pixels
        if self.__led_settings.is_color_mode_rgb():
            # static gamma
            self.__scale_red_gamma_curve = self.__gamma_controller.scale_red_curves[Gamma.DEFAULT_GAMMA_INDEX]
            self.__scale_green_gamma_curve = self.__gamma_controller.scale_green_curves[Gamma.DEFAULT_GAMMA_INDEX]
            self.__scale_blue_gamma_curve = self.__gamma_controller.scale_blue_curves[Gamma.DEFAULT_GAMMA_INDEX]
        else:
            # dynamic gamma
            self.__scale_red_gamma_curves = self.__gamma_controller.scale_red_curves
            self.__scale_green_gamma_curves = self.__gamma_controller.scale_green_curves
            self.__scale_blue_gamma_curves = self.__gamma_controller.scale_blue_curves
        self.__setup_pixels()

    def clear_screen(self):
        self.__pixels.clear_strip();

    def play_frame(self, avg_color_frame):
        self.__set_frame_pixels(avg_color_frame)
        self.__pixels.show()

    def fade_to_frame(self, avg_color_frame):
        if (self.__current_frame is None):
            self.__current_frame = avg_color_frame
            return self.play_frame(avg_color_frame)

        frame_steps = np.zeros([self.__led_settings.display_height, self.__led_settings.display_width, 3], np.int8)

        for x in range(self.__led_settings.display_width):
            for y in range(self.__led_settings.display_height):
                for rgb in range(0,3):
                    frame_steps[y, x, rgb] = ((avg_color_frame[y, x, rgb].astype(np.int16) - self.__current_frame[y, x, rgb].astype(np.int16)) / self.__FADE_STEPS).astype(np.int8)

        for current_step in range(1, self.__FADE_STEPS):
            new_frame = np.zeros([self.__led_settings.display_height, self.__led_settings.display_width, 3], np.uint8)
            for x in range(self.__led_settings.display_width):
                for y in range(self.__led_settings.display_height):
                    for rgb in range(0,3):
                        new_frame[y, x, rgb] = self.__current_frame[y, x, rgb] + (frame_steps[y, x, rgb] * current_step)

            # no need to sleep since the above calculation takes some small amount of time
            self.__set_frame_pixels(new_frame)
            self.__pixels.show()

        self.__current_frame = avg_color_frame
        self.__set_frame_pixels(avg_color_frame)
        self.__pixels.show()

    def __setup_pixels(self):
        # Add 8 because otherwise the last 8 LEDs don't powered correctly. Weird driver glitch?
        self.__pixels = apa102.APA102(
            num_led=(self.__led_settings.display_width * self.__led_settings.display_height + 8),
            global_brightness=self.__led_settings.brightness,
            mosi=self.__MOSI_PIN,
            sclk=self.__SCLK_PIN,
            order=self.__LED_ORDER
        )
        self.__pixels.clear_strip()
        return self.__pixels

    # CAUTION:
    # This method has been heavily optimized. The program spends the bulk of its execution time in this loop.
    # If making any changes, profile your code first to see if there are regressions, i.e.:
    #
    #   python3 -m cProfile -s cumtime video --url https://www.youtube.com/watch?v=AxuvUAjHYWQ --color-mode color
    #
    # In the nested for loop, function calls are to be avoided. Inlining them is more performant.
    #
    # See: https://github.com/dasl-/lightness/commit/9640268084acb0c46b2624178f350017ab666d41
    def __set_frame_pixels(self, avg_color_frame):
        if not (self.__led_settings.is_color_mode_rgb()):
            gamma_index = self.__gamma_controller.getGammaIndexForMonochromeFrame(avg_color_frame)

        for x in range(self.__led_settings.display_width):
            for y in range(self.__led_settings.display_height):
                # calculate gamma corrected colors
                if self.__led_settings.color_mode == LedSettings.COLOR_MODE_COLOR:
                    r, g, b = [
                        self.__scale_red_gamma_curve[avg_color_frame[y, x, 0]],
                        self.__scale_green_gamma_curve[avg_color_frame[y, x, 1]],
                        self.__scale_blue_gamma_curve[avg_color_frame[y, x, 2]]
                    ]
                elif self.__led_settings.color_mode == LedSettings.COLOR_MODE_R:
                    r = self.__scale_red_gamma_curves[gamma_index][avg_color_frame[y, x]]
                    g, b = [0, 0]
                elif self.__led_settings.color_mode == LedSettings.COLOR_MODE_G:
                    g = self.__scale_green_gamma_curves[gamma_index][avg_color_frame[y, x]]
                    r, b = [0, 0]
                elif self.__led_settings.color_mode == LedSettings.COLOR_MODE_B:
                    b = self.__scale_blue_gamma_curves[gamma_index][avg_color_frame[y, x]]
                    r, g = [0, 0]
                elif self.__led_settings.color_mode == LedSettings.COLOR_MODE_BW:
                    r, g, b = [
                        self.__scale_red_gamma_curves[gamma_index][avg_color_frame[y, x]],
                        self.__scale_green_gamma_curves[gamma_index][avg_color_frame[y, x]],
                        self.__scale_blue_gamma_curves[gamma_index][avg_color_frame[y, x]]
                    ]
                elif self.__led_settings.color_mode == LedSettings.COLOR_MODE_INVERT_COLOR:
                    r, g, b = [
                        self.__scale_red_gamma_curve[255 - avg_color_frame[y, x, 0]],
                        self.__scale_green_gamma_curve[255 - avg_color_frame[y, x, 1]],
                        self.__scale_blue_gamma_curve[255 - avg_color_frame[y, x, 2]]
                    ]
                elif self.__led_settings.color_mode == LedSettings.COLOR_MODE_INVERT_BW:
                    r, g, b = [
                        self.__scale_red_gamma_curves[gamma_index][255 - avg_color_frame[y, x]],
                        self.__scale_green_gamma_curves[gamma_index][255 - avg_color_frame[y, x]],
                        self.__scale_blue_gamma_curves[gamma_index][255 - avg_color_frame[y, x]]
                    ]
                else:
                    raise Exception('Unexpected color mode: {}'.format(self.__led_settings.color_mode))

                # set pixel
                if (self.__led_settings.flip_x):
                    x = self.__led_settings.display_width - x - 1
                if (self.__led_settings.flip_y):
                    y = self.__led_settings.display_height - y - 1

                # each row is zig-zagged, so every other row needs to be flipped horizontally
                if (y % 2 == 0):
                    pixel_index = (y * self.__led_settings.display_width) + (self.__led_settings.display_width - x - 1)
                else:
                    pixel_index = (y * self.__led_settings.display_width) + x

                # order on the strip is RBG (refer to self.__LED_ORDER)
                self.__pixels.set_pixel(pixel_index, r, b, g)
