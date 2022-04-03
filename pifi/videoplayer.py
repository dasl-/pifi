import numpy as np
from pifi.driver import APA102Driver, RGBMatrixDriver
from pifi.directoryutils import DirectoryUtils
from pifi.gamma import Gamma
from pifi.settings.ledsettings import LedSettings

class VideoPlayer:
    __FADE_STEPS = 5

    def __init__(self, led_settings, clear_screen = True):
        self.__led_settings = led_settings
        self.__current_frame = None
        self.__gamma_controller = Gamma(self.__led_settings)

        # static gamma curve
        self.__scale_red_gamma_curve = None
        self.__scale_green_gamma_curve = None
        self.__scale_blue_gamma_curve = None

        # dynamic gamma curves
        self.__scale_red_gamma_curves = None
        self.__scale_green_gamma_curves = None
        self.__scale_blue_gamma_curves = None

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

        if led_settings.driver == LedSettings.DRIVER_APA102:
            self.__driver = APA102Driver(led_settings, clear_screen)
        elif led_settings.driver == LedSettings.DRIVER_RGBMATRIX:
            self.__driver = RGBMatrixDriver(led_settings, clear_screen)
        else:
            raise Exception('Unsupported driver: {}'.format(self.__led_settings.driver))

    def clear_screen(self):
        self.__driver.clear_screen()

    def play_frame(self, avg_color_frame):
        self.__set_frame_pixels(avg_color_frame)

    def fade_to_frame(self, avg_color_frame):
        if (self.__current_frame is None):
            self.__current_frame = avg_color_frame
            return self.play_frame(avg_color_frame)

        frame_steps = np.zeros([self.__led_settings.display_height, self.__led_settings.display_width, 3], np.int8)

        for x in range(self.__led_settings.display_width):
            for y in range(self.__led_settings.display_height):
                for rgb in range(0, 3):
                    frame_steps[y, x, rgb] = ((avg_color_frame[y, x, rgb].astype(np.int16) - self.__current_frame[y, x, rgb].astype(np.int16)) / self.__FADE_STEPS).astype(np.int8)

        for current_step in range(1, self.__FADE_STEPS):
            new_frame = np.zeros([self.__led_settings.display_height, self.__led_settings.display_width, 3], np.uint8)
            for x in range(self.__led_settings.display_width):
                for y in range(self.__led_settings.display_height):
                    for rgb in range(0, 3):
                        new_frame[y, x, rgb] = self.__current_frame[y, x, rgb] + (frame_steps[y, x, rgb] * current_step)

            # no need to sleep since the above calculation takes some small amount of time
            self.__set_frame_pixels(new_frame)

        self.__current_frame = avg_color_frame
        self.__set_frame_pixels(avg_color_frame)

    def show_loading_screen(self):
        filename = 'loading_screen_monochrome.npy'
        if self.__led_settings.is_color_mode_rgb():
            filename = 'loading_screen_color.npy'
        loading_screen_path = DirectoryUtils().root_dir + '/' + filename
        self.play_frame(np.load(loading_screen_path))

    # This method transforms an input frame, which may be either a 2-dimensional
    # byte array if __led_settings.is_color_mode_rgb() is false, or 3d
    # otherwise, into an output frame by applying the user-provided transforms
    # such as color mode and flipping. The output is a 3d byte array suitable
    # for final display.
    def __transform_frame(self, avg_color_frame):
        if not (self.__led_settings.is_color_mode_rgb()):
            gamma_index = self.__gamma_controller.getGammaIndexForMonochromeFrame(avg_color_frame)

        shape = [self.__led_settings.display_height, self.__led_settings.display_width, 3]
        frame = np.zeros(shape, np.uint8)
        # calculate gamma corrected colors
        if self.__led_settings.color_mode == LedSettings.COLOR_MODE_COLOR:
            frame[:,:,0] = np.take(self.__scale_red_gamma_curve, avg_color_frame[:,:,0])
            frame[:,:,1] = np.take(self.__scale_green_gamma_curve, avg_color_frame[:,:,1])
            frame[:,:,2] = np.take(self.__scale_blue_gamma_curve, avg_color_frame[:,:,2])
        elif self.__led_settings.color_mode == LedSettings.COLOR_MODE_R:
            frame[:,:,0] = np.take(self.__scale_red_gamma_curves[gamma_index], avg_color_frame[:,:])
        elif self.__led_settings.color_mode == LedSettings.COLOR_MODE_G:
            frame[:,:,1] = np.take(self.__scale_green_gamma_curves[gamma_index], avg_color_frame[:,:])
        elif self.__led_settings.color_mode == LedSettings.COLOR_MODE_B:
            frame[:,:,2] = np.take(self.__scale_blue_gamma_curves[gamma_index], avg_color_frame[:,:])
        elif self.__led_settings.color_mode == LedSettings.COLOR_MODE_BW:
            frame[:,:,0] = np.take(self.__scale_red_gamma_curves[gamma_index], avg_color_frame[:,:])
            frame[:,:,1] = np.take(self.__scale_green_gamma_curves[gamma_index], avg_color_frame[:,:])
            frame[:,:,2] = np.take(self.__scale_blue_gamma_curves[gamma_index], avg_color_frame[:,:])
        elif self.__led_settings.color_mode == LedSettings.COLOR_MODE_INVERT_COLOR:
            frame[:,:,0] = np.take(self.__scale_red_gamma_curve, 255 - avg_color_frame[:,:,0])
            frame[:,:,1] = np.take(self.__scale_green_gamma_curve, 255 - avg_color_frame[:,:,1])
            frame[:,:,2] = np.take(self.__scale_blue_gamma_curve, 255 - avg_color_frame[:,:,2])
        elif self.__led_settings.color_mode == LedSettings.COLOR_MODE_INVERT_BW:
            frame[:,:,0] = np.take(self.__scale_red_gamma_curves[gamma_index], 255 - avg_color_frame[:,:])
            frame[:,:,1] = np.take(self.__scale_green_gamma_curves[gamma_index], 255 - avg_color_frame[:,:])
            frame[:,:,2] = np.take(self.__scale_blue_gamma_curves[gamma_index], 255 - avg_color_frame[:,:])
        else:
            raise Exception('Unexpected color mode: {}'.format(self.__led_settings.color_mode))

        flips = ()
        if (self.__led_settings.flip_y):
            flips += (0,)
        if (self.__led_settings.flip_x):
            flips += (1,)
        if flips:
            frame = np.flip(frame, flips)

        return frame

    def __set_frame_pixels(self, avg_color_frame):
        output_frame = self.__transform_frame(avg_color_frame)
        self.__driver.display_frame(output_frame)
