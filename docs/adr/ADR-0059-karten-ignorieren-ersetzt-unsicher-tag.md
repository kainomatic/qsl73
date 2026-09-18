# ADR-0059: Karten ignorieren — ersetzt den ungenutzten Unsicher-Tag

**Status:** Accepted

## Kontext

Desktop-Review (am Code geprüft): `tags.uncertain` war faktisch toter Code.
`log4om_write`/`run.write_selected` kennt zwar den Parameter `uncertain_doc_ids`
und setzt bei gesetztem Wert den `tags.uncertain`-Tag, aber `gui/controller.
start_write` hat diesen Parameter nirgends an `write_selected` übergeben — der Tag
wurde in der gesamten App nie gesetzt. KONZEPT §8 beschrieb damit ein nicht
existierendes Verhalten. Der ANZEIGE-Status „Unsicher" (`MatchResult.UNCERTAIN`,
die Matching-Einstufung) ist davon unabhängig und bleibt unverändert bestehen —
betroffen ist ausschließlich der ungenutzte Paperless-Tag-Slot.

Zusätzlicher, neuer Bedarf (DF1DS): Manche Karten sind nie zuordenbar — fremdes
Log, das QSO fehlt in der DB, oder eine eQSL/LoTW-Ausdruck wurde versehentlich mit
`qsl-card` getaggt. Solche Karten sollen dauerhaft aus dem Lauf verschwinden und
jederzeit wieder zurückgeholt werden können, ohne das Logbuch zu berühren.

## Entscheidung

1. **Ignorierliste = Paperless-Tag, kein lokaler Zustand.** Der Tag-Slot
   `tags.uncertain` wird durch `tags.ignored` ersetzt — weiterhin nur drei
   Tag-Felder (`input`, `confirmed`, `ignored`), kein viertes. Der Tag-Name ist wie
   bei den anderen Tags frei wählbar (Dropdown aus Paperless oder „Anlegen" mit
   eigenem Namen im Setup-Assistenten/den Einstellungen); `qsl-ignoriert` ist nur
   der Default-Vorschlag.
2. **Ignorieren/Wieder-Aufnehmen wirkt SOFORT beim Klick** (nur Paperless-Tag,
   Log4OM-DB unberührt, jederzeit umkehrbar). Das ist eine ausdrückliche Ausnahme
   zur KONZEPT-§5-Garantie „vor 'Jetzt schreiben' weder DB noch Tags" — diese
   Garantie schützt das Logbuch (Schreibzugriff auf die SQLite-Datei) und bleibt
   dafür uneingeschränkt gültig; ein Paperless-Tag auf einem bereits im
   Eingangskorb liegenden Dokument berührt weder DB noch Backup-Pfad.
3. **Kein Bestätigungsdialog.** Ein Umschalt-Button „Ignorieren" ⇄ „Nicht mehr
   ignorieren" ausschließlich im manuellen Zuordnungsdialog (nur für
   UNCERTAIN/NO_MATCH-Karten — CERTAIN-Karten öffnen diesen Dialog nie). Frühere
   Ignorierungen werden über einen neuen Menüpunkt „Bearbeiten → Ignorierte
   Karten…" zurückgeholt (Mehrfachauswahl, „Wieder aufnehmen").
4. **Ausschluss beim Laden serverseitig**, gleicher Mechanismus wie ADR-0032
   (`tags__id__none`, jetzt mit mehreren Tags kommagetrennt): `run_pass` schließt
   `confirmed` UND `ignored` aus.
5. **QSL73 legt den Ignoriert-Tag NICHT automatisch beim Ignorieren an**
   (ADR-0031 §5 bleibt unverändert gültig). Fehlt der Tag (leer konfiguriert oder
   nicht in Paperless vorhanden), erscheint ein Klartext-Hinweis statt eines
   Traceback-Dialogs; kein `create_tag`, kein PATCH, kein Audit-Eintrag. Anlegen
   geschieht ausschließlich im Setup-Assistenten/den Einstellungen über den
   bestehenden „Anlegen"-Weg (`matching_algorithm=0`).
