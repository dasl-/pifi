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

# generate loading screens
if [ ! -f /home/pi/lightness/loading_screen_monochrome.npy ]; then
    /home/pi/lightness/utils/img_to_led --image /home/pi/lightness/utils/loading_screen_monochrome.jpg --display-width $display_width --display-height $display_height --output-file /home/pi/lightness/loading_screen --color-mode monochrome
fi
if [ ! -f /home/pi/lightness/loading_screen_color.npy ]; then
    /home/pi/lightness/utils/img_to_led --image /home/pi/lightness/utils/loading_screen_color.jpg --display-width $display_width --display-height $display_height --output-file /home/pi/lightness/loading_screen --color-mode color
fi

# setup logging: syslog
sudo mkdir -p /var/log/lightness
sudo touch /var/log/lightness/video.log /var/log/lightness/server.log /var/log/lightness/queue.log
sudo cp /home/pi/lightness/install/*_syslog.conf /etc/rsyslog.d
sudo systemctl restart rsyslog

# setup logging: logrotate
sudo cp /home/pi/lightness/install/lightness_logrotate /etc/logrotate.d
sudo chown root:root /etc/logrotate.d/lightness_logrotate
sudo chmod 644 /etc/logrotate.d/lightness_logrotate

# setup systemd services
sudo cp /home/pi/lightness/install/*.service /etc/systemd/system
sudo chown root:root /etc/systemd/system/lightness_*.service
sudo chmod 644 /etc/systemd/system/lightness_*.service
sudo systemctl enable /etc/systemd/system/lightness_*.service
sudo systemctl daemon-reload
sudo systemctl restart $(ls /etc/systemd/system/lightness_*.service | cut -d'/' -f5)

# build the web app
sudo npm run build --prefix /home/pi/lightness/app
