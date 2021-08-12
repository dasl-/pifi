#!/bin/bash

# Script that is run via cron to update youtube-dl.
# Youtube releases updates every once in a while that breaks youtube-dl. If we don't constantly update
# to the latest youtube-dl version, the pifi will stop working.

set -x

echo "starting update_youtube-dl at $(date -u)"
sudo pip3 install --upgrade youtube_dl yt-dlp

# Just in case the youtube-dl cache got polluted, as it has before...
# https://github.com/ytdl-org/youtube-dl/issues/24780
#
# Parallel man page:
# If multiple ::: are given, each group will be treated as an input source, and all combinations of
# input sources will be generated. E.g. ::: 1 2 ::: a b c will result in the
# combinations (1,a) (1,b) (1,c) (2,a) (2,b) (2,c). This is useful for replacing nested for-loops.
#
# e.g.: sudo -u root youtube-dl --rm-cache-dir
# shellcheck disable=SC1083
parallel --will-cite --max-procs 0 --halt never sudo -u {1} {2} --rm-cache-dir ::: root pi ::: youtube-dl yt-dlp

# repopulate the cache that we just deleted? /shrug
# e.g.: sudo -u root youtube-dl --output - --restrict-filenames --format 'worst[ext=mp4]/worst' --newline 'https://www.youtube.com/watch?v=IB_2jkwxqh4' > /dev/null
# shellcheck disable=SC1083
parallel --will-cite --max-procs 0 --halt never sudo -u {1} {2} --output - --restrict-filenames --format 'worst[ext=mp4]/worst' --newline 'https://www.youtube.com/watch?v=IB_2jkwxqh4' > /dev/null ::: root pi ::: youtube-dl yt-dlp

echo "finished update_youtube-dl at $(date -u)"
