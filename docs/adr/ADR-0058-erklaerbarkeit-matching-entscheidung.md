# ADR-0058: Erklärbarkeit der Matching-Entscheidung (MatchReason)

**Status:** Accepted

## Kontext

Beta-Test-Befund (Issue #37): Im manuellen Zuordnungs-Dialog war nicht erkennbar,
WARUM eine Karte als „Unsicher" oder „Kein Treffer" eingestuft wurde. Die
Matching-Engine (`matching.match_card`, ADR-0016/ADR-0056) kennt den Grund intern
an jeder Entscheidungsstelle (fehlendes Rufzeichen, mehrere Kandidaten, Fuzzy-
Treffer, zu wenig übereinstimmende Felder, widersprechendes Feld, mehrdeutige
QSO-Kandidaten, Rufzeichen nicht zerlegbar, Karte nicht an eigenes Rufzeichen
adressiert) — gab ihn aber nicht nach außen.

Entscheidung (DF1DS): Grund als Klartext mit konkreten Werten anzeigen, PLUS immer
die rohen gelesenen Felder — im manuellen Dialog unterhalb der Suchfelder.

## Entscheidung

Die Matching-Engine liefert den Grund als **Daten**, die GUI rendert ihn nur:

- `MatchOutcome` erhält ein additives Feld `reason: Optional[MatchReason] = None`
  (Default `None` — abwärtskompatibel, bestehende Konstruktoraufrufe und Tests
  bleiben unverändert lauffähig).
- `MatchReason` ist eine kleine Dataclass: `code` (stabiler `MatchReasonCode`-Enum-
  Wert, für Logik/Tests), `text` (fertiger deutscher Klartext mit konkreten Werten,
  für die GUI-Anzeige), `details` (strukturierte Rohdaten hinter dem Text, für
  spätere Auswertung/i18n).
- `match_card()` setzt `reason` an JEDER Stelle, an der UNCERTAIN oder NO_MATCH
  entschieden wird; bei CERTAIN bleibt `reason=None`. Codes:
  `NOT_OWN_CALL`, `NO_CALL`, `CALL_NOT_DECOMPOSABLE`, `NO_CANDIDATE`,
  `MULTI_CALL`, `CONTRADICTION`, `FUZZY_CALL`, `TOO_FEW_FIELDS`, `MULTI_QSO`.
  (Der im Issue vorgeschlagene Katalog war ein Vorschlag — zwei zusätzliche Codes,
  `NOT_OWN_CALL` und `CALL_NOT_DECOMPOSABLE`, wurden ergänzt, weil es dafür
  eigene, im Code bereits vorhandene Entscheidungsstellen gibt.)
- Die Grund-Erzeugung selbst beeinflusst die Matching-Entscheidung NICHT — sie
  läuft ausschließlich an Stellen, an denen das Ergebnis (CERTAIN/UNCERTAIN/
  NO_MATCH) bereits feststeht. Für den NO_MATCH-Fall „kein Fremdcall-Kandidat
  trifft ein DB-QSO" (R1, ADR-0056) läuft zusätzlich eine rein diagnostische
  Zweitprüfung (`_diagnose_no_hits`): sie sucht, ob irgendein gelesenes Rufzeichen
  überhaupt ein DB-Rufzeichen trifft (unabhängig von Datum/Band/Mode), um zwischen
  „widersprechendes Feld" (`CONTRADICTION`) und „kein DB-Eintrag überhaupt"
  (`NO_CANDIDATE`/`MULTI_CALL`) zu unterscheiden — auch diese Zweitprüfung ändert
  das Ergebnis nicht, nur den erklärenden Text.
- Klartext-Erzeugung für die GUI ist tk-frei in `gui/filter_util.py`:
  `describe_reason(outcome) -> str` (Grund-Text oder `""` bei CERTAIN) und
  `describe_read_fields(card_fields) -> str` (Format „Rufzeichen X · Datum X ·
  Band X · Mode X · Zeit X", fehlende Felder = „–"; bei mehreren erkannten
  Fremdcall-Kandidaten — `call_from_candidates`, ADR-0056 — werden alle genannt).
- `gui/manual_assignment.py` zeigt unterhalb der Suchfelder zwei read-only,
  umbrechende Zeilen „Grund:"/„Gelesen:"; bei CERTAIN (defensiv, falls der Dialog
  dort je geöffnet wird) entfällt der Block vollständig.

## Abgrenzung

- Keine Änderung der Matching-Regeln selbst (ADR-0016/ADR-0056 bleiben unverändert
  maßgeblich) — `MatchReason` beschreibt nur, was die Regeln bereits entschieden
  haben.
- Hauptfenster-Zeilen-Tooltip (ursprünglich mitgeplant) wurde zurückgestellt:
  die bestehende Tooltip-Infrastruktur (`gui/tooltip.py`, ADR-0047) bindet
  statischen Text an ein ganzes Widget, nicht an einzelne Treeview-Zeilen — eine
  echte Umsetzung bräuchte einen neuen Motion-Tracking-Mechanismus. Als
  Folge-Issue #38 festgehalten.

## Konsequenzen

- Der manuelle Zuordnungs-Dialog erklärt jetzt in Klartext mit konkreten Werten,
  warum eine Karte nicht automatisch bestätigt wurde — spart Rückfragen im
  Beta-Test und im Alltagsbetrieb.
- Kein Verhaltensbruch: alle bestehenden Matching-Tests bleiben unverändert grün,
  weil `reason` rein additiv ist und die Entscheidungslogik nicht anfasst.
- Erweiterbar für spätere i18n (Codes + strukturierte `details` bereits getrennt
  vom deutschen Anzeigetext).
