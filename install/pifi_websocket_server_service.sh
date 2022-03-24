#!/usr/bin/env bash
# creates the websocket server service file
BASE_DIR="$(dirname "$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )")"
cat <<-EOF | sudo tee /etc/systemd/system/pifi_websocket_server.service >/dev/null
[Unit]
Description=pifi websocket server
After=network-online.target
Wants=network-online.target

[Service]
Environment=HOME=/root
# Command to execute when the service is started
ExecStart=$BASE_DIR/bin/websocket_server
Restart=on-failure
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=PIFI_WEBSOCKET_SERVER

[Install]
WantedBy=multi-user.target
EOF
