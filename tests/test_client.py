import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import client


class AuthenticationTests(unittest.TestCase):
    def result(self, code, stderr='', stdout='{}'):
        return subprocess.CompletedProcess([], code, stdout, stderr)

    def test_sudo_is_noninteractive_then_desktop_authentication(self):
        denied=self.result(1, 'sudo: a password is required')
        with patch.object(client, 'run', side_effect=[denied,self.result(0)]) as run:
            client.elevate(['/fixed/helper','set','BAT0','80'])
        self.assertEqual(run.call_args_list[0].args[0], ['/usr/bin/sudo','-n','--','/fixed/helper','set','BAT0','80'])
        self.assertEqual(run.call_args_list[1].args[0][0], '/usr/bin/pkexec')

    def test_helper_failure_is_never_retried(self):
        with patch.object(client, 'run', return_value=self.result(1, 'Driver rejected the setting')) as run:
            with self.assertRaisesRegex(RuntimeError, 'Driver rejected'):
                client.elevate(['/fixed/helper'])
        self.assertEqual(run.call_count,1)

    def test_sudo_policy_denial_is_not_authentication(self):
        with patch.object(client, 'run', return_value=self.result(1, 'sudo: user is not allowed to execute this command')) as run:
            with self.assertRaises(RuntimeError):
                client.elevate(['/fixed/helper'])
        self.assertEqual(run.call_count,1)

    def test_cancelled_authentication(self):
        with patch.object(client, 'run', side_effect=[self.result(1,'sudo: a password is required'),self.result(126)]):
            with self.assertRaisesRegex(RuntimeError,'cancelled or denied'):
                client.elevate(['/fixed/helper'])

    def test_missing_backend_cannot_receive_privileged_changes(self):
        with patch.object(sys,'argv',['client.py','set','BAT0','80']), patch.object(client,'trusted_executable',return_value=False), patch.object(client,'elevate') as elevate:
            self.assertEqual(client.main(),1)
        elevate.assert_not_called()


class PackagingTests(unittest.TestCase):
    def test_dynamic_panel_text_is_plain(self):
        source=(ROOT/'ChargeLimitControl.qml').read_text()
        self.assertIn('textFormat: Text.PlainText',source)
        self.assertNotIn('tooltipText:', source)
        self.assertNotIn('Text.AutoText', source)
        self.assertIn('component CareText: Text',source)

    def test_persistence_is_event_driven_not_a_polling_root_daemon(self):
        service=(ROOT/'system/omarchy-battery-care.service').read_text()
        self.assertIn('Type=oneshot',service)
        self.assertIn(' restore',service)
        self.assertNotIn('Restart=always',service)
        self.assertIn('ACTION=="add"',(ROOT/'system/95-omarchy-battery-care.rules').read_text())
        self.assertIn('post',(ROOT/'system/sleep-hook').read_text())


if __name__=='__main__':
    unittest.main()
