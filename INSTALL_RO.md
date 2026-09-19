# Instalare / Update – v0.2.0 TEST

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
2. Creează release/tag `v0.2.0`.
3. În HACS actualizează integrarea la `v0.2.0`.
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
