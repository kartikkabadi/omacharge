"""Exercise installer ordering using only temporary files and fake systemctl."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('care_installer', ROOT / 'system/install.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / 'source'
        self.source.mkdir()
        self.files = {}
        for name in ('helper', 'service'):
            (self.source / name).write_text('new ' + name)
            destination = self.root / ('installed-' + name)
            destination.write_text('old ' + name)
            self.files[name] = (str(destination), 0o755 if name == 'helper' else 0o644)
        for attribute, value in (('SOURCE', self.source), ('FILES', self.files)):
            self.enterContext(patch.object(installer, attribute, value))
        self.enterContext(patch.object(installer.os, 'geteuid', return_value=0))
        self.run = self.enterContext(patch.object(installer.subprocess, 'run'))
        # Protected-destination validation is tested separately; the test root
        # is intentionally user-owned and must never be a valid real target.
        self.validate = self.enterContext(patch.object(installer, 'validate_destination'))

    def invoke(self, command):
        with patch.object(installer.sys, 'argv', ['install.py', command]):
            installer.main()

    def test_install_replaces_the_complete_payload_with_fixed_permissions(self):
        self.invoke('install')
        self.assertEqual(self.validate.call_count, 2)
        for name, (path, mode) in self.files.items():
            self.assertEqual(Path(path).read_text(), 'new ' + name)
            self.assertEqual(Path(path).stat().st_mode & 0o777, mode)
        self.assertFalse(list(self.root.glob('.battery-care-*')))

    def test_late_preflight_failure_leaves_all_files_and_services_alone(self):
        self.validate.side_effect = [None, RuntimeError('unsafe destination')]
        with self.assertRaisesRegex(RuntimeError, 'unsafe destination'):
            self.invoke('install')
        self.run.assert_not_called()
        for name, (path, mode) in self.files.items():
            self.assertEqual(Path(path).read_text(), 'old ' + name)

    def test_missing_payload_is_detected_before_installation(self):
        (self.source / 'service').unlink()
        with self.assertRaises(FileNotFoundError):
            self.invoke('install')
        self.run.assert_not_called()
        self.assertEqual(Path(self.files['helper'][0]).read_text(), 'old helper')

    def test_removal_does_not_delete_a_running_backend_after_stop_failure(self):
        self.run.side_effect = subprocess.CalledProcessError(1, 'systemctl')
        with self.assertRaises(subprocess.CalledProcessError):
            self.invoke('remove')
        self.assertTrue(all(Path(path).exists() for path, mode in self.files.values()))

    def test_removal_preflights_before_stopping_services(self):
        self.validate.side_effect = RuntimeError('unsafe destination')
        with self.assertRaises(RuntimeError):
            self.invoke('remove')
        self.run.assert_not_called()

    def test_removal_also_works_when_unit_is_already_absent(self):
        self.run.return_value = subprocess.CompletedProcess([], 0, 'not-found\n', '')
        self.invoke('remove')
        self.assertFalse(any(Path(path).exists() for path, mode in self.files.values()))
        self.assertFalse(any('disable' in call.args[0] for call in self.run.call_args_list))


class DestinationTests(unittest.TestCase):
    def test_user_owned_parent_is_not_a_privileged_install_target(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, 'not protected'):
                installer.validate_destination(Path(directory) / 'helper')


if __name__ == '__main__':
    unittest.main()
