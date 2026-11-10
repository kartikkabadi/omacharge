# Changelog

## 0.1.1 — Marketplace submission audit

- Disable stale controls after status failures and validate the complete backend-to-QML protocol.
- Preserve custom edits and the selected battery across changing status readings; clarify setup success and unsupported presets.
- Make helper installation transactional, preflight all files, restore prior files and service state on failure, and bound lock waits and subprocesses.
- Harden executable ownership checks, saved-policy parsing, invalid firmware data handling, TLP detection and driver capability checks.
- Re-read thresholds after firmware switches to Custom mode and avoid redundant mode writes.
- Add installer rollback, security boundary, protocol and QML regression coverage; pin CI actions and test Python 3.11 and 3.14.
- Add a directory preview, direct removal instructions and explicit privilege and hardware-test disclosures.

## 0.1.0 — Omacharge community preview

- Integrate hardware-aware charge limits into the existing Omarchy power panel.
- Add native sysfs adapters and an optional Framework tool adapter.
- Add independent-battery controls, fixed conservation modes, validated custom percentages and safe threshold write order.
- Add authenticated root helper, atomic saved state, and boot/hotplug/resume restoration.
- Include installer, removal script, compatibility notes, CI tests and a real QML runtime harness.
- Verify the Apple Silicon path on an M1 Pro MacBook Pro; other adapters await physical-device reports.

- Publish as `io.github.kartikkabadi.omacharge` with matching Omafan-family branding, an ImageGen banner, Vantablack screenshot/MP4/GIF previews, install and migration guides, contribution notes and security guidance.
- Theme the custom-limit pickers and verify popup keyboard ownership.
