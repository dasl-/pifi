from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler, HTTPStatus
from io import BytesIO
import json
import ssl
import traceback
import urllib
from urllib.parse import urlparse
import time
from pifi.playlist import Playlist
from pifi.logger import Logger
from pifi.config import Config
from pifi.directoryutils import DirectoryUtils
from pifi.volumecontroller import VolumeController
from pifi.games.scores import Scores
from pifi.games.snake import Snake
from pifi.games.pong import Pong
from pifi.games.unixsockethelper import UnixSocketHelper
from pifi.settingsdb import SettingsDb
from pifi.database import Database

class PifiAPI():

    def __init__(self):
        self.__playlist = Playlist()
        self.__vol_controller = VolumeController()
        self.__settings_db = SettingsDb()
        self.__logger = Logger().set_namespace(self.__class__.__name__)

    # get all the data that we poll for every second in the pifi
    def get_queue(self):
        response_details = {}
        queue = self.__playlist.get_queue()
        response_details['queue'] = queue
        response_details['vol_pct'] = self.__vol_controller.get_vol_pct()
        response_details[SettingsDb.SCREENSAVER_SETTING] = self.__settings_db.is_enabled(SettingsDb.SCREENSAVER_SETTING, True)
        response_details['success'] = True
        return response_details

    # get all the data that we poll for every second in snake
    def get_snake_data(self):
        is_game_joinable = False
        game_joinable_countdown_s = None
        current_video = self.__playlist.get_current_video()
        if (
            current_video and current_video['type'] == Playlist.TYPE_GAME and current_video['title'] == Snake.GAME_TITLE and
            current_video['status'] == Playlist.STATUS_PLAYING_WAITING_FOR_PLAYERS
        ):
            is_game_joinable = True
            current_video_create_date = Database.database_date_to_unix_time(current_video['create_date'])
            game_joinable_countdown_s = max(
                round(UnixSocketHelper.MAX_MULTI_PLAYER_JOIN_TIME_S - (time.time() - current_video_create_date), 0),
                0
            )

        return {
            'is_game_joinable': is_game_joinable,
            'game_joinable_countdown_s': game_joinable_countdown_s,
            'vol_pct': self.__vol_controller.get_vol_pct(),
            'success': True
        }

    def get_volume(self):
        response_details = {}
        response_details['vol_pct'] = self.__vol_controller.get_vol_pct()
        response_details['success'] = True
        return response_details

    def enqueue(self, post_data):
        self.__playlist.enqueue(
            post_data['url'], post_data['color_mode'], post_data['thumbnail'], post_data['title'], post_data['duration'], Playlist.TYPE_VIDEO, ''
        )
        response_details = post_data
        response_details['success'] = True
        return response_details

    def enqueue_or_join_game(self, post_data):
        title = post_data['title']
        game_playlist_video_id = None
        did_join_existing_game = None
        num_players = None
        game_settings = {}

        current_video = self.__playlist.get_current_video()
        if (
            current_video and current_video['type'] == Playlist.TYPE_GAME and current_video['title'] == title and
            current_video['status'] == Playlist.STATUS_PLAYING_WAITING_FOR_PLAYERS
        ):
            # join game
            game_playlist_video_id = current_video['playlist_video_id']
            did_join_existing_game = True
            if title == Snake.GAME_TITLE:
                settings = Snake.make_settings_from_playlist_item(current_video)
                num_players = settings['num_players']
                game_settings['apple_count'] = settings['apple_count']
            elif title == Pong.GAME_TITLE:
                settings = Pong.make_settings_from_playlist_item(current_video)
                num_players = settings['num_players']
                game_settings['target_score'] = settings['target_score']
        else:
            # enqueue game
            game_type = Playlist.TYPE_GAME
            url = None
            duration = 'n/a'
            color_mode = ''

            if title == Snake.GAME_TITLE:
                thumbnail = '/assets/snake/snake-thumbnail.png'
                num_players = int(post_data['num_players'])
                apple_count = int(post_data['apple_count'])
                game_settings['apple_count'] = apple_count
                settings = json.dumps({
                    'difficulty': int(post_data['difficulty']),
                    'num_players': num_players,
                    'apple_count': apple_count,
                })
            elif title == Pong.GAME_TITLE:
                thumbnail = '/assets/pong/pong-thumbnail.png'
                num_players = 2  # Pong is always 2 players
                target_score = int(post_data.get('target_score', 5))
                game_settings['target_score'] = target_score
                settings = json.dumps({
                    'difficulty': int(post_data.get('difficulty', 5)),
                    'target_score': target_score,
                })
            else:
                return {'success': False, 'error': f'Unknown game: {title}'}

            game_playlist_video_id = self.__playlist.enqueue(
                url, color_mode, thumbnail, title, duration, game_type, settings
            )
            did_join_existing_game = False

            # Skip videos in the queue until we get to the game
            # Note: we have logic in the Queue class to re-enqueue videos of type TYPE_VIDEO that were skipped
            # in this manner. The video skipped here will be added back at the head of the queue.
            # See: Queue::__should_reenqueue_current_playlist_item
            while True:
                current_video = self.__playlist.get_current_video()
                if current_video is None:
                    break
                if current_video['playlist_video_id'] < game_playlist_video_id:
                    self.__playlist.skip(current_video['playlist_video_id'])
                else:
                    break

        response = {
            'success': True,
            'playlist_video_id': game_playlist_video_id,
            'did_join_existing_game': did_join_existing_game,
            'num_players': num_players,
        }
        response.update(game_settings)
        return response

    def submit_game_score_initials(self, post_data):
        if len(post_data['initials']) != 3:
            return {'success': False}
        score_id = int(post_data['score_id'])
        initials = post_data['initials'].upper()
        scores = Scores()
        success = scores.update_initials(score_id, initials)
        return {'success': success}

    def get_high_scores(self, get_data):
        game_type = get_data['game_type']
        scores = Scores()
        high_scores = scores.get_high_scores(game_type)
        return {
            'success': True,
            'high_scores': high_scores,
        }

    def skip(self, post_data):
        success = self.__playlist.skip(post_data['playlist_video_id'])
        return {'success': success}

    def remove(self, post_data):
        success = self.__playlist.remove(post_data['playlist_video_id'])
        return {'success': success}

    def clear(self):
        self.__playlist.clear()
        return {'success': True}

    def play_next(self, post_data):
        success = self.__playlist.play_next(post_data['playlist_video_id'])
        return {'success': success}

    def set_screensaver_enabled(self, post_data):
        self.__settings_db.set(SettingsDb.SCREENSAVER_SETTING, bool(post_data[SettingsDb.SCREENSAVER_SETTING]))
        return {'success': True}

    def set_vol_pct(self, post_data):
        vol_pct = int(post_data['vol_pct'])
        self.__vol_controller.set_vol_pct(vol_pct)
        return {
            'vol_pct': vol_pct,
            'success': True
        }

    def get_youtube_api_key(self):
        return {
            SettingsDb.SETTING_YOUTUBE_API_KEY: self.__settings_db.get(SettingsDb.SETTING_YOUTUBE_API_KEY),
            'success': True,
        }

    def get_screensavers(self):
        # All available screensavers
        all_screensavers = [
            {'id': 'game_of_life', 'name': 'Game of Life', 'description': "Conway's cellular automaton"},
            {'id': 'cyclic_automaton', 'name': 'Cyclic Automaton', 'description': 'Colorful cyclic patterns'},
            {'id': 'boids', 'name': 'Boids', 'description': 'Flocking simulation'},
            {'id': 'cosmic_dream', 'name': 'Cosmic Dream', 'description': 'Psychedelic plasma waves'},
            {'id': 'mandelbrot', 'name': 'Mandelbrot', 'description': 'Fractal zoom'},
            {'id': 'wave_interference', 'name': 'Wave Interference', 'description': 'Ripple patterns'},
            {'id': 'spirograph', 'name': 'Spirograph', 'description': 'Geometric curves'},
            {'id': 'lorenz', 'name': 'Lorenz Attractor', 'description': 'Chaotic butterfly'},
            {'id': 'metaballs', 'name': 'Metaballs', 'description': 'Blobby shapes'},
            {'id': 'starfield', 'name': 'Starfield', 'description': '3D star flight'},
            {'id': 'matrix_rain', 'name': 'Matrix Rain', 'description': 'Falling green code'},
            {'id': 'melting_clock', 'name': 'Melting Clock', 'description': 'Dali-style clock'},
            {'id': 'aurora', 'name': 'Aurora Borealis', 'description': 'Northern lights'},
            {'id': 'shadebobs', 'name': 'Shadebobs', 'description': 'Glowing trails'},
            {'id': 'flowfield', 'name': 'Flow Field', 'description': 'Particles in wind'},
            {'id': 'lavalamp', 'name': 'Lava Lamp', 'description': 'Rising and falling blobs'},
            {'id': 'reactiondiffusion', 'name': 'Reaction Diffusion', 'description': 'Organic coral patterns'},
            {'id': 'inkinwater', 'name': 'Ink in Water', 'description': 'Diffusing color blooms'},
            {'id': 'perlinworms', 'name': 'Perlin Worms', 'description': 'Slithering noise trails'},
            {'id': 'pendulumwaves', 'name': 'Pendulum Waves', 'description': 'Synchronized wave patterns'},
            {'id': 'stringart', 'name': 'String Art', 'description': 'Curved envelopes from lines'},
            {'id': 'unknownpleasures', 'name': 'Unknown Pleasures', 'description': 'Joy Division pulsar waves'},
            {'id': 'cloudscape', 'name': 'Cloudscape', 'description': 'Drifting clouds over gradient sky'},
        ]

        # Get enabled screensavers from settings, fall back to config
        enabled_json = self.__settings_db.get(SettingsDb.ENABLED_SCREENSAVERS)
        if enabled_json:
            enabled = json.loads(enabled_json)
        else:
            enabled = Config.get('screensavers.screensavers', ['game_of_life', 'cyclic_automaton'])

        return {
            'success': True,
            'screensavers': all_screensavers,
            'enabled': enabled,
        }

    def set_screensavers(self, post_data):
        enabled = post_data.get('enabled', [])
        self.__settings_db.set(SettingsDb.ENABLED_SCREENSAVERS, json.dumps(enabled))
        # Signal queue to restart screensaver so changes take effect immediately
        self.__settings_db.set(SettingsDb.RESTART_SCREENSAVER, '1')
        return {'success': True, 'enabled': enabled}

