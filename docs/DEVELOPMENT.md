# Development and verification

The frontend is QML hosted by Omarchy's Quickshell shell. `BatteryPanel.qml`
retains the original power panel, `ChargeLimitControl.qml` adds the charge cards,
and `ThresholdPicker.qml` supplies theme-aware custom selectors.

`backend.py` implements discovery, capability validation, safe write ordering,
read-back, saved state and restore. It is also the installed root helper.
`client.py` is the unprivileged bridge; it elevates only the installed helper.
`system/install.py` installs fixed helper and event-hook paths.

## Tests

```bash
python3 -m unittest discover -s tests -v
node --test tests/test_model.cjs tests/test_model.js
python3 -m py_compile backend.py client.py system/install.py
bash -n install.sh setup.sh uninstall.sh system/sleep-hook
omarchy plugin validate .
python3 tests/run-ui.py
```

The Python tests run with an isolated temporary sysfs tree and simulated kernel
side effects. Installer checks use temporary destinations, an isolated HOME and
fake service/shell commands. No real hardware is written and no authentication
is requested. Node.js 18+ runs the UI snapshot validation tests.
The UI test runs the actual component with a fake unprivileged backend, including
presets, subprocess round trips, custom pickers and their popup, restart bounds,
stable refresh and plain-text rendering. Quickshell and an installed Omarchy
shell are required for that test. GitHub CI runs the Python checks on 3.11 and 3.14, plus the JavaScript protocol checks. The QML harness is a local check because it needs the installed Omarchy shell.

## Preview media

On the Vantablack desktop used for the release:

```bash
python3 tools/render-previews.py
python3 tools/make-preview.py
```

The renderer uses the installed shell's Commons/Ui modules and the actual QML
component, with explicit sample states. It runs offscreen and does not change
the desktop language, theme, charge settings or bar. `ffmpeg` encodes the silent
MP4 and matching GIF. Generated screenshots identify themselves as simulated
hardware. See [media provenance](MEDIA.md).

## Adding hardware

Prefer actual capability files and bound drivers over vendor names. Never probe
support by writing a value. Document exact paths, ranges, start/stop constraints,
shared-battery behavior and firmware restrictions, with a primary source.

Add fixture tests for discovery, application, write order, rejection and restore.
A write must be confirmed by read-back before the policy is saved. Unknown
hardware stays read-only unless its driver explicitly advertises valid values.

Root commands accept control IDs and numeric settings, never caller-supplied
paths. Test-only sysfs injection is available through Python imports and is not
exposed as a privileged CLI option. Preserve that boundary.

Fixture coverage is not physical compatibility evidence. Keep the distinction
in the [validation record](VALIDATION.md) and report the exact model/kernel/driver
for any physical test.
