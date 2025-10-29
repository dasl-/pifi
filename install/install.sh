#!/usr/bin/env bash

set -euo pipefail -o errtrace

OS_VERSION=$(grep '^VERSION_ID=' /etc/os-release | sed 's/[^0-9]*//g')
CONFIG='/boot/config.txt'
if (( OS_VERSION > 12 )); then
    CONFIG='/boot/firmware/config.txt'
fi
old_config=$(cat $CONFIG)

BASE_DIR="$(dirname "$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )")"
HOSTNAME=''
RESTART_REQUIRED_FILE='/tmp/pifi_install_restart_required'

usage() {
    local exit_code=$1
    echo "usage: $0"
    echo "    -h            : Display this help message"
    echo "    -g HOSTNAME   : Set the hostname. This is optional."
    exit "$exit_code"
}

main(){
    trap 'fail $? $LINENO' ERR

    parseOpts "$@"
    generateLoadingScreens
    setTimezone
    setupSystemdServices
    setupYtDlpUpdateCron
    updateDbSchema
    buildWebApp
    disableWifiPowerManagement
    setOverVoltage
    setAvoidWarnings
    checkYoutubeApiKey

    # Setting the hostname should be as close to the last step as possible. Anything after this step that
    # requires `sudo` will emit a warning: "sudo: unable to resolve host raspberrypi: Name or service not known".
    # Note that `sudo` will still work; it's just a "warning".
    setHostname

    new_config=$(cat $CONFIG)
    config_diff=$(diff <(echo "$old_config") <(echo "$new_config") || true)
    if [[ -f $RESTART_REQUIRED_FILE || -n "$config_diff" ]] ; then
        info "Restart is required!"
        info "Config diff:\n$config_diff"
        info "Restarting..."

        # Hide the "sudo: unable to resolve host raspberrypi: Name or service not known" output by
        # redirecting stderr. This it to avoid someone thinking something didn't work  (it's fine).
        # Related to changing the hostname via setHostname above.
        sudo shutdown -r now 2>/dev/null
    fi
}

parseOpts(){
    while getopts ":hg:" opt; do
        case $opt in
            h) usage 0 ;;
            g)
                if [[ "$OPTARG" =~ ^[a-z]([a-z0-9-]*[a-z0-9])?$ ]]; then
                    HOSTNAME=${OPTARG}
                else
                    warn "Invalid hostname."
                    usage
                fi
                ;;
            \?)
                echo "Invalid option: -$OPTARG" >&2
                usage 1
                ;;
            :)
                echo "Option -$OPTARG requires an argument." >&2
                usage 1
                ;;
        esac
    done
}

generateLoadingScreens(){
    info "Generating loading screens"
    "$BASE_DIR"/utils/img_to_led --image "$BASE_DIR"/utils/loading_screen_monochrome.jpg --output-file "$BASE_DIR"/loading_screen --color-mode monochrome
    "$BASE_DIR"/utils/img_to_led --image "$BASE_DIR"/utils/loading_screen_color.jpg --output-file "$BASE_DIR"/loading_screen --color-mode color
}

setTimezone(){
    info "Setting timezone"
    sudo timedatectl set-timezone UTC
}

setupSystemdServices(){
    info "Setting up systemd services"

    sudo "$BASE_DIR/install/pifi_queue_service.sh"
    sudo "$BASE_DIR/install/pifi_server_service.sh"
    sudo "$BASE_DIR/install/pifi_websocket_server_service.sh"
    sudo chown root:root /etc/systemd/system/pifi_*.service
    sudo chmod 644 /etc/systemd/system/pifi_*.service
    sudo systemctl enable /etc/systemd/system/pifi_*.service
    sudo systemctl daemon-reload
    sudo systemctl restart $(ls /etc/systemd/system/pifi_*.service | cut -d'/' -f5)
}


setupYtDlpUpdateCron(){
    # setup yt-dlp update cron
    sudo "$BASE_DIR/install/pifi_cron.sh"
    sudo chown root:root /etc/cron.d/pifi
    sudo chmod 644 /etc/cron.d/pifi
}

updateDbSchema(){
    info "Updating DB schema (if necessary)..."
    sudo "$BASE_DIR"/utils/make_db
}

buildWebApp(){
    info "Building web app"
    npm run build --prefix "$BASE_DIR"/app
}

