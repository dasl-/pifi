#!/bin/bash
set -x

BASE_DIR="$(dirname "$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )")"

# installing and upgrading npm from scratch required a restart / re-login for the shell to recognize the new version
# when the version changed between `apt-get install npm` and `npm install npm@latest -g`
if ! which npm
then
    is_restart_required=true
fi

sudo apt update
# libsdl2-mixer: needed for pygame
# parallel: needed for update_youtube-dl.sh script
sudo apt -y install git python3-pip ffmpeg sqlite3 mbuffer npm libsdl2-mixer-2.0-0 parallel
sudo apt -y full-upgrade

sudo pip3 install --upgrade youtube_dl yt-dlp numpy HTTPServer apa102-pi pytz websockets simpleaudio pygame

# Just in case the youtube-dl cache got polluted, as it has before...
# https://github.com/ytdl-org/youtube-dl/issues/24780
# shellcheck disable=SC1083
parallel --will-cite --max-procs 0 --halt never sudo -u {1} {2} --rm-cache-dir ::: root pi ::: youtube-dl yt-dlp

# The `apt-get install npm` command installs a very old version of npm. Use npm to upgrade itself to latest.
sudo npm install npm@latest -g

# Install app dependencies
sudo npm install --prefix "$BASE_DIR/app"

if [ "$is_restart_required" = true ] ; then
    echo "Restarting..."
    sudo shutdown -r now
fi
