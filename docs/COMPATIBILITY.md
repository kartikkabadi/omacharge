# Hardware compatibility

Implemented is not the same as physically tested. The only physical device tested so far is an Apple MacBook Pro 14-inch (2021), M1 Pro. Every row below also has simulated-kernel coverage. Driver interfaces must actually exist; detection never writes a probe value.

| Adapter | Required interface | Controls offered |
|---|---|---|
| Apple Silicon | `macsmc-battery/charge_control_*_threshold` | Stop 80 or 100; restart fixed to 75 or 100 |
| ThinkPad | `thinkpad_acpi` plus standard battery thresholds | Stop 1–100; restart 0–99, below stop |
| Legacy ThinkPad | `smapi/BAT*/start_charge_thresh` and `stop_charge_thresh` | Restart 2–96; stop 6–100 |
| ASUS | `asus_wmi` plus battery end threshold | Stop 1–100; verifies driver response. Some firmware accepts only 40/60/80 |
| Dell | `dell_laptop`, thresholds, and `charge_types` | Restart 50–95; stop 55–100; gap at least 5; enables Custom mode |
| Huawei MateBook | `huawei-wmi/charge_control_thresholds` | Shared pair: restart 0–99, stop 1–100 |
| Lenovo conservation | `ideapad_acpi` and `Long_Life` charge type, or legacy `conservation_mode` | Fixed conservation on/off; exact percentage unknown |
| LG Gram | `lg_laptop` or `lg-laptop`, standard end threshold | 80 or 100 |
| MSI | `msi_ec`, standard end threshold | Stop 10–100; restart is stop minus 10 |
| Samsung | `samsung/battery_life_extender` | Fixed battery-life extender on/off (documented 80%) |
| Sony VAIO | `sony-laptop/battery_care_limiter` | 50, 80, 100 |
| System76 | `system76_acpi`, standard battery thresholds | Stop 1–100; restart 0–99 if exposed |
| Toshiba / Dynabook | `toshiba_acpi`, standard end threshold | 80 or 100 |
| Tuxedo / Clevo | TUXEDO DMI, explicit available start/end threshold lists, `charge_type` | Exact values advertised by driver; enables Custom mode |
| ChromeOS EC v2/v3 | Bound `cros-charge-control` platform driver and battery thresholds | End 1–100; restart 0–99 only if readable |
| Wilco EC | `wilco_charger`, separate `wilco-charger` thresholds and `charge_type` | Shared restart 50–95, stop 55–100, gap at least 5; Custom mode |
| Framework fallback | Framework DMI, no native adapter, root-owned `/usr/bin/framework_tool` | Stop 25–100 through `--charge-limit`; preserves firmware minimum |
| Other explicit-capability drivers | End threshold plus `charge_control_end_available_thresholds`; a readable start threshold also requires advertised start values | Only explicitly advertised values with at least one valid start/stop pair |

Shared platform interfaces produce a single **All batteries** card. Independent standard interfaces produce a card for each battery. Missing/removed batteries and `scope=Device` peripherals are ignored.

## Caveats

- Firmware support cannot be inferred from brand or CPU. Missing interfaces produce a read-only panel, not an attempted raw EC or SMC write.
- Framework's native `cros-charge-control` support depends on model and firmware. If the native interface is absent, install Framework's official tool for the optional fallback. The plugin does not load experimental modules, bypass lockdown, flash firmware, or use force flags. An unreadable Framework limit remains unknown until an authenticated operation can read it.
- Some ThinkPad firmware reports an off-by-one threshold. This release reports mismatches and refuses to save an unconfirmed value rather than silently treating it as exact.
- ASUS may expose an unreadable initial threshold after boot. The adapter still detects it, and verifies a subsequent write. Driver-reported success cannot guarantee that defective firmware enforces the limit.
- Lenovo's fixed conservation percentage may be 60%, 80%, or another model-dependent value. This release displays a mode, never guesses the percentage.
- Unsupported kernels, missing out-of-tree modules, BIOS restrictions, and external power-management software can prevent changes. The plugin reports failures and keeps the last verified saved selection.
- Active TLP blocks changes and restore. Other software that writes the same battery controls should also be configured to avoid competing policies; there is no universal way to detect every custom script.
