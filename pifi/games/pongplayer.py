import json
import socket
import time
import traceback

from pifi.config import Config
from pifi.logger import Logger
from pifi.games.unixsockethelper import UnixSocketHelper, SocketClosedException, SocketConnectionHandshakeException


class PongPlayer:
    """
    Represents a player in the Pong game.
    Manages paddle position and socket communication.
    """

    UP = 1
    DOWN = 2

    def __init__(self, player_index, server_unix_socket, pong_game, settings):
        self.__logger = Logger().set_namespace(self.__class__.__name__ + '_' + str(player_index))
        self.__pong_game = pong_game
        self.__player_index = player_index
        self.__settings = settings

        self.__display_height = Config.get_or_throw('leds.display_height')
        self.__paddle_height = Config.get('pong.paddle_height', 3)

        # Paddle position (y coordinate of top of paddle)
        self.__paddle_y = (self.__display_height - self.__paddle_height) // 2

        self.__score = 0
        self.__is_disconnected = False

        self.__unix_socket_helper = UnixSocketHelper().set_server_socket(server_unix_socket)
        self.__pending_move = None

    def get_paddle_y(self):
        return self.__paddle_y

    def get_paddle_height(self):
        return self.__paddle_height

    def get_score(self):
        return self.__score

    def add_score(self):
        self.__score += 1

    def is_disconnected(self):
        return self.__is_disconnected

    def get_player_index(self):
        return self.__player_index

    def accept_socket(self, playlist_video_id, accept_loop_start_time, max_wait_time):
        """Accept a socket connection from a player."""
        while True:
            if (time.time() - accept_loop_start_time) > max_wait_time:
                self.__logger.info('Player did not join within the time limit.')
                return False

            try:
                self.__unix_socket_helper.accept()
            except socket.timeout:
                # Keep trying to accept until max_wait_time expires
                continue
            except SocketConnectionHandshakeException:
                # Error during handshake, try again to clear stale connections
                self.__logger.info(f'Calling accept again due to handshake error: {traceback.format_exc()}')
                continue
            except Exception:
                self.__logger.error(f'Error accepting socket: {traceback.format_exc()}')
                return False

            # Verify this is the right client by checking playlist_video_id
            try:
                client_playlist_video_id = json.loads(self.__unix_socket_helper.recv_msg())['playlist_video_id']
                if client_playlist_video_id != playlist_video_id:
                    self.__logger.warning(f'Server was playing playlist_video_id: {playlist_video_id}, but client was ' +
                        f'playing playlist_video_id: {client_playlist_video_id}. Calling accept again.')
                    self.__unix_socket_helper.close()
                    continue
            except Exception:
                self.__logger.error(f'Error reading playlist_video_id from client: {traceback.format_exc()}')
                continue

            # Send player index message to client
            player_index_message = json.dumps({
                'message_type': 'player_index_message',
                'player_index': self.__player_index
            })
            try:
                self.__unix_socket_helper.send_msg(player_index_message)
            except Exception:
                self.__logger.error(f'Error sending player_index_message: {traceback.format_exc()}')
                return False

            return True

    def read_move(self):
        """Read move from socket and store it."""
        if self.__is_disconnected:
            return

        if self.__unix_socket_helper.is_ready_to_read():
            try:
                msg = self.__unix_socket_helper.recv_msg()
                move, client_send_time = msg.split()
                self.__pending_move = move
            except (SocketClosedException, ConnectionResetError):
                self.__logger.info("Socket closed for player")
                self.__is_disconnected = True
                self.__unix_socket_helper.close()
            except Exception:
                self.__logger.error(f'Error reading move: {traceback.format_exc()}')

    def apply_move(self):
        """Apply any pending move to the paddle."""
        if self.__pending_move is None:
            return

        move = self.__pending_move
        self.__pending_move = None

        if move == 'up':
            self.__paddle_y = max(0, self.__paddle_y - 1)
        elif move == 'down':
            self.__paddle_y = min(self.__display_height - self.__paddle_height, self.__paddle_y + 1)

    def send_socket_msg(self, msg):
        """Send a message to the player's socket."""
        if self.__is_disconnected:
            return
        try:
            self.__unix_socket_helper.send_msg(msg)
        except Exception:
            self.__logger.error(f'Error sending message: {traceback.format_exc()}')

    def end_game(self):
        """Clean up when game ends."""
        self.__unix_socket_helper.close()

    def get_paddle_color(self):
        """Get the color for this player's paddle."""
        if self.__player_index == 0:
            return [255, 100, 100]  # Red-ish for left player
        else:
            return [100, 100, 255]  # Blue-ish for right player
