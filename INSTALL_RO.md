# Instalare / Update – v0.2.3 TEST

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
2. Creează release/tag `v0.2.3`.
3. În HACS actualizează integrarea la `v0.2.3`.
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


## Fix v0.2.3

În v0.2.0 exista o problemă de ordine la oprirea inițiată din Sonoff:
Moes era oprit, dar frost target-ul era încercat prea devreme.

v0.2.3 face explicit:

1. Sonoff devine OFF.
2. Moes primește OFF.
3. Integrarea așteaptă confirmarea că Moes este efectiv OFF.
4. Abia apoi setează pe Moes frost target-ul Sonoff (7°C, 10°C etc.).
5. `working_target` rămâne memorat separat și nu este înlocuit cu frost target.


## Icon inclus

Arhiva include iconul integrării în două locuri:

- `icon.png` în rădăcina repo-ului
- `custom_components/tuya_sonoff_climate_bridge/icon.png` în pachetul integrării


## Fix v0.2.3

Sincronizarea vizuală OFF este activată implicit.

La oprire:
1. se păstrează `working_target`;
2. Moes primește frost target-ul Sonoff;
3. Moes este trecut în OFF;
4. integrarea verifică valoarea afișată;
5. dacă valoarea nu este corectă, retransmite comanda de până la 3 ori.

În Logs:
- `OFF visual sync OK` = sincronizare reușită;
- `OFF visual sync FAILED` = Moes/Tuya nu a acceptat valoarea.

Brand inclus exact în structura:
- `brand/icon.png`
- `brand/icon@2x.png`


## Fix icon v0.2.4

Iconul a fost mutat în locația corectă pentru Home Assistant 2026.3+:

`custom_components/tuya_sonoff_climate_bridge/brand/icon.png`

și:

`custom_components/tuya_sonoff_climate_bridge/brand/icon@2x.png`

După update este necesar restart Home Assistant. Dacă interfața păstrează iconul vechi/placeholder, fă refresh complet al browserului.


## Fix v0.2.5

- Mesajul `Bridge started` nu mai apare ca warning/error în Home Assistant Logs.
- La pornire, integrarea verifică memoria persistentă.
- Dacă `working_target` este egal cu o temperatură anti-îngheț Sonoff învățată
  (de exemplu 7°C sau 10°C), valoarea este ștearsă automat.
- Valoarea contaminată este eliminată și din storage, deci nu reapare după restart.
- Integrarea NU inventează o temperatură de lucru în locul celei șterse.
- Următoarea temperatură reală setată pe Moes sau observată valid în Sonoff HEAT
  devine noul `working_target`.
