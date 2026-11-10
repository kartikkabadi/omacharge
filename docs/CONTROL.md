# Controls and saved settings

Open the existing battery icon. The charge section describes the detected
interface and its current driver-reported setting.

## Battery percentage and the Apple charge limit

The bar and panel use the same desktop/UPower percentage and integer rounding.
The percentage is never capped at the selected charge limit.

On Apple Silicon, the native battery controller reports its own percentage.
UPower can instead estimate the level from remaining energy divided by full
energy. These estimates can differ: on the test Mac, Apple reported 80% while
UPower reported 82.9%, displayed as 82%. Both the native driver and UPower
reported that charging was paused, with a verified 80/75 limit and zero charge
power.

The charge card labels this **Apple charge limit** and, when the readings differ,
shows **Apple battery level** and **Desktop estimate** together. This comparison
requires one identified Apple battery with fresh readings; it is omitted for
multi-battery aggregates and unavailable telemetry. It explains the two scales;
it does not change the charge limit or force discharge.

## Presets

**Battery care** selects the valid stop value nearest 80% on a percentage-based
interface. On fixed conservation interfaces it enables the care mode. This is
not always an 80% limit: some firmware chooses 60% or another fixed value.

**Full charge** selects the interface's full-charge setting or disables its
conservation mode. This selection is saved too; it is not a one-time override.

## Custom limits

Custom pickers appear only when the adapter exposes useful alternatives. Stop
choices come from the adapter or explicit driver-advertised values. Start choices
are filtered to keep the required gap below Stop. Choosing a value does not apply
it until you press **Apply custom limits**.

Apple and MSI firmware derive the restart threshold themselves, so Omacharge
does not offer a separate start picker. Lenovo conservation percentages cannot
be read reliably, so the panel displays a mode rather than an invented number.

## Multiple batteries

Independent interfaces have a card for each battery. A change applies to that
card only. A platform-wide interface has one **All batteries** card because its
settings are shared. The standard hero reading still comes from Omarchy/UPower;
it is separate from the individual charge-control cards.

## Holding a limit

A limit pauses charging; it is not a discharge program. While connected to a
suitable charger, the laptop normally uses external power and stays near the
maximum. The lower threshold is the condition for restarting charging if charge
falls. It does not force periodic 80→20 or 80→75 cycles.

Some machines retain settings while off. Others reset them; the plugin restores
saved intent when Linux and the required driver are available again.

## Saved state and failures

The driver must report the requested setting before it is saved. **Saved for
restart** means the current read-back matches a saved selection. A driver error,
rounded/mismatched read-back or persistence failure is shown in the panel. Some
settings may already have changed after a partial operation; check the refreshed
current reading before retrying. A failed operation is never automatically
repeated using a different privilege route.

## Keyboard

| Key while the panel is open | Action |
|---|---|
| `8` | Battery care for the selected battery |
| `0` | Full charge for the selected battery |
| Arrows / `h j k l` | Navigate charge presets and power profiles |
| Enter / Space | Activate the highlighted choice |
| Esc | Close the panel |

Use the pointer to select a battery in a multi-battery layout and to open custom
pickers. Their arrow keys operate the open list. Right-clicking the bar icon
keeps Omarchy's percentage toggle.
