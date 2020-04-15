#!/bin/bash

# Script that is run via cron to update youtube-dl.
# Youtube releases updates every once in a while that breaks youtube-dl. If we don't constantly update
# to the latest youtube-dl version, the pifi will stop working.

set -x

echo "starting update_youtube-dl at $(date -u)"
sudo pip3 install --upgrade youtube_dl

# Just in case the youtube-dl cache got polluted, as it has before...
# https://github.com/ytdl-org/youtube-dl/issues/24780
sudo -u root youtube-dl --rm-cache-dir
sudo -u pi youtube-dl --rm-cache-dir

# repopulate the cache that we just deleted? /shrug
sudo -u root youtube-dl --output - --restrict-filenames --format 'worst[ext=mp4]/worst' --newline 'https://www.youtube.com/watch?v=IB_2jkwxqh4' > /dev/null
sudo -u pi youtube-dl --output - --restrict-filenames --format 'worst[ext=mp4]/worst' --newline 'https://www.youtube.com/watch?v=IB_2jkwxqh4' > /dev/null

echo "finished update_youtube-dl at $(date -u)"
