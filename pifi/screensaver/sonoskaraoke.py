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
        'break_dot_empty': (60, 60, 60),       # Dim - empty progress dot
        'break_dot_filled': (150, 100, 255),   # Purple - filled progress dot
        # Word-by-word highlighting for enhanced lyrics
        'word_sung': (120, 120, 120),          # Dimmer - already sung
        'word_current': (255, 180, 50),        # Orange - current word (hit!)
        'word_upcoming': (180, 180, 180),      # Medium - not yet sung
    }

    # Threshold for showing break indicator (seconds)
    BREAK_THRESHOLD = 16.0
    # How long to show current lyrics before switching to break dots
    LYRICS_DISPLAY_TIME = 8.0
    # Threshold for showing initial countdown before first lyrics
    INTRO_COUNTDOWN_THRESHOLD = 10.0
    # Time after last lyric to switch to outro mode
    OUTRO_THRESHOLD = 16.0

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
        self.__max_position = 0  # Monotonic position (never goes backward)
        self.__song_duration = 0  # Actual song duration from Sonos
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
        self.__line_start_time = 0  # When current line started
        self.__line_duration = 5.0  # How long until next line (seconds)
        self.__line_transition_progress = 1.0  # 0 = transitioning, 1 = stable
        self.__max_intro_progress = 0  # Monotonic progress for intro (never goes backward)
        self.__word_start_times = {}  # Maps word_idx to wall-clock time for smooth fades
        self.__preview_line = None  # Track current preview line for scroll reset
        self.__preview_scroll_start = 0  # Tick count when preview line changed
        self.__preview_wall_start = 0  # Wall-clock time when preview line changed

        # Sonos speaker reference
        self.__speaker = None

        # Background polling thread
        self.__poll_lock = threading.Lock()  # Protects position/track state
        self.__polling_active = False
        self.__poll_thread = None

        # Pre-allocated frame buffer (optimization: avoid allocation every frame)
        self.__frame_buffer = np.zeros((self.__height, self.__width, 3), dtype=np.uint8)

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

        # Start background polling thread
        self.__polling_active = True
        self.__poll_thread = threading.Thread(target=self.__polling_loop, daemon=True)
        self.__poll_thread.start()

        try:
            for tick in range(self.__max_ticks):
                self.__render()
                self.__tick_count += 1
                time.sleep(self.__tick_sleep)
        finally:
            # Stop background polling
            self.__polling_active = False
            if self.__poll_thread:
                self.__poll_thread.join(timeout=1.0)

        self.__logger.info("Sonos Karaoke screensaver ended")

    def __polling_loop(self):
        """Background thread for Sonos polling."""
        while self.__polling_active:
            self.__poll_sonos()
            # Sleep in small increments to allow quick shutdown
            for _ in range(int(self.__update_interval * 10)):
                if not self.__polling_active:
                    break
                time.sleep(0.1)

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
        """Poll Sonos for current track info (runs in background thread)."""
        if not self.__speaker:
            self.__logger.debug("No speaker connected")
            return

        try:
            # Network calls outside the lock
            track_info = self.__speaker.get_current_track_info()
            transport_info = self.__speaker.get_current_transport_info()

            title = track_info.get('title', '')
            artist = track_info.get('artist', '')
            position = track_info.get('position', '0:00:00')
            duration = track_info.get('duration', '0:00:00')
            state = transport_info.get('current_transport_state', '')

            # Parse times
            position_seconds = self.__parse_time(position)
            song_duration = self.__parse_time(duration)
            poll_time = time.time()
            is_playing = state == 'PLAYING'

            # Update state atomically under lock
            with self.__poll_lock:
                self.__position_seconds = position_seconds
                self.__song_duration = song_duration
                self.__last_poll_time = poll_time
                self.__is_playing = is_playing

                self.__logger.debug(
                    f"Poll: state={state}, title='{title}', artist='{artist}', pos={position}"
                )

                # Check if track changed
                track_changed = False
                if title != self.__current_track or artist != self.__current_artist:
                    self.__current_track = title
                    self.__current_artist = artist
                    self.__lyrics = []
                    self.__lyrics_available = False
                    self.__current_line_index = -1
                    self.__max_position = 0  # Reset monotonic position for new track
                    track_changed = True

            # Start lyrics fetch outside lock (it spawns its own thread)
            if track_changed and title and artist:
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

            # Fetch from both Musixmatch (word-by-word) and LRCLIB (usually more accurate)
            mm_lrc = None
            ll_lrc = None

            try:
                mm_lrc = syncedlyrics.search(
                    search_query, synced_only=True, enhanced=True,
                    providers=['Musixmatch']
                )
                if mm_lrc:
                    self.__logger.debug("Musixmatch: found lyrics")
            except Exception as e:
                self.__logger.debug(f"Musixmatch failed: {e}")

            try:
                ll_lrc = syncedlyrics.search(
                    search_query, synced_only=True,
                    providers=['Lrclib']
                )
                if ll_lrc:
                    self.__logger.debug("LRCLIB: found lyrics")
            except Exception as e:
                self.__logger.debug(f"LRCLIB failed: {e}")

            # Decide which to use based on timing comparison
            lrc = None
            source_provider = None

            if mm_lrc and ll_lrc:
                # Both available - compare first line timestamps
                mm_parsed = self.__parse_lrc(mm_lrc)
                ll_parsed = self.__parse_lrc(ll_lrc)

                if mm_parsed and ll_parsed:
                    mm_first = mm_parsed[0][0]
                    ll_first = ll_parsed[0][0]
                    diff = abs(mm_first - ll_first)

                    self.__logger.info(
                        f"Timing comparison: Musixmatch={mm_first:.2f}s, LRCLIB={ll_first:.2f}s, diff={diff:.2f}s"
                    )

                    if diff <= 1.0:
                        # Timings match - use Musixmatch for word-by-word
                        lrc = mm_lrc
                        source_provider = 'Musixmatch'
                        self.__logger.info("Using Musixmatch (timings match, word-by-word available)")
                    else:
                        # Timings differ - trust LRCLIB
                        lrc = ll_lrc
                        source_provider = 'LRCLIB'
                        self.__logger.info("Using LRCLIB (timing mismatch, LRCLIB more accurate)")
                elif ll_parsed:
                    lrc = ll_lrc
                    source_provider = 'LRCLIB'
                elif mm_parsed:
                    lrc = mm_lrc
                    source_provider = 'Musixmatch'
            elif ll_lrc:
                lrc = ll_lrc
                source_provider = 'LRCLIB'
            elif mm_lrc:
                lrc = mm_lrc
                source_provider = 'Musixmatch'
            else:
                # Try fallback providers
                for provider in ['NetEase', 'Megalobiz']:
                    try:
                        result = syncedlyrics.search(
                            search_query, synced_only=True, providers=[provider]
                        )
                        if result:
                            lrc = result
                            source_provider = provider
                            self.__logger.info(f"Fallback: found lyrics via {provider}")
                            break
                    except Exception as e:
                        self.__logger.debug(f"{provider} failed: {e}")

            if lrc:
                # Detect if it's enhanced (has <> word timestamps)
                is_enhanced = '<' in lrc and '>' in lrc
                quality = 'enhanced' if is_enhanced else 'synced'
                self.__logger.info(f"Lyrics source: {source_provider}, quality: {quality}")

                lyrics = self.__parse_lrc(lrc)

                # Verify timestamps are actually varied (not all 0)
                if lyrics:
                    timestamps = [l[0] for l in lyrics[:5]]
                    if len(set(timestamps)) <= 1:
                        self.__logger.debug("Lyrics have no real timestamps, discarding")
                        lyrics = []

                with self.__fetch_lock:
                    # Verify we're still on the same track
                    if self.__current_track == title and self.__current_artist == artist:
                        self.__lyrics = lyrics
                        self.__lyrics_available = len(lyrics) > 0
                        self.__lyrics_quality = quality if lyrics else None
                        if lyrics:
                            self.__logger.info(f"Found {len(lyrics)} lyric lines (quality={quality})")
                            self.__logger.debug(f"First line: [{lyrics[0][0]:.1f}s] {lyrics[0][1]}")
                        else:
                            self.__logger.info(f"No usable timed lyrics for: '{search_query}'")
            else:
                self.__logger.info(f"No synced lyrics found for: '{search_query}'")
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
        """Parse LRC format lyrics into list of (timestamp_seconds, line, word_timings).

        For enhanced lyrics, word_timings is a list of (timestamp, word) tuples.
        For synced lyrics, word_timings is None.

        Handles both enhanced LRC formats:
        - Start-only: <00:12.34>Word <00:12.89>next
        - Start+end pairs: <00:12.34> Word <00:12.50> <00:12.89> next <00:13.00>
        """
        lyrics = []

        # LRC format: [mm:ss.xx] lyrics text
        line_pattern = r'\[(\d+):(\d+)(?:\.(\d+))?\](.*)'

        # Enhanced format: captures timestamp and following content
        # Matches <mm:ss.xx> followed by any content until next < or end
        enhanced_pattern = r'<(\d+):(\d+)\.(\d+)>([^<]*)'

        for line in lrc_text.split('\n'):
            match = re.match(line_pattern, line)
            if match:
                minutes = int(match.group(1))
                seconds = int(match.group(2))
                centiseconds = int(match.group(3)) if match.group(3) else 0
                text = match.group(4).strip()

                if text:
                    timestamp = minutes * 60 + seconds + centiseconds / 100.0

                    if '<' in text and '>' in text:
                        # Parse all timestamp+content pairs
                        raw_pairs = []
                        for m in re.finditer(enhanced_pattern, text):
                            w_min = int(m.group(1))
                            w_sec = int(m.group(2))
                            w_cs = int(m.group(3))
                            w_ts = w_min * 60 + w_sec + w_cs / 100.0
                            content = m.group(4).strip()
                            raw_pairs.append((w_ts, content))

                        # Filter to only pairs with actual words (not just whitespace/empty)
                        # This handles both formats:
                        # - Start-only: each timestamp has a word
                        # - Start+end: word timestamps alternate with empty end timestamps
                        word_timings = [(ts, word.upper()) for ts, word in raw_pairs if word]
                        clean_text = ' '.join(word for _, word in word_timings)

                        lyrics.append((timestamp, clean_text, word_timings))
                    else:
                        lyrics.append((timestamp, text.upper(), None))

        # Sort by timestamp
        lyrics.sort(key=lambda x: x[0])
        return lyrics

    def __get_interpolated_position(self):
        """Get current position with interpolation between polls.

        Returns a monotonically increasing position to prevent backward jumps
        from polling jitter.
        """
        if not self.__is_playing or self.__last_poll_time == 0:
            return self.__position_seconds

        # Interpolate based on time since last poll
        elapsed = time.time() - self.__last_poll_time
        raw_position = self.__position_seconds + elapsed

        # Make position monotonic - never go backward (except for seeks)
        # Allow backward jumps of more than 2 seconds (indicates a seek)
        if raw_position < self.__max_position - 2.0:
            # This is a seek backward, reset max
            self.__max_position = raw_position
        else:
            self.__max_position = max(self.__max_position, raw_position)

        return self.__max_position

    # Anticipation: show lyrics slightly before their timestamp
    LYRIC_ANTICIPATION = 0.3

    def __get_current_lyric_index(self):
        """Find the current lyric line based on playback position."""
        if not self.__lyrics:
            return -1

        position = self.__get_interpolated_position()

        # Find the last lyric that started before current position
        # Add anticipation so lyrics appear slightly before their timestamp
        new_index = -1
        for i, (timestamp, _, _) in enumerate(self.__lyrics):
            if timestamp <= position + self.LYRIC_ANTICIPATION:
                new_index = i
            else:
                break

        # Hysteresis: don't go backwards unless it's a significant jump (seek)
        # This prevents flipping between lines due to small timing fluctuations
        if self.__current_line_index >= 0 and new_index < self.__current_line_index:
            # Only allow going back if position jumped back significantly (>2 seconds)
            if self.__current_line_index < len(self.__lyrics):
                current_timestamp = self.__lyrics[self.__current_line_index][0]
                if position > current_timestamp - 2.0:
                    # Small fluctuation, stay on current line
                    return self.__current_line_index

        return new_index

    def __render(self):
        """Render the display."""
        # Reuse pre-allocated buffer (clear to black)
        frame = self.__frame_buffer
        frame.fill(0)

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

        # Detect line change - reset scroll and calculate duration
        if current_idx != self.__current_line_index:
            self.__current_line_index = current_idx
            self.__line_transition_progress = 0.0
            self.__line_scroll_offset = 0
            self.__line_start_time = time.time()
            self.__word_start_times = {}  # Reset word timing for new line

            # Calculate how long until next line
            if current_idx >= 0 and current_idx + 1 < len(self.__lyrics):
                current_ts = self.__lyrics[current_idx][0]
                next_ts = self.__lyrics[current_idx + 1][0]
                self.__line_duration = max(1.0, next_ts - current_ts)
            else:
                self.__line_duration = 5.0  # Default

        # Animate transition
        if self.__line_transition_progress < 1.0:
            self.__line_transition_progress = min(1.0, self.__line_transition_progress + 0.1)

        # Get current and next lines
        current_line = ""
        next_line = ""

        if current_idx >= 0 and current_idx < len(self.__lyrics):
            current_line = self.__lyrics[current_idx][1]  # Already uppercase from parsing

        if current_idx + 1 < len(self.__lyrics):
            next_line = self.__lyrics[current_idx + 1][1]  # Already uppercase from parsing

        # Check for intro countdown - before first lyrics start
        if current_idx == -1 and self.__lyrics:
            first_lyric_time = self.__lyrics[0][0]
            position = self.__get_interpolated_position()

            if first_lyric_time >= self.INTRO_COUNTDOWN_THRESHOLD:
                # Show countdown to first lyrics
                # Use monotonic progress to prevent backward scroll from position fluctuations
                raw_progress = min(1.0, position / first_lyric_time) if first_lyric_time > 0 else 0
                self.__max_intro_progress = max(self.__max_intro_progress, raw_progress)
                intro_progress = self.__max_intro_progress

                first_line = self.__lyrics[0][1]  # Already uppercase from parsing
                self.__render_break_indicator(frame, intro_progress, first_line)
                self.__render_progress_bar(frame)
                return
        else:
            # Reset intro progress when not in intro
            self.__max_intro_progress = 0

        # Check for outro - past the last lyric by threshold
        if current_idx >= 0 and self.__lyrics and current_idx == len(self.__lyrics) - 1:
            last_lyric_time = self.__lyrics[-1][0]
            position = self.__get_interpolated_position()
            time_since_last = position - last_lyric_time

            if time_since_last >= self.OUTRO_THRESHOLD:
                # Show song/artist info for the outro
                self.__render_outro(frame)
                self.__render_progress_bar(frame)
                return

        # Use simple wall-clock time for smooth scroll animation
        # (Song position is only used for lyric line selection, not scroll)
        elapsed = time.time() - self.__line_start_time
        line_progress = min(1.0, elapsed / self.__line_duration) if self.__line_duration > 0 else 0

        # Check if we're in a long break - show progress dots AFTER current lyrics displayed
        if self.__line_duration >= self.BREAK_THRESHOLD and elapsed >= self.LYRICS_DISPLAY_TIME:
            # Calculate progress through the break portion only (after lyrics display time)
            break_duration = self.__line_duration - self.LYRICS_DISPLAY_TIME
            break_elapsed = elapsed - self.LYRICS_DISPLAY_TIME
            break_progress = min(1.0, break_elapsed / break_duration) if break_duration > 0 else 0

            # For next line scroll, use full elapsed time to continue smoothly from lyrics display
            full_progress = min(1.0, elapsed / self.__line_duration) if self.__line_duration > 0 else 0

            self.__render_break_indicator(frame, break_progress, next_line, full_progress)
            self.__render_progress_bar(frame)
            return

        # Render current line - use 2 lines if very long
        if current_line:
            # Get word timings for enhanced lyrics (if available)
            word_timings = None
            if current_idx >= 0 and current_idx < len(self.__lyrics):
                word_timings = self.__lyrics[current_idx][2]

            # Get current song position for word highlighting
            current_position = self.__get_interpolated_position()
            current_time = time.time()  # Wall-clock time for smooth fade animations

            pulse = 0.85 + 0.15 * np.sin(self.__tick_count * 0.2)
            current_color = tuple(int(c * pulse) for c in self.COLORS['current_line'])

            # Each char is 3 pixels wide + 1 pixel spacing, but last char has no trailing space
            # So N chars = N*3 + (N-1)*1 = N*4 - 1 pixels
            # For fitting, we use N*4 as a conservative estimate
            line_width = len(current_line) * 4
            # Max chars that fully fit: solve N*4 - 1 <= width, so N <= (width + 1) / 4
            chars_per_line = (self.__width + 1) // 4

            # Word colors for enhanced lyrics
            word_colors = {
                'sung': self.COLORS['word_sung'],
                'current': self.COLORS['word_current'],
                'upcoming': self.COLORS['word_upcoming'],
            }

            if line_width <= self.__width:
                # Short line - center it
                x = (self.__width - line_width) // 2
                if word_timings:
                    textutils.draw_text_with_word_colors(
                        frame, word_timings, x, 6, current_position,
                        word_colors, self.__width, self.__height,
                        word_start_times=self.__word_start_times, current_time=current_time
                    )
                else:
                    textutils.draw_text(frame, current_line, x, 6, current_color, self.__width, self.__height)
            elif len(current_line) <= chars_per_line * 2:
                # Medium line - try to split into 2 lines
                mid = len(current_line) // 2
                # Find a space near the middle to split
                split_pos = mid
                for i in range(min(5, mid)):
                    if mid - i >= 0 and current_line[mid - i] == ' ':
                        split_pos = mid - i
                        break
                    if mid + i < len(current_line) and current_line[mid + i] == ' ':
                        split_pos = mid + i
                        break

                line1 = current_line[:split_pos].strip()
                line2 = current_line[split_pos:].strip()

                # Check if both lines fit - if not, fall through to vertical scroll
                if len(line1) > chars_per_line or len(line2) > chars_per_line:
                    # Lines don't fit - use vertical scroll instead
                    if word_timings:
                        textutils.draw_vertical_scroll_text_with_words(
                            frame, word_timings, 0, 2, self.__width,
                            current_position, word_colors,
                            self.__width, self.__height,
                            line_height=7, visible_lines=2,
                            word_start_times=self.__word_start_times, current_time=current_time,
                            clip_bottom=19
                        )
                    else:
                        scroll_progress = min(1.0, line_progress * 1.67)
                        textutils.draw_vertical_scroll_text(
                            frame, current_line, 0, 2, self.__width,
                            current_color, scroll_progress,
                            self.__width, self.__height,
                            line_height=7, visible_lines=2, clip_bottom=19
                        )
                else:
                    # Both lines fit - center each line
                    x1 = max(0, (self.__width - len(line1) * 4) // 2)
                    x2 = max(0, (self.__width - len(line2) * 4) // 2)

                    if word_timings:
                        # Build a color for each character position in the full line
                        # by mapping characters to their words
                        char_colors = []
                        for word_idx, (_, word) in enumerate(word_timings):
                            word_color = textutils.get_word_color(
                                word_idx, word_timings, current_position, word_colors,
                                word_start_times=self.__word_start_times, current_time=current_time
                            )
                            for _ in word:
                                char_colors.append(word_color)
                            char_colors.append(word_color)  # space after word

                        # Draw line1 character by character with colors
                        cursor = x1
                        for i, char in enumerate(line1):
                            # Map line1 char position to full text position
                            color = char_colors[i] if i < len(char_colors) else word_colors['sung']
                            textutils.draw_char(frame, char, cursor, 2, color, self.__width, self.__height)
                            cursor += 4

                        # Draw line2 character by character with colors
                        # Line2 starts after split_pos in the original text
                        cursor = x2
                        for i, char in enumerate(line2):
                            full_pos = split_pos + 1 + i  # +1 for the space we split on
                            color = char_colors[full_pos] if full_pos < len(char_colors) else word_colors['sung']
                            textutils.draw_char(frame, char, cursor, 9, color, self.__width, self.__height)
                            cursor += 4
                    else:
                        textutils.draw_text(frame, line1, x1, 2, current_color, self.__width, self.__height)
                        textutils.draw_text(frame, line2, x2, 9, current_color, self.__width, self.__height)
            else:
                # Very long line - use vertical scrolling (2 lines at a time)
                if word_timings:
                    # Enhanced lyrics: scroll based on word completion
                    textutils.draw_vertical_scroll_text_with_words(
                        frame, word_timings, 0, 2, self.__width,
                        current_position, word_colors,
                        self.__width, self.__height,
                        line_height=7, visible_lines=2,
                        word_start_times=self.__word_start_times, current_time=current_time,
                        clip_bottom=19
                    )
                else:
                    # Non-enhanced lyrics: use time-based vertical scroll
                    # Complete scroll at 60% through, leaving 40% to read final lines
                    scroll_progress = min(1.0, line_progress * 1.67)
                    # Clip at y=21 (one pixel above preview line at y=22)
                    textutils.draw_vertical_scroll_text(
                        frame, current_line, 0, 2, self.__width,
                        current_color, scroll_progress,
                        self.__width, self.__height,
                        line_height=7, visible_lines=2, clip_bottom=19
                    )

        # Render next line (dimmer) - must complete scroll before it becomes current
        if next_line:
            # Track preview line changes to reset scroll
            if next_line != self.__preview_line:
                self.__preview_line = next_line
                self.__preview_scroll_start = self.__tick_count
                self.__preview_wall_start = time.time()

            next_color = self.COLORS['next_line']
            next_line_width = len(next_line) * 4

            # Position depends on whether current used 2 lines
            # Move preview down a bit for visual separation
            next_y = 20 if len(current_line) <= (self.__width // 4) * 2 else 22

            if next_line_width <= self.__width:
                x = (self.__width - next_line_width) // 2
                textutils.draw_text(frame, next_line, x, next_y, next_color, self.__width, self.__height)
            else:
                # Preview scroll timing is tricky - we need to guarantee:
                # 1. The scroll completes AT LEAST one full cycle before promotion
                # 2. If there's extra time (slow lyrics, countdown mode), loop as
                #    many times as possible at the standard scroll speed
                # 3. Always finish cleanly at the end position (not mid-scroll)
                # 4. Leave 0.3s dwell time so final word is visible before promotion
                #
                # draw_scrolling_text handles this with complete_in_ticks + loop=True:
                # - Calculates how many full loops fit evenly in the available time
                # - Adjusts cycle timing so the last loop ends exactly at deadline
                # - If not enough time for default speed, scrolls faster (1 cycle)
                line_end_time = self.__line_start_time + self.__line_duration
                dwell_buffer = 0.3  # Extra time for final word to be visible
                time_for_scroll = max(0.5, line_end_time - self.__preview_wall_start - dwell_buffer)
                complete_in_ticks = int(time_for_scroll / self.__tick_sleep)

                preview_scroll_offset = self.__tick_count - self.__preview_scroll_start
                textutils.draw_scrolling_text(
                    frame, next_line, 0, next_y, self.__width,
                    next_color, preview_scroll_offset,
                    self.__width, self.__height,
                    pause_duration=30,
                    complete_in_ticks=complete_in_ticks,
                    loop=True
                )

        # Progress bar at bottom
        self.__render_progress_bar(frame)

    def __render_break_indicator(self, frame, progress, next_line, scroll_progress=None):
        """Render progress dots during instrumental break.

        Shows a row of dots that fill in as the break progresses,
        with the next lyric line visible below.

        Args:
            progress: Progress through the break (0-1) for dot filling
            next_line: The upcoming lyric line to display
            scroll_progress: Progress for scrolling next line (0-1), defaults to progress
        """
        if scroll_progress is None:
            scroll_progress = progress
        # Number of dots based on display width (roughly 5-8 dots)
        num_dots = min(8, max(5, self.__width // 10))

        # Calculate how many dots should be filled
        # With n dots, we have n+1 states (0 to n filled), each gets equal time
        # At progress=0: 0 filled, at progress=1: all filled
        filled_dots = min(num_dots, int(progress * (num_dots + 1)))

        # Dot spacing and positioning
        dot_spacing = 6  # pixels between dot centers
        total_width = (num_dots - 1) * dot_spacing + 3  # 3px per dot
        start_x = (self.__width - total_width) // 2
        dot_y = 6

        # Draw dots
        for i in range(num_dots):
            x = start_x + i * dot_spacing

            if i < filled_dots:
                # Filled dot - brighter, pulsing slightly
                pulse = 0.8 + 0.2 * np.sin(self.__tick_count * 0.15 + i * 0.5)
                color = tuple(int(c * pulse) for c in self.COLORS['break_dot_filled'])
            else:
                # Empty dot
                color = self.COLORS['break_dot_empty']

            # Draw a small 2x2 dot
            for dy in range(2):
                for dx in range(2):
                    px, py = x + dx, dot_y + dy
                    if 0 <= px < self.__width and 0 <= py < self.__height:
                        frame[py, px] = color

        # Show next line below (so singer can prepare)
        if next_line:
            # Track preview line changes to reset scroll
            if next_line != self.__preview_line:
                self.__preview_line = next_line
                self.__preview_scroll_start = self.__tick_count
                self.__preview_wall_start = time.time()

            next_color = self.COLORS['next_line']
            next_line_width = len(next_line) * 4

            if next_line_width <= self.__width:
                x = (self.__width - next_line_width) // 2
                textutils.draw_text(frame, next_line, x, 20, next_color, self.__width, self.__height)
            else:
                # Same scroll timing logic as main preview (see comment above)
                # Guarantees complete cycles, loops if time allows, finishes clean
                # with 0.3s dwell buffer for final word visibility
                line_end_time = self.__line_start_time + self.__line_duration
                dwell_buffer = 0.3
                time_for_scroll = max(0.5, line_end_time - self.__preview_wall_start - dwell_buffer)
                complete_in_ticks = int(time_for_scroll / self.__tick_sleep)

                preview_scroll_offset = self.__tick_count - self.__preview_scroll_start
                textutils.draw_scrolling_text(
                    frame, next_line, 0, 20, self.__width,
                    next_color, preview_scroll_offset,
                    self.__width, self.__height,
                    pause_duration=30,
                    complete_in_ticks=complete_in_ticks,
                    loop=True
                )

    def __render_outro(self, frame):
        """Render song info during the outro (after last lyric)."""
        # Show track and artist like in the no-lyrics state
        if self.__current_track:
            track_upper = self.__current_track.upper()
            textutils.draw_scrolling_text(
                frame, track_upper, 0, 8, self.__width,
                self.COLORS['title'], self.__tick_count,
                self.__width, self.__height
            )

        if self.__current_artist:
            artist_upper = self.__current_artist.upper()
            textutils.draw_scrolling_text(
                frame, artist_upper, 0, 18, self.__width,
                self.COLORS['artist'], int(self.__tick_count * 0.8),
                self.__width, self.__height
            )

    def __render_progress_bar(self, frame):
        """Render a small progress bar showing position in song."""
        position = self.__get_interpolated_position()

        # Use actual song duration from Sonos if available, otherwise estimate from lyrics
        if self.__song_duration > 0:
            total_duration = self.__song_duration
        elif self.__lyrics:
            total_duration = self.__lyrics[-1][0] + 10  # Add 10s buffer
        else:
            return  # No duration info available

        if total_duration <= 0:
            return

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
