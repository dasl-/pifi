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


def get_word_color(word_idx, word_timings, current_position, colors, fade_duration=2.0,
                   word_start_times=None, current_time=None):
    """Determine color for a word based on current playback position.

    Words start bright and fade smoothly to sung color.

    Args:
        word_idx: Index of the word in word_timings
        word_timings: List of (timestamp, word) tuples
        current_position: Current song position in seconds
        colors: Dict with 'sung', 'current', 'upcoming' RGB tuples
        fade_duration: How long (seconds) for a word to fade from current to sung
        word_start_times: Optional dict mapping word_idx to wall-clock start time.
                         If provided, uses wall-clock time for smooth fades.
        current_time: Current wall-clock time (time.time()). Required if word_start_times is used.

    Returns:
        RGB tuple for this word
    """
    if word_idx >= len(word_timings):
        return colors['upcoming']

    word_start = word_timings[word_idx][0]

    if current_position < word_start:
        # Word hasn't started yet
        return colors['upcoming']
    else:
        # Word has started - calculate fade
        # Use wall-clock time if available for smooth animation
        if word_start_times is not None and current_time is not None:
            if word_idx not in word_start_times:
                # First time seeing this word as active - record wall-clock time
                word_start_times[word_idx] = current_time
            time_since_start = current_time - word_start_times[word_idx]
        else:
            # Fallback to song position (may be jerky)
            time_since_start = current_position - word_start

        if time_since_start >= fade_duration:
            # Fully faded to sung
            return colors['sung']
        else:
            # Smooth fade from current to sung
            current_color = colors['current']
            sung_color = colors['sung']

            # Linear progress for smooth fade
            fade_progress = time_since_start / fade_duration

            # Interpolate each channel
            r = current_color[0] + (sung_color[0] - current_color[0]) * fade_progress
            g = current_color[1] + (sung_color[1] - current_color[1]) * fade_progress
            b = current_color[2] + (sung_color[2] - current_color[2]) * fade_progress

            return (int(r), int(g), int(b))


def get_current_word_index(word_timings, current_position):
    """Find the index of the current word based on playback position.

    Returns:
        Tuple of (word_index, progress_within_word) where progress is 0-1
    """
    if not word_timings:
        return 0, 0.0

    current_idx = 0
    for i, (timestamp, _) in enumerate(word_timings):
        if current_position >= timestamp:
            current_idx = i
        else:
            break

    # Calculate progress within current word
    word_start = word_timings[current_idx][0]
    if current_idx + 1 < len(word_timings):
        word_end = word_timings[current_idx + 1][0]
    else:
        word_end = word_start + 2.0

    if word_end > word_start:
        progress = (current_position - word_start) / (word_end - word_start)
        progress = max(0.0, min(1.0, progress))
    else:
        progress = 0.0

    return current_idx, progress


def get_word_pixel_positions(word_timings):
    """Calculate the pixel x-position of each word's center.

    Returns:
        List of (center_x, width) for each word
    """
    positions = []
    cursor = 0
    for _, word in word_timings:
        word_width = len(word) * 4
        center = cursor + word_width // 2
        positions.append((center, word_width))
        cursor += word_width + 4  # word + space
    return positions


def draw_text_with_word_colors(frame, word_timings, x, y, current_position,
                                colors, width, height, font=None,
                                word_start_times=None, current_time=None):
    """Draw text with per-word colors based on playback position.

    Args:
        frame: numpy array of shape (height, width, 3)
        word_timings: List of (timestamp, word) tuples
        x, y: Top-left position
        current_position: Current song position in seconds
        colors: Dict with 'sung', 'current', 'upcoming' RGB tuples
        width, height: Frame dimensions for bounds checking
        font: Font dictionary to use (default: FONT_3X5)
        word_start_times: Optional dict for tracking word start times (for smooth fades)
        current_time: Current wall-clock time
    """
    cursor = x
    for word_idx, (_, word) in enumerate(word_timings):
        color = get_word_color(word_idx, word_timings, current_position, colors,
                               word_start_times=word_start_times, current_time=current_time)

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


