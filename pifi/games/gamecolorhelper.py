import math
import random

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

    def __init__(self):
        self.reset()

    def reset(self):
        self.__color_gradient_offset = random.uniform(0, 2 * math.pi)
        self.__color_gradient_offset2 = random.uniform(0, 2 * math.pi)

    @staticmethod
    def determine_game_color_mode(game_color_mode):
        if (
            game_color_mode == GameColorHelper.GAME_COLOR_MODE_RANDOM or
            game_color_mode not in GameColorHelper.GAME_COLOR_MODES
        ):
            return random.choice(GameColorHelper.GAME_COLOR_MODES)
        else:
            return game_color_mode

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
            return self.__make_color_gradient(color_change_freq, num_ticks, offset = self.__color_gradient_offset)

    def get_rgb2(self, game_color_mode, color_change_freq, num_ticks):
        if game_color_mode == self.GAME_COLOR_MODE_RED:
            return [255, 182, 193]
        if game_color_mode == self.GAME_COLOR_MODE_GREEN:
            return [193, 255, 182]
        if game_color_mode == self.GAME_COLOR_MODE_BLUE:
            return [0, 220, 255]
        if game_color_mode == self.GAME_COLOR_MODE_BW:
            return [150, 150, 150]
        if game_color_mode == self.GAME_COLOR_MODE_RAINBOW:
            return self.__make_color_gradient(color_change_freq, num_ticks, offset = self.__color_gradient_offset2)

    def get_help_string(self):
        game_color_mode_help_str = 'One of '
        for mode in self.GAME_COLOR_MODES:
            game_color_mode_help_str += f"'{mode}', "
        game_color_mode_help_str += "or '{}'.".format(GameColorHelper.GAME_COLOR_MODE_RANDOM)
        return game_color_mode_help_str

    # See: https://krazydad.com/tutorials/makecolors.php
    def __make_color_gradient(
        self, color_change_freq, num_ticks,
        freq1 = None, freq2 = None, freq3 = None,
        phase1 = 0, phase2 = 2 * math.pi / 3, phase3 = 4 * math.pi / 3,
        center = 127.5, amplitude = 127.5, offset = 0
    ):
        if freq1 is None:
            freq1 = color_change_freq
        if freq2 is None:
            freq2 = color_change_freq
        if freq3 is None:
            freq3 = color_change_freq

        r = math.sin(num_ticks * freq1 + phase1 + offset) * amplitude + center
        g = math.sin(num_ticks * freq2 + phase2 + offset) * amplitude + center
        b = math.sin(num_ticks * freq3 + phase3 + offset) * amplitude + center
        return [r, g, b]
