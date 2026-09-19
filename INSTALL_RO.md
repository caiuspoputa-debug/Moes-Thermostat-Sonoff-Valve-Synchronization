# Instalare / Update – v0.2.2 TEST

## Ce este nou

- Orice temperatură raportată de Sonoff cât valva este `off` este considerată temperatură anti-îngheț.
- Valoarea poate fi 7°C, 10°C sau alta; nu mai este hardcodată ca temperatură de lucru.
- Integrarea învață valoarea anti-îngheț reală pentru fiecare Sonoff.
- Opțiune nouă:
  **Afișează pe Moes temperatura anti-îngheț Sonoff când este OPRIT**.
- `working_target` este salvat persistent și este restaurat la pornire.
- Temperatura anti-îngheț nu poate suprascrie `working_target`.

## Update prin HACS

1. Publică fișierele acestei arhive în repository.
2. Creează release/tag `v0.2.2`.
3. În HACS actualizează integrarea la `v0.2.2`.
4. Repornește Home Assistant.
5. Intră la integrare → **Configure** și activează opțiunea de sincronizare vizuală dacă o dorești.

## Test recomandat

Pentru prima zonă:

- Moes: `climate.th_dormitor`
- Sonoff test: `climate.sonoff_a48011e07b`

Testează în această ordine:

1. HEAT la o temperatură normală.
2. OFF.
3. Confirmă că Sonoff raportează frost target.
4. Dacă opțiunea este activă, confirmă că Moes afișează aceeași valoare în OFF.
5. Pornește din nou HEAT și confirmă restaurarea `working_target`.
6. Modifică frost target-ul Sonoff, de exemplu 7°C → 10°C, cât este OFF; confirmă că Moes îl oglindește doar vizual și că la pornire revine temperatura de lucru memorată.


## Fix v0.2.2

În v0.2.0 exista o problemă de ordine la oprirea inițiată din Sonoff:
Moes era oprit, dar frost target-ul era încercat prea devreme.

v0.2.2 face explicit:

1. Sonoff devine OFF.
2. Moes primește OFF.
3. Integrarea așteaptă confirmarea că Moes este efectiv OFF.
4. Abia apoi setează pe Moes frost target-ul Sonoff (7°C, 10°C etc.).
5. `working_target` rămâne memorat separat și nu este înlocuit cu frost target.


## Icon inclus

Arhiva include iconul integrării în două locuri:

- `icon.png` în rădăcina repo-ului
- `custom_components/tuya_sonoff_climate_bridge/icon.png` în pachetul integrării