6. **Config-Migration übernimmt den alten `uncertain`-Wert NICHT.** `config_version`
   1 → 2: `tags.uncertain` wird verworfen, `tags.ignored` bekommt den Default
   `qsl-ignoriert`. Begründung: der alte Name wäre irreführend für die neue
   Bedeutung, und hinge der alte Tag entgegen dem Befund doch an irgendwelchen
   Dokumenten (z. B. durch externe Manipulation), würden diese beim nächsten Lauf
   still ausgefiltert — lieber ein bewusster Neustart mit dem Default-Namen.

## Konsequenzen

- Kein Verhaltensbruch für bestehende Läufe: `tags.uncertain` wurde nie gesetzt,
  also kann der Wegfall keine vorhandenen Paperless-Tags verwaisen lassen.
- Alte `config.yaml` (v1) lädt weiterhin fehlerfrei; nach dem Update muss der
  Ignoriert-Tag einmalig in den Einstellungen ausgewählt oder angelegt werden,
  bevor das Ignorieren-Feature nutzbar ist (README-Hinweis).
- `write_selected` verliert den nie genutzten `uncertain_doc_ids`-Parameter samt
  Tag-Block (toter Code entfernt).
- `RunResult.ignored_count` (additiv, Default `0`) zeigt der Statuszeile, wie
  viele Karten aktuell ignoriert sind — ein Zählfehler ist nicht fatal (WARNING im
  Log, Wert 0), damit ein Paperless-Hänger den Lauf nicht abbricht.
- Undo einer Papier-QSL-Bestätigung bleibt weiterhin V2 (KONZEPT §18) — Ignorieren
  betrifft ausschließlich Karten, die noch NICHT geschrieben wurden.

## Nachtrag (Review f8f3728) — Race beim Schließen während eines laufenden Aufrufs

Review-Befund: main_window liest `dlg.ignored` erst NACH dem Schließen des Dialogs.
Schließt der Nutzer den Dialog (Speichern/Speichern-und-nächste/Nächste/Abbrechen/
Fenster-X), während der Ignorieren/Wieder-Aufnehmen-Netzwerkaufruf noch läuft
(zwischen Klick und Antwort), ist der Paperless-Tag zu diesem Zeitpunkt ggf. bereits
gesetzt — main_window trägt die Karte aber mangels `dlg.ignored`-Update nicht als
ignoriert nach; sie bliebe fälschlich in Liste/Workflow/Schreib-Korb sichtbar.

**Entscheidung:** `gui/manual_assignment.py` führt einen `_in_flight`-Zustand
(True zwischen Klick und Antwort). Solange `_in_flight`, sind alle vier
Workflow-Buttons (Speichern, Speichern und nächste, Nächste, Abbrechen) gesperrt
und `WM_DELETE_WINDOW` (Fenster-X) wird ignoriert — der Dialog ist erst nach der
Antwort (Erfolg oder Fehler) wieder schließbar. Die reine Funktion
`dialog_buttons_state(in_flight, ignored, has_selection, has_next)` kapselt die
Freigabe-Logik tk-frei und testbar; außerhalb von `in_flight` unverändert
`save_buttons_enabled()`. Der Ignorieren-Button-Tooltip folgt jetzt ebenfalls dem
Zustand (`ignore_button_tooltip()`, `_Tooltip.set_text()` in `gui/tooltip.py`).

Zusätzlich in diesem Nachtrag behoben: `paperless.list_documents_with_all_tags`
fordert jetzt nur `fields=id,title,created,added` an (statt des vollen
Dokuments inkl. OCR-Text); die Auto-Matching-Warnung im Setup-Assistenten
(`wizard_logic.auto_matching_warning`) nennt jetzt korrekt „bestätigt markiert
oder ignoriert" statt der veralteten Formulierung „bestätigt/unsicher markiert".

Keine Änderung an den Entscheidungen 1–6 oben — reine Absicherung der bereits
getroffenen Entscheidung 3 (Umschalt-Button ohne Bestätigungsdialog).

## Querverweis — ADR-0063

Das hier erstmals dokumentierte cross-thread-Tk-Zugriffsmuster (direkter
`self.after(0, …)`-Aufruf aus einem Hintergrund-Thread) trat auch in
`gui/main_window.py::_start_update_check` auf (Issue #40, Fundstelle beim
Tcl-Absturz-Review). ADR-0063 stellt die Update-Prüfung aus demselben Grund auf das
hier etablierte Queue-Polling-Muster (ADR-0023) um.
