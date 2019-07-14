#!/bin/bash

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
