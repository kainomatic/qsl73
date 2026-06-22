# ADR-0013: Rufzeichen-Zerlegung und Zeit-Match-Logik

**Status:** Accepted

## Kontext

Analyse der echten Test-DB (428 QSOs, → `docs/discovery.md` §5.4) ergab:
- 10 von 403 Gegenstationen tragen einen `/`-Zusatz (Portabel-Suffixe wie `/P`, `/QRP`;
  Länderpräfixe bei Gast-Operationen; ein Grenzfall mit mehrdeutigem Regions-Suffix).
- Die eigene `stationcallsign`-Spalte enthält drei verschiedene Werte, darunter einen
  portablen eigenen Call. Ein starrer `To == own_callsign`-Vergleich würde portabel
  adressierte Karten fälschlicherweise verwerfen.

Zusätzlich ist unklar, wie Zeit-Kollisionen (zwei QSOs derselben Station am selben Tag)
aufgelöst werden sollen, wenn eine Karte nur das Datum, aber keine genaue Uhrzeit nennt.

## Entscheidung

### 1. Stammrufzeichen-Zerlegung

Rufzeichen mit `/` werden nach folgender Priorisierung zerlegt:

| Fall | Regel | Stammrufzeichen |
|------|-------|-----------------|
| a) | Teil nach `/` ist bekanntes Suffix (`matching.portable_suffixes`) | Teil vor `/` |
| b) | Teil vor `/` ist bekannter ITU-Länderpräfix (Code-Datendatei) | Teil nach `/` |
| c) | Beide Seiten unklar | → **unsicher** (kein erzwungenes Match) |

Die pflegbare Suffix-Liste (`P`, `M`, `MM`, `AM`, `QRP`, `A`, `R`, `T`) liegt in
`config.yaml` unter `matching.portable_suffixes`. Unbekannte Suffixe → Fall c), kein Absturz.
Die ITU-Länderpräfix-Liste wird als Code-interne Datendatei geführt (zu umfangreich für Config).

### 2. Suffix-Unterschied-Regel

Stimmt das Stammrufzeichen überein, aber der Zusatz unterscheidet sich (z. B. Log `DL1XXX/P`,
Karte `DL1XXX`):
- Datum + Band + Mode eindeutig → **sicher**.
- Irgendeine Unschärfe bei diesen Feldern → **unsicher**. Nie raten.

### 3. Eigener Call gegen alle stationcallsign-Werte

Die `To`-Zugehörigkeitsprüfung vergleicht (mit Stammrufzeichen-Zerlegung) gegen:
- `log4om.own_callsign` aus der Config (manueller Anker/Fallback).
- Alle in der Log4OM-DB vorkommenden `stationcallsign`-Werte.

Stimmt keiner überein → Karte überspringen.

### 4. Zeit-Match-Logik

Primäres Matching auf **Tag-Ebene** (keine Uhrzeit erforderlich).
Tie-Breaker: Bei mehreren gleichwertigen Kandidaten am selben Tag wird die Uhrzeit mit
Toleranz ± 30 Minuten genutzt. Kein eindeutiger Kandidat nach Tie-Breaker → **unsicher**.
Toleranzwert wird in Schritt 4 empirisch überprüft.

## Konsequenzen

**Positiv:**
- Portabel-Suffixe und Gast-Operationen werden korrekt aufgelöst.
- Portabel geloggte eigene Calls werden erkannt, ohne manuelle Config-Pflege.
- Zeit-Kollisionen landen statt eines Zufalls-Treffers sauber im manuellen Pfad.

**Negativ / Risiken:**
- ITU-Länderpräfix-Datendatei muss gepflegt werden (einmalig, selten).
- Fall c) (mehrdeutiger `/`-Zusatz wie `/IF9`) schickt die Karte in den manuellen Pfad —
  vertretbar, da dies ein Grenzfall ist.
- Suffix-Liste in Config muss bei Bedarf erweitert werden; Dokumentation im Setup-Assistenten.
