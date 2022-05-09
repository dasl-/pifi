class VideoColorMode:

    COLOR_MODE_COLOR = 'color'
    COLOR_MODE_BW = 'bw' # black and white
    COLOR_MODE_R = 'red'
    COLOR_MODE_G = 'green'
    COLOR_MODE_B = 'blue'
    COLOR_MODE_INVERT_COLOR = 'inv_color'
    COLOR_MODE_INVERT_BW = 'inv_bw'

    COLOR_MODES = [
        COLOR_MODE_COLOR,
        COLOR_MODE_BW,
        COLOR_MODE_R,
        COLOR_MODE_G,
        COLOR_MODE_B,
        COLOR_MODE_INVERT_COLOR,
        COLOR_MODE_INVERT_BW,
    ]

    @staticmethod
    def is_color_mode_rgb(color_mode):
        return color_mode in [VideoColorMode.COLOR_MODE_COLOR, VideoColorMode.COLOR_MODE_INVERT_COLOR]
