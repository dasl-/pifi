"""
Shared text rendering utilities for LED matrix screensavers.

Provides a 3x5 pixel font and functions for drawing text with scrolling and easing.
"""

# Simple 3x5 font for characters - optimized for low resolution displays
FONT_3X5 = {
    '0': [[1,1,1],[1,0,1],[1,0,1],[1,0,1],[1,1,1]],
    '1': [[0,1,0],[1,1,0],[0,1,0],[0,1,0],[1,1,1]],
    '2': [[1,1,1],[0,0,1],[1,1,1],[1,0,0],[1,1,1]],
    '3': [[1,1,1],[0,0,1],[0,1,1],[0,0,1],[1,1,1]],
    '4': [[1,0,1],[1,0,1],[1,1,1],[0,0,1],[0,0,1]],
    '5': [[1,1,1],[1,0,0],[1,1,1],[0,0,1],[1,1,1]],
    '6': [[1,1,1],[1,0,0],[1,1,1],[1,0,1],[1,1,1]],
    '7': [[1,1,1],[0,0,1],[0,0,1],[0,1,0],[0,1,0]],
    '8': [[1,1,1],[1,0,1],[1,1,1],[1,0,1],[1,1,1]],
    '9': [[1,1,1],[1,0,1],[1,1,1],[0,0,1],[1,1,1]],
    'A': [[0,1,0],[1,0,1],[1,1,1],[1,0,1],[1,0,1]],
    'B': [[1,1,0],[1,0,1],[1,1,0],[1,0,1],[1,1,0]],
    'C': [[0,1,1],[1,0,0],[1,0,0],[1,0,0],[0,1,1]],
    'D': [[1,1,0],[1,0,1],[1,0,1],[1,0,1],[1,1,0]],
    'E': [[1,1,1],[1,0,0],[1,1,0],[1,0,0],[1,1,1]],
    'F': [[1,1,1],[1,0,0],[1,1,0],[1,0,0],[1,0,0]],
    'G': [[0,1,1],[1,0,0],[1,0,1],[1,0,1],[0,1,1]],
    'H': [[1,0,1],[1,0,1],[1,1,1],[1,0,1],[1,0,1]],
    'I': [[1,1,1],[0,1,0],[0,1,0],[0,1,0],[1,1,1]],
    'J': [[0,1,1],[0,0,1],[0,0,1],[1,0,1],[0,1,0]],
    'K': [[1,0,1],[1,1,0],[1,0,0],[1,1,0],[1,0,1]],
    'L': [[1,0,0],[1,0,0],[1,0,0],[1,0,0],[1,1,1]],
    'M': [[1,0,1],[1,1,1],[1,0,1],[1,0,1],[1,0,1]],
    'N': [[1,0,1],[1,1,1],[1,1,1],[1,0,1],[1,0,1]],
    'O': [[0,1,0],[1,0,1],[1,0,1],[1,0,1],[0,1,0]],
    'P': [[1,1,0],[1,0,1],[1,1,0],[1,0,0],[1,0,0]],
    'Q': [[0,1,0],[1,0,1],[1,0,1],[1,0,1],[0,1,1]],
    'R': [[1,1,0],[1,0,1],[1,1,0],[1,0,1],[1,0,1]],
    'S': [[0,1,1],[1,0,0],[0,1,0],[0,0,1],[1,1,0]],
    'T': [[1,1,1],[0,1,0],[0,1,0],[0,1,0],[0,1,0]],
    'U': [[1,0,1],[1,0,1],[1,0,1],[1,0,1],[0,1,0]],
    'V': [[1,0,1],[1,0,1],[1,0,1],[0,1,0],[0,1,0]],
    'W': [[1,0,1],[1,0,1],[1,0,1],[1,1,1],[1,0,1]],
    'X': [[1,0,1],[1,0,1],[0,1,0],[1,0,1],[1,0,1]],
    'Y': [[1,0,1],[1,0,1],[0,1,0],[0,1,0],[0,1,0]],
    'Z': [[1,1,1],[0,0,1],[0,1,0],[1,0,0],[1,1,1]],
    ' ': [[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0]],
    '-': [[0,0,0],[0,0,0],[1,1,1],[0,0,0],[0,0,0]],
    '.': [[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,1,0]],
    ',': [[0,0,0],[0,0,0],[0,0,0],[0,1,0],[1,0,0]],
    "'": [[0,1,0],[0,1,0],[0,0,0],[0,0,0],[0,0,0]],
    '"': [[1,0,1],[1,0,1],[0,0,0],[0,0,0],[0,0,0]],
    '!': [[0,1,0],[0,1,0],[0,1,0],[0,0,0],[0,1,0]],
    '?': [[1,1,0],[0,0,1],[0,1,0],[0,0,0],[0,1,0]],
    '(': [[0,1,0],[1,0,0],[1,0,0],[1,0,0],[0,1,0]],
    ')': [[0,1,0],[0,0,1],[0,0,1],[0,0,1],[0,1,0]],
    '/': [[0,0,1],[0,0,1],[0,1,0],[1,0,0],[1,0,0]],
    '&': [[0,1,0],[1,0,1],[0,1,0],[1,0,1],[0,1,1]],
    ':': [[0,0,0],[0,1,0],[0,0,0],[0,1,0],[0,0,0]],
    '+': [[0,0,0],[0,1,0],[1,1,1],[0,1,0],[0,0,0]],
    # Direction arrows (chevron style)
    '^': [[0,1,0],[1,0,1],[0,0,0],[0,0,0],[0,0,0]],
    'v': [[0,0,0],[0,0,0],[0,0,0],[1,0,1],[0,1,0]],
}


