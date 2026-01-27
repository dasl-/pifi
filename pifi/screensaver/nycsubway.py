"""
NYC Subway Screensaver.

Displays real-time arrival times for NYC subway trains at configured stations.
Uses the MTA's GTFS-realtime feed via the underground library.
"""

# Work around protobuf C extension compatibility issues with Python 3.12+
# Must be set before protobuf is imported anywhere
# See: https://github.com/protocolbuffers/protobuf/issues/12186
import os
os.environ.setdefault('PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION', 'python')

import numpy as np
import time
import threading
from datetime import datetime, timezone

from pifi.config import Config
from pifi.led.ledframeplayer import LedFramePlayer
from pifi.logger import Logger
from pifi.screensaver.screensaver import Screensaver


class NycSubway(Screensaver):
    """NYC Subway arrival times display."""

    # MTA line colors (official colors)
    LINE_COLORS = {
        '1': (238, 53, 46), '2': (238, 53, 46), '3': (238, 53, 46),
        '4': (0, 147, 60), '5': (0, 147, 60), '6': (0, 147, 60), '6X': (0, 147, 60),
        '7': (185, 51, 173), '7X': (185, 51, 173),
        'A': (0, 57, 166), 'C': (0, 57, 166), 'E': (0, 57, 166),
        'B': (255, 99, 25), 'D': (255, 99, 25), 'F': (255, 99, 25), 'FX': (255, 99, 25), 'M': (255, 99, 25),
        'G': (108, 190, 69),
        'J': (153, 102, 51), 'Z': (153, 102, 51),
        'L': (167, 169, 172),
        'N': (252, 204, 10), 'Q': (252, 204, 10), 'R': (252, 204, 10), 'W': (252, 204, 10),
        'S': (128, 129, 131), 'FS': (128, 129, 131), 'GS': (128, 129, 131), 'H': (128, 129, 131),
        'SIR': (0, 57, 166),
    }

    # Feed URLs for each line
    FEED_URLS = {
        '1': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs',
        '2': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs',
        '3': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs',
        '4': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs',
        '5': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs',
        '6': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs',
        '7': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-7',
        'A': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-ace',
        'C': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-ace',
        'E': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-ace',
        'B': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-bdfm',
        'D': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-bdfm',
        'F': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-bdfm',
        'M': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-bdfm',
        'G': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-g',
        'J': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-jz',
        'Z': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-jz',
        'L': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-l',
        'N': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-nqrw',
        'Q': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-nqrw',
        'R': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-nqrw',
        'W': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-nqrw',
        'S': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-si',
    }

    # Simple 3x5 font for digits and letters
    # Optimized for readability at low resolution
    FONT = {
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
        'Q': [[0,1,0],[1,0,1],[1,0,1],[1,0,1],[0,1,1]],  # Fixed: cleaner Q with small tail
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
        ':': [[0,0,0],[0,1,0],[0,0,0],[0,1,0],[0,0,0]],
        '-': [[0,0,0],[0,0,0],[1,1,1],[0,0,0],[0,0,0]],
        '+': [[0,0,0],[0,1,0],[1,1,1],[0,1,0],[0,0,0]],
        # Direction arrows (chevron style)
        '^': [[0,1,0],[1,0,1],[0,0,0],[0,0,0],[0,0,0]],  # Up arrow
        'v': [[0,0,0],[0,0,0],[0,0,0],[1,0,1],[0,1,0]],  # Down arrow
        ',': [[0,0,0],[0,0,0],[0,0,0],[0,1,0],[1,0,0]],  # Comma
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
        self.__stop_ids = Config.get('nycsubway.stop_ids', ['127N', '127S'])
        self.__lines = Config.get('nycsubway.lines', ['1', '2', '3'])
        self.__update_interval = Config.get('nycsubway.update_interval', 30)
        self.__max_arrivals = Config.get('nycsubway.max_arrivals', 4)
        self.__max_ticks = Config.get('nycsubway.max_ticks', 3000)
        self.__tick_sleep = Config.get('nycsubway.tick_sleep', 1.0)

        # State
        self.__arrivals = []
        self.__last_update = 0
        self.__error_message = None
        self.__underground = None
        self.__scroll_offset = 0  # For scrolling station names
        self.__grouped_arrivals = []  # Arrivals grouped by (stop_id, line)
        self.__station_names = {}  # Cache: stop_id -> station name
        self.__station_names_loaded = False
        self.__fetch_in_progress = False  # Background fetch flag
        self.__fetch_lock = threading.Lock()  # Protect shared state

    def __init_feed(self):
        """Initialize the underground library."""
        if self.__underground is not None:
            return True

        try:
            import underground
            self.__underground = underground
            self.__logger.info("underground library loaded successfully")

            # Load station names on first init
            if not self.__station_names_loaded:
                self.__load_station_names()

            return True
        except ImportError:
            self.__error_message = "NO LIB"
            self.__logger.error("underground not installed. Run: pip install underground")
            return False
        except Exception as e:
            self.__error_message = "ERR"
            self.__logger.error(f"Failed to load underground: {e}")
            return False

    def __load_station_names(self):
        """Load station names from cache or MTA's GTFS static data."""
        self.__station_names_loaded = True

        import json
        from pathlib import Path

        # Cache file location
        cache_dir = Path.home() / '.cache' / 'pifi'
        cache_file = cache_dir / 'mta_stations.json'
        cache_max_age = 7 * 24 * 60 * 60  # 7 days in seconds

        # Try to load from cache first
        try:
            if cache_file.exists():
                cache_age = time.time() - cache_file.stat().st_mtime
                if cache_age < cache_max_age:
                    with open(cache_file, 'r') as f:
                        self.__station_names = json.load(f)
                    self.__logger.info(f"Loaded {len(self.__station_names)} station names from cache")
                    return
                else:
                    self.__logger.info("Station cache expired, refreshing...")
        except Exception as e:
            self.__logger.warning(f"Failed to load cache: {e}")

        # Fetch from MTA
        try:
            import requests
            import csv
            import io
            import zipfile

            # MTA's static GTFS feed URL
            gtfs_url = "http://web.mta.info/developers/data/nyct/subway/google_transit.zip"

            self.__logger.info("Fetching MTA station names...")
            response = requests.get(gtfs_url, timeout=30)
            response.raise_for_status()

            # Extract stops.txt from the zip
            with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
                with zf.open('stops.txt') as f:
                    reader = csv.DictReader(io.TextIOWrapper(f, 'utf-8'))
                    for row in reader:
                        stop_id = row.get('stop_id', '')
                        stop_name = row.get('stop_name', '')
                        if stop_id and stop_name:
                            # Shorten common suffixes
                            short_name = stop_name.upper()
                            short_name = short_name.replace(' - ', '-')
                            short_name = short_name.replace(' STREET', ' ST')
                            short_name = short_name.replace(' AVENUE', ' AV')
                            short_name = short_name.replace(' SQUARE', ' SQ')
                            short_name = short_name.replace(' BOULEVARD', ' BLVD')
                            short_name = short_name.replace(' PARKWAY', ' PKY')
                            short_name = short_name.replace(' JUNCTION', ' JCT')
                            short_name = short_name.replace(' HEIGHTS', ' HTS')
                            short_name = short_name.replace(' CENTER', ' CTR')
                            short_name = short_name.replace(' CENTRAL', ' CNTRL')
                            short_name = short_name.replace('GRAND CENTRAL', 'GR CNTRL')
                            short_name = short_name.replace('TIMES SQUARE', 'TIMES SQ')
                            self.__station_names[stop_id] = short_name

            self.__logger.info(f"Loaded {len(self.__station_names)} station names from MTA")

            # Save to cache
            try:
                cache_dir.mkdir(parents=True, exist_ok=True)
                with open(cache_file, 'w') as f:
                    json.dump(self.__station_names, f)
                self.__logger.info("Saved station names to cache")
            except Exception as e:
                self.__logger.warning(f"Failed to save cache: {e}")

        except Exception as e:
            self.__logger.warning(f"Failed to load station names: {e}")
            # Continue without station names - will fall back to stop_id

    def __fetch_arrivals(self):
        """Fetch arrival times from MTA feed."""
        if not self.__init_feed():
            return

        try:
            arrivals = []
            now = datetime.now(timezone.utc)

            # Get unique feeds needed for our lines
            feeds_to_check = set()
            for line in self.__lines:
                if line in self.FEED_URLS:
                    feeds_to_check.add(self.FEED_URLS[line])

            for feed_url in feeds_to_check:
                try:
                    feed = self.__underground.SubwayFeed.get(feed_url)

                    # extract_stop_dict returns: {"route_id": {"stop_id": [datetime, ...]}}
                    stop_dict = feed.extract_stop_dict()

                    for route_id, stops in stop_dict.items():
                        # Check if this is one of our lines
                        if route_id not in self.__lines:
                            continue

                        for stop_id, times in stops.items():
                            # Check if this is one of our stops
                            if stop_id not in self.__stop_ids:
                                continue

                            for arr_time in times:
                                # Ensure timezone aware comparison
                                if arr_time.tzinfo is None:
                                    arr_time = arr_time.replace(tzinfo=timezone.utc)
                                if arr_time > now:
                                    minutes = int((arr_time - now).total_seconds() / 60)
                                    arrivals.append({
                                        'line': route_id,
                                        'minutes': minutes,
                                        'stop_id': stop_id,
                                    })

                except Exception as e:
                    self.__logger.warning(f"Error fetching feed {feed_url}: {e}")

            # Sort by arrival time
            arrivals.sort(key=lambda x: x['minutes'])
            self.__arrivals = arrivals
            self.__error_message = None
            self.__logger.info(f"Fetched {len(self.__arrivals)} arrivals")

            # Group arrivals by stop_id
            self.__group_arrivals()

        except Exception as e:
            self.__error_message = "ERR"
            self.__logger.error(f"Failed to fetch arrivals: {e}")

    def __group_arrivals(self):
        """Group arrivals by (stop_id, line) pair with multiple times."""
        groups = {}

        for arrival in self.__arrivals:
            stop_id = arrival['stop_id']
            line = arrival['line']
            minutes = arrival['minutes']

            # Group key is (stop_id, line) to avoid ambiguity
            key = (stop_id, line)

            if key not in groups:
                # Get station name from cache, or use stop_id as fallback
                # Try with direction suffix first, then without
                station_name = self.__station_names.get(stop_id)
                if not station_name:
                    base_stop_id = stop_id[:-1] if stop_id and stop_id[-1] in 'NS' else stop_id
                    station_name = self.__station_names.get(base_stop_id, stop_id)

                direction = stop_id[-1] if stop_id and stop_id[-1] in 'NS' else ''

                groups[key] = {
                    'stop_id': stop_id,
                    'line': line,
                    'station_name': station_name,
                    'direction': direction,
                    'times': [],  # [minutes, ...]
                }

            groups[key]['times'].append(minutes)

        # Convert to list and sort
        grouped = list(groups.values())
        for g in grouped:
            g['times'].sort()
            g['earliest'] = g['times'][0] if g['times'] else 999

        grouped.sort(key=lambda x: x['earliest'])

        # Thread-safe update of grouped arrivals
        with self.__fetch_lock:
            self.__grouped_arrivals = grouped[:self.__max_arrivals]

    def play(self):
        """Run the screensaver."""
        self.__logger.info("Starting NYC Subway screensaver")

        # Start initial fetch in background
        self.__start_background_fetch()

        for tick in range(self.__max_ticks):
            # Start background fetch if needed (non-blocking)
            current_time = time.time()
            if current_time - self.__last_update > self.__update_interval:
                self.__start_background_fetch()
                self.__last_update = current_time

            self.__render()
            time.sleep(self.__tick_sleep)

        self.__logger.info("NYC Subway screensaver ended")

    def __start_background_fetch(self):
        """Start a background thread to fetch arrivals."""
        if self.__fetch_in_progress:
            return  # Already fetching

        self.__fetch_in_progress = True
        thread = threading.Thread(target=self.__fetch_arrivals_background, daemon=True)
        thread.start()

    def __fetch_arrivals_background(self):
        """Fetch arrivals in background thread."""
        try:
            self.__fetch_arrivals()
        finally:
            self.__fetch_in_progress = False

    def __render(self):
        """Render the current arrivals to the display."""
        frame = np.zeros((self.__height, self.__width, 3), dtype=np.uint8)

        # Thread-safe copy of arrivals
        with self.__fetch_lock:
            grouped_arrivals = list(self.__grouped_arrivals)

        if self.__error_message:
            self.__draw_text(frame, self.__error_message, 1, 1, (255, 100, 100))
        elif not grouped_arrivals:
            self.__draw_text(frame, "---", 1, 1, (100, 100, 100))
        else:
            # Layout: each row is one (station, line) pair
            # [Line bullet] [Direction] [Station name scrolling] [Times]
            row_height = 8  # 7px content + 1px spacing
            max_rows = self.__height // row_height

            for i, group in enumerate(grouped_arrivals[:max_rows]):
                y = i * row_height

                line = group['line']
                direction = group['direction']
                station_name = group['station_name']
                times = group['times']

                # Draw line bullet
                color = self.LINE_COLORS.get(line, (150, 150, 150))
                self.__draw_bullet(frame, 0, y, line, color)

                # Position after bullet
                after_bullet = 8

                # Draw direction arrow
                if direction == 'N':
                    self.__draw_char(frame, '^', after_bullet, y + 1, (100, 100, 100))
                elif direction == 'S':
                    self.__draw_char(frame, 'v', after_bullet, y + 1, (100, 100, 100))

                # Build times string: "3,7" (max 2 times to leave room for station name)
                times_str = ','.join(str(t) for t in times[:2])

                # Calculate positions for scrolling station name
                # Times go on the right side
                times_width = len(times_str) * 4
                times_x = self.__width - times_width

                # Station name scrolls in the middle section (tighter margins)
                name_start_x = after_bullet + 4
                name_end_x = times_x - 1
                name_width = name_end_x - name_start_x

                if name_width > 0:
                    # Draw scrolling station name
                    self.__draw_scrolling_text(
                        frame, station_name,
                        name_start_x, y + 1,
                        name_width,
                        (180, 180, 180)
                    )

                # Draw times on the right
                self.__draw_text(frame, times_str, times_x, y + 1, (255, 255, 255))

            # Advance scroll (1.0 per tick for smooth, readable speed)
            self.__scroll_offset += 1.0

        self.__led_frame_player.play_frame(frame)

    def __draw_scrolling_text(self, frame, text, x, y, max_width, color):
        """Draw text that scrolls horizontally if too wide, with partial character clipping."""
        text_width = len(text) * 4

        if text_width <= max_width:
            # Text fits, just draw it centered
            self.__draw_text(frame, text, x, y, color)
        else:
            # Text needs to scroll
            # Add spacing for wrap-around
            padded_text = text + "   " + text

            # Calculate scroll position
            scroll_pos = int(self.__scroll_offset) % (text_width + 12)  # 12 = 3 spaces * 4

            # Draw characters with clipping for partial visibility
            cursor = x - scroll_pos
            for char in padded_text:
                char_end = cursor + 3  # 3-pixel wide characters

                # Check if any part of this character is visible
                if char_end >= x and cursor < x + max_width:
                    self.__draw_char_clipped(frame, char, cursor, y, color, x, x + max_width)

                if cursor >= x + max_width:
                    break
                cursor += 4

    def __draw_char_clipped(self, frame, char, x, y, color, clip_left, clip_right):
        """Draw a single 3x5 character with horizontal clipping."""
        char = char.upper()
        if char not in self.FONT:
            return

        pattern = self.FONT[char]
        for dy, row in enumerate(pattern):
            for dx, pixel in enumerate(row):
                if pixel:
                    px, py = x + dx, y + dy
                    # Apply clipping
                    if px >= clip_left and px < clip_right:
                        if 0 <= px < self.__width and 0 <= py < self.__height:
                            frame[py, px] = color

    def __draw_bullet(self, frame, x, y, line, color):
        """Draw a 7x7 colored circle with line letter, MTA style."""
        # 7x7 circle pattern (1 = filled, 0 = empty)
        circle = [
            [0, 0, 1, 1, 1, 0, 0],
            [0, 1, 1, 1, 1, 1, 0],
            [1, 1, 1, 1, 1, 1, 1],
            [1, 1, 1, 1, 1, 1, 1],
            [1, 1, 1, 1, 1, 1, 1],
            [0, 1, 1, 1, 1, 1, 0],
            [0, 0, 1, 1, 1, 0, 0],
        ]

        # Draw the circle
        for dy in range(7):
            for dx in range(7):
                if circle[dy][dx]:
                    px, py = x + dx, y + dy
                    if 0 <= px < self.__width and 0 <= py < self.__height:
                        frame[py, px] = color

        # Draw line letter/number centered (3x5 font centered in 7x7)
        char = line[0].upper()
        # Text color: black on light backgrounds, white on dark
        brightness = (color[0] * 0.299 + color[1] * 0.587 + color[2] * 0.114)
        text_color = (0, 0, 0) if brightness > 128 else (255, 255, 255)
        # Center the 3x5 char in the 7x7 circle: x+2, y+1
        self.__draw_char(frame, char, x + 2, y + 1, text_color)

    def __draw_char(self, frame, char, x, y, color):
        """Draw a single 3x5 character."""
        char = char.upper()
        if char not in self.FONT:
            return

        pattern = self.FONT[char]
        for dy, row in enumerate(pattern):
            for dx, pixel in enumerate(row):
                if pixel:
                    px, py = x + dx, y + dy
                    if 0 <= px < self.__width and 0 <= py < self.__height:
                        frame[py, px] = color

    def __draw_text(self, frame, text, x, y, color):
        """Draw a text string."""
        cursor = x
        for char in text:
            self.__draw_char(frame, char, cursor, y, color)
            cursor += 4  # 3px char + 1px spacing

    @classmethod
    def get_id(cls) -> str:
        return 'nyc_subway'

    @classmethod
    def get_name(cls) -> str:
        return 'NYC Subway'

    @classmethod
    def get_description(cls) -> str:
        return 'Real-time NYC subway arrival times'
