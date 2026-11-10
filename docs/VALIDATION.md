# Validation record — version 0.1.0

Date: 10 November 2026.

## Physical device

- Apple MacBook Pro 14-inch (2021), M1 Pro; Arch Linux ARM, Omarchy 4.5.0, kernel `7.2.11-14-1-ARCH`.
- Native detection identifies `macsmc-battery` and offers exactly 80/100 maximums.
- Protected helper installation completed; executable is root-owned, mode 0755. Saved JSON is root-owned, mode 0644.
- Authenticated set operation returned and read back an 80% maximum and 75% restart, saved in both Battery Care's config and Asahi's restore config.
- Starting `omarchy-battery-care.service` restored the saved setting and exited successfully: `restored=[macsmc-battery]`, no errors, systemd result success/status 0.
- Service is enabled for boot; udev and resume hooks are installed. An actual reboot and suspend/resume cycle were not performed as part of this verification.
- Live battery panel loaded in the original bar position with the correct maximum and saved status. Stock power profiles remain present. The previous prototype is disabled and preserved.

## Automated tests

45 Python unit tests pass. Coverage includes vendor discovery and application, independent dual batteries, shared platform controls, driver-advertised discrete values, automatic restart thresholds, valid write order, read-back rejection, partial writes, saved-state restore, changed-machine rejection, missing/external devices, corrupt config, symlink escape rejection, fixed command arguments, TLP conflict handling, and privilege fallback behavior.

The real Quickshell QML component was loaded offscreen with a fake unprivileged backend. Its actual preset signals performed subprocess round trips, returned state updated the buttons, custom driver-specific pickers loaded, restart gaps were enforced, and repeated status refresh preserved the editor instance. A synthetic demonstration image is included; it contains no real user data.

Plugin manifest validation, Python compilation, shell syntax checks, and systemd unit verification pass on the installed machine.

## Community testing still needed

Other adapters are implementation- and fixture-tested, not physically certified. This distinction applies to ASUS, Dell, ThinkPad including SMAPI, Lenovo conservation, Huawei, LG, MSI, Samsung, Sony, System76, Toshiba, Tuxedo, ChromeOS EC, Wilco and the optional Framework tool fallback. Testers should report exact laptop model, kernel, driver, request and read-back; a vendor name is insufficient evidence.

Driver read-back is an acknowledgement, not independent electrical measurement. Firmware can ignore or misreport a setting. The plugin rejects mismatches and does not silently round them into a claimed success.
