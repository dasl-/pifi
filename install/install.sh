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

# setup logging: syslog
sudo mkdir -p /var/log/lightness
sudo touch /var/log/lightness/server.log /var/log/lightness/queue.log
sudo cp "$BASE_DIR"/install/*_syslog.conf /etc/rsyslog.d
sudo systemctl restart rsyslog

# clean up deprecated stuff:
# todo: delete this eventually
sudo rm -rf /var/log/lightness/video.log*

# setup logging: logrotate
sudo cp "$BASE_DIR"/install/lightness_logrotate /etc/logrotate.d
sudo chown root:root /etc/logrotate.d/lightness_logrotate
sudo chmod 644 /etc/logrotate.d/lightness_logrotate

# setup systemd services
sudo $BASE_DIR/install/lightness_queue_service.sh
sudo $BASE_DIR/install/lightness_server_service.sh
sudo chown root:root /etc/systemd/system/lightness_*.service
sudo chmod 644 /etc/systemd/system/lightness_*.service
sudo systemctl enable /etc/systemd/system/lightness_*.service
sudo systemctl daemon-reload
sudo systemctl restart $(ls /etc/systemd/system/lightness_*.service | cut -d'/' -f5)

# build the web app
sudo npm run build --prefix "$BASE_DIR"/app
