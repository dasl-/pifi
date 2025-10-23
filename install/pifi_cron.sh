#!/usr/bin/env bash
# creates the pifi cron file
BASE_DIR="$(dirname "$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )")"
cat <<-EOF | sudo tee /etc/cron.d/pifi >/dev/null
31 09 * * * root $BASE_DIR/utils/update_youtube-dl.sh
EOF
