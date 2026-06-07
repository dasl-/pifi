#!/usr/bin/env bash
#
# Set up a local dev environment for pifi on a Mac or Linux dev box.
# Creates a uv-managed virtualenv (.venv) with all runtime + dev dependencies,
# pinned by uv.lock. NOT for provisioning a Pi — see install_dependencies.sh.
#
# After this, run pifi commands through the venv with `uv run`, e.g.:
#   uv run ./bin/server
#   uv run pytest tests/
#   uv run pyright

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if ! command -v uv >/dev/null 2>&1; then
    echo "uv is required. Install from https://docs.astral.sh/uv/getting-started/installation/" >&2
    exit 1
fi

echo "Creating .venv and installing dependencies (pinned by uv.lock)..."
uv sync

echo
echo "Done. Run pifi commands through the venv with 'uv run', e.g.:"
echo "  uv run ./bin/server"
echo "  uv run pytest tests/"
echo "  uv run pyright"
