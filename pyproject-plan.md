# Plan: single-source, pinned, reproducible dependencies via `pyproject.toml` + `uv`

## Goal

- Define the project's Python dependencies in **one place** — no list duplicated between `install_dependencies.sh` and a requirements file.
- Pinned, reproducible installs via a committed `uv.lock`.
- A real dev environment isolated from system python, so a Homebrew/OS python bump can't orphan deps (the breakage that prompted this).
- Keep the door open to using the same source on the Pi, without forcing a Pi deployment change now.

## Single source of truth: `pyproject.toml` (+ `uv.lock`)

Every Python dependency lives in `pyproject.toml`. `uv.lock` (committed) holds the resolved pins. Both the dev box and the Pi installer read from this file; neither re-lists packages.

```toml
[project]
name = "pifi"
requires-python = "==3.13.*"          # matches the Pi (3.13.5)
dependencies = [
    "numpy", "requests", "pillow",     # in the list — dev needs them; Pi gets them from apt (see [tool.pifi])
    "pyjson5", "pygame", "pytz", "websockets",
    "soco", "syncedlyrics", "underground", "typing-extensions",
    "simpleaudio @ git+https://github.com/cexen/py-simple-audio.git",
]

[project.optional-dependencies]       # hardware LED drivers — opt-in, Pi-only
apa102  = ["apa102-pi"]
ws2812b = ["rpi-ws281x"]
# rgbmatrix is NOT here — it is a source build (git clone + make); stays special-cased.

[dependency-groups]                   # PEP 735 — dev tooling, never shipped
dev = ["pyright==1.1.409", "pytest"]

[tool.pifi]
# On the Pi these come from apt (prebuilt, distro BLAS), not pip. The Pi
# installer apt-installs them and excludes them from the uv install. Listing
# them here keeps the apt-exception in the same single source — each package
# name still appears exactly once.
apt-provided = ["numpy", "requests", "pillow"]
```

This also subsumes the pinned tool list currently in `install/_lib.sh` (`pyright==1.1.409` moves into the `dev` group), so there's still one place for it.

## Settled decisions

- **A — keep apt for numpy/requests/pillow on the Pi** (prebuilt, avoids slow ARM source builds, distro BLAS). They stay in the `dependencies` list (dev needs them) but are tagged `[tool.pifi] apt-provided` so the Pi sources them from apt and excludes them from the uv install. No package name written twice.
- **C — pin python 3.13** to match the Pi's 3.13.5. `requires-python = "==3.13.*"` plus a `.python-version` file (`3.13`) so `uv venv` builds the dev venv on 3.13. This is what permanently kills the "Homebrew bumped python and orphaned my deps" failure.
- **Launch convention — `uv run`.** Run pifi scripts on the dev box via `uv run` (e.g. `uv run ./bin/queue`, `uv run pytest tests/`). uv discovers the project venv and puts it first on PATH, so the scripts' `#!/usr/bin/env python3` shebang resolves to the venv python. Shebangs stay `#!/usr/bin/env python3` (portable — unchanged on the Pi, which runs system python via systemd). Running `uv run pytest` also fixes the preview subprocess tests, since the child `python3` inherits the venv PATH.

## Dependency inventory → new home

| Current location | Packages | New home |
|---|---|---|
| Pi apt (`python3-*`) | numpy, requests, pillow | `dependencies` + `[tool.pifi] apt-provided` (apt on Pi, pip on dev) |
| Pi pip core | pytz, websockets, pygame, pyjson5, soco, syncedlyrics, underground, typing-extensions, py-simple-audio (git) | `dependencies` |
| Pi pip, conditional | apa102-pi / rpi-ws281x | `optional-dependencies` extras |
| Pi source build | rgbmatrix | unchanged — special-cased in `installLedDriverRgbMatrix` |
| `_lib.sh` `DEV_TOOLS` | pyright | `dependency-groups.dev` |
| Pi apt, non-Python | ffmpeg, sqlite3, mbuffer, libsdl2-*, parallel, libopenblas, node, deno | unchanged — stay apt (not Python deps) |

## How each consumer uses the single source

- **Dev box** (`install_dev_dependencies.sh`): `uv sync` → builds `.venv` on python 3.13 from the lock, installs core + `dev` group (skips the Pi-only hardware extras). pyright auto-detects `.venv`. Replaces the current `uv tool install pyright`. Daily use: `uv run <script>` / `uv run pytest`.
- **Pi** (`install_dependencies.sh`):
  - `apt install` the `[tool.pifi] apt-provided` set (pip-name → apt-name mapping: numpy→python3-numpy, requests→python3-requests, pillow→python3-pil) + the existing non-Python system packages.
  - Install the rest into **system python**, pinned from the lock, excluding the apt-provided set:
    `uv export --no-emit-package numpy --no-emit-package requests --no-emit-package pillow …` → install into system python.
  - Install the one hardware extra selected by `leds.driver` config (from `optional-dependencies`).
  - `rgbmatrix` stays special-cased (source build).
  - System-python deployment model unchanged — systemd services keep pointing at system `python3`.

## Phasing

1. **Phase 1 — author the single source.** Add `pyproject.toml` (deps + extras + dev group + `[tool.pifi] apt-provided`) and `.python-version`; generate and commit `uv.lock`. Purely additive, no installer changes.
2. **Phase 2 — dev box (safe, fixes current breakage).** Rewrite `install_dev_dependencies.sh` to `uv sync`. Document `uv run` workflow in README. Verify app + tests + pyright all resolve against `.venv`. No Pi involvement.
3. **Phase 3 — Pi consumes the same source (needs hardware testing).** Rewrite `updateAndInstallPackages` to apt-install the `apt-provided` set + non-Python packages, then `uv export --no-emit-package …` the rest from the lock into system python. Keep rgbmatrix special-cased; install selected LED extra. System-python deployment unchanged.
4. **Phase 4 (optional, later) — full Pi venv.** Migrate the Pi to a venv too (service files point at `.venv/bin/python`). Not needed now; door left open.

## Open question

- **Scope**: land Phase 1+2 in one PR (dev-only, safe, fixes the current breakage) and do Phase 3 as a separate Pi-tested PR? Recommended.

## Notes / risks

- `uv export --no-emit-package` is the mechanism for excluding the apt-provided set from the Pi's pip install; confirm exact flags during Phase 3.
- Reproducibility on the Pi (system python, no venv) comes from installing the lock-pinned export; verify the exact `uv`/`pip` invocation on hardware.
- Moving numpy/pillow off apt to piwheels was rejected (Decision A) — revisit only if the apt exception becomes painful.
- Keep shebangs `#!/usr/bin/env python3` everywhere — never hardcode a venv path (would break the Pi).
