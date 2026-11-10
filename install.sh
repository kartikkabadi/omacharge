#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if [[ ${EUID} == 0 ]]; then
  echo 'Run install.sh as your desktop user; setup requests authentication when needed.' >&2
  exit 1
fi
if [[ $# -gt 1 || ( $# == 1 && $1 != --skip-backend ) ]]; then
  echo 'Usage: ./install.sh [--skip-backend]' >&2
  exit 2
fi
command -v omarchy >/dev/null
command -v python3 >/dev/null
omarchy plugin validate "$PWD"
if [[ ${1:-} != --skip-backend ]]; then
  python3 client.py setup
fi
# Stage a complete plugin before exposing its manifest to the shell watcher.
python3 - <<'PY'
from datetime import datetime
from pathlib import Path
import os
import shutil
import tempfile

source = Path.cwd()
parent = Path.home() / '.config/omarchy/plugins'
parent.mkdir(parents=True, exist_ok=True)
target = parent / 'community.battery-care'
if target.resolve() == source.resolve():
    raise SystemExit(0)
if target.is_symlink():
    raise SystemExit('Refusing to replace a symlinked plugin.')
stage = Path(tempfile.mkdtemp(prefix='.battery-care-stage-', dir=parent))
try:
    for item in source.iterdir():
        if item.name in ('.git', '__pycache__'):
            continue
        if item.is_dir():
            shutil.copytree(item, stage / item.name, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        else:
            shutil.copy2(item, stage / item.name)
    if target.exists():
        backup_dir = Path.home() / '.local/state/omarchy-battery-care/backups'
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup = backup_dir / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        target.rename(backup)
    os.replace(stage, target)
finally:
    if stage.exists():
        shutil.rmtree(stage)
PY
omarchy-shell shell rescanPlugins
# Discovery is asynchronous. Wait for this specific manifest, not a fixed delay.
for ((attempt=0; attempt<60; attempt++)); do
  if omarchy plugin list --json | python3 -c 'import json,sys; sys.exit(0 if any(p["id"]=="community.battery-care" for p in json.load(sys.stdin)) else 1)'; then
    python3 - <<'BACKUP'
from datetime import datetime
from pathlib import Path
import shutil
source=Path.home()/'.config/omarchy/shell.json'
if source.exists():
    directory=Path.home()/'.local/state/omarchy-battery-care/backups'
    directory.mkdir(parents=True,exist_ok=True)
    shutil.copy2(source,directory/('shell-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.json'))
BACKUP
    # Restore any existing power-panel clone first, then replace that same slot.
    omarchy plugin enable omarchy.power
    omarchy plugin enable community.battery-care
    # Flush old QML components as well as refreshing the manifest on updates.
    omarchy restart shell
    echo 'Battery Care is installed in the existing battery position.'
    exit 0
  fi
  sleep 0.1
done
echo 'Plugin files are installed, but discovery timed out. Run: omarchy-shell shell rescanPlugins' >&2
exit 1
