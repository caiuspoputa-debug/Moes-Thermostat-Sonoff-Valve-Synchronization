# Instalare – Tuya ↔ Sonoff Climate Bridge v0.1.0 TEST

## Instalare prin HACS

1. În HACS, adaugă repository-ul:
   `caiuspoputa-debug/Moes-Thermostat-Sonoff-Valve-Synchronization`
   ca tip **Integration**.
2. Descarcă versiunea `v0.1.0`.
3. Repornește Home Assistant.
4. Mergi la:
   **Settings → Devices & services → Add integration**
5. Caută:
   **Tuya ↔ Sonoff Climate Bridge**
6. Creează câte o asociere pentru fiecare zonă.

## Configurare

Pentru fiecare zonă alegi din UI:

- numele zonei;
- termostatul Moes/Tuya;
- una sau mai multe valve Sonoff TRVZB;
- temperatura anti-îngheț Sonoff (implicit 7°C).

Exemplu pentru test:

- Moes: `climate.th_dormitor`
- Sonoff test: `climate.sonoff_a48011e07b`

## Reguli de siguranță implementate

- Sincronizare bidirecțională ON/OFF.
- Sincronizare bidirecțională a temperaturii de lucru.
- Dacă Sonoff este `off`, integrarea NU execută `climate.set_temperature`.
- La pornirea Sonoff:
  1. trimite `set_hvac_mode("heat")`;
  2. așteaptă confirmarea `heat`;
  3. ignoră starea tranzitorie `heat / 7°C`;
  4. apoi aplică temperatura de lucru.
- La oprirea Sonoff, temperatura de 7°C nu este propagată către Moes.
- Integrarea păstrează separat `working_target`.
- Sunt filtrate confirmările proprii pentru a evita buclele Moes ↔ Sonoff.

## Instalare manuală

Copiază folderul:

`custom_components/tuya_sonoff_climate_bridge`

în:

`/config/custom_components/tuya_sonoff_climate_bridge`

și repornește Home Assistant.

## Important

Aceasta este o versiune de test. Prima validare se face cu o singură pereche Moes ↔ Sonoff înainte de configurarea tuturor zonelor.
