#!/usr/bin/env bash
# creates the queue service file
BASE_DIR="$(dirname "$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )")"
cat <<-EOF | sudo tee /etc/systemd/system/pifi_queue.service >/dev/null
[Unit]
Description=pifi queue
After=network-online.target
Wants=network-online.target

[Service]
Environment=HOME=/root
# Command to execute when the service is started
ExecStart=$BASE_DIR/queue
Restart=on-failure
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=PIFI_QUEUE

[Install]
WantedBy=multi-user.target
EOF
