#!/usr/bin/env bash

set -euo pipefail -o errtrace

BASE_DIR="$(dirname "$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )")"
RESTART_REQUIRED_FILE='/tmp/pifi_install_restart_required'

main(){
    trap 'fail $? $LINENO' ERR

    updateAndInstallPackages
    installLedDriver
    clearYoutubeDlCache
    installNode

    if [ -f $RESTART_REQUIRED_FILE ]; then
        echo "Restarting..."
        sudo shutdown -r now
    fi
}

updateAndInstallPackages(){
    info "Updating and installing packages..."

    # Allow the command `sudo apt build-dep python3-pygame` to run.
    # https://stackoverflow.com/questions/47773715/error-you-must-put-some-source-uris-in-your-sources-list
    sudo sed -i 's/#\s*deb-src/deb-src/' /etc/apt/sources.list

    sudo apt update

    # libsdl2-mixer: needed for pygame
    #   (maybe it's no longer necessary to explicitly install it since we have `sudo apt -y build-dep python3-pygame` below?`)
    # libsdl2-dev: needed for pygame
    #   (maybe it's no longer necessary to explicitly install it since we have `sudo apt -y build-dep python3-pygame` below?`)
    # parallel: needed for update_youtube-dl.sh script
    # libatlas-base-dev: needed for numpy
    sudo apt -y install git ffmpeg sqlite3 mbuffer libsdl2-mixer-2.0-0 libsdl2-dev parallel \
        libatlas-base-dev
    sudo apt -y build-dep python3-pygame # other dependencies needed for pygame
    sudo apt -y full-upgrade

    sudo python3 -m pip install --upgrade youtube_dl yt-dlp numpy pytz websockets simpleaudio pygame pyjson5
}

installLedDriver(){
    info "Installing LED driver..."
    local led_driver
    led_driver=$("$BASE_DIR"/utils/get_config_value --keys leds.driver)
    case $led_driver in
        apa102)     installLedDriverApa102 ;;
        rgbmatrix)  installLedDriverRgbMatrix ;;
        *)          die "Unsupported LED driver: $led_driver" ;;
    esac
}

installLedDriverApa102(){
    info "Installing LED driver apa102..."
    sudo python3 -m pip install --upgrade apa102-pi
}

# e.g. https://www.adafruit.com/product/2276
installLedDriverRgbMatrix(){
    info "Installing LED driver RGB Matrix..."

    local clone_dir
    clone_dir="$BASE_DIR/../rpi-rgb-led-matrix"
    if [ -d "$clone_dir" ]; then
        info "Pulling repo in $clone_dir ..."
        pushd "$clone_dir"
        git pull
    else
        info "Cloning repo into $clone_dir ..."
        git clone https://github.com/hzeller/rpi-rgb-led-matrix "$clone_dir"
        pushd "$clone_dir"
    fi

    make build-python PYTHON="$(command -v python3)"
    sudo make install-python PYTHON="$(command -v python3)"
    popd

    sudo python3 -m pip install --upgrade Pillow
}

clearYoutubeDlCache(){
    info "Clearing youtube-dl caches..."

    # https://askubuntu.com/a/329689
    local users
    users=$(awk -F: '$3 >= 1000 && $1 != "nobody" {print $1}' /etc/passwd)

    # Just in case the youtube-dl cache got polluted, as it has before...
    # https://github.com/ytdl-org/youtube-dl/issues/24780
    # shellcheck disable=SC1083
    parallel --will-cite --max-procs 0 --halt never sudo -u {1} {2} --rm-cache-dir ::: root "$users" ::: youtube-dl yt-dlp
}

installNode(){
    info "\\nInstalling node and npm..."

    # Install node and npm. Installing this with the OS's default packages provided by apt installs a pretty old
    # version of node and npm. We need a newer version.
    # See: https://github.com/nodesource/distributions/blob/master/README.md#installation-instructions
    curl -fsSL https://deb.nodesource.com/setup_18.x | sudo bash -
    sudo apt-get install -y nodejs

    info "\\nInstalling react app dependencies..."
    # TODO: when installing from scratch on a fresh OS installation, this step once failed with
    # and error: https://gist.github.com/dasl-/01b9bf9650730c7dbfab6c859ea6c0dc
    # See if this is reproducible on a fresh install sometime...
    # It's weird because apparently it's a node error, but the line that is executing below is a
    # npm command. Could npm be shelling out to node? Maybe I can figure this out by running
    # checking the process list while the next step is running, and htop to look at RAM usage.`
    npm install --prefix "$BASE_DIR/app"
}

fail(){
    local exit_code=$1
    local line_no=$2
    local script_name
    script_name=$(basename "${BASH_SOURCE[0]}")
    die "Error in $script_name at line number: $line_no with exit code: $exit_code"
}

info(){
    echo -e "\x1b[32m$*\x1b[0m" # green stdout
}

warn(){
    echo -e "\x1b[33m$*\x1b[0m" # yellow stdout
}

die(){
    echo
    echo -e "\x1b[31m$*\x1b[0m" >&2 # red stderr
    exit 1
}

main "$@"
