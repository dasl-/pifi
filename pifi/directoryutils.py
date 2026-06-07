import os

class DirectoryUtils:

    # The directory that you cloned the pifi repo into. E.g. "/home/<USER>/pifi".
    # Always set in __init__; declared here (without a value) so its type is str
    # rather than being inferred as None — that inference made every
    # `root_dir + '/...'` trip pyright's reportOptionalOperand.
    root_dir: str

    def __init__(self):
        self.root_dir = os.path.abspath(os.path.dirname(__file__) + '/..')
