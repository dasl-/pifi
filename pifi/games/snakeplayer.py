import time
import collections
import traceback
import json
import socket
from pifi.logger import Logger
from pifi.games.gamecolorhelper import GameColorHelper
import pifi.games.snake
from pifi.games.unixsockethelper import UnixSocketHelper, SocketClosedException, SocketConnectionHandshakeException

class SnakePlayer:

    UP = 1
    DOWN = 2
    LEFT = 3
    RIGHT = 4

    __SNAKE_STARTING_LENGTH = 4

    __SNAKE_COLOR_CHANGE_FREQ = 0.05

    __MULTIPLAYER_SNAKE_WINNER_COLOR_CHANGE_FREQ = 0.5

    def __init__(self, player_index, server_unix_socket, snake_game):
        self.__logger = Logger().set_namespace(self.__class__.__name__ + '_' + str(player_index))
        self.__snake_game = snake_game

        self.__player_index = player_index
        self.__is_multiplayer_winner = False
        self.__is_eliminated = False

        # If we can't read from the snake's socket, mark it for elimination the next time __maybe_eliminate_snakes is called
        self.__is_marked_for_elimination = False
        self.__num_ticks_since_elimination = 0

        # Doubly linked list, representing all the coordinate pairs in the snake
        self.__snake_linked_list = collections.deque()

        # Set representing all the coordinate pairs in the snake
        self.__snake_set = set()
        self.__unix_socket_helper = UnixSocketHelper().set_server_socket(server_unix_socket)
        self.__direction = None

    def should_show_snake(self):
        if (
            self.__is_eliminated and
            (self.__num_ticks_since_elimination % 2 == 0 or self.__num_ticks_since_elimination >= pifi.games.snake.Snake.ELIMINATED_SNAKE_BLINK_TICK_COUNT)
        ):
            return False
        return True

    def get_score(self):
        score = 0
        if (self.__snake_game.get_settings().num_players == 1):
            score = (len(self.__snake_linked_list) - self.__SNAKE_STARTING_LENGTH) * self.__snake_game.get_settings().difficulty
        else:
            score = (len(self.__snake_linked_list) - self.__SNAKE_STARTING_LENGTH)
        return score

    def get_snake_linked_list(self):
        return self.__snake_linked_list

    def get_snake_set(self):
        return self.__snake_set

    def is_eliminated(self):
        return self.__is_eliminated

    def is_marked_for_elimination(self):
        return self.__is_marked_for_elimination

    def eliminate(self):
        self.__is_eliminated = True

    def unmark_for_elimination(self):
        self.__is_marked_for_elimination = False

    def set_multiplayer_winner(self):
        self.__is_multiplayer_winner = True

    def read_move_and_set_direction(self):
        if self.__is_eliminated:
            return

        move = None
        if self.__unix_socket_helper.is_ready_to_read():
            try:
                move = self.__unix_socket_helper.recv_msg()
            except (SocketClosedException, ConnectionResetError):
                self.__logger.info("socket closed for player")
                self.__is_marked_for_elimination = True
                self.__unix_socket_helper.close()
                return
            move, await_move_from_client_start_time = move.split()
            await_move_from_client_start_time = float(await_move_from_client_start_time)
            elapsed_ms = (time.time() - await_move_from_client_start_time) * 1000
            tick_sleep_amount = self.__snake_game.get_tick_sleep_amount()
            if elapsed_ms > tick_sleep_amount:
                # You can analyze this data for instance via:
                # cat /var/log/pifi/queue.log | grep 'Total elapsed' | awk '{print $(NF-1)}' | datamash max 1 min 1 mean 1 median 1 q1 1 q3 1
                # You should comment out the sleep in Snake.__tick_sleep to get purer data (get timing data without including that sleep)
                self.__logger.info(f"Total elapsed from move start to registering: {elapsed_ms - tick_sleep_amount} ms")
            move = int(move)
            if move not in (self.UP, self.DOWN, self.LEFT, self.RIGHT):
                move = self.UP

        if move is not None:
            new_direction = move
            if (
                (self.__direction == self.UP or self.__direction == self.DOWN) and
                (new_direction == self.UP or new_direction == self.DOWN)
            ):
                pass
            elif (
                (self.__direction == self.LEFT or self.__direction == self.RIGHT) and
                (new_direction == self.LEFT or new_direction == self.RIGHT)
            ):
                pass
            else:
                self.__direction = new_direction

    # returns boolean was_apple_eaten
    def tick(self):
        was_apple_eaten = False
        if self.__is_eliminated:
            return was_apple_eaten

        old_head_y, old_head_x = self.__snake_linked_list[0]

        if self.__direction == self.UP:
            new_head = ((old_head_y - 1) % self.__snake_game.get_settings().display_height, old_head_x)
        elif self.__direction == self.DOWN:
            new_head = ((old_head_y + 1) % self.__snake_game.get_settings().display_height, old_head_x)
        elif self.__direction == self.LEFT:
            new_head = (old_head_y, (old_head_x - 1) % self.__snake_game.get_settings().display_width)
        elif self.__direction == self.RIGHT:
            new_head = (old_head_y, (old_head_x + 1) % self.__snake_game.get_settings().display_width)

        self.__snake_linked_list.insert(0, new_head)

        # Must call this before placing the apple to ensure the apple is not placed on the new head
        self.__snake_set.add(new_head)

        if new_head == self.__snake_game.get_apple():
            was_apple_eaten = True
        else:
            old_tail = self.__snake_linked_list[-1]
            del self.__snake_linked_list[-1]
            if old_tail != new_head:
                # Prevent edge case when the head is "following" the tail.
                # If the old_tail is the same as the new_head, we don't want to remove the old_tail from the set
                # because  the call to `self.__snake_set.add(new_head)` would have been a no-op above.
                self.__snake_set.remove(old_tail)

        return was_apple_eaten

    def increment_tick_counters(self):
        if self.__is_eliminated:
            self.__num_ticks_since_elimination += 1

    def is_coordinate_occupied(self, y, x):
        if self.__is_eliminated:
            return False

        if (y, x) in self.__snake_set:
            return True
        return False

    def get_snake_rgb(self):
        if self.__snake_game.get_settings().num_players <= 1:
            return self.__snake_game.get_game_color_helper().get_rgb(
                self.__snake_game.get_game_color_mode(), self.__SNAKE_COLOR_CHANGE_FREQ, self.__snake_game.get_num_ticks()
            )
        else:
            if self.__is_multiplayer_winner:
                return self.__snake_game.get_game_color_helper().get_rgb(
                    GameColorHelper.GAME_COLOR_MODE_RAINBOW, self.__MULTIPLAYER_SNAKE_WINNER_COLOR_CHANGE_FREQ, self.__snake_game.get_num_ticks()
                )

            if self.__player_index == 0:
                return self.__snake_game.get_game_color_helper().get_rgb(
                    GameColorHelper.GAME_COLOR_MODE_GREEN, self.__SNAKE_COLOR_CHANGE_FREQ, self.__snake_game.get_num_ticks()
                )
            if self.__player_index == 1:
                return self.__snake_game.get_game_color_helper().get_rgb(
                    GameColorHelper.GAME_COLOR_MODE_BLUE, self.__SNAKE_COLOR_CHANGE_FREQ, self.__snake_game.get_num_ticks()
                )
            if self.__player_index == 2:
                return self.__snake_game.get_game_color_helper().get_rgb(
                    GameColorHelper.GAME_COLOR_MODE_RED, self.__SNAKE_COLOR_CHANGE_FREQ, self.__snake_game.get_num_ticks()
                )
            if self.__player_index == 3:
                return self.__snake_game.get_game_color_helper().get_rgb(
                    GameColorHelper.GAME_COLOR_MODE_BW, self.__SNAKE_COLOR_CHANGE_FREQ, self.__snake_game.get_num_ticks()
                )
            return self.__snake_game.get_game_color_helper().get_rgb(
                GameColorHelper.GAME_COLOR_MODE_RAINBOW, self.__SNAKE_COLOR_CHANGE_FREQ, self.__snake_game.get_num_ticks()
            )

    # If one snake, place it's head in the center pixel, with it's body going to the left.
    #
    # If more than one snake, divide the grid into three columns. Alternate placing snake
    # heads on the left and right borders of the middle column. Snakes heads placed on the
    # left border will have their bodies jut to the left. Snake heads placed on the right
    # border will have their bodies jut to the right.
    #
    # When placing N snakes, divide the grid into N + 1 rows. Snakes will placed one per
    # row border.
    def place_snake_at_starting_location(self):
        starting_height = int(
            round(
                (self.__player_index + 1) * (self.__snake_game.get_settings().display_height / (self.__snake_game.get_settings().num_players + 1)),
                1
            )
        )

        if self.__snake_game.get_settings().num_players == 1:
            starting_width = int(round(self.__snake_game.get_settings().display_width / 2, 1))
        else:
            if self.__player_index % 2 == 0:
                starting_width = int(round(self.__snake_game.get_settings().display_width / 3, 1))
            else:
                starting_width = int(round((2 / 3) * self.__snake_game.get_settings().display_width, 1))

        if self.__player_index % 2 == 0:
            self.__direction = self.RIGHT
        else:
            self.__direction = self.LEFT

        for x in range(self.__SNAKE_STARTING_LENGTH):
            if self.__player_index % 2 == 0:
                coordinate = (starting_height, starting_width - x)
            else:
                coordinate = (starting_height, starting_width + x)
            self.__snake_linked_list.append(coordinate)
            self.__snake_set.add(coordinate)

    def end_game(self):
        self.__unix_socket_helper.close()

        # Break circular reference
        # TODO: confirm this works
        # https://rushter.com/blog/python-garbage-collector/
        self.__snake_game = None

    # Returns true on success, false if the socket is closed. If we were unable to send the message,
    # may also throw an exception.
    def send_socket_msg(self, msg):
        if self.__unix_socket_helper.is_connection_socket_open():
            self.__unix_socket_helper.send_msg(msg)
            return True
        return False

    # returns boolean success
    def accept_socket(self, playlist_video_id, accept_loop_start_time, max_accept_sockets_wait_time_s):
        while True:
            if (time.time() - accept_loop_start_time) > max_accept_sockets_wait_time_s:
                # Make sure we don't wait indefinitely for players to join the game
                self.__logger.info('Not all players joined within the time limit for game joining.')
                return False

            try:
                self.__unix_socket_helper.accept()
            except socket.timeout:
                # Keep trying to accept until max_accept_sockets_wait_time_s expires...
                continue
            except SocketConnectionHandshakeException:
                # Error during handshake, there may be other websocket initiated connections in the backlog that want accepting.
                # Try again to avoid a situation where we accidentally had more backlogged requests than we ever call
                # accept on. For example, if people spam the "new game" button, we may have several websockets that called
                # `connect` on the unix socket, but only one instance of the snake process will ever call `accept` (the rest got
                # skipped by the playlist). Thus, if we did not loop through and accept all these queued requests, we would never
                # eliminate this backlog of queued stale requests.
                self.__logger.info('Calling accept again due to handshake error: {}'.format(traceback.format_exc()))
                continue
            except Exception:
                # Error during `accept`, so no indication that there are other connections that want accepting.
                # The backlog is probably empty. Not sure what would trigger this error.
                self.__logger.error('Caught exception during accept: {}'.format(traceback.format_exc()))
                return False

            # Sanity check that the client that ended up connected to our socket is the one that was actually intended.
            # This could be mismatched if two client new game requests happened in quick succession.
            # 1) First "new game" request opens websocket and calls `connect` on the unix socket
            # 2) second "new game" request opens websocket and calls `connect` on unix socket
            # 3) First "new game" queues up in the playlist table
            # 4) Second "new game" queues up in the playlist table, causing the one queued in (3) to be skipped
            # 5) Snake process starts running, corresponding to the playlist item queued up in (4)
            # 6) Snake calls `accept` and is now connected via the unix socket to the websocket from (1)
            # 7) observe that client is from first "new game" request and server is from second "new game" request. Mismatch.
            try:
                client_playlist_video_id = json.loads(self.__unix_socket_helper.recv_msg())['playlist_video_id']
                if client_playlist_video_id != playlist_video_id:
                    self.__logger.warning(f"Server was playing playlist_video_id: {playlist_video_id}, but client was " +
                        f"playing playlist_video_id: {client_playlist_video_id}. Calling accept again due to " +
                        "playlist_video_id mismatch issue.")
            except Exception:
                self.__logger.error(f'Error reading playlist_video_id from client: {traceback.format_exc()}')
                continue

            # send client msg indicating its player index
            if (self.__snake_game.get_settings().num_players > 1):
                player_index_message = json.dumps({
                    'message_type': 'player_index_message',
                    'player_index': self.__player_index
                })
                try:
                    if not self.send_socket_msg(player_index_message):
                        self.__logger.info('Could not send player_index_message, call returned False.')
                        return False
                except Exception:
                    self.__logger.info('Could not send player_index_message: {}'.format(traceback.format_exc()))
                    return False

            return True
