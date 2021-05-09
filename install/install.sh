#!/bin/bash

usage() {
  local exit_code=$1
  echo "usage: $0 -w <display width> -l <display height>"
  echo "    -h                   display this help message"
  echo "    -w <display width>   Num of LEDs in the array horizontally. Defaults to 28."
  echo "    -l <display height>  Num of LEDs in the array vertically. Defaults to 18."
  exit "$exit_code"
}

# get opts
display_width=28
display_height=18
while getopts ":hw:l:" opt; do
  case $opt in
    h) usage 0 ;;
    w) display_width=$OPTARG ;;
    l) display_height=$OPTARG ;;
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

set -x

BASE_DIR="$(dirname "$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )")"

# generate loading screens
if [ ! -f "$BASE_DIR"/loading_screen_monochrome.npy ]; then
    "$BASE_DIR"/utils/img_to_led --image "$BASE_DIR"/utils/loading_screen_monochrome.jpg --display-width $display_width --display-height $display_height --output-file "$BASE_DIR"/loading_screen --color-mode monochrome
fi
if [ ! -f "$BASE_DIR"/loading_screen_color.npy ]; then
    "$BASE_DIR"/utils/img_to_led --image "$BASE_DIR"/utils/loading_screen_color.jpg --display-width $display_width --display-height $display_height --output-file "$BASE_DIR"/loading_screen --color-mode color
fi

# set timezone
sudo timedatectl set-timezone UTC

# setup logging: syslog
sudo mkdir -p /var/log/pifi
sudo touch /var/log/pifi/server.log /var/log/pifi/queue.log /var/log/pifi/websocket_server.log /var/log/pifi/update_youtube-dl.log
sudo cp "$BASE_DIR"/install/*_syslog.conf /etc/rsyslog.d
sudo systemctl restart rsyslog

# setup logging: logrotate
sudo cp "$BASE_DIR"/install/pifi_logrotate /etc/logrotate.d
sudo chown root:root /etc/logrotate.d/pifi_logrotate
sudo chmod 644 /etc/logrotate.d/pifi_logrotate

# setup systemd services
sudo "$BASE_DIR/install/pifi_queue_service.sh"
sudo "$BASE_DIR/install/pifi_server_service.sh"
sudo "$BASE_DIR/install/pifi_websocket_server_service.sh"
sudo chown root:root /etc/systemd/system/pifi_*.service
sudo chmod 644 /etc/systemd/system/pifi_*.service
sudo systemctl enable /etc/systemd/system/pifi_*.service
sudo systemctl daemon-reload
sudo systemctl restart $(ls /etc/systemd/system/pifi_*.service | cut -d'/' -f5)

# setup youtube-dl update cron
sudo "$BASE_DIR/install/pifi_cron.sh"
sudo chown root:root /etc/cron.d/pifi
sudo chmod 644 /etc/cron.d/pifi

# Update database schema (if necessary)
sudo "$BASE_DIR"/utils/make_db

# build the web app
npm run build --prefix "$BASE_DIR"/app

# Set the hostname. Allows sshing and hitting the pifi webpage via "pifi.local"
# See: https://www.raspberrypi.org/documentation/remote-access/ip-address.md "Resolving raspberrypi.local with mDNS"
if [[ $(cat /etc/hostname) != pifi ]]; then
  echo "pifi" | sudo tee /etc/hostname >/dev/null 2>&1
  sudo sed -i -E 's/(127\.0\.1\.1\s+)[^ ]+/\1pifi/g' /etc/hosts
  is_restart_required=true
fi

if [ "$is_restart_required" = true ] ; then
    echo "Restarting..."
    sudo shutdown -r now
fi
