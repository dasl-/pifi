import random

from pifi.config import Config
from pifi.games.cellularautomata.cyclicautomaton import CyclicAutomaton
from pifi.games.cellularautomata.gameoflife import GameOfLife
from pifi.led.ledframeplayer import LedFramePlayer
from pifi.logger import Logger

class ScreensaverManager:

    def __init__(self):
        self.__logger = Logger().set_namespace(self.__class__.__name__)

        # Ensure only one instance of the LedFramePlayer is used across all screensavers.
        # See: https://github.com/dasl-/pifi/commit/fd48ba5b41bba6c6aa0034d743e40de153482f21
        self.__led_frame_player = LedFramePlayer()

        screensaver_types = Config.get("screensavers.screensavers")
        self.__screensavers = []
        if "game_of_life" in screensaver_types:
            self.__screensavers.append(GameOfLife(led_frame_player = self.__led_frame_player))
        if "cyclic_automaton" in screensaver_types:
            self.__screensavers.append(CyclicAutomaton(led_frame_player = self.__led_frame_player))

    def run(self):
        while True:
            screensaver = random.choice(self.__screensavers)
            screensaver.play()
