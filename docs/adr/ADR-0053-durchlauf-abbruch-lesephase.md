# ADR-0053: Durchlauf-Abbruch in der Lesephase (cancel_event-Mechanik)

**Status:** Accepted

## Kontext

Ein laufender Massen-Durchlauf (`run_pass`) soll abbrechbar sein.
Die Lesephase schreibt nicht — Abbruch ist sicherheitstechnisch unkritisch.
Drei Designfragen mussten geklärt werden:

1. **UI**: Eigener „Abbrechen"-Button oder Button-Umwandlung?
2. **Teilergebnis**: Verwerfen oder anzeigen?
3. **Abbruchposition**: Sofort oder nur an sicherer Stelle?

Issue #31, aufgebaut auf ADR-0023 (Queue-Pattern) und ADR-0022 (RunResult-Struktur).

## Entscheidungen

### V1 — Button-Umwandlung

Der „Durchlauf starten"-Button wandelt sich während des Laufs in „Durchlauf abbrechen"
(Text + Command wechseln; gleicher Button, kein separates Widget).
Nach Lauf-Ende ODER Abbruch zurück auf „Durchlauf starten".

**Begründung:** Platzsparend; Status wird implizit durch den Button kommuniziert;
kein zweites Widget das bei normalem Betrieb deaktiviert ist.

### V2 — Teilergebnis anzeigen

Bei Abbruch werden die bis dahin vollständig gelesenen Karten als normales Ergebnis
in der Trefferliste angezeigt.
Ein dezenter Status-Hinweis kennzeichnet es als Teilergebnis:
„Durchlauf abgebrochen — Teilergebnis: N Karten gelesen."
Kein modaler Dialog.

**Begründung:** Der Nutzer kann mit dem Teilergebnis sofort weiterarbeiten
(manuelle Zuordnung, Schreiben). Verwerfen wäre Informationsverlust ohne Mehrwert.

### V3 — Abbruch nur an der Kartengrenze (Datensicherheit vor Reaktionszeit)

Das Stop-Flag wird **ausschließlich am Schleifenanfang**, vor Beginn der nächsten Karte,
geprüft. Mitten in der Verarbeitung einer Einzelkarte wird **nie** abgebrochen.
Eine Karte, die gerade ausgewertet wird, wird immer vollständig fertig verarbeitet.

Akzeptierte Verzögerung: 1–5 s im Worst Case.

**Begründung:** Jede Karte im Teilergebnis ist garantiert vollständig
(kein halbes `CardResult`). Die Lesephase ist seit ADR-0051 rein OCR-basiert —
eine Einzelkarte dauert < 50 ms; die Verzögerung ist im Alltag nicht spürbar.

### Signalmechanik — cancel_event statt Rückgabe-Flag

`run_pass` erhält einen optionalen Parameter `cancel_event: threading.Event | None = None`.
Das Event wird im Hintergrund-Thread von `RunController.start_run()` erstellt und
über `RunController.cancel_run()` gesetzt (threadsicher, idempotent, kein Lock nötig).

**Alternativen verworfen:**
- `_stop_flag: bool` — nicht threadsicher ohne Lock.
- Separater Rückgabeweg (Exception) — aufwändiger, bricht die normale Rückgabepfad-Logik.

### cancelled-Flag im RunResult (ADR-0022-Erweiterung)

`RunResult` erhält ein neues Feld `cancelled: bool = False`.
Das Flag wird von `run_pass` gesetzt, wenn die Schleife via cancel_event beendet wurde.
Der Controller legt `RunDoneEvent(result)` in die Queue — kein separater Event-Typ.

**Begründung:** Der GUI-Handler (`_handle_event`) muss ohnehin auf das Ergebnis zugreifen;
ein eigenes `RunCancelledEvent` wäre ein separater Pfad für identische Verarbeitung.
Das `cancelled`-Flag im RunResult hält alles im bestehenden Pfad.

### Verhältnis zu ADR-0030 (#30 — PdfByteCache/Prefetch)

Der Lauf-Abbruch betrifft nur `run_pass` (Lesephase).
`PdfByteCache` (manueller Dialog) läuft unabhängig und wird über seinen eigenen
`stop()`-Aufruf beendet (`_on_close`). Beide Mechaniken konkurrieren nicht.

## Konsequenzen

- `run_pass` ist vollständig rückwärtskompatibel: ohne `cancel_event` identisches Verhalten.
- `RunResult.cancelled` — neues Feld mit Default `False`, bestehende Serialisierungen unberührt.
- Die GUI zeigt bei `cancelled=True` einen Teilergebnis-Hinweis statt der normalen Fertig-Meldung.
- `_run_active: bool` im `MainWindow` verfolgt den Lauf-Zustand für Button-Umwandlung.
- Kein Schreibvorgang wird durch den Abbruch ausgelöst oder beeinflusst.
