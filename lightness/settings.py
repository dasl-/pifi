class Settings:
    # Boolean - color output?
    is_color = None

    # Int - Number of pixels / units
    display_width = None

    # Int - Number of pixels / units
    display_height = None

    # Int - Global brightness value, max of 31
    brightness = None

    # Boolean - swap left to right, depending on wiring
    flip_x = None

    # Boolean - swap top to bottom, depending on wiring
    flip_y = None

    def __init__(self, args):
        self.setFromArgs(args)

    def setFromArgs(self, args):
        self.is_color = args.is_color
        self.display_width = args.display_width
        self.display_height = args.display_height
        self.brightness = args.brightness
        self.flip_x = args.flip_x
        self.flip_y = args.flip_y
