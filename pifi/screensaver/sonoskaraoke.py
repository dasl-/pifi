"""
Sonos Karaoke Screensaver.

Displays synced lyrics from currently playing Sonos track.
Uses SoCo for Sonos integration and syncedlyrics for lyrics fetching.
"""

import numpy as np
import re
import threading
import time

from pifi.config import Config
from pifi.led.ledframeplayer import LedFramePlayer
from pifi.logger import Logger
from pifi.screensaver.screensaver import Screensaver
from pifi.screensaver import textutils


class SonosKaraoke(Screensaver):
    """Sonos karaoke lyrics display."""

    # Colors
    COLORS = {
        'current_line': (255, 255, 255),      # White - current lyric
        'next_line': (100, 100, 100),          # Gray - upcoming line
        'title': (255, 220, 100),              # Yellow - song title
        'artist': (100, 180, 255),             # Blue - artist
        'no_lyrics': (150, 150, 150),          # Gray - status messages
        'waiting': (80, 80, 80),               # Dim - waiting state
    }

    def __init__(self, led_frame_player=None):
        super().__init__(led_frame_player)
        self.__logger = Logger().set_namespace(self.__class__.__name__)

        if led_frame_player is None:
            led_frame_player = LedFramePlayer()
        self.__led_frame_player = led_frame_player

        self.__width = Config.get('leds.display_width', 64)
        self.__height = Config.get('leds.display_height', 32)

        # Configuration
        self.__speaker_name = Config.get('sonoskaraoke.speaker_name', None)
        self.__update_interval = Config.get('sonoskaraoke.update_interval', 0.5)
        self.__max_ticks = Config.get('sonoskaraoke.max_ticks', 6000)
        self.__tick_sleep = Config.get('sonoskaraoke.tick_sleep', 0.05)

        # State
        self.__current_track = None
        self.__current_artist = None
        self.__lyrics = []  # List of (timestamp_seconds, line_text)
        self.__position_seconds = 0
        self.__last_poll_time = 0  # For position interpolation
        self.__is_playing = False
        self.__last_fetch_time = 0
        self.__lyrics_available = False
        self.__lyrics_quality = None  # 'synced', 'plain', or None
        self.__fetch_in_progress = False
        self.__fetch_lock = threading.Lock()

        # Animation state
        self.__tick_count = 0
        self.__scroll_offset = 0
        self.__current_line_index = -1
        self.__line_scroll_offset = 0  # Per-line scroll, resets on line change
        self.__line_transition_progress = 1.0  # 0 = transitioning, 1 = stable

        # Sonos speaker reference
        self.__speaker = None

    def play(self):
        """Run the screensaver."""
        self.__logger.info("Starting Sonos Karaoke screensaver")

        # Try to discover/connect to Sonos
        if not self.__connect_to_sonos():
            self.__logger.error("Could not connect to Sonos")
            # Show error for a bit then exit
            for _ in range(100):
                self.__render_no_sonos()
                time.sleep(0.1)
            return

        self.__logger.info(f"Connected to Sonos: {self.__speaker.player_name}")

        for tick in range(self.__max_ticks):
            # Periodic Sonos polling
            current_time = time.time()
            if current_time - self.__last_fetch_time > self.__update_interval:
                self.__poll_sonos()
                self.__last_fetch_time = current_time

            self.__render()
            self.__tick_count += 1
            time.sleep(self.__tick_sleep)

        self.__logger.info("Sonos Karaoke screensaver ended")

    def __connect_to_sonos(self):
        """Connect to a Sonos speaker.

        Discovery priority:
        1. If speaker_name is configured, use that specific speaker
        2. Otherwise, prefer a speaker that is playing AND has track info
        3. Fall back to any playing speaker
        4. Fall back to any available speaker
        """
        try:
            import soco

            speakers = soco.discover(timeout=5)
            if not speakers:
                return False

            # Sort by name for deterministic ordering
            speaker_list = sorted(list(speakers), key=lambda s: s.player_name)
            self.__logger.info(f"Discovered {len(speaker_list)} Sonos speakers")

            if self.__speaker_name:
                # Find specific speaker by name
                for speaker in speaker_list:
                    if speaker.player_name.lower() == self.__speaker_name.lower():
                        self.__speaker = speaker
                        return True
                self.__logger.warning(
                    f"Speaker '{self.__speaker_name}' not found"
                )

            # Collect info about all speakers
            candidates = []
            for speaker in speaker_list:
                try:
                    transport = speaker.get_current_transport_info()
                    state = transport.get('current_transport_state', '')
                    track = speaker.get_current_track_info()
                    title = track.get('title', '')
                    artist = track.get('artist', '')
                    position = track.get('position', '')

                    is_coordinator = speaker.is_coordinator
                    has_track = bool(title and title.strip())
                    is_playing = state == 'PLAYING'
                    valid_position = position and 'NOT_IMPLEMENTED' not in position

                    self.__logger.info(
                        f"  {speaker.player_name}: state={state}, coordinator={is_coordinator}, "
                        f"title='{title[:30]}', valid_pos={valid_position}"
                    )

                    candidates.append({
                        'speaker': speaker,
                        'is_playing': is_playing,
                        'has_track': has_track,
                        'is_coordinator': is_coordinator,
                        'valid_position': valid_position,
                    })
                except Exception as e:
                    self.__logger.warning(f"  {speaker.player_name}: error - {e}")
                    continue

            # Score candidates: prefer playing + has track + coordinator + valid position
            def score(c):
                return (
                    c['is_playing'] * 8 +
                    c['has_track'] * 4 +
                    c['is_coordinator'] * 2 +
                    c['valid_position'] * 1
                )

            candidates.sort(key=score, reverse=True)

            if candidates:
                best = candidates[0]
                self.__speaker = best['speaker']
                self.__logger.info(
                    f"Selected: {self.__speaker.player_name} "
                    f"(score={score(best)}, playing={best['is_playing']}, track={best['has_track']})"
                )
                return True

            # Fallback
            self.__speaker = speaker_list[0]
            self.__logger.info(f"Fallback to: {self.__speaker.player_name}")
            return True

        except ImportError:
            self.__logger.error("soco library not installed. Run: pip install soco")
        except Exception as e:
            self.__logger.error(f"Error connecting to Sonos: {e}")

        return False

    def __poll_sonos(self):
        """Poll Sonos for current track info."""
        if not self.__speaker:
            self.__logger.debug("No speaker connected")
            return

        try:
            track_info = self.__speaker.get_current_track_info()
            transport_info = self.__speaker.get_current_transport_info()

            title = track_info.get('title', '')
            artist = track_info.get('artist', '')
            position = track_info.get('position', '0:00:00')

            # Parse position to seconds and record poll time for interpolation
            self.__position_seconds = self.__parse_time(position)
            self.__last_poll_time = time.time()

            # Check if playing
            state = transport_info.get('current_transport_state', '')
            self.__is_playing = state == 'PLAYING'

            self.__logger.debug(
                f"Poll: state={state}, title='{title}', artist='{artist}', pos={position}"
            )

            # Check if track changed
            if title != self.__current_track or artist != self.__current_artist:
                self.__current_track = title
                self.__current_artist = artist
                self.__lyrics = []
                self.__lyrics_available = False
                self.__current_line_index = -1

                if title and artist:
                    self.__start_lyrics_fetch(title, artist)

        except Exception as e:
            self.__logger.error(f"Error polling Sonos: {e}")

    def __parse_time(self, time_str):
        """Parse time string like '0:01:23' or '1:23' to seconds."""
        if not time_str or 'NOT_IMPLEMENTED' in time_str:
            return 0

        try:
            parts = time_str.split(':')
            if len(parts) == 3:
                h, m, s = parts
                return int(h) * 3600 + int(m) * 60 + int(s)
            elif len(parts) == 2:
                m, s = parts
                return int(m) * 60 + int(s)
            else:
                return int(parts[0])
        except (ValueError, IndexError):
            return 0

    def __start_lyrics_fetch(self, title, artist):
        """Start background lyrics fetch."""
        if self.__fetch_in_progress:
            return

        self.__fetch_in_progress = True
        thread = threading.Thread(
            target=self.__fetch_lyrics_background,
            args=(title, artist),
            daemon=True
        )
        thread.start()

    def __fetch_lyrics_background(self, title, artist):
        """Fetch lyrics in background thread."""
        try:
            search_query = f"{title} {artist}"
            self.__logger.info(f"Fetching lyrics for: '{search_query}'")

            import syncedlyrics

            # Try synced lyrics first
            lrc = syncedlyrics.search(search_query, synced_only=True)
            quality = 'synced'

            # Fall back to plain if no synced available
            if not lrc:
                self.__logger.debug("No synced lyrics, trying plain...")
                lrc = syncedlyrics.search(search_query, plain_only=True)
                quality = 'plain'

            if lrc:
                self.__logger.debug(f"Raw LRC response ({len(lrc)} chars): {lrc[:200]}...")
                lyrics = self.__parse_lrc(lrc)

                # Check if it's actually synced (has timestamps) or plain
                if lyrics and quality == 'synced':
                    # Verify timestamps are varied (not all 0)
                    timestamps = [l[0] for l in lyrics[:5]]
                    if len(set(timestamps)) <= 1:
                        quality = 'plain'
                        self.__logger.debug("Lyrics have no real timestamps, treating as plain")

                with self.__fetch_lock:
                    # Verify we're still on the same track
                    if self.__current_track == title and self.__current_artist == artist:
                        self.__lyrics = lyrics
                        self.__lyrics_available = len(lyrics) > 0
                        self.__lyrics_quality = quality if lyrics else None
                        self.__logger.info(f"Found {len(lyrics)} lyric lines (quality={quality})")
                        if lyrics:
                            self.__logger.debug(f"First line: [{lyrics[0][0]:.1f}s] {lyrics[0][1]}")
            else:
                self.__logger.info(f"No lyrics found for: '{search_query}'")
                with self.__fetch_lock:
                    self.__lyrics = []
                    self.__lyrics_available = False
                    self.__lyrics_quality = None

        except ImportError:
            self.__logger.error("syncedlyrics not installed. Run: pip install syncedlyrics")
        except Exception as e:
            self.__logger.error(f"Error fetching lyrics: {e}")
            import traceback
            self.__logger.debug(traceback.format_exc())
        finally:
            self.__fetch_in_progress = False

    def __parse_lrc(self, lrc_text):
        """Parse LRC format lyrics into list of (timestamp_seconds, line)."""
        lyrics = []

        # LRC format: [mm:ss.xx] lyrics text
        # or [mm:ss] lyrics text
        pattern = r'\[(\d+):(\d+)(?:\.(\d+))?\](.*)'

        for line in lrc_text.split('\n'):
            match = re.match(pattern, line)
            if match:
                minutes = int(match.group(1))
                seconds = int(match.group(2))
                # Centiseconds (optional)
                centiseconds = int(match.group(3)) if match.group(3) else 0
                text = match.group(4).strip()

                if text:  # Skip empty lines
                    timestamp = minutes * 60 + seconds + centiseconds / 100.0
                    lyrics.append((timestamp, text))

        # Sort by timestamp
        lyrics.sort(key=lambda x: x[0])
        return lyrics

    def __get_interpolated_position(self):
        """Get current position with interpolation between polls."""
        if not self.__is_playing or self.__last_poll_time == 0:
            return self.__position_seconds

        # Interpolate based on time since last poll
        elapsed = time.time() - self.__last_poll_time
        return self.__position_seconds + elapsed

    def __get_current_lyric_index(self):
        """Find the current lyric line based on playback position."""
        if not self.__lyrics:
            return -1

        position = self.__get_interpolated_position()

        # Find the last lyric that started before current position
        current_index = -1
        for i, (timestamp, _) in enumerate(self.__lyrics):
            if timestamp <= position:
                current_index = i
            else:
                break

        return current_index

    def __render(self):
        """Render the display."""
        frame = np.zeros((self.__height, self.__width, 3), dtype=np.uint8)

        if not self.__is_playing and not self.__current_track:
            if self.__tick_count % 100 == 0:
                self.__logger.debug("Render: waiting (no track, not playing)")
            self.__render_waiting(frame)
        elif not self.__lyrics_available:
            if self.__tick_count % 100 == 0:
                self.__logger.debug(f"Render: no lyrics (track='{self.__current_track}')")
            self.__render_no_lyrics(frame)
        else:
            self.__render_lyrics(frame)

        self.__scroll_offset += 0.5
        self.__led_frame_player.play_frame(frame)

    def __render_waiting(self, frame):
        """Render waiting for music state."""
        # Pulsing effect
        pulse = 0.5 + 0.5 * np.sin(self.__tick_count * 0.1)
        color = tuple(int(c * pulse) for c in self.COLORS['waiting'])

        text = "WAITING"
        x = (self.__width - len(text) * 4) // 2
        y = self.__height // 2 - 2
        textutils.draw_text(frame, text, x, y, color, self.__width, self.__height)

    def __render_no_sonos(self):
        """Render no Sonos found error."""
        frame = np.zeros((self.__height, self.__width, 3), dtype=np.uint8)

        textutils.draw_text(frame, "NO SONOS", 8, 8, (255, 100, 100), self.__width, self.__height)
        textutils.draw_text(frame, "FOUND", 16, 18, (255, 100, 100), self.__width, self.__height)

        self.__led_frame_player.play_frame(frame)

    def __render_no_lyrics(self, frame):
        """Render track info when no lyrics available."""
        # Show track and artist nicely centered vertically
        # Track at y=8, artist at y=18 for better spacing
        if self.__current_track:
            track_upper = self.__current_track.upper()
            textutils.draw_scrolling_text(
                frame, track_upper, 0, 8, self.__width,
                self.COLORS['title'], self.__scroll_offset,
                self.__width, self.__height
            )

        if self.__current_artist:
            artist_upper = self.__current_artist.upper()
            textutils.draw_scrolling_text(
                frame, artist_upper, 0, 18, self.__width,
                self.COLORS['artist'], self.__scroll_offset * 0.8,
                self.__width, self.__height
            )

        # Show loading indicator only while fetching
        if self.__fetch_in_progress:
            status = "..."
            x = (self.__width - len(status) * 4) // 2
            textutils.draw_text(frame, status, x, 26, self.COLORS['no_lyrics'], self.__width, self.__height)

    def __render_lyrics(self, frame):
        """Render synced lyrics."""
        current_idx = self.__get_current_lyric_index()

        # Detect line change - reset scroll for new line
        if current_idx != self.__current_line_index:
            self.__current_line_index = current_idx
            self.__line_transition_progress = 0.0
            self.__line_scroll_offset = 0  # Reset scroll for new line

        # Animate transition
        if self.__line_transition_progress < 1.0:
            self.__line_transition_progress = min(1.0, self.__line_transition_progress + 0.1)

        # Increment per-line scroll
        self.__line_scroll_offset += 0.5

        # Get current and next lines
        current_line = ""
        next_line = ""

        if current_idx >= 0 and current_idx < len(self.__lyrics):
            current_line = self.__lyrics[current_idx][1].upper()

        if current_idx + 1 < len(self.__lyrics):
            next_line = self.__lyrics[current_idx + 1][1].upper()

        # Layout: current line in top half, next line in bottom half
        # Current line at y=6, next line at y=18

        # Render current line (with scroll if too long)
        if current_line:
            # Pulse effect on current line
            pulse = 0.85 + 0.15 * np.sin(self.__tick_count * 0.2)
            current_color = tuple(int(c * pulse) for c in self.COLORS['current_line'])

            line_width = len(current_line) * 4
            if line_width <= self.__width:
                # Center short lines
                x = (self.__width - line_width) // 2
                textutils.draw_text(frame, current_line, x, 6, current_color, self.__width, self.__height)
            else:
                # Scroll long lines - use per-line scroll offset
                textutils.draw_scrolling_text(
                    frame, current_line, 0, 6, self.__width,
                    current_color, self.__line_scroll_offset,
                    self.__width, self.__height
                )

        # Render next line (dimmer)
        if next_line:
            next_color = self.COLORS['next_line']

            line_width = len(next_line) * 4
            if line_width <= self.__width:
                x = (self.__width - line_width) // 2
                textutils.draw_text(frame, next_line, x, 18, next_color, self.__width, self.__height)
            else:
                # Next line scrolls slower
                textutils.draw_scrolling_text(
                    frame, next_line, 0, 18, self.__width,
                    next_color, self.__line_scroll_offset * 0.7,
                    self.__width, self.__height
                )

        # Quality indicator pixel (top-right corner)
        self.__render_quality_indicator(frame)

        # Progress bar at bottom
        self.__render_progress_bar(frame)

    def __render_quality_indicator(self, frame):
        """Render a small pixel in top-right showing lyrics quality.

        Green = synced (good timing)
        Yellow = plain (no timing, just showing text)
        Off = no lyrics
        """
        if not self.__lyrics_quality:
            return

        # Top-right corner, 1 pixel
        x = self.__width - 2
        y = 1

        if self.__lyrics_quality == 'synced':
            color = (0, 255, 0)  # Green
        elif self.__lyrics_quality == 'plain':
            color = (255, 200, 0)  # Yellow
        else:
            return

        frame[y, x] = color

    def __render_progress_bar(self, frame):
        """Render a small progress bar showing position in song."""
        if not self.__lyrics or self.__current_line_index < 0:
            return

        # Get total duration from last lyric timestamp (approximate)
        if self.__lyrics:
            position = self.__get_interpolated_position()
            total_duration = self.__lyrics[-1][0] + 10  # Add 10s buffer
            progress = min(1.0, position / total_duration)

            bar_y = self.__height - 2
            bar_width = int(self.__width * progress)

            # Draw progress bar
            for x in range(bar_width):
                # Gradient from cyan to magenta
                ratio = x / self.__width
                r = int(100 + 155 * ratio)
                g = int(255 * (1 - ratio * 0.6))
                b = 255
                frame[bar_y, x] = (r, g, b)

    @classmethod
    def get_id(cls) -> str:
        return 'sonos_karaoke'

    @classmethod
    def get_name(cls) -> str:
        return 'Sonos Karaoke'

    @classmethod
    def get_description(cls) -> str:
        return 'Synced lyrics display for Sonos playback'
