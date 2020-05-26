import numpy as np

class ScoreDisplayer:

    # LedSettings
    __settings = None

    __video_player = None

    __score = None

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
    __digit_components = (
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

    def __init__(self, settings, video_player, score):
        self.__settings = settings
        self.__video_player = video_player
        self.__score = score

    # TODO: validate if score too big
    def display_score(self):
        score_string = str(self.__score)
        digit_component_length = self.__get_digit_component_length()

        # omitted left corner + component length + omitted right corner + padding
        digit_width = 1 + digit_component_length + 1 + 1

        # omitted top pixel + component length + omitted middle pixel + component length + omitted bottom pixel
        digit_height = 1 + digit_component_length + 1 + digit_component_length + 1

        num_digits = len(score_string)

        score_width = digit_width * num_digits
        x = round((self.__settings.display_width - score_width) / 2)
        y = round((self.__settings.display_height - digit_height) / 2)
        frame = np.zeros([self.__settings.display_height, self.__settings.display_width, 3], np.uint8)
        rgb = [255, 0, 0] # red
        for i in range(0, num_digits):
            self.__write_digit(x, y, int(score_string[i]), digit_component_length, frame, rgb)
            x = x + digit_width

        self.__video_player.play_frame(frame)

    def __write_digit(self, x, y, digit, digit_component_length, frame, rgb):
        digit_components = self.__digit_components[digit]
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
        return 3
        return min(
            round(4 * self.__settings.display_width / 28),
            round(4 * self.__settings.display_height / 18)
        )
