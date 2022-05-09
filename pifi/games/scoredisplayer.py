import numpy as np

from pifi.config import Config

class ScoreDisplayer:

    """
             0
           ----
          |    |
        1 |    | 2
          |    |
          |  3 |
           ----
          |    |
          |    |
        4 |    | 5
          |    |
           ----
             6
    """
    __DIGIT_COMPONENTS = (
        # 0  1  2  3  4  5  6
        (1, 1, 1, 0, 1, 1, 1), # 0
        (0, 0, 1, 0, 0, 1, 0), # 1
        (1, 0, 1, 1, 1, 0, 1), # 2
        (1, 0, 1, 1, 0, 1, 1), # 3
        (0, 1, 1, 1, 0, 1, 0), # 4
        (1, 1, 0, 1, 0, 1, 1), # 5
        (1, 1, 0, 1, 1, 1, 1), # 6
        (1, 0, 1, 0, 0, 1, 0), # 7
        (1, 1, 1, 1, 1, 1, 1), # 8
        (1, 1, 1, 1, 0, 1, 1), # 9
    )

    def __init__(self, led_frame_player, score):
        self.__led_frame_player = led_frame_player
        self.__score = score

    # TODO: validate if score too big
    def display_score(self, rgb = [255, 0, 0]):
        score_string = str(self.__score)
        digit_component_length = self.__get_digit_component_length()

        # omitted left corner + component length + omitted right corner + padding
        digit_width = 1 + digit_component_length + 1 + 1

        # omitted top pixel + component length + omitted middle pixel + component length + omitted bottom pixel
        digit_height = 1 + digit_component_length + 1 + digit_component_length + 1

        num_digits = len(score_string)
        score_width = digit_width * num_digits
        display_width = Config.get_or_throw('leds.display_width')
        display_height = Config.get_or_throw('leds.display_height')
        x = round((display_width - score_width) / 2)
        y = round((display_height - digit_height) / 2)
        frame = np.zeros([display_height, display_width, 3], np.uint8)
        for i in range(0, num_digits):
            self.__write_digit(x, y, int(score_string[i]), digit_component_length, frame, rgb)
            x = x + digit_width

        self.__led_frame_player.play_frame(frame)

    def __write_digit(self, x, y, digit, digit_component_length, frame, rgb):
        digit_components = self.__DIGIT_COMPONENTS[digit]
        for digit_component in range(0, 7):
            if digit_components[digit_component] == 0:
                continue
            elif digit_component == 0:
                for i in range(0, digit_component_length):
                    frame[y, x + i + 1] = rgb
            elif digit_component == 1:
                for i in range(0, digit_component_length):
                    frame[y + 1 + i, x] = rgb
            elif digit_component == 2:
                for i in range(0, digit_component_length):
                    frame[y + 1 + i, x + 1 + digit_component_length] = rgb
            elif digit_component == 3:
                for i in range(0, digit_component_length):
                    frame[y + 1 + digit_component_length, x + i + 1] = rgb
            elif digit_component == 4:
                for i in range(0, digit_component_length):
                    frame[y + 1 + digit_component_length + 1 + i, x] = rgb
            elif digit_component == 5:
                for i in range(0, digit_component_length):
                    frame[y + 1 + digit_component_length + 1 + i, x + 1 + digit_component_length] = rgb
            elif digit_component == 6:
                for i in range(0, digit_component_length):
                    frame[y + 1 + digit_component_length + 1 + digit_component_length, x + i + 1] = rgb

    def __get_digit_component_length(self):
        return min(
            round(3 * Config.get_or_throw('leds.display_width') / 28),
            round(3 * Config.get_or_throw('leds.display_height') / 18)
        )
