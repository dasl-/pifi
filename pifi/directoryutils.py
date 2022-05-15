import os

class DirectoryUtils:

    # The directory that you cloned the pifi repo into. E.g. "/home/<USER>/pifi".
    root_dir = None

    def __init__(self):
        self.root_dir = os.path.abspath(os.path.dirname(__file__) + '/..')
