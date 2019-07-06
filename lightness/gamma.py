import numpy as np

class Gamma:
    # possible gamma curve range, step by .1
    __MIN_GAMMA_CURVE = 2
    __MAX_GAMMA_CURVE = 6

    # % to scale down the max brightness of each individual led
    __RED_MAX_BRIGHTNESS = 1
    __GREEN_MAX_BRIGHTNESS = .45
    __BLUE_MAX_BRIGHTNESS = .375

    # list of gamma curves from min to max
    scale_red = []
    scale_blue = []
    scale_green = []

    __video_settings = None

    gamma_index = 18

    def __init__(self, video_settings):
        self.__video_settings = video_settings
        self.__generateGammaScales()

    def getScaledRGBOutputForColorFrame(self, frame, x, y):
        return [
            self.getScaledOutputForPixel(frame[y, x, 0], 'r'),
            self.getScaledOutputForPixel(frame[y, x, 1], 'g'),
            self.getScaledOutputForPixel(frame[y, x, 2], 'b')
        ]

    def getScaledRGBOutputForBlackAndWhiteFrame(self, frame, x, y):
        return [
            self.getScaledOutputForPixel(frame[y, x], 'r'),
            self.getScaledOutputForPixel(frame[y, x], 'g'),
            self.getScaledOutputForPixel(frame[y, x], 'b')
        ]

    def getScaledOutputForPixel(self, brightness, color):
        gamma_scale = []

        if color == 'r':
            gamma_scale = self.scale_red
        elif color == 'g':
            gamma_scale = self.scale_green
        elif color == 'b':
            gamma_scale = self.scale_blue

        return gamma_scale[self.gamma_index][int(brightness)]

    # powers auto gamma curve using the average brightness of the given frame
    def setGammaIndexForFrame(self, frame):
        self.gamma_index = self.getGammaIndexByMagicForFrame(frame)
        return self.gamma_index

    def getGammaIndexByMagicForFrame(self, frame):
        brightness_avg = np.mean(frame)
        brightness_std = np.std(frame)

        #magic defined here: https://docs.google.com/spreadsheets/d/1hF3N0hCOzZlIG9VZPjADr9MhL_TWClaLHs6NJCH47AM/edit#gid=0
        #calibrated at global brightness of 3 (i think?)
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
            self.scale_red.append(self.__getGammaScaleValues(i/10, 255, int(255 * self.__RED_MAX_BRIGHTNESS)))
            self.scale_blue.append(self.__getGammaScaleValues(i/10, 255, int(255 * self.__BLUE_MAX_BRIGHTNESS)))
            self.scale_green.append(self.__getGammaScaleValues(i/10, 255, int(255 * self.__GREEN_MAX_BRIGHTNESS)))

        # for black and white, if r, g, or b has a zero in the scale they all should be 0
        # otherwise dim pixels will be just that color
        if not self.__video_settings.is_color:
            for g in range(0, ((self.__MAX_GAMMA_CURVE - self.__MIN_GAMMA_CURVE) * 10)):
                for i in range(0, 256):
                    if min(self.scale_red[g][i], self.scale_green[g][i], self.scale_blue[g][i]) == 0:
                        self.scale_red[g][i] = 0
                        self.scale_green[g][i] = 0
                        self.scale_blue[g][i] = 0
                    else:
                        break
