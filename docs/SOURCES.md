# Reference sources

Read-only research references used to implement the documented interfaces:

- Linux power-supply ABI: https://github.com/torvalds/linux/blob/master/Documentation/ABI/testing/sysfs-class-power
- TLP vendor compatibility documentation: https://linrunner.de/tlp/settings/bc-vendors.html
- TLP reference adapters, reviewed at commit `abb780be4f08916ff49103b461d741065b323777`: https://github.com/linrunner/TLP/tree/abb780be4f08916ff49103b461d741065b323777/bat.d
- Framework tool command and output format, reviewed at commit `758de92afd11cc989099eeff694840c7a95ce016`: https://github.com/FrameworkComputer/framework-system/blob/758de92afd11cc989099eeff694840c7a95ce016/framework_lib/src/commandline/mod.rs
- Framework examples: https://github.com/FrameworkComputer/framework-system/blob/main/EXAMPLES.md
- Omarchy base panel and model, from installed Omarchy 4.5.0: https://github.com/omacom/omarchy
- Omarchy Apple Silicon package support: https://github.com/omacom/omarchy-mac-pkgs

The native sysfs adapters here are an independent Python implementation. No TLP or Framework source code is redistributed. Framework's installed tool is an optional runtime dependency only on relevant machines.
