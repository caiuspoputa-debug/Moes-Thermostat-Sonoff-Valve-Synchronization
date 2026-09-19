# Moes Thermostat – Sonoff Valve Synchronization

Home Assistant custom integration for safe bidirectional synchronization between a Moes/Tuya thermostat and one or more Sonoff TRVZB radiator valves.

## v0.2.3

This version adds dynamic frost-target handling and optional visual OFF synchronization.

### New behavior

- **Any Sonoff target reported while that Sonoff is `off` is treated as frost target**, regardless of whether it is 7°C, 10°C or another configured value.
- The frost target is learned dynamically per Sonoff valve and is never accepted as `working_target`.
- Optional **Mirror Sonoff frost target on Moes while OFF** setting.
- When visual mirroring is enabled:
  - both devices can show the same frost value while OFF;
  - the real heating target is stored separately;
  - the real target is restored automatically when heating starts.
- `working_target` and learned frost targets are persisted across Home Assistant restarts.
- If the user changes the Moes target while OFF, that becomes the next heating target; with visual mirroring enabled, the display then returns to the frost value while remaining OFF.

## Core safety rule

The bridge **never calls `climate.set_temperature` on a Sonoff valve while that valve is `off`**.

Safe Sonoff start sequence:

```text
OFF
→ set_hvac_mode("heat")
→ wait for confirmed HEAT
→ ignore temporary HEAT/frost target
→ wait for restored working target
→ set desired working target
```

## Bidirectional behavior

### Moes → Sonoff

- Moes OFF → Sonoff OFF.
- Moes HEAT → safely start Sonoff, then apply working target.
- Moes target change in HEAT → Sonoff target change.
- Moes target change in OFF → save as next `working_target`; Sonoff stays OFF.

### Sonoff → Moes

- Sonoff HEAT target change → Moes receives the new working target.
- Sonoff OFF → Moes OFF.
- Sonoff OFF target change (for example frost 7°C → 10°C) → learned as frost only; never propagated as working target.
- Sonoff OFF → HEAT → wait until a non-frost target appears before propagating it.

## Configuration

Each bridge entry has:

- Zone name
- One Moes/Tuya climate entity
- One or more Sonoff TRVZB climate entities
- **Mirror Sonoff frost target on Moes while OFF** (optional)
- Fallback frost temperature (used only until the real OFF value is learned)

For multi-valve zones, the first selected Sonoff valve is used as the preferred visual frost source.

## HACS

1. Add this repository to HACS as a custom **Integration** repository.
2. Install release `v0.2.3`.
3. Restart Home Assistant.
4. Open **Settings → Devices & services → Tuya ↔ Sonoff Climate Bridge**.
5. Configure one entry per zone.


### v0.2.2 fix

Fixed OFF visual synchronization ordering:

```text
Sonoff -> OFF
Moes -> OFF
wait until Moes reports OFF
Moes target -> learned Sonoff frost target (7°C / 10°C / etc.)
```

This fixes the case where Moes successfully turned OFF but kept the previous
working target on screen instead of showing the Sonoff frost value.


## Project assets

- `icon.png` included in the repository root
- `custom_components/tuya_sonoff_climate_bridge/icon.png` included inside the integration package


## v0.2.3

- Visual frost mirroring is now **enabled by default**.
- Fixes upgraded config entries that did not contain the new mirror option.
- Robust Moes OFF visual sequence:
  1. preserve `working_target`;
  2. preload learned Sonoff frost target on Moes;
  3. set Moes HVAC mode to OFF;
  4. wait for confirmed OFF;
  5. verify displayed target;
  6. retry up to three times if needed.
- Adds explicit log messages for OFF visual synchronization.
- Adds repository branding:
  - `brand/icon.png` (256×256)
  - `brand/icon@2x.png` (512×512)


## v0.2.4

Brand asset path fixed for Home Assistant 2026.3+.

Correct structure:

```text
custom_components/
└── tuya_sonoff_climate_bridge/
    └── brand/
        ├── icon.png
        └── icon@2x.png
```

The previous repository-root `brand/` folder was not the location used by Home Assistant for local custom-integration branding.
