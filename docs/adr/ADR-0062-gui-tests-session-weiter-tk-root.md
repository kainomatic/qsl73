# ADR-0062: GUI-Tests nutzen einen session-weiten tk-Root

**Status:** Accepted

## Kontext

Issue #40: Der volle `pytest -m "not slow"`-Lauf stürzte auf der Windows-Dev-Maschine
reproduzierbar mit `Tcl_AsyncDelete: async handler deleted by the wrong thread` ab.
Per Bisektion belegt: Ursache waren mehrere hundert einzelne `tk.Tk()`-Erzeugungen und
-Zerstörungen in einem einzigen Python-Prozess — jede Testdatei unter `tests/gui/`
erzeugte pro tk-Test ein eigenes `tk.Tk()`-Root und zerstörte es am Testende wieder.
Das erschöpft die Tcl-Runtime, keine Logikursache im Anwendungscode. CI (Linux, ohne
Display) war nicht betroffen, da dort alle tk-Tests skippen.

Zusätzlich definierte jede tk-Testdatei ihre eigene `_tk_available()`/`_has_display()`-
Prüfung (Duplikat an sechs Stellen), die selbst schon ein `tk.Tk()` erzeugte und
zerstörte — verschärfte das Problem weiter, ohne einen fachlichen Vorteil zu bieten.

## Entscheidung

Genau **ein** `tk.Tk()`-Root pro Testprozess, bereitgestellt über eine
session-scoped pytest-Fixture in `tests/gui/conftest.py`:

- `tk_root` (session-scoped): erzeugt einmalig ein verstecktes (`withdraw()`) Root,
  zerstört es am Sessionende. Ist kein Display/tk verfügbar, skippt die Fixture per
  `pytest.skip(...)` — das skippt automatisch jeden Test, der sie (direkt oder über
  `tk_child`) anfordert. Dies ist die **einzige** zentrale tk-Verfügbarkeitsprüfung;
  die bisherigen sechs pro Datei duplizierten `_tk_available()`/`_has_display()`
  entfallen ersatzlos.
- `tk_child` (function-scoped): liefert je Test ein frisches `tk.Toplevel`-Kind von
  `tk_root` statt eines neuen `tk.Tk()`. Nach dem Test wird nur dieses Toplevel (und
  seine Kinder) zerstört, nicht der Session-Root.

Einzelne Tests, die intern mehrere sequentielle "Root"-artige Fenster brauchen (z. B.
`test_about_dialog.py`, das zwei Dialogvarianten nacheinander misst), erzeugen dafür
`tk.Toplevel(tk_root)` direkt im Testkörper statt `tk.Tk()` — Erzeugung/Zerstörung
bleibt dort test-lokal, betrifft aber nie den Session-Root selbst.

Dialoge, die als Toplevel-Kind ihres Parents gesucht werden (`_find_toplevel(root)`),
funktionieren unverändert: `tk.Toplevel` unterstützt dieselbe API (`winfo_children()`,
`after()`, `update()`, `destroy()`) wie `tk.Tk()`, daher genügt der Austausch des
Parent-Objekts ohne Änderung der Testlogik.

## Konsequenzen

- Neue GUI-Tests unter `tests/gui/` folgen diesem Muster: kein `tk.Tk()` mehr im
  einzelnen Test, stattdessen `tk_root`- oder `tk_child`-Fixture anfordern.
- `pytest -m "not slow"` läuft auf der Windows-Dev-Maschine mehrfach hintereinander
  im selben Prozess durch, ohne Tcl-Absturz (siehe Auftragsbericht zu Issue #40).
- Skip-Verhalten bleibt für CI (kein Display) unverändert: dieselben Tests skippen
  weiterhin, nur die Prüfung liegt jetzt zentral in `conftest.py`.
- Ein `Variable.__del__`-Warning (`RuntimeError: main thread is not in main loop`)
  tritt gelegentlich am Sessionende auf, wenn eine `tk.StringVar` o. ä. den
  Interpreter überlebt — bislang nur als `PytestUnraisableExceptionWarning`, keine
  Testfehler. Nicht Gegenstand dieses ADRs; bei Bedarf separates Issue.
