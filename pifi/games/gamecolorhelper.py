import math
import random
from pifi.settings.ledsettings import LedSettings

# utils for doing color in games
class GameColorHelper:

    GAME_COLOR_MODE_RANDOM = 'random'
    GAME_COLOR_MODE_RED = 'red'
    GAME_COLOR_MODE_GREEN = 'green'
    GAME_COLOR_MODE_BLUE = 'blue'
    GAME_COLOR_MODE_BW = 'bw'
    GAME_COLOR_MODE_RAINBOW = 'rainbow'

    # Lists all modes except GAME_COLOR_MODE_RANDOM
    GAME_COLOR_MODES = [
        GAME_COLOR_MODE_RED, GAME_COLOR_MODE_GREEN, GAME_COLOR_MODE_BLUE,
        GAME_COLOR_MODE_BW, GAME_COLOR_MODE_RAINBOW
    ]

    __color_gradient_offset = None

    def __init__(self):
        self.reset()

    def reset(self):
        self.__color_gradient_offset = random.uniform(0, 2 * math.pi)

    def set_game_color_mode(self, settings, game_color_mode):
        if game_color_mode == None:
            game_color_mode = self.GAME_COLOR_MODE_RANDOM

        game_color_mode = game_color_mode.lower()
        if game_color_mode in self.GAME_COLOR_MODES or game_color_mode == self.GAME_COLOR_MODE_RANDOM:
            settings.game_color_mode = game_color_mode
        else:
            raise Exception("Unknown game_color_mode: {}".format(game_color_mode))

    def determine_game_color_mode(self, settings):
        if settings.game_color_mode == self.GAME_COLOR_MODE_RANDOM:
            return random.choice(self.GAME_COLOR_MODES)
        else:
            return settings.game_color_mode

    def get_rgb(self, game_color_mode, color_change_freq, num_ticks):
        if game_color_mode == self.GAME_COLOR_MODE_RED:
            return [255, 0, 0]
        if game_color_mode == self.GAME_COLOR_MODE_GREEN:
            return [0, 255, 0]
        if game_color_mode == self.GAME_COLOR_MODE_BLUE:
            return [0, 0, 255]
        if game_color_mode == self.GAME_COLOR_MODE_BW:
            return [255, 255, 255]
        if game_color_mode == self.GAME_COLOR_MODE_RAINBOW:
            return self.__make_color_gradient(color_change_freq, num_ticks)

    # See: https://krazydad.com/tutorials/makecolors.php
    def __make_color_gradient(
        self, color_change_freq, num_ticks,
        freq1 = None, freq2 = None, freq3 = None,
        phase1 = 0, phase2 = 2 * math.pi / 3, phase3 = 4 * math.pi / 3,
        center = 127.5, amplitude = 127.5
    ):
        if freq1 == None:
            freq1 = color_change_freq
        if freq2 == None:
            freq2 = color_change_freq
        if freq3 == None:
            freq3 = color_change_freq

        r = math.sin(num_ticks * freq1 + phase1 + self.__color_gradient_offset) * amplitude + center
        g = math.sin(num_ticks * freq2 + phase2 + self.__color_gradient_offset) * amplitude + center
        b = math.sin(num_ticks * freq3 + phase3 + self.__color_gradient_offset) * amplitude + center
        return [r, g, b]
