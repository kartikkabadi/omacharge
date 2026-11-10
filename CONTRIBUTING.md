# Contributing

Bug fixes, translations and hardware reports are welcome. Start with a clear
issue describing the behavior, or open a focused pull request with the change
and its verification.

For hardware reports, include the exact laptop model, kernel, Omarchy version,
detected driver, requested settings, read-back and observed charging behavior.
Use the compatibility-report issue template. Review diagnostic output before
sharing it; omit credentials, serial numbers and full environment dumps.

Run the checks in [the development guide](docs/DEVELOPMENT.md). Add meaningful
fixture tests when changing detection, write ordering, saved state or privilege
handling. Check the real QML offscreen for interaction changes.

Do not broaden hardware claims from a vendor name or simulation alone. Preserve
license notices and keep UI text in translation catalogs. Keep dynamic device
and error text plain so it cannot be interpreted as markup.
