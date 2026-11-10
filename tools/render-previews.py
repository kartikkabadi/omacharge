#!/usr/bin/env python3
"""Render the real QML with sample hardware in the current Omarchy theme."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

project = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,default=project/'assets/screenshots')
args=parser.parse_args()
shell=Path('/usr/share/omarchy/shell')
with tempfile.TemporaryDirectory(prefix='omacharge-preview-') as tmp:
    root=Path(tmp)
    for name in ('Ui','Commons'):
        shutil.copytree(shell/name,root/name)
    shutil.copytree(project/'i18n',root/'i18n')
    for name in ('ChargeLimitControl.qml','ThresholdPicker.qml'):
        shutil.copy2(project/name,root/name)
    for source,target in [('Preview.qml','shell.qml'),('mock-status.py','mock-status.py'),('preview-state.json','state.json')]:
        shutil.copy2(project/'tools'/source,root/target)
    env={**os.environ,'QT_QPA_PLATFORM':'offscreen','QT_QPA_PLATFORMTHEME':'','QT_QUICK_BACKEND':'software'}
    env.pop('WAYLAND_DISPLAY',None)
    result=subprocess.run(['quickshell','-p',str(root),'--no-color'],capture_output=True,text=True,env=env,timeout=25)
    output=result.stdout+result.stderr
    print(output)
    if result.returncode or 'PREVIEW COMPLETE' not in output or any(s in output for s in ('TypeError','ReferenceError','Failed to load configuration')):
        raise SystemExit(1)
    args.output.mkdir(parents=True,exist_ok=True)
    for name in ('battery-care.png','custom-limits.png','conservation.png'):
        shutil.copy2(root/name,args.output/name)
