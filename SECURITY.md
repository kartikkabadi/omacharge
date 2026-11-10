# Security

Omacharge includes an authenticated root helper that changes battery settings.
The helper is root-owned, validates freshly discovered control IDs and numeric
values, and never accepts a request-supplied filesystem path. Installation and
updates require administrator authentication. No passwordless authorization rule
is installed.

Please report suspected privilege escalation, arbitrary file access or command
execution privately through GitHub's private vulnerability reporting when it is
available. Do not publish credentials or a working exploit in a public issue.
For ordinary compatibility and UI problems, use the regular issue tracker.

Keep the helper and frontend on matching release versions. Use one charge
manager; the plugin deliberately blocks changes while TLP is active. Read-back
and validation cannot correct defective firmware or guarantee battery behavior
under every kernel or hardware failure.
