import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('care_backend', ROOT / 'backend.py')
bc = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = bc
spec.loader.exec_module(bc)


class SimulatedKernel(bc.Engine):
    """Model sysfs side effects, derived thresholds, enum reads, and invariants."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.writes = []
        self.ignore_writes = False
        self.fail_path = None

    def conflicts(self):
        return []

    def write(self, relative, value):
        if relative == self.fail_path:
            raise PermissionError('Firmware rejected the write')
        self.writes.append((relative, str(value)))
        if self.ignore_writes:
            return
        control = next((c for c in self.discover() if relative.startswith(c.path + '/')), None)
        if control and control.start_values and control.kind != 'pair' and relative.endswith((control.start_file, control.end_file)):
            old = self.current(control)
            start = int(value) if relative.endswith(control.start_file) else old['start']
            end = int(value) if relative.endswith(control.end_file) else old['end']
            if start is not None and end is not None and start > end - control.gap:
                raise OSError('Intermediate thresholds violate firmware invariant')
        if relative.endswith('charge_types'):
            value = 'Standard [Long_Life]' if value == 'Long_Life' else '[Standard] Long_Life' if value == 'Standard' else 'Standard [Custom]'
        super().write(relative, value)
        if control and relative.endswith(control.end_file) and control.derived:
            start = 75 if int(value) == 80 else 100
            if control.derived == 'msi':
                start = int(value) - 10
            super().write(control.path + '/' + control.start_file, start)


class HardwareTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.sys = self.base / 'sys'
        self.sys.mkdir()
        self.engine = SimulatedKernel(self.sys, self.base / 'settings.json', self.base / 'asahi.conf')
        self.file('class/power_supply/BAT0/type', 'Battery')
        self.file('class/power_supply/BAT0/present', '1')
        self.file('class/power_supply/BAT0/capacity', '56')

    def file(self, path, value):
        target = self.sys / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(str(value))
        return target

    def module(self, name):
        (self.sys / 'module' / name).mkdir(parents=True, exist_ok=True)

    def standard(self, module, name='BAT0', start=75, end=80):
        self.module(module)
        if module == 'asus_wmi':
            self.file('class/dmi/id/sys_vendor', 'ASUSTeK COMPUTER INC.')
        self.file(f'class/power_supply/{name}/type', 'Battery')
        self.file(f'class/power_supply/{name}/charge_control_end_threshold', end)
        if start is not None:
            self.file(f'class/power_supply/{name}/charge_control_start_threshold', start)
        return f'class/power_supply/{name}'

    def control(self):
        return self.engine.discover()[0]

    def set_limit(self, end, start=None):
        return self.engine.set(self.control().id, end, start)

    def test_apple_accepts_only_native_limits_and_synchronizes_asahi(self):
        self.file('class/power_supply/BAT0/present', 0)
        self.standard('macsmc_power', 'macsmc-battery', 100, 100)
        self.assertEqual(self.control().driver, 'apple')
        self.assertEqual(self.control().stop_values, [80, 100])
        result = self.set_limit(80)['controls'][0]
        self.assertEqual((result['end'], result['start']), (80, 75))
        self.assertTrue(result['persisted'])
        self.assertEqual(self.engine.asahi.read_text(), 'CHARGE_CONTROL_END_THRESHOLD=80\n')
        self.set_limit(100)
        self.assertEqual(self.engine.current(self.control()), {'end': 100, 'start': 100})
        with self.assertRaises(bc.CareError):
            self.set_limit(90)

    def test_thinkpad_dual_batteries_have_independent_settings(self):
        self.standard('thinkpad_acpi')
        self.standard('thinkpad_acpi', 'BAT1')
        self.assertEqual(len(self.engine.discover()), 2)
        self.engine.set('BAT0', 85, 70)
        self.assertEqual(self.engine.current(self.engine.discover()[1])['end'], 80)
        self.engine.set('BAT1', 90, 75)
        self.assertEqual(len(self.engine.load_config()['devices']), 2)

    def test_dell_enables_custom_and_raises_stop_before_start(self):
        base = self.standard('dell_laptop', start=50, end=55)
        self.file(base + '/charge_types', '[Standard] Custom')
        self.set_limit(100, 95)
        self.assertEqual([Path(p).name for p, v in self.engine.writes], ['charge_types', 'charge_control_end_threshold', 'charge_control_start_threshold'])
        self.assertEqual(self.engine.read(base + '/charge_types'), 'Standard [Custom]')
        with self.assertRaises(bc.CareError):
            self.set_limit(80, 78)

    def test_lowering_stop_lowers_start_first(self):
        self.standard('thinkpad_acpi', start=96, end=100)
        self.set_limit(80, 75)
        self.assertTrue(self.engine.writes[0][0].endswith('start_threshold'))

    def test_asus_unreadable_initial_threshold_still_detected(self):
        self.standard('asus_wmi', start=None)
        self.file('class/power_supply/BAT0/charge_control_end_threshold', '')
        self.assertEqual(self.engine.status()['controls'][0]['end'], None)
        self.set_limit(80)
        self.assertEqual(self.engine.current(self.control())['end'], 80)

    def test_lg_and_toshiba_offer_only_80_and_100(self):
        for module, driver in [('lg_laptop', 'lg'), ('toshiba_acpi', 'toshiba')]:
            with self.subTest(driver=driver):
                for p in (self.sys / 'module').glob('*') if (self.sys / 'module').exists() else []:
                    p.rmdir()
                self.standard(module, start=None)
                self.assertEqual(self.control().driver, driver)
                self.assertEqual(self.control().stop_values, [80, 100])
                self.set_limit(100)
                with self.assertRaises(bc.CareError):
                    self.set_limit(60)

    def test_msi_uses_firmware_derived_restart(self):
        self.standard('msi_ec', start=70, end=80)
        self.assertEqual(self.control().driver, 'msi')
        result = self.set_limit(90)['controls'][0]
        self.assertEqual((result['end'], result['start']), (90, 80))
        with self.assertRaises(bc.CareError):
            self.set_limit(90, 75)

    def test_system76_separate_limits(self):
        self.standard('system76_acpi')
        self.set_limit(85, 60)
        self.assertEqual(self.engine.current(self.control()), {'end': 85, 'start': 60})

    def test_huawei_paired_global_interface(self):
        self.file('devices/platform/huawei-wmi/charge_control_thresholds', '75 80')
        self.assertEqual(self.control().driver, 'huawei')
        self.set_limit(90, 70)
        self.assertEqual(self.engine.read('devices/platform/huawei-wmi/charge_control_thresholds'), '70 90')
        self.assertTrue(self.engine.status()['controls'][0]['shared'])

    def test_lenovo_legacy_toggle_does_not_invent_percentage(self):
        self.file('bus/platform/drivers/ideapad_acpi/VPC2004:00/conservation_mode', 0)
        self.assertEqual(self.control().driver, 'lenovo-legacy')
        self.assertEqual(self.control().stop_values, [0, 1])
        self.set_limit(1)
        self.assertEqual(self.engine.current(self.control())['end'], 1)
        self.assertIn('cannot be read', self.control().warning)
        with self.assertRaises(bc.CareError):
            self.set_limit(80)

    def test_lenovo_charge_types(self):
        (self.sys / 'bus/platform/drivers/ideapad_acpi').mkdir(parents=True)
        self.file('class/power_supply/BAT0/charge_types', '[Standard] Long_Life')
        self.assertEqual(self.control().kind, 'charge-types')
        self.set_limit(1)
        self.assertEqual(self.engine.current(self.control())['end'], 1)
        self.set_limit(0)
        self.assertEqual(self.engine.current(self.control())['end'], 0)

    def test_samsung_toggle(self):
        self.file('devices/platform/samsung/battery_life_extender', 0)
        self.assertEqual(self.control().driver, 'samsung')
        self.set_limit(1)
        self.assertEqual(self.engine.current(self.control()), {'end': 1, 'start': None})

    def test_sony_fixed_thresholds(self):
        self.file('devices/platform/sony-laptop/battery_care_limiter', 100)
        self.assertEqual(self.control().stop_values, [50, 80, 100])
        self.set_limit(50)
        with self.assertRaises(bc.CareError):
            self.set_limit(60)

    def test_sony_disabled_limiter_is_full_charge_not_zero_percent(self):
        path = self.file('devices/platform/sony-laptop/battery_care_limiter', 0)
        self.assertEqual(self.engine.current(self.control())['end'], 100)
        self.set_limit(80)
        self.set_limit(100)
        self.assertEqual(path.read_text().strip(), '0')
        self.assertTrue(self.engine.status()['controls'][0]['persisted'])

    def test_legacy_thinkpad(self):
        self.file('devices/platform/smapi/BAT0/stop_charge_thresh', 100)
        self.file('devices/platform/smapi/BAT0/start_charge_thresh', 96)
        self.assertEqual(self.control().driver, 'thinkpad-legacy')
        self.set_limit(80, 75)
        self.assertEqual(self.engine.current(self.control()), {'end': 80, 'start': 75})

    def enable_cros(self, with_start):
        self.standard('cros_charge_control', start=75 if with_start else None)
        driver = self.sys / 'bus/platform/drivers/cros-charge-control'
        driver.mkdir(parents=True)
        link = self.sys / 'bus/platform/devices/cros-charge-control.0.auto/driver'
        link.parent.mkdir(parents=True)
        link.symlink_to(driver)

    def test_cros_v3_has_start_threshold(self):
        self.enable_cros(True)
        self.assertEqual(self.control().driver, 'cros-ec')
        self.set_limit(85, 60)
        self.assertEqual(self.engine.current(self.control()), {'end': 85, 'start': 60})

    def test_cros_v2_stop_only(self):
        self.enable_cros(False)
        self.assertEqual(self.control().start_values, [])
        self.set_limit(85)
        self.assertEqual(self.engine.current(self.control()), {'end': 85, 'start': None})

    def test_wilco_separate_charger(self):
        self.module('wilco_charger')
        self.file('class/power_supply/wilco-charger/charge_control_start_threshold', 75)
        self.file('class/power_supply/wilco-charger/charge_control_end_threshold', 80)
        self.file('class/power_supply/wilco-charger/charge_type', 'Standard')
        self.assertEqual(self.control().driver, 'wilco-ec')
        self.set_limit(90, 80)
        self.assertEqual(self.engine.current(self.control()), {'end': 90, 'start': 80})

    def test_tuxedo_uses_driver_advertised_values(self):
        self.file('class/dmi/id/sys_vendor', 'TUXEDO')
        base = self.standard('clevo_acpi')
        self.file(base + '/charge_control_start_available_thresholds', '40 50 60 70 80 95')
        self.file(base + '/charge_control_end_available_thresholds', '60 70 80 90 100')
        self.file(base + '/charge_type', 'Standard')
        self.assertEqual(self.control().driver, 'tuxedo')
        self.set_limit(90, 70)
        with self.assertRaises(bc.CareError):
            self.set_limit(85, 70)

    def test_framework_optional_vendor_tool(self):
        self.file('class/dmi/id/sys_vendor', 'Framework')
        with patch.object(bc, 'trusted_executable', return_value=True), patch.object(self.engine, 'framework', return_value=(0, 80)):
            self.assertEqual(self.control().driver, 'framework-tool')
            self.set_limit(80)
        with patch.object(bc, 'trusted_executable', return_value=False):
            self.assertEqual(self.engine.discover(), [])

    def test_framework_command_is_fixed_and_output_verified(self):
        proc = subprocess.CompletedProcess([], 0, 'Minimum 0%, Maximum 80%\n', '')
        with patch.object(bc, 'trusted_executable', return_value=True), patch.object(bc.subprocess, 'run', return_value=proc) as run:
            self.assertEqual(self.engine.framework(80), (0, 80))
            self.assertEqual(run.call_args.args[0], ['/usr/bin/framework_tool', '--charge-limit', '80'])
        bad = subprocess.CompletedProcess([], 0, 'Unknown response 80', '')
        with patch.object(bc, 'trusted_executable', return_value=True), patch.object(bc.subprocess, 'run', return_value=bad):
            with self.assertRaises(bc.CareError):
                self.engine.framework(80)

    def test_framework_timeout_keeps_status_available_but_limit_unknown(self):
        control = bc.Control('platform-framework', 'framework-tool', '', 'All batteries', kind='framework')
        with patch.object(self.engine, 'framework', side_effect=subprocess.TimeoutExpired('framework_tool', 12)):
            self.assertEqual(self.engine.current(control), {'start': None, 'end': None})

    def test_framework_invalid_minimum_is_rejected(self):
        proc = subprocess.CompletedProcess([], 0, 'Minimum 90%, Maximum 80%\n', '')
        with patch.object(bc, 'trusted_executable', return_value=True), patch.object(bc.subprocess, 'run', return_value=proc):
            with self.assertRaises(bc.CareError):
                self.engine.framework()

    def test_unknown_vendor_does_not_guess_ranges(self):
        self.file('class/power_supply/BAT0/charge_control_end_threshold', 80)
        self.assertEqual(self.engine.discover(), [])
        self.file('class/power_supply/BAT0/charge_control_end_available_thresholds', '60 80 100')
        self.assertEqual(self.control().driver, 'sysfs-advertised')
        self.assertEqual(self.control().stop_values, [60, 80, 100])

    def test_advertised_pairs_exclude_unusable_maximums(self):
        base = self.standard('unknown_driver', start=80, end=100)
        self.file(base + '/charge_control_end_available_thresholds', '60 80 100')
        self.file(base + '/charge_control_start_available_thresholds', '80 95')
        self.assertEqual(self.control().stop_values, [100])
        self.assertIsNone(self.engine.status()['controls'][0]['careStop'])
        self.set_limit(100)
        self.assertEqual(self.engine.current(self.control()), {'start': 95, 'end': 100})
        self.file(base + '/charge_control_end_available_thresholds', '60 80')
        self.assertEqual(self.engine.discover(), [])

    def test_unknown_restart_range_is_not_guessed(self):
        base = self.standard('unknown_driver')
        self.file(base + '/charge_control_end_available_thresholds', '60 80 100')
        self.assertEqual(self.engine.discover(), [])

    def test_external_batteries_and_removed_batteries_are_ignored(self):
        self.standard('thinkpad_acpi')
        self.file('class/power_supply/BAT0/scope', 'Device')
        self.assertEqual(self.engine.discover(), [])
        self.file('class/power_supply/BAT0/scope', 'System')
        self.file('class/power_supply/BAT0/present', 0)
        self.assertEqual(self.engine.discover(), [])

    def test_driver_rejection_is_not_saved(self):
        self.standard('thinkpad_acpi')
        self.engine.ignore_writes = True
        with self.assertRaisesRegex(bc.CareError, 'not saved'):
            self.set_limit(90, 75)
        self.assertFalse(self.engine.config.exists())

    def test_partial_failure_does_not_save_success(self):
        base = self.standard('thinkpad_acpi', start=96, end=100)
        self.engine.fail_path = base + '/charge_control_end_threshold'
        with self.assertRaisesRegex(bc.CareError, "not saved"):
            self.set_limit(80, 75)
        self.assertFalse(self.engine.config.exists())
        self.assertEqual(self.engine.current(self.control())['start'], 75)

    def test_invalid_device_and_values_never_write(self):
        self.standard('thinkpad_acpi')
        for id, end, start in [('../../etc/passwd', 80, 75), ('BAT0', True, 75), ('BAT0', 101, 75), ('BAT0', 80, 90)]:
            with self.subTest(id=id, end=end, start=start), self.assertRaises(bc.CareError):
                self.engine.set(id, end, start)
        self.assertEqual(self.engine.writes, [])

    def test_saved_setting_restores_after_driver_resets(self):
        base = self.standard('thinkpad_acpi')
        self.set_limit(85, 70)
        self.file(base + '/charge_control_end_threshold', 100)
        self.file(base + '/charge_control_start_threshold', 96)
        result = self.engine.restore()
        self.assertEqual(result['restored'], ['BAT0'])
        self.assertEqual(self.engine.current(self.control()), {'end': 85, 'start': 70})

    def test_other_machine_does_not_restore_saved_setting(self):
        self.standard('thinkpad_acpi')
        self.set_limit(85, 70)
        self.file('class/dmi/id/product_name', 'Different machine')
        self.engine.writes.clear()
        self.assertEqual(self.engine.restore()['restored'], [])
        self.assertEqual(self.engine.writes, [])

    def test_saved_config_paths_are_never_trusted(self):
        self.standard('thinkpad_acpi')
        self.set_limit(85, 70)
        data = self.engine.load_config()
        data['devices']['BAT0']['end'] = '../../etc/passwd'
        data['devices']['BAT0']['path'] = '/etc/passwd'
        self.engine.config.write_text(json.dumps(data))
        self.engine.writes.clear()
        with self.assertRaises(bc.CareError):
            self.engine.restore()
        self.assertEqual(self.engine.writes, [])

    def test_boolean_saved_values_are_not_treated_as_integers(self):
        self.standard('msi_ec', start=0, end=10)
        self.set_limit(10)
        original = self.engine.load_config()
        for field in ('schema', 'end', 'start'):
            data = json.loads(json.dumps(original))
            if field == 'schema':
                data[field] = True
            else:
                data['devices']['BAT0'][field] = True
            self.engine.config.write_text(json.dumps(data))
            self.engine.writes.clear()
            with self.assertRaises(bc.CareError):
                self.engine.restore()
            self.assertEqual(self.engine.writes, [])

    def test_full_saved_device_table_cannot_write_an_unreadable_33rd_entry(self):
        self.standard('thinkpad_acpi')
        data = {'schema': 1, 'devices': {f'OLD{i}': {'identity': '0' * 64, 'driver': 'thinkpad', 'end': 80, 'start': 75} for i in range(32)}}
        self.engine.config.write_text(json.dumps(data))
        with self.assertRaisesRegex(bc.CareError, 'saved device limit'):
            self.set_limit(90, 75)
        self.assertEqual(self.engine.writes, [])
        self.assertEqual(self.engine.load_config(), data)

    def test_derived_boolean_restart_is_rejected_before_writes(self):
        self.standard('msi_ec', start=0, end=10)
        with self.assertRaises(bc.CareError):
            self.set_limit(10, False)
        self.assertEqual(self.engine.writes, [])

    def test_huawei_out_of_range_readings_are_unknown(self):
        self.file('devices/platform/huawei-wmi/charge_control_thresholds', '999 1000')
        self.assertEqual(self.engine.current(self.control()), {'start': None, 'end': None})

    def test_corrupt_config_is_not_overwritten(self):
        self.standard('thinkpad_acpi')
        self.engine.config.write_text('{broken')
        with self.assertRaises(bc.CareError):
            self.set_limit(80, 75)
        self.assertEqual(self.engine.config.read_text(), '{broken')
        self.assertTrue(self.engine.status()['error'])
        self.assertEqual(self.engine.writes, [])

    def test_config_symlink_is_rejected(self):
        other = self.base / 'other'
        other.write_text('preserve')
        self.engine.config.symlink_to(other)
        self.standard('thinkpad_acpi')
        with self.assertRaises(bc.CareError):
            self.set_limit(80, 75)
        self.assertEqual(other.read_text(), 'preserve')

    def test_sysfs_escape_is_rejected(self):
        (self.sys / 'escape').symlink_to(self.base)
        with self.assertRaises(bc.CareError):
            self.engine.write('escape/other', 'bad')

    def test_readback_failure_does_not_create_config(self):
        base = self.standard('asus_wmi', start=None)
        self.engine.ignore_writes = True
        self.file(base + '/charge_control_end_threshold', '')
        with self.assertRaises(bc.CareError):
            self.set_limit(80)
        self.assertFalse(self.engine.config.exists())

    def test_tlp_conflict_blocks_both_set_and_restore(self):
        self.standard('thinkpad_acpi')
        self.set_limit(85, 70)
        self.engine.writes.clear()
        with patch.object(self.engine, 'conflicts', return_value=['tlp.service']):
            with self.assertRaises(bc.CareError):
                self.set_limit(90, 75)
            self.assertEqual(self.engine.restore()['restored'], [])
        self.assertEqual(self.engine.writes, [])

    def test_asahi_adoption_never_changes_hardware(self):
        self.file('class/power_supply/BAT0/present', 0)
        self.standard('macsmc_power', 'macsmc-battery')
        self.engine.asahi.write_text('CHARGE_CONTROL_END_THRESHOLD=80\n')
        self.engine.adopt_asahi()
        self.assertTrue(self.engine.config.exists())
        self.assertEqual(self.engine.writes, [])

    def test_save_failure_reports_hardware_may_have_changed(self):
        self.standard('thinkpad_acpi')
        with patch.object(bc, 'atomic_write', side_effect=PermissionError('disk read only')):
            with self.assertRaisesRegex(bc.CareError, 'driver accepted'):
                self.set_limit(85, 70)
        self.assertEqual(self.engine.current(self.control())['end'], 85)

    def test_no_battery_on_desktops(self):
        self.file('class/power_supply/BAT0/present', 0)
        self.file('devices/platform/samsung/battery_life_extender', 0)
        self.assertEqual(self.engine.status()['controls'], [])

    def test_atomic_config_has_no_temporary_files_and_normal_permissions(self):
        self.standard('thinkpad_acpi')
        self.set_limit(80, 75)
        self.assertEqual(self.engine.config.stat().st_mode & 0o777, 0o644)
        self.assertEqual(list(self.base.glob('.battery-care-*')), [])

    def test_markup_shaped_model_is_data(self):
        self.standard('thinkpad_acpi')
        self.file('class/dmi/id/product_name', '<img src="https://example.invalid/tracker">')
        self.assertEqual(self.engine.status()['machine']['model'], '<img src="https://example.invalid/tracker">')
        self.assertEqual(self.engine.writes, [])


    def test_asus_module_on_other_vendor_does_not_guess_support(self):
        self.standard('asus_wmi', start=None)
        self.file('class/dmi/id/sys_vendor', 'Different manufacturer')
        self.assertEqual(self.engine.discover(), [])

    def test_apple_missing_restart_interface_is_read_only(self):
        self.file('class/power_supply/BAT0/present', 0)
        self.standard('macsmc_power', 'macsmc-battery', start=None)
        self.assertEqual(self.engine.discover(), [])

    def test_wilco_incomplete_interface_is_read_only(self):
        self.module('wilco_charger')
        self.file('class/power_supply/wilco-charger/charge_control_end_threshold',80)
        self.assertEqual(self.engine.discover(), [])

    def test_full_charge_not_invented_when_not_advertised(self):
        self.file('class/power_supply/BAT0/charge_control_end_threshold',80)
        self.file('class/power_supply/BAT0/charge_control_end_available_thresholds','60 80')
        control=self.engine.status()['controls'][0]
        self.assertIsNone(control['fullStop'])
        self.assertEqual(control['careStop'],80)

    def test_care_preset_never_selects_zero_or_full_charge(self):
        self.file('class/power_supply/BAT0/charge_control_end_threshold',100)
        self.file('class/power_supply/BAT0/charge_control_end_available_thresholds','0 100')
        control=self.engine.status()['controls'][0]
        self.assertIsNone(control['careStop'])
        self.assertEqual(control['fullStop'],100)

    def test_switching_custom_mode_rechecks_reset_thresholds(self):
        base=self.standard('dell_laptop',start=95,end=100)
        self.file(base+'/charge_types','[Standard] Custom')
        write=self.engine.write
        def switching(path,value):
            write(path,value)
            if path.endswith('charge_types'):
                self.file(base+'/charge_control_start_threshold',55)
                self.file(base+'/charge_control_end_threshold',60)
        with patch.object(self.engine,'write',side_effect=switching):
            self.set_limit(80,75)
        self.assertEqual([Path(p).name for p,v in self.engine.writes], ['charge_types','charge_control_end_threshold','charge_control_start_threshold'])

    def test_already_custom_mode_is_not_rewritten(self):
        base=self.standard('dell_laptop')
        self.file(base+'/charge_types','Standard [Custom]')
        self.set_limit(85,70)
        self.assertFalse(any(p.endswith('charge_types') for p,v in self.engine.writes))

    def test_malformed_saved_value_disables_status_and_preserves_file(self):
        self.standard('thinkpad_acpi')
        self.set_limit(80,75)
        data=self.engine.load_config()
        data['devices']['BAT0']['start']=True
        raw=json.dumps(data)
        self.engine.config.write_text(raw)
        self.assertTrue(self.engine.status()['error'])
        with self.assertRaises(bc.CareError): self.set_limit(85,70)
        self.assertEqual(self.engine.config.read_text(),raw)

    def test_huawei_malformed_pair_stays_unknown(self):
        self.file('devices/platform/huawei-wmi/charge_control_thresholds','1000 5000')
        self.assertEqual(self.engine.current(self.control()),{'start':None,'end':None})

    def test_service_check_failure_blocks_writes(self):
        self.standard('thinkpad_acpi')
        with patch.object(self.engine,'conflicts',return_value=['charge-manager-status-unavailable']):
            self.assertTrue(self.engine.status()['error'])
            with self.assertRaisesRegex(bc.CareError,'Could not check'): self.set_limit(80,75)
            self.assertTrue(self.engine.restore()['errors'])
        self.assertEqual(self.engine.writes,[])

    def test_non_utf8_config_is_a_read_only_error(self):
        self.standard('thinkpad_acpi')
        self.engine.config.write_bytes(b'\xff\xfe')
        self.assertTrue(self.engine.status()['error'])
        self.assertEqual(self.engine.writes,[])

    def test_non_utf8_firmware_text_does_not_hide_battery_controls(self):
        self.standard('thinkpad_acpi')
        self.file('class/dmi/id/product_name','').write_bytes(b'\xff')
        self.assertEqual(self.engine.machine()['model'],'')
        self.assertEqual(len(self.engine.status()['controls']),1)


if __name__ == '__main__':
    unittest.main()
