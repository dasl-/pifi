import numpy as np
from pifi.settings.ledsettings import LedSettings

class Gamma:

    DEFAULT_GAMMA_INDEX = 18

    # list of gamma curves from min to max
    scale_red_curves = []
    scale_blue_curves = []
    scale_green_curves = []

    # possible gamma curve range, step by .1
    __MIN_GAMMA_CURVE = 2
    __MAX_GAMMA_CURVE = 6

    # % to scale down the max brightness of each individual led
    __RED_MAX_BRIGHTNESS = 1
    __GREEN_MAX_BRIGHTNESS = .45
    __BLUE_MAX_BRIGHTNESS = .375

    __led_settings = None

    def __init__(self, led_settings):
        self.__led_settings = led_settings
        self.__generateGammaScales()

    # powers auto dynamic gamma curve using the average brightness of the given frame
    def getGammaIndexForMonochromeFrame(self, frame):
        brightness_avg = np.mean(frame)
        brightness_std = np.std(frame)

        # magic defined here: https://docs.google.com/spreadsheets/d/1hF3N0hCOzZlIG9VZPjADr9MhL_TWClaLHs6NJCH47AM/edit#gid=0
        # calibrated with:
        #   * --brightness of 3 (i think?)
        #   * black and white video
        #   * using opencv LED color averaging rather than ffmpeg (https://github.com/dasl-/pifi/commit/8a4703fb479421160b9c119dc718b747a8627b4f#commitcomment-34206224)
        gamma_index = (-0.2653691135*brightness_std) + (0.112790567*(brightness_avg)) + 18.25205188

        if gamma_index < 0:
            return 0
        elif gamma_index >= ((self.__MAX_GAMMA_CURVE - self.__MIN_GAMMA_CURVE) * 10) - 1:
            return ((self.__MAX_GAMMA_CURVE - self.__MIN_GAMMA_CURVE) * 10) - 1
        else:
            return int(round(gamma_index))

    # gamma: Correction factor
    # max_in: Top end of INPUT range
    # max_out: Top end of OUTPUT range
    # https://learn.adafruit.com/led-tricks-gamma-correction/
    def __getGammaScaleValues(self, gamma, max_in, max_out):
        gamma_list = []
        for i in range(0, max_in+1):
            gamma_list.append(
                int(
                    round(
                        pow(float(i / max_in), gamma) * max_out
                    )
                )
            )

        return gamma_list

    def __generateGammaScales(self):
        for i in range(self.__MIN_GAMMA_CURVE * 10, self.__MAX_GAMMA_CURVE * 10):
            self.scale_red_curves.append(self.__getGammaScaleValues(i/10, 255, int(255 * self.__RED_MAX_BRIGHTNESS)))
            self.scale_blue_curves.append(self.__getGammaScaleValues(i/10, 255, int(255 * self.__BLUE_MAX_BRIGHTNESS)))
            self.scale_green_curves.append(self.__getGammaScaleValues(i/10, 255, int(255 * self.__GREEN_MAX_BRIGHTNESS)))

        # for black and white, if r, g, or b has a zero in the scale they all should be 0
        # otherwise dim pixels will be just that color
        if self.__led_settings.color_mode == LedSettings.COLOR_MODE_BW:
            for g in range(0, ((self.__MAX_GAMMA_CURVE - self.__MIN_GAMMA_CURVE) * 10)):
                for i in range(0, 256):
                    if min(self.scale_red_curves[g][i], self.scale_green_curves[g][i], self.scale_blue_curves[g][i]) == 0:
                        self.scale_red_curves[g][i] = 0
                        self.scale_green_curves[g][i] = 0
                        self.scale_blue_curves[g][i] = 0
                    else:
                        break
