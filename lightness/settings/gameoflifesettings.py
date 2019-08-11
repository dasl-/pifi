from lightness.settings.ledsettings import LedSettings

class GameOfLifeSettings(LedSettings):

    DEFAULT_SEED_LIVENESS_PROBABILITY = 1/3

    seed_liveness_probability = None

    def __init__(
        self, color_mode = None, display_width = None, display_height = None,
        brightness = None, flip_x = False, flip_y = False, log_level = None,
        seed_liveness_probability = None,
    ):
        super().__init__(
            color_mode, display_width, display_height, brightness, flip_x, flip_y, log_level
        )
        if seed_liveness_probability == None:
            seed_liveness_probability = self.DEFAULT_SEED_LIVENESS_PROBABILITY
        self.seed_liveness_probability = seed_liveness_probability
