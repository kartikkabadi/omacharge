#!/usr/bin/env bash
set -euo pipefail
if [[ $# -gt 1 || ( $# == 1 && $1 != --backend ) ]]; then
  echo 'Usage: ./uninstall.sh [--backend]' >&2
  exit 2
fi
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if [[ ${1:-} == --backend ]]; then
  python3 - <<'PY'
from pathlib import Path
import sys
sys.path.insert(0, str(Path.cwd()))
from client import elevate
print(elevate(['/usr/bin/python3', '-I', str(Path.cwd()/'system/install.py'), 'remove']).stdout)
PY
fi
omarchy plugin disable community.battery-care
printf '%s\n' 'Restored the standard power widget. Saved limits and current hardware settings were preserved.'
printf '%s\n' 'To remove plugin files: omarchy plugin remove community.battery-care --yes'
