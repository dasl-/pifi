#!/usr/bin/env bash
#
# Install dev tools needed to work on pifi locally on a Mac or Linux dev box.
# This is NOT for provisioning a Pi — see install_dependencies.sh for that.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_lib.sh
source "${SCRIPT_DIR}/_lib.sh"

installDevTools

echo
echo "Done."
