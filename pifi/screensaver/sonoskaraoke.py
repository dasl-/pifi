"""
Sonos Karaoke Screensaver.

Displays synced lyrics from currently playing Sonos track.
Uses SoCo for Sonos integration and syncedlyrics for lyrics fetching.
"""

import numpy as np
import time

from pifi.config import Config
from pifi.screensaver.karaokebase import KaraokeBase
from pifi.screensaver import textutils


class SonosKaraoke(KaraokeBase):
    """Sonos karaoke lyrics display."""

    def __init__(self, led_frame_player=None):
        super().__init__(led_frame_player)

        # Sonos-specific configuration
        self.__speaker_name = Config.get('sonos_karaoke.speaker_name', None)
        self.__update_interval = Config.get('sonos_karaoke.update_interval', 0.5)
        self._max_ticks = Config.get('sonos_karaoke.max_ticks', 6000)
        self._tick_sleep = Config.get('sonos_karaoke.tick_sleep', 0.05)
        self._pulse_lyrics = Config.get('sonos_karaoke.pulse_lyrics', True)

        # Sonos speaker reference
        self.__speaker = None

    def _connect(self) -> bool:
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

            speaker_list = sorted(list(speakers), key=lambda s: s.player_name)
            self._logger.info(f"Discovered {len(speaker_list)} Sonos speakers")

            if self.__speaker_name:
                for speaker in speaker_list:
                    if speaker.player_name.lower() == self.__speaker_name.lower():
                        self.__speaker = speaker
                        return True
                self._logger.warning(
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

                    self._logger.info(
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
                    self._logger.warning(f"  {speaker.player_name}: error - {e}")
                    continue

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
                self._logger.info(
                    f"Selected: {self.__speaker.player_name} "
                    f"(score={score(best)}, playing={best['is_playing']}, track={best['has_track']})"
                )
                return True

            # Fallback
            self.__speaker = speaker_list[0]
            self._logger.info(f"Fallback to: {self.__speaker.player_name}")
            return True

        except ImportError:
            self._logger.error("soco library not installed. Run: pip install soco")
        except Exception as e:
            self._logger.error(f"Error connecting to Sonos: {e}")

        return False

    def _polling_loop(self):
        """Background thread for Sonos polling."""
        while self._polling_active:
            self.__poll_sonos()
            # Sleep in small increments to allow quick shutdown
            for _ in range(max(1, int(self.__update_interval * 10))):
                if not self._polling_active:
                    break
                time.sleep(0.1)

    def __poll_sonos(self):
        """Poll Sonos for current track info."""
        if not self.__speaker:
            self._logger.debug("No speaker connected")
            return

        try:
            track_info = self.__speaker.get_current_track_info()
            transport_info = self.__speaker.get_current_transport_info()

            title = track_info.get('title', '')
            artist = track_info.get('artist', '')
            position = track_info.get('position', '0:00:00')
            duration = track_info.get('duration', '0:00:00')
            state = transport_info.get('current_transport_state', '')

            position_seconds = self.__parse_time(position)
            song_duration = self.__parse_time(duration)
            poll_time = time.time()
            is_playing = state == 'PLAYING'

            with self._poll_lock:
                self._position_seconds = position_seconds
                self._song_duration = song_duration
                self._last_poll_time = poll_time
                self._is_playing = is_playing
                self._current_track = title
                self._current_artist = artist

                self._logger.debug(
                    f"Poll: state={state}, title='{title}', artist='{artist}', pos={position}"
                )

        except Exception as e:
            self._logger.error(f"Error polling Sonos: {e}")

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

    def _get_source_display_name(self) -> str:
        if self.__speaker:
            return self.__speaker.player_name.upper()
        if self.__speaker_name:
            return self.__speaker_name.upper()
        return "SONOS"

    def _render_connection_error(self, frame):
        textutils.draw_text(frame, "NO SONOS", 8, 8, (255, 100, 100), self._width, self._height)
        textutils.draw_text(frame, "FOUND", 16, 18, (255, 100, 100), self._width, self._height)

    @classmethod
    def get_id(cls) -> str:
        return 'sonos_karaoke'

    @classmethod
    def get_name(cls) -> str:
        return 'Sonos Karaoke'

    @classmethod
    def get_description(cls) -> str:
        return 'Synced lyrics display for Sonos playback'
