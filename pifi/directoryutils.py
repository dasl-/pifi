import os

class DirectoryUtils:

    root_dir = None

    def __init__(self):
        self.root_dir = os.path.abspath(os.path.dirname(__file__) + '/..')
