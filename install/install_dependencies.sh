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
sudo apt -y install git python3-pip ffmpeg sqlite3 mbuffer npm \
    libsdl2-mixer-2.0-0 # needed for pygame
sudo apt -y full-upgrade

sudo pip3 install --upgrade youtube_dl numpy HTTPServer apa102-pi pytz websockets simpleaudio pygame

# Just in case the youtube-dl cache got polluted, as it has before...
# https://github.com/ytdl-org/youtube-dl/issues/24780
sudo youtube-dl --rm-cache-dir
youtube-dl --rm-cache-dir

# The `apt-get install npm` command installs a very old version of npm. Use npm to upgrade itself to latest.
sudo npm install npm@latest -g

# Install app dependencies
sudo npm install --prefix "$BASE_DIR/app"

if [ "$is_restart_required" = true ] ; then
    echo "Restarting..."
    sudo shutdown -r now
fi