class PifiServerRequestHandler(BaseHTTPRequestHandler):

    def __init__(self, request, client_address, server):
        self.__root_dir = DirectoryUtils().root_dir + "/app/build"
        self.__api = PifiAPI()
        self.__logger = Logger().set_namespace(self.__class__.__name__)
        BaseHTTPRequestHandler.__init__(self, request, client_address, server)

    def do_OPTIONS(self):
        self.send_response(200, "ok")
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header("Access-Control-Allow-Headers", "X-Requested-With")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        try:
            if self.path[:4] == "/api":
                return self.__do_api_GET(self.path[5:])

            return self.__serve_static_asset()
        except Exception:
            self.log_error('Exception: {}'.format(traceback.format_exc()))

    def do_POST(self):
        try:
            if self.path[:4] == "/api":
                return self.__do_api_POST(self.path[5:])
            return self.__serve_static_asset()
        except Exception:
            self.log_error('Exception: {}'.format(traceback.format_exc()))

    def __do_404(self):
        self.send_response(404)
        self.end_headers()

    def __do_api_GET(self, path):
        parsed_path = urllib.parse.urlparse(path)
        get_data = urllib.parse.unquote(parsed_path.query)
        if get_data:
            get_data = json.loads(get_data)

        if parsed_path.path == 'queue':
            response = self.__api.get_queue()
        elif parsed_path.path == 'vol_pct':
            response = self.__api.get_volume()
        elif parsed_path.path == 'high_scores':
            response = self.__api.get_high_scores(get_data)
        elif parsed_path.path == 'snake':
            response = self.__api.get_snake_data()
        elif parsed_path.path == 'youtube_api_key':
            response = self.__api.get_youtube_api_key()
        elif parsed_path.path == 'screensavers':
            response = self.__api.get_screensavers()
        else:
            self.__do_404()
            return

        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        resp = BytesIO()
        resp.write(bytes(json.dumps(response), 'utf-8'))
        self.wfile.write(resp.getvalue())

    def __do_api_POST(self, path):
        content_length = int(self.headers['Content-Length'])

        post_data = None
        if content_length > 0:
            body = self.rfile.read(content_length)
            post_data = json.loads(body.decode("utf-8"))

        if path == 'queue':
            response = self.__api.enqueue(post_data)
        elif path == 'skip':
            response = self.__api.skip(post_data)
        elif path == 'remove':
            response = self.__api.remove(post_data)
        elif path == 'clear':
            response = self.__api.clear()
        elif path == 'play_next':
            response = self.__api.play_next(post_data)
        elif path == 'screensaver':
            response = self.__api.set_screensaver_enabled(post_data)
        elif path == 'vol_pct':
            response = self.__api.set_vol_pct(post_data)
        elif path == 'enqueue_or_join_game':
            response = self.__api.enqueue_or_join_game(post_data)
        elif path == 'submit_game_score_initials':
            response = self.__api.submit_game_score_initials(post_data)
        elif path == 'screensavers':
            response = self.__api.set_screensavers(post_data)
        else:
            self.__do_404()
            return

        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        resp = BytesIO()
        resp.write(bytes(json.dumps(response), 'utf-8'))
        self.wfile.write(resp.getvalue())

    def __serve_static_asset(self):
        self.path = urlparse(self.path).path # get rid of query parameters e.g. `?foo=bar&baz=1`
        if self.path == '/':
            self.path = '/index.html'

        if self.path == '/snake' or self.path == '/snake/':
            self.path = DirectoryUtils().root_dir + '/assets/snake/snake.html'
        elif self.path == '/pong' or self.path == '/pong/':
            self.path = DirectoryUtils().root_dir + '/assets/pong/pong.html'
        elif self.path == '/settings' or self.path == '/settings/':
            self.path = DirectoryUtils().root_dir + '/assets/settings/settings.html'
        elif self.path.startswith('/assets/'):
            self.path = DirectoryUtils().root_dir + '/assets/' + self.path[len('/assets/'):]
        else:
            self.path = self.__root_dir + self.path

        try:
            file_to_open = open(self.path, 'rb').read()
            self.send_response(200)
        except Exception as e:
            self.__logger.error(str(e))
            self.log_error('Exception: {}'.format(traceback.format_exc()))
            file_to_open = "File not found"
            self.__do_404()
            return

        if self.path.endswith('.js'):
            self.send_header("Content-Type", "text/javascript")
        elif self.path.endswith('.css'):
            self.send_header("Content-Type", "text/css")
        elif self.path.endswith('.svg') or self.path.endswith('.svgz'):
            self.send_header("Content-Type", "image/svg+xml")
        self.end_headers()

        if type(file_to_open) is bytes:
            self.wfile.write(file_to_open)
        else:
            self.wfile.write(bytes(file_to_open, 'utf-8'))
        return

    def log_request(self, code='-', size='-'):
        if isinstance(code, HTTPStatus):
            code = code.value
        self.log_message('[REQUEST] "%s" %s %s', self.requestline, str(code), str(size))

    def log_error(self, format, *args):
        self.__logger.error("%s - - %s" % (self.client_address[0], format % args))

    def log_message(self, format, *args):
        self.__logger.info("%s - - %s" % (self.client_address[0], format % args))

class PifiThreadingHTTPServer(ThreadingHTTPServer):

    # Override: https://github.com/python/cpython/blob/18cb2ef46c9998480f7182048435bc58265c88f2/Lib/socketserver.py#L421-L443
    # See: https://docs.python.org/3/library/socketserver.html#socketserver.BaseServer.request_queue_size
    # This prevents messages we might see in `dmesg` like:
    #   [Sat Jan 29 00:44:36 2022] TCP: request_sock_TCP: Possible SYN flooding on port 80. Sending cookies.  Check SNMP counters.
    request_queue_size = 128

class Server:

    def __init__(self):
        self.__secure = Config.get('server.use_ssl')

        if not self.__secure:
            self.__server = PifiThreadingHTTPServer(('0.0.0.0', 80), PifiServerRequestHandler)
        else:
            self.__server = PifiThreadingHTTPServer(('0.0.0.0', 443), PifiServerRequestHandler)
            self.__server.socket = ssl.wrap_socket(self.__server.socket,
                                                   keyfile=Config.get_or_throw('server.keyfile'),
                                                   certfile=Config.get_or_throw('server.certfile'),
                                                   server_side=True)

    def serve_forever(self):
        self.__server.serve_forever()
