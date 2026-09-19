# Moes Thermostat – Sonoff Valve Synchronization

Home Assistant custom integration for bidirectional synchronization between a Moes/Tuya thermostat and one or more Sonoff TRVZB radiator valves.

## What it does

- Synchronizes HVAC mode in both directions.
- Synchronizes target temperature in both directions.
- Supports one Moes thermostat controlling one or more Sonoff TRVZB valves.
- Keeps the Sonoff frost-protection temperature separate from the normal working target.
- Never sends `climate.set_temperature` to a Sonoff TRVZB while that valve is `off`.
- Waits for the Sonoff valve to confirm `heat` before sending the working target.
- Ignores the temporary Sonoff `heat / 7°C` transition seen during startup.
- Includes anti-loop protection so bridge-generated confirmations are not treated as new user commands.

## Verified behavior

### Moes thermostat

- The target temperature remains valid while the thermostat is `off`.
- Changing the target while `off` does not automatically enable heating.
- `hvac_action` may be unavailable while the thermostat is in `heat`, so the bridge uses HVAC mode as the primary state.

### Sonoff TRVZB

When the valve is `off`, Home Assistant reports the frost-protection target (typically 7°C), not the normal working target.

Observed startup sequence:

```text
off / 7°C
→ heat / 7°C
→ heat / restored target
→ heating
```

Observed shutdown sequence:

```text
heat / working target
→ off / working target
→ off / 7°C
→ action off
```

The bridge therefore keeps its own working target and never treats the Sonoff frost value as the normal heating setpoint.

## Configuration

Each bridge entry is configured from the Home Assistant UI:

- Zone name
- One Moes/Tuya climate entity
- One or more Sonoff TRVZB climate entities
- Sonoff frost-protection temperature (default: 7°C)

This makes it possible to create several room mappings without editing YAML.

Example:

```text
Dormitor:
  climate.th_dormitor
    ↔ climate.sonoff_a48011e039

Salon:
  climate.th_salon
    ↔ climate.sonoff_xxxxx1
    ↔ climate.sonoff_xxxxx2
```

## Installation with HACS

1. Add this repository to HACS as a custom repository of type **Integration**.
2. Download the latest release.
3. Restart Home Assistant.
4. Go to **Settings → Devices & services → Add integration**.
5. Search for **Tuya ↔ Sonoff Climate Bridge**.
6. Select the Moes thermostat and the Sonoff TRVZB valve(s) for the zone.

## Manual installation

Copy:

```text
custom_components/tuya_sonoff_climate_bridge
```

to:

```text
/config/custom_components/tuya_sonoff_climate_bridge
```

Then restart Home Assistant.

## Test status

Current version: **v0.1.0 test**

The first test should be performed with a single Moes thermostat and a single Sonoff TRVZB valve before expanding to all zones.

## Safety rule

The bridge must never call `climate.set_temperature` on a Sonoff TRVZB while that valve is `off`.

The Sonoff value shown while off (normally 7°C) is treated as frost protection, not as the normal working setpoint.
