#!/usr/bin/python3 -I
# SPDX-License-Identifier: MIT
"""Capability-based battery charge control. No CLI-supplied filesystem paths."""
import argparse
import contextlib
from dataclasses import dataclass, field
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile

VERSION = '0.1.1'
HELPER = Path('/usr/local/libexec/omarchy-battery-care')
CONFIG = Path('/etc/omarchy-battery-care.json')
LOCK = Path('/run/lock/omarchy-battery-care.lock')
FRAMEWORK_TOOL = Path('/usr/bin/framework_tool')
MAX_CONFIG_BYTES = 65536


class CareError(RuntimeError):
    pass


def trusted_executable(path):
    try:
        info = path.lstat()
        return stat.S_ISREG(info.st_mode) and info.st_uid == 0 and not info.st_mode & 0o022 and os.access(path, os.X_OK)
    except OSError:
        return False


def atomic_write(path, text):
    """Save a root-owned setting without following destination symlinks."""
    if path.is_symlink():
        raise CareError(f'Refusing a symbolic link at {path}.')
    temp = None
    try:
        with tempfile.NamedTemporaryFile('w', dir=path.parent, prefix='.battery-care-', delete=False) as stream:
            temp = stream.name
            os.fchmod(stream.fileno(), 0o644)
            stream.write(text)
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


@dataclass
class Control:
    id: str
    driver: str
    path: str
    label: str
    kind: str = 'threshold'
    stop_values: list = field(default_factory=lambda: list(range(1, 101)))
    start_values: list = field(default_factory=list)
    end_file: str = 'charge_control_end_threshold'
    start_file: str = 'charge_control_start_threshold'
    mode_file: str = ''
    derived: str = ''
    gap: int = 1
    full_start: int = 95
    shared: bool = False
    warning: str = ''

    def default_start(self, end):
        if self.derived == 'apple':
            return 75 if end == 80 else 100
        if self.derived == 'msi':
            return end - 10
        if not self.start_values:
            return None
        target = self.full_start if end == 100 else end - 5
        allowed = [v for v in self.start_values if v <= end - self.gap]
        if not allowed:
            raise CareError('No valid restart threshold exists for this maximum.')
        return min(allowed, key=lambda v: abs(v - target))


