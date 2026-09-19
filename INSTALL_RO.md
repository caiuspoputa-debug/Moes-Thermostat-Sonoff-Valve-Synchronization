# Tuya ↔ Sonoff Climate Bridge v0.1.0 TEST

## Ce este această versiune
Prima versiune de test a bridge-ului bidirecțional dintre un termostat Moes/Tuya și una sau mai multe valve Sonoff TRVZB.

### Regula critică implementată
Cât timp o valvă Sonoff este `off`, integrarea NU execută niciodată `climate.set_temperature` pe acea valvă.

Pornirea unei valve este:
1. `climate.set_hvac_mode(..., heat)`
2. așteaptă confirmarea `state == heat`
3. tolerează starea tranzitorie `heat / 7°C`
4. așteaptă restaurarea targetului intern al Sonoff (maxim ~5.5 s)
5. doar apoi trimite temperatura de lucru dorită

La oprire trimite numai `set_hvac_mode(off)`.

## Asocierea dispozitivelor
Integrarea este instalată o singură dată. Fiecare config entry reprezintă o cameră/zonă.

În UI alegi din dropdown:
- numele zonei
- termostatul Moes/Tuya
- una sau mai multe valve Sonoff TRVZB
- frost temperature Sonoff (implicit 7°C)

Pentru cele 4 termostate, adaugi integrarea de 4 ori și faci cele 4 asocieri. Nu modifici codul.

## Instalare
1. Copiază folderul:
   `custom_components/tuya_sonoff_climate_bridge`
   în:
   `/config/custom_components/`
2. Repornește Home Assistant.
3. Settings → Devices & services → Add integration.
4. Caută `Tuya ↔ Sonoff Climate Bridge`.
5. Pentru primul test selectează:
   - Moes: `climate.th_dormitor`
   - Sonoff test: `climate.sonoff_a48011e07b`
   - Frost: `7.0`
6. Salvează.

Important: la încărcarea integrării NU se trimit comenzi inițiale către dispozitive. Sincronizarea începe la prima schimbare reală făcută după setup.

## Ce sincronizează v0.1.0
### Moes → Sonoff
- target modificat în Moes OFF: memorează targetul; Sonoff rămâne OFF
- Moes OFF → HEAT: pornește Sonoff în siguranță, apoi trimite targetul
- target modificat în Moes HEAT: trimite targetul către Sonoff
- Moes HEAT → OFF: oprește Sonoff fără temperatură

### Sonoff → Moes
- target modificat în Sonoff HEAT: trimite targetul către Moes
- Sonoff HEAT → OFF: oprește Moes și celelalte valve ale zonei
- Sonoff OFF → HEAT / 7°C: NU trimite 7°C către Moes; așteaptă targetul real
- după apariția targetului real: actualizează Moes și celelalte valve ale zonei

## Limitări deliberate în v0.1.0
- Sunt sincronizate numai modurile `off` și `heat`.
- `auto` nu este propagat încă, fiindcă nu l-am caracterizat prin teste.
- `hvac_action` nu este folosit pentru decizia ON/OFF.
- Nu aplică factor ×5/÷5. Bridge-ul folosește valorile deja normalizate din `climate.th_*`.

## Loguri
Integrarea scrie temporar mesaje la nivel WARNING pentru ca testele să fie ușor de urmărit în Settings → System → Logs.
Caută `tuya_sonoff_climate_bridge` sau mesajele care încep cu numele zonei.
