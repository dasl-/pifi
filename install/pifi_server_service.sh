#!/usr/bin/env bash
# creates the server service file
BASE_DIR="$(dirname "$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )")"
cat <<-EOF | sudo tee /etc/systemd/system/pifi_server.service >/dev/null
[Unit]
Description=pifi server
After=network-online.target
Wants=network-online.target

[Service]
Environment=HOME=/root
# Add venv to path so shebangs and subprocess calls resolve to the venv interpreter, not system python.
# To avoid overhead and possible dependency resolution related network access, don't use `uv` here.
ExecStart=/usr/bin/bash -c 'PATH=$BASE_DIR/.venv/bin:\$PATH exec $BASE_DIR/bin/server'
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF
