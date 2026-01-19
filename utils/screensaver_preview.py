#!/usr/bin/env python3
"""
Terminal-based screensaver preview tool.

Renders screensavers to the terminal using ANSI 24-bit colors,
allowing you to test and preview without a Raspberry Pi.

Usage:
    python utils/screensaver_preview.py [screensaver_name] [options]

Examples:
    python utils/screensaver_preview.py cosmic_dream
    python utils/screensaver_preview.py boids --width 32 --height 16
    python utils/screensaver_preview.py game_of_life --scale 2
"""

import argparse
import os
import sys
import time
import signal

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Build registry dynamically from ScreensaverManager
from pifi.screensaver.screensavermanager import ScreensaverManager

SCREENSAVER_REGISTRY = []
for screensaver_id, cls in ScreensaverManager.SCREENSAVER_CLASSES.items():
    module_path = cls.__module__
    class_name = cls.__name__
    name = cls.get_id()
    description = cls.get_description()
    config_key = cls.get_id()

    SCREENSAVER_REGISTRY.append((name, module_path, class_name, description, config_key))

SCREENSAVER_REGISTRY.sort(key=lambda x: x[0])

# Build lookup dicts
SCREENSAVER_BY_NAME = {s[0]: s for s in SCREENSAVER_REGISTRY}
# Also allow aliases without underscores
for s in SCREENSAVER_REGISTRY:
    alias = s[0].replace('_', '')
    if alias != s[0]:
        SCREENSAVER_BY_NAME[alias] = s


class TerminalFramePlayer:
    """
    Mock LedFramePlayer that renders frames to the terminal using ANSI colors.

    Uses the upper-half block character (▀) to render 2 vertical pixels per
    character cell - foreground color for top pixel, background for bottom.
    """

    # Upper half block - foreground is top pixel, background is bottom
    HALF_BLOCK = '▀'

    def __init__(self, width, height, scale=1):
        self.width = width
        self.height = height
        self.scale = scale
        self._frame_count = 0
        self._start_time = time.time()

        # Hide cursor and clear screen
        sys.stdout.write('\033[?25l')  # Hide cursor
        sys.stdout.write('\033[2J')     # Clear screen
        sys.stdout.flush()

    def play_frame(self, frame):
        """Render a frame to the terminal."""
        self._render_frame(frame)
        self._frame_count += 1

    def fade_to_frame(self, frame):
        """For terminal preview, just render directly (no fade)."""
        self.play_frame(frame)

    def clear_screen(self):
        """Clear the terminal."""
        sys.stdout.write('\033[2J')
        sys.stdout.flush()

    def _render_frame(self, frame):
        """Render frame using ANSI 24-bit color codes."""
        output = []

        # Move cursor to home position
        output.append('\033[H')

        # Process 2 rows at a time (top and bottom pixel per character)
        for y in range(0, self.height, 2):
            row_chars = []
            for x in range(self.width):
                # Top pixel (foreground)
                r1, g1, b1 = int(frame[y, x, 0]), int(frame[y, x, 1]), int(frame[y, x, 2])

                # Bottom pixel (background) - check bounds
                if y + 1 < self.height:
                    r2, g2, b2 = int(frame[y+1, x, 0]), int(frame[y+1, x, 1]), int(frame[y+1, x, 2])
                else:
                    r2, g2, b2 = 0, 0, 0

                # ANSI 24-bit color: \033[38;2;R;G;Bm for foreground, \033[48;2;R;G;Bm for background
                char = f'\033[38;2;{r1};{g1};{b1}m\033[48;2;{r2};{g2};{b2}m{self.HALF_BLOCK * self.scale}'
                row_chars.append(char)

            # Reset colors at end of row and add newline
            output.append(''.join(row_chars) + '\033[0m\n')

        # Add FPS counter
        elapsed = time.time() - self._start_time
        if elapsed > 0:
            fps = self._frame_count / elapsed
            output.append(f'\033[0mFrame: {self._frame_count} | FPS: {fps:.1f} | Press Ctrl+C to exit')

        sys.stdout.write(''.join(output))
        sys.stdout.flush()

    def cleanup(self):
        """Restore terminal state."""
        sys.stdout.write('\033[0m')     # Reset colors
        sys.stdout.write('\033[?25h')   # Show cursor
        sys.stdout.write('\n')
        sys.stdout.flush()


