# Pifi

A Raspberry Pi-based LED matrix display system for playing YouTube videos, screensavers, and games (Snake).

## Project Structure

```
pifi/
├── server.py           # HTTP API server (port 80/443) for web interface
├── queue.py            # Main playback loop - manages video/game/screensaver playback
├── playlist.py         # Playlist/queue management with SQLite
├── database.py         # SQLite database with schema migrations
├── config.py           # JSON config loader (config.json + default_config.json)
├── video/
│   ├── videoprocessor.py    # Downloads videos via yt-dlp, processes frames with ffmpeg
│   ├── videocolormode.py    # Color mode constants (color, grayscale, R/G/B, invert)
│   └── videoscreensaver.py  # Screensaver video playback
├── led/
│   ├── ledframeplayer.py    # Frame rendering with gamma correction
│   ├── gamma.py             # Gamma correction curves
│   └── drivers/             # LED driver implementations
│       ├── driverapa102.py      # APA102 LED strip driver
│       ├── driverrgbmatrix.py   # RGB Matrix (HUB75) driver
│       └── driverws2812b.py     # WS2812B LED strip driver
├── games/
│   ├── snake.py             # Snake game implementation
│   ├── snakeplayer.py       # Player state/controls for Snake
│   ├── scores.py            # High score tracking
│   └── cellularautomata/    # Game of Life and Cyclic automaton screensavers
├── websocketserver.py   # WebSocket server for real-time game controls
├── volumecontroller.py  # System volume control via amixer
├── settingsdb.py        # Persistent settings storage
└── screensavermanager.py # Screensaver selection and management
```

## Configuration

Configuration is loaded from `config.json` (merged with `default_config.json`). Key settings:

- `leds.driver`: LED driver type (`apa102`, `rgbmatrix`, `ws2812b`)
- `leds.display_width` / `leds.display_height`: LED matrix dimensions
- `leds.flip_x` / `leds.flip_y`: Display orientation
- `video.color_mode`: Color rendering mode
- `video.should_save_video`: Cache downloaded videos
- `server.use_ssl`: Enable HTTPS

Config uses dot notation for nested keys: `Config.get('leds.display_width')`

## Key Dependencies

- `yt-dlp`: YouTube video downloading
- `ffmpeg`/`ffplay`: Video processing and audio playback
- `numpy`: Frame buffer manipulation
- `sqlite3`: Database for playlist, scores, settings
- `simpleaudio`/`pygame.mixer`: Sound effects and music
- `pyjson5`: JSON5 config parsing
- `mbuffer`: Video streaming buffer

## Running

The system runs two main processes:

1. **Queue process** (`bin/queue`): Main playback loop
2. **Server process** (`bin/server`): HTTP API on port 80/443

## API Endpoints

- `GET /api/queue` - Get current queue and player state
- `POST /api/queue` - Enqueue a video
- `POST /api/skip` - Skip current video
- `POST /api/clear` - Clear queue
- `POST /api/vol_pct` - Set volume
- `POST /api/enqueue_or_join_game` - Start/join Snake game
- `GET /api/high_scores` - Get game high scores

## Development Notes

- Use `/usr/bin/git` instead of `git` for git operations
- Database schema version is tracked; migrations run automatically
- LED drivers may have constraints on multiple simultaneous instances
- Video processing uses FIFOs for inter-process communication
- Games communicate with web clients via Unix domain sockets + WebSockets
