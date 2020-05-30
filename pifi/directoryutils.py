import os

class DirectoryUtils:

    # Will be: "/home/pi/development/pifi" if you install in the default location
    root_dir = None

    def __init__(self):
        self.root_dir = os.path.abspath(os.path.dirname(__file__) + '/..')
