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
from pifi.screensaver.lenia import Lenia
from pifi.screensaver.pixelsort import PixelSort
from pifi.screensaver.fire import Fire
from pifi.screensaver.colorfield import ColorField
from pifi.screensaver.doublependulum import DoublePendulum
from pifi.screensaver.halftone import Halftone
from pifi.screensaver.misprint import Misprint
from pifi.screensaver.opart import OpArt
from pifi.screensaver.noisegradient import NoiseGradient
from pifi.screensaver.domainwarp import DomainWarp
from pifi.screensaver.kaleidoscope import Kaleidoscope
from pifi.screensaver.moire import Moire
from pifi.screensaver.phyllotaxis import Phyllotaxis
from pifi.screensaver.inkinwater import InkInWater
from pifi.screensaver.perlinworms import PerlinWorms
from pifi.screensaver.pendulumwaves import PendulumWaves
from pifi.screensaver.stringart import StringArt
from pifi.screensaver.blueprint import Blueprint
from pifi.screensaver.testprint import TestPrint
from pifi.screensaver.klee import Klee
from pifi.screensaver.unknownpleasures import UnknownPleasures
from pifi.screensaver.dvdbounce import DvdBounce
from pifi.screensaver.hexgrid import HexGrid
from pifi.screensaver.geodesic import Geodesic
from pifi.screensaver.purkinje import Purkinje
from pifi.screensaver.vortices import Vortices
from pifi.screensaver.escher import Escher
from pifi.screensaver.gradienttest import GradientTest
from pifi.screensaver.nycsubway import NycSubway
from pifi.screensaver.wfmu import Wfmu
from pifi.screensaver.sonoskaraoke import SonosKaraoke
from pifi.screensaver.airplaykaraoke import AirPlayKaraoke
from pifi.screensaver.cellularautomata.cyclicautomaton import CyclicAutomaton
from pifi.screensaver.cellularautomata.gameoflife import GameOfLife
from pifi.screensaver.videoscreensaver import VideoScreensaver
from pifi.led.ledframeplayer import LedFramePlayer
from pifi.screensaver.transitionplayer import TransitionPlayer
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
        Lenia,
        DomainWarp,
        Kaleidoscope,
        Moire,
        Phyllotaxis,
        PixelSort,
        Fire,
        ColorField,
        DoublePendulum,
        Halftone,
        Misprint,
        OpArt,
        NoiseGradient,
        InkInWater,
        PerlinWorms,
        PendulumWaves,
        StringArt,
        Blueprint,
        TestPrint,
        Klee,
        UnknownPleasures,
        DvdBounce,
        HexGrid,
        Geodesic,
        Purkinje,
        Vortices,
        Escher,
        GradientTest,
        NycSubway,
        Wfmu,
        SonosKaraoke,
        AirPlayKaraoke,
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

        # Validate all screensavers can be instantiated (fail-fast behavior)
        # We don't cache these instances because screensavers read config in __init__,
        # and we need fresh instances each time to pick up config changes from the UI.
        self.__logger.info("Validating screensaver instantiation...")
        for screensaver_id, cls in self.SCREENSAVER_CLASSES.items():
            try:
                cls(led_frame_player=self.__led_frame_player)
                self.__logger.debug(f"  {screensaver_id}: OK")
            except Exception as e:
                self.__logger.error(f"  {screensaver_id}: FAILED - {e}")
                raise
        self.__logger.info("All screensavers validated successfully")

        self.__transition_player = TransitionPlayer(self.__led_frame_player)

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

    def run(self):
        next_screensaver = None
        while True:
            # Reload config overrides from database before playing
            # This picks up any changes made via the settings UI
            Config.reload_overrides([SettingsDb.SCREENSAVER_SETTINGS])

            enabled = Config.get('screensavers.enabled')

            # Build list of available screensaver IDs
            available_ids = []
            for screensaver_id in enabled:
                if screensaver_id in self.SCREENSAVER_CLASSES:
                    available_ids.append(screensaver_id)

            # Fall back to game of life if nothing enabled
            if not available_ids:
                available_ids.append('game_of_life')

            if next_screensaver is not None:
                # Use the pre-warmed screensaver from last iteration's transition
                screensaver = next_screensaver
                next_screensaver = None
            else:
                # First iteration or transitions disabled — fresh start
                screensaver_id = random.choice(available_ids)
                screensaver_cls = self.SCREENSAVER_CLASSES[screensaver_id]
                screensaver = screensaver_cls(led_frame_player=self.__led_frame_player)

            transitions_enabled = Config.get('screensavers.transitions.enabled', True)
            screensaver.play(auto_teardown=not transitions_enabled)

            if transitions_enabled:
                # Pick next screensaver. Warm-up is handled inside the
                # transition so the from_screensaver keeps animating.
                # Avoid repeating the same screensaver back-to-back.
                current_id = screensaver.get_id()
                candidates = [sid for sid in available_ids if sid != current_id]
                if not candidates:
                    candidates = available_ids
                next_id = random.choice(candidates)
                next_cls = self.SCREENSAVER_CLASSES[next_id]
                next_screensaver = next_cls(led_frame_player=self.__led_frame_player)

                # Live transition: both screensavers animate during the blend.
                # The transition handles _setup() and warm-up of the next
                # screensaver internally, spread across transition steps.
                self.__transition_player.play_transition(
                    from_screensaver=screensaver,
                    to_screensaver=next_screensaver,
                )
                screensaver._teardown()

                # If the next screensaver failed during warm-up (e.g. missing
                # dependency), discard it so we don't immediately exit in play()
                if not next_screensaver._warmed_up:
                    next_screensaver = None
