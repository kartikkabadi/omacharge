#!/usr/bin/python3 -I
# SPDX-License-Identifier: MIT
"""Install/remove only Omacharge's protected backend and event hooks."""
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import json
import contextlib
import fcntl
import time

SOURCE = Path(__file__).resolve().parent.parent
UNIT = 'omarchy-battery-care.service'
INSTALL_LOCK = Path('/run/lock/omarchy-battery-care-install.lock')
FILES = {
    'backend.py': ('/usr/local/libexec/omarchy-battery-care', 0o755),
    'system/omarchy-battery-care.service': ('/etc/systemd/system/omarchy-battery-care.service', 0o644),
    'system/95-omarchy-battery-care.rules': ('/etc/udev/rules.d/95-omarchy-battery-care.rules', 0o644),
    'system/sleep-hook': ('/usr/lib/systemd/system-sleep/omarchy-battery-care', 0o755),
    'system/org.omarchy.community.battery-care.policy': ('/usr/share/polkit-1/actions/org.omarchy.community.battery-care.policy', 0o644),
}
MAX_FILE_BYTES = 200000


class InstallError(RuntimeError):
    pass


def validate_destination(path):
    if path.is_symlink():
        raise InstallError(f'Refusing a symlink at {path}')
    if path.exists():
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
            raise InstallError(f'Installation file is not protected: {path}')
    for parent in (path.parent, *path.parent.parents):
        if parent.is_symlink():
            raise InstallError(f'Refusing a symlinked installation directory: {parent}')
        if parent.exists():
            info = parent.lstat()
            if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
                raise InstallError(f'Installation directory is not protected: {parent}')


def read_bounded(path):
    with path.open('rb') as stream:
        data = stream.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        raise InstallError(f'Unexpectedly large installation file: {path.name}')
    return data


def write_atomic(path, data, mode):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.battery-care-', delete=False) as stream:
            temp = stream.name
            os.fchmod(stream.fileno(), mode)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
        fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        if temp and os.path.exists(temp):
            os.unlink(temp)


def command(args, check=True):
    return subprocess.run(args, check=check, capture_output=True, text=True, timeout=25)


def install(removing=False, source=SOURCE, files=FILES):
    # Validate every source and destination before any mutation, then retain a rollback image.
    plan = []
    for name, (destination, mode) in files.items():
        path = Path(destination)
        validate_destination(path)
        previous = (read_bounded(path), stat.S_IMODE(path.stat().st_mode)) if path.exists() else None
        data = None
        if not removing:
            payload = source / name
            if payload.is_symlink() or not payload.is_file():
                raise InstallError(f'Installation payload is not a regular file: {name}')
            data = read_bounded(payload)
        plan.append((path, data, mode, previous))
    was_enabled = command(['/usr/bin/systemctl', 'is-enabled', '--quiet', UNIT], check=False).returncode == 0
    was_active = removing and command(['/usr/bin/systemctl', 'is-active', '--quiet', UNIT], check=False).returncode == 0
    touched = []
    enable_attempted = False
    try:
        if removing and (was_enabled or any(path.name == UNIT and previous for path, _, _, previous in plan)):
            command(['/usr/bin/systemctl', 'disable', '--now', UNIT])
        for path, data, mode, previous in plan:
            touched.append((path, previous))
            if removing:
                path.unlink(missing_ok=True)
            else:
                write_atomic(path, data, mode)
        command(['/usr/bin/systemctl', 'daemon-reload'])
        command(['/usr/bin/udevadm', 'control', '--reload-rules'])
        if not removing:
            enable_attempted = True
            command(['/usr/bin/systemctl', 'enable', UNIT])
            # Adopts an already-active setting; installation never selects a different limit.
            command(['/usr/local/libexec/omarchy-battery-care', 'adopt-asahi'])
    except (OSError, InstallError, subprocess.SubprocessError) as error:
        rollback_errors = []
        def recover(args):
            try:
                command(args)
            except (OSError, subprocess.SubprocessError) as issue:
                rollback_errors.append(str(issue))
        if not was_enabled and enable_attempted:
            recover(['/usr/bin/systemctl', 'disable', UNIT])
        for path, previous in reversed(touched):
            try:
                if previous is None:
                    path.unlink(missing_ok=True)
                else:
                    write_atomic(path, *previous)
            except OSError as issue:
                rollback_errors.append(str(issue))
        recover(['/usr/bin/systemctl', 'daemon-reload'])
        recover(['/usr/bin/udevadm', 'control', '--reload-rules'])
        if was_enabled:
            recover(['/usr/bin/systemctl', 'enable', UNIT])
        if was_active:
            recover(['/usr/bin/systemctl', 'start', UNIT])
        details = ' Previous installed files were restored.' if not rollback_errors else ' Rollback also failed: ' + '; '.join(rollback_errors)[:800]
        raise InstallError(f'Installation could not complete: {error}.{details}') from error
    return {'installed': not removing, 'settingsPreserved': True}


@contextlib.contextmanager
def installation_lock():
    fd = os.open(INSTALL_LOCK, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(fd)
        if info.st_uid != 0 or not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077:
            raise InstallError('The installer lock is not root-owned.')
        deadline = time.monotonic() + 8
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise InstallError('Another Omacharge installation is running. Try again when it finishes.')
                time.sleep(0.05)
        yield
    finally:
        os.close(fd)


def main():
    if os.geteuid() != 0 or sys.argv[1:] not in (['install'], ['remove']):
        print('Usage (administrator): install.py install|remove', file=sys.stderr)
        return 2
    try:
        with installation_lock():
            result = install(removing=sys.argv[1] == 'remove')
        print(json.dumps(result))
        return 0
    except (OSError, InstallError, subprocess.SubprocessError) as error:
        print(str(error)[:2000], file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
