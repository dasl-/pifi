### Python development environment

pifi's Python dependencies are managed with [uv](https://docs.astral.sh/uv/),
pinned by `pyproject.toml` / `uv.lock`. Set up a local dev environment once:

1. Install uv: https://docs.astral.sh/uv/getting-started/installation/
2. Create the virtualenv (`.venv`) with all runtime + dev dependencies:
   `./install/install_dev_dependencies.sh` (this just runs `uv sync`).

Then run pifi commands and tooling through the venv with `uv run`:

```
uv run ./bin/server      # run a pifi entrypoint
uv run pytest tests/     # run the test suite (see ../tests/README.md)
uv run pyright           # type-check; enforced by tests/test_pyright.py
```

`uv run` puts `.venv` first on PATH, so scripts that shell out to `python3`
use the venv interpreter too. To reconcile the pyright suppression baseline
after type changes: `uv run utils/pyright_suppress.py`.

### Setting up sublime via rmate:
1. `sudo wget -O /usr/local/bin/subl https://raw.github.com/aurora/rmate/master/rmate`
1. `sudo chmod a+x /usr/local/bin/subl`

### Setting up sublime with sftp:
This is another option. This rsync script will be useful to sync the remote pi copy with your local copy. Run it from your local machine. Modify as appropriate for your directory structure, IP address etc.:
```
rsync -avz --delete --exclude '*.swp' --exclude '.git' --exclude '.tags' --exclude '*.jar' \
  --exclude '*.class' --exclude '*.md5' --exclude '*.sha1' --exclude '*.zip' \
  --exclude '.project' --exclude '.DS_Store' --exclude '*.gem' --exclude '*.gz' \
  --exclude 'vendor/gems' --exclude '*.a' --exclude '*.so' --exclude '*.so.*' \
  --exclude '*.la' --exclude 'sftp-config.json' --exclude '.idea' --exclude '*.db' \
  --exclude '*.rpm' --exclude '*.sqlite' --exclude '*.tsv' --exclude 'node_modules/' --exclude 'build/' \
  --exclude 'data/' --exclude '__pycache__/' --exclude '*.npy' \
  pi@192.168.1.100:~/development/ ~/pi/development
```

### Starting the development server
From your local checkout directory:
```
$ npm start --prefix app
```
