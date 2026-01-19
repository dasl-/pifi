#!/usr/bin/env bash

set -euo pipefail -o errtrace

BASE_DIR="$(dirname "$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )")"
RESTART_REQUIRED_FILE='/tmp/pifi_install_restart_required'
# OS_VERSION=$(grep '^VERSION_ID=' /etc/os-release | sed 's/[^0-9]*//g')
CONFIG='/boot/firmware/config.txt'

main(){
    trap 'fail $? $LINENO' ERR

    updateAndInstallPackages
    installDeno
    setupUv
    installYtDlp
    enableSpi
    installLedDriver
    installNode

    if [ -f $RESTART_REQUIRED_FILE ]; then
        echo "Restarting..."
        sudo shutdown -r now
    fi
}

updateAndInstallPackages(){
    info "Updating and installing packages..."

    # Allow the command `sudo apt build-dep python3-pygame` to run.
    sudo sed -i 's/^Types: deb\s*$/Types: deb deb-src/' /etc/apt/sources.list.d/debian.sources

    sudo apt update

    # python3-pip: needed to ensure we have the pip module. Else we'd get errors like this:
    #   https://askubuntu.com/questions/1388144/usr-bin-python3-no-module-named-pip
    # libsdl2-mixer: needed for pygame
    #   (maybe it's no longer necessary to explicitly install it since we have `sudo apt -y build-dep python3-pygame` below?`)
    # libsdl2-dev: needed for pygame
    #   (maybe it's no longer necessary to explicitly install it since we have `sudo apt -y build-dep python3-pygame` below?`)
    # parallel: needed for update_yt-dlp.sh script

    sudo apt -y install git python3-pip ffmpeg sqlite3 mbuffer libsdl2-mixer-2.0-0 libsdl2-dev parallel \
        libopenblas-dev python3-numpy
    sudo apt -y build-dep python3-pygame # other dependencies needed for pygame
    sudo apt -y full-upgrade

    # RE simpleaudio, see: https://github.com/hamiltron/py-simple-audio/issues/72#issuecomment-1902610214
    # Install Python packages with pip (yt-dlp is installed separately via uv tool install)
    sudo PIP_BREAK_SYSTEM_PACKAGES=1 python3 -m pip install --upgrade pytz websockets pygame pyjson5 \
        git+https://github.com/cexen/py-simple-audio.git uv
}

# yt-dlp now requires a JS interpreter. They recommend Deno:
# https://github.com/yt-dlp/yt-dlp/wiki/EJS
installDeno(){
    info "\\nInstalling deno..."
    local deno_version
    deno_version='2.6.5'
    if command -v deno >/dev/null 2>&1 && deno --version | head -n1 | grep -q "^deno $deno_version "; then
        echo "Deno $deno_version is already installed"
        return
    fi

    sudo rm -rf /tmp/deno
    mkdir -p /tmp/deno
    wget -P /tmp/deno "https://github.com/denoland/deno/releases/download/v$deno_version/deno-aarch64-unknown-linux-gnu.zip"
    unzip -d /tmp/deno /tmp/deno/deno-aarch64-unknown-linux-gnu.zip
    sudo chmod a+x /tmp/deno/deno
    sudo mv /tmp/deno/deno /usr/bin/deno
    sudo rm -rf /tmp/deno
}

setupUv(){
    info "\\nSetting up uv..."

    # Install a version of python that is supported by the latest version of yt-dlp
    # Install as root. Always invoke uv as root such that it uses a consistent set of working directories.
    # See: https://github.com/astral-sh/uv/issues/11360
    sudo uv python install 3.13
}

installYtDlp(){
    info "\\nInstalling yt-dlp..."

    # Remove the pip installed yt-dlp in case it's present (we used to install yt-dlp with pip).
    sudo PIP_BREAK_SYSTEM_PACKAGES=1 python3 -m pip uninstall -y 'yt-dlp[default]'
    sudo PIP_BREAK_SYSTEM_PACKAGES=1 python3 -m pip uninstall -y 'yt-dlp'
    "$BASE_DIR"/utils/update_yt-dlp.sh
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
    sudo PIP_BREAK_SYSTEM_PACKAGES=1 python3 -m pip install --upgrade apa102-pi
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

    sudo PIP_BREAK_SYSTEM_PACKAGES=1 python3 -m pip install --upgrade Pillow
    sudo apt -y install python3-pillow

    make build-python PYTHON="$(command -v python3)"
    sudo make install-python PYTHON="$(command -v python3)"
    popd
}

installLedDriverWs2812b(){
    info "Installing LED driver ws2812b..."
    sudo PIP_BREAK_SYSTEM_PACKAGES=1 python3 -m pip install --upgrade rpi_ws281x

    # Set SPI buffer size.
    # See: https://github.com/rpi-ws281x/rpi-ws281x-python/tree/master/library#spi
    local spi_bufsiz='spidev.bufsiz=32768'
    cmdline_path='/boot/firmware/cmdline.txt'
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
