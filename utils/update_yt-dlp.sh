#!/usr/bin/env bash

# Script that is run via cron to update yt-dlp.
# Youtube releases updates every once in a while that breaks yt-dlp. If we don't constantly update
# to the latest yt-dlp version, the pifi will stop working.
#
# By using uv to install yt-dlp, we can install yt-dlp even when the OS's python version
# is too old to be supported by yt-dlp. See: https://github.com/dasl-/piwall2/issues/31

echo "starting update_yt-dlp at $(date -u)"
/usr/local/bin/uv tool install 'yt-dlp[default]@latest'

# symlink yt-dlp to a place that's on our path by default
sudo ln -sf /home/pi/.local/bin/yt-dlp /usr/bin/yt-dlp

# Just in case the yt-dlp cache got polluted, as it has before...
# https://github.com/ytdl-org/youtube-dl/issues/24780
#
# Parallel man page:
# If multiple ::: are given, each group will be treated as an input source, and all combinations of
# input sources will be generated. E.g. ::: 1 2 ::: a b c will result in the
# combinations (1,a) (1,b) (1,c) (2,a) (2,b) (2,c). This is useful for replacing nested for-loops.
#
# e.g.: sudo -u root yt-dlp --rm-cache-dir
# shellcheck disable=SC1083
parallel --will-cite --max-procs 0 --halt never sudo -u {1} yt-dlp --rm-cache-dir ::: root pi

# repopulate the cache that we just deleted? /shrug
# e.g.: sudo -u root yt-dlp --output - --restrict-filenames --format 'worst[ext=mp4]/worst' --newline 'https://www.youtube.com/watch?v=IB_2jkwxqh4' > /dev/null
# shellcheck disable=SC1083
parallel --will-cite --max-procs 0 --halt never sudo -u {1} yt-dlp --output - --restrict-filenames --format 'worst[ext=mp4]/worst' --newline 'https://www.youtube.com/watch?v=IB_2jkwxqh4' > /dev/null ::: root pi

echo "finished update_yt-dlp at $(date -u)"
