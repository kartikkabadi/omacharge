# Installation, updates and removal

## Requirements

Omacharge uses Omarchy's version-1 shell plugin API, Python 3.11+, systemd,
sudo and a desktop polkit agent. Development and runtime checks use Omarchy
4.5.0; earlier releases are not yet qualified. Check the
[hardware matrix](COMPATIBILITY.md) for the required driver interface.

## Install through Omarchy

```bash
omarchy plugin add https://github.com/kartikkabadi/omacharge.git --enable
```

Open the battery icon. Detection is available immediately. **Finish setup**
installs the root-owned helper and restore hooks using desktop authentication.
Run only one instance of the battery/power panel.

## Install from source

```bash
git clone https://github.com/kartikkabadi/omacharge.git
cd omacharge
./install.sh
```

Run as your desktop user. The installer requests authentication itself. It
backs up `shell.json`, installs the protected backend, copies the frontend into
`~/.config/omarchy/plugins/io.github.kartikkabadi.omacharge`, restores the standard
power-panel position if another clone occupies it, and replaces that slot with
Omacharge. The shell restarts once to flush cached QML components.

Installing never selects a new charge limit. An existing verified Apple/Asahi
setting can be adopted without changing the hardware.

`./install.sh --skip-backend` installs only the frontend. **Finish setup** can
install the backend later.

## Existing local power-panel clones

Omacharge is a replacement for the standard power widget. When installing with
the Omarchy plugin command, first restore the original slot:

```bash
omarchy plugin enable omarchy.power
omarchy plugin enable io.github.kartikkabadi.omacharge
```

The complete `install.sh` flow handles this automatically. Previous clone files
are preserved. For the initial prototype, this includes `kk.power` and
`community.battery-care`; their saved Apple limit continues to be adopted.

Backups of the bar config and replaced Omacharge frontend are kept under
`~/.local/state/omarchy-battery-care/backups`. Restore individual settings you need
instead of overwriting newer desktop changes with an old full config.

## Updates

For an Omarchy-managed checkout:

```bash
omarchy plugin update io.github.kartikkabadi.omacharge --yes
cd ~/.config/omarchy/plugins/io.github.kartikkabadi.omacharge
./setup.sh
omarchy restart shell
```

For a separate source checkout, pull its updates and run `./install.sh` again.
Updating the frontend does not silently update the privileged helper. Setup
requests authentication and replaces the helper with a root-owned copy. The
client refuses charge changes when the backend's release version differs.

## Protected files

| Path | Purpose |
|---|---|
| `/usr/local/libexec/omarchy-battery-care` | Root-owned backend |
| `/etc/omarchy-battery-care.json` | Verified saved settings |
| `/etc/systemd/system/omarchy-battery-care.service` | Boot/hotplug restore oneshot |
| `/etc/udev/rules.d/95-omarchy-battery-care.rules` | Device-add trigger |
| `/usr/lib/systemd/system-sleep/omarchy-battery-care` | Resume restore hook |
| `/usr/share/polkit-1/actions/org.omarchy.community.battery-care.policy` | Authenticated helper action |

The internal helper paths remain stable across the Omacharge branding change.
No passwordless authorization rule is installed. There is no polling root daemon.

## Removal

From the installed or source checkout:

```bash
./uninstall.sh             # Restore the stock widget
./uninstall.sh --backend   # Also remove helper and restore hooks
```

Then remove the frontend:

```bash
omarchy plugin remove io.github.kartikkabadi.omacharge --yes
```

Saved configuration and the current hardware setting are preserved. Select
Full charge before removal if you want to lift the limit. Firmware or the
existing Apple/Asahi restore mechanism may otherwise retain it. Back up and
remove `/etc/omarchy-battery-care.json` manually only when you want to discard
all saved policies; the removal script deliberately preserves it.
