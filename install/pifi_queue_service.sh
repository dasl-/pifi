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
# Prepend the pifi venv to PATH so '#!/usr/bin/env python3' (in bin/* and the
# scripts they spawn) resolves to the venv interpreter, not system python.
# A bash -c wrapper (rather than 'uv run', which adds overhead and may hit the
# network for dep resolution) lets \$PATH pick up systemd's default service PATH
# instead of hardcoding it; exec replaces bash so the service stays MainPID.
ExecStart=/usr/bin/bash -c 'PATH=$BASE_DIR/.venv/bin:\$PATH exec $BASE_DIR/bin/queue'
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF
