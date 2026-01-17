import random

from pifi.config import Config
from pifi.games.boids import Boids
from pifi.games.cosmicdream import CosmicDream
from pifi.games.mandelbrot import Mandelbrot
from pifi.games.waveinterference import WaveInterference
from pifi.games.spirograph import Spirograph
from pifi.games.lorenz import Lorenz
from pifi.games.metaballs import Metaballs
from pifi.games.starfield import Starfield
from pifi.games.matrixrain import MatrixRain
from pifi.games.meltingclock import MeltingClock
from pifi.games.aurora import Aurora
from pifi.games.shadebobs import Shadebobs
from pifi.games.cellularautomata.cyclicautomaton import CyclicAutomaton
from pifi.games.cellularautomata.gameoflife import GameOfLife
from pifi.video.videoscreensaver import VideoScreensaver
from pifi.led.ledframeplayer import LedFramePlayer
from pifi.logger import Logger

class ScreensaverManager:

    def __init__(self):
        self.__logger = Logger().set_namespace(self.__class__.__name__)

        # Ensure only one instance of the LedFramePlayer is used across all screensavers.
        # See: https://github.com/dasl-/pifi/commit/fd48ba5b41bba6c6aa0034d743e40de153482f21
        self.__led_frame_player = LedFramePlayer()

        screensaver_types = Config.get("screensavers.screensavers")
        saved_videos = Config.get("screensavers.saved_videos", [])
        self.__screensavers = []
        if "game_of_life" in screensaver_types:
            self.__screensavers.append(GameOfLife(led_frame_player = self.__led_frame_player))
        if "cyclic_automaton" in screensaver_types:
            self.__screensavers.append(CyclicAutomaton(led_frame_player = self.__led_frame_player))
        if "boids" in screensaver_types:
            self.__screensavers.append(Boids(led_frame_player = self.__led_frame_player))
        if "cosmic_dream" in screensaver_types:
            self.__screensavers.append(CosmicDream(led_frame_player = self.__led_frame_player))
        if "mandelbrot" in screensaver_types:
            self.__screensavers.append(Mandelbrot(led_frame_player = self.__led_frame_player))
        if "wave_interference" in screensaver_types:
            self.__screensavers.append(WaveInterference(led_frame_player = self.__led_frame_player))
        if "spirograph" in screensaver_types:
            self.__screensavers.append(Spirograph(led_frame_player = self.__led_frame_player))
        if "lorenz" in screensaver_types:
            self.__screensavers.append(Lorenz(led_frame_player = self.__led_frame_player))
        if "metaballs" in screensaver_types:
            self.__screensavers.append(Metaballs(led_frame_player = self.__led_frame_player))
        if "starfield" in screensaver_types:
            self.__screensavers.append(Starfield(led_frame_player = self.__led_frame_player))
        if "matrix_rain" in screensaver_types:
            self.__screensavers.append(MatrixRain(led_frame_player = self.__led_frame_player))
        if "melting_clock" in screensaver_types:
            self.__screensavers.append(MeltingClock(led_frame_player = self.__led_frame_player))
        if "aurora" in screensaver_types:
            self.__screensavers.append(Aurora(led_frame_player = self.__led_frame_player))
        if "shadebobs" in screensaver_types:
            self.__screensavers.append(Shadebobs(led_frame_player = self.__led_frame_player))
        if saved_videos != []:
            self.__screensavers.append(VideoScreensaver(video_list = saved_videos))

    def run(self):
        while True:
            screensaver = random.choice(self.__screensavers)
            screensaver.play()
