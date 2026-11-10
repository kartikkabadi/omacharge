import contextlib
import io
import json
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import backend
import client


class TrustAndLockTests(unittest.TestCase):
    def trust(self, unsafe=None, owner=0):
        def info(path):
            leaf=str(path)=='/safe/tool'
            mode=stat.S_IFREG|0o755 if leaf else stat.S_IFDIR|0o755
            uid=owner if leaf else 0
            if str(path)==unsafe: mode|=0o022
            return types.SimpleNamespace(st_mode=mode,st_uid=uid)
        with patch.object(Path,'resolve',lambda p,strict=False:p), patch.object(Path,'lstat',info), patch.object(backend.os,'access',return_value=True):
            return backend.trusted_executable(Path('/safe/tool'))

    def test_root_owned_file_in_protected_directories_is_trusted(self):
        self.assertTrue(self.trust())

    def test_root_owned_file_below_writable_directory_is_not_trusted(self):
        self.assertFalse(self.trust(unsafe='/safe'))

    def test_writable_executable_is_not_trusted(self):
        self.assertFalse(self.trust(unsafe='/safe/tool'))

    def test_non_root_owner_is_not_trusted(self):
        self.assertFalse(self.trust(owner=1000))

    def test_lock_contention_has_a_deadline(self):
        with tempfile.TemporaryDirectory() as tmp:
            info=types.SimpleNamespace(st_uid=0,st_mode=stat.S_IFREG|0o600)
            with patch.object(backend,'LOCK',Path(tmp)/'lock'), patch.object(backend.os,'fstat',return_value=info), patch.object(backend.fcntl,'flock',side_effect=BlockingIOError), patch.object(backend.time,'monotonic',side_effect=[0,9]):
                with self.assertRaisesRegex(backend.CareError,'busy'):
                    with backend.locked(): self.fail('An unavailable lock was entered')

    def test_service_check_error_fails_closed(self):
        result=subprocess.CompletedProcess([],1,'','cannot connect to system bus')
        with patch.object(backend.subprocess,'run',return_value=result):
            self.assertEqual(backend.Engine().conflicts(),['charge-manager-status-unavailable'])

    def test_missing_tlp_unit_is_not_a_conflict(self):
        with patch.object(backend.subprocess,'run',return_value=subprocess.CompletedProcess([],4,'','')):
            self.assertEqual(backend.Engine().conflicts(),[])

    def test_installer_lock_has_a_deadline(self):
        import importlib.util
        spec=importlib.util.spec_from_file_location('installer_lock_test',Path(__file__).resolve().parents[1]/'system/install.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            info=types.SimpleNamespace(st_uid=0,st_mode=stat.S_IFREG|0o600)
            with patch.object(module,'INSTALL_LOCK',Path(tmp)/'lock'), patch.object(module.os,'fstat',return_value=info), patch.object(module.fcntl,'flock',side_effect=BlockingIOError), patch.object(module.time,'monotonic',side_effect=[0,9]):
                with self.assertRaisesRegex(module.InstallError,'installation is running'):
                    with module.installation_lock(): self.fail('Contended installer lock was entered')


class ClientRecoveryTests(unittest.TestCase):
    def response(self,data,code=0,stderr=''):
        return subprocess.CompletedProcess([],code,json.dumps(data),stderr)

    def test_old_helper_status_falls_back_to_current_read_only_detection(self):
        responses=[self.response({'version':'old'}),self.response({'version':backend.VERSION,'controls':[]})]
        output=io.StringIO()
        with patch.object(client,'trusted_executable',return_value=True), patch.object(client,'run',side_effect=responses) as run, patch.object(sys,'argv',['client.py','status']), contextlib.redirect_stdout(output):
            self.assertEqual(client.main(),0)
        self.assertFalse(json.loads(output.getvalue())['installed'])
        self.assertIn('backend.py',run.call_args_list[1].args[0][-2])

    def test_broken_helper_status_still_allows_read_only_recovery(self):
        responses=[self.response({},1,'broken'),self.response({'version':backend.VERSION,'controls':[]})]
        with patch.object(client,'trusted_executable',return_value=True), patch.object(client,'run',side_effect=responses), patch.object(sys,'argv',['client.py','status']), contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(client.main(),0)
        self.assertFalse(json.loads(output.getvalue())['installed'])

    def test_outdated_helper_never_receives_a_mutation(self):
        with patch.object(client,'trusted_executable',return_value=True), patch.object(client,'run',return_value=self.response({'version':'old'})), patch.object(client,'elevate') as elevate, patch.object(sys,'argv',['client.py','set','BAT0','80']), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(client.main(),1)
        elevate.assert_not_called()

    def test_failed_status_before_set_never_elevates(self):
        with patch.object(client,'trusted_executable',return_value=True), patch.object(client,'run',return_value=self.response({},1,'service failed')), patch.object(client,'elevate') as elevate, patch.object(sys,'argv',['client.py','set','BAT0','80']), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(client.main(),1)
        elevate.assert_not_called()

    def test_elevated_operation_gets_time_to_complete(self):
        with patch.object(client,'run',return_value=self.response({})) as run:
            client.elevate(['/fixed/helper'])
        self.assertGreaterEqual(run.call_args.kwargs['timeout'],90)


if __name__=='__main__': unittest.main()
