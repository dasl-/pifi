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
# Prepend the pifi venv so '#!/usr/bin/env python3' (in bin/* and the scripts
# they spawn via bash) resolves to the venv interpreter, not system python.
Environment=PATH=$BASE_DIR/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart=$BASE_DIR/bin/queue
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF
