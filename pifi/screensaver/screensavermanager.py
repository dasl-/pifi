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

    # List of all available screensaver classes
    # To add a new screensaver: import it above and add the class to this list
    _SCREENSAVER_CLASSES = [
        GameOfLife,
        CyclicAutomaton,
        Boids,
        CosmicDream,
        Mandelbrot,
        WaveInterference,
        Spirograph,
        Lorenz,
        Metaballs,
        Starfield,
        MatrixRain,
        MeltingClock,
        Aurora,
        Shadebobs,
        FlowField,
        LavaLamp,
        ReactionDiffusion,
        InkInWater,
        PerlinWorms,
        PendulumWaves,
        StringArt,
        UnknownPleasures,
        Cloudscape,
        VideoScreensaver,
    ]

    # Build map of screensaver ID to class using get_id() from each class
    # This eliminates duplication - the ID comes from the class itself
    SCREENSAVER_CLASSES = {cls.get_id(): cls for cls in _SCREENSAVER_CLASSES}

    # Cache for get_all_screensavers() result
    _all_screensavers_cache = None

    def __init__(self):
        self.__logger = Logger().set_namespace(self.__class__.__name__)
        self.__settings_db = SettingsDb()

        # Ensure only one instance of the LedFramePlayer is used across all screensavers.
        # See: https://github.com/dasl-/pifi/commit/fd48ba5b41bba6c6aa0034d743e40de153482f21
        self.__led_frame_player = LedFramePlayer()

        # Pre-instantiate all screensavers upfront
        # This provides fail-fast behavior if there are instantiation issues
        self.__screensaver_cache = {
            screensaver_id: cls(led_frame_player=self.__led_frame_player)
            for screensaver_id, cls in self.SCREENSAVER_CLASSES.items()
        }

    @staticmethod
    def get_all_screensavers():
        """Get metadata for all available screensavers."""
        # Lazy initialization of cache - build once, return many times
        if ScreensaverManager._all_screensavers_cache is None:
            screensavers = []
            for cls in ScreensaverManager._SCREENSAVER_CLASSES:
                screensavers.append({
                    'id': cls.get_id(),
                    'name': cls.get_name(),
                    'description': cls.get_description(),
                })
            ScreensaverManager._all_screensavers_cache = sorted(screensavers, key=lambda x: x['id'])

        return ScreensaverManager._all_screensavers_cache

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
        """Get a screensaver instance from the pre-instantiated cache."""
        return self.__screensaver_cache.get(screensaver_id)

    def run(self):
        saved_videos = Config.get("screensavers.saved_videos", [])
        video_screensaver = VideoScreensaver(led_frame_player=self.__led_frame_player) if saved_videos else None

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
