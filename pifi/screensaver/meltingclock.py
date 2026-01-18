import numpy as np
import time
import random
from datetime import datetime

from pifi.config import Config
from pifi.logger import Logger
from pifi.led.ledframeplayer import LedFramePlayer
from pifi.screensaver.screensaver import Screensaver


class MeltingClock(Screensaver):
    """
    Melting clock screensaver.

    Displays the current time with a Dalí-inspired melting effect.
    When digits change, they drip and melt downward before the
    new digit appears.
    """

    # 3x5 pixel font for digits 0-9 and colon
    # Each digit is a list of 5 rows, each row is 3 bits
    FONT = {
        '0': [
            [1, 1, 1],
            [1, 0, 1],
            [1, 0, 1],
            [1, 0, 1],
            [1, 1, 1],
        ],
        '1': [
            [0, 1, 0],
            [1, 1, 0],
            [0, 1, 0],
            [0, 1, 0],
            [1, 1, 1],
        ],
        '2': [
            [1, 1, 1],
            [0, 0, 1],
            [1, 1, 1],
            [1, 0, 0],
            [1, 1, 1],
        ],
        '3': [
            [1, 1, 1],
            [0, 0, 1],
            [1, 1, 1],
            [0, 0, 1],
            [1, 1, 1],
        ],
        '4': [
            [1, 0, 1],
            [1, 0, 1],
            [1, 1, 1],
            [0, 0, 1],
            [0, 0, 1],
        ],
        '5': [
            [1, 1, 1],
            [1, 0, 0],
            [1, 1, 1],
            [0, 0, 1],
            [1, 1, 1],
        ],
        '6': [
            [1, 1, 1],
            [1, 0, 0],
            [1, 1, 1],
            [1, 0, 1],
            [1, 1, 1],
        ],
        '7': [
            [1, 1, 1],
            [0, 0, 1],
            [0, 0, 1],
            [0, 0, 1],
            [0, 0, 1],
        ],
        '8': [
            [1, 1, 1],
            [1, 0, 1],
            [1, 1, 1],
            [1, 0, 1],
            [1, 1, 1],
        ],
        '9': [
            [1, 1, 1],
            [1, 0, 1],
            [1, 1, 1],
            [0, 0, 1],
            [1, 1, 1],
        ],
        ':': [
            [0, 0, 0],
            [0, 1, 0],
            [0, 0, 0],
            [0, 1, 0],
            [0, 0, 0],
        ],
    }

    DIGIT_WIDTH = 3
    DIGIT_HEIGHT = 5

    def __init__(self, led_frame_player=None):
        super().__init__(led_frame_player)
        self.__logger = Logger().set_namespace(self.__class__.__name__)

        if led_frame_player is None:
            self.__led_frame_player = LedFramePlayer()
        else:
            self.__led_frame_player = led_frame_player

        self.__width = Config.get_or_throw('leds.display_width')
        self.__height = Config.get_or_throw('leds.display_height')

        # Current displayed time string
        self.__current_time = ""

        # Melting state for each character position
        # Each entry: {'char': str, 'drops': [(x, y, vy, brightness), ...], 'forming': float}
        self.__char_states = []

        # Frame buffer with floating point for smooth effects
        self.__buffer = None

        # Color hue (slowly cycles)
        self.__hue = 0.0

    def play(self):
        self.__logger.info("Starting Melting Clock screensaver")
        self.__reset()

        max_ticks = Config.get('melting_clock.max_ticks', 5000)
        tick = 0

        while tick < max_ticks:
            self.__tick()
            time.sleep(self.__get_tick_sleep())
            tick += 1

        self.__logger.info("Melting Clock screensaver ended")

    def __reset(self):
        self.__current_time = ""
        self.__char_states = []
        self.__buffer = np.zeros((self.__height, self.__width), dtype=np.float32)
        self.__hue = random.random()

    def __tick(self):
        # Get current time
        show_seconds = Config.get('melting_clock.show_seconds', False)
        if show_seconds:
            new_time = datetime.now().strftime("%H:%M:%S")
        else:
            new_time = datetime.now().strftime("%H:%M")

        # Check for time changes and trigger melting
        if new_time != self.__current_time:
            self.__handle_time_change(new_time)
            self.__current_time = new_time

        # Update melting animations
        self.__update_animations()

        # Slowly cycle hue
        hue_speed = Config.get('melting_clock.hue_speed', 0.001)
        self.__hue = (self.__hue + hue_speed) % 1.0

        self.__render()

    def __handle_time_change(self, new_time):
        """Handle transition from old time to new time."""
        old_time = self.__current_time

        # Initialize char states if needed
        while len(self.__char_states) < len(new_time):
            self.__char_states.append({
                'char': '',
                'drops': [],
                'forming': 1.0,  # 1.0 = fully formed
                'old_char': '',
            })

        # Check each character
        for i, new_char in enumerate(new_time):
            if i < len(old_time):
                old_char = old_time[i]
            else:
                old_char = ''

            if new_char != old_char and old_char != '':
                # Character changed - trigger melt!
                self.__start_melt(i, old_char, new_char)
            elif new_char != self.__char_states[i]['char']:
                # New character without melt (initial display)
                self.__char_states[i]['char'] = new_char
                self.__char_states[i]['forming'] = 0.0  # Start forming

    def __start_melt(self, char_index, old_char, new_char):
        """Start melting animation for a character."""
        state = self.__char_states[char_index]
        state['old_char'] = old_char
        state['char'] = new_char
        state['forming'] = 0.0  # New char will form as old one melts

        # Calculate character position
        x_offset = self.__get_char_x(char_index)
        y_offset = self.__get_char_y()

        # Create drops from each pixel of the old character
        if old_char in self.FONT:
            font_data = self.FONT[old_char]
            for row in range(self.DIGIT_HEIGHT):
                for col in range(self.DIGIT_WIDTH):
                    if font_data[row][col]:
                        # Create a drop for this pixel
                        drop_x = x_offset + col
                        drop_y = y_offset + row
                        # Random velocity and slight position variation
                        vy = random.uniform(0.1, 0.3)
                        brightness = 1.0
                        # Add slight delay based on row (top melts first? or bottom?)
                        delay = row * 0.1
                        state['drops'].append({
                            'x': drop_x,
                            'y': float(drop_y),
                            'vy': vy,
                            'brightness': brightness,
                            'delay': delay,
                        })

    def __update_animations(self):
        """Update all melting and forming animations."""
        melt_speed = Config.get('melting_clock.melt_speed', 0.15)
        form_speed = Config.get('melting_clock.form_speed', 0.05)

        for state in self.__char_states:
            # Update drops (melting)
            new_drops = []
            for drop in state['drops']:
                if drop['delay'] > 0:
                    drop['delay'] -= 0.1
                    new_drops.append(drop)
                else:
                    drop['y'] += drop['vy'] * melt_speed
                    drop['vy'] += 0.05  # Gravity
                    drop['brightness'] -= 0.02  # Fade out

                    # Keep drop if still visible
                    if drop['y'] < self.__height and drop['brightness'] > 0:
                        new_drops.append(drop)

            state['drops'] = new_drops

            # Update forming (new character fades in)
            if state['forming'] < 1.0:
                state['forming'] = min(1.0, state['forming'] + form_speed)

    def __get_char_x(self, char_index):
        """Get x position for a character."""
        # Calculate total width of time string
        show_seconds = Config.get('melting_clock.show_seconds', False)
        if show_seconds:
            # HH:MM:SS = 8 chars, but colons are narrower
            total_width = 6 * self.DIGIT_WIDTH + 2 * 3 + 7  # 6 digits + 2 colons + spacing
        else:
            # HH:MM = 5 chars
            total_width = 4 * self.DIGIT_WIDTH + 1 * 3 + 4  # 4 digits + 1 colon + spacing

        start_x = (self.__width - total_width) // 2

        # Position based on character index
        x = start_x
        for i in range(char_index):
            x += self.DIGIT_WIDTH + 1  # digit width + spacing

        return x

    def __get_char_y(self):
        """Get y position for characters (centered vertically)."""
        return (self.__height - self.DIGIT_HEIGHT) // 2

    def __render(self):
        # Fade existing buffer (creates trails)
        fade = Config.get('melting_clock.trail_fade', 0.85)
        self.__buffer *= fade

        frame = np.zeros([self.__height, self.__width, 3], np.uint8)
        y_offset = self.__get_char_y()

        # Draw each character
        for i, state in enumerate(self.__char_states):
            x_offset = self.__get_char_x(i)
            char = state['char']
            forming = state['forming']

            # Draw the forming/formed character
            if char in self.FONT and forming > 0:
                font_data = self.FONT[char]
                for row in range(self.DIGIT_HEIGHT):
                    for col in range(self.DIGIT_WIDTH):
                        if font_data[row][col]:
                            px = x_offset + col
                            py = y_offset + row
                            if 0 <= px < self.__width and 0 <= py < self.__height:
                                # Fade in from top
                                row_progress = (forming * self.DIGIT_HEIGHT - (self.DIGIT_HEIGHT - 1 - row))
                                pixel_brightness = max(0, min(1, row_progress))
                                self.__buffer[py, px] = max(self.__buffer[py, px], pixel_brightness)

            # Draw melting drops
            for drop in state['drops']:
                px = int(drop['x'])
                py = int(drop['y'])
                if 0 <= px < self.__width and 0 <= py < self.__height:
                    self.__buffer[py, px] = max(self.__buffer[py, px], drop['brightness'])

                # Draw trail
                trail_y = int(drop['y'] - drop['vy'] * 0.5)
                if 0 <= px < self.__width and 0 <= trail_y < self.__height:
                    self.__buffer[trail_y, px] = max(self.__buffer[trail_y, px], drop['brightness'] * 0.5)

        # Convert buffer to colored frame
        color_mode = Config.get('melting_clock.color_mode', 'rainbow')

        for y in range(self.__height):
            for x in range(self.__width):
                b = self.__buffer[y, x]
                if b > 0.01:
                    if color_mode == 'rainbow':
                        rgb = self.__hsv_to_rgb(self.__hue, 0.8, b)
                    elif color_mode == 'green':
                        rgb = [0, int(b * 255), int(b * 100)]
                    elif color_mode == 'blue':
                        rgb = [int(b * 100), int(b * 150), int(b * 255)]
                    elif color_mode == 'red':
                        rgb = [int(b * 255), int(b * 50), 0]
                    else:  # white
                        v = int(b * 255)
                        rgb = [v, v, v]
                    frame[y, x] = rgb

        self.__led_frame_player.play_frame(frame)

    def __hsv_to_rgb(self, h, s, v):
        """Convert HSV color to RGB."""
        if s == 0.0:
            return [int(v * 255)] * 3

        i = int(h * 6.0)
        f = (h * 6.0) - i
        p = v * (1.0 - s)
        q = v * (1.0 - s * f)
        t = v * (1.0 - s * (1.0 - f))
        i = i % 6

        if i == 0:
            r, g, b = v, t, p
        elif i == 1:
            r, g, b = q, v, p
        elif i == 2:
            r, g, b = p, v, t
        elif i == 3:
            r, g, b = p, q, v
        elif i == 4:
            r, g, b = t, p, v
        else:
            r, g, b = v, p, q

        return [int(r * 255), int(g * 255), int(b * 255)]

    def __get_tick_sleep(self):
        return Config.get('melting_clock.tick_sleep', 0.05)

    @classmethod
    def get_id(cls) -> str:
        return 'melting_clock'

    @classmethod
    def get_name(cls) -> str:
        return 'Melting Clock'

    @classmethod
    def get_description(cls) -> str:
        return 'Time display with melting digits'
