# ADR-0063: Update-Prüfung nutzt Queue-Polling statt cross-thread self.after

**Status:** Accepted

## Kontext

Issue #40 hielt als zusätzlich zu prüfenden Produktivcode-Punkt fest: `gui/main_window.
py::_start_update_check` rief `self.after(0, …)` **direkt aus dem Hintergrund-Thread**
auf (`threading.Thread(target=_check, daemon=True).start()`; `_check` rief am Ende
`self.after(0, lambda: self._handle_update_result(...))`).

Das ist exakt das cross-thread-Tk-Zugriffsmuster, das im manuellen Zuordnungs-Dialog
(`gui/manual_assignment.py::_on_toggle_ignore`) nachweislich zu Problemen führte — dort
blockierte ein direkter `self.after(0, …)`-Aufruf aus dem Hintergrund-Thread die
verschachtelte `wait_window()`-Eventloop faktisch bis zum Timeout (ADR-0059, behoben
durch Umstellung auf das in `RunController`/`gui/controller.py` etablierte
Queue-Polling-Muster, ADR-0023). Bei `_start_update_check` lief das Symptom bislang
nicht auf, weil die Prüfung nicht in einer verschachtelten `wait_window()`-Schleife
liegt (sondern im normalen `mainloop()`), sondern im ganz normalen Hauptfenster
läuft — das grundsätzliche Risiko (Tk-API-Zugriff aus einem Nicht-UI-Thread ist laut
Tk-Dokumentation nicht threadsicher) bleibt aber dasselbe.

## Entscheidung

`_start_update_check` ruft `self.after(0, …)` nicht mehr direkt aus dem
Hintergrund-Thread auf. Stattdessen bekommt `RunController`
(`gui/controller.py`) eine neue Methode `start_update_check(current_version, channel,
*, manual=False)`, die `check_for_update()` in einem Daemon-Thread ausführt und das
Ergebnis als neues `UpdateCheckDoneEvent(result, manual)` in dieselbe `queue.Queue`
legt, die `MainWindow` bereits für `ProgressEvent`/`RunDoneEvent`/`WriteDoneEvent`/
`ErrorEvent` über `root.after(100, self._poll)` abholt (`_handle_event` bekommt einen
zusätzlichen `elif isinstance(event, UpdateCheckDoneEvent)`-Zweig, der
`_handle_update_result(event.result, manual=event.manual)` aufruft). `manual`
unterscheidet weiterhin automatische Prüfung (`schedule_update_check()` nach
Programmstart) von manueller Prüfung (Menüpunkt „Nach Updates suchen").

**Bestehende Queue statt neuem Event-Kanal:** Es wird dieselbe `self._event_queue`
genutzt, kein separater Update-Kanal — konsistent mit den bestehenden vier
Event-Typen, kein zweiter Poll-Loop nötig, `_handle_event` bleibt der einzige
Dispatch-Ort für Hintergrund-Ergebnisse im UI-Thread.

`_start_update_check` selbst startet keinen eigenen `threading.Thread` mehr (entfernt);
der `import threading` in `main_window.py` entfällt damit als ungenutzt.

## Konsequenzen

- Kein direkter tk-Zugriff mehr aus einem Nicht-UI-Thread in `main_window.py` — alle
  vier bisherigen Event-Typen und der neue `UpdateCheckDoneEvent` laufen über
  denselben `_poll()`/`_handle_event()`-Mechanismus (ADR-0023).
- `check_for_update()` wirft laut `updater.py` intern nie — Netzwerk-/Parse-Fehler
  landen bereits als `UpdateCheckResult(status=ERROR, ...)`; `start_update_check()`
  braucht deshalb (anders als `start_run`/`start_write`) kein eigenes `try/except` mit
  `ErrorEvent`.
- Nutzersichtbares Verhalten unverändert: automatische vs. manuelle Prüfung,
  Statusmeldungen, Update-Dialog, „Später"/Opt-out-Verhalten bleiben exakt wie vor
  der Umstellung — nur der Transportweg des Ergebnisses in den UI-Thread ändert sich.
- `RunController.start_update_check()` ist wie `start_run`/`start_write` ohne Display
  testbar (`tests/gui/test_controller.py`); die Queue-Dispatch-Logik in `MainWindow`
  ist über ungebundene Methodenaufrufe mit `MagicMock`-`self` ebenfalls ohne tk
  testbar (`tests/gui/test_main_window_update_check.py`).
- Ein weiterer `self.after(0, …)`-Aufruf aus einem Hintergrund-Thread besteht
  unverändert in `gui/update_dialog.py::_on_download_install` (Download-Fortschritt/
  -Abschluss/-Fehler, drei Stellen). Außerhalb des Scopes dieses ADRs, nur zur
  Kenntnis festgehalten (Issue #40 bezog sich ausschließlich auf `main_window.py`).
  `gui/app.py`s `app.after(0, lambda: show_beta_notice(app))` ist **kein** Beispiel
  desselben Musters — der Aufruf steht im Haupt-Thread von `run_app()`, nicht in
  einem Hintergrund-Thread.
