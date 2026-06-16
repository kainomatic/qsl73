# ADR-0012: Robustheit der Kartenauswertung

**Status:** Accepted

## Kontext

Die vollständige Bilderkennung aller 7 Musterkarten (Claude Desktop, 2026-06-16,
→ `docs/discovery.md` §5.3) hat drei Robustheits-Lücken im bisherigen Matching-Design
(§6) aufgedeckt:

1. **QR-Code mit Nicht-QSO-Inhalt:** Eine Karte (Zazzle-Druckdienst) trägt einen
   QR-Code mit Werbe-/Herstellerkennung. Der bisherige Ablauf ging davon aus, dass ein
   dekodierter QR-Code immer QSO-Daten enthält.

2. **Portabler eigener Call:** Eine Karte adressiert den eigenen Call portabel
   (`SV9/[BASISCALL]`). Ein starrer `To == own_callsign`-Vergleich würde diese Karte
   fälschlicherweise verwerfen.

3. **Daten auf der Vorderseite:** Eine Karte hatte die QSO-Tabelle auf der Vorderseite.
   Eine Annahme „QSO-Daten immer auf der Rückseite" wäre falsch.

Zusätzlich haben die Karten neue Datums- und Mode-Varianten gezeigt (§5.3), die eine
Erweiterung der Normalisierungstabellen erfordern.

## Entscheidung

Drei Robustheitsregeln werden in §6 festgeschrieben:

**1. QR-Inhalt-Validierung (§6.2):**
Nach dem Dekodieren eines QR-Codes wird der Inhalt auf gültiges QSO-Format geprüft
(Mindest-Schlüssel `From`, `To`, `Date`, `Band`, `Mode` vorhanden?). Nur bei positivem
Ergebnis wird der QR-Inhalt verwendet. Ungültige QR-Codes (Werbe-/Druckdienst-Codes)
werden ignoriert. Mehrere QR-Codes pro Karte möglich — den ersten mit gültigem QSO-Format
verwenden.

**2. Tolerantes eigenes-Call-Matching (§6.3):**
Der Abgleich von `To` (Karte) gegen den eigenen Call erfolgt Basis-Call-basiert:
Präfixe (`SV9/DH3KR`) und Suffixe (`DH3KR/P`, `/M`, `/MM`) werden abgetrennt.
Optional zusätzlicher Abgleich gegen `stationcallsign`-Werte aus der Log4OM-DB.
Ziel: Portabel-QSLs korrekt dem eigenen Log zuordnen, nicht verwerfen.

**3. Mehrseiten-Auswertung (§6.2/§6.3):**
Alle PDF-Seiten eines Dokuments werden ausgewertet — für QR-Suche (alle Seitenbilder)
und für OCR-Text (Paperless `content`-Feld deckt alle Seiten ab).

**Zusätzlicher Grundsatz:**
Unbekannte Formate (z. B. Datums-Exoten wie römische Monatsziffern) werden **nicht** per
Sonderregel erschlossen. Grundsatz: lieber „nicht normalisierbar" → **unsicher** als ein
fehleranfälliges Ratespiel. Der manuelle Pfad (§9) fängt diese Fälle auf.

Normalisierungstabellen (§6.3) wurden um folgende real aufgetretene Varianten erweitert:
- Datum: `TT Monatsname JJJJ` (`23Apr2025`), US-Spaltenformat (Month/Day/Year getrennt),
  `MM/DD/YYYY`, `MM/DD/YY`.
- Mode: `2×SSB`, `2xSSB` → `SSB`.

## Konsequenzen

**Positiv:**
- Portabel-QSLs werden nicht fälschlicherweise verworfen.
- Werbe-QR-Codes führen nicht zu Falsch-Matches oder Abstürzen.
- QSO-Daten auf der Vorderseite werden zuverlässig gefunden.
- Klare Regel für unbekannte Formate verhindert unerklärliche Falsch-Matches.

**Negativ / Risiken:**
- QR-Validierung erfordert robustes Parsen des QR-Texts (Fehler-Toleranz gegenüber
  Leerzeichen, Feldreihenfolge, Tippvarianten im Key-Namen).
- Basis-Call-Extraktion muss auch verschachtelte Fälle korrekt handhaben
  (z. B. Präfix enthält selbst einen `/`).
- Mehrseiten-Rendering erhöht Bild-Verarbeitungsaufwand; bei einseitigen Karten
  bleibt der Overhead gering.
