"""
Karaoke Base Class.

Shared rendering, lyrics fetching, and state management for karaoke screensavers.
Subclasses provide the music source (Sonos, AirPlay, etc.).
"""

import numpy as np
import re
import threading
import time
from abc import abstractmethod

from pifi.config import Config
from pifi.led.ledframeplayer import LedFramePlayer
from pifi.logger import Logger
from pifi.screensaver.screensaver import Screensaver
from pifi.screensaver import textutils


class KaraokeBase(Screensaver):
    """Base class for karaoke lyrics display screensavers."""

    # Persisted state — class-level so it survives max_ticks instance restarts.
    # Use KaraokeBase._field = value for writes (self._field = creates instance vars).
    _current_track = None
    _current_artist = None
    _position_seconds = 0
    _song_duration = 0
    _last_poll_time = 0
    _is_playing = False
    _album_art_frame = None

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
    # Anticipation: show lyrics slightly before their timestamp
    LYRIC_ANTICIPATION = 0.3

    def __init__(self, led_frame_player=None):
        super().__init__(led_frame_player)
        self._logger = Logger().set_namespace(self.__class__.__name__)

        if led_frame_player is None:
            led_frame_player = LedFramePlayer()
        self._led_frame_player = led_frame_player

        self._width = Config.get('leds.display_width', 64)
        self._height = Config.get('leds.display_height', 32)

        # Subclasses should override these in their __init__
        self._tick_sleep = 0.05
        self._max_ticks = 6000
        self._pulse_lyrics = True

        self._poll_lock = threading.Lock()
        self._polling_active = False

        # Private state - lyrics
        self.__lyrics = []  # List of (timestamp_seconds, line_text, word_timings)
        self.__lyrics_available = False
        self.__lyrics_quality = None  # 'synced', 'enhanced', or None
        self.__lyrics_track = None   # Track name lyrics were fetched for
        self.__lyrics_artist = None  # Artist name lyrics were fetched for
        self.__fetch_in_progress = False
        self.__fetch_lock = threading.Lock()

        # Private state - animation
        self.__tick_count = 0
        self.__scroll_offset = 0
        self.__current_line_index = -1
        self.__line_scroll_offset = 0
        self.__line_start_time = 0
        self.__line_duration = 5.0
        self.__line_transition_progress = 1.0
        self.__max_position = 0  # Monotonic position (never goes backward)
        self.__max_intro_progress = 0
        self.__word_start_times = {}
        self.__preview_line = None
        self.__preview_scroll_start = 0
        self.__preview_wall_start = 0

        # Track change detection (render loop compares against these)
        self.__last_track = None
        self.__last_artist = None

        # Pre-allocated frame buffer
        self.__frame_buffer = np.zeros((self._height, self._width, 3), dtype=np.uint8)

    def play(self):
        """Run the screensaver."""
        self._logger.info(f"Starting {self.get_name()} screensaver")

        if not self._connect():
            self._logger.error(f"Could not connect to {self._get_source_display_name()}")
            frame = np.zeros((self._height, self._width, 3), dtype=np.uint8)
            for _ in range(100):
                frame.fill(0)
                self._render_connection_error(frame)
                self._led_frame_player.play_frame(frame)
                time.sleep(0.1)
            return

        self._logger.info(f"Connected to {self._get_source_display_name()}")

        # Start background polling thread
        self._polling_active = True
        poll_thread = threading.Thread(target=self._polling_loop, daemon=True)
        poll_thread.start()

        try:
            for tick in range(self._max_ticks):
                if self._is_past_screensaver_timeout():
                    break
                self.__render()
                self.__tick_count += 1
                time.sleep(self._tick_sleep)
        finally:
            self._polling_active = False
            poll_thread.join(timeout=1.0)

        self._logger.info(f"{self.get_name()} screensaver ended")

    # --- Abstract methods for subclasses ---

    @abstractmethod
    def _connect(self) -> bool:
        """Connect to the music source. Returns True on success."""
        pass

    @abstractmethod
    def _polling_loop(self):
        """Background thread loop for polling the music source.

        Must update protected state under _poll_lock:
            _current_track, _current_artist,
            _position_seconds, _song_duration, _last_poll_time, _is_playing

        Check _polling_active to know when to stop.
        """
        pass

    @abstractmethod
    def _get_source_display_name(self) -> str:
        """Return display name for the music source (e.g. 'SONOS', 'AIRPLAY')."""
        pass

    @abstractmethod
    def _render_connection_error(self, frame):
        """Render connection error on the frame."""
        pass

    # --- Track change detection ---

    def __check_track_change(self):
        """Detect track changes and trigger lyrics fetch."""
        with self._poll_lock:
            track = self._current_track
            artist = self._current_artist

        if track != self.__last_track or artist != self.__last_artist:
            self.__last_track = track
            self.__last_artist = artist

            # Track went to None (e.g. pend during pause). Don't clear
            # lyrics — the render loop already shows "waiting" when there's
            # no track, and preserving lyrics lets us reuse them if the
            # same song resumes.
            if not track:
                return

            # Same song resumed — reuse cached lyrics instead of re-fetching.
            if (artist and
                    track == self.__lyrics_track and artist == self.__lyrics_artist):
                self._logger.info(
                    f"Reusing cached lyrics for: '{track}' by '{artist}'"
                )
                return

            self.__lyrics = []
            self.__lyrics_available = False
            self.__lyrics_quality = None
            self.__current_line_index = -1
            self.__max_position = 0
            self.__max_intro_progress = 0
            self.__word_start_times = {}
            self.__preview_line = None

            self.__start_lyrics_fetch(track, artist)

    # --- Lyrics fetching ---

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
            self._logger.info(f"Fetching lyrics for: '{title}' by '{artist}'")

            with self._poll_lock:
                duration = int(self._song_duration) if self._song_duration > 0 else None

            # Try providers in order of reliability. Use direct API calls
            # with structured metadata (title, artist, duration) for better
            # version matching instead of free-text search.
            lrc = None
            source_provider = None

            fetchers = [
                ('Musixmatch', lambda: self.__fetch_musixmatch(title, artist, duration)),
                ('LRCLIB', lambda: self.__fetch_lrclib(title, artist, duration)),
            ]
            for provider, fetcher in fetchers:
                try:
                    result = fetcher()
                    if result:
                        lrc = result
                        source_provider = provider
                        self._logger.info(f"Found lyrics via {provider}")
                        break
                    else:
                        self._logger.debug(f"{provider}: no results")
                except Exception as e:
                    self._logger.debug(f"{provider} failed: {e}")

            # Fall back to syncedlyrics text search for remaining providers
            if not lrc:
                try:
                    import syncedlyrics
                    search_query = f"{title} {artist}"
                    for provider in ['NetEase', 'Megalobiz']:
                        try:
                            result = syncedlyrics.search(
                                search_query, synced_only=True,
                                providers=[provider]
                            )
                            if result:
                                lrc = result
                                source_provider = provider
                                self._logger.info(f"Found lyrics via {provider}")
                                self._logger.debug(
                                    f"{provider} response ({len(result)} bytes): "
                                    f"{result[:500]}"
                                )
                                break
                            else:
                                self._logger.debug(f"{provider}: no results")
                        except Exception as e:
                            self._logger.debug(f"{provider} failed: {e}")
                except ImportError:
                    self._logger.debug("syncedlyrics not installed, skipping fallback providers")

            if lrc:
                is_enhanced = '<' in lrc and '>' in lrc
                quality = 'enhanced' if is_enhanced else 'synced'
                self._logger.info(f"Lyrics source: {source_provider}, quality: {quality}")

                lyrics = self.__parse_lrc(lrc)

                # Verify timestamps are actually varied (not all 0)
                if lyrics:
                    timestamps = [l[0] for l in lyrics[:5]]
                    if len(set(timestamps)) <= 1:
                        self._logger.debug("Lyrics have no real timestamps, discarding")
                        lyrics = []

                with self.__fetch_lock:
                    if self._current_track == title and self._current_artist == artist:
                        self.__lyrics = lyrics
                        self.__lyrics_available = len(lyrics) > 0
                        self.__lyrics_quality = quality if lyrics else None
                        self.__lyrics_track = title
                        self.__lyrics_artist = artist
                        if lyrics:
                            self._logger.info(f"Found {len(lyrics)} lyric lines (quality={quality})")
                            self._logger.debug(f"First line: [{lyrics[0][0]:.1f}s] {lyrics[0][1]}")
                        else:
                            self._logger.info(f"No usable timed lyrics for: '{title}' by '{artist}'")
            else:
                self._logger.info(f"No synced lyrics found for: '{title}' by '{artist}'")
                with self.__fetch_lock:
                    self.__lyrics = []
                    self.__lyrics_available = False
                    self.__lyrics_quality = None
        except Exception as e:
            self._logger.error(f"Error fetching lyrics: {e}")
            import traceback
            self._logger.debug(traceback.format_exc())
        finally:
            self.__fetch_in_progress = False

            # If the track changed while we were fetching (e.g. rapid skipping),
            # __check_track_change already updated __last_track but couldn't start
            # a new fetch because __fetch_in_progress was True. Re-trigger now.
            with self._poll_lock:
                current_track = self._current_track
                current_artist = self._current_artist
            if (current_track and current_artist and
                    (current_track != title or current_artist != artist)):
                self._logger.info(
                    f"Track changed during fetch, re-fetching for: "
                    f"'{current_track}' by '{current_artist}'"
                )
                self.__start_lyrics_fetch(current_track, current_artist)

    # --- Direct provider API calls ---
    # Using structured metadata (title, artist, duration) for better
    # version matching instead of syncedlyrics' free-text search.

    __mm_token = None
    __MM_URL = 'https://apic-desktop.musixmatch.com/ws/1.1/'

    def __mm_get_token(self):
        """Fetch a fresh Musixmatch API token. Returns token or None."""
        import requests
        r = requests.get(KaraokeBase.__MM_URL + 'token.get', params={
            'app_id': 'web-desktop-app-v1.0',
            'user_language': 'en',
            't': str(int(time.time() * 1000)),
        }, timeout=(3, 5))
        raw_text = r.text
        self._logger.debug(
            f"Musixmatch token.get response ({len(raw_text)} bytes): "
            f"{raw_text[:500]}"
        )
        data = r.json()
        if data['message']['header']['status_code'] == 401:
            KaraokeBase.__mm_token = None
            return None

        KaraokeBase.__mm_token = data['message']['body']['user_token']
        return KaraokeBase.__mm_token

    def __mm_api(self, endpoint, params):
        """Make a Musixmatch API request. Retries with a fresh token on 401."""
        import requests

        if not KaraokeBase.__mm_token:
            if not self.__mm_get_token():
                self._logger.debug("Musixmatch: could not get token")
                return None

        for attempt in range(2):
            req_params = dict(params)
            req_params.update({
                'app_id': 'web-desktop-app-v1.0',
                'usertoken': KaraokeBase.__mm_token,
                't': str(int(time.time() * 1000)),
            })
            r = requests.get(self.__MM_URL + endpoint, params=req_params, timeout=(3, 5))
            raw_text = r.text
            self._logger.debug(
                f"Musixmatch {endpoint} response ({len(raw_text)} bytes): "
                f"{raw_text[:500]}"
            )
            data = r.json()
            status = data['message']['header']['status_code']

            if status == 401 and attempt == 0:
                self._logger.debug("Musixmatch token expired, refreshing")
                if not self.__mm_get_token():
                    self._logger.debug("Musixmatch: could not refresh token")
                    return None
                continue

            if status != 200:
                return None
            return data['message'].get('body')

    def __fetch_musixmatch(self, title, artist, duration):
        """Fetch lyrics from Musixmatch using matcher API for version-accurate results."""
        # Try matcher endpoint first (single best match)
        params = {'q_track': title, 'q_artist': artist}
        if duration:
            params['f_subtitle_length'] = duration
        body = self.__mm_api('matcher.track.get', params)

        if body and 'track' in body:
            track = body['track']
            track_id = track['track_id']
            matched_length = track.get('track_length', 0)
            self._logger.debug(
                f"Musixmatch matcher: '{track.get('track_name', '')}' "
                f"(id={track_id}, length={matched_length}s)"
            )

            duration_ok = not duration or not matched_length or abs(matched_length - duration) <= 10
            if duration_ok:
                lrc = self.__mm_fetch_lyrics_by_track_id(track_id)
                if lrc:
                    return lrc

            if not duration_ok:
                self._logger.debug(
                    f"Musixmatch matcher duration mismatch: {matched_length}s vs expected {duration}s, "
                    f"trying search"
                )
            else:
                self._logger.debug(
                    f"Musixmatch matcher: no lyrics for track_id={track_id}, trying search"
                )

        # Fall back to track.search — returns multiple results we can filter by duration
        if duration:
            track_id = self.__mm_search_by_duration(title, artist, duration)
            if track_id:
                return self.__mm_fetch_lyrics_by_track_id(track_id)

        return None

    def __mm_search_by_duration(self, title, artist, duration):
        """Search Musixmatch for a track matching our duration. Returns track_id or None."""
        body = self.__mm_api('track.search', {
            'q_track': title, 'q_artist': artist,
            'page_size': '10', 'page': '1',
        })
        if not body or 'track_list' not in body:
            return None

        best_id = None
        best_diff = float('inf')
        for item in body['track_list']:
            track = item['track']
            length = track.get('track_length', 0)
            if not length:
                continue
            diff = abs(length - duration)
            if diff < best_diff:
                best_diff = diff
                best_id = track['track_id']
                best_name = track.get('track_name', '')
                best_length = length

        if best_id and best_diff <= 10:
            self._logger.debug(
                f"Musixmatch search: '{best_name}' (id={best_id}, length={best_length}s, "
                f"diff={best_diff}s)"
            )
            return best_id

        self._logger.debug(
            f"Musixmatch search: no duration match within 10s (best diff={best_diff}s)"
        )
        return None

    def __mm_fetch_lyrics_by_track_id(self, track_id):
        """Fetch lyrics (richsync or LRC) for a Musixmatch track ID."""
        # Try word-by-word (richsync) first
        rich_body = self.__mm_api('track.richsync.get', {'track_id': track_id})
        if rich_body and 'richsync' in rich_body:
            try:
                import json as json_mod
                richsync = json_mod.loads(rich_body['richsync']['richsync_body'])
                lrc_lines = []
                for line in richsync:
                    ts = line['ts']
                    mm = int(ts) // 60
                    ss = int(ts) % 60
                    cs = int((ts % 1) * 100)
                    line_tag = f'[{mm:02d}:{ss:02d}.{cs:02d}]'

                    words = []
                    for w in line['l']:
                        wt = float(ts) + float(w['o'])
                        wm = int(wt) // 60
                        ws = int(wt) % 60
                        wc = int((wt % 1) * 100)
                        words.append(f'<{wm:02d}:{ws:02d}.{wc:02d}>{w["c"]}')

                    lrc_lines.append(f'{line_tag} {"".join(words)}')

                return '\n'.join(lrc_lines)
            except Exception as e:
                self._logger.debug(f"Musixmatch richsync parse failed: {e}")

        # Fall back to line-level sync
        sub_body = self.__mm_api('track.subtitle.get', {
            'track_id': track_id, 'subtitle_format': 'lrc',
        })
        if sub_body and 'subtitle' in sub_body:
            return sub_body['subtitle']['subtitle_body']

        return None

    def __fetch_lrclib(self, title, artist, duration):
        """Fetch lyrics from LRCLIB using structured metadata for version-accurate results."""
        import requests
        params = {'track_name': title, 'artist_name': artist}
        if duration:
            params['duration'] = duration

        r = requests.get('https://lrclib.net/api/get', params=params, timeout=(3, 5))
        raw_text = r.text
        self._logger.debug(
            f"LRCLIB response (status={r.status_code}, {len(raw_text)} bytes): "
            f"{raw_text[:500]}"
        )
        if r.status_code != 200:
            return None

        data = r.json()
        return data.get('syncedLyrics')

    def __parse_lrc(self, lrc_text):
        """Parse LRC format lyrics into list of (timestamp_seconds, line, word_timings).

        For enhanced lyrics, word_timings is a list of (timestamp, word) tuples.
        For synced lyrics, word_timings is None.

        Handles both enhanced LRC formats:
        - Start-only: <00:12.34>Word <00:12.89>next
        - Start+end pairs: <00:12.34> Word <00:12.50> <00:12.89> next <00:13.00>
        """
        lyrics = []

        line_pattern = r'\[(\d+):(\d+)(?:\.(\d+))?\](.*)'
        enhanced_pattern = r'<(\d+):(\d+)\.(\d+)>([^<]*)'

        def parse_frac(s):
            """Parse fractional seconds, handling both centiseconds and milliseconds."""
            if not s:
                return 0.0
            return int(s) / (10 ** len(s))

        for line in lrc_text.split('\n'):
            match = re.match(line_pattern, line)
            if match:
                minutes = int(match.group(1))
                seconds = int(match.group(2))
                frac = parse_frac(match.group(3))
                text = match.group(4).strip()

                if text:
                    timestamp = minutes * 60 + seconds + frac

                    if '<' in text and '>' in text:
                        raw_pairs = []
                        for m in re.finditer(enhanced_pattern, text):
                            w_min = int(m.group(1))
                            w_sec = int(m.group(2))
                            w_frac = parse_frac(m.group(3))
                            w_ts = w_min * 60 + w_sec + w_frac
                            content = m.group(4).strip()
                            raw_pairs.append((w_ts, content))

                        word_timings = [(ts, word.upper()) for ts, word in raw_pairs if word]
                        clean_text = ' '.join(word for _, word in word_timings)

                        lyrics.append((timestamp, clean_text, word_timings))
                    else:
                        lyrics.append((timestamp, text.upper(), None))

        lyrics.sort(key=lambda x: x[0])
        return lyrics

    # --- Position and lyric index ---

    def __get_interpolated_position(self):
        """Get current position with interpolation between polls.

        Returns a monotonically increasing position to prevent backward jumps
        from polling jitter.
        """
        if not self._is_playing or self._last_poll_time == 0:
            return self._position_seconds

        elapsed = time.time() - self._last_poll_time
        raw_position = self._position_seconds + elapsed

        # Make position monotonic - allow backward jumps of >2s (indicates a seek)
        if raw_position < self.__max_position - 2.0:
            self.__max_position = raw_position
        else:
            self.__max_position = max(self.__max_position, raw_position)

        return self.__max_position

    def __get_current_lyric_index(self):
        """Find the current lyric line based on playback position."""
        if not self.__lyrics:
            return -1

        position = self.__get_interpolated_position()

        new_index = -1
        for i, (timestamp, _, _) in enumerate(self.__lyrics):
            if timestamp <= position + self.LYRIC_ANTICIPATION:
                new_index = i
            else:
                break

        # Hysteresis: don't go backwards unless it's a significant jump (seek)
        if self.__current_line_index >= 0 and new_index < self.__current_line_index:
            if self.__current_line_index < len(self.__lyrics):
                current_timestamp = self.__lyrics[self.__current_line_index][0]
                if position > current_timestamp - 2.0:
                    return self.__current_line_index

        return new_index

    # --- Rendering ---

    def __render(self):
        """Render the display."""
        # Check for track changes and trigger lyrics fetch
        self.__check_track_change()

        # Reuse pre-allocated buffer (clear to black)
        frame = self.__frame_buffer
        frame.fill(0)

        if not self._is_playing and not self._current_track:
            if self.__tick_count % 100 == 0:
                self._logger.debug("Render: waiting (no track, not playing)")
            self.__render_waiting(frame)
        elif not self.__lyrics_available:
            if self.__tick_count % 100 == 0:
                self._logger.debug(f"Render: no lyrics (track='{self._current_track}')")
            self.__render_no_lyrics(frame)
        else:
            if self.__tick_count % 200 == 0:
                pos = self.__get_interpolated_position()
                poll_age = time.time() - self._last_poll_time if self._last_poll_time else -1
                self._logger.debug(
                    f"Render: lyrics line={self.__current_line_index} "
                    f"pos={pos:.1f}s playing={self._is_playing} "
                    f"max_pos={self.__max_position:.1f}s "
                    f"poll_age={poll_age:.1f}s"
                )
            self.__render_lyrics(frame)

        self.__scroll_offset += 0.5
        self._led_frame_player.play_frame(frame)

    def __render_waiting(self, frame):
        """Render waiting for music state with animated idle display."""
        t = self.__tick_count * 0.12

        # Draw gentle wave of dots across the middle
        num_dots = 8
        wave_y = self._height // 2
        dot_spacing = self._width // (num_dots + 1)

        for i in range(num_dots):
            phase = i * 0.7
            y_offset = int(3 * np.sin(t + phase))
            brightness = 0.5 + 0.5 * np.sin(t * 0.8 + phase + 1.5)

            x = dot_spacing * (i + 1)
            y = wave_y + y_offset

            hue_shift = i / num_dots
            r = int(150 * brightness * (1 - hue_shift * 0.3))
            g = int(100 * brightness * (0.5 + hue_shift * 0.3))
            b = int(200 * brightness * (0.6 + hue_shift * 0.4))
            color = (r, g, b)

            for dy in range(2):
                for dx in range(2):
                    px, py = x + dx, y + dy
                    if 0 <= px < self._width and 0 <= py < self._height:
                        frame[py, px] = color

        # Text at bottom
        text_pulse = 0.6 + 0.4 * np.sin(t * 0.5)
        text_color = tuple(int(120 * text_pulse) for _ in range(3))

        text = f"NO MUSIC ON {self._get_source_display_name()}"

        text_width = len(text) * 4
        if text_width <= self._width:
            x = (self._width - text_width) // 2
            textutils.draw_text(frame, text, x, self._height - 7, text_color,
                                self._width, self._height)
        else:
            textutils.draw_scrolling_text(
                frame, text, 0, self._height - 7, self._width,
                text_color, self.__tick_count,
                self._width, self._height
            )

    def __render_no_lyrics(self, frame):
        """Render track info when no lyrics available."""
        if not self._current_track and not self._current_artist:
            self.__render_waiting(frame)
            return

        self.__apply_album_art_background(frame)

        if self._current_track:
            track_upper = self._current_track.upper()
            textutils.draw_scrolling_text(
                frame, track_upper, 0, 8, self._width,
                self.COLORS['title'], self.__scroll_offset,
                self._width, self._height
            )

        if self._current_artist:
            artist_upper = self._current_artist.upper()
            textutils.draw_scrolling_text(
                frame, artist_upper, 0, 18, self._width,
                self.COLORS['artist'], self.__scroll_offset * 0.8,
                self._width, self._height
            )

        if self.__fetch_in_progress:
            status = "..."
            x = (self._width - len(status) * 4) // 2
            textutils.draw_text(frame, status, x, 26, self.COLORS['no_lyrics'], self._width, self._height)

    def __render_lyrics(self, frame):
        """Render synced lyrics."""
        current_idx = self.__get_current_lyric_index()

        # Detect line change - reset scroll and calculate duration
        if current_idx != self.__current_line_index:
            self.__current_line_index = current_idx
            self.__line_transition_progress = 0.0
            self.__line_scroll_offset = 0
            self.__line_start_time = time.time()
            self.__word_start_times = {}

            if current_idx >= 0 and current_idx + 1 < len(self.__lyrics):
                current_ts = self.__lyrics[current_idx][0]
                next_ts = self.__lyrics[current_idx + 1][0]
                self.__line_duration = max(1.0, next_ts - current_ts)
            else:
                self.__line_duration = 5.0

        # Animate transition
        if self.__line_transition_progress < 1.0:
            self.__line_transition_progress = min(1.0, self.__line_transition_progress + 0.1)

        # Get current and next lines
        current_line = ""
        next_line = ""

        if current_idx >= 0 and current_idx < len(self.__lyrics):
            current_line = self.__lyrics[current_idx][1]

        if current_idx + 1 < len(self.__lyrics):
            next_line = self.__lyrics[current_idx + 1][1]

        # Check for intro countdown - before first lyrics start
        if current_idx == -1 and self.__lyrics:
            first_lyric_time = self.__lyrics[0][0]
            position = self.__get_interpolated_position()

            if first_lyric_time >= self.INTRO_COUNTDOWN_THRESHOLD:
                raw_progress = min(1.0, position / first_lyric_time) if first_lyric_time > 0 else 0
                self.__max_intro_progress = max(self.__max_intro_progress, raw_progress)
                intro_progress = self.__max_intro_progress

                first_line = self.__lyrics[0][1]
                self.__render_break_indicator(frame, intro_progress, first_line)
                self.__render_progress_bar(frame)
                return
        else:
            self.__max_intro_progress = 0

        # Check for outro - past the last lyric by threshold
        if current_idx >= 0 and self.__lyrics and current_idx == len(self.__lyrics) - 1:
            last_lyric_time = self.__lyrics[-1][0]
            position = self.__get_interpolated_position()
            time_since_last = position - last_lyric_time

            if time_since_last >= self.OUTRO_THRESHOLD:
                self.__render_outro(frame)
                self.__render_progress_bar(frame)
                return

        elapsed = time.time() - self.__line_start_time
        line_progress = min(1.0, elapsed / self.__line_duration) if self.__line_duration > 0 else 0

        # Check if we're in a long break
        if self.__line_duration >= self.BREAK_THRESHOLD and elapsed >= self.LYRICS_DISPLAY_TIME:
            break_duration = self.__line_duration - self.LYRICS_DISPLAY_TIME
            break_elapsed = elapsed - self.LYRICS_DISPLAY_TIME
            break_progress = min(1.0, break_elapsed / break_duration) if break_duration > 0 else 0

            full_progress = min(1.0, elapsed / self.__line_duration) if self.__line_duration > 0 else 0

            self.__render_break_indicator(frame, break_progress, next_line, full_progress)
            self.__render_progress_bar(frame)
            return

        # Render current line
        if current_line:
            word_timings = None
            if current_idx >= 0 and current_idx < len(self.__lyrics):
                word_timings = self.__lyrics[current_idx][2]

            current_position = self.__get_interpolated_position()
            current_time = time.time()

            if self._pulse_lyrics:
                pulse = 0.85 + 0.15 * np.sin(self.__tick_count * 0.2)
            else:
                pulse = 0.75
            current_color = tuple(int(c * pulse) for c in self.COLORS['current_line'])

            line_width = len(current_line) * 4
            chars_per_line = (self._width + 1) // 4

            word_colors = {
                'sung': self.COLORS['word_sung'],
                'current': self.COLORS['word_current'],
                'upcoming': self.COLORS['word_upcoming'],
            }

            if line_width <= self._width:
                x = (self._width - line_width) // 2
                if word_timings:
                    textutils.draw_text_with_word_colors(
                        frame, word_timings, x, 6, current_position,
                        word_colors, self._width, self._height,
                        word_start_times=self.__word_start_times, current_time=current_time
                    )
                else:
                    textutils.draw_text(frame, current_line, x, 6, current_color, self._width, self._height)
            elif len(current_line) <= chars_per_line * 2:
                mid = len(current_line) // 2
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

                if len(line1) > chars_per_line or len(line2) > chars_per_line:
                    if word_timings:
                        textutils.draw_vertical_scroll_text_with_words(
                            frame, word_timings, 0, 2, self._width,
                            current_position, word_colors,
                            self._width, self._height,
                            line_height=7, visible_lines=2,
                            word_start_times=self.__word_start_times, current_time=current_time,
                            clip_bottom=19
                        )
                    else:
                        scroll_progress = min(1.0, line_progress * 1.67)
                        textutils.draw_vertical_scroll_text(
                            frame, current_line, 0, 2, self._width,
                            current_color, scroll_progress,
                            self._width, self._height,
                            line_height=7, visible_lines=2, clip_bottom=19
                        )
                else:
                    x1 = max(0, (self._width - len(line1) * 4) // 2)
                    x2 = max(0, (self._width - len(line2) * 4) // 2)

                    if word_timings:
                        char_colors = []
                        for word_idx, (_, word) in enumerate(word_timings):
                            word_color = textutils.get_word_color(
                                word_idx, word_timings, current_position, word_colors,
                                word_start_times=self.__word_start_times, current_time=current_time
                            )
                            for _ in word:
                                char_colors.append(word_color)
                            char_colors.append(word_color)

                        cursor = x1
                        for i, char in enumerate(line1):
                            color = char_colors[i] if i < len(char_colors) else word_colors['sung']
                            textutils.draw_char(frame, char, cursor, 2, color, self._width, self._height)
                            cursor += 4

                        cursor = x2
                        for i, char in enumerate(line2):
                            full_pos = split_pos + 1 + i
                            color = char_colors[full_pos] if full_pos < len(char_colors) else word_colors['sung']
                            textutils.draw_char(frame, char, cursor, 9, color, self._width, self._height)
                            cursor += 4
                    else:
                        textutils.draw_text(frame, line1, x1, 2, current_color, self._width, self._height)
                        textutils.draw_text(frame, line2, x2, 9, current_color, self._width, self._height)
            else:
                if word_timings:
                    textutils.draw_vertical_scroll_text_with_words(
                        frame, word_timings, 0, 2, self._width,
                        current_position, word_colors,
                        self._width, self._height,
                        line_height=7, visible_lines=2,
                        word_start_times=self.__word_start_times, current_time=current_time,
                        clip_bottom=19
                    )
                else:
                    scroll_progress = min(1.0, line_progress * 1.67)
                    textutils.draw_vertical_scroll_text(
                        frame, current_line, 0, 2, self._width,
                        current_color, scroll_progress,
                        self._width, self._height,
                        line_height=7, visible_lines=2, clip_bottom=19
                    )

        # Render next line (dimmer)
        if next_line:
            if next_line != self.__preview_line:
                self.__preview_line = next_line
                self.__preview_scroll_start = self.__tick_count
                self.__preview_wall_start = time.time()

            next_color = self.COLORS['next_line']
            next_line_width = len(next_line) * 4

            next_y = 20 if len(current_line) <= (self._width // 4) * 2 else 22

            if next_line_width <= self._width:
                x = (self._width - next_line_width) // 2
                textutils.draw_text(frame, next_line, x, next_y, next_color, self._width, self._height)
            else:
                line_end_time = self.__line_start_time + self.__line_duration
                dwell_buffer = 0.3
                time_for_scroll = max(0.5, line_end_time - self.__preview_wall_start - dwell_buffer)
                complete_in_ticks = int(time_for_scroll / self._tick_sleep)

                preview_scroll_offset = self.__tick_count - self.__preview_scroll_start
                textutils.draw_scrolling_text(
                    frame, next_line, 0, next_y, self._width,
                    next_color, preview_scroll_offset,
                    self._width, self._height,
                    pause_duration=30,
                    complete_in_ticks=complete_in_ticks,
                    loop=True
                )

        # Progress bar at bottom
        self.__render_progress_bar(frame)

    def __apply_album_art_background(self, frame):
        """Copy album art into the frame buffer as a dimmed background."""
        if self._album_art_frame is not None:
            np.copyto(frame, self._album_art_frame)

    def __render_break_indicator(self, frame, progress, next_line, scroll_progress=None):
        """Render progress dots during instrumental break."""
        self.__apply_album_art_background(frame)
        if scroll_progress is None:
            scroll_progress = progress

        num_dots = min(8, max(5, self._width // 10))
        filled_dots = min(num_dots, int(progress * (num_dots + 1)))

        dot_spacing = 6
        total_width = (num_dots - 1) * dot_spacing + 3
        start_x = (self._width - total_width) // 2
        dot_y = 6

        for i in range(num_dots):
            x = start_x + i * dot_spacing

            if i < filled_dots:
                pulse = 0.8 + 0.2 * np.sin(self.__tick_count * 0.15 + i * 0.5)
                color = tuple(int(c * pulse) for c in self.COLORS['break_dot_filled'])
            else:
                color = self.COLORS['break_dot_empty']

            for dy in range(2):
                for dx in range(2):
                    px, py = x + dx, dot_y + dy
                    if 0 <= px < self._width and 0 <= py < self._height:
                        frame[py, px] = color

        if next_line:
            if next_line != self.__preview_line:
                self.__preview_line = next_line
                self.__preview_scroll_start = self.__tick_count
                self.__preview_wall_start = time.time()

            next_color = self.COLORS['next_line']
            next_line_width = len(next_line) * 4

            if next_line_width <= self._width:
                x = (self._width - next_line_width) // 2
                textutils.draw_text(frame, next_line, x, 20, next_color, self._width, self._height)
            else:
                line_end_time = self.__line_start_time + self.__line_duration
                dwell_buffer = 0.3
                time_for_scroll = max(0.5, line_end_time - self.__preview_wall_start - dwell_buffer)
                complete_in_ticks = int(time_for_scroll / self._tick_sleep)

                preview_scroll_offset = self.__tick_count - self.__preview_scroll_start
                textutils.draw_scrolling_text(
                    frame, next_line, 0, 20, self._width,
                    next_color, preview_scroll_offset,
                    self._width, self._height,
                    pause_duration=30,
                    complete_in_ticks=complete_in_ticks,
                    loop=True
                )

    def __render_outro(self, frame):
        """Render song info during the outro (after last lyric)."""
        self.__apply_album_art_background(frame)
        if self._current_track:
            track_upper = self._current_track.upper()
            textutils.draw_scrolling_text(
                frame, track_upper, 0, 8, self._width,
                self.COLORS['title'], self.__tick_count,
                self._width, self._height
            )

        if self._current_artist:
            artist_upper = self._current_artist.upper()
            textutils.draw_scrolling_text(
                frame, artist_upper, 0, 18, self._width,
                self.COLORS['artist'], int(self.__tick_count * 0.8),
                self._width, self._height
            )

    def __render_progress_bar(self, frame):
        """Render a small progress bar showing position in song."""
        position = self.__get_interpolated_position()

        if self._song_duration > 0:
            total_duration = self._song_duration
        elif self.__lyrics:
            total_duration = self.__lyrics[-1][0] + 10
        else:
            return

        if total_duration <= 0:
            return

        progress = min(1.0, position / total_duration)

        bar_y = self._height - 2
        bar_width = int(self._width * progress)

        for x in range(bar_width):
            ratio = x / self._width
            r = int(100 + 155 * ratio)
            g = int(255 * (1 - ratio * 0.6))
            b = 255
            frame[bar_y, x] = (r, g, b)
