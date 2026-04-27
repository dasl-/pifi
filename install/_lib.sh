# Shared definitions sourced by install_dependencies.sh (Pi) and
# install_dev_dependencies.sh (dev machine). Not directly executable.
#
# DEV_TOOLS lists uv-installed tools that should exist on both Pi and dev
# machines. Each entry is a uv install spec (name==version) so adding a new
# tool means appending one line — both installers pick it up.
#
# These tools are only invoked by humans (e.g. `pyright` over SSH on the Pi),
# never by pifi runtime code, so a user-local `uv tool install` is fine —
# no sudo, no system-wide UV_* layout, no /usr/bin symlink. (Contrast with
# yt-dlp, which is shelled out to raw via subprocess, hence the heavier
# install pattern in utils/update_yt-dlp.sh.)

# shellcheck disable=SC2034
DEV_TOOLS=(
    'pyright==1.1.409'
)

installDevTools(){
    if ! command -v uv >/dev/null 2>&1; then
        echo "uv is required. Install from https://docs.astral.sh/uv/getting-started/installation/" >&2
        return 1
    fi

    for tool in "${DEV_TOOLS[@]}"; do
        echo "Installing ${tool}..."
        uv tool install --upgrade "${tool}"
    done
}