def setup_mock_config(width, height):
    """Set up a mock configuration for testing."""
    from pifi.config import Config

    # Load actual config files using existing Config class
    # This reads and merges default_config.json and config.json
    Config.load_config_if_not_loaded(should_set_log_level=False)

    # Override LED configuration for terminal preview
    Config.set('log_level', 'warning')
    Config.set('leds.driver', 'terminal')
    Config.set('leds.display_width', width)
    Config.set('leds.display_height', height)
    Config.set('leds.brightness', 31)
    Config.set('leds.flip_x', False)
    Config.set('leds.flip_y', False)


def get_screensaver(name, frame_player):
    """Get a screensaver instance by name."""
    from pifi.screensaver.screensavermanager import ScreensaverManager

    name = name.lower().replace('-', '_').replace(' ', '_')

    if name not in ScreensaverManager.SCREENSAVER_CLASSES:
        available = [cls.get_id() for cls in ScreensaverManager.SCREENSAVER_CLASSES.values()]
        raise ValueError(f"Unknown screensaver: {name}\nAvailable: {', '.join(available)}")

    cls = ScreensaverManager.SCREENSAVER_CLASSES[name]
    return cls(led_frame_player=frame_player)


def list_screensavers():
    """Print list of available screensavers."""
    print("Available screensavers:")
    max_name_len = max(len(s[0]) for s in SCREENSAVER_REGISTRY)
    for name, _, _, description, _ in SCREENSAVER_REGISTRY:
        print(f"  {name:<{max_name_len}} - {description}")


def main():
    # Build epilog dynamically
    screensaver_list = "\n".join(
        f"  {name:<18} - {desc}"
        for name, _, _, desc, _ in SCREENSAVER_REGISTRY
    )

    parser = argparse.ArgumentParser(
        description='Preview screensavers in the terminal',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Available screensavers:
{screensaver_list}

Examples:
  %(prog)s cosmic_dream
  %(prog)s boids --width 48 --height 24
  %(prog)s game_of_life --scale 2
        """
    )

    parser.add_argument(
        'screensaver',
        nargs='?',
        default='cosmic_dream',
        help='Name of screensaver to preview (default: cosmic_dream)'
    )

    parser.add_argument(
        '-W', '--width',
        type=int,
        default=28,
        help='Display width in pixels (default: 28)'
    )

    parser.add_argument(
        '-H', '--height',
        type=int,
        default=18,
        help='Display height in pixels (default: 18)'
    )

    parser.add_argument(
        '-s', '--scale',
        type=int,
        default=1,
        help='Horizontal scale factor (default: 1 for ~square pixels, increase if too narrow)'
    )

    parser.add_argument(
        '-l', '--list',
        action='store_true',
        help='List available screensavers and exit'
    )

    args = parser.parse_args()

    if args.list:
        list_screensavers()
        return 0

    # Set up mock config
    setup_mock_config(args.width, args.height)

    # Create terminal frame player
    frame_player = TerminalFramePlayer(args.width, args.height, args.scale)

    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        frame_player.cleanup()
        print("\nExited.")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    try:
        # Get and run screensaver
        screensaver = get_screensaver(args.screensaver, frame_player)
        print(f"Starting {args.screensaver} ({args.width}x{args.height})...")
        time.sleep(1)
        screensaver.play()

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    except Exception as e:
        frame_player.cleanup()
        raise

    finally:
        frame_player.cleanup()

    return 0


if __name__ == '__main__':
    sys.exit(main())