class Engine:
    """The alternate roots exist only for import-based tests, never CLI flags."""
    def __init__(self, sysroot=Path('/sys'), config=CONFIG, asahi=Path('/etc/udev/macsmc-battery.conf')):
        self.root = Path(sysroot).resolve()
        self.config = Path(config)
        self.asahi = Path(asahi)

    def path(self, relative):
        path = self.root / relative
        if not path.resolve().is_relative_to(self.root):
            raise CareError('A device path escaped sysfs.')
        return path

    def read(self, relative, default=''):
        try:
            with self.path(relative).open() as stream:
                return stream.read(4096).strip()
        except OSError:
            return default

    def number(self, relative):
        value = self.read(relative)
        return int(value) if re.fullmatch(r'\d{1,3}', value) and 0 <= int(value) <= 100 else None

    def exists(self, relative):
        return self.path(relative).is_file()

    def module(self, name):
        return self.path('module/' + name).is_dir()

    def write(self, relative, value):
        # /sys is kernel-owned; user input can select only rediscovered control IDs.
        path = self.path(relative)
        if not path.is_file():
            raise CareError('The battery was removed or its control disappeared.')
        with path.open('w') as stream:
            stream.write(str(value) + '\n')

    def machine(self):
        vendor = self.read('class/dmi/id/sys_vendor')
        model = self.read('class/dmi/id/product_name')
        if not vendor and not model:
            model = self.read('firmware/devicetree/base/model').replace('\0', '')
            vendor = 'Apple' if model.startswith('Apple ') else ''
        return {'vendor': vendor[:100], 'model': model[:160]}

    def identity(self, control):
        raw = json.dumps([self.machine(), control.driver, control.id], sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()

    def batteries(self):
        result = []
        for path in sorted(self.path('class/power_supply').glob('*')):
            base = f'class/power_supply/{path.name}'
            if self.read(base + '/type') != 'Battery' or self.read(base + '/scope') == 'Device':
                continue
            if self.read(base + '/present', '1') != '1':
                continue
            if not re.fullmatch(r'[A-Za-z0-9_.:-]{1,80}', path.name):
                continue
            result.append({'id': path.name, 'capacity': self.number(base + '/capacity'),
                           'status': self.read(base + '/status', 'Unknown')[:40]})
        return result[:16]

    def available(self, base, kind):
        raw = self.read(base + f'/charge_control_{kind}_available_thresholds')
        if not raw:
            return []
        if not re.fullmatch(r'\d{1,3}(?:\s+\d{1,3}){0,100}', raw):
            return []
        values = sorted(set(map(int, raw.split())))
        return values if all(0 <= v <= 100 for v in values) else []

    def discover(self):
        batteries = self.batteries()
        if not batteries:
            return []
        result = []
        # These platform controls affect all batteries and must be written once.
        platforms = [
            ('huawei', 'devices/platform/huawei-wmi/charge_control_thresholds', 'pair', list(range(1, 101)), list(range(0, 100))),
            ('lenovo-legacy', 'bus/platform/drivers/ideapad_acpi/VPC2004:00/conservation_mode', 'toggle', [0, 1], []),
            ('samsung', 'devices/platform/samsung/battery_life_extender', 'toggle', [0, 1], []),
            ('sony', 'devices/platform/sony-laptop/battery_care_limiter', 'threshold', [50, 80, 100], []),
        ]
        for driver, path, kind, stops, starts in platforms:
            if self.exists(path):
                return [Control('platform-' + driver, driver, str(Path(path).parent), 'All batteries',
                                kind=kind, stop_values=stops, start_values=starts,
                                end_file=Path(path).name, start_file='', shared=True,
                                full_start=0 if driver == 'huawei' else 95,
                                warning='The conservation percentage is fixed by the firmware and cannot be read.' if driver == 'lenovo-legacy' else '')]
        cros = any(p.name.startswith('cros-charge-control.') and (p / 'driver').is_symlink()
                   and (p / 'driver').resolve().name == 'cros-charge-control'
                   for p in self.path('bus/platform/devices').glob('*'))
        vendor = self.machine()['vendor'].lower()
        for battery in batteries:
            name = battery['id']
            base = 'class/power_supply/' + name
            end = base + '/charge_control_end_threshold'
            start = base + '/charge_control_start_threshold'
            has_start = self.number(start) is not None
            driver = ''
            kwargs = {}
            if name == 'macsmc-battery' and self.exists(end):
                driver = 'apple'
                kwargs = dict(stop_values=[80, 100], derived='apple')
            elif self.path('bus/platform/drivers/ideapad_acpi').is_dir() and 'Long_Life' in self.read(base + '/charge_types'):
                driver = 'lenovo'
                kwargs = dict(kind='charge-types', stop_values=[0, 1], end_file='charge_types', shared=True,
                              warning='The conservation percentage is fixed by the firmware and cannot be read.')
            elif not self.exists(end):
                legacy = 'devices/platform/smapi/' + name
                if self.exists(legacy + '/stop_charge_thresh'):
                    driver = 'thinkpad-legacy'
                    base = legacy
                    kwargs = dict(stop_values=list(range(6, 101)), start_values=list(range(2, 97)),
                                  end_file='stop_charge_thresh', start_file='start_charge_thresh', full_start=96)
                else:
                    continue
            elif self.module('thinkpad_acpi'):
                driver = 'thinkpad'
                kwargs = dict(start_values=list(range(0, 100)) if has_start else [], full_start=96,
                              warning='Some ThinkPad firmware reports thresholds slightly differently; mismatches are not saved.')
            elif self.module('dell_laptop'):
                driver = 'dell'
                if not has_start or not self.exists(base + '/charge_types'):
                    continue
                kwargs = dict(stop_values=list(range(55, 101)), start_values=list(range(50, 96)), gap=5, mode_file='charge_types')
            elif self.module('msi_ec'):
                driver = 'msi'
                kwargs = dict(stop_values=list(range(10, 101)), derived='msi')
            elif self.module('lg_laptop') or self.path('devices/platform/lg-laptop').is_dir():
                driver = 'lg'
                kwargs = dict(stop_values=[80, 100])
            elif self.module('toshiba_acpi'):
                driver = 'toshiba'
                kwargs = dict(stop_values=[80, 100])
            elif self.module('system76_acpi'):
                driver = 'system76'
                kwargs = dict(start_values=list(range(0, 100)) if has_start else [], full_start=90)
            elif cros:
                driver = 'cros-ec'
                kwargs = dict(start_values=list(range(0, 100)) if has_start else [], full_start=0)
            elif vendor == 'tuxedo' and self.available(base, 'end'):
                driver = 'tuxedo'
                starts = self.available(base, 'start')
                if not starts or not has_start or not self.exists(base + '/charge_type'):
                    continue
                kwargs = dict(stop_values=self.available(base, 'end'), start_values=starts, mode_file='charge_type')
            elif self.module('asus_wmi'):
                driver = 'asus'
                kwargs = dict(warning='The driver reports the requested limit; some firmware accepts only specific percentages.')
            else:
                # The ABI permits rounded values. Do not guess ranges for unknown drivers.
                values = self.available(base, 'end')
                if not values:
                    continue
                if has_start and not self.available(base, 'start'):
                    # A readable restart control needs a documented range too.
                    continue
                driver = 'sysfs-advertised'
                kwargs = dict(stop_values=values, start_values=self.available(base, 'start') if has_start else [])
            control = Control(name, driver, base, name, **kwargs)
            if control.start_values:
                control.stop_values = [end for end in control.stop_values
                                       if any(start <= end - control.gap for start in control.start_values)]
                if not control.stop_values:
                    continue
            result.append(control)
            if kwargs.get('shared'):
                return result[-1:]
        # Wilco has a separate charger control, alongside BAT0/BAT1 telemetry.
        wilco = 'class/power_supply/wilco-charger'
        if self.module('wilco_charger') and self.exists(wilco + '/charge_control_end_threshold'):
            return [Control('platform-wilco', 'wilco-ec', wilco, 'All batteries', shared=True,
                            stop_values=list(range(55, 101)), start_values=list(range(50, 96)), gap=5, mode_file='charge_type')]
        if not result and vendor == 'framework' and trusted_executable(FRAMEWORK_TOOL):
            result.append(Control('platform-framework', 'framework-tool', '', 'All batteries', kind='framework',
                                  shared=True, stop_values=list(range(25, 101)),
                                  warning='Uses framework_tool because native charge-control sysfs is unavailable. Reading may require authentication.'))
        return result

    def framework(self, end=None):
        if not trusted_executable(FRAMEWORK_TOOL):
            raise CareError('Install a root-owned /usr/bin/framework_tool for this hardware.')
        args = [str(FRAMEWORK_TOOL), '--charge-limit']
        if end is not None:
            args.append(str(end))
        proc = subprocess.run(args, capture_output=True, text=True, timeout=12, env={'PATH': '/usr/bin:/bin', 'LC_ALL': 'C'})
        match = re.search(r'^Minimum (\d{1,3})%, Maximum (\d{1,3})%\s*$', proc.stdout, re.M)
        if proc.returncode or not match or not 0 <= int(match[1]) <= int(match[2]) <= 100:
            raise CareError('Framework could not confirm the charge limit. ' + proc.stderr[:400].strip())
        return int(match[1]), int(match[2])

    def current(self, control):
        path = control.path + '/' + control.end_file
        if control.kind == 'framework':
            try:
                _minimum, end = self.framework()
                return {'start': None, 'end': end}
            except (CareError, OSError, subprocess.SubprocessError):
                return {'start': None, 'end': None}
        if control.kind == 'pair':
            values = self.read(path).split()
            if len(values) != 2 or not all(re.fullmatch(r'\d{1,3}', v) and 0 <= int(v) <= 100 for v in values):
                return {'start': None, 'end': None}
            return {'start': int(values[0]), 'end': int(values[1])}
        if control.kind == 'charge-types':
            token = re.search(r'\[([^\]]+)\]', self.read(path))
            return {'start': None, 'end': {'Long_Life': 1, 'Standard': 0}.get(token[1] if token else '')}
        end = self.number(path)
        if control.driver == 'sony' and end == 0:
            end = 100  # The Sony ABI uses zero for a disabled limiter.
        return {'end': end, 'start': self.number(control.path + '/' + control.start_file)
                if control.start_file and (control.start_values or control.derived) else None}

    def load_config(self):
        if self.config.is_symlink():
            raise CareError('Refusing a symbolic link for the saved configuration.')
        try:
            with self.config.open() as stream:
                raw = stream.read(MAX_CONFIG_BYTES + 1)
        except FileNotFoundError:
            return {'schema': 1, 'devices': {}}
        if len(raw) > MAX_CONFIG_BYTES:
            raise CareError('The saved configuration is too large.')
        try:
            data = json.loads(raw)
        except ValueError as error:
            raise CareError('The saved configuration is invalid JSON; it was left untouched.') from error
        if not isinstance(data, dict) or type(data.get('schema')) is not int or data['schema'] != 1 or not isinstance(data.get('devices'), dict) or len(data['devices']) > 32:
            raise CareError('The saved configuration has an unsupported format.')
        for key, value in data['devices'].items():
            if (not re.fullmatch(r'[A-Za-z0-9_.:-]{1,80}', key) or not isinstance(value, dict)
                    or not isinstance(value.get('identity'), str) or not re.fullmatch(r'[0-9a-f]{64}', value['identity'])
                    or type(value.get('end')) is not int or not 0 <= value['end'] <= 100
                    or (value.get('start') is not None and (type(value['start']) is not int or not 0 <= value['start'] <= 100))):
                raise CareError('The saved configuration contains an invalid device setting; it was left untouched.')
        return data

    def asahi_value(self):
        try:
            with self.asahi.open() as stream:
                lines = stream.read(4096).splitlines()
            for line in lines:
                if line in ('CHARGE_CONTROL_END_THRESHOLD=80', 'CHARGE_CONTROL_END_THRESHOLD=100'):
                    return int(line.partition('=')[2])
        except OSError:
            pass
        return None

    def saved(self, control, config):
        value = config['devices'].get(control.id)
        if isinstance(value, dict) and value.get('identity') == self.identity(control):
            return {'end': value.get('end'), 'start': value.get('start'), 'source': 'plugin'}
        if control.driver == 'apple':
            end = self.asahi_value()
            if end in (80, 100):
                return {'end': end, 'start': control.default_start(end), 'source': 'asahi'}
        return None

    def conflicts(self):
        try:
            result = subprocess.run(['/usr/bin/systemctl', 'is-active', '--quiet', 'tlp.service'], timeout=3, capture_output=True)
            return ['tlp.service'] if result.returncode == 0 else []
        except (OSError, subprocess.SubprocessError):
            return []

    def status(self):
        error = ''
        try:
            config = self.load_config()
        except CareError as issue:
            config = {'devices': {}}
            error = str(issue)
        controls = []
        for control in self.discover():
            current = self.current(control)
            saved = self.saved(control, config)
            controls.append(dict(id=control.id, driver=control.driver, label=control.label, kind=control.kind,
                                 shared=control.shared, stopValues=control.stop_values, startValues=control.start_values,
                                 derived=control.derived, gap=control.gap, fullStart=control.full_start,
                                 careStop=1 if control.kind in ('toggle', 'charge-types') else min(control.stop_values, key=lambda v: abs(v-80)),
                                 fullStop=0 if control.kind in ('toggle', 'charge-types') else max(control.stop_values),
                                 warning=control.warning, saved=saved, persisted=bool(saved and current == {k: saved[k] for k in ('end', 'start')}),
                                 **current))
        return dict(version=VERSION, machine=self.machine(), batteries=self.batteries(), controls=controls,
                    conflicts=self.conflicts(), error=error)

    def validate(self, control, end, start=None):
        if type(end) is not int or end not in control.stop_values:
            raise CareError('This maximum charge is not supported by the detected driver.')
        if control.derived or not control.start_values:
            expected = control.default_start(end)
            if start is not None and (type(start) is not int or start != expected):
                raise CareError('This driver controls the restart threshold automatically.')
            return expected
        if start is None:
            start = control.default_start(end)
        if type(start) is not int or start not in control.start_values or start > end - control.gap:
            raise CareError('The restart threshold is outside this driver’s range or too close to the maximum.')
        return start

    def apply(self, control, end, start=None):
        start = self.validate(control, end, start)
        old = self.current(control)
        if control.kind == 'framework':
            _min, actual = self.framework(end)
            if actual != end:
                raise CareError('Framework returned a different limit; it was not saved.')
        elif control.kind == 'pair':
            self.write(control.path + '/' + control.end_file, f'{start} {end}')
        elif control.kind == 'charge-types':
            self.write(control.path + '/' + control.end_file, 'Long_Life' if end else 'Standard')
        else:
            if control.mode_file:
                self.write(control.path + '/' + control.mode_file, 'Custom')
            writes = [(control.end_file, 0 if control.driver == 'sony' and end == 100 else end)]
            if control.start_values:
                # Respect the firmware's start/stop invariant at every intermediate write.
                pair = (control.start_file, start)
                if old['end'] is not None and start > old['end'] - control.gap:
                    writes.append(pair)
                else:
                    writes.insert(0, pair)
            for name, value in writes:
                self.write(control.path + '/' + name, value)
        actual = self.current(control)
        wanted = {'start': start, 'end': end}
        if actual != wanted:
            raise CareError(f'The driver reports {actual}, rather than {wanted}. The selection was not saved; some settings may already have changed.')
        if control.mode_file:
            mode = self.read(control.path + '/' + control.mode_file)
            if mode != 'Custom' and '[Custom]' not in mode:
                raise CareError('The driver did not confirm Custom charging mode; settings were not saved.')
        return actual

    def set(self, id, end, start=None):
        if self.conflicts():
            raise CareError('TLP is active and may overwrite charge settings. Choose one charge manager before making changes.')
        config = self.load_config()
        control = next((v for v in self.discover() if v.id == id), None)
        if control is None:
            raise CareError('The selected charge control is no longer available.')
        if id not in config['devices'] and len(config['devices']) >= 32:
            raise CareError('The saved device limit has been reached. Remove obsolete saved entries before adding a new battery.')
        try:
            actual = self.apply(control, end, start)
        except OSError as error:
            raise CareError(f'The driver could not complete the change: {error}. Some settings may already have changed; the selection was not saved.') from error
        config['devices'][id] = dict(identity=self.identity(control), driver=control.driver, **actual)
        try:
            atomic_write(self.config, json.dumps(config, indent=2) + '\n')
            if control.driver == 'apple':
                atomic_write(self.asahi, f'CHARGE_CONTROL_END_THRESHOLD={end}\n')
        except (OSError, CareError) as error:
            raise CareError(f'The driver accepted the selection, but saving all restart settings failed: {error}') from error
        return self.status()

    def adopt_asahi(self):
        config = self.load_config()
        for control in self.discover():
            if control.driver == 'apple' and control.id not in config['devices']:
                end = self.asahi_value()
                if end in (80, 100) and self.current(control) == {'end': end, 'start': control.default_start(end)}:
                    config['devices'][control.id] = dict(identity=self.identity(control), driver=control.driver, end=end, start=control.default_start(end))
                    atomic_write(self.config, json.dumps(config, indent=2) + '\n')

    def restore(self):
        if self.conflicts():
            return {'restored': [], 'skipped': ['TLP is active'], 'errors': []}
        config = self.load_config()
        result = {'restored': [], 'skipped': [], 'errors': []}
        for control in self.discover():
            saved = self.saved(control, config)
            if not saved or saved['source'] != 'plugin':
                continue
            try:
                self.apply(control, saved['end'], saved['start'])
                result['restored'].append(control.id)
            except (OSError, CareError, subprocess.SubprocessError) as error:
                result['errors'].append(control.id + ': ' + str(error))
        return result


@contextlib.contextmanager
def locked():
    fd = os.open(LOCK, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(fd)
        if info.st_uid != 0 or not stat.S_ISREG(info.st_mode) or info.st_mode & 0o022 or info.st_nlink != 1:
            raise CareError('The battery-control lock is not a protected root-owned file.')
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='command', required=True)
    subs.add_parser('status')
    subs.add_parser('restore')
    subs.add_parser('adopt-asahi')
    setter = subs.add_parser('set')
    setter.add_argument('device')
    setter.add_argument('end', type=int)
    setter.add_argument('start', type=int, nargs='?')
    args = parser.parse_args()
    try:
        engine = Engine()
        if args.command == 'status':
            result = engine.status()
        else:
            if os.geteuid() != 0:
                raise CareError('Administrator authentication is required.')
            with locked():
                if args.command == 'set':
                    result = engine.set(args.device, args.end, args.start)
                elif args.command == 'adopt-asahi':
                    engine.adopt_asahi()
                    result = engine.status()
                else:
                    result = engine.restore()
        print(json.dumps(result))
        return 1 if result.get('errors') else 0
    except (OSError, CareError, ValueError, subprocess.SubprocessError) as error:
        print(str(error)[:2000], file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
