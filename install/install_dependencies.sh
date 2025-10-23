#!/usr/bin/env bash

set -euo pipefail -o errtrace

BASE_DIR="$(dirname "$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )")"
CONFIG='/boot/config.txt'
RESTART_REQUIRED_FILE='/tmp/pifi_install_restart_required'
OS_VERSION=$(grep '^VERSION_ID=' /etc/os-release | sed 's/[^0-9]*//g')

main(){
    trap 'fail $? $LINENO' ERR

    updateAndInstallPackages
    enableSpi
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

    # libatlas-base-dev: needed for numpy ?
    if (( OS_VERSION > 12 )); then
        local atlas_package=''
        local numpy_package='' # numpy is installed by default?

        # Fix for `Error: You must put some 'deb-src' URIs in your sources.list`
        # This error occurs when doing `sudo apt -y build-dep ...`
        # sudo bash -c 'cp -a /etc/apt/sources.list /etc/apt/sources.list.bak.$(date +%Y%m%d-%H%M%S) 2>/dev/null; \
        # cat >/etc/apt/sources.list <<EOF
        # deb http://deb.debian.org/debian trixie main contrib non-free non-free-firmware
        # deb-src http://deb.debian.org/debian trixie main contrib non-free non-free-firmware

        # deb http://security.debian.org/debian-security trixie-security main contrib non-free non-free-firmware
        # deb-src http://security.debian.org/debian-security trixie-security main contrib non-free non-free-firmware

        # deb http://deb.debian.org/debian trixie-updates main contrib non-free non-free-firmware
        # deb-src http://deb.debian.org/debian trixie-updates main contrib non-free non-free-firmware
        # EOF

        # mkdir -p /etc/apt/sources.list.d; \
        # cp -a /etc/apt/sources.list.d/raspi.list /etc/apt/sources.list.d/raspi.list.bak.$(date +%Y%m%d-%H%M%S) 2>/dev/null; \
        # cat >/etc/apt/sources.list.d/raspi.list <<EOF
        # deb http://archive.raspberrypi.org/debian/ trixie main
        # deb-src http://archive.raspberrypi.org/debian/ trixie main
        # EOF

        # apt update'
    else
        local atlas_package='libatlas-base-dev'
        local numpy_package='numpy'
    fi

    # python3-pip: needed to ensure we have the pip module. Else we'd get errors like this:
    #   https://askubuntu.com/questions/1388144/usr-bin-python3-no-module-named-pip
    # libsdl2-mixer: needed for pygame
    #   (maybe it's no longer necessary to explicitly install it since we have `sudo apt -y build-dep python3-pygame` below?`)
    # libsdl2-dev: needed for pygame
    #   (maybe it's no longer necessary to explicitly install it since we have `sudo apt -y build-dep python3-pygame` below?`)
    # parallel: needed for update_youtube-dl.sh script

    sudo apt -y install git python3-pip ffmpeg sqlite3 mbuffer libsdl2-mixer-2.0-0 libsdl2-dev parallel \
        $atlas_package libopenblas-dev
    sudo apt -y build-dep python3-pygame # other dependencies needed for pygame
    sudo apt -y full-upgrade

    sudo PIP_BREAK_SYSTEM_PACKAGES=1 python3 -m pip install --upgrade youtube_dl yt-dlp $numpy_package pytz websockets simpleaudio pygame pyjson5
}

enableSpi(){
    if [ "$(sudo raspi-config nonint get_spi)" = "1" ]; then
        info "Enabling SPI..."
        # https://raspberrypi.stackexchange.com/a/96679
        sudo raspi-config nonint do_spi 0
        touch $RESTART_REQUIRED_FILE
    else
        info "SPI was already enabled."
    fi
}

installLedDriver(){
    info "Installing LED driver..."
    local led_driver
    led_driver=$("$BASE_DIR"/utils/get_config_value --keys leds.driver)
    case $led_driver in
        apa102)     installLedDriverApa102 ;;
        rgbmatrix)  installLedDriverRgbMatrix ;;
        ws2812b)    installLedDriverWs2812b ;;
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

installLedDriverWs2812b(){
    info "Installing LED driver ws2812b..."
    sudo python3 -m pip install --upgrade rpi_ws281x

    # Set SPI buffer size.
    # See: https://github.com/rpi-ws281x/rpi-ws281x-python/tree/master/library#spi
    local spi_bufsiz='spidev.bufsiz=32768'
    local cmdline_path='/boot/cmdline.txt'
    if ! grep -q $spi_bufsiz $cmdline_path ; then
        info "Updating spidev.bufsiz..."
        sudo sed -i '1 s/$/ spidev.bufsiz=32768/' $cmdline_path
        touch $RESTART_REQUIRED_FILE
    else
        info "spidev.bufsiz is already large enough..."
    fi

    # Set core_freq / core_freq_min
    # See: https://github.com/rpi-ws281x/rpi-ws281x-python/tree/master/library#spi
    # https://www.raspberrypi.com/documentation/computers/config_txt.html#overclocking
    if grep -q 'Raspberry Pi 4 ' /proc/device-tree/model ; then
        local rpi4_core_freq_min='core_freq_min=500'
        if [ "$(vcgencmd get_config core_freq_min)" = $rpi4_core_freq_min ] ; then
            info "Detected Raspberry Pi 4 - core_freq_min is already set appropriately."
        else
            info "Detected Raspberry Pi 4 - setting core_freq_min..."
            echo -e "\n[pi4]\n$rpi4_core_freq_min\n\n[all]\n" | sudo tee -a $CONFIG >/dev/null
            touch $RESTART_REQUIRED_FILE
        fi
    elif grep -q 'Raspberry Pi 3 ' /proc/device-tree/model ; then
        local rpi3_core_freq='core_freq=250'
        if [ "$(vcgencmd get_config core_freq)" = $rpi3_core_freq ] ; then
            info "Detected Raspberry Pi 3 - core_freq is already set appropriately."
        else
            info "Detected Raspberry Pi 3 - setting core_freq..."
            echo -e "\n[pi3]\n$rpi3_core_freq\n\n[all]\n" | sudo tee -a $CONFIG >/dev/null
            touch $RESTART_REQUIRED_FILE
        fi
    fi
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
