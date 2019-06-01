class Settings:
    # Boolean - color output?
    is_color = None

    # Int - Number of pixels / units
    display_width = None

    # Int - Number of pixels / units
    display_height = None

    # Int - Global brightness value, max of 31
    brightness = None

    def __init__(self, args):
        self.setFromArgs(args)

    def setFromArgs(self, args):
        self.is_color = args.is_color
        self.display_width = args.display_width
        self.display_height = args.display_height
        self.brightness = args.brightness
