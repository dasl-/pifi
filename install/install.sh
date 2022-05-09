#!/usr/bin/env bash

set -euo pipefail -o errtrace

CONFIG=/boot/config.txt
old_config=$(cat $CONFIG)

BASE_DIR="$(dirname "$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )")"
is_restart_required=false

usage() {
    local exit_code=$1
    echo "usage: $0"
    echo "    -h    display this help message"
    exit "$exit_code"
}

main(){
    trap 'fail $? $LINENO' ERR

    parseOpts "$@"
    generateLoadingScreens
    setTimezone
    setupLogging
    setupSystemdServices
    setupYoutubeDlUpdateCron
    updateDbSchema
    buildWebApp
    setHostname
    disableWifiPowerManagement
    checkYoutubeApiKey

    new_config=$(cat $CONFIG)
    config_diff=$(diff <(echo "$old_config") <(echo "$new_config") || true)
    if [[ $is_restart_required = true || -n "$config_diff" ]] ; then
        info "Restart is required!"
        info "Config diff:\n$config_diff"
        info "Restarting..."
        sudo shutdown -r now
    fi
}

parseOpts(){
    while getopts ":h" opt; do
        case $opt in
            h) usage 0 ;;
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

setupLogging(){
    info "Setting up logging"

    # setup logging: syslog
    sudo mkdir -p /var/log/pifi
    sudo touch /var/log/pifi/server.log /var/log/pifi/queue.log /var/log/pifi/websocket_server.log /var/log/pifi/update_youtube-dl.log
    sudo cp "$BASE_DIR"/install/*_syslog.conf /etc/rsyslog.d
    sudo systemctl restart rsyslog

    # setup logging: logrotate
    sudo cp "$BASE_DIR"/install/pifi_logrotate /etc/logrotate.d
    sudo chown root:root /etc/logrotate.d/pifi_logrotate
    sudo chmod 644 /etc/logrotate.d/pifi_logrotate
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


setupYoutubeDlUpdateCron(){
    # setup youtube-dl update cron
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

# Set the hostname. Allows sshing and hitting the pifi webpage via "pifi.local"
# See: https://www.raspberrypi.com/documentation/computers/remote-access.html#resolving-raspberrypi-local-with-mdns
setHostname(){
    info "Setting hostname"
    if [[ $(cat /etc/hostname) != pifi ]]; then
        echo "pifi" | sudo tee /etc/hostname >/dev/null 2>&1
        sudo sed -i -E 's/(127\.0\.1\.1\s+)[^ ]+/\1pifi/g' /etc/hosts
        is_restart_required=true
    fi
}

# https://github.com/raspberrypi/linux/issues/2522#issuecomment-692559920
# https://forums.raspberrypi.com/viewtopic.php?p=1764517#p1764517
# Maybe wifi power management is cause of occasional network issues?
#   See: https://gist.github.com/dasl-/18599c40408d268adfc92f8704ca1c11#2022-01-24
disableWifiPowerManagement(){
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
