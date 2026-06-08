#!/usr/bin/env bash
#
# Set up a local dev environment for pifi on a Mac or Linux machine.
# Creates a uv-managed virtualenv (.venv) with all runtime + dev dependencies,
# pinned by uv.lock. NOT for provisioning a Pi — see install_dependencies.sh.
#
# After this, run pifi commands through the venv with `uv run`, e.g.:
#   uv run ./bin/server
#   uv run pytest tests/
#   uv run pyright

set -euo pipefail

BASE_DIR="$(dirname "$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )")"

if ! command -v uv >/dev/null 2>&1; then
    echo "uv is required. Install from https://docs.astral.sh/uv/getting-started/installation/" >&2
    exit 1
fi

echo "Creating .venv and installing dependencies (pinned by uv.lock)..."
pushd "$BASE_DIR"
uv sync
popd

echo
echo "Done. Run pifi commands through the venv with 'uv run', e.g.:"
echo "  uv run ./bin/server"
echo "  uv run pytest tests/"
echo "  uv run pyright"
