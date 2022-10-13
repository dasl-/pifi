import numpy as np
import random
import os
import sys
import time
import subprocess

# This is necessary for the imports below to work
root_dir = os.path.abspath(os.path.dirname(__file__) + '/../..')
sys.path.append(root_dir)

from pifi.config import Config
from pifi.led.ledframeplayer import LedFramePlayer
from pifi.logger import Logger

from PIL import Image
from PIL import GifImagePlugin
GifImagePlugin.LOADING_STRATEGY = GifImagePlugin.LoadingStrategy.RGB_ALWAYS
import random

class Pibyt(object):
    def __init__(self, app_path, led_frame_player = None):
        self._logger = Logger().set_namespace(self.__class__.__name__)
        self._board = None
        if led_frame_player is None:
            self.__led_frame_player = LedFramePlayer()
        else:
            self.__led_frame_player = led_frame_player

        apps = Config.get("pibyt.apps", {"nyancat": {}})
        self.__dur = Config.get("pibyt.duration", 15)
        self.__apps = []
        for app in apps:
            d = os.path.join(app_path, app)
            for f in os.listdir(d):
                f = os.path.join(d,f)
                if os.path.isfile(f):
                    ext = os.path.splitext(f)[-1].lower()
                    if ext == ".star":
                        self.__apps.append({"path": f, "config": apps[app]})
                        break

    def play(self):
        app = random.choice(self.__apps)
        args = ["/home/pi/pixlet/pixlet", "render", "--gif", "-o", "foo.gif", app["path"]]
        for key, value in app["config"].items():
            args.append(f"{key}={value}")
        print(args)
        out = subprocess.run(args, capture_output=True)
        print(out)

        img = Image.open("foo.gif")
        #print("yay", img.n_frames)

        start = time.time()
        # Display individual frames from the loaded animated GIF file
        while time.time() - start < self.__dur:
            for frame in range(0,img.n_frames):
                img.seek(frame)
                if time.time() - start >= 15:
                    break
                if img.mode == 'P':
                    continue
                dur = img.info.get('duration', 15)
                arr = np.array(img)
                self.__led_frame_player.play_frame(arr)
                time.sleep(dur / 1000.)

if __name__ == '__main__':
    Pibyt("/home/pi/community/apps").play()
