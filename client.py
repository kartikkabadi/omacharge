#!/usr/bin/python3
# SPDX-License-Identifier: MIT
"""Unprivileged UI bridge. Elevate only the installed, root-owned helper."""
import json
import os
from pathlib import Path
import subprocess
import sys

from backend import HELPER, VERSION, trusted_executable


def run(command, timeout=15):
    return subprocess.run(command, capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=timeout,
                          env={**os.environ, 'LC_ALL': 'C'})


def needs_auth(result):
    return result.returncode == 1 and 'sudo:' in result.stderr.lower() and any(
        phrase in result.stderr.lower() for phrase in ('a password is required', 'a terminal is required', 'no askpass program specified'))


def elevate(command):
    result = run(['/usr/bin/sudo', '-n', '--', *command], timeout=120)
    if needs_auth(result):
        result = run(['/usr/bin/pkexec', *command], timeout=180)
    # Never retry a helper error: it may have already written part of a selection.
    if result.returncode:
        if result.returncode in (126, 127):
            raise RuntimeError('Authentication was cancelled or denied.')
        raise RuntimeError(result.stderr.strip()[:2000] or 'The operation failed.')
    return result


def main():
    args = sys.argv[1:]
    try:
        if args == ['setup']:
            installer = str(Path(__file__).resolve().parent / 'system' / 'install.py')
            elevate(['/usr/bin/python3', '-I', installer, 'install'])
            args = ['status']
        installed = trusted_executable(HELPER)
        if args == ['status']:
            data = None
            if installed:
                result = run([str(HELPER), 'status'], timeout=30)
                if result.returncode == 0:
                    try:
                        candidate = json.loads(result.stdout)
                        if isinstance(candidate, dict) and candidate.get('version') == VERSION:
                            data = candidate
                    except ValueError:
                        pass
            # A broken/older helper cannot hide new frontend capabilities or its setup button.
            if data is None:
                command = ['/usr/bin/python3', '-I', str(Path(__file__).with_name('backend.py')), 'status']
                result = run(command, timeout=30)
                if result.returncode:
                    raise RuntimeError(result.stderr.strip()[:2000] or 'Battery status is unavailable.')
                data = json.loads(result.stdout)
                installed = False
            if not isinstance(data, dict):
                raise RuntimeError('The battery helper returned an invalid status.')
            data['installed'] = installed
            print(json.dumps(data))
            return 0
        if len(args) in (3, 4) and args[0] == 'set':
            if not installed:
                raise RuntimeError('Finish backend setup before changing a limit.')
            result = run([str(HELPER), 'status'], timeout=30)
            if result.returncode:
                raise RuntimeError(result.stderr.strip()[:2000] or 'The battery helper is unavailable.')
            status = json.loads(result.stdout)
            if not isinstance(status, dict) or status.get('version') != VERSION:
                raise RuntimeError('Update the backend using Finish setup before changing a limit.')
            # Backend rediscovery and validation remain authoritative.
            print(elevate([str(HELPER), *args]).stdout.strip())
            return 0
        raise RuntimeError('Usage: client.py status | setup | set DEVICE END [START]')
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(str(error)[:2000], file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
