# VideoRecord stored in the database
class VideoRecord:

    STATUS_QUEUED = 'QUEUED'
    STATUS_LOADING = 'LOADING'
    STATUS_PLAYING = 'PLAYING'
    STATUS_SKIP = 'SKIP'
    STATUS_DONE = 'DONE'

    SIGNAL_KILL = 'KILL'
