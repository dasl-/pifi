#!/bin/bash
# creates the queue service file
BASE_DIR="$(dirname "$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )")"
cat <<-EOF | sudo tee /etc/systemd/system/lightness_queue.service >/dev/null
[Unit]
Description=lightness queue
After=network-online.target
Wants=network-online.target

[Service]
# Command to execute when the service is started
ExecStart=$BASE_DIR/queue
Restart=on-failure
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=LIGHTNESS_QUEUE

[Install]
WantedBy=multi-user.target
EOF
