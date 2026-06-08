#!/usr/bin/env bash
# creates the yt-dlp update service + timer files
BASE_DIR="$(dirname "$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )")"

# View logs via: sudo journalctl -u pifi_update_yt_dlp.service
cat <<-EOF | sudo tee /etc/systemd/system/pifi_update_yt_dlp.service >/dev/null
[Unit]
Description=pifi update yt-dlp

[Service]
Type=oneshot
ExecStart=$BASE_DIR/utils/update_yt-dlp.sh
SyslogIdentifier=update_yt_dlp
EOF

cat <<-EOF | sudo tee /etc/systemd/system/pifi_update_yt_dlp.timer >/dev/null
[Unit]
Description=pifi update yt-dlp timer

[Timer]
OnCalendar=*-*-* 09:31:00
Persistent=true

[Install]
WantedBy=timers.target
EOF
