# Omacharge validation

Date: 10 November 2026.

## Version 0.1.1 submission review

- 64 Python tests and 4 JavaScript tests pass. The additions cover privileged
  installer preflight, interrupted/removal scenarios, an isolated frontend install
  with configuration/frontend backups, malformed saved values, impossible
  advertised pairs, Sony disable semantics, Framework timeouts, slow privilege
  operations, response validation and the saved-device bound.
- The real QML runtime harness passes, including a failed status subprocess,
  disabled stale controls, subsequent recovery and an immediate post-action read.
- The three real-QML sample previews render successfully with the revised parser.
  `preview.png` is a copy of the labelled Apple sample, for the marketplace card.
- The revised backend's read-only status was checked on the physical Mac below:
  it read maximum 80%, restart 75%, persisted true, no config error or conflict.
  No hardware setting was changed during this review.
- Manifest validation, Python compilation, shell syntax, systemd unit validation
  and whitespace checks pass. GitHub CI runs Python and JavaScript checks.

The hardware-write and restore-service observations below belong to version
0.1.0. A physical reboot/resume and other laptop models remain unverified; this
review does not convert simulated coverage into physical compatibility claims.

## Version 0.1.0 physical device

- Apple MacBook Pro 14-inch (2021), M1 Pro; Arch Linux ARM, Omarchy 4.5.0, kernel `7.2.11-14-1-ARCH`.
- With external power connected, the battery reached 80% and the native driver reported `Not charging`; the 80/75 thresholds remained active. This confirms the observed hold behavior on this device.
- Native detection identifies `macsmc-battery` and offers exactly 80/100 maximums.
- Protected helper installation completed; executable is root-owned, mode 0755. Saved JSON is root-owned, mode 0644.
- Authenticated set operation returned and read back an 80% maximum and 75% restart, saved in both Battery Care's config and Asahi's restore config.
- Starting `omarchy-battery-care.service` restored the saved setting and exited successfully: `restored=[macsmc-battery]`, no errors, systemd result success/status 0.
- Service is enabled for boot; udev and resume hooks are installed. An actual reboot and suspend/resume cycle were not performed as part of this verification.
- Live battery panel loaded in the original bar position with the correct maximum and saved status. Stock power profiles remain present.

## Automated tests

45 Python unit tests pass. Coverage includes vendor discovery and application, independent dual batteries, shared platform controls, driver-advertised discrete values, automatic restart thresholds, valid write order, read-back rejection, partial writes, saved-state restore, changed-machine rejection, missing/external devices, corrupt config, symlink escape rejection, fixed command arguments, TLP conflict handling, and privilege fallback behavior.

The real Quickshell QML component was loaded offscreen with a fake unprivileged backend. Its actual preset signals performed subprocess round trips, returned state updated the buttons, custom driver-specific pickers loaded, restart gaps were enforced, and repeated status refresh preserved the editor instance. A synthetic demonstration image is included; it contains no real user data.

Plugin manifest validation, Python compilation, shell syntax checks, and systemd unit verification pass on the installed machine.

## Community testing still needed

Other adapters are implementation- and fixture-tested, not physically certified. This distinction applies to ASUS, Dell, ThinkPad including SMAPI, Lenovo conservation, Huawei, LG, MSI, Samsung, Sony, System76, Toshiba, Tuxedo, ChromeOS EC, Wilco and the optional Framework tool fallback. Testers should report exact laptop model, kernel, driver, request and read-back; a vendor name is insufficient evidence.

Driver read-back is an acknowledgement, not independent electrical measurement. Firmware can ignore or misreport a setting. The plugin rejects mismatches and does not silently round them into a claimed success.

The public package includes a separate Omacharge ImageGen banner and three Vantablack UI previews with matching MP4/GIF media. The preview fixtures are explicitly labelled; they do not add physical-device claims.