def ease_in_out(progress, ease_zone=0.2):
    """Apply gentle easing at ends, linear in middle.

    Creates smooth acceleration at start and deceleration at end,
    with constant velocity through the middle section.

    Args:
        progress: Value from 0.0 to 1.0 representing position in animation
        ease_zone: Fraction of animation to ease at each end (default 0.2 = 20%)

    Returns:
        Eased progress value from 0.0 to 1.0
    """
    if progress <= 0:
        return 0.0
    if progress >= 1:
        return 1.0

    if progress < ease_zone:
        # Quadratic ease in (slow start, accelerate)
        t = progress / ease_zone
        return 0.5 * ease_zone * t * t
    elif progress > 1 - ease_zone:
        # Quadratic ease out (decelerate, slow end)
        t = (1 - progress) / ease_zone
        return 1 - 0.5 * ease_zone * t * t
    else:
        # Linear middle - constant velocity
        mid_progress = (progress - ease_zone) / (1 - 2 * ease_zone)
        return 0.5 * ease_zone + mid_progress * (1 - ease_zone)


def draw_char(frame, char, x, y, color, width, height, font=None):
    """Draw a single 3x5 character to a frame buffer.

    Args:
        frame: numpy array of shape (height, width, 3)
        char: Character to draw
        x, y: Top-left position
        color: RGB tuple (r, g, b)
        width, height: Frame dimensions for bounds checking
        font: Font dictionary to use (default: FONT_3X5)
    """
    if font is None:
        font = FONT_3X5

    char = char.upper()
    if char not in font:
        return

    pattern = font[char]
    for dy, row in enumerate(pattern):
        for dx, pixel in enumerate(row):
            if pixel:
                px, py = x + dx, y + dy
                if 0 <= px < width and 0 <= py < height:
                    frame[py, px] = color


def draw_text(frame, text, x, y, color, width, height, font=None):
    """Draw a text string to a frame buffer.

    Args:
        frame: numpy array of shape (height, width, 3)
        text: String to draw
        x, y: Top-left position
        color: RGB tuple (r, g, b)
        width, height: Frame dimensions for bounds checking
        font: Font dictionary to use (default: FONT_3X5)
    """
    cursor = x
    for char in text:
        draw_char(frame, char, cursor, y, color, width, height, font)
        cursor += 4  # 3px char + 1px spacing


def draw_char_clipped(frame, char, x, y, color, clip_left, clip_right, width, height, font=None):
    """Draw a character with horizontal clipping for partial visibility.

    Args:
        frame: numpy array of shape (height, width, 3)
        char: Character to draw
        x, y: Top-left position
        color: RGB tuple (r, g, b)
        clip_left, clip_right: Horizontal clipping bounds
        width, height: Frame dimensions for bounds checking
        font: Font dictionary to use (default: FONT_3X5)
    """
    if font is None:
        font = FONT_3X5

    char = char.upper()
    if char not in font:
        return

    pattern = font[char]
    for dy, row in enumerate(pattern):
        for dx, pixel in enumerate(row):
            if pixel:
                px, py = x + dx, y + dy
                if clip_left <= px < clip_right:
                    if 0 <= px < width and 0 <= py < height:
                        frame[py, px] = color


def draw_scrolling_text(frame, text, x, y, max_width, color, scroll_offset,
                        width, height, font=None, gap=20, pause_duration=60):
    """Draw text that scrolls horizontally if too wide.

    Args:
        frame: numpy array of shape (height, width, 3)
        text: String to draw
        x, y: Top-left position
        max_width: Maximum width before scrolling
        color: RGB tuple (r, g, b)
        scroll_offset: Current scroll position (increments each tick)
        width, height: Frame dimensions
        font: Font dictionary to use (default: FONT_3X5)
        gap: Pixel gap between text repeats when scrolling
        pause_duration: Ticks to pause at start position
    """
    text_width = len(text) * 4

    if text_width <= max_width:
        draw_text(frame, text, x, y, color, width, height, font)
    else:
        total_scroll = text_width + gap
        cycle_length = total_scroll + pause_duration
        cycle_pos = int(scroll_offset) % cycle_length

        if cycle_pos < pause_duration:
            scroll_pos = 0
        else:
            scroll_ticks = cycle_pos - pause_duration
            progress = scroll_ticks / total_scroll
            eased_progress = ease_in_out(progress)
            scroll_pos = int(eased_progress * total_scroll)

        cursor = x - scroll_pos
        padded_text = text + "     " + text  # 5 space gap

        for char in padded_text:
            char_end = cursor + 3

            if char_end >= x and cursor < x + max_width:
                draw_char_clipped(frame, char, cursor, y, color, x, x + max_width, width, height, font)

            if cursor >= x + max_width:
                break
            cursor += 4
