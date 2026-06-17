# ADR-0023: GUI-Architektur — Controller/Queue-Pattern + PID-Lockfile

**Status:** Accepted

## Kontext

Die tkinter-GUI (Schritt 6b) muss run_pass und write_selected in Hintergrund-Threads
ausführen, ohne die Oberfläche einzufrieren. Gleichzeitig müssen Controller-Logik und
Zustandsübergänge unit-testbar sein (CI auf Linux, kein Display).

## Entscheidung

1. **Controller/Queue-Pattern:** `RunController` in `gui/controller.py` kennt keine
   tk-Widgets. Er startet Threads und legt Ergebnis-Events (`ProgressEvent`,
   `RunDoneEvent`, `WriteDoneEvent`, `ErrorEvent`) in eine `queue.Queue` ab.
   Das MainWindow pollt die Queue mit `root.after(100, self._poll)` — alle GUI-Updates
   laufen damit sicher im tk-Mainloop-Thread. Keine direkten tk-Calls aus Threads.

2. **PID-Lockfile für Single-Instance:** `InstanceLock` in `gui/app.py` schreibt die
   eigene PID in `%APPDATA%\QSL73\qsl73.lock`. Beim Start prüft eine neue Instanz,
   ob die im Lockfile gespeicherte PID noch läuft (`os.kill(pid, 0)`). Ist sie aktiv,
   beendet sich die neue Instanz mit einer Hinweismeldung. Der Mechanismus ist
   plattformtolerant (auf Linux: funktioniert im Test; auf Windows: produktiv wirksam).
   Kein pywin32 erforderlich — bewusst einfacher als Win32-Mutex, ausreichend für
   den Anwendungsfall (einmaliger Start durch DF1DS per Doppelklick).

3. **tk-Skip-Guard in Tests:** Tests in `tests/gui/` die echte Fenster brauchen,
   erhalten ein `pytestmark = pytest.mark.skipif(not _tk_available(), ...)`.
   Controller-, Filter- und Logik-Tests brauchen keinen Skip-Guard.

## Konsequenzen

+ Controller vollständig ohne Display testbar
+ tk-Updates thread-sicher (ausschließlich via root.after)
+ Kein zusätzlicher Dependency für Single-Instance
- Stale-Lock bei unsauberem Programmabbruch möglich (PID-Recycling-Risiko gering
  da QSL73 nur einmal am Tag genutzt wird; Lock wird beim sauberen Beenden gelöscht)
