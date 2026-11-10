# Omacharge validation — version 0.1.2

Date: 10 November 2026.

## Version 0.1.2 submission review

- 98 Python tests and 10 JavaScript protocol tests pass. The suite includes the earlier 0.1.1 submission fixes and the extended audit below.
- The actual QML component passes preset, custom-picker, stable editor/draft, stale-read, recovery and setup-message checks against simulated hardware.
- Root `preview.png` is a labelled real-QML sample for the directory card. README screenshots and demo media use the same explicitly simulated states.
- The protected helper was installed through the normal authenticated setup path on the Mac below. Status confirmed maximum 80%, restart 75%, saved policy, no config error or conflict. An authenticated set request for the existing 80% limit succeeded and read back 80/75 while the battery remained at 80% and Not charging.
- Python compilation, shell syntax, manifest, systemd unit and whitespace checks pass. CI tests Python 3.11 and 3.14 and both JavaScript suites.

A physical reboot/resume and other laptop models remain unverified. Simulated coverage does not establish physical compatibility.

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

98 Python unit tests and 10 JavaScript protocol tests pass. Coverage includes vendor discovery and application, independent dual batteries, shared platform controls, driver-advertised discrete values, automatic restart thresholds, valid write order, read-back rejection, partial writes, saved-state restore, changed-machine rejection, missing/external devices, corrupt config, symlink escape rejection, fixed command arguments, TLP conflict handling, and privilege fallback behavior.

The installer tests cover preflight rejection, protected destination checks, transaction rollback, service enablement and active-state recovery, removal failures, file bounds and lock deadlines. Audit tests cover writable executable ancestors, corrupt/non-UTF-8 state, fail-closed service detection, outdated-helper fallback and rejected handshakes. Protocol tests reject malformed nested data, excessive payloads and invalid choices before QML binding.

The real Quickshell QML component was loaded offscreen with a fake unprivileged backend. Its actual preset signals performed subprocess round trips, returned state updated the buttons, custom driver-specific pickers loaded, restart gaps were enforced, repeated status refresh preserved the editor and unsaved selection, failed reads disabled stale writes, recovery cleared transient errors, and setup displayed its own success message. A synthetic demonstration image is included; it contains no real user data.

Plugin manifest validation, Python compilation, shell syntax checks, and systemd unit verification pass on the installed machine.

## Community testing still needed

Other adapters are implementation- and fixture-tested, not physically certified. This distinction applies to ASUS, Dell, ThinkPad including SMAPI, Lenovo conservation, Huawei, LG, MSI, Samsung, Sony, System76, Toshiba, Tuxedo, ChromeOS EC, Wilco and the optional Framework tool fallback. Testers should report exact laptop model, kernel, driver, request and read-back; a vendor name is insufficient evidence.

Driver read-back is an acknowledgement, not independent electrical measurement. Firmware can ignore or misreport a setting. The plugin rejects mismatches and does not silently round them into a claimed success.

The public package includes a separate Omacharge ImageGen banner and three Vantablack UI previews with matching MP4/GIF media. The preview fixtures are explicitly labelled; they do not add physical-device claims.
