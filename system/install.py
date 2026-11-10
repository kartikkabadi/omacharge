#!/usr/bin/python3 -I
# SPDX-License-Identifier: MIT
"""Install/remove only Battery Care's root-owned backend and event hooks."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

SOURCE = Path(__file__).resolve().parent.parent
FILES = {
    'backend.py': ('/usr/local/libexec/omarchy-battery-care', 0o755),
    'system/omarchy-battery-care.service': ('/etc/systemd/system/omarchy-battery-care.service', 0o644),
    'system/95-omarchy-battery-care.rules': ('/etc/udev/rules.d/95-omarchy-battery-care.rules', 0o644),
    'system/sleep-hook': ('/usr/lib/systemd/system-sleep/omarchy-battery-care', 0o755),
    'system/org.omarchy.community.battery-care.policy': ('/usr/share/polkit-1/actions/org.omarchy.community.battery-care.policy', 0o644),
}


def validate_destination(path):
    # Check every destination before stopping services or replacing any files.
    for parent in (path.parent, *path.parent.parents):
        if parent.is_symlink():
            raise RuntimeError(f'Refusing a symlinked installation directory: {parent}')
        if parent.exists():
            info = parent.stat()
            if not parent.is_dir() or info.st_uid != 0 or info.st_mode & 0o022:
                raise RuntimeError(f'Installation directory is not protected: {parent}')
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise RuntimeError(f'Refusing a non-regular installation target: {path}')


def main():
    if os.geteuid() != 0 or sys.argv[1:] not in (['install'], ['remove']):
        sys.exit('Usage (administrator): install.py install|remove')
    removing = sys.argv[1] == 'remove'
    # Validate the complete payload before writing anything.
    payload = {}
    if not removing:
        for source, (destination, mode) in FILES.items():
            data = (SOURCE / source).read_bytes()
            if len(data) > 200000:
                sys.exit('Unexpectedly large installer payload.')
            payload[destination] = data, mode
    for destination, mode in FILES.values():
        validate_destination(Path(destination))
    if removing:
        loaded = subprocess.run(['/usr/bin/systemctl', 'show', '--property=LoadState', '--value', 'omarchy-battery-care.service'],
                                check=True, capture_output=True, text=True).stdout.strip()
        if loaded != 'not-found':
            subprocess.run(['/usr/bin/systemctl', 'disable', '--now', 'omarchy-battery-care.service'], check=True)
    for source, (destination, mode) in FILES.items():
        path = Path(destination)
        if removing:
            path.unlink(missing_ok=True)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = None
        try:
            with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.battery-care-', delete=False) as stream:
                temp = stream.name
                os.fchmod(stream.fileno(), mode)
                stream.write(payload[destination][0])
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp, path)
        finally:
            if temp and os.path.exists(temp):
                os.unlink(temp)
    subprocess.run(['/usr/bin/systemctl', 'daemon-reload'], check=True)
    subprocess.run(['/usr/bin/udevadm', 'control', '--reload-rules'], check=True)
    if not removing:
        subprocess.run(['/usr/bin/systemctl', 'enable', 'omarchy-battery-care.service'], check=True)
        # Adopt only an already-active Asahi setting; installing never changes charge limits.
        subprocess.run(['/usr/local/libexec/omarchy-battery-care', 'adopt-asahi'], check=True, stdout=subprocess.DEVNULL)
    print(json.dumps({'installed': not removing, 'settingsPreserved': True}))


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        sys.exit(str(error))
