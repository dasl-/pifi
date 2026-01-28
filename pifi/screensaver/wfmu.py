"""
WFMU Radio Screensaver.

Displays the current track and artist from WFMU radio streams.
Uses WFMU's XML API to fetch now-playing information.
"""

import numpy as np
import time
import threading
import xml.etree.ElementTree as ET

from pifi.config import Config
from pifi.led.ledframeplayer import LedFramePlayer
from pifi.logger import Logger
from pifi.screensaver.screensaver import Screensaver
from pifi.screensaver import textutils


class Wfmu(Screensaver):
    """WFMU radio now-playing display."""

    # Channel IDs for WFMU streams
    CHANNELS = {
        'wfmu': 0,           # Main WFMU 91.1
        'gtd': 4,            # Give the Drummer Radio
        'rock_n_soul': 6,    # Rock'n'Soul Radio
    }

    # Colors for display elements
    COLORS = {
        'show': (100, 180, 255),     # Light blue for show name
        'track': (255, 255, 255),    # White for track
        'artist': (255, 220, 100),   # Yellow for artist
        'divider': (80, 80, 80),     # Gray for dividers
        'logo': (255, 100, 50),      # Orange for WFMU logo
    }

    def __init__(self, led_frame_player=None):
        super().__init__(led_frame_player)
        self.__logger = Logger().set_namespace(self.__class__.__name__)

        if led_frame_player is None:
            led_frame_player = LedFramePlayer()
        self.__led_frame_player = led_frame_player

        self.__width = Config.get('leds.display_width')
        self.__height = Config.get('leds.display_height')

        # Configuration
        channel_name = Config.get('wfmu.channel', 'wfmu')
        self.__channel = self.CHANNELS.get(channel_name, 0)
        self.__update_interval = Config.get('wfmu.update_interval', 15)
        self.__max_ticks = Config.get('wfmu.max_ticks', 3000)
        self.__tick_sleep = Config.get('wfmu.tick_sleep', 0.05)

        # State
        self.__show_name = ""
        self.__artist = ""
        self.__title = ""
        self.__last_update = 0
        self.__error_message = None
        self.__fetch_in_progress = False
        self.__fetch_lock = threading.Lock()
        self.__tick_count = 0
        self.__scroll_offset = 0

        # Animation state for track changes
        self.__current_display = {'artist': '', 'title': '', 'show': ''}
        self.__target_display = {'artist': '', 'title': '', 'show': ''}
        self.__transition_progress = 1.0  # 0 = transitioning, 1 = stable

    def __fetch_now_playing(self):
        """Fetch current track info from WFMU API."""
        try:
            import requests

            url = f"https://wfmu.org/currentliveshows.php?xml=1&c={self.__channel}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            # Parse XML
            root = ET.fromstring(response.content)

            artist = root.findtext('artist', '').strip()
            title = root.findtext('title', '').strip()
            song = root.findtext('song', '').strip()
            show = root.findtext('show', '').strip()

            # Sometimes song contains "Title" by Artist format
            if not artist and not title and song:
                if '" by ' in song:
                    # Parse '"Title" by Artist' format
                    parts = song.split('" by ')
                    if len(parts) == 2:
                        title = parts[0].strip('"').strip()
                        artist = parts[1].strip()
                elif ' - ' in song:
                    # Parse 'Artist - Title' format
                    parts = song.split(' - ', 1)
                    if len(parts) == 2:
                        artist = parts[0].strip()
                        title = parts[1].strip()
                else:
                    title = song

            # Thread-safe update
            with self.__fetch_lock:
                # Check if track changed
                if artist != self.__artist or title != self.__title:
                    self.__target_display = {
                        'artist': artist.upper() if artist else '',
                        'title': title.upper() if title else '',
                        'show': show.upper() if show else '',
                    }
                    self.__transition_progress = 0.0

                self.__artist = artist
                self.__title = title
                self.__show_name = show
                self.__error_message = None

            self.__logger.info(f"Now playing: {artist} - {title} on {show}")

        except Exception as e:
            self.__logger.error(f"Failed to fetch now playing: {e}")
            with self.__fetch_lock:
                self.__error_message = "NO SIGNAL"

    def __start_background_fetch(self):
        """Start a background thread to fetch track info."""
        if self.__fetch_in_progress:
            return

        self.__fetch_in_progress = True
        thread = threading.Thread(target=self.__fetch_background, daemon=True)
        thread.start()

    def __fetch_background(self):
        """Fetch in background thread."""
        try:
            self.__fetch_now_playing()
        finally:
            self.__fetch_in_progress = False

    def play(self):
        """Run the screensaver."""
        self.__logger.info("Starting WFMU screensaver")

        # Start initial fetch
        self.__start_background_fetch()

        for tick in range(self.__max_ticks):
            # Periodic refresh
            current_time = time.time()
            if current_time - self.__last_update > self.__update_interval:
                self.__start_background_fetch()
                self.__last_update = current_time

            self.__render()
            time.sleep(self.__tick_sleep)

        self.__logger.info("WFMU screensaver ended")

    def __render(self):
        """Render the current track info."""
        frame = np.zeros((self.__height, self.__width, 3), dtype=np.uint8)

        # Thread-safe copy
        with self.__fetch_lock:
            error = self.__error_message
            target = dict(self.__target_display)

        # Update transition
        if self.__transition_progress < 1.0:
            self.__transition_progress = min(1.0, self.__transition_progress + 0.05)
            if self.__transition_progress >= 1.0:
                self.__current_display = target

        if error:
            self.__draw_text(frame, error, 2, self.__height // 2 - 2, (255, 100, 100))
        elif not self.__current_display['title'] and not self.__current_display['artist']:
            # Waiting for data
            self.__draw_text(frame, "WFMU", 2, 2, self.COLORS['logo'])
            dots = "." * ((self.__tick_count // 10) % 4)
            self.__draw_text(frame, f"TUNING{dots}", 2, 10, (100, 100, 100))
        else:
            self.__render_now_playing(frame)

        self.__tick_count += 1
        self.__scroll_offset += 1.0
        self.__led_frame_player.play_frame(frame)

    def __render_now_playing(self, frame):
        """Render the now playing info."""
        display = self.__current_display
        show = display['show']
        artist = display['artist']
        title = display['title']

        # Layout for 64x32 display:
        # Row 0-6: Show name (scrolling if needed)
        # Row 7: Divider line
        # Row 8-17: Track title (scrolling, larger area)
        # Row 18-23: Artist (scrolling)
        # Row 24-31: Visualization bars or just empty

        # Show name at top
        if show:
            show_y = 1
            show_width = len(show) * 4
            if show_width <= self.__width:
                self.__draw_text(frame, show, 1, show_y, self.COLORS['show'])
            else:
                self.__draw_scrolling_text(frame, show, 1, show_y, self.__width - 2, self.COLORS['show'])

        # Divider line
        divider_y = 8
        for x in range(self.__width):
            if x % 2 == 0:  # Dashed line
                frame[divider_y, x] = self.COLORS['divider']

        # Track title - main focus, larger area
        if title:
            title_y = 11
            title_width = len(title) * 4
            if title_width <= self.__width:
                # Center if it fits
                x_offset = max(0, (self.__width - title_width) // 2)
                self.__draw_text(frame, title, x_offset, title_y, self.COLORS['track'])
            else:
                self.__draw_scrolling_text(frame, title, 0, title_y, self.__width, self.COLORS['track'])

        # Artist name
        if artist:
            artist_y = 19
            artist_width = len(artist) * 4
            if artist_width <= self.__width:
                x_offset = max(0, (self.__width - artist_width) // 2)
                self.__draw_text(frame, artist, x_offset, artist_y, self.COLORS['artist'])
            else:
                self.__draw_scrolling_text(frame, artist, 0, artist_y, self.__width, self.COLORS['artist'])

        # Audio visualization bars at bottom
        self.__draw_audio_bars(frame, 26)

    def __draw_audio_bars(self, frame, y):
        """Draw animated audio visualization bars."""
        import math
        bar_width = 3
        bar_gap = 1
        num_bars = self.__width // (bar_width + bar_gap)

        for i in range(num_bars):
            # Create pseudo-random but smooth animation
            phase = i * 0.5 + self.__tick_count * 0.15
            height = int(3 + 3 * abs(math.sin(phase)))

            x = i * (bar_width + bar_gap)
            for dy in range(height):
                bar_y = self.__height - 1 - dy
                if bar_y >= y:
                    # Gradient from orange at bottom to yellow at top
                    intensity = 1.0 - (dy / 6.0)
                    color = (
                        int(255 * intensity),
                        int(150 * intensity + 50),
                        int(50 * intensity)
                    )
                    for dx in range(bar_width):
                        if x + dx < self.__width:
                            frame[bar_y, x + dx] = color

    def __draw_scrolling_text(self, frame, text, x, y, max_width, color):
        """Draw scrolling text with easing."""
        textutils.draw_scrolling_text(
            frame, text, x, y, max_width, color,
            self.__scroll_offset, self.__width, self.__height
        )

    def __draw_text(self, frame, text, x, y, color):
        """Draw a text string."""
        textutils.draw_text(frame, text, x, y, color, self.__width, self.__height)

    @classmethod
    def get_id(cls) -> str:
        return 'wfmu'

    @classmethod
    def get_name(cls) -> str:
        return 'WFMU Radio'

    @classmethod
    def get_description(cls) -> str:
        return 'Shows current track playing on WFMU radio'
