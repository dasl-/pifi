class Gamma:
    # possible gamma curve range, step by .1
    MIN_GAMMA_CURVE = 2
    MAX_GAMMA_CURVE = 6

    # % to scale down the max brightness of each individual led
    RED_MAX_BRIGHTNESS = 1
    GREEN_MAX_BRIGHTNESS = .45
    BLUE_MAX_BRIGHTNESS = .375

    # list of gamma curves from min to max
    scale_red = []
    scale_blue = []
    scale_green = []

    is_color = None
    display_width = None
    display_height = None
    gamma_index = 18

    def __init__(self, is_color, display_width, display_height):
        self.is_color = is_color
        self.display_width = display_width
        self.display_height = display_height
        self.generateGammaScales()

    def getScaledRGBOutputForColorFrame(self, avg_color_frame, x, y):
        return [
            self.getScaledOutputForFrame(avg_color_frame, avg_color_frame[x, y, 2], True),
            self.getScaledOutputForFrame(avg_color_frame, avg_color_frame[x, y, 1], False, True),
            self.getScaledOutputForFrame(avg_color_frame, avg_color_frame[x, y, 0], False, False, True)
        ]

    def getScaledRGBOutputForBlackAndWhiteFrame(self, avg_color_frame, x, y):
        return [
            self.getScaledOutputForFrame(avg_color_frame, avg_color_frame[x, y], True),
            self.getScaledOutputForFrame(avg_color_frame, avg_color_frame[x, y], False, True),
            self.getScaledOutputForFrame(avg_color_frame, avg_color_frame[x, y], False, False, True)
        ]

    def getScaledOutputForFrame(self, avg_color_frame, val, r = False, g = False, b = False):
        gamma_scale = []

        if r:
            gamma_scale = self.scale_red
        elif g:
            gamma_scale = self.scale_green
        elif b:
            gamma_scale = self.scale_blue

        return gamma_scale[self.gamma_index][int(val)]

    # set a specific index (0=min)
    def setGammaIndex(self, new_gamma_index):
        self.gamma_index = new_gamma_index

    # powers auto gamma curve using the average brightness of the given frame
    def setGammaIndexForFrame(self, avg_color_frame):
        brightness_total = 0
        if self.is_color:
            self.setGammaIndex(18)
        else:
            total_leds = (self.display_width * self.display_height)
            for x in range(self.display_width):
                for y in range(self.display_height):
                    brightness_total += avg_color_frame[x, y]

            brightness_avg = brightness_total / total_leds
            self.gamma_index = int(round(brightness_avg / 256 * ((self.MAX_GAMMA_CURVE - self.MIN_GAMMA_CURVE) * 10), 0))

        # print("gamma: " + str((self.gamma_index + 10) / 10))
        return self.gamma_index

    # gamma: Correction factor
    # max_in: Top end of INPUT range
    # max_out: Top end of OUTPUT range
    def getGammaScaleValues(self, gamma, max_in, max_out):
        gamma_list = []
        for i in range(0, max_in+1):
            gamma_list.append(
                int(
                    round(
                        pow(float(i / max_in), gamma) * max_out
                    )
                )
            )

        return gamma_list;

    # is_color: true for color video
    def generateGammaScales(self):
        for i in range(self.MIN_GAMMA_CURVE * 10, self.MAX_GAMMA_CURVE * 10):
            self.scale_red.append(self.getGammaScaleValues(i/10, 255, int(255 * self.RED_MAX_BRIGHTNESS)))
            self.scale_blue.append(self.getGammaScaleValues(i/10, 255, int(255 * self.BLUE_MAX_BRIGHTNESS)))
            self.scale_green.append(self.getGammaScaleValues(i/10, 255, int(255 * self.GREEN_MAX_BRIGHTNESS)))

        # for black and white, if r, g, or b has a zero in the scale they all should be 0
        # otherwise dim pixels will be just that color
        if not self.is_color:
            for g in range(0, ((self.MAX_GAMMA_CURVE - self.MIN_GAMMA_CURVE) * 10)):
                for i in range(0, 256):
                    if min(self.scale_red[g][i], self.scale_green[g][i], self.scale_blue[g][i]) == 0:
                        self.scale_red[g][i] = 0
                        self.scale_green[g][i] = 0
                        self.scale_blue[g][i] = 0
                    else:
                        break
