import numpy as np
import random
import time
import simpleaudio
import traceback
import json
import secrets
from pygame import mixer
from pifi.logger import Logger
from pifi.playlist import Playlist
from pifi.videoplayer import VideoPlayer
from pifi.games.gamecolorhelper import GameColorHelper
from pifi.games.scoredisplayer import ScoreDisplayer
from pifi.games.scores import Scores
from pifi.games.snakeplayer import SnakePlayer
from pifi.games.unixsockethelper import UnixSocketHelper
from pifi.directoryutils import DirectoryUtils

class Snake:

    GAME_TITLE = "snake"

    __GAME_OVER_REASON_SNAKE_STATE = 'game_over_reason_snake_state'
    __GAME_OVER_REASON_SKIP_REQUESTED = 'game_over_reason_skip_requested'
    __GAME_OVER_REASON_CLIENT_SOCKET_SIGNAL = 'game_over_reason_client_socket_signal'

    ELIMINATED_SNAKE_BLINK_TICK_COUNT = 8

    __APPLE_COLOR_CHANGE_FREQ = 0.2

    __logger = None

    # SnakeSettings
    __settings = None

    __game_color_helper = None

    __num_ticks = 0

    __game_color_mode = None

    __players = None

    __eliminated_snake_count = 0

    __last_eliminated_snake_sound = None

    __apple = None
    __apples_eaten_count = 0

    __apple_sound = simpleaudio.WaveObject.from_wave_file(DirectoryUtils().root_dir +
        "/assets/snake/sfx_coin_double7_75_pct_vol.wav")
    __background_music = None
    __victory_sound_file = DirectoryUtils().root_dir + "/assets/snake/SFX_LEVEL_UP_40_pct_vol.wav"

    __playlist = None

    __playlist_video = None

    def __init__(self, settings, unix_socket, playlist_video):
        self.__logger = Logger().set_namespace(self.__class__.__name__)
        self.__logger.info("Doing init with SnakeSettings: {}".format(vars(settings)))

        self.__settings = settings
        self.__game_color_helper = GameColorHelper()
        self.__video_player = VideoPlayer(self.__settings)
        self.__playlist = Playlist()
        self.__playlist_video = playlist_video
        self.__players = []
        for i in range(self.__settings.num_players):
            self.__players.append(SnakePlayer(i, unix_socket, self))

        # why do we use both simpleaudio and pygame mixer? see: https://github.com/dasl-/pifi/blob/master/utils/sound_test.py
        mixer.init(frequency = 22050, buffer = 512)
        background_music_file = secrets.choice([
            'dragon_quest4_05_town.wav',
            'dragon_quest4_04_solitary_warrior.wav',
            'dragon_quest4_19_a_pleasant_casino.wav',
            'radia_senki_reimei_hen_06_unknown_village_elfas.wav', #todo: has a blip in the loop
            'the_legend_of_zelda_links_awakening_04_mabe_village_loop.wav',
        ])
        self.__background_music = mixer.Sound(DirectoryUtils().root_dir + "/assets/snake/{}".format(background_music_file))
        self.__game_color_mode = self.__game_color_helper.determine_game_color_mode(self.__settings)

    def play_snake(self):
        for i in range(self.__settings.num_players):
            self.__players[i].place_snake_at_starting_location()
        self.__place_apple()
        self.__show_board()

        if not self.__accept_sockets():
            self.__end_game(self.__GAME_OVER_REASON_CLIENT_SOCKET_SIGNAL)
            return

        self.__background_music.play(loops = -1)

        while True:
            # TODO : sleep for a variable amount depending on how long each loop iteration took. Should
            # lead to more consistent tick durations?
            self.__tick_sleep()

            for i in range(self.__settings.num_players):
                self.__players[i].read_move_and_set_direction()

            self.__tick()
            self.__maybe_eliminate_snakes()
            if self.__is_game_over():
                self.__end_game(self.__GAME_OVER_REASON_SNAKE_STATE)
                break
            if self.__should_skip_game():
                self.__end_game(self.__GAME_OVER_REASON_SKIP_REQUESTED)
                break

    def get_num_ticks(self):
        return self.__num_ticks

    def get_apple(self):
        return self.__apple

    def get_game_color_helper(self):
        return self.__game_color_helper

    def get_game_color_mode(self):
        return self.__game_color_mode

    def get_settings(self):
        return self.__settings

    def __tick(self):
        self.__increment_tick_counters()
        was_apple_eaten = False
        for i in range(self.__settings.num_players):
            if(self.__players[i].tick()):
                was_apple_eaten = True
        if was_apple_eaten:
            self.__eat_apple()

        self.__show_board()

    def __eat_apple(self):
        self.__apples_eaten_count += 1
        self.__apple_sound.play()
        self.__place_apple()
        player_scores = []
        for i in range(self.__settings.num_players):
            player_scores.append(self.__players[i].get_score())

        score_message = None
        if self.__settings.num_players <= 1:
            score_message = json.dumps({
                'message_type': 'single_player_score',
                'player_scores': player_scores,
            })
        else:
            apples_left = self.__settings.apple_count - self.__apples_eaten_count
            score_message = json.dumps({
                'message_type': 'multi_player_score',
                'player_scores': player_scores,
                'apples_left': apples_left,
            })

        for i in range(self.__settings.num_players):
            try:
                self.__players[i].send_socket_msg(score_message)
            except Exception:
                self.__logger.info('Unable to send score message to player {}'.format(i))

    def __place_apple(self):
        # TODO: make better?
        while True:
            x = random.randint(0, self.__settings.display_width - 1)
            y = random.randint(0, self.__settings.display_height - 1)
            is_coordinate_occupied_by_a_snake = False
            for i in range(self.__settings.num_players):
                is_coordinate_occupied_by_a_snake = self.__players[i].is_coordinate_occupied(y, x)
                if is_coordinate_occupied_by_a_snake:
                    break
            if not is_coordinate_occupied_by_a_snake:
                break
        self.__apple = (y, x)

    def __maybe_eliminate_snakes(self):
        eliminated_snakes = set()

        # Eliminate snakes that:
        # 1) overlapped themselves
        # 2) overlapped other snakes
        # 3) were previously marked for elimination
        for i in range(self.__settings.num_players):
            if self.__players[i].is_eliminated():
                continue

            this_snake_head = self.__players[i].get_snake_linked_list()[0]
            for j in range(self.__settings.num_players):
                if self.__players[j].is_eliminated():
                    continue

                if i == j:
                    # Check if this snake overlapped itself
                    if len(self.__players[i].get_snake_set()) < len(self.__players[i].get_snake_linked_list()):
                        eliminated_snakes.add(i)
                else:
                    # Check if this snake's head overlapped that snake (any other snake)
                    that_snake_set = self.__players[j].get_snake_set()
                    if this_snake_head in that_snake_set:
                        eliminated_snakes.add(i)

            # Eliminate snakes that were previously marked for elimination
            if self.__players[i].is_marked_for_elimination():
                if i not in eliminated_snakes:
                    eliminated_snakes.add(i)
                self.__players[i].unmark_for_elimination()

        for i in eliminated_snakes:
            self.__players[i].eliminate()

        self.__eliminated_snake_count += len(eliminated_snakes)

        # Play snake death sound in multiplayer if any snakes were eliminated
        if len(eliminated_snakes) > 0 and self.__settings.num_players > 1:
            self.__last_eliminated_snake_sound = simpleaudio.WaveObject.from_wave_file(
                DirectoryUtils().root_dir + "/assets/snake/sfx_sound_nagger1_50_pct_vol.wav").play()

    def __is_game_over(self):
        if self.__settings.num_players > 1:
            if self.__eliminated_snake_count >= (self.__settings.num_players - 1):
                return True
            if self.__apples_eaten_count >= self.__settings.apple_count:
                return True
        elif self.__settings.num_players == 1:
            if self.__eliminated_snake_count > 0:
                return True

        return False

    def __show_board(self):
        frame = np.zeros([self.__settings.display_height, self.__settings.display_width, 3], np.uint8)

        for i in range(self.__settings.num_players):
            if (not self.__players[i].should_show_snake()):
                # Blink snakes for the first few ticks after they are eliminated.
                # TODO: move this into new Player class (Player::should_display or something)
                continue

            for (y, x) in self.__players[i].get_snake_linked_list():
                frame[y, x] = self.__players[i].get_snake_rgb()

        if self.__apple is not None:
            apple_rgb = self.__game_color_helper.get_rgb(
                GameColorHelper.GAME_COLOR_MODE_RAINBOW, self.__APPLE_COLOR_CHANGE_FREQ, self.__num_ticks
            )
            frame[self.__apple[0], self.__apple[1]] = apple_rgb

        self.__video_player.play_frame(frame)

    def __end_game(self, reason):
        if self.__background_music:
            self.__background_music.fadeout(500)

        score = None
        if self.__settings.num_players == 1: # only do scoring in single player
            score = self.__players[0].get_score()
            if reason == self.__GAME_OVER_REASON_SNAKE_STATE:
                self.__do_scoring(score)
        elif self.__settings.num_players > 1 and reason == self.__GAME_OVER_REASON_SNAKE_STATE:
            if self.__eliminated_snake_count == self.__settings.num_players:
                # The last N players died at the same time in a head to head collision. There was no winner.
                for i in range(self.ELIMINATED_SNAKE_BLINK_TICK_COUNT + 1):
                    self.__tick_sleep()
                    self.__show_board()
                    self.__increment_tick_counters()
                self.__tick_sleep()
            else:
                # We have a winner / winners
                winners = self.__determine_multiplayer_winners()
                winner_message = json.dumps({
                    'message_type': 'multi_player_winners',
                    'winners': winners,
                })
                for i in range(self.__settings.num_players):
                    try:
                        self.__players[i].send_socket_msg(winner_message)
                    except Exception:
                        self.__logger.info('Unable to send winner message to player {}'.format(i))

                did_play_victory_sound = False
                victory_sound = None
                while_counter = 0
                max_loops = 100
                while True:
                    self.__tick_sleep()
                    self.__show_board()
                    self.__increment_tick_counters()
                    if (
                        not did_play_victory_sound and
                        (self.__last_eliminated_snake_sound is None or not self.__last_eliminated_snake_sound.is_playing())
                    ):
                        # Wait for eliminated snake sound to finish before playing victory sound
                        victory_sound = (simpleaudio.WaveObject
                            .from_wave_file(self.__victory_sound_file)
                            .play())
                        did_play_victory_sound = True

                    # Exit after playing the victory sound and waiting for the snakes to blink enough times, whichever
                    # takes longer.
                    if (
                        (
                            did_play_victory_sound and
                            not victory_sound.is_playing() and
                            while_counter > (2 * self.ELIMINATED_SNAKE_BLINK_TICK_COUNT)
                        ) or
                        (while_counter > max_loops)
                    ):
                        break
                    while_counter += 1

        for i in range(self.__settings.num_players):
            self.__players[i].end_game()

        self.__clear_board()
        mixer.quit()
        simpleaudio.stop_all()

        self.__logger.info("game over. score: {}. Reason: {}".format(score, reason))

    def __do_scoring(self, score):
        simpleaudio.WaveObject.from_wave_file(DirectoryUtils().root_dir + "/assets/snake/LOZ_Link_Die.wav").play()
        scores = Scores()
        is_high_score = scores.is_high_score(score, self.GAME_TITLE)
        score_id = scores.insert_score(score, self.GAME_TITLE)
        if is_high_score:
            highscore_message = json.dumps({
                'message_type': 'high_score',
                'score_id': score_id
            })
            try:
                self.__players[0].send_socket_msg(highscore_message)
            except Exception:
                # If game ended due to the player closing the tab, we will be unable to send the message to their websocket.
                # We will still insert their high score into the DB, and their initials will be "AAA".
                self.__logger.error('Unable to send high score message: {}'.format(traceback.format_exc()))

        time.sleep(0.3)
        for x in range(self.ELIMINATED_SNAKE_BLINK_TICK_COUNT + 1): # blink board
            time.sleep(0.1)
            self.__show_board()
            self.__increment_tick_counters()
            time.sleep(0.1)

        score_color = [255, 0, 0] # red
        score_tick = 0
        if is_high_score:
            score_color = self.__game_color_helper.get_rgb(
                game_color_mode = GameColorHelper.GAME_COLOR_MODE_RAINBOW,
                color_change_freq = 0.2,
                num_ticks = score_tick
            )
            (simpleaudio.WaveObject
                .from_wave_file(self.__victory_sound_file)
                .play())
        score_displayer = ScoreDisplayer(self.__settings, self.__video_player, score)
        score_displayer.display_score(score_color)

        for i in range(1, 100):
            # if someone clicks "New Game" while the score is being displayed, immediately start a new game
            # instead of waiting for the score to stop being displayed
            #
            # also make the score display in rainbow if it was a high score.
            time.sleep(0.05)

            if is_high_score:
                score_tick += 1
                score_color = self.__game_color_helper.get_rgb(
                    game_color_mode = GameColorHelper.GAME_COLOR_MODE_RAINBOW,
                    color_change_freq = 0.2,
                    num_ticks = score_tick
                )
                score_displayer.display_score(score_color)

            if i % 5 == 0 and self.__should_skip_game():
                break

    # Win a multiplayer game by either:
    # 1) Being the last player remaining or
    # 2) Eating the most apples out of the non-eliminated snakes. In this case, there may be more than one winner.
    def __determine_multiplayer_winners(self):
        winners = []
        if self.__settings.num_players == self.__eliminated_snake_count + 1:
            # Case 1
            for i in range(self.__settings.num_players):
                if not self.__players[i].is_eliminated():
                    self.__players[i].set_multiplayer_winner()
                    winners.append(i)
                    break
        elif self.__apples_eaten_count >= self.__settings.apple_count:
            # Case 2
            longest_snake_length = None
            longest_snake_indexes = []
            for i in range(self.__settings.num_players):
                if self.__players[i].is_eliminated():
                    continue
                snake_length = len(self.__players[i].get_snake_linked_list())
                if longest_snake_length is None or snake_length > longest_snake_length:
                    longest_snake_length = snake_length
                    longest_snake_indexes = [i]
                elif snake_length == longest_snake_length:
                    longest_snake_indexes.append(i)
            for i in longest_snake_indexes:
                self.__players[i].set_multiplayer_winner()
                winners.append(i)
        return winners

    def __clear_board(self):
        frame = np.zeros([self.__settings.display_height, self.__settings.display_width, 3], np.uint8)
        self.__video_player.play_frame(frame)

    def __tick_sleep(self):
        time.sleep(-0.02 * self.__settings.difficulty + 0.21)

    def __increment_tick_counters(self):
        self.__num_ticks += 1
        for i in range(self.__settings.num_players):
            self.__players[i].increment_tick_counters()

    def __should_skip_game(self):
        if self.__playlist.should_skip_video_id(self.__playlist_video['playlist_video_id']):
            return True
        return False

    # returns boolean success
    def __accept_sockets(self):
        # todo: database util method to share logic for date conversion
        playlist_video_create_date_epoch = time.mktime(time.strptime(self.__playlist_video['create_date'], '%Y-%m-%d  %H:%M:%S'))
        max_accept_sockets_wait_time_s = UnixSocketHelper.MAX_SINGLE_PLAYER_JOIN_TIME_S
        if self.__settings.num_players > 1:
            max_accept_sockets_wait_time_s = UnixSocketHelper.MAX_MULTI_PLAYER_JOIN_TIME_S + 1 # give a 1s extra buffer
        for i in range(self.__settings.num_players):
            if not (
                self.__players[i].accept_socket(
                    self.__playlist_video['playlist_video_id'], playlist_video_create_date_epoch, max_accept_sockets_wait_time_s
                )
            ):
                return False

        if self.__settings.num_players > 1:
            return self.__playlist.set_all_players_ready(self.__playlist_video['playlist_video_id'])
        return True
