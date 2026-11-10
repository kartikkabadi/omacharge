#!/usr/bin/env python3
"""Run real Quickshell QML against a fake, unprivileged backend."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--screenshot',type=Path)
args=parser.parse_args()
project = Path(__file__).resolve().parents[1]
shell = Path('/usr/share/omarchy/shell')
if not shutil.which('quickshell') or not (shell / 'Ui').exists():
    raise SystemExit('UI tests require Quickshell and an installed Omarchy shell.')
with tempfile.TemporaryDirectory(prefix='battery-care-ui-') as tmp:
    root = Path(tmp)
    for module in ('Ui', 'Commons'):
        shutil.copytree(shell / module, root / module)
    for name in ('ChargeLimitControl.qml','ThresholdPicker.qml','ChargeModel.js'):
        shutil.copy2(project/name,root/name)
    shutil.copytree(project / 'i18n', root / 'i18n')
    for file in (project / 'tests/qml').iterdir():
        if file.is_file():
            shutil.copy2(file, root / file.name)
    control = dict(id='TEST', driver='apple', label='TEST', kind='threshold', shared=False,
                   stopValues=[80,100], startValues=[], derived='apple', gap=1, fullStart=100,
                   careStop=80, fullStop=100, warning='', saved=None, persisted=True, end=100, start=100)
    state = dict(version='0.1.2', installed=True, controls=[control], batteries=[{'id':'TEST','capacity':80,'status':'Not charging'}], conflicts=[], error='')
    (root / 'mock-state.json').write_text(json.dumps(state))
    env = {**os.environ, 'QT_QPA_PLATFORM':'offscreen', 'QT_QUICK_BACKEND':'software'}
    env.pop('WAYLAND_DISPLAY', None)
    env['QT_QPA_PLATFORMTHEME'] = ''
    result = subprocess.run(['quickshell', '-p', str(root), '--no-color'], env=env, capture_output=True, text=True, timeout=25)
    output = result.stdout + result.stderr
    print(output)
    if result.returncode or 'PASS: UI presets' not in output or 'FAIL:' in output or 'ReferenceError' in output or 'TypeError' in output:
        raise SystemExit(1)

    if args.screenshot:
        args.screenshot.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(root/'demo-panel.png',args.screenshot)
