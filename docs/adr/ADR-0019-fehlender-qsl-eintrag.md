# ADR-0019: Fehlender CT='QSL'-Eintrag → Exception, kein stiller Neuanlegen

**Status:** Accepted

## Kontext

Log4OM legt beim Erstellen eines QSO normalerweise alle 7 Bestätigungstypen an
(QSL, EQSL, LOTW, QRZCOM, HAMQTH, HRDLOG, CLUBLOG). In älteren DB-Versionen
könnte der `CT="QSL"`-Eintrag fehlen. Dies ist offene Frage #3 aus
`docs/discovery.md §6` (Status: offen / Niedrig).

`apply_paper_qsl` (Schritt 5a) begegnet diesem Fall: Es gibt keinen QSL-Eintrag
im `qsoconfirmations`-Array, in den `R="Yes"` gesetzt werden könnte.

## Entscheidung

Bei fehlendem `CT="QSL"`-Eintrag wirft `apply_paper_qsl` eine
`QslEntryNotFoundError` — statt still einen neuen Eintrag anzulegen oder
einen anderen Eintrag zu beschreiben.

**Begründung:**

- **Sicherheit:** Ein stilles Neuanlegen würde Daten schreiben, die Log4OM
  möglicherweise nicht erwartet; unklar, ob die Reihenfolge oder Struktur
  der Einträge für Log4OM relevant ist.
- **Klare Fehlergrenze:** Der Aufrufer (5b) kann die Exception fangen und
  dem Nutzer eine verständliche Meldung zeigen bzw. das QSO überspringen.
- **Schema-Validierung kommt in 5b/5c:** Die Schema-Prüfung (ADR-0004) findet
  vor dem eigentlichen Schreibvorgang statt und soll u. a. sicherstellen,
  dass alle erwarteten Eintragstypen vorhanden sind. `QslEntryNotFoundError`
  ist ein Sicherheitsnetz darunter.

## Konsequenzen

- `apply_paper_qsl` ist bei fehlendem QSL-Eintrag sicher — keine Teilschreibung,
  kein Datenverlust.
- Aufrufer (Schritt 5b) muss `QslEntryNotFoundError` abfangen und als
  Fehlerfall protokollieren.
- `docs/discovery.md §6` Frage #3 bleibt offen für die Schema-Validierung in 5c,
  die das Problem vorgelagert erkennt und eine klare Nutzer-Meldung liefert.