# https://github.com/raspberrypi/linux/issues/2522#issuecomment-692559920
# https://forums.raspberrypi.com/viewtopic.php?p=1764517#p1764517
# Maybe wifi power management is cause of occasional network issues?
#   See: https://gist.github.com/dasl-/18599c40408d268adfc92f8704ca1c11#2022-01-24
disableWifiPowerManagement(){
    if [ ! -f /etc/rc.local ]; then
        # rc.local file no longer exists in newer raspbian, but we can still create it and it will be used:
        # https://forums.raspberrypi.com/viewtopic.php?p=2283266#p2283266
cat <<-EOF | sudo tee /etc/rc.local >/dev/null
#!/bin/sh -e
logger "rc.local here"
exit 0
EOF
        sudo chmod 755 /etc/rc.local
    fi
    if ! grep -q '^iwconfig wlan0 power off' /etc/rc.local ; then
        info "Disabling wifi power management..."

        # disable it
        sudo iwconfig wlan0 power off

        # ensure it stays disabled after reboots
        if [ "$(grep --count '^exit 0$' /etc/rc.local)" -ne 1 ] ; then
           die "Unexpected contents in /etc/rc.local"
        fi
        sudo sed /etc/rc.local -i -e "s/^exit 0$/iwconfig wlan0 power off/"
        echo "exit 0" | sudo tee -a /etc/rc.local >/dev/null 2>&1
    else
        info "Wifi power management already disabled"
    fi
}

# See: https://github.com/dasl-/piwall2/blob/main/docs/issues_weve_seen_before.adoc#video-playback-freezes-cause-1
#      https://github.com/Hexxeh/rpi-firmware/issues/249
#      https://www.raspberrypi.com/documentation/computers/config_txt.html#overclocking
#      https://github.com/dasl-/pifi/blob/main/docs/issues_weve_seen_before.adoc#unable-to-ssh-onto-pi--hit-pifi-web-page
setOverVoltage(){
    over_voltage=$(vcgencmd get_config over_voltage | sed -n 's/over_voltage=\(.*\)/\1/p')
    if (( over_voltage >= 2 )); then
        info "over_voltage was already high enough ( $over_voltage )..."
        return
    fi

    force_turbo=$(vcgencmd get_config force_turbo | sed -n 's/force_turbo=\(.*\)/\1/p')
    if (( force_turbo == 1 )); then
        # See: https://www.raspberrypi.com/documentation/computers/config_txt.html#overclocking-options
        warn "WARNING: not setting over_voltage because force_turbo is enabled and we don't " \
            "want to set your warranty bit. This might result in video playback issues."
        return
    fi

    # Set over_voltage.
    info "Setting over_voltage to 2..."

    # comment out existing over_voltage lines in config
    sudo sed $CONFIG -i -e "s/^\(over_voltage=.*\)/#\1/"

    echo -e 'over_voltage=2' | sudo tee -a $CONFIG >/dev/null
}

# See:
# https://github.com/dasl-/pifi/blob/main/docs/issues_weve_seen_before.adoc#spurious-undervoltage-warnings-resulting-in-throttling
# https://www.raspberrypi.com/documentation/computers/legacy_config_txt.html#avoid_warnings
setAvoidWarnings(){
    local avoid_warnings
    avoid_warnings=$(vcgencmd get_config avoid_warnings | sed -n 's/avoid_warnings=\(.*\)/\1/p')
    if (( avoid_warnings == 2 )); then
        info "avoid_warnings was already set ( $avoid_warnings )..."
        return
    fi

    # Set avoid_warnings.
    info "Setting avoid_warnings to 2..."

    # comment out existing avoid_warnings lines in config
    sudo sed $CONFIG -i -e "s/^\(avoid_warnings=.*\)/#\1/"

    echo -e 'avoid_warnings=2' | sudo tee -a $CONFIG >/dev/null
}

checkYoutubeApiKey(){
    info "Checking for youtube API key..."
    local youtube_api_key
    youtube_api_key=$("$BASE_DIR"/utils/youtube_api_key)
    if [ -z "${youtube_api_key}" ]; then
        warn "WARNING: your youtube API key has not been set. See: https://github.com/dasl-/pifi/blob/main/docs/setting_your_youtube_api_key.adoc"
    else
        info "Found youtube API key!"
    fi
}

# Set the hostname. Allows sshing and hitting the pifi webpage via "HOSTNAME.local"
# See: https://www.raspberrypi.com/documentation/computers/remote-access.html#resolving-raspberrypi-local-with-mdns
setHostname(){
    if [[ -n ${HOSTNAME} ]]; then
        info "Setting hostname to '$HOSTNAME' (if not already set to '$HOSTNAME')..."
        if [[ $(cat /etc/hostname) != "$HOSTNAME" ]]; then
            echo "$HOSTNAME" | sudo tee /etc/hostname >/dev/null 2>&1
            sudo sed -i -E 's/(127\.0\.1\.1\s+)[^ ]+/\1'"$HOSTNAME"'/g' /etc/hosts
            touch $RESTART_REQUIRED_FILE
        fi
    fi
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
