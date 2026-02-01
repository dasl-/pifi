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
    'N': [[1,1,1],[1,0,1],[1,0,1],[1,0,1],[1,0,1]],  # Lowercase-style n (arch + two legs)
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


def get_word_color(word_idx, word_timings, current_position, colors):
    """Determine color for a word based on current playback position.

    Args:
        word_idx: Index of the word in word_timings
        word_timings: List of (timestamp, word) tuples
        current_position: Current song position in seconds
        colors: Dict with 'sung', 'current', 'upcoming' RGB tuples

    Returns:
        RGB tuple for this word
    """
    if word_idx >= len(word_timings):
        return colors['upcoming']

    word_start = word_timings[word_idx][0]

    # Get next word start time (or a large value if last word)
    if word_idx + 1 < len(word_timings):
        next_start = word_timings[word_idx + 1][0]
    else:
        next_start = word_start + 2.0  # Assume 2 seconds for last word

    if current_position < word_start:
        return colors['upcoming']
    elif current_position < next_start:
        return colors['current']
    else:
        return colors['sung']


def draw_text_with_word_colors(frame, word_timings, x, y, current_position,
                                colors, width, height, font=None):
    """Draw text with per-word colors based on playback position.

    Args:
        frame: numpy array of shape (height, width, 3)
        word_timings: List of (timestamp, word) tuples
        x, y: Top-left position
        current_position: Current song position in seconds
        colors: Dict with 'sung', 'current', 'upcoming' RGB tuples
        width, height: Frame dimensions for bounds checking
        font: Font dictionary to use (default: FONT_3X5)
    """
    cursor = x
    for word_idx, (_, word) in enumerate(word_timings):
        color = get_word_color(word_idx, word_timings, current_position, colors)

        for char in word:
            draw_char(frame, char, cursor, y, color, width, height, font)
            cursor += 4

        # Add space after word (except last)
        if word_idx < len(word_timings) - 1:
            cursor += 4  # Space character width


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
                        width, height, font=None, gap=20, pause_duration=60,
                        complete_in_ticks=None, loop=True):
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
        complete_in_ticks: If provided, ensures scroll completes by this tick count.
                          scroll_offset is treated as current tick count.
                          - If deadline requires faster than default: scrolls faster
                          - If deadline allows default speed: uses default, aligned to finish on time
                          Easing is applied. Useful for timed scroll that must finish by a deadline.
        loop: If True (default), loops continuously when time allows.
              If False with complete_in_ticks, scrolls once and holds at end.
    """
    text_width = len(text) * 4

    if text_width <= max_width:
        draw_text(frame, text, x, y, color, width, height, font)
    else:
        total_scroll = text_width - max_width  # Distance to scroll

        if complete_in_ticks is not None and complete_in_ticks > 0:
            # Calculate default speed: ~1 pixel per 2 ticks (smooth default)
            default_ticks_per_scroll = total_scroll * 2 + pause_duration

            if complete_in_ticks < default_ticks_per_scroll:
                # Deadline requires faster than default - use timed mode (no pause)
                progress = min(1.0, scroll_offset / complete_in_ticks)
                eased_progress = ease_in_out(progress)
                scroll_pos = int(eased_progress * total_scroll)
            elif not loop:
                # No looping - scroll once at default speed, hold at end
                scroll_ticks = default_ticks_per_scroll - pause_duration
                if scroll_offset < pause_duration:
                    scroll_pos = 0
                else:
                    progress = min(1.0, (scroll_offset - pause_duration) / scroll_ticks)
                    eased_progress = ease_in_out(progress)
                    scroll_pos = int(eased_progress * total_scroll)
            else:
                # Looping mode - scroll text fully off screen for smooth loop
                loop_scroll = text_width + gap
                loop_ticks = loop_scroll * 2 + pause_duration  # Default speed for full loop

                # Calculate cycles aligned to finish on deadline
                num_cycles = max(1, int(complete_in_ticks / loop_ticks))
                adjusted_cycle = complete_in_ticks / num_cycles

                cycle_pos = scroll_offset % adjusted_cycle

                if cycle_pos < pause_duration:
                    scroll_pos = 0
                else:
                    scroll_progress = (cycle_pos - pause_duration) / (adjusted_cycle - pause_duration)
                    eased_progress = ease_in_out(min(1.0, scroll_progress))
                    scroll_pos = int(eased_progress * loop_scroll)
        else:
            # Normal looping scroll mode
            loop_scroll = text_width + gap  # Include gap for looping
            cycle_length = loop_scroll + pause_duration
            cycle_pos = int(scroll_offset) % cycle_length

            if cycle_pos < pause_duration:
                scroll_pos = 0
            else:
                scroll_ticks = cycle_pos - pause_duration
                progress = scroll_ticks / loop_scroll
                eased_progress = ease_in_out(progress)
                scroll_pos = int(eased_progress * loop_scroll)

        cursor = x - scroll_pos
        padded_text = text + "     " + text  # 5 space gap for looping

        for char in padded_text:
            char_end = cursor + 3

            if char_end >= x and cursor < x + max_width:
                draw_char_clipped(frame, char, cursor, y, color, x, x + max_width, width, height, font)

            if cursor >= x + max_width:
                break
            cursor += 4


def draw_scrolling_text_with_words(frame, word_timings, x, y, max_width,
                                   current_position, colors, scroll_offset,
                                   width, height, font=None, gap=20, pause_duration=60,
                                   complete_in_ticks=None, loop=True):
    """Draw scrolling text with per-word colors based on playback position.

    Similar to draw_scrolling_text but colors each word based on whether
    it has been sung, is current, or is upcoming.

    Args:
        frame: numpy array of shape (height, width, 3)
        word_timings: List of (timestamp, word) tuples
        x, y: Top-left position
        max_width: Maximum width before scrolling
        current_position: Current song position in seconds
        colors: Dict with 'sung', 'current', 'upcoming' RGB tuples
        scroll_offset: Current scroll position (increments each tick)
        width, height: Frame dimensions
        font: Font dictionary to use (default: FONT_3X5)
        gap: Pixel gap between text repeats when scrolling
        pause_duration: Ticks to pause at start position
        complete_in_ticks: If provided, ensures scroll completes by this tick count
        loop: If True, loops continuously; if False, scrolls once and holds
    """
    # Build full text and character-to-word mapping
    chars_with_colors = []
    for word_idx, (_, word) in enumerate(word_timings):
        color = get_word_color(word_idx, word_timings, current_position, colors)
        for char in word:
            chars_with_colors.append((char, color))
        # Add space after word (except last)
        if word_idx < len(word_timings) - 1:
            chars_with_colors.append((' ', color))

    text_width = len(chars_with_colors) * 4

    if text_width <= max_width:
        # No scrolling needed - just draw with word colors
        cursor = x
        for char, color in chars_with_colors:
            draw_char(frame, char, cursor, y, color, width, height, font)
            cursor += 4
    else:
        total_scroll = text_width - max_width

        if complete_in_ticks is not None and complete_in_ticks > 0:
            default_ticks_per_scroll = total_scroll * 2 + pause_duration

            if complete_in_ticks < default_ticks_per_scroll:
                progress = min(1.0, scroll_offset / complete_in_ticks)
                eased_progress = ease_in_out(progress)
                scroll_pos = int(eased_progress * total_scroll)
            elif not loop:
                scroll_ticks = default_ticks_per_scroll - pause_duration
                if scroll_offset < pause_duration:
                    scroll_pos = 0
                else:
                    progress = min(1.0, (scroll_offset - pause_duration) / scroll_ticks)
                    eased_progress = ease_in_out(progress)
                    scroll_pos = int(eased_progress * total_scroll)
            else:
                loop_scroll = text_width + gap
                loop_ticks = loop_scroll * 2 + pause_duration

                num_cycles = max(1, int(complete_in_ticks / loop_ticks))
                adjusted_cycle = complete_in_ticks / num_cycles

                cycle_pos = scroll_offset % adjusted_cycle

                if cycle_pos < pause_duration:
                    scroll_pos = 0
                else:
                    scroll_progress = (cycle_pos - pause_duration) / (adjusted_cycle - pause_duration)
                    eased_progress = ease_in_out(min(1.0, scroll_progress))
                    scroll_pos = int(eased_progress * loop_scroll)
        else:
            loop_scroll = text_width + gap
            cycle_length = loop_scroll + pause_duration
            cycle_pos = int(scroll_offset) % cycle_length

            if cycle_pos < pause_duration:
                scroll_pos = 0
            else:
                scroll_ticks = cycle_pos - pause_duration
                progress = scroll_ticks / loop_scroll
                eased_progress = ease_in_out(progress)
                scroll_pos = int(eased_progress * loop_scroll)

        # Draw with clipping and word colors
        # Pad the text for looping
        gap_chars = [(' ', colors['upcoming'])] * 5
        padded_chars = chars_with_colors + gap_chars + chars_with_colors

        cursor = x - scroll_pos
        for char, color in padded_chars:
            char_end = cursor + 3

            if char_end >= x and cursor < x + max_width:
                draw_char_clipped(frame, char, cursor, y, color, x, x + max_width, width, height, font)

            if cursor >= x + max_width:
                break
            cursor += 4
