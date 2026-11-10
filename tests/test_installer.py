import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('care_installer', ROOT/'system/install.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root/'source'
        self.source.mkdir()
        self.helper = self.root/'installed/helper'
        self.unit = self.root/'installed'/installer.UNIT
        self.helper.parent.mkdir()
        (self.source/'backend.py').write_bytes(b'new helper')
        (self.source/'unit').write_bytes(b'new unit')
        self.helper.write_bytes(b'old helper')
        self.helper.chmod(0o755)
        self.unit.write_bytes(b'old unit')
        self.files = {'backend.py': (str(self.helper),0o755), 'unit': (str(self.unit),0o644)}
        self.calls=[]
        self.enabled=True
        self.active=False
        self.failure=None
        self.failures=0
        def command(args, check=True):
            self.calls.append(args)
            if 'is-enabled' in args:
                return subprocess.CompletedProcess(args,0 if self.enabled else 1,'','')
            if 'is-active' in args:
                return subprocess.CompletedProcess(args,0 if self.active else 3,'','')
            if self.failure and self.failure(args) and self.failures==0:
                self.failures+=1
                raise subprocess.CalledProcessError(1,args,stderr='simulated failure')
            return subprocess.CompletedProcess(args,0,'','')
        self.command=patch.object(installer,'command',side_effect=command)
        self.command.start()
        self.addCleanup(self.command.stop)
        # The fixture directory is deliberately user-owned; root path validation is tested separately.
        self.validation=patch.object(installer,'validate_destination')
        self.validate=self.validation.start()
        self.addCleanup(self.validation.stop)

    def run_install(self, removing=False):
        return installer.install(removing,self.source,self.files)

    def assert_original(self):
        self.assertEqual(self.helper.read_bytes(),b'old helper')
        self.assertEqual(self.unit.read_bytes(),b'old unit')
        self.assertEqual(self.helper.stat().st_mode & 0o777,0o755)
        self.assertEqual(list(self.helper.parent.glob('.battery-care-*')),[])

    def test_success_installs_complete_payload_and_enables_restore(self):
        self.assertTrue(self.run_install()['installed'])
        self.assertEqual(self.helper.read_bytes(),b'new helper')
        self.assertEqual(self.unit.read_bytes(),b'new unit')
        self.assertIn(['/usr/bin/systemctl','enable',installer.UNIT],self.calls)
        self.assertEqual(self.calls[-1],['/usr/local/libexec/omarchy-battery-care','adopt-asahi'])

    def test_late_preflight_error_never_changes_earlier_file(self):
        self.validate.side_effect=[None,installer.InstallError('unsafe final path')]
        with self.assertRaises(installer.InstallError): self.run_install()
        self.assert_original()
        self.assertEqual(self.calls,[])

    def test_missing_payload_is_detected_before_mutation(self):
        (self.source/'unit').unlink()
        with self.assertRaises(installer.InstallError): self.run_install()
        self.assert_original()
        self.assertEqual(self.calls,[])

    def test_source_symlink_is_rejected(self):
        (self.source/'unit').unlink()
        (self.source/'unit').symlink_to(self.unit)
        with self.assertRaises(installer.InstallError): self.run_install()
        self.assert_original()

    def test_write_failure_rolls_back_preceding_replacement(self):
        write=installer.write_atomic
        def fail(path,data,mode):
            if data==b'new unit': raise OSError('disk full')
            write(path,data,mode)
        with patch.object(installer,'write_atomic',side_effect=fail), self.assertRaisesRegex(installer.InstallError,'restored'):
            self.run_install()
        self.assert_original()

    def test_service_reload_failure_rolls_back(self):
        self.failure=lambda args:'daemon-reload' in args
        with self.assertRaisesRegex(installer.InstallError,'restored'): self.run_install()
        self.assert_original()
        self.assertEqual(self.calls[-1],['/usr/bin/systemctl','enable',installer.UNIT])

    def test_enable_failure_restores_previously_enabled_service(self):
        self.failure=lambda args:'enable' in args
        with self.assertRaises(installer.InstallError): self.run_install()
        self.assert_original()
        self.assertEqual(self.calls[-1],['/usr/bin/systemctl','enable',installer.UNIT])

    def test_failed_new_install_removes_new_files_and_disables_unit(self):
        self.helper.unlink(); self.unit.unlink(); self.enabled=False
        self.failure=lambda args:'adopt-asahi' in args
        with self.assertRaises(installer.InstallError): self.run_install()
        self.assertFalse(self.helper.exists()); self.assertFalse(self.unit.exists())
        self.assertIn(['/usr/bin/systemctl','disable',installer.UNIT],self.calls)

    def test_remove_preserves_saved_policy(self):
        saved=self.root/'saved.json'; saved.write_text('keep settings')
        self.assertFalse(self.run_install(True)['installed'])
        self.assertFalse(self.helper.exists()); self.assertFalse(self.unit.exists())
        self.assertEqual(saved.read_text(),'keep settings')

    def test_remove_failure_restores_files_and_enabled_state(self):
        self.failure=lambda args:'--reload-rules' in args
        with self.assertRaises(installer.InstallError): self.run_install(True)
        self.assert_original()
        self.assertEqual(self.calls[-1],['/usr/bin/systemctl','enable',installer.UNIT])

    def test_destination_symlink_is_refused(self):
        link=self.root/'link'; link.symlink_to(self.helper)
        with self.assertRaisesRegex(installer.InstallError,'symlink'):
            installer.validate_destination.__wrapped__(link) if hasattr(installer.validate_destination,'__wrapped__') else self.actual_validation(link)

    def actual_validation(self,path):
        self.validation.stop()
        try: return installer.validate_destination(path)
        finally: self.validation.start()

    def test_user_owned_or_shared_destination_parent_is_refused(self):
        with self.assertRaisesRegex(installer.InstallError,'not protected'):
            self.actual_validation(self.helper)

    def test_rollback_restarts_an_interrupted_restore(self):
        self.active=True
        self.failure=lambda args:'--reload-rules' in args
        with self.assertRaises(installer.InstallError): self.run_install(True)
        self.assert_original()
        self.assertEqual(self.calls[-1],['/usr/bin/systemctl','start',installer.UNIT])


if __name__=='__main__': unittest.main()
