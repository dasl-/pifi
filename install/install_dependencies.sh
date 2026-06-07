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
    setupVenv
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

    # System libraries + build tooling only — NOT Python packages. pifi's Python
    # deps live in pyproject.toml / uv.lock and install into a venv (setupVenv).
    # We no longer apt-install python3-numpy/requests/pil, and we dropped the SDL
    # (libsdl2-*) and OpenBLAS (libopenblas-dev) dev libs plus the heavy
    # `build-dep python3-pygame` (and the deb-src hack it needed): numpy/pillow/
    # pygame now install as prebuilt aarch64 wheels that bundle their own
    # SDL/OpenBLAS. What's left:
    #   git: clone rpi-rgb-led-matrix; uv builds simpleaudio from a git URL.
    #   python3-pip: bootstraps uv (setupUv).
    #   build-essential, libasound2-dev: compile the source-built extensions in
    #     the venv — simpleaudio (git, links ALSA) and, for the ws2812b driver,
    #     rpi-ws281x (sdist). They build against the uv-managed Python's bundled
    #     headers (setupVenv), so the system python3-dev isn't needed. NOTE:
    #     rgbmatrix's `make build-python` may additionally need Cython. Since it
    #     builds against the venv interpreter (not system python3), add Cython to
    #     the venv (e.g. as a pyproject build dep) rather than apt cython3 if a
    #     source build fails on a Pi.
    #   ffmpeg: video processing/playback. sqlite3: DB CLI. mbuffer: video
    #     streaming buffer. parallel: update_yt-dlp.sh.
    sudo apt -y install git python3-pip build-essential libasound2-dev \
        ffmpeg sqlite3 mbuffer parallel
    sudo apt -y full-upgrade
}

# Build the pifi virtualenv (.venv) from uv.lock — the same single source the
# dev env uses. Pinned (--frozen). --managed-python makes uv use (downloading if
# needed) its own CPython matching .python-version / requires-python (3.13),
# independent of whatever python the base OS ships — so the install isn't tied
# to the Pi running a particular system python. The source-built extensions
# (simpleaudio, rpi-ws281x) compile against that managed python's bundled
# headers, which is why the system python3-dev isn't needed.
# Installs runtime deps + the dev group (pyright/pytest); the LED-driver extra
# is added later by installLedDriver. pifi itself is not installed as a package
# ([tool.uv] package = false) — the bin/ scripts run it in-place via sys.path.
# Run unprivileged so .venv (and uv's managed python) are owned by the repo
# user; the (root) systemd services just execute .venv/bin/python, which root
# can read fine. Kept separate from the root-owned /opt/uv python that yt-dlp
# uses (setupUv), per https://github.com/astral-sh/uv/issues/11360.
setupVenv(){
    info "\\nCreating the pifi virtualenv (.venv) from uv.lock..."
    ( cd "$BASE_DIR" && uv sync --frozen --managed-python )
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

    # uv is an install-time tool (used just below, by setupVenv, and by the
    # yt-dlp update cron), not a pifi runtime dependency, so it's installed
    # directly with pip rather than listed in pyproject.toml.
    sudo PIP_BREAK_SYSTEM_PACKAGES=1 python3 -m pip install --upgrade uv

    sudo mkdir --parents /opt/uv/python /opt/uv/python-bin /opt/uv/tools /opt/uv/tools-bin

    # Install a version of python that is supported by the latest version of yt-dlp
    # Install as root. Always invoke uv as root such that it uses a consistent set of working directories.
    # See: https://github.com/astral-sh/uv/issues/11360
    sudo UV_PYTHON_INSTALL_DIR=/opt/uv/python UV_PYTHON_BIN_DIR=/opt/uv/python-bin UV_TOOL_DIR=/opt/uv/tools UV_TOOL_BIN_DIR=/opt/uv/tools-bin uv python install 3.13
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
    info "\\nInstalling LED driver..."
    # Read the driver via the venv python (setupVenv has run, so pifi's config
    # deps are available). apa102 / ws2812b ship as pip extras and just need
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

# Add an LED-driver extra (apa102 / ws2812b) from pyproject's optional
# dependencies into the venv, pinned by the lock. uv sync keeps the base deps
# and dev group; it just adds the extra's packages.
syncLedExtra(){
    info "Installing the '$1' LED-driver extra into the venv..."
    ( cd "$BASE_DIR" && uv sync --frozen --managed-python --extra "$1" )
}

# e.g. https://www.adafruit.com/product/2276
installLedDriverRgbMatrix(){
    info "Installing LED driver RGB Matrix..."

    local clone_dir venv_python
    clone_dir="$BASE_DIR/../rpi-rgb-led-matrix"
    venv_python="$BASE_DIR/.venv/bin/python"
    if [ -d "$clone_dir" ]; then
        info "Pulling repo in $clone_dir ..."
        pushd "$clone_dir"
        git pull
    else
        info "Cloning repo into $clone_dir ..."
        git clone https://github.com/hzeller/rpi-rgb-led-matrix "$clone_dir"
        pushd "$clone_dir"
    fi

    # Build and install the python binding into the venv (no sudo — the venv is
    # owned by the repo user). rgbmatrix has no PyPI package, so it lives in the
    # venv alongside the lock-managed deps rather than being apt/pip-installed.
    make build-python PYTHON="$venv_python"
    make install-python PYTHON="$venv_python"
    popd
}

configureLedDriverWs2812b(){
    info "Configuring LED driver ws2812b... (the rpi-ws281x package is installed from the ws2812b extra)"

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
