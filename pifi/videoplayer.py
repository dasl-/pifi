import numpy as np

from pifi.config import Config
from pifi.directoryutils import DirectoryUtils
from pifi.gamma import Gamma
from pifi.leddrivers.leddrivers import LedDrivers
from pifi.video.videocolormode import VideoColorMode

# TODO: rename pifi/leds/ledframeplayer.py
class VideoPlayer:

    __FADE_STEPS = 5

    # clear_screen: whether to clear the screen when initializing
    # video_color_mode: only applicable when playing videos
    def __init__(self, clear_screen = True, video_color_mode = VideoColorMode.COLOR_MODE_COLOR):
        self.__current_frame = None
        self.__gamma_controller = Gamma(video_color_mode = video_color_mode)

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
        if VideoColorMode.is_color_mode_rgb(video_color_mode):
            # static gamma
            self.__scale_red_gamma_curve = self.__gamma_controller.scale_red_curves[Gamma.DEFAULT_GAMMA_INDEX]
            self.__scale_green_gamma_curve = self.__gamma_controller.scale_green_curves[Gamma.DEFAULT_GAMMA_INDEX]
            self.__scale_blue_gamma_curve = self.__gamma_controller.scale_blue_curves[Gamma.DEFAULT_GAMMA_INDEX]
        else:
            # dynamic gamma
            self.__scale_red_gamma_curves = self.__gamma_controller.scale_red_curves
            self.__scale_green_gamma_curves = self.__gamma_controller.scale_green_curves
            self.__scale_blue_gamma_curves = self.__gamma_controller.scale_blue_curves

        led_driver = Config.get_or_throw('leds.driver')
        if led_driver == LedDrivers.DRIVER_APA102:
            from pifi.leddrivers.driverapa102 import DriverApa102
            self.__driver = DriverApa102(clear_screen)
        elif led_driver == LedDrivers.DRIVER_RGBMATRIX:
            from pifi.leddrivers.driverrgbmatrix import DriverRgbMatrix
            self.__driver = DriverRgbMatrix(clear_screen)
        else:
            raise Exception(f'Unsupported driver: {led_driver}.')

        self.__video_color_mode = video_color_mode

    def clear_screen(self):
        self.__driver.clear_screen()

    def play_frame(self, frame):
        self.__set_frame_pixels(frame)

    def fade_to_frame(self, frame):
        if (self.__current_frame is None):
            self.__current_frame = frame
            return self.play_frame(frame)

        display_width = Config.get_or_throw('leds.display_width')
        display_height = Config.get_or_throw('leds.display_height')
        frame_steps = np.zeros([display_height, display_width, 3], np.int8)

        for x in range(display_width):
            for y in range(display_height):
                for rgb in range(0, 3):
                    frame_steps[y, x, rgb] = ((frame[y, x, rgb].astype(np.int16) - self.__current_frame[y, x, rgb].astype(np.int16)) / self.__FADE_STEPS).astype(np.int8)

        for current_step in range(1, self.__FADE_STEPS):
            new_frame = np.zeros([display_height, display_width, 3], np.uint8)
            for x in range(display_width):
                for y in range(display_height):
                    for rgb in range(0, 3):
                        new_frame[y, x, rgb] = self.__current_frame[y, x, rgb] + (frame_steps[y, x, rgb] * current_step)

            # no need to sleep since the above calculation takes some small amount of time
            self.__set_frame_pixels(new_frame)

        self.__current_frame = frame
        self.__set_frame_pixels(frame)

    def show_loading_screen(self):
        filename = 'loading_screen_monochrome.npy'
        if VideoColorMode.is_color_mode_rgb(self.__video_color_mode):
            filename = 'loading_screen_color.npy'
        loading_screen_path = DirectoryUtils().root_dir + '/' + filename
        self.play_frame(np.load(loading_screen_path))

    # This method transforms an input frame, which may be either a 2-dimensional
    # byte array if VideoColorMode.is_color_mode_rgb() is false, or 3d
    # otherwise, into an output frame by applying the user-provided transforms
    # such as color mode and flipping. The output is a 3d byte array suitable
    # for final display.
    def __transform_frame(self, frame):
        if not (VideoColorMode.is_color_mode_rgb(self.__video_color_mode)):
            gamma_index = self.__gamma_controller.getGammaIndexForMonochromeFrame(frame)

        shape = [Config.get_or_throw('leds.display_height'), Config.get_or_throw('leds.display_width'), 3]
        transformed_frame = np.zeros(shape, np.uint8)
        # calculate gamma corrected colors
        if self.__video_color_mode == VideoColorMode.COLOR_MODE_COLOR:
            transformed_frame[:, :, 0] = np.take(self.__scale_red_gamma_curve, frame[:, :, 0])
            transformed_frame[:, :, 1] = np.take(self.__scale_green_gamma_curve, frame[:, :, 1])
            transformed_frame[:, :, 2] = np.take(self.__scale_blue_gamma_curve, frame[:, :, 2])
        elif self.__video_color_mode == VideoColorMode.COLOR_MODE_R:
            transformed_frame[:, :, 0] = np.take(self.__scale_red_gamma_curves[gamma_index], frame[:, :])
        elif self.__video_color_mode == VideoColorMode.COLOR_MODE_G:
            transformed_frame[:, :, 1] = np.take(self.__scale_green_gamma_curves[gamma_index], frame[:, :])
        elif self.__video_color_mode == VideoColorMode.COLOR_MODE_B:
            transformed_frame[:, :, 2] = np.take(self.__scale_blue_gamma_curves[gamma_index], frame[:, :])
        elif self.__video_color_mode == VideoColorMode.COLOR_MODE_BW:
            transformed_frame[:, :, 0] = np.take(self.__scale_red_gamma_curves[gamma_index], frame[:, :])
            transformed_frame[:, :, 1] = np.take(self.__scale_green_gamma_curves[gamma_index], frame[:, :])
            transformed_frame[:, :, 2] = np.take(self.__scale_blue_gamma_curves[gamma_index], frame[:, :])
        elif self.__video_color_mode == VideoColorMode.COLOR_MODE_INVERT_COLOR:
            transformed_frame[:, :, 0] = np.take(self.__scale_red_gamma_curve, 255 - frame[:, :, 0])
            transformed_frame[:, :, 1] = np.take(self.__scale_green_gamma_curve, 255 - frame[:, :, 1])
            transformed_frame[:, :, 2] = np.take(self.__scale_blue_gamma_curve, 255 - frame[:, :, 2])
        elif self.__video_color_mode == VideoColorMode.COLOR_MODE_INVERT_BW:
            transformed_frame[:, :, 0] = np.take(self.__scale_red_gamma_curves[gamma_index], 255 - frame[:, :])
            transformed_frame[:, :, 1] = np.take(self.__scale_green_gamma_curves[gamma_index], 255 - frame[:, :])
            transformed_frame[:, :, 2] = np.take(self.__scale_blue_gamma_curves[gamma_index], 255 - frame[:, :])
        else:
            raise Exception(f'Unexpected color mode: {self.__video_color_mode}.')

        flips = ()
        if Config.get('leds.flip_y', False):
            flips += (0,)
        if Config.get('leds.flip_x', False):
            flips += (1,)
        if flips:
            transformed_frame = np.flip(transformed_frame, flips)

        return transformed_frame

    def __set_frame_pixels(self, frame):
        output_frame = self.__transform_frame(frame)
        self.__driver.display_frame(output_frame)
