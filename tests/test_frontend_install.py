"""Run the actual frontend installer with isolated HOME and fake shell IPC."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = 'io.github.kartikkabadi.omacharge'


@unittest.skipIf(os.geteuid() == 0, 'The frontend installer correctly refuses root.')
class FrontendInstallTests(unittest.TestCase):
    def test_existing_frontend_and_bar_config_are_backed_up(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            commands = home / 'bin'
            commands.mkdir()
            log = home / 'commands.log'
            # No command reaches the real desktop shell or requests elevation.
            fake = '''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
with Path(os.environ['OMACHARGE_TEST_LOG']).open('a') as stream:
    stream.write(json.dumps([Path(sys.argv[0]).name, *sys.argv[1:]]) + '\\n')
if sys.argv[1:] == ['plugin', 'list', '--json']:
    print(json.dumps([{'id': 'io.github.kartikkabadi.omacharge'}]))
'''
            for name in ('omarchy', 'omarchy-shell'):
                path = commands / name
                path.write_text(fake)
                path.chmod(0o755)
            config = home / '.config/omarchy/shell.json'
            config.parent.mkdir(parents=True)
            config.write_text('{"userSetting":"preserve me"}\n')
            target = config.parent / 'plugins' / PLUGIN
            target.mkdir(parents=True)
            (target / 'old-user-file').write_text('preserved')
            result = subprocess.run(['bash', str(ROOT / 'install.sh'), '--skip-backend'],
                                    capture_output=True, text=True, timeout=20,
                                    env={**os.environ, 'HOME': str(home), 'PATH': str(commands) + os.pathsep + os.environ['PATH'],
                                         'OMACHARGE_TEST_LOG': str(log)})
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(json.loads((target / 'manifest.json').read_text())['id'], PLUGIN)
            self.assertFalse((target / '.git').exists())
            backups = home / '.local/state/omarchy-battery-care/backups'
            self.assertEqual(len(list(backups.glob('*/old-user-file'))), 1)
            self.assertEqual(len(list(backups.glob('shell-*.json'))), 1)
            self.assertEqual(config.read_text(), '{"userSetting":"preserve me"}\n')
            calls = [json.loads(line) for line in log.read_text().splitlines()]
            self.assertIn(['omarchy', 'plugin', 'enable', 'omarchy.power'], calls)
            self.assertIn(['omarchy', 'plugin', 'enable', PLUGIN], calls)
            self.assertIn(['omarchy', 'restart', 'shell'], calls)
            self.assertFalse(list(target.parent.glob('.battery-care-stage-*')))


if __name__ == '__main__':
    unittest.main()
