import math
import time
from driver import apa102
from lightness.gamma import Gamma
from lightness.videosettings import VideoSettings

class VideoPlayer:
    __video_settings = None

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

    def __init__(self, video_settings):
        self.__video_settings = video_settings
        self.__gamma_controller = Gamma(self.__video_settings)

        # Memoizing the specific gamma curve index for static gamma videos enables us to shave
        # 1 or 2 milliseconds off the loop per frame. See: self.__setFramePixels
        if self.__video_settings.is_color_mode_rgb():
            # static gamma
            self.__scale_red_gamma_curve = self.__gamma_controller.scale_red_curves[Gamma.DEFAULT_GAMMA_INDEX]
            self.__scale_green_gamma_curve = self.__gamma_controller.scale_green_curves[Gamma.DEFAULT_GAMMA_INDEX]
            self.__scale_blue_gamma_curve = self.__gamma_controller.scale_blue_curves[Gamma.DEFAULT_GAMMA_INDEX]
        else:
            # dynamic gamma
            self.__scale_red_gamma_curves = self.__gamma_controller.scale_red_curves
            self.__scale_green_gamma_curves = self.__gamma_controller.scale_green_curves
            self.__scale_blue_gamma_curves = self.__gamma_controller.scale_blue_curves
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

    # CAUTION:
    # This method has been heavily optimized. The program spends the bulk of its execution time in this loop.
    # If making any changes, profile your code first to see if there are regressions, i.e.:
    #
    #   python3 -m cProfile -s cumtime video --url https://www.youtube.com/watch?v=AxuvUAjHYWQ --color-mode color
    #
    # In the nested for loop, function calls are to be avoided. Inlining them is more performant.
    #
    # See: https://github.com/dasl-/lightness/commit/9640268084acb0c46b2624178f350017ab666d41
    def __setFramePixels(self, avg_color_frame):
        if not (self.__video_settings.is_color_mode_rgb()):
            gamma_index = self.__gamma_controller.getGammaIndexForMonochromeFrame(avg_color_frame)

        for x in range(self.__video_settings.display_width):
            for y in range(self.__video_settings.display_height):
                # calculate gamma corrected colors
                if self.__video_settings.color_mode == VideoSettings.COLOR_MODE_COLOR:
                    r, g, b = [
                        self.__scale_red_gamma_curve[avg_color_frame[y, x, 0]],
                        self.__scale_green_gamma_curve[avg_color_frame[y, x, 1]],
                        self.__scale_blue_gamma_curve[avg_color_frame[y, x, 2]]
                    ]
                elif self.__video_settings.color_mode == VideoSettings.COLOR_MODE_R:
                    r = self.__scale_red_gamma_curves[gamma_index][avg_color_frame[y, x]]
                    g, b = [0, 0]
                elif self.__video_settings.color_mode == VideoSettings.COLOR_MODE_G:
                    g = self.__scale_green_gamma_curves[gamma_index][avg_color_frame[y, x]]
                    r, b = [0, 0]
                elif self.__video_settings.color_mode == VideoSettings.COLOR_MODE_B:
                    b = self.__scale_blue_gamma_curves[gamma_index][avg_color_frame[y, x]]
                    r, g = [0, 0]
                elif self.__video_settings.color_mode == VideoSettings.COLOR_MODE_BW:
                    r, g, b = [
                        self.__scale_red_gamma_curves[gamma_index][avg_color_frame[y, x]],
                        self.__scale_green_gamma_curves[gamma_index][avg_color_frame[y, x]],
                        self.__scale_blue_gamma_curves[gamma_index][avg_color_frame[y, x]]
                    ]
                elif self.__video_settings.color_mode == VideoSettings.COLOR_MODE_INVERT_COLOR:
                    r, g, b = [
                        self.__scale_red_gamma_curve[255 - avg_color_frame[y, x, 0]],
                        self.__scale_green_gamma_curve[255 - avg_color_frame[y, x, 1]],
                        self.__scale_blue_gamma_curve[255 - avg_color_frame[y, x, 2]]
                    ]
                elif self.__video_settings.color_mode == VideoSettings.COLOR_MODE_INVERT_BW:
                    r, g, b = [
                        self.__scale_red_gamma_curves[gamma_index][255 - avg_color_frame[y, x]],
                        self.__scale_green_gamma_curves[gamma_index][255 - avg_color_frame[y, x]],
                        self.__scale_blue_gamma_curves[gamma_index][255 - avg_color_frame[y, x]]
                    ]
                else:
                    raise Exception('Unexpected color mode: {}'.format(self.__video_settings.color_mode))

                # set pixel
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
