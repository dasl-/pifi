import json
import math
import numpy as np
from pygame import mixer
import random
import signal
import simpleaudio
import socket
import sys
import time
import traceback

from pifi.config import Config
from pifi.logger import Logger
from pifi.playlist import Playlist
from pifi.led.ledframeplayer import LedFramePlayer
from pifi.games.gamecolorhelper import GameColorHelper
from pifi.games.scoredisplayer import ScoreDisplayer
from pifi.games.scores import Scores
from pifi.games.pongplayer import PongPlayer
from pifi.games.unixsockethelper import UnixSocketHelper
from pifi.directoryutils import DirectoryUtils


class Pong:
    """
    Classic Pong game with multiplayer support.

    Two players control paddles on opposite sides of the screen.
    A ball bounces between them; score by getting the ball past
    the opponent's paddle. First to the target score wins.
    """

    GAME_TITLE = "pong"

    __GAME_OVER_REASON_SCORE = 'game_over_reason_score'
    __GAME_OVER_REASON_DISCONNECT = 'game_over_reason_disconnect'
    __GAME_OVER_REASON_SKIPPED = 'game_over_reason_skipped'

    def __init__(self, server_unix_socket_fd, playlist_video, settings):
        self.__logger = Logger().set_namespace(self.__class__.__name__)
        self.__num_ticks = 0
        self.__playlist_video = playlist_video
        self.__settings = settings

        self.__display_width = Config.get_or_throw('leds.display_width')
        self.__display_height = Config.get_or_throw('leds.display_height')

        # Ball state
        self.__ball_x = self.__display_width / 2
        self.__ball_y = self.__display_height / 2
        self.__ball_vx = 0
        self.__ball_vy = 0

        # Players
        server_unix_socket = socket.socket(fileno=server_unix_socket_fd)
        UnixSocketHelper().set_server_unix_socket_timeout(server_unix_socket)

        self.__players = [
            PongPlayer(0, server_unix_socket, self, settings),
            PongPlayer(1, server_unix_socket, self, settings),
        ]

        # Audio
        mixer.init(frequency=22050, buffer=512)
        self.__bounce_sound = simpleaudio.WaveObject.from_wave_file(
            DirectoryUtils().root_dir + "/assets/snake/sfx_coin_double7_75_pct_vol.wav"
        )
        self.__score_sound = simpleaudio.WaveObject.from_wave_file(
            DirectoryUtils().root_dir + "/assets/snake/sfx_sound_nagger1_50_pct_vol.wav"
        )

        self.__led_frame_player = LedFramePlayer()
        self.__game_color_helper = GameColorHelper()

        self.__register_signal_handlers()

    def play_pong(self):
        self.__reset_ball()
        self.__show_board()

        if not self.__accept_sockets():
            self.__end_game(self.__GAME_OVER_REASON_DISCONNECT)
            return

        # Countdown before starting
        self.__countdown()

        while True:
            self.__tick_sleep()

            # Read player inputs
            for player in self.__players:
                player.read_move()

            # Apply moves
            for player in self.__players:
                player.apply_move()

            # Update ball
            self.__update_ball()

            # Check for scoring
            scorer = self.__check_scoring()
            if scorer is not None:
                self.__handle_score(scorer)

                # Check for game over
                if self.__is_game_over():
                    self.__end_game(self.__GAME_OVER_REASON_SCORE)
                    return

                # Reset ball after score
                self.__reset_ball(serve_to=1 - scorer)
                time.sleep(0.5)

            # Check for disconnection
            if self.__players[0].is_disconnected() or self.__players[1].is_disconnected():
                self.__end_game(self.__GAME_OVER_REASON_DISCONNECT)
                return

            self.__show_board()
            self.__num_ticks += 1

    def __countdown(self):
        """Show a brief countdown before the game starts."""
        for i in range(3, 0, -1):
            self.__show_board()
            time.sleep(0.5)

    def __reset_ball(self, serve_to=None):
        """Reset the ball to the center with a random direction."""
        self.__ball_x = self.__display_width / 2
        self.__ball_y = self.__display_height / 2

        speed = Config.get('pong.ball_speed', 0.5)

        # Random angle, but mostly horizontal
        angle = random.uniform(-0.4, 0.4)  # Radians, roughly +-23 degrees

        # Determine which direction to serve
        if serve_to is None:
            direction = random.choice([-1, 1])
        else:
            direction = 1 if serve_to == 1 else -1

        self.__ball_vx = math.cos(angle) * speed * direction
        self.__ball_vy = math.sin(angle) * speed

    def __update_ball(self):
        """Update ball position and handle collisions."""
        # Move ball
        self.__ball_x += self.__ball_vx
        self.__ball_y += self.__ball_vy

        # Bounce off top/bottom walls
        if self.__ball_y <= 0:
            self.__ball_y = -self.__ball_y
            self.__ball_vy = -self.__ball_vy
            self.__bounce_sound.play()
        elif self.__ball_y >= self.__display_height - 1:
            self.__ball_y = 2 * (self.__display_height - 1) - self.__ball_y
            self.__ball_vy = -self.__ball_vy
            self.__bounce_sound.play()

        # Check paddle collisions
        paddle_width = 1
        ball_ix = int(self.__ball_x)
        ball_iy = int(self.__ball_y)

        # Left paddle (player 0)
        if ball_ix <= paddle_width and self.__ball_vx < 0:
            paddle_y = self.__players[0].get_paddle_y()
            paddle_h = self.__players[0].get_paddle_height()
            if paddle_y <= ball_iy < paddle_y + paddle_h:
                self.__ball_x = paddle_width
                self.__ball_vx = -self.__ball_vx

                # Add spin based on where ball hit paddle
                hit_pos = (ball_iy - paddle_y) / paddle_h - 0.5  # -0.5 to 0.5
                self.__ball_vy += hit_pos * 0.3

                # Speed up slightly
                self.__ball_vx *= 1.05
                self.__bounce_sound.play()

        # Right paddle (player 1)
        if ball_ix >= self.__display_width - 1 - paddle_width and self.__ball_vx > 0:
            paddle_y = self.__players[1].get_paddle_y()
            paddle_h = self.__players[1].get_paddle_height()
            if paddle_y <= ball_iy < paddle_y + paddle_h:
                self.__ball_x = self.__display_width - 1 - paddle_width
                self.__ball_vx = -self.__ball_vx

                # Add spin based on where ball hit paddle
                hit_pos = (ball_iy - paddle_y) / paddle_h - 0.5
                self.__ball_vy += hit_pos * 0.3

                # Speed up slightly
                self.__ball_vx *= 1.05
                self.__bounce_sound.play()

        # Clamp ball velocity
        max_speed = Config.get('pong.max_ball_speed', 1.5)
        speed = math.sqrt(self.__ball_vx ** 2 + self.__ball_vy ** 2)
        if speed > max_speed:
            self.__ball_vx = self.__ball_vx / speed * max_speed
            self.__ball_vy = self.__ball_vy / speed * max_speed

    def __check_scoring(self):
        """Check if the ball has passed a paddle. Returns scorer index or None."""
        if self.__ball_x < 0:
            return 1  # Player 1 (right) scores
        elif self.__ball_x >= self.__display_width:
            return 0  # Player 0 (left) scores
        return None

    def __handle_score(self, scorer):
        """Handle a player scoring."""
        self.__players[scorer].add_score()
        self.__score_sound.play()

        # Send score update to players
        score_msg = json.dumps({
            'message_type': 'score_update',
            'scores': [self.__players[0].get_score(), self.__players[1].get_score()],
        })
        for player in self.__players:
            player.send_socket_msg(score_msg)

        self.__logger.info(f"Player {scorer} scored! Scores: {self.__players[0].get_score()} - {self.__players[1].get_score()}")

    def __is_game_over(self):
        """Check if the game is over."""
        target_score = self.__settings.get('target_score', 5)
        return (
            self.__players[0].get_score() >= target_score or
            self.__players[1].get_score() >= target_score
        )

    def __show_board(self):
        """Render the game state to the LED display."""
        frame = np.zeros([self.__display_height, self.__display_width, 3], np.uint8)

        # Draw paddles
        for player in self.__players:
            paddle_y = player.get_paddle_y()
            paddle_h = player.get_paddle_height()
            color = player.get_paddle_color()

            # Paddle x position
            if player.get_player_index() == 0:
                paddle_x = 0
            else:
                paddle_x = self.__display_width - 1

            for y in range(paddle_y, min(paddle_y + paddle_h, self.__display_height)):
                frame[y, paddle_x] = color

        # Draw ball
        ball_ix = int(self.__ball_x)
        ball_iy = int(self.__ball_y)
        if 0 <= ball_ix < self.__display_width and 0 <= ball_iy < self.__display_height:
            # Ball color cycles for visual interest
            ball_color = self.__game_color_helper.get_rgb(
                GameColorHelper.GAME_COLOR_MODE_RAINBOW, 0.2, self.__num_ticks
            )
            frame[ball_iy, ball_ix] = ball_color

        # Draw center line (dashed)
        center_x = self.__display_width // 2
        for y in range(0, self.__display_height, 2):
            frame[y, center_x] = [50, 50, 50]

        self.__led_frame_player.play_frame(frame)

    def __end_game(self, reason):
        """Handle game over."""
        self.__logger.info(f"Game over. Reason: {reason}")

        if reason == self.__GAME_OVER_REASON_SCORE:
            # Determine winner
            if self.__players[0].get_score() > self.__players[1].get_score():
                winner = 0
            else:
                winner = 1

            winner_msg = json.dumps({
                'message_type': 'game_over',
                'winner': winner,
                'scores': [self.__players[0].get_score(), self.__players[1].get_score()],
            })
            for player in self.__players:
                player.send_socket_msg(winner_msg)

            # Flash winner's paddle
            for _ in range(10):
                self.__show_board()
                time.sleep(0.2)
                self.__num_ticks += 1

        for player in self.__players:
            player.end_game()

        self.__clear_board()
        mixer.quit()
        simpleaudio.stop_all()

    def __clear_board(self):
        """Clear the display."""
        frame = np.zeros([self.__display_height, self.__display_width, 3], np.uint8)
        self.__led_frame_player.play_frame(frame)

    def __tick_sleep(self):
        """Sleep between ticks based on difficulty."""
        base_sleep = 0.05
        difficulty = self.__settings.get('difficulty', 5)
        sleep_time = base_sleep - (difficulty * 0.004)  # Faster at higher difficulty
        time.sleep(max(0.02, sleep_time))

    def __accept_sockets(self):
        """Accept socket connections from both players."""
        max_wait = UnixSocketHelper.MAX_MULTI_PLAYER_JOIN_TIME_S + 1
        start_time = time.time()

        for player in self.__players:
            if not player.accept_socket(
                self.__playlist_video['playlist_video_id'],
                start_time,
                max_wait
            ):
                return False

        return Playlist().set_all_players_ready(self.__playlist_video['playlist_video_id'])

    def __register_signal_handlers(self):
        """Register signal handlers for graceful shutdown."""
        signal.signal(signal.SIGINT, self.__signal_handler)
        signal.signal(signal.SIGHUP, self.__signal_handler)
        signal.signal(signal.SIGQUIT, self.__signal_handler)
        signal.signal(signal.SIGTERM, self.__signal_handler)

    def __signal_handler(self, sig, frame):
        self.__logger.info(f"Caught signal {sig}, exiting gracefully...")
        self.__end_game(self.__GAME_OVER_REASON_SKIPPED)
        sys.exit(sig)

    @staticmethod
    def make_settings_from_playlist_item(playlist_item):
        """Parse settings from a playlist item."""
        difficulty = 5
        target_score = 5

        try:
            settings = json.loads(playlist_item['settings'])
            difficulty = int(settings.get('difficulty', 5))
            target_score = int(settings.get('target_score', 5))
        except Exception:
            Logger().set_namespace("Pong").error(f'Error parsing settings: {traceback.format_exc()}')

        # Validation
        difficulty = max(1, min(10, difficulty))
        target_score = max(1, min(21, target_score))

        return {
            'difficulty': difficulty,
            'target_score': target_score,
            'num_players': 2,  # Pong is always 2 players
        }
