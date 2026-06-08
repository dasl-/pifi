#!/usr/bin/env bash

set -euo pipefail -o errtrace

BASE_DIR="$(dirname "$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )")"
RESTART_REQUIRED_FILE='/tmp/pifi_install_restart_required'
# OS_VERSION=$(grep '^VERSION_ID=' /etc/os-release | sed 's/[^0-9]*//g')
CONFIG='/boot/firmware/config.txt'
# yt-dlp requires frequent updates. Allow its version of python to diverge from the version of python used by
# the rest of the codebase.
YT_DLP_PYTHON_VERSION='3.13'

main(){
    trap 'fail $? $LINENO' ERR

    updateAndInstallPackages
    installDeno
    installUvAndVenv
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

    sudo apt update

    # System libraries + build tooling only — NOT Python packages. The pifi's Python
    # dependencies live in pyproject.toml / uv.lock and install into a venv.
    #
    #   python3-pip: bootstraps uv
    #   build-essential, libasound2-dev: compile the source-built extensions in
    #     the venv — simpleaudio and, for the ws2812b driver, rpi-ws281x (sdist).
    #   ffmpeg: video processing/playback.
    #   mbuffer: video streaming buffer.
    #   parallel: needed for update_yt-dlp.sh script
    sudo apt -y install git python3-pip build-essential libasound2-dev \
        ffmpeg sqlite3 mbuffer parallel
    sudo apt -y full-upgrade
}

installUvAndVenv(){
    info "\\nInstalling uv and creating the pifi virtualenv (.venv) from uv.lock..."

    sudo PIP_BREAK_SYSTEM_PACKAGES=1 python3 -m pip install --upgrade uv

    # Build the pifi virtualenv (.venv) from uv.lock.
    #   --frozen: pin dependencyversions
    #   --managed-python: makes uv use (downloading if needed) its own Python, separate
    #     from the system installed one
    #
    # Run unprivileged so .venv (and uv's managed python) are owned by the repo
    # user; the (root) systemd services just execute .venv/bin/python, which root
    # can read fine.
    pushd "$BASE_DIR"
    uv sync --frozen --managed-python
    popd
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

installYtDlp(){
    info "\\nInstalling yt-dlp..."

    sudo mkdir --parents /opt/uv/python /opt/uv/python-bin /opt/uv/tools /opt/uv/tools-bin

    # Install a version of python that is supported by the latest version of yt-dlp
    # Install as root. With respect to yt-dlp, always invoke uv as root such that it uses a consistent set of working directories.
    # See: https://github.com/astral-sh/uv/issues/11360
    sudo UV_PYTHON_INSTALL_DIR=/opt/uv/python UV_PYTHON_BIN_DIR=/opt/uv/python-bin UV_TOOL_DIR=/opt/uv/tools UV_TOOL_BIN_DIR=/opt/uv/tools-bin uv python install $YT_DLP_PYTHON_VERSION

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
    info "\\nInstalling LED driver..."
    # apa102 / ws2812b ship as pip extras and just need
    # their package synced into the venv; ws2812b additionally needs SPI/clock
    # tuning. rgbmatrix has no pip package — it's a source build into the venv.
    local led_driver
    led_driver=$("$BASE_DIR"/.venv/bin/python "$BASE_DIR"/utils/get_config_value --keys leds.driver)
    info "Configured LED driver: $led_driver"
    case $led_driver in
        apa102)     syncLedExtra apa102 ;;
        ws2812b)    syncLedExtra ws2812b; configureLedDriverWs2812b ;;
        rgbmatrix)  installLedDriverRgbMatrix ;;
        *)          die "Unsupported LED driver: $led_driver" ;;
    esac
}

syncLedExtra(){
    pushd "$BASE_DIR"
    uv sync --frozen --managed-python --extra "$1"
    popd
}

# e.g. https://www.adafruit.com/product/2276
installLedDriverRgbMatrix(){
    info "Installing LED driver RGB Matrix..."

    local clone_dir venv_python
    clone_dir="$BASE_DIR/../rpi-rgb-led-matrix"
    venv_python="$BASE_DIR/.venv/bin/python"

    pushd "$BASE_DIR"
    uv sync --frozen --managed-python --group rgbmatrix-build
    popd

    if [ -d "$clone_dir" ]; then
        info "Pulling repo in $clone_dir ..."
        pushd "$clone_dir"
        git pull
    else
        info "Cloning repo into $clone_dir ..."
        git clone https://github.com/hzeller/rpi-rgb-led-matrix "$clone_dir"
        pushd "$clone_dir"
    fi

    make build-python PYTHON="$venv_python"
    sudo make install-python PYTHON="$venv_python"
    popd

    info "Verifying the rgbmatrix binding imports..."
    "$venv_python" -c 'import rgbmatrix'
}

configureLedDriverWs2812b(){
    info "Configuring LED driver ws2812b..."

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
