#!/usr/bin/env bash

set -euo pipefail -o errtrace

BASE_DIR="$(dirname "$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )")"
is_restart_required=false

main(){
    trap 'fail $? $LINENO' ERR

    updateAndInstallPackages
    installLedDriver
    clearYoutubeDlCache
    installNpm
    installAppDependencies

    if [ "$is_restart_required" = true ] ; then
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
    sudo apt -y install git python3-pip ffmpeg sqlite3 mbuffer npm libsdl2-mixer-2.0-0 libsdl2-dev parallel \
        libatlas-base-dev
    sudo apt -y build-dep python3-pygame # other dependencies needed for pygame
    sudo apt -y full-upgrade

    sudo pip3 install --upgrade youtube_dl yt-dlp numpy pytz websockets simpleaudio pygame pyjson5
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
    sudo pip3 install --upgrade apa102-pi
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

    sudo pip3 install --upgrade Pillow
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

installNpm(){
    info "Installing npm..."

    # installing and upgrading npm from scratch required a restart / re-login for the shell to recognize the new version
    # when the version changed between `apt install npm` and `npm install npm@latest -g`
    if ! which npm >/dev/null ; then
        is_restart_required=true
    fi

    # The `apt install npm` command installs a very old version of npm. Use npm to upgrade itself to latest.
    sudo npm install npm@latest -g
}

installAppDependencies(){
    info "Installing app dependencies..."

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
