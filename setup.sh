#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
# The Python bridge tries sudo -n, then requests desktop authentication if needed.
python3 client.py setup
