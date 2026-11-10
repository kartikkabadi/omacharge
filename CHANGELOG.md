# Changelog

## 0.1.2 — Extended submission audit

- Disable stale controls after status failures and validate the complete backend-to-QML protocol.
- Preserve custom edits and the selected battery across changing status readings; clarify setup success and unsupported presets.
- Make helper installation transactional, preflight all files, restore prior files and service state on failure, and bound lock waits and subprocesses.
- Harden executable ownership checks, saved-policy parsing, invalid firmware data handling, TLP detection and driver capability checks.
- Re-read thresholds after firmware switches to Custom mode and avoid redundant mode writes.
- Add installer rollback, security boundary, protocol and QML regression coverage; pin CI actions and test Python 3.11 and 3.14.
- Add a directory preview, direct removal instructions and explicit privilege and hardware-test disclosures.

## 0.1.1 — Community submission review

- Disable charge changes after failed status reads, validate complete UI snapshots, and recover on the next successful refresh.
- Fix post-action refreshes that could be skipped while a process was exiting; distinguish setup completion from a saved charge change.
- Allow slow authenticated setup/read-back operations without retrying a timed-out or failed helper.
- Filter impossible advertised threshold pairs, reject undocumented restart ranges, and handle Framework timeouts without losing the panel.
- Normalize Sony's disabled limiter to full charge and use its native disable value.
- Reject malformed saved device entries and prevent exceeding the saved-device bound before touching hardware; strengthen lock-file checks.
- Preflight every privileged destination before installation/removal, preserve files after service-stop failure, and support repeated removal.
- Add isolated frontend/backend installer checks, malformed-response tests, real QML failure/recovery coverage and a root marketplace preview.

## 0.1.0 — Omacharge community preview

- Integrate hardware-aware charge limits into the existing Omarchy power panel.
- Add native sysfs adapters and an optional Framework tool adapter.
- Add independent-battery controls, fixed conservation modes, validated custom percentages and safe threshold write order.
- Add authenticated root helper, atomic saved state, and boot/hotplug/resume restoration.
- Include installer, removal script, compatibility notes, CI tests and a real QML runtime harness.
- Verify the Apple Silicon path on an M1 Pro MacBook Pro; other adapters await physical-device reports.

- Publish as `io.github.kartikkabadi.omacharge` with matching Omafan-family branding, an ImageGen banner, Vantablack screenshot/MP4/GIF previews, install and migration guides, contribution notes and security guidance.
- Theme the custom-limit pickers and verify popup keyboard ownership.
