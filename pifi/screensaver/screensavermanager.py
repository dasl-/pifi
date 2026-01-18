import json
import random

from pifi.config import Config
from pifi.screensaver.boids import Boids
from pifi.screensaver.cosmicdream import CosmicDream
from pifi.screensaver.mandelbrot import Mandelbrot
from pifi.screensaver.waveinterference import WaveInterference
from pifi.screensaver.spirograph import Spirograph
from pifi.screensaver.lorenz import Lorenz
from pifi.screensaver.metaballs import Metaballs
from pifi.screensaver.starfield import Starfield
from pifi.screensaver.matrixrain import MatrixRain
from pifi.screensaver.meltingclock import MeltingClock
from pifi.screensaver.aurora import Aurora
from pifi.screensaver.shadebobs import Shadebobs
from pifi.screensaver.flowfield import FlowField
from pifi.screensaver.lavalamp import LavaLamp
from pifi.screensaver.reactiondiffusion import ReactionDiffusion
from pifi.screensaver.inkinwater import InkInWater
from pifi.screensaver.perlinworms import PerlinWorms
from pifi.screensaver.pendulumwaves import PendulumWaves
from pifi.screensaver.stringart import StringArt
from pifi.screensaver.unknownpleasures import UnknownPleasures
from pifi.screensaver.cloudscape import Cloudscape
from pifi.screensaver.cellularautomata.cyclicautomaton import CyclicAutomaton
from pifi.screensaver.cellularautomata.gameoflife import GameOfLife
from pifi.screensaver.videoscreensaver import VideoScreensaver
from pifi.led.ledframeplayer import LedFramePlayer
from pifi.settingsdb import SettingsDb
from pifi.logger import Logger

class ScreensaverManager:

    # Map of screensaver ID to class
    SCREENSAVER_CLASSES = {
        'game_of_life': GameOfLife,
        'cyclic_automaton': CyclicAutomaton,
        'boids': Boids,
        'cosmic_dream': CosmicDream,
        'mandelbrot': Mandelbrot,
        'wave_interference': WaveInterference,
        'spirograph': Spirograph,
        'lorenz': Lorenz,
        'metaballs': Metaballs,
        'starfield': Starfield,
        'matrix_rain': MatrixRain,
        'melting_clock': MeltingClock,
        'aurora': Aurora,
        'shadebobs': Shadebobs,
        'flowfield': FlowField,
        'lavalamp': LavaLamp,
        'reactiondiffusion': ReactionDiffusion,
        'inkinwater': InkInWater,
        'perlinworms': PerlinWorms,
        'pendulumwaves': PendulumWaves,
        'stringart': StringArt,
        'unknownpleasures': UnknownPleasures,
        'cloudscape': Cloudscape,
    }

    def __init__(self):
        self.__logger = Logger().set_namespace(self.__class__.__name__)
        self.__settings_db = SettingsDb()

        # Ensure only one instance of the LedFramePlayer is used across all screensavers.
        # See: https://github.com/dasl-/pifi/commit/fd48ba5b41bba6c6aa0034d743e40de153482f21
        self.__led_frame_player = LedFramePlayer()

        # Cache of instantiated screensavers
        self.__screensaver_cache = {}

    @staticmethod
    def get_enabled_screensavers():
        """Get list of enabled screensaver IDs from database."""
        settings_db = SettingsDb()
        enabled_json = settings_db.get(SettingsDb.ENABLED_SCREENSAVERS)
        if enabled_json:
            return json.loads(enabled_json)
        return ['game_of_life', 'cyclic_automaton']

    def __get_enabled_screensavers(self):
        """Get list of enabled screensaver IDs from SettingsDb."""
        return ScreensaverManager.get_enabled_screensavers()

    def __get_screensaver(self, screensaver_id):
        """Get or create a screensaver instance."""
        if screensaver_id not in self.__screensaver_cache:
            if screensaver_id in self.SCREENSAVER_CLASSES:
                cls = self.SCREENSAVER_CLASSES[screensaver_id]
                self.__screensaver_cache[screensaver_id] = cls(led_frame_player=self.__led_frame_player)
        return self.__screensaver_cache.get(screensaver_id)

    def run(self):
        saved_videos = Config.get("screensavers.saved_videos", [])
        video_screensaver = VideoScreensaver(video_list=saved_videos) if saved_videos else None

        while True:
            # Re-read enabled screensavers each iteration so changes take effect
            enabled = self.__get_enabled_screensavers()

            # Build list of available screensavers
            available = []
            for screensaver_id in enabled:
                screensaver = self.__get_screensaver(screensaver_id)
                if screensaver:
                    available.append(screensaver)

            # Add video screensaver if configured
            if video_screensaver:
                available.append(video_screensaver)

            # Fall back to game of life if nothing enabled
            if not available:
                available.append(self.__get_screensaver('game_of_life'))

            screensaver = random.choice(available)
            screensaver.play()
