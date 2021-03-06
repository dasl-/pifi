#!/bin/bash
set -x

BASE_DIR="$(dirname "$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )")"

# installing and upgrading npm from scratch required a restart / re-login for the shell to recognize the new version
# when the version changed between `apt-get install npm` and `npm install npm@latest -g`
if ! which npm
then
    is_restart_required=true
fi

sudo apt-get update
# TODO: many of these deps are probably no longer necessary - leftover from when we used opencv
sudo apt-get -y install git vim python3-pip libilmbase-dev libopenexr-dev libgstreamer1.0-dev libtiff5-dev libjasper-dev libpng-dev libjpeg-dev libavcodec-dev libavformat-dev libswscale-dev libv4l-dev libgtk2.0-dev libatlas-base-dev gfortran libgdk-pixbuf2.0-dev libpango1.0-dev libcairo2-dev libqtgui4 libqt4-test ffmpeg sqlite3 mbuffer npm python3-pygame
sudo apt-get -y dist-upgrade

sudo pip3 install --upgrade youtube_dl numpy opencv-python sharedmem HTTPServer apa102-pi pytz websockets simpleaudio python3-pygame

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