def draw_char_clipped_vertical(frame, char, x, y, color, clip_bottom, width, height, font=None):
    """Draw a character with vertical clipping for partial visibility.

    Args:
        frame: numpy array of shape (height, width, 3)
        char: Character to draw
        x, y: Top-left position
        color: RGB tuple (r, g, b)
        clip_bottom: Y coordinate to stop drawing at (exclusive)
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
                if py < clip_bottom:
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
                                   complete_in_ticks=None, loop=True, word_sync=False):
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
        word_sync: If True, scroll follows current word position (keeps it centered)
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

        if word_sync:
            # Word-driven scrolling: scroll to keep current word visible
            word_positions = get_word_pixel_positions(word_timings)
            current_word_idx, word_progress = get_current_word_index(word_timings, current_position)

            # Target position: 1/3 from left for comfortable reading
            target_x = max_width // 3

            # Get current word center, interpolate toward next word
            if current_word_idx < len(word_positions):
                current_center = word_positions[current_word_idx][0]
                if current_word_idx + 1 < len(word_positions):
                    next_center = word_positions[current_word_idx + 1][0]
                    # Smooth interpolation between words
                    center = current_center + (next_center - current_center) * word_progress
                else:
                    center = current_center
            else:
                center = 0

            # Scroll so the current word center is at target_x
            scroll_pos = int(center - target_x)
            # Clamp to valid range
            scroll_pos = max(0, min(total_scroll, scroll_pos))

        elif complete_in_ticks is not None and complete_in_ticks > 0:
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


def split_text_to_lines(text, max_chars_per_line):
    """Split text into lines that fit within max character width.

    Tries to split at word boundaries (spaces) when possible.

    Args:
        text: Text to split
        max_chars_per_line: Maximum characters per line

    Returns:
        List of line strings
    """
    words = text.split(' ')
    lines = []
    current_line = ""

    for word in words:
        if not current_line:
            current_line = word
        elif len(current_line) + 1 + len(word) <= max_chars_per_line:
            current_line += " " + word
        else:
            lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    return lines


def get_word_line_positions(word_timings, max_chars_per_line):
    """Calculate which line each word belongs to when text is wrapped.

    Args:
        word_timings: List of (timestamp, word) tuples
        max_chars_per_line: Maximum characters per line

    Returns:
        List of (line_index, char_offset_in_line) for each word
    """
    positions = []
    current_line = 0
    current_char = 0

    for _, word in word_timings:
        word_len = len(word)

        # Check if word fits on current line
        if current_char > 0 and current_char + 1 + word_len > max_chars_per_line:
            # Move to next line
            current_line += 1
            current_char = 0

        positions.append((current_line, current_char))
        current_char += word_len + 1  # +1 for space

    return positions


def draw_vertical_scroll_text_with_words(frame, word_timings, x, y, max_width,
                                          current_position, colors, width, height,
                                          line_height=7, visible_lines=2,
                                          word_complete_delay=0.3, anticipation=0.3,
                                          font=None, word_start_times=None, current_time=None):
    """Draw wrapped text that scrolls vertically based on word completion.

    Splits long text into multiple lines and shows 2 at a time.
    Scrolls up when the last word on the top visible line is complete.

    Args:
        frame: numpy array of shape (height, width, 3)
        word_timings: List of (timestamp, word) tuples
        x, y: Top-left position
        max_width: Maximum width for text
        current_position: Current song position in seconds
        colors: Dict with 'sung', 'current', 'upcoming' RGB tuples
        width, height: Frame dimensions
        line_height: Pixels per line (including spacing)
        visible_lines: Number of lines to show at once
        word_complete_delay: Seconds after word starts before considering it "complete"
        anticipation: Seconds to show next lines before they're triggered
        font: Font dictionary to use (default: FONT_3X5)
        word_start_times: Optional dict for tracking word start times (for smooth fades)
        current_time: Current wall-clock time
    """
    max_chars_per_line = max_width // 4

    # Build lines from word_timings
    word_line_positions = get_word_line_positions(word_timings, max_chars_per_line)
    num_lines = max(pos[0] for pos in word_line_positions) + 1 if word_line_positions else 1

    if num_lines <= visible_lines:
        # All lines fit, no scrolling needed
        target_scroll_line = 0
    else:
        # Find the first word index on each line
        first_word_per_line = {}
        for word_idx, (line_idx, _) in enumerate(word_line_positions):
            if line_idx not in first_word_per_line:
                first_word_per_line[line_idx] = word_idx

        # Scroll to keep the current/upcoming word's line visible
        # We want the line with the next word to sing to be on screen
        max_scroll = num_lines - visible_lines

        # Find which word is current/upcoming
        current_word_idx = 0
        for word_idx, (ts, _) in enumerate(word_timings):
            if current_position + anticipation >= ts:
                current_word_idx = word_idx
            else:
                break

        # Find which line that word is on
        if current_word_idx < len(word_line_positions):
            current_word_line = word_line_positions[current_word_idx][0]
        else:
            current_word_line = num_lines - 1

        # Scroll so current word's line is the top visible line
        # (but not beyond max_scroll)
        target_scroll_line = min(current_word_line, max_scroll)

    # Build lines with words
    lines = []
    for line_idx in range(num_lines):
        lines.append([])

    for word_idx, (line_idx, char_offset) in enumerate(word_line_positions):
        lines[line_idx].append((word_idx, word_timings[word_idx]))

    # Draw visible lines
    visible_start = target_scroll_line
    visible_end = min(num_lines, target_scroll_line + visible_lines)

    for line_idx in range(visible_start, visible_end):
        line_y = y + (line_idx - target_scroll_line) * line_height

        # Skip if off screen
        if line_y < -5 or line_y >= height:
            continue

        # Calculate x position to center this line
        line_text = ' '.join(word for _, (_, word) in lines[line_idx])
        line_pixel_width = len(line_text) * 4
        line_x = max(0, (max_width - line_pixel_width) // 2)

        # Draw each word with its color
        cursor = line_x
        for word_idx, (_, word) in lines[line_idx]:
            color = get_word_color(word_idx, word_timings, current_position, colors,
                                   word_start_times=word_start_times, current_time=current_time)

            for char in word:
                if 0 <= cursor < width and 0 <= line_y < height - 5:
                    draw_char(frame, char, cursor, line_y, color, width, height, font)
                cursor += 4

            # Space after word
            cursor += 4


def draw_vertical_scroll_text(frame, text, x, y, max_width, color, line_progress,
                               width, height, line_height=7, visible_lines=2,
                               clip_bottom=None, font=None):
    """Draw wrapped text that scrolls smoothly vertically with easing.

    Splits long text into multiple lines and scrolls continuously through them,
    using ease-in-out for smooth motion. Similar to horizontal scroll behavior.

    Args:
        frame: numpy array of shape (height, width, 3)
        text: Text to display
        x, y: Top-left position
        max_width: Maximum width for text
        color: RGB tuple for text color
        line_progress: Progress through the line (0-1), controls vertical scroll
        width, height: Frame dimensions
        line_height: Pixels per line (including spacing)
        visible_lines: Number of lines to show at once
        clip_bottom: Y coordinate to stop drawing at (exclusive). If None, no clipping.
        font: Font dictionary to use (default: FONT_3X5)
    """
    max_chars_per_line = max_width // 4

    # Split text into lines
    lines = split_text_to_lines(text, max_chars_per_line)
    num_lines = len(lines)

    if num_lines <= visible_lines:
        # All lines fit, just draw centered
        for line_idx, line in enumerate(lines):
            line_y = y + line_idx * line_height
            line_pixel_width = len(line) * 4
            line_x = max(0, (max_width - line_pixel_width) // 2)
            draw_text(frame, line, line_x, line_y, color, width, height, font)
        return

    # Smooth continuous scroll with easing
    # Total scroll distance in pixels
    total_scroll_pixels = (num_lines - visible_lines) * line_height

    # Apply easing to progress for smooth start/end
    eased_progress = ease_in_out(line_progress)

    # Calculate pixel offset
    scroll_y = int(eased_progress * total_scroll_pixels)

    # Determine effective clip boundary
    effective_clip = clip_bottom if clip_bottom is not None else height

    # Draw all lines that might be visible (with pixel-level offset)
    for line_idx, line in enumerate(lines):
        # Calculate y position with scroll offset
        line_y = y + (line_idx * line_height) - scroll_y

        # Skip lines that are completely off screen or below clip
        if line_y < y - line_height or line_y >= effective_clip:
            continue

        # Skip if line would be completely below clip
        if line_y + 5 <= 0:  # 5 is font height
            continue

        line_pixel_width = len(line) * 4
        line_x = max(0, (max_width - line_pixel_width) // 2)

        # Draw with vertical clipping
        if clip_bottom is not None and line_y + 5 > clip_bottom:
            # Need to clip - draw character by character with pixel clipping
            cursor = line_x
            for char in line:
                draw_char_clipped_vertical(frame, char, cursor, line_y, color,
                                           clip_bottom, width, height, font)
                cursor += 4
        else:
            draw_text(frame, line, line_x, line_y, color, width, height, font)
