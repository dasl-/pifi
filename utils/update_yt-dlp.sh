#!/usr/bin/env bash

# Script that is run via cron to update yt-dlp.
# Youtube releases updates every once in a while that breaks yt-dlp. If we don't constantly update
# to the latest yt-dlp version, the pifi will stop working.

echo "starting update_yt-dlp at $(date -u)"
sudo python3 -m pip install --upgrade yt-dlp

# https://askubuntu.com/a/329689
users=$(awk -F: '$3 >= 1000 && $1 != "nobody" {print $1}' /etc/passwd)

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
parallel --will-cite --max-procs 0 --halt never sudo -u {1} yt-dlp --rm-cache-dir ::: root "$users"

# repopulate the cache that we just deleted? /shrug
# e.g.: sudo -u root yt-dlp --output - --restrict-filenames --format 'worst[ext=mp4]/worst' --newline 'https://www.youtube.com/watch?v=IB_2jkwxqh4' > /dev/null
# shellcheck disable=SC1083
parallel --will-cite --max-procs 0 --halt never sudo -u {1} yt-dlp --output - --restrict-filenames --format 'worst[ext=mp4]/worst' --newline 'https://www.youtube.com/watch?v=IB_2jkwxqh4' > /dev/null ::: root "$users"

echo "finished update_yt-dlp at $(date -u)"
