"""
AirPlay Karaoke Screensaver.

Displays synced lyrics from currently playing AirPlay track via shairport-sync.
Reads metadata from shairport-sync's metadata pipe.
"""

import base64
import os
import re
import time

from pifi.config import Config
from pifi.screensaver.karaokebase import KaraokeBase
from pifi.screensaver import textutils


class AirPlayKaraoke(KaraokeBase):
    """AirPlay karaoke lyrics display via shairport-sync metadata."""

    # Persist track metadata across instances. shairport-sync only sends
    # track info on changes and prgr events infrequently, so when the
    # screensaver restarts (max_ticks rotation), a new instance would
    # otherwise have no track info or playing state until the next event.
    _last_known_track = None
    _last_known_artist = None
    _last_known_position = 0
    _last_known_duration = 0
    _last_known_poll_time = 0
    _last_known_playing = False

    def __init__(self, led_frame_player=None):
        super().__init__(led_frame_player)

        # AirPlay-specific configuration
        self.__metadata_pipe = Config.get(
            'airplay_karaoke.metadata_pipe', '/tmp/shairport-sync-metadata'
        )
        self._max_ticks = Config.get('airplay_karaoke.max_ticks', 6000)
        self._tick_sleep = Config.get('airplay_karaoke.tick_sleep', 0.05)
        self._pulse_lyrics = Config.get('airplay_karaoke.pulse_lyrics', True)

    def _connect(self) -> bool:
        """Check if shairport-sync metadata pipe exists."""
        if os.path.exists(self.__metadata_pipe):
            self._logger.info(f"Metadata pipe found: {self.__metadata_pipe}")

            # Restore last known state from previous instance (see class-level
            # comment). Position and poll_time let the base class extrapolate
            # the current lyrics position instead of jumping to 0:00.
            if AirPlayKaraoke._last_known_track:
                with self._poll_lock:
                    self._current_track = AirPlayKaraoke._last_known_track
                    self._current_artist = AirPlayKaraoke._last_known_artist
                    self._position_seconds = AirPlayKaraoke._last_known_position
                    self._song_duration = AirPlayKaraoke._last_known_duration
                    self._last_poll_time = AirPlayKaraoke._last_known_poll_time
                    self._is_playing = AirPlayKaraoke._last_known_playing
                self._logger.info(
                    f"Restored track: '{self._current_track}' by '{self._current_artist}' "
                    f"playing={self._is_playing}"
                )

            return True
        self._logger.warning(f"Metadata pipe not found: {self.__metadata_pipe}")
        return False

    def _polling_loop(self):
        """Read shairport-sync metadata pipe continuously."""
        while self._polling_active:
            try:
                # Open pipe - blocks until a writer opens the other end
                with open(self.__metadata_pipe, 'r') as pipe:
                    buffer = ''
                    pending_metadata = {}

                    while self._polling_active:
                        line = pipe.readline()
                        if not line:
                            # Pipe closed (writer disconnected)
                            self._logger.info("Metadata pipe closed, setting _is_playing=False, will reopen")
                            with self._poll_lock:
                                self._is_playing = False
                                AirPlayKaraoke._last_known_playing = False
                            break

                        buffer += line

                        # Process complete <item>...</item> blocks
                        while '<item>' in buffer and '</item>' in buffer:
                            start = buffer.index('<item>')
                            end = buffer.index('</item>') + len('</item>')
                            item_xml = buffer[start:end]
                            buffer = buffer[end:]

                            self.__process_item(item_xml, pending_metadata)

            except FileNotFoundError:
                self._logger.debug("Metadata pipe not found, waiting...")
                # Sleep in small increments to allow quick shutdown
                for _ in range(10):
                    if not self._polling_active:
                        return
                    time.sleep(0.1)
            except Exception as e:
                self._logger.error(f"Error reading metadata pipe: {e}")
                for _ in range(10):
                    if not self._polling_active:
                        return
                    time.sleep(0.1)

    def __process_item(self, item_xml, pending_metadata):
        """Process a single metadata item from the pipe.

        shairport-sync metadata format:
        <item><type>hex</type><code>hex</code><length>N</length>
              <data encoding="base64">...</data></item>

        Type and code are 4-char ASCII strings encoded as 8 hex digits.
        """
        type_match = re.search(r'<type>([\da-fA-F]+)</type>', item_xml)
        code_match = re.search(r'<code>([\da-fA-F]+)</code>', item_xml)

        if not type_match or not code_match:
            return

        try:
            item_type = bytes.fromhex(type_match.group(1)).decode('ascii', errors='ignore')
            item_code = bytes.fromhex(code_match.group(1)).decode('ascii', errors='ignore')
        except (ValueError, UnicodeDecodeError):
            return

        # Extract data if present
        data_match = re.search(r'<data encoding="base64">\s*(.*?)\s*</data>', item_xml, re.DOTALL)
        data = ''
        if data_match:
            try:
                data = base64.b64decode(data_match.group(1)).decode('utf-8', errors='ignore')
            except Exception:
                data = ''

        if item_code != 'PICT':
            log_data = data[:100] if data else ''
            self._logger.debug(f"Pipe item: type={item_type} code={item_code} data={log_data!r}")

        # Handle metadata batching (mdst/mden bracket a set of metadata items)
        if item_type == 'ssnc':
            if item_code == 'mdst':
                pending_metadata.clear()
                return
            elif item_code == 'mden':
                # Metadata batch complete — apply to instance and persist to
                # class state for survival across max_ticks restarts.
                with self._poll_lock:
                    if 'title' in pending_metadata:
                        self._current_track = pending_metadata['title']
                        AirPlayKaraoke._last_known_track = self._current_track
                    if 'artist' in pending_metadata:
                        self._current_artist = pending_metadata['artist']
                        AirPlayKaraoke._last_known_artist = self._current_artist
                pending_metadata.clear()
                return
            elif item_code == 'prgr':
                self.__parse_progress(data)
                return
            elif item_code == 'pbeg':
                self._logger.info("Received pbeg, setting _is_playing=True")
                with self._poll_lock:
                    self._is_playing = True
                    AirPlayKaraoke._last_known_playing = True
                return
            elif item_code in ('pfls', 'paus'):
                # Pause — freeze lyrics at current position
                self._logger.info(f"Received {item_code} (pause), setting _is_playing=False")
                with self._poll_lock:
                    self._is_playing = False
                    AirPlayKaraoke._last_known_playing = False
                return
            elif item_code == 'prsm':
                # Resume — update poll time so interpolation doesn't jump
                # forward by the pause duration
                self._logger.info("Received prsm (resume), setting _is_playing=True")
                with self._poll_lock:
                    self._is_playing = True
                    self._last_poll_time = time.time()
                    AirPlayKaraoke._last_known_playing = True
                    AirPlayKaraoke._last_known_poll_time = self._last_poll_time
                return
            elif item_code == 'pend':
                # Playback genuinely ended — clear both instance and class-level
                # state so the display shows "NO MUSIC" and a future instance
                # won't restore stale track info.
                self._logger.info("Received pend, setting _is_playing=False")
                with self._poll_lock:
                    self._is_playing = False
                    self._current_track = None
                    self._current_artist = None
                    AirPlayKaraoke._last_known_track = None
                    AirPlayKaraoke._last_known_artist = None
                    AirPlayKaraoke._last_known_position = 0
                    AirPlayKaraoke._last_known_duration = 0
                    AirPlayKaraoke._last_known_poll_time = 0
                    AirPlayKaraoke._last_known_playing = False
                return

        # Collect core metadata items.
        # Only store non-empty values: we suspect shairport-sync may send
        # metadata batches with empty fields mid-song (e.g. during AirPlay
        # session renegotiation). Without this guard, _current_track would
        # become '' (falsy), __check_track_change would clear the lyrics,
        # and the display would briefly flash "NO MUSIC ON AIRPLAY" until
        # the next metadata batch arrives with the real track info.
        if item_type == 'core':
            if item_code == 'minm' and data:
                pending_metadata['title'] = data
            elif item_code == 'asar' and data:
                pending_metadata['artist'] = data
            elif item_code == 'asal' and data:
                pending_metadata['album'] = data

    def __parse_progress(self, data):
        """Parse progress string: 'start/current/end' as RTP frame numbers at 44100 Hz."""
        try:
            parts = data.strip().split('/')
            if len(parts) != 3:
                return

            start_rtp = int(parts[0])
            current_rtp = int(parts[1])
            end_rtp = int(parts[2])

            position_seconds = (current_rtp - start_rtp) / 44100.0
            duration_seconds = (end_rtp - start_rtp) / 44100.0

            with self._poll_lock:
                self._position_seconds = max(0, position_seconds)
                self._song_duration = max(0, duration_seconds)
                self._last_poll_time = time.time()
                self._is_playing = True

                # Persist to class state so a new instance after max_ticks
                # rotation can resume lyrics from the right position.
                AirPlayKaraoke._last_known_position = self._position_seconds
                AirPlayKaraoke._last_known_duration = self._song_duration
                AirPlayKaraoke._last_known_poll_time = self._last_poll_time
                AirPlayKaraoke._last_known_playing = True
        except (ValueError, ZeroDivisionError):
            pass

    def _get_source_display_name(self) -> str:
        return "AIRPLAY"

    def _render_connection_error(self, frame):
        textutils.draw_text(frame, "NO AIRPLAY", 4, 8, (255, 100, 100), self._width, self._height)
        textutils.draw_text(frame, "FOUND", 16, 18, (255, 100, 100), self._width, self._height)

    @classmethod
    def get_id(cls) -> str:
        return 'airplay_karaoke'

    @classmethod
    def get_name(cls) -> str:
        return 'AirPlay Karaoke'

    @classmethod
    def get_description(cls) -> str:
        return 'Synced lyrics display for AirPlay playback via shairport-sync'
