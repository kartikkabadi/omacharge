# Troubleshooting

## No charge controls

The kernel must expose the interface listed in the [hardware matrix](COMPATIBILITY.md).
A supported brand alone is insufficient. Omacharge does not probe by writing
unknown values, load experimental drivers, bypass firmware restrictions or flash
firmware. Missing support leaves battery reporting available and charge controls
read-only.

## Finish setup remains visible

Run `./setup.sh` as your normal desktop user from the installed checkout. Setup
requests desktop authentication when needed. Confirm that
`/usr/local/libexec/omarchy-battery-care` exists, is root-owned and is executable.
A frontend/backend version mismatch also requires setup after an update.

## Authentication was cancelled

Open the panel and try the selection again when ready. No automatic retry is
scheduled. Omarchy's desktop polkit agent must be running for GUI authentication.

## TLP is active

Omacharge leaves changes and restore read-only while `tlp.service` is active.
Choose one charge manager. Do not run competing policies that repeatedly write
the same interface. Omacharge does not disable TLP or alter power profiles for you.

## A setting failed or reports a different value

Check the refreshed current reading. Firmware may reject, round, ignore or
misreport a requested value. Dell can require an unlocked BIOS charging policy;
some ASUS firmware accepts only specific percentages. Some ThinkPads report
threshold quirks. Omacharge does not save an unconfirmed selection as success.

## Limit was lost after boot or sleep

```bash
systemctl is-enabled omarchy-battery-care.service
systemctl status omarchy-battery-care.service
journalctl -u omarchy-battery-care.service
```

The restore service is a oneshot; `inactive (dead)` after a successful run is
normal. Check the result and log rather than expecting a permanently active
process. Late devices also trigger a udev restore; resume has a post-sleep hook.
Actual reboot and suspend behavior still need physical tests on each model.

## Framework fallback

When native controls are absent, install Framework's official `framework_tool`
at `/usr/bin/framework_tool`. It must be root-owned and not writable by other
users. Read access can require authentication, so the current limit may initially
show unavailable. Failures are reported; force flags and raw EC writes are not used.

## Diagnostics

```bash
python3 client.py status
```

Run from the installed checkout. Review the JSON before posting it. It includes
manufacturer/model and battery IDs, not serial numbers, credentials or user paths.
For a bug report include the exact model, kernel, Omarchy version, requested
values, returned values and the visible error. Avoid full environment dumps.
