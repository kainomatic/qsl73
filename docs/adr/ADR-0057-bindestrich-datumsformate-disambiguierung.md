# ADR-0057: Bindestrich-Datumsformate TT-MM-JJJJ/TT-MM-JJ mit >12-Disambiguierung

**Status:** Accepted

## Kontext

Im Beta-Test v0.5.0-beta2 (2026-09-17) endete eine gedruckte Karte mit OCR-Datum
`"14-09-2024"` (Bindestrich, Tag-Monat-Jahr) als „Unsicher" ohne erkanntes Datum.
`normalize_date()` (`src/qsl73/normalize.py`) kannte bis dahin nur Punkt- (`TT.MM.JJ`/
`TT.MM.JJJJ`) und Schrägstrich-getrennte Formate (`MM/DD/YYYY`, `TT/MM/JJ`), aber kein
bindestrich-getrenntes `TT-MM-JJJJ`/`TT-MM-JJ`. Die Formattabelle in KONZEPT.md §6.3
führte das Format ebenfalls nicht.

Der Bindestrich ist im Tokenizer (`run._tokenize`, `_STRIP_CHARS`) bewusst **nicht**
als Trennzeichen enthalten — Kommentar dort: ein führendes/folgendes `-07` (RST-Wert)
darf nicht versehentlich zu `07` entstrippt werden. Das Token `"14-09-2024"` kommt also
bereits heute unverändert bei `normalize_date()` an; es fehlte nur die Format-Erkennung
selbst.

## Entscheidung

`normalize_date()` um ein Bindestrich-Format `TT-MM-JJJJ`/`TT-MM-JJ` ergänzt (Tag und
Monat 1- oder 2-stellig, Jahr 2- oder 4-stellig), mit derselben Mehrdeutigkeitsregel wie
beim bestehenden Schrägstrich-2-stellig-Fall (ADR-0007/ADR-0014 — im Zweifel lieber
unsicher als falsch raten):

- Erstes Feld `> 12` → eindeutig Tag-Monat-Jahr.
- Zweites Feld `> 12` → eindeutig Monat-Tag-Jahr.
- Beide Felder `<= 12` → mehrdeutig → `None` (kein Raten).
- 2-stelliges Jahr wird wie bisher über `_expand_year` (`>= 30` → 19xx, `< 30` → 20xx)
  expandiert.

Das bestehende `YYYY-MM-DD`-Format (4-stelliges Jahr vorne, `fullmatch`) bleibt
unverändert und hat weiterhin Vorrang — dort ist die Reihenfolge der Felder eindeutig,
keine Kollision mit dem neuen Bindestrich-Fall möglich.

Am Tokenizer (`_STRIP_CHARS`) wird nichts geändert — der Bindestrich bleibt bewusst
kein Trennzeichen; ein Test belegt, dass das Token unverändert bei `normalize_date()`
ankommt.

**Abgrenzung:** Kein Erschließen weiterer exotischer Bindestrich- oder sonstiger
Datumsformate (z. B. römische Monatsziffern `17-XI-93`) über diese Entscheidung hinaus —
ADR-0014 bleibt Leitlinie: unbekannte/exotische Formate bleiben bewusst `None` statt
per Sonderregel geraten zu werden.

## Konsequenzen

- Gedruckte Karten mit bindestrich-getrenntem `TT-MM-JJJJ`/`TT-MM-JJ`-Datum werden ab
  sofort korrekt normalisiert statt fälschlich als „Unsicher" ohne Datum zu enden.
- Kein Risiko für bestehende Formate: `YYYY-MM-DD` hat weiterhin Vorrang (eindeutiger
  `fullmatch` mit 4-stelligem Jahr vorne); alle bestehenden Datumstests bleiben unverändert
  grün.
- Zwei im selben Beta-Test-Befund entdeckte, aber nicht umgesetzte Punkte wurden als
  separate GitHub-Issues festgehalten statt hier mitentschieden: Sonderrufzeichen mit
  zwei Ziffern im Rufzeichen-Muster, und OCR-Zeichenverwechslung O/0 und I/1 bei
  Rufzeichen.
