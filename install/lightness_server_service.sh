#!/bin/bash
# creates the server service file
BASE_DIR="$(dirname "$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )")"
cat <<-EOF | sudo tee /etc/systemd/system/lightness_server.service >/dev/null
[Unit]
Description=lightness server
After=network-online.target
Wants=network-online.target

[Service]
# Command to execute when the service is started
ExecStart=$BASE_DIR/server
Restart=on-failure
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=LIGHTNESS_SERVER

[Install]
WantedBy=multi-user.target
EOF
