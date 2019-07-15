#!/bin/bash
set -x

# installing and upgrading npm from scratch required a restart / re-login for the shell to recognize the new version
# when the version changed between `apt-get install npm` and `npm install npm@latest -g`
if ! which npm
then
    is_restart_required=true
fi

sudo apt-get update
sudo apt-get -y install git vim python3-pip libilmbase-dev libopenexr-dev libgstreamer1.0-dev libtiff5-dev libjasper-dev libpng-dev libjpeg-dev libavcodec-dev libavformat-dev libswscale-dev libv4l-dev libgtk2.0-dev libatlas-base-dev gfortran libgdk-pixbuf2.0-dev libpango1.0-dev libcairo2-dev libqtgui4 libqt4-test ffmpeg sqlite3 mbuffer npm
sudo apt-get -y dist-upgrade

sudo pip3 install --upgrade youtube_dl numpy opencv-python sharedmem HTTPServer apa102-pi pytz

# The `apt-get install npm` command installs a very old version of npm. Use npm to upgrade itself to latest.
sudo npm install npm@latest -g

# Install app dependencies
sudo npm install --prefix /home/pi/lightness/app

if [ "$is_restart_required" = true ] ; then
    echo "Restarting..."
    sudo shutdown -r now
fi